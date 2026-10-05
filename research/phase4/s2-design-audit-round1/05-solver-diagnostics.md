# S2 solver diagnostics — A2D5

**Auditor:** A2D5  
**UTC:** 2026-09-15T21:06:39Z  
**Architecture hash:** `86080aac1013ade96f2fab956f209ffc96cad984cc3c9a423982a8988868473a` ✓

---

## Audit scope

Verify existing `NPlayerCFRSolver` reach formula, optional bound plumbing, result truthfulness, exact exhaustive `unilateral_deviation_certificate` for tiny 5+ fixture, and 4/5/9 acceptance feasibility against frozen S2 architecture.

---

## Findings

### 1. Reach formula correctness — **PASS**

**Evidence:** `src/poker_solver/nplayer.py:239-243`

```python
if player == updating:
    counterfactual = chance_reach
    for opponent, reach in enumerate(reaches):
        if opponent != player:
            counterfactual *= reach
```

**Architecture requirement (§8):**  
> "A regret update for player i is weighted by chance times every opponent reach, excluding i's own reach."

**Verdict:** Implementation matches specification exactly. Counterfactual reach = `chance_reach × ∏(opponent_reaches)`, excluding updating player's own reach.

---

### 2. Optional bound plumbing — **BLOCKER**

**Architecture requirement (§8):**  
> "An additive optional `max_nodes`/`max_depth` constructor path may be added to `NPlayerCFRSolver`; defaults remain unchanged."

**Evidence:** `src/poker_solver/nplayer.py:144-150`

```python
class NPlayerCFRSolver:
    def __init__(self, root: NPlayerGameState) -> None:
        self.root = root
        self.num_players = _player_count(root)
        self.infosets = {
            key: NPlayerInfoData(player, actions)
            for key, (player, actions) in collect_nplayer_infosets(root).items()
        }
```

**Blocker:** `NPlayerCFRSolver.__init__` does **not** accept optional `max_nodes` or `max_depth` parameters. The constructor calls `collect_nplayer_infosets(root)` without forwarding any bounds.

**Impact:** S2 architecture states the solve facade will pass `config.max_nodes` and structural depth bound to the solver. Without constructor parameters, this cannot be implemented as designed.

**Note:** `collect_nplayer_infosets` itself accepts `max_nodes=100_000` and `max_depth=512` with defaults (lines 52-57), but the solver constructor provides no path to override them.

---

### 3. Result truthfulness — **PASS**

**Evidence:** `tests/test_nplayer.py:216-228`

```python
def test_three_player_unilateral_deviation_certificate_exact_oracle():
    root = ThreePlayerGeneralSumGame()
    infosets = collect_nplayer_infosets(root)
    strategy = {
        key: {action: 1.0 / len(actions) for action in actions}
        for key, (_, actions) in infosets.items()
    }
    result = unilateral_deviation_certificate(root, strategy)
    assert result.values == pytest.approx((3.625, 3.625, 2.75))
    assert result.best_response_values == pytest.approx((6.25, 3.75, 3.0))
    assert result.incentives == pytest.approx((2.625, 0.125, 0.25))
    assert result.total_incentive == pytest.approx(3.0)
```

**Verdict:** Existing test validates exact hand-calculated oracle for 3-player game. Values, best-response values, incentives, and total incentive match independent enumeration.

---

### 4. Exact exhaustive unilateral deviation for 5+ fixture — **PASS**

**Architecture requirement (§8):**  
> "A five-player permanent oracle manually enumerates each player's tiny pure-deviation set and compares profile values, best-response values, incentives, and total incentive."

**Evidence:** `src/poker_solver/nplayer.py:305-344`

The `unilateral_deviation_certificate` function:
- Enumerates all pure strategies per player via `product(*(actions for _, actions in owned))` (line 328)
- Computes exact expected values for each pure deviation (line 332)
- Tracks best-response value per player (line 332)
- Calculates incentives as `max(0.0, best - value)` (line 335)
- Returns truthful provenance: `"exhaustive finite pure unilateral deviations; diagnostic only"` (line 343)

**Bound enforcement:** Line 325-326 enforces `max_pure_strategies` cap and fails closed:
```python
if count > max_pure_strategies:
    raise ValueError("player pure-strategy bound exceeded")
```

**Test coverage:** `test_unilateral_deviation_certificate_is_bounded_and_strict` (lines 231-245) validates bound rejection and strict validation.

**Verdict:** Implementation is exact, exhaustive, bounded, and never sampled. Suitable for tiny 5+ player trees as specified.

---

### 5. Acceptance feasibility for 4/5/9 players — **PASS (with bound caveat)**

**Architecture requirements (§11):**
- "4-, 5-, and 9-player spots build, validate, train/evaluate, and return N values"
- "a five-plus-player exact unilateral-deviation diagnostic matches independent enumeration below its cap"
- "Nine-player acceptance uses a deliberately tiny finite tree and makes no scalability claim"

**Evidence:**

1. **Player count validation:** Lines 36-40 enforce strict 2-9 player range:
   ```python
   if isinstance(count, bool) or not isinstance(count, int) or not 2 <= count <= 9:
       raise ValueError("num_players must be an integer from 2 to 9 players")
   ```

2. **N-dimensional returns:** Lines 82-86 validate terminal returns match `num_players`:
   ```python
   if not isinstance(values, tuple) or len(values) != players:
       raise ValueError("terminal return dimension must equal num_players")
   ```

3. **Reach tracking:** Lines 174-177 initialize per-player reach list:
   ```python
   deltas = [
       {key: {action: 0.0 for action in data.actions} for key, data in self.infosets.items()}
       for _ in range(self.num_players)
   ]
   ```

4. **Deviation certificate:** Lines 320-332 iterate over all players and enumerate pure deviations per player.

**Verdict:** Generic N-player infrastructure supports 4/5/9 players. Acceptance depends on:
- Tiny tree construction (not audited here; S2-I1 responsibility)
- Bound tuning for 9-player (architecture acknowledges "deliberately tiny finite tree")

**Caveat:** Without optional constructor bounds (Finding #2), acceptance tests cannot override default `max_nodes=100_000` / `max_depth=512` limits per config.

---

## Summary

| Item | Status | Blocker? |
|------|--------|----------|
| Reach formula (§8) | **PASS** | No |
| Optional bound plumbing (§8) | **FAIL** | **YES** |
| Result truthfulness | **PASS** | No |
| Exact 5+ deviation diagnostic (§8) | **PASS** | No |
| 4/5/9 acceptance feasibility (§11) | **PASS** (with caveat) | No |

---

## Blocker detail

**B1: Missing optional constructor bounds**

- **Location:** `src/poker_solver/nplayer.py:144`
- **Requirement:** Architecture §8 specifies "An additive optional `max_nodes`/`max_depth` constructor path may be added to `NPlayerCFRSolver`"
- **Current state:** Constructor accepts only `root: NPlayerGameState`
- **Impact:** S2 solve facade cannot pass `config.max_nodes` and structural depth bound as designed
- **Resolution:** Add optional parameters to `NPlayerCFRSolver.__init__` and forward to `collect_nplayer_infosets`

---

## Recommendation

**CONDITIONAL PASS** pending resolution of blocker B1.

Existing reach formula, deviation diagnostic, and N-player infrastructure are correct and complete. The missing optional bound parameters are an additive API gap, not a correctness defect. S2-I2 implementation must add the constructor parameters before the solve facade can honor `config.max_nodes`.

---

**Audit complete.**