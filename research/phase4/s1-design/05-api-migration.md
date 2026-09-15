# S1 API and Migration Design: No-Caller-Continuation Standard Flop Request

**Date:** 2026-09-15 (UTC)  
**Scope:** Phase 4 S1 — public API, JSON schema, CLI, and backward-compatible migration  
**Status:** Design specification (implementation deferred)  
**Workstream:** 05-api-migration

---

## 1. Executive Summary

This document defines the **public typed API, JSON schema, CLI interface, and migration path** for S1 automatic all-street continuation. It specifies:

- **Standard mode:** No caller-supplied continuation values; automatic flop→turn→river traversal
- **Reference/advanced mode:** Explicit continuation values preserved for testing, oracles, and edge cases
- **Strict validation:** Malformed-input rejection matrix, resource limits, defensive copies
- **Backward compatibility:** All v1/v2/v3 behavior unchanged; S1 is additive
- **Deterministic output:** Same input/seed → same strategy/values
- **Truth labels:** Approximate vs. exact, provenance strings

**Out of scope:** Implementation, tests, shared documentation, git operations.

---

## 2. Design Principles

### 2.1 Additive Evolution

- **v1 (river):** Single-street with explicit ranges/wagers (unchanged)
- **v2 (multi-street):** Flop/turn/river with explicit runouts (unchanged)
- **v3 (utilities):** Bounded Phase-3 utilities (ICM, ranges, inference) (unchanged)
- **S1 extension:** v2 + automatic continuation flag (new optional field)

### 2.2 Fail-Closed Validation

- Reject unknown fields
- Reject bool-as-int, non-finite weights, negative values
- Reject empty combo lists, zero-total weights
- Reject resource-limit violations before tree construction
- Reject missing continuation values in explicit mode

### 2.3 Determinism Contract

- Vanilla CFR: same config → same output (no seed)
- MCCFR: same config + seed → same output
- Runout order: deterministic enumeration
- Sizing: deterministic candidate selection
- Cache keys: collision-resistant (SHA256 hashes)

### 2.4 Truth Labeling

- `approximate: false` — complete finite-tree CFR to configured iterations
- `approximate: true` — checkdown-equity, rollout, or neural continuation
- `provenance: str` — human-readable method description

---

## 3. Typed Python API

### 3.1 Configuration Dataclass Extension

```python
# src/poker_solver/api.py (extension)

from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True, slots=True)
class MultiStreetConfigS1:
    """Extended multi-street configuration with automatic continuation."""
    
    # Inherited from MultiStreetConfig (v2)
    version: int  # Must be 2
    starting_street: Literal["flop", "turn", "river"]
    starting_board: tuple[int, ...]
    initial_dead_pot: int
    effective_stack: int
    player0_combos: tuple[WeightedCombo, ...]
    player1_combos: tuple[WeightedCombo, ...]
    allowed_runouts: tuple[tuple[int, ...], ...]
    betting_mode: Literal["no-limit", "pot-limit"]
    wager_targets: tuple[int, ...]
    
    # S1 extension
    continuation_mode: Literal["automatic", "explicit"] = "automatic"
    explicit_continuation: Mapping[ContinuationKey, tuple[float, float]] | None = None
    
    # S1 resource limits (optional overrides)
    s1_max_nodes: int = 100_000
    s1_max_depth: int = 512
    s1_turn_iteration_budget: int = 1_000
    s1_river_iteration_budget: int = 500
```

**Validation rules:**

1. If `continuation_mode == "automatic"`:
   - `explicit_continuation` must be `None`
   - `starting_street` must be `"flop"` or `"turn"`
   - `allowed_runouts` must be non-empty
   - Pre-solve resource check: `estimated_nodes ≤ s1_max_nodes`

2. If `continuation_mode == "explicit"`:
   - `explicit_continuation` must be a non-empty mapping
   - Every reachable closed leaf must have a continuation entry
   - Continuation values must be zero-sum: `sum(values) == 0.0` within `1e-9`

3. Resource limits:
   - `s1_max_nodes` must be positive integer ≤ 10_000_000
   - `s1_max_depth` must be positive integer ≤ 1024
   - Iteration budgets must be positive integers ≤ 1_000_000

