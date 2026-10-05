# S1-I1 Audit 06: Regression and Scope Coverage

**Auditor:** Non-author independent audit  
**Batch:** S1-I1 (core typed facade and bounded composite solve)  
**Date:** 2026-09-15  
**Workdir:** `/home/genomix-node/poker-solver`

---

## 1. Syntax and Import Validation

**Command:**
```bash
python3 -m compileall src/poker_solver/allstreet.py src/poker_solver/api_v4.py src/poker_solver/bounded_tree.py
```

**Result:** ✅ **PASS**  
- Exit code: 0
- All three S1-I1 production modules compile without syntax errors
- No import-time failures

---

## 2. Focused S1-I1 Test Execution

**Command:**
```bash
.venv/bin/python -m pytest tests/test_allstreet_config.py tests/test_allstreet_state.py tests/test_api_v4.py tests/test_bounded_tree.py -v
```

**Result:** ⚠️ **PARTIAL**  
- **Passed:** 65 tests
- **Failed:** 52 tests
- **Total focused:** 117 tests

### Failure Categories:

#### 2.1 Test Setup Defects (41 failures)
- All 41 failures in `test_allstreet_config.py` caused by missing `Card` import
- Error: `NameError: name 'Card' is not defined`
- Tests are structurally correct but cannot construct fixtures
- **Root cause:** Test file missing `from poker_solver.cards import Card` or equivalent

#### 2.2 Production Defects (3 failures in `test_allstreet_state.py`)
- `test_river_check_check_terminal`: River check-check incorrectly terminates before second check
- `test_zero_sum_terminals`: Same river progression defect
- `test_complete_flop_to_river_path`: Same river progression defect
- **Root cause:** `MultiStreetState` terminates at river after first check instead of allowing check-check showdown

#### 2.3 API Schema Defects (8 failures in `test_api_v4.py`)
- All 8 failures caused by payload schema mismatch
- Error: `ValueError: unknown payload fields: ['game']`
- Tests expect flat payload structure; `api_v4.py` expects nested `game` object
- **Root cause:** API implementation does not match documented flat schema in ARCHITECTURE_PHASE4_S1.md §3.2

---

## 3. Full Regression Suite

**Command:**
```bash
.venv/bin/python -m pytest
```

**Result:** ⚠️ **PARTIAL**  
- **Total collected:** 515 tests
- **Passed:** 463 tests (89.9%)
- **Failed:** 52 tests (10.1%)
- **Baseline:** 398 tests (per ARCHITECTURE_PHASE4_S1.md §1)
- **New S1-I1 tests:** 117 tests
- **Runtime:** 200.73s

### Regression Analysis:
- All 52 failures are S1-I1 tests (no baseline regression)
- Existing 398-test baseline remains green
- No interference with preflop, multiway, nplayer, ICM, or bounty modules

---

## 4. Symbol and Behavioral Inventory

### 4.1 `src/poker_solver/allstreet.py`
- **Classes:** 2 (`AllStreetPostflopConfig`, `AllStreetSolveResult`)
- **Functions:** 3 (`create_allstreet_root`, `solve_allstreet_postflop`, plus `__post_init__`)
- **Lines:** 245
- **Assigned scope:** Typed config/adapter/root/result (S1-I1 item 1)

### 4.2 `src/poker_solver/api_v4.py`
- **Functions:** 5+ (dispatch_v4, _object, _list, _int, _float, _str)
- **Lines:** 262
- **Assigned scope:** Strict envelope; no CLI/shared exports (S1-I1 item 4)
- **Defect:** Schema does not match flat payload structure per §3.2

### 4.3 `src/poker_solver/bounded_tree.py`
- **Classes:** 1 (`BoundedTreeStats`)
- **Functions:** 1 (`validate_bounded_tree`)
- **Lines:** 233
- **Assigned scope:** Two-player node/depth preflight (S1-I1 item 6)
- **Test coverage:** 30/30 tests pass

### 4.4 Test Files
- `tests/test_allstreet_config.py`: 41 tests (all fail due to missing Card import)
- `tests/test_allstreet_state.py`: 13 tests (10 pass, 3 fail on river progression)
- `tests/test_api_v4.py`: 33 tests (25 pass, 8 fail on schema mismatch)
- `tests/test_bounded_tree.py`: 30 tests (all pass)

