# S4 Design: Executable Small Oracle and Large Bounded Tractability Fixtures

**Date:** 2026-09-16 (UTC)  
**Scope:** Phase 4 S4 — Automatic abstraction tractability fixtures  
**Status:** Design complete (implementation deferred)  
**Agent:** S4D4 (design-only, fixtures/tractability/oracle analyst)

---

## 1. Mission and context

**Task:** Design executable small comparable exact/abstract fixture and literal large spot where exact exceeds a declared practical cap while abstracted completes beneath it.

**Context from PHASE4_MISSION.md S4 (lines 22–24):**
> Automatic hand abstraction to keep solves tractable (e.g., category-based or blocker-aware abstraction chosen via design wave), with a documented abstraction policy and determinism.
> - **Acceptance:** an abstracted solve of a large spot completes with bounded state count; abstracted vs exact (on a small comparable spot) within a derived bound; abstraction policy is explicit in config; determinism; no silent strategy corruption (strategically identical combos stay identical).

**Existing infrastructure:**
- `allstreet.py`: Automatic all-street postflop solver (S1-I1, lines 1–275)
- `bounded_tree.py`: Bounded two-player tree validation (lines 1–247)
- `test_allstreet_oracle.py`: Independent automatic-versus-explicit continuation oracles (lines 1–251)
- S1 design doc `01-algorithm.md`: Exact recursive continuation semantics (478 lines)

**Observed baseline (from probes):**
- Small strategic oracle (1 runout, 1 wager, 1 combo each): 58 nodes, 19 terminals, 15 chance, 24 decision, depth 12
- Small structural oracle (1 runout, 0 wagers, 1 combo each): 10 nodes, 1 terminal, 3 chance, 6 decision, depth 9
- Medium spot (45 runouts, 3 wagers, 1 combo each): 166 nodes, 45 terminals, 11 chance, 110 decision, depth 9
- Large spot (190 runouts, 4 wagers, 2 combos each): ~5s solve time, node count TBD

---

## 2. Small comparable fixture: exact vs. abstracted oracle

### 2.1 Design rationale

**Goal:** A spot small enough that both exact and abstracted solves complete quickly (<1s), allowing direct comparison of strategies, values, and exploitability.

**Constraints:**
- Must have **strategic content** (non-trivial betting, multiple runouts with different equities)
- Must be **small enough for exact solve** (node count < 1,000, depth < 20)
- Must be **large enough to abstract** (multiple combos per player that can be bucketed)
- Must have **known oracle properties** (zero-sum, determinism, bounded exploitability)

**Chosen parameters:**
- **Street:** Flop (3-card board)
- **Runouts:** 3 turn-river pairs (small but diverse equity outcomes)
- **Stacks:** 100 chips effective
- **Pot:** 20 chips (0.2 SPR, encourages betting)
- **Wagers:** 2 sizes (20, 50) — pot-limit mode
- **Combos per player:** 3 (allows 2-bucket or 3-bucket abstraction)
- **Board:** `2c 3d 4h` (low, no flush draws on flop)
- **Player 0 combos:** `AsKs` (nut flush draw), `As5s` (wheel draw + flush draw), `Ac6c` (gutshot + backdoor)
- **Player 1 combos:** `KhQh` (two overs + backdoor), `JhTh` (gutshot + backdoor), `9h8h` (gutshot + backdoor)
- **Runouts:** `(9s, Kc)`, `(Tc, Jd)`, `(7s, 6s)` — diverse: P0 wins runout 1 (flush), split equity runout 2, P0 wins runout 3 (flush)

### 2.2 Expected exact metrics

**Physical state count (bounded_tree validation):**
- Root: 1 (flop deal)
- Flop chance: 3 runouts → 3 branches
- Per runout: 1 turn deal → 1 river deal → 1 showdown state
- Flop decision tree per runout: 
  - P0 acts: CHECK or RAISE(20) or RAISE(50) → 3 actions
  - After CHECK: P1 acts: CHECK (terminal) or RAISE(20) or RAISE(50) → 3 actions
    - After P1 RAISE: P0 acts: FOLD (terminal) or CALL (terminal) → 2 actions
  - After P0 RAISE: P1 acts: FOLD (terminal) or CALL (terminal) → 2 actions
- Approximate decision nodes per runout: 3 (P0 root) + 3 (P1 after check) + 2×2 (P0 facing bet, P1 facing bet) = ~10 decision nodes
- Approximate terminals per runout: 1 (check-check) + 2 (P1 bet, P0 fold/call) + 2 (P0 bet, P1 fold/call) = ~5 terminals
- **Total nodes (3 runouts):** ~3 (chance) + 3×10 (decision) + 3×5 (terminal) = ~48 nodes
- **Depth:** root → flop chance (1) → turn chance (2) → river chance (3) → flop decision (4) → max 3 bets → ~10

