VERDICT: FINDINGS

# W3 re-audit round 2 — R3 (UI DOM contract + live browser E2E)

Auditor: fresh adversarial agent. Frozen scope: commit d37eec3 (web/index.html, web/app.js, web/style.css).
Browser: Playwright 1.63 / Chromium 1234 headless (venv /tmp/pwaudit) against the live server http://127.0.0.1:7777 (not restarted).
Integrity: the bytes served live for `/`, `/app.js` and `/style.css` have the same sha256 as `git show d37eec3:web/*` and as the working tree (65dcc1c6…, 326987ef…, 2f34223d…).
Scripts (outside repo): /tmp/pwaudit/r2_fixes.py, r2_more.py, r2_geom.py, r2_detail.py, r2_sticky.py, e2e_r2.py; logs r2_fixes.log, r2_geom.log.

Summary: all six round-1 repairs verified fixed in a real browser. Live E2E on one river spot and one Kuhn spot matched the API with 0 value diffs. There were no console errors in the normal flow. I found 2 new MINOR defects: one keyboard regression introduced by the F1 fix, and one mobile layout issue.

## Round-1 repair verification

| Item | Result | Evidence |
|---|---|---|
| F1 Enter after clicking an action button | **FIXED.** Click Bet (Kuhn), Check (river) or Bet 33 (river), then press Enter: each sends exactly one `practice-submit-play` with the clicked play, and the result panel appears. Clicking a size preset then pressing Enter also submits `bet 33`. Enter on `#next-spot` still does its native action (one solve, no submit). | screens-r2/01-f1-enter-after-click-1280.png |
| F2 aria-disabled on #action-size | **FIXED.** `getAttribute('aria-disabled')` is null. No element in the document has `aria-disabled`. `page.fill('#action-size','50')` now succeeds and auto-selects Bet 33. | r2_fixes.log |
| F3 iterations '1.5' / '2e2' | **FIXED.** `1.5`, `2e2`, `1e1`, `-3` and `0` each show "Iterations must be a positive integer." on both Re-solve and Submit, and no request is sent. ` 7 ` is trimmed and sends 7. `99999999` is sent, the server answers 400, the UI shows "Solve failed: solve.iterations must be <= 20000", and clearing the field and re-solving recovers. | screens-r2/03-f3-iter-1p5-1280.png, 03-f3-iter-2e2-1280.png, 05-iter-too-big-1280.png |
| F4 villain card backs | **FIXED.** Kuhn: 1 hero card, 1 villain back. River: 2 and 2. | screens-r2/04-f4-kuhn-intro-backs-1280.png, 04-f4-river-oop-bet-or-check-backs-1280.png |
| F5 overlap at 420/360 | **FIXED.** At ≤560 px the felt is a flex column. On the pre-submit river and Kuhn spots (scrollY=0), the generic overlap scan finds no intersections among villain, board cards, pot, hero, stacks, title and meta at 560, 420 or 360. A visual check of 11-river-pre-360x740.png confirms it. | screens-r2/11-river-pre-{420x900,360x740}.png, 21-spot-details-river-360.png |
| Spot-list rows on mobile | **FIXED.** Row heights are 69 px (scrollHeight 67) at 900/560/420/360 and 90 px at 1280. `#spot-list` is 260 px tall with its own scroll. | r2_geom.log, screens-r2/10-initial-360x740.png |

## Live E2E at 1280x800 (diff against a direct POST /api/v4 practice-submit-play with the same payload)

- **River** `river-oop-bet-or-check/e79981f9d62d`, play check. Pre-submit: board 5♦3♠9♥2♠4♣, hero 6♦7♦, pot 100, stacks P0 (Hero) 200 / P1 200, actions Check / Bet 33, no `%` in body text. Post-submit: score 0, grade Inaccuracy, EV loss "2.742 chips (2.74% pot)", 2 mix segments and 2 legend items, 4 range rows (hand + text), 2 Q rows (label + q to 3dp), feedback, provenance (iterations 200, params_hash 6741d37f…09ab9 full via data-full-hash, algorithm, backend, entrypoint, solver_version, nash_conv to 6dp, seed "none"). **0 diffs.** The harness flagged one grade diff, but it was only `innerText` picking up CSS `text-transform: uppercase`. textContent is "Inaccuracy".
- **River with iterations 5 + Re-solve**: the request carries `solve:{iterations:5}`. The UI shows iterations 5 and params_hash 3239d4cd… (changed). 0 diffs.
- **River bet with an off-tree size of 50**: the API returns size_mapped=true, mapped Bet 33, score 100, Perfect, 0.000. The DOM is identical and adds "(size mapped to Bet 33)". The Q table "yours"/"best" tags both sit on Bet 33. screens-r2/31-river-bet50-result-1280.png.
- **Kuhn** `kuhn-intro/820b58289136` (keyboard `c` + Enter): board empty, hero J, pot 2, stacks 1/1, no size row. Result Perfect with 3 range rows. **0 diffs.**
- Console/pageerror were empty across all E2E and geometry runs at all 5 widths. The single exception was the browser's own "Failed to load resource: 400" line during the deliberate iterations=99999999 test, which is expected and handled in the UI.
- There is no horizontal overflow at any width (scrollWidth == clientWidth at 1280/900/560/420/360).

