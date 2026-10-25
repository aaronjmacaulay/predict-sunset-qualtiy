# Architecture

How the codebase is structured: the parts, how they depend on each other, and
the contracts between them. Not the internal logic of each part (see the
design specs in `docs/superpowers/specs/` and `research/research.md` for that).

> **Status (Oct 2026):** this describes the **target** structure for the
> Python package. The code today is still JavaScript in a flatter shape; see
> [Current state](#current-state-vs-target). The Python migration
> (NEXT-STEPS C1) builds this structure.

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

Defined in `models.py` (proposed; dataclasses).

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

## Current state vs target

Until C1 lands:

| Today (JS) | Target (Python) |
|---|---|
| `src/sunset/sunset_score.js` + `.py` (duplicate) | `scoring.py` (from the `.py`) + `models.py` |
| `src/sunset/pinpoint.js` | split into `cli.py`, `pinpoint.py`, `geo.py`, `sources/openmeteo.py` |
| `src/sunset/terrain.js` | `terrain.py` (pure) + elevation fetch in `sources/openmeteo.py` |
| `tests/sunset_score.test.js` | `tests/test_scoring.py` |
| `study/analysis/*.js` | Python analysis reading `ratings.json` (NEXT-STEPS B2a) |

---

## Structural issues

Found in Claude's review of the JS code (Oct 2026). Tracked here; NEXT-STEPS
refers to them by ID. C1 resolves most of them by building the target
structure.

| ID | Issue | Resolved by | Status |
|---|---|---|---|
| S1 | `pinpoint.js` does everything: argument parsing, URL building, HTTP, solar geometry, upwind strategy, orchestration, printing. | Split per the diagram (C1) | open |
| S2 | `pinpoint.js` runs its CLI at module top level (no "run only when executed directly" guard), so importing it starts network calls. Main reason it has no tests. | `cli.py` separate from `pinpoint.py` (C1) | open |
| S3 | `terrain` fetches elevations inside the same function as the horizon geometry, so the maths can't be tested offline. | `terrain.py` takes elevations as input; fetch moves to `sources/` (C1) | open |
| S4 | Open-Meteo URLs hard-coded in several places; no single place for new data sources (Tier 3). | `sources/` layer (C1) | open |
| S5 | Contracts are implicit: the observation is a plain object, unvalidated. No `null` checks on API responses, so a missing value becomes NaN instead of an error (untested; plausible where air-quality coverage is patchy). | `models.Observation` with validation; fail loudly (C1). Fallback policy is NEXT-STEPS D3. | open |
| S6 | `score()` computes four terms and sub-factors but returns one integer; the terms only reach the screen via trace printing. | `ScoreResult` (C1); needed for F2 | open |
| S7 | Printing mixed into computation: trace output inside `score()`, `pinpoint` prints as it goes. | Formatting moves to `cli.py` (C1) | open |
| S8 | `destinationPoint()` duplicated in `pinpoint` and `terrain` (deliberately, to keep `terrain` standalone). | Shared `geo.py` (C1) | open |
| S9 | No shared vocabulary between the study's rating labels (`cloud_reflection`, `color_vibrancy`, …) and the scorer's terms (`canvas`, `clarity`, …). Personalisation needs a mapping. | Design work in F2 | open |
