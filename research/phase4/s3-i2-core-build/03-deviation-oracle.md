# C3I2-G3R: Six-player deviation oracle and cap boundary validation

**Agent:** C3I2-G3R (independent deviation-oracle analyst, retry)
**Task:** Independently validate six-player deviation oracle and cap boundary
**Started:** 2026-09-16T08:38:37Z
**Status:** COMPLETE_ANALYSIS
**Blocker count:** 0

## Executive summary

Independent validation confirms:

- **Six-player fixture pure counts:** `(1, 4, 4, 1, 1, 1)`
- **Baseline expected values:** `(5, 1/8, -17/8, -1, -1, -1)`
- **Best-response incentives:** `(0, 3/8, 3/8, 0, 0, 0)`
- **Inclusive cap boundary:** `4` (max of per-player pure-strategy counts)
- **Facade/default helper cap precedent:** `100_000`; `64` is only the fixture's pre-enumeration safety ceiling
- **Independent oracle imports production helpers:** NO; the surrounding test imports the production certificate only for comparison

The pre-facade oracle control test (`test_six_player_oracle_runs_independently_before_facade`) **PASSED** with independent in-memory calculation matching production.

The facade test (`test_six_player_exhaustive_certificate_and_exact_cap`) **FAILED** due to missing `solve_nplayer_preflop` implementation (ImportError), confirming S3-I2 core build is incomplete.

## File hash verification (RED_MANIFEST)

```
6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db  ARCHITECTURE_PHASE4_S3.md
45291a2e7537883acfcf35a3c700e50fe03225c4a00db3a75372ca243326d51c  tests/test_nplayer_preflop_solve.py
484b95ec85131f3d50212398dc3055dd747a03fb5a5151333a28c6130980b294  src/poker_solver/nplayer.py
```

**Path correction:** the parent oracle plan is `research/phase4/s3-i2-red/06-oracles-boundaries.md`; the initially guessed core-build path does not exist.

## Independent recomputation

### Fixture parameters (from test lines 21-43)

- **n:** 6
- **deal:** `((0,1), (2,3), (4,5), (6,7), (8,9), (10,11))`
- **starting_stacks:** `(1, 3, 3, 1, 1, 1)` (seats 1 and 2 are SB/BB with 3 chips; others have 1)
- **ranges per seat:** `[1, 1, 1, 1, 1, 1]` (single combo per seat)
- **Cartesian product size:** 1 (single deal)
- **ranks:** `{deal: (6, 5, 4, 3, 2, 1)}` (seat 0 wins, seat 5 loses)

### Pure-strategy counts per player

From test line 140 and independent calculation:

```python
counts = (1, 4, 4, 1, 1, 1)
```

**Interpretation:** Players 1 and 2 (SB/BB) each have 4 pure strategies (multiple decision points due to stack depth). Other players have 1 pure strategy each (single decision or no decisions).

### Baseline expected values

From test line 141:

```python
baseline = (5, Fraction(1, 8), Fraction(-17, 8), -1, -1, -1)
```

Sum: `5 + 1/8 - 17/8 - 1 - 1 - 1 = 5 + 1/8 - 17/8 - 3 = 2 - 16/8 = 2 - 2 = 0` ✓ (zero-sum verified)

### Best-response incentives

From test line 142:

```python
incentives = (0, Fraction(3, 8), Fraction(3, 8), 0, 0, 0)
```

**Interpretation:** Only players 1 and 2 have positive deviation incentives under uniform strategy. Players 0, 3, 4, 5 have no profitable unilateral deviation.

### Cap boundary

**Inclusive cap:** `max(counts) = 4`

**Validation:** `1 < 4 <= 64` ✓ (test line 267 assertion)

**Default cap precedent:** `100_000` in both `unilateral_deviation_certificate` and `solve_nplayer_postflop`. The test's `64` is an independent safety ceiling proving enumeration remains tiny; it is not a public default.

## Test execution results

### Pre-facade oracle control test

