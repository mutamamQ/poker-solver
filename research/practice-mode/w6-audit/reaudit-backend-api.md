# W6 re-audit 1: W5 backend and API repairs at `72f0053`

- **Auditor:** fresh non-author, read-only.
- **Tree:** `/tmp/w6audit` at `72f0053eb44e` (tag `practice-mode-w5`). `git status --short` was empty at the end of the audit.
- **Scratch:** `/tmp/w6a1/`. Every script cited below is in `/tmp/w6a1/s/`.
- **Host:** 2 vCPU, load average 2–5.

Common prefix for every repro:
```
cd /tmp/w6audit && PYTHONPATH=/tmp/w6audit/src R=/home/genomix-node/poker-solver/.venv/bin/python
# POKER_PRACTICE_CACHE_DIR / POKER_PRACTICE_DATA_DIR always point under /tmp/w6a1 (the scripts set them)
```

**Baseline:** `$R -m pytest -q -p no:cacheprovider tests/test_practice_*.py` gave **431 passed in 244.12s** (`/tmp/w6a1/pytest.txt`).

## Verdict

- No BLOCKER and no MAJOR findings.
- All 10 prior backend findings and all 7 prior API findings are FIXED, except backend F8, which is PARTIAL. The repair author documented that limitation.
- New issues: 2 MINOR, 2 NIT.

## New findings (all reproduced)

| # | Sev | Finding |
|---|---|---|
| N1 | MINOR | Single-flight does not pass the leader's error to followers. Each waiting follower re-runs the failing solve one after another, so latency grows as N × budget. |
| N2 | MINOR | The progress/leaderboard anti-forging fix closes the `solve` override, but the scores can still be inflated three other ways, all using only default parameters: the solve-spot oracle, retrying every action (best = MAX), and farming new spots via `seed`. |
| N3 | NIT | The fingerprint coverage test does not require `practice/nplayer_metrics.py`. A mutant that drops it from `FINGERPRINT_MODULES` passes every W5 test. |
| N4 | NIT | Two processes running different code against one cache dir delete each other's entries on every read, so the cache keeps flipping between versions. |

### N1 — MINOR: a failed leader is re-run by every follower, one after another
Look at `SolverAdapter.solve` around line 442. When the leader raises, `flight[2]` stays `None`. Each follower then takes the per-key lock in turn, finds no hit, and calls `_solve_cold` itself.

The good news first. There is no deadlock, every caller does get an exception, and `_inflight` is cleaned up afterwards. The problem is that a deterministic failure is computed N times, one after another.

The solves that fail this way are budget overruns and deterministic `ValueError`s. A deterministic example is a custom spot whose hand has no compatible deal. With the default `timeout_s=60` and the server's 90 s 504, the second concurrent request for a slow spot already exceeds the HTTP deadline. Its orphaned thread then burns another full budget of CPU.

Repro: `$R /tmp/w6a1/s/probes2.py sf`. It runs flop-cbet spot 0 at 20000 iterations with adapter `timeout_s=1.5` and 4 threads.
```
alive threads: 0
results (thread, outcome, seconds): [(0, 'ValueError', 3.0), (1, 'ValueError', 5.4), (2, 'ValueError', 8.2), (3, 'ValueError', 10.1)]
_solve_cold invocations: 4 total wall 10.2 inflight left: {}
```
Suggested fix: store the leader's exception in the flight entry and re-raise it to the followers already waiting. New arrivals can retry.

### N2 — MINOR: leaderboard inflation without any `solve` override
F1 is fixed for the `solve` override (see the table). The leaderboard, however, can still be pushed to 100 per spot with no limit on the number of spots, using only the default solve:
1. **Oracle.** `practice-solve-spot` returns `action_values` for the canonical solve. The client submits the argmax-Q action.
2. **Retry.** `best_score = MAX(score)` per spot, so submitting every legal action once guarantees 100.
3. **Seed farming.** `seed` is a free API parameter, and each seed generates new `spot_id`s with full canonical status. So `total_best_score`, which is the leaderboard sort key, is unbounded.

Repros:
```
$R /tmp/w6a1/s/api_repros.py      # section "F1 bypass"
oracle scores: [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
leaderboard top: [{'rank': 1, 'user': 'oracle', 'spots_attempted': 12, 'attempts': 12, 'avg_best_score': 100.0, 'total_best_score': 1200.0}]
$R /tmp/w6a1/s/retry_lb.py        # submit each legal action once, default solve
[{'rank': 1, 'user': 'retry', 'spots_attempted': 12, 'attempts': 24, 'avg_best_score': 100.0, 'total_best_score': 1200.0}]
$R /tmp/w6a1/s/seed_farm_river.py # river-oop-bet-or-check, seeds 1..3 (the "1..5" in the label is stale text)
distinct spot_ids over seeds 1..5: 36 recorded: 36
[{'rank': 1, 'user': 'farmer', 'spots_attempted': 36, 'attempts': 36, 'avg_best_score': 100.0, 'total_best_score': 3600.0}]
```
For comparison, the whole seed-0 catalog has 72 spots across all families.

