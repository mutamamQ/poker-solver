# Phase 3 Range and Strategy Table Design

## Purpose

This document defines the exact computation, aggregation, serialization, and validation contracts for range and strategy tables displayed to users. These tables present per-combo and per-class frequencies, action breakdowns, and expected values for both the acting player's own strategy and the opponent's conditional range at any selected public node.

## Evidence and dependencies

- `research/phase3/ranges-display.md`: canonical range representation, 169-class expansion, blocker semantics, strategy-table identities, and acceptance fixtures.
- `research/phase3/opponent-inference.md`: Bayesian posterior conditioning on observed actions, log-space normalization, and sequential update semantics.
- `ARCHITECTURE.md`: game protocol, information-state keys, strategy representation, CFR reach equations, and zero-sum terminal utilities.
- Solver outputs: `cfr.py` `expected_values`, `average_strategy`, information-set policies, and reach-weighted regret updates.

## Scope

Phase 3 implements range/strategy tables for bounded explicit finite perfect-recall trees only. Neural evaluation, large-game approximation, and GUI matrix editors are documented boundaries.

## Canonical data model

### Input requirements

A table request must supply:

1. **Game and configuration**: a validated `GameState` root (Kuhn, river, or multi-street) with exact ranges, board, and betting structure.
2. **Strategy document**: a complete `Strategy = dict[InfoKey, dict[Action, float]]` covering every information set in the tree, with action probabilities summing to `1.0` within `1e-10` input validation tolerance.
3. **Selected public node**: a canonical public history or node identifier that uniquely determines the current board, street, and action sequence. The node must exist in the game tree.
4. **Target player**: 0 or 1, identifying whose range/strategy to display.
5. **Payoff baseline and units**: the zero point and scale for reported EVs (e.g., symmetric initial-pot baseline as in `river.py`).

### Explicit combo representation

Every table row corresponds to one explicit two-card combination `(c1, c2)` where `c1` and `c2` are canonical card integers in ascending order. The 1,326 Hold'em combos partition into:

- 13 pair classes × 6 suit combinations = 78 pair combos;
- 78 distinct-rank suited classes × 4 = 312 suited combos;
- 78 distinct-rank offsuit classes × 12 = 936 offsuit combos.

Combos are sorted by the global lexicographic order of `(c1, c2)` card integers.

### Blocker filtering

Before any computation, remove combos that intersect:

- the public board at the selected node;
- known dead cards;
- the other player's exact hand (when conditioning on a specific deal in a solved tree traversal).

Empty compatible mass after filtering is an error and must not produce NaN rows.

### Source range weights

Each player's initial range assigns a finite weight `w(h) ∈ [0,1]` to every explicit combo `h`. These weights are inclusion frequencies and need not sum to one. Zero-weight combos may be retained for round-trip display but are omitted from solver conversion.

## Reach and conditional probability

### Counterfactual reach

For a given public history and explicit deal `(h0, h1)`, the **counterfactual reach** of player `i`'s hand `hi` at the selected node is:

`reach_i(hi) = w_i(hi) * pi_-i * pi_c`,

where:

- `w_i(hi)` is the source range weight;
- `pi_-i` is the product of opponent action probabilities along the public history leading to the selected node;
- `pi_c` is the product of chance probabilities (the normalized joint deal probability after blockers, and any public runout probabilities if multi-street).

In a full-tree traversal, `pi_-i * pi_c` is the **counterfactual reach** excluding the target player's own action probabilities.

### Matchup weighting

When aggregating over hidden opponent hands, each terminal or action-EV contribution is weighted by the **matchup count**: the number of compatible opponent combos (after blockers) times their respective weights and reach probabilities. This is the "matchup weighting" described in PioSOLVER FAQ (source 6 of `ranges-display.md`).

### Normalized conditional probability

Within the displayed player's range at the selected node, the normalized probability of hand `h` is:

`P(h | node) = reach(h) / sum_k reach(k)`,

where the sum runs over all compatible combos for that player.

## Action breakdown and expected values

### Information-set policy

If the target player acts at the selected node, retrieve the information-state key for hand `h`:

`key = (game_version, player, sorted_own_cards, board, public_history, ...)`

and the corresponding policy from the strategy document:

`sigma(h, ·) = strategy[key]`.

The policy is a probability distribution over legal actions at that information set. All histories in the same information set share the same policy by perfect recall.

### Action expected value

For each legal action `a` at the selected node, the **action EV** `EV(h, a)` is computed by:

