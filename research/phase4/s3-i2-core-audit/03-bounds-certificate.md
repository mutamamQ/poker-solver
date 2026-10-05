# S3-I2 Core Audit: Bounds and Certificate Behavior

**Audit ID:** A3I2-C3R
**Date:** 2026-09-16 UTC
**Scope:** Permanent fixture validation, node/depth bounds, certificate behavior
**Test Suite:** `tests/test_nplayer_preflop_solve.py` (52 tests)
**Result:** ✅ **PASS** — All tests passed (1.11s)

---

## Executive Summary

Validated complete bounds and certificate behavior using **only permanent fixtures** from `_config(n)` with N ∈ {2, 6, 9}. All 52 tests passed. No invented fixtures, no custom ranges/stacks. Established max_depth formula, node bound forwarding, and exhaustive certificate behavior with exact pure-strategy caps.

---

## Permanent Fixtures (lines 21-43)

**Function:** `_config(n, *, weighted=False, max_raises=1)`

### Configuration Parameters
- **Players:** N ∈ {2, 6, 9}
- **Stacks:** 3 chips for SB/BB seats, 1 chip for others
- **Forced posts:** Uniform 1-chip antes for all seats + SB(1) + BB(1)
- **Ranges:** Deterministic tiny deals: seat `i` gets cards `(2i, 2i+1)`
- **Weighted variant:** Seat 0 gets additional `(40, 41)` combo with weight 3
- **Max raises:** 1 or 2 (parametrized)
- **Max nodes:** 100 (the permanent fixture's explicit bound; the public config has no implicit default)
- **Max deals:** 2 if weighted, else 1

### Showdown Ranks
- **Unweighted:** Single deal, ranks = `(n, n-1, ..., 2, 1)`
- **Weighted:** Two deals with distinct rank orderings

**Key property:** Deliberately tiny trees for tractable exhaustive validation.

---

## Max Depth Formula (line 124, 203, 244)

```python
max_depth = 2 + n + max_raises * (n - 1)
```

### Verified Instances
- **N=2, max_raises=1:** depth = 2 + 2 + 1×1 = **5**
- **N=6, max_raises=1:** depth = 2 + 6 + 1×5 = **13**
- **N=9, max_raises=1:** depth = 2 + 9 + 1×8 = **19**
- **N=2, max_raises=2:** depth = 2 + 2 + 2×1 = **6**
- **N=6, max_raises=2:** depth = 2 + 6 + 2×5 = **18**
- **N=9, max_raises=2:** depth = 2 + 9 + 2×8 = **27**

**Test coverage:** `test_exact_structural_depth[2/6/9]` (lines 241-244)

---

## Node Bound Forwarding (lines 247-259)

### Direct Solver Bounds (`test_direct_solver_bounds`)
- `NPlayerCFRSolver(root, max_nodes=1, max_depth=100)` → **ValueError: "node bound"**
- `NPlayerCFRSolver(root, max_nodes=100, max_depth=1)` → **ValueError: "depth bound"**

### Facade Forwarding (`test_facade_forwards_node_bound`)
- Config with `max_nodes=2` → `_solve()` → **ValueError: "node bound"**
- Confirms facade correctly forwards config bounds to solver

**Permanent fixture bound:** `_config` passes `max_nodes=100` explicitly (line 37).

---

## Certificate Behavior

### Default: No Certificate (lines 199, 189-238)
- `_solve(config, iterations=3)` → `result.certificate is None`
- Certificate only generated when `include_deviation_certificate=True`

### Exhaustive Certificate (`test_six_player_exhaustive_certificate_and_exact_cap`, lines 262-279)

**Six-player fixture (N=6):**
- **Pure-strategy counts per seat:** `(1, 4, 4, 1, 1, 1)` (line 140)
- **Maximum cap required:** 4 (seats 1 and 2 each have 4 pure strategies)
- **Cap=4:** ✅ **PASS** — Certificate generated successfully
- **Cap=3:** ❌ **FAIL** — `ValueError: "pure-strategy bound exceeded"`

**Certificate contents (lines 271-277):**
```python
cert.values                  # Baseline expected values (matches independent oracle)
cert.best_response_values    # Best unilateral deviation values per seat
cert.incentives              # max(0, best - baseline) per seat
cert.total_incentive         # sum(incentives)
cert.provenance              # "exhaustive finite pure unilateral deviations; diagnostic only"
```

**Validation:** Independent `_oracle()` enumeration (lines 95-111) confirms production certificate matches exhaustive pure-strategy search.

### Strict Cap Validation (`test_certificate_cap_fails_closed`, lines 282-285)
- Six-player with `max_pure_strategies=1` → **ValueError: "pure-strategy bound exceeded"**
- Confirms fail-closed behavior: insufficient cap rejects certificate generation

### Independent Oracle (lines 132-151)
- **Function:** `_oracle(root, infosets, strategy)` — exhaustive pure-strategy enumeration
- **Six-player uniform strategy:**
  - Baseline values: `(5, 1/8, -17/8, -1, -1, -1)`
  - Incentives: `(0, 3/8, 3/8, 0, 0, 0)`
  - Pure-strategy counts: `(1, 4, 4, 1, 1, 1)`
- **Production certificate:** Matches oracle to 1e-12 absolute tolerance
- **Cap enforcement:** `max_pure_strategies=3` → ValueError (requires 4)

---

## Strict Parameter Validation

### Algorithm (lines 159-163)
- **Valid:** `"vanilla-cfr"`
- **Invalid:** `"unknown"`, `"cfr+"`, `""`, `None`, `True`, `1` → **ValueError: "algorithm"**

### Iterations (lines 166-170)
- **Valid:** Positive integers (1, 2, 3, ...)
- **Invalid:** `0`, `-1`, `True`, `False`, `1.5`, `"1"`, `None` → **ValueError: "iterations"**

### Include Certificate (lines 173-177)
- **Valid:** `True`, `False`
- **Invalid:** `0`, `1`, `"true"`, `None` → **ValueError: "include_deviation_certificate"**

### Max Pure Strategies (lines 180-185)
- **Public facade default:** `100_000` (verified from the frozen solve signature)
- **Valid:** Positive integers (1, 2, 3, ...)
- **Invalid:** `0`, `-1`, `True`, `False`, `1.5`, `"1"`, `None` → **ValueError: "max_pure_strategies"**
- **Enforced even when `include_deviation_certificate=False`** (lines 181-185)

---

## Test Manifest (52 tests, all passed)

### Fixture Construction (9 tests, lines 114-129)
- `test_fixtures_construct_and_traverse_without_facade[n-weighted-max_raises]`
- **Coverage:** the nine explicit parametrized N/weighted/max-raise combinations in the permanent suite
- **Validates:** Tree construction, deal enumeration, chance outcomes, depth bounds, solver initialization

### Independent Oracle (1 test, lines 132-151)
- `test_six_player_oracle_runs_independently_before_facade`
- **Validates:** Exhaustive pure-strategy enumeration matches production certificate

### Type Existence (1 test, lines 154-156)
- `test_result_type_exists`
- **Validates:** `NPlayerPreflopSolveResult` module location

### Strict Validation (28 tests, lines 159-185)
- `test_strict_algorithm[6 variants]`
- `test_strict_iterations[7 variants]`
- `test_strict_include_certificate[4 variants]`
- `test_strict_pure_cap_even_when_not_requested[14 variants: 7 caps × 2 include values]`

### Solve Result Properties (3 tests, lines 188-238)
- `test_solve_deterministic_finite_immutable_result[2/6/9]`
- **Validates:** Determinism, immutability, metadata, expected values, strategy structure

### Depth Formula (3 tests, lines 241-244)
- `test_exact_structural_depth[2/6/9]`
- **Validates:** `max_depth = 2 + n + max_raises * (n - 1)`

### Bounds Forwarding (2 tests, lines 247-259)
- `test_direct_solver_bounds`
- `test_facade_forwards_node_bound`

### Certificate Behavior (2 tests, lines 262-285)
- `test_six_player_exhaustive_certificate_and_exact_cap`
- `test_certificate_cap_fails_closed`

---

## Key Findings

1. **Permanent fixtures only:** All tests use `_config(n)` with N ∈ {2, 6, 9}. No invented fixtures.
2. **Max depth formula:** `2 + n + max_raises * (n - 1)` — verified for all N and max_raises combinations.
3. **Node bound forwarding:** Config `max_nodes` correctly propagates to solver; violations raise ValueError.
4. **Permanent fixture bound:** `_config` explicitly uses `max_nodes=100`; this is not an implicit config default.
5. **Certificate default:** `None` unless `include_deviation_certificate=True`.
6. **Exhaustive certificate:** Requires `max_pure_strategies >= max(pure_strategy_counts_per_seat)`.
7. **Six-player cap:** Requires 4; cap=3 fails closed with ValueError.
8. **Independent validation:** `_oracle()` exhaustive enumeration confirms production certificate accuracy.
9. **Strict validation:** All parameters (algorithm, iterations, certificate, cap) enforce type and value constraints.
10. **Immutability:** Result objects are frozen; strategy and metadata are deeply immutable.

---

## Conclusion

✅ **All 52 tests passed.** Bounds and certificate behavior fully validated using permanent fixtures. No invented configurations. Max depth formula established. Node bound forwarding confirmed. Certificate behavior (None/exhaustive) and pure-strategy cap enforcement verified. Independent oracle validates production certificate accuracy.

**No blockers. Audit complete.**