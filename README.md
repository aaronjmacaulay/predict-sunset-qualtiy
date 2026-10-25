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
[risk-poc.md](risk-poc.md).

---

## Status

| Piece | State |
|---|---|
| Physical scoring model | Written, runs, **uncalibrated** — constants are physically reasoned, not fitted |
| Live pinpoint tool (Tier 1) | Implemented & live-tested — `pinpoint.js` scores a real lat/lon/date via Open-Meteo |
| Terrain occlusion (Tier 2) | Implemented & integrated — `terrain.js` replaces the flat-horizon placeholder |
| Satellite cross-check (Tier 3, phase 1) | Workflow validated manually (interactive, no ML yet) — not automated into a script |
| Photo corpus | 42 camera photos + 16 licensed stock photos downloaded locally |
| Human ratings | 8 photos rated by 2 raters (Sandy, Aaron), 16 reviews; 16 stock photos still awaiting ratings |
| Label analysis | First pass done — see [analysis/report.md](analysis/report.md) |

**Headline finding so far:** in the 16 reviews collected, the strongest
correlates of score are *photo-specific* (foreground quality, focus), not
sky conditions. Restricting to labels a weather forecast could ever see
drops leave-one-out R² from 0.54 to 0.21. Small sample, but it points at a
real ceiling on forecast-only prediction. Details and caveats in
[analysis/report.md](analysis/report.md) and the full label taxonomy in
[docs/superpowers/specs/2026-08-18-sunset-rating-labels-design.md](docs/superpowers/specs/2026-08-18-sunset-rating-labels-design.md).

---

## The two halves, in more detail

### 1. Live forecasting tool — tiered approach

The design docs in [`docs/superpowers/specs`](docs/superpowers/specs) build
the tool up in tiers, each closing a specific accuracy gap in the one
before it:

1. **[Tier 1 — pinpoint scoring tool](docs/superpowers/specs/2026-09-04-pinpoint-scoring-tool-design.md)**
   — Ports the scoring formula to JavaScript (`src/sunset_score.js`) and
   wires it to live data via `src/pinpoint.js`: given a lat/lon and date,
   fetch the actual sunset time, compute solar azimuth, sample cloud cover
   upwind along that bearing, and produce a score. Known gap: a single bad
   upwind weather-grid cell can wrongly zero out the score — a "hyperlocal
   effect" that later tiers exist to catch.

2. **[Tier 2 — terrain occlusion](docs/superpowers/specs/2026-09-04-terrain-occlusion-tier2-design.md)**
   — Replaces Tier 1's flat-horizon assumption with a real horizon profile
   computed from elevation data (`src/terrain.js`), so mountains/ridges in
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
`user-input/stock-userratings.md` / `stock-aaronreview.md`.

This connects to the live tool in one specific place: the `photo_specific`
tier in the taxonomy is exactly the category `terrain.js`'s docs point to
as genuinely unresolvable from elevation/weather data by design (a specific
tree or building in frame) — not a gap later tiers are meant to close.

---

## Layout

```
research.md              Main design doc — physics, existing tools, every input
                         variable with its literal API parameter and source link
risk-poc.md              Risk ranking + the rating-consistency POC design
Sunset_Forecasting_Tool_Notes.docx   Word version of the research notes

docs/superpowers/specs/
  2026-08-18-sunset-rating-labels-design.md   Label taxonomy, tagging methodology, findings
  2026-09-04-pinpoint-scoring-tool-design.md  Tier 1 design doc
  2026-09-04-terrain-occlusion-tier2-design.md Tier 2 design doc
  2026-09-04-tier3-satellite-phase1-design.md Tier 3 phase 1 design doc

src/
  sunset_score.py        The original scoring model. Stdlib only, no deps.
  sunset_score.js        Direct JS port, verified to reproduce the Python worked
                         examples exactly. Pure functions, no I/O.
  sunset_score.test.js   Test file for the above.
  pinpoint.js            Live tool: lat/lon/date -> real score via Open-Meteo (Tier 1).
  terrain.js             Real horizon-profile occlusion from elevation data (Tier 2).

analysis/
  label_data.js          16 reviews hand-tagged into 11 signed labels (+1/-1/0)
  label_analysis.js      Correlation + ridge regression passes over that data
  report.md              Written-up findings from the above
  stock_manifest.json    Source URL, license, and sky-condition tag per stock photo
  sat_test/              Satellite JPEGs pulled/cropped while validating Tier 3 phase 1

user-input/
  photo-ratings.md       Sandy + Aaron ratings for 8 camera photos (filled in)
  stock-userratings.md   Blank rating template for the 16 stock photos
  stock-aaronreview.md   Blank review table for the same 16

photos/
  used/     (8)          The camera photos that have been rated
  unused/   (34)         Downloaded but not yet rated
  stock/    (16)         Wikimedia Commons photos + ATTRIBUTION.md

photosunset/             The original 41 Google Drive shortcuts (.url) these
                         photos came from. Superseded by photos/ — kept as
                         provenance.
design/                  UI mockups (Main.dc.html, sunset-scout-mockup.html) —
                         not wired to the scoring/live tools yet.
fixtures/                Empty.
```