1. Forcing action `a` at the current node for hand `h`.
2. Following the supplied strategy profile for all subsequent decisions.
3. Averaging terminal utilities over all compatible opponent hands and chance outcomes, weighted by their counterfactual reach (opponent reach × chance probability).
4. **Not** multiplying by the player's own probability of choosing `a`.

This is the standard counterfactual value used in CFR regret updates.

### Mixed hand EV

The **mixed EV** for hand `h` at the selected node is:

`EV(h) = sum_a sigma(h, a) * EV(h, a)`,

the expected value when following the strategy.

### Aggregation identities (validation)

Every table output must satisfy:

1. **Action distribution**: for each acting hand, `sum_a sigma(h, a) = 1.0` within `1e-12`.
2. **Mixed EV identity**: `EV(h) = sum_a sigma(h, a) * EV(h, a)` within `1e-12`.
3. **Aggregate action frequency**: the displayed aggregate frequency for action `a` is the **reach-weighted** average:
   ```
   freq(a) = sum_h reach(h) * sigma(h, a) / sum_h reach(h)
   ```
   not an unweighted mean of per-hand probabilities.
4. **Aggregate EV**: the displayed aggregate EV is the **reach-weighted** (equivalently, matchup-weighted) mean:
   ```
   EV_aggregate = sum_h reach(h) * EV(h) / sum_h reach(h)
   ```
5. **Root consistency**: when the selected node is the game root and the same baseline is used, aggregating per-hand EVs for both players reproduces the raw `expected_values(root, strategy)` within `1e-12`.
6. **Class aggregation**: a 169-class row's frequency and EV equal the reach-weighted aggregation of its child explicit combos.

### EV ordering and equilibrium

At exact Nash equilibrium, actions with positive probability are best responses and have equal EV up to solution tolerance. However:

- EV may be positive, zero, or negative for any action.
- Fold EV is **not** generally less than every alternative; it depends on pot odds and ranges.
- Finite-iteration strategies need not satisfy exact action-EV equality.

No silent EV clamping or reordering is applied.

## Opponent range view

### Posterior conditioning

An opponent range view at the selected node reports the opponent's **conditional combo distribution** given the public history. If the public history includes observed opponent actions `a1, ..., aT`, apply Bayesian updates per `opponent-inference.md`:

`P(h | a1, ..., aT) ∝ w(h) * product_t L_t(h)`,

where `L_t(h)` is the opponent's strategy probability for action `at` at history `t` when holding hand `h`, derived from the supplied strategy document.

Blockers are applied before likelihood multiplication. Zero total mass is an error.

### Action breakdown for opponent

If the opponent is the actor at the selected node, report their per-combo action probabilities `sigma(h, a)` and action EVs `EV(h, a)` exactly as for the own-range view.

If the opponent is **not** the actor (e.g., the selected node is a decision point for the viewing player or a chance node), action fields are **absent** rather than copied from a different node or guessed.

## 169-class aggregation

A **class row** is a display reduction, never a solver input after blockers. Classes are:

- Pairs: `AA`, `KK`, ..., `22` (13 classes).
- Suited: `AKs`, `AQs`, ..., `32s` (78 classes).
- Offsuit: `AKo`, `AQo`, ..., `32o` (78 classes).

For class `C` with child combos `H_C`:

- **Class reach**: `reach(C) = sum_{h in H_C} reach(h)`.
- **Class action frequency**: `sigma(C, a) = sum_{h in H_C} reach(h) * sigma(h, a) / reach(C)`.
- **Class action EV**: `EV(C, a) = sum_{h in H_C} reach(h) * EV(h, a) / reach(C)`.
- **Class mixed EV**: `EV(C) = sum_{h in H_C} reach(h) * EV(h) / reach(C)`.

Class rows are generated **after** explicit-combo rows and must independently satisfy the aggregation identities.

## Unavailable and zero-reach handling

- **Zero reach after blockers**: if a combo is blocked or has zero conditional reach, it may be omitted from output or displayed with a clear `"reach": 0` marker. It must not produce NaN EV.
- **Unreachable node**: if the selected node has zero total conditional mass for the target player (e.g., a branch that is never reached under the supplied strategy), the request fails with a specific "unreachable node" error. No NaN rows are emitted.
- **Missing strategy key**: if the strategy document does not contain a required information-set key, the request fails with "incomplete strategy."
- **Illegal action in strategy**: if the strategy assigns positive probability to an action not in `legal_actions()`, validation fails.

## Strict JSON schema (version 1)

