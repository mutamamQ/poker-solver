# Phase 4 S1-I1 immutable-result audit: config validation

**Audit date:** 2026-09-15  
**Auditor:** Independent non-author verification  
**Candidate manifest:** `CANDIDATE_MANIFEST.md` (frozen 2026-09-15T16:52:34Z)  
**Base commit:** 7a817e618a3c0898b531e88440b490323c62b49b  
**Scope:** Config validation contract for `api_v4.dispatch_v4`

---

## Executive summary

**VERDICT: ✅ PASS — All config validation contracts verified executable and correct.**

Executed 13 targeted config validation tests covering:
- Malformed type rejection (booleans as integers)
- Non-finite float rejection (inf, -inf, nan)
- Card uniqueness and blocker conflict detection
- Positive/non-negative numeric constraints
- Algorithm-seed contract enforcement
- Defensive input isolation (deep copy verification)

All tests **PASSED** in 0.38s with zero failures.

---

## Test execution record

### Command
```bash
cd /home/genomix-node/poker-solver && python3 -m pytest \
  tests/test_api_v4.py::test_bool_as_int_rejected_for_numeric_fields \
  tests/test_api_v4.py::test_nonfinite_weight_rejected \
  tests/test_api_v4.py::test_negative_weight_rejected \
  tests/test_api_v4.py::test_zero_total_weight_rejected \
  tests/test_api_v4.py::test_duplicate_cards_in_board_rejected \
  tests/test_api_v4.py::test_duplicate_cards_in_combo_rejected \
  tests/test_api_v4.py::test_blocker_conflict_board_and_combo_rejected \
  tests/test_api_v4.py::test_blocker_conflict_in_runout_rejected \
  tests/test_api_v4.py::test_duplicate_cards_in_runout_rejected \
  tests/test_api_v4.py::test_vanilla_cfr_with_seed_rejected \
  tests/test_api_v4.py::test_mccfr_without_seed_rejected \
  tests/test_api_v4.py::test_non_positive_iterations_rejected \
  tests/test_api_v4.py::test_deep_response_isolation_comprehensive \
  -v
```

### Result
```
============================= test session starts ==============================
platform linux -- Python 3.11.16, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: /home/genomix-node/poker-solver
configfile: pyproject.toml
collecting ... collected 13 items

tests/test_api_v4.py::test_bool_as_int_rejected_for_numeric_fields PASSED [  7%]
tests/test_api_v4.py::test_nonfinite_weight_rejected PASSED              [ 15%]
tests/test_api_v4.py::test_negative_weight_rejected PASSED               [ 23%]
tests/test_api_v4.py::test_zero_total_weight_rejected PASSED             [ 30%]
tests/test_api_v4.py::test_duplicate_cards_in_board_rejected PASSED      [ 38%]
tests/test_api_v4.py::test_duplicate_cards_in_combo_rejected PASSED      [ 46%]
tests/test_api_v4.py::test_blocker_conflict_board_and_combo_rejected PASSED [ 53%]
tests/test_api_v4.py::test_blocker_conflict_in_runout_rejected PASSED    [ 61%]
tests/test_api_v4.py::test_duplicate_cards_in_runout_rejected PASSED     [ 69%]
tests/test_api_v4.py::test_vanilla_cfr_with_seed_rejected PASSED         [ 76%]
tests/test_api_v4.py::test_mccfr_without_seed_rejected PASSED            [ 84%]
tests/test_api_v4.py::test_non_positive_iterations_rejected PASSED       [ 92%]
tests/test_api_v4.py::test_deep_response_isolation_comprehensive PASSED  [100%]

============================== 13 passed in 0.38s ==============================
```

---

## Validation coverage

### 1. Type safety (malformed types)
- ✅ **Boolean-as-integer rejection** (`test_bool_as_int_rejected_for_numeric_fields`)
  - Verified `iterations=True` and `effective_stack=False` both raise `ValueError`
  - Implementation: `api_v4.py:46` checks `isinstance(value, bool)` before `isinstance(value, int)`

### 2. Non-finite float rejection
- ✅ **Infinity and NaN rejection** (`test_nonfinite_weight_rejected`)
  - Verified `weight=float('inf')`, `weight=float('nan')`, `weight=float('-inf')` all raise `ValueError`
  - Implementation: `api_v4.py:61` uses `isfinite()` check with `finite=True` flag

### 3. Numeric constraints
- ✅ **Negative weight rejection** (`test_negative_weight_rejected`)
  - Verified `weight=-1.0` raises `ValueError`
  - Implementation: `api_v4.py:63-64` enforces `nonnegative=True` for weights

