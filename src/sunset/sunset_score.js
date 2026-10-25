// sunset_score.js — direct port of sunset_score.py's pure scoring math (no I/O).
// Keep in sync with sunset_score.py; either can be checked against the other's
// worked examples. See sunset_score.py's module docstring for the modelling
// rationale (multiplicative chain of necessary conditions, not a weighted average).

function clamp(x, lo, hi) {
  return Math.max(lo, Math.min(hi, x));
}

function bell(x, mu, sigma) {
  return Math.exp(-((x - mu) ** 2) / (2 * sigma ** 2));
}

// TERM 1 — light path gate: can the light physically get through?
function lightPathGate(cloudLowUpwind, terrainBlockDeg) {
  const path = 1.0 - (clamp(cloudLowUpwind, 0, 100) / 100.0) ** 1.5;
  const terrain = clamp(1.0 - terrainBlockDeg / 8.0, 0.25, 1.0);
  return { gate: path * terrain, path, terrain };
}

// TERM 2 — canvas: is there anything up there to light up?
function canvas(cloudHigh, cloudMid) {
  const high = bell(cloudHigh, 55, 28);
  const mid = bell(cloudMid, 30, 25);
  return { canvas: clamp(0.70 * high + 0.30 * mid, 0.0, 1.0), high, mid };
}

// TERM 3 — clarity: will the colour arrive saturated or washed out?
function clarity(rh2m, visibilityM, pblHeightM) {
  const rhF = clamp(1.0 - (rh2m - 45.0) / 55.0, 0.25, 1.0);
  const visF = clamp(visibilityM / 24000.0, 0.20, 1.0);
  const pblF = clamp(0.55 + (pblHeightM / 2000.0) * 0.45, 0.55, 1.0);
  return { clarity: rhF ** 0.5 * visF ** 0.6 * pblF, rhF, visF, pblF };
}

// TERM 4 — aerosol: the colour-saturation multiplier.
function aerosol(aod, pm25) {
  const boost = 0.85 + 0.35 * bell(aod, 0.18, 0.12);
  const overload = aod > 0.5 ? clamp(1.0 - (aod - 0.5) / 0.8, 0.35, 1.0) : 1.0;
  const pmPen = clamp(1.0 - Math.max(0.0, pm25 - 20.0) / 60.0, 0.5, 1.0);
  return { aerosol: boost * overload * pmPen, boost, overload, pmPen };
}

function label(s) {
  if (s >= 75) return "exceptional";
  if (s >= 55) return "very good";
  if (s >= 35) return "decent";
  if (s >= 18) return "mediocre";
  return "poor";
}

function score(o, trace = false) {
  const { gate, path, terrain } = lightPathGate(o.cloud_low_upwind, o.terrain_block_deg);
  const { canvas: canv, high: cHi, mid: cMid } = canvas(o.cloud_high, o.cloud_mid);
  const { clarity: clar, rhF, visF, pblF } = clarity(o.rh_2m, o.visibility_m, o.pbl_height_m);
  const { aerosol: aer, boost, overload, pmPen } = aerosol(o.aod, o.pm25);

  const raw = gate * canv * clar * aer;
  const final = clamp(Math.round(raw * 100), 0, 100);

  if (trace) {
    console.log(`  TERM 1  light path gate           = ${gate.toFixed(3)}`);
    console.log(`            upwind low cloud ${o.cloud_low_upwind.toFixed(0).padStart(5)}%  -> path    ${path.toFixed(3)}`);
    console.log(`            terrain block   ${o.terrain_block_deg.toFixed(1).padStart(5)}deg -> terrain ${terrain.toFixed(3)}`);
    console.log(`  TERM 2  canvas                    = ${canv.toFixed(3)}`);
    console.log(`            high cloud      ${o.cloud_high.toFixed(0).padStart(5)}%  -> bell    ${cHi.toFixed(3)}  (x0.70)`);
    console.log(`            mid cloud       ${o.cloud_mid.toFixed(0).padStart(5)}%  -> bell    ${cMid.toFixed(3)}  (x0.30)`);
    console.log(`  TERM 3  clarity                   = ${clar.toFixed(3)}`);
    console.log(`            RH              ${o.rh_2m.toFixed(0).padStart(5)}%  -> ${rhF.toFixed(3)} ^0.5`);
    console.log(`            visibility   ${o.visibility_m.toFixed(0).padStart(8)}m  -> ${visF.toFixed(3)} ^0.6`);
    console.log(`            PBL height   ${o.pbl_height_m.toFixed(0).padStart(8)}m  -> ${pblF.toFixed(3)}`);
    console.log(`  TERM 4  aerosol multiplier        = ${aer.toFixed(3)}`);
    console.log(`            AOD            ${o.aod.toFixed(2).padStart(6)}   -> boost   ${boost.toFixed(3)}`);
    console.log(`            overload factor           ${overload.toFixed(3)}`);
    console.log(`            PM2.5          ${o.pm25.toFixed(1).padStart(6)}   -> ${pmPen.toFixed(3)}`);
    console.log(`  ----------------------------------------------------`);
    console.log(`  ${gate.toFixed(3)} x ${canv.toFixed(3)} x ${clar.toFixed(3)} x ${aer.toFixed(3)} = ${raw.toFixed(4)}`);
    console.log(`  SCORE = ${final}/100   (${label(final)})`);
  }

  return final;
}