### 3.2 Solve Function Signature

```python
def solve_multistreet_s1(
    config: MultiStreetConfigS1,
    algorithm: Literal["vanilla-cfr", "external-sampling-mccfr"],
    iterations: int,
    seed: int | None = None,
) -> SolveResult:
    """Solve a multi-street game with optional automatic continuation.
    
    Args:
        config: Validated S1 configuration
        algorithm: CFR variant
        iterations: Flop-level iterations (turn/river use config budgets)
        seed: Random seed (required for MCCFR, must be None for vanilla)
    
    Returns:
        SolveResult with values, exploitability, strategy, and metadata
    
    Raises:
        ValueError: Invalid config, resource limit exceeded, missing continuation
        ResourceExceededError: Runtime node/depth limit exceeded
    """
```

**Metadata extensions:**

```python
result.metadata = {
    "config_version": 2,
    "starting_street": "flop",
    "continuation_mode": "automatic",
    "s1_turn_solves": 42,  # Number of turn subtrees solved
    "s1_river_solves": 168,  # Number of river subtrees solved
    "s1_total_nodes": 87_432,
    "s1_max_depth_reached": 47,
    "approximate": False,
    "provenance": "complete finite-tree CFR with automatic turn/river continuation",
}
```

### 3.3 Backward Compatibility

**Existing `solve_multistreet` function unchanged:**

```python
def solve_multistreet(
    config: MultiStreetConfig,  # v2, no S1 fields
    algorithm: Literal["vanilla-cfr", "external-sampling-mccfr"],
    iterations: int,
    seed: int | None = None,
) -> SolveResult:
    """Original v2 API — unchanged behavior."""
```

**Migration path:**

- `solve_multistreet` continues to work for all v2 configs
- `solve_multistreet_s1` is the new entry point for S1 features
- Internal implementation: `solve_multistreet_s1` delegates to `solve_multistreet` when `continuation_mode == "explicit"`

---

## 4. JSON Schema

### 4.1 Standard Mode (Automatic Continuation)

```json
{
  "version": 2,
  "starting_street": "flop",
  "starting_board": ["2c", "3d", "4h"],
  "initial_dead_pot": 10,
  "effective_stack": 100,
  "player0_combos": [
    {"cards": ["As", "Ks"], "weight": 1.0},
    {"cards": ["Ah", "Kh"], "weight": 0.5}
  ],
  "player1_combos": [
    {"cards": ["Qd", "Jd"], "weight": 1.0}
  ],
  "allowed_runouts": [
    ["9s"],
    ["Tc"]
  ],
  "betting_mode": "no-limit",
  "wager_targets": [10, 25, 50, 100],
  "continuation_mode": "automatic",
  "s1_max_nodes": 100000,
  "s1_turn_iteration_budget": 1000,
  "s1_river_iteration_budget": 500
}
```

**Field descriptions:**

- `continuation_mode`: `"automatic"` (default if omitted) or `"explicit"`
- `s1_max_nodes`: Optional; defaults to 100,000
- `s1_turn_iteration_budget`: Optional; defaults to 1,000
- `s1_river_iteration_budget`: Optional; defaults to 500

### 4.2 Reference Mode (Explicit Continuation)

```json
{
  "version": 2,
  "starting_street": "flop",
  "starting_board": ["2c", "3d", "4h"],
  "initial_dead_pot": 10,
  "effective_stack": 100,
  "player0_combos": [{"cards": ["As", "Ks"], "weight": 1.0}],
  "player1_combos": [{"cards": ["Qd", "Jd"], "weight": 1.0}],
  "allowed_runouts": [],
  "betting_mode": "no-limit",
  "wager_targets": [10, 50, 100],
  "continuation_mode": "explicit",
  "explicit_continuation": {
    "((0,12),(16,11),CHECK,CHECK)": [5.0, -5.0],
    "((0,12),(16,11),RAISE:10,CALL:10)": [8.0, -8.0]
  }
}
```

**Continuation key format:**

- String representation of `(deal, history)` tuple
- `deal`: `((p0_card0, p0_card1), (p1_card0, p1_card1))`
- `history`: Tuple of action strings (e.g., `"CHECK"`, `"RAISE:10"`)
- Values: `[player0_value, player1_value]` (must sum to 0.0)

