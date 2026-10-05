# G205 final solver and diagnostic audit — parent-normalized

Verdict: PASS.

The fresh recovery verified raw SHA-256 322ed04e and inspected the exact final architecture, `src/poker_solver/nplayer.py`, and `tests/test_nplayer.py`.

Verified specification surfaces:

- S2-I2 must add keyword-only `max_nodes` and `max_depth` constructor bounds and forward them to existing bounded collection while preserving defaults;
- existing counterfactual reach is reused, not duplicated;
- average strategy is copied into detached nested mappings with truthful bounded metadata;
- unilateral-deviation diagnostics remain exact exhaustive pure-deviation enumeration, fail closed on `max_pure_strategies`, and are never called convergence or sampled exploitability;
- deliberately tiny 4/5/9 fixtures can fit the explicit deal/node/depth caps, and the required five-player reach/deviation oracles are feasible.

The original report's illustrative `max_raises=0` example is excluded because the final config requires a positive value; fixtures can instead use all-in roots or one bounded raise without changing the conclusion.
