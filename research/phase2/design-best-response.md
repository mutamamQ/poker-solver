# Best Response and Exploitability Integration Design

## Executive Summary

This document specifies a scalable, infoset-consistent best-response and exploitability computation system for the poker-solver codebase. The design preserves the existing pure-enumeration oracle (`best_response.py`) while defining preconditions, fail-closed checks, API contracts, complexity bounds, and TDD cross-checks for multi-street tractability.

## Current Implementation Analysis

### Existing Components

**`best_response.py`** (90 lines):
- `best_response(root, opponent_profile, player)` → `(float, dict[InfoKey, Action])`
  - Pure enumeration over all action combinations for `player`
  - Complexity: O(|A|^|I|) where |A| = actions per infoset, |I| = infosets owned by player
  - Returns best value and deterministic pure-strategy response
- `nash_conv(root, profile)` → `NashConvResult`
  - Computes both players' best responses against `profile`
  - Returns values, BR values, incentives, NashConv (sum of incentives)
  - Exploitability = NashConv / 2
- `validate_strategy(root, profile)` → `None` (raises on invalid)
  - Checks: all infosets covered, actions match, probabilities valid and sum to 1.0

**`cfr.py`** (162 lines):
- `collect_infosets(root)` → `dict[InfoKey, tuple[int, tuple[Action, ...]]]`
  - Full tree walk, validates perfect recall (consistent owner reach)
  - Returns infoset → (owner, actions) mapping
- `expected_values(root, profile)` → `(float, float)`
  - Tree traversal computing expected utility for both players
- `CFRSolver.train(iterations)` → `Strategy`
  - Synchronous vanilla CFR with regret matching
  - Validates perfect recall via owner-reach consistency checks

**`model.py`** (42 lines):
- `GameState` protocol: `current_player()`, `legal_actions()`, `chance_outcomes()`, `child(action)`, `information_state_key(player)`, `returns()`
- `Action(kind: str, amount: int = 0)` immutable dataclass
- `InfoKey = Hashable`, `Strategy = Mapping[InfoKey, ActionPolicy]`
- Constants: `CHANCE = -1`, `TERMINAL = -2`

### Test Coverage

**`test_best_response.py`** (63 lines):
- `HiddenBitState`: minimal chance + single-infoset game
- Tests: infoset consistency, NashConv non-negativity, convergence on Kuhn poker (< 0.03 after 5k iterations)
- Validates strategy rejection (probabilities not summing to 1.0)

**`test_cfr.py`** (36 lines):
- Regret matching unit tests
- Kuhn poker: determinism, value convergence to -1/18 ± 0.003, NashConv < 0.03
- Continuation training, probability normalization

**`test_kuhn.py`** (42 lines):
- Tree structure: 55 nodes, 30 terminals, 24 decision nodes, 1 chance node, 12 infosets
- Terminal utilities, infoset abstraction correctness

## Algorithm Specification

### Core Best Response (Pure Enumeration Oracle)

**Preserve existing `best_response()` as ground truth.**

```python
def best_response(
    root: GameState,
    opponent_profile: Strategy,
    player: int
) -> tuple[float, dict[InfoKey, Action]]:
    """
    Compute exact pure-strategy best response via exhaustive enumeration.
    
    Preconditions:
    - player ∈ {0, 1}
    - opponent_profile is valid (passes validate_strategy for opponent infosets)
    - root is a well-formed GameState (no cycles, finite tree)
    
    Algorithm:
    1. Collect all infosets owned by `player` via collect_infosets(root)
    2. Enumerate all pure-strategy combinations (Cartesian product over action sets)
    3. For each combination, compute expected value via tree traversal
    4. Return maximum value and corresponding pure strategy
    
    Complexity:
    - Time: O(|A|^|I| · |N|) where:
      - |A| = max actions per infoset
      - |I| = number of infosets owned by player
      - |N| = tree size (nodes)
    - Space: O(|I| + |N|) for recursion stack and strategy storage
    
    Fail-closed checks:
    - Raises ValueError if player not in {0, 1}
    - Returns -inf → actual value if player owns zero infosets
    - Validates opponent_profile implicitly via tree traversal (KeyError if missing infoset)
    """
```

**Current implementation is correct.** No changes required to algorithm.

### Exploitability via NashConv

**Preserve existing `nash_conv()` with enhanced documentation.**

