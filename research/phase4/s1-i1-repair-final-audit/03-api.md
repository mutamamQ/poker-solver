# A03 Strict v4 API Audit Report

**Auditor:** A03 (non-author repair auditor)  
**Timestamp:** 2026-09-15T18:48:00Z  
**Candidate:** S1-I1 repaired (manifest frozen 2026-09-15T18:43:25Z)  
**Workspace:** `/home/genomix-node/poker-solver`  
**HEAD:** `7a817e6`

---

## Executive Summary

**VERDICT: PASS**

Strict v4 API (`src/poker_solver/api_v4.py`) enforces all specified contracts:
- Envelope version must be integer 4 (rejects 4.0, bool, string)
- Flat request schema with exact field sets (unknown/missing rejected)
- Type guards reject booleans as numerics, nonfinite floats
- Bounds enforced (positive/nonnegative)
- Response JSON-serializable with no NaN/Infinity
- Mutation isolation across calls
- Deterministic outputs (vanilla-cfr unconditional, mccfr with seed)
- Legacy API unchanged (426 tests pass)

---

## Hash Verification

```text
30d94c226a82375afa2a10f4e3c3b785e37009257023b65da296742bf7cbd1ea  src/poker_solver/allstreet.py
a695b0a91831f5764681caa8d3c461c29c8d9e663357f6796301a8c68c4a2047  src/poker_solver/api_v4.py
c221d77dffed3866b497acdef2ea039e93cd5b10e9ce387f1b6f0537df9b91f9  src/poker_solver/bounded_tree.py
bdacc32688361f0cec48205b722aca8843c24dca4f58dd11479d5aa85fdfa490  src/poker_solver/multistreet.py
a2765f7a3a6c538b38ea9d0c3471c4aade00e7c0db4ba0dda300eeb250437de4  tests/test_allstreet_config.py
b632e5d72c19679e591a1ef1e743af08c3ea50772c0712441d0703d925cd63da  tests/test_allstreet_state.py
fa1ec90e10dd11c44c730472f8502b797ed0eb0ef59d9c8e8d1994f72053540f  tests/test_api_v4.py
ed7184c00939dd8a847d7655f5cb60a1d696f1aacb3d143d3f3d286a6139936e  tests/test_bounded_tree.py
```

✅ All 8 hashes match `CANDIDATE_MANIFEST.md`

---

## Test Execution

### Official Test Suite

```bash
uv run pytest tests/test_api_v4.py -v
# 36 passed in 1.50s
```

**Coverage:**
- Canonical end-to-end solve
- Deterministic vanilla-cfr (identical copies)
- Deterministic mccfr with same seed
- Unknown/missing field rejection (request + payload)
- Bool-as-int rejection
- Nonfinite/negative weight rejection
- Algorithm-seed consistency
- Explicit continuation/payoff_table rejection
- Bounds (iterations, max_nodes, max_depth)
- Duplicate/blocker conflicts
- Resource bound errors
- JSON serialization with strict NaN check
- Metadata truthfulness
- Version/operation/betting_mode validation
- Deep response isolation

### Legacy API Tests

```bash
uv run pytest tests/ -k 'not slow and not allstreet and not bounded' -q --tb=no
# 426 passed, 105 deselected in 155.21s
```

✅ No regressions in evaluator, cards, deck, hand strength, equity, or other core modules.

---

## Adversarial Probes

### 1. Envelope Version Strictness

**Probe:** `/tmp/audit_api_v4_strict.py::test_version_rejection`

```python
request["version"] = 4.0   # float
request["version"] = True  # bool
request["version"] = "4"   # string
```

**Result:**
```
PASS: 4.0 rejected ("version must be JSON integer 4")
PASS: bool True rejected
PASS: string '4' rejected
```

**Evidence:** Lines 115-117 in `api_v4.py`:
```python
if isinstance(version_value, bool) or not isinstance(version_value, int) or version_value != 4:
    raise ValueError("version must be JSON integer 4")
```

---

### 2. Schema Enforcement

**Probe:** `/tmp/audit_api_v4_strict.py::test_unknown_fields`, `test_missing_fields`

```python
request["extra_field"] = "bad"  # unknown request field
payload["unknown_param"] = 123  # unknown payload field
del request["operation"]        # missing request field
del payload["iterations"]       # missing payload field
```

**Result:**
```
PASS: unknown request field rejected ("unknown request fields: ['extra_field']")
PASS: unknown payload field rejected ("unknown payload fields: ['unknown_param']")
PASS: missing operation rejected ("missing request fields: ['operation']")
PASS: missing iterations rejected ("missing payload fields: ['iterations']")
```

**Evidence:** `_object()` and `_object_with_optional()` helpers (lines 10-36) enforce exact field sets with sorted error messages.

---

### 3. Nested Object Rejection

**Probe:** `/tmp/audit_api_v4_strict.py::test_nested_rejection`

```python
payload["starting_board"] = [{"card": 0}, 1, 2]  # nested object in flat array
```

**Result:**
```
PASS: nested object in starting_board rejected: starting_board[0] must be a JSON integer
```

**Evidence:** `_int()` helper (line 46) rejects non-int types, including dicts.

---

### 4. Boolean Rejection

**Probe:** `/tmp/audit_api_v4_strict.py::test_boolean_rejection`

```python
payload["iterations"] = True   # bool as int
combo["weight"] = False        # bool as float
```

**Result:**
```
PASS: bool True as iterations rejected ("must be a JSON integer")
PASS: bool False as weight rejected ("must be a number")
```

**Evidence:**
- Line 46: `if isinstance(value, bool) or not isinstance(value, int):`
- Line 56: `if isinstance(value, bool):`

---

### 5. Nonfinite Rejection

**Probe:** `/tmp/audit_api_v4_strict.py::test_nonfinite_rejection`

