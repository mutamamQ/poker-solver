# Practice mode operations

These commands were verified at commit `72f0053` (tag `practice-mode-w5`) with `.venv/bin/python`
from the repo root, using temp `POKER_PRACTICE_CACHE_DIR` / `POKER_PRACTICE_DATA_DIR`. The output
shown is from those runs (`python` below means `.venv/bin/python`).

## Environment variables

| variable | used by | default | effect |
|---|---|---|---|
| `POKER_PRACTICE_CACHE_DIR` | `solve_cache.DiskSolveCache.from_env()`, which also backs the API adapter | `~/.cache/poker-solver/practice` | directory for persisted solves (one `<params_hash>.json` per solve). Ignored if empty |
| `POKER_PRACTICE_DATA_DIR` | `progress.ProgressStore.from_env()` | `~/.local/share/poker-solver/practice` | directory holding `progress.sqlite3` |
| `POKER_PRACTICE_TIMEOUT` | `server.py` | `90` | seconds before `POST /api/v4` answers `504 {"error":"solve timed out"}`. Fractional values are allowed. Non-positive or non-numeric values are ignored |
| `POKER_PRACTICE_WEB` | `server.py` | `<repo>/web` | static UI directory (`--web-dir` takes precedence) |
| `PYTHON` | `scripts/practice_smoke.sh`, `scripts/solver_eval.sh` | `<repo>/.venv/bin/python` | interpreter |

Both directories are read when the process starts. The progress store opens lazily on the first
progress/submit call. Separate from the server timeout, each adapter solve has its own budget of
60 s (`SolverAdapter(timeout_s=60)`), checked between 25-iteration training chunks for both CFR and
MCCFR. A solve that runs over it fails with `solve exceeded the 60s budget ...` and no partial
result is returned. The `warm` CLI uses `--timeout` (default 600 s) instead.

When the server's timeout fires it cancels the request's deadline token *before* answering 504,
so a timed-out `practice-submit-play` records no progress row. The solve itself cannot be
interrupted: it finishes in its daemon thread and fills the solve cache, so a retry is usually
instant. Verified: with `POKER_PRACTICE_TIMEOUT=1`, a cold 3-max submit for user `late` returned
504 after 1.0 s; 30 s later `practice-progress` for `late` showed 0 attempts and the cache held the
finished solve.

## Server

```bash
.venv/bin/python -m poker_solver.practice.server --host 127.0.0.1 --port 7777 [--web-dir DIR]
# prints: Practice server on http://127.0.0.1:7777/
curl -sS http://127.0.0.1:7777/api/health        # {"ok":true}
scripts/practice_smoke.sh 7794                     # starts its own server on 7794, 7 checks, stops it
```

The server listens with a backlog of 64 (`REQUEST_QUEUE_SIZE`) and serves each request in a daemon
thread. Identical concurrent solve requests share one solve (adapter single flight).

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

Warming the whole catalog at family defaults solves all 72 spots. `preflop-3max-open` now
defaults to 5000 iterations. Cold times at `72f0053` on the 2-CPU host: the benchmark measured
11.4 s for a 3-max spot and 3.8 s for `flop-cbet` (load ≈ 3); under heavier load a 3-max spot
can take longer, so a full warm takes several minutes:

```text
$ python -m poker_solver.practice.solve_cache warm --families flop-cbet,preflop-3max-open --limit 2
miss    21.965s preflop-3max-open/a4b66447a35b 319fa5bd28d9
miss    25.681s preflop-3max-open/0214b0a35aef 9d6e40a483ea
warmed 2 spots: 0 hit, 2 miss, 0 error, 47.65s total; dir /tmp/w6docs/clicache
```

(That run overlapped other jobs on the host; the same spot took 12.3 s cold through the server
moments earlier.)

```text
$ python -m poker_solver.practice.solve_cache stats
dir: /tmp/w6docs/clicache
count: 4
bytes: 10320
disk_ok: True
schema: practice-solve-cache-v2  solver_version: 0.1.0
code_fingerprint: 64edd0f87171cbc74535a0027efa90834ff969d9d7b329c7d4e6f390da284448
$ python -m poker_solver.practice.solve_cache clear
removed 6 cache files from /tmp/w6docs/clicache
```

`clear` removes only cache entry files and stale `.tmp-*` files. Other files in the directory are
left alone. Cache entries are invalidated automatically (treated as a miss and deleted on read)
when the schema, the installed `poker-solver` version, or the **code fingerprint** changes. The
fingerprint is a sha256 over the source of the solver and practice modules in
`solve_cache.FINGERPRINT_MODULES`, so editing any of them (even a comment) re-solves everything.
Files written by the W4 code (schema v1) are discarded. Records whose provenance does not match
their own spot (params, params_hash, backend, solve) are also rejected.

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
- `submit` records progress only for the family-default solve. With `--iterations N` (unless N is
  the family default) it is scored but `result.progress` is `null`.
- `submit` scores a pure action. `KIND` must match a legal kind exactly, including case (`check`
  and `bet` on river/Kuhn spots, `CHECK` and `RAISE` on flop/turn/preflop spots). A wager
  `AMOUNT` that is not in the solved menu is snapped to the nearest solved size. Mixed plays are
  only available through the JSON API.

Verified examples:

