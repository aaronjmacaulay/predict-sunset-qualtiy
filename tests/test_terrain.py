import json

import pytest

from sunset import terrain

N_POINTS = 1 + len(terrain.BEARING_OFFSETS_DEG) * len(terrain.DISTANCES_KM)


def test_elevation_angle_matches_js_reference(fixtures_dir):
    ref = json.loads((fixtures_dir / "js_reference_geo.json").read_text())
    for c in ref["elevation_angle"]:
        assert terrain.elevation_angle_deg(c["observer_m"], c["target_m"], c["km"]) == pytest.approx(c["deg"], abs=1e-9)


def test_terrain_below_the_horizon_blocks_nothing():
    assert terrain.elevation_angle_deg(1000, 900, 2) == 0.0


def test_profile_points_start_with_the_observer():
    points = terrain.profile_points(49.28, -123.12, 251.1)
    assert len(points) == N_POINTS
    assert points[0] == (49.28, -123.12)


def test_flat_terrain_gives_zero_block():
    result = terrain.horizon_profile(251.1, [0.0] * N_POINTS)
    assert result.terrain_block_deg == 0.0
    assert [round(b.bearing, 1) for b in result.bearings] == [236.1, 243.6, 251.1, 258.6, 266.1]


def test_a_single_ridge_sets_the_block_for_its_bearing():
    elevations = [0.0] * N_POINTS
    # bearing index 2 (straight at the sun), distance index 3 (5 km)
    elevations[1 + 2 * len(terrain.DISTANCES_KM) + 3] = 500.0
    result = terrain.horizon_profile(251.1, elevations)
    assert result.terrain_block_deg == pytest.approx(terrain.elevation_angle_deg(0, 500, 5))
    assert [b.block_deg > 0 for b in result.bearings] == [False, False, True, False, False]


def test_wrong_number_of_elevations_is_an_error():
    with pytest.raises(ValueError):
        terrain.horizon_profile(251.1, [0.0] * 10)
