# PRACTICE_MODE_DESIGN.md — GTO Wizard Practice Mode Clone (Wave 0, parent-authored)

Status: AUTHORITATIVE Wave-0 design. Design-wave reports (research/practice-mode/design/01..06)
may refine it. They do not override it unless the parent reconciles the change into this file.
Branch: `feat/practice-mode`. Rollback tag: `practice-mode-baseline`. Baseline gate: 817 passed.

## 0. Non-negotiables
1. Every optimal strategy, optimal size, action EV and score comes from a solver solve run when
   the spot is used, or from a content-addressed cache of that solve. No hand-written answers, no
   literal strategy tables in source, tests or fixtures.
2. Every solved artifact carries `SolveProvenance`: backend, entrypoint, the full canonical solve
   params, `params_hash` (sha256 of canonical JSON), algorithm, iterations, seed, nash_conv,
   wall_time_s and solver package version. The UI and CLI must be able to display it.
3. A permanent test asserts that changing `iterations`, a range, the pot or the stack changes the
   optimal strategy and/or the score, and that `params_hash` changes too.
4. Code standard: frozen dataclasses, `MappingProxyType`/tuple defensive copies, fail-closed
   `ValueError` validation (bool is not int), no bare `except Exception`, deterministic seeds,
   docstrings. Use only the stdlib plus what is already in the repo.

## 1. Solver surfaces used (verified in Wave 0)
- `river.RiverConfig(board[5], pot: float, stack: int, bet: int, range0, range1)` + `river_root`
  -> heads-up river with a single bet size. P0 acts first (OOP).
- `allstreet.AllStreetPostflopConfig(version="allstreet-postflop-v1", starting_board[3],
  initial_dead_pot, effective_stack, player0_combos, player1_combos, allowed_runouts,
  betting_mode, wager_targets, max_nodes, max_depth)` + `solve_allstreet_postflop(config,
  algorithm, iterations, seed)` -> `AllStreetSolveResult` (strategy Mapping[InfoKey ->
  Mapping[Action, p]], values, nash_conv). Also `create_allstreet_root(config)` for walking.
- `api_v4.dispatch_v4({"version": 4, "operation": op, "payload": {...}})` with ops
  `solve-allstreet-postflop`, `solve-nplayer-postflop`, `solve-nplayer-preflop`. The version must
  be the JSON integer 4. Flat payload.
- `cfr.CFRSolver(root).train(n)` -> average strategy; `cfr.expected_values(root, profile)`;
  `best_response.nash_conv(root, profile)`, `best_response(root, profile, player)`.
- `kuhn.kuhn_root()`, `KUHN_VALUE_P0 = -1/18`; `equity.WeightedCombo(cards, weight)`;
  `cards.parse_card/format_card`; `model.Action(kind, amount?)`, `CHANCE=-1`, `TERMINAL=-2`,
  the `GameState` protocol.
- `nplayer_preflop` / `nplayer_postflop` (3-max) via `dispatch_v4`. Their payload schemas are in
  `api_v4._dispatch_nplayer_*`.

## 2. Package layout: `src/poker_solver/practice/`
| module | responsibility |
|---|---|
| `spot.py` | `PracticeSpot`, `SolveParams`, `HeroDecision`, canonical JSON + `params_hash` |
| `adapter.py` | `SolverAdapter`: turns a PracticeSpot into a solver call and returns a `SolvedSpot` |
| `evaluate.py` | action-value (Q) computation at hero decision infosets under the solved profile |
| `scorer.py` | `score_play(solved, play) -> PlayScore` (EV loss, score, grade, feedback) |
| `catalog.py` | generator for spot families (parameter grids, seeded) -> `tuple[PracticeSpot,...]` |
| `progress.py` | `ProgressStore` (JSON file, atomic write, per-spot attempts/best/history) |
| `cache.py` | content-addressed solve cache keyed by `params_hash` (opt-in dir; default in-memory) |
| `service.py` | stateless facade used by the API, CLI and HTTP server (list/solve/submit/progress) |
| `server.py` | stdlib `http.server` JSON API + serving of static `web/` |
| `web/index.html`, `web/app.js`, `web/style.css` | minimal UI that only consumes the API |

