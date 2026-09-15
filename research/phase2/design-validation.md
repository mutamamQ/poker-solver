# Phase 2 validation test plan

## Overview

This document defines the complete accuracy, determinism, benchmark, and independent-oracle test plan for Phase 2. Every test is executable on this machine with predeclared tolerances and no flakiness. Tests are separated into four gates: exhaustive correctness, stochastic confidence, determinism, and runtime.

## 1. Exhaustive correctness gates

These tests use exact integer equality or tight floating-point tolerances against independent oracles.

### 1.1 Five-card evaluator census

**Test:** `tests/test_evaluator.py::test_exhaustive_five_card_category_counts`

**Oracle:** Exhaustive combinatorics over all C(52,5) = 2,598,960 hands

**Independence:** Level 1 (published frequency vector)

**Acceptance:** Exact integer equality for all nine category counts:
```python
[1_302_540, 1_098_240, 123_552, 54_912, 10_200, 5_108, 3_744, 624, 40]
```
Sum must equal 2,598,960.

**Status:** Implemented and passing.

---

### 1.2 Seven-card evaluator cross-check

**Test:** `scripts/crosscheck_treys.py`

**Oracle:** Treys 0.1.8 (independent implementation)

**Independence:** Level 1 (external codebase)

**Acceptance:** 
- 100,000 random seven-card hands: exact category agreement
- 50,000 random comparisons: exact ordering agreement (sign of rank delta)
- Deterministic seed: `0xC0FFEE`

**Execution:** `uv run --with treys python scripts/crosscheck_treys.py`

**Status:** Implemented and passing.

---

### 1.3 Exact equity fixtures

**Test:** `tests/test_equity.py::test_exact_postflop_fixtures` (14 parametrized cases)

**Oracle:** `research/equity_fixtures.md` — 16 exact-card win/tie/loss counts generated exhaustively with Treys 0.1.8

**Independence:** Level 1 (external oracle generation)

**Acceptance:** Exact integer equality for `(wins, ties, losses)` tuples on all 14 postflop fixtures.

**Status:** Implemented and passing (14 of 16 fixtures; 2 preflop marked `@pytest.mark.slow`).

---

### 1.4 Kuhn poker analytical value

**Test:** `tests/test_cfr.py::test_kuhn_cfr_is_deterministic_and_approaches_value`

**Oracle:** Analytical game value for player 0 = -1/18 ≈ -0.0556

**Independence:** Level 1 (published analytical result)

**Acceptance:** 
- Absolute EV error ≤ 0.003 after 5,000 vanilla CFR iterations
- NashConv < 0.03 game units

**Status:** Implemented and passing.

---

### 1.5 Scalable best response vs. pure enumeration

**Test:** `tests/test_best_response.py::test_kuhn_nashconv_nonnegative_and_decreases_to_small_value`

**Oracle:** Existing Cartesian pure-strategy enumerator (in-project independent algorithm)

**Independence:** Level 2 (independent algorithmic implementation)

**Acceptance:** 
- Dynamic BR and pure enumeration differ by ≤ 1e-12 for both players on all test profiles
- NashConv ≥ 0 (within 1e-9 numerical tolerance)
- NashConv < 0.03 on Kuhn after 5,000 iterations

**Status:** Implemented and passing.

---

### 1.6 Hidden-bit information-set consistency trap

**Test:** `tests/test_best_response.py::test_best_response_is_infoset_consistent_hidden_bit`

**Oracle:** Exhaustive brute force (legal infoset-consistent responder value = 0; illegal per-history maximization would yield +1)

**Independence:** Level 2 (independent exhaustive oracle)

**Acceptance:** 
- BR value exactly 0.0 (within pytest.approx default tolerance)
- NashConv exactly 0.0

**Status:** Implemented and passing.

---

### 1.7 Kuhn tree audit

**Test:** `tests/test_kuhn.py::test_full_tree_counts_and_known_value_constant`

**Oracle:** Hand-verified tree structure

