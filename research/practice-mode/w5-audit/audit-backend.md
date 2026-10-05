# W5 audit-1 — W4 backend (families, adapter routes, disk solve cache, R1)

Auditor: non-author, read-only. Target: frozen worktree `/tmp/w4audit` @ `5a3e61f` (branch feat/practice-mode).
Scratch: `/tmp/w5a1/` (all scripts referenced below are there). Worktree verified clean afterwards (`git status --short` empty).
Common prefix for every repro (abbreviated `$RUN` below):

```
cd /tmp/w4audit && export POKER_PRACTICE_CACHE_DIR=/tmp/w5a1/cache POKER_PRACTICE_DATA_DIR=/tmp/w5a1/data \
  PYTHONPATH=/tmp/w4audit/src; RUN=/home/genomix-node/poker-solver/.venv/bin/python
```

Host: 2 vCPU, load average 2–6.5 during the audit.

Baseline: `$RUN -m pytest -q tests/test_practice_families.py tests/test_practice_solve_cache.py` → **60 passed in 63.37s**.

## Summary

| # | Severity | Finding |
|---|---|---|
| F1 | MAJOR | Some corrupt cache files crash the solve every time instead of counting as a miss. The bad file is not removed, so the spot keeps failing until someone clears the cache by hand. |
| F2 | MAJOR | Changing solver code does not invalidate the cache. `solver_version` is the static package version `0.1.0`, so results from old or buggy code are served after a fix. |
| F3 | MAJOR (test gap) | Hero Q-values for preflop-hu-open, flop-cbet and turn-barrel are not tested. A mutant that fakes their Q passes all 314 practice tests. |
| F4 | MINOR | The displayed `optimal_action` is the argmax of the strategy, not of Q. At the family defaults the "optimal" action can be graded *Inaccuracy*, while another action scores 100. |
| F5 | MINOR | Facing an all-in on the turn (multistreet), the user is offered a pseudo `RAISE` that is really a call. Both buttons grade *Perfect* and the strategy splits its mass between them. Catalog spots cannot reach this node; custom spots can. |
| F6 | MINOR | The MCCFR allstreet route checks the time budget only after training finishes. With `timeout_s=2` it ran for 10.1 s, and the API accepts MCCFR with up to 20 000 iterations. |
| F7 | MINOR | Concurrent cold requests for the same spot are not single-flighted, so the solve runs twice. On this 2-vCPU host that pushed a flop solve from 9.9 s to 16.4 s. |
| F8 | MINOR | A well-formed but tampered record is served as-is. Nothing checks that `provenance.params` or `provenance.iterations` match the spot. |
| F9 | NIT | With `memory_items=0` and a failed disk write, `SolverAdapter.solve` raises `KeyError` after a successful solve. |
| F10 | NIT | `key in DiskSolveCache` raises `ValueError` for a non-hex key, where a `MutableMapping` should return `False`. |

Checks that passed (reproduced) are listed at the end.

---

## F1 — MAJOR: some corrupt cache files crash every solve and are never removed

`DiskSolveCache._load` reads with `path.read_text(encoding="utf-8")` inside `try/except (FileNotFoundError, OSError)` only, then
decodes inside `except (ValueError, KeyError, TypeError, AttributeError, IndexError)`. Three corruptions escape both handlers:
- **Invalid UTF-8:** raises `UnicodeDecodeError` from `read_text`. It subclasses `ValueError`, but it is raised outside the decode `try`.
- **Deep nesting:** `RecursionError` from `json.loads`.
- **Zero-denominator fraction:** `ZeroDivisionError` from `Fraction(n, 0)` in `_decode_key`.

In each case the file stays on disk, so every later request for that spot fails. The contract says such files are "ignored (treated as miss) and removed".

