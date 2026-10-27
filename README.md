# Hyperlocal Sunset Forecasting Tool

Can you forecast how good tonight's sunset will be at a specific spot — and is
"good" even the same thing for everyone?

The project has two halves that are deliberately being worked in parallel:

1. **A physical scoring model** — turn weather-model variables (cloud by
   altitude, humidity, aerosol, terrain) into a 0–100 sunset score, live for
   a real coordinate and date.
2. **A ground-truth study** — find out what people actually respond to in a
   sunset, and whether they agree with each other, before calibrating
   anything against the model.

Half 2 exists because half 1 quietly assumes a single universal "good
sunset". If that assumption is wrong, the target variable changes shape and
the scoring architecture has to change with it. See
[risk-poc.md](research/risk-poc.md).

---

## Status

| Piece | State |
|---|---|
| Physical scoring model | Written, runs, **uncalibrated** — constants are physically reasoned, not fitted |
| Live pinpoint tool (Tier 1) | Implemented & live-tested — `sunset score <lat> <lon>` scores a real place/date via Open-Meteo |
| Terrain occlusion (Tier 2) | Implemented & integrated — real horizon profile replaces the flat-horizon placeholder |
| Code | Python package (`src/sunset/`), managed with uv; 46 offline tests |
| Satellite cross-check (Tier 3, phase 1) | Workflow validated manually (interactive, no ML yet) — not automated into a script |
| Photo corpus | 42 camera photos + 16 licensed stock photos downloaded locally |
| Human ratings | 8 photos rated by 2 raters (Sandy, Aaron), 16 reviews; 16 stock photos still awaiting ratings |
| Label analysis | First pass done — see [study/analysis/report.md](study/analysis/report.md) |

**Headline finding so far:** in the 16 reviews collected, the strongest
correlates of score are *photo-specific* (foreground quality, focus), not
sky conditions. Restricting to labels a weather forecast could ever see
drops leave-one-out R² from 0.54 to 0.21. Small sample, but it points at a
real ceiling on forecast-only prediction. Details and caveats in
[study/analysis/report.md](study/analysis/report.md) and the full label taxonomy in
[docs/superpowers/specs/2026-08-18-sunset-rating-labels-design.md](docs/superpowers/specs/2026-08-18-sunset-rating-labels-design.md).

---

## The two halves, in more detail

### 1. Live forecasting tool — tiered approach

The design docs in [`docs/superpowers/specs`](docs/superpowers/specs) build
the tool up in tiers, each closing a specific accuracy gap in the one
before it:

1. **[Tier 1 — pinpoint scoring tool](docs/superpowers/specs/2026-09-04-pinpoint-scoring-tool-design.md)**
   — Wires the scoring formula (`src/sunset/scoring.py`) to live data
   (`src/sunset/pinpoint.py`): given a lat/lon and date,
   fetch the actual sunset time, compute solar azimuth, sample cloud cover
   upwind along that bearing, and produce a score. Known gap: a single bad
   upwind weather-grid cell can wrongly zero out the score — a "hyperlocal
   effect" that later tiers exist to catch.

2. **[Tier 2 — terrain occlusion](docs/superpowers/specs/2026-09-04-terrain-occlusion-tier2-design.md)**
   — Replaces Tier 1's flat-horizon assumption with a real horizon profile
   computed from elevation data (`src/sunset/terrain.py`), so mountains/ridges in
   the sunset direction correctly reduce the score. Pure geometry, no
   weather data. Known gaps: no buildings/trees, and DEM resolution (~90m)
   misses small local features.

3. **[Tier 3, phase 1 — satellite imagery](docs/superpowers/specs/2026-09-04-tier3-satellite-phase1-design.md)**
   — A human/Claude-in-the-loop cross-check against real satellite imagery
   from shortly before sunset, to catch exactly the hyperlocal misses Tiers
   1-2 can't see. Deliberately interactive rather than ML-based for this
   first pass; true automated cloud-type classification is flagged as an
   open problem with no good free data source yet.

Each tier is designed to be independently testable and to slot cleanly
into the next — Tier 2 replaced a single placeholder value in Tier 1's
output; Tier 3 is a cross-check layered on top of both, not a replacement.

