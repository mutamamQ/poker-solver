# R03 bounded-tree RED evidence

Status: RED_READY (parent-recovered after worker no-execution output)

The child proposed the right four missing exception boundaries but did not write or execute the tests. After ownership cleared, the parent added one production-importing parametrized regression in `tests/test_bounded_tree.py` covering:

1. terminal `legal_actions()` failure;
2. terminal `chance_outcomes()` failure;
3. chance-node `legal_actions()` failure;
4. decision-node `chance_outcomes()` failure.

Each fixture raises `RuntimeError("callback explosion")`; the contract requires stable `ValueError("<callback>() failed: callback explosion")` normalization.

Parent RED receipt before production repair:

- `uv run pytest tests/test_bounded_tree.py -q`
- 4 failed, 28 passed
- all four failures leaked the raw `RuntimeError` from the intended callback path.
