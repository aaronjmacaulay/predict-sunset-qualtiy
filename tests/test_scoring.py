"""
Regression lock for the scoring model.

Freezes the known-correct scores for the documented scenarios (the original
Python worked examples, matched exactly by the JS port), so any change -
intentional calibration or accidental breakage - shows up here instead of
silently changing scores. A failure after a deliberate tuning change is
expected: update the expected value AND say why in the same commit.
"""

import math

import pytest

from sunset import scoring
from sunset.models import MissingDataError, Observation

EXPECTED_SCORES = {
    "Post-frontal classic": 90,
    "Marine layer (coastal summer)": 4,
    "Wildfire smoke, moderate": 30,
    "Wildfire smoke, heavy": 3,
    "Pair A: clear to the west": 72,
    "Pair B: same sky, deck 120km west": 26,
    "Bluebird clear sky": 25,
    "Solid overcast": 0,
    "Ideal sky, but ridge to the west": 24,
}


@pytest.mark.parametrize("name,expected", EXPECTED_SCORES.items())
def test_documented_scenarios_score_as_expected(name, expected):
    assert scoring.score(scoring.SCENARIOS[name]).score == expected


def test_every_scenario_has_an_expected_value():
    assert set(scoring.SCENARIOS) == set(EXPECTED_SCORES)


def test_result_carries_the_terms_and_their_product():
    r = scoring.score(scoring.SCENARIOS["Post-frontal classic"])
    assert r.raw == pytest.approx(r.gate * r.canvas * r.clarity * r.aerosol)
    assert r.gate == pytest.approx(r.path * r.terrain)
    assert r.aerosol == pytest.approx(r.boost * r.overload * r.pm_pen)
    assert r.label == "exceptional"


def test_pair_a_vs_b_shows_upwind_sampling_matters():
    a = scoring.score(scoring.SCENARIOS["Pair A: clear to the west"])
    b = scoring.score(scoring.SCENARIOS["Pair B: same sky, deck 120km west"])
    assert a.canvas == b.canvas and a.score > b.score


@pytest.mark.parametrize("s,label", [(75, "exceptional"), (74, "very good"), (55, "very good"),
                                     (35, "decent"), (18, "mediocre"), (17, "poor"), (0, "poor")])
def test_label_thresholds(s, label):
    assert scoring.label(s) == label


@pytest.mark.parametrize("bad", [None, math.nan, math.inf, "12", True])
def test_observation_rejects_missing_or_non_numeric_values(bad):
    fields = dict(vars(scoring.SCENARIOS["Post-frontal classic"]))
    fields["aod"] = bad
    with pytest.raises(MissingDataError, match="aod"):
        Observation(**fields)
