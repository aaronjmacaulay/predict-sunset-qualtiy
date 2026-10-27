"""
label_analysis.py — what drives the human sunset ratings?

Reads study/ratings/ratings.json (hand-tagged labels per review) and runs:

Pass 1: Pearson correlation of each label with score (pooled, and per rater) -
        robust at small N, doubles as a rating-consistency check between raters.
Pass 2: Ridge regression (standardized features, leave-one-out CV) as an actual
        predictor, with coefficients ranked by influence. Run on all labels, and
        on sky_weather + geometry labels only (the "transferable to a
        forecast-based predictor" subset), each with and without a rater_id
        feature (does knowing WHO is rating help?).

Run: uv run python study/analysis/label_analysis.py
"""

import json
from pathlib import Path

import numpy as np

RATINGS = Path(__file__).resolve().parents[1] / "ratings" / "ratings.json"


def load(path=RATINGS):
    data = json.loads(Path(path).read_text())
    return data["labels"], data["reviews"]


def pearson(xs, ys):
    x, y = np.asarray(xs, float), np.asarray(ys, float)
    dx, dy = x - x.mean(), y - y.mean()
    denom = np.sqrt((dx ** 2).sum() * (dy ** 2).sum())
    return 0.0 if denom == 0 else float((dx * dy).sum() / denom)


def correlation_pass(rows, label_names, title):
    scores = [r["score"] for r in rows]
    results = []
    for name in label_names:
        xs = [r["labels"][name] for r in rows]
        results.append((name, pearson(xs, scores), sum(v != 0 for v in xs)))
    results.sort(key=lambda t: abs(t[1]), reverse=True)  # stable, like the JS sort

    print(f"\n=== Correlation pass: {title} (n={len(rows)}) ===")
    print("label".ljust(32) + "r".rjust(8) + "  mentions")
    for name, r, n in results:
        print(name.ljust(32) + f"{r:.3f}".rjust(8) + f"  {n}")
    return results


def standardize(X):
    """Population std (ddof=0); all-zero columns get std 1 to avoid divide-by-zero."""
    std = X.std(axis=0)
    std[std == 0] = 1
    return (X - X.mean(axis=0)) / std


def ridge_fit(X, y, alpha):
    """Ridge on centred y, no intercept term in the penalty. Returns (beta, intercept)."""
    intercept = y.mean()
    beta = np.linalg.solve(X.T @ X + alpha * np.eye(X.shape[1]), X.T @ (y - intercept))
    return beta, intercept


def ridge_pass(rows, label_names, title, alpha=2.0):
    X = standardize(np.array([[r["labels"][n] for n in label_names] for r in rows], float))
    y = np.array([r["score"] for r in rows], float)
    n = len(y)

    beta, _ = ridge_fit(X, y, alpha)

    # Leave-one-out CV for an honest (if noisy) accuracy estimate.
    # Note: standardization uses all rows, as in the original JS analysis.
    sse = 0.0
    for i in range(n):
        keep = np.arange(n) != i
        b, ic = ridge_fit(X[keep], y[keep], alpha)
        sse += (ic + X[i] @ b - y[i]) ** 2
    sst = ((y - y.mean()) ** 2).sum()
    loo_r2, loo_rmse = 1 - sse / sst, np.sqrt(sse / n)

    coefs = sorted(zip(label_names, beta), key=lambda t: abs(t[1]), reverse=True)
    print(f"\n=== Ridge regression: {title} (n={n}, alpha={alpha:g}) ===")
    print("label".ljust(32) + "coef".rjust(8))
    for name, c in coefs:
        print(name.ljust(32) + f"{c:.3f}".rjust(8))
    print(f"Leave-one-out R^2 = {loo_r2:.3f}   RMSE = {loo_rmse:.2f} (score scale 1-10)")
    return coefs, loo_r2, loo_rmse


def main():
    labels, rows = load()
    all_names = [l["name"] for l in labels]
    transferable = [l["name"] for l in labels if l["tier"] != "photo_specific"]

    correlation_pass(rows, all_names, "pooled (Sandy + Aaron)")
    correlation_pass([r for r in rows if r["rater"] == "Sandy"], all_names, "Sandy only")
    correlation_pass([r for r in rows if r["rater"] == "Aaron"], all_names, "Aaron only")

    ridge_pass(rows, all_names, "all labels, pooled")
    ridge_pass(rows, transferable, "sky_weather + geometry labels only, pooled")

    # Does knowing WHO is rating help, on top of the labels? Add a rater_id
    # feature (Sandy=-1, Aaron=+1) to the pooled model instead of fitting two
    # separate n=8 models (too few rows for this many features each).
    with_id = [{**r, "labels": {**r["labels"], "rater_id": 1 if r["rater"] == "Aaron" else -1}} for r in rows]
    ridge_pass(with_id, all_names + ["rater_id"], "all labels + rater_id, pooled")
    ridge_pass(with_id, transferable + ["rater_id"], "sky_weather + geometry labels + rater_id, pooled")


if __name__ == "__main__":
    main()
