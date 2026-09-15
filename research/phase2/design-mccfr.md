# External-sampling MCCFR design specification

## Overview

This document specifies external-sampling Monte Carlo Counterfactual Regret Minimization (MCCFR) compatible with the existing generic `GameState` protocol and vanilla CFR implementation. External-sampling MCCFR samples one outcome at chance nodes and one action at opponent nodes while traversing all actions at updating-player nodes, providing an unbiased estimator with lower iteration cost than full-tree vanilla CFR.

## Scope and compatibility

- **Game class**: finite, sequential, two-player zero-sum, perfect recall.
- **Protocol**: existing `GameState` protocol from `model.py` (unchanged).
- **Vanilla CFR**: `CFRSolver` in `cfr.py` remains available and unchanged.
- **New class**: `MCCFRSolver` with the same public API surface as `CFRSolver`.
- **Convergence guarantee**: two-player Nash convergence per Lanctot et al. 2009.
- **Out of scope**: multiplayer, general-sum, CFR+, discounted CFR, pruning.

## Algorithm specification

### External-sampling traversal

For each iteration `t` and each updating player `p ∈ {0, 1}`:

1. Start at the root state.
2. At **chance nodes**: sample one outcome `a ~ chance_outcomes()` using the solver's dedicated `random.Random(seed)` instance; traverse `child(a)`.
3. At **opponent nodes** (current_player ≠ p): sample one action `a ~ σ^t(I)` from the current strategy; traverse `child(a)`.
4. At **updating-player nodes** (current_player = p): traverse **all** legal actions; compute strategy-weighted node value and accumulate sampled counterfactual regret.
5. At **terminal nodes**: return `returns()[p]`.

### Update equations

Let `I` be an information set owned by player `p`, `A(I)` its legal actions, `σ^t(I)` the current strategy at iteration `t`, `π^{-p}` the opponent reach probability, and `π^c` the chance reach probability along the sampled path.

**Sampled counterfactual value** for action `a` at information set `I`:
```
v^t(I, a) = value returned by recursive traversal of child(a)
```

**Sampled node value**:
```
v^t(I) = Σ_{a ∈ A(I)} σ^t(I, a) · v^t(I, a)
```

**Sampled counterfactual regret** (accumulated during the updating-player traversal):
```
ΔR^t(I, a) = π^{-p} · π^c · (v^t(I, a) - v^t(I))
```

**Cumulative regret update** (after traversal completes):
```
R^{t+1}(I, a) = R^t(I, a) + ΔR^t(I, a)
```

**Current strategy** (regret matching, computed at the start of each iteration):
```
σ^t(I, a) = R^t_+(I, a) / Σ_{a' ∈ A(I)} R^t_+(I, a')   if denominator > 0
          = 1 / |A(I)|                                  otherwise

where R^t_+(I, a) = max(0, R^t(I, a))
```

### Average strategy

The average strategy is accumulated **only at opponent nodes** during the updating-player traversal, using the two-player simple-averaging convention:

```
S^{t+1}(I, a) = S^t(I, a) + π^p · σ^t(I, a)
```

where `π^p` is the updating player's reach probability to information set `I` along the sampled path.

**Returned average strategy** (after all iterations):
```
σ̄(I, a) = S(I, a) / Σ_{a' ∈ A(I)} S(I, a')   if denominator > 0
         = 1 / |A(I)|                         otherwise
```

## Implementation requirements

### Class structure

```python
class MCCFRSolver:
    def __init__(self, root: GameState, seed: int = 0):
        """Initialize solver with root state and RNG seed.
        
        Args:
            root: Root game state implementing GameState protocol.
            seed: Integer seed for random.Random instance (default 0).
        """
        self.root = root
        self.seed = seed
        self.rng = random.Random(seed)
        self.infosets: dict[InfoKey, InfoData] = {}  # lazy discovery
        self.iterations = 0

    def current_strategy(self) -> Strategy:
        """Return current regret-matching strategy."""

    def average_strategy(self) -> Strategy:
        """Return average strategy across all iterations."""

    def train(self, iterations: int) -> Strategy:
        """Run iterations and return average strategy.
        
        Args:
            iterations: Positive integer iteration count.
            
        Returns:
            Average strategy after training.
            
        Raises:
            ValueError: if iterations <= 0 or not an integer.
        """

    def values(self) -> tuple[float, float]:
        """Return expected values under average strategy."""
```

### RNG ownership and determinism

- Each `MCCFRSolver` instance owns a dedicated `random.Random(seed)` object.
- The seed is stored as `self.seed` and included in serialized output.
- Sampling order:
  1. Chance outcomes: sample using `rng.choices(outcomes, weights=probabilities, k=1)[0]` with stable action order from `chance_outcomes()`.
  2. Opponent actions: sample using `rng.choices(actions, weights=policy_values, k=1)[0]` with stable action order from `legal_actions()`.
