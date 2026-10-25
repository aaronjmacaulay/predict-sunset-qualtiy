# Hyperlocal sunset forecasting tool

Forecasts how good a sunset will be at a specific lat/lon/date, and studies
whether "good" is the same for everyone or needs per-user preferences.
See README.md for the full picture and NEXT-STEPS.md for the plan.

## Commands

`package.json` has scripts only (`npm test`, `npm run analyze`, `npm run score -- <lat> <lon>`); no dependencies, plain CommonJS on Node (v24 verified).

```bash
node --test src/sunset_score.test.js   # scorer tests (the only test file; passes, 2 tests)
node src/pinpoint.js <lat> <lon> [YYYY-MM-DD]   # live score (Tier 1+2), needs network
node src/terrain.js ...                # horizon occlusion on its own
node analysis/label_analysis.js        # correlation + ridge passes over rating labels
python src/sunset_score.py             # original scorer, worked examples, stdlib only
```

## Rules that matter

- **Score is multiplicative, not a weighted average:**
  `gate × canvas × clarity × aerosol`. A sunset is a chain of necessary
  conditions. Do not "simplify" it into a sum.
- **Cloud is sampled upwind** along the solar azimuth (50–250 km), not overhead.
- **Constants are uncalibrated.** They are physically reasoned, not fitted.
  Do not tune them until there is enough human rating data (see NEXT-STEPS E).
- **`src/sunset_score.py` and `src/sunset_score.js` must stay in sync by hand.**
  There is no automated parity check yet. Change both or neither.
- **No API keys, by design.** Open-Meteo and elevation data are keyless; keep
  it that way.
- Resolve "today" in the observer's local timezone, not UTC (see `pinpoint.js`).

## Data and the rating study

- Ratings live in markdown (`user-input/`); labels are hand-copied into
  `analysis/label_data.js`. n=16 reviews so far (2 raters), so results are
  directional only. Don't present them as conclusions.
- Label tiers: `sky_weather` and `geometry` are forecastable;
  `photo_specific` (focus, foreground) is not and must not be fed to a forecaster.
- `photos/` is ~148 MB and `analysis/sat_test/` ~46 MB. Don't read or glob
  these directories wholesale.
- Stock photos are CC BY / BY-SA: keep `photos/stock/ATTRIBUTION.md` with them.

## Status and gaps

- No git history beyond the initial commit (most files untracked), no CI,
  no deployment, no tests for `pinpoint.js`/`terrain.js`.
- `design/` mockups are not wired to any code.
- A repo reorganisation is planned (NEXT-STEPS C1). Update the paths in this
  file when it happens.
