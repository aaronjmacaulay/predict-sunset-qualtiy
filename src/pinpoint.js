// pinpoint.js — Tier 1 + Tier 2 live pinpoint sunset scoring tool.
//
// Usage: node src/pinpoint.js <lat> <lon> [YYYY-MM-DD]
// Date defaults to today. Scores the FORECASTED conditions at that date's
// sunset hour (rounded to the nearest hourly bucket), not conditions "now".
//
// terrain_block_deg comes from terrain.js's horizon-profile scan (Tier 2).

const { score } = require("./sunset_score");
const { getTerrainBlockDeg } = require("./terrain");

const WEATHER_URL = "https://api.open-meteo.com/v1/forecast";
const AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality";
const UPWIND_DISTANCES_KM = [50, 150, 250];

function toRad(d) { return (d * Math.PI) / 180; }
function toDeg(r) { return (r * 180) / Math.PI; }
function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }

// Solar azimuth at a given instant, for an observer at (lat, lon).
// Standard NOAA solar position algorithm, ~0.01deg accuracy - plenty for
// picking a compass bearing to sample upwind along.
function solarAzimuth(date, lat, lon) {
  const jd = date.getTime() / 86400000 + 2440587.5;
  const jc = (jd - 2451545.0) / 36525.0;

  const geomMeanLongSun = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360;
  const geomMeanAnomSun = 357.52911 + jc * (35999.05029 - 0.0001537 * jc);
  const eccentEarthOrbit = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc);
  const sunEqOfCtr =
    Math.sin(toRad(geomMeanAnomSun)) * (1.914602 - jc * (0.004817 + 0.000014 * jc)) +
    Math.sin(toRad(2 * geomMeanAnomSun)) * (0.019993 - 0.000101 * jc) +
    Math.sin(toRad(3 * geomMeanAnomSun)) * 0.000289;
  const sunTrueLong = geomMeanLongSun + sunEqOfCtr;
  const sunAppLong = sunTrueLong - 0.00569 - 0.00478 * Math.sin(toRad(125.04 - 1934.136 * jc));
  const meanObliqEcliptic = 23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60;
  const obliqCorr = meanObliqEcliptic + 0.00256 * Math.cos(toRad(125.04 - 1934.136 * jc));
  const sunDeclin = toDeg(Math.asin(Math.sin(toRad(obliqCorr)) * Math.sin(toRad(sunAppLong))));

  const y = Math.tan(toRad(obliqCorr / 2)) ** 2;
  const eqOfTime = toDeg(
    y * Math.sin(2 * toRad(geomMeanLongSun)) -
    2 * eccentEarthOrbit * Math.sin(toRad(geomMeanAnomSun)) +
    4 * eccentEarthOrbit * y * Math.sin(toRad(geomMeanAnomSun)) * Math.cos(2 * toRad(geomMeanLongSun)) -
    0.5 * y * y * Math.sin(4 * toRad(geomMeanLongSun)) -
    1.25 * eccentEarthOrbit * eccentEarthOrbit * Math.sin(2 * toRad(geomMeanAnomSun))
  ) * 4;

  const timeUTCmin = date.getUTCHours() * 60 + date.getUTCMinutes() + date.getUTCSeconds() / 60;
  const trueSolarTime = (timeUTCmin + eqOfTime + 4 * lon + 1440) % 1440;
  let hourAngle = trueSolarTime / 4 - 180;
  if (hourAngle < -180) hourAngle += 360;

  const solarZenith = toDeg(Math.acos(
    Math.sin(toRad(lat)) * Math.sin(toRad(sunDeclin)) +
    Math.cos(toRad(lat)) * Math.cos(toRad(sunDeclin)) * Math.cos(toRad(hourAngle))
  ));

  const azimuthDenom = Math.cos(toRad(lat)) * Math.sin(toRad(solarZenith));
  let azimuth;
  if (Math.abs(azimuthDenom) > 0.001) {
    const arg = clamp(
      (Math.sin(toRad(lat)) * Math.cos(toRad(solarZenith)) - Math.sin(toRad(sunDeclin))) / azimuthDenom,
      -1, 1
    );
    azimuth = 180 - toDeg(Math.acos(arg));
    if (hourAngle > 0) azimuth = -azimuth;
  } else {
    azimuth = lat > 0 ? 180 : 0;
  }
  return (azimuth + 360) % 360;
}