### 2. Photo rating study — ground truth / calibration

Goal: figure out which real, physical qualities of a sunset drive how much
people like it, separate from qualities of the *photo* that happen to have
captured it. Full taxonomy, methodology, and findings are in
[docs/superpowers/specs/2026-08-18-sunset-rating-labels-design.md](docs/superpowers/specs/2026-08-18-sunset-rating-labels-design.md).
In brief:

- Collect a set of sunset photographs.
- Have 2-4 people each rate every photo 0-10, plus a free-text list of
  likes/dislikes.
- Turn the likes/dislikes into a structured set of labels (11 so far — see
  the taxonomy doc), each tagged by whether it could ever be predicted from
  a forecast (`sky_weather`, `geometry`) or is tied to that specific photo
  (`photo_specific`, e.g. focus, foreground clutter, over-processing).
- Test whether those labels predict the human rating, via correlation and
  ridge regression.
- Compare the full-label model against a forecast-only (transferable-label)
  model to see how much of a rating a forecast could ever explain.

Status: n=16 reviews (8 camera photos × Sandy + Aaron). The 16 stock photos
chosen to cover conditions the first batch missed (marine layer, overcast,
wildfire smoke, cirrus-heavy) are downloaded but still awaiting ratings in
`study/ratings/stock-userratings.md` / `stock-aaronreview.md`.

This connects to the live tool in one specific place: the `photo_specific`
tier in the taxonomy is exactly the category the Tier 2 terrain spec points to
as genuinely unresolvable from elevation/weather data by design (a specific
tree or building in frame) — not a gap later tiers are meant to close.

---

## Layout

```
src/sunset/        The predictor (Python package). Module structure and
                   dependency rules: ARCHITECTURE.md
tests/             pytest tests; fixtures/ holds recorded API responses
study/             The rating study: ratings/ (incl. ratings.json),
                   analysis/, photos/, scratch/
research/          Background research and the risk/POC write-up
docs/superpowers/  Design specs
design/            UI mockups (not wired to the code yet)
```

---

## Running things

Quick reference (details for each below):

```bash
uv sync                                        # one-time setup
uv run pytest                                  # run the tests (offline)
uv run sunset score <lat> <lon> [YYYY-MM-DD]   # live sunset score, needs internet
uv run sunset scenarios                        # the 9 example skies, no internet
uv run python study/analysis/label_analysis.py # the rating-study analysis
uv run sunset terrain <lat> <lon> <azimuth>    # horizon scan only (debugging)
```

### uv: the project's Python manager