```python
def nash_conv(root: GameState, profile: Strategy) -> NashConvResult:
    """
    Compute NashConv and exploitability for a strategy profile.
    
    Preconditions:
    - profile is valid (passes validate_strategy)
    - root is well-formed
    
    Algorithm:
    1. Validate profile completeness and probability constraints
    2. Compute expected values for both players under profile
    3. Compute best response value for each player against profile
    4. Incentive_i = BR_value_i - expected_value_i
    5. NashConv = sum of incentives (must be non-negative)
    6. Exploitability = NashConv / 2
    
    Complexity:
    - Time: O(|A|^|I₀| · |N| + |A|^|I₁| · |N|) for two best-response calls
    - Space: O(|N|) for tree traversal
    
    Fail-closed checks:
    - Raises ValueError if profile invalid (via validate_strategy)
    - Raises ArithmeticError if NashConv < -1e-9 (indicates BR bug)
    - Clamps NashConv to max(0.0, total) to handle floating-point noise
    
    Returns:
    - values: (p0_value, p1_value) under profile
    - best_response_values: (br0, br1)
    - incentives: (br0 - values[0], br1 - values[1])
    - nash_conv: sum of incentives
    - exploitability: nash_conv / 2 (property)
    """
```

### Infoset Consistency Validation

**Existing `collect_infosets()` enforces perfect recall:**

```python
def collect_infosets(root: GameState) -> dict[InfoKey, tuple[int, tuple[Action, ...]]]:
    """
    Traverse game tree and collect all information sets.
    
    Preconditions:
    - root is well-formed (no cycles, finite)
    
    Algorithm:
    1. Depth-first traversal of game tree
    2. At each decision node, record (player, actions) for infoset key
    3. Validate consistency: if key seen before, (player, actions) must match
    
    Complexity:
    - Time: O(|N|) single tree traversal
    - Space: O(|I|) for infoset storage
    
    Fail-closed checks:
    - Raises ValueError if same InfoKey maps to different (player, actions)
      → Detects imperfect recall / inconsistent abstraction
    - Implicitly validates tree structure (will hang/crash on cycles)
    
    Returns:
    - Mapping from InfoKey to (owner_player, legal_actions_tuple)
    """
```

**CFR's `_walk()` adds runtime perfect-recall check:**
- Tracks `owner_reaches` dict during traversal
- Raises `ValueError` if same infoset reached with different owner probability
- Tolerance: 1e-12 absolute

## API Contract

### Public Interface

```python
# Core best response
best_response(
    root: GameState,
    opponent_profile: Strategy,
    player: int
) -> tuple[float, dict[InfoKey, Action]]

# Exploitability measurement
nash_conv(
    root: GameState,
    profile: Strategy
) -> NashConvResult

# Strategy validation (called internally by nash_conv)
validate_strategy(
    root: GameState,
    profile: Strategy,
    tolerance: float = 1e-10
) -> None  # raises ValueError on invalid

# Result container
@dataclass(frozen=True)
class NashConvResult:
    values: tuple[float, float]
    best_response_values: tuple[float, float]
    incentives: tuple[float, float]
    nash_conv: float
    
    @property
    def exploitability(self) -> float:
        return self.nash_conv / 2.0
```

### Integration with CFR

```python
# Typical usage pattern
solver = CFRSolver(root)
strategy = solver.train(iterations=10_000)

# Measure exploitability
result = nash_conv(root, strategy)
print(f"Exploitability: {result.exploitability:.6f}")
print(f"Player 0 incentive: {result.incentives[0]:.6f}")
print(f"Player 1 incentive: {result.incentives[1]:.6f}")

# Compute best response for analysis
br_value, br_strategy = best_response(root, strategy, player=0)
print(f"Best response value: {br_value:.6f}")
```

## Complexity Analysis

### Tractability Bounds

| Game Size | |I₀| | |I₁| | |A| | |N| | BR Time | NashConv Time | Tractable? |
|-----------|------|------|------|------|---------|---------------|------------|
| Kuhn poker | 6 | 6 | 2 | 55 | 2^6 · 55 ≈ 3.5k | 2 · 3.5k ≈ 7k | ✓ |
| Leduc Hold'em (small) | ~50 | ~50 | 3 | ~10k | 3^50 · 10k ≈ 10^24 | Intractable | ✗ |
| Single-street toy | 10 | 10 | 3 | 500 | 3^10 · 500 ≈ 30M | 60M | ✓ (slow) |
| Two-street toy | 30 | 30 | 3 | 5k | 3^30 · 5k ≈ 10^15 | Intractable | ✗ |

**Tractability threshold:** |I| ≤ 15, |A| ≤ 3 for pure enumeration.

### Multi-Street Tractability

