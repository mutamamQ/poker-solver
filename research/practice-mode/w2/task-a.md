# W2 task-a — web/index.html + web/app.js

## Files
- `web/index.html` — static shell. Has every required ID from UI_CONTRACT (practice-app, spot-list, spot-status, spot-details, board-cards, pot-value, stacks-list, action-history, hero-hand, action-controls, action-size, submit-play, result-panel, score-value, grade-value, ev-loss-value, optimal-mix, range-strategy, provenance, error-message) plus iterations-input, resolve-btn, feedback-text, action-values, spot-filter, next-spot.
- `web/app.js` — vanilla-JS IIFE, no dependencies. Every API string is written with textContent or attributes; innerHTML is never used.

## Decisions
- **Cards:** T is shown as "10". Single-character cards are treated as Kuhn cards (`card kuhn`, no suit span). Range hands such as "9d9h" are split into 2-char cards. The hero row is found by comparing the sorted card list against `hero_hand_str`.
- **Practice-mode secrecy:** the solve response stays in `state.solved`. Before submit, only `spot` and `legal_actions` are read from it. strategy, action_values and range_strategy are read only from `submit.result.solved`.
- **Table before the solve returns:** while the solve runs, the table is pre-rendered from the list-spots entry, so the board and stacks appear at once. When the solve arrives it is re-rendered from `result.spot`.
- **Size input:** `#size-row` (class `size-row`) holds `#action-size` and the `.size-preset` chips. It is shown only when a legal bet/raise has amount > 0. The default is the smallest legal amount. Kuhn's `bet` has amount 0, so no size row is shown there. Choosing a sized action fills in its amount. A typed size is sent as-is and the server snaps it (`size_mapped`/`mapped_action` is appended to the feedback).
- **Button label:** `Cap(kind)`, plus the amount when it is > 0 (e.g. "Bet 33").
- **Grade class:** `grade-` + the API grade lowercased, with any non-[a-z0-9_-] character replaced by `-`.
- **EV loss format:** `X.XXX chips (Y.YY% pot)`. The score ring's text is the score; `--score` is the raw API score.
- **Provenance source:** taken from `solved.provenance`, falling back to `score.provenance`. `seed: null` is shown as "none". params_hash shows its first 16 characters plus "…"; the full hash is in `title` and `data-full-hash`.
- **Q table:** marks the row matching `best_action` as "best" and the row matching the user's play (or `mapped_action`) as "yours".
- **Pending state:** while any request is in flight, submit, re-solve, next-spot, the action buttons and the size input are disabled, and `#solve-spinner.spinner` is shown. A solve token drops stale responses when the user switches spots mid-solve. After a submit, all actions stay locked until a new spot is selected or the spot is re-solved.
- **Keyboard:** F, C (check, else call), B (bet, else raise; also focuses the size input), Enter (submit). Shortcuts are ignored while typing in inputs. Enter in iterations-input re-solves instead.
- **Next spot:** advances cyclically through the currently filtered list.
- **Extra classes not in the contract** (style.css may ignore them): app-title, kbd-hint, topbar-field, spot-header, spot-meta, seat-name, seat-cards, board-area, pot-label, history-row, history-label, size-presets, submit-row, result-summary, result-stats, stat, stat-label, q-table (with tr.best and tr.chosen), mix-legend-item, range-hand, range-text.

## Verification (2026-10-05)
- `node --check web/app.js` → OK.
- Server on :7790: `/` 200, `/app.js` 200, `/style.css` 200 (style.css comes from the parallel worker).
- curl with the exact JS payloads, all 200:
  - list `{}`
  - solve `{spot_id}` (kuhn)
  - solve `{spot_id, solve:{iterations:40}}` (river)
  - submit `{spot_id, play:{kind:"bet",amount:0}}` (kuhn)
  - submit off-tree `{play:{kind:"bet",amount:50}, solve:{iterations:40}}` → `size_mapped=true`
- Unknown spot_id → 400 `{"error":...}`, as expected.
- Headless browser smoke test:
  - 36 spots listed.
  - River spot renders board and hero cards and the buttons "Check" / "Bet 33", with size default 33. The result panel stays hidden before submit.
  - B + Enter → score 100, `--score` set, `grade-perfect`, mix segments with widths, Q table, 4 range rows with 1 `.hero-hand-row`, full provenance grid.
  - The Kuhn spot renders `card kuhn` J with buttons Check / Bet.
- Server killed. `pytest -q tests/test_practice_api.py` → 37 passed.
- grep found no hardcoded probabilities, grades or spot ids in app.js.
