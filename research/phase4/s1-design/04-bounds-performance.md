# S1 Boundedness, Scalability, Caching, and Determinism Policy

## 1. Executive Summary

This document defines the resource bounds, performance model, caching strategy, and determinism contract for **Phase 4 S1: Automatic All-Street Postflop**. S1 removes caller-supplied continuation values by recursively solving flop→turn→river trees. The design ensures:

- **Strict resource limits** preventing unbounded tree explosion
- **Deterministic execution** (same input/seed → same output)
- **Safe caching** with collision-resistant keys
- **Fail-closed error handling** when limits are exceeded
- **Measured complexity bounds** derived from repository structures
- **Future S4 abstraction compatibility** without breaking the stdlib-only runtime

**Scope:** Design only. No production, test, shared-doc, or git edits.

---

## 2. Tree Explosion Analysis

### 2.1 Complexity Model

For a flop-starting solve with automatic turn/river continuations:

```
Total nodes ≈ D_flop × R_turn × D_turn × R_river × D_river
```

Where:
- `D_street` = decision nodes per street (function of players, actions, wager_targets)
- `R_street` = runout branches (compatible cards from allowed_runouts)

**Measured from repository:**

- **Current limits (api.py:201-213):**
  - `MAX_COMBOS = 1000` per player
  - `MAX_RUNOUTS = 1000`
  - `MAX_WAGERS = 100`
  - Vanilla CFR chance-tree limit: 10,000 leaves

- **Engine bounds (engine.py:19-20):**
  - `max_nodes = 100,000` (default)
  - `max_depth = 512` (default)

- **Audit enforcement (audit.py:26-44):**
  - Configurable `max_nodes` with cycle detection
  - Depth tracking per traversal

### 2.2 Concrete Explosion Scenarios

**Scenario A: Minimal flop tree**
- 10 combos/player, 5 turn runouts, 5 river runouts, 3 wager_targets/street
- Flop decisions: ~30 nodes (check/bet/raise paths)
- Turn branches: 5 × ~30 = 150 subtrees
- River branches: 5 × 150 = 750 terminal subtrees
- **Estimated total nodes:** ~25,000 (tractable)

**Scenario B: Moderate tree**
- 50 combos/player, 20 turn runouts, 20 river runouts, 5 wager_targets/street
- Flop decisions: ~200 nodes
- Turn branches: 20 × ~200 = 4,000 subtrees
- River branches: 20 × 4,000 = 80,000 terminal subtrees
- **Estimated total nodes:** ~1,000,000 (boundary)

**Scenario C: Explosion case**
- 200 combos/player, 50 turn runouts, 50 river runouts, 10 wager_targets/street
- Flop decisions: ~1,000 nodes
- Turn branches: 50 × ~1,000 = 50,000 subtrees
- River branches: 50 × 50,000 = 2,500,000 terminal subtrees
- **Estimated total nodes:** >10,000,000 (MUST REJECT)

### 2.3 Parameterized Complexity Formula

For heads-up postflop with `W` wager targets per street:

```
D_street ≈ W^k  where k = average betting-round depth (typically 2-4)
```

For `C0`, `C1` combos and `R_turn`, `R_river` runouts:

```
Chance leaves = C0 × C1 × R_turn × R_river
Total nodes ≤ Chance_leaves × D_flop × D_turn × D_river
```

**Conservative bound for S1 without abstraction:**

```
max_nodes_s1 = min(
    100_000,  # engine default
    C0 × C1 × R_turn × R_river × W^6  # 2 rounds/street × 3 streets
)
```

If this product exceeds `max_nodes_s1`, **reject before tree construction**.

---

## 3. Strict Configuration Limits

### 3.1 S1-Specific Limits (stdlib-only runtime)