Impact is low: the app is local, has a single user, and has no authentication. Still, the W5 F1 goal of "leaderboard measures skill" is not met.

Options, choose any:
- rank on the first attempt per spot, not the best;
- count only `seed == 0` (or a server-fixed seed) as canonical;
- stop returning Q from solve-spot before a submit has been recorded.

### N3 — NIT: fingerprint coverage of `nplayer_metrics.py` is not protected by any test
`FINGERPRINT_MODULES` does include `practice/nplayer_metrics.py`. I checked the transitive import closure of `practice/adapter.py` with an AST walk: nothing reachable is missing. The list also has 3 extra entries (`nplayer_postflop`, `practice/catalog`, `practice/scoring`), which is harmless.

However, `test_f2_fingerprint_covers_required_modules` hard-codes a `required` set that does not contain `practice/nplayer_metrics.py`. Mutant `mG` deletes that line from `FINGERPRINT_MODULES`, and the W5 repair, API and cache test files plus `test_practice_adapter.py` all pass:
```
mG_fingerprint_drops_nplayer_metrics :: ...... [100%]   (no failure; /tmp/w6a1/mutants.txt)
```
If that line were later dropped, edits to the 3-max trainer or NashConv would serve stale 3-max results.

Suggested fix: add `nplayer_metrics.py` to `required`. Better still, derive the closure from the imports in the test.

### N4 — NIT: different code versions sharing a cache dir delete each other's entries
The repro uses `$R /tmp/w6a1/s/probes2.py fp`, with two `DiskSolveCache` instances whose fingerprints differ.
```
new-code process wrote file: True
old-code process reads: None | file still present after old read: False | old.discarded 1
```
Rejecting the record is correct, since it fails closed. But the reader also deletes the other version's valid file, so two worktrees or servers on the default `~/.cache/poker-solver/practice` keep forcing each other to re-solve. A per-fingerprint subdirectory, or a miss without the delete, would avoid this.

## Prior findings: FIXED / NOT FIXED

