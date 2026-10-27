# Hyperlocal Sunset Forecasting Tool

*Project notes, input variables, data sources & scoring model — updated 3 August 2026*

---

## 1. What Makes a Good Sunset

Sunset colour comes down to a combination of atmospheric factors working together, not any single condition.

**High-altitude moisture + clear low air.** High, thin cloud (cirrus/altocumulus) acts as a screen to catch and reflect light, combined with clean, dry air near the ground so that light isn't scattered into haze before it arrives.

**Particulate content.** A moderate amount of fine particulate (dust, smoke, volcanic aerosol) scatters out blue/green wavelengths and leaves red/orange/pink dominant. Too much, though, and the sky just looks grey-brown.

**Recent frontal passage.** A cold front that recently cleared low-level haze, followed by cirrus streaming in aloft, is the classic setup for vivid colour.

**Low surface humidity.** Water vapour near the surface mutes contrast and washes out colour.

**Timing and geometry.** Light travels through the most atmosphere right at and just after sunset, maximising the scattering that produces red and orange. Clouds at the right height can catch light from a sun already below the horizon.

---

## 2. Existing Sunset Forecasting Tools

Several services already do pinpoint sunset-quality scoring by running weather model data (GFS/HRRR/ECMWF) through a scoring algorithm tuned to cloud altitude, humidity, and aerosol content.

