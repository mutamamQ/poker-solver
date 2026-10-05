# W5 repair — C11 / 3-max NashConv / C15 plus audit F3, F4, F6, F7

Branch `feat/practice-mode`, base HEAD `5a3e61f`. Nothing is committed.
Owned files changed:
- `src/poker_solver/practice/adapter.py`
- `src/poker_solver/practice/catalog.py`
- new `src/poker_solver/practice/nplayer_metrics.py`
- `tests/test_practice_families.py`
- new `tests/test_practice_w5_repairs.py`

`models.py` and `evaluate.py` are unchanged.

I also made a one-assertion F4 update in `tests/test_practice_adapter.py` (`check_solved`). It is required because the
`optimal_action` definition changed.

## 1. C11: preflop-3max-open under-solved (was 7.18 % of pot)

**Root cause.** The default was 100 iterations. The `nplayer.NPlayerCFRSolver` path was too slow to afford more within 20 s:
about 5.5 s per 100 iterations under load.

**Fix: a faster trainer that gives identical results, plus a larger budget.** The new trainer is
`practice/nplayer_metrics.py`, in three stages:

1. **`FlatTree`** compiles the real solver tree (behind `CachedState`) once into index arrays. Returns, chance probabilities,
   action order and infoset keys are copied verbatim.
2. **`FlatNPlayerCFR`** reproduces `NPlayerCFRSolver` exactly:
   - same regret matching;
   - same counterfactual weights;
   - same float operation order;
   - one walk returns the value vector for all players, instead of one walk per player.
3. For trees of the form "root chance over private deals, identical betting shape per deal", it walks the **public tree once
   with all 27 deals as vectors**:
   - elementwise work runs through `map(operator.mul/add/sub)`;
   - per-infoset accumulation uses `functools.reduce(add)` in deal order, which is the reference's DFS order;
   - it checks that each infoset lives at exactly one public node; if not, it falls back to the generic walk.
   - The one deviation, skipping the int `0 +` start of `sum()`, is value-preserving: `0 + x == x`.

- **Equivalence.** The profiles are `==` (exact float equality) to `NPlayerCFRSolver.train` on all 20 preflop catalog spots
  (HU and 3-max, 40 iterations, chunked 15+25). Tests cover 3-max spots 0 and 5, HU spot 0, and 3-player Kuhn through
  both paths.
- **Speed.** About 0.15 ms per iteration versus about 55 ms per iteration for the old path, roughly 30× including the
  per-player walks.
  - Cold-solve breakdown at 5000 iterations, load ≈ 3.6: equity table 0.5 s, compile 1.25 s, train 8.9 s,
    NashConv 0.02 s, evaluation 0.02 s.
- **Default budget.** `FAMILY_DEFAULT_SOLVE["preflop-3max-open"] = SolveParams(iterations=5000)`. Only new-family
  `params_hash` values change.
  - The 36 legacy spot_ids and params_hashes are byte-identical. sha256 of the ids is `7b5b7100…`, of the hashes `5d6ec1eb…`.
    This was checked against a HEAD worktree and is asserted in a test.
  - All 72 spot_ids are unchanged (sha256 `3d4cc288…` at both HEAD and now).
- **Why 5000.** Spot `ce0eddffc9af` converges slowest: 1.05 % at 3000 iterations, 0.994 % at 4000, 0.861 % at 5000.
  4000 iterations is too close to the 1 % line.

## 2. Real 3-max exploitability (was `nash_conv=None`)

- `nplayer_metrics.nash_conv_nplayer(tree, profile)` computes NashConv = Σ_i (BR_i − u_i):
  - the best response is exact and infoset-consistent (opponent × chance reach aggregated per infoset, one action per
    infoset, memoised);
  - it uses the same definition as the benchmark oracle `games.nash_conv_n`.
- For 3-max spots the adapter now stores this value in `SolveProvenance.nash_conv` as a finite float. The JSON shape is
  unchanged.
- **Agreement with the oracle.** The difference is 0.0 on 3-max spots 0 and 5 (catalog order), and ≤ 1e-12 on
  3-player Kuhn. That is tested.
- **R1.** The metric is recomputed at runtime and falls as iterations increase (60 → 240, tested).
- **Side effect on C6.** The benchmark's C6 now also compares the 3-max practice spot, because the provenance value is no
  longer None.

## 3. C15 / audit F5: pseudo-raise facing an all-in

- **Defect.** `multistreet` (and `allstreet`, which builds on it) lists `RAISE(t)` when `t` equals the call target facing
  an all-in.
- **Fix, presentation layer only.** `adapter.pseudo_raise_aliases` detects such raises and `merge_pseudo_raises` folds
  their probability into the matching `CALL`.
  - This applies to `legal_actions`, `strategy`, `action_values` and every `range_strategy` row.
  - The solver tree, the profile and NashConv are untouched.
  - Fail-closed: the merge is refused if Q(pseudo-raise) differs from Q(call) by more than 1e-9 relative.
- **Test** (custom turn spot facing a stack-sized shove):
  - the raw tree still offers `RAISE(200)`;
  - the user is offered only `(FOLD, CALL 200)`;
  - CALL's Q and FOLD's Q equal the raw solve bit for bit;
  - merged probability = raw call + raw pseudo-raise;
  - NashConv equals the solver's own;
  - submitting `RAISE 200` is rejected.
- A second test confirms that no catalog flop or turn spot exposes a pseudo-raise.
- The underlying `multistreet` tree defect remains. It is outside my files, so the benchmark's C15 will still grade
  PARTIAL on its structural check.

## 4. Audit findings F3, F4, F6, F7

