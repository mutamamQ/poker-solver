# S1-I2 parent shared-integration GREEN

Status: GREEN_READY for candidate freeze.

Implemented only after all exclusive worker ownership cleared:

- `src/poker_solver/cli.py`: additive `phase4 REQUEST [--json]` using existing loader/emitter/error boundary and `dispatch_v4`;
- `src/poker_solver/__init__.py`: exactly five agreed all-street/v4 public exports;
- `src/poker_solver/api_v3.py`: truthful additive `allstreet-postflop` feature through the existing deep-copy-isolated v3 capabilities response;
- corrected permanent oracle, example, CLI, and exports/capability tests without introducing an unsupported explicit-continuation production field or invented `get_capabilities` API.

TDD chronology

- CLI RED: 9 failures from absent `phase4`; valid v3 control passed.
- Package/capability RED: 6 failures from five absent exports plus absent v3 feature.
- Production integration was then applied minimally.

Parent GREEN receipts

1. `tests/test_phase4_s1_exports.py` plus `tests/test_allstreet_oracle.py`: 11 passed.
2. Optimized canonical example plus real CLI: 14 passed in 4.28s.
3. S1-I2 plus existing S1/API/CLI integration gate: 178 passed in 16.32s.
4. Full repository regression: 556 passed in 324.87s.

The original Phase-3 baseline is a strict subset of the passing full suite. Tag `phase3-398-green` remains preserved.
