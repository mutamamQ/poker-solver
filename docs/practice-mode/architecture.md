# Practice mode architecture

Practice mode works like GTO Wizard's puzzle mode. You get a spot, pick an action, and the
score is the EV you lost compared with a runtime solve of that spot. The code is in
`src/poker_solver/practice/`, the UI in `web/`, and the design rationale in
`PRACTICE_MODE_DESIGN.md`.

## Rule R1: no stored answers

Every strategy, Q value, range strategy, score and grade is computed at request time by the
real solver, or loaded from a cache entry that a real solve wrote earlier. The catalog only
builds inputs: boards, ranges, pots, stacks, bet sizes, the hero hand and the public line.
No pre-solved files are committed. A test asserts that no `<sha256>.json` cache file exists
in the repo tree. Parameter-sensitivity tests check that changing iterations, a range, the
pot, the stack or the bet size changes `params_hash` and the solver output
(`tests/test_practice_no_hardcode.py`, `tests/test_practice_w3_regressions.py`,
`tests/test_practice_families.py`, and benchmark criterion C9).

## Request flow

```
browser (web/index.html, app.js)            CLI (python -m poker_solver.practice.api)
        |  POST /api/v4 {version:4, operation, payload}          |
        v                                                        |
practice/server.py  (stdlib ThreadingHTTPServer; strict JSON,    |
        |            1 MiB body cap, 90 s solve timeout -> 504)  |
        v                                                        v
poker_solver.api_v4.dispatch_v4  -- "practice-*" -->  practice/api.py: handle_practice
                                                          |
         +------------------------+-----------------------+-------------------+
         v                        v                       v                   v
   catalog.generate_catalog   SolverAdapter.solve     scoring.score_play   progress.ProgressStore
   / find_spot (inputs only)  (cache by params_hash)  (EV loss, grade)     (SQLite attempts)
                                  |        ^
                                  v        |
                         solver backends   solve_cache.DiskSolveCache (JSON per params_hash)
                                  |
                                  v
                         evaluate.action_values (Q per legal action, exact tree walk)
```

## Modules

| module | role |
|---|---|
| `models.py` | Frozen dataclasses `SolveParams`, `PracticeSpot`, `SolveProvenance` and `SolvedSpot`, with validation. `PracticeSpot.params_hash()` is the sha256 of the canonical JSON, solve params included. `spot_id` is `family/<12 hex>` and does not depend on the solve params. |
| `catalog.py` | Deterministic seeded generator of the 7 families (72 spots at seed 0). Each family is a parameter grid with a per-cell RNG derived from sha256. `FAMILY_DEFAULT_SOLVE` holds per-family default iterations. |
| `adapter.py` | `SolverAdapter(cache, timeout_s=60)` routes each backend to a real solver entry point (table below). It walks the solved tree to the hero infoset, calls `evaluate.action_values`, and returns a `SolvedSpot` with provenance. It is thread-safe and its cache is keyed by `params_hash`. |
| `evaluate.py` | Computes Q(a) for each legal hero action: hero payoff of taking `a`, then everyone follows the solved profile, with opponents weighted by range weight × reach and chance by probability. The computation is N-player generic. |
| `scoring.py` | `parse_play` (pure action or mix; off-menu sizes snapped to the nearest solved size) and `score_play`, which returns EV loss, % pot, score, grade, solver noise and feedback text built only from those numbers. |
| `solve_cache.py` | `DiskSolveCache`: one JSON file per `params_hash` with an LRU memory layer, plus the `warm/stats/clear` CLI. See [operations.md](operations.md). |
| `progress.py` | `ProgressStore`: SQLite in WAL mode with one row per scored attempt. Every aggregate (best, last, totals, leaderboard) is computed in SQL at read time. |
| `api.py` | Validates and handles the five `practice-*` operations, and provides the smoke CLI. It builds a module-level `_ADAPTER` backed by `DiskSolveCache.from_env()` and falls back to an in-memory dict if the disk cache is unavailable. |
| `server.py` | Static file allow-list (`/`, `/index.html`, `/app.js`, `/style.css`), `POST /api/v4`, `GET /api/health`, and security headers (CSP, nosniff, X-Frame-Options DENY, no-referrer). |

## Backend routing

