# Sunset rating labels: taxonomy, tagging methodology, and findings so far

> **Note (2026-10-26):** written when the code was JavaScript. It has since been
> migrated to Python (NEXT-STEPS C1). File mapping: `sunset_score.py`/`.js` →
> `src/sunset/scoring.py` (+ `models.py`); `pinpoint.js` → `pinpoint.py`, `cli.py`,
> `sources/openmeteo.py`, `geo.py`; `terrain.js` → `terrain.py`; `label_data.js` →
> `study/ratings/ratings.json`; `label_analysis.js` → `label_analysis.py`.
> See ARCHITECTURE.md. The text below is unchanged.

Status: living document, updated as the labeled dataset grows. Last updated
2026-08-18 after the initial 16-review pass (8 photos x Sandy + Aaron) and the
cloud-type/color split.

## 1. Purpose

Sandy and Aaron have been rating sunset photos in free text (a 1-10 score plus
Likes/Dislikes). The goal is to turn that free text into structured labels,
then use the labels to:

1. Understand which visual themes actually drive a high or low rating.
2. Eventually calibrate `sunset_score.py`'s physically-reasoned constants
   (research.md §8) against real human ratings instead of guessed weights.
3. Longer-term, predict a rating for a sunset **without a photo** — i.e. from
   a weather/astronomy forecast alone, the way someone deciding whether to
   drive to a viewpoint would need. This constrains the taxonomy: every label
   is tagged with whether it could ever come from a forecast, or whether it's
   inherently tied to one specific photo.

## 2. Data sources

- `study/ratings/photo-ratings.md` — 8 original camera photos, Sandy + Aaron,
  16 reviews total. Fully tagged (see `study/analysis/label_data.js`).
- `study/ratings/stock-userratings.md`, `study/ratings/stock-aaronreview.md` — blank
  templates for 16 additional stock photos (`study/photos/stock/`), chosen to fill
  condition/quality gaps the original 8 didn't cover. Not yet filled in —
  pending Sandy and Aaron.
- `study/photos/used/` vs `study/photos/unused/` — the 8 rated vs. 33 unrated original
  camera photos (`IMG_7206.jpg` was recovered separately; it was referenced
  in ratings but missing from the original download batch).

## 3. Label taxonomy

11 labels, each scored on a **signed scale per review**: `+1` praised
(appeared in Likes), `-1` criticized (appeared in Dislikes), `0` not
mentioned. See §4 for how multiple mentions of the same theme in one review
are combined.

Every label carries a **tier**, which is the load-bearing design decision
here — it says whether the label could ever be predicted from a forecast
without a photo:

- **sky_weather** — forecastable from a weather model (Open-Meteo-style
  cloud cover/type, humidity, aerosol data). Maps onto research.md groups
  A–C.
- **geometry** — forecastable from sun position + a known viewpoint, no
  weather model needed (astronomy + terrain). Maps onto research.md groups
  D–E. Depends on *where* the viewer stands, but not on that day's specific
  photo.
- **photo_specific** — an artifact of that exact photo, photographer, or
  spot. No plausible data source generalizes it. Not forecastable, full
  stop. Useful for knowing the ceiling on how well a forecast-only predictor
  could ever do, but not something to chase.

| Label | Tier | What it captures |
|---|---|---|
| `cloud_amount` | sky_weather | High/mid cloud "canvas" fullness — too little vs. too much/overcast. Mirrors `sunset_score.py`'s `canvas` term |
| `cloud_type` | sky_weather | Cloud structure/texture (cirrus-like, "brooding," "uniform," explicit "right type of clouds") — independent of color |
| `sun_blocking_clouds` | sky_weather | Low cloud specifically obstructing the sun's disk/glow, as distinct from overall cloud amount. Mirrors `sunset_score.py`'s `gate`/`path` term (upwind low cloud) |
| `color_vibrancy` | sky_weather | Hue/saturation of the sky or clouds — striking/saturated vs. unsaturated/plain/dull |
| `gradient_transition` | sky_weather | Smoothness of the color transition across the sky |
| `cloud_reflection` | sky_weather | Light reflecting off cloud undersides — needs a cloud deck to exist, so it's weather-gated even though the physics is sun-angle driven |
| `sun_timing` | geometry | Pre-peak / at-peak / post-peak relative to the color window — a function of clock time + location, no weather needed |
| `water_reflection` | geometry | Reflection quality on water, given water is in frame — driven by sun/viewer angle (specular geometry), not by weather |
| `foreground_quality` | photo_specific | Trees/buildings/water/composition at that specific spot |
| `focus_sharpness` | photo_specific | Camera/photographer artifact |
| `obstructions` | photo_specific | Wires, poles, cutoff framing, crooked horizon — that location's/photographer's clutter |
| `sun_obstruction_by_foreground` | photo_specific | "Sun behind trees" — a specific tree, not a sky property |
| `authenticity` | photo_specific | Photo reads as artificial/over-processed/fake ("too artificial," "almost feels fake") — a processing artifact, not a sky property |