- **Determinism contract**: identical interpreter, root state, seed, and iteration count produce byte-identical canonical JSON output (sorted keys, stable float repr).
- Different seeds are permitted to produce different trajectories; correctness is measured by convergence metrics, not trajectory identity.

### Lazy infoset discovery

- `MCCFRSolver` does **not** call `collect_infosets(root)` at initialization.
- Information sets are discovered and added to `self.infosets` on first visit during traversal.
- This enables MCCFR to handle games with enormous chance trees (e.g., full Hold'em deals) where only a tiny fraction of information sets are ever reached.
- When an information set `I` is first encountered:
  ```python
  if key not in self.infosets:
      self.infosets[key] = InfoData(player, actions)
  ```
- The `InfoData` dataclass is reused from `cfr.py` (unchanged).

### Serialization contract

**Canonical JSON output** for `average_strategy()` and solver state:

- Information set keys: sorted by `repr(key)` for deterministic ordering.
- Action dictionaries: sorted by action (actions are `@dataclass(order=True)`).
- Floating-point: Python's default `repr()` (sufficient for local regression; RFC 8785 conformance not claimed).
- Metadata: include `{"algorithm": "mccfr-external", "seed": <int>, "iterations": <int>}` in serialized solver state.

**Example**:
```json
{
  "algorithm": "mccfr-external",
  "seed": 42,
  "iterations": 1000,
  "strategy": {
    "('kuhn-v1', 0, 'J', ())": {
      "Action(kind='bet', amount=0)": 0.0,
      "Action(kind='check', amount=0)": 1.0
    }
  }
}
```

### API compatibility with vanilla CFR

`MCCFRSolver` provides the same public methods as `CFRSolver`:

- `__init__(root, seed=0)`: constructor (seed parameter added).
- `current_strategy() -> Strategy`: regret-matching strategy.
- `average_strategy() -> Strategy`: time-averaged strategy.
- `train(iterations: int) -> Strategy`: run iterations, return average strategy.
- `values() -> tuple[float, float]`: expected values under average strategy (delegates to `expected_values(root, average_strategy())` from `cfr.py`).
- `.iterations`: public integer attribute tracking total iterations run.

The only API difference is the optional `seed` parameter in `__init__`.

## Testing requirements

### Determinism tests

**test_mccfr_same_seed_is_deterministic**:
```python
def test_mccfr_same_seed_is_deterministic():
    solver1 = MCCFRSolver(kuhn_root(), seed=42)
    strategy1 = solver1.train(100)
    solver2 = MCCFRSolver(kuhn_root(), seed=42)
    strategy2 = solver2.train(100)
    assert strategy1 == strategy2  # exact dict equality
    assert solver1.seed == solver2.seed == 42
```

**test_mccfr_different_seeds_may_differ**:
```python
def test_mccfr_different_seeds_may_differ():
    solver1 = MCCFRSolver(kuhn_root(), seed=1)
    strategy1 = solver1.train(100)
    solver2 = MCCFRSolver(kuhn_root(), seed=2)
    strategy2 = solver2.train(100)
    # Strategies are allowed to differ; no assertion on equality
    assert solver1.seed != solver2.seed
```

### Convergence tests

**test_mccfr_kuhn_approaches_value_with_seed_matrix**:
```python
@pytest.mark.parametrize("seed", [0, 1, 42, 123, 999])
def test_mccfr_kuhn_approaches_value_with_seed_matrix(seed):
    solver = MCCFRSolver(kuhn_root(), seed=seed)
    strategy = solver.train(10_000)
    value = expected_values(kuhn_root(), strategy)[0]
    assert value == pytest.approx(KUHN_VALUE_P0, abs=0.03)
    nc = nash_conv(kuhn_root(), strategy).nash_conv
    assert nc < 0.10  # looser than vanilla due to sampling variance
```

**Rationale**: Seed matrix (5 seeds) with 10,000 iterations each. Absolute EV tolerance `0.03` and NashConv threshold `0.10` are pre-registered gates based on sampling variance. These are looser than vanilla CFR's `0.003` EV and `0.03` NashConv because MCCFR has higher per-iteration variance.

### Vanilla vs MCCFR agreement

**test_vanilla_and_mccfr_agree_on_kuhn**:
```python
def test_vanilla_and_mccfr_agree_on_kuhn():
    vanilla_solver = CFRSolver(kuhn_root())
    vanilla_strategy = vanilla_solver.train(5_000)
    vanilla_ev = expected_values(kuhn_root(), vanilla_strategy)
    
    mccfr_solver = MCCFRSolver(kuhn_root(), seed=42)
    mccfr_strategy = mccfr_solver.train(20_000)
    mccfr_ev = expected_values(kuhn_root(), mccfr_strategy)
    
    assert vanilla_ev[0] == pytest.approx(mccfr_ev[0], abs=0.03)
    assert vanilla_ev[1] == pytest.approx(mccfr_ev[1], abs=0.03)
```

**Rationale**: MCCFR uses 4x iterations to compensate for sampling variance. Absolute tolerance `0.03` is pre-registered based on expected MCCFR variance on Kuhn.

### Probability normalization

**test_mccfr_probabilities_normalize**:
```python
def test_mccfr_probabilities_normalize():
    solver = MCCFRSolver(kuhn_root(), seed=0)
    solver.train(100)
    for policy in solver.average_strategy().values():
        assert sum(policy.values()) == pytest.approx(1.0)
        assert all(p >= 0 for p in policy.values())
```

### Lazy discovery validation

**test_mccfr_lazy_discovery_on_large_chance_tree**:
```python
def test_mccfr_lazy_discovery_on_large_chance_tree():
    # Synthetic game with 1000 chance outcomes but only ~10 visited per sample
    root = LargeChanceGame()  # hypothetical test fixture
    solver = MCCFRSolver(root, seed=0)
    solver.train(50)
    # Verify that infosets discovered << total possible infosets
    assert len(solver.infosets) < 100  # far fewer than 1000 * branches
```

**Note**: `LargeChanceGame` is a placeholder for a synthetic fixture with a large chance tree. If no such fixture exists in Phase 2, this test may be deferred or replaced with a comment documenting the lazy-discovery property.

### Chance sampling frequency test

**test_mccfr_chance_sampling_frequencies**:
```python
def test_mccfr_chance_sampling_frequencies():
    # Synthetic game with known chance distribution
    # Run MCCFR with fixed seed and count sampled outcomes
    solver = MCCFRSolver(UniformChanceGame(), seed=42)
    solver.train(1000)
    # Extract sampling counts from instrumented traversal or logs
    # Assert counts match expected distribution within tolerance
    # (Exact fixture TBD based on available test games)
```

**Rationale**: Validates that chance sampling respects declared probabilities. Requires a simple test game with observable chance outcomes. If not immediately available, document as a future test.

### API compatibility

**test_mccfr_api_matches_vanilla**:
```python
def test_mccfr_api_matches_vanilla():
    vanilla = CFRSolver(kuhn_root())
    mccfr = MCCFRSolver(kuhn_root(), seed=0)
    
    # Both support the same methods
    assert hasattr(mccfr, 'current_strategy')
    assert hasattr(mccfr, 'average_strategy')
    assert hasattr(mccfr, 'train')
    assert hasattr(mccfr, 'values')
    assert hasattr(mccfr, 'iterations')
    
    mccfr.train(10)
    assert mccfr.iterations == 10
    assert isinstance(mccfr.values(), tuple)
    assert len(mccfr.values()) == 2
```

## Acceptance criteria summary

| Criterion | Gate |
|-----------|------|
| Determinism | Same seed/input/iterations → byte-identical canonical JSON |
| Seed independence | Different seeds accepted; trajectories may differ |
| Kuhn convergence | Seed matrix (5 seeds, 10k iter): abs EV error ≤ 0.03, NashConv < 0.10 |
| Vanilla agreement | Kuhn: vanilla 5k iter vs MCCFR 20k iter, abs EV diff ≤ 0.03 |
| Probability validity | All policies sum to 1.0 ± 1e-9, all probabilities ≥ 0 |
| Lazy discovery | Information sets created on first visit, not at init |
| API compatibility | Same public methods as `CFRSolver` (plus seed parameter) |
| Vanilla CFR unchanged | `CFRSolver` in `cfr.py` remains available and unmodified |

## Implementation notes

### Reach probability tracking

During traversal, track three reach probabilities:
- `p0`: player 0 reach (product of player 0's action probabilities).
- `p1`: player 1 reach (product of player 1's action probabilities).
- `pc`: chance reach (product of sampled chance outcome probabilities).

At updating-player nodes:
- Counterfactual reach = `(p1 if updating == 0 else p0) * pc`.
- Owner reach (for averaging) = `(p0 if player == 0 else p1)`.

At opponent nodes (during updating-player traversal):
- Accumulate average strategy using owner reach of the **updating player** (not the opponent).

### Traversal structure

```python
def _walk_external(
    self,
    state: GameState,
    updating: int,
    p0: float,
    p1: float,
    pc: float,
    profile: Strategy,
) -> float:
    player = state.current_player()
    if player == TERMINAL:
        return state.returns()[updating]
    
    if player == CHANCE:
        # Sample one outcome
        outcomes = state.chance_outcomes()
        actions, probs = zip(*outcomes)
        sampled_action = self.rng.choices(actions, weights=probs, k=1)[0]
        sampled_prob = dict(outcomes)[sampled_action]
        return self._walk_external(
            state.child(sampled_action),
            updating,
            p0,
            p1,
            pc * sampled_prob,
            profile,
        )
    
    actions = state.legal_actions()
    key = state.information_state_key(player)
    
    # Lazy discovery
    if key not in self.infosets:
        self.infosets[key] = InfoData(player, actions)
    
    policy = profile[key]
    
    if player == updating:
        # Traverse all actions
        action_values = {}
        for action in actions:
            new_p0 = p0 * policy[action] if player == 0 else p0
            new_p1 = p1 * policy[action] if player == 1 else p1
            action_values[action] = self._walk_external(
                state.child(action), updating, new_p0, new_p1, pc, profile
            )
        
        node_value = sum(policy[a] * action_values[a] for a in actions)
        cf_reach = (p1 if player == 0 else p0) * pc
        
        # Accumulate regret
        for action in actions:
            self.infosets[key].regrets[action] += cf_reach * (
                action_values[action] - node_value
            )
        
        return node_value
    else:
        # Opponent node: sample one action and accumulate average strategy
        action_list = list(actions)
        probs = [policy[a] for a in action_list]
        sampled_action = self.rng.choices(action_list, weights=probs, k=1)[0]
        
        # Accumulate average strategy (updating player's reach)
        updating_reach = p0 if updating == 0 else p1
        for action in actions:
            self.infosets[key].strategy_sum[action] += (
                updating_reach * policy[action]
            )
        
        new_p0 = p0 if player == 1 else p0  # opponent doesn't update p0
        new_p1 = p1 if player == 0 else p1  # opponent doesn't update p1
        return self._walk_external(
            state.child(sampled_action), updating, new_p0, new_p1, pc, profile
        )
```

**Note**: The above is illustrative pseudocode. The actual implementation must handle reach updates correctly: when sampling at an opponent node, the opponent's reach is **not** multiplied by the sampled action probability (it remains 1.0 along the sampled path), but the updating player's reach is carried forward unchanged.

### Iteration loop

```python
def train(self, iterations: int) -> Strategy:
    if not isinstance(iterations, int) or iterations <= 0:
        raise ValueError("iterations must be a positive integer")
    
    for _ in range(iterations):
        # Compute current strategy via regret matching
        snapshot = self.current_strategy()
        
        # Traverse once per player
        self._walk_external(self.root, 0, 1.0, 1.0, 1.0, snapshot)
        self._walk_external(self.root, 1, 1.0, 1.0, 1.0, snapshot)
        
        self.iterations += 1
    
    return self.average_strategy()
```

**Important**: Regret updates are accumulated **during** the traversal (inside `_walk_external`), not in a separate post-processing step. The `snapshot` strategy is frozen at the start of each iteration and used for both traversals.

## References

- Original CFR: Zinkevich et al. 2007, https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- MCCFR: Lanctot et al. 2009, https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html
- OpenSpiel external-sampling implementation: https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/algorithms/external_sampling_mccfr.py
- OpenSpiel algorithm inventory: https://openspiel.readthedocs.io/en/latest/algorithms.html
- Python `random` module: https://docs.python.org/3/library/random.html
- Phase 2 research: `mccfr-vs-cfr.md`, `determinism-performance.md`, `accuracy-fixtures.md`

## Exclusions

- **CFR+ and discounted CFR**: separate algorithms with different regret update rules; not mixed into MCCFR.
- **Outcome sampling**: different sampling scheme; not implemented in Phase 2.
- **Pruning**: optimization requiring separate correctness proof.
- **Multiplayer/general-sum**: outside two-player zero-sum convergence guarantee.
- **Abstraction**: suit isomorphism, card abstraction, action abstraction are separate techniques.
- **Cross-platform byte-identical floats**: not claimed without RFC 8785 serializer.

## File ownership

This design document is the **sole** deliverable for this task. Implementation will be done in a separate task and will:

- Add `MCCFRSolver` class to `src/poker_solver/cfr.py` or a new `src/poker_solver/mccfr.py` module.
- Add tests to `tests/test_cfr.py` or a new `tests/test_mccfr.py` module.
- Leave `CFRSolver` and all existing tests unchanged.

No source or test files are modified by this design task.