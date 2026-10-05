VERDICT: FINDINGS

# W3 re-audit round 3 — R3 (UI live browser)

Auditor: fresh adversarial agent. Frozen scope: commit 13ddaa9 (web/index.html, web/app.js, web/style.css).
Browser: Playwright / Chromium 1234 headless (venv /tmp/pwaudit), against the live server http://127.0.0.1:7777 (not restarted).
Integrity check: the bytes served live equal `git show 13ddaa9:web/*` and the working tree. The sha256 prefixes are index.html 65dcc1c690d5, app.js 110e35253f49 and style.css 87462ea8f2a4. `git status` shows no modification under web/.
Scripts (outside the repo, in /tmp/pwaudit): r3_fixes.py, r3_sticky.py, e2e_r3.py, r3_geom.py, r3_stale.py, r3_detail.py, r3_mid*.py, r3_wrap.py, r3_sel2.py. Each has a matching .log file.

Summary: both round-2 repairs are verified fixed. The live E2E run showed 0 value diffs against the API for the river spot and the Kuhn spot, covering the table and the result. There were no console errors at any of the 5 widths. Keyboard shortcuts and the stale-response guard work. I found one MINOR layout defect, which predates this commit and was not reported in round 2: at 901–1090 px the topbar wraps and covers the top of the sticky sidebar.

## Round-2 repair verification

| Item | Result | Evidence |
|---|---|---|
| F1 (F-A) Click Check, Tab to "Bet 33", Enter | **FIXED.** Focus lands on "Bet 33" and exactly one submit is sent: `{kind:"bet",amount:33}`. The result is graded as bet[33] (Perfect, 0.000), and the selected state moves to Bet 33. | r3_fixes.log F1a; screens-r3/01-f1-check-tab-enter-bet33-1280.png |
| Reverse case: Bet 33 selected, Shift+Tab to Check, Enter | **FIXED.** It submits `check`. | F1c |
| Enter on a focused, unselected action with no prior selection | **FIXED.** It submits `bet 33`. Previously it only selected the action. | F1b |
| Kuhn: click Check, Tab to Bet, Enter | It submits `bet 0`. | F1d |
| Enter in #action-size | **OK.** With Bet selected and 47 typed, Enter submits `bet 47`, and the server maps it to Bet 33 with "(size mapped to Bet 33)". With Check selected, typing 60 auto-selects Bet 33 and Enter submits `bet 60`. Pressing `b` focuses #action-size; typing 80 and pressing Enter submits `bet 80`. | F1e/F1f/F1g |
| Size preset focus + Enter (Check previously selected) | It submits `bet 33`. | F1h |
| Native buttons | Enter on #submit-play sends exactly one submit. Enter on #next-spot only solves the next spot (no submit). Enter on a disabled action after a submit sends nothing extra. Space on an action only selects it. | F1i–F1k |
| F2 (F-B) topbar at ≤900 px | **FIXED.** Computed `position: static` at 900/560/420/360 and `sticky` at 901/1280. After scrolling to #board-cards or #result-panel, the topbar sits fully above the viewport (for example top=-728 at 360x740). `elementFromPoint` at y=10..120 hits page content, not the topbar. | r3_sticky.log; screens-r3/02-f2-scrolled-board-cards-{360x740,420x900,560x900,900x800}.png |

## Live E2E at 1280x800 (diff against a direct POST /api/v4 practice-submit-play with the captured payload)

- **River** `river-oop-bet-or-check/e79981f9d62d`, play check:
  - Table: board 5♦3♠9♥2♠4♣, hero 6♦7♦, pot 100, stacks 200/200, actions Check / Bet 33. These match `solved.spot` and `legal_actions`. There is no `%` in the body text before submit.
  - Result: score 0, grade Inaccuracy, EV "2.742 chips (2.74% pot)". The mix segments and legend, 4 range rows, 2 Q rows, feedback, and all provenance keys (including the full params_hash, nash_conv to 6dp and seed "none") match.
  - **0 diffs** (table and result).
- **River, iterations 5 + Re-solve:** the payload carries `solve:{iterations:5}`. The UI shows iterations 5 and a new params_hash (3239d4cd…). **0 diffs.**
- **Kuhn** `kuhn-intro/820b58289136`, submitted with keyboard `c` + Enter:
  - Table: hero J, no board, pot 2, stacks 1/1, Check / Bet, no size row.
  - Result: Perfect, 3 range rows.
  - **0 diffs.**
