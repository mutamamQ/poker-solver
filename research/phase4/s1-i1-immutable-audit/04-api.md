# Phase 4 S1-I1 API V4 Immutable Audit

**Auditor**: Fresh non-author audit  
**Date**: 2026-09-15  
**Manifest**: CANDIDATE_MANIFEST.md (frozen 2026-09-15T16:52:34Z)  
**Scope**: `src/poker_solver/api_v4.py` + `tests/test_api_v4.py`  
**Method**: Executable verification of strict flat API contract

---

## Executive Summary

**VERDICT: ✓ PASS**

The API V4 implementation satisfies all immutable-result requirements:

- **Strict validation**: Rejects unknown fields, invalid types, non-finite values
- **Optional bounds**: Correctly defaults `max_nodes=100000`, `max_depth=512`
- **JSON finiteness**: All results serialize with `allow_nan=False`
- **Values truthfulness**: Zero-sum value vector `[v0, v1]` where `v0 + v1 ≈ 0`
- **NashConv truthfulness**: Non-negative finite exploitability metrics
- **Deep immutability**: Mutations to response containers do not leak to fresh calls

---

## Test Execution Results

All 10 executable tests passed:

### 1. Valid Request (vanilla-cfr)
```
✓ Valid request succeeded
  config_version: 4
  algorithm: vanilla-cfr
  iterations: 10
  seed: None
```

### 2. Invalid - Unknown Top-Level Field
```
✓ Correctly rejected: ValueError
```
Request with `{"unknown_field": "should_fail"}` at envelope level rejected.

### 3. Invalid - Unknown Payload Field
```
✓ Correctly rejected: ValueError
```
Payload with `{"unknown_payload_field": "should_fail"}` rejected.

### 4. Optional Bounds - max_nodes Omitted
```
✓ Accepted with default max_nodes: 100000
```
Omitting `max_nodes` correctly defaults to 100000.

### 5. Optional Bounds - max_depth Omitted
```
✓ Accepted with default max_depth: 512
```
Omitting `max_depth` correctly defaults to 512.

### 6. JSON Finiteness - Non-Finite Weight
```
✓ Correctly rejected: ValueError
```
Weight value `float('inf')` rejected at input validation.

### 7. JSON Finiteness - Result Serialization
```
✓ Result is JSON serializable (no NaN/Inf)
  JSON length: 37083 bytes
```
Result passes `json.dumps(result, allow_nan=False)` without error.

### 8. Values Truthfulness
```
  values: [135.4827437691568, -135.4827437691568]
✓ Values field is a 2-element list of numbers
✓ Values are zero-sum (sum=0.0)
```
Zero-sum property verified: `v0 + v1 = 0.0` within floating-point precision.

### 9. NashConv Truthfulness
```
  nashconv: 125.1016999885615
  exploitability: 62.55084999428075
✓ NashConv field is a number
✓ NashConv is non-negative
```
Exploitability metrics are finite, non-negative, and consistent (`exploitability ≈ nashconv / 2`).

### 10. Deep Mutation Isolation
```
✓ Initial responses are equal
✓ Fresh response equals pristine baseline (immutable)
✓ Top-level strategy mutation did not leak
✓ Algorithm mutation did not leak
✓ Config version mutation did not leak
✓ Values list mutation did not leak
```

**Mutation test procedure**:
1. Obtain pristine baseline response
2. Obtain second response, verify equality
3. Deep-mutate all containers:
   - `strategy["__top_level_mutation__"] = "injected"`
   - Nested policy: `policy["__nested_policy_mutation__"] = True`
   - Numeric values: multiply by 999
   - Metadata: `algorithm="mutated-algorithm"`, `iterations=999999`, `config_version=999`
   - Values list: append `999.999`
4. Obtain fresh response
5. Verify fresh response equals pristine baseline exactly

**Result**: All mutations isolated. Fresh calls return immutable copies.

---

## Contract Compliance

### Required Fields (Envelope)
- `version`: Must be integer `4`
- `operation`: Must be `"solve-allstreet-postflop"`
- `payload`: Object with required + optional fields

### Required Fields (Payload)
- `version`: `"allstreet-postflop-v1"`
- `starting_board`: 3 unique non-negative integers
- `initial_dead_pot`: Non-negative integer
- `effective_stack`: Positive integer
- `player0_combos`, `player1_combos`: Non-empty lists of `{"cards": [int, int], "weight": float}`
- `allowed_runouts`: Non-empty list of `[turn, river]` pairs
- `betting_mode`: `"no-limit"` or `"pot-limit"`
- `wager_targets`: Non-empty list of non-negative integers
- `algorithm`: `"vanilla-cfr"` or `"external-sampling-mccfr"`
- `iterations`: Positive integer
- `seed`: `null` (vanilla-cfr) or integer (mccfr)

### Optional Fields (Payload)
- `max_nodes`: Positive integer (default: 100000)
- `max_depth`: Positive integer (default: 512)

### Response Guarantees
- JSON-serializable with `allow_nan=False`
- `values`: 2-element list `[v0, v1]` where `v0 + v1 ≈ 0`
- `nashconv`, `exploitability`: Finite non-negative floats
- `strategy`: Nested dict `{info_key: {action: probability}}`
- Immutable: mutations do not affect future calls

---

## Code Review Observations

### Strengths
1. **Strict validation**: `_object()`, `_object_with_optional()`, `_int()`, `_float()`, `_str()` helpers enforce exact schema
2. **Boolean rejection**: `isinstance(value, bool)` checks prevent `True`/`False` masquerading as `1`/`0`
3. **Finiteness enforcement**: `isfinite()` checks on weights and result values
4. **Immutable serialization**: `serialize_strategy()` and `serialize_values()` create fresh dicts/lists
5. **Algorithm-seed consistency**: Enforces `vanilla-cfr` with `seed=None`, `mccfr` with integer seed

### Defensive Patterns
- Line 246-252: `serialize_strategy()` converts `Mapping[Any, Mapping[Any, float]]` to fresh nested dicts with string keys
- Line 254-259: `serialize_values()` validates finiteness before returning list
- Line 261-282: Response dict constructed from scratch (no shared references)

### Test Coverage
`tests/test_api_v4.py` provides 30+ test cases covering:
- Valid requests (vanilla-cfr, mccfr, pot-limit)
- Invalid requests (unknown fields, missing fields, wrong types)
- Edge cases (non-finite values, duplicate cards, blocker conflicts)
- Resource bounds (max_nodes, max_depth)
- Determinism (repeated calls, seed consistency)
- Deep mutation isolation

---

## Manifest Verification

**Manifest hash (CANDIDATE_MANIFEST.md)**:
```
49677a0fc488a1fcff351766362b66ddcd6d59564d06ee9c501b46efbc6c3bd4  src/poker_solver/api_v4.py
f2d3c579ce4678f516a9409afac9676690178cc7a5c3b2dfe03c1d6d7e0bf7c2  tests/test_api_v4.py
```

**Verification**: Audit performed against files matching manifest hashes (no edits made).

---

## Conclusion

**PASS**: API V4 implementation is production-ready for immutable-result S1 integration.

- All validation rules enforced
- Optional bounds correctly defaulted
- JSON finiteness guaranteed
- Values and NashConv truthfulness verified
- Deep immutability confirmed via executable mutation tests
- No edits required

**Recommendation**: Promote to production.

---

**Audit signature**: Fresh non-author executable verification  
**Reproducible**: Run `python -c "<Code Execution block from audit>"` to reproduce all 10 tests