| family | backend | solver entry point (from `provenance.entrypoint`) | NashConv reported |
|---|---|---|---|
| `kuhn-intro` | kuhn | `poker_solver.kuhn.kuhn_root+cfr.CFRSolver.train` | yes |
| `river-oop-bet-or-check`, `river-ip-facing-bet` | river | `poker_solver.river.river_root+cfr.CFRSolver.train` | yes |
| `preflop-hu-open` | nplayer-preflop | `poker_solver.nplayer_preflop.create_nplayer_preflop_root+nplayer.NPlayerCFRSolver.train (terminal-table: evaluator.evaluate_seven sampled equity)` | yes |
| `preflop-3max-open` | nplayer-preflop | same as above, 3 seats | **no (`null`)** |
| `flop-cbet` | allstreet | `poker_solver.allstreet.create_allstreet_root+cfr.CFRSolver.train (solve_allstreet_postflop pipeline: ...)` | yes |
| `turn-barrel` | multistreet | `poker_solver.multistreet.create_root(turn)+cfr.CFRSolver.train` | yes |

The entry points above were captured from real `practice-solve-spot` calls at `5a3e61f`. Only
`allstreet` accepts `external-sampling-mccfr`. The other backends reject it with
`backend <b> supports only vanilla-cfr`.

Preflop leaves have no postflop play. For each compatible deal, the adapter draws 256 boards
(seeded by sha256 of the deal), ranks them with `evaluator.evaluate_seven`, and passes the
resulting exact `Fraction` utilities to the solver as a terminal table. Side pots come from
`game_structure`.

## Families (grid at `5a3e61f`)

| family | grid | ranges | default solve |
|---|---|---|---|
| `kuhn-intro` | 4 public nodes × card J/Q/K | Kuhn deck | 200 |
| `river-oop-bet-or-check` | 2 range shapes × pot {100,200} × bet {33,75,125}% pot, SPR 2 | 4 combos/side | 200 |
| `river-ip-facing-bet` | same grid, hero facing the bet | 4 combos/side | 200 |
| `preflop-hu-open` | 2 shapes × stack {30,50} × open-to {4,5,6} chips; blinds 1/2 | 5 combos/seat | 300 |
| `preflop-3max-open` | {BTN first-in, SB after BTN fold} × 2 shapes × open-to {5,6}; stack 40 | 3 combos/seat | 100 |
| `flop-cbet` | {OOP first, IP after check} × 2 shapes × bet {33,75}% pot; pot 100, SPR 2 | 3 combos/side, 2 turn+river runouts | 200 |
| `turn-barrel` | same roles/shapes/sizes | 4 combos/side, 4 river runouts | 200 |

Each spot gives the solver one bet size, plus all-in in preflop trees, which allow at most 2 raises.

## Caching layers

1. The `SolverAdapter` cache is a `DiskSolveCache` (memory LRU of 256 entries in front of JSON
   files), keyed by the full `params_hash`. Changing any solve param or spot input is a different
   key and triggers a new solve.
2. Disk entries record a schema (`practice-solve-cache-v1`) and the `solver_version`. A mismatched,
   corrupt or oversized file (> 64 MiB) counts as a miss and is deleted. An entry is written only
   if it round-trips exactly, with floats compared exactly.
3. If the cache directory is unusable, the cache degrades to memory-only (`disk_ok: False`) and no
   solve is lost.

## Progress store

The `attempts` table has the columns user, spot_id, family, street, game_type, score, grade,
ev_loss_pct, params_hash and ts. Only `practice-submit-play` writes to it, using the score
`score_play` computed from the real solve. Clients cannot send a score. The store opens lazily on
first use. If it cannot open or record, the submit still returns 200 with `progress: null`.

## UI (`web/`)

The UI is static and has no build step. It renders values with `textContent` only, under a strict
same-origin CSP. It contains:

- A spot list with family, street and game-type filters. The filter values come from the API.
- A felt table with board and hero cards, plus 1 or 2 villains.
- Action buttons with a size input and presets. Keyboard shortcuts are f, c, b and Enter.
- An iterations override with a Re-solve button.
- A result panel: score ring, grade, EV loss, optimal-mix bar, Q table, range strategy and provenance.
- `#progress-panel` and `#leaderboard-panel`.
- `#user-input`, stored in localStorage under `practice.user`.

During a long solve the UI shows `Solving… Ns`. After 10 s it adds "(server limit 90 s)".

## Tests

Practice tests live in `tests/test_practice_*.py`. The benchmark test is `tests/test_solver_evaluation.py`.
`tests/conftest.py` points `POKER_PRACTICE_CACHE_DIR` and `POKER_PRACTICE_DATA_DIR` at a
per-session temp dir, so tests never write to `~/.cache` or `~/.local`.
