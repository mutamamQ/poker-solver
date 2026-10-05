# W4 task C — persisted progress tracker + disk solve cache wiring

## Files
- NEW `src/poker_solver/practice/progress.py` — `ProgressStore` (SQLite).
- MOD `src/poker_solver/practice/api.py` — progress recording, 2 new ops, CLI, disk-cache wiring.
- NEW `tests/test_practice_progress.py` — 32 tests.
- MOD `tests/test_practice_cli_smoke.py` (not in my ownership list, but forced by the contract):
  two exact-set assertions updated — `PRACTICE_OPERATIONS` now also contains
  `practice-progress`/`practice-leaderboard`, and the submit result key set gains `progress`.
  No other existing test changed; `test_practice_api.py` and `test_practice_w3_regressions.py` untouched.

## Design
- Storage: one `attempts` row per scored submit (user, spot_id, family, street, game_type, score,
  grade, ev_loss_pct, params_hash, ts). All aggregates (attempts, best = MAX, last = latest row id,
  first_at/last_at, totals, leaderboard) are computed in SQL at read time — no derived state to drift.
- `ProgressStore(path)`: one connection `check_same_thread=False`, guarded by a `threading.Lock`;
  `journal_mode=WAL`, `busy_timeout=10s`, autocommit; `schema_migrations(version, applied_at)` table with
  ordered migration list (`SCHEMA_VERSION = 1`); refuses DBs newer than supported. Parameterized SQL only
  (the one `.format` inserts a constant fragment, never user data).
- `from_env()`: `$POKER_PRACTICE_DATA_DIR/progress.sqlite3`, else
  `~/.local/share/poker-solver/practice/progress.sqlite3`.
- Timestamps: fixed-width ISO-8601 UTC `YYYY-MM-DDTHH:MM:SS.ffffffZ` (lexical order = chronological).
- api.py opens the store lazily on first use (import never touches disk); `set_progress_store(store|None)`
  exposed for tests/embedding.
- Fail-soft: any store open/record exception -> logged, `result.progress = null`, submit still 200.
  `practice-progress`/`practice-leaderboard` with an unavailable store raise `ValueError`
  ("progress store unavailable" -> HTTP 400) since there is nothing to return.
- Scores recorded are only `score_play(solved, play)` of the real solve; clients cannot send a
  `progress`/`score` field (unknown keys rejected).
- User: `^[A-Za-z0-9_.-]{1,32}$` via `fullmatch` (rejects trailing newline), default `local`; invalid -> `ValueError`.
  Applies to submit (previously only non-empty string) and progress.
- `practice-progress` `{user?, spot_id?}` -> `{user, totals:{attempts, spots_attempted, avg_best_score,
  avg_last_score}, spots:[...]}`; averages are `null` when the user has no attempts (decision: avoid a fake 0).
- `practice-leaderboard` `{limit? 1..100 = 20, family?}` -> `{entries:[{rank, user, spots_attempted, attempts,
  avg_best_score, total_best_score}]}`; best per (user, spot) within the family filter; order
  total_best desc, avg_best desc, user asc; ranks are 1..n positional (full ties still get distinct ranks,
  ordered by user).
- Both new ops: provenance `null`, envelope unchanged.
- Disk solve cache: `_ADAPTER = SolverAdapter(cache=_build_cache())`; lazy import of
  `solve_cache.DiskSolveCache.from_env()`; ImportError -> info log + dict, other errors -> warning + dict.
- CLI: `progress [--user U] [--spot-id S]`, `leaderboard [--limit N] [--family F]`; JSON on stdout,
  exit 2 on ValueError; list/solve/submit unchanged.

## Tests (tests/test_practice_progress.py)
Real kuhn submits through `dispatch_v4` (record + best/last/first/last_at), default user, 9 invalid users
(submit + progress, nothing recorded), store-record failure and store-unavailable -> progress null but
submit OK, payload validation for both ops, client-sent `progress` rejected, totals/best/last math with
fixed timestamps, leaderboard ordering + ties + limit + family filter, leaderboard from real submits,
persistence across instances + schema version, SQL-injection strings, from_env paths, concurrency
(8 threads x 25 writes over 2 connections to one WAL file -> 200 attempts), CLI, HTTP smoke via `make_server`
(submit/progress/leaderboard 200, invalid user 400).

## Results
See summary below (filled in after the full run).

- `tests/test_practice_progress.py`: 32 passed.
- Practice set (progress + api + w3_regressions + cli_smoke + solve_cache): 152 passed.
- Full suite `.venv/bin/python -m pytest -q`: **1058 passed** in 392 s (baseline 1026; solve_cache.py from
  task B landed during the run, so its tests may or may not be in that count — re-run after all W4 tasks).
- With task B's module present, `practice.api._ADAPTER._cache` is a `DiskSolveCache` (verified).
- CLI manual smoke (temp data dir): submit -> progress entry, `progress --user`, `leaderboard`, `--limit 0` -> rc 2.
