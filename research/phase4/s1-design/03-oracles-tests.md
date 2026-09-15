# S1 Acceptance: Independent Oracles and Test Plan

## 1. Scope and Exclusions

This document defines **independent verification oracles** and **acceptance tests** for S1 (Phase 4 continuation-value architecture). It specifies:

- Executable tiny-game fixtures with exact expected values;
- Quantitative bounds comparing automatic versus explicit continuation;
- Zero-sum, normalized-policy, determinism, hidden-information noninterference, and convergence-vs-iterations checks;
- Exact proposed test commands and PASS criteria.

**Out of scope:** architecture design, ownership, implementation, production code, shared documentation, git operations.

---

## 2. Fixture Inventory

### 2.1 Kuhn Poker (Existing)

**Purpose:** Analytical baseline for determinism, convergence, and NashConv.

**Oracle:** Published analytical value: player 0 EV = -1/18 ≈ -0.0556.

**Independence:** Level 1 (external analytical result).

**Existing tests:**
- `tests/test_kuhn.py::test_full_tree_counts_and_known_value_constant`
- `tests/test_cfr.py::test_kuhn_cfr_is_deterministic_and_approaches_value`
- `tests/test_mccfr.py::test_kuhn_analytical_ev_and_nashconv`

**Acceptance (already passing):**
- Vanilla CFR: `|EV_0 - (-1/18)| ≤ 0.003` after 5,000 iterations; `NashConv < 0.03`.
- MCCFR: seed matrix (5 seeds × 10,000 iterations): `|EV_0 - (-1/18)| ≤ 0.010`; `NashConv < 0.10`.

---

### 2.2 Tiny Multi-Street Fixture (Existing)

**Purpose:** Bounded flop-to-river game for multi-street accounting, chance conditioning, and best-response oracles.

**Specification:** `poker_solver.phase2_fixture.tiny_multistreet_root()`

**Configuration:**
- Starting street: flop (`2c 3d 4h`)
- Player 0: `(As, 5s)` weight 1.0
- Player 1: `(Kh, Qh)` weight 1.0
- Allowed runouts: `(9s, Kc)`, `(Tc, Jd)`
- Initial pot: 2 units; effective stack: 1 unit
- Betting: pot-limit; wager targets: `(1,)`

**Tree size:** ~hundreds of nodes (bounded by 2 runout sequences × 2 turn cards × betting tree).

**Existing tests:** `tests/test_phase2_oracle.py`
- `test_fixture_chance_mass_and_conditional_runouts`
- `test_fixture_runouts_are_conditioned_on_private_blockers`
- `test_fixture_audit_and_every_terminal_zero_sum`
- `test_dynamic_best_response_matches_exhaustive_oracle`
- `test_vanilla_reference_converges_on_fixture`
- `test_mccfr_seed_matrix_value_agrees_with_vanilla`

**Acceptance (already passing):**
- Audit: all terminals zero-sum within `1e-12`.
- Dynamic BR = exhaustive BR within `1e-12` for both players, uniform and trained profiles.
- Vanilla CFR: `NashConv < 0.005` after 1,000 iterations.
- MCCFR: 5 seeds × 5,000 iterations: `|EV_0 - vanilla_EV_0| ≤ 0.01`.

---

### 2.3 Hidden-Bit Game (Existing)

**Purpose:** Information-set consistency trap — illegal per-history maximization yields +1; legal infoset-consistent BR yields 0.

**Oracle:** Exhaustive brute force.

**Independence:** Level 2 (independent algorithmic oracle).

**Existing test:** `tests/test_best_response.py::test_best_response_is_infoset_consistent_hidden_bit`

**Acceptance (already passing):**
- BR value exactly 0.0 (within `pytest.approx` default tolerance).
- NashConv exactly 0.0.

---

## 3. S1-Specific Oracles: Automatic vs. Explicit Continuation

### 3.1 Principle

S1 introduces **automatic continuation** (implicit multi-street traversal) versus **explicit continuation** (user-supplied terminal values at a depth boundary). The oracle compares:

1. **Automatic reference:** Full traversal to natural terminals (showdown/fold) using existing `tiny_multistreet_root()`.
2. **Explicit construction:** Manually truncated tree at a street boundary with continuation values derived from the automatic reference's subtree EVs.

If both solvers use identical continuation values and identical truncated structure, their strategies and root EVs must agree within numerical tolerance.

---

### 3.2 Explicit-Continuation Reference Construction

**Fixture:** `tiny_multistreet_explicit_flop_truncation`

**Construction algorithm:**

