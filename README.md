# Poker Solver

A correctness-first Python 3.11 reference implementation of vanilla CFR and external-sampling MCCFR for finite two-player zero-sum games.

It ships:

- standard three-card Kuhn poker;
- a real, deliberately compact heads-up Texas Hold'em river game;
- bounded heads-up flop/turn/river games with exact weighted deals, configured runouts, and discrete no-limit or pot-limit actions;
- exact five-card and seven-card evaluation;
- exhaustive exact-card and blocker-aware range equity;
- scalable information-set-consistent best responses, an exhaustive tiny-game oracle, NashConv, and half-NashConv;
- a deterministic JSON-capable CLI;
- exhaustive, known-answer, adversarial, and external-oracle tests.

This is not a commercial unrestricted Hold'em solver. Phase 3 adds bounded heads-up preflop, one-round exactly-three-player postflop, declared rake/side pots, finite N-player CFR, ICM, immediate one-hand bounties, nodelocks/profiles, exact finite Bayesian inference, structural tree editing, and range/strategy tables. These features require explicit finite ranges, actions, chance outcomes, and caller-supplied continuation/showdown data. There is no unrestricted full-game solving, automatic abstraction, continuous sizing, learned continuation model, PLO, or nine-player strategic solve claim. Small exact trees are intentional.

## Requirements

- Python 3.11 or newer
- `uv`

No third-party runtime package is required. Pytest is installed by the development group. Treys is used ephemerally only for the optional external cross-check.

## Install

From this directory:

```bash
uv sync
```

## CLI

```bash
uv run poker-solver --help
```

### Evaluate a hand

Exactly five or seven strict two-character cards are accepted. Ranks are `23456789TJQKA`; suits are lowercase `cdhs`.

```bash
uv run poker-solver evaluate As Ks Qs Js Ts --json
```

Example result:

```json
{"cards":["As","Ks","Qs","Js","Ts"],"category":"straight-flush","rank":[8,12]}
```

Larger rank tuples compare as stronger hands.

### Exact heads-up equity

Hero and villain are exact comma-separated two-card hands. Boards contain zero, three, four, or five comma-separated cards.

```bash
uv run poker-solver equity \
  --hero As,Ah \
  --villain Ks,Kh \
  --board 2c,3d,4h,8s,9c \
  --json
```

The response contains integer `wins`, `ties`, `losses`, `total`, and equity `(wins + ties/2) / total`. Preflop exact enumeration is intentionally slower.

### Solve canonical Kuhn poker

```bash
uv run poker-solver solve-kuhn --iterations 5000 --json
```

The response includes the average CFR strategy, both player values, raw `nash_conv`, and `exploitability_half_nash_conv`. At 5,000 iterations the verified reference run produced player-0 value `-0.0555064005`, close to the canonical `-1/18`, with NashConv `0.0066048961`.

### Solve the shipped river spot

```bash
uv run poker-solver solve-spot examples/river_spot.json --iterations 5000 --json
```

Spot files are strict JSON objects with exactly these fields:

```json
{
  "version": 1,
  "board": ["2c", "3d", "4h", "9s", "Kc"],
  "pot": 2,
  "stack": 1,
  "bet": 1,
  "range0": [{"cards": ["As", "5s"], "weight": 1}],
  "range1": [{"cards": ["Kh", "Qh"], "weight": 1}]
}
```

`pot` is a finite positive JSON number. `stack` and `bet` are positive JSON integers, and `bet <= stack`. Combo weights are finite nonnegative JSON numbers. Strings and booleans are not silently coerced. Illegal collisions are removed before joint range normalization; a spot with no compatible positive-weight deals is rejected.

### Solve a bounded multi-street spot

Version 2 supports flop, turn, or river starts, exact combo weights, complete legal runout sequences, discrete raise-to targets, and `no-limit` or `pot-limit` legality:

```bash
uv run poker-solver solve-multistreet examples/multistreet_spot.json \
  --algorithm external-sampling-mccfr --iterations 10000 --seed 42 --json \
  > /tmp/multistreet-solve.json
```

Use `--algorithm vanilla-cfr` without `--seed` for bounded exact reference trees. Oversized exact chance trees fail closed. The result contains a round-trippable strategy, player values, raw `nash_conv`, and `exploitability_half_nash_conv`.

Recompute exploitability from the emitted strategy:

```bash
uv run poker-solver exploitability \
  examples/multistreet_spot.json /tmp/multistreet-solve.json --json
```

Pass `-` instead of the multi-street config path to read strict version-2 JSON from stdin. `allowed_runouts` contains complete remaining board sequences: two cards for a flop start, one for a turn start, and an empty list for a river start. Each `Action.amount` is a raise-to target on the current street.

### Phase 3 bounded utilities

The additive version-3 facade uses a strict envelope with exactly `version`, `operation`, and `payload`:

```bash
printf '%s' '{"version":3,"operation":"capabilities","payload":{}}' |
  uv run poker-solver phase3 - --json

printf '%s' '{"version":3,"operation":"icm","payload":{"stacks":[3,1],"payouts":[100,0]}}' |
  uv run poker-solver phase3 - --json

printf '%s' '{"version":3,"operation":"range-normalize","payload":{"text":"AA,AKs:0.5"}}' |
  uv run poker-solver phase3 - --json
```

