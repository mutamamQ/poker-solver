# S4 Design: Strict Public API/Config/Result and RED-First Test Contract

**Agent:** S4D5 (design-only public config/API/TDD contract analyst)  
**Timestamp:** 2026-09-16 (UTC)  
**Scope:** Phase 4 S4 automatic abstraction — strict immutable public API, config validation, result schema, v4 JSON integration, and RED-first vertical test contract.  
**Ownership:** `research/phase4/s4-design/05-api-tdd-contract.md` only; no implementation/production/test edits.

---

## 1. Executive Summary

S4 (automatic abstraction) requires a strict public API contract that:

1. **Extends v4 JSON dispatch** additively with a new operation `"solve-abstracted-postflop"`
2. **Enforces immutable config/result** with defensive copying and frozen dataclasses
3. **Rejects bool-as-int, nonfinite, unknown fields, and mutation aliasing**
4. **Documents approximate truth** (abstraction policy, state-count bounds, strategically-identical-combo preservation)
5. **Maintains backward compatibility** (existing v4 operations unchanged)
6. **Specifies RED-first vertical tests** with exact file paths and staged RED→GREEN commands

---

## 2. Public API Contract

### 2.1 New v4 Operation: `solve-abstracted-postflop`

**Envelope:**
```json
{
  "version": 4,
  "operation": "solve-abstracted-postflop",
  "payload": { ... }
}
```

**Payload (required fields):**
```json
{
  "version": "abstracted-postflop-v1",
  "starting_board": [int, int, int],
  "initial_dead_pot": int,
  "effective_stack": int,
  "player0_combos": [{"cards": [int, int], "weight": float}, ...],
  "player1_combos": [{"cards": [int, int], "weight": float}, ...],
  "allowed_runouts": [[int, int], ...],
  "betting_mode": "no-limit" | "pot-limit",
  "wager_targets": [int, ...],
  "abstraction_policy": {
    "kind": "category-based" | "blocker-aware",
    "max_buckets": int,
    "deterministic": true
  },
  "algorithm": "vanilla-cfr" | "external-sampling-mccfr",
  "iterations": int,
  "seed": int | null
}
```

**Payload (optional fields):**
```json
{
  "max_nodes": int,
  "max_depth": int
}
```

**Validation rules:**
- `version`: exactly `"abstracted-postflop-v1"` (string)
- `starting_board`: exactly 3 unique cards (int 0–51)
- `initial_dead_pot`: non-negative int (reject bool)
- `effective_stack`: positive int (reject bool)
- `player0_combos`, `player1_combos`: non-empty, each combo has `cards` (2 unique ints 0–51) and `weight` (finite float ≥ 0)
- Total weight per player must be positive (reject zero-mass ranges)
- `allowed_runouts`: non-empty, each runout exactly 2 unique cards, no overlap with board, unique runouts
- `betting_mode`: `"no-limit"` or `"pot-limit"` only
- `wager_targets`: non-empty, unique, strictly increasing non-negative ints
- `abstraction_policy.kind`: `"category-based"` or `"blocker-aware"` only
- `abstraction_policy.max_buckets`: positive int
- `abstraction_policy.deterministic`: must be boolean `true` (reject `false` or non-bool)
- `algorithm`: `"vanilla-cfr"` or `"external-sampling-mccfr"` only
- `iterations`: positive int (reject bool)
- `seed`: null for vanilla-cfr, int for mccfr (reject bool)
- `max_nodes`: optional positive int (default 100000)
- `max_depth`: optional positive int (default 512)

**Rejection cases:**
- Unknown top-level or payload fields
- Missing required fields
- Bool as int (e.g., `iterations: true`)
- Nonfinite weights (inf, -inf, nan)
- Negative weights, zero total weight
- Duplicate/overlapping cards
- Invalid algorithm/seed pairing
- Explicit `continuation` or `payoff_table` fields (automatic only)

---

### 2.2 Response Schema