---

## 5. Gap Analysis

### 5.1 Missing S1-I1 Artifacts
- ❌ `tests/test_allstreet_config.py` (item 2): Exists but has import defect
- ❌ `tests/test_allstreet_state.py` (item 3): Exists but has 3 production-defect failures
- ❌ `src/poker_solver/api_v4.py` (item 4): Exists but schema does not match spec
- ❌ `tests/test_api_v4.py` (item 5): Exists but 8 tests fail on schema mismatch
- ✅ `src/poker_solver/bounded_tree.py` + `tests/test_bounded_tree.py` (item 6): Complete and green

### 5.2 Production Gaps
1. **River check-check terminal:** `MultiStreetState` does not allow check-check showdown on river
2. **API v4 schema:** Nested `game` object instead of flat payload per §3.2
3. **Test fixture imports:** Missing `Card` import in `test_allstreet_config.py`

---

## 6. Mandatory Gate Compliance (§6.3)

| Gate | Status | Evidence |
|------|--------|----------|
| Standard flop request reaches river terminals | ❌ FAIL | River check-check defect blocks natural showdown |
| Every terminal is zero-sum | ⚠️ UNTESTED | Test blocked by river defect |
| Every policy is finite/nonnegative/normalized | ⚠️ UNTESTED | Solve tests blocked by API schema |
| Repeated vanilla runs exactly equal | ⚠️ UNTESTED | Test blocked by API schema |
| MCCFR same-seed runs exactly equal | ⚠️ UNTESTED | Test blocked by API schema |
| Opponent-card-only changes preserve infokey | ✅ PASS | `test_opponent_card_noninterference` passes |
| Blocked runouts never appear, mass=1 | ✅ PASS | `test_blocked_runout_filtering`, `test_compatible_runout_chance_mass` pass |
| Fold/call/check/all-in/raise fixtures retain behavior | ✅ PASS | 7/10 state tests pass |
| Focused tests pass | ❌ FAIL | 65/117 pass (55.6%) |
| All prior 398 + additive tests pass | ⚠️ PARTIAL | 398 baseline green; 52/117 additive fail |

---

## 7. Verdict

**Overall:** ❌ **FAIL**

### Blocking Defects:
1. **Test setup:** Missing `Card` import blocks 41 config validation tests
2. **Production:** River check-check terminal defect blocks 3 state tests and violates §4 state-machine contract
3. **API schema:** Nested `game` object violates §3.2 flat payload spec, blocks 8 API tests

### Non-Blocking Observations:
- ✅ Syntax/import validation clean
- ✅ Bounded tree module complete (30/30 tests green)
- ✅ No baseline regression (398 prior tests remain green)
- ✅ 89.9% of full suite passes

### Required Repairs:
1. Add `from poker_solver.cards import Card` to `tests/test_allstreet_config.py`
2. Fix `MultiStreetState` river check-check progression to allow showdown
3. Flatten `api_v4.py` payload schema per §3.2 (remove nested `game` object)

### Audit Recommendation:
**REJECT S1-I1 for acceptance.** Repair blocking defects, re-run focused + full suite to GREEN, then submit for fresh non-author repair audit per §7 batch acceptance rule.

---

## 8. Exact Commands and Counts

```bash
# Syntax validation
python3 -m compileall src/poker_solver/allstreet.py src/poker_solver/api_v4.py src/poker_solver/bounded_tree.py
# Exit: 0, Output: (empty = success)

# Focused S1-I1 tests
.venv/bin/python -m pytest tests/test_allstreet_config.py tests/test_allstreet_state.py tests/test_api_v4.py tests/test_bounded_tree.py -v
# Collected: 117, Passed: 65, Failed: 52

# Full regression
.venv/bin/python -m pytest
# Collected: 515, Passed: 463, Failed: 52, Runtime: 200.73s

# Test collection count
python3 -m pytest --co -q | wc -l
# Output: 515 (includes header lines; actual test count confirmed in full run)
```

---

**Audit complete.** S1-I1 batch has 3 blocking defects preventing acceptance.