# Tier 2: terrain occlusion

Status: implemented and live-tested, integrated into `pinpoint.js`. This is
the "Tier 2 — add terrain occlusion" from research.md §5, replacing the
`terrain_block_deg = 0` placeholder from Tier 1
(`docs/superpowers/specs/2026-09-04-pinpoint-scoring-tool-design.md`).

## 1. Purpose

Compute how many degrees above the true (flat) horizon an observer's actual
visible horizon sits, in the direction of sunset — the real western
horizon profile, not the sea-level assumption Tier 1 used. This is pure
geometry (research.md §7 group E): no weather data needed, just elevation
data and the observer's position.

## 2. Data source

Open-Meteo's free, keyless batch **Elevation API**
(`api.open-meteo.com/v1/elevation`, Copernicus DEM, ~90m resolution).
Confirmed it accepts 50+ comma-separated lat/lon pairs in one request.
Chosen over OpenTopography (requires an API key) and USGS EarthExplorer
(manual download, no live API) specifically to keep this tool consistent
with Tier 1's "no API key" approach.

## 3. Architecture

**New file: `src/terrain.js`**, no dependency on `pinpoint.js` (the
great-circle destination-point formula is duplicated rather than imported,
so `terrain.js` stays independently testable — see `sunset_score.js`'s
precedent of isolation from I/O). Exports `getTerrainBlockDeg(lat, lon,
sunsetAzimuthDeg)`.

`pinpoint.js` calls it alongside the existing weather/AQ fetches
(`Promise.all`), and its result replaces the old hardcoded `0` in the
`terrain_block_deg` field passed to `sunset_score.js`.

## 4. Geometry

- **Bearing sweep:** 5 bearings at sunset azimuth ± 15°, ± 7.5°, and
  center — covers the sun's azimuth swing during the ~30-60min color
  window (research.md's "sample along the bearing" applied to terrain,
  not just cloud).
- **Distance grid per bearing:** `1, 2, 3, 5, 8, 13, 21, 34, 55, 90` km —
  roughly geometric spacing for finer resolution close-in (where angular
  sensitivity to a given height is highest) and coarser further out.
- **Per point:** `angle = atan2((terrain_elev - observer_elev -
  curvature_drop), distance)`, where `curvature_drop = distance² / (2 ×
  6371km × 7/6)` — the standard combined Earth-curvature + atmospheric-
  refraction correction (7/6 is the common approximation for how
  refraction bends light slightly around the curve). Clamped to ≥0.
- **Per bearing:** the max angle across its 10 distance samples (whichever
  point casts the highest angle, near or far).
- **Across bearings:** the max of the 5 (see §6 for why).
- Total: 51 elevation lookups (50 profile points + 1 observer point) in a
  single batched API call.

## 5. Verification performed

- **Positive test, North Vancouver, BC (49.31636, -123.06934):** due-west
  bearings (267°, 274°) returned exactly 0° (flat, open water across the
  Strait of Georgia); bearings 15-22° further round (289°, 297°) picked up
  real terrain, topping out at 2.02° from a 562m peak at 13km — the North
  Shore mountains. **This within-run contrast (flat water vs. real
  mountains in the same scan) is the strongest evidence the geometry is
  correct**, since it isn't dependent on cross-location comparison.
- **Attempted negative control, Swartz Bay, BC:** expected near-zero
  (assumed open water to the west), got 5.14°. Investigated rather than
  dismissed: Swartz Bay sits on the Saanich Peninsula itself, not facing
  open ocean, and the sampled points showed a coherent real profile
  (~140m near the terminal, dropping to 0m at a water gap around 5-8km,
  rising to 400-800m further out toward Vancouver Island's interior) —
  concluded this is genuine local terrain, not a bug. **Lesson: Swartz Bay
  was a bad choice for a "flat water" test site** — it's nestled among
  islands and channels, not open-ocean-facing. The North Vancouver result
  is the reliable verification.
- **Full integration:** `pinpoint.js` run end-to-end at North Vancouver
  (2026-09-04) — terrain scan (2.10°) correctly feeds the `gate` term
  (`terrain` factor 0.738, a real ~26% reduction), producing a coherent
  trace alongside the existing weather/AQ data, no errors.

## 6. Known limitations / decisions carried over

- **Max-across-bearings, not average or single-bearing** — same
  reasoning as Tier 1's worst-of-3 cloud aggregation, but more defensible
  here: terrain is a fixed physical fact from a deterministic DEM, not a
  noisy forecast, so a real ridge anywhere in the ±15° sweep genuinely
  will block part of the color window at some point.
- **DEM-only — no buildings or trees.** This only ever explains natural
  terrain blocking. A specific building or tree in front of the sun stays
  in the `photo_specific` tier of the rating-labels taxonomy
  (`docs/superpowers/specs/2026-08-18-sunset-rating-labels-design.md`) —
  genuinely unresolvable from elevation data, by design, not a gap to
  close later.
- **~90m DEM resolution** — fine for ridges and mountains, will miss
  small/sharp local features (a single building, a narrow gap in a ridge)
  that Tier 3 (live satellite/webcam) would be needed to catch, same as
  Tier 1's hyperlocal-effect limitation.

## 7. Open items / next steps

- No automated test suite yet for `terrain.js` or `pinpoint.js` — same
  gap noted in the Tier 1 spec, still open.
- Tier 3 (live satellite/webcam confirmation) is the next tier per
  research.md, and the harder one — no design work done yet.