### Request

```json
{
  "version": 1,
  "request_type": "range_table" | "strategy_table",
  "game_config": { ... },
  "strategy_document": {
    "format": "poker-solver-strategy-v1",
    "algorithm": "vanilla-cfr" | "external-mccfr" | ...,
    "iterations": <int>,
    "infosets": {
      "<serialized_key>": {"<action_json>": <float>, ...},
      ...
    }
  },
  "selected_node": {
    "public_history": [<action_objects>],
    "board": [<card_strings>],
    "street": "preflop" | "flop" | "turn" | "river"
  },
  "target_player": 0 | 1,
  "payoff_baseline": "symmetric_initial_pot" | "zero_sum_terminal",
  "output_options": {
    "include_classes": true | false,
    "include_action_ev": true | false,
    "sort_order": "canonical" | "ev_descending"
  }
}
```

### Response

```json
{
  "format": "poker-solver-range-table-v1",
  "request_type": "range_table" | "strategy_table",
  "target_player": 0 | 1,
  "selected_node": { ... },
  "payoff_baseline": "symmetric_initial_pot",
  "payoff_units": "big_blinds" | "chips",
  "total_compatible_mass": <float>,
  "player_acts": true | false,
  "explicit_combos": [
    {
      "cards": ["As", "Kd"],
      "source_weight": 1.0,
      "reach": 0.123,
      "probability": 0.045,
      "strategy": {"check": 0.6, "bet": 0.4},
      "action_ev": {"check": 2.5, "bet": 2.5},
      "mixed_ev": 2.5
    },
    ...
  ],
  "classes": [
    {
      "class": "AA",
      "reach": 0.456,
      "probability": 0.123,
      "strategy": {"check": 0.55, "bet": 0.45},
      "action_ev": {"check": 3.2, "bet": 3.2},
      "mixed_ev": 3.2
    },
    ...
  ],
  "aggregate": {
    "strategy": {"check": 0.58, "bet": 0.42},
    "mixed_ev": 2.8
  },
  "validation": {
    "action_distribution_tolerance": 1e-12,
    "mixed_ev_identity_tolerance": 1e-12,
    "all_checks_passed": true
  }
}
```

### Serialization rules

- **Deterministic ordering**: explicit combos sorted by `(c1, c2)` card integers; classes sorted by standard rank order (pairs descending, then suited/offsuit by high-to-low ranks); actions sorted by a canonical stable order (check, call, fold, bet/raise by amount).
- **Finite values**: NaN, infinity, and non-finite floats are rejected. Missing or null numeric fields fail validation.
- **Strict types**: booleans are not integers; `"player_acts": 1` is invalid.
- **Unknown fields**: top-level unknown fields cause a warning; unknown fields in nested objects fail.
- **Duplicate JSON keys**: rejected via `object_pairs_hook` during parsing.
- **Decimal precision**: floats serialized with sufficient precision to round-trip within `1e-15`; typically 17 significant digits.

## CLI interface

```
poker-solver range-table \
  --game-config <path.json> \
  --strategy <path.json> \
  --node <public_history_spec> \
  --player 0|1 \
  [--include-classes] \
  [--json]
```

Successful output goes to stdout; errors to stderr with exit status 2 (invalid input) or 1 (runtime failure).

## Exact test oracles

1. **Tiny river fixture**: enumerate every terminal manually for the shipped two-type-per-player river game. For each player, each hand, each acting node, verify:
   - Action probabilities sum to 1.0 within `1e-12`.
   - Mixed EV equals dot product of action probabilities and action EVs within `1e-12`.
   - Action EVs match manual terminal enumeration.

2. **Aggregate root identity**: for the same tiny river game at the root node, aggregate per-hand EVs using reach weights. Result must match `cfr.expected_values(root, strategy)` within `1e-12`.

3. **Class aggregation**: for a small multi-combo class (e.g., `AA` with 6 combos, 3 compatible after blockers), verify class reach, action frequencies, and EV equal the reach-weighted sum of child combos within `1e-12`.

4. **Opponent posterior**: construct a two-hand opponent range with known prior weights `(1/4, 3/4)` and one observed action with likelihoods `(1, 1/3)`. Verify displayed opponent probabilities are `(1/2, 1/2)` per the Bayes fixture in `opponent-inference.md`.

5. **Action split identity**: for every hand at an acting node, verify `reach(h) * sigma(h, a)` equals the unnormalized posterior mass for the action-specific range, matching PioSOLVER source 4.

