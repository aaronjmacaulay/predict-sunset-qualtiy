# Test fixtures

Recorded on 2026-10-26 from the last JavaScript version of the predictor,
just before the Python migration. They let the tests run offline and pin the
Python to the JS behaviour.

| File | What |
|---|---|
| `openmeteo_<place>_<date>.json` | Every Open-Meteo request made by one `pinpoint` run, as `{url: response}`. Replayed by `conftest.replay_fetch`. |
| `expected_pinpoint_<place>_<date>.txt` | The JS `pinpoint.js` output for that run. The Python CLI output must match it exactly. |
| `expected_scenarios.txt` | Worked example + 9 scenarios (identical in the original Python and the JS). |
| `expected_label_analysis.txt` | Output of the JS rating-label analysis. |
| `js_reference_geo.json` | Solar azimuth, destination points and elevation angles computed by the JS. |

Places: Vancouver (49.2827, -123.1207), flat horizon, score 6; Squamish
(49.7016, -123.1558), mountains to the west (terrain block 13.5 deg) and 100%
upwind low cloud, score 0.

The `expected_*` files are a regression lock. If you deliberately change
scoring or output, regenerate them and say why in the commit message.
