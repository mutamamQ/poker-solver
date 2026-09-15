# Phase 3 bounded backend

Phase 3 is an additive collection of finite poker-game components. It preserves the version-1/version-2 APIs and does not claim unrestricted Hold'em solving, GTO Wizard parity, multiplayer Nash convergence, learned opponent models, or room-specific strategy data.

## Capability boundary

| Feature | Implemented scope |
|---|---|
| Game structure | Exact integer contribution ledgers, refunds, side pots, odd chips, declared rake |
| Sizing | Strict finite fixed, dynamic, and automatic candidate selection |
| Ranges | Weighted two-card parsing, editing, persistence, and blocker filtering |
| ICM | Exact subset recursion for 1 through 10 players |
| Bounties | Immediate one-hand bounty accounting only |
| N-player CFR | Deterministic full traversal on declared finite 2 through 9-player trees |
| Nodelocks/profiles | Complete fixed policies and finite behavior shaping; actual EV remains separate |
| Inference | Exact finite Bayesian updates from caller-supplied public likelihood tables |
| Tree editing | Atomic immutable add/remove/replace with explicit cache invalidation |
| Preflop | Heads-up finite weighted deals and betting; caller-supplied terminal table |
| Multiway | Exactly three players and one postflop betting round; caller-supplied ranks |
| Range tables | Reach-weighted per-combo policies, force-action EVs, and aggregate frequencies |
| Presets | Two non-presolved templates |
| Engine dispatch | Programmatic `classic` finite-tree CFR and approximate `checkdown-equity` |

Unavailable: Fast/DDLS without a shipped neural continuation model, unrestricted all-street Hold'em, continuous actions, automatic abstraction, nine-player strategic solving, and PLO.

`MCCFR` names an algorithm; it is not an accuracy mode. The deterministic full-tree implementation is the reference `Classic` path for the declared finite tree. No fixed iteration count is an equilibrium guarantee.

`EngineConfig` and `solve_engine` provide programmatic dispatch. `classic` runs configured finite-tree CFR and labels its result non-approximate; this does not certify convergence. `checkdown-equity` follows `CHECK` at every decision, honors chance probabilities, and is explicitly approximate because it ignores future betting. `fast-ddls` always fails closed.

Seven additional `examples/phase3_*.json` files cover synthetic preflop, three-player river, range, inference, ICM/bounty, and checkdown fixtures. They are input templates rather than charts or solved strategies. The three programmatic v3 fixtures are wrapper documents: pass their `request` member to `dispatch_v3`; the wrapper itself is intentionally not a strict CLI envelope. Run the bounded semantic benchmark with `uv run python scripts/benchmark_phase3.py`; timings are machine-dependent and every benchmark result includes a semantic check and synthetic-scope label.

## Version-3 envelope

Every request is a JSON object with exactly:

```json
{"version":3,"operation":"capabilities","payload":{}}
```

Run a request from a file or stdin:

```bash
uv run poker-solver phase3 request.json --json
uv run poker-solver phase3 - --json < request.json
```

Errors print `error: ...` to stderr and return status 2. Unknown or missing fields fail closed.

### `capabilities`

Payload: `{}`. Returns the live bounded/unavailable feature manifest.

### `list-presets`

Payload: `{}`. Returns deterministic copies of `btn-vs-bb-25bb` and `threeway-flop-demo`. The matching files under `examples/phase3/` are templates; neither contains a solved strategy.

### `icm`

```json
{"version":3,"operation":"icm","payload":{"stacks":[50,30,20],"payouts":[100,50,0]}}
```

Stacks must be finite positive numbers. Payouts must be finite nonnegative numbers in nonincreasing order. Fields have equal lengths and at most 10 entries.

### `bounty-ko`

```json
{"version":3,"operation":"bounty-ko","payload":{"eliminated_bounty":"75","recipient_shares":{"0":"2/3","1":"1/3"}}}
```

Rationals are JSON numbers or strings such as `"2/3"`; strings are capped at 256 characters. Shares must be nonnegative and sum to one. Results are rational strings and represent immediate one-hand cash only.

### `range-normalize`

```json
{"version":3,"operation":"range-normalize","payload":{"text":"AA,AKs:0.5"}}
```

Input uses the range-v1 grammar accepted by `ranges.import_range_text`; output is canonical text plus combo count. Input text is capped at 1,000,000 characters.

### `size-convert`

```json
{"version":3,"operation":"size-convert","payload":{"expression":{"unit":"big-blinds","value":3},"context":{"pot":300,"own_commitment":100,"highest_commitment":200,"remaining_stack":1900,"big_blind":100}}}
```

