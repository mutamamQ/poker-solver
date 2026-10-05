# W5 audit-2 — progress tracker / v4 practice ops / CLI / server robustness

Auditor: non-author, read-only. Tree: `/tmp/w4audit` @ `5a3e61f`. Scratch: `/tmp/w5a2/`.
Runner: `cd /tmp/w4audit && PYTHONPATH=/tmp/w4audit/src /home/genomix-node/poker-solver/.venv/bin/python …`
with `POKER_PRACTICE_CACHE_DIR` / `POKER_PRACTICE_DATA_DIR` under `/tmp/w5a2`. My own server ran on 7792
(plus throwaway servers on 7795/7891/7892). All of them are stopped. I did not touch port 7777.

## Summary

| # | Severity | Finding |
|---|----------|---------|
| F1 | MAJOR | Clients can forge progress and leaderboard scores by sending a degenerate `solve` (for example `iterations: 1`). |
| F2 | MINOR | A submit that returns 504 still writes an attempt row later, and its solve keeps burning CPU. |
| F3 | MINOR | Fail-soft store failure is latched for the life of the process, so the store never recovers without a restart. |
| F4 | MINOR | Listen backlog is 5 (stdlib default), so concurrent API clients get `ECONNRESET`. |
| F5 | NIT | 400 messages leak raw Python codec errors for lone-surrogate strings. |
| F6 | NIT | `last_at` uses MAX(ts) but `last_score`/`last_grade` use MAX(id), so they can describe different attempts. |
| F7 | NIT | If the DB file is deleted while the process runs, later attempts go to an unlinked inode and are silently lost. |

No BLOCKERs. No 500s anywhere in the fuzzing. No SQL injection.

## Verified OK (no finding)

- **Tests:** `pytest -q tests/test_practice_progress.py tests/test_practice_cli_smoke.py` → `60 passed in 4.99s`.
- **Response shapes match CONTRACT.md exactly:**
  - submit result keys are `{progress, score, solved, user}`.
  - The `progress` entry keys are `{spot_id, family, street, game_type, attempts, best_score, last_score, last_grade, first_at, last_at}`. It is equal to the matching `practice-progress` spot entry.
  - `practice-progress` returns `{user, totals:{attempts, spots_attempted, avg_best_score, avg_last_score}, spots}` with provenance `null`.
  - `practice-leaderboard` returns `{entries:[{rank, user, spots_attempted, attempts, avg_best_score, total_best_score}]}` with provenance `null`.
  - Timestamps match `^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z$`.
- **Envelope:** every 200 had exactly `{version, operation, result, provenance}` and every 400 had exactly `{error}`. That held across 38 payload-fuzz cases and 16 raw-body cases (`/tmp/w5a2/fuzz.py`, `/tmp/w5a2/raw.py`). Fuzz inputs included:
  - unknown keys; wrong types; `limit` set to `True`, `1.0`, `"5"`, `0`, `101`, `±10**30`, or a 5000-digit int.
  - `user` set to unicode, `a'*33`, `"a\n"`, `None`, or `1`.
  - a 100 000-char `spot_id` and a NUL `spot_id`.
  - duplicate keys, NaN, `1e2`, `version` 4.0/true, invalid UTF-8, and nesting 100 000 deep.
  - a client-sent `progress` or `score` field, which is rejected as an unknown field.
- **SQL injection:** `spot_id = "x' OR 1=1 --"` and `family = "x' OR 1=1--"` return 200 with empty results. A `user` with quotes gets a regex 400. All SQL is parameterized; the single `.format` only inserts a constant fragment.
- **Math:**
  - 120 parallel HTTP submits across 6 users and 9 spots (kuhn + river), against 251 rows total.
  - Recomputing per-user progress independently from the sqlite rows (`/tmp/w5a2/math.py`) gave 0 mismatches over 7 users.
  - Leaderboard checks over family ∈ {none, kuhn-intro, river-oop-bet-or-check} × limit ∈ {1, 3, 100} all passed: order, ranks, ties (three users tied at total 700, broken by avg), and the family filter.
- **Persistence:** I stopped and restarted the server on the same data dir; `practice-progress{user:u1}` was byte-identical before and after.
- **Concurrency:**
  - Processes: 12 processes × 200 `ProgressStore.record`, racing on schema creation too, run 3 times. Each run gave 2400/2400 rows, 0 errors, `journal_mode=wal`, and one `schema_migrations` row.
  - CLI: 12 parallel `api submit` processes all exited 0, none had `progress: null`, and 12 rows were written.
  - Threads: no "database is locked" errors.
- **Fail-soft:** in each of these cases submit returned 200 with `progress: null`, and progress/leaderboard returned 400 `progress store unavailable`:
  - read-only data dir
  - data dir path is a file
  - random-bytes DB
  - read-only existing DB
  - DB path is a directory
  - DB schema v9 (newer than supported)
- **CLI:**
  - These exit 0 with JSON output: `progress`, `--user`, `--spot-id`, `leaderboard`, `--limit/--family`.
  - Validation errors exit 2 with `error: …`. Bad argparse input also exits 2.
  - An unwritable store with `progress` exits 2.

## Findings

### F1 — MAJOR: clients can forge progress/leaderboard scores through the `solve` override