### 4.3 Validation Rules

**Required fields (all modes):**

```python
required = {
    "version", "starting_street", "starting_board", "initial_dead_pot",
    "effective_stack", "player0_combos", "player1_combos",
    "allowed_runouts", "betting_mode", "wager_targets"
}
```

**Optional S1 fields:**

```python
optional_s1 = {
    "continuation_mode",  # Default: "automatic"
    "explicit_continuation",  # Default: None
    "s1_max_nodes",  # Default: 100_000
    "s1_max_depth",  # Default: 512
    "s1_turn_iteration_budget",  # Default: 1_000
    "s1_river_iteration_budget",  # Default: 500
}
```

**Rejection matrix:**

| Input | Error |
|-------|-------|
| Unknown field | `"unknown fields: ['bad_field']"` |
| Missing required field | `"missing required fields: ['effective_stack']"` |
| `version != 2` | `"unsupported version 3, expected 2"` |
| `continuation_mode` not in `{"automatic", "explicit"}` | `"continuation_mode must be 'automatic' or 'explicit'"` |
| `continuation_mode == "automatic"` + `explicit_continuation != None` | `"automatic mode cannot have explicit_continuation"` |
| `continuation_mode == "explicit"` + `explicit_continuation == None` | `"explicit mode requires explicit_continuation"` |
| `continuation_mode == "automatic"` + `starting_street == "river"` | `"automatic continuation requires flop or turn starting street"` |
| `continuation_mode == "automatic"` + `allowed_runouts == []` | `"automatic continuation requires non-empty allowed_runouts"` |
| `s1_max_nodes` not positive int | `"s1_max_nodes must be a positive integer"` |
| `s1_max_nodes > 10_000_000` | `"s1_max_nodes exceeds maximum of 10000000"` |
| Estimated nodes > `s1_max_nodes` | `"Estimated 2500000 nodes exceeds limit 100000"` |
| Continuation value not zero-sum | `"continuation values must sum to zero"` |
| Missing continuation entry | `"missing continuation value for leaf ((0,12),(16,11),CHECK,CHECK)"` |

---

## 5. CLI Interface

### 5.1 New Command: `solve-multistreet-s1`

```bash
poker-solver solve-multistreet-s1 CONFIG \
  --algorithm {vanilla-cfr,external-sampling-mccfr} \
  --iterations ITERATIONS \
  [--seed SEED] \
  [--json]
```

**Arguments:**

- `CONFIG`: JSON file path or `"-"` for stdin
- `--algorithm`: Required; `vanilla-cfr` or `external-sampling-mccfr`
- `--iterations`: Required; positive integer (flop-level iterations)
- `--seed`: Optional; required for MCCFR, must be absent for vanilla
- `--json`: Optional; emit compact JSON (default: human-readable)

**Example (automatic mode):**

```bash
poker-solver solve-multistreet-s1 flop_auto.json \
  --algorithm vanilla-cfr \
  --iterations 2000 \
  --json > result.json
```

**Example (explicit mode):**

```bash
poker-solver solve-multistreet-s1 flop_explicit.json \
  --algorithm vanilla-cfr \
  --iterations 2000 \
  --json > result.json
```

### 5.2 Backward Compatibility

**Existing `solve-multistreet` command unchanged:**

```bash
poker-solver solve-multistreet CONFIG \
  --algorithm {vanilla-cfr,external-sampling-mccfr} \
  --iterations ITERATIONS \
  [--seed SEED] \
  [--json]
```

- Continues to work for all v2 configs without S1 fields
- Ignores S1 fields if present (forward compatibility: old CLI + new config → uses v2 behavior)

### 5.3 Output Format

**JSON output (automatic mode):**