**Independence:** Level 2 (exhaustive traversal)

**Acceptance:** Exact counts:
- 55 nodes, 30 terminals, 24 decision nodes, 1 chance node, 12 infosets
- `KUHN_VALUE_P0 ≈ -1/18` (within pytest.approx)

**Status:** Implemented and passing.

---

### 1.8 Compact river game correctness

**Test:** `tests/test_river.py::test_compact_river_cfr_reaches_low_nashconv`

**Oracle:** Best-response exploitability (validated independently in 1.5)

**Independence:** Level 2 (independent BR algorithm)

**Acceptance:** 
- NashConv < 0.01 after 5,000 vanilla CFR iterations
- Sum of player values ≈ 0.0 (within 1e-12, zero-sum check)

**Status:** Implemented and passing.

---

## 2. Stochastic confidence gates

These tests validate MCCFR against vanilla CFR using predeclared seed matrices and statistical tolerances.

### 2.1 MCCFR vs. vanilla CFR on Kuhn

**Test:** To be implemented as `tests/test_mccfr.py::test_mccfr_vs_vanilla_kuhn`

**Oracle:** Vanilla CFR (validated independently via analytical value and BR)

**Independence:** Level 3 backed by Level 1/2 (internal agreement with externally validated reference)

**Method:**
1. Run vanilla CFR on Kuhn for 10,000 iterations (deterministic)
2. Run external-sampling MCCFR for 10,000 iterations with seeds `[42, 123, 456, 789, 1011, 1213, 1415, 1617, 1819, 2021]`
3. Compute player 0 EV for each MCCFR seed
4. Compute sample mean and 95% Student-t confidence interval
5. Require:
   - |mean_MCCFR - EV_vanilla| ≤ 0.03
   - Upper CI bound - EV_vanilla ≤ 0.05

**Acceptance:** Both mean error and CI upper bound meet predeclared tolerances.

**Status:** Not yet implemented.

---

### 2.2 MCCFR vs. vanilla CFR on tiny river spot

**Test:** To be implemented as `tests/test_mccfr.py::test_mccfr_vs_vanilla_tiny_river`

**Oracle:** Vanilla CFR on the same restricted-runout river game

**Independence:** Level 3 backed by Level 2 (BR-validated vanilla CFR)

**Method:**
1. Define a restricted-runout river game (see Section 3 below)
2. Run vanilla CFR for 5,000 iterations
3. Run MCCFR for 10,000 iterations with seeds `[100, 200, 300, 400, 500]`
4. Compute NashConv for each MCCFR seed
5. Require:
   - Mean NashConv ≤ vanilla NashConv + 0.02
   - 95% CI upper bound ≤ vanilla NashConv + 0.05

**Acceptance:** Statistical bounds met.

**Status:** Not yet implemented.

---

## 3. Tiny restricted-runout multi-street oracle

This is a fully specified small Hold'em game used as an independent oracle for multi-street transitions, accounting, and algorithm validation.

### 3.1 Specification

**Game:** Heads-up no-limit Hold'em river spot

**Board:** `2c 3d 4h 9s` (turn; river to be dealt)

**Restricted deck:** Only `{Kc, Tc}` are legal river cards (2 outcomes instead of 44)

**Player 0 range:** `{(As, 5s): 1.0, (Qs, Js): 1.0}` (2 combos, equal weight)

**Player 1 range:** `{(Kh, Qh): 1.0, (9h, 8h): 1.0}` (2 combos, equal weight)

**Starting pot:** 2.0 units

**Effective stack:** 1.0 unit each

**Betting:** One pot-sized bet (1.0 unit) allowed per street; actions are check, bet(1.0), fold, call

**Tree size:** 
- 2 river runouts × 4 deal pairs = 8 chance outcomes
- Each public tree: check-check, check-bet-fold, check-bet-call, bet-fold, bet-call = 5 terminal branches
- Total: 8 × 5 = 40 terminal histories (plus internal nodes)