| Tool | Notes |
|---|---|
| [SunsetWx](https://sunsetwx.com/) | Well-known dedicated scoring service ([how-to guide](https://sunsetwx.com/how-to/)) |
| [Alpenglow](https://alpenglowapp.com/) | Popular iOS/Android app with location-specific scores |
| [Sunset Predictor](https://sunset-predictor.com/) / [Sunsethue](https://sunsethue.com/) | Web-based quality score + timing tools |
| [Windy.com](https://www.windy.com/) | General weather platform; layer cloud cover by altitude manually — the DIY approach |

A [comparison review of Skyfire and SunsetWx](https://www.jmpeltier.com/review-skyfire-sunsetwx-predicting-sunrise-sunset/) covers real-world accuracy. Reception is generally positive for planning a few hours to a couple of days out, less reliable further out since cloud-deck detail is one of the harder things for models to nail precisely.

---

## 3. The Hyperlocal Effect

Regional and model forecasts describe an average condition across a grid cell (a few km to tens of km), not the exact sky above one viewing spot. Real local structure that models miss includes:

**Stray cloud edges.** A single low cloud bank or shower right at the western horizon can block the sun in the final minutes, even when the model called the area clear.

**Terrain occlusion.** A ridge, mountain, or even a line of hills to the west can hide the sun early, or generate its own localised cloud that the model grid doesn't resolve.

**Urban and local haze.** A city's pollution plume or a local inversion can mute colour at one spot while a location miles away with cleaner air gets a vivid sunset.

**Coastal microclimates.** Sea breeze fronts and marine layer fog form and clear on a timescale and spatial scale tighter than models capture.

**Very local events.** A nearby brush fire, passing shower, or contrails can change the sky right above you in ways no forecast accounts for.

---

## 4. Would a Pinpoint Location Remove the Hyperlocal Effect?

Not entirely. A pinpoint query is still answered from the same underlying model grid (HRRR ≈ 3 km cells, GFS ≈ 13–25 km), so it returns whichever cell the point falls in rather than truly local information. What genuinely narrows the gap:

**Higher-resolution model input** narrows grid cell size, but the very finest local structure still falls through.

**Live data sources** — real-time satellite imagery, webcam feeds, air-quality sensors, and ground station reports — describe what's actually happening rather than what was predicted.

**Terrain and viewing geometry.** Knowing the exact elevation profile to the west solves the terrain-occlusion problem with pure geometry, no weather data needed.

The realistic design is pinpoint model data plus terrain geometry for the multi-day forecast, switching to live satellite/webcam confirmation in the final hour or two before sunset.

---

## 5. How Complicated Would This Be to Build?

### Tier 1 — Basic pinpoint scoring tool (days to ~1 week, solo project)

Pull cloud-by-altitude and humidity data for a coordinate from a free API (e.g. Open-Meteo), run it through a scoring formula, display the result. This is essentially what SunsetWx and Sunset Predictor already do — a tractable solo project.

### Tier 2 — Add terrain occlusion (a few more weeks)

Use elevation data (SRTM/Copernicus DEM) to compute a horizon profile looking west from the viewer's point and check at what angle terrain blocks the sun. A standard viewshed calculation, but stitching it together well and making it fast for arbitrary points takes real engineering time.

### Tier 3 — Live satellite/webcam confirmation (the genuinely hard part)

Requires identifying cloud type and opacity from satellite band data — not just presence, but thin cirrus versus thick stratus — and reasoning about it relative to the viewer's exact sightline. A geometry problem layered on an image-classification problem. This is the piece that separates a hobby project from a product like SunsetWx, and likely why their scoring algorithm is kept proprietary.

**Bottom line:** pinpoint + terrain is an achievable few-weeks side project. The live-satellite layer is where real domain expertise (or a much rougher heuristic) becomes necessary.

---

## 6. Two Notes on Sampling

### Sample upwind, not just overhead

Sunset light reaches the observer along a path running roughly west. Conditions 50–300 km along the solar azimuth line matter as much as conditions directly overhead — a clear sky above you is useless if there is a thick deck sitting where the light has to come from. Every variable in groups A, B and C below should be sampled at several points along that bearing, not only at the observer's coordinate.

### Cloud band definitions are API-specific

Open-Meteo splits cloud cover at 3 km and 8 km (low / mid / high). Other providers use different thresholds, and the standard meteorological definitions vary by latitude. Pin down which convention your source uses before tuning any scoring weights against it.

---

## 7. Every Input, and Where to Get It

Complete list of the physical inputs that determine sunset quality, grouped roughly in order of predictive weight. Parameter names are literal API strings where one exists.

### A · Cloud structure
*The primary driver of whether there is anything to light up.*

| Input | Why it matters | Source / parameter | Link |
|---|---|---|---|
| High cloud cover (>8 km) | The canvas. Thin cirrus/altocumulus catches and reflects reddened light. The single strongest positive predictor. | `cloud_cover_high` | [Open-Meteo](https://open-meteo.com/en/docs) |
| Mid cloud cover (3–8 km) | Moderate amounts add depth and texture; heavy mid deck starts blocking light from below. | `cloud_cover_mid` | [Open-Meteo](https://open-meteo.com/en/docs) |
| Low cloud cover (0–3 km) | The main killer. A low deck on the western horizon blocks the sun before it can illuminate anything above. | `cloud_cover_low` | [Open-Meteo](https://open-meteo.com/en/docs) |
| Total cloud cover | Sanity check / overcast detection. | `cloud_cover` | [Open-Meteo](https://open-meteo.com/en/docs) |
| Cloud cover by pressure level | Finer vertical profile than the 3-band split — finds the exact layer that will catch light. | `cloud_cover_1000hPa` … `cloud_cover_300hPa` | [Open-Meteo](https://open-meteo.com/en/docs) |
| Cloud optical depth (COD) | Thin vs. thick. Thin cirrus glows; thick stratus goes flat grey. Model cover % alone cannot tell these apart. | GOES-R ABI Level 2 COD | [GOES-R COD](https://www.goes-r.gov/products/baseline-cloud-opt-depth.html) · [NCEI](https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc%3AC01508) |
| Cloud phase (ice vs. liquid) | Ice clouds are cirrus — the good kind. Distinguishes a high ice deck from a water-cloud layer. | GOES-R ABI L2 Cloud Phase | [GOES-R products](https://www.goes-r.gov/products/overview.html) |
| Cloud base height / ceiling | Actual observed ceiling at nearby stations — ground truth for the low-cloud blocking check. | METAR (cloud groups, ceiling) | [aviationweather.gov API](https://aviationweather.gov/data/api/) |

### B · Moisture & clarity
*Whether the light arrives clean or washed out.*

| Input | Why it matters | Source / parameter | Link |
|---|---|---|---|
| Surface relative humidity | High surface RH mutes contrast and washes colour toward pale pink/grey. | `relative_humidity_2m` | [Open-Meteo](https://open-meteo.com/en/docs) |
| RH at pressure levels | Moisture aloft indicates where cloud will actually form and persist through sunset. | `relative_humidity_850hPa`, `_700hPa`, `_500hPa`, `_300hPa` | [Open-Meteo](https://open-meteo.com/en/docs) |
| Dew point | Paired with temperature gives the humidity spread — a cleaner haze proxy than RH alone. | `dew_point_2m` | [Open-Meteo](https://open-meteo.com/en/docs) |
| Visibility | Direct measure of how much the near-surface air is scattering. Low visibility = muted sunset. | `visibility` | [Open-Meteo](https://open-meteo.com/en/docs) |
| Boundary layer height | A shallow PBL traps haze and pollution near the ground, dulling the horizon. A deep one disperses it. | `boundary_layer_height_pbl` | [Open-Meteo](https://open-meteo.com/en/docs) |

### C · Aerosols & particulates
*The colour-saturation term — moderate is vivid, heavy is brown.*

| Input | Why it matters | Source / parameter | Link |
|---|---|---|---|
| Aerosol optical depth (AOD) | The single best particulate metric. A moderate band boosts reds; too high and the sky goes flat brown. | `aerosol_optical_depth` · GOES-R ABI L2 AOD | [Open-Meteo AQ](https://open-meteo.com/en/docs/air-quality-api) · [GOES-R AOD](https://www.goes-r.gov/products/baseline-aerosol-opt-depth.html) |
| PM2.5 | Fine particulate — the size range that scatters blue out most effectively. Also the haze/pollution proxy. | `pm2_5` | [Open-Meteo AQ](https://open-meteo.com/en/docs/air-quality-api) · [AirNow](https://docs.airnowapi.org/) · [PurpleAir](https://api.purpleair.com/) |
| PM10 | Coarse particulate — dust and larger. Separates dust events from smoke/pollution. | `pm10` | [Open-Meteo AQ](https://open-meteo.com/en/docs/air-quality-api) |
| Dust concentration | Saharan/desert dust events are a classic vivid-sunset driver. | `dust` | [Open-Meteo AQ (CAMS)](https://open-meteo.com/en/docs/air-quality-api) |
| Sea salt aerosol | Coastal-specific scattering term. | `sea_salt_aerosol` | [Open-Meteo AQ](https://open-meteo.com/en/docs/air-quality-api) |
| Sulphur dioxide | Proxy for volcanic plumes and industrial output — volcanic sulphate aerosol produces the most famous sunsets. | `sulphur_dioxide` | [Open-Meteo AQ](https://open-meteo.com/en/docs/air-quality-api) |
| Smoke (surface + column) | Wildfire smoke, forecast explicitly. Moderate smoke is spectacular; dense smoke is dull orange murk. | HRRR-Smoke model output | [NOAA HRRR-Smoke](https://rapidrefresh.noaa.gov/hrrr/HRRRsmoke/) · [NOMADS](https://nomads.ncep.noaa.gov/) |
| Active fire detections | Upstream fire locations tell you whether smoke is about to arrive, before the aerosol models catch up. | FIRMS area API (VIIRS/MODIS) | [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/area/) |
| Volcanic activity | Stratospheric sulphate from eruptions produces months of enhanced sunsets — a slow-moving background term. | Weekly eruption reports | [Smithsonian GVP](https://volcano.si.edu/) |

### D · Sun geometry
*When to look, and which direction.*

| Input | Why it matters | Source / parameter | Link |
|---|---|---|---|
| Sunset / sunrise time | Anchors the whole forecast to the right hour at the right coordinate. | SunCalc (local) or sunrise-sunset API | [SunCalc](https://github.com/mourner/suncalc) · [sunrise-sunset.org](https://sunrise-sunset.org/api) |
| Solar azimuth at sunset | Tells you which compass bearing to evaluate — and which upwind grid cells the light actually passes through. | `SunCalc.getPosition().azimuth` | [SunCalc](https://github.com/mourner/suncalc) |
| Solar elevation vs. time | Golden hour and blue hour windows; the −4° to −6° range is when afterglow peaks. | `SunCalc.getPosition().altitude` | [NOAA Solar Calculator](https://gml.noaa.gov/grad/solcalc/) |
| Civil twilight duration | Latitude-dependent. Longer twilight means a longer, more gradual colour show. | `civil_twilight_begin` / `_end` | [sunrise-sunset.org](https://sunrise-sunset.org/api) |

### E · Terrain & observer geometry
*Pure geometry, fully solvable, no weather data needed.*

| Input | Why it matters | Source / parameter | Link |
|---|---|---|---|
| Observer elevation | A higher observer sees over low haze and local obstructions, and sees the sun later. | Elevation lookup by lat/long | [Open-Elevation](https://www.open-elevation.com/) · [Open-Meteo Elevation](https://open-meteo.com/en/docs/elevation-api) |
| Western horizon profile | The occlusion angle — at what elevation terrain hides the sun. Turns "official sunset" into "your sunset". | Copernicus DEM 30 m / SRTM / NASADEM | [OpenTopography](https://opentopography.org/developers) · [USGS EarthExplorer](https://earthexplorer.usgs.gov/) |
| Built obstruction | In cities, buildings block the horizon long before terrain does. | OSM `building:levels` / `height` | [Overpass API](https://overpass-api.de/) |

### F · Dynamics & trend
*Will conditions hold, clear, or close in by sunset.*

| Input | Why it matters | Source / parameter | Link |
|---|---|---|---|
| Wind at cloud level | Determines whether a blocking deck advects out (or in) during the critical final hour. | `wind_speed_500hPa`, `wind_direction_500hPa` | [Open-Meteo](https://open-meteo.com/en/docs) |
| Surface pressure / MSLP | Rising pressure behind a front means clearing — the classic post-frontal setup. | `pressure_msl`, `surface_pressure` | [Open-Meteo](https://open-meteo.com/en/docs) |
| Frontal position | The post-frontal "clean air below, cirrus above" pattern is the single best synoptic signature. | WPC surface analysis charts | [NOAA WPC](https://www.wpc.ncep.noaa.gov/html/sfc-zoom.php) |
| Precipitation | Rain at sunset blocks it; rain that ends 1–2 h before sunset is one of the best possible setups. | `precipitation`, `rain`, `showers` | [Open-Meteo](https://open-meteo.com/en/docs) |
| Live radar | Real-time confirmation that a shower will or won't clear the western horizon in time. | NEXRAD mosaic tiles | [RainViewer](https://www.rainviewer.com/api.html) · [Iowa State IEM](https://mesonet.agron.iastate.edu/GIS/radmap_api.phtml) |

### G · Live ground truth
*The final-hour layer that closes the hyperlocal gap.*

| Input | Why it matters | Source / parameter | Link |
|---|---|---|---|
| Visible satellite imagery | Actual cloud position and texture right now, every 5–15 min. Catches the stray bank the model missed. | GOES-16/18/19 ABI visible + IR | [NOAA STAR](https://www.star.nesdis.noaa.gov/GOES/) · [AWS Open Data](https://registry.opendata.aws/noaa-goes/) |
| Surface observations | Station-reported sky condition, ceiling, and visibility — cheap, frequent, and genuinely local. | METAR / SPECI reports | [aviationweather.gov API](https://aviationweather.gov/data/api/) |
| Webcams | Direct visual confirmation. The final check no model can substitute for. | Public look-west camera feeds | [Windy Webcams](https://www.windy.com/webcams) |

**Practical starting point:** groups A, B and D alone — all available from two free, keyless Open-Meteo endpoints plus a sun-position library — get you a working quality score. Group E is pure geometry and is the highest-value addition after that. Group G is the hard tier and the one that actually closes the hyperlocal gap.

---

## 8. Scoring Model

Reference implementation: `src/sunset/scoring.py`.

### Structure

The four terms combine **multiplicatively**, not as a weighted average:

```
score = gate × canvas × clarity × aerosol
```

This encodes a physical claim. These aren't four factors that trade off against each other — they're four conditions that all have to hold. Multiplication means any term near zero drags the result to zero regardless of the others, which is correct: a solid marine layer blocking the sun *should* override a beautiful cirrus deck. An average would let good terms compensate for a physically fatal one.

### The recurring device: a bell curve

Cloud cover and aerosol are both non-monotonic — more isn't better, and neither is less. There's a sweet spot with different failure modes on each side, which needs a peaked response:

```
bell(x, μ, σ) = exp( −(x − μ)² / (2σ²) )
```

Returns 1.0 at the optimum `μ`, falling off symmetrically. `σ` controls tolerance. It's the Gaussian shape without the normalising constant, so the peak is exactly 1.0 rather than the area being 1.0.

### Term 1 — light path gate

```
path    = 1 − (low_cloud_upwind / 100)^1.5
terrain = clamp(1 − block_deg / 8, 0.25, 1.0)
gate    = path × terrain
```

The exponent 1.5 matters. At 1.0, cloud cover would penalise linearly. But partial cover isn't uniformly opaque — it has gaps, and light finds them. An exponent above 1 makes low-to-moderate cover cheap while high cover still bites hard.

The terrain floor of 0.25 is physical, not a fudge: high cirrus is lit by sunlight that passed over the ridge tens of km away, so a blocked horizon costs the low-angle direct light but never the whole show.

**Uses upwind low cloud, not overhead.** Light reaching the cirrus above you travelled west-to-east; what matters is the deck it passed through on the way.

### Term 2 — canvas

```
canvas = 0.70 · bell(cloud_high, μ=55, σ=28)
       + 0.30 · bell(cloud_mid,  μ=30, σ=25)
```

High cloud peaks at 55% with a wide σ=28, so roughly 30–80% all scores well — that breadth is deliberate. Mid cloud peaks lower and carries less weight because it blocks about as readily as it reflects. Weights sum to exactly 1.0, so the term reaches but cannot exceed 1.0 naturally.

### Term 3 — clarity

```
rh_f    = clamp(1 − (rh − 45)/55, 0.25, 1.0)
vis_f   = clamp(visibility / 24000, 0.20, 1.0)
pbl_f   = clamp(0.55 + (pbl/2000)·0.45, 0.55, 1.0)
clarity = rh_f^0.5 × vis_f^0.6 × pbl_f
```

The fractional exponents handle redundancy. Humidity, visibility, and boundary-layer depth are three partially-overlapping measurements of the same physical quantity (near-surface scattering). Multiplying them raw would double- and triple-count it, so raising each to a power below 1 pulls it toward 1.0 and softens its individual bite.

These are linear ramps, not bells, because clarity genuinely is monotonic — less haze is always better.

### Term 4 — aerosol

```
boost    = 0.85 + 0.35 · bell(aod, μ=0.18, σ=0.12)
overload = clamp(1 − (aod − 0.5)/0.8, 0.35, 1.0)   if aod > 0.5
pm_pen   = clamp(1 − max(0, pm25 − 20)/60, 0.5, 1.0)
aerosol  = boost × overload × pm_pen
```

The only term that can exceed 1.0, and that asymmetry is the point: moderate particulate genuinely improves a sunset by scattering blue out of the light path. The offset-and-scale maps the bell's 0–1 range onto 0.85–1.20, so clean air is a mild penalty and optimal loading is a 20% bonus. Overload and PM2.5 sit dormant until their thresholds, then ramp down — modelling where extra particulate stops saturating colour and starts turning the sky brown.

### Worked example — "post-frontal classic"

```
TERM 1  light path gate           = 0.908
          upwind low cloud    10%  -> path    0.968
          terrain block     0.5deg -> terrain 0.938
TERM 2  canvas                    = 0.983
          high cloud         60%  -> bell    0.984  (x0.70)
          mid cloud          25%  -> bell    0.980  (x0.30)
TERM 3  clarity                   = 0.841
          RH                 48%  -> 0.945 ^0.5
          visibility      24000m  -> 1.000 ^0.6
          PBL height       1400m  -> 0.865
TERM 4  aerosol multiplier        = 1.195
          AOD              0.16   -> boost   1.195
          PM2.5             7.0   -> 1.000
----------------------------------------------------
0.908 × 0.983 × 0.841 × 1.195 = 0.8971  ->  90/100
```

No single term is bad here, yet the result isn't 97 — clarity at 0.841 quietly costs 16%. That's multiplication working as intended: mediocrity in one place is never fully recoverable elsewhere.

### Scenario results

| Scenario | Score | Rating |
|---|---:|---|
| Post-frontal classic | 90 | exceptional |
| Pair A: clear to the west | 72 | very good |
| Wildfire smoke, moderate | 30 | mediocre |
| Pair B: same sky, deck 120 km west | 26 | mediocre |
| Bluebird clear sky | 25 | mediocre |
| Ideal sky, but ridge to the west | 24 | mediocre |
| Marine layer (coastal summer) | 4 | poor |
| Wildfire smoke, heavy | 3 | poor |
| Solid overcast | 0 | poor |

### Why Pair A and Pair B diverge

Everything except upwind low cloud is identical, so only `path` changes:

```
A:  1 − 0.05^1.5 = 0.988820   → gate 0.927018
B:  1 − 0.75^1.5 = 0.350481   → gate 0.328576
ratio = 0.3544
```

Since the other three terms are unchanged and multiplication is associative, the final scores land in exactly that ratio: 72 × 0.3544 ≈ 26. One input, sampled 120 km west instead of overhead, moves the answer by nearly a factor of three. This is the concrete argument for sampling along the solar azimuth.

### Calibration caveat

The constants — μ=55, σ=28, the exponent 1.5, the 0.85/0.35 offset — are physically reasoned but **not fitted to data**. Until calibrated, treat scores as ordinal (this beats that) rather than absolute. Real calibration means collecting historical conditions paired with human-scored photographs of what the sunset actually looked like, then optimising these parameters against that set.

Note also that the scenario inputs are representative rather than observed — Open-Meteo's API is disallowed by robots.txt for automated fetching in the environment these notes were built in. Swapping in a live API call is a few lines; the input keys already match the parameter names exactly.

---

## Sources

- [SunsetWx](https://sunsetwx.com/) · [how-to guide](https://sunsetwx.com/how-to/)
- [Alpenglow](https://alpenglowapp.com/) · [App Store](https://apps.apple.com/us/app/alpenglow-sunset-forecast/id978589174)
- [Sunset Predictor](https://sunset-predictor.com/) · [Sunsethue](https://sunsethue.com/)
- [Skyfire vs SunsetWx review](https://www.jmpeltier.com/review-skyfire-sunsetwx-predicting-sunrise-sunset/)
- [Windy community: sunrise/sunset forecast](https://community.windy.com/topic/12863/sunrise-sunset-forecast)
- [Using Windy to predict sunset colour (video)](https://www.youtube.com/watch?v=ZNBOtJyOpJI)
- [Open-Meteo Forecast API](https://open-meteo.com/en/docs) · [Air Quality API](https://open-meteo.com/en/docs/air-quality-api)
- [NOAA NOMADS](https://nomads.ncep.noaa.gov/) · [HRRR-Smoke](https://rapidrefresh.noaa.gov/hrrr/HRRRsmoke/)
- [NOAA STAR GOES imagery](https://www.star.nesdis.noaa.gov/GOES/) · [GOES on AWS](https://registry.opendata.aws/noaa-goes/)
- [NASA FIRMS Area API](https://firms.modaps.eosdis.nasa.gov/api/area/)
- [OpenTopography](https://opentopography.org/developers) · [USGS EarthExplorer](https://earthexplorer.usgs.gov/)
- [SunCalc](https://github.com/mourner/suncalc) · [NOAA Solar Calculator](https://gml.noaa.gov/grad/solcalc/)
- [aviationweather.gov Data API](https://aviationweather.gov/data/api/)
- [RainViewer API](https://www.rainviewer.com/api.html) · [Iowa State IEM RadMap](https://mesonet.agron.iastate.edu/GIS/radmap_api.phtml)
