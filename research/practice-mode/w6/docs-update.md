# W6 docs refresh: report

Documented commit: `72f0053` (tag `practice-mode-w5`). The practice code there is the W5 code from
`2a6f57c`; `72f0053` only adds the re-run `results.json` / `results.md`. Nothing committed.
`src/`, `tests/`, `web/`, `STATE.txt`, `PROGRESS.md`, `benchmark.py` and `results.*` were not edited.
(`PROGRESS.md` and `STATE.txt` show as modified in the worktree because other agents edited them.)

## Files updated

| file | main changes |
|---|---|
| `PRACTICE_MODE.md` | Commit → 72f0053/tag. 3-max default 5000 + flat vectorised trainer. Progress recorded only for family-default solves, with CLI examples adjusted (the `submit` example no longer uses `--iterations`). `optimal_action` rule. All-in pseudo-raise merged into CALL. UI shortcuts work on every family, labels, neutral Best badge. Verdict rewritten from W5 `results.md`: overall FAIL (C14 1.8e5 s), correctness PARTIAL, C11 PARTIAL only because of flop-cbet 1.122 %, 3-max 0.143 % PASS, C15 PARTIAL. Capability table: FAIL = 2-player NL and postflop; PARTIAL = 3-max, preflop, multi-street, ICM, sizing. Limitations: removed "3-max null NashConv / exploitable"; added flop-cbet 1.12 %, multistreet pseudo-raise still built internally, single flight, 504/60 s budgets, cold-time ranges. |
| `docs/practice-mode/api.md` | All examples re-captured from a server on port 7797: list, solve (40 iterations), 3-max solve (5000 iterations, `nash_conv` 0.012866, new entrypoint string, `optimal_action` RAISE 40), submit at the family default (recorded), override submit (`progress: null`), snap, mix, progress, filtered progress, leaderboard, family leaderboard. Documented the anti-forging rule (`solve: {}` is not the default for 3-max, but is for Kuhn; checked with `_resolve_spot_canonical`). Documented the pseudo-raise merge, the `optimal_action` definition and the finite 3-max NashConv. Error table extended (lowercase `raise` on 3-max, MCCFR on river, lone surrogate, 504 writes no row, generic store errors). |
| `docs/practice-mode/architecture.md` | Request-flow diagram (backlog 64, deadline token, single flight, family-default-only progress). New `nplayer_metrics.py` row. Adapter: single flight, chunked budget for CFR and MCCFR. Server/api/progress: RequestToken, 30 s retry, inode reopen. New preflop entrypoints captured live, 3-max NashConv "yes". 3-max grid default 5000. New "presentation-layer rules" section (pseudo-raise merge, `optimal_action`). Cache: schema v2, code fingerprint + module list, record consistency checks, volatile pinning, 0700. Progress anti-forging/deadline/robustness. UI W5 fixes. W5 test files. |
| `docs/practice-mode/operations.md` | Commit/tag. Chunked budget. 504 cancels the token (verified, see below). Backlog 64 and single flight. Re-captured `warm` hit/miss, 3-max warm timings, and `stats` output (v2 + `code_fingerprint`). Fingerprint invalidation explained. `submit --iterations` not recorded, plus a verified example pair. Unknown-family exit 2. Troubleshooting rows: `progress: null`, 30 s retry, generic store error, DB deleted, invalid string encoding, re-solve after a code edit, cold times. |
| `docs/practice-mode/solver-evaluation.md` | "Current verdict" rewritten from W5 `results.md`/`results.json` (run on 2a6f57c, clean tree, 499 s): criteria 17/2/1, a failing/partial table, capabilities, a W4→W5 delta, the pass list with W5 numbers. Notes that `results.md` still prints the stale "nash_conv=None for 3-max" scope-cap string from `benchmark.py`. Run times updated. |
| `README.md` (Practice mode section only) | Tag/commit, smoke command, verdict summary consistent with `results.md`. |
| `research/solver-evaluation/REPORT.md` | Header/run metadata → W5 run. Verdict, capability table, criteria rows (C2, C6, C9, C11, C12, C14, C15) and gap list rewritten to match `results.md`/`results.json` exactly. New "Changes since the W4 run" table. Reproduce timings. |