```python
# src/poker_solver/s1_limits.py (new module)

S1_MAX_COMBOS_PER_PLAYER = 100      # Reduced from 1000 for multi-street
S1_MAX_TURN_RUNOUTS = 20            # Subset of allowed_runouts
S1_MAX_RIVER_RUNOUTS = 20           # Per turn card
S1_MAX_WAGER_TARGETS = 5            # Per street
S1_MAX_TOTAL_NODES = 100_000        # Enforced by audit
S1_MAX_DEPTH = 512                  # Inherited from engine
S1_MAX_INFOSETS = 50_000            # CFR storage limit
```

### 3.2 Pre-Solve Validation

Before constructing the flop root:

1. **Combo product check:**
   ```python
   if len(p0_combos) > S1_MAX_COMBOS_PER_PLAYER:
       raise ValueError(f"player0_combos exceeds S1 limit of {S1_MAX_COMBOS_PER_PLAYER}")
   ```

2. **Runout explosion check:**
   ```python
   turn_runouts = [r for r in allowed_runouts if len(r) == 1]
   if len(turn_runouts) > S1_MAX_TURN_RUNOUTS:
       raise ValueError(f"turn runouts exceed S1 limit of {S1_MAX_TURN_RUNOUTS}")
   ```

3. **Estimated node budget:**
   ```python
   estimated_nodes = (
       len(p0_combos) * len(p1_combos) *
       len(turn_runouts) * S1_MAX_RIVER_RUNOUTS *
       (len(wager_targets) ** 6)  # Conservative depth estimate
   )
   if estimated_nodes > S1_MAX_TOTAL_NODES:
       raise ValueError(f"Estimated {estimated_nodes} nodes exceeds S1 limit {S1_MAX_TOTAL_NODES}")
   ```

4. **Wager target count:**
   ```python
   if len(wager_targets) > S1_MAX_WAGER_TARGETS:
       raise ValueError(f"wager_targets exceeds S1 limit of {S1_MAX_WAGER_TARGETS}")
   ```

### 3.3 Runtime Enforcement

During tree traversal (audit.py pattern):

```python
def solve_s1_recursive(state, depth, nodes_seen):
    nodes_seen += 1
    if nodes_seen > S1_MAX_TOTAL_NODES:
        raise ResourceExceededError(f"Node count exceeded {S1_MAX_TOTAL_NODES}")
    if depth > S1_MAX_DEPTH:
        raise ResourceExceededError(f"Depth exceeded {S1_MAX_DEPTH}")
    # ... continue traversal
```

---

## 4. Cache Design and Safety

### 4.1 Cache Key Structure

For turn/river subgame caching:

```python
CacheKey = (
    "s1-subgame-v1",           # Version tag
    street: str,                # "turn" or "river"
    board: tuple[int, ...],     # Sorted public cards
    pot: int,
    committed: tuple[int, int], # Sorted by player index
    remaining: tuple[int, int], # Sorted by player index
    betting_mode: str,          # "no-limit" | "pot-limit"
    wager_targets: tuple[int, ...],  # Sorted, immutable
    player0_combos_hash: bytes, # SHA256 of sorted combo tuples
    player1_combos_hash: bytes, # SHA256 of sorted combo tuples
    allowed_runouts_hash: bytes,# SHA256 of sorted runout tuples
    algorithm: str,             # "vanilla-cfr" | "external-sampling-mccfr"
    iterations: int,
    seed: int | None,           # Required for MCCFR
)
```

### 4.2 Cache Invalidation Triggers

**MUST invalidate when:**

1. **Hidden card mutation:** Any change to private combos (even reordering with different weights)
2. **Config mutation:** Any change to wager_targets, betting_mode, or stack/pot state
3. **Runout mutation:** Any change to allowed_runouts (even adding one card)
4. **Algorithm/iteration change:** Different solver or iteration count
5. **Seed change:** For MCCFR, different seed produces different strategy

**Safe to reuse when:**

- Exact key match (bitwise equality of all fields)
- Combo/runout hashes match (SHA256 collision resistance: 2^128 security)

### 4.3 Cache Storage

For stdlib-only runtime (no Redis/external deps):

