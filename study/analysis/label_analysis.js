// label_analysis.js — two analysis passes over the hand-tagged sunset rating labels.
//
// Pass 1: Pearson correlation of each label with score (pooled, and per rater) —
//         robust at small N, doubles as a rating-consistency check between raters.
// Pass 2: Ridge regression (standardized features, leave-one-out CV) as an actual
//         predictor, reported with coefficients ranked by influence. Run once on
//         all labels, and again restricted to sky_weather + geometry labels only
//         (the "transferable to a forecast-based predictor" subset).
//
// Run: node study/analysis/label_analysis.js

const { LABELS, ROWS } = require("./label_data");

function pearson(xs, ys) {
  const n = xs.length;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;
  let num = 0, dx2 = 0, dy2 = 0;
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - mx, dy = ys[i] - my;
    num += dx * dy; dx2 += dx * dx; dy2 += dy * dy;
  }
  if (dx2 === 0 || dy2 === 0) return 0;
  return num / Math.sqrt(dx2 * dy2);
}

function correlationPass(rows, labelNames, title) {
  const scores = rows.map(r => r.score);
  const results = labelNames.map(name => {
    const xs = rows.map(r => r.labels[name]);
    return { name, r: pearson(xs, scores), nMentions: xs.filter(v => v !== 0).length };
  });
  results.sort((a, b) => Math.abs(b.r) - Math.abs(a.r));
  console.log(`\n=== Correlation pass: ${title} (n=${rows.length}) ===`);
  console.log("label".padEnd(32) + "r".padStart(8) + "  mentions");
  for (const res of results) {
    console.log(res.name.padEnd(32) + res.r.toFixed(3).padStart(8) + "  " + res.nMentions);
  }
  return results;
}

// ---- minimal matrix helpers (plain arrays of arrays) ----
function transpose(A) { return A[0].map((_, j) => A.map(row => row[j])); }
function matmul(A, B) {
  const r = A.length, k = B.length, c = B[0].length;
  const out = Array.from({ length: r }, () => new Array(c).fill(0));
  for (let i = 0; i < r; i++)
    for (let j = 0; j < c; j++) {
      let s = 0;
      for (let m = 0; m < k; m++) s += A[i][m] * B[m][j];
      out[i][j] = s;
    }
  return out;
}
function matvec(A, v) { return A.map(row => row.reduce((s, a, j) => s + a * v[j], 0)); }
function addScaledIdentity(A, alpha) {
  return A.map((row, i) => row.map((v, j) => (i === j ? v + alpha : v)));
}
function invert(A) {
  const n = A.length;
  const M = A.map((row, i) => [...row, ...Array.from({ length: n }, (_, j) => (i === j ? 1 : 0))]);
  for (let col = 0; col < n; col++) {
    let pivot = col;
    for (let r = col + 1; r < n; r++) if (Math.abs(M[r][col]) > Math.abs(M[pivot][col])) pivot = r;
    [M[col], M[pivot]] = [M[pivot], M[col]];
    const pv = M[col][col];
    for (let j = 0; j < 2 * n; j++) M[col][j] /= pv;
    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const f = M[r][col];
      for (let j = 0; j < 2 * n; j++) M[r][j] -= f * M[col][j];
    }
  }
  return M.map(row => row.slice(n));
}

function standardize(X) {
  const n = X.length, p = X[0].length;
  const means = new Array(p).fill(0), stds = new Array(p).fill(0);
  for (let j = 0; j < p; j++) {
    means[j] = X.reduce((s, row) => s + row[j], 0) / n;
  }
  for (let j = 0; j < p; j++) {
    const variance = X.reduce((s, row) => s + (row[j] - means[j]) ** 2, 0) / n;
    stds[j] = Math.sqrt(variance) || 1; // avoid divide-by-zero for all-zero columns
  }
  const Xs = X.map(row => row.map((v, j) => (v - means[j]) / stds[j]));
  return { Xs, means, stds };
}

function ridgeFit(X, y, alpha) {
  const n = X.length;
  const my = y.reduce((a, b) => a + b, 0) / n;
  const yc = y.map(v => v - my);
  const Xt = transpose(X);
  const XtX = matmul(Xt, X);
  const XtXreg = addScaledIdentity(XtX, alpha);
  const XtXinv = invert(XtXreg);
  const Xty = matvec(Xt, yc);
  const beta = matvec(XtXinv, Xty);
  return { beta, intercept: my };
}

function ridgePredict(beta, intercept, x) {
  return intercept + x.reduce((s, v, j) => s + v * beta[j], 0);
}

function ridgePass(rows, labelNames, title, alpha = 2.0) {
  const rawX = rows.map(r => labelNames.map(name => r.labels[name]));
  const y = rows.map(r => r.score);
  const { Xs } = standardize(rawX);

  // fit on all data for the reported coefficients
  const { beta, intercept } = ridgeFit(Xs, y, alpha);

  // leave-one-out CV for an honest (if noisy) accuracy estimate
  const n = Xs.length;
  let sse = 0, sst = 0;
  const meanY = y.reduce((a, b) => a + b, 0) / n;
  for (let i = 0; i < n; i++) {
    const trainX = Xs.filter((_, idx) => idx !== i);
    const trainY = y.filter((_, idx) => idx !== i);
    const { beta: b, intercept: ic } = ridgeFit(trainX, trainY, alpha);
    const pred = ridgePredict(b, ic, Xs[i]);
    sse += (pred - y[i]) ** 2;
    sst += (y[i] - meanY) ** 2;
  }
  const looR2 = 1 - sse / sst;
  const looRMSE = Math.sqrt(sse / n);

  const coefTable = labelNames
    .map((name, j) => ({ name, coef: beta[j] }))
    .sort((a, b) => Math.abs(b.coef) - Math.abs(a.coef));

  console.log(`\n=== Ridge regression: ${title} (n=${n}, alpha=${alpha}) ===`);
  console.log("label".padEnd(32) + "coef".padStart(8));
  for (const c of coefTable) console.log(c.name.padEnd(32) + c.coef.toFixed(3).padStart(8));
  console.log(`Leave-one-out R^2 = ${looR2.toFixed(3)}   RMSE = ${looRMSE.toFixed(2)} (score scale 1-10)`);
  return { coefTable, looR2, looRMSE };
}

// ---------------------------------------------------------------------------

const allLabelNames = LABELS.map(l => l.name);
const transferableNames = LABELS.filter(l => l.tier !== "photo_specific").map(l => l.name);

const sandyRows = ROWS.filter(r => r.rater === "Sandy");
const aaronRows = ROWS.filter(r => r.rater === "Aaron");

correlationPass(ROWS, allLabelNames, "pooled (Sandy + Aaron)");
correlationPass(sandyRows, allLabelNames, "Sandy only");
correlationPass(aaronRows, allLabelNames, "Aaron only");

ridgePass(ROWS, allLabelNames, "all labels, pooled");
ridgePass(ROWS, transferableNames, "sky_weather + geometry labels only, pooled");

// ---- does knowing WHO is rating help, on top of the labels? ----
// Add a rater_id feature (Sandy=-1, Aaron=+1) to the pooled model instead of
// fitting two separate n=8 models (too few rows for 11 features each).
const rowsWithRaterId = ROWS.map(r => ({
  ...r,
  labels: { ...r.labels, rater_id: r.rater === "Aaron" ? 1 : -1 },
}));

ridgePass(rowsWithRaterId, [...allLabelNames, "rater_id"], "all labels + rater_id, pooled");
ridgePass(rowsWithRaterId, [...transferableNames, "rater_id"], "sky_weather + geometry labels + rater_id, pooled");
