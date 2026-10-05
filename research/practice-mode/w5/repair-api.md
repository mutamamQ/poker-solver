# W5 repair-C — progress / API / server audit findings F1–F7

Source: `research/practice-mode/w5-audit/audit-progress-api.md`. Files changed (owned):
`src/poker_solver/practice/{api,progress,server}.py`, `tests/test_practice_progress.py`,
NEW `tests/test_practice_w5_api_repairs.py` (23 tests). Not committed.

## Fixes

| # | Fix |
|---|-----|
| F1 MAJOR | `practice-submit-play` records progress **only when the effective solve is the family default** (`find_spot` without `solve` → catalog `FAMILY_DEFAULT_SOLVE`); an override counts only if it yields the identical `params_hash` (e.g. `solve: {}` or the explicit default). Non-canonical overrides are still solved and scored ("what if" practice) but `result.progress = null`; result keys stay `{user, score, solved, progress}`, no new envelope keys. Rows keep storing `params_hash` (now always the canonical one). Documented in the `api.py` module docstring. |
| F2 | New `progress.RequestToken` (deadline + cancel, lock-guarded) bound to the dispatch thread via `request_scope`. `server._run_with_timeout` creates one per `/api/v4` request; on timeout it `cancel()`s **before** returning 504. `api._record` writes via `token.run_side_effect(...)`, so a cancelled/expired request writes nothing. Race at the deadline: if the write already committed, `cancel()` returns False and the server waits (≤5 s) for the result instead of reporting 504 for a recorded attempt. The orphaned solve itself still runs to completion (CFR is not interruptible); it only warms the solve cache. |
| F3 | Permanent `_STORE_FAILED` latch replaced by `_STORE_RETRY_AT`: a failed open is retried after `STORE_RETRY_S = 30` s (monotonic clock); `set_progress_store(None)` resets it. |
| F4 | `_PracticeHTTPServer(ThreadingHTTPServer)` with `request_queue_size = REQUEST_QUEUE_SIZE = 64`, `daemon_threads = True`. |
| F5 | `api._str` and `progress._text` reject non-UTF-8-encodable strings (lone surrogates) with `"<field>: invalid string encoding"`; store-error 400s are now the generic `"progress store error"` (detail goes to the log); server maps `UnicodeError` to `"malformed JSON: invalid string encoding"` / `"invalid string encoding"`, never codec text. |
| F6 | `_SPOT_SQL` rewritten: a CTE computes `MIN(id)` and `MAX(id)` per spot, then joins those rows. `last_score/last_grade/last_at/family/street/game_type` all come from the MAX(id) row and `first_at` from the MIN(id) row. |
| F7 | `ProgressStore` records `(st_dev, st_ino)` on open, and `_ensure_file_locked()` runs before every read and write. If the file is gone or has a different inode, the store closes the connection, deletes any stale `-wal`/`-shm` when the main file is gone, reopens and migrates, and increments `reopen_count`. `:memory:` stores are exempt. |

Envelope invariants are unchanged: a 200 is exactly `{version, operation, result, provenance}` and a 400 is exactly `{error}`. Both are asserted in the new tests.

## Tests
`tests/test_practice_progress.py`: `SOLVE` changed from 30 iterations to 200, which equals the kuhn-intro family default. Without that, those tests would be exercising the F1 non-recording path. No other changes in that file.

`tests/test_practice_w5_api_repairs.py` reproduces each audit repro:
- F1: iterations=1 forge → `progress` null, absent from leaderboard. Explicit default and `{}` still count. Stored params_hash is canonical. The HTTP path is covered too.
- F2: token semantics, a cancelled token skips the write, and a real HTTP 504 run (POKER_PRACTICE_TIMEOUT=0.3, solve held until after the 504) leaves 0 rows. An on-time submit still records.
- F3: unwritable → fixed dir. Nothing reopens inside the backoff window; it recovers after the backoff. Uses a mocked monotonic clock.
- F4: `request_queue_size == 64`. 64 concurrent clients behind a barrier all get 200.
- F5: lone surrogates in four ops over HTTP give a generic 400. An invalid-UTF-8 body gives a generic 400. Store-level validation is covered.
- F6: the backwards-timestamp repro.
- F7: delete → recreate (also verified after a "restart"), replace → reopen, an unchanged file never reopens, and `:memory:` still works.

Results (run per file):
- test_practice_progress.py: 32 passed
- test_practice_w5_api_repairs.py: 23 passed
- test_practice_api.py: 37 passed
- test_practice_cli_smoke.py: 28 passed
- test_practice_w3_regressions.py: 19 passed
- test_practice_ui.py: 17 passed
- test_practice_ui_w4.py: **12 passed, 1 failed**. `test_live_submit_then_progress_shows_attempt` submits with `solve: {"iterations": 30}` and expects a recorded attempt. That is exactly the F1 forging path, so the failure is the intended behaviour change. The test is outside my ownership. Fix needed (one line in that test): drop `"solve": solve` from the submit, or use `{"iterations": 200}`, which is the kuhn default.

## Notes for UI owner
`web/app.js` already handles `progress: null` (`applySubmitProgress` reloads the panels). When the iterations override is set, the UI could show a hint like "custom solve, not recorded". No change is required for correctness.
