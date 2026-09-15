# R02 all-street GREEN evidence

Status: GREEN_READY (parent recovery)

R02 correctly made no source edit because its bounded wait ended before R01's RED marker. After all child ownership cleared, the parent retained the valid RED tests and applied the minimum production repair in `src/poker_solver/allstreet.py`:

- normalize all public sequence fields to detached tuples before validation;
- recursively detach/freeze metadata mappings and mutable collections.

Parent GREEN receipt:

- `uv run pytest tests/test_allstreet_config.py tests/test_bounded_tree.py tests/test_api_v4.py -q`
- 116 passed in 2.31s

Full regression receipt:

- `uv run pytest -q`
- 531 passed in 199.21s