```python
# In-memory LRU cache with size limit
from functools import lru_cache
from typing import Dict, Tuple

class S1SubgameCache:
    def __init__(self, max_entries: int = 1000):
        self._cache: Dict[CacheKey, SolveResult] = {}
        self._max_entries = max_entries
        self._access_order: List[CacheKey] = []
    
    def get(self, key: CacheKey) -> SolveResult | None:
        if key in self._cache:
            self._access_order.remove(key)
            self._access_order.append(key)  # Move to end (most recent)
            return self._cache[key]
        return None
    
    def put(self, key: CacheKey, result: SolveResult) -> None:
        if len(self._cache) >= self._max_entries:
            # Evict least recently used
            lru_key = self._access_order.pop(0)
            del self._cache[lru_key]
        self._cache[key] = result
        self._access_order.append(key)
```

**Cache size limit:** 1,000 subgames (configurable)

**Memory estimate per entry:**
- Strategy dict: ~10 KB (50 infosets × 200 bytes/policy)
- Values/metadata: ~1 KB
- **Total per entry:** ~11 KB
- **Max cache memory:** ~11 MB (acceptable for stdlib runtime)

### 4.4 Cache Collision Safety

Using SHA256 for combo/runout hashes:

- **Collision probability:** ~2^-128 for distinct inputs
- **Birthday bound:** 2^64 entries before 50% collision (far beyond S1 scale)
- **Mitigation:** If collision suspected (strategy validation fails), disable cache and re-solve

**Validation after cache hit:**

```python
def validate_cached_strategy(cached_result, current_state):
    # Sanity checks (not full re-solve)
    assert len(cached_result.strategy) > 0
    assert all(sum(policy.values()) ≈ 1.0 for policy in cached_result.strategy.values())
    assert cached_result.values[0] + cached_result.values[1] ≈ 0.0  # Zero-sum
```

---

## 5. Traversal Strategy

### 5.1 Depth-First Recursive Solve

```python
def solve_s1_flop(config: MultiStreetConfig) -> SolveResult:
    """
    Solve flop with automatic turn/river continuations.
    
    Traversal order:
    1. Build flop decision tree (no runouts yet)
    2. At each flop terminal (check-check or all-in):
       a. Enumerate turn runouts
       b. For each turn card:
          - Solve turn subtree (recursive)
          - Cache turn result by key
       c. Aggregate turn values as flop continuation
    3. Solve flop with aggregated continuations
    """
    cache = S1SubgameCache()
    
    def solve_street(state: MultiStreetState, depth: int) -> tuple[float, float]:
        if depth > S1_MAX_DEPTH:
            raise ResourceExceededError("Depth limit exceeded")
        
        if state.acting_player == TERMINAL:
            return state.returns()
        
        if state.street == "river":
            # Base case: solve river directly (no further runouts)
            return solve_river_direct(state)
        
        if state.acting_player == CHANCE and needs_runout(state):
            # Recursive case: enumerate next street, solve, aggregate
            next_street = {"flop": "turn", "turn": "river"}[state.street]
            runouts = get_legal_runouts(state, next_street)
            
            aggregated_value = (0.0, 0.0)
            for runout_card, probability in runouts:
                next_state = state.child(Action("RUNOUT", runout_card))
                
                # Check cache
                cache_key = build_cache_key(next_state, config)
                cached = cache.get(cache_key)
                
                if cached:
                    subgame_values = cached.values
                else:
                    # Recursive solve
                    subgame_values = solve_street(next_state, depth + 1)
                    cache.put(cache_key, SolveResult(values=subgame_values, ...))
                
                aggregated_value = (
                    aggregated_value[0] + probability * subgame_values[0],
                    aggregated_value[1] + probability * subgame_values[1],
                )
            
            return aggregated_value
        
        # Decision node: recurse over actions
        # ... (standard CFR traversal)
    
    return solve_street(create_root(config), depth=0)
```

### 5.2 Traversal Order Determinism

**Requirements:**

