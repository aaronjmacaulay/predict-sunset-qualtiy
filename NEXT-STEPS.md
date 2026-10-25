# Next Steps

Project planning file. Two sources feed it: the README's "Next steps" list
(research/product work) and a first review for AI-assisted development
(repo hygiene and structure). Each item has a **Done when** line so it can be
handed to a person or an agent as a bounded task.

Status key: `[ ]` not started · `[~]` in progress · `[x]` done

---

## Overview

Suggested order of work:

A1 → A2 → A3 → B1 (reorganise) → C1 (migrate, with B2a) → C2 (tests) → B2b →
D as needed → E → F1–F4 (in parallel with
the above, by the human raters) → G1–G3 → F5–F7 → G4–G5.

Sections:

- **A. Repo foundations** - version control, CLAUDE.md, scripts.
- **B. Restructure by role** - folder layout, structured ratings data.
- **C. Python migration, then tests** - port to Python with uv, pytest.
- **D. Design improvements** - modelling and efficiency changes suggested by
  Claude (structural issues live in ARCHITECTURE.md).
- **E. Housekeeping fixes** - small inconsistencies in docs and data.
- **F. Research / product** - rating study, calibration, Tier 3 work, and F2
  personalisation.
- **G. Deployment** - product shape, hosting, CI, alerting, UI (undefined).

---

## A. Repo foundations (do first — everything else gets safer)

- [x] **A1. Put the work under version control.** Committed and pushed to
  `origin` (the `aaronjmacaulay` GitHub repo). Decision: commit rated + stock
  photos; ignore unrated photos and satellite scratch imagery.
  Only the template `.gitignore` and README are committed; all source, docs
  and data are untracked. Ignore or LFS `analysis/sat_test/` (~46 MB) and
  `photos/unused/`; extend `.gitignore` for Node (`node_modules/`) and macOS
  (`.DS_Store`).
  *Done when:* source, docs, specs, ratings and stock photos are committed in
  small logical commits and `git status` is clean.

- [x] **A2. Add a short `CLAUDE.md`.**
  Terse, agent-facing: commands, the "multiplicative, not averaged" rule,
  keep `.py`/`.js` scorers in sync, constants are uncalibrated and must not be
  tuned without ratings data, no API keys by design.
  *Done when:* a fresh agent session can run tests and the live tool from
  `CLAUDE.md` alone.

- [x] **A3. Add `package.json` with scripts.**
  `npm test`, `npm run analyze`, `npm run score -- <lat> <lon> [date]`.
  Still zero dependencies.
  *Done when:* all three scripts run from the repo root.

## B. Restructure by role

Done before the Python migration (C) so the new code lands in its final
layout once instead of being written and then moved.

- [x] **B1. Reorganise folders.** Done; see README Layout, and
  ARCHITECTURE.md for the areas and layout decisions (no `build/`,
  `study/` as one folder, `app/` reserved, where personalisation lives).
  Directories had lost their write bit, probably from a Windows-to-Unix copy;
  restored with `chmod u+w`.

- [ ] **B2. Structured ratings data**, in two parts:
  - **B2a (done alongside C1):** replace hand-copied `label_data.js` with one
    `ratings.json`/CSV (photo, rater, score, labels, tags) that the Python
    analysis reads. Avoids writing a JS loader only to rewrite it.
  - **B2b (after C2):** generate `report.md` from the data.
  *Done when:* adding a rating means adding a row, then re-running the
  analysis with `uv run`.

## C. Python migration, then tests

Order: B1 (folders) first, then migrate to Python (C1), then pytest tests
(C2). The old Python/JS parity test is dropped: once the JS is gone there is
only one scorer.