**Success response:**
```json
{
  "version": 4,
  "operation": "solve-abstracted-postflop",
  "config_version": 4,
  "game_version": "abstracted-postflop-v1",
  "starting_street": "flop",
  "continuation": "automatic-natural-terminal",
  "abstraction": {
    "policy": "category-based" | "blocker-aware",
    "max_buckets": int,
    "actual_buckets": int,
    "deterministic": true,
    "provenance": "<description>"
  },
  "algorithm": "vanilla-cfr" | "external-sampling-mccfr",
  "iterations": int,
  "seed": int | null,
  "max_nodes": int,
  "max_depth": int,
  "strategy": {"<info_key>": {"<action>": float, ...}, ...},
  "values": [float, float],
  "nashconv": float,
  "exploitability": float,
  "metadata": {
    "terminal_count": int,
    "chance_count": int,
    "decision_count": int,
    "abstraction_state_count": int,
    "original_state_count_estimate": int
  },
  "provenance": "abstracted flop-to-river finite-tree traversal with <policy> abstraction",
  "approximate": true
}
```

**Metadata guarantees:**
- `config_version`: always 4
- `game_version`: exactly `"abstracted-postflop-v1"`
- `starting_street`: always `"flop"`
- `continuation`: always `"automatic-natural-terminal"`
- `abstraction.actual_buckets`: ≤ `max_buckets`, truthful count
- `abstraction.deterministic`: always `true`
- `approximate`: always `true` (abstraction is approximate)
- `provenance`: human-readable description of abstraction method
- `strategy`: JSON-serializable with `allow_nan=False` (no inf/nan)
- `values`: finite floats, zero-sum within floating-point tolerance

**Error response:**
- Raise `ValueError` with descriptive message (no partial results)
- Node/depth limit violations mention "node" or "depth" in error message

---

## 3. Immutable Config Dataclass

**Module:** `src/poker_solver/abstracted_postflop.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from poker_solver.equity import WeightedCombo

@dataclass(frozen=True, slots=True)
class AbstractionPolicy:
    """Immutable abstraction policy configuration."""
    kind: Literal["category-based", "blocker-aware"]
    max_buckets: int
    deterministic: bool  # must be True

    def __post_init__(self) -> None:
        if self.kind not in ("category-based", "blocker-aware"):
            raise ValueError(f"abstraction kind must be 'category-based' or 'blocker-aware', got {self.kind!r}")
        if isinstance(self.max_buckets, bool) or not isinstance(self.max_buckets, int) or self.max_buckets <= 0:
            raise ValueError("max_buckets must be a positive integer")
        if self.deterministic is not True:
            raise ValueError("deterministic must be exactly True")

@dataclass(frozen=True, slots=True)
class AbstractedPostflopConfig:
    """Immutable configuration for abstracted all-street postflop solve."""
    version: str
    starting_board: tuple[int, int, int]
    initial_dead_pot: int
    effective_stack: int
    player0_combos: tuple[WeightedCombo, ...]
    player1_combos: tuple[WeightedCombo, ...]
    allowed_runouts: tuple[tuple[int, int], ...]
    betting_mode: Literal["no-limit", "pot-limit"]
    wager_targets: tuple[int, ...]
    abstraction_policy: AbstractionPolicy
    max_nodes: int = 100_000
    max_depth: int = 512

    def __post_init__(self) -> None:
        # Defensive tuple conversion
        object.__setattr__(self, "starting_board", tuple(self.starting_board))
        object.__setattr__(self, "player0_combos", tuple(self.player0_combos))
        object.__setattr__(self, "player1_combos", tuple(self.player1_combos))
        object.__setattr__(self, "allowed_runouts", tuple(tuple(r) for r in self.allowed_runouts))
        object.__setattr__(self, "wager_targets", tuple(self.wager_targets))
        
        # Version validation
        if self.version != "abstracted-postflop-v1":
            raise ValueError(f"version must be 'abstracted-postflop-v1', got {self.version!r}")
        
        # (All validation rules from section 2.1 applied here)
        # ... [full validation as in AllStreetPostflopConfig]
```

