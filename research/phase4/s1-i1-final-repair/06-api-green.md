# R06 strict-v4 GREEN evidence

Status: GREEN_READY

R05's permanent production-importing regression `test_float_envelope_version_rejected` established the intended RED: envelope version `4.0` was accepted because Python compares it equal to integer `4`. Parent reproduced that RED before the source edit.

R06 minimally repaired `src/poker_solver/api_v4.py` by requiring the envelope version value to be an actual `int` (while continuing to reject `bool`) and equal to 4.

R06 receipt:

- `uv run pytest tests/test_api_v4.py -q`
- 36 passed

Parent integrated GREEN receipt:

- `uv run pytest tests/test_allstreet_config.py tests/test_bounded_tree.py tests/test_api_v4.py -q`
- 116 passed in 2.31s

Full regression receipt:

- `uv run pytest -q`
- 531 passed in 199.21s