### Tier decisions worth remembering

- **`cloud_reflection` stays `sky_weather`, not `geometry`**, even though
  reflection physics is sun-angle driven, because it also requires cloud
  cover to exist — and cloud cover has to be forecast. `water_reflection`
  is `geometry` because water's presence is a fixed property of the
  viewpoint (not weather), so only the sun-angle part varies day to day.
- **`cloud_type` was split out of a combined `cloud_type_color` label** on
  2026-08-18 (see §5) because type (structure) and color (hue/saturation)
  are physically distinct and separately forecastable, and conflating them
  was actively causing tagging errors (double-counting, mis-categorization).
- **`sun_blocking_clouds` was split out of `cloud_amount` and `authenticity`
  was added as a new label**, both on 2026-08-18, after reading Aaron's
  first batch of stock-photo reviews (see §5b). Both default to `0` across
  all 16 existing reviews — a clean additive change, no re-tagging needed,
  and confirmed to leave every existing correlation/regression number
  unchanged (`study/analysis/label_analysis.js` rerun, identical output for prior
  labels).

## 4. Tagging methodology — turning free text into label values

This is the part that isn't obvious from the code, so it's written down
here. Applied by hand (Claude reading each review) across all 16 reviews so
far; the same rules should apply to future batches for consistency.

1. **Read the full review, split into individual Likes/Dislikes phrases.**
   Each phrase is matched to zero, one, or more labels — a single phrase can
   span two themes (e.g. "bands of clouds and color shades" → both
   `cloud_type` and `gradient_transition`).
2. **Score each match `+1` if from Likes, `-1` if from Dislikes.**
3. **Net multiple mentions of the same label within one review by summing,
   then clipping to `{-1, 0, +1}`.** E.g. "decent reflection" (+1) and "need
   more reflections" (-1) in the same review nets to `0` — representing a
   genuinely mixed signal, not a coin-flip. This means `0` conflates "not
   mentioned" with "mentioned both ways" — a real limitation (see §6).
4. **Ambiguous generic praise defaults to `color_vibrancy`.** Phrases like
   "great sky" or "nice sky" with no more specific theme named are treated
   as a color impression, since that's the most common thing driving a
   generic positive reaction to a sky. This is a judgment call, not derived
   from the text itself — flagged so it can be revisited.
5. **Reflection phrases default to `cloud_reflection` unless water is
   explicitly present in that photo's other bullets** (e.g. "water view,"
   "landscape has ... water visible"), in which case they're tagged
   `water_reflection` instead. Ambiguous "good reflection" mentions were
   resolved this way rather than by guessing.
6. **Stray junk (typos, accidental text like "asdsa" after a photo link) is
   dropped**, not tagged to anything.
7. **No photo metadata (links, filenames) or composition praise beyond what's
   written is invented** — only what the rater actually wrote gets tagged.

### Known limitation: `0` is overloaded

Because step 3 nets mixed mentions to `0`, the current dataset can't
distinguish "this theme never came up" from "this theme came up as a wash."
Splitting into two fields (mention count + net sentiment) would fix this
but adds complexity; noted as a possible future refinement, not done yet
since it hasn't clearly mattered for the analysis so far.

## 5. Cloud type vs. color split (2026-08-18)

Originally `cloud_type_color` combined structure and color into one label.
Splitting it surfaced two real tagging bugs, both now fixed in
`study/analysis/label_data.js`:

- IMG_2081/Aaron: "nice bright orange on the clouds" had been tagged to
  *both* `cloud_type_color` and `color_vibrancy` — a straightforward
  double-count. Now counted only once, under `color_vibrancy`.
- IMG_0914/Aaron: "cloud colour is not great, a redder or orangey cloud
  would be better" had been folded into the type label. It's a color
  complaint, not a structural one — moved to `color_vibrancy` (`-1`); the
  same review's "right cloud type creating good reflection" is genuinely
  structural and stayed as `cloud_type` (`+1`).

