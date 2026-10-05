# S1 Red-Team Plan: Implementation-Wave Hazards and Audit Strategy

**Date:** 2026-09-15 (UTC)  
**Scope:** Phase 4 S1 automatic all-street continuation — red-team hazards, implementation batches, and adversarial audit plan  
**Status:** Design only (no implementation, no source/test/shared-doc/git edits)

---

## 1. Executive Summary

This document identifies **S1-specific implementation hazards** for automatic flop→turn→river continuation and proposes **dependency-safe implementation batches** with **fresh non-author audits** after every batch. The focus is on **automatic all-street hazards** unique to S1:

- Leaf double-counting and continuation-value accounting
- Fold/showdown terminal classification
- Public/private chance conditioning and blocker leakage
- Information-set collisions and hidden-card leakage
- Stale cache entries and invalidation triggers
- Direct-construction invariants (zero-sum, policy normalization)
- Recursion depth and tree-size limits
- Multiway/rake conservation across recursive subtrees
- False convergence claims and iteration-budget allocation

**Out of scope:** Generic Phase 3 feature auditing, preflop/multiway/ICM/bounty features unrelated to S1, web UI, abstraction (S4), continuous sizing (S5).

---

## 2. S1-Specific Hazard Register

### 2.1 Leaf Double-Counting (CRITICAL)

**Hazard:** When a flop leaf triggers turn recursion, the turn solver enumerates turn runouts and solves each turn subtree. If the aggregation logic counts the same flop leaf multiple times (e.g., once per turn runout instead of weighted-average), the flop solver sees inflated/deflated continuation values.

**Manifestation:**
- Zero-sum violation at flop root (sum of expected values ≠ 0).
- Flop strategy diverges from explicit-continuation oracle by >1e-6.
- Exploitability increases instead of decreasing with iterations.

**Attack vector:**
```python
# WRONG: summing turn values without weighting by runout probability
aggregated = sum(solve_turn(runout).values[0] for runout in turn_runouts)
# CORRECT: weighted average
aggregated = sum(prob * solve_turn(runout).values[0] for runout, prob in turn_runouts_with_probs)
```

**Detection:**
- Unit test: `test_flop_continuation_aggregation_is_weighted_average`
- Oracle: explicit-continuation fixture (03-oracles-tests.md §3.2)
- Audit: inspect aggregation loop in `_build_next_street_root` or equivalent helper

**Mitigation:**
- Aggregation must use `chance_outcomes()` probabilities (multistreet.py lines 155–192)
- Assert `sum(probabilities) == 1.0` within 1e-12 before aggregation
- Log aggregated value and per-runout contributions in debug mode

---

### 2.2 Fold vs. Showdown Terminal Classification (HIGH)

**Hazard:** River terminals are either fold (one player wins pot) or showdown (evaluator ranks hands). If the recursion logic misclassifies a terminal (e.g., treats a fold as showdown or vice versa), payoffs are wrong.

**Manifestation:**
- Fold awards pot to wrong player.
- Showdown uses stale/wrong board cards (e.g., flop board instead of river board).
- Zero-sum violation at river terminals.

**Attack vector:**
```python
# WRONG: always treating river CALL as showdown, ignoring all-in refund
if action.kind == "CALL" and street == "river":
    return showdown_terminal(state)  # Misses uncalled-excess refund
```

**Detection:**
- Unit test: `test_river_fold_awards_pot_to_correct_player`
- Unit test: `test_river_showdown_uses_full_five_card_board`
- Audit: inspect `child()` logic in multistreet.py lines 283–432 (fold/call/check branches)

**Mitigation:**
- Reuse existing `MultiStreetState.child()` logic (lines 283–432) — already handles fold/showdown/refund
- Do NOT reimplement terminal classification in S1 code
- Assert `terminal_reason` is set and matches expected pattern (`fold-{player}` or `showdown-{street}`)

---

### 2.3 Public/Private Chance Conditioning (CRITICAL)

