import pytest

from conftest import replay_fetch
from sunset.cli import format_pinpoint
from sunset.models import MissingDataError
from sunset.pinpoint import pinpoint
from sunset.sources.openmeteo import OpenMeteo

CASES = [
    ("vancouver", 49.2827, -123.1207, 6),
    ("squamish", 49.7016, -123.1558, 0),
]


@pytest.mark.parametrize("place,lat,lon,score", CASES)
def test_pinpoint_reproduces_the_recorded_js_run_exactly(fixtures_dir, place, lat, lon, score):
    source = OpenMeteo(replay_fetch(f"openmeteo_{place}_2026-10-26.json"))
    p = pinpoint(lat, lon, "2026-10-26", source)
    assert p.result.score == score
    expected = (fixtures_dir / f"expected_pinpoint_{place}_2026-10-26.txt").read_text()
    assert format_pinpoint(p) + "\n" == expected


def test_squamish_is_blocked_by_terrain_and_upwind_cloud():
    source = OpenMeteo(replay_fetch("openmeteo_squamish_2026-10-26.json"))
    p = pinpoint(49.7016, -123.1558, "2026-10-26", source)
    assert p.observation.cloud_low_upwind == 100
    assert p.terrain.terrain_block_deg > 13


def test_missing_air_quality_fails_loudly_instead_of_nan():
    def drop_aod(url, body):
        if "air-quality" in url:
            body["hourly"]["aerosol_optical_depth"] = [None] * len(body["hourly"]["time"])
    source = OpenMeteo(replay_fetch("openmeteo_vancouver_2026-10-26.json", drop_aod))
    with pytest.raises(MissingDataError, match="aod"):
        pinpoint(49.2827, -123.1207, "2026-10-26", source)


def test_missing_upwind_cloud_fails_loudly():
    def drop_low_cloud(url, body):
        if "cloud_cover_low" in url and "48.5" in url:
            body["hourly"]["cloud_cover_low"] = [None] * len(body["hourly"]["time"])
    source = OpenMeteo(replay_fetch("openmeteo_vancouver_2026-10-26.json", drop_low_cloud))
    with pytest.raises(MissingDataError, match="cloud_low_upwind"):
        pinpoint(49.2827, -123.1207, "2026-10-26", source)
