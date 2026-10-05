# W3 audit-3 — R3 UI/DOM contract + live end-to-end (real browser)

Auditor: fresh adversarial agent. Date: 2026-10-05. Target: commit 67c421f (manifest frozen at c9e01d0).
Browser: Chromium 1234 (Playwright 1.63 python, headless) against the LIVE server http://127.0.0.1:7777/ (not restarted).
Scripts used (outside repo): /tmp/pwaudit/e2e.py, e2e2.py, e2e3.py, geom.py; logs run1.log, run2c.log.

## VERDICT: FINDINGS (0 BLOCKER, 0 MAJOR, 5 MINOR)

The core R3 contract holds: all 20 required DOM IDs present exactly once. Every value shown after submit matched a direct
`practice-submit-play` call with the same payload. That covers score, grade, EV loss, mix segments and legend, every
range-row hand and percentage, Q rows, and provenance (iterations, params_hash, backend, algorithm, entrypoint,
solver_version). No strategy is shown before submit, there is no innerHTML, and no console errors appeared. The findings
below are all minor UX, accessibility or layout issues.

## Manifest / integrity
- `sha256sum -c` over all 21 manifest entries: all OK, including web/app.js, web/index.html and web/style.css.
- The bytes the live server serves for `/`, `/app.js` and `/style.css` hash to the same values as the manifest (65dcc1c6…, 72bf9097…, 1f7dbae1…).
- The task's "server.py" is `src/poker_solver/practice/server.py` (there is no top-level server.py). Its hash is OK (45206d90…).

## (1) DOM contract — PASS
I fetched `/` live and counted `id="…"`. Each of these appears exactly once: practice-app, spot-list, spot-status, spot-details,
board-cards, pot-value, stacks-list, action-history, hero-hand, action-controls, action-size, submit-play,
result-panel, score-value, grade-value, ev-loss-value, optimal-mix, range-strategy, provenance, error-message.
The extra IDs (iterations-input, resolve-btn, feedback-text, action-values, spot-filter) also appear once each.

## (2) Live E2E — results
| Step | Result |
|---|---|
| a. load | The list renders 36 spots, and the status reads "36 spots". |
| b. river spot `river-oop-bet-or-check/e79981f9d62d` | Board shows 5 glyph cards: 5♦ 3♠ 9♥ 2♠ 4♣. Hero shows 6♦ 7♦. Pot is 100. Stacks show P0 (Hero) 200 and P1 200. Buttons are Check and Bet 33, with the size row visible. No `%` text appears anywhere in the body before submit. |
| c/d/e. Check + submit | DOM shows score 0, grade Inaccuracy, EV loss "2.742 chips (2.74% pot)", 2 mix segments (Check 5.4%, Bet 33 94.6%), 4 range rows, 2 Q rows, iterations 200, params_hash 6741d37f…09ab9 (full hash in `data-full-hash`). The direct API call returns identical values. 0 diffs (the grade shows upper-case only through CSS `text-transform`; textContent is "Inaccuracy"). |
| f. Kuhn `kuhn-intro/820b58289136` (keyboard `c` + Enter) | Board is empty, hero shows J, pot 2, stacks 1/1. Result: score 100, Perfect, 0.000 EV loss, mix Check 82.0% / Bet 18.0%, 3 range rows (J/Q/K) with the hero row highlighted, iterations 200, hash 33b15134…. Matches the API with 0 diffs. |
| g. iterations=5 + Re-solve + submit | The request carries `solve:{iterations:5}`. Displayed iterations is 5. params_hash changed from 6741d37f… to 3239d4cd…. Matches the API. |
| h. keyboard | `f` selects Fold, `c` selects Check or Call, `b` selects Bet and focuses the size input. Enter submits when focus is on the body. On the facing-bet spot (Fold/Call only), `b` correctly does nothing. Console and pageerror stayed empty across all runs. |
| races | Two rapid spot clicks end with the last spot shown. Switching spot while a submit is in flight drops the stale submit result: no result panel appears, and the new spot renders correctly. |
| off-tree size | Typing 50 (and 5000) submits bet 50. The server maps it to bet 33, and the UI shows the server feedback plus "(size mapped to Bet 33)". Entering -1 or an empty size shows the client error "Enter a positive size." and sends no request. |
| responsive | No horizontal overflow at 420 px or 1280 px (scrollWidth equals clientWidth). |

## FINDINGS

### F1 — MINOR — Enter does not submit after mouse-selecting an action (contradicts the "Enter submit" hint)
- Location: web/app.js:600 (`if (!typing && ev.target && ev.target.tagName === "BUTTON") return;`) and index.html:23 (hint text).
- Repro: Select the Kuhn spot, then click (or focus) the **Bet** button. Press Enter, then press Enter again.
- Expected: Enter submits the selected play, as the topbar hint "Enter submit" says.
- Actual: Focus stays on the action button, so Enter only re-activates that button. The result panel never appears (log: `Enter on Bet button: selected ['Bet'] result False`, then `2nd Enter on button result False`). Enter submits only when focus is not on a button, which is not the case after the normal mouse flow.