Supported units are defined by `sizing.validate_size_expression`, including pot percent, previous-bet multiple, big blinds, geometric sizing, and all-in. Values are raise-to targets. Conversion does not silently clamp an illegal result; game-state legality filters candidates separately.

### `inference`

```json
{
  "version": 3,
  "operation": "inference",
  "payload": {
    "hypotheses": [
      {"label":"tight","prior":"1","provenance":"caller fixture","likelihoods":{"root":{"fold":"3/4","call":"1/4"}}},
      {"label":"loose","prior":"1","provenance":"caller fixture","likelihoods":{"root":{"fold":"1/4","call":"3/4"}}}
    ],
    "observations": [{"public_key":"root","action":"fold"}]
  }
}
```

Likelihood rows are complete exact distributions. Hypotheses must have identical ordered public observation/action coverage. Private/hidden/hole-card observation keys are rejected. Zero-evidence sequences fail closed without smoothing. Limits are 64 hypotheses and 4,096 observations.

## Typed Python interfaces

Game trees and strategies intentionally remain typed Python APIs rather than loosely encoded JSON.

### Finite N-player solving

```python
from poker_solver.nplayer import (
    NPlayerCFRSolver,
    collect_nplayer_infosets,
    expected_values_nplayer,
    unilateral_deviation_certificate,
)

collect_nplayer_infosets(root, max_nodes=10_000, max_depth=512)
solver = NPlayerCFRSolver(root)
solver.train(100)
strategy = solver.average_strategy()
values = expected_values_nplayer(root, strategy)
certificate = unilateral_deviation_certificate(
    root, strategy, max_pure_strategies=100_000
)
```

The root must satisfy the `GameState` protocol and fully enumerate a finite tree. Node and depth bounds fail closed. Values in three-player zero-rake games sum to zero; declared rake changes the sum by the rake paid. The unilateral-deviation certificate exhaustively enumerates pure information-set deviations up to its explicit bound. It is a diagnostic, not a multiplayer Nash-convergence guarantee.

### Nodelocks and profiles

Use `constraints.validate_locks`, `ConstrainedCFRSolver`, `BehaviorProfile`, and `resolve_profile_locks`. A lock is a complete action distribution keyed by an observed information state. Profile-shaped training EV is not actual game EV; recompute actual EV on the original game.

### Preflop

Build `WeightedCombo`, `Continuation`, and `PreflopConfig`, then call `create_preflop_root`. Forced posts are applied once. Chance deals are blocker-compatible. `Action.amount` is a raise-to street commitment. Full raises and exact short all-ins follow the configured reopening policy. Every non-fold closed leaf requires an exact caller-supplied `(deal, history)` continuation value; missing coverage raises `ValueError`.

### Exactly-three-player postflop

Build `MultiwayConfig` and call `create_three_player_root`. The model supports one finite betting round, weighted blocker-compatible private triples, full and short raises, folds/all-ins, side pots, odd chips, and optional declared rake. Showdown ranks are caller supplied per private deal. It is not an unrestricted multi-street multiplayer solver.

### Structural edits

Use `FiniteNode`, `FiniteTree`, `EditOperation`, and `apply_tree_edits`. Batches run in declared order on a private copy and are atomic. A successful edit requires a fresh solver and invalidates root, regrets, average-policy sums, iterations, EV, tables, and locks. Stable node IDs do not make old action-signature locks valid after structural change.

### Range/strategy tables

`build_range_table(root, strategy, seat, provenance=...)` accepts a complete strategy for every reachable information set. Rows contain the source combo weight, chance reach/range probability, legal actions, action probabilities, force-action EVs, and mixed EV. Aggregates are reach weighted. Opponent/nonacting views omit action columns. These are exact diagnostics for the supplied finite strategy, not population frequencies or GTO claims.

## Numerics and immutability

- Chip ledgers, pots, refunds, and odd chips use integers.
- Exact probability/accounting boundaries use `Fraction` where declared.
- Booleans are rejected where numbers or integers are required.
- Negative and nonfinite values fail closed.
- Public result mappings and finite states are immutable or defensive copies.
- Caller mutation after construction cannot alter accepted configurations.

## Verification

```bash
uv run pytest -q
```

The full suite includes the original Phase 1+2 baseline plus Phase 3 focused, integration, malformed-input, accounting, information-noninterference, and boundedness tests. Runtime depends on the host and does not imply a solver speed or accuracy guarantee.