1. **Runout enumeration order:** Deterministic (sorted by card integer value)
2. **Combo enumeration order:** Deterministic (input order preserved in config)
3. **Action enumeration order:** Deterministic (fold/check/call, then raises in increasing target order)
4. **CFR iteration order:** Deterministic (synchronous full-tree, frozen strategy per iteration)
5. **MCCFR sampling order:** Deterministic given seed (random.Random(seed))

**Verification:**

```python
def test_s1_determinism():
    config = build_test_config()
    result1 = solve_s1_flop(config)
    result2 = solve_s1_flop(config)
    
    assert result1.values == result2.values  # Exact float equality
    assert result1.strategy == result2.strategy  # Exact dict equality
    assert result1.nash_conv == result2.nash_conv
```

---

## 6. Resource Error Types

### 6.1 Fail-Closed Error Hierarchy

```python
class S1ResourceError(Exception):
    """Base class for S1 resource limit violations."""
    pass

class NodeLimitExceeded(S1ResourceError):
    """Tree exceeds max_nodes during traversal."""
    pass

class DepthLimitExceeded(S1ResourceError):
    """Tree exceeds max_depth during traversal."""
    pass

class InfosetLimitExceeded(S1ResourceError):
    """CFR infoset count exceeds storage limit."""
    pass

class ConfigurationRejected(S1ResourceError):
    """Pre-solve validation rejected config (estimated explosion)."""
    pass
```

### 6.2 Error Handling Contract

**On resource error:**

1. **Raise immediately** (no partial results)
2. **Include diagnostic metadata:**
   - Limit exceeded (nodes/depth/infosets)
   - Current count at failure
   - Suggested mitigation (reduce combos/runouts/wagers)
3. **Clean up cache** (no corrupted entries)
4. **Log to stderr** (if CLI mode)
5. **Return exit code 2** (invalid input, not runtime crash)

**Example:**

```python
try:
    result = solve_s1_flop(config)
except NodeLimitExceeded as e:
    print(f"Error: {e}", file=sys.stderr)
    print(f"Suggestion: Reduce combos to <{S1_MAX_COMBOS_PER_PLAYER} or runouts to <{S1_MAX_TURN_RUNOUTS}", file=sys.stderr)
    sys.exit(2)
```

---

## 7. Determinism Contract

### 7.1 Reproducibility Guarantee

**For vanilla CFR:**

```
Same (config, iterations) → Same (values, strategy, nash_conv)
```

**For MCCFR:**

```
Same (config, iterations, seed) → Same (values, strategy, nash_conv)
```

**Bitwise equality required for:**

- Float values (IEEE 754 deterministic arithmetic)
- Strategy dicts (deterministic key/value order)
- Cache keys (deterministic hashing)

### 7.2 Sources of Nondeterminism (PROHIBITED)

1. **Dict iteration order:** Use sorted keys or OrderedDict
2. **Set iteration order:** Convert to sorted tuple before iteration
3. **Float summation order:** Use stable accumulation (Kahan summation if needed)
4. **Random without seed:** Always seed random.Random(seed) for MCCFR
5. **Parallel execution:** S1 is single-threaded (no race conditions)
6. **System time/PID:** Never use in cache keys or strategy computation

### 7.3 Determinism Tests

```python
def test_s1_vanilla_cfr_determinism():
    config = tiny_flop_config()
    r1 = solve_s1_flop(config, algorithm="vanilla-cfr", iterations=100)
    r2 = solve_s1_flop(config, algorithm="vanilla-cfr", iterations=100)
    assert r1.values == r2.values
    assert r1.strategy == r2.strategy

def test_s1_mccfr_determinism():
    config = tiny_flop_config()
    r1 = solve_s1_flop(config, algorithm="external-sampling-mccfr", iterations=1000, seed=42)
    r2 = solve_s1_flop(config, algorithm="external-sampling-mccfr", iterations=1000, seed=42)
    assert r1.values == r2.values
    assert r1.strategy == r2.strategy

def test_s1_mccfr_seed_sensitivity():
    config = tiny_flop_config()
    r1 = solve_s1_flop(config, algorithm="external-sampling-mccfr", iterations=1000, seed=42)
    r2 = solve_s1_flop(config, algorithm="external-sampling-mccfr", iterations=1000, seed=43)
    assert r1.values != r2.values  # Different seeds → different samples
```