## 3. Data model (frozen dataclasses)
```
SolveParams: algorithm ("vanilla-cfr"|"external-sampling-mccfr"), iterations:int>0, seed:int|None
PracticeSpot:
  spot_id: str              # = family + "/" + params_hash[:12]  (derived, never hand-typed)
  family: str               # e.g. "river-oop-bet-or-check"
  backend: "kuhn"|"river"|"allstreet"|"nplayer-preflop"
  game_type: "heads-up"|"3-max"
  street: "preflop"|"flop"|"turn"|"river"
  board: tuple[int,...]     # 0/3/5 cards depending on street
  hero_seat: int; villain_seats: tuple[int,...]
  ranges: tuple[tuple[WeightedCombo,...], ...]   # per seat
  pot: int|float; stacks: tuple[int,...]
  action_history: tuple[Action,...]               # public line leading to the decision
  bet_sizes: tuple[int,...] # abstraction offered to the solver (wager targets)
  hero_hand: tuple[int,int]|None  # concrete dealt hand for the drill (sampled from the range by seed)
  solve: SolveParams
  backend_extra: Mapping[str, Any] (frozen; e.g. allowed_runouts, betting_mode, max_nodes)
  def canonical() -> dict ; def params_hash() -> str
SolvedSpot:
  spot: PracticeSpot; provenance: SolveProvenance
  decision: DecisionPoint   # hero's infoset at the drill node
  strategy: Mapping[Action, float]          # optimal mix for hero_hand at that infoset
  action_values: Mapping[Action, float]     # Q(a), chips, hero perspective
  range_strategy: Mapping[str(hand), Mapping[Action, float]]  # whole-range view for the UI grid
  optimal_action: Action; optimal_size: int|None
Play: action kind + optional amount, OR a mixed {Action: prob} (validated, sums to 1 ±1e-9)
PlayScore: ev_loss_chips, ev_loss_pct_pot, score (0..100), grade, chosen_q, best_q,
  solver_mix_q, solver_self_loss, feedback: str, mapped_action (when off-tree size is snapped),
  provenance (same object as SolvedSpot)
```
InfoKey matching: the adapter finds the hero infoset by walking the solver tree with the spot's
action_history and hero_hand. It must not parse `str(InfoKey)` heuristics where the tree walk is
available. The tree walk is authoritative.

## 4. Solver adapter contract
`SolverAdapter.solve(spot) -> SolvedSpot`. Routing:
- `kuhn`: `kuhn_root` + CFRSolver (verification/tutorial family; hero_hand is J/Q/K).
- `river`: `RiverConfig` + `CFRSolver.train(iterations)` (vanilla only).
- `allstreet` (flop; turn via one allowed turn card fixed into the start board if MultiStreetConfig
  supports `starting_street="turn"`, otherwise PARTIAL and documented): `solve_allstreet_postflop`.
- `nplayer-preflop` (3-max): `dispatch_v4` with `solve-nplayer-preflop`, so the envelope is used
  at least once end-to-end.
The adapter always returns the solver's average strategy. It never post-edits probabilities
except to drop exact-zero noise when displaying. It records `nash_conv` when the backend
exposes it.

## 5. Scoring metric (EV loss vs the solver's optimal strategy)
Let sigma* be the solved average profile. At hero decision infoset I with dealt hand h:
- Q(a) = hero expected payoff (chips) of taking a at I, then everyone (hero included) follows
  sigma*. Opponent hands are weighted by their range weights times their sigma* reach to I, and
  chance is weighted by its probabilities. Computed in `evaluate.py` by an exact tree walk
  (counterfactual value / opponent reach mass).
- best_q = max_a Q(a). solver_mix_q = sum sigma*(a)Q(a). solver_self_loss = best_q - solver_mix_q
  (0 at an exact equilibrium; grows at low iterations and is displayed as solver noise).
- User play pi_u: a pure action (pi_u = delta_a) or a mix. chosen_q = sum pi_u(a)Q(a).
- **EV loss** = max(0, best_q - chosen_q). This is the GTO-Wizard convention: an action in the
  equilibrium support has ~0 loss. ev_loss_pct_pot = 100 * EV loss / pot_at_decision.
- **Score** = 100 * max(0, 1 - EV loss / max(best_q - min_a Q(a), eps)). If every action has
  equal Q, score = 100.
- **Grade** by ev_loss_pct_pot: <=0.25 Perfect, <=1 Good, <=3 Inaccuracy, <=8 Mistake, else
  Blunder.
- **Off-tree size**: snap to the nearest abstraction size (ties go to the smaller size) and
  report `mapped_action` with `size_mapped=True`. Never invent an EV for an unsolved size.
- Feedback text is generated from the numbers only: the optimal action, the size, the mix, the
  EV delta and the most-weighted alternative.
Exact-zero check: Kuhn at many iterations => solver_self_loss < 1e-3; the river toy (sec. 8)
=> Q(bet) ~= Q(check) for bluff-catchers at indifference.

## 6. Spot catalog generator
`generate_catalog(families=..., seed=0, solve=SolveParams(...)) -> tuple[PracticeSpot, ...]`.
Each family is a parameter grid, not a puzzle list:
- `kuhn-intro`: hero in {P0, P1} x card {J,Q,K} x public node.
- `river-oop-bet-or-check`, `river-ip-facing-bet`: boards sampled by seed, ranges from
  `ranges.py`/`presets.py` expressions (polar vs bluff-catcher, merged vs condensed), pots/stacks
  from a SPR grid, bet in {33%, 75%, 125% pot}.
- `flop-cbet-small-tree`: allstreet, 3-card board, <=2 runouts, 1-2 wager targets, max_nodes
  bounded for <~10 s solves.
