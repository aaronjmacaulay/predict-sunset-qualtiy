# Tier 1: live pinpoint sunset scoring tool

Status: implemented and live-tested. This is the "Tier 1 — basic pinpoint
scoring tool" from research.md §5, wired up to real weather data.

## 1. Purpose

Turn `sunset_score.py`'s scoring formula from a set of hand-written scenario
constants into a live tool: give it a coordinate and a date, it fetches real
forecast data for that location's actual sunset moment and returns a score.
This is the foundation Tier 2 (terrain occlusion) and Tier 3 (live
satellite/webcam) build on top of.

## 2. Why JavaScript, not Python

`sunset_score.py` is Python, but there is no real Python installed on this
machine — only the Windows Store stub alias. Node.js is what's actually on
PATH and what the label-analysis scripts (`analysis/*.js`) already use. To
keep this testable and runnable, the scoring math was ported to
`src/sunset_score.js` (pure functions, no I/O) rather than extended in a
language that can't be executed here. The port was verified to reproduce
`sunset_score.py`'s worked example exactly: "Post-frontal classic" → 90/100,
and all 9 scenarios in `SCENARIOS` match. Keep both files in sync manually
if the scoring formula changes; there's no automated cross-check.

## 3. Architecture

Two files, split so the pure scoring math stays independently testable:

- **`src/sunset_score.js`** — direct port of `sunset_score.py`. No network
  I/O. Exports `score()`, `label()`, `SCENARIOS`, and the four term
  functions.
- **`src/pinpoint.js`** — the live tool. All fetching and geometry live
  here; it builds the same input shape `sunset_score.py` already uses and
  calls `score(..., trace=true)`.

CLI: `node src/pinpoint.js <lat> <lon> [YYYY-MM-DD]`. Date defaults to
today. Works for past dates too (tested against yesterday) as well as
future forecast dates, since Open-Meteo's `start_date`/`end_date` params
cover both without needing a separate historical API.

## 4. Data flow

1. **Sunset time** — `daily=sunset` from the Open-Meteo forecast API gives
   the exact sunset moment for that coordinate/date directly; no need to
   reimplement sunrise/sunset astronomy.
2. **Solar azimuth** — Open-Meteo doesn't provide this, so it's computed
   locally with a standalone NOAA solar-position formula (~0.01deg
   accuracy) in `pinpoint.js`. Used only to pick the upwind sampling
   bearing.
3. **Upwind sample points** — 3 points at 50/150/250km along the solar
   azimuth bearing (great-circle destination-point formula), matching
   research.md §6's "sample upwind, not just overhead" guidance.
4. **Weather fetch** — main coordinate gets `cloud_cover_high`,
   `cloud_cover_mid`, `relative_humidity_2m`, `visibility`,
   `boundary_layer_height`; the 3 upwind points each get just
   `cloud_cover_low` (cheap, single-parameter calls). All at the sunset
   hour, rounded to the **nearest hourly bucket** (Open-Meteo is hourly-
   resolution; sunset is rarely exactly on the hour, and cloud forecasts
   aren't precise enough for sub-hour interpolation to be worth the
   complexity).
5. **Upwind aggregation** — `cloud_low_upwind` = the **worst (highest)**
   of the 3 upwind readings. See §6 for why, and its known failure mode.
6. **Air quality fetch** — main coordinate, `aerosol_optical_depth` and
   `pm2_5`, same sunset hour.
7. **`terrain_block_deg` is hardcoded to `0`.** Tier 2 isn't built yet;
   this is a known placeholder, printed explicitly in the trace output so
   it's never mistaken for a real measurement.
8. Assembled observation is passed straight into the unmodified
   `sunset_score.js` scoring formula.

## 5. Verification performed

- **Formula parity:** `sunset_score.js` run standalone reproduces
  `sunset_score.py`'s documented worked example exactly (90/100 for
  "Post-frontal classic", identical scores across all 9 `SCENARIOS`).
- **Live run 1** — Swartz Bay ferry terminal, BC (48.68294, -123.41933),
  yesterday's actual sunset (2026-09-03, 19:51 local). Returned 13/100
  (poor) — sky was genuinely clear (0% high/mid cloud), consistent in
  magnitude with the "Bluebird clear sky" scenario (25/100).
- **Live run 2** — Active Pass, BC (48.8667, -123.3167, approximate — no
  geocoder entry exists for a strait), same date/hour. Returned **0/100**,
  contradicted by an actual photo taken from the ferry at that sunset
  showing a vivid, well-defined orange/red horizon band under a broken
  mid-level cloud deck — clearly not a fully blocked sunset. See §6.

## 6. Known limitation: single-grid-cell false blocks

The Active Pass run's 50km upwind point reported 100% low cloud cover,
which collapses the `gate` term's `path` factor to ~0 via
`1 - (cloud_low/100)^1.5`, and the worst-of-3 rule let that one reading
override two much clearer readings (0% and 2% at 150km/250km) and zero out
the whole score. The real photo shows the sun clearly getting through at
low angle — the 100% reading was likely either a coarse grid cell
averaging over a partial/gapped deck, or the model placing a cloud patch
slightly off from its real position. This is precisely the "hyperlocal
effect" research.md §3 describes (a single stray cloud bank a model grid
cell can't resolve) — and precisely what Tier 3 (live satellite/webcam
confirmation) exists to catch. **Decision: kept worst-of-3 as designed
rather than softening it to a median/average**, since under-penalizing a
real blocking deck is worse than over-penalizing a false one, and one
counter-example isn't enough evidence to redesign the aggregation. This
limitation is expected to recur until Tier 3 exists, and is not a bug to
fix in Tier 1.

## 7. Open items / next steps

- Transition to Tier 2 (terrain occlusion): replace the `terrain_block_deg
  = 0` placeholder with a real horizon-profile calculation from elevation
  data (DEM), per research.md §5 Tier 2 and §7 group E.
- No automated test suite exists for either file; verification so far has
  been manual (worked-example parity + 2 live runs). Worth a lightweight
  test file if `pinpoint.js`'s geometry/aggregation logic grows more
  complex during Tier 2.
- Consider revisiting the worst-of-3 aggregation once more real-photo
  comparisons accumulate — right now there's exactly one counter-example,
  not a pattern.