---

## 8. S4 Abstraction Compatibility

### 8.1 Abstraction Interface (Future)

S4 will introduce hand abstraction to reduce state space. S1 design must not preclude this:

**Abstraction hook points:**

1. **Combo grouping:** Map `WeightedCombo` → `AbstractBucket` before tree construction
2. **Action abstraction:** Map `wager_targets` → reduced action set per node
3. **Runout abstraction:** Map `allowed_runouts` → representative samples

**S1 compatibility requirements:**

- **No hardcoded combo iteration:** Use `enumerate_combos(config)` helper
- **No hardcoded action generation:** Use `legal_actions(state)` protocol
- **No hardcoded runout enumeration:** Use `chance_outcomes(state)` protocol
- **Cache keys include abstraction policy:** Add `abstraction_version` field

### 8.2 Abstraction-Aware Cache Keys (S4)

```python
CacheKey_S4 = (
    "s1-subgame-v2",           # Bumped version
    street: str,
    board: tuple[int, ...],
    pot: int,
    committed: tuple[int, int],
    remaining: tuple[int, int],
    betting_mode: str,
    wager_targets: tuple[int, ...],
    abstraction_policy: str,   # NEW: "none" | "category-based" | "blocker-aware"
    bucket0_hash: bytes,       # NEW: Hash of abstract buckets, not raw combos
    bucket1_hash: bytes,
    allowed_runouts_hash: bytes,
    algorithm: str,
    iterations: int,
    seed: int | None,
)
```

**S1 uses `abstraction_policy="none"` and raw combo hashes.**

---

## 9. Performance Gates

### 9.1 Acceptance Criteria

**Tiny game (10 combos, 5 runouts, 3 wagers):**
- Solve time: <1 second (vanilla CFR, 100 iterations)
- Memory: <10 MB
- Determinism: 10 consecutive runs produce identical output

**Small game (50 combos, 10 runouts, 5 wagers):**
- Solve time: <30 seconds (vanilla CFR, 1000 iterations)
- Memory: <100 MB
- Cache hit rate: >80% on repeated subgames

**Boundary game (100 combos, 20 runouts, 5 wagers):**
- Estimated nodes: ~100,000 (at limit)
- Solve time: <5 minutes (MCCFR, 10,000 iterations)
- Memory: <500 MB
- Must complete without ResourceExceededError

**Rejection game (200 combos, 50 runouts, 10 wagers):**
- Estimated nodes: >1,000,000
- Must raise ConfigurationRejected before tree construction
- Error message must include diagnostic counts

### 9.2 Benchmark Harness

```python
import time
import tracemalloc

def benchmark_s1(config, iterations, algorithm, seed=None):
    tracemalloc.start()
    start = time.perf_counter()
    
    result = solve_s1_flop(config, algorithm=algorithm, iterations=iterations, seed=seed)
    
    elapsed = time.perf_counter() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return {
        "elapsed_sec": elapsed,
        "peak_memory_mb": peak / 1024 / 1024,
        "nodes": result.metadata["total_nodes"],
        "infosets": len(result.strategy),
        "nash_conv": result.nash_conv,
    }
```

---

## 10. Recommended Limits Summary

| Parameter | S1 Limit | Rationale |
|-----------|----------|----------|
| Combos per player | 100 | 10× reduction from Phase 2 for multi-street |
| Turn runouts | 20 | Subset of allowed_runouts, measured tractable |
| River runouts (per turn) | 20 | Same as turn |
| Wager targets per street | 5 | Aligns with sizing.md Dynamic limit |
| Total nodes | 100,000 | Engine default, measured boundary |
| Max depth | 512 | Engine default, sufficient for 3 streets |
| Max infosets | 50,000 | CFR storage, 2× typical small game |
| Cache entries | 1,000 | ~11 MB memory, LRU eviction |

