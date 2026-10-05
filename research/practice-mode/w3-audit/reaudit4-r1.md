VERDICT: CLEAN

# W3 re-audit round 4, R1 (no hardcoded answers), commit 40a520c (feat/practice-mode)

No R1 findings reproduced.

## 1. Diff 13ddaa9..40a520c (src, web)
`git diff --stat 13ddaa9 40a520c -- src web`: 2 files, +14 lines.
- `src/poker_solver/practice/server.py` (+12): a `parse_request` override that skips up to 8 leading empty
  lines (RFC 9112 2.2), and a `send_error` fix that sets `request_version` to `protocol_version` when it is still
  HTTP/0.9. Both are HTTP framing only. They contain no strategy, Q, score or grade data and leave dispatch untouched.
- `web/style.css` (+2): two media queries for the topbar and sidebar layout. Layout only.
The diff introduces no literals, tables or answer data.

## 2. Tests
`.venv/bin/python -m pytest -q tests/test_practice_no_hardcode.py tests/test_practice_w3_regressions.py`
-> `26 passed in 19.99s`.

## 3. Live check on http://127.0.0.1:7777/api/v4
`practice-list-spots` returned 36 spots: 12 kuhn-intro, 12 river-oop-bet-or-check and 12 river-ip-facing-bet.

`practice-solve-spot` with vanilla-cfr at iterations 5 and 300:

| spot_id | it | params_hash | strategy (check/bet) | Q (check/bet) |
|---|---|---|---|---|
| kuhn-intro/820b58289136 | 5 | c0cc24b479adc5fa… | 0.625 / 0.375 | -1.06618 / -1.7 |
| kuhn-intro/820b58289136 | 300 | e074865e909895b5… | 0.80303 / 0.19697 | -1.00052 / -1.09523 |
| river-oop-bet-or-check/e79981f9d62d | 5 | 3239d4cdab6aea96… | 0.51453 / 0.48547 | 64.2710 / 59.9 |
| river-oop-bet-or-check/e79981f9d62d | 300 | f9adb80dad85e443… | 0.08919 / 0.91081 | 54.9797 / 56.8387 |

For both spots, spot_id stayed the same across the two iteration counts, while strategy, action_values and
params_hash all differed. Provenance reports iterations of 5 and 300, and the entrypoints are
`kuhn_root+cfr.CFRSolver.train` and `river_root+cfr.CFRSolver.train`.

`practice-submit-play` (iterations 300). I recomputed each result from the returned Q values using the formulas in DESIGN section 5:
- River e799…, pure check, pot 100: best_q 56.83867 (bet 33), chosen 54.97966. The recomputed loss is 1.85901
  chips (1.859% pot), score 0 (check is min Q) and grade Inaccuracy. All match the server exactly, with a diff of 0.0.
- Kuhn 820b…, mix check 0.3 / bet 0.7, pot 2: chosen_q -1.06682 and loss 0.066294 (3.3147% pot). The recomputed score
  is 30.0 and the grade is Mistake. All match the server exactly, with a diff of 0.0.
- In both cases the Q values in the submit response equal the Q values from the separate 300-iteration solve call.

Note (not a finding): the submits returned in about 0.03 s, with provenance wall_time_s 5.84 s for the river spot. That
means the earlier runtime solve was reused from a params-keyed cache. The cache key includes the iteration count,
so this is not hardcoding.