Supported JSON operations are `capabilities`, `list-presets`, `icm`, `bounty-ko`, `range-normalize`, `size-convert`, and `inference`. Tree editing, N-player solving, engine dispatch, nodelocks/profiles, preflop, three-player postflop, and range tables use their typed Python APIs because they contain game trees and strategies. The engine exposes full-traversal `classic` and explicitly approximate `checkdown-equity`; `fast-ddls` fails closed because no neural continuation-value model ships with this repository.

The bundled `examples/phase3/` and `examples/phase3_*.json` files are non-presolved synthetic templates, not recommended strategies or room defaults. The wrapper-style programmatic fixtures require passing their `request` member to `dispatch_v3`; they are not direct CLI envelopes. See `docs/PHASE3.md` for schemas, Python examples, numeric bounds, and exact limitations. `uv run python scripts/benchmark_phase3.py` runs four bounded synthetic semantic benchmarks; its timings are machine-dependent and are not production-throughput claims.

## Practice mode

Branch `feat/practice-mode` adds a GTO Wizard-style practice mode: a local web UI and API where you play solver-generated spots and are graded by EV loss against a runtime solve. It covers Kuhn, river, flop, turn, heads-up preflop and 3-max preflop families.

```bash
.venv/bin/python -m poker_solver.practice.server --port 7777   # open http://127.0.0.1:7777/
```

See `PRACTICE_MODE.md` for how to run it, how scoring works, the known limitations, and how to read the solver evaluation. The solver evaluation's current verdict is in `research/solver-evaluation/results.md`. Detailed docs are in `docs/practice-mode/`.

## Utility convention

Values are net, zero-sum utility from the beginning of a spot. For initial dead pot `D`, contribution `C_i`, and terminal award `A_i`, multi-street utility is `A_i - C_i - D/2`. The version-1 river special cases are:

- unbet showdown: winner `+P/2`, loser `-P/2`;
- called bet: winner `+(P/2+B)`, loser the negative;
- bet-fold: bettor `+P/2`, folder `-P/2` because the unmatched bet is returned;
- tie: `(0, 0)`.

## Tests

Run the complete Definition-of-Done suite:

```bash
uv run pytest -q
```

It includes the exhaustive 2,598,960-hand five-card category census, two exhaustive preflop equity fixtures, stochastic seed matrices, and multi-street oracle checks; it takes several minutes on the reference machine.

Fast development pass:

```bash
uv run pytest -m 'not slow' -q
```

External deterministic evaluator cross-check:

```bash
uv run --with treys python scripts/crosscheck_treys.py
```

That command checks 100,000 random seven-card categories and 50,000 random heads-up comparisons against Treys with a fixed seed.

## Verified reference metrics

On the mission host:

- Phase 2 fast suite: 181 tests in 72.03 seconds (4 slow tests deselected);
- Kuhn, 5,000 CFR iterations: 2.63 seconds, 30,080 KiB maximum RSS;
- compact river example, 5,000 iterations: 8.03 seconds, 29,952 KiB maximum RSS;
- compact river NashConv at 5,000 iterations: `0.0076313537`.

Exact runtime is machine-dependent. Vanilla full-tree CFR work scales with every history visited per iteration. Exact range equity scales with compatible hand pairs times legal runouts. Exhaustive pure-strategy best response scales exponentially and remains only an oracle; the default dynamic best response avoids Cartesian strategy enumeration on supported perfect-recall trees. MCCFR reduces iteration cost but adds variance and has no universal speedup claim.

## Library layout

- `model.py`: finite-game protocol and immutable actions
- `cards.py`: strict cards and deck
- `evaluator.py`: exact five/seven-card ranking
- `equity.py`: exhaustive exact and weighted-range equity
- `kuhn.py`: canonical Kuhn game
- `river.py`: compact Hold'em river game
- `cfr.py`: synchronous full-tree vanilla CFR
- `mccfr.py`: seeded external-sampling MCCFR
- `multistreet.py`: bounded immutable flop/turn/river state machine
- `phase2_fixture.py`: tiny independently auditable multi-street fixture
- `best_response.py`: dynamic BR, exhaustive oracle, and NashConv
- `api.py`: strict version-2 parsing and round-trippable strategy JSON
- `audit.py`: exhaustive structural validation
- `game_structure.py`: exact ledgers, side pots, odd chips, and declared rake
- `sizing.py`: fixed/dynamic/automatic finite sizing selection
- `ranges.py`: weighted range editor and strict persistence
- `icm.py` / `bounties.py`: bounded tournament utilities
- `nplayer.py` / `constraints.py`: finite 2..9-player CFR and locks/profiles
- `inference.py`: exact finite public-observation Bayesian updates
- `tree_edit.py`: immutable atomic structural edits and invalidation metadata
- `preflop.py`: bounded heads-up preflop with terminal-table continuation
- `multiway.py`: one-round exactly-three-player postflop
- `range_table.py`: reach-weighted per-combo strategy and action-EV tables
- `api_v3.py` / `presets.py`: strict Phase-3 utility facade and example catalog
- `cli.py`: deterministic command boundary

See `ARCHITECTURE.md` for equations and invariants, `research/` for cited design research, `review/` for adversarial/final gates, and `SWARM_REPORT.md` for the BryantGPT orchestration experiment.
