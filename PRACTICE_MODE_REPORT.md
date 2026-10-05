# Practice Mode Report (GTO Wizard-style puzzle mode)

Branch: feat/practice-mode. Tag: practice-mode-done.

## What was built
- **`src/poker_solver/practice/`**
  - **`models.py`:** spot, solve params and action types. Provides `params_hash` and `spot_id`; `spot_id` stays the same when only the solve params change.
  - **`catalog.py`:** spot catalog generator with 36 spots:
    - 12 Kuhn
    - 12 river out-of-position bet-or-check
    - 12 river facing a bet
    The catalog holds only spot definitions, never answers.
  - **`adapter.py`:** the solver adapter. Every solve runs at request time through the real solver entry points:
    - Kuhn CFR
    - river CFR
    - `allstreet.solve_allstreet_postflop`
    The cache is keyed by the full `params_hash`.
  - **`evaluate.py`:** action values (Q) per legal action, from a walk of the solved tree.
  - **`scoring.py`:** scoring per design §5:
    - EV loss against the best Q
    - percent of pot
    - score
    - grade
    - comparison with the solver's mix
  - **`api.py`:** v4 operations `practice-list-spots`, `practice-solve-spot` and `practice-submit-play`, plus a CLI.
  - **`server.py`:** stdlib threaded HTTP server.
    - Serves `web/` and `POST /api/v4`, using the `dispatch_v4` envelope `{version:4, operation, payload}`.
    - Hardening:
      - bounded solve timeout (504)
      - 1 MiB body limit (413)
      - strict JSON (duplicate keys, NaN and deep nesting all give 400)
      - JSON 404/405 errors with security headers
      - 30 s socket timeout and a whole-request deadline
- **`src/poker_solver/api_v4.py`:** routes the `practice-*` operations.
- **`web/index.html`, `web/app.js`, `web/style.css`:** dark, responsive practice UI. Values are rendered with `textContent` only.
  - Left side: spot list with a family filter.
  - Table area: felt table with board and hero card glyphs, pot and stacks.
  - Actions: fold/check/call/bet/raise buttons, a size input with presets, and keyboard shortcuts (f, c, b, Enter).
  - Results:
    - score ring, grade, EV loss
    - optimal-mix bar
    - Q table and whole-range strategy table
    - feedback
    - solver provenance (algorithm, iterations, `params_hash`, entry point, exploitability)
  - An iterations override with a Re-solve button.

## How to run
    cd /home/genomix-node/poker-solver
    .venv/bin/python -m poker_solver.practice.server --host 127.0.0.1 --port 7777
    # open http://127.0.0.1:7777/
    scripts/practice_smoke.sh 7791          # live smoke (7 checks)
    .venv/bin/python -m poker_solver.practice.api list|solve|submit ...   # CLI

## Solver verdict (rule R1)
Every answer comes from the solver.

- **No hardcoded values:** no strategy, Q value, score or grade is stored anywhere in the catalog, API, JS or CSS. An AST scan and grep tests guard this.
- **Parameter sensitivity:** permanent tests (`tests/test_practice_no_hardcode.py` and `tests/test_practice_w3_regressions.py`) prove that changing one of the following, by itself, changes the returned answer for the same `spot_id`:
  - **Iterations:** 5 vs 300, for all 3 families. Strategy, Q values, range strategy and `params_hash` all change.
  - **Range width.**
  - **Pot.**
  - **Stack:** on the allstreet route with the bet size held fixed.
- **Auditor checks:**
  - Strategy and Q values from an independent CFR re-solve matched the API to 1e-14.
  - Recomputing the scoring by hand matched to 1e-12.
  - Mutation testing confirmed each kind of hardcoding (Q values, strategy, range strategy, stack) is caught by at least one test.
- **Known limitation:** the river backend ignores stack size once the stack covers the bet, which is correct poker. Flop spots are left out of the catalog because each solve takes about 10 s; the adapter's flop route itself is tested.

## Process
- **W0:** design (7 reports).
- **W1:** backend (3 subagents).
- **W2:** frontend (3 subagents).
- **W3:** audit with 3 non-author auditors per round. All rounds used bryant-opus-55 per the owner's directive.
  - Round 1: 2 MAJOR + 11 MINOR.
  - Round 2: 2 MAJOR + 5 MINOR.
  - Every finding was reproduced, then repaired with a regression test.
  - Round 3: R1 clean; 4 MINOR/LOW server issues and 1 MINOR UI issue. 3 server issues and the UI issue repaired; header trickle and the legacy solve-allstreet-postflop body shape accepted, both LOW.
  - Round 4: R1 and R3 clean; 1 MINOR server issue (leading CRLF bypassed the request-line length limit), repaired with a test and verified live.
- **Final suite:** 1026 passed (baseline 817 + 209 new).
- **Server:** running at http://127.0.0.1:7777 (tmux session practice7777).

## bryant-gpt provider issues
Full log is in PROGRESS.md under "## bryant-gpt provider issues". In W1, the OpenAI bryant models failed to produce any code:
- **bryant-gpt61-sol:** blocked from creating files.
- **bryant-gpt6-luna:** stopped on a tool-call format error.
- **bryant-gpt6-astra:** stopped to ask a question.
Before that, the orchestrator's tools returned "not available in the current context" until the bridge moved to native function calling. After the owner directed everything onto bryant-opus-55, all dispatches finished with real work.