**Hazard:** When building a turn subtree from a flop leaf, the turn root must condition on:
1. **Public chance:** the turn card (from `allowed_runouts`)
2. **Private chance:** the dealt hole cards (from flop's `private_deal`)
3. **Blockers:** turn runouts must exclude cards in `private_deal` and `board`

If the turn root uses the wrong `private_deal` (e.g., flop's deal instead of conditioned deal) or allows blocked runouts, information leaks.

**Manifestation:**
- Turn subtree includes impossible runouts (e.g., turn card = player's hole card).
- Information-set keys collide (two histories with different opponent cards map to same key).
- Hidden-information noninterference test fails (03-oracles-tests.md §7.2).

**Attack vector:**
```python
# WRONG: reusing flop's private_deal without checking blockers
turn_root = MultiStreetState(
    private_deal=flop_state.private_deal,  # Correct
    board=flop_state.board + (turn_card,),  # Correct
    allowed_runouts=config.allowed_runouts,  # WRONG: not filtered for blockers
)
```

**Detection:**
- Unit test: `test_turn_runouts_exclude_private_deal_blockers`
- Unit test: `test_continuation_values_respect_information_sets` (03-oracles-tests.md §7.2)
- Audit: inspect `_build_next_street_root` blocker filtering

**Mitigation:**
- Use `MultiStreetState.chance_outcomes()` (lines 155–192) — already filters blockers
- Assert `len(legal_runouts) > 0` before recursion
- Log blocked runouts in debug mode

---

### 2.4 Information-Set Collisions (CRITICAL)

**Hazard:** `information_state_key()` (multistreet.py lines 434–451) must produce **identical keys** for histories in the same information set and **distinct keys** for histories in different sets. If the key omits a public signal (e.g., pot size, committed amounts, street) or includes a private signal (e.g., opponent's cards), collisions or leaks occur.

**Manifestation:**
- CFR merges strategies for distinct game states → incorrect equilibrium.
- Best-response exploitability is artificially low (BR assumes illegal information).
- Hidden-bit game test fails (03-oracles-tests.md §2.3).

**Attack vector:**
```python
# WRONG: omitting pot from key
return (player, own_cards, board, public_history)  # Two states with different pots collide
```

**Detection:**
- Unit test: `test_infoset_key_includes_all_public_signals`
- Unit test: `test_infoset_key_excludes_opponent_private_cards`
- Audit: inspect `information_state_key()` implementation (multistreet.py lines 434–451)

**Mitigation:**
- Reuse existing `MultiStreetState.information_state_key()` (lines 434–451) — already correct
- Do NOT reimplement key construction in S1 code
- Assert key is hashable and deterministic (same state → same key)

---

### 2.5 Stale Cache Entries (HIGH)

**Hazard:** The subgame cache (04-bounds-performance.md §4) keys on `(board, pot, committed, remaining, combos_hash, runouts_hash, algorithm, iterations, seed)`. If any of these fields mutate between cache write and read, the cached strategy is stale.

**Manifestation:**
- Determinism test fails (same config → different output across runs).
- Cached strategy has wrong action set (e.g., cached turn strategy includes a bet size not in current `wager_targets`).
- Zero-sum violation (cached values don't match current pot/stacks).

**Attack vector:**
```python
# WRONG: mutating config after cache key construction
cache_key = build_cache_key(state, config)
config.wager_targets = (1, 2, 3)  # Mutation!
cached = cache.get(cache_key)  # Returns stale strategy with old wager_targets
```

**Detection:**
- Unit test: `test_cache_invalidates_on_config_mutation`
- Unit test: `test_cached_strategy_action_set_matches_current_config`
- Audit: inspect cache key construction and config immutability

**Mitigation:**
- `MultiStreetConfig` is `@dataclass(frozen=True)` (multistreet.py line 18) — immutable by construction
- Cache key must include `wager_targets` tuple (04-bounds-performance.md §4.1)
- Assert `config` is frozen before caching
- Validate cached strategy's action set matches `state.legal_actions()` after cache hit

---

### 2.6 Zero-Sum Violation in Recursive Subtrees (CRITICAL)

**Hazard:** Every terminal (fold/showdown) must satisfy `sum(returns()) == 0` (or `-rake` if rake is enabled). If a recursive subtree violates zero-sum, the violation propagates to the parent tree.

**Manifestation:**
- `sum(expected_values(flop_root, strategy)) != 0` (within 1e-10).
- Audit traversal detects non-zero-sum terminal.
- Exploitability calculation fails (assumes zero-sum).

**Attack vector:**
```python
# WRONG: awarding pot without subtracting contributions
award = (pot, 0)  # Player 0 wins pot
return (award[0], award[1])  # WRONG: ignores total_contributed
```

**Detection:**
- Unit test: `test_all_terminals_zero_sum` (existing: test_audit.py)
- Unit test: `test_recursive_subtree_terminals_zero_sum` (new)
- Audit: exhaustive terminal traversal with `audit_game()` (audit.py)

**Mitigation:**
- Reuse existing `MultiStreetState.returns()` (lines 453–477) — already correct
- Do NOT reimplement payoff calculation in S1 code
- Assert `abs(sum(returns())) <= 1e-10` at every terminal
- Log non-zero-sum terminals in debug mode

---

### 2.7 Policy Normalization in Recursive Subtrees (MEDIUM)

**Hazard:** CFR's regret-matching (cfr.py lines 25–31) produces policies that sum to 1.0. If a recursive subtree's solver returns a non-normalized policy, the parent solver's expected-value calculation is wrong.

**Manifestation:**
- `sum(strategy[infoset].values()) != 1.0` (within 1e-9).
- Expected values are scaled incorrectly.
- Convergence stalls (non-normalized policies break regret updates).

**Attack vector:**
```python
# WRONG: returning current strategy instead of average strategy
return solver.current_strategy()  # May not normalize if regrets are all negative
```

**Detection:**
- Unit test: `test_recursive_subtree_policies_normalize` (03-oracles-tests.md §5.2)
- Audit: inspect `train()` return value (must be `average_strategy()`, not `current_strategy()`)

**Mitigation:**
- Always return `solver.average_strategy()` from recursive solves (cfr.py line 119)
- Assert `sum(policy.values()) == pytest.approx(1.0)` for every infoset
- Log non-normalized policies in debug mode

---

### 2.8 Recursion Depth and Tree-Size Limits (HIGH)

**Hazard:** Recursive solving can exceed Python's recursion limit (default ~1000) or the configured `max_nodes`/`max_depth` (engine.py lines 19–20, 04-bounds-performance.md §3). If limits are not enforced, the solver crashes or hangs.

**Manifestation:**
- `RecursionError: maximum recursion depth exceeded`.
- `ResourceExceededError: node count exceeded` (04-bounds-performance.md §6.1).
- Solver hangs on large trees (no progress for >5 minutes).

**Attack vector:**
```python
# WRONG: no depth tracking in recursive solve
def solve_street(state):
    if state.acting_player == TERMINAL:
        return state.returns()
    # ... recurse without depth check
    return solve_street(state.child(action))  # Unbounded recursion
```

**Detection:**
- Unit test: `test_recursion_depth_limit_enforced`
- Unit test: `test_node_count_limit_enforced`
- Audit: inspect depth/node tracking in recursive solve loop

**Mitigation:**
- Pass `depth` parameter to recursive solve (04-bounds-performance.md §5.1)
- Assert `depth <= max_depth` before recursion
- Assert `nodes_seen <= max_nodes` before recursion
- Raise `DepthLimitExceeded` or `NodeLimitExceeded` (04-bounds-performance.md §6.1)

---

### 2.9 Multiway/Rake Conservation (MEDIUM)

**Hazard:** If rake is enabled (`game_structure.py` lines 60–71), terminals must satisfy `sum(returns()) == -rake`. If a recursive subtree ignores rake or applies it multiple times, conservation fails.

**Manifestation:**
- `sum(expected_values(root, strategy)) != -rake` (within 1e-10).
- Multiway (3+ players) terminals don't sum to `-rake`.

**Attack vector:**
```python
# WRONG: applying rake at every street instead of once at showdown
rake = calculate_rake(pot)
river_values = solve_river(state)
return (river_values[0] - rake, river_values[1])  # WRONG: rake already applied in river
```

**Detection:**
- Unit test: `test_multiway_recursive_subtree_rake_conservation`
- Audit: inspect rake application in `returns()` (multistreet.py lines 453–477)

**Mitigation:**
- Rake is applied **once** at showdown terminals (multistreet.py lines 453–477)
- Do NOT apply rake in aggregation logic
- Assert `sum(returns()) == -rake` at every terminal

---

### 2.10 False Convergence Claims (MEDIUM)

**Hazard:** S1 uses fixed iteration budgets (`recursion_iterations`), not adaptive convergence thresholds. If the implementation claims "converged" without measuring exploitability, the claim is false.

**Manifestation:**
- Documentation/logs claim "converged to Nash equilibrium".
- User expects epsilon-Nash but gets fixed-iteration approximation.
- Exploitability is high despite "converged" label.

**Attack vector:**
```python
# WRONG: claiming convergence without exploitability measurement
strategy = solver.train(iterations)
return EngineResult(provenance="converged to Nash equilibrium")  # FALSE
```

**Detection:**
- Audit: inspect `EngineResult.provenance` string (engine.py line 37)
- Audit: search codebase for "converged", "Nash", "equilibrium" claims

**Mitigation:**
- Use provenance string: `"complete configured finite-tree CFR"` (engine.py line 76)
- Do NOT claim "converged" or "Nash" without exploitability measurement
- Document iteration budget as a hyperparameter, not a convergence guarantee

---

## 3. Implementation Batches (Dependency-Safe)

### Batch 1: Core Recursive Solve (No Caching)

**Scope:**
- Add `Continuation(kind="auto-recursive", next_street_config, recursion_iterations)` to `preflop.py` / `multiway.py`.
- Implement `_build_next_street_root(current_state, next_config)` helper.
- Implement `_select_solver(root)` helper (CFRSolver vs. NPlayerCFRSolver).
- Implement `_expected_values(root, strategy)` helper.
- Modify `PreflopState.child()` or `ThreePlayerPostflopState._settle()` to call recursive solver.
- **No caching** (cache added in Batch 2).

**Files modified:**
- `src/poker_solver/preflop.py` (if preflop continuation)
- `src/poker_solver/multiway.py` (if postflop continuation)
- `src/poker_solver/multistreet.py` (if new helpers)

**Tests (new):**
- `tests/test_s1_core.py::test_auto_recursive_continuation_no_cache`
- `tests/test_s1_core.py::test_flop_to_turn_recursion_builds_correct_root`
- `tests/test_s1_core.py::test_turn_to_river_recursion_builds_correct_root`
- `tests/test_s1_core.py::test_recursive_solve_matches_explicit_continuation` (oracle from 03-oracles-tests.md §3.2)

**Acceptance:**
- All new tests pass.
- Existing 398 tests remain green.
- Zero-sum holds at all terminals (audit traversal).
- Policies normalize (sum to 1.0 within 1e-9).
- Determinism: same config → same output (vanilla CFR).

**Audit (fresh non-author):**
- Inspect `_build_next_street_root` for blocker filtering (Hazard 2.3).
- Inspect aggregation loop for weighted-average (Hazard 2.1).
- Inspect terminal classification (fold vs. showdown, Hazard 2.2).
- Inspect `information_state_key()` usage (Hazard 2.4).
- Run `audit_game()` on a tiny recursive fixture.

---

### Batch 2: Subgame Caching

**Scope:**
- Implement `S1SubgameCache` (LRU, 1000 entries, 04-bounds-performance.md §4.3).
- Implement `build_cache_key()` (SHA256 combo/runout hashes, 04-bounds-performance.md §4.1).
- Integrate cache into recursive solve loop (check before solve, store after solve).
- Add cache hit/miss logging (debug mode).

**Files modified:**
- `src/poker_solver/s1_cache.py` (new module)
- `src/poker_solver/multistreet.py` (or wherever recursive solve lives)

**Tests (new):**
- `tests/test_s1_cache.py::test_cache_hit_returns_identical_strategy`
- `tests/test_s1_cache.py::test_cache_miss_solves_and_stores`
- `tests/test_s1_cache.py::test_cache_invalidates_on_config_mutation` (Hazard 2.5)
- `tests/test_s1_cache.py::test_cache_key_collision_resistance` (SHA256)
- `tests/test_s1_cache.py::test_cache_lru_eviction`

**Acceptance:**
- Cache hit rate >80% on repeated subgames (04-bounds-performance.md §9.1).
- Determinism preserved (cached vs. uncached produce identical output).
- All Batch 1 tests still pass.

**Audit (fresh non-author):**
- Inspect cache key construction (includes all mutation-sensitive fields, Hazard 2.5).
- Inspect cache validation after hit (action set matches current config).
- Inspect LRU eviction logic (no memory leak).
- Run determinism test with cache enabled/disabled.

---

### Batch 3: Resource Limits and Error Handling

**Scope:**
- Implement pre-solve validation (04-bounds-performance.md §3.2).
- Implement runtime depth/node tracking (04-bounds-performance.md §3.3).
- Define `S1ResourceError` hierarchy (04-bounds-performance.md §6.1).
- Raise `ConfigurationRejected`, `NodeLimitExceeded`, `DepthLimitExceeded` with diagnostic metadata.

**Files modified:**
- `src/poker_solver/s1_limits.py` (new module)
- `src/poker_solver/multistreet.py` (or wherever recursive solve lives)

**Tests (new):**
- `tests/test_s1_limits.py::test_pre_solve_rejects_explosion_case` (Hazard 2.8)
- `tests/test_s1_limits.py::test_runtime_node_limit_enforced`
- `tests/test_s1_limits.py::test_runtime_depth_limit_enforced`
- `tests/test_s1_limits.py::test_error_includes_diagnostic_metadata`

**Acceptance:**
- Boundary game (100 combos, 20 runouts, 5 wagers) completes without error (04-bounds-performance.md §9.1).
- Rejection game (200 combos, 50 runouts, 10 wagers) raises `ConfigurationRejected` before tree construction.
- All Batch 1+2 tests still pass.

**Audit (fresh non-author):**
- Inspect pre-solve validation formula (matches 04-bounds-performance.md §3.2).
- Inspect depth/node tracking (incremented correctly, Hazard 2.8).
- Inspect error messages (include counts and mitigation suggestions).
- Run boundary+1 test (should fail closed).

---

### Batch 4: Integration Tests and Oracles

**Scope:**
- Implement all tests from 03-oracles-tests.md:
  - Explicit-continuation oracle (§3.2)
  - Checkdown-equity counterexample (§3.3)
  - Zero-sum invariant (§4.2)
  - Policy normalization (§5.2)
  - Determinism (§6.2)
  - Information-set consistency (§7.2)
  - Convergence sweep (§8.2)
- Add `tests/test_s1_integration.py` with end-to-end flop→turn→river solve.

**Files modified:**
- `tests/test_s1_continuation_oracle.py` (new module)
- `tests/test_s1_integration.py` (new module)

**Tests (new):**
- All tests from 03-oracles-tests.md §9 (checklist in §12)

**Acceptance:**
- All oracle tests pass (tolerances from 03-oracles-tests.md §10).
- Explicit-continuation oracle agrees within 1e-9.
- Convergence sweep: `|nashconv_trunc - nashconv_auto| <= 0.01`.
- All Batch 1+2+3 tests still pass.

**Audit (fresh non-author):**
- Inspect oracle construction (explicit-continuation fixture, 03-oracles-tests.md §3.2).
- Inspect convergence sweep (5 iteration checkpoints, 03-oracles-tests.md §8.2).
- Run hidden-information noninterference test (Hazard 2.4).
- Run checkdown-equity counterexample (strategic > equity by >0.05).

---

## 4. Adversarial Audit Protocol

### 4.1 Audit Timing

**After every batch:**
1. Implementer(s) submit PR with batch code + tests.
2. **Fresh auditor(s)** (different from implementers) assigned.
3. Auditor(s) review code, run tests, run audit checklist (§4.2).
4. Auditor(s) report findings (PASS / FAIL / CONDITIONAL).
5. If FAIL: implementer(s) fix, auditor(s) re-review.
6. If PASS: batch accepted, next batch starts.

**Auditor pool:**
- Rotate auditors across batches (no auditor reviews their own implementation).
- Max 6 concurrent subagents (PHASE4_MISSION.md line 5).
- Auditor assignment: parent orchestrator (gpt-5.6-sol).

---

### 4.2 Audit Checklist (Per Batch)

**Code review:**
- [ ] No hardcoded iteration counts (use `recursion_iterations` from config).
- [ ] No hardcoded combo/runout iteration (use `chance_outcomes()` protocol).
- [ ] No reimplemented `information_state_key()` (reuse existing).
- [ ] No reimplemented `returns()` (reuse existing).
- [ ] No reimplemented terminal classification (reuse `child()` logic).
- [ ] Aggregation uses weighted average (Hazard 2.1).
- [ ] Blocker filtering uses `chance_outcomes()` (Hazard 2.3).
- [ ] Cache key includes all mutation-sensitive fields (Hazard 2.5).
- [ ] Depth/node tracking incremented correctly (Hazard 2.8).
- [ ] No "converged" or "Nash" claims without exploitability (Hazard 2.10).

**Test execution:**
- [ ] All new tests pass (pytest exit code 0).
- [ ] All existing 398 tests pass (no regressions).
- [ ] Determinism test: 10 consecutive runs produce identical output.
- [ ] Zero-sum test: `audit_game()` on recursive fixture, all terminals within 1e-10.
- [ ] Policy normalization: all infosets sum to 1.0 within 1e-9.

**Oracle agreement:**
- [ ] Explicit-continuation oracle (if Batch 4): within 1e-9.
- [ ] Convergence sweep (if Batch 4): within 0.01.
- [ ] Checkdown-equity counterexample (if Batch 4): strategic > equity by >0.05.

**Performance:**
- [ ] Tiny game (<1 sec, Batch 1+).
- [ ] Small game (<30 sec, Batch 2+).
- [ ] Boundary game (<5 min, Batch 3+).
- [ ] Rejection game (raises error before tree construction, Batch 3+).

**Documentation:**
- [ ] Docstrings for new functions (Google style).
- [ ] Type hints for all parameters and returns.
- [ ] No invented claims (e.g., "optimal", "converged", "Nash" without proof).

---

### 4.3 Audit Report Template

```markdown
# S1 Batch {N} Audit Report

**Auditor:** {name}  
**Date:** {ISO-8601 UTC}  
**Batch:** {1|2|3|4}  
**Verdict:** {PASS|FAIL|CONDITIONAL}

## Code Review Findings

- [ ] Checklist item 1: {PASS|FAIL|N/A} — {notes}
- [ ] Checklist item 2: {PASS|FAIL|N/A} — {notes}
- ...

## Test Execution Results

- New tests: {pass_count}/{total_count} passed
- Existing tests: {398|other} passed
- Determinism: {PASS|FAIL} — {notes}
- Zero-sum: {PASS|FAIL} — {notes}
- Policy normalization: {PASS|FAIL} — {notes}

## Oracle Agreement (Batch 4 only)

- Explicit-continuation: {PASS|FAIL} — error {value}
- Convergence sweep: {PASS|FAIL} — max delta {value}
- Checkdown-equity: {PASS|FAIL} — strategic - equity = {value}

## Performance

- Tiny game: {time} sec
- Small game: {time} sec
- Boundary game: {time} sec (if applicable)
- Rejection game: {PASS|FAIL} (if applicable)

## Issues Found

1. {Issue description, hazard reference, severity}
2. ...

## Recommendation

{PASS: accept batch and proceed to next | FAIL: reject, implementer must fix issues | CONDITIONAL: minor issues, accept with documented caveats}
```

---

## 5. Hazard-to-Batch Mapping

| Hazard | Batch | Detection | Mitigation |
|--------|-------|-----------|------------|
| 2.1 Leaf double-counting | 1 | Oracle test, audit aggregation loop | Weighted average, assert sum(probs)==1.0 |
| 2.2 Fold/showdown classification | 1 | Unit test, audit `child()` usage | Reuse existing logic, assert `terminal_reason` |
| 2.3 Public/private chance | 1 | Unit test, audit blocker filtering | Use `chance_outcomes()`, assert len>0 |
| 2.4 Infoset collisions | 1 | Hidden-bit test, audit key construction | Reuse existing `information_state_key()` |
| 2.5 Stale cache | 2 | Unit test, audit key fields | Frozen config, validate action set after hit |
| 2.6 Zero-sum violation | 1 | Audit traversal, unit test | Reuse existing `returns()`, assert sum==0 |
| 2.7 Policy normalization | 1 | Unit test, audit `train()` return | Return `average_strategy()`, assert sum==1.0 |
| 2.8 Recursion/tree limits | 3 | Unit test, audit depth/node tracking | Pass depth param, assert limits, raise error |
| 2.9 Multiway/rake | 1 | Unit test, audit rake application | Apply once at showdown, assert sum==-rake |
| 2.10 False convergence | 4 | Audit provenance string | Use "complete finite-tree CFR", no "Nash" |

---

## 6. Acceptance Criteria (Final Gate)

**Before merging S1 to main:**

- [ ] All 4 batches accepted by auditors.
- [ ] All tests from 03-oracles-tests.md pass (checklist in §12).
- [ ] All hazards from §2 mitigated (evidence in audit reports).
- [ ] Existing 398 tests remain green.
- [ ] Performance gates met (04-bounds-performance.md §9).
- [ ] Determinism verified (10 consecutive runs, vanilla CFR).
- [ ] Zero-sum verified (audit traversal on 3 fixtures: tiny, small, boundary).
- [ ] Policy normalization verified (all infosets, 3 fixtures).
- [ ] Explicit-continuation oracle within 1e-9 (03-oracles-tests.md §3.2).
- [ ] Convergence sweep within 0.01 (03-oracles-tests.md §8.2).
- [ ] Checkdown-equity counterexample: strategic > equity by >0.05 (03-oracles-tests.md §3.3).
- [ ] No "converged" or "Nash" claims without exploitability measurement.
- [ ] Documentation updated (README.md, docs/PHASE4.md).

---

## 7. Out-of-Scope (Not S1 Red-Team)

**Do NOT audit in S1 red-team:**
- Preflop tree builder (S3)
- Multiway 4–9 players (S2)
- Automatic abstraction (S4)
- Continuous sizing (S5)
- ICM/bounty multi-street (S6)
- Web UI (S7)
- Phase 3 features (already audited in Phase 3)
- Generic CFR correctness (already audited in Phase 1/2)

**Rationale:** S1 red-team focuses on **automatic all-street hazards** unique to recursive continuation. Generic feature auditing is out of scope.

---

## 8. References

1. **S1 design context:**
   - `research/phase4/s1-design/01-algorithm.md` (recursive continuation design)
   - `research/phase4/s1-design/03-oracles-tests.md` (acceptance oracles)
   - `research/phase4/s1-design/04-bounds-performance.md` (cache, limits, determinism)

2. **Repository evidence:**
   - `src/poker_solver/multistreet.py` (lines 1–495): MultiStreetState, chance_outcomes, child, information_state_key, returns
   - `src/poker_solver/cfr.py` (lines 1–162): CFRSolver, regret_matching, expected_values
   - `src/poker_solver/engine.py` (lines 1–139): EngineConfig, solve_engine, checkdown-equity
   - `src/poker_solver/nplayer.py` (lines 1–300): NPlayerCFRSolver, collect_nplayer_infosets
   - `tests/test_multistreet.py`, `tests/test_multiway_phase3.py` (existing multistreet/multiway tests)

3. **Mission constraints:**
   - `PHASE4_MISSION.md` (lines 9–12): S1 acceptance criteria
   - `PHASE4_MISSION.md` (lines 48–56): Hard rules (adversarial cross-check, untrusted proposals, goal-check gate)

---

## 9. Heartbeat Log

**Batch start heartbeats:**
- Batch 1 start: append `2026-09-15T{HH:MM:SS}Z batch-1-start` to `/home/genomix-node/poker-solver/.hb/p4-s1-design-redteam`
- Batch 2 start: append `2026-09-15T{HH:MM:SS}Z batch-2-start`
- Batch 3 start: append `2026-09-15T{HH:MM:SS}Z batch-3-start`
- Batch 4 start: append `2026-09-15T{HH:MM:SS}Z batch-4-start`

**Audit complete heartbeats:**
- Batch 1 audit: append `2026-09-15T{HH:MM:SS}Z batch-1-audit-{PASS|FAIL}`
- Batch 2 audit: append `2026-09-15T{HH:MM:SS}Z batch-2-audit-{PASS|FAIL}`
- Batch 3 audit: append `2026-09-15T{HH:MM:SS}Z batch-3-audit-{PASS|FAIL}`
- Batch 4 audit: append `2026-09-15T{HH:MM:SS}Z batch-4-audit-{PASS|FAIL}`

---

**End of S1 red-team plan.**