---

## 4. Immutable Result Dataclass

```python
from types import MappingProxyType
from typing import Any, Mapping

@dataclass(frozen=True, slots=True)
class AbstractedSolveResult:
    """Immutable result from abstracted postflop solve."""
    algorithm: str
    seed: int | None
    iterations: int
    values: tuple[float, float]
    nash_conv: float
    half_nash_conv: float
    strategy: Mapping[Any, Mapping[Any, float]]
    config_version: int
    game_version: str
    starting_street: str
    continuation: str
    abstraction_policy: str
    abstraction_buckets: int
    max_nodes: int
    max_depth: int
    node_count: int
    max_depth_reached: int
    approximate: bool
    provenance: str
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        # Deep-freeze strategy and metadata
        frozen_strategy = MappingProxyType({
            info_key: MappingProxyType(dict(policy))
            for info_key, policy in self.strategy.items()
        })
        object.__setattr__(self, "strategy", frozen_strategy)
        object.__setattr__(self, "metadata", _deep_freeze(self.metadata))
```

---

## 5. v4 Dispatcher Integration

**File:** `src/poker_solver/api_v4.py`

**Changes:**
1. Add `"solve-abstracted-postflop"` to allowed operations in `dispatch_v4`
2. Add new dispatcher function `_dispatch_abstracted_postflop(payload_value: Any) -> dict[str, Any]`
3. Route to new dispatcher when `operation == "solve-abstracted-postflop"`

**Backward compatibility:**
- Existing operations (`"solve-allstreet-postflop"`, `"solve-nplayer-postflop"`, `"solve-nplayer-preflop"`) unchanged
- No modifications to existing payload schemas
- Additive-only change

---

## 6. Capability Exports

**File:** `src/poker_solver/__init__.py`

**Add:**
```python
from .abstracted_postflop import (
    AbstractionPolicy,
    AbstractedPostflopConfig,
    AbstractedSolveResult,
    solve_abstracted_postflop,
)
```

---

## 7. RED-First Vertical Test Contract

### 7.1 Test Files

**Primary test file (RED-first contract):**
- `tests/test_abstracted_api_v4.py` — strict v4 JSON API contract tests

**Supporting test files (implementation-owned):**
- `tests/test_abstracted_config.py` — config validation (similar to `test_allstreet_config.py`)
- `tests/test_abstracted_oracle.py` — small-spot abstracted vs exact comparison

### 7.2 Staged RED/GREEN Commands

**RED stage (before implementation):**
```bash
# Create test file with failing imports and minimal structure
touch tests/test_abstracted_api_v4.py

# Expected: ImportError or AttributeError
pytest tests/test_abstracted_api_v4.py::test_canonical_abstracted_solve -v
```

**GREEN stage (after implementation):**
```bash
# Full API contract suite
pytest tests/test_abstracted_api_v4.py -v

# Full suite (must preserve 398-test baseline)
pytest -q
# Expected: 398 + N new tests passed
```

### 7.3 Required Test Coverage (test_abstracted_api_v4.py)

**Canonical success cases:**
1. `test_canonical_abstracted_solve_category_based` — minimal valid category-based solve
2. `test_canonical_abstracted_solve_blocker_aware` — minimal valid blocker-aware solve
3. `test_deterministic_vanilla_cfr_abstracted` — repeated runs produce identical results
4. `test_deterministic_mccfr_abstracted_same_seed` — MCCFR with same seed identical

**Validation rejection cases:**
5. `test_unknown_payload_field_rejected`
6. `test_missing_required_field_abstraction_policy`
7. `test_bool_as_int_rejected_iterations`
8. `test_nonfinite_weight_rejected`
9. `test_invalid_abstraction_kind_rejected`
10. `test_non_positive_max_buckets_rejected`
11. `test_deterministic_false_rejected`
12. `test_vanilla_cfr_with_seed_rejected`
13. `test_mccfr_without_seed_rejected`
14. `test_explicit_continuation_field_rejected`