```json
{
  "algorithm": "vanilla-cfr",
  "iterations": 2000,
  "seed": null,
  "values": [12.34, -12.34],
  "nash_conv": 0.042,
  "exploitability_half_nash_conv": 0.021,
  "metadata": {
    "config_version": 2,
    "starting_street": "flop",
    "continuation_mode": "automatic",
    "s1_turn_solves": 42,
    "s1_river_solves": 168,
    "s1_total_nodes": 87432,
    "s1_max_depth_reached": 47,
    "approximate": false,
    "provenance": "complete finite-tree CFR with automatic turn/river continuation"
  },
  "strategy": {
    "format": "poker-solver-strategy-v1",
    "policies": [
      {
        "information_state": "('multistreet-v1', 0, (0, 12), (2, 3, 4), (), 10, (0, 0), (100, 100), 'no-limit')",
        "actions": [
          {"kind": "CHECK", "amount": 0, "probability": 0.65},
          {"kind": "RAISE", "amount": 10, "probability": 0.35}
        ]
      }
    ]
  }
}
```

**Human-readable output:**

```
Algorithm: vanilla-cfr
Iterations: 2000
Values: [12.34, -12.34]
NashConv: 0.042
Exploitability: 0.021

Metadata:
  Continuation mode: automatic
  Turn solves: 42
  River solves: 168
  Total nodes: 87432
  Max depth: 47
  Approximate: false
  Provenance: complete finite-tree CFR with automatic turn/river continuation

Strategy: 1234 information sets (use --json for full output)
```

---

## 6. Malformed-Input Rejection Matrix

### 6.1 Type Errors

| Input | Expected | Error |
|-------|----------|-------|
| `"version": true` | int | `"version must be a JSON integer"` |
| `"version": 2.0` | int | `"version must be a JSON integer"` |
| `"effective_stack": "100"` | int | `"effective_stack must be a JSON integer"` |
| `"initial_dead_pot": -5` | non-negative int | `"initial_dead_pot must be non-negative"` |
| `"player0_combos": {}` | list | `"player0_combos must be a list"` |
| `"combo[0].weight": false` | number | `"combo 0 weight must not be a boolean"` |
| `"combo[0].weight": Infinity` | finite | `"combo 0 weight must be finite"` |
| `"starting_street": "preflop"` | flop/turn/river | `"starting_street must be 'flop', 'turn', or 'river'"` |
| `"betting_mode": "limit"` | no-limit/pot-limit | `"betting_mode must be 'no-limit' or 'pot-limit'"` |

### 6.2 Structural Errors

| Input | Error |
|-------|-------|
| Empty `player0_combos` | `"player0_combos must not be empty"` |
| Zero total weight | `"player0_combos total weight must be positive"` |
| Duplicate combo | `"player0_combos contains duplicate hands"` |
| Combo overlaps board | `"combo cards overlap with board"` |
| Runout overlaps board | `"runout overlaps with starting board"` |
| Duplicate runout | `"allowed_runouts must be unique"` |
| Wrong runout length | `"runouts must contain exactly 2 cards"` (turn from flop) |
| Unsorted wager_targets | `"wager_targets must be unique and increasing"` |

### 6.3 S1-Specific Errors

| Input | Error |
|-------|-------|
| `continuation_mode == "automatic"` + river start | `"automatic continuation requires flop or turn starting street"` |
| `continuation_mode == "automatic"` + empty runouts | `"automatic continuation requires non-empty allowed_runouts"` |
| `continuation_mode == "explicit"` + no table | `"explicit mode requires explicit_continuation"` |
| `continuation_mode == "automatic"` + table present | `"automatic mode cannot have explicit_continuation"` |
| Estimated nodes > limit | `"Estimated 2500000 nodes exceeds limit 100000"` |
| `s1_max_nodes > 10_000_000` | `"s1_max_nodes exceeds maximum of 10000000"` |
| Missing continuation entry | `"missing continuation value for leaf ((0,12),(16,11),CHECK,CHECK)"` |
| Non-zero-sum continuation | `"continuation values must sum to zero (got 0.001)"` |

### 6.4 Resource Limit Errors (Runtime)

| Condition | Error |
|-----------|-------|
| Nodes exceeded during solve | `ResourceExceededError: "Node count 100001 exceeded limit 100000"` |
| Depth exceeded | `ResourceExceededError: "Depth 513 exceeded limit 512"` |
| Cycle detected | `ValueError: "cycle detected in game tree"` |

---

## 7. Compatibility Matrix

