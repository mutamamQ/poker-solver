# R01 all-street RED evidence

Status: RED_READY (parent-recovered after worker transport/stale-summary failure)

Permanent regressions in `tests/test_allstreet_config.py` import production `poker_solver.allstreet` and cover:

- list input copied to tuple for `starting_board`, both combo ranges, nested `allowed_runouts`, and `wager_targets`;
- caller mutation cannot change the stored configuration;
- nested result metadata mappings/lists are defensively detached and recursively immutable.

Parent RED receipt before production repair:

- `uv run pytest tests/test_allstreet_config.py -q`
- 5 failed, 43 passed
- Failures were the four missing config conversions and nested metadata alias leak.

Chronology: R01 wrote the four config tests before the production edit but failed to complete its report. Parent inspected those tests, ran the intended RED, added the missing nested-metadata test, reran the intended five-test RED, then released production ownership.