- [ ] **C1. Migrate back to Python.**
  The JS port only existed because the original Windows machine had no
  working Python (Tier 1 spec §2); Python is the team's stronger language and
  suits a backend/scheduled-job and the analysis/ML work. Port `pinpoint.js`,
  `terrain.js` and `analysis/label_analysis.js` to Python (the analysis reads
  the new `ratings.json` data from B2a rather than porting `label_data.js`).
  Build the **target structure in ARCHITECTURE.md** (`models`, `scoring`,
  `geo`, `terrain`, `sources/`, `pinpoint`, `cli`); this resolves structural
  issues S1–S4 and S6–S8, and S5's fail-loudly part. `scoring.py` starts from
  `sunset_score.py` (keep its docstrings; drop the "frozen reference copy"
  note). Then delete the JS.
  **Tooling: uv.** Replace `package.json` with `pyproject.toml` + committed
  `uv.lock` (`.venv/` stays ignored). Commands become `uv run ...`
  (e.g. `uv run pytest`). Keep the core scorer and live tool stdlib-only
  (`urllib`/`requests` for API calls); numpy (or scikit-learn) only for the
  analysis code, pytest in a dev dependency group. uv 0.12.1 is already
  installed. Update CLAUDE.md, README and the specs that say "JS".
  Carry over the existing regression test (9 scenario scores) as the first
  pytest. Python 3.14 is installed; numpy and pytest are not (uv will manage
  them).
  **Faithful in behaviour, new in structure:** same scores for the same
  inputs (including worst-case upwind cloud); modelling changes go in D.
  Verify with the 9 scenario scores plus a live `pinpoint` run in JS and
  Python for the same place and date (run both at the same time, since
  forecasts update). Keep Python's rounding (`round(2.5)` = 2; JS gives 3).
  *Done when:* every command in CLAUDE.md runs in Python and no `.js` remains.

- [ ] **C2. Tests for `pinpoint` and `terrain`** (pytest), using recorded API
  responses in `fixtures/` (currently empty).
  *Done when:* `pytest` covers both modules offline.

- ~~C3. Python/JS parity test~~ **Dropped**: unnecessary after C1.

## D. Design improvements (suggested by Claude)

From Claude's review of the JS code (Oct 2026). **Structural issues** are
tracked in ARCHITECTURE.md (S1–S9); C1 resolves most of them by building the
target structure, and S9 belongs to F2. What remains here are modelling and
efficiency changes. None is needed before C1, which keeps behaviour
unchanged so it can be verified.