### 7.1 API Version Compatibility

| Config Version | `solve_multistreet` (v2) | `solve_multistreet_s1` (S1) |
|----------------|--------------------------|-----------------------------|
| v2 (no S1 fields) | ✅ Works (original behavior) | ✅ Works (automatic mode default) |
| v2 + `continuation_mode: "automatic"` | ⚠️ Ignores S1 fields, uses v2 | ✅ Works (S1 automatic) |
| v2 + `continuation_mode: "explicit"` | ⚠️ Ignores S1 fields, uses v2 | ✅ Works (S1 explicit) |
| v1 (river) | ❌ Wrong function | ❌ Wrong function |
| v3 (utilities) | ❌ Wrong function | ❌ Wrong function |

### 7.2 CLI Compatibility

| Command | v2 Config | v2 + S1 Fields |
|---------|-----------|----------------|
| `solve-multistreet` | ✅ Works | ⚠️ Ignores S1 fields |
| `solve-multistreet-s1` | ✅ Works (auto default) | ✅ Works |

### 7.3 Serialization Compatibility

| Strategy Format | v2 | S1 |
|-----------------|----|----||
| `poker-solver-strategy-v1` | ✅ | ✅ |
| Information state keys | ✅ Same format | ✅ Same format |
| Action representation | ✅ Same | ✅ Same |

**Key insight:** S1 strategies use the same serialization format as v2; only the metadata differs.

---

## 8. Migration Sequence

### 8.1 Phase 1: Additive API (No Breaking Changes)

**Goal:** Introduce S1 API alongside v2 without breaking existing code.

**Steps:**

1. Add `MultiStreetConfigS1` dataclass (inherits v2 fields + S1 extensions)
2. Add `solve_multistreet_s1` function (new entry point)
3. Add `solve-multistreet-s1` CLI command
4. Add S1 validation logic (pre-solve checks, runtime limits)
5. Add S1 metadata fields to `SolveResult`
6. Update JSON schema documentation (additive)

**Compatibility:**

- ✅ All existing v2 code continues to work
- ✅ All existing v2 configs continue to work
- ✅ All existing v2 tests continue to pass
- ✅ S1 is opt-in (use new function/command)

### 8.2 Phase 2: Deprecation Warnings (Optional)

**Goal:** Signal future consolidation without breaking changes.

**Steps:**

1. Add deprecation warning to `solve_multistreet` docstring:
   ```python
   """Original v2 API. For automatic continuation, use solve_multistreet_s1."""
   ```
2. CLI help text: `solve-multistreet` → "(legacy; use solve-multistreet-s1 for S1 features)"

**Compatibility:**

- ✅ No functional changes
- ⚠️ Documentation signals future direction

### 8.3 Phase 3: Consolidation (Future, Breaking)

**Goal:** Merge S1 into v2 as the default behavior.

**Steps:**

1. Rename `MultiStreetConfigS1` → `MultiStreetConfig` (replace v2)
2. Rename `solve_multistreet_s1` → `solve_multistreet` (replace v2)
3. Remove old v2 function (breaking change)
4. Update all tests and documentation

**Compatibility:**

- ❌ Breaking change: old v2 code must migrate to S1 API
- ✅ Migration path: replace `solve_multistreet` → `solve_multistreet_s1` (mechanical)

**Recommendation:** Defer Phase 3 until S1 is battle-tested (Phase 4 S2/S3/S4).

---

## 9. Defensive Copies and Immutability

### 9.1 Input Validation

**Rule:** All mutable inputs are copied before validation.

```python
def load_multistreet_config_s1(data: dict[str, Any]) -> MultiStreetConfigS1:
    # Defensive copy: caller cannot mutate after validation
    data = dict(data)
    
    # Validate and extract fields
    player0_combos = tuple(_parse_combo(item, i) for i, item in enumerate(data["player0_combos"]))
    # ... (all fields copied into immutable tuples)
    
    return MultiStreetConfigS1(
        version=2,
        player0_combos=player0_combos,  # Immutable tuple
        # ...
    )
```

### 9.2 Output Immutability

**Rule:** All outputs are immutable or defensively copied.

