# A3I2-C1R: Strictness and Immutability Audit (Retry)

**Status**: PASS
**Auditor**: A3I2-C1R
**Completed**: 2026-09-16T09:14:45Z
**Candidate Manifest**: CANDIDATE_MANIFEST.md (frozen 2026-09-16T08:52:39Z)

## Manifest Integrity Verification

All 10 candidate files verified against frozen SHA-256 manifest:

```text
✓ 6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db  ARCHITECTURE_PHASE4_S3.md
✓ 484b95ec85131f3d50212398dc3055dd747a03fb5a5151333a28c6130980b294  src/poker_solver/nplayer.py
✓ 5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae  src/poker_solver/nplayer_preflop.py
✓ 45291a2e7537883acfcf35a3c700e50fe03225c4a00db3a75372ca243326d51c  tests/test_nplayer_preflop_solve.py
✓ bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268  tests/test_nplayer_preflop_config.py
✓ 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd  tests/test_nplayer_preflop_betting.py
✓ e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
✓ 1217cf74f1468252fbc7f941621dc57154c910003eb27fbf8947b7bc5a42e289  tests/test_nplayer_preflop_information.py
✓ 1826b203fe264acd159e5efb35d07a5122ddb12fb75c405078833733a7c3bcec  research/phase4/s3-i2-core-build/01-core-author.md
✓ a51dfcbc692fc434bbe5f485d526f83e411de6e837a4111d06a6c055822e7065  research/phase4/s3-i2-core-build/PARENT_CORE_GATE.md
```

**Result**: 10/10 files match frozen manifest exactly. Candidate integrity confirmed.

## Test Execution

**Command**:
```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_solve.py -k 'strict or immutable'
```

**Result**: 34 passed, 18 deselected in 0.67s

### Test Breakdown

**Strictness Tests (31 passed)**:
- `test_strict_algorithm`: 6 variants (unknown, cfr+, empty, None, True, 1) — all PASSED
- `test_strict_iterations`: 7 variants (0, -1, True, False, 1.5, 1, None) — all PASSED
- `test_strict_include_certificate`: 4 variants (0, 1, "true", None) — all PASSED
- `test_strict_pure_cap_even_when_not_requested`: 14 variants (False/True × 7 cap values) — all PASSED

**Immutability Tests (3 passed)**:
- `test_solve_deterministic_finite_immutable_result`: 3 variants (players=2, 6, 9) — all PASSED

**Total**: 34/34 permanent tests passed with no failures, no invented probes.

## Audit Findings

### Input Validation (Strictness)

1. **Algorithm parameter**: Correctly rejects invalid types (unknown, cfr+, empty string, None, True, 1) with clear `ValueError` messages
2. **Iterations parameter**: Correctly rejects non-positive integers (0, -1), non-integers (True, False, 1.5), and None
3. **Include certificate parameter**: Correctly rejects non-boolean types (0, 1, "true", None)
4. **Pure strategy cap**: Correctly validates even when `include_deviation_certificate=False`, preventing silent acceptance of invalid configuration

### Result Immutability

1. **Deterministic behavior**: Identical inputs produce identical results across multiple invocations (tested with 2, 6, 9 players)
2. **Result freezing**: Solve results are immutable — attempts to modify returned strategies, metadata, or certificates fail with appropriate errors
3. **Result truthfulness**: The explicit iteration field and convergence/determinism metadata accurately reflect the solve contract.

## Verdict

**PASS**: All 34 strictness and immutability tests passed. The frozen candidate demonstrates:
- Comprehensive input validation with clear error messages
- Deterministic, reproducible solve behavior
- Immutable result objects with truthful metadata
- No silent failures or configuration acceptance

**Blockers**: 0
**Audit completed**: 2026-09-16T09:14:45Z
