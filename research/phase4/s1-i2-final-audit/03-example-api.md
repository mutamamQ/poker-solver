# A203 canonical-example and strict-v4 audit — parent-normalized

Verdict: PASS.

The fresh non-author A203 reviewer executed all 20 example/CLI/export integration tests in 19.52s and inspected the frozen strict-v4 dispatcher and example.

Verified

- The example is a direct `{version, operation, payload}` strict-v4 request with bounded nodes/depth, complete two-card runouts, one combo per player, vanilla CFR and no seed.
- Production dispatch returns exact v4/game/starting-street/continuation identity, finite zero-sum values, normalized policies and truthful bounded provenance.
- Repeated direct dispatch is exactly deterministic and serializes with `allow_nan=False`.
- CLI file/stdin/error behavior and both deterministic algorithms pass their permanent tests.
- The exact five package exports and deep-copy-isolated v3 capability feature pass.

Broader strict-schema rejection is grounded in the already frozen `tests/test_api_v4.py` S1-I1 contract, not inferred from these 20 tests alone. All eight S1-I2 hashes remained unchanged. No candidate defect was found.
