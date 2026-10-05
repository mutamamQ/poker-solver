# W1 task-2 — practice scoring, API handlers, CLI smoke

Files (owned): `src/poker_solver/practice/scoring.py`, `src/poker_solver/practice/api.py`,
`tests/test_practice_scoring.py`, `tests/test_practice_cli_smoke.py`, this file.
Imports task-1 modules (`models`, `catalog`, `adapter`) directly; no shims.

## Scoring (`scoring.py`)
Exactly PRACTICE_MODE_DESIGN.md §5, **no score floor** (report 01 finding 3 floor proposal NOT adopted):
`best_q=max Q`, `worst_q=min Q`, `spread=best_q-worst_q`, `solver_mix_q=Σσ*Q`,
`solver_self_loss=best_q-solver_mix_q` (ArithmeticError if < -1e-9, then clamped to 0),
`chosen_q=Σπ_u Q`, `ev_loss=max(0,best_q-chosen_q)`, `pct=100·loss/pot_at_decision`,
`score=100 if spread<=1e-12 else 100·max(0,1-loss/spread)`. Grades inclusive on unrounded pct:
≤0.25 Perfect, ≤1 Good, ≤3 Inaccuracy, ≤8 Mistake, else Blunder. All Q from `solved.action_values`.

API: `parse_play(obj, legal) -> ParsedPlay`, `score_distribution(q, sigma, pot, parsed, legal, provenance)`
(pure), `score_play(solved, play_json_or_ParsedPlay) -> PlayScore`, `grade_for(pct)`.

Decisions:
- Pure play `{kind, amount?}`: amount omitted → the unique legal action of that kind; if several sizes of that
  kind exist, ValueError (ambiguous). Mix entries require both `kind` and `amount` (report 04).
- Snapping only for kinds `bet/raise/BET/RAISE` whose kind is legal; nearest size, tie → smaller. Unsized
  kinds with a non-legal amount → ValueError. Snapped mix duplicates are merged (probabilities summed);
  duplicate *requested* actions → ValueError. Probabilities finite, ≥0, Σ=1 ±1e-9, no renormalisation.
- `mapped_action` is set only for a snapped pure play (per report 04); for mixes see `mappings`.
  `size_mapped` is true whenever any snap happened.
- Added fields beyond the brief: `best_action` (argmax Q, legal-order tie-break; report 01 §4) and
  `mappings` list. `play` = canonical evaluated play (after snapping/merging).
- Feedback template (numbers only): `Solver: <mix sorted by p desc>. You: <play>[ (mapped from X -> Y)].
  EV loss L chips (P% pot) -> Grade. Best EV action: A (Q=+q)[; most-weighted alternative: B (Q=+q)].
  [ Solver noise: S chips.]` (noise note when self_loss > 0.25% pot).

## API (`api.py`)
`PRACTICE_OPERATIONS`, `handle_practice(operation, payload)`, `main(argv)`. Module-level `_ADAPTER =
`SolverAdapter()` caches by params_hash. `solve` override: `{algorithm?, iterations?, seed?}` (omitted
fields take the `SolveParams()` defaults vanilla-cfr/200/null — relaxed so the HTTP test client's
`{iterations, seed}` shape parses; iterations 1..20000; SolveParams enforces vanilla→seed null,
MCCFR→int seed; adapter currently rejects MCCFR with ValueError). Catalog `seed` default 0, `families`
must be non-empty, unique, known. Unknown/missing keys, bool-as-int → ValueError. Every response passes
`json.dumps(allow_nan=False)` (checked in `_check_json`, ValueError otherwise). `user` defaults `"local"`
and is echoed only (no persistence in this task — progress is a later task).

### Envelope (all ops)
```
{"version": 4, "operation": <op>, "result": <below>, "provenance": <Provenance|null>}
```
`Action = {"kind": str, "amount": int}`;
`Provenance = {backend, entrypoint, params:<spot canonical>, params_hash, algorithm, iterations, seed,
nash_conv:float|null, wall_time_s, solver_version}`.
`Spot = {format, family, backend, game_type, street, board:[int], hero_seat, villain_seats:[int],
ranges:[[{cards:[int,int], weight}]], pot:float, stacks:[int], action_history:[Action], bet_sizes:[int],
hero_hand:[int,int]|null, solve:{algorithm, iterations, seed}, backend_extra:{...}, spot_id, params_hash,
board_str:[str], hero_hand_str:[str], label}` (from task-1 `PracticeSpot.to_json`).

### practice-list-spots — payload `{families?:[str], seed?:int, limit?:int>=1}`
```
result = {"spots": [Spot, ...], "families": [str, ...]}     provenance = null
```
`families` echoes the request, or all `catalog.FAMILIES` when omitted. No solving.

### practice-solve-spot — payload `{spot_id:str, families?, seed?, solve?:SolveParams}`
```
result = SolvedSpot = {
  "spot": Spot, "provenance": Provenance,
  "legal_actions": [Action], "pot_at_decision": float,
  "strategy": [{"action": Action, "probability": float}],
  "action_values": [{"action": Action, "q": float}],
  "range_strategy": [{"hand": str, "strategy": [{"action": Action, "probability": float}]}],
  "optimal_action": Action, "optimal_size": int|null }