Repro (through the real API handler; memory layer cleared to simulate a restart):
```
cd /tmp/w4audit && POKER_PRACTICE_CACHE_DIR=/tmp/w5a1/apicache POKER_PRACTICE_DATA_DIR=/tmp/w5a1/apidata \
  PYTHONPATH=/tmp/w4audit/src $RUN /tmp/w5a1/api_corrupt.py
```
Output:
```
cached file written: True
invalid-utf8 1 UnicodeDecodeError (ValueError subclass=True) | file still present: True
invalid-utf8 2 UnicodeDecodeError (ValueError subclass=True) | file still present: True
deep-nesting 1 RecursionError (ValueError subclass=False) | file still present: True
deep-nesting 2 RecursionError (ValueError subclass=False) | file still present: True
fraction-zero-den 1 ZeroDivisionError (ValueError subclass=False) | file still present: True
fraction-zero-den 2 ZeroDivisionError (ValueError subclass=False) | file still present: True
```
In `server.py`, the two non-`ValueError` cases fall through to the generic `except Exception` → HTTP 500. The UTF-8 case returns 400 with
a codec message. The same failures also show up at the cache level in `$RUN /tmp/w5a1/cache_probes.py`, probes
`invalid-utf8-file`, `invalid-utf8-file-through-adapter`, `deeply-nested-json` and `fraction-zero-denominator`.

Suggested fix: move the read inside the decode `try`, and catch `Exception` (or at least `UnicodeDecodeError`, `RecursionError`,
`ZeroDivisionError` and `OverflowError`) → discard the file.

## F2 — MAJOR: changing solver code does not invalidate the cache

`adapter.solver_version()` returns `importlib.metadata.version("poker-solver")`. The venv has an editable install
(`direct_url.json: {"url":"file:///home/genomix-node/poker-solver","dir_info":{"editable":true}}`), and the version is a static
`0.1.0`. Any change to the solver, the adapter or `evaluate.py` keeps the same version and the same `params_hash`, so stale results
are served from `~/.cache/poker-solver/practice` indefinitely. This hits R1 directly: after a correctness fix, users keep seeing the
old numbers. Task-B notes that "a solver package version bump invalidates", but nothing bumps the version.

Repro: the mutant adapter (uniform strategy, `/tmp/w5a1/m1_uniform_policy`) writes the cache, then the real code reads it.
```
cd /tmp/w4audit && POKER_PRACTICE_CACHE_DIR=/tmp/w5a1/cache POKER_PRACTICE_DATA_DIR=/tmp/w5a1/data $RUN /tmp/w5a1/stale_version.py
```
Output:
```
MUTANT(m1 uniform) writes: solver_version 0.1.0 strategy {'CHECK0': 0.5, 'RAISE33': 0.5}
REAL code reads: solver_version 0.1.0 strategy {'CHECK0': 0.5, 'RAISE33': 0.5}
REAL code, empty cache: solver_version 0.1.0 strategy {'CHECK0': 0.9902, 'RAISE33': 0.0098}
```
Suggested fix: include a hash of the solver and practice source files (or the git tree hash, or an explicit `ALGO_VERSION`
constant) in `solver_version` / the record. Clear the cache on mismatch.

## F3 — MAJOR (test gap): Q-values for three new families are not tested

The tests catch a constant strategy (see R1 below). Q, however, is only cross-checked for the 3-max SB spot
(`test_3max_sb_spot_q_values_for_hero`). For the mutant I patched a copy so that, for preflop-hu-open, flop-cbet and turn-barrel,
Q becomes `0` for the strategy-argmax action and `-1` for every other action. Fake Q values directly corrupt the score, grade and
EV-loss shown to the user.
```
cd /tmp/w5a1/m6_newfam_q && POKER_PRACTICE_CACHE_DIR=/tmp/w5a1/mc6 POKER_PRACTICE_DATA_DIR=/tmp/w5a1/md6 \
  PYTHONPATH=$PWD/src $RUN -m pytest -q -p no:cacheprovider tests/test_practice_*.py
```
Output: `314 passed in 136.80s` (the mutant survives).
(Mutant source: `/tmp/w5a1/m6_newfam_q/src/poker_solver/practice/adapter.py` line 540.)
Note: my independent recomputation (below) shows the shipped Q values *are* correct. This is a regression-protection gap, not a
wrong answer. Suggested fix: add a test per family comparing `solved.action_values` against an independent `action_values()` over
a raw solve, like the existing 3-max test.

## F4 — MINOR: "optimal action" contradicts the grading at family defaults

