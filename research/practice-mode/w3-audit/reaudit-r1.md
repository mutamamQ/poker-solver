VERDICT: FINDINGS

# W3 re-audit round 2 — R1 (no hardcoding, solver fidelity)

Scope: branch feat/practice-mode @ d37eec3. Auditor scratch files live in /tmp/r1mut (not in the repo).
Python: `.venv/bin/python`. Live server http://127.0.0.1:7777 was used read-only and left running.

## Verification of round-1 repairs

### (a) Q / strategy / range_strategy mutation tests: VERIFIED
Pytest plugin `/tmp/r1mut/r1mut_plugin.py` wraps `SolverAdapter._finish` and replaces one output field
with constants (`R1MUT=q` sets Q to {a_i: i}, `strategy` makes it uniform, `range` makes every range entry uniform).
Command (run from the repo root):

    PYTHONPATH=/tmp/r1mut R1MUT=<mode> .venv/bin/python -m pytest -p r1mut_plugin -q -p no:cacheprovider \
        tests/test_practice_no_hardcode.py tests/test_practice_w3_regressions.py

| mode | result |
|---|---|
| (none) | 19 passed |
| q | 4 failed (test_iterations_change_action_values x3, test_pot_change_changes_action_values) |
| strategy | 1 failed (test_stack_change_changes_answer) |
| range | 1 failed (test_b_pot_changes_answers_and_hash) |
| all | 10 failed |

At least one test fails for each mutation, so the repair holds. Coverage of strategy-only and
range-only hardcoding depends on a single test each, so it is thin but it works.

### (b) Stack sensitivity: the test passes, but it does not show that stack has any effect. See F1.

### Independent river re-solve: MATCHES
Spot `river-oop-bet-or-check/e79981f9d62d` (pot 100, stacks 200, bet 33), solved via `practice-solve-spot` on :7777
at 7 and 400 iterations (`/tmp/r1mut/api.py`). I then re-solved it directly with `river_root` + `CFRSolver.train` and my own
tree walk for Q, without using practice.evaluate (`/tmp/r1mut/indep.py`):
- 7 it: σ = check .63817 / bet .36183, Q = 62.9767 / 59.4286 (API and independent results match exactly)
- 400 it: σ = check .06689 / bet .93311, Q = 55.3217 / 56.3108 (match to 1e-14)
- nash_conv drops from 12.96 to 0.426, params_hash changes, and range_strategy changes (e.g. KcKs check .641 → .281).

### Scoring vs PRACTICE_MODE_DESIGN.md §5: MATCHES
Submitted a pure `check` at 400 iterations. I recomputed every metric by hand from the API's Q and σ:
ev_loss 0.98908, pct 0.98908, score 0.0 (spread equals the loss, because check is the worst action), grade Good (≤1),
solver_mix_q 56.24461, self_loss 0.06616. All values are identical to the API response. scoring.py:357-370 implements §5 exactly.

No new float or strategy literals were found in the catalog, api, api_v4 practice routing, app.js or index.html.
The d37eec3 diffs to scoring.py, server.py and app.js only add validation and UI changes.

## Findings

### F1 — MAJOR — the stack-sensitivity test changes the bet size together with the stack; the stack alone is never shown to change anything
- tests/test_practice_w3_regressions.py:125-134 (`test_stack_change_changes_answer`) changes `stacks` 40→150 **and**
  `bet_sizes` 40→150 at the same time. The river backend only uses stack for validation (src/poker_solver/river.py:33-36) and the infoset key
  (river.py:124). Payoffs and the tree depend on `bet` only, so the change in the answer comes entirely from the bet size.
- Reproduction 1: with the same bet, the stack has no effect on the answer:

      .venv/bin/python /tmp/r1mut/stack.py
      # stack40/bet40, stack150/bet40 and stack1000/bet40 give identical strategy {check .168859, bet40 .831141},
      # identical Q {51.881, 55.483} and identical range_strategy (True)

- Reproduction 2: the test still passes when the adapter ignores the spot's stack completely
  (the plugin forces `RiverConfig(stack=10**9)` at src/poker_solver/practice/adapter.py:183-190):

      PYTHONPATH=/tmp/r1mut .venv/bin/python -m pytest -p r1stack_plugin -q -p no:cacheprovider \
          "tests/test_practice_w3_regressions.py::test_stack_change_changes_answer"
      # 1 passed

- Impact: R1 requires a permanent test showing that changing the stack changes the answer. The current test would not catch
  stack being dropped or hardcoded. For every catalog family (kuhn and river), the stack has no effect on the answer.
- A genuine test is possible on the allstreet route. I ran `/tmp/r1mut/as.py` on the allstreet fixture from
  tests/test_practice_adapter.py:29 at 30 iterations, changing only the stack:
  - stack 40: σ = CHECK .872 / RAISE33 .128, Q(CHECK) = -11.13
  - stack 100 and 400: σ = .726 / .274, Q(CHECK) = +0.399

  An allstreet stack-only test, or a river test that keeps the bet fixed, would actually exercise the stack parameter.
