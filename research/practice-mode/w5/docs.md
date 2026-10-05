# W5 docs task: report

Commit documented: `5a3e61f` (feat/practice-mode). Nothing committed. `src/`, `tests/`, `web/`,
`STATE.txt` and `PROGRESS.md` were not edited.

## Files written

| file | status | content |
|---|---|---|
| `PRACTICE_MODE.md` | new | How to run (server, env vars, cache warm, smoke, CLI); UI walkthrough; family table; scoring formula and grade bands; how to read the solver evaluation (source of truth = `research/solver-evaluation/results.md`, worst-case rule, the two headline verdicts, verdict at 5a3e61f: overall FAIL / correctness PARTIAL, with C11/C14/C15 numbers); known limitations (scale C14, tiny ranges, single bet size, abstraction caps, 3-max quality and null NashConv, MCCFR only on allstreet, cold-solve times, no auth). |
| `docs/practice-mode/api.md` | new | All 5 v4 ops (`practice-list-spots`, `-solve-spot`, `-submit-play`, `-progress`, `-leaderboard`) with request/response JSON captured from real HTTP calls to a server on port 7794 (temp cache/data dirs). Also covers the transport envelope, common fields, the family table, scoring, pure/off-menu-snap/mix submit examples, a 3-max solve example, and a captured error table (400/404/405/504). Long arrays and repeated `provenance.params` are shortened and marked. |
| `docs/practice-mode/architecture.md` | new | Rule R1; request-flow diagram; module table; backend routing with the real `provenance.entrypoint` strings; family grids; caching layers; progress store; UI; test isolation. |
| `docs/practice-mode/solver-evaluation.md` | new | Benchmark files; how to run (quick/full/--only/pytest); PASS/PARTIAL/FAIL definitions; threshold table (from `THRESHOLDS`); the worst-case rule (verbatim `VERDICT_RULE` plus explanation of scope caps and the correctness-only verdict); the verdict at 5a3e61f (results.md committed there, run on ed886c8 dirty); `results.json` layout; what the verdict means for users. Says explicitly that results.md overrides this page. |
| `docs/practice-mode/operations.md` | new | Env var table (`POKER_PRACTICE_CACHE_DIR`, `POKER_PRACTICE_DATA_DIR`, `POKER_PRACTICE_TIMEOUT`, `POKER_PRACTICE_WEB`, `PYTHON`); the 60 s adapter budget vs the 90 s server timeout; server + smoke; `solve_cache warm/stats/clear` with real output; API CLI incl. `progress`/`leaderboard`; resetting state; troubleshooting table. |
| `README.md` | edited (+10 lines) | New `## Practice mode` section only, inserted before `## Utility convention`. It links to `PRACTICE_MODE.md`, `results.md` and `docs/practice-mode/`. |

## Commands verified (all with `.venv/bin/python`, temp `POKER_PRACTICE_CACHE_DIR`/`POKER_PRACTICE_DATA_DIR` under /tmp/pmdocs.*)

- `-m poker_solver.practice.server --host 127.0.0.1 --port 7794`: banner printed. Checked `GET /api/health`, `GET /` (200), `GET /nope` (404), `GET /api/v4` (405) and a duplicate-key body (400). Stopped afterwards; port 7794 is free and 7777 was never touched.
- `POKER_PRACTICE_TIMEOUT=1` server: a cold 3-max solve returned 504 `solve timed out`.
- HTTP `POST /api/v4` for all 5 ops, including user/spot filters, family leaderboard, off-menu snap, mix play, solves of every new family (preflop-hu, preflop-3max, flop-cbet incl. cached repeat 0.04 s vs 8.8 s cold, turn-barrel), and the error cases.
- `-m poker_solver.practice.api list [--family] [--limit]`, `solve --iterations`, `submit KIND [AMOUNT] --iterations --user`, `progress [--user] [--spot-id]`, `leaderboard [--limit] [--family]`, plus invalid user and unknown family (exit 2).
- `-m poker_solver.practice.solve_cache stats | warm --families --limit --iterations (miss then hit) | warm --families nope (exit 2) | --dir D warm/stats | clear | warm --help`, and `warm --families flop-cbet,preflop-3max-open --limit 2` (18 s, exit 0).
- `external-sampling-mccfr`: accepted on flop-cbet; rejected on kuhn and river (`supports only vanilla-cfr`).
- `scripts/practice_smoke.sh 7794`: SMOKE PASS (7 checks).
- `scripts/solver_eval.sh quick <tmpdir>`: overall=FAIL correctness=PARTIAL in 52 s, with git 5a3e61f (dirty). `benchmark.py --mode quick --out <tmp> --only C1-kuhn-analytic`: PASS. The canonical results.* files were not rewritten (full mode was not run).

## Notes / caveats

- The verdict numbers quoted are from `research/solver-evaluation/results.md` as committed at 5a3e61f. That file records a run on `ed886c8` with a dirty tree. The docs say so and defer to results.md.
- An untracked `src/poker_solver/practice/nplayer_metrics.py` appeared during this task. A concurrent repair probably adds 3-max NashConv. The docs say 3-max `nash_conv` is `null` *at 5a3e61f*. If the repair lands, update the "NashConv reported" column in architecture.md, the 3-max limitation in PRACTICE_MODE.md and solver-evaluation.md, and the `preflop-3max-open` solve example in api.md.
- Captured example values (Q, scores, timings) are run-specific solver output. They are not reference answers.
