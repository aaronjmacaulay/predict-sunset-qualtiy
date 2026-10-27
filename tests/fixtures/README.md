# Test fixtures

Recorded API responses and expected outputs, so the tests run offline. The
`2026-10-26` files were recorded from the last JavaScript version, just
before the Python migration, and pin the Python to the JS behaviour. Newer
files are recorded from the Python with:

    uv run python tests/record_fixture.py <name> <lat> <lon> <YYYY-MM-DD>

| File | What |
|---|---|
| `openmeteo_<place>_<date>.json` | Every Open-Meteo request made by one `pinpoint` run, as `{url: response}`. Replayed by `conftest.replay_fetch`. |
| `expected_pinpoint_<place>_<date>.txt` | The CLI output for that run (from the JS for the 2026-10-26 files). The Python CLI output must match it exactly. |
| `expected_scenarios.txt` | Worked example + 9 scenarios (identical in the original Python and the JS). |
| `expected_label_analysis.txt` | Output of the JS rating-label analysis. |
| `js_reference_geo.json` | Solar azimuth, destination points and elevation angles computed by the JS. |

Places: Vancouver 2026-07-22, older than the forecast API's window, so it
exercises the historical-archive fallback (the first request is a recorded
"out of allowed range" error), score 4; Vancouver (49.2827, -123.1207)
2026-10-26, flat horizon, score 6; Squamish
(49.7016, -123.1558), mountains to the west (terrain block 13.5 deg) and 100%
upwind low cloud, score 0.

The `expected_*` files are a regression lock. If you deliberately change
scoring or output, regenerate them and say why in the commit message.