`practice-submit-play` accepts a client `solve` block (`iterations` 1..20000). The score is computed against
that solve, and it is recorded and ranked exactly like a full-strength solve. `params_hash` is stored but
ignored by every aggregate. A 1-iteration CFR "solve" produces a uniform strategy with degenerate Q-values, so the
action the real equilibrium rejects is graded "Perfect".

Strictly, the score is still "server-side scoring of a real solve", but the client chooses how real that solve is.
The effect is that best-score and leaderboard totals can be inflated freely. Repro (`/tmp/w5a2/shape.py`, fresh users):

```
spot kuhn-intro/820b58289136, play {"kind":"bet","amount":0}
honest (default solve, 200 it)        -> 200 0.0   Mistake  stored best 0.0
gamer  (solve iterations=1)           -> 200 100.0 Perfect  stored best 100.0
```

Q-values on the same spot (`/tmp/w5a2/forge2.py`) show why:

- At the default 200 iterations, check q=-1.0008 and bet q=-1.1148.
- At `iterations=1`, check q=-1.25 and bet q=-0.5.

`river-oop-bet-or-check` behaves the same way: at it=1 the optimal action flips to `check`.

Suggested fix (choose one):

- Record or rank only attempts whose solve equals the spot's canonical `solve` (that is, `params_hash` equals the catalog hash).
- Or key best/leaderboard on `params_hash` and exclude non-canonical attempts.
- Or reject `solve` together with `user`.

### F2 — MINOR: a timed-out submit (504) still records the attempt later

`_run_with_timeout` abandons the daemon dispatch thread but never cancels it. The solve finishes and
`_record` writes a row that the client was told failed. The orphaned solve also keeps using CPU, and
repeated 504s pile up such threads. Repro (server started with `POKER_PRACTICE_TIMEOUT=0.5` on port 7795, `/tmp/w5a2/tmo.py 1500 t2`):

```
submit 504 {'error': 'solve timed out'} 0.52
immediately after 504: attempts 0
after 43 s: attempts 1 Good
```

The sqlite row was `(1, 't2', 0.0, 'Good', '2026-10-05T06:19:32.735673Z')`. With `iterations=20000` the
server process had used 35 s of CPU after the 504 and was still solving 2 minutes later.

### F3 — MINOR: fail-soft failure is latched until restart

`api._progress_store` sets `_STORE_FAILED = True` on the first failed open and never retries. If the data dir is
temporarily unwritable (for example at boot, before a mount), progress stays disabled for the life of the process:
submits return `progress: null` and progress/leaderboard return 400, even after the dir is fixed. Repro (`/tmp/w5a2/sticky.py`, same process):

```
while unwritable: None
after dir fixed: None
progress op after fix -> progress store unavailable
files in dir: []
```

Suggested fix: retry the open with a backoff, for example at most once every N seconds, instead of a permanent latch.

### F4 — MINOR: listen backlog of 5 resets concurrent API clients

`make_server` uses `ThreadingHTTPServer` with the stdlib default `request_queue_size = 5`. `/api/v4` requests
are slow enough to fill the accept queue, and the host has `tcp_syncookies=1`, so extra connections get RST.
Repro (`/tmp/w5a2/conc.py N api`, which runs N×4 `practice-progress` requests with N threads):

```
24 api Counter({200: 92, 'ConnectionResetError: [Errno 104] Connection reset by peer': 4})
64 api Counter({200: 230, 'ConnectionResetError: [Errno 104] Connection reset by peer': 26})
same code, request_queue_size=128 (port 7891):  64 api Counter({200: 256})
same code, request_queue_size=5   (port 7892):  64 api Counter({200: 232, 'ConnectionResetError…': 24})
```

My first parallel-submit run used 24 threads and aborted on exactly this RST. The UI has a single user, so impact is
low, but scripted or benchmark clients will see sporadic failures. Fix: set `request_queue_size` to around 128 on the server class.

### F5 — NIT: raw codec error text in 400 bodies

A lone surrogate in a string reaches sqlite and the encoder error text is echoed back:

```
practice-leaderboard {"family":"\ud800"} -> 400 {"error": "'utf-8' codec can't encode character '\\ud800' in position 0: surrogates not allowed"}
practice-progress    {"spot_id":"\ud800"} -> 400 (same message)
```

The status code is correct; only the message is wrong. Better: validate strings as encodable and return
"spot_id must be valid UTF-8 text".

### F6 — NIT: `last_at` and `last_score`/`last_grade` can refer to different attempts

`_SPOT_SQL` takes `last_*` from the highest `id` but `last_at` from `MAX(ts)`. When timestamps go backwards
(NTP step, or the public `ts=` argument), the entry is internally inconsistent:

```
record(score=100, ts=now); record(score=0, ts=now-1s)
-> last_score 0.0, last_grade 'Blunder', last_at = <ts of the 100-score attempt>,
   first_at = <ts of the Blunder attempt>
```

Suggested fix: derive `first_at`/`last_at` from MIN(id)/MAX(id) rows, matching how `last_*` is chosen.

### F7 — NIT: deleting the DB at runtime silently loses later attempts

The single long-lived connection keeps writing to the unlinked inode. Repro (`/tmp/w5a2/unlink.py`):

```
1st 1
after rm, 2nd 2 3rd 3
files on disk: []
```

Submits report attempts 2 and 3, but nothing is on disk and everything is lost at exit. This is an edge case;
mention it in the operations docs, or check the file's `st_ino` before writes.
