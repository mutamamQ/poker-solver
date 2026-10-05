# I206 parent-only shared integration contract — parent recovery

Status: READY after interrupted retry ownership cleared.

The retry inspected the correct source surfaces and derived the CLI and five package exports, but repeatedly rewrote its report and reintroduced the rejected invented `poker_solver.get_capabilities` API. This recovered contract removes that invention.

Minimal production patch

1. `src/poker_solver/cli.py`
   - import `dispatch_v4`;
   - register additive `phase4 REQUEST [--json]` beside `phase3`;
   - route the loaded direct request through `dispatch_v4` and existing `_emit`;
   - reuse existing file/stdin loading and `ValueError`/`OSError`/JSON error handling.

2. `src/poker_solver/__init__.py`
   - re-export exactly the five agreed public symbols:
     `AllStreetPostflopConfig`, `AllStreetSolveResult`, `create_allstreet_root`, `solve_allstreet_postflop`, and `dispatch_v4`.

3. `src/poker_solver/api_v3.py`
   - add truthful feature `allstreet-postflop` to the existing `_FEATURES` manifest with status `implemented-bounded`, starting street `flop`, continuation `automatic-natural-terminal`, and interfaces `typed`, `json-v4`, `cli-phase4`;
   - retain the existing `dispatch_v3` `capabilities` deep-copy boundary.

No `get_capabilities` function is required or permitted by the agreed S1-I2 package-export list. Existing v1/v2/v3 command paths remain unchanged.

Required GREEN gates

- `tests/test_phase4_s1_cli.py`
- `tests/test_phase4_s1_exports.py`
- `tests/test_phase4_s1_example.py`
- `tests/test_allstreet_oracle.py`
- existing CLI, v3 API, v4 API, and all-street suites
- full regression before candidate freeze