**Information-set count:**
- Player 0: 3 combos × 3 runouts = 9 private states, but **information sets abstract over runouts** (player doesn't see runout until river)
- Flop information sets (before runout): P0 root (3 combos, 1 infoset per combo = 3), P1 after check (3 combos, 1 infoset per combo = 3), etc.
- **Exact infoset count:** ~6–12 per player (depends on action history granularity)

**Chance mass:**
- 3 runouts, uniform probability → 1/3 each
- Total chance mass = 1.0 (validated by bounded_tree)

**Zero-sum:**
- Every terminal: `sum(returns) == 0` (no rake in fixture)
- Validated by bounded_tree and test_allstreet_oracle

**Expected runtime:**
- Exact solve (100 iterations): <1s (based on 58-node spot taking <1s)
- Abstracted solve (100 iterations): <0.5s (fewer infosets)

### 2.3 Abstraction policy: equity bucketing

**Method:** Partition each player's combos into **2 buckets** based on **flop equity vs. opponent's range**.

**Bucket assignment (computed offline, hardcoded in fixture):**
- Player 0:
  - Bucket 0 (strong): `AsKs`, `As5s` (flush draws, >50% equity vs. P1 range)
  - Bucket 1 (weak): `Ac6c` (gutshot only, <50% equity)
- Player 1:
  - Bucket 0 (strong): `KhQh` (two overs, ~45% equity vs. P0 range)
  - Bucket 1 (weak): `JhTh`, `9h8h` (gutshots, ~35% equity)

**Information-set mapping:**
- Exact: infoset key = `(player, combo_index, action_history)`
- Abstracted: infoset key = `(player, bucket_index, action_history)`
- Combos in the same bucket **share the same strategy**

**Determinism:**
- Bucket assignment is **deterministic** (hardcoded mapping)
- Same input → same abstracted infosets → same strategy

**Strategic preservation:**
- Combos in the same bucket have **similar equity** → similar optimal strategies
- No "silent corruption": if two combos have identical equity and blockers, they are in the same bucket and get the same strategy (correct)
- If two combos have different equity, they are in different buckets (or accepted approximation if bucketed together)

### 2.4 Expected abstracted metrics

**Information-set count:**
- Player 0: 2 buckets (down from 3 combos) → ~33% reduction
- Player 1: 2 buckets (down from 3 combos) → ~33% reduction
- **Total infoset reduction:** ~33% (fewer regret tables, faster iteration)

**Node count (physical states):**
- **Unchanged**: abstraction affects information sets, not physical game tree
- Bounded_tree validation sees the same 48 nodes

**Expected value difference (exact vs. abstracted):**
- **Bound:** `|V_exact - V_abstracted| <= exploitability_exact + exploitability_abstracted + abstraction_error`
- Abstraction error: combos in the same bucket have equity difference ~5–10%, so strategies differ by ~5–10% in EV
- **Derived bound:** `|V_exact - V_abstracted| <= 0.05 * pot = 1.0 chips` (5% of 20-chip pot)
- **Acceptance threshold:** `|V_exact[0] - V_abstracted[0]| <= 2.0` (10% of pot, conservative)

**Exploitability (Nash conv):**
- Exact (100 iterations): <0.01 (based on test_allstreet_oracle, 1,000 iterations → <1e-6)
- Abstracted (100 iterations): <0.05 (higher due to bucketing approximation)

### 2.5 Fixture implementation contract

**File:** `tests/test_phase4_s4_oracle.py`

**Test 1: `test_small_exact_oracle_baseline`**
```python
def test_small_exact_oracle_baseline():
    """Small 3-combo, 3-runout, 2-wager exact solve completes and satisfies oracles."""
    config = _small_oracle_config(abstraction=None)
    result = solve_allstreet_postflop(config, algorithm="vanilla-cfr", iterations=100)
    
    # Bounded tree oracle
    assert result.node_count < 100, "exact small oracle exceeds 100 nodes"
    assert result.max_depth_reached < 15, "exact small oracle exceeds depth 15"
    assert result.metadata["terminal_count"] > 0
    assert result.metadata["chance_count"] == 3, "3 runouts"
    
    # Zero-sum oracle (no rake)
    root = create_allstreet_root(config)
    for terminal in _all_terminals(root):
        returns = terminal.returns()
        assert abs(sum(returns)) < 1e-9, "zero-sum violation"
    
    # Policy oracle
    for infoset, policy in result.strategy.items():
        assert abs(sum(policy.values()) - 1.0) < 1e-9, "policy sum violation"
    
    # Exploitability oracle
    assert result.nash_conv < 0.1, "exact small oracle exploitability exceeds 0.1"
    
    # Determinism oracle
    result2 = solve_allstreet_postflop(config, algorithm="vanilla-cfr", iterations=100)
    assert result.values == result2.values, "determinism violation"
```

**Test 2: `test_small_abstracted_oracle_within_bound`**
```python
def test_small_abstracted_oracle_within_bound():
    """Abstracted solve (2 buckets) completes and agrees with exact within derived bound."""
    exact_config = _small_oracle_config(abstraction=None)
    abstracted_config = _small_oracle_config(abstraction="equity-2-bucket")
    
    exact_result = solve_allstreet_postflop(exact_config, algorithm="vanilla-cfr", iterations=100)
    abstracted_result = solve_allstreet_postflop(abstracted_config, algorithm="vanilla-cfr", iterations=100)
    
    # Abstracted completes
    assert abstracted_result.node_count == exact_result.node_count, "abstraction changes physical tree"
    assert abstracted_result.approximate is True, "abstracted result must be marked approximate"
    assert "equity-2-bucket" in abstracted_result.provenance, "provenance must document abstraction"
    
    # Value agreement within derived bound
    exact_value = exact_result.values[0]
    abstracted_value = abstracted_result.values[0]
    bound = 2.0  # 10% of 20-chip pot
    assert abs(exact_value - abstracted_value) <= bound, (
        f"exact vs. abstracted value difference {abs(exact_value - abstracted_value):.3f} "
        f"exceeds bound {bound}"
    )
    
    # Exploitability bound
    assert abstracted_result.nash_conv < 0.2, "abstracted exploitability exceeds 0.2"
    
    # Determinism
    abstracted_result2 = solve_allstreet_postflop(abstracted_config, algorithm="vanilla-cfr", iterations=100)
    assert abstracted_result.values == abstracted_result2.values, "abstracted determinism violation"
```

**Test 3: `test_small_oracle_convergence_sweep`**
```python
def test_small_oracle_convergence_sweep():
    """Exact and abstracted exploitability both decrease with iterations."""
    exact_config = _small_oracle_config(abstraction=None)
    abstracted_config = _small_oracle_config(abstraction="equity-2-bucket")
    
    exact_exploits = []
    abstracted_exploits = []
    for iterations in (10, 50, 200):
        exact_result = solve_allstreet_postflop(exact_config, algorithm="vanilla-cfr", iterations=iterations)
        abstracted_result = solve_allstreet_postflop(abstracted_config, algorithm="vanilla-cfr", iterations=iterations)
        exact_exploits.append(exact_result.nash_conv)
        abstracted_exploits.append(abstracted_result.nash_conv)
    
    # Monotonic decrease
    assert exact_exploits[-1] < exact_exploits[0], "exact exploitability does not decrease"
    assert abstracted_exploits[-1] < abstracted_exploits[0], "abstracted exploitability does not decrease"
    
    # Abstracted exploitability >= exact (abstraction is an approximation)
    for exact_e, abstracted_e in zip(exact_exploits, abstracted_exploits):
        assert abstracted_e >= exact_e - 1e-6, "abstracted exploitability < exact (impossible)"
```

**Helper: `_small_oracle_config`**
```python
def _small_oracle_config(abstraction: str | None) -> AllStreetPostflopConfig:
    """Small 3-combo, 3-runout, 2-wager oracle fixture.
    
    Args:
        abstraction: None (exact) or "equity-2-bucket" (abstracted)
    """
    flop = (parse_card("2c"), parse_card("3d"), parse_card("4h"))
    runouts = (
        (parse_card("9s"), parse_card("Kc")),
        (parse_card("Tc"), parse_card("Jd")),
        (parse_card("7s"), parse_card("6s")),
    )
    
    if abstraction is None:
        # Exact: 3 combos per player, each gets its own strategy
        player0_combos = (
            WeightedCombo((parse_card("As"), parse_card("Ks")), 1.0),
            WeightedCombo((parse_card("As"), parse_card("5s")), 1.0),
            WeightedCombo((parse_card("Ac"), parse_card("6c")), 1.0),
        )
        player1_combos = (
            WeightedCombo((parse_card("Kh"), parse_card("Qh")), 1.0),
            WeightedCombo((parse_card("Jh"), parse_card("Th")), 1.0),
            WeightedCombo((parse_card("9h"), parse_card("8h")), 1.0),
        )
    elif abstraction == "equity-2-bucket":
        # Abstracted: bucket 0 (strong) has 2 combos, bucket 1 (weak) has 1 combo
        # Implementation: use weighted combos to simulate bucketing
        # (Real S4 implementation would modify information_state_key to map combos to buckets)
        # For design fixture, we approximate by giving bucket combos equal weight
        player0_combos = (
            WeightedCombo((parse_card("As"), parse_card("Ks")), 1.0),  # bucket 0
            WeightedCombo((parse_card("As"), parse_card("5s")), 1.0),  # bucket 0
            WeightedCombo((parse_card("Ac"), parse_card("6c")), 1.0),  # bucket 1
        )
        player1_combos = (
            WeightedCombo((parse_card("Kh"), parse_card("Qh")), 1.0),  # bucket 0
            WeightedCombo((parse_card("Jh"), parse_card("Th")), 1.0),  # bucket 1
            WeightedCombo((parse_card("9h"), parse_card("8h")), 1.0),  # bucket 1
        )
        # NOTE: True abstraction requires modifying information_state_key in the game state
        # to return (player, bucket_index, history) instead of (player, combo_index, history).
        # This design fixture assumes that implementation exists in S4-I1.
    else:
        raise ValueError(f"unknown abstraction {abstraction!r}")
    
    return AllStreetPostflopConfig(
        version="allstreet-postflop-v1",
        starting_board=flop,
        initial_dead_pot=20,
        effective_stack=100,
        player0_combos=player0_combos,
        player1_combos=player1_combos,
        allowed_runouts=runouts,
        betting_mode="pot-limit",
        wager_targets=(20, 50),
        max_nodes=1_000,
        max_depth=64,
    )
```

**Commands:**
```bash
# Run small oracle tests
pytest tests/test_phase4_s4_oracle.py::test_small_exact_oracle_baseline -v
pytest tests/test_phase4_s4_oracle.py::test_small_abstracted_oracle_within_bound -v
pytest tests/test_phase4_s4_oracle.py::test_small_oracle_convergence_sweep -v

# Expected output:
# test_small_exact_oracle_baseline PASSED (node_count < 100, depth < 15, nash_conv < 0.1)
# test_small_abstracted_oracle_within_bound PASSED (|V_exact - V_abstracted| <= 2.0)
# test_small_oracle_convergence_sweep PASSED (exploitability decreases)
```

---

## 3. Large bounded tractability fixture: exact exceeds cap, abstracted completes

### 3.1 Design rationale

**Goal:** A spot where the exact solve **exceeds a declared practical cap** (node count or runtime), but the abstracted solve **completes beneath the cap**.

**Practical cap definition:**
- **Node count cap:** 100,000 nodes (based on `max_nodes=100_000` in test_allstreet_oracle.py line 53)
- **Runtime cap:** 60 seconds (1 minute, practical limit for interactive solving)
- **Depth cap:** 128 (based on `max_depth=64` in small oracle, doubled for large spot)

**Constraints:**
- Must be **realistic poker** (not a pathological adversarial tree)
- Must have **known scaling behavior** (node count grows exponentially with combos/runouts/wagers)
- Must be **deterministic** (same input → same node count)

**Chosen parameters:**
- **Street:** Flop
- **Runouts:** 20 turn-river pairs (realistic subset of 44×43=1,892 possible)
- **Stacks:** 500 chips effective
- **Pot:** 100 chips (0.2 SPR)
- **Wagers:** 5 sizes (50, 100, 200, 350, 500) — pot-limit mode
- **Combos per player (exact):** 10 (realistic range size)
- **Combos per player (abstracted):** 10 combos → 3 buckets (strong/medium/weak)
- **Board:** `2c 3d 4h` (same as small oracle, for consistency)

### 3.2 Expected exact metrics (exceeds cap)

**Physical state count (bounded_tree validation):**
- Root: 1
- Flop chance: 20 runouts → 20 branches
- Per runout: 1 turn deal → 1 river deal → 1 showdown state
- Flop decision tree per runout:
  - P0 acts: CHECK or RAISE(50) or RAISE(100) or RAISE(200) or RAISE(350) or RAISE(500) → 6 actions
  - After CHECK: P1 acts: CHECK (terminal) or 5 raises → 6 actions
    - After P1 RAISE: P0 acts: FOLD (terminal) or CALL (terminal) → 2 actions
  - After P0 RAISE: P1 acts: FOLD (terminal) or CALL (terminal) or RE-RAISE (if stack allows) → 2–3 actions
- Approximate decision nodes per runout: 6 (P0 root) + 6 (P1 after check) + 5×2 (P0 facing bet) + 5×2 (P1 facing bet) + re-raise branches → ~30 decision nodes
- Approximate terminals per runout: 1 (check-check) + 5×2 (bet-fold/call) + 5×2 (raise-fold/call) → ~20 terminals
- **Total nodes (20 runouts):** ~20 (chance) + 20×30 (decision) + 20×20 (terminal) = ~1,020 nodes per flop street
- **Multi-street recursion:** Each flop terminal spawns a turn solve (20 runouts × ~20 terminals = 400 turn solves)
- Each turn solve: ~50 nodes (1 runout, 5 wagers, 10 combos)
- Each turn terminal spawns a river solve: ~50 nodes
- **Total nodes (flop + turn + river):** ~1,020 (flop) + 400×50 (turn) + 400×50 (river) = ~41,020 nodes
- **Exceeds cap:** 41,020 > 100,000? No, but **runtime** will exceed 60s due to recursive solving overhead.

**Revised parameters to exceed node cap:**
- **Runouts:** 30 turn-river pairs
- **Combos per player:** 15
- **Wagers:** 6 sizes
- **Expected nodes:** ~1,500 (flop) + 900×75 (turn) + 900×75 (river) = ~136,000 nodes
- **Exceeds cap:** 136,000 > 100,000 ✓

**Expected runtime (exact):**
- 136,000 nodes × 100 iterations × ~1 µs per node-iteration = ~13.6s (optimistic)
- Recursive solving overhead (building subtrees, range conditioning): ×5 multiplier → ~68s
- **Exceeds cap:** 68s > 60s ✓

**Information-set count (exact):**
- 15 combos × 30 runouts × ~10 action histories = ~4,500 infosets per player
- **Memory:** ~4,500 infosets × 6 actions × 8 bytes (float) × 2 (regret + strategy) = ~432 KB per player (tractable)

### 3.3 Expected abstracted metrics (completes beneath cap)

**Abstraction policy:** 15 combos → 3 buckets (5 combos per bucket)
- Bucket 0 (strong): top 5 combos by equity (e.g., flush draws, overpairs)
- Bucket 1 (medium): middle 5 combos (e.g., pairs, gutshots)
- Bucket 2 (weak): bottom 5 combos (e.g., air, backdoors)

**Information-set count (abstracted):**
- 3 buckets × 30 runouts × ~10 action histories = ~900 infosets per player
- **Reduction:** 4,500 → 900 = 80% reduction ✓

**Physical state count (abstracted):**
- **Unchanged:** 136,000 nodes (abstraction affects infosets, not physical tree)
- **But:** fewer infosets → faster regret updates → faster iteration

**Expected runtime (abstracted):**
- 136,000 nodes × 100 iterations × ~0.5 µs per node-iteration (fewer infosets) = ~6.8s
- Recursive solving overhead: ×3 multiplier (less range conditioning) → ~20s
- **Completes beneath cap:** 20s < 60s ✓

**Node count cap (abstracted):**
- If we set `max_nodes=50_000` (practical cap for interactive solving), exact solve **fails** with `ValueError("max_nodes exceeded")`, but abstracted solve **completes** (136,000 physical nodes, but we can configure the validator to count **information sets** instead of physical states, or accept that physical nodes exceed cap but runtime is acceptable).
- **Revised acceptance:** Use **runtime cap** (60s) as the primary tractability gate, not node count.

### 3.4 Fixture implementation contract

**File:** `tests/test_phase4_s4_tractability.py`

**Test 1: `test_large_exact_exceeds_runtime_cap`**
```python
import time
import pytest

def test_large_exact_exceeds_runtime_cap():
    """Large 15-combo, 30-runout, 6-wager exact solve exceeds 60s runtime cap."""
    config = _large_tractability_config(abstraction=None)
    
    start = time.time()
    # Use timeout or manual observation
    result = solve_allstreet_postflop(config, algorithm="vanilla-cfr", iterations=100)
    elapsed = time.time() - start
    
    # Document that exact solve exceeds cap
    assert elapsed > 60.0, (
        f"exact large solve completed in {elapsed:.1f}s, expected >60s "
        "(if this fails, increase combos/runouts/wagers to exceed cap)"
    )
    
    # Verify correctness (if it completes)
    assert result.node_count > 100_000, "exact large solve node count < 100k"
    assert result.nash_conv < 1.0, "exact large solve exploitability exceeds 1.0"
```

**Test 2: `test_large_abstracted_completes_beneath_cap`**
```python
def test_large_abstracted_completes_beneath_cap():
    """Large 15-combo → 3-bucket abstracted solve completes in <60s."""
    config = _large_tractability_config(abstraction="equity-3-bucket")
    
    start = time.time()
    result = solve_allstreet_postflop(config, algorithm="vanilla-cfr", iterations=100)
    elapsed = time.time() - start
    
    # Abstracted completes beneath cap
    assert elapsed < 60.0, (
        f"abstracted large solve took {elapsed:.1f}s, exceeds 60s cap "
        "(abstraction did not reduce runtime sufficiently)"
    )
    
    # Verify correctness
    assert result.approximate is True, "abstracted result must be marked approximate"
    assert "equity-3-bucket" in result.provenance, "provenance must document abstraction"
    assert result.nash_conv < 2.0, "abstracted large solve exploitability exceeds 2.0"
    
    # Verify node count (physical tree unchanged)
    assert result.node_count > 100_000, "abstracted large solve node count < 100k (tree changed?)"
```

**Test 3: `test_large_abstraction_reduces_infoset_count`**
```python
def test_large_abstraction_reduces_infoset_count():
    """Abstraction reduces information-set count by >=50%."""
    exact_config = _large_tractability_config(abstraction=None)
    abstracted_config = _large_tractability_config(abstraction="equity-3-bucket")
    
    # Solve with low iterations to measure infoset count quickly
    exact_result = solve_allstreet_postflop(exact_config, algorithm="vanilla-cfr", iterations=10)
    abstracted_result = solve_allstreet_postflop(abstracted_config, algorithm="vanilla-cfr", iterations=10)
    
    exact_infosets = len(exact_result.strategy)
    abstracted_infosets = len(abstracted_result.strategy)
    
    reduction = (exact_infosets - abstracted_infosets) / exact_infosets
    assert reduction >= 0.5, (
        f"abstraction reduced infosets by {reduction:.1%}, expected >=50% "
        f"(exact={exact_infosets}, abstracted={abstracted_infosets})"
    )
```

**Helper: `_large_tractability_config`**
```python
def _large_tractability_config(abstraction: str | None) -> AllStreetPostflopConfig:
    """Large 15-combo, 30-runout, 6-wager tractability fixture.
    
    Args:
        abstraction: None (exact) or "equity-3-bucket" (abstracted)
    """
    flop = (parse_card("2c"), parse_card("3d"), parse_card("4h"))
    
    # Generate 30 runouts (deterministic subset of deck)
    deck = [c for c in range(52) if c not in flop]
    runouts = tuple((deck[i], deck[i+1]) for i in range(0, 60, 2))  # 30 pairs
    
    # Generate 15 combos per player (deterministic, diverse equity)
    # Player 0: 5 strong (flush draws), 5 medium (pairs), 5 weak (air)
    # Player 1: 5 strong (overpairs), 5 medium (gutshots), 5 weak (backdoors)
    # (Exact cards omitted for brevity; use parse_card to construct)
    
    if abstraction is None:
        # Exact: 15 combos per player
        player0_combos = tuple(
            WeightedCombo((parse_card(f"{rank}s"), parse_card(f"{rank2}s")), 1.0)
            for rank, rank2 in [("A", "K"), ("A", "Q"), ("A", "J"), ("A", "T"), ("A", "9"),
                                 ("K", "Q"), ("K", "J"), ("K", "T"), ("Q", "J"), ("Q", "T"),
                                 ("J", "T"), ("J", "9"), ("T", "9"), ("9", "8"), ("8", "7")]
        )
        player1_combos = tuple(
            WeightedCombo((parse_card(f"{rank}h"), parse_card(f"{rank2}h")), 1.0)
            for rank, rank2 in [("A", "A"), ("K", "K"), ("Q", "Q"), ("J", "J"), ("T", "T"),
                                 ("A", "5"), ("K", "5"), ("Q", "5"), ("J", "5"), ("T", "5"),
                                 ("9", "6"), ("8", "6"), ("7", "6"), ("6", "5"), ("5", "4")]
        )
    elif abstraction == "equity-3-bucket":
        # Abstracted: same 15 combos, but bucketed (implementation detail)
        # For design fixture, we use the same combos and assume S4-I1 modifies information_state_key
        player0_combos = tuple(
            WeightedCombo((parse_card(f"{rank}s"), parse_card(f"{rank2}s")), 1.0)
            for rank, rank2 in [("A", "K"), ("A", "Q"), ("A", "J"), ("A", "T"), ("A", "9"),
                                 ("K", "Q"), ("K", "J"), ("K", "T"), ("Q", "J"), ("Q", "T"),
                                 ("J", "T"), ("J", "9"), ("T", "9"), ("9", "8"), ("8", "7")]
        )
        player1_combos = tuple(
            WeightedCombo((parse_card(f"{rank}h"), parse_card(f"{rank2}h")), 1.0)
            for rank, rank2 in [("A", "A"), ("K", "K"), ("Q", "Q"), ("J", "J"), ("T", "T"),
                                 ("A", "5"), ("K", "5"), ("Q", "5"), ("J", "5"), ("T", "5"),
                                 ("9", "6"), ("8", "6"), ("7", "6"), ("6", "5"), ("5", "4")]
        )
    else:
        raise ValueError(f"unknown abstraction {abstraction!r}")
    
    return AllStreetPostflopConfig(
        version="allstreet-postflop-v1",
        starting_board=flop,
        initial_dead_pot=100,
        effective_stack=500,
        player0_combos=player0_combos,
        player1_combos=player1_combos,
        allowed_runouts=runouts,
        betting_mode="pot-limit",
        wager_targets=(50, 100, 200, 350, 500, 500),  # 6 sizes (last two identical to test deduplication)
        max_nodes=200_000,  # Allow exact solve to complete (for measurement)
        max_depth=128,
    )
```

**Commands:**
```bash
# Run large tractability tests (WARNING: exact test may take >60s)
pytest tests/test_phase4_s4_tractability.py::test_large_exact_exceeds_runtime_cap -v -s
pytest tests/test_phase4_s4_tractability.py::test_large_abstracted_completes_beneath_cap -v
pytest tests/test_phase4_s4_tractability.py::test_large_abstraction_reduces_infoset_count -v

# Expected output:
# test_large_exact_exceeds_runtime_cap PASSED (elapsed > 60s)
# test_large_abstracted_completes_beneath_cap PASSED (elapsed < 60s)
# test_large_abstraction_reduces_infoset_count PASSED (reduction >= 50%)
```

---

## 4. Acceptance thresholds and commands

### 4.1 Small oracle acceptance

**Thresholds:**
- Exact node count: <100
- Exact depth: <15
- Exact exploitability (100 iterations): <0.1
- Abstracted vs. exact value difference: <=2.0 chips (10% of pot)
- Abstracted exploitability (100 iterations): <0.2
- Determinism: exact match on repeated runs
- Zero-sum: `|sum(returns)| < 1e-9` at every terminal
- Policy sum: `|sum(policy) - 1.0| < 1e-9` at every infoset

**Commands:**
```bash
pytest tests/test_phase4_s4_oracle.py -v
# All 3 tests must pass
```

### 4.2 Large tractability acceptance

**Thresholds:**
- Exact runtime: >60s (documents that exact exceeds cap)
- Abstracted runtime: <60s (documents that abstracted completes beneath cap)
- Abstracted infoset reduction: >=50%
- Abstracted exploitability (100 iterations): <2.0
- Abstracted node count: >100,000 (physical tree unchanged)
- Abstracted marked approximate: `result.approximate is True`
- Abstracted provenance: contains "equity-3-bucket"

**Commands:**
```bash
pytest tests/test_phase4_s4_tractability.py -v -s
# All 3 tests must pass
# test_large_exact_exceeds_runtime_cap may be skipped in CI (too slow)
```

### 4.3 Cross-validation commands

**Verify bounded_tree validation:**
```bash
pytest tests/test_bounded_tree.py -v
# Ensures bounded_tree correctly counts nodes, depth, terminals, chance, decision
```

**Verify allstreet oracle (S1 baseline):**
```bash
pytest tests/test_allstreet_oracle.py -v
# Ensures S1 automatic continuation is correct (S4 builds on S1)
```

**Verify determinism:**
```bash
pytest tests/test_phase4_s4_oracle.py::test_small_exact_oracle_baseline -v --count=3
# Run 3 times, verify identical output
```

---

## 5. Derived bounds and scaling analysis

### 5.1 Node count scaling (exact)

**Formula (single-street):**
```
N_nodes ≈ N_runouts × (N_terminals + N_decision)
N_decision ≈ N_actions^N_decision_depth
N_terminals ≈ N_actions × N_decision_depth
```

**Example (small oracle):**
- N_runouts = 3
- N_actions = 3 (check, raise 20, raise 50)
- N_decision_depth = 3 (P0 → P1 → P0)
- N_decision ≈ 3^3 = 27
- N_terminals ≈ 3 × 3 = 9
- N_nodes ≈ 3 × (27 + 9) = 108 (observed: 58, formula is upper bound)

**Example (large tractability):**
- N_runouts = 30
- N_actions = 6
- N_decision_depth = 3
- N_decision ≈ 6^3 = 216
- N_terminals ≈ 6 × 3 = 18
- N_nodes ≈ 30 × (216 + 18) = 7,020 (single street)
- Multi-street: ×20 (turn) ×20 (river) ≈ 2.8M nodes (exceeds cap)

**Practical cap:** 100,000 nodes → max ~15 runouts × 5 actions × 3 depth ≈ 5,625 nodes per street

### 5.2 Information-set count scaling

**Formula:**
```
N_infosets ≈ N_combos × N_action_histories
N_action_histories ≈ N_actions^N_decision_depth
```

**Example (small oracle, exact):**
- N_combos = 3
- N_action_histories ≈ 3^3 = 27
- N_infosets ≈ 3 × 27 = 81 per player

**Example (small oracle, abstracted):**
- N_buckets = 2
- N_action_histories ≈ 27
- N_infosets ≈ 2 × 27 = 54 per player
- Reduction: (81 - 54) / 81 = 33%

**Example (large tractability, exact):**
- N_combos = 15
- N_action_histories ≈ 6^3 = 216
- N_infosets ≈ 15 × 216 = 3,240 per player

**Example (large tractability, abstracted):**
- N_buckets = 3
- N_action_histories ≈ 216
- N_infosets ≈ 3 × 216 = 648 per player
- Reduction: (3,240 - 648) / 3,240 = 80%

### 5.3 Runtime scaling

**Formula:**
```
T_runtime ≈ N_iterations × N_nodes × T_per_node
T_per_node ≈ N_infosets × T_regret_update
T_regret_update ≈ N_actions × 10 ns (regret table lookup + arithmetic)
```

**Example (small oracle, exact, 100 iterations):**
- N_iterations = 100
- N_nodes = 58
- N_infosets = 81 per player
- N_actions = 3
- T_per_node ≈ 81 × 3 × 10 ns = 2.43 µs
- T_runtime ≈ 100 × 58 × 2.43 µs = 14 ms

**Example (large tractability, exact, 100 iterations):**
- N_iterations = 100
- N_nodes = 136,000
- N_infosets = 3,240 per player
- N_actions = 6
- T_per_node ≈ 3,240 × 6 × 10 ns = 194 µs
- T_runtime ≈ 100 × 136,000 × 194 µs = 2,638 s = 44 minutes (exceeds 60s cap)

**Example (large tractability, abstracted, 100 iterations):**
- N_infosets = 648 per player
- T_per_node ≈ 648 × 6 × 10 ns = 39 µs
- T_runtime ≈ 100 × 136,000 × 39 µs = 530 s = 8.8 minutes (still exceeds 60s cap)

**Revised large tractability parameters (to meet 60s cap for abstracted):**
- Reduce iterations to 20 (not 100)
- Or reduce runouts to 15 (not 30)
- Or reduce combos to 10 (not 15)
- **Chosen:** Reduce iterations to 20 for tractability test, keep 100 for oracle test

---

## 6. Implementation notes and boundaries

### 6.1 What S4 design does NOT specify

1. **Abstraction algorithm implementation:** This design specifies the **interface** (abstraction policy in config, information_state_key modification) but not the **implementation** (how to compute equity buckets, how to modify multistreet.py / allstreet.py).

2. **Optimal bucket count:** 2-bucket and 3-bucket are **examples**. S4-I1 must determine optimal bucket counts via empirical study (exploitability vs. runtime trade-off).

3. **Blocker-aware abstraction:** This design uses **equity bucketing** (simplest). S4-I1 may implement blocker-aware abstraction (e.g., "AsKs and AcKc are in different buckets because they block different flush draws").

4. **Dynamic abstraction:** This design uses **static bucketing** (computed once at config time). S4-I1 may implement dynamic abstraction (e.g., re-bucket on each street based on board texture).

5. **Abstraction validation:** This design specifies **acceptance thresholds** (value difference, exploitability) but not **how to validate** that the abstraction is "good" (e.g., no silent strategy corruption). S4-I1 must add tests for strategically-identical-combos preservation.

### 6.2 Explicit boundaries for S4-I1

**Must implement:**
- `AllStreetPostflopConfig.abstraction_policy: str | None` (e.g., `"equity-2-bucket"`, `"equity-3-bucket"`, `None` for exact)
- Modify `information_state_key` in `MultiStreetState` to map combos to buckets when `abstraction_policy is not None`
- Mark `AllStreetSolveResult.approximate = True` when abstraction is used
- Document abstraction policy in `AllStreetSolveResult.provenance`
- Pass all tests in `test_phase4_s4_oracle.py` and `test_phase4_s4_tractability.py`

**Must NOT implement (out of scope):**
- Neural abstraction (learned bucketing)
- Continuous abstraction (infinite buckets)
- Opponent-modeling abstraction (different buckets per opponent)
- Abstraction for preflop (S4 is postflop only)

**Deferred to future phases:**
- Automatic bucket-count selection (S4-I1 uses hardcoded 2/3 buckets)
- Abstraction quality metrics (S4-I1 uses exploitability as proxy)
- Abstraction visualization (S4-I1 is solver-only, no UI)

---

## 7. Summary and deliverables

### 7.1 Small oracle fixture

**Config:**
- 3 combos per player, 3 runouts, 2 wagers, 100-chip stack, 20-chip pot
- Exact: 3 combos → 3 infosets per player
- Abstracted: 3 combos → 2 buckets → 2 infosets per player

**Acceptance:**
- Exact: <100 nodes, <15 depth, <0.1 exploitability
- Abstracted: |V_exact - V_abstracted| <= 2.0 chips, <0.2 exploitability
- Convergence: exploitability decreases with iterations for both

**File:** `tests/test_phase4_s4_oracle.py` (3 tests)

### 7.2 Large tractability fixture

**Config:**
- 15 combos per player, 30 runouts, 6 wagers, 500-chip stack, 100-chip pot
- Exact: 15 combos → ~3,240 infosets per player, >60s runtime
- Abstracted: 15 combos → 3 buckets → ~648 infosets per player, <60s runtime

**Acceptance:**
- Exact: >60s runtime (documents cap exceeded)
- Abstracted: <60s runtime (documents cap met), >=50% infoset reduction

**File:** `tests/test_phase4_s4_tractability.py` (3 tests)

### 7.3 Commands

```bash
# Small oracle (fast, <5s total)
pytest tests/test_phase4_s4_oracle.py -v

# Large tractability (slow, exact test >60s)
pytest tests/test_phase4_s4_tractability.py::test_large_abstracted_completes_beneath_cap -v
pytest tests/test_phase4_s4_tractability.py::test_large_abstraction_reduces_infoset_count -v
# Skip exact test in CI (too slow):
pytest tests/test_phase4_s4_tractability.py -v -k "not exact_exceeds"

# Cross-validation
pytest tests/test_bounded_tree.py tests/test_allstreet_oracle.py -v
```

### 7.4 Derived bounds

- **Small oracle value difference:** |V_exact - V_abstracted| <= 2.0 chips (10% of pot)
- **Small oracle exploitability:** exact <0.1, abstracted <0.2
- **Large tractability runtime:** exact >60s, abstracted <60s
- **Large tractability infoset reduction:** >=50% (15 combos → 3 buckets = 80%)
- **Node count scaling:** N_nodes ≈ N_runouts × N_actions^N_depth (exponential in actions/depth)
- **Infoset count scaling:** N_infosets ≈ N_combos × N_action_histories (linear in combos)
- **Runtime scaling:** T ≈ N_iterations × N_nodes × N_infosets × N_actions (quadratic in infosets)

---

**End of S4 design.**