- **F3 (Q-value tests).** `test_hero_q_values_match_independent_recompute` covers preflop-hu-open, flop-cbet and
  turn-barrel, 2 spots each. For each spot it:
  - rebuilds the game with the benchmark-owned `Memo` and trains the repo solver;
  - computes Q with `games.independent_action_values` (not `practice.evaluate`, not `CachedState`);
  - requires |ΔQ| ≤ 1e-9, |Δσ| ≤ 1e-12, a non-degenerate Q spread, and consistency of `optimal_action`.
  - **Mutant check.** I applied the audit's fake-Q mutant (0 for the strategy argmax, −1 otherwise) to a copy of `src`.
    All 6 parametrisations then fail (`6 failed, 2 passed` in the selected run).
- **F4 (`optimal_action`).** `adapter.optimal_action` returns the highest-Q action among actions the strategy plays
  (probability > 0). Ties go to the higher probability, then legal order.
  - At equilibrium this is still a strategy action, and it is never an action the solver does not play.
  - The audit's example (σ argmax CALL, Q argmax FOLD) now yields FOLD.
  - `test_practice_adapter.check_solved` and `test_practice_families._check_solved` now assert the new rule.
- **F6 (MCCFR budget).** MCCFR allstreet training goes through the same chunked `_train_chunked` loop as CFR
  (25-iteration chunks, budget checked between chunks).
  - Chunking leaves the result unchanged: MCCFR keeps its RNG and regrets across chunks, and the test checks equality
    with a single 60-iteration block.
  - With `timeout_s=1`, 20 000 iterations raise `ValueError(...budget...)` in under 8 s; before, it took about 10 s at
    `timeout_s=2`.
- **F7 (single flight).** `SolverAdapter.solve` keeps a per-`params_hash` in-flight entry: a lock, a reference count and the
  leader's result.
  - Concurrent cold requests wait on the lock; followers return the cached or leader result.
  - If the leader fails, the next waiter solves. The entry is removed when the last waiter leaves.
  - Test: 4 concurrent threads give `solve_count == 1` and the identical object.
  - Side fix (also audit F9): if the cache does not retain the entry, the adapter returns the solve instead of raising
    `KeyError`.

## 5. Measurements (family defaults, cold `SolverAdapter(cache={})`, this 2-vCPU host)

Exploitability = 100 · (NashConv / n) / pot, the benchmark's C11 definition.

| family | iterations | cold s | load | exploitability % pot |
|---|---|---|---|---|
| kuhn-intro | 200 | 0.29 | 6.3 | 0.865 |
| river-oop-bet-or-check | 200 | 3.77 | 6.3 | 0.254 |
| river-ip-facing-bet | 200 | 3.74 | 6.3 | 0.868 |
| preflop-hu-open | 300 | 1.61 | 6.3 | 0.340 |
| **preflop-3max-open (all 8 spots)** | **5000** | see below | | **0.035 – 0.861** (max ce0eddffc9af) |
| flop-cbet | 200 | 3.67 | 5.8 | 1.122 (unchanged; C11 PARTIAL, not in scope) |
| turn-barrel | 200 | 2.77 | 5.8 | 0.580 |

3-max cold solve times for all 8 spots at 5000 iterations:

| load | cold solve range |
|---|---|
| ≈ 1.4–2.3 | 11.5–15.2 s |
| ≈ 3.0–3.7 | 11.5–16.6 s |
| ≈ 6–7.5 (full suite running concurrently) | 13.6–21.9 s |

Per-spot exploitability (% pot) at 5000 iterations:

| spot | % pot |
|---|---|
| a4b66447a35b | 0.143 |
| 0214b0a35aef | 0.143 |
| 77d9d76f7f14 | 0.100 |
| e59e7098b6df | 0.077 |
| a99ed8603bf2 | 0.151 |
| ce0eddffc9af | 0.861 |
| 4c22e22fda00 | 0.035 |
| a4a027dd24c3 | 0.125 |

Before this repair the figures were 100 iterations, 7.18 % (spot 0) and `nash_conv=None`.

**Caveat on the time budget.** At load 2–5 every 3-max spot is within 20 s, at most 16.6 s. Above load ≈ 6 the slowest spots
can exceed 20 s (21.9 s seen). The adapter's own timeout is 60 s, so those solves still complete.
F7 single-flight removes the duplicate-request amplification that the audit flagged.

## 6. Tests

- `tests/test_practice_w5_repairs.py`: 23 tests, all pass (~100 s).
- `tests/test_practice_*.py` before the F3–F7 work: **325 passed** (148 s).
- Final `tests/test_practice_*.py` and full-suite counts: see section 7.

## 7. Final suite results
- `tests/test_practice_w5_repairs.py` (final, 23 tests): **23 passed**.
- Full suite `.venv/bin/python -m pytest -q` (final tree, including the other W5 agents' concurrent edits): **1253 passed, 0 failed**
  in 438 s. Includes `tests/test_solver_evaluation.py`, which runs the benchmark live. The W4 baseline was 1136; the extra tests
  come from the W5 agents.
- An earlier full run, started while another agent was mid-edit on `progress.py`, showed 11 failures. All were in
  `test_practice_progress.py` and `test_practice_ui_w4.py`, with `sqlite3 ... no such column: a.spot_id` and similar errors.
  Those failures were not in my files. Re-run alone, the two modules gave 45 passed, and the final full run is green.

## 8. Left open
- `flop-cbet` is at 1.12 % of pot at its 200-iteration default, so C11 is PARTIAL for it. That was not in scope.
- The `multistreet` engine still produces the degenerate RAISE node. Only the user-facing layer is fixed, so the benchmark's
  C15 structural check stays PARTIAL until `multistreet.py` is changed.
- At host load above ≈ 6, the slowest 3-max spots can take more than 20 s cold. The worst seen was 21.9 s.
