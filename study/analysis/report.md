# Sunset rating label analysis — first pass

> **Note (2026-10-26):** written when the code was JavaScript. It has since been
> migrated to Python (NEXT-STEPS C1). File mapping: `sunset_score.py`/`.js` →
> `src/sunset/scoring.py` (+ `models.py`); `pinpoint.js` → `pinpoint.py`, `cli.py`,
> `sources/openmeteo.py`, `geo.py`; `terrain.js` → `terrain.py`; `label_data.js` →
> `study/ratings/ratings.json`; `label_analysis.js` → `label_analysis.py`.
> See ARCHITECTURE.md. The text below is unchanged.

Source data: `study/ratings/photo-ratings.md` (8 photos x 2 raters = 16 reviews),
hand-tagged into 11 signed labels (+1 praised / -1 criticized / 0 not mentioned)
across three tiers. See `study/analysis/label_data.js` for the full tagged dataset and
per-row reasoning, `study/analysis/label_analysis.js` for the analysis code.

Tiers:
- **sky_weather** — forecastable from a weather model: `cloud_amount`,
  `cloud_type_color`, `color_vibrancy`, `gradient_transition`, `cloud_reflection`
- **geometry** — forecastable from sun position + viewpoint, no weather needed:
  `sun_timing`, `water_reflection`
- **photo_specific** — artifact of that photo/photographer/spot, not forecastable:
  `foreground_quality`, `focus_sharpness`, `obstructions`,
  `sun_obstruction_by_foreground`

## Pass 1 — correlation (pooled, n=16)

| Label | r | Tier |
|---|---:|---|
| foreground_quality | 0.595 | photo_specific |
| focus_sharpness | 0.590 | photo_specific |
| sun_obstruction_by_foreground | 0.496 | photo_specific |
| cloud_reflection | 0.467 | sky_weather |
| sun_timing | -0.447 | geometry |
| water_reflection | 0.234 | geometry |
| gradient_transition | -0.188 | sky_weather |
| cloud_amount | 0.183 | sky_weather |
| cloud_type_color | 0.101 | sky_weather |
| color_vibrancy | 0.091 | sky_weather |
| obstructions | -0.020 | photo_specific |

**The strongest correlates are photo-specific**, not sky/geometry. Foreground
quality and focus outrank every weather-driven label. This is the headline
finding for the "predict without the photo" goal below.

## Pass 1b — per-rater (n=8 each)

Sandy's top correlate: `focus_sharpness` (0.796), then `foreground_quality`
(0.738). Aaron's top correlate: `water_reflection` (0.581), then
`gradient_transition` (-0.464). The two raters' rankings don't agree well —
consistent with risk-poc.md's open question about whether "sunset quality" is
a shared objective property. At n=8 per rater this is suggestive, not proof;
the planned rating-consistency study (risk-poc.md POC 1) is still the right
way to settle it properly.

## Pass 2 — ridge regression (standardized features, leave-one-out CV, alpha=2)

**All 11 labels:** LOO R^2 = 0.555, RMSE = 1.14 (on a 1-10 scale). Top
coefficients: `foreground_quality` (0.656), `water_reflection` (0.599),
`focus_sharpness` (0.554), `cloud_amount` (0.524), `sun_obstruction_by_foreground`
(0.521).

**sky_weather + geometry labels only (the "transferable" subset — what a
forecast-based predictor could ever see):** LOO R^2 = 0.188, RMSE = 1.54. Top
coefficients: `sun_timing` (-0.851), `cloud_reflection` (0.773),
`water_reflection` (0.614).

## What this means for "predict the rating without the photo"

Dropping the photo-specific labels roughly **triples the unexplained variance**
(R^2 0.555 -> 0.188) in this sample. That's the honest ceiling estimate right
now: a forecast-only predictor, even a perfect one, may only explain a modest
fraction of what makes Sandy or Aaron score a sunset highly — a lot of the
signal in these reviews is about that specific photo (composition, focus,
incidental foreground), not the sky itself.

Practical implications:
- `cloud_reflection`, `sun_timing`, and `water_reflection` are the load-bearing
  transferable labels so far — worth prioritizing if/when calibrating
  `sunset_score.py` against this data.
- `color_vibrancy` and `cloud_type_color`, despite being frequently mentioned
  (12 and 7 mentions respectively), barely correlate with score (r=0.09, 0.10).
  Either they're genuinely weak drivers, or the label is too coarse to capture
  what's actually being judged — worth a closer look before trusting the null result.
- `obstructions` shows ~zero correlation (-0.02) despite being photo-specific —
  wires/poles/cutoff framing get mentioned but don't seem to move the score much
  in this sample.

## Caveats (read before acting on any of this)

- **n=16**, 8 of which are Sandy and 8 Aaron — every number above has a wide
  confidence interval. Treat rankings as directional, not definitive.
- Labels were hand-tagged by Claude from short free text, with real judgment
  calls on ambiguous phrases (documented inline in `label_data.js`). A
  different tagger could reasonably produce different numbers.
- Ridge alpha=2 was picked as a reasonable default, not tuned; LOO R^2 at this
  sample size is itself high-variance and will shift if more data comes in.
- This is a first pass meant to surface direction, not a result to calibrate
  `sunset_score.py` against yet — that should wait for a larger rated set
  (the 33 remaining downloaded, unrated photos) and ideally the risk-poc.md
  rating-consistency study.
