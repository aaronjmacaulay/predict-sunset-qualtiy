# Architecture

How the codebase is structured: the parts, how they depend on each other, and
the contracts between them. Not the internal logic of each part (see the
design specs in `docs/superpowers/specs/` and `research/research.md` for that).

> **Status (2026-10-26):** implemented. The Python package in `src/sunset/`
> follows this structure; it replaced an earlier JavaScript version (see
> [Migration from JavaScript](#migration-from-javascript)).

---

## Diagram

Dependencies point **down only**.

```
                    ┌───────────────────────────────┐
  people / jobs ──▶ │  cli.py   (later: app/, alert │   parse args, format output
                    │           job, web API)       │
                    └───────────────┬───────────────┘
                                    │ place, date
                                    ▼
                    ┌───────────────────────────────┐
                    │  pinpoint.py                  │   orchestration:
                    │  place/date → Observation     │   sunset time → azimuth →
                    │            → ScoreResult      │   upwind points → fetch → score
                    └──┬────────┬─────────┬────────┬┘
                       │        │         │        │
          ┌────────────┘        │         │        └──────────────┐
          ▼                     ▼         ▼                       ▼
  ┌──────────────┐   ┌────────────────┐ ┌──────────────┐ ┌──────────────────────┐
  │  geo.py      │   │  terrain.py    │ │  scoring.py  │ │  sources/            │
  │  sun azimuth │◀──│  elevations →  │ │  Observation │ │   openmeteo.py       │──▶ Open-Meteo
  │  dest. point │   │  horizon angle │ │  → Score-    │ │   weather, air       │    (HTTP, no key)
  └──────────────┘   └────────────────┘ │    Result    │ │   quality, elevation,│
                                        └──────────────┘ │   sunset             │
          pure computation: no I/O, no printing          │  later: satellite,   │
                                                         │  METAR               │
                                                         └──────────────────────┘
                                                            the only I/O layer
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  models.py   Observation, ScoreResult   (used by every layer above)     │
  └─────────────────────────────────────────────────────────────────────────┘

  ─────────────────────────────── separate world ───────────────────────────────

  study/   ratings.json → analysis (correlation, ridge) → report.md
           no imports from src/; F2 personalisation will need a mapping
           between rating labels and ScoreResult features (see S9)
```

---

## The three areas

| Area | Where | What it is |
|---|---|---|
| **Predictor** | `src/sunset/` | Place + date → sunset score and features. A library with a thin CLI on top. |
| **Rating study** | `study/` | Human ratings of sunset photos and the analysis of what drives them. Ground truth for calibrating and personalising the predictor. |
| **App** (future) | `app/` (not created) | Whatever users touch: web app, alerts, mobile. Shape undecided (NEXT-STEPS G1). Mockups in `design/`. |

The predictor and study share no code. They connect through data: the study
produces ratings and (later) calibration constants or user profiles that the
predictor consumes.

---

## Layers and dependency rules

| Layer | Modules | May import | Must not |
|---|---|---|---|
| Interface | `cli.py` (later `app/`) | `pinpoint`, `models` | contain scoring or fetching logic |
| Orchestration | `pinpoint.py` | everything below | print or parse arguments |
| Pure computation | `scoring.py`, `terrain.py`, `geo.py` | `models`, `geo` | do I/O, print, or import `sources` |
| I/O | `sources/*.py` | `models` | contain scoring or geometry logic |
| Contracts | `models.py` | nothing | depend on anything in the package |

Consequences:

- Pure modules are tested with plain inputs, no fixtures, no network.
- `sources/` is tested against recorded API responses in `tests/fixtures/`.
- `pinpoint` is tested by giving it a fake source.
- A new interface (app, alert job) reuses `pinpoint` unchanged.

---

## Data contracts

Defined in `models.py` (frozen dataclasses).

**Observation**: everything the scorer needs, at sunset, for one place.

| Field | Unit | Source |
|---|---|---|
| `cloud_high`, `cloud_mid` | % | weather at the spot |
| `cloud_low_upwind` | % | weather at 50/150/250 km toward the sun (currently the max) |
| `rh_2m` | % | weather at the spot |
| `visibility_m` | m | weather at the spot |
| `pbl_height_m` | m | weather at the spot (boundary layer height) |
| `aod` | unitless | air quality (aerosol optical depth) |
| `pm25` | µg/m³ | air quality |
| `terrain_block_deg` | degrees | `terrain` horizon scan |

All fields required; a missing value is an error, not NaN (see S5).

**ScoreResult**: the scorer's output.

- `score` (0–100) and `label` ("poor" … "exceptional")
- the four terms: `gate`, `canvas`, `clarity`, `aerosol`
- their sub-factors (e.g. `path`, `terrain`, `high`, `mid`, `rh_f`, …)

The terms and sub-factors are the **features** a personalised score would
weight (NEXT-STEPS F2). `pinpoint` returns the Observation and ScoreResult
together with context (sunset time, azimuth, upwind samples, horizon profile)
so an interface can explain the score.

---

## External services

| Service | Used for | Key? |
|---|---|---|
| Open-Meteo Forecast API | sunset time, cloud, humidity, visibility, boundary layer | no |
| Open-Meteo Air Quality API | AOD, PM2.5 | no |
| Open-Meteo Elevation API | terrain profile (Copernicus DEM, ~90 m) | no |

No API keys, by design. Tier 3 adds satellite imagery (manual today) and
possibly METAR station data; both belong in `sources/`.

---

## Where new things go

- **A new data source** (satellite, METAR, another weather model): a module
  in `sources/`, returning plain values or `models` types. Wire it in
  `pinpoint`.
- **A new score term or input**: a field on `Observation`, a function in
  `scoring.py`, a sub-factor on `ScoreResult`. Add a scenario and update the
  regression test.
- **A new interface** (alert job, web API, app): calls `pinpoint`; lives in
  `cli.py` or `app/`, never inside the predictor's lower layers.
- **Personalisation**: the function that turns ScoreResult features + a user
  profile into a personal score is pure and belongs in `src/sunset/`.
  Storing profiles and showing results belong in `app/`.
- **Rating-study analysis**: `study/analysis/`. Not imported by the predictor.

---

## Decisions

- **Python, managed with uv.** `pyproject.toml` + `uv.lock`. The JS port
  existed only because the original Windows machine lacked Python.
- **Stdlib-only predictor.** `src/sunset/` keeps zero third-party
  dependencies (HTTP via `urllib`, or `requests` if needed) so it deploys
  anywhere. numpy / scikit-learn only in `study/`.
- **No `build/` directory.** Python needs no build step. A web app's tooling
  will create its own output folder later (gitignored). CI lives in
  `.github/`.
- **`study/` is one folder.** Photos, ratings, analysis and report together,
  instead of split across `data/`, `analysis/`, `user-input/`.
- **`app/` is reserved,** created only after the product shape (G1) and
  hosting (G2) are decided.
- **Specs stay in `docs/superpowers/`,** where the superpowers workflow
  expects them.

---

## Migration from JavaScript

Done 2026-10-26 (NEXT-STEPS C1). Verified by identical output: the 9
scenario scores, the rating analysis, and live `pinpoint` runs for two places
(recorded as `tests/fixtures/`).

| Was (JS) | Now (Python) |
|---|---|
| `sunset_score.js` + `sunset_score.py` (duplicate) | `scoring.py` (from the `.py`) + `models.py` |
| `pinpoint.js` | `cli.py`, `pinpoint.py`, `geo.py`, `sources/openmeteo.py` |
| `terrain.js` | `terrain.py` (pure) + elevation fetch in `sources/openmeteo.py` |
| `sunset_score.test.js` | `tests/test_*.py` (46 tests, offline) |
| `study/analysis/label_analysis.js` + `label_data.js` | `label_analysis.py` + `study/ratings/ratings.json` |

---

## Structural issues

Found in Claude's review of the JS code (Oct 2026). Tracked here; NEXT-STEPS
refers to them by ID. The Python migration (C1) resolved S1–S8 and S10.

| ID | Issue | Resolved by | Status |
|---|---|---|---|
| S1 | `pinpoint.js` does everything: argument parsing, URL building, HTTP, solar geometry, upwind strategy, orchestration, printing. | Split per the diagram (C1) | resolved |
| S2 | `pinpoint.js` runs its CLI at module top level (no "run only when executed directly" guard), so importing it starts network calls. Main reason it has no tests. | `cli.py` separate from `pinpoint.py` (C1) | resolved |
| S3 | `terrain` fetches elevations inside the same function as the horizon geometry, so the maths can't be tested offline. | `terrain.py` takes elevations as input; fetch moves to `sources/` (C1) | resolved |
| S4 | Open-Meteo URLs hard-coded in several places; no single place for new data sources (Tier 3). | `sources/` layer (C1) | resolved |
| S5 | Contracts are implicit: the observation is a plain object, unvalidated. No `null` checks on API responses, so a missing value becomes NaN instead of an error (untested; plausible where air-quality coverage is patchy). | `models.Observation` with validation; fail loudly (C1). Fallback policy is NEXT-STEPS D3. | resolved (fails loudly); fallbacks open in D3 |
| S6 | `score()` computes four terms and sub-factors but returns one integer; the terms only reach the screen via trace printing. | `ScoreResult` (C1); needed for F2 | resolved |
| S7 | Printing mixed into computation: trace output inside `score()`, `pinpoint` prints as it goes. | Formatting moves to `cli.py` (C1) | resolved |
| S8 | `destinationPoint()` duplicated in `pinpoint` and `terrain` (deliberately, to keep `terrain` standalone). | Shared `geo.py` (C1) | resolved |
| S9 | No shared vocabulary between the study's rating labels (`cloud_reflection`, `color_vibrancy`, …) and the scorer's terms (`canvas`, `clarity`, …). Personalisation needs a mapping. | Design work in F2 | open |
| S10 | Timezone bug: `pinpoint.js` parsed Open-Meteo's local sunset time (no offset) in the *machine's* timezone, so the solar azimuth was only right when the machine shared the location's timezone. On a UTC machine (typical for servers) Vancouver's sunset bearing came out 149° instead of 251°, sampling clouds in the wrong direction. | Python converts with the location's timezone; `geo.solar_azimuth` rejects naive times (C1) | resolved |