1. Solve `tiny_multistreet_root()` with vanilla CFR for 2,000 iterations → `reference_profile`.
2. Compute `reference_ev = expected_values(root, reference_profile)`.
3. Identify all flop decision nodes after private deal chance (before turn runout chance).
4. For each such node `n`:
   - Compute continuation EV for both players under `reference_profile` by evaluating the subtree rooted at `n`.
   - Store `continuation_table[n.info_key] = (ev_0, ev_1)`.
5. Construct a **truncated game state** that:
   - Matches `tiny_multistreet_root()` up to flop action close;
   - Replaces turn/river chance and showdown with immediate terminal nodes returning `continuation_table` values.
6. Solve the truncated game with vanilla CFR for 2,000 iterations → `truncated_profile`.
7. Compute `truncated_ev = expected_values(truncated_root, truncated_profile)`.

**Oracle invariant:**
```python
assert abs(truncated_ev[0] - reference_ev[0]) <= 1e-9
assert abs(truncated_ev[1] - reference_ev[1]) <= 1e-9
```

**Tolerance rationale:** Exact tree identity and deterministic CFR → numerical precision only.

**Test location:** `tests/test_s1_continuation_oracle.py::test_explicit_continuation_matches_automatic`

**Status:** To be implemented.

---

### 3.3 Checkdown-Equity Heuristic Counterexample

**Purpose:** Prove that naive equity rollout ≠ strategic continuation value.

**Fixture:** `strategic_vs_equity_divergence_game`

**Construction:**

1. Start from a simplified flop state with:
   - Player 0: strong draw (e.g., flush draw, ~35% equity).
   - Player 1: made hand (e.g., top pair, ~65% equity).
   - Remaining stack: 1 pot-sized bet.
2. **Checkdown equity:** Player 0 EV ≈ -0.30 pot (0.35 × 1 - 0.65 × 1).
3. **Strategic continuation:** Player 0 can bluff; Player 1 must fold some hands → Player 0 EV > checkdown equity.
4. Measure:
   - `strategic_ev = solve_full_tree().values()[0]`
   - `equity_ev = checkdown_equity(player0_range, player1_range, board)`
   - `delta = strategic_ev - equity_ev`

**Oracle invariant:**
```python
assert delta > 0.05  # Strategic value exceeds equity by at least 5% of pot
```

**Test location:** `tests/test_s1_continuation_oracle.py::test_checkdown_equity_underestimates_strategic_value`

**Status:** To be implemented.

---

## 4. Zero-Sum Invariants

### 4.1 Existing Coverage

**Test:** `tests/test_audit.py::test_valid_kuhn_audit_counts`

**Oracle:** `audit_game()` exhaustive traversal.

**Invariant:** Every terminal node: `|sum(returns)| ≤ 1e-10`.

**Acceptance:** Already passing for Kuhn and `tiny_multistreet_root()`.

---

### 4.2 S1 Extension: Explicit-Continuation Zero-Sum

**Test:** `tests/test_s1_continuation_oracle.py::test_explicit_continuation_zero_sum`

**Invariant:** Truncated game with explicit continuation values must satisfy:
```python
for terminal in all_terminals(truncated_root):
    assert abs(sum(terminal.returns())) <= 1e-10
```

**Rationale:** Continuation values are derived from zero-sum subtrees → truncated terminals remain zero-sum.

**Status:** To be implemented.

---

## 5. Normalized-Policy Invariants

### 5.1 Existing Coverage

**Tests:**
- `tests/test_cfr.py::test_training_can_continue_and_probabilities_normalize`
- `tests/test_mccfr.py::test_action_probabilities_normalize`

**Invariant:** For all infosets `I` and profiles `σ`:
```python
assert sum(σ[I].values()) == pytest.approx(1.0)
assert all(p >= 0 for p in σ[I].values())
```

**Acceptance:** Already passing for vanilla CFR and MCCFR.

---

### 5.2 S1 Extension: Explicit-Continuation Policy Normalization

**Test:** `tests/test_s1_continuation_oracle.py::test_truncated_policies_normalize`

**Invariant:** Truncated game strategies must satisfy normalization:
```python
truncated_profile = CFRSolver(truncated_root).train(1000)
for key, policy in truncated_profile.items():
    assert sum(policy.values()) == pytest.approx(1.0)
    assert all(p >= 0 for p in policy.values())
```

**Status:** To be implemented.

---

## 6. Determinism Gates

### 6.1 Existing Coverage

