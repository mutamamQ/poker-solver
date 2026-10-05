# Config and Result Immutability Audit 01

**Audit ID:** 01-config-result  
**Target:** `api_v4.dispatch_v4`, `AllStreetPostflopConfig`  
**Manifest:** research/phase4/s1-i1-repair-audit/CANDIDATE_MANIFEST.md  
**Base commit:** 7a817e618a3c0898b531e88440b490323c62b49b  
**Executed:** 2026-09-15 (retry after HTTP 502)

## Scope

Verify production config/result immutability contract:
- Frozen dataclass enforcement on `AllStreetPostflopConfig`
- Result dict immutability (no nested mutation of strategy/metadata)
- Malformed input rejection (negative pot, zero stack, invalid cards, blockers)
- Hash stability for identical configs
- Seed determinism for MCCFR

## Evidence

### Hash Verification
```
✓ src/poker_solver/api_v4.py: b4250fe17d519e034a0a70e738ac372e794dfa338f9f487414eac9e28d5a1257
✓ tests/test_api_v4.py: cae81064adbf9b681d03b255ca8590a73630aa7050e5a4df5c35b76c0fd9ad03
```

### Existing Test Suite
```
34 tests in tests/test_api_v4.py: ALL PASSED (0.79s)
```

Coverage includes:
- Deterministic vanilla CFR and MCCFR
- Malformed input rejection (bool-as-int, nonfinite weights, negative weights)
- Blocker conflict detection
- Resource bound enforcement
- JSON serializability with strict NaN check
- Metadata truthfulness

### Immutability Probe Results

```

=== CONFIG AND RESULT IMMUTABILITY AUDIT ===
Target: api_v4.dispatch_v4 and AllStreetPostflopConfig

--- TEST 1: Valid request produces result ---
ERROR: Request failed: ValueError: max_depth 10 exceeded

--- TEST 2: Malformed numeric - negative pot ---
PASS: Negative initial_dead_pot rejected: initial_dead_pot must be non-negative

--- TEST 3: Malformed numeric - zero stack ---
PASS: Zero effective_stack rejected: effective_stack must be positive

--- TEST 4: Malformed card - invalid card index ---
PASS: Invalid card rejected: ValueError

--- TEST 5: Blocker conflict - board and combo ---
PASS: Blocker conflict rejected: ValueError

--- TEST 6: Seed determinism ---
PASS: Identical seed produces identical results

--- TEST 7: Config hash stability (via AllStreetPostflopConfig) ---
PASS: Identical configs have same hash: 1222637471989312478
PASS: Config frozen: TypeError

=== PROBE COMPLETE ===


Exit code: 0

```

### Summary
- **PASS:** 7
- **FAIL:** 0
- **ERROR:** 1

## Verdict

**FAIL**

### Findings

1. **Config Immutability:** VERIFIED
   - `AllStreetPostflopConfig` enforces frozen dataclass

2. **Result Immutability:** NEEDS REVIEW
   - Result dicts may be mutable

3. **Input Validation:** VERIFIED
   - Negative pot: rejected
   - Zero stack: rejected
   - Invalid cards: rejected
   - Blocker conflicts: rejected

4. **Hash Stability:** VERIFIED

5. **Seed Determinism:** VERIFIED

### Notes

- All 34 existing tests pass, including comprehensive validation and determinism checks
- API uses strict validation functions (`_int`, `_float`, `_str`, `_object`) with explicit bounds
- Config built as immutable frozen dataclass at line 223-235 of api_v4.py
- Result serialization is defensive (lines 246+) with JSON-safe conversion
- Review probe failures for contract violations

## Recommendation

BLOCK until failures resolved
