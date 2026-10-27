# Tier 3, phase 1: satellite imagery — manual/interactive interpretation

> **Note (2026-10-26):** written when the code was JavaScript. It has since been
> migrated to Python (NEXT-STEPS C1). File mapping: `sunset_score.py`/`.js` →
> `src/sunset/scoring.py` (+ `models.py`); `pinpoint.js` → `pinpoint.py`, `cli.py`,
> `sources/openmeteo.py`, `geo.py`; `terrain.js` → `terrain.py`; `label_data.js` →
> `study/ratings/ratings.json`; `label_analysis.js` → `label_analysis.py`.
> See ARCHITECTURE.md. The text below is unchanged.

Status: workflow validated end-to-end, not yet automated into a script.
This is a first slice of "Tier 3 — live satellite/webcam confirmation"
from research.md §5, using the phase 1 approach (interactive, no ML) that
was explicitly chosen over building an automated classifier (phase 2,
future work) for this first pass.

## 1. Purpose

Give a qualitative, human-in-the-loop cross-check against the Tier 1+2
forecast score, using real satellite imagery from shortly before sunset —
closing part of the "hyperlocal effect" gap research.md §3 describes
(a model grid cell can be wrong; a photo of what's actually up there can
catch that). This is explicitly the "final hour or two before sunset"
layer research.md §4 calls for.

## 2. Why manual/interactive, not automated classification

Confirmed architecturally distinct from Tier 1/2: `pinpoint.js` and
`terrain.js` are deterministic scripts with no LLM involved at runtime.
Actually distinguishing cloud type/opacity from an image (thin cirrus vs.
thick stratus) either needs a live Claude session looking at the image, or
real image-classification code — the latter is explicitly the hard part
research.md flags, needing domain expertise or training data neither of
which exist yet. Decision: start with the interactive approach (works
today, zero ML risk), treat automated classification as separate future
work once there's a reason to invest in it.

## 3. Data source

NOAA STAR's pre-rendered GOES-West GeoColor sector JPEGs:
`https://cdn.star.nesdis.noaa.gov/GOES18/ABI/SECTOR/{sector}/GEOCOLOR/latest.jpg`
— free, no API key, CC0-licensed, updated every 5-15 minutes. Chosen over
raw GOES band data on AWS (NetCDF, would need real geospatial processing
libraries like satpy/rasterio to extract/reproject/crop) since these are
already-rendered images, directly viewable.

**Known limitation:** sector coverage is CONUS-optimized. Tested against
this project's actual test coordinate (southern Vancouver Island, near
Sooke, BC, 48.4931/-123.3467) — neither the `pnw` sector (2400x2400) nor
the larger `wus` sector (4000x4000, "Western US Seaboard") is centered on
this location; both place it at the very top edge of frame. A generous
crop of `wus`'s top-left region (see §4) worked well enough for a
qualitative read, but this won't generalize cleanly to arbitrary
coordinates without either (a) picking a different sector per rough
region, or (b) finding a Canada-centered imagery source for BC/northern
locations specifically. Not solved generally yet - solved for this one
test case.

## 4. Workflow (as actually performed)

1. Fetch the sector JPEG (`curl` to the URL above).
2. Crop to the region of interest. No documented pixel-to-lat/lon mapping
   was readily available for these sector images (likely a non-trivial
   map projection, not simple equirectangular), so this was done by eye —
   crop generously around where the target coastline is recognizable,
   not a precise geographic crop. Used Python + Pillow for this (now that
   Python is installed - see §5):
   ```python
   from PIL import Image
   img = Image.open("wus_latest.jpg")
   w, h = img.size
   crop = img.crop((0, 0, int(w*0.55), int(h*0.28)))  # top-left region
   crop = crop.resize((crop.width*2, crop.height*2), Image.LANCZOS)
   crop.save("wus_crop_topleft.jpg", quality=95)
   ```
3. View the crop (Read tool) and describe cloud structure/texture/extent
   in the direction of the sunset azimuth and upwind corridor already
   computed by `pinpoint.js`.
4. Compare that qualitative read against the Tier 1+2 numeric score and
   its term breakdown — note agreement or contradiction, same spirit as
   the Active Pass cross-check in the Tier 1 spec.

## 5. Python is now available

