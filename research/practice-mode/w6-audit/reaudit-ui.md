# W6 re-audit-2: live UI re-audit at 72f0053 (tag practice-mode-w5)

Auditor: fresh non-author, read-only. Worktree `/tmp/w6audit` (HEAD `72f0053`). Own server on `127.0.0.1:7796` with
`POKER_PRACTICE_CACHE_DIR=/tmp/w6a2/cache` and `POKER_PRACTICE_DATA_DIR=/tmp/w6a2/data`. Port 7777 was not touched,
and the server was stopped at the end. No source files were edited.

Method: Chromium over CDP. Keys were sent as real `Input.dispatchKeyEvent` events. Geometry comes from
`getBoundingClientRect`. API traffic was captured with a fetch wrapper installed before page load, which also
recorded `securitypolicyviolation`, `error` and `unhandledrejection` events.

Evidence is in `screens-ui/`: `shortcuts.json` (7 families × F/C/B/B/A), `layout.json` (2 spots × 6 widths),
`custom_iter_submit.json` and `3max-1400.png`.

## Prior findings 1–7

| # | Prior finding | Status | Evidence |
|---|---------------|--------|----------|
| 1 | MAJOR: F/C/B and size input dead on the 4 uppercase families | **FIXED** (one residual, see N1) | With focus blurred before each key, on preflop-hu `6db0bd5d4d67`, 3-max `a4b66447a35b` and `a99ed8603bf2`, flop `9a471ac7b613` and turn `b95c7dba968a`: `f`→Fold, `c`→Call 2/Check, `b`→Raise N, a 2nd `b`→Raise 30/40 (it cycles). Submit becomes enabled. Size row is visible, with presets `4,30` / `5,40` / `33`. Typing 12 and pressing Enter sends `{"kind":"RAISE","amount":12}` (original case). The API returns `size_mapped:true, mapped_action RAISE 5`, and the UI shows "(size mapped to Raise 5)". Legacy families still work: kuhn `c`/`b` and `f`/`c`, river-oop `c`/`b`, river-ip `f`/`c`. |
| 2 | MINOR: Best badge coloured by last grade | **FIXED** | User `w6a2ui` submitted Raise 5 (99.78, Perfect), then Fold (0, Blunder) on `a4b66447a35b`. Badge reads `Best 99.8`, class `best-badge` (no `grade-*`), colour `rgb(179,162,255)`, bg `rgba(124,92,255,0.12)`, title `Best score 99.8 · 2 attempts`. |
| 3 | MINOR: leaderboard "me" stale after user change | **FIXED** | Before the change: `['w6a2ui[me]']`. Right after `change` to `someoneelse`, with no Refresh: `['w6a2ui']`, and `#progress-user` shows `· someoneelse`. Switching back gives `['w6a2ui[me]']` immediately. |
| 4 | MINOR: progress table clipped at every width | **FIXED** | At 360/600/900/1100/1400/1600: `#progress-spots` scrollWidth equals clientWidth (294/510/820/704/1004/1194). `#leaderboard-table` is the same (304/520/820/704/1004/1194). 0 cells extend past the panel, 0 cells overflow, and page `scrollWidth == clientWidth` at every width. Cards mode is used at 360 and 600 (thead hidden; `::before` shows `"Spot"`, `"Tries"`, …). Progress and leaderboard panels stack with a 16 px gap and do not intersect. |
| 5 | NIT: HU villain seat overlaps `#spot-meta` ≥1400 px | **FIXED** | turn-barrel at 1400: seat top is 143.8, below the meta bottom of 120.3 (0 intersection). At 1600 it is the same. 3-max: 0 intersections among seats, meta, title, board, pot, hero and solve-status at all 6 widths. No action-button or topbar overlaps. |
| 6 | NIT: focus dropped to `<body>` after submit | **FIXED** | After a successful submit, focus is on `#next-spot`. Enter on it solves the next spot (`flop-cbet/c3994d4975b4`) and focus lands on the first `.action-btn`. Submit HTTP 500 → focus on `#submit-play`. Solve network failure → focus on `#resolve-btn`. |
| 7 | NIT: raw uppercase labels | **FIXED** (one residual, see N2) | Buttons show `Fold, Call 2, Raise 5, Raise 40`. History shows `Fold` (3-max SB) and `Check`, `Raise 33`. Legend shows `Fold 0.0% … Raise 40 96.3%`. Q table shows `Fold/Call 2/Raise 5/Raise 40`. Range text is humanized. The request still sends `RAISE`/`FOLD`/`CALL`, and the API response kinds are unchanged (uppercase). |

## New / residual findings (reproduced)

| # | Severity | Finding |
|---|----------|---------|
| N1 | MINOR | After `B`, focus is trapped in `#action-size`, so F/C/B no longer work. The advertised "B again cycles Raise 5 → Raise 40" can't be reached by keyboard. |
| N2 | NIT | `#feedback-text` still shows raw API tokens (`RAISE[40]`, `bet[33]`) next to humanized labels. |
| N3 | NIT | A submit with a non-default Iterations override is silently not recorded (`progress: null`), and the UI gives no notice. |

No BLOCKER or MAJOR.

### N1. MINOR: the B shortcut moves focus into the size input, which disables all later shortcuts

Steps: load the page and pick `preflop-3max-open/a99ed8603bf2`. Blur focus once, then send real key events
`b`, `b`, `c`, `f` with no blur in between.

Measured after each key, as (selected button, `document.activeElement`):
`b`→(Raise 5, `#action-size`), `b`→(Raise 5, `#action-size`), `c`→(Raise 5, `#action-size`),
`f`→(Raise 5, `#action-size`).

