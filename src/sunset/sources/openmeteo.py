"""
openmeteo.py — Open-Meteo forecast, air-quality and elevation APIs.

Free and keyless, consistent with the rest of the project. All requests go
through one `fetch_json(url)` function, injectable so tests can replay
recorded responses (tests/fixtures/) instead of hitting the network.

Weather for dates older than the forecast API's window (about the last three
months) comes from the Historical Forecast API instead: same parameters, an
archive of past forecasts. The switch happens when the forecast API answers
"out of allowed range", so recorded test fixtures never go stale.

Hourly values are taken at the bucket nearest the sunset time (not
interpolated; see NEXT-STEPS D2). Missing values come back as None and are
rejected by models.Observation, not turned into NaN.
"""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"

FetchJson = Callable[[str], dict]


class ApiError(RuntimeError):
    """An HTTP error from Open-Meteo, with the reason it gave (if any)."""

    def __init__(self, url: str, status: int, reason: str = ""):
        super().__init__(f"{url} -> HTTP {status}" + (f": {reason}" if reason else ""))
        self.status, self.reason = status, reason


def http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "sunset-predictor"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as err:
        try:
            reason = json.load(err).get("reason", "")
        except (ValueError, AttributeError):
            reason = ""
        raise ApiError(url, err.code, reason) from err


@dataclass(frozen=True)
class SunsetTime:
    local_iso: str         # e.g. "2026-10-26T18:00", in the location's timezone
    timezone: str          # e.g. "America/Vancouver"
    utc: datetime          # the same instant, timezone-aware UTC


def _to_utc(local_iso: str, tz_name: str, utc_offset_seconds: int) -> datetime:
    local = datetime.fromisoformat(local_iso)
    try:
        return local.replace(tzinfo=ZoneInfo(tz_name)).astimezone(timezone.utc)
    except ZoneInfoNotFoundError:
        # No tz database (e.g. Windows without tzdata): use the offset
        # Open-Meteo reports, which is right except across a DST change.
        return (local - timedelta(seconds=utc_offset_seconds)).replace(tzinfo=timezone.utc)


def _nearest_hour_index(times: list[str], target_iso: str) -> int:
    target = datetime.fromisoformat(target_iso)
    return min(range(len(times)), key=lambda i: abs(datetime.fromisoformat(times[i]) - target))


class OpenMeteo:
    def __init__(self, fetch_json: FetchJson = http_get_json):
        self.fetch_json = fetch_json
        self._historical_dates: set[str] = set()

    def _weather(self, date: str, query: str) -> dict:
        """Forecast API, or the historical archive once a date is out of range."""
        if date not in self._historical_dates:
            try:
                return self.fetch_json(f"{WEATHER_URL}?{query}")
            except ApiError as err:
                if err.status != 400 or "out of allowed range" not in err.reason:
                    raise
                self._historical_dates.add(date)
        return self.fetch_json(f"{HISTORICAL_URL}?{query}")

    def local_today(self, lat: float, lon: float) -> str:
        """Today's date in the OBSERVER'S timezone, not the caller's.

        e.g. 00:17 UTC is still 5:17 pm the previous day in Vancouver; using
        the machine's UTC date would silently score tomorrow's sunset.
        """
        j = self.fetch_json(f"{WEATHER_URL}?latitude={lat}&longitude={lon}"
                            f"&daily=sunset&timezone=auto&forecast_days=1")
        return j["daily"]["time"][0]

    def sunset(self, lat: float, lon: float, date: str) -> SunsetTime:
        j = self._weather(date, f"latitude={lat}&longitude={lon}&daily=sunset&timezone=auto"
                                f"&start_date={date}&end_date={date}")
        sunsets = (j.get("daily") or {}).get("sunset") or [None]
        if not sunsets[0]:
            raise RuntimeError(f"No sunset time returned for {date} at ({lat}, {lon})")
        return SunsetTime(sunsets[0], j["timezone"], _to_utc(sunsets[0], j["timezone"], j["utc_offset_seconds"]))

    def spot_weather(self, lat: float, lon: float, date: str, at_local_iso: str) -> dict:
        j = self._weather(date, f"latitude={lat}&longitude={lon}&timezone=auto"
                                f"&hourly=cloud_cover_high,cloud_cover_mid,relative_humidity_2m,visibility,"
                                f"boundary_layer_height&start_date={date}&end_date={date}")
        h = j["hourly"]
        i = _nearest_hour_index(h["time"], at_local_iso)
        return {
            "hour": h["time"][i],
            "cloud_high": h["cloud_cover_high"][i],
            "cloud_mid": h["cloud_cover_mid"][i],
            "rh_2m": h["relative_humidity_2m"][i],
            "visibility_m": h["visibility"][i],
            "pbl_height_m": h["boundary_layer_height"][i],
        }

    def low_cloud(self, lat: float, lon: float, date: str, at_local_iso: str) -> float | None:
        j = self._weather(date, f"latitude={lat}&longitude={lon}&timezone=auto"
                                f"&hourly=cloud_cover_low&start_date={date}&end_date={date}")
        h = j["hourly"]
        return h["cloud_cover_low"][_nearest_hour_index(h["time"], at_local_iso)]

    def air_quality(self, lat: float, lon: float, date: str, at_local_iso: str) -> dict:
        j = self.fetch_json(f"{AQ_URL}?latitude={lat}&longitude={lon}&timezone=auto"
                            f"&hourly=aerosol_optical_depth,pm2_5&start_date={date}&end_date={date}")
        h = j["hourly"]
        i = _nearest_hour_index(h["time"], at_local_iso)
        return {"aod": h["aerosol_optical_depth"][i], "pm25": h["pm2_5"][i]}

    def elevations(self, points: list[tuple[float, float]]) -> list[float]:
        """Elevation (m, Copernicus DEM ~90 m) for each (lat, lon), in one batch call."""
        lats = ",".join(f"{lat:.5f}" for lat, _ in points)
        lons = ",".join(f"{lon:.5f}" for _, lon in points)
        return self.fetch_json(f"{ELEVATION_URL}?latitude={lats}&longitude={lons}")["elevation"]