Installed via winget (`Python.Python.3.13`, 3.13.15) specifically to get
Pillow for this cropping step — the project's other code stays JS
(`sunset_score.js` is still the canonical scoring implementation; this
doesn't change that). Note: this session's already-running terminal
processes cached their PATH before the install, so `python`/`pip` don't
resolve directly in them — use the full path
(`C:\Users\aaron\AppData\Local\Programs\Python\Python313\python.exe`) or a
fresh terminal.

## 5b. True cloud-type classification: open problem (not solved)

Checked how much the IR bands add beyond GeoColor, and whether any free
public source exposes actual cloud-genus or ice/liquid-phase data (the
"cirrus vs. thick stratus" distinction research.md's Tier 3 is fundamentally
about):

- **NOAA STAR sector JPEGs, Band 13 (clean longwave IR — cloud-top
  temperature):** genuinely useful, but only for a coarse height read.
  Confirmed it can rule "high, cold, thick cloud" in or out (no cold-top
  color enhancement over our test corridor = probably low/mid-level,
  matching the forecast's low high-cloud reading) — but the color
  threshold on this product is tuned for deep convection, not fine-grained
  height/type discrimination within "not very cold."
- **`DayCloudPhase`/`CloudPhaseDistinction`** (the actual GOES-R ABI L2
  Cloud Phase product research.md originally cited): not available as a
  rendered image from this CDN (404) for this satellite/sector.
- **Windy and Ventusky:** checked directly — both are the same shape of
  data as what `sunset_score.py` already uses (cloud cover % by high/mid/
  low altitude band). Windy.app's own educational content lists which
  cloud genera *typically* occur at each altitude, but that's reference
  material, not a live per-pixel classification. Neither exposes real
  cloud-type data.

**Conclusion: true cloud-type/phase classification is left as an open
problem.** Nothing free and readily available (checked: NOAA STAR rendered
products, Windy, Ventusky) provides it. Closing this gap for real would
mean either finding GOES-R's raw Cloud Phase data in some other accessible
form, or building actual image-classification/ML work from raw multi-band
satellite data — the same "genuinely hard part" research.md flagged from
the start, now confirmed rather than assumed.

## 6. Verified example run

Location: 48.4931, -123.3467 (near Sooke, BC). Date: 2026-09-04 (local
"today" - see §7 bug fix). Tier 1+2 score: 13/100 poor, driven by weak
canvas (3% high cloud, 51% mid cloud) and moderate upwind low cloud (31%
at 50km, dropping to ~0-1% further out). Satellite crop showed broken,
streaky, textured cloud over the upwind Pacific corridor with visible
gaps - no solid blocking deck, no dramatic cirrus canvas either.
**Consistent with the forecast score**, no override needed this time.

## 7. Bug fix made along the way (in pinpoint.js, not part of Tier 3 itself)

Found while preparing this test: `pinpoint.js`'s default date (when none is
passed) used `new Date().toISOString().slice(0,10)` - the caller's **UTC**
calendar date, not the **observer's local** date. For a Vancouver-area
(UTC-7) location, any run between 5pm and midnight local already sees a
UTC date one day ahead, silently scoring tomorrow's sunset instead of
tonight's. Fixed with a new `resolveLocalToday(lat, lon)` that asks
Open-Meteo for "today" in that location's own timezone before doing
anything else. Confirmed fix: run at 00:17 UTC / 5:17pm local correctly
resolved to 2026-09-04 (tonight), not 2026-09-05.

## 8. Open items / next steps

- Sector-selection/coverage problem (§3) not solved generally - only
  worked around for one test coordinate.
- No automated crop - still a manual "look at the image and figure out
  where the coastline is" step each time.
- Phase 2 (automated classification, no LLM at runtime) is unaddressed,
  deliberately deferred per the decision in §2.
- The METAR/surface-observations sub-piece of Tier 3 (structured data,
  no image interpretation needed) was scoped in conversation but not yet
  built - see the paused design discussion before this satellite work.
- The notification/alerting idea that motivated exploring Tier 3 further
  is still unresolved - cloud routines (`schedule` skill) can't access
  local files/this project without a git repo + hosting, and that path
  was explicitly deferred by the user. No local (Task Scheduler) path has
  been explored either.
