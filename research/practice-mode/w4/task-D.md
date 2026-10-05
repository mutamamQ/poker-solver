# W4 task D — practice web UI: filters, 3-max, progress, leaderboard, user, long-solve state

Files owned/changed: `web/index.html`, `web/app.js`, `web/style.css` (extended, not rewritten),
new `tests/test_practice_ui_w4.py`. No Python sources touched. Not committed.

## What changed

### index.html (all W2 IDs kept; verified by the W2 + W4 tests)
- `#user-input` (text, maxlength 32, pattern mirrors server regex) in the topbar + `#user-hint` validation message.
- `#spot-filter` moved from the topbar into a sidebar filter group next to the new `#street-filter` and
  `#game-filter` (each select ships with only its "All …" option; values come from the spot list).
- `#solve-status` (elapsed counter), `#table-felt` id on the felt.
- New `.stats-grid` below the result panel: `#progress-panel` (`#progress-user`, `#progress-refresh`,
  `#progress-status`, `#progress-totals`, `#progress-spots`) and `#leaderboard-panel`
  (`#leaderboard-scope`, `#leaderboard-refresh`, `#leaderboard-status`, `#leaderboard-table`).

### app.js
- **Filters**: street/game options = distinct `street` / `game_type` values of listed spots (streets sorted
  preflop→flop→turn→river, unknown appended; display order only). Filters AND together; status shows
  "N spots of M". Each spot item now shows street + game-type tags; `family-badge` gets `data-family`.
- **3-max**: villains read from `spot.villain_seats` (fallback: non-hero stack indexes). First villain uses
  existing `#seat-villain`; extra villains are created as `.seat.villain.extra-villain` (`#seat-villain-2`, …)
  and removed when switching spots. Felt gets `players-2|players-3|players-many`; seat labels show
  `Villain (Pn) · <stack>` from the API.
- **User**: loaded from `localStorage['practice.user']`, validated with `^[A-Za-z0-9_.-]{1,32}$`;
  invalid → hint + `aria-invalid`, not stored/sent, submit blocked with an error. Empty = server default
  (`user` omitted). Sent as `user` on `practice-submit-play` and `practice-progress`. Storage failures are
  swallowed (in-memory only).
- **Progress panel**: `practice-progress {user?}` on load, on user change, after each submit, and via
  Refresh. Renders totals (attempts, spots tried, avg best, avg last) and a per-spot table (label, street ·
  game, tries, best, last, grade badge, last played local time), sorted by `last_at` desc. Spot-list
  **best-score badge** (`.best-badge`, coloured by `last_grade`) when an entry exists. Submit's
  `result.progress` entry (if present) is merged immediately, then a full refresh runs.
- **Leaderboard panel**: `practice-leaderboard {limit: 20, family?}` (family = current family filter);
  current user's row highlighted (`tr.me`).
- **Graceful degradation**: any error (HTTP 4xx from an unknown op, network) → panel status
  "Progress unavailable: <msg>" / "Leaderboard unavailable: <msg>", `.is-unavailable` class, no global
  error banner, badges cleared; rest of the UI unaffected. Request tokens prevent stale responses.
- **Long solves**: `startSolving(verb)` shows `Solving… Ns` (or `Scoring… Ns` on submit) in
  `#solve-status` and inline in `#action-controls`, ticking every second; after 10 s appends
  "(server limit 90 s)". `#practice-app[aria-busy]` set; submit/resolve/next/action buttons disabled via
  existing `state.pending`. `fetch` gets an `AbortController` safety net at 90 + 15 s with a clear message
  (server's own 90 s timeout normally answers first).
- All values rendered via `textContent`/`createElement`; numbers only from API responses (scores formatted
  `toFixed(1)`).

### style.css (appended W4 section)
Filter group (1 col desktop sidebar, 3 cols at 561–900 px), spot tags/best badge, 3-max seat positions
(villains at 26 % / 74 % of the top rail, stacks move into flow, extra top margin + bottom padding so
nothing collides with the header or hero seat; static stacking ≤560 px), solving pill, stats grid
(`auto-fit minmax(min(100%,420px),1fr)`), totals grid (4→2 cols ≤560 px), scrollable data tables with
sticky headers, unavailable state.

## Verification
- `tests/test_practice_ui_w4.py`: **13 passed** (none skipped — task C's `practice-progress`/`leaderboard`
  ops were live at test time, so the submit→progress round-trip ran). Covers: W2+W4 IDs present & unique,
  form-element/aria checks, selects not hardcoded, CSP (no inline handlers/styles/scripts), no
  innerHTML/outerHTML/insertAdjacentHTML/eval/string timers/on*= assignments, no numeric
  strategy/score/rank literals or hardcoded spot ids/hashes in app.js/style.css, CSS hooks, live index serves
  new IDs, live spot JSON has street/game_type/villain_seats consistent with stacks, leaderboard shape,
  submit with `user` then `practice-progress` shows +1 attempt with matching last_score/street/game_type.
  Progress/leaderboard tests `skip` only if the op returns an error.
- Existing `tests/test_practice_ui.py`: 17 passed (unchanged).
- Browser check (own server on :7790 with temp data/cache dirs; :7777 untouched):
  - Real flow: filter street=river → select → `Solving… 0s` shown, submit disabled → submit → badge
    "Best …", totals, per-spot row, leaderboard row for the typed user; `practice.user` persisted.
  - Keyboard-only: Enter on focused spot item → C → Enter submits; works.
  - Simulated 400 for progress/leaderboard → both panels show "… unavailable: …", spots still load, no
    global error.
  - 3-max layout (client-side injected fake spot since task A families weren't in the list yet): at
    360/600/900/1100/1400/1600 px no bounding-box overlaps among villain seats, hero seat, stacks, board,
    title/meta; `scrollWidth == clientWidth` (no horizontal overflow). 2-player spots unchanged.

- Full suite (`.venv/bin/python -m pytest -q`): **1107 passed, 1 failed, 4 errors**. The failure and all
  4 errors are in the untracked `tests/test_solver_evaluation.py`, which is not from this task. It
  imports `research/solver-evaluation/benchmark.py`, and that file doesn't exist (FileNotFoundError).
  Nothing else failed.

## Notes / decisions
- Family filter moved from the topbar to the sidebar (ID unchanged) to group the three filters and keep the
  topbar from overflowing with the new Player field.
- Leaderboard scope follows the family filter (contract supports `family`); street/game filters don't
  affect it (no API param).
- Villain card backs = hero hand size (unchanged W2 behaviour) for every villain.
- Real 3-max spots weren't available from the catalog during this task (task A concurrent); layout was
  validated with a synthetic client-side spot only — re-check once `preflop-3max-open` lands.
