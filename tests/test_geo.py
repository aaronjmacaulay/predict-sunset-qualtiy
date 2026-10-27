import json
from datetime import datetime, timezone

import pytest

from sunset import geo


@pytest.fixture
def ref(fixtures_dir):
    return json.loads((fixtures_dir / "js_reference_geo.json").read_text())


def test_solar_azimuth_matches_js_reference(ref):
    for case in ref["azimuth"]:
        when = datetime.fromisoformat(case["iso"].replace("Z", "+00:00"))
        assert geo.solar_azimuth(when, case["lat"], case["lon"]) == pytest.approx(case["deg"], abs=1e-6)


def test_solar_azimuth_equinox_sunset_at_equator_is_due_west():
    assert geo.solar_azimuth(datetime(2026, 3, 20, 18, tzinfo=timezone.utc), 0, 0) == pytest.approx(270, abs=0.5)


def test_solar_azimuth_rejects_naive_datetime():
    # A naive time is what caused the JS bug (ARCHITECTURE.md S10).
    with pytest.raises(ValueError):
        geo.solar_azimuth(datetime(2026, 10, 26, 18, 0), 49.28, -123.12)


def test_destination_point_matches_js_reference(ref):
    for case in ref["destination"]:
        lat, lon = geo.destination_point(case["lat"], case["lon"], case["bearing"], case["km"])
        assert lat == pytest.approx(case["result"]["lat"], abs=1e-9)
        assert lon == pytest.approx(case["result"]["lon"], abs=1e-9)


def test_destination_point_wraps_across_the_antimeridian():
    _, lon = geo.destination_point(10, 179.9, 90, 50)
    assert -180 <= lon < -179
