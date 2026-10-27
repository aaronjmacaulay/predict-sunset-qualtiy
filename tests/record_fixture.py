"""
Record a live pinpoint run as a test fixture (needs network).

  uv run python tests/record_fixture.py <name> <lat> <lon> <YYYY-MM-DD>

Writes tests/fixtures/openmeteo_<name>_<date>.json (every request, including
error responses) and expected_pinpoint_<name>_<date>.txt (the CLI output).
Not a test itself: pytest only collects test_*.py files.
"""

import json
import sys
from pathlib import Path

from sunset.cli import format_pinpoint
from sunset.pinpoint import pinpoint
from sunset.sources.openmeteo import ApiError, OpenMeteo, http_get_json

FIXTURES = Path(__file__).parent / "fixtures"


def main(name, lat, lon, date):
    recorded = {}

    def recording_fetch(url):
        try:
            recorded[url] = body = http_get_json(url)
            return body
        except ApiError as err:
            recorded[url] = {"_error": {"status": err.status, "reason": err.reason}}
            raise

    result = pinpoint(float(lat), float(lon), date, OpenMeteo(recording_fetch))
    (FIXTURES / f"openmeteo_{name}_{date}.json").write_text(json.dumps(recorded, indent=1) + "\n")
    (FIXTURES / f"expected_pinpoint_{name}_{date}.txt").write_text(format_pinpoint(result) + "\n")
    print(format_pinpoint(result))


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
