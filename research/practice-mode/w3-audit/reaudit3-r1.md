VERDICT: CLEAN

# W3 re-audit round 3, R1 (no hardcoding, parameter sensitivity), commit 13ddaa9

Auditor: fresh adversarial subagent. No repo files changed except this report.

## Baseline
- `.venv/bin/python -m pytest -q tests/test_practice_w3_regressions.py tests/test_practice_no_hardcode.py` → **23 passed**.

## Round-2 repair: stack-only test
- `tests/test_practice_w3_regressions.py:125` `test_stack_change_changes_answer` builds one allstreet flop spot and solves it with
  `stacks=(40,40)` and with `stacks=(400,400)`. Bet sizes `(33,)`, pot, ranges, iterations (15), runouts and board are all the same.
  The test asserts that `bet_sizes` match, so this changes ONLY the stack. Confirmed.

## Mutation checks
Each mutation was applied through a pytest plugin (`-p`, kept outside the repo in /tmp/r1mut). The plugin wraps the solver config
constructors that `practice/adapter.py` imports, so only the value passed to the real solver changes. The spot and its params_hash stay the same.

| Mutation (plugin `mut2.py`) | Result |
|---|---|
| none | 10 passed (selected R1 tests) |
| stack forced to 100 (`RiverConfig.stack`, `AllStreetPostflopConfig.effective_stack`) | **FAILED** `test_stack_change_changes_answer` (`assert (0.0 > 0.001 or 0.0 > 0.001)`) |
| pot forced to 10 (`RiverConfig.pot`, `initial_dead_pot`) | **FAILED** `test_pot_change_changes_action_values`, `test_b_pot_changes_answers_and_hash` (and `test_b_range_width…`) |
| range width ignored (RiverConfig ranges frozen to the first seen for board+pot) | **FAILED** `test_b_range_width_changes_answers_and_hash` |
| iterations forced to 50 (`_train_cfr`, plugin `mut_plugin.py`) | **FAILED** all 3 `test_iterations_change_action_values[*]` and all 3 `test_a_iterations_change_strategy_and_hash[*]` |

Repro: `MUT=<stack|pot|range> PYTHONPATH=/tmp/r1mut .venv/bin/python -m pytest -q -p no:cacheprovider -p mut2 tests/test_practice_w3_regressions.py tests/test_practice_no_hardcode.py -k "stack or pot or iterations or range_width"`.

Each of iterations, range width, pot and stack has at least one permanent test that fails when the solver is made to ignore that parameter alone.

## Hardcoding grep
- The 13ddaa9 diff to src/web is limited to these changes: the `api_v4._float` OverflowError→ValueError change, `practice/server.py` HTTP hardening,
  `web/app.js` Enter-key handling and one CSS line. None of them adds a strategy, Q, score or grade literal.
- `practice/*.py` numeric literals are tolerances, timeouts, Kuhn's fixed pot/stack validation (models.py:379) and the grade band
  thresholds in scoring.py:49-55. These are scoring configuration, not solved answers. `test_c_no_float_probability_dict_literals` passes.
- `api_v4.py:551-557` sends every `practice-*` operation to `practice.api.handle_practice`, with no inline answers.
- On the live server (127.0.0.1:7777), `practice-solve-spot` for `kuhn-intro/917ebff3aaea` returns a check probability of 0.458 at 5 iterations
  and 0.988 at 300 iterations, with different Q values. The answers are computed at runtime.

## Findings
None reproduced.
