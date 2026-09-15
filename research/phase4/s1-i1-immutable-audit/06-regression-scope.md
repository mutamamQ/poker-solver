# Phase 4 S1-I1 Immutable Audit: Regression Scope

**Audit timestamp:** 2026-09-15T16:52:34Z (frozen)  
**Base commit:** `7a817e618a3c0898b531e88440b490323c62b49b`  
**Auditor role:** Fresh non-author verification  
**Manifest:** `CANDIDATE_MANIFEST.md` (8 files, SHA256-verified)

---

## Executive Summary

**VERDICT: PASS WITH ONE ADVISORY**

All executable gates passed. Manifest integrity confirmed. One dormant skip marker found in test file (does not execute; tests run and pass). No unauthorized probe files, no placeholders in production code, full S1-I1 contract coverage verified.

---

## Verification Results

### 1. Manifest Integrity

**Status:** ✅ PASS

All 8 candidate files verified against declared SHA256 hashes:

```
5cfac6f10b4f03e9e209e74912032abfff025efef6a8113d5f362a2268b50295  src/poker_solver/allstreet.py
49677a0fc488a1fcff351766362b66ddcd6d59564d06ee9c501b46efbc6c3bd4  src/poker_solver/api_v4.py
aa08d546495091f394c75f5c716b63fa9342d785588eafa1e367f2d8e59dc0d4  src/poker_solver/bounded_tree.py
bdacc32688361f0cec48205b722aca8843c24dca4f58dd11479d5aa85fdfa490  src/poker_solver/multistreet.py
954da7036b58e58bf741d1026c333c20c2e5bbf07ba64d5a625ba26838824632  tests/test_allstreet_config.py
b632e5d72c19679e591a1ef1e743af08c3ea50772c0712441d0703d925cd63da  tests/test_allstreet_state.py
f2d3c579ce4678f516a9409afac9676690178cc7a5c3b2dfe03c1d6d7e0bf7c2  tests/test_api_v4.py
1351676894f588e29762f5046777f1ba9b1be527ddd2598cfba4f76782c519a0  tests/test_bounded_tree.py
```

**Exact match:** All computed hashes match manifest.

---

### 2. Whitespace & Syntax

**Status:** ✅ PASS

- `git diff --check`: Clean (exit 0, no output)
- `python3 -m compileall -q src/ tests/`: PASS (exit 0)

No trailing whitespace, no syntax errors.

---

### 3. Focused Test Execution (S1-I1 Contract)

**Status:** ✅ PASS

**Command:**
```bash
python3 -m pytest tests/test_allstreet_config.py tests/test_allstreet_state.py \
                   tests/test_api_v4.py tests/test_bounded_tree.py -v
```

**Result:** **126 passed in 2.36s**

**Breakdown:**
- `test_allstreet_config.py`: 46 tests
- `test_allstreet_state.py`: 17 tests
- `test_api_v4.py`: 37 tests
- `test_bounded_tree.py`: 26 tests

**Total S1-I1 coverage:** 126 executable tests, 0 failures, 0 skips executed.

---

### 4. Full Regression Suite

**Status:** ✅ PASS

**Command:**
```bash
python3 -m pytest -v
```

**Result:** **524 passed in 205.82s (0:03:25)**

**Exact count:** 524 tests collected, 524 passed, 0 failed, 0 skipped, 0 errors.

Full test inventory confirmed via `pytest --co -q`.

---

### 5. Skip/Placeholder Audit

**Status:** ⚠️ ADVISORY (non-blocking)

**Finding:** One dormant skip marker in `tests/test_allstreet_config.py`:

```python
pytest.skip("allstreet module not yet implemented", allow_module_level=True)
```

**Impact:** None. This line is **not executed** (tests run and pass). Likely a fossil comment or conditional guard that is bypassed. Does not affect test execution or coverage.

**Recommendation:** Remove in post-freeze cleanup (not required for immutability gate).

**Production code:** No placeholders, TODOs, FIXMEs, or stubs found in:
- `src/poker_solver/allstreet.py`
- `src/poker_solver/api_v4.py`
- `src/poker_solver/bounded_tree.py`
- `src/poker_solver/multistreet.py`