**Problem:** Infoset count grows exponentially with streets.
- Single street: O(|hands| · |actions|)
- Two streets: O(|hands|² · |actions|² · |board_cards|)
- Three streets (full Hold'em): O(|hands|³ · |actions|³ · |board_cards|²)

**Mitigation strategies (future work, not in current design):**

1. **Sampling-based BR:** Monte Carlo CFR best response (not exact)
2. **Abstraction:** Card bucketing, action abstraction
3. **Incremental BR:** Reuse computation across similar profiles
4. **Parallel enumeration:** Distribute action combinations across workers
5. **Pruning:** Alpha-beta style cutoffs (requires careful infoset handling)

**Current design scope:** Pure enumeration oracle for games with |I| ≤ 20 per player.

## Preconditions and Fail-Closed Checks

### Input Validation

**`best_response()`:**
- ✓ `player ∈ {0, 1}` → `ValueError`
- ✓ Implicit: `opponent_profile` must cover opponent infosets → `KeyError` during traversal
- ✓ Handles zero-infoset case (player has no decisions) → returns value against opponent

**`nash_conv()`:**
- ✓ Calls `validate_strategy()` → `ValueError` if:
  - Missing infoset in profile
  - Wrong action set for infoset
  - Invalid probabilities (non-finite, negative)
  - Probabilities don't sum to 1.0 (tolerance 1e-10)
- ✓ Checks NashConv ≥ -1e-9 → `ArithmeticError` if negative (BR bug detector)

**`collect_infosets()`:**
- ✓ Validates perfect recall → `ValueError` if same InfoKey has inconsistent (player, actions)
- ⚠ No cycle detection (will hang on cyclic graphs)
- ⚠ No depth limit (will stack overflow on deep trees)

**`CFRSolver._walk()`:**
- ✓ Runtime perfect-recall check via `owner_reaches` → `ValueError` if reach probability inconsistent
- Tolerance: 1e-12 absolute

### Recommended Additions (Future)

```python
def validate_game_tree(
    root: GameState,
    max_depth: int = 10_000,
    max_nodes: int = 1_000_000
) -> dict[str, int]:
    """
    Validate game tree structure before expensive computation.
    
    Checks:
    - No cycles (via visited set)
    - Depth within limit
    - Node count within limit
    - All terminal nodes return finite values
    - All chance nodes have probabilities summing to 1.0
    
    Returns:
    - {"nodes": N, "terminals": T, "depth": D, "infosets": I}
    
    Raises:
    - ValueError on structural issues
    - RuntimeError on resource limits exceeded
    """
```

**Not implemented in current design** (out of scope for this phase).

## TDD Cross-Check Matrix

### Test Coverage Requirements

| Component | Test Case | Property Verified | Status |
|-----------|-----------|-------------------|--------|
| `best_response()` | Hidden bit game | Infoset consistency | ✓ Exists |
| `best_response()` | Kuhn poker | Correct value vs known equilibrium | ✓ Exists |
| `best_response()` | Zero-infoset player | Handles empty strategy | ⚠ Missing |
| `best_response()` | Invalid player ID | Raises ValueError | ⚠ Missing |
| `nash_conv()` | Uniform random strategy | Non-negative, symmetric | ✓ Exists |
| `nash_conv()` | Kuhn equilibrium | Exploitability < 0.03 | ✓ Exists |
| `nash_conv()` | Invalid profile | Raises ValueError | ✓ Exists |
| `nash_conv()` | Negative NashConv | Raises ArithmeticError | ⚠ Missing |
| `validate_strategy()` | Missing infoset | Raises ValueError | ✓ Implicit |
| `validate_strategy()` | Wrong actions | Raises ValueError | ✓ Implicit |
| `validate_strategy()` | Invalid probabilities | Raises ValueError | ✓ Implicit |
| `collect_infosets()` | Kuhn poker | Correct count (12) | ✓ Exists |
| `collect_infosets()` | Imperfect recall | Raises ValueError | ⚠ Missing |
| `CFRSolver._walk()` | Perfect recall | Owner reach consistency | ✓ Exists |
| Integration | CFR → NashConv | Convergence to low exploitability | ✓ Exists |

### Recommended Additional Tests

```python
# test_best_response.py additions

def test_best_response_with_zero_infosets():
    """Player with no decisions should return expected value."""
    # Construct game where player 1 has no infosets
    # (e.g., player 0 always acts, then terminal)
    pass

def test_best_response_rejects_invalid_player():
    with pytest.raises(ValueError, match="player must be 0 or 1"):
        best_response(kuhn_root(), {}, player=2)
    with pytest.raises(ValueError, match="player must be 0 or 1"):
        best_response(kuhn_root(), {}, player=-1)

def test_nash_conv_detects_negative_value():
    """Simulate BR bug by mocking best_response to return too-low value."""
    # Requires monkeypatching or dependency injection
    pass

def test_collect_infosets_rejects_imperfect_recall():
    """Construct game where same InfoKey has different action sets."""
    # Requires custom GameState implementation
    pass

def test_best_response_determinism():
    """Multiple calls with same inputs return identical results."""
    profile = {("test", 0): {Action("a"): 0.5, Action("b"): 0.5}}
    br1 = best_response(test_root, profile, 0)
    br2 = best_response(test_root, profile, 0)
    assert br1 == br2

def test_exploitability_is_half_nash_conv():
    result = nash_conv(kuhn_root(), uniform_strategy)
    assert result.exploitability == pytest.approx(result.nash_conv / 2.0)
```

### Cross-Check with CFR Convergence

**Property:** As CFR iterations → ∞, exploitability → 0.

```python
def test_cfr_exploitability_decreases_monotonically():
    """Exploitability should decrease (or stay flat) with more training."""
    solver = CFRSolver(kuhn_root())
    exploits = []
    for _ in range(10):
        solver.train(100)
        result = nash_conv(kuhn_root(), solver.average_strategy())
        exploits.append(result.exploitability)
    # Allow small increases due to variance, but trend should be downward
    assert exploits[-1] < exploits[0]
    assert exploits[-1] < 0.05
```

**Existing test:** `test_kuhn_nashconv_nonnegative_and_decreases_to_small_value` covers this.

## Implementation Checklist

### Current Status (Phase 2 Baseline)

- ✅ Pure enumeration best response implemented
- ✅ NashConv and exploitability computation
- ✅ Strategy validation with probability checks
- ✅ Infoset collection with perfect-recall validation
- ✅ CFR integration with runtime consistency checks
- ✅ Basic test coverage (3 tests in `test_best_response.py`)
- ✅ Kuhn poker convergence validation

### Recommended Enhancements (Future Phases)

- ⬜ Add missing test cases (zero-infoset, invalid player, imperfect recall)
- ⬜ Implement `validate_game_tree()` for structural checks
- ⬜ Add depth/node limits to `collect_infosets()`
- ⬜ Benchmark tractability on multi-street toy games
- ⬜ Document complexity thresholds in user-facing docs
- ⬜ Implement sampling-based BR for large games (future)
- ⬜ Add parallel enumeration for medium games (future)
- ⬜ Profile memory usage on large infoset counts

## Acceptance Criteria

### Fast Pytest Acceptance

**Run:** `.venv/bin/python -m pytest tests/test_best_response.py -v`

**Expected output:**
```
tests/test_best_response.py::test_best_response_is_infoset_consistent_hidden_bit PASSED
tests/test_best_response.py::test_kuhn_nashconv_nonnegative_and_decreases_to_small_value PASSED
tests/test_best_response.py::test_invalid_profile_rejected PASSED

3 passed in < 5s
```

**Current status:** ✅ All tests pass (verified 2.76s runtime).

### Integration Acceptance

```python
# Smoke test for full pipeline
from poker_solver.cfr import CFRSolver
from poker_solver.best_response import nash_conv
from poker_solver.kuhn import kuhn_root

solver = CFRSolver(kuhn_root())
strategy = solver.train(1000)
result = nash_conv(kuhn_root(), strategy)

assert result.exploitability < 0.1  # Reasonable convergence
assert result.nash_conv >= 0.0      # Non-negative
assert result.values[0] + result.values[1] == pytest.approx(0.0)  # Zero-sum
```

## Conclusion

The current `best_response.py` implementation is **correct and complete** for its design scope:
- Pure enumeration oracle for exact best response
- Infoset-consistent via `collect_infosets()` validation
- Fail-closed checks for invalid inputs
- Tractable for games with |I| ≤ 15 per player

**No source code changes required.** The existing implementation satisfies all requirements for Phase 2.

**Future work** should focus on:
1. Expanding test coverage (missing edge cases)
2. Adding structural validation (`validate_game_tree()`)
3. Documenting tractability limits in user docs
4. Implementing scalable BR methods for multi-street games (sampling, abstraction)

**Multi-street tractability** is bounded by exponential infoset growth. Current design is suitable for:
- Single-street toy games (✓)
- Kuhn poker and similar small games (✓)
- Leduc Hold'em and larger games (✗ requires future enhancements)

The pure enumeration oracle should be **preserved as ground truth** for validating future approximate methods.