## Overlap scan (1280, 900, 560, 420, 360; initial, river pre/post, Kuhn pre/post)

The scan compared bounding boxes of about 40 element classes, clipped to overflow ancestors. None of the raw hits is a visible overlap:
- `#seat-hero` vs the `.history-row` box (12 px, 1280/900): the history row is a full-width box whose content (the "Action" label and step pill) ends at x≈434. The hero seat sits at x≈687-893, so the overlap is empty box area, and a visual check of 21-spot-details-river-1280.png confirmed it.
- `.range-hand` (120 px min-width, in a 96/80 px column) vs the bar cell: the actual cards end at x+59. Measured card-to-bar intersection is 0 px² on every row.
- The topbar hits in post-submit states come from the page being scrolled under the sticky header. That is covered by F-B below.

## FINDINGS

### F-A — MINOR (keyboard regression introduced by the F1 fix) — Enter on a focused, unselected action button submits the *previously selected* action
- Location: web/app.js:605-611 (`onKey`). Since d37eec3, Enter on any `.action-btn` calls `ev.preventDefault(); submitPlay()`. preventDefault suppresses the native button click, so the focused button is never activated and whatever `state.selectedAction` holds is submitted.
- Repro (1280x800): select `river-oop-bet-or-check/e79981f9d62d` and click **Check**. Press **Tab** (focus moves to "Bet 33"; `document.activeElement.textContent == "Bet 33"`, selected is still ["Check"]). Press **Enter**.
- Expected: Enter on the focused "Bet 33" button activates it (selects Bet 33) and submits Bet 33, or at least does not submit a different action.
- Actual: the request is `play: {kind: "check", amount: 0}`, and the result is graded as Check (Inaccuracy, 2.742 EV loss). Reproduced both with `locator.focus()` and with a real Tab keypress (r2_more.py output: `F1g(Tab) submitted: [{'kind': 'check', 'amount': 0}]`).
- Related inconsistency: with *no* prior selection, focusing Bet 33 and pressing Enter only selects it. Submit is disabled, so preventDefault never fires, the native click runs, and nothing is submitted (`F1f … result False`). The same key on the same button either selects or submits depending on hidden state.
- Screenshot: research/practice-mode/w3-audit/screens-r2/02-f1g-enter-on-bet-submits-check-1280.png

### F-B — MINOR — At 360 px the sticky topbar wraps to 4 rows and permanently covers ~25% of the viewport
- Location: web/style.css:183-197 (`.topbar { position: sticky; top: 0; z-index: 50; flex-wrap: wrap; … }`). The ≤560 px media block (style.css:1007-1027, 1071-1075) only reduces padding: it does not unstick the bar or compact it, and it keeps the `.kbd-hint` line even on touch widths.
- Repro: use a 360x740 viewport, select `river-oop-bet-or-check/e79981f9d62d`, and scroll so the spot panel is at the top. `.topbar` measures 187 px tall (25.3% of 740) with 4 wrapped rows (title+Family / Iterations / Re-solve / keyboard hint) and stays pinned. At 420x900 and 560x900 it is 138 px (15%). Content scrolls underneath it: in the post-submit 360 screenshot the topbar covers the villain seat and board cards, and the geometry scan reports `label.topbar-field[Iterations]` over all 5 board cards and `.kbd-hint` over the hero cards (r2_geom.log "360-river-post").
- Expected: on mobile the header should not consume a quarter of the screen over the table, for example by not being sticky at ≤560 px, or by being compacted and hiding the keyboard hint on narrow screens.
- Actual: only ~550 px of the 740 px viewport shows content, and the board and hero cards slide under a translucent bar while scrolling. All values are still reachable by scrolling, so this is minor.
- Screenshots: research/practice-mode/w3-audit/screens-r2/30-sticky-topbar-scrolled-360x740.png, 12-river-post-360x740.png

## Notes (not findings)
- Grade casing: the DOM textContent is the API string. Upper case is CSS only.
- `practice-solve-spot` still sends the full strategy to the browser before submit, as noted in round 1. The W2 contract permits this, and nothing is rendered before submit (no `%` in body text).
- Submit and Next spot look tight on 360 px (vision check), but there is no overlap. Cosmetic only, not reported.
