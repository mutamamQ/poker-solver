# W3 audit-1: R1 (no hardcoding, solver fidelity)

Auditor: fresh adversarial agent. Scope: frozen manifest `research/practice-mode/w3-audit/CANDIDATE_MANIFEST.md` (HEAD 67c421f).
Scratch scripts are in `/tmp/r1audit/`. I edited no repo file except this report. I started no server of my own and only queried 7777.

## VERDICT: FINDINGS (2 MINOR, 0 BLOCKER, 0 MAJOR)

The core R1 property holds. Every strategy, Q value, score and grade I checked comes from a runtime `CFRSolver` solve, and I reproduced the numbers independently to 0.0 difference. The two findings are gaps in test coverage and spec coverage, not hardcoded answers.

## Verified clean (reproduced)

- **Manifest:** `grep -E '^[0-9a-f]{64}' CANDIDATE_MANIFEST.md | sha256sum -c` returns OK for all 21 files.
- **Source review of `models`, `catalog`, `adapter`, `evaluate`, `scoring` and `api`:**
  - No literal strategy, probability, EV, optimal action or grade answer.
  - `catalog.py` contains only solver inputs: range texts, pot grid, bet %, SPR, Kuhn public nodes.
  - Grade thresholds (`scoring.py:48-53`) match design §5.
  - `adapter._policy_at` (adapter.py:275-282) copies `float(policy[a])` without editing it.
  - The cache is keyed by the full `params_hash`, which includes `solve`. Its only writer is `solve()` after a real solve (adapter.py:149-152). I found no default or fallback answer path. An unrouted backend raises `ValueError`.
  - The hero infoset is found by a tree walk (`locate_decision`). No module parses `str(InfoKey)`, per a grep for `str(`, `repr(`, `split(` and `startswith` on infokeys.
- **`tests/test_practice_no_hardcode.py`:** 8 passed. Full practice suite: 190 passed.
- **Mutations, run as pytest plugins via `PYTHONPATH=/tmp/r1audit .venv/bin/python -m pytest -p <mut> ...`:**
  - `mut_s` replaces `SolverAdapter._policy_at` with a uniform constant. no_hardcode fails 4 of 8 tests, so a hardcoded strategy is caught.
  - `mut_q` and `mut_q2` replace the Q values with constants. They are caught by the full suite but **not** by the no_hardcode file (see F1).
- **Independent math, `/tmp/r1audit/kuhn_q.py`:**
  - Spot: `kuhn-intro/ba3e63844dda` (P1 holds Q and faces a bet), 3000 iterations.
  - My own walk (`kuhn_root` + `CFRSolver.train(3000)`, opponent-reach weighting) gives Q(fold) = -1.0 and Q(call) = -1.05815306771459, with sigma = fold 0.65886 / call 0.34114.
  - `practice-solve-spot` returns the same values. |ΔQ| = 0.0 and |Δsigma| = 0.0.
  - I scored 3 plays against §5 (ev_loss, pct, score, grade, self_loss), with pot_at_decision = 3. All match to 1e-12:

    | play | ev_loss | % pot | score | grade |
    |---|---|---|---|---|
    | call | 0.05815 | 1.938 | 0 | Inaccuracy |
    | fold | 0 | 0 | 100 | Perfect |
    | mix call 0.3 / fold 0.7 | 0.01745 | 0.58 | 70.0 | Good |

    solver_self_loss = 0.019838 in all three cases.
- **Live check on 127.0.0.1:7777** (curl POST `/api/v4`, `practice-solve-spot`, iterations 5 vs 400):
  - `kuhn-intro/820b58289136`: hash c0cc24b4… vs 5303a6d1…; strategy [0.625, 0.375] vs [0.7868, 0.2132]; nash_conv 0.377 vs 0.025.
  - `river-oop-bet-or-check/e79981f9d62d`: hash 3239d4cd… vs d03aae8f…; strategy [0.5145, 0.4855] vs [0.0669, 0.9331].
  - For both spots, the hash, strategy, Q values and range_strategy all differ between the two iteration counts.
- **web/app.js and web/style.css:**
  - The only numeric literal in app.js is `p < 0.08`, a display threshold for tiny segments at app.js:448.
  - Grades and scores are rendered from API fields.
  - The grade names in style.css are only color classes.
  - No literal answers.

