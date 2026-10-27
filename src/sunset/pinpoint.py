"""
pinpoint.py — Tier 1 + Tier 2: score a real place and date from live data.

Orchestration only: no printing, no argument parsing (that's cli.py), no
HTTP details (that's sources/). Scores the FORECAST conditions at that date's
sunset hour, not conditions "now".

  sunset time -> solar azimuth -> upwind points -> fetch -> Observation -> score
"""

from dataclasses import dataclass

from sunset import geo, scoring, terrain
from sunset.models import Observation, ScoreResult
from sunset.sources.openmeteo import OpenMeteo

UPWIND_DISTANCES_KM = [50, 150, 250]


@dataclass(frozen=True)
class UpwindSample:
    km: float
    lat: float
    lon: float
    low_cloud: float | None


@dataclass(frozen=True)
class PinpointResult:
    lat: float
    lon: float
    date: str
    sunset_local: str
    timezone: str
    azimuth_deg: float
    evaluated_hour: str            # the hourly bucket nearest sunset
    upwind: list[UpwindSample]
    terrain: terrain.TerrainResult
    observation: Observation
    result: ScoreResult


def pinpoint(lat: float, lon: float, date: str | None = None,
             source: OpenMeteo | None = None) -> PinpointResult:
    """Score the sunset at (lat, lon) on `date` (YYYY-MM-DD; default: today
    in the location's own timezone)."""
    source = source or OpenMeteo()
    date = date or source.local_today(lat, lon)

    sunset = source.sunset(lat, lon, date)
    azimuth = geo.solar_azimuth(sunset.utc, lat, lon)

    spot = source.spot_weather(lat, lon, date, sunset.local_iso)
    upwind = []
    for km in UPWIND_DISTANCES_KM:
        p_lat, p_lon = geo.destination_point(lat, lon, azimuth, km)
        upwind.append(UpwindSample(km, p_lat, p_lon, source.low_cloud(p_lat, p_lon, date, sunset.local_iso)))
    aq = source.air_quality(lat, lon, date, sunset.local_iso)
    horizon = terrain.horizon_profile(azimuth, source.elevations(terrain.profile_points(lat, lon, azimuth)))

    # Worst case across the upwind samples: one cloudy cell sets the whole
    # light-path term. Known weakness, kept as-is for now (NEXT-STEPS D1).
    low_clouds = [u.low_cloud for u in upwind]
    observation = Observation(
        cloud_high=spot["cloud_high"],
        cloud_mid=spot["cloud_mid"],
        cloud_low_upwind=None if None in low_clouds else max(low_clouds),
        rh_2m=spot["rh_2m"],
        visibility_m=spot["visibility_m"],
        pbl_height_m=spot["pbl_height_m"],
        aod=aq["aod"],
        pm25=aq["pm25"],
        terrain_block_deg=horizon.terrain_block_deg,
    )

    return PinpointResult(
        lat=lat, lon=lon, date=date,
        sunset_local=sunset.local_iso, timezone=sunset.timezone,
        azimuth_deg=azimuth, evaluated_hour=spot["hour"],
        upwind=upwind, terrain=horizon,
        observation=observation, result=scoring.score(observation),
    )