6. **Unreachable branch**: select a node with zero reach under the supplied strategy. Verify the request fails with "unreachable node" error, not NaN output.

7. **Blocker consistency**: with hero `AsKd` and opponent range `AA,AKs,AKo`, verify exactly 12 opponent combos appear (3 `AA`, 2 `AKs`, 7 `AKo` per the enumeration in `ranges-display.md`).

8. **Non-acting opponent view**: select a node where the target player does not act (e.g., opponent's decision node when viewing own range, or a chance node). Verify `"player_acts": false` and action/EV fields are absent, not zero or copied from another node.

9. **Deterministic serialization**: generate the same table twice; verify byte-identical JSON output (sorted keys, stable float formatting).

10. **Raw strategy reproduction**: for a single information set, verify the displayed per-hand action probabilities exactly match the raw `strategy[key]` dictionary from the input document.

## Module boundaries and implementation phases

### New modules

- `range_table.py`: core computation of reach, conditional probability, action EV, mixed EV, and class aggregation. Depends on `model.py`, `cards.py`, `equity.py`, and solver outputs. No CLI or JSON serialization.
- `range_table_api.py`: strict JSON request/response parsing, validation, and serialization. Depends on `range_table.py`. Exposes a pure function `compute_range_table(request: dict) -> dict`.
- `tests/test_range_table.py`: unit tests for reach computation, EV identities, class aggregation, and blocker filtering.
- `tests/test_range_table_api.py`: JSON schema validation, deterministic serialization, and error handling.
- `tests/test_range_table_integration.py`: end-to-end tests using solved Kuhn and river fixtures, verifying all 10 exact oracles above.

### CLI integration

- `cli.py`: add `range-table` and `strategy-table` subcommands. Parse arguments, load game config and strategy JSON, call `range_table_api.compute_range_table`, emit JSON or human-readable table to stdout.

### Phased delivery

Phase 3 Wave B implementation proceeds in three sub-batches:

1. **Core computation**: `range_table.py` with reach, action EV, mixed EV, and explicit-combo output. Tests for tiny river fixture and aggregation identities.
2. **Class aggregation and opponent view**: 169-class rows, Bayesian posterior conditioning, and non-acting opponent views. Tests for class identity and blocker consistency.
3. **JSON API and CLI**: strict schema, deterministic serialization, error boundaries, and CLI integration. Tests for schema validation and byte-determinism.

Each sub-batch requires a fresh non-author adversarial review under `review/phase3/range-tables-<sub-batch>.md` before the next sub-batch starts.

## Acceptance criteria

Before Phase 3 Wave B is complete:

- All 10 exact test oracles pass with tolerance `1e-12` (or `1e-15` where specified).
- `pytest tests/test_range_table*.py` is green.
- CLI `poker-solver range-table --json` produces valid, deterministic JSON for the shipped river fixture.
- Adversarial review reports zero blocking findings.
- No new runtime dependencies added (standard library only).
- All Phase 1 and Phase 2 tests remain green (non-regression).

## Non-goals and documented boundaries

- **GUI matrix editor**: out of backend scope; this design defines the data contract only.
- **Large-game approximation**: Phase 3 supports only bounded explicit trees. Neural EV estimation, bucketing, and abstraction are future work.
- **Multi-way pots**: three-player games are a documented boundary.
- **Real-time opponent modeling**: learning an unknown opponent strategy from a hand database (as in Bayes' Bluff) is not Phase 3 scope. This module conditions on a supplied behavioral model only.
- **Claiming real-opponent truth**: inference results are explicitly conditional on the supplied model and do not prove the opponent's true holdings or strategy.

## References

1. `research/phase3/ranges-display.md`: canonical range representation, 169-class expansion, blocker semantics, strategy-table identities.
2. `research/phase3/opponent-inference.md`: Bayesian posterior, log-space normalization, sequential updates.
3. `ARCHITECTURE.md`: game protocol, CFR reach equations, zero-sum utilities.
4. PioSOLVER range/strategy explanation: https://piosolver.com/docs/viewer/numbers_in_piosolver/
5. PioSOLVER GTO FAQ on matchup weighting: https://piosolver.com/docs/faq/gto_concept/
6. Southey et al., "Bayes' Bluff: Opponent Modelling in Poker": http://poker.cs.ualberta.ca/publications/UAI05.pdf
7. Zinkevich et al., CFR behavioral strategies: https://proceedings.neurips.cc/paper/2007/file/08d98638c6fcd194a4b1e6992063e944-Paper.pdf