Post-split result: `cloud_type` alone correlates with score at r=-0.07
(pooled, n=16) — essentially no signal — while `color_vibrancy` strengthened
to r=0.12 pooled (r=0.40 for Aaron specifically). In this small sample,
what predicts a high rating is whether clouds are *present and lit up*, not
their structural type. This may be a real finding or an artifact of n=16 and
short free-text reviews that rarely name specific cloud types — worth
re-checking once the stock-photo batch (which deliberately includes several
"vivid cirrus" examples) is rated.

## 5b. Sun-blocking clouds, authenticity, and a data-quality gate (2026-08-18)

Aaron's first pass at reviewing the 16 stock photos surfaced patterns the
taxonomy didn't have room for:

- **"The low-lying clouds are obstructing the sun"** (STOCK_02) is a
  distinct concern from `cloud_amount` — it's specifically low cloud
  blocking the sun's disk/glow, matching `sunset_score.py`'s `gate` term
  (upwind low cloud, exponent 1.5) as opposed to its `canvas` term (high/mid
  cloud fullness, which `cloud_amount` now represents). Added as
  `sun_blocking_clouds` (sky_weather).
- **"Too artificial," "almost feels fake"** (STOCK_06, STOCK_08) is a new
  failure mode: over-processed/over-saturated color reads as fake and gets
  penalized, independent of the color itself being technically vibrant.
  Added as `authenticity` (photo_specific — it's about that photo's
  processing, not a sky property).
- **Modeling note, not a taxonomy change:** the authenticity finding hints
  `color_vibrancy` may be non-monotonic — like the aerosol bell curve
  already in `sunset_score.py`'s Term 4 (moderate is a bonus, too much
  tips into "brown"/"fake") — rather than simply "more praise is better."
  Not worth splitting into separate under/over-saturation labels at n=16;
  revisit once there's more data specifically showing both failure
  directions.
- **"Not a sunset" is a data-quality flag, not a label.** Aaron marked
  STOCK_09 this way, and separately declined to rate STOCK_06/10/11/16 as
  "too artificial or weren't sunset photos" (STOCK_10/11/16 have since been
  removed from `study/photos/stock/` entirely). These get **excluded and replaced**
  with a different photo under the same STOCK_NN slot — never tagged with
  any label — the same way the original 4 mistagged stock photos were
  swapped out right after download (see `study/photos/stock/ATTRIBUTION.md`).
  Replacements for STOCK_06/09/10/11/16 are pending as of this writing.

## 6. Findings so far (n=16, pending the 16 stock-photo ratings)

Full detail and code: `study/analysis/report.md`, `study/analysis/label_analysis.js`,
`study/analysis/label_data.js`. Headlines:

- **Photo-specific labels correlate most strongly with score** —
  `foreground_quality` (r=0.60), `focus_sharpness` (r=0.59),
  `sun_obstruction_by_foreground` (r=0.50) all outrank every sky_weather/
  geometry label.
- **Ridge regression, leave-one-out CV:** all 11 labels → R²=0.54;
  restricted to sky_weather+geometry only (the "transferable" set) →
  R²=0.21. A forecast-only predictor's honest ceiling, on this data, is
  low — a lot of what drives these ratings is about the specific photo, not
  the sky.
- **A `rater_id` feature (Sandy vs. Aaron) doesn't help and slightly hurts
  LOO R²** — the two raters aren't offset by a constant amount, they weight
  *different labels* differently (Sandy: focus/foreground; Aaron: water
  reflection/gradient). This is an interaction effect a flat indicator
  can't capture, and echoes the open rating-consistency question in
  `risk-poc.md`.
- **Top transferable labels so far:** `cloud_reflection`, `sun_timing`,
  `water_reflection`, `color_vibrancy` — these carry what little
  forecast-transferable signal exists in this sample.

## 7. Open items / next steps

- Replace STOCK_06, STOCK_09, STOCK_10, STOCK_11, STOCK_16 (flagged by
  Aaron as artificial-looking or not sunsets at all; three of the five
  files are already gone from `study/photos/stock/`) and get his reviews for the
  replacements before merging his stock ratings anywhere.
- Get Sandy and Aaron's ratings for the 16 stock photos
  (`study/ratings/stock-userratings.md`, `study/ratings/stock-aaronreview.md`),
  merge into `photo-ratings.md` the same way as before, hand-tag against
  this taxonomy, and rerun both analysis passes at n=48 (3 ratings per
  photo now — enables real inter-rater agreement stats, not just n=8-per-
  rater correlation).
- Revisit the `0`-is-overloaded limitation (§4) if it starts to matter.
- Once there's enough data to trust it, feed the sky_weather/geometry
  findings back into `sunset_score.py`'s constants (research.md §8's
  calibration caveat already flags this as the intended next step).