- ✅ **Zero total weight rejection** (`test_zero_total_weight_rejected`)
  - Verified all-zero weights (no positive compatible mass) raises `ValueError`
  - Implementation: Downstream validation in `allstreet.py` (not in `api_v4.py` itself)

- ✅ **Non-positive iterations rejection** (`test_non_positive_iterations_rejected`)
  - Verified `iterations=0` and `iterations=-10` both raise `ValueError`
  - Implementation: `api_v4.py:201` uses `positive=True` flag

### 4. Card uniqueness and blocker conflicts
- ✅ **Duplicate cards in board** (`test_duplicate_cards_in_board_rejected`)
  - Verified `starting_board=[0, 0, 2]` raises `ValueError`
  - Implementation: `api_v4.py:149-150` checks `len(set(starting_board)) != 3`

- ✅ **Duplicate cards in combo** (`test_duplicate_cards_in_combo_rejected`)
  - Verified `cards=[3, 3]` raises `ValueError`
  - Implementation: `api_v4.py:168-169` checks `cards[0] == cards[1]`

- ✅ **Blocker conflict: board vs combo** (`test_blocker_conflict_board_and_combo_rejected`)
  - Verified board card appearing in combo raises `ValueError`
  - Implementation: Downstream validation in `allstreet.py`

- ✅ **Blocker conflict in runout** (`test_blocker_conflict_in_runout_rejected`)
  - Verified runout card already on board raises `ValueError`
  - Implementation: Downstream validation in `allstreet.py`

- ✅ **Duplicate cards in runout** (`test_duplicate_cards_in_runout_rejected`)
  - Verified `runout=[7, 7]` raises `ValueError`
  - Implementation: `api_v4.py:187-188` checks `runout[0] == runout[1]`

### 5. Algorithm-seed contract
- ✅ **Vanilla CFR with seed rejected** (`test_vanilla_cfr_with_seed_rejected`)
  - Verified `algorithm="vanilla-cfr"` + `seed=42` raises `ValueError`
  - Implementation: `api_v4.py:209-210` enforces deterministic algorithm has no seed

- ✅ **MCCFR without seed rejected** (`test_mccfr_without_seed_rejected`)
  - Verified `algorithm="external-sampling-mccfr"` + `seed=None` raises `ValueError`
  - Implementation: `api_v4.py:211-212` enforces stochastic algorithm requires seed

### 6. Defensive input isolation
- ✅ **Deep response isolation** (`test_deep_response_isolation_comprehensive`)
  - Verified mutations to returned response (strategy, metadata, nested policies) do not affect subsequent calls
  - Tested: top-level strategy injection, nested policy mutation, numeric field corruption, list append
  - Fresh response after mutations equals pristine baseline exactly
  - Implementation: `api_v4.py:246-282` serializes immutable structures to fresh dicts/lists

---

## Implementation notes

### Validation architecture
1. **Type guards** (`api_v4.py:10-73`): Helper functions `_int()`, `_float()`, `_str()`, `_list()`, `_object()` enforce strict JSON type contracts
2. **Boolean rejection**: Explicit `isinstance(value, bool)` check before numeric type checks (Python's `bool` is subclass of `int`)
3. **Finite float enforcement**: `isfinite()` check with `finite=True` flag (default for weights)
4. **Constraint flags**: `positive=True`, `nonnegative=True`, `allowed={...}` for domain restrictions
5. **Immutable config construction**: `AllStreetPostflopConfig` built from validated primitives (tuples, not lists)
6. **Defensive serialization**: `serialize_strategy()` and `serialize_values()` convert immutable mappings to fresh JSON-safe dicts

### Blocker validation split
- **API layer** (`api_v4.py`): Validates intra-structure uniqueness (board cards unique, combo cards unique, runout cards unique)
- **Domain layer** (`allstreet.py`): Validates cross-structure conflicts (board vs combos, board vs runouts, combos vs runouts)
- This separation keeps API validation stateless and domain validation context-aware

---

## Audit conclusion

**All config validation contracts are executable, correct, and defensive.**

- Type safety: Boolean-as-int trap avoided ✅
- Numeric safety: Non-finite floats rejected ✅
- Domain constraints: Card uniqueness and blocker conflicts enforced ✅
- Algorithm contracts: Seed requirements matched to algorithm determinism ✅
- Input isolation: Deep copy defense verified against mutation ✅

**No issues found. Candidate manifest config validation is immutable-result ready.**

---

**Audit completed:** 2026-09-15  
**Files examined:**
- `src/poker_solver/api_v4.py` (282 lines, SHA256: 49677a0f...)
- `tests/test_api_v4.py` (480 lines, SHA256: f2d3c579...)

**Test suite:** 13/13 passed (0.38s)  
**Modifications made:** None (read-only audit)