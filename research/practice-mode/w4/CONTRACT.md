# W4 shared contract (orchestrator-authored, binding for all W4 tasks)

Repo /home/genomix-node/poker-solver, branch feat/practice-mode. Python: .venv/bin/python.
Baseline suite: 1026 passed. Hard rule R1: every strategy / Q / range strategy / score / grade is computed
at runtime by the real solver. NO hardcoded answers, NO committed pre-solved cache files.

## Families (task A owns catalog/models/adapter)
New families, all solver-generated (names fixed):
- `preflop-hu-open`    backend `nplayer-preflop`, game_type `heads-up`, street `preflop` (2 players)
- `preflop-3max-open`  backend `nplayer-preflop`, game_type `3-max`,    street `preflop` (3 players)
- `flop-cbet`          backend `allstreet`,       game_type `heads-up`, street `flop`
- `turn-barrel`        backend `multistreet`,     game_type `heads-up`, street `turn`
Existing: `kuhn-intro`, `river-oop-bet-or-check`, `river-ip-facing-bet` (unchanged ids).
Spot JSON keeps all current keys (`family, backend, game_type, street, board, hero_seat, villain_seats,
ranges, pot, stacks, action_history, bet_sizes, hero_hand, solve, spot_id, params_hash, board_str,
hero_hand_str, label`). 3-max: `villain_seats` has 2 entries, `stacks` 3 entries.
Default solve per family may differ (family default iterations); cold solve budget <= 20 s each on
this host at the family default; flop/turn are NOT dropped for speed (the disk cache makes repeats instant).

## Persistent solve cache (task B owns practice/solve_cache.py)
- `DiskSolveCache(directory)` implements `MutableMapping[str, SolvedSpot]`, keyed by full `params_hash`.
- `DiskSolveCache.from_env()` -> directory `$POKER_PRACTICE_CACHE_DIR` or `~/.cache/poker-solver/practice`.
- One JSON file per key, atomic write (tmp + os.replace), file records schema version + solver_version;
  mismatched/corrupt files are ignored (treated as miss) and removed. Loaded SolvedSpot must be equal
  (field-by-field, floats exact) to the one saved. Memory LRU layer in front is allowed.
- CLI: `python -m poker_solver.practice.solve_cache warm [--families f1,f2] [--limit N]` pre-solves via
  the real SolverAdapter; `stats`; `clear`.

## Progress tracker (task C owns practice/progress.py + practice/api.py)
- SQLite store `ProgressStore(path)`; `ProgressStore.from_env()` -> `$POKER_PRACTICE_DATA_DIR/progress.sqlite3`
  default `~/.local/share/poker-solver/practice/progress.sqlite3`. Thread-safe, WAL, fail-soft.
- user id regex `^[A-Za-z0-9_.-]{1,32}$`, default "local".
- `practice-submit-play` records an attempt (spot_id, family, street, game_type, score, grade,
  ev_loss_pct, params_hash, ts) and its result gains `"progress": <spot entry after update>`
  (null if recording failed; never fails the submit).
- New v4 operations (already allowed in api_v4 by the orchestrator):
  - `practice-progress` payload `{user?: str, spot_id?: str}` ->
    result `{user, totals: {attempts, spots_attempted, avg_best_score, avg_last_score},
             spots: [{spot_id, family, street, game_type, attempts, best_score, last_score,
                      last_grade, first_at, last_at}]}`  (ISO-8601 UTC strings), provenance null.
  - `practice-leaderboard` payload `{limit?: int 1..100 = 20, family?: str}` ->
    result `{entries: [{rank, user, spots_attempted, attempts, avg_best_score, total_best_score}]}`,
    provenance null. Ranking: total_best_score desc, then avg_best_score desc, then user asc.
- CLI: `python -m poker_solver.practice.api progress [--user U]` and `leaderboard [--limit N] [--family F]`.
- `practice/api.py` builds `_ADAPTER = SolverAdapter(cache=<DiskSolveCache.from_env()>)` falling back to an
  in-memory dict if the cache module/dir is unavailable (fail-soft, logged).

## UI (task D owns web/*)
- Spot list gets street + game-type filters (values from spot JSON), 3-max villain display.
- Progress panel `#progress-panel` (totals + per-spot best/last/attempts, best-score badge in spot list)
  and leaderboard panel `#leaderboard-panel`; user name input `#user-input` persisted in localStorage
  and sent as `user` on submit/progress. All values from API responses only.
- Long solves: visible "solving…" state with elapsed-seconds counter; server timeout is 90 s.

## Tests
`tests/conftest.py` (orchestrator) points POKER_PRACTICE_CACHE_DIR and POKER_PRACTICE_DATA_DIR at a
per-session temp dir, so tests never touch ~/.cache or ~/.local. Do not write to the home dirs in tests.