## Commands verified (all `.venv/bin/python` from the repo root, temp dirs under `/tmp/w6docs/`)

Server (port 7797; port 7777 never touched; 7797 stopped afterwards, confirmed free):
- `-m poker_solver.practice.server --host 127.0.0.1 --port 7797` with temp `POKER_PRACTICE_CACHE_DIR`/`DATA_DIR`: banner `Practice server on http://127.0.0.1:7797/`. Checked `GET /api/health` `{"ok":true}`, `GET /` 200 with CSP, `GET /nope` 404, `GET /api/v4` 405.
- `POST /api/v4`:
  - list (filtered, and all 72; family default iterations confirmed: 3-max = 5000);
  - solve river 40 iterations;
  - solve 3-max default: 12.3 s cold, 0.044 s repeat, finite `nash_conv`;
  - solve flop-cbet: 13.8 s cold, 0.16 s repeat;
  - MCCFR on flop-cbet: 200; MCCFR on river/kuhn: 400;
  - submit default (recorded), submit with a 40-iteration override (`progress` null), snap, mix (user `local`);
  - progress (all / one spot), leaderboard (limit / family);
  - errors: unknown spot, bad user, unknown field, wrong-case kind on river and 3-max, duplicate key, lone surrogate.
- `POKER_PRACTICE_TIMEOUT=1` server: cold 3-max submit → 504 `solve timed out` after 1.0 s. 30 s later, progress for that user = 0 attempts, and the cache held the finished solve.
- `scripts/practice_smoke.sh 7797`: SMOKE PASS (7 checks).

CLI:
- `-m poker_solver.practice.api list --family river-oop-bet-or-check --limit 3`; `solve … --iterations 40`.
- `submit … check --iterations 40 --user alice` (progress null); `submit … check --user alice` (recorded); `submit kuhn-intro/820b58289136 check --user carol`; `submit … bet 50 --iterations 40` (snap feedback).
- `progress --user alice|carol`; `leaderboard --limit 10`; `leaderboard --family kuhn-intro --limit 2`.
- `progress --user 'bad user'` (exit 2); `list --family nope` (exit 2); `--help`.
- `-m poker_solver.practice.solve_cache clear`; `warm --families kuhn-intro,river-ip-facing-bet --limit 4 --iterations 30` (4 miss, then 4 hit).
- `solve_cache stats` (v2 + fingerprint); `warm --families nope` (exit 2); `--dir D warm …` / `--dir D stats`.
- `warm --families flop-cbet,preflop-3max-open --limit 2` (2 × 3-max, 21.97 s and 25.68 s under concurrent load, exit 0); `warm --help`.
- `-m poker_solver.practice.server --help`; `uv sync --locked --dry-run` (no changes).

Benchmark (no canonical files rewritten):
- `scripts/solver_eval.sh quick /tmp/w6docs/seq`: overall=FAIL correctness=PARTIAL in 33.9 s, git 72f0053 (dirty from other agents' PROGRESS/STATE edits).
- `research/solver-evaluation/benchmark.py --mode quick --out /tmp/w6docs/se1 --only C1-kuhn-analytic`: PASS. `--help`.
- `pytest -q tests/test_solver_evaluation.py`: 5 passed in 24 s.
- `scripts/solver_eval.sh full`: **not run** (it would rewrite `results.*`, which this task does not own). Its documented timing (~8 min) comes from the W5 run's recorded 499 s.

## Notes / caveats

- `results.md` capability gaps still say "the adapter reports nash_conv=None for 3-max". The string is hard-coded in `benchmark.py` (`CAPABILITY_RULES`, line ~253) and is stale. The docs flag it; fixing it needs a benchmark edit plus a re-run (owner: benchmark).
- The C6 evidence in `results.json` does not include practice-spot comparisons, because C6 runs before C10 appends them. The docs therefore do not claim C6 checks the 3-max practice NashConv. Equality with the oracle is covered by `tests/test_practice_w5_repairs.py` (per the W5 repair report).
- Captured timings vary with host load: the 3-max cold solve took 11.4 s in the benchmark, 12.3 s via the server and 22–26 s during the concurrent warm. The docs give ranges.
- `flop-cbet` and `turn-barrel` catalog spots still label the first bet `RAISE`. This is unchanged and already noted in the UI repair report.
