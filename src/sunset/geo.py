"""
geo.py — sun position and great-circle geometry. Pure functions, no I/O.

Shared by pinpoint (upwind sampling) and terrain (horizon scan), which each
had their own copy of destination_point in the JS version (ARCHITECTURE.md S8).
"""

import math
from datetime import datetime, timezone

EARTH_RADIUS_KM = 6371


def solar_azimuth(when: datetime, lat: float, lon: float) -> float:
    """Compass bearing of the sun (degrees, 0 = north, clockwise) at `when`.

    Standard NOAA solar position algorithm, ~0.01 deg accuracy - plenty for
    picking a bearing to sample upwind along. `when` must be timezone-aware;
    a naive datetime is ambiguous and is rejected.
    """
    if when.tzinfo is None:
        raise ValueError("solar_azimuth needs a timezone-aware datetime")
    when = when.astimezone(timezone.utc)

    rad, deg = math.radians, math.degrees
    jd = when.timestamp() / 86400 + 2440587.5
    jc = (jd - 2451545.0) / 36525.0

    geom_mean_long_sun = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
    geom_mean_anom_sun = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
    eccent_earth_orbit = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    sun_eq_of_ctr = (
        math.sin(rad(geom_mean_anom_sun)) * (1.914602 - jc * (0.004817 + 0.000014 * jc))
        + math.sin(rad(2 * geom_mean_anom_sun)) * (0.019993 - 0.000101 * jc)
        + math.sin(rad(3 * geom_mean_anom_sun)) * 0.000289
    )
    sun_true_long = geom_mean_long_sun + sun_eq_of_ctr
    sun_app_long = sun_true_long - 0.00569 - 0.00478 * math.sin(rad(125.04 - 1934.136 * jc))
    mean_obliq_ecliptic = 23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60
    obliq_corr = mean_obliq_ecliptic + 0.00256 * math.cos(rad(125.04 - 1934.136 * jc))
    sun_declin = deg(math.asin(math.sin(rad(obliq_corr)) * math.sin(rad(sun_app_long))))

    y = math.tan(rad(obliq_corr / 2)) ** 2
    eq_of_time = deg(
        y * math.sin(2 * rad(geom_mean_long_sun))
        - 2 * eccent_earth_orbit * math.sin(rad(geom_mean_anom_sun))
        + 4 * eccent_earth_orbit * y * math.sin(rad(geom_mean_anom_sun)) * math.cos(2 * rad(geom_mean_long_sun))
        - 0.5 * y * y * math.sin(4 * rad(geom_mean_long_sun))
        - 1.25 * eccent_earth_orbit * eccent_earth_orbit * math.sin(2 * rad(geom_mean_anom_sun))
    ) * 4

    time_utc_min = when.hour * 60 + when.minute + (when.second + when.microsecond / 1e6) / 60
    true_solar_time = (time_utc_min + eq_of_time + 4 * lon + 1440) % 1440
    hour_angle = true_solar_time / 4 - 180
    if hour_angle < -180:
        hour_angle += 360

    solar_zenith = deg(math.acos(
        math.sin(rad(lat)) * math.sin(rad(sun_declin))
        + math.cos(rad(lat)) * math.cos(rad(sun_declin)) * math.cos(rad(hour_angle))
    ))

    azimuth_denom = math.cos(rad(lat)) * math.sin(rad(solar_zenith))
    if abs(azimuth_denom) > 0.001:
        arg = (math.sin(rad(lat)) * math.cos(rad(solar_zenith)) - math.sin(rad(sun_declin))) / azimuth_denom
        azimuth = 180 - deg(math.acos(max(-1.0, min(1.0, arg))))
        if hour_angle > 0:
            azimuth = -azimuth
    else:
        azimuth = 180 if lat > 0 else 0
    return (azimuth + 360) % 360


def destination_point(lat: float, lon: float, bearing_deg: float, distance_km: float) -> tuple[float, float]:
    """Great-circle destination (lat, lon) from a start point, bearing and distance."""
    bearing = math.radians(bearing_deg)
    lat1, lon1 = math.radians(lat), math.radians(lon)
    ang_dist = distance_km / EARTH_RADIUS_KM
    lat2 = math.asin(
        math.sin(lat1) * math.cos(ang_dist) + math.cos(lat1) * math.sin(ang_dist) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(ang_dist) * math.cos(lat1),
        math.cos(ang_dist) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), ((math.degrees(lon2) + 540) % 360) - 180