`_finish` sets `optimal_action` to the argmax of the *strategy*. Scoring grades by *Q*. When CFR has not converged, the two
disagree. In a sweep of all 36 new-family spots at default iterations (`/tmp/w5a1/timing_all.jsonl`), one spot disagreed by more
than 1e-3 chips:
```
cd /tmp/w4audit && POKER_PRACTICE_CACHE_DIR=/tmp/w5a1/oq POKER_PRACTICE_DATA_DIR=/tmp/w5a1/oqd PYTHONPATH=/tmp/w4audit/src $RUN /tmp/w5a1/optimal_vs_q.py
```
```
iterations 300 optimal_action {'kind': 'CALL', 'amount': 2}
strategy [('FOLD', 0, 0.2302), ('CALL', 2, 0.571), ('RAISE', 5, 0.0012), ('RAISE', 30, 0.1975)]
Q [('FOLD', 0, -1.0), ('CALL', 2, -1.043), ('RAISE', 5, -1.1953), ('RAISE', 30, -1.1128)]
submit {'kind': 'FOLD', 'amount': 0} score 100.0 Perfect ev_loss_pct_pot 0.0
submit {'kind': 'CALL', 'amount': 2} score 77.97 Inaccuracy ev_loss_pct_pot 1.434
```
The UI labels CALL as the solver's optimal play, yet submitting CALL is graded Inaccuracy. On the same spot, preflop-hu-open
`CALL 2` from the button is a limp, and `RAISE 5` scores 0.0 although its EV loss is only 6.5 % of the pot (score is normalised to
the action spread). Suggested fix: derive `optimal_action` from Q (or label it "most frequent action"), and/or raise iterations
where the two disagree.

## F5 — MINOR: pseudo-raise that is really a call when facing all-in (turn-barrel / multistreet)

`multistreet.legal_actions` adds `RAISE target` when `target - committed == remaining` even if that equals the call amount. The
practice layer passes it through unchanged.
```
cd /tmp/w4audit && $RUN /tmp/w5a1/allin_probe.py     # turn-barrel spot 0, stacks=(33,33), line CHECK, RAISE 33 (villain all-in)
```
```
legal: [('FOLD', 0), ('CALL', 33), ('RAISE', 33)]
strategy: {'FOLD0': 0.0795, 'CALL33': 0.4602, 'RAISE33': 0.4602}
Q: {'FOLD0': -50.0, 'CALL33': 30.051951, 'RAISE33': 30.051951}
optimal: Action(kind='CALL', amount=33) optimal_size: None
score {'kind': 'CALL', 'amount': 33} {'score': 100.0, 'grade': 'Perfect', 'ev_loss_pct_pot': 0.0}
score {'kind': 'RAISE', 'amount': 33} {'score': 100.0, 'grade': 'Perfect', 'ev_loss_pct_pot': 0.0}
```
The values are not affected, but the user sees a "Raise 33" button that is not a raise, and the solver frequency (46 % / 46 %) is
split across two buttons for the same action. This also affects the range-strategy display. Catalog spots never reach this node:
every catalog flop/turn hero node offers only `CHECK` / `RAISE <bet>`, because hero acts first or after a check, and a bet is at
most 75 of a 200 stack. So the issue only appears for custom spots or deeper lines. Suggested fix: in the adapter, merge
`RAISE x` into `CALL x` when x equals the call amount (or filter it in `multistreet`).

## F6 — MINOR: MCCFR allstreet ignores the time budget during training

`_solve_allstreet` calls `MCCFRSolver(...).train(iterations)` in one block and compares the clock only afterwards.
`api._solve_params` accepts `external-sampling-mccfr` with up to `MAX_ITERATIONS = 20000`, so a client can start an unbounded flop
solve. The server answers 504 after 90 s, but its daemon worker thread keeps burning CPU.
```
cd /tmp/w4audit && $RUN /tmp/w5a1/budget_probe.py mccfr
```
```
ValueError: allstreet solve exceeded the 2s budget
elapsed 10.1s with timeout_s=2.0
vanilla ValueError: solve exceeded the 2s budget after 50 of 20000 iterations; no partial result is returned
vanilla elapsed 2.3s with timeout_s=2.0
```

## F7 — MINOR: no single-flight for concurrent cold solves of the same spot

