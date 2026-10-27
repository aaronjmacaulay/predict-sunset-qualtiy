import copy
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _parse(url):
    parts = urlsplit(url)
    return f"{parts.netloc}{parts.path}", dict(parse_qsl(parts.query))


def _coords_match(a: str, b: str) -> bool:
    xs, ys = a.split(","), b.split(",")
    return len(xs) == len(ys) and all(abs(float(x) - float(y)) < 1e-6 for x, y in zip(xs, ys))


def replay_fetch(name: str, overrides=None):
    """A fetch_json that answers from a recorded fixture instead of the network.

    Coordinates are matched with a small tolerance, since JS and Python may
    differ in the last digit of a computed upwind point. `overrides(url, body)`
    can mutate a response, e.g. to simulate a missing value.
    """
    recorded = [(*_parse(url), body) for url, body in json.loads((FIXTURES / name).read_text()).items()]

    def fetch(url):
        base, params = _parse(url)
        for r_base, r_params, body in recorded:
            if r_base != base or r_params.keys() != params.keys():
                continue
            if all(_coords_match(params[k], r_params[k]) if k in ("latitude", "longitude")
                   else params[k] == r_params[k] for k in params):
                body = copy.deepcopy(body)
                if overrides:
                    overrides(url, body)
                return body
        raise AssertionError(f"no recorded response for {url}")

    return fetch


@pytest.fixture
def fixtures_dir():
    return FIXTURES
