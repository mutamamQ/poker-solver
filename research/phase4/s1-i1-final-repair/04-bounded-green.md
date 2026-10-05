# R04 bounded-tree GREEN evidence

Status: GREEN_READY (parent recovery)

R04 correctly made no source edit because its prerequisite RED marker did not yet exist. After parent-recovered RED, the parent added narrow exception boundaries in `src/poker_solver/bounded_tree.py` for the four uncovered callback paths. Each preserves the callback text, raises the documented `ValueError`, and chains the original exception.

Parent GREEN receipt:

- `uv run pytest tests/test_allstreet_config.py tests/test_bounded_tree.py tests/test_api_v4.py -q`
- 116 passed in 2.31s

Full regression receipt:

- `uv run pytest -q`
- 531 passed in 199.21s