**Tests:** `tests/test_phase2_determinism.py`
- `test_vanilla_cfr_deterministic_serialization`
- `test_mccfr_same_seed_deterministic`
- `test_mccfr_different_seed_diverges`
- `test_vanilla_cfr_regret_accumulation_deterministic`
- `test_mccfr_lazy_infoset_discovery_deterministic`

**Invariant:** Vanilla CFR is byte-identical across runs; MCCFR with same seed is byte-identical.

**Acceptance:** Already passing.

---

### 6.2 S1 Extension: Explicit-Continuation Determinism

**Test:** `tests/test_s1_continuation_oracle.py::test_explicit_continuation_deterministic`

**Method:**
1. Construct `truncated_root` twice independently.
2. Solve each with vanilla CFR for 1,000 iterations.
3. Serialize both strategies to canonical JSON.
4. Compute SHA-256 hash.

**Invariant:**
```python
assert hash1 == hash2
```

**Status:** To be implemented.

---

## 7. Hidden-Information Noninterference

### 7.1 Existing Coverage

**Test:** `tests/test_best_response.py::test_best_response_is_infoset_consistent_hidden_bit`

**Oracle:** Hidden-bit game where illegal per-history maximization yields +1; legal infoset-consistent BR yields 0.

**Acceptance:** Already passing.

---

### 7.2 S1 Extension: Continuation-Value Information Leakage

**Test:** `tests/test_s1_continuation_oracle.py::test_continuation_values_respect_information_sets`

**Principle:** Continuation values at an information set must be **identical** for all histories in that set, even if those histories have different hidden opponent cards.

**Method:**
1. Construct a toy game where two histories `h1, h2` belong to the same infoset `I` but have different opponent private cards.
2. Compute continuation values for `h1` and `h2` from a reference profile.
3. Assert:
```python
assert continuation_value(h1, player) == pytest.approx(continuation_value(h2, player), abs=1e-12)
```

**Failure mode:** If continuation construction leaks opponent cards, values will differ.

**Status:** To be implemented.

---

## 8. Convergence vs. Iterations

### 8.1 Existing Coverage

**Tests:**
- `tests/test_cfr.py::test_kuhn_cfr_is_deterministic_and_approaches_value`
- `tests/test_mccfr.py::test_kuhn_analytical_ev_and_nashconv` (parametrized seed matrix)
- `tests/test_phase2_oracle.py::test_vanilla_reference_converges_on_fixture`

**Invariant:** NashConv decreases (on average) and approaches zero; EV approaches analytical/reference value.

**Acceptance:** Already passing with predeclared tolerances.

---

### 8.2 S1 Extension: Convergence Sweep Decision Rule

**Test:** `tests/test_s1_continuation_oracle.py::test_convergence_sweep_truncated_vs_automatic`

**Method:**
1. Solve `tiny_multistreet_root()` (automatic) for `[100, 500, 1000, 2000, 5000]` iterations.
2. Solve `truncated_root` (explicit continuation) for the same iteration counts.
3. For each iteration count `n`, compute:
   - `nashconv_auto[n] = nash_conv(auto_root, auto_profile[n]).nash_conv`
   - `nashconv_trunc[n] = nash_conv(trunc_root, trunc_profile[n]).nash_conv`
4. Assert:
```python
for n in iteration_counts:
    assert abs(nashconv_trunc[n] - nashconv_auto[n]) <= 0.01
```

**Rationale:** Identical continuation values → convergence rates should match within measurement noise.

**Decision rule:** If `nashconv_trunc[n] > nashconv_auto[n] + 0.01` for any `n`, the explicit-continuation construction is incorrect.

**Status:** To be implemented.

---

## 9. Proposed Test Commands

### 9.1 Fast Acceptance Suite

**Command:**
```bash
pytest -v tests/test_s1_continuation_oracle.py -m "not slow"
```

**Expected runtime:** < 5 seconds.

**Coverage:**
- Explicit continuation matches automatic (1,000 iterations).
- Zero-sum invariant.
- Policy normalization.
- Determinism.
- Information-set consistency.

---

### 9.2 Full Convergence Suite

**Command:**
```bash
pytest -v tests/test_s1_continuation_oracle.py
```

**Expected runtime:** < 30 seconds.

**Coverage:**
- All fast tests.
- Convergence sweep (5 iteration counts).
- Checkdown-equity counterexample.

---

### 9.3 Integration with Existing Suites

**Command:**
```bash
pytest -v -m "not benchmark"
```

**Expected runtime:** < 60 seconds.

**Coverage:**
- All existing Phase 2 oracles.
- All S1 continuation oracles.

---

