# Practice mode operations

These commands were verified at commit `5a3e61f` with `.venv/bin/python` from the repo root,
using temp `POKER_PRACTICE_CACHE_DIR` / `POKER_PRACTICE_DATA_DIR`. The output shown is from
those runs.

## Environment variables

| variable | used by | default | effect |
|---|---|---|---|
| `POKER_PRACTICE_CACHE_DIR` | `solve_cache.DiskSolveCache.from_env()`, which also backs the API adapter | `~/.cache/poker-solver/practice` | directory for persisted solves (one `<params_hash>.json` per solve). Ignored if empty |
| `POKER_PRACTICE_DATA_DIR` | `progress.ProgressStore.from_env()` | `~/.local/share/poker-solver/practice` | directory holding `progress.sqlite3` |
| `POKER_PRACTICE_TIMEOUT` | `server.py` | `90` | seconds before `POST /api/v4` answers `504 {"error":"solve timed out"}`. Non-positive or non-numeric values are ignored |
| `POKER_PRACTICE_WEB` | `server.py` | `<repo>/web` | static UI directory (`--web-dir` takes precedence) |
| `PYTHON` | `scripts/practice_smoke.sh`, `scripts/solver_eval.sh` | `<repo>/.venv/bin/python` | interpreter |

Both directories are read when the process starts. The progress store opens lazily on the first
progress/submit call. Separate from the server timeout, each adapter solve has its own budget of
60 s (`SolverAdapter(timeout_s=60)`). A solve that runs over it fails with
`solve exceeded the 60s budget ...` and no partial result is returned. The `warm` CLI uses
`--timeout` (default 600 s) instead.

## Server

```bash
.venv/bin/python -m poker_solver.practice.server --host 127.0.0.1 --port 7777 [--web-dir DIR]
# prints: Practice server on http://127.0.0.1:7777/
curl -sS http://127.0.0.1:7777/api/health        # {"ok":true}
scripts/practice_smoke.sh 7794                     # starts its own server on 7794, 7 checks, stops it
```

The smoke script prints `SMOKE PASS (7 checks)` when everything works. It writes to whatever cache
and data directories the environment points at, so set the two variables to temp directories if
you don't want it touching your home cache.

## Solve cache CLI

```bash
python -m poker_solver.practice.solve_cache [--dir DIR] warm  [--families a,b] [--limit N] [--iterations N] [--seed S] [--timeout SEC]
python -m poker_solver.practice.solve_cache [--dir DIR] stats
python -m poker_solver.practice.solve_cache [--dir DIR] clear
```

`--dir` overrides `$POKER_PRACTICE_CACHE_DIR`. It is a global option and goes **before** the
subcommand.

`warm` pre-solves catalog spots through the real `SolverAdapter`. When `--iterations` is
omitted, each family uses its default solve, which produces the same `params_hash` the UI and
API use. Warming with `--iterations N` only helps requests that override iterations to N.

```text
$ python -m poker_solver.practice.solve_cache warm --families kuhn-intro,river-ip-facing-bet --limit 4 --iterations 30
miss     0.033s kuhn-intro/820b58289136 a8cc6b670343
miss     0.048s kuhn-intro/917ebff3aaea f9ac40e7589f
miss     0.048s kuhn-intro/e2b61aafe517 9f2ef0d2112b
miss     0.049s kuhn-intro/51f7579c8132 ef4ea0fb08cd
warmed 4 spots: 0 hit, 4 miss, 0 error, 0.18s total; dir /tmp/pmdocs.YIZv/cache
$ # same command again
hit      0.000s kuhn-intro/820b58289136 a8cc6b670343
...
warmed 4 spots: 4 hit, 0 miss, 0 error, 0.00s total; dir /tmp/pmdocs.YIZv/cache
```

`--limit` applies to the combined catalog in the catalog's own family order, not the order you
pass to `--families`. That is why the run above warmed only Kuhn spots, and why
`warm --families flop-cbet,preflop-3max-open --limit 2` warms two `preflop-3max-open` spots. Each line has the format `hit|miss|error  <seconds>s <spot_id> <params_hash[:12]>`.
Exit codes: 0 on success, 1 if any spot errored, 2 for bad arguments, e.g.
`error: unknown family 'nope'; known: (...)`.

Warming the whole catalog at family defaults solves all 72 spots. Cold times measured at
`5a3e61f` on a loaded 2-CPU host were up to about 16 s for one `preflop-3max-open` spot and
about 9 s for `flop-cbet`, so a full warm takes several minutes.

```text
$ python -m poker_solver.practice.solve_cache stats
dir: /tmp/pmdocs.YIZv/cache
count: 7
bytes: 27782
disk_ok: True
schema: practice-solve-cache-v1  solver_version: 0.1.0
$ python -m poker_solver.practice.solve_cache clear
removed 11 cache files from /tmp/pmdocs.YIZv/cache
```