```python
@dataclass(frozen=True, slots=True)
class SolveResult:
    """Immutable result — caller cannot mutate."""
    algorithm: str
    values: tuple[float, float]  # Immutable tuple
    strategy: dict[Any, dict[Any, float]]  # Caller gets a copy
    metadata: dict[str, Any]  # Caller gets a copy
```

**Strategy serialization:**

```python
def serialize_strategy(strategy: Strategy) -> dict[str, Any]:
    # Returns a new dict; caller cannot mutate internal strategy
    return {
        "format": "poker-solver-strategy-v1",
        "policies": [
            {
                "information_state": repr(key),
                "actions": [
                    {"kind": action.kind, "amount": action.amount, "probability": policy[action]}
                    for action in sorted(policy)
                ],
            }
            for key, policy in sorted(strategy.items(), key=lambda item: repr(item[0]))
        ],
    }
```

### 9.3 Cache Safety

**Rule:** Cache keys are immutable; cached values are never mutated.

```python
# Cache key: immutable tuple of hashable values
CacheKey = tuple[str, str, tuple[int, ...], int, tuple[int, int], ...]

# Cache value: frozen dataclass
@dataclass(frozen=True)
class CachedSubgameResult:
    values: tuple[float, float]
    strategy: MappingProxyType[Any, MappingProxyType[Action, float]]  # Immutable
```

---

## 10. Deterministic Output Contract

### 10.1 Vanilla CFR

**Contract:** Same config → same output (no randomness).

**Guarantees:**

- Runout enumeration: deterministic order (sorted by card index)
- Combo enumeration: deterministic order (sorted by card tuple)
- Action enumeration: deterministic order (CHECK < CALL < RAISE, sorted by amount)
- Information state keys: deterministic repr (sorted tuples)
- Strategy serialization: deterministic order (sorted by repr(key))

**Test:**

```python
def test_vanilla_cfr_is_deterministic():
    config = load_multistreet_config_s1(fixture_data())
    result1 = solve_multistreet_s1(config, "vanilla-cfr", 1000, seed=None)
    result2 = solve_multistreet_s1(config, "vanilla-cfr", 1000, seed=None)
    assert result1.values == result2.values
    assert result1.strategy == result2.strategy
```

### 10.2 MCCFR

**Contract:** Same config + seed → same output.

**Guarantees:**

- Seeded RNG: `random.Random(seed)` for chance sampling
- RNG state: saved/restored per information set (order-independent)
- Runout sampling: deterministic given seed
- Action sampling: deterministic given seed

**Test:**

```python
def test_mccfr_is_deterministic_with_seed():
    config = load_multistreet_config_s1(fixture_data())
    result1 = solve_multistreet_s1(config, "external-sampling-mccfr", 1000, seed=42)
    result2 = solve_multistreet_s1(config, "external-sampling-mccfr", 1000, seed=42)
    assert result1.values == result2.values
    assert result1.strategy == result2.strategy
```

### 10.3 Cross-Platform Determinism

**Limitation:** Python's `hash()` is not deterministic across processes (PYTHONHASHSEED).

**Mitigation:** Never use `hash()` for ordering; always use explicit sort keys.

```python
# ❌ BAD: hash-dependent order
sorted(strategy.items())

# ✅ GOOD: explicit repr-based order
sorted(strategy.items(), key=lambda item: repr(item[0]))
```

---

## 11. Truth Labels and Provenance

### 11.1 Approximate Flag

**Values:**

- `false` — Complete finite-tree CFR to configured iterations
- `true` — Approximate method (checkdown-equity, rollout, neural)

**S1 behavior:**

- Automatic mode: `approximate = false` (exact finite-tree traversal)
- Explicit mode: `approximate = false` (caller-supplied values are treated as exact)

### 11.2 Provenance String

**Format:** Human-readable method description.

**Examples:**

- `"complete finite-tree CFR with automatic turn/river continuation"`
- `"complete finite-tree CFR with explicit caller-supplied continuation"`
- `"checkdown-equity rollout; ignores future betting"`
- `"neural continuation model v2.1.0"`

**S1 provenance:**

