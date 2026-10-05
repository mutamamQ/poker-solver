# W5 audit-3 — live adversarial UI audit (W4 practice web UI @ 5a3e61f)

Auditor: non-author, read-only. Worktree `/tmp/w4audit` (HEAD `5a3e61f`). Own server on
`127.0.0.1:7793` with `POKER_PRACTICE_CACHE_DIR=/tmp/w5a3/cache`, `POKER_PRACTICE_DATA_DIR=/tmp/w5a3/data`
(port 7777 untouched; server stopped at the end). Browser: Chromium via CDP, all checks scripted with
`getBoundingClientRect`/DOM reads and compared against raw API responses captured by a fetch wrapper.
Evidence: `screens-ui/submit_families.json`, `screens-ui/layout.json`, `screens-ui/3max-{360,1100,1600}.png`.

## Summary

| # | Severity | Finding |
|---|----------|---------|
| 1 | MAJOR | Keyboard shortcuts F/C/B (and therefore C→Enter submit) and the size input are dead on all 4 new families (36/72 spots): API emits UPPERCASE action kinds, UI matches lowercase only |
| 2 | MINOR | Best-score badge is coloured by `last_grade`, not by the best score it displays ("Best 100.0" rendered red/purple as `grade-blunder`) |
| 3 | MINOR | Leaderboard "me" highlight goes stale after changing `#user-input` (leaderboard not reloaded/re-rendered on user change) |
| 4 | MINOR | Progress table always needs horizontal scrolling — even at 1600 px the "Last played" column is clipped off the panel |
| 5 | NIT | Heads-up villain seat box overlaps `#spot-meta` at ≥1400 px (22×2 px @1400, 108×2 px @1600) |
| 6 | NIT | Focus is dropped to `<body>` after submit; keyboard user must re-Tab ~20+ stops to continue |
| 7 | NIT | Uppercase kinds leak verbatim into labels (`FOLD`, `CALL 2`, `RAISE 5`, history `FOLD`/`CHECK`) while legacy families show `Check`/`Bet 33` |

No BLOCKERs. Verified OK (details at the end): 7 families, all 120 filter combinations, 3-max table, 0/3/4
board cards, submit result panels for each new family, solving counter + disabled controls, user validation +
persistence, progress totals/rows/badges, leaderboard per family, error states, no page-level horizontal
scroll, no CSP violations / JS errors.

---

## 1. MAJOR — Shortcuts and size input broken for preflop-hu-open, preflop-3max-open, flop-cbet, turn-barrel

**Cause (observed in data):** `practice-solve-spot` returns `legal_actions` with uppercase kinds for the new
backends, e.g. 3-max `preflop-3max-open/a4b66447a35b`:
`[{"kind":"FOLD","amount":0},{"kind":"CALL","amount":2},{"kind":"RAISE","amount":5},{"kind":"RAISE","amount":40}]`;
flop `flop-cbet/11769311f1bd`: `CHECK 0, RAISE 33`; action_history is likewise `FOLD`/`CHECK`.
`app.js` compares case-sensitively: `selectByKinds(["fold"])`, `["check","call"]`, `["bet","raise"]`
(lines 985–991) and `SIZED_KINDS = {bet:true, raise:true}` (line 13, used by `sizedAmounts`, `currentPlay`,
the `action-size` input handler). The W2 UI contract says kinds are lowercase, so this is a UI↔API contract
mismatch; either side can fix it, but the UI is what's broken for the user.

**Steps:**
1. Load `http://127.0.0.1:7793/`, click spot `preflop-3max-open/a4b66447a35b`, wait for the 4 action buttons.
2. Blur focus (`document.activeElement.blur()`), press `f`, `c`, `b` (CDP `Input.dispatchKeyEvent`).
3. Read `.action-btn.selected` and `#submit-play.disabled`.

**Result:** after each key, no button is selected and `submitDisabled=true`. Same on
`flop-cbet/9a471ac7b613` (`c`, `b` → nothing selected; then `Enter` → nothing submitted).
Control: on `river-oop-bet-or-check/*` (lowercase kinds) `c` → `Check` selected; `b` → `Bet 33` selected,
size row shown, focus moved to `#action-size`.

