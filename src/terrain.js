// terrain.js — Tier 2: terrain-occlusion horizon profile.
//
// Computes terrain_block_deg: how many degrees above the true (flat) horizon
// the observer's actual visible horizon sits, in the direction of sunset.
// Uses Open-Meteo's free, keyless batch Elevation API (Copernicus DEM, ~90m
// resolution) - no API key needed, consistent with the rest of this project.

const ELEVATION_URL = "https://api.open-meteo.com/v1/elevation";

const BEARING_OFFSETS_DEG = [-15, -7.5, 0, 7.5, 15];
const DISTANCES_KM = [1, 2, 3, 5, 8, 13, 21, 34, 55, 90];

const EARTH_RADIUS_KM = 6371;
const REFRACTION_K = 7 / 6; // standard curvature+refraction correction factor

function toRad(d) { return (d * Math.PI) / 180; }
function toDeg(r) { return (r * 180) / Math.PI; }

// Great-circle destination point given a start coordinate, bearing, and distance.
// Duplicated from pinpoint.js deliberately - terrain.js has no dependency on
// pinpoint.js so it stays independently testable.
function destinationPoint(lat, lon, bearingDeg, distanceKm) {
  const bearing = toRad(bearingDeg);
  const lat1 = toRad(lat), lon1 = toRad(lon);
  const angDist = distanceKm / EARTH_RADIUS_KM;
  const lat2 = Math.asin(
    Math.sin(lat1) * Math.cos(angDist) + Math.cos(lat1) * Math.sin(angDist) * Math.cos(bearing)
  );
  const lon2 = lon1 + Math.atan2(
    Math.sin(bearing) * Math.sin(angDist) * Math.cos(lat1),
    Math.cos(angDist) - Math.sin(lat1) * Math.sin(lat2)
  );
  return { lat: toDeg(lat2), lon: ((toDeg(lon2) + 540) % 360) - 180 };
}

// Angle above true horizontal at which a point of given elevation/distance
// appears, correcting for Earth curvature and atmospheric refraction.
function elevationAngleDeg(observerElevM, targetElevM, distanceKm) {
  const curvatureDropM = (distanceKm ** 2 / (2 * REFRACTION_K * EARTH_RADIUS_KM)) * 1000;
  const heightDiffM = targetElevM - observerElevM - curvatureDropM;
  return Math.max(0, toDeg(Math.atan2(heightDiffM, distanceKm * 1000)));
}

async function fetchElevations(points) {
  const lats = points.map((p) => p.lat.toFixed(5)).join(",");
  const lons = points.map((p) => p.lon.toFixed(5)).join(",");
  const url = `${ELEVATION_URL}?latitude=${lats}&longitude=${lons}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`);
  const j = await res.json();
  return j.elevation;
}

// Returns { terrainBlockDeg, observerElevationM, bearings: [{bearing, blockDeg, samples}] }
async function getTerrainBlockDeg(lat, lon, sunsetAzimuthDeg) {
  const bearings = BEARING_OFFSETS_DEG.map((offset) => (sunsetAzimuthDeg + offset + 360) % 360);

  // point 0 = observer's own location; rest = bearing x distance grid
  const points = [{ lat, lon }];
  const index = []; // maps points[i>0] back to (bearingIdx, distanceIdx)
  bearings.forEach((bearing, bIdx) => {
    DISTANCES_KM.forEach((km, dIdx) => {
      points.push(destinationPoint(lat, lon, bearing, km));
      index.push({ bIdx, dIdx, km });
    });
  });

  const elevations = await fetchElevations(points);
  const observerElevationM = elevations[0];

  const bearingResults = bearings.map((bearing) => ({
    bearing,
    samples: [],
    blockDeg: 0,
  }));

  index.forEach(({ bIdx, dIdx, km }, i) => {
    const targetElevM = elevations[i + 1];
    const angle = elevationAngleDeg(observerElevationM, targetElevM, km);
    bearingResults[bIdx].samples.push({ km, elevationM: targetElevM, angleDeg: angle });
    if (angle > bearingResults[bIdx].blockDeg) bearingResults[bIdx].blockDeg = angle;
  });

  const terrainBlockDeg = Math.max(...bearingResults.map((b) => b.blockDeg));

  return { terrainBlockDeg, observerElevationM, bearings: bearingResults };
}

module.exports = { getTerrainBlockDeg, elevationAngleDeg, destinationPoint, BEARING_OFFSETS_DEG, DISTANCES_KM };

if (require.main === module) {
  const [, , latArg, lonArg, azArg] = process.argv;
  if (!latArg || !lonArg || !azArg) {
    console.error("Usage: node src/terrain.js <lat> <lon> <sunsetAzimuthDeg>");
    process.exit(1);
  }
  getTerrainBlockDeg(parseFloat(latArg), parseFloat(lonArg), parseFloat(azArg)).then((result) => {
    console.log(`Observer elevation: ${result.observerElevationM}m`);
    for (const b of result.bearings) {
      console.log(`Bearing ${b.bearing.toFixed(1)}deg -> block ${b.blockDeg.toFixed(2)}deg`);
      for (const s of b.samples) {
        console.log(`    ${String(s.km).padStart(3)}km  elev ${String(s.elevationM).padStart(5)}m  angle ${s.angleDeg.toFixed(2)}deg`);
      }
    }
    console.log(`\nterrain_block_deg (max across bearings) = ${result.terrainBlockDeg.toFixed(2)}`);
  }).catch((err) => {
    console.error("Error:", err.message);
    process.exit(1);
  });
}