### F2 — MINOR — The size input is marked `aria-disabled="true"` while it is enabled and is the intended entry point
- Location: web/app.js:365-367.
- Repro: Select any river spot (no action selected yet). The `#action-size` element is `disabled=false`, but `aria-disabled="true"`. Playwright's `page.fill("#action-size","50")` times out with "element is not enabled" (run2b.log). Typing into the input does work (app.js:630 auto-selects Bet), and the submit goes through.
- Expected: The accessibility state matches the real state. The input is editable, so `aria-disabled` should be false or absent.
- Actual: Assistive technology announces the size field as disabled, even though typing a size is a supported way to choose a bet.

### F3 — MINOR — A non-integer iterations value is silently truncated by the client
- Location: web/app.js:113-117 (`parseInt(raw, 10)`).
- Repro: Type `1.5` into the Iterations field, click Re-solve, pick an action and submit.
- Expected: Either an error ("must be a positive integer"; the error text already exists for 0 and -3), or the raw value is sent so the server can validate it.
- Actual: No error appears. The client sends `iterations: 1`, and provenance shows `iterations 1` (log: `prov iterations shown for 1.5: 1`). This is client-side alteration of user input. The displayed value still matches the API, so it is minor.

### F4 — MINOR — Villain is always drawn with 2 card backs, including Kuhn (1 card per player)
- Location: web/index.html:45 (two static `.card.back` spans). app.js never adjusts them.
- Repro: Select any `kuhn-intro/*` spot. Hero shows 1 card (from the API), but Villain shows 2 face-down cards.
- Evidence: screens/08-mobile-kuhn-presubmit-420x900.png, screens/04-kuhn-result-1280x800.png.
- Expected: The villain card count reflects the game (the hero_hand_str length or the backend).
- Actual: The client shows a fixed 2-card villain hand that does not come from the API. This is a small breach of "nothing invented client-side" (it is static chrome, not data).

### F5 — MINOR — Narrow-viewport table overlap (≤ 420 px)
- Location: web/style.css @media (max-width:560px) block (~L1007-1027). Seat and stack positioning do not account for the smaller felt.
- Repro: Use a 420x900 viewport, select `river-oop-bet-or-check/e79981f9d62d`, and let the deal animation settle. Measured bounding boxes (geom.py):
  - `#stacks-list` [276,607,376,658] overlaps the 5th board card 4♣ [269,649,303,697] (27×9 px). It also overlaps `#seat-villain` [131,571,289,636].
  - `#seat-villain` (top 571) overlaps `#spot-meta` (bottom 580), clipping the bottom of the "river-oop-bet-or-check · river" subtitle.
  - At 360x740 the stacks box also overlaps board cards 4 and 5.
  - At 560 px only the villain/meta overlap remains. At 900 and 1280 px there is no overlap.
- Evidence: screens/10-river-presubmit-settled-420x900.png, screens/10-river-presubmit-settled-360x740.png, screens/06-mobile-result-420x900.png.
- Expected: No element overlaps the board or text on mobile.
- Actual: There are small overlaps. All values stay readable, so this is minor.

## NOTES (not findings / not reproduced as defects)
- **XSS:** app.js never uses innerHTML. All API strings go through `textContent`. Class names derived from API values are sanitised (`actClass`, grade class regex). Clean.
- **Strategy before submit:** Nothing from `strategy`, `action_values` or `range_strategy` is rendered before submit, which I verified in the live DOM (no `%`, result panel hidden). However, `practice-solve-spot` returns the full strategy to the browser, and app.js keeps it in `state.solved`, so it can be seen in devtools or the network tab. The W2 contract allows this, but a strict "hidden until submit" rule would need a server-side split.
- **Client-side invention:** Apart from F4, every number comes from the response. Static labels ("First to act", "Hero (P#)" derived from hero_seat, "P#" seat names, "chips", "% pot", "none" for a null seed) are formatting only. The score is rounded to 0.1, `ev_loss` to 3 decimals and `nash_conv` to 6. params_hash is visually truncated to 16 characters, with the full value in `title` and `data-full-hash`.
- **Not UI defects:** The API itself returns "most-weighted alternative: bet[33]" identical to the best action, and score 0 alongside grade "Inaccuracy". The UI displays both faithfully. These are scoring-module questions for the backend auditors.
- **Vision false positive:** A vision check of the first screenshot (02, taken mid deal-animation) reported "only 1 board card". The DOM and settled screenshots show all 5 cards at opacity 1. Not a defect.
- **Sidebar scrolling:** On desktop the sidebar is sticky with internal scroll. On mobile `#spot-list` is capped at 260 px with its own scroll. This works, with no overflow.

## Screenshots (research/practice-mode/w3-audit/screens/)
- 01-initial-1280x800.png
- 02-river-presubmit-1280x800.png (mid deal-animation)
- 03-river-result-1280x800.png (full page)
- 04-kuhn-result-1280x800.png (full page)
- 05-mobile-initial-420x900.png
- 06-mobile-result-420x900.png
- 07-ip-facing-bet-presubmit-1280x800.png
- 08-mobile-kuhn-presubmit-420x900.png
- 09-mobile-kuhn-result-viewport-420x900.png
- 10-river-presubmit-settled-{1280x800,900x800,560x900,420x900,360x740}.png
