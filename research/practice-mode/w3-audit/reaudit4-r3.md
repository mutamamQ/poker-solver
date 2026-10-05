VERDICT: CLEAN

# W3 re-audit round 4 — R3 (UI final verification)

- **Auditor:** fresh adversarial agent.
- **Frozen scope:** commit 40a520c (web/index.html, web/app.js, web/style.css).
- **Browser:** Playwright with headless Chromium 1234 (venv /tmp/pwaudit), run against the live server http://127.0.0.1:7777. The server was not restarted.
- **Integrity:** the live bytes match `git show 40a520c:web/*`. sha256 prefixes: index.html 65dcc1c690d5, app.js 110e35253f49, style.css 8a46b183d082. `git status web/` is clean.
- **Change since 13ddaa9:** only style.css:1078-1079, which adds two media queries.
- **Scripts** (outside the repo, each with a matching .log): /tmp/pwaudit/r4_sticky.py, r4_sticky2.py, r4_scrolly.py, e2e_r4.py, r4_fixes.py, r4_geom.py, r4_detail.py.
- **Screenshots:** research/practice-mode/w3-audit/screens-r4/.

## F-C repair verification (style.css:1078-1079): FIXED

**Computed styles** (r4_sticky.log):

| Width | `.topbar` position | Topbar height | flex-wrap | `.sidebar` top (CSS) |
|---|---|---|---|---|
| 1000 / 1024 | static | 93.6 (wraps to 2 lines, harmless while static) | wrap | 0px |
| 1090 / 1100 | static | 59.3 | wrap | 0px |
| 1101 / 1280 / 1600 | **sticky** | **60.0 exactly** | **nowrap** | **60px** |

At 1101+ the sidebar's measured top is 60.0, which equals the topbar bottom of 60.0, so there is zero overlap. The old 3 px overlap at 1280 is gone.

**Scroll by 400 px** with a river result displayed, so the document is about 1800 px tall (r4_sticky2b.log, r4_scrolly.log). I confirmed scrollY=400 with both `scrollTo` and a real mouse wheel over main. The topbar bottom and the sidebar top below are the same reading at each width.

| Width | Topbar bottom / sidebar top | "Spots" h2 top | First spot row | `elementFromPoint` hits |
|---|---|---|---|---|
| 1000 / 1024 / 1090 | topbar scrolled off (bottom −306 / −306 / −341); sidebar top 0 | 17 | 86.8–176.9 | h2 → panel-title, row → SPOT |
| 1101 / 1280 / 1600 | 60 / 60 | 77 | 146.8–236.9 | h2 → panel-title, row → SPOT at top, middle and bottom |

In every case, neither the heading nor the first row is under the topbar. Screenshots: `01-scroll400-{1000,1024,1090,1101,1280,1600}x800.png`, checked visually at 1024 and 1280.

**Sidebar's own scroll:** I wheeled the sidebar by 120 px at 1101+. Its content is clipped at the sidebar's own top edge (y=60), which is normal internal scrolling. The topbar does not cover the sidebar box. The last spot item is reachable at every width (bottom 783 against a sidebar bottom of 800).

**Topbar clipping/overflow at 1101 and 1280:**

- topbar scrollWidth equals clientWidth (1101/1101, 1280/1280), and scrollHeight 59 equals clientHeight 59.
- No descendant's box extends outside the topbar box (`outside: []`).
- All 5 children sit on one row with tops between 10 and 19 px and bottoms at 49 px or less.
- At 1101 the right-most child, `.kbd-hint`, spans 779–1081, leaving 20 px of padding to the 1101 edge.
- A visual check of `02-topbar-1101x800.png` showed nothing clipped or truncated. `02-topbar-1280x800.png` is also attached.
- `documentElement` has no horizontal overflow at any of the 7 widths tested: 1000, 1024, 1090, 1100, 1101, 1280 and 1600.