- [ ] **D1. Revisit worst-case upwind cloud.** Low cloud is the *max* of 3
  samples (50/150/250 km), so one cloudy grid cell sets the whole light-path
  term (the Tier 1 spec's known weakness). Averaging or distance-weighting is
  a modelling choice; decide it deliberately, ideally against ratings data.
- [ ] **D2. Interpolate to sunset time.** Weather is taken at the nearest
  hourly bucket (a 7:29 pm sunset uses 7:00 data). Interpolating between the
  two surrounding hours is more faithful.
- [ ] **D3. Fallbacks for missing API data.** After C1, missing values fail
  loudly (S5). Decide whether some should fall back instead (e.g. a default
  AOD where air-quality coverage is missing) and how the result says so.
- [ ] **D4. Batch the upwind weather requests.** The 3 upwind points are 3
  separate calls; Open-Meteo accepts multiple coordinates per request
  (`terrain` already does this for elevation; the forecast endpoint very
  likely does too, to verify).

## E. Housekeeping fixes

- [ ] Add `study/analysis/README.md` (referenced by `report.md` and
  `label_data.js` but missing), or remove the references.
- [ ] `report.md`: change "33 remaining unrated photos" to 34.
- [ ] `report.md`: document the 4 ridge passes (two `rater_id` passes were
  added to `label_analysis.js` after the report was written).
- [ ] Record where `study/photos/used/IMG_7206.jpg` came from (no `.url`
  shortcut).
- [ ] Keep `study/photos/stock/ATTRIBUTION.md` with the images (CC BY / BY-SA).
- [ ] Decide whether to delete `study/scratch/rq401.json` (leftover Wikimedia
  search response).

## F. Research / product (from the README)

1. [ ] **Rate the 16 stock photos** (`study/ratings/stock-*.md`).
2. [ ] **Rate more of the 34 unused camera photos** (n=16 reviews is only
   directional).
3. [ ] **Run the rating-consistency study** (`research/risk-poc.md` POC 1).
4. [ ] **Calibrate** scoring constants against real ratings — only after 1–3.
5. [ ] **METAR / surface-observation sub-piece of Tier 3** (structured data,
   no image interpretation).
6. [ ] **Automate Tier 3 satellite workflow** (phase 2); classifier is
   deliberately deferred.
7. [ ] **Notifications / alerting** — blocked on G (deployment).
8. [ ] **Tests for `pinpoint`/`terrain`** — covered by C2.

## F2. Personalisation (the question the rating study exists to answer)

The study asks: do people share one idea of a "good sunset", or do they
differ enough that each user needs a preference profile (stated or inferred)?
Current evidence (n=8 per rater, Sandy and Aaron): their top correlates differ
(Sandy: focus/foreground; Aaron: water reflection/gradient), so it is
suggestive but not proven. The answer changes the product's output shape:

- **If people agree:** one score per spot, calibrated against pooled ratings.
- **If people differ:** the forecaster outputs *features* (cloud
  reflection, colour, water reflection, sun timing, ...) and a per-user
  profile turns them into a personal score.

- [ ] **F2.1.** Run POC 1 with more raters (risk-poc.md targets 20–30; the
  Google Form route is enough). Decision rule is already written there
  (mean pairwise correlation ≳ 0.6 and no clusters ⇒ single score).
- [ ] **F2.2.** Make `sunset_score` able to emit the decomposed features
  alongside the single score, so either outcome is supported without a
  rewrite (ScoreResult, built in C1; ARCHITECTURE.md S6).
- [ ] **F2.3.** If taste differs, choose how profiles are obtained:
  (a) user picks/weights archetypes, (b) user rates ~10 calibration photos
  on first use, (c) inferred from feedback ("was tonight good?").
  Recommendation: (b), since the rating tooling already exists.
- [ ] **F2.4.** Add the "photo-specific" ceiling to the product framing: a
  forecast can only explain the sky/geometry part of a rating (LOO R² 0.19 vs
  0.55 with photo labels in the first pass). Personalised *spot* knowledge
  (foreground, obstructions) may need to be a per-user/per-spot input
  rather than something forecast.
- [ ] **F2.5.** Define the mapping between rating labels and score features
  (ARCHITECTURE.md S9).

## G. Deployment (undefined — needs a decision before F7)

Nothing is deployed and nothing is specified. Summary:

- **Today:** a local CLI (`npm run score -- <lat> <lon>`). No server, no
  hosting config, no build step, no CI (`.github/` absent, no Dockerfile).
- **UI:** `design/` holds two Claude-Design mockups ("Sunset Scout": a
  "Tonight" view with a per-spot score). They are static and not wired to any
  code. Note: the mockup is a published-artifact design canvas, not a
  production front end.
- **Alerting:** the Tier 3 spec says scheduled cloud routines can't reach this
  project without a git repo + hosting, and that path was explicitly deferred.
- **Rating study:** `risk-poc.md` says a Google Form / Typeform is enough; no
  app is planned for collecting ratings.

Decisions needed:

- [ ] **G1. Decide the product shape.** Options: (a) personal CLI + scheduled
  alert to self; (b) small web app showing tonight's score for saved spots;
  (c) mobile/PWA. Recommendation: start with (a), then (b).
- [ ] **G2. Choose hosting.** The code is pure functions plus HTTP calls to
  free, keyless APIs (Open-Meteo, elevation), so a static site plus a
  serverless function or a scheduled GitHub Action fits. Pick one.
- [ ] **G3. Define the build/CI pipeline.** Minimum: GitHub Action running
  the tests (`uv run pytest` after C1) on push. Then a deploy job for
  whatever G2 picks.
- [ ] **G4. Alerting path.** Scheduled job → compute score for saved spots
  ~2–3 h before sunset → push/email if above threshold.
- [ ] **G5. Wire the UI** (`design/`) to the predictor's output, or rebuild the
  mockup as real front-end code.
