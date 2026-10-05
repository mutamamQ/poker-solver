# W1 task-1 — practice data model, catalog, adapter, evaluator

Status: DONE. Files (all new): `src/poker_solver/practice/{__init__,models,catalog,adapter,evaluate}.py`,
`tests/test_practice_{models,catalog,adapter,no_hardcode}.py`.
Stdlib only; no strategy/probability literals anywhere; every answer comes from a runtime CFR solve.

## Public API

### `poker_solver.practice.models`
- Constants: `SPOT_FORMAT="practice-spot-v1"`, `ALGORITHMS`, `BACKENDS`, `GAME_TYPES`, `STREETS`,
  `KUHN_CARDS=("J","Q","K")`, `EXTRA_KEYS` (backend_extra allowlist).
- `SolveParams(algorithm="vanilla-cfr", iterations=200, seed=None)` — frozen; vanilla requires
  seed None, MCCFR requires int seed; `.canonical()`, `SolveParams.from_json(d)`.
- `PracticeSpot(family, backend, game_type, street, board, hero_seat, villain_seats, ranges, pot,
  stacks, action_history, bet_sizes, hero_hand, solve=SolveParams(), backend_extra={})` — frozen, slots.
  - Derived: `spot_id` = `family + "/" + sha256(canonical minus "solve")[:12]`; `params_hash()` =
    sha256 of full canonical JSON (sort_keys, `(",",":")`), includes solve.
  - `.canonical()` (fresh dict, keys: format, family, backend, game_type, street, board, hero_seat,
    villain_seats, ranges[[{cards,weight}]], pot(float), stacks, action_history[{kind,amount}],
    bet_sizes, hero_hand, solve, backend_extra), `.with_solve(SolveParams)`, `.to_json()` (canonical +
    spot_id, params_hash, board_str, hero_hand_str, label), properties `hero_hand_str`, `label`.
  - Validation (ValueError, bool≠int): enums & backend/game/street compatibility; board length by
    street; cards 0..51 unique; villain_seats exactly the other seats; pot finite>0 (normalized to
    float); stacks positive ints, equal for heads-up; bet_sizes unique increasing ≤ stack; ranges are
    `WeightedCombo`, weight in [0,1], duplicates rejected, zero-weight/board-blocked combos dropped,
    sorted, each side non-empty; hero_hand in sanitized hero range, off board, not blocking every
    villain combo; backend_extra keys allowlisted and recursively frozen JSON.
  - Kuhn: `hero_hand=None`, `backend_extra={"kuhn_card": J|Q|K}`, empty board/ranges, pot 2, stacks
    (1,1), bet_sizes (1,), history must be one of the 4 nonterminal nodes with hero acting.
  - River: exactly one bet size, history must be a nonterminal node of the one-bet tree with hero acting.
  - Allstreet: flop only (turn -> ValueError "turn start unsupported by allstreet facade (PARTIAL)"),
    extra must have allowed_runouts, betting_mode, max_nodes, max_depth; integer-valued pot.
- `SolveProvenance(backend, entrypoint, params, params_hash, algorithm, iterations, seed, nash_conv,
  wall_time_s, solver_version)` + `.to_json()`.
- `SolvedSpot(spot, provenance, legal_actions, pot_at_decision, info_key, strategy, action_values,
  range_strategy, optimal_action, optimal_size)` — validates policy coverage/sum, finite Q,
  provenance hash == spot hash, optimal_size consistency. `.to_json()` keys exactly: spot, provenance,
  legal_actions, pot_at_decision, strategy[{action,probability}], action_values[{action,q}],
  range_strategy[{hand,strategy}], optimal_action, optimal_size (legal-action order everywhere).
- Helpers: `action_to_json(Action)`, `action_from_json(dict)`, `format_hand(cards) -> "AsKd"`.

### `poker_solver.practice.evaluate`
- `action_values(root, profile, hero, target_key) -> (MappingProxyType[Action,float], mass)` —
  exactly report 01 §3 (chance × opponent reach, hero reach excluded; fsum; ValueError on zero
  mass, inconsistent actions, missing/invalid policy, bool hero).
- `subtree_value(state, profile, hero) -> float`; `checked_policy(state, profile, player)`.

### `poker_solver.practice.adapter`
- `SolverAdapter(cache=None, timeout_s=60.0)`: `.solve(spot) -> SolvedSpot`, `.cached(spot)`,
  `.solve_count`. Dict cache keyed by params_hash under a `threading.Lock` (concurrent misses may both
  solve; first stored result wins and is returned to all).
- `solve_spot(spot)` — module default adapter. `solver_version()`; `ENTRYPOINTS`;
  `locate_decision(root, spot, hand, backend) -> HeroDecision|None`; `HeroDecision(info_key,
  legal_actions, pot_at_decision)`.