**Size input side effect:** for every new-family spot `#size-row` stays `hidden` and `#size-presets` is empty
even though `RAISE` actions are legal (3-max: `RAISE 5`/`RAISE 40`; flop/turn: `RAISE 33`), so the custom-size
path (server snapping of off-tree sizes) can't be reached on 4 of 7 families. Measured: `sizeVis:false,
presets:[]` for all four families (`submit_families.json`).

Workaround that does work: Tab to an action button and press Enter (selects and submits). The advertised
hint "F fold · C check/call · B bet/raise · Enter submit" is wrong for half the catalog.

## 2. MINOR — Best badge coloured by last grade

**Steps:** user `auditor3`; submit `RAISE 5` on `preflop-3max-open/a4b66447a35b` (API: score 100, Perfect);
re-select the same spot, submit `FOLD` (API: Blunder).
**Result:** the badge reads `Best 100.0` (correct, from `best_score`), but its class is `best-badge grade-blunder`,
colour `rgb(179,162,255)`, background `rgba(179,162,255,0.14)`; tooltip `Best score 100.0 · 2 attempts`.
`bestBadge()` adds `grade-<last_grade>` (app.js 468). A "Best 100" badge in blunder colour misrepresents the
best result. (The API entry has no best grade; either colour by last and label it "Last", or keep it neutral.)

## 3. MINOR — Leaderboard "me" row stale after user change

**Steps:** user `auditor3` (ranked #1), click leaderboard Refresh → row `auditor3` has `tr.me`. Change
`#user-input` to `someoneelse` and fire `change`.
**Result:** `#progress-user` updates to `· someoneelse` and progress reloads, but the leaderboard still shows
`auditor3` highlighted as `me` (`['auditor3[me]']`). `applyUser(true)` only calls `loadProgress()`;
`renderLeaderboard` computes `me` only when the leaderboard is (re)loaded. The highlight is corrected only
after a manual Refresh, a family-filter change, or the next submit.

## 4. MINOR — Progress table clipped at every width

The progress table has a fixed min width: `#progress-spots` `scrollWidth=795` vs `clientWidth`
570 @1600, 704 @1100, 520 @600, 314 @360 (`overflow-x:auto`). At 1600 px the `Last played` header spans
x=984..1138 while the panel's right edge is x=913, so the column is fully hidden until the user scrolls
sideways. The stats grid lays the two panels out side by side from 900 px up, so the progress panel only gets
about half the main column. There's no page-level overflow (the scroll stays inside the panel), but at no
tested width is the table readable without horizontal scrolling. Leaderboard table fits (520/520 etc.) except
at 360 (330 vs 314).

## 5. NIT — Villain seat overlaps spot meta at wide widths (heads-up spots)

Spot `turn-barrel/b95c7dba968a`, scroll 0:
- 1400 px: `#seat-villain` [729.9, 117.8, 960.1, 193.8] vs `#spot-meta` [937.7, 100.5, 1045.5, 120.3] → 22×2 px intersection.
- 1600 px: `#seat-villain` [824.9, 117.8, 1055.1, 193.8] vs same meta → 108×2 px.
The seat sits 14 px above the felt top (felt top 131.8) by design, and its box (opaque bg + 1 px border) clips
the descender line of "turn-barrel · turn". 3-max spots (seats at 26 %/74 %) have no overlaps at any width;
there were no other intersections among seats, board, pot, stacks, title, meta or status at 360–1600.

## 6. NIT — Focus lost after submit

Keyboard flow: Tab order is user → iterations → 3 filters → spot items (Enter selects) → … reaching the first
`.action-btn` took 23 Tabs from the active spot item (3-max). Tab, Enter on `CALL 2` selected and submitted
(works). When the result rendered, `document.activeElement` was `BODY`, so Next spot means tabbing through
the whole list again. Focus should move to the result or `#next-spot`.

## 7. NIT — Raw uppercase labels

`actionLabel()` only capitalises the first char, so new families show `FOLD`, `CALL 2`, `RAISE 40`, history
step `FOLD`/`CHECK`, mix legend `FOLD 0.2%`, while legacy families show `Check`, `Bet 33`. Values come from the
API (so no fabrication); it's just inconsistent presentation. Same root cause as #1.

---

## Verified (no finding)

- **Families/filters:** `#spot-filter` lists all 7 families from `result.families`; street options
  `preflop, flop, turn, river`; game `3-max, heads-up`. Exhaustive 8×5×3 = 120 combinations: UI list equals
  the AND-filtered API list in order in all 120 (0 mismatches). Empty combo (flop + 3-max) → "No spots
  available.", Next disabled. Counts: kuhn 12, river-oop 12, river-ip 12, preflop-hu 12, preflop-3max 8,
  flop 8, turn 8 = 72.
