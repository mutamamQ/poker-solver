# W4 task A — four solver-backed practice families

Owner files: `src/poker_solver/practice/{models,catalog,adapter}.py`, new `tests/test_practice_families.py`.
`evaluate.py` needed no change (its Q computation is already N-player generic: counterfactual weight =
chance reach x product of all opponents' reach). Minimal expectation updates in two existing tests
(see "Other test edits").

## Families (catalog grows 36 -> 72 spots)

| family | backend | game_type / street | spots | grid (deterministic from `seed` via sha256 cell RNG) | default solve |
|---|---|---|---|---|---|
| `preflop-hu-open` | `nplayer-preflop` | heads-up / preflop | 12 | 2 range shapes x stacks {30,50} x open-to {4,5,6} chips; hero BTN/SB first in; 5 combos per seat | vanilla-cfr, 300 it |
| `preflop-3max-open` | `nplayer-preflop` | 3-max / preflop | 8 | {BTN first-in, SB after BTN fold} x 2 shapes x open-to {5,6}; stack 40; 3 combos per seat; `villain_seats` 2 entries, `stacks` 3 entries | vanilla-cfr, 100 it |
| `flop-cbet` | `allstreet` | heads-up / flop | 8 | {OOP first, IP after CHECK} x 2 range shapes x bet {33,75}% pot; pot 100, SPR 2; 3 combos/side; 2 (turn,river) runouts | vanilla-cfr, 200 it |
| `turn-barrel` | `multistreet` | heads-up / turn | 8 | same roles/shapes/sizes; 4 combos/side; 4 river runouts; river betting on | vanilla-cfr, 200 it |

Blinds are 1/2 chips (`models.PREFLOP_BLINDS`), pot = 3, button = seat 0. Preflop open sizes are raise-to chips
(converted to a `big-blinds` sizing expression for the solver); all-in is always also offered by the solver,
max 2 raises. Range choice (which hands are dealt) is by class text through `ranges.import_range_text`;
seats draw sequentially from the unused deck so every deal is compatible. Postflop runout cards avoid all
range cards. No probabilities / EVs exist anywhere in the catalog.

`FAMILY_DEFAULT_SOLVE` gives each family its default; with `generate_catalog(solve=None)` each family uses
its own default. Legacy families still default to `SolveParams()` → **legacy spot_ids and params_hashes
are byte-identical** (verified: sha256 of the 36 ids for seeds 0 and 1 equals the HEAD tree's output).
An explicit `solve=` still applies to every family; `spot_id` never depends on solve.

## Models
- `BACKENDS` += `multistreet`; `_BACKEND_SHAPE` now maps backend -> (allowed game types, streets):
  `nplayer-preflop` -> heads-up **and** 3-max / preflop; `multistreet` -> heads-up / turn. allstreet+turn still
  rejected (message points to `multistreet`).
- New `backend_extra` keys `max_raises` (<=4), `equity_samples` (<=5000). Preflop validation: pot == blinds,
  stacks and open sizes > big blind, actions in {FOLD,CHECK,CALL,RAISE}. Runout validation shared by
  allstreet (2-card) and multistreet (1-card), duplicates rejected.
- Preflop label: `Preflop 3-max BTN with KhKs; blinds 1/2, stack 40, open to 5; line: ...`.

## Adapter
- `nplayer-preflop`: `preflop_config(spot)` builds `NPlayerPreflopConfig`. Closed multi-way leaves are
  valued by a **runtime** equity table: for each compatible deal, `equity_samples` (256) boards are drawn with a
  seed = sha256(deal) and ranked with `evaluator.evaluate_seven`; side pots / odd chips via
  `game_structure.build_pot_layers/award_pot_layers`; exact `Fraction` utilities (zero-sum checked) supplied as
  a `terminal-table` continuation. Solved with `nplayer.NPlayerCFRSolver.train` (chunked, timeout-checked).
  NashConv is reported for heads-up; `None` for 3-max (two-player best response is undefined for 3).
- `multistreet`: `MultiStreetConfig(starting_street="turn", river_betting=True)` -> `validate_bounded_tree` ->
  `cfr.CFRSolver` -> `nash_conv`.
- `allstreet`: same steps as `solve_allstreet_postflop` (bounded-tree validation, CFR/MCCFR,
  `complete_strategy`, NashConv) run over a memoized root. Test asserts the profile and NashConv equal the
  facade's exactly. Entry-point string updated accordingly.
- `CachedState`: transparent memoizing proxy over the immutable game states (children, legal actions, keys,
  returns). Values are identical (verified: 3-max profile diff vs uncached facade = 0.0); speed-up 30-50x for
  nplayer-preflop (validation in `NPlayerPreflopState.__post_init__` re-enumerates deals on every child) and
  ~5x for allstreet.
- `SolvedSpot.info_key` is now `portable_key(raw_key)` (dataclasses such as `ForcedPost` /
  `NPlayerPreflopPublicAction` -> `(TypeName, *fields)` tuples) so new-family solves round-trip through task B's
  `DiskSolveCache` (tested). Lookups still use the raw solver key.
- `ENTRYPOINTS` has entries for all 5 backends.

## Measured cold solve times (family default iterations, `SolverAdapter.solve`, this 2-vCPU QEMU host)

Host load average was 2-8 during measurement (other jobs running), so these are pessimistic.

| family | iterations | spots timed | min s | max s | notes |
|---|---|---|---|---|---|
| preflop-hu-open | 300 | 12/12 | 4.5 | 9.8 | (load ~8) |
| preflop-3max-open | 100 | 8/8 | 6.6 | 10.0 | ~1 s equity table + ~5.5 s CFR |
| flop-cbet | 200 | 8/8 | 2.8 | 4.1 | before memoization: 13.8-43 s at 120-200 it |
| turn-barrel | 200 | 8/8 | 2.5 | 5.4 | |

All are within the 20 s budget. 3-max stays at 100 iterations: at 200 it measured 14-28 s under load, too close
to the limit. Flop/turn were not dropped. Range sizes were chosen from prototypes: flop with 2 bet sizes
measured 147 s, so each spot uses one bet size (plus all-in).

## Tests — `tests/test_practice_families.py` (24 tests, ~27 s, no skips)
- Registration; legacy 36 spots keep `SolveParams()`.
- Per family: 8-12 spots, unique ids and hashes, deterministic, independent of other families requested,
  seed-sensitive, `spot_id` stable under solve changes, shape (backend/game_type/street/board length/seat
  counts), every contract JSON key present, `find_spot` round trip.
- 3-max: two villains and both hero situations.
- Validation of the new backends.
- Per family end-to-end solve via `SolverAdapter`: probabilities sum to 1 over legal actions; range
  strategies valid; finite Q; provenance; open size offered; cache hit.
- 3-max SB-after-fold: Q-values and strategy recomputed independently (raw `NPlayerCFRSolver` +
  `evaluate.action_values`) and checked equal.
- The memoized allstreet route equals the `solve_allstreet_postflop` facade exactly.
- The preflop equity table is computed at runtime, is zero-sum, and changes with `equity_samples`.
- **R1 per family**: same spot_id, 3 vs N iterations -> strategy/Q and range strategy change. Range width
  (villain combo dropped, or hero range = dealt hand) -> answer changes (scans the first 3 spots, because one
  flop cell is degenerate for single-combo drops).
- Disk-cache round trip for 3-max and turn solves.

## Other test edits (expectations only)
- `tests/test_practice_catalog.py::test_families_and_size`: upper bound 40 -> 100 (catalog is now 72).
- `tests/test_practice_adapter.py`: ENTRYPOINTS set now includes `nplayer-preflop`, `multistreet`; allstreet
  entry-point assertion now uses `startswith` for the new pipeline string.

## Test results
- `.venv/bin/python -m pytest -q tests/test_practice_*.py` -> **314 passed** in 74.6 s (exit 0).
- `.venv/bin/python -m pytest -q` (full suite) -> **1131 passed, 1 failed, 4 errors** in 461 s. All 5 non-passes are
  in `tests/test_solver_evaluation.py` (another agent's untracked benchmark work):
  `FileNotFoundError: research/solver-evaluation/benchmark.py` (the file does not exist yet). That is unrelated to
  this task. Every other test passes, including the baseline 1026 and the tests the other W4 agents added.