`onKey` returns early for typing targets (`isTypingTarget(input)`), and the `b` handler itself focuses `#action-size`
(app.js 1087–1088). After one `B`:
- the second `B` doesn't cycle to Raise 40, even though repair-ui.md and the W5 table say "B: Raise 5 → Raise 40 → Raise 5";
- C and F do nothing, and since there is no visible feedback, the key presses are simply lost.

The only ways out are Tab (to `.size-preset`; then `c` → Call 2 works), clicking, or Esc+click. Cycling does work
if focus is removed between presses (`shortcuts.json`, blurred: `b`,`b` → Raise 30 / Raise 40).

The same trap applies to the legacy `river-oop-bet-or-check/e79981f9d62d` (`b`,`c`,`f` → stays `Bet 33`, focus
`#action-size`), where it predates W5. W5 extends it to the four new families and advertises cycling that the
trap prevents. The hint "F fold · C check/call · B bet/raise" is accurate only until B is pressed.

### N2. NIT: feedback sentence keeps raw kind tokens

Steps: on `preflop-3max-open/a4b66447a35b`, press B and Enter. `#feedback-text` =
`Solver: RAISE[40] 96.3%, RAISE[5] 3.6%, CALL[2] 0.1%, FOLD 0.0%. You: RAISE[5]. … Best EV action: RAISE[40] …`.
The legend right below says `Raise 40 96.3%`, and the appended note says `(size mapped to Raise 5)`. On river-oop the
sentence reads `Solver: bet[33] 92.8%, check 7.2%`.

The string comes verbatim from `score.feedback` in the API, so nothing is fabricated. It is only the one remaining
place where finding 7's inconsistent labels survive: within one panel the kinds appear as uppercase, lowercase and
humanized.

### N3. NIT: custom-iterations submit is silently not recorded

Steps: user `w6a2ui`, set Iterations to `150`, pick `river-oop-bet-or-check/e79981f9d62d` (family default 200),
then press `c` and Enter.

- Request: `solve:{iterations:150}`.
- API: HTTP 200, `result.progress: null`, provenance `iterations 150`.
- UI: the result renders normally. Progress totals are unchanged before and after (`Attempts 4 · Spots tried 3 ·
  Avg best 80.8 · Avg last 47.6`), and no Best badge appears on the spot.
- `#error-message`, `#solve-status` and `#progress-status` are all empty. `document.body.innerText` contains no
  "record", "not saved", "tracked" or "override" text.

So null is handled gracefully (no error, no crash), but the user isn't told the attempt doesn't count.

Control: Iterations `300` on preflop-hu-open (equal to that family's default of 300) is recorded, with progress
returned and attempts 3→4. That is correct, but equally unexplained.

## Regression hunt: verified, no finding

- **All-in spots / pseudo-raise:**
  - Solved all 72 catalog spots via the API. 0 have a `RAISE` whose amount equals a `CALL` amount, in `legal_actions`, `strategy` or any `range_strategy` row.
  - No catalog spot under seeds 0–5 reaches an all-in node.
  - Backend all-in node (turn-barrel stacks 33/33, line CHECK, RAISE 33): the adapter gives `legal [FOLD 0, CALL 33]`. I stubbed that real solve into the UI's solve response.
  - The UI then shows exactly `Fold`, `Call 33`, with size row hidden and presets `[]`. `b` and `a` select nothing; `c` → Call 33. History is `Check, Raise 33`, stacks `33/33`.
- **3-max layout/values:**
  - `a99ed8603bf2`: felt `players-3`, villains `Villain (P0) · 40` and `Villain (P2) · 40`, `Hero (P1)`.
  - Pot `3`, stacks `P0 40 / P1 (Hero) 40 / P2 40`, history `Fold`. All equal the API spot.
- **Displayed values vs API:** 3-max custom-size submit (`77d9d76f7f14`):
  - score `77.8` (77.7559), Blunder, `0.666 chips (22.20% pot)`;
  - Q `0.000/0.660/2.328/2.994` with `yours` on Raise 5 (mapped) and `best` on Raise 40 (= `best_action`);
  - mix-seg widths `0.005% / 0.0104697% / 0.0857737% / 99.8988%` = API probabilities × 100;
  - 3 range rows = API, 1 hero row.
  - No displayed number was absent from the API responses.
- **Error states** (fetch monkeypatched): submit 500 → "Submit failed: boom …", result hidden, submit re-enabled. Submit with
  non-JSON 200 → "Submit failed: Malformed API response". Solve network reject → "Solve failed: Failed to fetch", no
  buttons. Progress 500 / leaderboard reject → "Progress unavailable: …" / "Leaderboard unavailable: …",
  `.is-unavailable`, badges 0. Recovery on Refresh restores 4 badges. Iterations `abc` → "Iterations must be a
  positive integer.", no request. Iterations `99999999` → "Solve failed: solve.iterations must be <= 20000".
- **Focus/keyboard:** Tab from the active spot item to the first action button takes 24 presses (unchanged; acceptable now that
  post-submit and post-next focus are handled). Enter on a focused action button selects it and submits.
- **CSP/console:** header `default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'`.
  0 CSP violations and 0 JS errors or unhandled rejections across all flows.

## Out-of-scope observation (backend/perf, not UI; not counted)

When I warmed the cache with 4 concurrent cold `practice-solve-spot` calls on this host, all 8 `preflop-3max-open` spots
failed with HTTP 400: `solve exceeded the 60s budget after 3700–4750 of 5000 iterations`. Solved one at a time, they took
9.6–16.7 s each. A few users clicking cold 3-max spots at the same time would see "Solve failed: …".
