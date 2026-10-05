# Phase 4 S1-I1 Result Immutability Audit

**Auditor:** Non-author independent verification  
**Date:** 2026-09-15  
**Candidate:** research/phase4/s1-i1-immutable-audit/CANDIDATE_MANIFEST.md  
**Base commit:** 7a817e618a3c0898b531e88440b490323c62b49b  

## Manifest Verification

✓ All 8 candidate file hashes verified against working tree:

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

## Immutability Test Results

### Test Configuration
- **Module:** `poker_solver.allstreet.AllStreetSolveResult`
- **Entry point:** `solve_allstreet_postflop()`
- **Test scenario:** Minimal flop-to-river solve (1 combo per player, 1 runout, 1 bet size)
- **Iterations:** 50 (vanilla-cfr)

### Test 1: Direct Field Mutation ✓ PASS

Attempted mutations on result object:
- `result.values = (999.0, -999.0)` → **FrozenInstanceError**
- `result.nash_conv = 999.0` → **FrozenInstanceError**
- `result.strategy = {}` → **FrozenInstanceError**
- `result.metadata = {}` → **FrozenInstanceError**

**Mechanism:** `@dataclass(frozen=True, slots=True)` on `AllStreetSolveResult`

**Verification:** All fields retained original values and object IDs after mutation attempts.

### Test 2: Nested Strategy Mutation ✓ PASS

Attempted mutations on strategy mapping:
- `result.strategy[key] = {"fold": 1.0}` → **TypeError**
- `result.strategy['__injected__'] = {"fold": 1.0}` → **TypeError**
- `result.strategy[key][action] = 0.999` → **TypeError**

**Mechanism:** `MappingProxyType` wrapping at two levels:
1. Top-level strategy: `MappingProxyType({info_key: policy, ...})`
2. Nested policies: `MappingProxyType({action: prob, ...})`

**Verification:** Strategy entries and nested policies retained original values and object IDs.

### Test 3: Metadata Mutation ✓ PASS

Attempted mutations on metadata mapping:
- `result.metadata['terminal_count'] = 999999` → **TypeError**
- `result.metadata['__injected__'] = 'malicious'` → **TypeError**

**Mechanism:** `MappingProxyType(dict(self.metadata))` in `AllStreetSolveResult.__post_init__`

**Verification:** Metadata entries retained original values.

### Test 4: Separate Solves Isolation ✓ PASS

Two identical solves with same config:
- `result.values == result2.values` → **True** (deterministic)
- `id(result.strategy) != id(result2.strategy)` → **True** (separate objects)

**Verification:** Each solve produces independent immutable result objects.

### Test 5: Strategy Readability ✓ PASS

Strategy mapping remains fully readable:
- 52 strategy entries accessible via iteration
- All keys and nested policies readable via dict protocol
- Sample entry:
  ```python
  ('multistreet-v1', 0, (3, 4), (0, 1, 2), (), 100, (0, 0), (200, 200), 'no-limit'):
    {Action(kind='CHECK', amount=0): 0.9637890625, Action(kind='RAISE', amount=50): 0.0362109375}
  ```

**Verification:** `MappingProxyType` preserves full read access while blocking writes.

## Implementation Review

### AllStreetSolveResult (allstreet.py:126-157)

```python
@dataclass(frozen=True, slots=True)
class AllStreetSolveResult:
    """Immutable result from all-street postflop solve."""
    algorithm: str
    seed: int | None
    iterations: int
    values: tuple[float, float]
    nash_conv: float
    half_nash_conv: float
    strategy: Mapping[Any, Mapping[Any, float]]
    # ... 10 more fields

    def __post_init__(self) -> None:
        frozen_strategy = MappingProxyType(
            {
                info_key: MappingProxyType(dict(policy))
                for info_key, policy in self.strategy.items()
            }
        )
        object.__setattr__(self, "strategy", frozen_strategy)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
```

**Key mechanisms:**
1. `frozen=True` prevents direct field assignment
2. `slots=True` prevents dynamic attribute addition
3. `__post_init__` wraps mutable mappings in `MappingProxyType`
4. Nested policies also wrapped for deep immutability

### API v4 Serialization (api_v4.py:245-282)

The `dispatch_v4()` function serializes the immutable result to JSON-safe dict:
- Strategy: `serialize_strategy()` converts `MappingProxyType` → nested `dict` with string keys
- Values: `serialize_values()` converts tuple → list with finite validation
- Metadata: `dict(result.metadata)` unwraps `MappingProxyType`

**No mutation risk:** Serialization creates new dicts; original result remains immutable.

## Verdict

**✓ IMMUTABILITY: PASS**

All executable probes confirm:
1. ✓ Direct field mutation blocked (dataclass `frozen=True`)
2. ✓ Top-level strategy mutation blocked (`MappingProxyType`)
3. ✓ Nested policy mutation blocked (nested `MappingProxyType`)
4. ✓ Metadata mutation blocked (`MappingProxyType`)
5. ✓ Separate solves produce isolated immutable objects
6. ✓ Strategy and metadata remain fully readable

The `AllStreetSolveResult` dataclass provides **deep immutability** for all result fields, including nested strategy and metadata mappings. No construction aliasing or cross-solve contamination detected.

## Recommendation

**APPROVE** for S1-I1 immutable-result gate.

The implementation satisfies all immutability requirements:
- Result objects are frozen at construction
- Nested collections are recursively wrapped in read-only proxies
- Separate solves produce independent objects
- All data remains accessible for downstream consumption

---

**Audit complete:** 2026-09-15T16:53:12Z
