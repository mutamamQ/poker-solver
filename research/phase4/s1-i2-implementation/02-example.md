# I202 canonical S1 example — parent final evidence

Status: GREEN_READY.

Artifacts

- `examples/phase4_s1_flop.json`
- `tests/test_phase4_s1_example.py`

The example is a direct strict-v4 `solve-allstreet-postflop` request with integer card IDs, one combo per player, two complete runouts, explicit node/depth limits, vanilla CFR, no seed, and 10 iterations. It contains no pre-solved response or wrapper-only fields.

After I202 ownership cleared, the parent reduced redundant repeated solves while preserving all behavioral checks. The module now performs four production-importing tests with a module-scoped result and one independent repeat:

- exact request schema and bounded synthetic shape;
- unchanged `dispatch_v4` execution, truthful provenance, finite zero-sum values;
- nonempty finite normalized strategy;
- exact determinism and strict JSON serialization.

The same file is executed through the real additive CLI by `tests/test_phase4_s1_cli.py::test_phase4_canonical_example_executes`.

Parent GREEN receipts

- example plus CLI: `14 passed in 4.28s`;
- 11-module S1 integration gate: `178 passed in 16.32s`;
- full repository: `556 passed in 324.87s`.