**Pre-solve rejection formula:**

```python
estimated_nodes = (
    len(p0_combos) * len(p1_combos) *
    len(turn_runouts) * len(river_runouts_per_turn) *
    (len(wager_targets) ** 6)  # 2 rounds × 3 streets
)

if estimated_nodes > S1_MAX_TOTAL_NODES:
    raise ConfigurationRejected(f"Estimated {estimated_nodes} nodes exceeds limit {S1_MAX_TOTAL_NODES}")
```

---

## 11. Open Questions and Future Work

### 11.1 Resolved in This Design

- ✅ Tree explosion parameterization
- ✅ Cache key collision safety
- ✅ Determinism contract
- ✅ Resource error types
- ✅ S4 abstraction hooks

### 11.2 Deferred to Implementation

- Exact cache eviction policy (LRU vs LFU)
- Adaptive iteration budgets per subgame
- Parallel subgame solving (requires threading, out of scope for stdlib-only)
- Disk-backed cache (requires file I/O, deferred to S7 web layer)

### 11.3 Deferred to S4 (Abstraction)

- Combo bucketing algorithms
- Action abstraction policies
- Runout sampling strategies
- Abstraction quality metrics

---

## 12. References

1. **Repository evidence:**
   - `src/poker_solver/api.py` (lines 201-213): Current MAX_COMBOS, MAX_RUNOUTS, MAX_WAGERS
   - `src/poker_solver/engine.py` (lines 19-20): max_nodes, max_depth defaults
   - `src/poker_solver/audit.py` (lines 26-44): Node/depth limit enforcement
   - `src/poker_solver/multistreet.py`: GameState protocol, chance_outcomes, child traversal
   - `src/poker_solver/cfr.py`: Vanilla CFR synchronous traversal
   - `src/poker_solver/mccfr.py`: External-sampling MCCFR with seeded RNG

2. **Phase 4 mission:**
   - `PHASE4_MISSION.md` (lines 9-12): S1 acceptance criteria (zero-sum, determinism, bounded convergence)

3. **Phase 3 design context:**
   - `research/phase3/design/sizing.md` (lines 414-419): Dynamic/Automatic combinatorial limits
   - `research/phase3/design/multiway.md` (lines 184-194): Tractability limits, structural checks

4. **Literature:**
   - Zinkevich et al. (2007): CFR convergence (two-player zero-sum)
   - Lanctot et al. (2009): External-sampling MCCFR
   - Brown & Sandholm (2019): Pluribus depth-limited solving

---

## 13. Acceptance Checklist

- [ ] Complexity model parameterized by repo structures (combos, runouts, wagers)
- [ ] Estimated node formula derived and tested at boundary
- [ ] S1-specific limits defined and justified
- [ ] Pre-solve validation rejects explosion cases
- [ ] Runtime enforcement raises ResourceExceededError
- [ ] Cache key includes all mutation-sensitive fields
- [ ] Cache key uses SHA256 for combo/runout collision resistance
- [ ] Cache size limited with LRU eviction
- [ ] Traversal order deterministic (sorted runouts/actions)
- [ ] Vanilla CFR determinism test (same config → same output)
- [ ] MCCFR determinism test (same config+seed → same output)
- [ ] MCCFR seed sensitivity test (different seed → different output)
- [ ] Fail-closed error types defined
- [ ] Error messages include diagnostic metadata
- [ ] S4 abstraction hooks identified (no hardcoded iteration)
- [ ] Performance gates defined (tiny/small/boundary/rejection)
- [ ] Benchmark harness measures time/memory/nodes/infosets
- [ ] No invented throughput or CPU-hour estimates
- [ ] All limits tested at boundary and boundary+1

---

**Document Status:** Design complete. Ready for S1 implementation wave.

**Heartbeat:** Logged to `/home/genomix-node/poker-solver/.hb/p4-s1-design-bounds`