- **3-max render** (`preflop-3max-open/a4b66447a35b`): felt `players-3`; `#seat-villain` "Villain (P1) · 40" and
  `#seat-villain-2` "Villain (P2) · 40", 2 card backs each; hero "Hero (P0)" with Kh Ks; stacks P0/P1/P2 = 40
  (API `[40,40,40]`, `villain_seats [1,2]`); pot 3 = API pot/pot_at_decision; history "First to act"; 0 board
  cards; buttons `FOLD, CALL 2, RAISE 5, RAISE 40` = API legal_actions exactly. SB spot `a99ed8603bf2`: hero P1,
  villains P0/P2, history `FOLD`. Switching back to a HU spot removes the extra seat (1 villain, `players-2`).
- **Boards:** preflop 0, flop 3 (`9d Tc 2h`), turn 4 (`As Td 7h 6s`) cards, matching `board_str`.
- **Submit per new family** (preflop-hu, flop, turn, 3-max ×2): score/grade/EV text equal to API
  (e.g. 3-max SB: 54.47788… → "54.5", Blunder, "1.224 chips (40.81% pot)"); mix-bar segment count and widths =
  API probabilities (e.g. 48.2258 %); legend, Q table (best/yours tags), range rows count = API, exactly one
  hero-hand row; provenance backend/algorithm/iterations/nash_conv (null → "—")/wall_time/solver_version/hash
  prefix equal to API. Strategy isn't shown before submit (result panel hidden; only legal actions).
- **Solving state:** cold 3-max solve took about 17 s (API wall_time 16.09 s). "Solving… Ns" ticked every second in
  both `#solve-status` and inline; "(server limit 90 s)" appended from 10 s; submit/resolve/next disabled and
  `aria-busy=true` throughout; all restored on completion. Cold flop 4.6 s, turn 3.6 s, preflop-hu 2.5 s,
  3-max SB 7.1 s.
- **User input:** `bad name!`, 33×`a`, `é`, `../x` → hint shown, `aria-invalid=true`, storage and progress
  unchanged; `  spaced  ` trimmed → `spaced`; empty → storage removed, server default `local`; value persists
  across reload; corrupted stored `<bad>` is discarded on load. Iterations `-5` → "Iterations must be a positive integer."
- **Progress:** totals (5 / 5 / 50.9 / 50.9) and per-spot rows (sorted by `last_at` desc: spot, tries, best,
  last, grade) equal `practice-progress {user:auditor3}`; best badges present for exactly the 5 API spots
  with matching `Best x.x`.
- **Leaderboard:** for "all" and each of the 7 families, UI rows equal `practice-leaderboard {limit:20,family}`
  rows (rank|user|spots|tries|avg|total); scope label follows the family filter; empty → "No ranked players yet."
- **Error states** (fetch monkeypatched pre-load): progress+leaderboard HTTP 500 or network reject → "Progress
  unavailable: …"/"Leaderboard unavailable: …", `.is-unavailable`, totals hidden, badges cleared, spots still
  load, no global banner. list-spots 500 → "Failed to load spots: …" in status + banner. solve 500 → "Solve
  failed: …", submit stays disabled. submit 500 → "Submit failed: …", no result panel, submit re-enabled.
  A failed Refresh after a good load also clears badges.
- **Layout:** at 360/600/900/1100/1400/1600 `documentElement.scrollWidth == clientWidth`; no element extends
  past the viewport outside `.table-wrap`; no topbar child overlaps, no action-button overlaps, no seat/board/pot/
  stack overlaps for 3-max (only #5 for HU at ≥1400).
- **CSP/console:** header `default-src 'self'; style-src 'self'; script-src 'self'…`; a
  `securitypolicyviolation` + `error` listener installed before load recorded 0 events across the full
  flow (inline `style.width`/`setProperty` via CSSOM are allowed).
- **Displayed values:** every number shown traced to an API field; the only UI constants are labels,
  "(server limit 90 s)" and formatting.

## Out-of-scope observations (API/scoring, not UI; not counted)

- Flop/turn IP after a check: legal actions are `CHECK, RAISE 33` — the first bet is labelled RAISE by the backend.
- Grade/score coupling looks odd: 3-max SB fold score 54.5 graded "Blunder"; turn check score 0 graded "Mistake".