## Findings

### F1 MINOR: the dedicated R1 test does not guard action values or scores
- **Location:** tests/test_practice_no_hardcode.py:58, :66, :84, :92.
- **What it checks:** test_a checks only strategy and range_strategy. test_b accepts "strategy OR action_values". Because the strategy alone changes, a hardcoded Q (and therefore a hardcoded score) passes every test in the file.
- **Reproduction:**
  ```
  cd /home/genomix-node/poker-solver
  PYTHONPATH=/tmp/r1audit .venv/bin/python -m pytest -q -p mut_q  tests/test_practice_no_hardcode.py
  PYTHONPATH=/tmp/r1audit .venv/bin/python -m pytest -q -p mut_q2 tests/test_practice_no_hardcode.py
  ```
  - `mut_q` wraps `adapter.action_values` to return Q = 0.0 for all actions.
  - `mut_q2` returns Q = action index.
- **Expected:** failures, since design §0.3 says the test must show the "optimal strategy and/or the score" responds to the parameters.
- **Actual:** `8 passed` for both mutations.
- **Mitigation already present:** the wider suite catches both. `mut_q` fails `test_practice_cli_smoke.py::test_r1_iterations_change_score_and_hash` and `test_practice_scoring.py::test_real_solve_dominated_action_positive_loss`. `mut_q2` fails only `test_practice_ui.py::test_e2e_solve_and_submit[kuhn]`. So R1 is enforced, but by tests outside the R1 file, and the index-constant Q mutation is caught by a single UI e2e test.

### F2 MINOR: the stack-sensitivity requirement of §0.3 is not tested, and the stack has no effect on answers in the routed backends
- **Location:** tests/test_practice_no_hardcode.py. No test varies `stacks`. The only stack check is `test_practice_models.py:175`, which covers the hash only.
- **Reproduction:**
  ```
  .venv/bin/python -c "import dataclasses;from poker_solver.practice.catalog import generate_catalog;from poker_solver.practice.adapter import SolverAdapter;from poker_solver.practice.models import SolveParams;s=generate_catalog(families=('river-oop-bet-or-check',),solve=SolveParams(iterations=200),limit=1)[0];t=dataclasses.replace(s,stacks=(s.stacks[0]*3,)*2);A=SolverAdapter();a,b=A.solve(s),A.solve(t);print(s.params_hash()!=t.params_hash(),dict(a.strategy)==dict(b.strategy),dict(a.action_values)==dict(b.action_values))"
  ```
- **Expected (§0.3):** changing the stack changes the strategy and/or the score, and also the `params_hash`.
- **Actual:** `True True True`. The hash changes, but the strategy and Q values are identical: check 0.05389 / bet 0.94611 and Q = 54.084 / 56.825 at both stacks. The river backend has a single bet size that is always ≤ stack, so the stack is not a strategic input. Kuhn's stack is fixed at (1, 1), and allstreet is not in the catalog. So no catalog family can satisfy the stack clause.
- **Not a hardcoding defect.** It is a gap between the spec and its coverage. Fixing it needs a stack-sensitive family (for example an all-in-capped bet, or allstreet) or an explicit spec amendment.

## NOTES (speculation or design observations, not reproduced as defects)
- `SolverAdapter(cache=...)` accepts an external mapping and does not re-check that a cached `SolvedSpot.provenance.params_hash` equals its key. `SolvedSpot` itself enforces provenance-hash = spot-hash, so a poisoned entry would need a deliberately wrong key. No production path injects a cache: `api._ADAPTER = SolverAdapter()`.
- `optimal_action` is the argmax of solver *probability* (adapter.py:246-247), while `best_action` in scoring is the argmax of Q. At low iterations these can differ. Both are solver-derived and the UI labels them separately. This is consistent with §3/§5 but could confuse users.
- `_pot_at` for Kuhn (adapter.py:72) is a closed-form pot from the game rules (ante 2 + 1 per bet/call), not read from state. It is correct for Kuhn and is not an answer value.
- The API accepts `external-sampling-mccfr`, but the Kuhn and river backends reject it with `ValueError`. This fails closed, so there is no R1 impact.
