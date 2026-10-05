# W5 repair-D — UI audit findings 1–7 fixed

Source: `research/practice-mode/w5-audit/audit-ui.md`. Files changed: `web/app.js`, `web/style.css`,
`web/index.html` (hint text unchanged in meaning), `tests/test_practice_ui_w4.py` (one test adapted to W5 F1),
new `tests/test_practice_w5_ui_repairs.py`. No Python under `src/` touched. Not committed.
The strict CSP still holds: no inline script/style, no innerHTML. All existing DOM IDs are kept.

## Fixes

| # | Finding | Fix |
|---|---------|-----|
| 1 MAJOR | F/C/B and the size input were dead on preflop-hu-open, preflop-3max-open, flop-cbet and turn-barrel (uppercase `FOLD/CALL/RAISE`) | Every kind comparison now goes through `normKind()` (trim + lowercase): `isSized()`, `indexesByKinds()`, `sizedAmounts`, `currentPlay`, the size-input handler and the presets. Buttons, shortcuts and sizes all come from the API's `legal_actions`. The play sent back keeps the **original** kind string (`RAISE`), which the server requires (lowercase `raise` → 400). Pressing the same key again cycles through matching actions (B: Raise 5 → Raise 40). Typing an exact legal amount selects that action; an off-tree amount keeps or picks a raise, and the server snaps it (`size_mapped`). An `A` key covers all-in kinds if a backend ever emits them. Presets get `aria-pressed`/`.selected`. |
| 2 | Best badge was coloured by `last_grade` | The API gives no best-attempt grade, so the badge is now neutral (accent colour, no `grade-*` class). CSS forces the neutral style. |
| 3 | Leaderboard "me" row went stale after a user change | `applyUser(true)` immediately re-renders the cached leaderboard result (`lastLeaderboard`, API data) with the new `me`, then reloads it. |
| 4 | Progress table clipped at every width | The stats panels now stack full width. Table cells can wrap (spot labels are no longer ellipsized). Header alignment matches numeric cells. Below 640 px **panel** width (container query), rows become labelled cards: `td[data-label]` plus `attr()`, with the thead hidden. |
| 5 | HU villain seat overlapped `#spot-meta` at ≥1400 px | `.table-felt { margin-top: 34px }` from 561 px up, the same clearance 3-max already had. |
| 6 | Focus fell to `<body>` after submit | After a result, focus goes to `#next-spot`; after a failure, to `#submit-play`. After a solve (e.g. Next spot), if focus was lost it goes to the first action button. Shortcuts focus the selected button (or `#action-size` for B with sizes), so Enter submits. |
| 7 | Raw `FOLD`/`CALL 2`/`RAISE 40` labels | `kindLabel()` maps kinds to Fold/Check/Call/Bet/Raise/All-in, and unknown kinds become "Some kind". This is display only. Labels apply to buttons, history, mix legend, Q table, range text and the "size mapped to" note. `text-transform: none` on buttons and history chips. |

## Live verification (own server 127.0.0.1:7795, isolated cache/data dirs; port 7777 untouched; stopped at end)

- 3-max `a4b66447a35b`: buttons `Fold, Call 2, Raise 5, Raise 40`. Size row visible with presets `5, 40`.
  `f`→Fold, `c`→Call 2, `b`→Raise 5 (focus `#action-size`), `b`→Raise 40, `b`→Raise 5. Submit enabled.
  B, then type 12, then Enter: request play `{"kind":"RAISE","amount":12}`. Feedback ends "(size mapped to Raise 5)".
  Legend and Q table show `Fold/Call 2/Raise 5/Raise 40`. Focus after the result: `next-spot`.
- 3-max SB `a99ed8603bf2`: history `Fold`.
- Legacy families unchanged: river-oop `c`→Check, `b`→Bet 33 + size focus; river-ip `f`/`c`; kuhn `c`/`b`.
- Badge: `Best 99.8` → class `best-badge`, colour `rgb(179,162,255)`, bg `rgba(124,92,255,0.12)`.
- Leaderboard: user `w5ui_a`[me] → change to `probe_w5` → `probe_w5`[me] immediately, no Refresh.
- Layout via getBoundingClientRect, turn-barrel (HU) and 3-max, at 360/900/1400/1600:
  page overflow 0; progress `scrollWidth==clientWidth` (294/820/1004/1194); leaderboard same; 0 cells
  outside the panel; seat∩spot-header area 0. At 1400/1600 the HU seat top is 143.8, below the meta bottom of 120.3
  (it was 117.8 before the fix). At 360 the tables render as stacked cards.

## Tests

`tests/test_practice_ui.py` + `tests/test_practice_ui_w4.py` + `tests/test_practice_w5_ui_repairs.py`:
**51 passed** (13.0 s, warm solve cache).

The new file has 21 tests: 7 static, 4 live API, and 10 live-browser tests on a real `make_server` (ephemeral port,
isolated `ProgressStore`). The browser tests drive headless Chrome over CDP with a stdlib WebSocket client
and skip only if no Chrome is installed. They cover:
- shortcuts, labels and presets per new family
- the custom size sending the original uppercase kind
- focus after submit and after Next spot
- the neutral badge after two attempts
- the leaderboard `me` moving without a Refresh
- layout at 4 widths × 2 spots

Against the HEAD UI, 16/21 fail (the 5 passing are API/CSP sanity checks).

`test_practice_ui_w4.py::test_live_submit_then_progress_shows_attempt` was already failing with the
concurrent W5 F1 backend change: submits with a non-default `solve` override are no longer recorded. It now
asserts that rule, then checks that a family-default submit is recorded. Note: like before, that test writes to the
default progress store unless `POKER_PRACTICE_DATA_DIR` is set.

## Not changed / notes

- The server still labels a flop/turn first bet as `RAISE` (audit out-of-scope), so the UI shows "Raise 33".
- Two identical-colour raise buttons are told apart only by their amount (unchanged design).