- Routing: kuhn → `kuhn_root + CFRSolver.train`; river → `RiverConfig + river_root +
  CFRSolver.train`; allstreet (flop) → `solve_allstreet_postflop` then `create_allstreet_root` for the
  walk. nplayer-preflop → ValueError (not routed, PARTIAL).
- Hero infoset: tree walk over each root deal whose hero private hand matches, replaying
  action_history by exact `Action` membership; all compatible deals must yield one key. No str parsing.
- range_strategy: same walk for every hero-range combo (Kuhn: J/Q/K); combos blocked by every villain
  combo are omitted (they never reach the node).
- optimal_action = max probability, ties by legal order; optimal_size = amount for sized bet/raise.
- Provenance: entrypoint string, `nash_conv(root, profile).nash_conv`, measured wall_time_s,
  importlib.metadata version or "unknown".
- Budget: CFR trained in chunks of 25 iterations; exceeding timeout_s → ValueError, nothing cached.

### `poker_solver.practice.catalog`
- `FAMILIES = ("kuhn-intro", "river-oop-bet-or-check", "river-ip-facing-bet")`.
- `generate_catalog(families=None, seed=0, solve=None, limit=None)` → 36 spots (12 Kuhn + 12 + 12
  river), ~10 ms, no solving. `find_spot(spot_id, families=None, seed=0, solve=None)`.
- River grid: range shape {polar-vs-catchers, merged-vs-condensed} × pot {100, 200} × bet {33,75,125}%
  pot (bet = (pot*pct+50)//100), stack = 2×pot. Per-cell RNG = sha256([seed, family, axes]); board
  via `rng.sample(range(52),5)` (≤64 retries); 4 combos per side sampled from
  `ranges.import_range_text(...).blocked(board)`; hero hand via `rng.choices` weighted by range weight.
- Also exported: `RANGE_SHAPES`, `RIVER_BET_PCTS`, `RIVER_POTS`, `RIVER_SPR`, `RIVER_COMBOS_PER_SIDE`, `river_ranges`.

## Deviations / decisions
- Module named `models.py` (per task contract) rather than design's `spot.py`. No `HeroDecision` in
  models; a minimal `HeroDecision` lives in adapter.py. SolvedSpot has flat `legal_actions`/`info_key`/
  `pot_at_decision` instead of a `decision` object.
- spot_id excludes `solve` (owner-approved refinement).
- `flop-cbet-small-tree` (allstreet) NOT in the catalog: PARTIAL. The adapter route works and is tested
  on a tiny hand-built spot (2×2 combos, 1 runout, 1 wager target, ~0.3 s at 15 iterations), but
  report 02 measured ~9.6 s at 200 iterations for a 2-combo/1-runout tree, too slow for the catalog
  default. `preflop-3max-open` not implemented (out of scope for this task's routing list).
- Kuhn BET is `Action("bet", 0)` (unsized) → `optimal_size=None` even though the kind is bet.
- River combos per side = 4 (not 4–8): measured 200-iteration solves are 0.6–1.6 s at 4×4; 5×5 was
  ~2.1 s, over the 2 s budget.
- Kuhn self-loss: report 01 already showed per-infoset self_loss < 1e-3 is NOT met by all infosets at
  2000 iterations (P0 Q facing bet ≈ 1.6e-2). The test instead asserts: self_loss ≥ 0; mass-weighted
  self-loss per player ≤ that player's NashConv incentive (+1e-3); ≥ 6 of 12 infosets < 1e-3; total
  self-loss decreases from 200 to 2000 iterations.
- No-hardcode (b): river pot ×3 and villain/hero range narrowing are used. Stack is NOT used because
  RiverState payoffs don't depend on stack once stack ≥ bet (report 02 §2.2).
- backend_extra for river carries descriptive metadata (bet_pct, spr, range_shape, cell_seed); it's
  part of identity but not passed to the solver.

## Tests
- 69 tests in the four practice files; ~9 s total (slowest: no-hardcode (a) river at 300 iterations ≈ 2.2 s each).
- Full suite (`.venv/bin/python -m pytest -q`): **988 passed, 2 failed in 241 s**. Both failures are in
  `tests/test_practice_api.py`, which belongs to another worker and was untracked/in progress at the time:
  `test_http_solve_and_submit` and `test_http_r1_iterations_change_answer`. That test sends
  `solve: {"iterations": N, "seed": 7}` with the default vanilla algorithm. `SolveParams` rejects that
  with "vanilla-cfr requires seed=None", following reports 02 and 03. **Parent decision needed:** either the
  api layer drops/ignores `seed` for vanilla, or SolveParams accepts it. I kept it strict, because otherwise
  a seed that has no effect would still change params_hash. Baseline 817 + my 69 all pass.
