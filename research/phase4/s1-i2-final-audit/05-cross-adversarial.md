# A205 cross-adversarial audit — parent-normalized

Verdict: PASS.

The fresh non-author A205 reviewer ran all 25 permanent S1-I2 tests twice: 25/25 passed in 45.26s and 23.19s.

Verified attack surfaces

- structural oracle uses manual terminal enumeration and does not consume automatic solve output;
- strategic oracle uses independent manual backward induction and a separate test-only GameState;
- every measured automatic/explicit root gap obeys `NC_auto + NC_explicit + 1e-12`;
- the convergence sweep proves first-to-last improvement (it does not claim strict monotonicity at every intermediate point);
- example and fixtures are valid and production-importing;
- CLI error paths, file/stdin handling and deterministic output have unconditional assertions;
- v3 capability results are recursively isolated by deep copy;
- package exports are identity checks, not wrappers;
- values are finite/zero-sum, policies normalized, and provenance does not overclaim convergence or unrestricted scope.

All eight frozen hashes remained unchanged. No blocker, major or minor candidate defect was reproduced.
