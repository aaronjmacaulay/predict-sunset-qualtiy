from datetime import datetime, timezone

import pytest

from conftest import replay_fetch
from sunset.sources.openmeteo import OpenMeteo, _nearest_hour_index

VAN = (49.2827, -123.1207)


@pytest.fixture
def source():
    return OpenMeteo(replay_fetch("openmeteo_vancouver_2026-10-26.json"))


def test_sunset_time_is_converted_using_the_locations_timezone(source):
    s = source.sunset(*VAN, "2026-10-26")
    assert s.local_iso == "2026-10-26T18:00"
    assert s.timezone == "America/Vancouver"
    # 18:00 PDT (UTC-7) -> 01:00 UTC next day, whatever the machine's timezone.
    assert s.utc == datetime(2026, 10, 27, 1, 0, tzinfo=timezone.utc)


def test_spot_weather_and_air_quality_use_the_nearest_hour(source):
    w = source.spot_weather(*VAN, "2026-10-26", "2026-10-26T18:00")
    assert w["hour"] == "2026-10-26T18:00"
    assert w["rh_2m"] == 84 and w["visibility_m"] == 17500
    aq = source.air_quality(*VAN, "2026-10-26", "2026-10-26T18:00")
    assert aq["aod"] == pytest.approx(0.1, abs=0.005)


def test_nearest_hour_index_picks_the_closest_bucket():
    times = ["2026-10-26T17:00", "2026-10-26T18:00", "2026-10-26T19:00"]
    assert _nearest_hour_index(times, "2026-10-26T18:29") == 1
    assert _nearest_hour_index(times, "2026-10-26T18:31") == 2


def test_missing_sunset_is_an_error():
    def drop_sunset(url, body):
        body["daily"]["sunset"] = [None]
    source = OpenMeteo(replay_fetch("openmeteo_vancouver_2026-10-26.json", drop_sunset))
    with pytest.raises(RuntimeError, match="No sunset time"):
        source.sunset(*VAN, "2026-10-26")