const SCENARIOS = {
  "Post-frontal classic": { cloud_high: 60, cloud_mid: 25, cloud_low_upwind: 10, rh_2m: 48, visibility_m: 24000, pbl_height_m: 1400, aod: 0.16, pm25: 7, terrain_block_deg: 0.5 },
  "Marine layer (coastal summer)": { cloud_high: 55, cloud_mid: 20, cloud_low_upwind: 85, rh_2m: 88, visibility_m: 9000, pbl_height_m: 350, aod: 0.10, pm25: 6, terrain_block_deg: 0.5 },
  "Wildfire smoke, moderate": { cloud_high: 35, cloud_mid: 15, cloud_low_upwind: 5, rh_2m: 40, visibility_m: 14000, pbl_height_m: 1600, aod: 0.42, pm25: 38, terrain_block_deg: 0.5 },
  "Wildfire smoke, heavy": { cloud_high: 30, cloud_mid: 10, cloud_low_upwind: 5, rh_2m: 38, visibility_m: 4000, pbl_height_m: 1500, aod: 1.30, pm25: 145, terrain_block_deg: 0.5 },
  "Pair A: clear to the west": { cloud_high: 55, cloud_mid: 20, cloud_low_upwind: 5, rh_2m: 55, visibility_m: 20000, pbl_height_m: 1200, aod: 0.18, pm25: 10, terrain_block_deg: 0.5 },
  "Pair B: same sky, deck 120km west": { cloud_high: 55, cloud_mid: 20, cloud_low_upwind: 75, rh_2m: 55, visibility_m: 20000, pbl_height_m: 1200, aod: 0.18, pm25: 10, terrain_block_deg: 0.5 },
  "Bluebird clear sky": { cloud_high: 0, cloud_mid: 0, cloud_low_upwind: 0, rh_2m: 45, visibility_m: 24000, pbl_height_m: 1800, aod: 0.09, pm25: 4, terrain_block_deg: 0.5 },
  "Solid overcast": { cloud_high: 100, cloud_mid: 95, cloud_low_upwind: 95, rh_2m: 92, visibility_m: 7000, pbl_height_m: 500, aod: 0.12, pm25: 9, terrain_block_deg: 0.5 },
  "Ideal sky, but ridge to the west": { cloud_high: 60, cloud_mid: 25, cloud_low_upwind: 10, rh_2m: 48, visibility_m: 24000, pbl_height_m: 1400, aod: 0.16, pm25: 7, terrain_block_deg: 6.0 },
};

module.exports = { score, label, SCENARIOS, lightPathGate, canvas, clarity, aerosol, bell, clamp };

if (require.main === module) {
  console.log("=".repeat(60));
  console.log("WORKED EXAMPLE — 'Post-frontal classic'");
  console.log("=".repeat(60));
  score(SCENARIOS["Post-frontal classic"], true);

  console.log();
  console.log("=".repeat(60));
  console.log("ALL SCENARIOS");
  console.log("=".repeat(60));
  for (const [name, obs] of Object.entries(SCENARIOS)) {
    const s = score(obs);
    const bar = "#".repeat(Math.floor(s / 2.5));
    console.log(`${name.padEnd(34)} ${String(s).padStart(3)}/100  ${bar} ${label(s)}`);
  }
}