`SolverAdapter.solve` releases the lock while solving. Two simultaneous requests for an uncached spot (for example a double click
or two tabs) both run the full solve.
```
cd /tmp/w4audit && $RUN /tmp/w5a1/budget_probe.py dup
```
```
2 concurrent requests for the same cold spot: solve_count=2, wall=16.4s
single cold solve: 9.9s
```
(flop-cbet spot 0 at its default of 200 iterations; host load ≈4.) With 3-max already at 14.4 s cold under load (F-timing below), a
duplicate would push it past the 20 s budget.

## F8 — MINOR: cache records are not internally consistency-checked

`solved_from_record` checks the schema, the key, the version and the spot hash. It does not check that `provenance.params ==
spot.canonical()`, that `provenance.iterations/algorithm/seed == spot.solve`, or that `optimal_action` follows from `strategy`. A
record that has been edited by hand or is half-migrated loads as an exact hit:
```
cd /tmp/w4audit && $RUN /tmp/w5a1/cache_probes.py      # probes tampered-wellformed-record, provenance-inconsistent-with-spot
```
```
PROBE tampered-wellformed-record: orig=[('check', 0.90625), ('bet', 0.09375)] served=[('check', 0.0), ('bet', 1.0)]
PROBE provenance-inconsistent-with-spot: served provenance iterations=99999 params.pot=999.0 spot.solve.iterations=20
```
Low risk, since the cache dir is user-local (0700). It is still cheap to reject provenance that disagrees with the spot.

## F9 — NIT: `memory_items=0` + write failure → `KeyError`

`SolverAdapter.solve` runs `setdefault(key, solved)` and then `return self._cache[key]`. With `memory_items=0`, the LRU evicts
immediately; if the disk write also fails, the read-back raises `KeyError`, even though the solve succeeded.
Same script, probe `memory_items0-write-failure`:
```
PROBE memory_items0-write-failure: RAISED KeyError: 'cabd668d7cfa1c95b4581e30020607f27fd61f09bb351fa4e4246f3e5c485e59'
```
This is not the default configuration (`memory_items=256`). Fix: return `solved` itself, not a read-back.

## F10 — NIT: `__contains__` raises for malformed keys
Same script, probe `contains-non-key`: `[(123, 'ValueError'), ('nothex', 'ValueError')]`. `Mapping.__contains__` should return
`False` here.

---

## Checks that passed (reproduced)

### R1 — no hardcoded answers
- No float literals in `catalog/adapter/models/evaluate/solve_cache.py`. `search_files '\b0\.\d+'` matches only `0.0` comparisons
  in `evaluate.py`. No module reads committed data: the only file I/O in `practice/` is the cache in `solve_cache.py` and the
  request parsing in `server.py`. No `<sha256>.json` files are tracked (`test_no_presolved_cache_files_in_repo` passes).
  `research/solver-evaluation/results.json` is committed but not imported by practice code.
- The preflop equity table is built at runtime in `preflop_config` (seeded `evaluate_seven` sampling). Sampled equity is accurate:
  AsKs vs QhQd gives 0.459 at 256 samples vs 0.4591 at 20 000 (`$RUN /tmp/w5a1/submit_probe.py`, last line).
- Mutation testing (`/tmp/w5a1/make_mutants.py`, `/tmp/w5a1/run_mutants.sh`, output in `/tmp/w5a1/mutants.txt` and
  `mutants2.txt`):
  - m1, constant uniform strategy: caught by 7 tests in families+adapter.
  - m4, pure first action: caught by 3.
  - m3, preflop equity forced to all-ties: caught by 3 (equity test plus the two preflop range-width R1 tests).
  - m2, constant Q = 0: caught by 1 test in families and 8 more across the practice suite.
  - m5/m6, Q faked except for 3-max: the families tests miss it; m6 survives the whole suite → **F3**.

### Correctness — independent recomputation
The check is `/tmp/w5a1/indep.py`. It builds an uncached raw root, trains the raw solver, and computes Q with its own
counterfactual walk (chance × opponent reach, without `practice.evaluate`). Output is in `/tmp/w5a1/indep.jsonl`:

