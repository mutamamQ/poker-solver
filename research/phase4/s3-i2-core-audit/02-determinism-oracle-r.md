# A3I2-C2 Core Audit: Determinism and Independent Oracle (Retry)

**Auditor**: A3I2-C2R (fresh non-author retry)
**Timestamp**: 2026-09-16T09:15:23Z
**Workspace**: /home/genomix-node/poker-solver
**Candidate Status**: FROZEN_PENDING_FULL_AND_FRESH_AUDIT

## Manifest Verification

All 10 candidate files verified against CANDIDATE_MANIFEST.md SHA-256 hashes:

```
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

**Manifest integrity**: PASS (10/10)

## Determinism Tests (N=2, 6, 9)

### Test: `test_solve_deterministic_finite_immutable_result`

**Command**:
```bash
python -m pytest tests/test_nplayer_preflop_solve.py::test_solve_deterministic_finite_immutable_result -v --tb=short
```

**Result**: 3 passed in 0.85s

**Verification**:
- ✓ Exact determinism: two independent solves produce identical strategy, expected_values, metadata
- ✓ Finite values: all expected_values are finite floats
- ✓ Zero-sum: sum(expected_values) ≈ 0 within 1e-12
- ✓ Normalized strategies: all probabilities in [0,1], sum to 1.0 within 1e-12
- ✓ Immutability: result objects frozen (FrozenInstanceError on mutation)
- ✓ Deep copy isolation: strategy and metadata detached from caller-owned sources

## Independent Oracle Verification (6-player)

### Test: `test_six_player_oracle_runs_independently_before_facade`

**Command**:
```bash
python -m pytest tests/test_nplayer_preflop_solve.py::test_six_player_oracle_runs_independently_before_facade -v --tb=short
```

**Result**: 1 passed in 0.10s

**Independent Oracle Implementation**:
- `_values(state, strategy)`: recursive full-tree expectation, no production helpers
- `_oracle(root, infosets, strategy)`: exhaustive pure-strategy enumeration
  - Enumerates all pure deviations per player (counts: 1, 4, 4, 1, 1, 1)
  - Computes best-response values independently
  - Calculates incentives as max(0, best - baseline)

**Verification**:
- ✓ Independent oracle runs without production EV/certificate logic
- ✓ Baseline values sum to zero
- ✓ Best-response values ≥ baseline values (monotonicity)
- ✓ Production `unilateral_deviation_certificate` matches independent oracle within 1e-12
- ✓ Pure-strategy bound enforcement: correctly rejects cap=3 (requires cap=4)

**Exact Values (uniform strategy)**:
```
baseline = (5, 1/8, -17/8, -1, -1, -1)
incentives = (0, 3/8, 3/8, 0, 0, 0)
counts = (1, 4, 4, 1, 1, 1)
```

### Test: `test_six_player_exhaustive_certificate_and_exact_cap`

**Command**:
```bash
python -m pytest tests/test_nplayer_preflop_solve.py::test_six_player_exhaustive_certificate_and_exact_cap -v --tb=short
```

**Result**: 1 passed in 0.32s

**Verification**:
- ✓ Exhaustive certificate with trained strategy matches independent `_oracle` within 1e-12
- ✓ Pure-strategy cap correctly enforced (cap=4 required, cap=3 rejected)
- ✓ Certificate provenance: "exhaustive finite pure unilateral deviations; diagnostic only"

## Full Test Suite

### Core Solve Tests (52 tests)

**Command**:
```bash
python -m pytest tests/test_nplayer_preflop_solve.py -v --tb=short
```

**Result**: 52 passed in 1.70s

### Supporting Core Tests (56 tests)

**Command**:
```bash
python -m pytest tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py -v --tb=short
```

**Result**: 56 passed in 0.15s

**Total permanent tests**: 108 passed (52 + 56)

## Final Verdict

**PASS**

### Summary

- ✓ All 10 manifest files verified (SHA-256 match)
- ✓ Determinism verified for N=2, 6, 9 (pytest permanent tests)
- ✓ Exact chance outcomes deterministic
- ✓ Finite normalized strategies (all probabilities in [0,1], sum to 1.0)
- ✓ Zero-sum verified (sum of expected values ≈ 0 within 1e-12)
- ✓ Independent `_values` oracle matches production within 1e-12
- ✓ Independent `_oracle` pure-deviation enumeration matches production certificate within 1e-12
- ✓ 108 permanent tests passed (52 solve + 56 supporting)
- ✓ No candidate edits made

### Audit Metadata

- **Auditor**: A3I2-C2R
- **Completion**: 2026-09-16T09:15:23Z
- **Heartbeat**: 1
- **Blocker count**: 0

---

**Audit complete. Candidate approved for next gate.**