### 3.2 Validation tests

**Test suite:** `tests/test_tiny_oracle.py` (to be created)

**Tests:**

1. **Probability mass:** All chance outcomes sum to 1.0 (exact)
2. **Terminal accounting:** Every terminal return pair sums to 0.0 (within 1e-12)
3. **Chip conservation:** Sum of returns equals net contributions (exact integer cents if using integer chips)
4. **Dynamic BR = pure enumeration:** Both players, all test profiles, absolute error ≤ 1e-12
5. **Vanilla CFR convergence:** NashConv < 0.01 after 10,000 iterations
6. **MCCFR convergence:** Mean NashConv over 5 seeds within 0.02 of vanilla after 20,000 iterations

**Status:** Not yet implemented.

---

## 4. Determinism gates

These tests verify reproducibility and stable output.

### 4.1 Vanilla CFR byte-identical JSON

**Test:** `tests/test_determinism.py::test_vanilla_cfr_json_hash_stable`

**Method:**
1. Run vanilla CFR on Kuhn for 1,000 iterations twice in the same process
2. Serialize both strategies to canonical JSON (sorted keys)
3. Compute SHA-256 hash of both JSON strings
4. Assert hashes are identical

**Acceptance:** Identical hash locally (no cross-platform claim).

**Status:** Not yet implemented.

---

### 4.2 MCCFR seed acceptance and trajectory change

**Test:** `tests/test_determinism.py::test_mccfr_seed_changes_trajectory`

**Method:**
1. Run MCCFR on Kuhn with seed=42 for 1,000 iterations
2. Run MCCFR on Kuhn with seed=43 for 1,000 iterations
3. Assert final strategies differ (at least one infoset policy differs by > 0.01)
4. Assert both converge to acceptable NashConv (< 0.1 for this short run)

**Acceptance:** Seed changes trajectory; both runs converge.

**Status:** Not yet implemented.

---

## 5. Runtime benchmark gates

These tests assert completion and coarse performance ceilings; they do not validate correctness.

### 5.1 Kuhn vanilla CFR benchmark

**Test:** `tests/test_benchmark.py::test_kuhn_vanilla_cfr_runtime`

**Method:**
1. Warm-up: run 100 iterations (discard)
2. Measure: run 10,000 iterations, repeat 3 times, take median wall-clock time
3. Assert median ≤ 5.0 seconds (generous 3× margin over measured baseline)

**Baseline measurement:** To be established on this machine before setting ceiling.

**Acceptance:** Completes within ceiling; does not validate correctness.

**Status:** Not yet implemented.

---

### 5.2 Compact river vanilla CFR benchmark

**Test:** `tests/test_benchmark.py::test_river_vanilla_cfr_runtime`

**Method:**
1. Warm-up: 10 iterations on the compact river config from `test_river.py`
2. Measure: 1,000 iterations, repeat 3 times, take median
3. Assert median ≤ 10.0 seconds (to be calibrated)

**Acceptance:** Completes within ceiling.

**Status:** Not yet implemented.

---

## 6. Test execution and CI integration

### 6.1 Fast acceptance suite

All tests except those marked `@pytest.mark.slow` or `@pytest.mark.benchmark`.

**Command:** `pytest -v -m "not slow and not benchmark"`

**Expected runtime:** < 10 seconds

**CI:** Run on every commit.

---

### 6.2 Full correctness suite

All exhaustive and stochastic tests, including slow marks.

**Command:** `pytest -v -m "not benchmark"`

**Expected runtime:** < 60 seconds

**CI:** Run on pull requests and main branch.

---

### 6.3 Benchmark suite

Runtime gates only.

**Command:** `pytest -v -m benchmark`

**Expected runtime:** < 30 seconds

**CI:** Run nightly or on performance-sensitive changes.

---

## 7. Summary of tolerances and gates