## 10. Acceptance Criteria Summary

| Test | Oracle | Tolerance | PASS Criterion |
|------|--------|-----------|----------------|
| Explicit = Automatic EV | Reference CFR solve | `≤ 1e-9` | Absolute EV error |
| Explicit zero-sum | Exhaustive terminal walk | `≤ 1e-10` | Sum of returns |
| Policy normalization | Sum of probabilities | `≤ 1e-10` | `sum(σ[I]) - 1.0` |
| Determinism | Repeat solve + hash | Exact | SHA-256 equality |
| Information-set consistency | Hidden-card histories | `≤ 1e-12` | Continuation value equality |
| Convergence sweep | NashConv at 5 checkpoints | `≤ 0.01` | `|nashconv_trunc - nashconv_auto|` |
| Checkdown-equity divergence | Strategic solve vs. equity | `> 0.05` | `strategic_ev - equity_ev` |

---

## 11. Fixture Definitions (Pseudocode)

### 11.1 Explicit-Continuation Truncated Game

```python
def build_explicit_continuation_fixture():
    # Step 1: Solve full game
    full_root = tiny_multistreet_root()
    full_solver = CFRSolver(full_root)
    reference_profile = full_solver.train(2000)
    reference_ev = expected_values(full_root, reference_profile)
    
    # Step 2: Extract continuation values at flop close
    continuation_table = {}
    for node in all_flop_decision_nodes(full_root):
        key = node.information_state_key(node.current_player())
        ev_0, ev_1 = evaluate_subtree(node, reference_profile)
        continuation_table[key] = (ev_0, ev_1)
    
    # Step 3: Build truncated game
    truncated_root = build_truncated_game(
        config=tiny_multistreet_config(),
        truncation_point="flop_close",
        continuation_table=continuation_table,
    )
    
    return truncated_root, reference_ev, continuation_table
```

---

### 11.2 Checkdown-Equity Counterexample

```python
def build_checkdown_equity_counterexample():
    config = MultiStreetConfig(
        starting_street="flop",
        starting_board=parse_cards(("Ah", "Kh", "2c")),
        player0_combos=(WeightedCombo(parse_cards(("Qh", "Jh")), 1.0),),  # Flush draw
        player1_combos=(WeightedCombo(parse_cards(("As", "Qs")), 1.0),),  # Top pair
        allowed_runouts=(
            parse_cards(("3h", "4h")),  # Flush completes
            parse_cards(("3c", "4c")),  # Brick
        ),
        initial_dead_pot=2,
        effective_stack=2,
        betting_mode="pot-limit",
        wager_targets=(2,),
    )
    root = create_root(config)
    
    # Strategic solve
    solver = CFRSolver(root)
    strategic_profile = solver.train(5000)
    strategic_ev = expected_values(root, strategic_profile)[0]
    
    # Checkdown equity
    equity_p0 = compute_equity(
        player0_range=config.player0_combos,
        player1_range=config.player1_combos,
        board=config.starting_board,
        runouts=config.allowed_runouts,
    )
    equity_ev = (equity_p0 - 0.5) * config.initial_dead_pot
    
    return strategic_ev, equity_ev
```

---

## 12. Implementation Checklist

**To implement:**
- [ ] `tests/test_s1_continuation_oracle.py` module
- [ ] `build_explicit_continuation_fixture()` helper
- [ ] `build_truncated_game()` constructor (accepts continuation table)
- [ ] `test_explicit_continuation_matches_automatic`
- [ ] `test_explicit_continuation_zero_sum`
- [ ] `test_truncated_policies_normalize`
- [ ] `test_explicit_continuation_deterministic`
- [ ] `test_continuation_values_respect_information_sets`
- [ ] `test_convergence_sweep_truncated_vs_automatic`
- [ ] `test_checkdown_equity_underestimates_strategic_value`
- [ ] `build_checkdown_equity_counterexample()` helper
- [ ] `compute_equity()` utility (if not already present)
- [ ] Pytest markers: `@pytest.mark.slow` for convergence sweep

---

## 13. Sources

- CFR: https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- MCCFR: https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html
- Depth-limited solving: https://arxiv.org/abs/1805.11751 (Brown & Sandholm, 2018)
- OpenSpiel exploitability: https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/algorithms/exploitability.py
- Repository validation strategy: `research/validation_strategy.md`
- Repository Phase 2 accuracy fixtures: `research/phase2/accuracy-fixtures.md`
- Repository Phase 2 validation plan: `research/phase2/design-validation.md`

---

**End of S1 acceptance oracle and test plan.**
