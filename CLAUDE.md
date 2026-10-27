# Hyperlocal sunset forecasting tool

Forecasts how good a sunset will be at a specific lat/lon/date, and studies
whether "good" is the same for everyone or needs per-user preferences.
See README.md for the full picture, ARCHITECTURE.md for structure and
dependency rules, and NEXT-STEPS.md for the plan.

## Commands

Python package managed with uv. `uv sync` once; then:

```bash
uv run pytest                                  # all tests, offline (recorded API fixtures)
uv run sunset score <lat> <lon> [YYYY-MM-DD]   # live score (Tier 1+2), needs network
uv run sunset scenarios                        # traced worked example + 9 scenarios
uv run sunset terrain <lat> <lon> <azimuth>    # horizon scan on its own, needs network
uv run python study/analysis/label_analysis.py # correlation + ridge over rating labels
```

Open-Meteo rate-limits bursts (HTTP 429). Prefer tests over repeated live runs.
Record a new fixture: `uv run python tests/record_fixture.py <name> <lat> <lon> <date>`.

## Rules that matter

- **Score is multiplicative, not a weighted average:**
  `gate × canvas × clarity × aerosol`. A sunset is a chain of necessary
  conditions. Do not "simplify" it into a sum.
- **Cloud is sampled upwind** along the solar azimuth (50–250 km), not overhead.
- **Constants are uncalibrated.** They are physically reasoned, not fitted.
  Do not tune them until there is enough human rating data (see NEXT-STEPS F).
  If you change scoring, update the regression tests and `tests/fixtures/expected_*`
  in the same commit and say why.
- **Respect the layers** (ARCHITECTURE.md): only `sources/` does I/O; only
  `cli.py` prints; `scoring`, `terrain`, `geo` stay pure.
- **The predictor stays stdlib-only.** numpy etc. only in `study/`.
- **No API keys, by design.** Open-Meteo and elevation data are keyless; keep
  it that way.
- **Times:** resolve "today" and the sunset instant in the location's own
  timezone, never the machine's (see ARCHITECTURE.md S10).
- **Missing data fails loudly** (`MissingDataError`), never NaN.

## Data and the rating study

- Labels per review live in `study/ratings/ratings.json` (one review per
  line); the free-text ratings they were tagged from are the markdown files
  next to it. n=16 reviews so far (2 raters), so results are directional
  only. Don't present them as conclusions.
- Label tiers: `sky_weather` and `geometry` are forecastable;
  `photo_specific` (focus, foreground) is not and must not be fed to a forecaster.
- `study/photos/` is ~148 MB and `study/scratch/sat_test/` ~46 MB. Don't read or glob
  these directories wholesale.
- Stock photos are CC BY / BY-SA: keep `study/photos/stock/ATTRIBUTION.md` with them.

## Layout

- `src/sunset/` - the predictor package (see ARCHITECTURE.md for modules)
- `tests/` - pytest; `fixtures/` has recorded API responses and expected outputs
- `study/` - the rating study: `ratings/`, `analysis/`, `photos/`, `scratch/`
- `research/` - background docs; `docs/superpowers/` - specs (leave there)
- `design/` - UI mockups; `app/` is reserved for later (not created yet)

## Status and gaps

- No CI, no deployment.
- `design/` mockups are not wired to any code.
