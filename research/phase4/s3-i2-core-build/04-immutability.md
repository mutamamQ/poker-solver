# S3-I2-G4R: Deep immutability and detachment analysis

**Analyst:** C3I2-G4R (read-only immutability specialist, retry)
**Timestamp:** 2026-09-16T08:42:41Z
**Status:** COMPLETE_ANALYSIS
**Blocker count:** 0

## 1. Mandate and scope

Analyze the minimal deep-detachment implementation required for `NPlayerPreflopSolveResult` under normal construction and `dataclasses.replace`. Nested strategy maps (information-key → action → probability) and nested metadata map/list values must be detached and read-only, while hashable information keys and Action keys remain intact.

**Exclusive writable paths:**
- `/home/genomix-node/poker-solver/research/phase4/s3-i2-core-build/04-immutability.md`
- `/home/genomix-node/poker-solver/research/phase4/s3-i2-core-build/.hb/C3I2-G4R`

**Read-only inputs:**
- `/home/genomix-node/poker-solver/research/phase4/s3-i2-red/RED_MANIFEST.md`
- `tests/test_nplayer_preflop_solve.py` (lines 227-238: deep mutation test)
- Architecture section 2.5 (matrix game reference)
- Existing freeze helpers in `allstreet.py`, `nplayer_preflop.py`, `engine.py`

## 2. RED evidence

RED_MANIFEST.md (frozen 2026-09-16T08:36:00Z) authenticates test file SHA-256 `45291a2e...` covering 89 failures + 19 passing controls.

**Critical test (lines 227-238):**
```python
# Public result construction must detach caller-owned outer AND inner maps.
source = {k: dict(p) for k, p in first.strategy.items()}
metadata = {"nested": {"flags": [False]}}
detached = replace(first, strategy=source, metadata=metadata)
source[key][action] = -99
source.clear()
metadata["nested"]["flags"].append(True)
assert detached.strategy == second.strategy
assert tuple(detached.metadata["nested"]["flags"]) == (False,)
with pytest.raises(TypeError):
    detached.metadata["nested"]["new"] = True
```

**Assertions:**
1. Mutating the caller's `source` dict after `replace()` must not affect `detached.strategy`
2. Mutating nested `source[key]` inner dicts must not affect `detached.strategy`
3. Mutating caller's `metadata` nested dict/list after `replace()` must not affect `detached.metadata`
4. `detached.metadata` nested containers must be read-only (TypeError on write)

## 3. Existing freeze patterns

### 3.1 `allstreet.py` (lines 20-28): `_deep_freeze`
```python
def _deep_freeze(value: Any) -> Any:
    """Recursively detach and freeze standard mutable containers."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_deep_freeze(item) for item in value)
    return value
```

**Behavior:** Recursively copies and freezes all nested standard containers. Maps become `MappingProxyType`, lists/tuples become tuples, sets become frozensets. Leaves (strings, numbers, hashable objects) pass through unchanged.

### 3.2 `engine.py` (lines 40-44): `_freeze_strategy`
```python
def _freeze_strategy(strategy) -> Mapping[Hashable, Mapping[Action, float]]:
    return MappingProxyType({
        key: MappingProxyType(dict(policy))
        for key, policy in strategy.items()
    })
```

**Behavior:** Two-level shallow freeze. Outer map and each inner policy map wrapped in `MappingProxyType`. Does NOT recursively freeze keys or values beyond the two-level structure.

### 3.3 `nplayer_preflop.py` (lines 106-109): `_freeze_expression`
```python
def _freeze_expression(expression: Mapping[str, object]) -> Mapping[str, object]:
    copied = dict(expression)
    validate_size_expression(copied)
    return _FrozenExpression(tuple(sorted(copied.items())))
```

**Behavior:** Domain-specific immutable hashable mapping for sizing rules. Not applicable to general nested containers.

## 4. Required implementation

### 4.1 Strategy detachment

**Structure:** `strategy: Mapping[InfoKey, Mapping[Action, float]]`