provenance = Provenance (== result.provenance)
```
With a `solve` override, `spot.spot_id` is unchanged and `params_hash` changes.

### practice-submit-play — payload `{spot_id, play:Play, families?, seed?, solve?, user?:str}`
`Play = {kind, amount?} | {"mix": [{"action": {kind, amount}, "probability": number}, ...]}`
```
result = {
  "user": str,
  "score": {
    "ev_loss_chips": float, "ev_loss_pct_pot": float, "score": float, "grade": str,
    "chosen_q": float, "best_q": float, "worst_q": float,
    "solver_mix_q": float, "solver_self_loss": float,
    "best_action": Action, "feedback": str,
    "mapped_action": Action|null, "size_mapped": bool,
    "play": Action | {"mix": [{"action": Action, "probability": float}]},
    "mappings": [{"requested": Action, "mapped": Action}],
    "provenance": Provenance },
  "solved": SolvedSpot }
provenance = Provenance (== result.score.provenance == result.solved.provenance)
```

### CLI smoke
`python -m poker_solver.practice.api list [--family F]... [--seed N] [--limit N]`
`python -m poker_solver.practice.api solve SPOT_ID [--iterations N]`
`python -m poker_solver.practice.api submit SPOT_ID KIND [AMOUNT] [--iterations N] [--user U]`
Prints one compact sorted JSON envelope; ValueError → `error: ...` on stderr, exit 2.
`--iterations` builds `{"algorithm": "vanilla-cfr", "iterations": N, "seed": null}`.

## Verification
- `tests/test_practice_scoring.py` + `tests/test_practice_cli_smoke.py`: 65 passed in ~13.7 s (Kuhn 2000-it
  fixture dominates). R1 check: same play at 5 vs 500 iterations changes params_hash and
  (best_q, solver_mix_q, score), spot_id unchanged.
- Sample live feedback (Kuhn P0 J root, 100 its): `Solver: check 80.6%, bet 19.4%. You: bet. EV loss 0.145
  chips (7.27% pot) -> Mistake. Best EV action: check (Q=-1.002); most-weighted alternative: check
  (Q=-1.002). Solver noise: 0.028 chips.`
- Full suite: 988 passed, 2 failed — both in `tests/test_practice_api.py` (not owned by task-2):
  `test_http_solve_and_submit`, `test_http_r1_iterations_change_answer`. They send
  `solve: {"iterations": N, "seed": 7}` with no algorithm, i.e. vanilla-cfr + seed 7, which task-1's
  `SolveParams` rejects ("vanilla-cfr requires seed=None"). The API deliberately does not silently drop the
  seed (fail-closed). Fix belongs in that test (send `"seed": null`, or `"algorithm":
  "external-sampling-mccfr"` once the adapter supports it).
- Parent: wire `dispatch_v4` → `handle_practice(op, payload)` for names in `PRACTICE_OPERATIONS`.