`clear` removes only cache entry files and stale `.tmp-*` files. Other files in the directory are
left alone. Cache entries are invalidated automatically when the schema or the installed
`poker-solver` version changes.

## Practice API CLI (list / solve / submit / progress / leaderboard)

Each command prints one JSON response envelope on stdout (keys sorted). Errors go to stderr as
`error: <message>` with exit code 2.

```bash
python -m poker_solver.practice.api list [--family F]... [--seed S] [--limit N]
python -m poker_solver.practice.api solve SPOT_ID [--iterations N]
python -m poker_solver.practice.api submit SPOT_ID KIND [AMOUNT] [--iterations N] [--user U]
python -m poker_solver.practice.api progress [--user U] [--spot-id SPOT_ID]
python -m poker_solver.practice.api leaderboard [--limit N] [--family F]
```

- `--family` can be repeated on `list`.
- `--iterations N` sends `{"algorithm":"vanilla-cfr","iterations":N,"seed":null}`. Without it the
  family default is used.
- `submit` scores a pure action. `KIND` must match a legal kind exactly, including case (`check`
  and `bet` on river/Kuhn spots, `CHECK` and `RAISE` on flop/turn/preflop spots). A wager
  `AMOUNT` that is not in the solved menu is snapped to the nearest solved size. Mixed plays are
  only available through the JSON API.

Verified examples:

```text
$ python -m poker_solver.practice.api submit kuhn-intro/820b58289136 check --user carol
  -> result.user=carol, score.grade=Perfect, score.score=100.0, progress.attempts=1
$ python -m poker_solver.practice.api submit river-oop-bet-or-check/e79981f9d62d bet 50 --iterations 40
  -> feedback: "Solver: bet[33] 73.1%, check 26.9%. You: bet[33] (mapped from bet[50] -> bet[33]). EV loss 0.000 chips (0.00% pot) -> Perfect. ..."
$ python -m poker_solver.practice.api progress --user carol
{"operation": "practice-progress", "provenance": null, "result": {"spots": [{"attempts": 1, "best_score": 100.0, "family": "kuhn-intro", ...}], "totals": {"attempts": 1, "avg_best_score": 100.0, "avg_last_score": 100.0, "spots_attempted": 1}, "user": "carol"}, "version": 4}
$ python -m poker_solver.practice.api leaderboard --family kuhn-intro --limit 2
{"operation": "practice-leaderboard", "provenance": null, "result": {"entries": [{"attempts": 1, "avg_best_score": 100.0, "rank": 1, ...}]}, "version": 4}
$ python -m poker_solver.practice.api progress --user 'bad user'
error: user must match ^[A-Za-z0-9_.-]{1,32}$          (exit 2)
```

## Resetting state

- Solves: `python -m poker_solver.practice.solve_cache clear`, or delete `$POKER_PRACTICE_CACHE_DIR`.
- Progress: stop the server, then delete `$POKER_PRACTICE_DATA_DIR/progress.sqlite3`, along with the
  `-wal` and `-shm` files if they exist. No CLI deletes progress.

## Troubleshooting

| symptom | cause / fix |
|---|---|
| HTTP 504 `solve timed out` | The solve took longer than `POKER_PRACTICE_TIMEOUT` (90 s). The worker thread may still finish and fill the cache. Retry, warm the spot ahead of time with `solve_cache warm`, or lower the iterations |
| 400 `solve exceeded the 60s budget after ...` | The adapter's own budget ran out. Lower the iterations. For offline pre-solving, use `warm --timeout` with a larger value |
| 400 `backend river supports only vanilla-cfr` | MCCFR was requested on a non-allstreet spot. Only `flop-cbet` (allstreet) accepts `external-sampling-mccfr` |
| 400 `play: action kind 'CHECK' is not legal here (legal: [...])` | The kind has the wrong case or isn't legal at this node. Copy it from `legal_actions` |
| 400 `unknown spot_id '...' for seed 0` | The spot ID came from a different `seed` or an older catalog. List the spots again |
| 400 `progress store unavailable` | `progress.sqlite3` could not be opened, e.g. the data dir is unwritable or the DB is newer than the code. Submits keep working with `progress: null` |
| `stats` shows `disk_ok: False` | The cache dir cannot be written. Solves are kept in memory only and are lost on restart |
| Every request re-solves after an upgrade | Expected: entries carry `solver_version`, and a mismatch is treated as a miss and deleted |
| First open of a flop/3-max spot is slow (~10–16 s) | Cold solve. Later requests with the same `params_hash` are served from the cache (0.04 s measured). Warm ahead of time |
| UI progress panel says "Progress unavailable: ..." | The progress ops failed, e.g. the store is unavailable. The rest of the UI still works |
| Port already in use | Pick another `--port`. Port 7777 is the project's long-running instance |
| Tests write to home dirs | They shouldn't: `tests/conftest.py` redirects both variables to a temp dir. When running scripts by hand, export temp directories yourself |