```python
combo["weight"] = float('inf')
combo["weight"] = float('nan')
```

**Result:**
```
PASS: Infinity rejected ("must be finite")
PASS: NaN rejected ("must be finite")
```

**Evidence:** Line 61-62 in `_float()`:
```python
if finite and not isfinite(result):
    raise ValueError(f"{label} must be finite")
```

---

### 6. Bounds Enforcement

**Probe:** `/tmp/audit_api_v4_strict.py::test_bounds`

```python
payload["effective_stack"] = -1   # must be positive
payload["effective_stack"] = 0    # must be positive
combo["weight"] = -0.5            # must be non-negative
```

**Result:**
```
PASS: negative effective_stack rejected ("must be positive")
PASS: zero effective_stack rejected ("must be positive")
PASS: negative weight rejected ("must be non-negative")
```

**Evidence:**
- Line 48-49: `if positive and value <= 0:`
- Line 63-64: `if nonnegative and result < 0:`

---

### 7. JSON Serialization

**Probe:** `/tmp/audit_json_serialization.py::test_json_serialization`

```python
response = dispatch_v4(request)
serialized = json.dumps(response)  # must not raise
assert 'NaN' not in serialized and 'Infinity' not in serialized
```

**Result:**
```
PASS: Response JSON-serializable (20151 bytes)
PASS: JSON round-trip successful
PASS: No NaN/Infinity in serialized JSON
```

**Evidence:** Lines 247-260 in `api_v4.py` serialize strategy/values defensively:
```python
def serialize_strategy(strategy):
    return {str(k): {str(a): float(p) for a, p in policy.items()} for k, policy in strategy.items()}

def serialize_values(values):
    if not isfinite(v0) or not isfinite(v1):
        raise ValueError(f"non-finite value vector: ({v0}, {v1})")
    return [float(v0), float(v1)]
```

---

### 8. Mutation Isolation

**Probe:** `/tmp/audit_json_serialization.py::test_mutation_isolation`

```python
response1 = dispatch_v4(copy.deepcopy(request))
response1["strategy"][first_key]["MUTATED"] = 999.999
response1["metadata"]["INJECTED"] = "contamination"
response2 = dispatch_v4(copy.deepcopy(request))
assert "MUTATED" not in str(response2["strategy"])
assert "INJECTED" not in response2["metadata"]
```

**Result:**
```
PASS: Strategy isolated across calls
PASS: Metadata isolated across calls
```

**Evidence:** `serialize_strategy()` creates fresh dicts; `dict(result.metadata)` copies metadata.

---

### 9. Deterministic Outputs

**Probe:** `/tmp/audit_determinism.py`

```python
# Vanilla CFR (no seed)
r1 = dispatch_v4(request)
r2 = dispatch_v4(request)
r3 = dispatch_v4(request)
assert r1 == r2 == r3

# MCCFR with seed=42
r1 = dispatch_v4(request_seed42)
r2 = dispatch_v4(request_seed42)
assert r1 == r2

# MCCFR with different seeds
r1 = dispatch_v4(request_seed42)
r2 = dispatch_v4(request_seed999)
assert r1 != r2
```

**Result:**
```
PASS: vanilla-cfr deterministic across 3 calls
PASS: mccfr with seed=42 deterministic
PASS: mccfr with different seeds produces different results
```

**Evidence:** Vanilla CFR is deterministic by algorithm design; MCCFR seeds RNG at solve entry.

---

## Error Normalization

All validation errors follow consistent format:
- Field path in label (e.g., `"player0_combos[2].weight"`)
- Constraint in message (e.g., `"must be non-negative"`)
- Sorted lists for unknown/missing fields

**Sample errors from test suite:**
```
ValueError: version must be JSON integer 4
ValueError: unknown request fields: ['extra_field']
ValueError: missing payload fields: ['iterations', 'seed']
ValueError: starting_board[0] must be a JSON integer
ValueError: player0_combos[1].weight must be finite
ValueError: effective_stack must be positive
```

---

## Unchanged Legacy API Behavior

**Test coverage:**
- `tests/test_evaluator.py`: 20 passed (hand strength, 7-card best, wheel, tiebreaks)
- `tests/test_cards.py`: 9 passed (round-trip, strict parsing, duplicates)
- 426 total legacy tests passed (155s)

**No changes to:**
- `poker_solver/evaluator.py`
- `poker_solver/card.py`
- `poker_solver/deck.py`
- `poker_solver/lookup.py`
- `poker_solver/hand.py`
- `poker_solver/equity.py`

---

## Artifacts Retained

**Production-importing probes (in `/tmp`):**
- `/tmp/audit_api_v4_strict.py` (version, schema, types, bounds)
- `/tmp/audit_json_serialization.py` (JSON safety, mutation isolation)
- `/tmp/audit_determinism.py` (vanilla-cfr, mccfr seed behavior)

**Heartbeat:**
- `.hb/A03` (updated each batch)

---

## Conclusion

Strict v4 API contract fully enforced:

1. ✅ Envelope version 4.0/bool/string rejection
2. ✅ Strict flat request schema (unknown/missing/nested rejected)
3. ✅ Boolean rejection where numerics expected
4. ✅ Nonfinite numeric rejection
5. ✅ Bounds enforcement (positive/nonnegative)
6. ✅ Error normalization (consistent format, sorted lists)
7. ✅ Response JSON serialization (no NaN/Infinity)
8. ✅ Mutation isolation across calls
9. ✅ Deterministic outputs (vanilla-cfr unconditional, mccfr with seed)
10. ✅ Unchanged legacy API behavior (426 tests pass)

**Recommendation:** Candidate ready for merge.

---

**Auditor:** A03  
**Signed:** 2026-09-15T18:48:00Z