[uv](https://docs.astral.sh/uv/) installs the right Python and the
project's libraries into a private folder (`.venv/`, not committed), so the
project never depends on what happens to be installed on your machine.

Install it once per computer: `brew install uv` on a Mac, or see the uv
website for other systems.

- **`uv sync`** reads `pyproject.toml` (what the project needs) and
  `uv.lock` (the exact versions) and creates or updates `.venv/`. Run it
  after cloning, and again after pulling changes that touch either file.
- **`uv run <command>`** runs a command inside that environment. You never
  need to "activate" anything; just put `uv run` in front.
- **Adding a library:** `uv add --group analysis pandas` (for the rating
  study) or `uv add --group dev <name>` (for tools). Commit the changed
  `pyproject.toml` and `uv.lock` together. Keep the predictor in
  `src/sunset/` free of third-party libraries (see ARCHITECTURE.md).

### Tests: `uv run pytest`

[pytest](https://docs.pytest.org/) finds every `tests/test_*.py` file and
runs each function whose name starts with `test_`. A test is a small
program that checks one thing, such as "the Post-frontal classic scenario
still scores 90". The tests run offline in under a second, so run them after
every change. All passing means you didn't break anything they check:

```
..............................................                [100%]
46 passed in 0.05s
```

Each dot is a passing test. A failure prints `F` and then shows the test,
the line that failed, and the expected vs actual values. Useful variations:

```bash
uv run pytest -v                      # one line per test, with names
uv run pytest tests/test_scoring.py   # one file only
uv run pytest -k terrain              # only tests with "terrain" in the name
uv run pytest -x                      # stop at the first failure
```

The tests don't use the internet. `tests/fixtures/` holds real Open-Meteo
responses recorded on 2026-10-26, and the tests replay them. Some tests
compare the whole output with a saved copy, so if you *deliberately* change
the scoring or the output format, those tests will fail. That's expected:
update the saved copy in `tests/fixtures/` and say why in the commit
message (see `tests/fixtures/README.md`).

### Live score: `uv run sunset score <lat> <lon> [YYYY-MM-DD]`

The actual forecaster. For a place and date it fetches the sunset time,
works out the compass direction the sun sets in, checks low cloud 50, 150
and 250 km in that direction, gets cloud, humidity, visibility and air
quality at your spot, scans the terrain toward the sunset, and prints every
input and the score. The date defaults to today *at that location*. It
works for past and future dates the forecast covers.

```bash
uv run sunset score 49.2827 -123.1207              # Vancouver, today
uv run sunset score 49.7016 -123.1558 2026-10-26   # Squamish, a given date
```

Shortened output:

```
Sunset time: 2026-10-26T18:00 (America/Vancouver)
Solar azimuth at sunset: 251.1 deg
Upwind low cloud samples:
  50km @ 251deg -> (49.135, -123.771): 47%
  ...
terrain_block_deg (max across bearings): 0.46

  TERM 1  light path gate           = 0.639
  ...
  0.639 x 0.248 x 0.311 x 1.130 = 0.0556
  SCORE = 6/100   (poor)
```

Needs the internet. Open-Meteo is free but rate-limits bursts: if you get
`HTTP 429`, wait a minute.

### Example skies: `uv run sunset scenarios`

No internet needed. Scores 9 hand-made example skies ("Post-frontal
classic", "Marine layer", "Wildfire smoke", ...) and works through the first
one term by term. The quickest way to see how the formula behaves. "Pair A"
and "Pair B" have identical skies overhead but differ in cloud 120 km to the
west (72 vs 26), which is why the tool samples upwind. The scenarios live in
`src/sunset/scoring.py`.

### Rating study: `uv run python study/analysis/label_analysis.py`

Not the forecaster: this analyses the human ratings. It reads
`study/ratings/ratings.json` (each review's score plus its likes and dislikes
tagged as labels) and prints which labels track the scores, overall and per
rater, and how well the ratings can be predicted with and without
photo-specific labels. `study/analysis/report.md` is the write-up of this
output. After adding ratings to `ratings.json`, rerun it.

### Horizon only: `uv run sunset terrain <lat> <lon> <azimuth>`

For debugging the terrain part on its own: how many degrees hills or
mountains block the view toward a compass bearing (`<azimuth>`, e.g. 251 for
a west-south-west autumn sunset in Vancouver). Prints the elevation and angle
of each sampled point. Needs the internet.

---

## The scoring model in one paragraph

`score = light_path_gate × canvas × clarity × aerosol`, times 100.

Multiplicative, **not** a weighted average — that's the central modelling
decision. A sunset is a chain of necessary conditions, and any one broken
link ruins it; averaging would let a gorgeous cirrus deck paper over a
solid marine layer that is physically blocking the sun. Two other choices
worth knowing: low cloud is sampled **upwind** along the solar azimuth
(50–250 km) rather than overhead, because the light has to travel through
it to get here; and the aerosol term is the only one allowed to exceed 1.0,
because moderate particulate genuinely improves a sunset. The `Pair A` /
`Pair B` scenarios exist to demonstrate the upwind point: identical sky
overhead, 72 vs 26.

The live tool (`pinpoint.py`) computes the same four terms from real
weather/AQ data instead of hand-written scenario constants, and Tier 2 adds
a fifth input — `terrain_block_deg`, a real horizon-occlusion angle instead
of the flat-horizon assumption — into the `gate` term.

Full derivation in [research.md](research/research.md) §8.

---

## Next steps

See [NEXT-STEPS.md](NEXT-STEPS.md) for the plan, including research,
housekeeping and deployment items.

---

## Licensing

Code and docs are the project's own. The stock photos in `study/photos/stock/` are
third-party (CC BY, CC BY-SA, public domain) and keep their own licenses; see
[study/photos/stock/ATTRIBUTION.md](study/photos/stock/ATTRIBUTION.md). Redistribute them
unmodified and with that file.