### Backend audit (`w5-audit/audit-backend.md`)
| # | Status | Evidence (re-run at 72f0053) |
|---|---|---|
| F1 corrupt files crash | **FIXED** | `api_corrupt.py`: invalid-utf8, deep-nesting and fraction-zero-den give `OK` on attempts 1 and 2, with `discarding ... RecursionError` / `ZeroDivisionError` logged. `cache_probes.py` shows `get -> None, file exists=False` for all three, and the adapter path re-solves. |
| F2 code change does not invalidate | **FIXED** | `stale_fp.py`: a mutant tree writes (`ver 0.1.0 fp d41a627a89c8 optimal CALL 2`), then the real tree reads (`ver 0.1.0 fp 64edd0f87171 ... discarded 1 optimal FOLD 0`). The record is rejected and re-solved. Fingerprint coverage is complete (AST closure), but see N3. |
| F3 Q untested for 3 families | **FIXED** | I re-applied the original fake-Q mutant (`mut/mH_newfam_fakeq`). `test_hero_q_values_match_independent_recompute` gives **6 failed, 1 passed** (`/tmp/w6a1/mH.txt`). |
| F4 optimal_action vs grading | **FIXED** | `optimal_all.py` over all 72 catalog spots at family defaults: `optimal!=best: 0`, and every optimal action scores 100 Perfect (`/tmp/w6a1/optimal_all.jsonl`). On the original `preflop-hu-open/cc905da2f472` spot the optimal action is now `FOLD`. Mutant `mE` (argmax σ) is killed by `test_optimal_action_is_highest_q_within_support`. |
| F5 pseudo-raise facing all-in | **FIXED** | `allin_probe.py`: `legal: [('FOLD', 0), ('CALL', 33)]`, strategy `{'FOLD0': 0.0795, 'CALL33': 0.9205}`. 0.9205 = 0.4602 + 0.4602, the old split, so no mass is lost. Q of CALL is unchanged at 30.051951. Submitting `RAISE 33` raises `ValueError: play: action kind 'RAISE' is not legal here`, which is a 400 over HTTP. Mutant `mB` (merge drops mass) is killed. |
| F6 MCCFR budget | **FIXED** | `budget_probe.py mccfr`: `solve exceeded the 2s budget after 6675 of 20000 iterations`, `elapsed 2.0s`. Before the fix it was 10.1 s. Chunked MCCFR is identical to a single 60-iteration block (`probes2.py mccfr`: `True`, NashConv 43.4716768… in both). |
| F7 no single-flight | **FIXED** (see N1 for the failure path) | `budget_probe.py dup`: `solve_count=1, wall=5.4s` (single solve 3.9 s). Mutant `mD` is killed. |
| F8 record consistency | **PARTIAL** (as documented) | `provenance-inconsistent-with-spot` is now rejected (`discarding ... provenance algorithm/iterations/seed do not match spot.solve`; my probe's AttributeError comes from it receiving `None`). `tampered-wellformed-record` is still served, with `served=[('check', 0.0), ('bet', 1.0)]`. The repair notes call this out of scope, so it is not new. |
| F9 memory_items=0 + write fail | **FIXED** | `memory_items0-write-failure: ok 21` |
| F10 `__contains__` raises | **FIXED** | `contains-non-key: [(123, False), ('nothex', False)]` |

### API audit (`w5-audit/audit-progress-api.md`); repro `$R /tmp/w6a1/s/api_repros.py`, real HTTP server on an ephemeral port
| # | Status | Evidence |
|---|---|---|
| F1 forge via `solve` | **FIXED** for the override (bypasses remain, see N2) | `honest 200 0.0 Mistake progress: 0.0`; `gamer 200 100.0 Perfect progress: None`; `leaderboard users: ['honest']`. The override cannot be bypassed with an equal hash: the API takes only `spot_id`, so no custom spot payload can be sent. `solve:{}` maps to `SolveParams()` (200 iterations), which differs from the 3-max/HU/flop/turn defaults and is therefore correctly non-canonical. Vanilla CFR forces `seed=None`. Mutant `mC` is killed. |
| F2 504 still records | **FIXED** | `submit 504 ... 0.51`, `canonical cold submit 504`, then after 40 s `t3 attempts: 0` and `t2 attempts: 0`. The orphaned solve still runs to completion, as documented, but it is bounded by the adapter's 60 s budget. |
| F3 latched store failure | **FIXED** | `probes2.py sticky`: `while unwritable: None`, `immediately after fix (inside backoff): None`, `after backoff: 1`, and the DB files are created. |
| F4 backlog 5 | **FIXED** | 64 threads × 4 requests gave `Counter({200: 256})`. |
| F5 codec text in 400 | **FIXED** | `(400, {'error': 'family: invalid string encoding'})`, `(400, {'error': 'spot_id: invalid string encoding'})` |
| F6 last_at vs last_score | **FIXED** | Both now come from the MAX(id) row: `last_score 0.0 Blunder last_at …08.066107Z first_at …09.066107Z`. That is the timestamp of the Blunder attempt. |
| F7 DB deleted at runtime | **FIXED** | `after rm 2nd 1 3rd 2 files ['p.sqlite3', ...] rows on disk (2,)` |

## Regression hunt: checks that passed (reproduced)

- **Vectorised 3-max trainer, bit-exact.** `bitexact.py 40` compares FlatNPlayerCFR against `nplayer.NPlayerCFRSolver` over the benchmark-owned `games.Memo` (not CachedState). It covers **all 20 preflop catalog spots** (12 HU, 8 3-max), trained in odd chunks of 1+6+13+20 iterations. Result: `ALL EXACT: True count 20`, `maxd 0.0`, and every spot takes the public deal-vector path (`/tmp/w6a1/bitexact.txt`). Mutant `mF` changes the regret summation order and is caught by the bit-identity test.
- **NashConv correctness.**
  - `nash_conv_nplayer` equals the independent oracle `games.nash_conv_n` exactly (`max d_nc 0.0`) on all 20 spots.
  - On HU spots it also agrees with `best_response.nash_conv` within 4e-16.
  - In a separate brute-force check on HU Kuhn, I enumerated every pure strategy of the responder against random non-equilibrium profiles. The flat BR equals the brute-force BR (`max abs diff: 1.1e-16`, `GAME=hu brute_br.py`).
  - Mutant `mA` (BR always picks action 0) is killed. A 3-player brute force was too slow on this host, and I stopped it.
- **Pseudo-raise merge:** no mass is lost, Q stays consistent, and RAISE is rejected (see F5). No catalog spot exposes an alias, since all 72 spots have strategy sums equal to 1 within 1.1e-16.
- **504 deadline token:** `RequestToken.run_side_effect` holds its lock around the write, and `cancel()` returns `not committed`. Code review found no race that both records and returns 504. The live run recorded 0 rows.
- **R1 (no hardcoded answers):**
  - In `nplayer_metrics.py` and the new adapter code, the only float literals are 0.0/1.0 initialisers and the 1e-9 merge tolerance.
  - There are no tracked `<sha256>.json` cache files.
  - The equity table is computed at runtime.
  - Mutants killed by the W5 tests: mA, mB, mC, mD, mE, mF, plus mH (the original fake-Q mutant). Only mG survives (N3). Output in `/tmp/w6a1/mutants.txt` and `/tmp/w6a1/mH.txt`.
- **Cold-solve timing at defaults** (`optimal_all.jsonl`, load about 2–5):

  | family | range |
  |---|---|
  | 3-max | 9.5–11.1 s |
  | flop | 2.6–4.1 s |
  | turn | 1.8–3.1 s |
  | river | 0.7–2.8 s |
  | HU preflop | 0.5–1.2 s |

  Every family is within the 20 s budget.