**Measurement note:** in my first harness pass, some readings showed scrollY=11 instead of 400. A dedicated re-measurement (r4_scrolly.log) was stable at 400 synchronously and over 800 ms, 4 times out of 4 at 1024 and at 1280. The app contains no `scrollTo`/`scrollIntoView` calls, and the computed `scroll-behavior` is auto. The odd readings were a harness timing artifact. This is not a finding.

## Live E2E at 1280x800, diffed against a direct POST /api/v4 practice-submit-play using the captured payload (r4_e2e.log)

- **River** `river-oop-bet-or-check/e79981f9d62d`, play check:
  - Table: board 5♦3♠9♥2♠4♣, hero 6♦7♦, pot 100, stacks 200/200, actions Check / Bet 33. There is no `%` in the body before submit.
  - Result: 0, Inaccuracy, "2.742 chips (2.74% pot)". Mix and legend: Check 5.4% / Bet 33 94.6%. Q: 54.084 / 56.825. Plus 4 range rows, the feedback text and all provenance fields.
  - **Table diffs [] and result diffs [].**
- **River with iterations=5 and Re-solve:** the payload carries `solve:{iterations:5}`, the UI shows iterations 5 and the new params_hash 3239d4cd…. **Diffs [].**
- **Kuhn** `kuhn-intro/820b58289136`, submitted with the `c` key then Enter:
  - Table: J, no board, pot 2, stacks 1/1, Check / Bet, no size row.
  - Result: 100, Perfect, mix 82.0/18.0, 3 range rows.
  - **Table diffs [] and result diffs [].**

## Enter-key behaviour from round 3 (r4_fixes.log): all still pass

| Case | Result |
|---|---|
| Click Check, Tab to Bet 33, Enter | one submit `{bet,33}` |
| Focused, unselected Bet 33 with no prior selection, Enter | `{bet,33}` |
| Bet 33 selected, Shift+Tab to Check, Enter | `{check}` |
| Kuhn: Tab to Bet, Enter | `{bet,0}` |
| Enter in #action-size after typing 47 | `{bet,47}`, server reply "(size mapped to Bet 33)" |
| Check selected, type 60, Enter | Bet 33 auto-selects, submits `{bet,60}` |
| `b`, type 80, Enter | `{bet,80}` |
| Size preset focused, Enter | `{bet,33}` |
| Enter on #submit-play | exactly one submit |
| Enter on #next-spot | only `practice-solve-spot` is sent |
| Enter after the result is shown | no extra submit |
| Space on an action | selects only |

- **Shortcut keys:** `f`/`c`/`b` work on Fold/Call and Check/Bet spots. `b` on Fold/Call does nothing, and `b` on a Check/Bet spot focuses #action-size. Typing `c` inside #iterations-input does not change the selection.

## Console, overlap and overflow at 1280 / 900 / 560 / 420 / 360 (r4_geom.log, r4_detail.log)

- **Console:** the console and pageerror logs were empty at every width and in every state (initial, river before and after submit, Kuhn before and after submit) and throughout the E2E and Enter runs.
- **Horizontal overflow:** scrollWidth equals clientWidth everywhere. The 420 result page also had 0 elements outside the viewport.
- **Overlap scan:** the generic bounding-box scan flags only the same box-only pairs as round 3:
  - `#seat-hero` against the full-width `.history-row` container
  - `.range-hand` (120 px min-width box) against the bar cell
  - at 1280 and 900 in the initial empty state only, `#spot-title` "Select a spot" against `#seat-villain`, overlapping by 2 px vertically
- **Measured visible intersections:** range card against mix bar is 0 px² on every row at all 5 widths, and hero seat against history children is 0 px². A visual check of `12-river-post-360x740.png` found no overlap and no overflow.

## Findings

None reproduced.

The vision review of the 360 px screenshot raised cosmetic opinions: a mid-identifier wrap of the long provenance entrypoint, an unlabeled third Q column, and low-contrast disabled buttons. These are design-level choices. They are not contract violations, they are not regressions in the frozen diff, and they are not layout defects, so they are not reported.