```text
$ python -m poker_solver.practice.api submit river-oop-bet-or-check/e79981f9d62d check --iterations 40 --user alice
  -> score.grade=Mistake, result.progress=null            (custom solve: scored, not recorded)
$ python -m poker_solver.practice.api submit river-oop-bet-or-check/e79981f9d62d check --user alice
  -> score.grade=Inaccuracy, result.progress.attempts=1   (family default 200: recorded)
$ python -m poker_solver.practice.api submit kuhn-intro/820b58289136 check --user carol
  -> result.user=carol, score.grade=Perfect, score.score=100.0, progress.attempts=1
$ python -m poker_solver.practice.api submit river-oop-bet-or-check/e79981f9d62d bet 50 --iterations 40
  -> feedback: "Solver: bet[33] 73.1%, check 26.9%. You: bet[33] (mapped from bet[50] -> bet[33]). EV loss 0.000 chips (0.00% pot) -> Perfect. ..."
$ python -m poker_solver.practice.api progress --user carol
{"operation": "practice-progress", "provenance": null, "result": {"spots": [{"attempts": 1, "best_score": 100.0, "family": "kuhn-intro", ...}], "totals": {"attempts": 1, "avg_best_score": 100.0, "avg_last_score": 100.0, "spots_attempted": 1}, "user": "carol"}, "version": 4}
$ python -m poker_solver.practice.api leaderboard --limit 10
{"operation": "practice-leaderboard", "provenance": null, "result": {"entries": [{"attempts": 1, "avg_best_score": 100.0, "rank": 1, "spots_attempted": 1, "total_best_score": 100.0, "user": "carol"}, {"attempts": 1, "avg_best_score": 0.0, "rank": 2, "spots_attempted": 1, "total_best_score": 0.0, "user": "alice"}]}, "version": 4}
$ python -m poker_solver.practice.api leaderboard --family kuhn-intro --limit 2
{"operation": "practice-leaderboard", "provenance": null, "result": {"entries": [{"attempts": 1, "avg_best_score": 100.0, "rank": 1, ...}]}, "version": 4}
$ python -m poker_solver.practice.api progress --user 'bad user'
error: user must match ^[A-Za-z0-9_.-]{1,32}$          (exit 2)
$ python -m poker_solver.practice.api list --family nope
error: unknown families: ['nope']; known: ['flop-cbet', 'kuhn-intro', ...]   (exit 2)
```

## Resetting state

- Solves: `python -m poker_solver.practice.solve_cache clear`, or delete `$POKER_PRACTICE_CACHE_DIR`.
- Progress: stop the server, then delete `$POKER_PRACTICE_DATA_DIR/progress.sqlite3`, along with the
  `-wal` and `-shm` files if they exist. No CLI deletes progress.

## Troubleshooting

| symptom | cause / fix |
|---|---|
| HTTP 504 `solve timed out` | The solve took longer than `POKER_PRACTICE_TIMEOUT` (90 s). A timed-out submit is **not** recorded. The worker thread still finishes and fills the cache. Retry, warm the spot ahead of time with `solve_cache warm`, or lower the iterations |
| Submit scored but `progress: null`, attempt missing from progress/leaderboard | The submit used a non-default solve (`--iterations`, UI Re-solve with custom iterations, or a `solve` override with a different `params_hash`). Only family-default solves are recorded. Submit without the override |
| 400 `solve exceeded the 60s budget after ...` | The adapter's own budget ran out. Lower the iterations. For offline pre-solving, use `warm --timeout` with a larger value |
| 400 `backend river supports only vanilla-cfr` | MCCFR was requested on a non-allstreet spot. Only `flop-cbet` (allstreet) accepts `external-sampling-mccfr` |
| 400 `play: action kind 'CHECK' is not legal here (legal: [...])` | The kind has the wrong case or isn't legal at this node. Copy it from `legal_actions` |
| 400 `unknown spot_id '...' for seed 0` | The spot ID came from a different `seed` or an older catalog. List the spots again |
| 400 `progress store unavailable` | `progress.sqlite3` could not be opened, e.g. the data dir is unwritable or the DB is newer than the code. Submits keep working with `progress: null`. The open is retried 30 s after a failure, so fixing the directory recovers without a restart. Other store failures answer the generic 400 `progress store error` (details go to the server log) |
| `progress.sqlite3` deleted while the server runs | The store detects the missing/replaced file before the next read or write and recreates it (empty) |
| 400 `...: invalid string encoding` | A string field contained a lone UTF-16 surrogate or the body was not valid UTF-8 |
| `stats` shows `disk_ok: False` | The cache dir cannot be written. Solves are kept in memory only and are lost on restart |
| Every request re-solves after an upgrade or a code edit | Expected: entries carry `solver_version` and a `code_fingerprint` of the solver sources; a mismatch is treated as a miss and deleted. Re-run `warm` |
| First open of a 3-max spot is slow (~11–26 s), flop ~4–14 s | Cold solve. Later requests with the same `params_hash` are served from the cache (0.04 s measured for 3-max). Concurrent requests for the same spot share one solve. Warm ahead of time |
| UI progress panel says "Progress unavailable: ..." | The progress ops failed, e.g. the store is unavailable. The rest of the UI still works |
| Port already in use | Pick another `--port`. Port 7777 is the project's long-running instance |
| Tests write to home dirs | They shouldn't: `tests/conftest.py` redirects both variables to a temp dir. When running scripts by hand, export temp directories yourself |