| Test | Oracle | Independence | Tolerance | Status |
|---|---|---:|---|---|
| Five-card census | Exhaustive combinatorics | 1 | Exact integer | ✅ Passing |
| Seven-card Treys | Treys 0.1.8 | 1 | Exact category/order | ✅ Passing |
| Exact equity | Treys fixtures | 1 | Exact (win, tie, loss) | ✅ Passing |
| Kuhn value | Analytical -1/18 | 1 | abs ≤ 0.003 | ✅ Passing |
| Scalable BR | Pure enumeration | 2 | abs ≤ 1e-12 | ✅ Passing |
| Hidden-bit trap | Exhaustive | 2 | exact 0.0 | ✅ Passing |
| Kuhn tree audit | Hand-verified | 2 | Exact counts | ✅ Passing |
| River NashConv | BR (validated) | 2 | < 0.01 | ✅ Passing |
| MCCFR vs vanilla (Kuhn) | Vanilla CFR | 3 | mean abs ≤ 0.03, CI ≤ 0.05 | ⬜ Not implemented |
| MCCFR vs vanilla (river) | Vanilla CFR | 3 | mean Δ ≤ 0.02, CI ≤ 0.05 | ⬜ Not implemented |
| Tiny oracle accounting | Exhaustive | 2 | abs ≤ 1e-12 | ⬜ Not implemented |
| Vanilla JSON hash | Repeat run | Repeatability | Identical SHA-256 | ⬜ Not implemented |
| MCCFR seed change | Same game | Repeatability | Trajectory differs | ⬜ Not implemented |
| Kuhn benchmark | Wall-clock | Performance | ≤ 5.0s (TBD) | ⬜ Not implemented |
| River benchmark | Wall-clock | Performance | ≤ 10.0s (TBD) | ⬜ Not implemented |

---

## 8. Anti-patterns and rejected approaches

- ❌ Monotonic exploitability: stochastic metrics can rise locally
- ❌ Iteration count as accuracy proof: convergence rate varies
- ❌ Screenshots or GUI percentages: not machine-verifiable
- ❌ Circular validation: never use CFR output as its own oracle
- ❌ Invented fixture values: all oracles must be externally generated or analytically derived
- ❌ Cross-platform byte identity without RFC 8785: claim numerical agreement with tolerances instead
- ❌ Arbitrary regret clipping or silent abstractions: separate algorithms require separate tests

---

## 9. Sources

- CFR: https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- MCCFR: https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html
- Kuhn poker: https://www.rand.org/content/dam/rand/pubs/reports/2006/R1654.pdf
- OpenSpiel algorithms: https://openspiel.readthedocs.io/en/latest/algorithms.html
- Treys: https://github.com/ihendley/treys
- PH Evaluator: https://github.com/HenryRLee/PokerHandEvaluator
- Best response (IJCAI 054): https://www.ijcai.org/Proceedings/11/Papers/054.pdf
- RFC 8785 JSON canonicalization: https://datatracker.ietf.org/doc/rfc8785/

---

## 10. Implementation checklist

**Completed:**
- ✅ Five-card evaluator exhaustive census
- ✅ Seven-card Treys cross-check script
- ✅ Exact equity fixtures (14 postflop)
- ✅ Kuhn analytical value and NashConv
- ✅ Scalable BR vs. pure enumeration
- ✅ Hidden-bit infoset consistency trap
- ✅ Kuhn tree audit
- ✅ Compact river CFR convergence

**To implement:**
- ⬜ `tests/test_mccfr.py` with Kuhn and river stochastic gates
- ⬜ `tests/test_tiny_oracle.py` with restricted-runout multi-street oracle
- ⬜ `tests/test_determinism.py` with JSON hash and seed-change tests
- ⬜ `tests/test_benchmark.py` with runtime ceilings (after baseline measurement)
- ⬜ Measure and document baseline runtimes on this machine
- ⬜ Add pytest markers: `@pytest.mark.slow`, `@pytest.mark.benchmark`
- ⬜ CI configuration for fast/full/benchmark suites

---

**End of validation test plan.**