---

### 6. Unauthorized Probe Files

**Status:** ✅ PASS

No files matching `probe`, `unauthorized`, `temp`, or `scratch` patterns found in `tests/`.

---

## S1-I1 Contract Coverage Inventory

### Implemented Modules (4 production files)

1. **`src/poker_solver/allstreet.py`** (257 lines)  
   - `AllStreetPostflopConfig` dataclass (frozen, immutable)
   - `create_allstreet_root()` factory
   - `solve_allstreet_postflop()` solver facade
   - Deep immutability enforcement via `MappingProxyType`

2. **`src/poker_solver/api_v4.py`** (282 lines)  
   - Strict JSON schema validation helpers
   - `solve_allstreet_postflop_v4()` programmatic API
   - Additive version-4 envelope protocol

3. **`src/poker_solver/bounded_tree.py`**  
   - `validate_bounded_tree()` structural validator
   - Max-nodes and max-depth enforcement

4. **`src/poker_solver/multistreet.py`**  
   - `MultiStreetConfig` and `create_root()` (dependency)
   - Street progression and terminal logic

### Test Coverage (4 test files, 126 tests)

1. **`tests/test_allstreet_config.py`** (46 tests)  
   - Config construction validation (version, board, stacks, combos, runouts)
   - Defensive copying (tuples, immutability)
   - Algorithm validation (vanilla CFR, MCCFR, seed requirements)
   - Result metadata and deep immutability

2. **`tests/test_allstreet_state.py`** (17 tests)  
   - Street progression (flop→turn→river)
   - Runout filtering and chance mass
   - Fold/call/raise accounting
   - Zero-sum terminals
   - Determinism and card noninterference

3. **`tests/test_api_v4.py`** (37 tests)  
   - End-to-end solve (canonical path)
   - Determinism (vanilla CFR, MCCFR with seed)
   - Schema validation (unknown fields, missing fields, bool-as-int rejection)
   - Resource bounds (max_nodes, max_depth)
   - Blocker conflicts and card validation
   - JSON serializability and metadata truthfulness

4. **`tests/test_bounded_tree.py`** (26 tests)  
   - Tree structure validation (terminal, chance, decision nodes)
   - Actor and action consistency
   - Max-nodes and max-depth enforcement
   - Cycle detection

---

## Regression Scope: Exact Executable Verdict

### Immutability Gate

**PASS:** All 8 manifest files are SHA256-verified immutable.

### Executable Gates

| Gate | Command | Expected | Actual | Status |
|------|---------|----------|--------|--------|
| Whitespace | `git diff --check` | exit 0, no output | exit 0, no output | ✅ PASS |
| Syntax | `python3 -m compileall -q src/ tests/` | exit 0 | exit 0 | ✅ PASS |
| Focused (S1-I1) | `pytest test_allstreet_config.py test_allstreet_state.py test_api_v4.py test_bounded_tree.py -v` | 126 passed | **126 passed in 2.36s** | ✅ PASS |
| Full Suite | `pytest -v` | 524 passed | **524 passed in 205.82s** | ✅ PASS |

### Contract Compliance

- ✅ All S1-I1 modules implemented (no stubs)
- ✅ All S1-I1 tests executable (no skips in run)
- ✅ No unauthorized probe files
- ⚠️ One dormant skip marker (non-blocking; does not execute)

---

## Recommendations

1. **Post-freeze cleanup:** Remove dormant `pytest.skip()` line in `tests/test_allstreet_config.py` (line found via grep; does not affect current execution).

2. **Immutability seal:** Candidate is ready for immutable-result promotion. All gates passed.

---

## Audit Provenance

- **Workdir:** `/home/genomix-node/poker-solver`
- **Python:** 3.11.16 (venv: `.venv`)
- **Pytest:** 9.1.1
- **Git HEAD:** `7a817e618a3c0898b531e88440b490323c62b49b` ("phase4: reconcile S1 all-street design")
- **Audit mode:** Fresh non-author verification (no edits)

---

**Final verdict:** ✅ **PASS** — All executable gates satisfied. Candidate approved for immutable-result freeze.