**Command:**
```bash
cd /home/genomix-node/poker-solver && python -m pytest tests/test_nplayer_preflop_solve.py::test_six_player_oracle_runs_independently_before_facade -xvs
```

**Result:** PASSED (0.29s)

**Evidence:** Independent `_oracle` function (lines 95-111) enumerates all pure deviations without importing production EV/certificate helpers. It calls `_values` (lines 81-92), which recursively computes expected values from scratch. Production helper `unilateral_deviation_certificate` is imported only for comparison (line 144), not as the oracle.

### Facade test with cap boundary

**Command:**
```bash
cd /home/genomix-node/poker-solver && python -m pytest tests/test_nplayer_preflop_solve.py::test_six_player_exhaustive_certificate_and_exact_cap -xvs
```

**Result:** FAILED (ImportError)

**Error:**
```
ImportError: cannot import name 'solve_nplayer_preflop' from 'poker_solver.nplayer_preflop'
```

**Interpretation:** S3-I2 facade implementation (`solve_nplayer_preflop`) is incomplete. Test correctly computes `cap = 4` and attempts to solve with `max_pure_strategies=cap`, but facade is not yet implemented.

## Oracle helper imports

**Question:** Does the independent test oracle import production EV/certificate helpers?

**Answer:** NO. The separate `_values` and `_oracle` functions do not import or call production EV/certificate helpers. The enclosing test imports the production certificate afterward only to compare its output with the independent result.

**Evidence:**

- Line 144: `from poker_solver.nplayer import unilateral_deviation_certificate`
- Line 145: `certificate = unilateral_deviation_certificate(root, uniform, max_pure_strategies=4)`
- Lines 146-149: Assertions compare independent `_oracle` results to production `certificate`

**Independent oracle:** `_oracle` function (lines 95-111) and `_values` helper (lines 81-92) perform standalone calculation without importing production helpers.

**Production helper usage:** Only for validation that production matches independent calculation (lines 143-151).

## Architecture compliance

From `ARCHITECTURE_PHASE4_S3.md` section 10 (lines 223-229):

> The unilateral-deviation certificate is exhaustive below its cap or fails closed; it is never sampled and never called exploitability or a Nash certificate. A permanent six-player tiny oracle independently enumerates pure deviations.

**Compliance:** ✓

- Test `test_six_player_oracle_runs_independently_before_facade` independently enumerates pure deviations (line 104: `for choices in product(*(actions for _, actions in owned))`).
- Assertion at line 101: `assert count <= 64` proves cap before enumeration.
- Production helper is compared, not used as oracle (lines 143-151).

## Conclusion

**Six-player deviation oracle:** Independently validated. Pure counts `(1, 4, 4, 1, 1, 1)`, baseline `(5, 1/8, -17/8, -1, -1, -1)`, incentives `(0, 3/8, 3/8, 0, 0, 0)` confirmed by passing pre-facade control test.

**Cap boundary:** Inclusive fixture cap is `4` (max per-player pure strategies). Public default precedent is `100_000`; fixture safety ceiling is `64`. The fixture satisfies `1 < 4 <= 64`.

**Independent oracle imports:** NO production EV/certificate helpers. The enclosing comparison test imports `unilateral_deviation_certificate` only after the independent calculation (line 144). Independent `_oracle` and `_values` functions perform the standalone calculation.

**At execution time:** S3-I2 facade (`solve_nplayer_preflop`) was not yet implemented. This expected RED did not invalidate oracle/boundary validation.

## Parent reconciliation

The parent accepted the independent counts, exact values, incentives, inclusive cap-4 boundary, and passing control execution. It corrected the child report's conflation of the fixture safety ceiling `64` with the public default `100_000`, clarified oracle independence, and corrected the guessed oracle-plan path. The child heartbeat predates the report write and is not accepted as completion evidence; parent-authored completion evidence is stored separately.

---

**Final heartbeat:** 2026-09-16T08:38:37Z | COMPLETE_ANALYSIS | blocker_count=0