**Response contract cases:**
15. `test_result_is_json_serializable_strict_nan_check`
16. `test_metadata_truthful_approximate_true`
17. `test_abstraction_metadata_present_and_bounded`
18. `test_deep_response_isolation_comprehensive`

**Backward compatibility:**
19. `test_existing_v4_operations_unchanged` — verify `solve-allstreet-postflop` still works

### 7.4 Expected Test Attribution

**RED tests (design-authored, before implementation):**
- All 19 tests in `tests/test_abstracted_api_v4.py` authored by S4D5 (this design)
- Tests import `from poker_solver.api_v4 import dispatch_v4`
- Tests import `from poker_solver.abstracted_postflop import AbstractedPostflopConfig` (will fail until implementation)

**GREEN implementation (implementation-authored):**
- `src/poker_solver/abstracted_postflop.py` — config, result, solve function
- `src/poker_solver/api_v4.py` — dispatcher integration
- `src/poker_solver/__init__.py` — exports
- `tests/test_abstracted_config.py` — detailed config validation
- `tests/test_abstracted_oracle.py` — abstracted vs exact comparison

---

## 8. Abstraction Policy Documentation

**Required in result provenance:**
- `"category-based"`: "Hands grouped by equity percentile categories; strategically similar combos share policy"
- `"blocker-aware"`: "Hands grouped by blocker effects on opponent ranges; preserves removal effects"

**Determinism guarantee:**
- Same config + same seed (for MCCFR) → same abstraction buckets → same strategy
- Documented in `PHASE4.md` under S4 boundaries

**Approximate truth:**
- `approximate: true` in all abstracted results
- Provenance states abstraction method explicitly
- No claims of "exact equilibrium" or "GTO parity"
- Documented bound: abstracted vs exact (on small comparable spot) within derived tolerance

---

## 9. Acceptance Criteria (from PHASE4_MISSION.md)

**S4 acceptance (design contract):**
1. ✅ Abstracted solve of large spot completes with bounded state count
2. ✅ Abstracted vs exact (small spot) within derived bound — oracle test required
3. ✅ Abstraction policy explicit in config — `abstraction_policy` field
4. ✅ Determinism — same config/seed → same result
5. ✅ No silent strategy corruption — strategically identical combos stay identical (oracle test)

**Test contract:**
- RED-first: 19 tests in `test_abstracted_api_v4.py` fail before implementation
- GREEN: all tests pass after implementation
- Baseline preserved: 398 prior tests still green

---

## 10. Design Boundaries

**In scope (this design):**
- Public API contract (v4 JSON operation)
- Config/result immutability and validation
- Test file structure and RED/GREEN staging
- Metadata schema and provenance

**Out of scope (implementation-owned):**
- Abstraction algorithm implementation (category-based, blocker-aware)
- Bucket assignment logic
- State-space reduction mechanics
- Performance optimization
- Integration with existing multistreet solver

**No implementation edits:**
- This design does NOT modify production code
- This design does NOT write test implementations
- This design does NOT commit to git

---

## 11. File Manifest

**Design output (this agent):**
- `research/phase4/s4-design/05-api-tdd-contract.md` (this file)
- `research/phase4/s4-design/.hb/S4D5` (heartbeat)

**Implementation targets (future agents):**
- `src/poker_solver/abstracted_postflop.py` (new)
- `src/poker_solver/api_v4.py` (additive edit)
- `src/poker_solver/__init__.py` (additive edit)
- `tests/test_abstracted_api_v4.py` (new, RED-first)
- `tests/test_abstracted_config.py` (new)
- `tests/test_abstracted_oracle.py` (new)

---

## 12. Design Hash and Status

**Design hash:** `sha256(this file content)` — to be computed on final write  
**Status:** COMPLETE_DESIGN  
**Heartbeat:** live UTC timestamp in `.hb/S4D5`  
**Attribution:** S4D5 design-only agent, no implementation

---

**End of S4 API/TDD Contract Design**