**Requirements:**
- InfoKey (hashable tuple) and Action (frozen dataclass) remain unchanged
- Outer map must be detached from caller's dict
- Each inner policy map must be detached from caller's nested dicts
- Both levels must be read-only

**Minimal implementation:**
```python
def _freeze_strategy(strategy) -> Mapping[Hashable, Mapping[Action, float]]:
    return MappingProxyType({
        key: MappingProxyType(dict(policy))
        for key, policy in strategy.items()
    })
```

**Rationale:** `engine.py:_freeze_strategy` already implements exactly this pattern. The `dict(policy)` call creates a shallow copy of each inner map, detaching it from the caller's nested dict. `MappingProxyType` wraps both levels for read-only access. Keys (InfoKey tuples) and values (Action instances, floats) are immutable or copied, so no deeper recursion is needed.

### 4.2 Metadata detachment

**Structure:** `metadata: Mapping[str, object]` (arbitrary nested dicts/lists/primitives)

**Requirements:**
- Outer map must be detached from caller's dict
- Nested dicts must be detached and read-only
- Nested lists must be detached and converted to tuples
- Arbitrary nesting depth

**Minimal implementation:**
```python
def _deep_freeze(value: Any) -> Any:
    """Recursively detach and freeze standard mutable containers."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_deep_freeze(item) for item in value)
    return value
```

**Rationale:** `allstreet.py:_deep_freeze` already implements exactly this pattern. It recursively traverses nested containers, copying and freezing at each level. The test's `metadata["nested"]["flags"]` structure (dict containing dict containing list) requires this recursive approach.

### 4.3 Result `__post_init__` integration

**Location:** `NPlayerPreflopSolveResult.__post_init__` (to be implemented in `nplayer_preflop.py`)

**Required transformations:**
```python
def __post_init__(self) -> None:
    # Strategy: two-level detachment
    object.__setattr__(self, "strategy", MappingProxyType({
        key: MappingProxyType(dict(policy))
        for key, policy in self.strategy.items()
    }))

    # Metadata: recursive deep freeze
    object.__setattr__(self, "metadata", _deep_freeze(self.metadata))
```

**Execution context:** `__post_init__` runs after `__init__` assigns constructor arguments to fields. For `dataclasses.replace(result, strategy=source, metadata=metadata)`, the replacement values are assigned first, then `__post_init__` runs, applying the freeze transformations to the caller-provided mutable containers.

## 5. Exact test mapping

**Line 228:** `source = {k: dict(p) for k, p in first.strategy.items()}`
- Caller creates mutable outer dict with mutable inner dicts

**Line 229:** `metadata = {"nested": {"flags": [False]}}`
- Caller creates mutable nested dict/list structure

**Line 230:** `detached = replace(first, strategy=source, metadata=metadata)`
- `replace()` constructs new result with caller's mutable containers
- `__post_init__` applies `_freeze_strategy` to `strategy` → outer/inner `MappingProxyType` wrapping `dict()` copies
- `__post_init__` applies `_deep_freeze` to `metadata` → recursive `MappingProxyType`/tuple conversion

**Line 231:** `source[key][action] = -99`
- Mutates caller's nested dict
- **Assertion (line 234):** `detached.strategy == second.strategy` passes because `dict(policy)` in `_freeze_strategy` created a detached copy

**Line 232:** `source.clear()`
- Mutates caller's outer dict
- **Assertion (line 234):** Still passes because outer `MappingProxyType` wraps a new dict comprehension

**Line 233:** `metadata["nested"]["flags"].append(True)`
- Mutates caller's nested list
- **Assertion (line 235):** `tuple(detached.metadata["nested"]["flags"]) == (False,)` passes because `_deep_freeze` converted the list to a tuple containing the original single element

**Line 236-237:** `with pytest.raises(TypeError): detached.metadata["nested"]["new"] = True`
- Attempts to mutate the result's nested dict
- **Assertion:** Raises `TypeError` because `_deep_freeze` wrapped `metadata["nested"]` in `MappingProxyType`