| spot | iters | max\|ΔQ\| | max\|Δstrategy\| | info_key | Q-argmax = optimal? |
|---|---|---|---|---|---|
| preflop-hu-open/6db0bd5d4d67 | 300 | 4.4e-16 | 0.0 | match | RAISE30 = RAISE30 |
| preflop-3max-open/a99ed8603bf2 | 30 | 4.4e-16 | 0.0 | match | RAISE40 ≠ RAISE5 (F4) |
| flop-cbet/9a471ac7b613 | 200 | 0.0 | 0.0 | match | CHECK0 = CHECK0 |
| turn-barrel/66dd7963184f | 200 | 1.8e-15 | 0.0 | match | RAISE75 = RAISE75 |
| turn-barrel/af62a65c533a | 200 | 0.0 | 0.0 | match | RAISE33 = RAISE33 |

Repro: `$RUN /tmp/w5a1/indep.py flop-cbet 0 200`, and likewise for the others.

**CachedState wrapper equals the uncached solver over the full profile** (`/tmp/w5a1/profile_identity.py`, output in
`/tmp/w5a1/identity.txt`):
```
flop-cbet[1] iters=200 infosets=252 max|diff|=0.0 cached=4.62s raw=18.20s nash_conv cached=11.77802995206089 raw=11.77802995206089
turn-barrel[0] iters=200 infosets=208 max|diff|=0.0 cached=3.61s raw=34.58s nash_conv cached=1.1597242271293595 raw=1.1597242271293595
preflop-hu-open[3] iters=100 infosets=40 max|diff|=0.0 cached=1.78s raw=80.28s nash_conv cached=0.15407584002331998 raw=0.15407584002331998
preflop-3max-open[6] iters=10 infosets=162 max|diff|=0.0 cached=4.10s raw=80.79s
```

### Disk cache
- **Round trip:** exact for all 7 families × 3 spots (indices 0, 1, 4) at default iterations, through a fresh `DiskSolveCache`
  instance. Comparison is `==`, `to_json` equality, `.hex()` of every strategy/Q float, and `info_key`. All 21 gave `exact: true`
  (`$RUN /tmp/w5a1/timing_roundtrip.py 0,1,4`, output in `/tmp/w5a1/timing.jsonl`).
- **Changed params never hit:** iterations, pot, stacks, range weight and algorithm all miss (`changed-params-never-hit` →
  every value `True`).
- **Multi-process writers:** 4 processes writing the same 3 keys → `rc=[0,0,0,0] files=3 tmp_left=[] all_load=True discarded=0`.
- **Path traversal:** key regex `^[0-9a-f]{64}$` is enforced on get/set/del; the existing 10-case test passes. Symlinked entries are
  ignored.
- **Version and schema mismatch:** a version-string or schema mismatch is discarded (existing tests pass). The weakness is the
  version *source* (F2).

### info_key format change and submit/scoring
`SolvedSpot.to_json()` does not emit `info_key` (it is `None` in the API result for every family), and scoring never reads it.
Through the real API, submitting every legal action plus the solver mix worked for all 7 families, and progress was recorded
(`$RUN /tmp/w5a1/submit_probe.py`, with `POKER_PRACTICE_CACHE_DIR=/tmp/w5a1/subcache`). Example lines:
```
preflop-3max-open info_key type: NoneType | pure: [('FOLD', 0, 100.0, 'Perfect', True), ('CALL', 2, 25.52..., 'Blunder', True), ...] | solver-mix score: 86.31
turn-barrel info_key type: NoneType | pure: [('CHECK', 0, 0.0, 'Blunder', True), ('RAISE', 75, 100.0, 'Perfect', True)] | solver-mix score: 63.26
```

### Cold solve time per family at defaults (budget 20 s)
All 36 new-family spots, a fresh adapter each time, no cache (`$RUN /tmp/w5a1/timing_all.py preflop-hu-open,preflop-3max-open,flop-cbet,turn-barrel`,
output in `/tmp/w5a1/timing_all.jsonl`, 1-min load 2.0–4.5):

| family | iters | spots | min s | max s |
|---|---|---|---|---|
| preflop-hu-open | 300 | 12 | 1.77 | 2.53 |
| preflop-3max-open | 100 | 8 | 6.80 | **14.40** (load 3.8) |
| flop-cbet | 200 | 8 | 4.91 | 8.41 |
| turn-barrel | 200 | 8 | 2.18 | 5.85 |

Every spot is within budget. 3-max uses 72 % of the budget under moderate load, and a duplicate concurrent solve (F7) or higher
load would exceed it. Legacy families: 0.13–6.33 s (`timing.jsonl`).