---

## Running things

**The scoring model (Python original)** — prints a traced worked example,
then all 9 scenarios with a bar chart:

```bash
python src/sunset_score.py
```

**The live pinpoint tool (Tier 1+2, JS)** — scores a real coordinate/date:

```bash
node src/pinpoint.js <lat> <lon> [YYYY-MM-DD]
```

Date defaults to today (resolved in the location's own local timezone, not
UTC). Works for past and future dates via Open-Meteo's forecast API.

**The label analysis** — prints 3 correlation passes and 4 ridge
regressions:

```bash
node analysis/label_analysis.js
```

Verified working (Node v24). No dependencies, no `package.json` — plain
CommonJS.

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

The live tool (`pinpoint.js`) computes the same four terms from real
weather/AQ data instead of hand-written scenario constants, and Tier 2 adds
a fifth input — `terrain_block_deg`, a real horizon-occlusion angle instead
of the flat-horizon assumption — into the `gate` term.

Full derivation in [research.md](research.md) §8.

---

## Next steps

1. **Rate the 16 stock photos** — templates are sitting blank in
   `user-input/`. They were chosen to cover conditions the camera photos
   missed (marine layer, overcast, wildfire smoke, cirrus-heavy) so the
   label analysis stops being dominated by one kind of sky.
2. **Rate more of the 34 unused camera photos** — n=16 reviews is too
   small for any of the current numbers to be more than directional.
3. **Run the rating-consistency study properly** (risk-poc.md POC 1) — the
   per-rater split already hints Sandy and Aaron weight different things.
4. **Then, and only then**, calibrate `sunset_score.py`/`sunset_score.js`'s
   constants against real ratings instead of physical reasoning.
5. **Build the METAR/surface-observations sub-piece of Tier 3** —
   structured station data, no image interpretation needed, scoped in
   conversation but not yet built.
6. **Automate Tier 3's satellite workflow** (phase 2) — currently a manual
   crop-and-look process; an automated classifier is deliberately deferred
   future work, not started.
7. **Sort out notifications/alerting** — the original motivation for
   pushing into Tier 3 ("tell me when a great sunset is coming") is still
   unresolved; it needs the tool hosted somewhere a scheduled job can reach
   it, which hasn't been set up.
8. No automated test suite exists yet for `pinpoint.js`/`terrain.js` (only
   `sunset_score.test.js`) — verification so far has been manual (worked-
   example parity checks and live runs against real locations/photos).

---

## Housekeeping notes

- `photos/` is ~148 MB — wants a `.gitignore` or LFS rather than going
  straight into git.
- `analysis/report.md` and `label_data.js` both reference an
  `analysis/README.md` that doesn't exist.
- `analysis/report.md` documents 2 analysis passes; `label_analysis.js` now
  runs 4 ridge variants (it gained two `rater_id` passes). The report is
  slightly behind the code.
- `report.md` says "33 remaining downloaded, unrated photos"; the actual
  count in `photos/unused/` is 34.
- `photos/used/IMG_7206.jpg` has no matching `.url` shortcut in
  `photosunset/` — it came from somewhere other than the Drive folder.
- CC BY / CC BY-SA stock photos require attribution if ever published. Keep
  [photos/stock/ATTRIBUTION.md](photos/stock/ATTRIBUTION.md) with the
  images.
- Keep `sunset_score.py` and `sunset_score.js` in sync manually if the
  scoring formula changes — there's no automated cross-check between them.