- `preflop-3max-open`: nplayer-preflop BTN/SB/BB open/fold spots from the existing payload schema.
Hero hands are sampled with `random.Random(seed)` from range combos that do not collide with the
board. spot_id is derived from params_hash, so it is stable and unique. Tests forbid literal
strategies in catalog.py (AST/grep test: no float-probability dict literals).

## 7. API / CLI / UI surface
- api_v4 new ops (same strict envelope, version 4): `practice-list-spots` {families?, seed?,
  limit?}, `practice-solve-spot` {spot | spot_id+catalog params}, `practice-submit-play`
  {spot_id, play, user?}, `practice-progress` {user?}, `practice-leaderboard` {}. The parent owns
  integration into `api_v4.py` (a shared file). Practice logic lives in `practice/service.py`.
  Responses are JSON-safe and include `provenance`.
- CLI: `poker-solver practice list|solve|submit|progress|leaderboard|serve` (the parent integrates
  into `cli.py`; handlers live in `practice/cli.py`). The progress file path comes from
  `--store` or `$POKER_PRACTICE_STORE`, defaulting to `~/.local/share/poker-solver/practice.json`.
- Web UI: `practice serve --port 8787` serves `web/` plus `/api/v4` POST (the same dispatch). The
  page lists spots, shows board/pot/stacks/history/hero hand, offers action buttons and a size
  input generated from the solved action set, and after submit shows the score, grade, EV loss,
  the optimal mix bar, a whole-range strategy table and the provenance. No answers live in the JS.

## 8. Solver evaluation (`research/solver-evaluation/`)
`benchmark.py` (reproducible, seeded, writes `results.json` + `results.md`) plus a permanent test
module for fast checks. Independent references, never the solver's own output:
1. Kuhn: game value -1/18; alpha-family equilibrium constraints (P0 bets J with alpha<=1/3, K with
   3*alpha, calls Q with alpha+1/3); exploitability -> 0 over iterations (log-log slope).
2. Polarized river toy (nuts/air vs bluff-catcher), analytic: bluff ratio b/(p+2b) and call
   frequency p/(p+b) for several sizes => checks sizing sensitivity.
3. Equity: `scripts/crosscheck_treys.py` style comparison and hand-computed preflop all-in EVs.
4. Best response: exhaustive vs fast BR agreement; nash_conv monotone trend; CFR vs MCCFR
   agreement within a derived tolerance.
5. n-player: 3-player Kuhn (known equilibrium family; P1 value -1/48, to be verified against the
   cited source before use) or exact 3-max preflop push/fold checks; ICM vs hand-computed
   Malmuth-Harville.
6. Timing/scaling table (nodes, infosets, seconds per iteration) per backend; all-in and edge
   cases.
Verdict table per capability: 2-player NL, 3-max, preflop, postflop, multi-street, ICM, mixed
strategy, sizing => PASS / PARTIAL / FAIL with the evidence row ids and a concrete gap list.
This goes into `PRACTICE_MODE_REPORT.md`.

## 9. Test plan (permanent, production-importing; files owned per wave)
- `tests/test_practice_spot.py`: validation, immutability, canonical/hash stability.
- `tests/test_practice_adapter.py`: each backend solves; strategy sums to 1; provenance present.
- `tests/test_practice_scorer.py`: Kuhn/river-toy exactness, off-tree snapping, mixed plays, grades.
- `tests/test_practice_catalog.py`: determinism by seed, unique ids, no literal strategies.
- `tests/test_practice_no_hardcode.py`: **changing iterations / range / pot / stack changes the
  strategy or score and params_hash** (the required DoD test).
- `tests/test_practice_progress.py`: persistence, atomic write, best/attempts, corrupt-file
  fail-closed.
- `tests/test_practice_api.py`, `tests/test_practice_cli.py`, `tests/test_practice_server.py`
  (HTTP round trip on an ephemeral port), `tests/test_solver_evaluation.py`.
All practice tests use small trees and must add <60 s to the full suite.

## 10. Wave plan and ownership
- Design wave (6, read-only on src): 01 scorer/metric, 02 adapter+evaluate, 03 spot/catalog,
  04 API/CLI/progress, 05 web UI + test plan, 06 solver-evaluation benchmark. Reports go to
  `research/practice-mode/design/0N-*.md`.
- Impl wave A (6): spot.py | adapter.py+cache.py | evaluate.py | scorer.py | catalog.py |
  progress.py, each paired with its own test file. The parent integrates `practice/__init__.py`.
- Impl wave B/C (6): service.py | practice/cli.py | server.py | web/* | solver-evaluation
  benchmark | evaluation tests. The parent integrates `api_v4.py`, `cli.py`, `__init__.py`.
- After every batch: a frozen manifest at `research/practice-mode/<wave>-audit/CANDIDATE_MANIFEST.md`,
  then 6 non-author auditors on a different model than the author. Repair only reproduced
  findings, re-audit, commit.
- Finish: docs (`PRACTICE_MODE.md`, `PRACTICE_MODE_REPORT.md`, STATE/PROGRESS), full suite
  green, tag `practice-mode-done`.