```python
if config.continuation_mode == "automatic":
    provenance = "complete finite-tree CFR with automatic turn/river continuation"
else:
    provenance = "complete finite-tree CFR with explicit caller-supplied continuation"
```

### 11.3 Metadata Transparency

**Required fields:**

```python
metadata = {
    "config_version": 2,
    "starting_street": "flop",
    "continuation_mode": "automatic" | "explicit",
    "approximate": False,
    "provenance": "...",
}
```

**Optional S1 fields (automatic mode only):**

```python
metadata.update({
    "s1_turn_solves": 42,
    "s1_river_solves": 168,
    "s1_total_nodes": 87432,
    "s1_max_depth_reached": 47,
    "s1_turn_iteration_budget": 1000,
    "s1_river_iteration_budget": 500,
})
```

---

## 12. Acceptance Criteria

### 12.1 API Completeness

- ✅ `MultiStreetConfigS1` dataclass with all S1 fields
- ✅ `solve_multistreet_s1` function with typed signature
- ✅ `load_multistreet_config_s1` validation function
- ✅ JSON schema examples (automatic + explicit modes)
- ✅ CLI command `solve-multistreet-s1`
- ✅ Backward compatibility: v2 API unchanged

### 12.2 Validation Coverage

- ✅ Malformed-input rejection matrix (30+ cases)
- ✅ Resource limit pre-checks (estimated nodes, depth)
- ✅ Runtime limit enforcement (node count, depth, cycles)
- ✅ Zero-sum validation (continuation values)
- ✅ Defensive copies (input/output immutability)

### 12.3 Determinism

- ✅ Vanilla CFR: same config → same output
- ✅ MCCFR: same config + seed → same output
- ✅ Explicit sort keys (no hash-dependent ordering)
- ✅ Deterministic runout/combo/action enumeration

### 12.4 Truth Labeling

- ✅ `approximate` flag (false for S1 automatic/explicit)
- ✅ `provenance` string (method description)
- ✅ Metadata transparency (turn/river solve counts, node counts)

### 12.5 Migration Path

- ✅ Phase 1: Additive API (no breaking changes)
- ✅ Compatibility matrix (v2 ↔ S1)
- ✅ CLI backward compatibility
- ✅ Serialization format unchanged

---

## 13. Out-of-Scope Items

**Explicitly excluded from this design:**

1. **Implementation:** No production code, no `src/` edits
2. **Tests:** No `tests/` edits, no pytest fixtures
3. **Shared documentation:** No `docs/`, `README.md`, `ARCHITECTURE.md` edits
4. **Git operations:** No commits, branches, or tags
5. **Performance optimization:** Caching, parallelization (covered in 04-bounds-performance.md)
6. **Neural DDLS:** Fast mode, learned value functions (Phase 4 A1, separate project)
7. **Rollout recursion:** Monte Carlo continuation (rejected alternative, see 01-algorithm.md)
8. **Abstraction:** Range/action bucketing (Phase 4 S4)
9. **Multiway S1:** 3+ player automatic continuation (Phase 4 S2)
10. **Preflop S1:** Automatic preflop continuation (Phase 4 S3)

---

## 14. Summary

This document specifies the **public API, JSON schema, CLI, and migration path** for S1 automatic all-street continuation. Key design decisions:

1. **Additive evolution:** S1 extends v2 without breaking changes
2. **Dual-mode API:** Automatic (standard) + explicit (reference/advanced)
3. **Strict validation:** Fail-closed on malformed input, resource limits
4. **Deterministic output:** Same input/seed → same strategy/values
5. **Truth labeling:** Approximate flag + provenance string
6. **Backward compatibility:** All v1/v2/v3 behavior unchanged
7. **Defensive design:** Immutable configs, copied outputs, collision-resistant cache keys

**Next steps (implementation phase):**

1. Implement `load_multistreet_config_s1` validation
2. Implement `solve_multistreet_s1` with automatic continuation logic
3. Add CLI command `solve-multistreet-s1`
4. Add S1 acceptance tests (see 03-oracles-tests.md)
5. Update API documentation (additive)

**Acceptance gate:** This design is complete when it defines exact typed signatures, JSON examples, compatibility matrix, malformed-input matrix, and migration sequence. ✅ **COMPLETE**