## 6. Architecture alignment

The authoritative source is `ARCHITECTURE_PHASE4_S3.md` §2.5, which requires a frozen solve result containing a detached immutable strategy, N expected values, optional exhaustive certificate, metadata/provenance, and `approximate=False`. The deep `dataclasses.replace` assertions in `test_nplayer_preflop_solve.py` make that detachment requirement executable. The initially cited Phase-3 nodelock matrix document is unrelated and is not S3 authority.

## 7. Minimal implementation summary

**Required additions to `nplayer_preflop.py`:**

1. **Import `_deep_freeze` pattern** (or define locally):
   ```python
   def _deep_freeze(value: Any) -> Any:
       if isinstance(value, Mapping):
           return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
       if isinstance(value, (list, tuple)):
           return tuple(_deep_freeze(item) for item in value)
       if isinstance(value, (set, frozenset)):
           return frozenset(_deep_freeze(item) for item in value)
       return value
   ```

2. **Define `NPlayerPreflopSolveResult` dataclass** (frozen=True, slots=True):
   ```python
   @dataclass(frozen=True, slots=True)
   class NPlayerPreflopSolveResult:
       strategy: Mapping[Hashable, Mapping[Action, float]]
       expected_values: tuple[float, ...]
       metadata: Mapping[str, object]
       certificate: UnilateralDeviationCertificate | None
       algorithm: str
       iterations: int
       config_version: int
       game_version: str
       max_nodes: int
       max_depth: int
       provenance: str
       approximate: bool

       def __post_init__(self) -> None:
           # Two-level strategy detachment
           object.__setattr__(self, "strategy", MappingProxyType({
               key: MappingProxyType(dict(policy))
               for key, policy in self.strategy.items()
           }))
           # Recursive metadata detachment
           object.__setattr__(self, "metadata", _deep_freeze(self.metadata))
   ```

**No changes required to:**
- Information keys (already hashable tuples)
- Action keys (already frozen dataclass instances)
- Float values (immutable primitives)
- Other result fields (primitives, tuples, or explicitly frozen)

## 8. Verification

The RED test `test_solve_deterministic_finite_immutable_result` (lines 189-238) exercises:
- Normal construction: `first = _solve(config, iterations=3)` → `__post_init__` applies freeze
- `dataclasses.replace`: `detached = replace(first, strategy=source, metadata=metadata)` → `__post_init__` applies freeze to replacement values
- Outer mutation: `source.clear()` → detached strategy unaffected
- Nested mutation: `source[key][action] = -99` → detached strategy unaffected
- Nested metadata mutation: `metadata["nested"]["flags"].append(True)` → detached metadata unaffected
- Read-only enforcement: `detached.metadata["nested"]["new"] = True` → TypeError

**All assertions map to the specified implementation.**

## 9. Conclusion

**COMPLETE_ANALYSIS:** The minimal deep-detachment implementation for `NPlayerPreflopSolveResult` requires:

1. Two-level `MappingProxyType` wrapping with `dict()` copy for `strategy` (pattern already exists in `engine.py:_freeze_strategy`)
2. Recursive `_deep_freeze` for `metadata` (pattern already exists in `allstreet.py:_deep_freeze`)
3. Application in `__post_init__` via `object.__setattr__` (standard frozen dataclass pattern)

**Blocker count:** 0

Hashable information keys and Action keys remain intact. Nested strategy maps and nested metadata containers are detached and read-only. The implementation satisfies all RED test assertions (lines 227-238) under both normal construction and `dataclasses.replace`.

## Parent reconciliation

The parent accepted the two-level strategy freeze and recursive metadata freeze analysis. It corrected the unrelated Phase-3 architecture citation and restored the authoritative S3 result fields `UnilateralDeviationCertificate | None` and `approximate: bool`. No valid child completion heartbeat was written; parent-authored completion evidence is stored separately.