- Console and pageerror output was empty in every run. There is no horizontal overflow at 1280/900/560/420/360 (scrollWidth == clientWidth).

## Keyboard shortcuts / stale guard
- On `river-ip-facing-bet` (Fold/Call): `f` selects Fold, `c` selects Call, and `b` does nothing because no bet/raise is legal. On the river OOP spot: `f` does nothing, `c` selects Check, and `b` selects Bet 33 and focuses #action-size. Typing `c` inside #iterations-input does not change the selection.
- Stale guard: I wrapped `fetch` so river responses are delayed by 4 s.
  - (a) Select river, then switch to Kuhn before the solve returns. The late river response is ignored: the Kuhn title, J card, Check/Bet buttons and spinner state are all intact.
  - (b) Submit on river, then switch to Kuhn before the submit returns. The late result is not rendered: the result panel stays hidden, Kuhn actions stay enabled, and there is no error.
  - Evidence: r3_stale.log, screens-r3/04-stale-guard-{solve,submit}-1280.png.

## Overlap scan (1280, 900, 560, 420, 360 × initial / river pre+post / Kuhn pre+post)
- At 560/420/360 the generic bounding-box scan reports 0 overlaps, except the `.range-hand` box vs the bar cell.
- At 1280/900 the only hits are box-only: `#seat-hero` vs the full-width `.history-row` box, and `.range-hand` (120 px min-width) vs the bar cell.
- I measured the intersections between visible content directly. Range card vs mix bar is **0 px²** on every row at all 5 widths. `#seat-hero` vs history-row children is **0 px²** (r3_detail.log). Neither is a visible overlap.

## FINDINGS

### F-C — MINOR — At 901–1090 px the wrapped sticky topbar covers the top ~38 px of the sticky sidebar
- Location: web/style.css:217-221 (`.sidebar { position: sticky; top: var(--topbar-h); max-height: calc(100vh - var(--topbar-h)); … }`, with `--topbar-h: 56px` at :77), together with web/style.css:183-197 (`.topbar { position: sticky; top: 0; z-index: 50; flex-wrap: wrap; … }`). The repair at :1077 only unsticks the topbar at ≤900 px.
- Cause: between 901 and 1090 px the topbar contents wrap onto two lines, so the bar is 94 px tall (measured by sweeping widths: 94 px at 901–1090, 59 px at ≥1091). The sidebar still sticks at a fixed 56 px, so 38 px of the sidebar sits under the opaque, z-index-50 topbar.
- Repro:
  1. Open the page at 1000x800 (or 1024x800).
  2. Select `river-oop-bet-or-check/e79981f9d62d`.
  3. Scroll the page by 38 px or more, or use the mouse wheel over the sidebar.
- Measured result: topbar bottom 93.6, sidebar top 55.6. `elementFromPoint` on the sidebar's "Spots" heading returns the topbar. While the sidebar scrolls, the first visible spot row is cut off under the bar: its family pill and the start of its label are hidden (r3_mid2.log, r3_mid3.log; confirmed by a visual check of the screenshot).
- At 1280 the same mechanism produces a negligible 3 px overlap (topbar 59 px vs top:56).
- Impact: the "Spots" heading and the top of the first visible spot row are hidden. Content is still reachable by scrolling the sidebar, and the last row is fully visible (bottom 783 < 800). Cosmetic and layout only, so MINOR.
- History: this predates 13ddaa9 (the code is unchanged since the wave-2 commit c9e01d0) and was not reported in round 2.
- Screenshots: research/practice-mode/w3-audit/screens-r3/03-sidebar-under-topbar-wheel-1024x800.png and 03-sidebar-under-topbar-1000x800-scroll400.png

## Notes (not findings)
- After submit, all action buttons are disabled. `.action-btn:disabled { box-shadow: none; opacity: .38 }` (style.css:640-645) removes the ring from the selected button, so Check and Bet 33 look alike visually (screens-r3/06-selected-after-submit-1280.png). `aria-pressed="true"` remains on the chosen button, and the Q table marks it "yours", so the information is still displayed. Cosmetic only.
- The grade's upper case is CSS `text-transform` only. Its textContent equals the API string.