// Great-circle destination point given a start coordinate, bearing, and distance.
function destinationPoint(lat, lon, bearingDeg, distanceKm) {
  const R = 6371;
  const bearing = toRad(bearingDeg);
  const lat1 = toRad(lat), lon1 = toRad(lon);
  const angDist = distanceKm / R;
  const lat2 = Math.asin(
    Math.sin(lat1) * Math.cos(angDist) + Math.cos(lat1) * Math.sin(angDist) * Math.cos(bearing)
  );
  const lon2 = lon1 + Math.atan2(
    Math.sin(bearing) * Math.sin(angDist) * Math.cos(lat1),
    Math.cos(angDist) - Math.sin(lat1) * Math.sin(lat2)
  );
  return { lat: toDeg(lat2), lon: ((toDeg(lon2) + 540) % 360) - 180 };
}

function nearestHourIndex(times, targetIso) {
  const target = new Date(targetIso).getTime();
  let best = 0, bestDiff = Infinity;
  times.forEach((t, i) => {
    const diff = Math.abs(new Date(t).getTime() - target);
    if (diff < bestDiff) { bestDiff = diff; best = i; }
  });
  return best;
}

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`);
  return res.json();
}

async function getSunsetTime(lat, lon, dateStr) {
  const url = `${WEATHER_URL}?latitude=${lat}&longitude=${lon}&daily=sunset&timezone=auto` +
    `&start_date=${dateStr}&end_date=${dateStr}`;
  const j = await fetchJson(url);
  if (!j.daily || !j.daily.sunset || !j.daily.sunset[0]) {
    throw new Error(`No sunset time returned for ${dateStr} at (${lat}, ${lon})`);
  }
  return { sunsetIso: j.daily.sunset[0], timezone: j.timezone };
}

// Resolves "today" in the OBSERVER'S local timezone, not the caller's UTC
// clock date. Needed because e.g. 00:17 UTC is already 5:17pm the previous
// day in Vancouver (UTC-7) - a naive new Date().toISOString() would silently
// score tomorrow's sunset instead of tonight's for any evening run.
async function resolveLocalToday(lat, lon) {
  const url = `${WEATHER_URL}?latitude=${lat}&longitude=${lon}&daily=sunset&timezone=auto&forecast_days=1`;
  const j = await fetchJson(url);
  return j.daily.time[0];
}

async function getMainWeather(lat, lon, dateStr, sunsetIso) {
  const url = `${WEATHER_URL}?latitude=${lat}&longitude=${lon}&timezone=auto` +
    `&hourly=cloud_cover_high,cloud_cover_mid,relative_humidity_2m,visibility,boundary_layer_height` +
    `&start_date=${dateStr}&end_date=${dateStr}`;
  const j = await fetchJson(url);
  const idx = nearestHourIndex(j.hourly.time, sunsetIso);
  return {
    hour: j.hourly.time[idx],
    cloud_high: j.hourly.cloud_cover_high[idx],
    cloud_mid: j.hourly.cloud_cover_mid[idx],
    rh_2m: j.hourly.relative_humidity_2m[idx],
    visibility_m: j.hourly.visibility[idx],
    pbl_height_m: j.hourly.boundary_layer_height[idx],
  };
}

async function getUpwindLowCloud(lat, lon, dateStr, sunsetIso) {
  const url = `${WEATHER_URL}?latitude=${lat}&longitude=${lon}&timezone=auto` +
    `&hourly=cloud_cover_low&start_date=${dateStr}&end_date=${dateStr}`;
  const j = await fetchJson(url);
  const idx = nearestHourIndex(j.hourly.time, sunsetIso);
  return j.hourly.cloud_cover_low[idx];
}

async function getAirQuality(lat, lon, dateStr, sunsetIso) {
  const url = `${AQ_URL}?latitude=${lat}&longitude=${lon}&timezone=auto` +
    `&hourly=aerosol_optical_depth,pm2_5&start_date=${dateStr}&end_date=${dateStr}`;
  const j = await fetchJson(url);
  const idx = nearestHourIndex(j.hourly.time, sunsetIso);
  return { aod: j.hourly.aerosol_optical_depth[idx], pm25: j.hourly.pm2_5[idx] };
}

async function run(lat, lon, dateStr) {
  console.log(`Pinpoint sunset score — (${lat}, ${lon}) on ${dateStr}`);
  console.log("=".repeat(60));

  const { sunsetIso, timezone } = await getSunsetTime(lat, lon, dateStr);
  console.log(`Sunset time: ${sunsetIso} (${timezone})`);

  const azimuth = solarAzimuth(new Date(sunsetIso), lat, lon);
  console.log(`Solar azimuth at sunset: ${azimuth.toFixed(1)} deg`);

  const upwindPoints = UPWIND_DISTANCES_KM.map((km) => ({
    km,
    ...destinationPoint(lat, lon, azimuth, km),
  }));

  const [mainWeather, upwindClouds, aq, terrain] = await Promise.all([
    getMainWeather(lat, lon, dateStr, sunsetIso),
    Promise.all(upwindPoints.map((p) => getUpwindLowCloud(p.lat, p.lon, dateStr, sunsetIso))),
    getAirQuality(lat, lon, dateStr, sunsetIso),
    getTerrainBlockDeg(lat, lon, azimuth),
  ]);

  console.log(`Evaluated hour (nearest bucket): ${mainWeather.hour}`);
  console.log("Upwind low cloud samples:");
  upwindPoints.forEach((p, i) => {
    console.log(`  ${p.km}km @ ${azimuth.toFixed(0)}deg -> (${p.lat.toFixed(3)}, ${p.lon.toFixed(3)}): ${upwindClouds[i]}%`);
  });
  const cloudLowUpwind = Math.max(...upwindClouds);
  console.log(`Worst-case upwind low cloud: ${cloudLowUpwind}%`);
  console.log(`Observer elevation: ${terrain.observerElevationM}m`);
  console.log("Terrain horizon scan:");
  terrain.bearings.forEach((b) => {
    console.log(`  ${b.bearing.toFixed(1)}deg -> block ${b.blockDeg.toFixed(2)}deg`);
  });
  console.log(`terrain_block_deg (max across bearings): ${terrain.terrainBlockDeg.toFixed(2)}`);
  console.log();

  const observation = {
    cloud_high: mainWeather.cloud_high,
    cloud_mid: mainWeather.cloud_mid,
    cloud_low_upwind: cloudLowUpwind,
    rh_2m: mainWeather.rh_2m,
    visibility_m: mainWeather.visibility_m,
    pbl_height_m: mainWeather.pbl_height_m,
    aod: aq.aod,
    pm25: aq.pm25,
    terrain_block_deg: terrain.terrainBlockDeg,
  };

  score(observation, true);
}

const [, , latArg, lonArg, dateArg] = process.argv;
if (!latArg || !lonArg) {
  console.error("Usage: node src/pinpoint.js <lat> <lon> [YYYY-MM-DD]");
  process.exit(1);
}
const lat = parseFloat(latArg), lon = parseFloat(lonArg);

(async () => {
  try {
    const dateStr = dateArg || await resolveLocalToday(lat, lon);
    await run(lat, lon, dateStr);
  } catch (err) {
    console.error("Error:", err.message);
    process.exit(1);
  }
})();
