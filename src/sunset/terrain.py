"""
terrain.py — Tier 2: terrain-occlusion horizon profile. Pure, no I/O.

Computes terrain_block_deg: how many degrees above the true (flat) horizon
the observer's actual visible horizon sits, in the direction of sunset.

Split in two so the geometry is testable offline (ARCHITECTURE.md S3):
  profile_points()   which points to look up (observer first, then the grid)
  horizon_profile()  given their elevations, the blocking angle per bearing
The elevation lookup itself lives in sunset.sources.openmeteo.
"""

import math
from dataclasses import dataclass

from sunset.geo import EARTH_RADIUS_KM, destination_point

BEARING_OFFSETS_DEG = [-15, -7.5, 0, 7.5, 15]
DISTANCES_KM = [1, 2, 3, 5, 8, 13, 21, 34, 55, 90]

REFRACTION_K = 7 / 6  # standard curvature+refraction correction factor


@dataclass(frozen=True)
class Sample:
    km: float
    elevation_m: float
    angle_deg: float


@dataclass(frozen=True)
class BearingProfile:
    bearing: float
    block_deg: float
    samples: list[Sample]


@dataclass(frozen=True)
class TerrainResult:
    terrain_block_deg: float        # max block across all bearings
    observer_elevation_m: float
    bearings: list[BearingProfile]


def elevation_angle_deg(observer_elev_m: float, target_elev_m: float, distance_km: float) -> float:
    """Angle above true horizontal at which a point of given elevation and
    distance appears, correcting for Earth curvature and atmospheric
    refraction. Never negative: terrain below the horizon blocks nothing."""
    curvature_drop_m = (distance_km ** 2 / (2 * REFRACTION_K * EARTH_RADIUS_KM)) * 1000
    height_diff_m = target_elev_m - observer_elev_m - curvature_drop_m
    return max(0.0, math.degrees(math.atan2(height_diff_m, distance_km * 1000)))


def scan_bearings(sunset_azimuth_deg: float) -> list[float]:
    return [(sunset_azimuth_deg + offset + 360) % 360 for offset in BEARING_OFFSETS_DEG]


def profile_points(lat: float, lon: float, sunset_azimuth_deg: float) -> list[tuple[float, float]]:
    """Points whose elevation is needed: the observer, then bearing x distance."""
    points = [(lat, lon)]
    for bearing in scan_bearings(sunset_azimuth_deg):
        for km in DISTANCES_KM:
            points.append(destination_point(lat, lon, bearing, km))
    return points


def horizon_profile(sunset_azimuth_deg: float, elevations: list[float]) -> TerrainResult:
    """Blocking angle per bearing, given elevations in profile_points() order."""
    expected = 1 + len(BEARING_OFFSETS_DEG) * len(DISTANCES_KM)
    if len(elevations) != expected:
        raise ValueError(f"expected {expected} elevations, got {len(elevations)}")

    observer_elevation_m = elevations[0]
    grid = iter(elevations[1:])
    profiles = []
    for bearing in scan_bearings(sunset_azimuth_deg):
        samples = []
        for km in DISTANCES_KM:
            target = next(grid)
            samples.append(Sample(km, target, elevation_angle_deg(observer_elevation_m, target, km)))
        profiles.append(BearingProfile(bearing, max([0.0] + [s.angle_deg for s in samples]), samples))

    return TerrainResult(
        terrain_block_deg=max(p.block_deg for p in profiles),
        observer_elevation_m=observer_elevation_m,
        bearings=profiles,
    )
