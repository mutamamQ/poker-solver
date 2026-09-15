# API v3 Architecture: Strict JSON Contract for Phase 3 Extensions

## Status and provenance

This document defines the version-3 JSON API surface for GTO Wizard feature-parity extensions (Phase 3). It is derived from:

- PHASE3_MISSION.md mission requirements
- Ten root research reports in research/phase3/
- ARCHITECTURE.md Phase 1+2 baseline
- Existing src/poker_solver/api.py implementation (version 2)
- Observed test coverage (185 tests green)

No endpoints are invented. Every operation below extends the existing version-2 contract or adds new versioned endpoints that preserve backward compatibility.

## Existing API surface (observed from api.py)

### Version 2: Multi-street solving

**Module:** `src/poker_solver/api.py`

**Public functions:**

1. `load_multistreet_config(data: dict[str, Any]) -> MultiStreetConfig`
   - Validates version-2 multi-street configuration
   - Strict validation: rejects unknown fields, bool-as-int, non-finite weights
   - Required fields: `version`, `starting_street`, `starting_board`, `initial_dead_pot`, `effective_stack`, `player0_combos`, `player1_combos`, `allowed_runouts`, `betting_mode`, `wager_targets`
   - Size limits: MAX_COMBOS=1000, MAX_RUNOUTS=1000, MAX_WAGERS=100

2. `solve_multistreet(config, algorithm, iterations, seed) -> SolveResult`
   - Algorithms: `"vanilla-cfr"` (no seed), `"external-sampling-mccfr"` (requires seed)
   - Vanilla CFR limit: 10,000 exact chance leaves
   - Returns: `SolveResult(algorithm, seed, iterations, values, nash_conv, half_nash_conv, strategy, metadata)`

3. `compute_exploitability(root, strategy) -> ExploitabilityResult`
   - Returns: `ExploitabilityResult(nash_conv, half_nash_conv, values, best_response_values, incentives)`

4. `complete_strategy(root: GameState, strategy: Strategy) -> Strategy`
   - Fills lazily unvisited infosets with uniform policies

5. `serialize_strategy(strategy: Strategy) -> dict[str, Any]`
   - Format: `"poker-solver-strategy-v1"`
   - Deterministic, sorted, round-trippable JSON

6. `deserialize_strategy(root: GameState, data: Any) -> Strategy`
   - Validates against exact game tree
   - Rejects duplicate/missing information states

7. `load_json_input(source: str | Path) -> dict[str, Any]`
   - Loads from file path or stdin (`"-"`)

**Validation helpers (internal):**

- `_strict_int(value, field)` — rejects booleans and floats
- `_strict_number(value, field)` — rejects booleans, requires finite
- `_strict_positive_int(value, field)`
- `_strict_nonnegative_int(value, field)`
- `_strict_nonnegative_number(value, field)`
- `_parse_combo(item, index)` — strict WeightedCombo validation
- `_parse_board(cards, field)` — strict card list validation
- `_parse_runout(runout, index)` — strict runout validation

**No API tests found** in tests/ directory (search returned zero results). API validation is exercised through integration tests in test_cli.py and module tests.

## Phase 3 operation matrix

| Feature | Tier | API Endpoint | Request Version | Response Format | Module Dependencies |
|---------|------|--------------|-----------------|-----------------|---------------------|
| **Preflop heads-up solving** | 1 | `solve_preflop_headsup` | 3 | `preflop-solve-result-v1` | preflop.py, sizing.py, continuation.py |
| **Bet sizing modes** | 1 | `convert_size_expression`, `select_dynamic_sizes`, `select_automatic_sizes` | 3 | `sizing-conversion-v1` | sizing.py |
| **Range editor** | 1 | `parse_range_text`, `serialize_range_text`, `edit_range`, `save_range_library`, `load_range_library` | 3 | `poker-solver-range-v1`, `poker-solver-range-library-v1` | ranges.py |
| **Range/strategy tables** | 1 | `compute_range_table`, `compute_opponent_range_view` | 3 | `range-table-v1` | ranges.py, display.py |
| **Tree editing** | 1 | `edit_tree`, `validate_tree_edit` | 3 | `tree-edit-result-v1` | tree_edit.py |
| **Nodelocking** | 1 | `apply_nodelocks`, `validate_nodelock` | 3 | `nodelock-config-v1` | nodelock.py |
| **Player profiles** | 1 | `apply_profile`, `validate_profile` | 3 | `profile-config-v1` | profiles.py |
| **Rake** | 1 | `apply_rake_policy`, `validate_rake` | 3 | `rake-policy-v1` | rake.py (extends multistreet.py) |
| **Opponent range inference** | 1 | `infer_opponent_range` | 3 | `poker-solver-posterior-v1` | inference.py |
| **Three-way postflop** | 1 | `solve_multiway` | 3 | `multiway-solve-result-v1` | multiway.py, nplayer_cfr.py |
| **Canonical spot presets** | 2 | `load_preset`, `list_presets` | 3 | `preset-library-v1` | presets.py |
| **Nine-way preflop** | 3 | Documented boundary | — | — | — |
| **ICM/bounties** | 3 | Documented boundary | — | — | — |
| **DDLS/Fast engine** | 3 | Documented boundary | — | — | — |

## Version 3 request/response contracts

### 3.1 Preflop heads-up solving

**Endpoint:** `solve_preflop_headsup(config: dict) -> dict`

**Request schema (version 3):**

```json
{
  "version": 3,
  "game": "holdem-preflop-heads-up",
  "stacks": {"BTN_SB": <int>, "BB": <int>},
  "blinds": {"small": <int>, "big": <int>},
  "ante_mode": "none" | {"per_player": <int>} | {"total": <int>} | {"bb_ante": <int>} | {"explicit": [<int>, <int>]},
  "player0_combos": [{"cards": [<str>, <str>], "weight": <number>}, ...],
  "player1_combos": [{"cards": [<str>, <str>], "weight": <number>}, ...],
  "tree_config": {
    "sizing_mode": "fixed" | "dynamic" | "automatic",
    "size_expressions": [<size_expr>, ...],
    "max_raises": <int>
  },
  "continuation_mode": "all-in-runout" | "table" | "checkdown-equity",
  "continuation_payload": <depends on mode>,
  "algorithm": "vanilla-cfr" | "external-sampling-mccfr",
  "iterations": <int>,
  "seed": <int> | null
}
```

**Size expression schema:**

```json
{"unit": "pot-percent", "value": <number>}
{"unit": "geometric", "streets": <int>, "scale": <number>}
{"unit": "previous-bet-multiple", "value": <number>}
{"unit": "big-blinds", "value": <number>}
{"unit": "all-in"}
```

**Response schema:**

```json
{
  "format": "preflop-solve-result-v1",
  "algorithm": <str>,
  "seed": <int> | null,
  "iterations": <int>,
  "values": [<float>, <float>],
  "nash_conv": <float>,
  "half_nash_conv": <float>,
  "strategy": <serialized strategy>,
  "metadata": {
    "game": "holdem-preflop-heads-up",
    "continuation_model": <str>,
    "approximation": <bool>,
    "effective_stack": <int>,
    "starting_pot": <int>
  }
}
```

**Validation rules:**

- Stacks must be positive integers
- Blinds must be positive integers, `big > small`
- Ante amounts must be non-negative integers
- Total ante must be divisible by 2 for heads-up
- Forced postings cannot exceed starting stacks
- Combo weights must be finite, in [0,1]
- Empty combo lists rejected
- Zero total weight rejected
- Card collisions rejected (board, dead cards, overlapping combos)
- Size expressions validated per sizing.py contract
- Continuation mode must provide required payload
- Non-all-in closing without continuation mode fails
- Algorithm/seed contract matches version 2

### 3.2 Bet sizing conversion and selection

**Endpoint:** `convert_size_expression(expr: dict, context: dict) -> dict`

**Request:**

```json
{
  "version": 3,
  "expression": <size_expr>,
  "context": {
    "pot": <int>,
    "highest_commitment": <int>,
    "own_commitment": <int>,
    "remaining_stack": <int>,
    "big_blind": <int>
  }
}
```

**Response:**

```json
{
  "format": "sizing-conversion-v1",
  "target_amount": <int>,
  "unrounded_amount": <str>,
  "rounding_rule": "round-half-up",
  "is_legal": <bool>,
  "legality_reason": <str> | null
}
```

**Endpoint:** `select_dynamic_sizes(config: dict) -> dict`

**Request:**

```json
{
  "version": 3,
  "candidates": [<size_expr>, ...],
  "retained_count": <int>,
  "selecting_player": 0 | 1,
  "game_config": <game configuration>,
  "solver_config": {
    "algorithm": <str>,
    "iterations": <int>,
    "seed": <int> | null
  },
  "tie_tolerance": <float>
}
```

**Response:**

```json
{
  "format": "dynamic-sizing-result-v1",
  "selected_subset": [<size_expr>, ...],
  "selected_targets": [<int>, ...],
  "selecting_player_ev": <float>,
  "all_subsets_evaluated": [
    {"subset": [...], "targets": [...], "ev": <float>},
    ...
  ]
}
```

**Endpoint:** `select_automatic_sizes(config: dict) -> dict`

**Request:**

```json
{
  "version": 3,
  "context": <sizing context>,
  "max_sizes": <int>,
  "ev_tolerance": <float>,
  "selecting_player": 0 | 1,
  "game_config": <game configuration>,
  "solver_config": <solver configuration>
}
```

**Response:**

```json
{
  "format": "automatic-sizing-result-v1",
  "selected_subset": [<size_expr>, ...],
  "selected_targets": [<int>, ...],
  "selecting_player_ev": <float>,
  "full_tree_ev": <float>,
  "ev_gap": <float>,
  "candidate_grid": [<size_expr>, ...]
}
```

**Validation rules:**

- All numeric fields must be strict JSON numbers (not booleans)
- Finite values required (no NaN, infinity)
- Pot, commitments, stack must be non-negative integers
- Size expression fields validated per unit type
- Geometric requires `streets > 0`, `scale > 0`
- Previous-bet-multiple requires `value > 0`
- Rounding uses decimal round-half-up to nearest chip
- Targets above stack illegal unless expression is `all-in`
- Targets below minimum raise illegal unless exact short all-in
- Duplicate targets deduplicated by target value
- Dynamic/Automatic: candidate count must not exceed architecture limit
- Retained count must be positive and ≤ candidate count

### 3.3 Range editor and serialization

**Endpoint:** `parse_range_text(text: str) -> dict`

**Request:**

```json
{
  "version": 3,
  "format": "poker-solver-range-v1",
  "text": <str>
}
```

**Response:**

```json
{
  "format": "poker-solver-range-v1",
  "combos": [
    {"cards": [<str>, <str>], "weight": <number>},
    ...
  ]
}
```

**Text grammar (poker-solver-range-v1):**

```
document := entry ("," entry)*
entry := token [":" decimal_weight]
token := class | explicit_combo
class := "AA" | "KK" | ... | "22" | "AKs" | "AKo" | ...
explicit_combo := card card
card := rank suit
rank := "2" | "3" | ... | "9" | "T" | "J" | "Q" | "K" | "A"
suit := "c" | "d" | "h" | "s"
```

**Endpoint:** `serialize_range_text(combos: list) -> str`

**Endpoint:** `edit_range(range_data: dict, operation: dict) -> dict`

**Request:**

```json
{
  "version": 3,
  "range": {"combos": [...]},
  "operation": {
    "action": "add" | "set_weight" | "remove" | "include_or_replace",
    "token": <class or explicit combo>,
    "weight": <number>
  }
}
```

**Response:**

```json
{
  "format": "poker-solver-range-v1",
  "combos": [...]
}
```

**Endpoint:** `save_range_library(library: dict, path: str) -> dict`

**Endpoint:** `load_range_library(path: str) -> dict`

**Library format:**

```json
{
  "format": "poker-solver-range-library-v1",
  "ranges": {
    "<name>": {"combos": [...]},
    ...
  }
}
```

**Validation rules:**

- Text parsing: no whitespace inside tokens
- Default weight is 1.0
- Weights must be finite JSON numbers in [0, 1]
- Booleans rejected
- Overlapping entries in text rejected
- Class tokens: ranks descending, exact `s`/`o` suffix
- Explicit combos: strict two-character card format
- Card collisions rejected
- Operations atomic: all combos must exist/not exist as required
- Library names: `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}`
- Duplicate JSON keys rejected via `object_pairs_hook`
- Save uses atomic replace (temp file + os.replace)

### 3.4 Range and strategy tables

**Endpoint:** `compute_range_table(config: dict) -> dict`

**Request:**

```json
{
  "version": 3,
  "game_root": <serialized game or preset ID>,
  "strategy": <serialized strategy>,
  "public_node": <canonical node selector>,
  "player": 0 | 1 | 2,
  "output_mode": "explicit-combos" | "explicit-and-classes"
}
```

**Response:**

```json
{
  "format": "range-table-v1",
  "player": <int>,
  "public_node": <selector>,
  "player_acts": <bool>,
  "total_compatible_mass": <float>,
  "rows": [
    {
      "combo": [<str>, <str>],
      "source_weight": <float>,
      "conditional_reach": <float>,
      "normalized_probability": <float>,
      "actions": [
        {"kind": <str>, "amount": <int>, "probability": <float>, "ev": <float>},
        ...
      ],
      "mixed_ev": <float>
    },
    ...
  ],
  "class_rows": [...],
  "aggregate": {
    "action_frequencies": [{"kind": <str>, "amount": <int>, "frequency": <float>}, ...],
    "aggregate_ev": <float>
  },
  "baseline": <str>,
  "units": "chips"
}
```

**Endpoint:** `compute_opponent_range_view(config: dict) -> dict`

**Response format:** Same as `range-table-v1` but `player_acts` may be false and `actions` field absent when opponent does not act at selected node.

**Validation rules:**

- Strategy must be complete (all infosets covered)
- Public node must be reachable
- Player must be valid for game
- Zero conditional mass fails (unreachable node)
- Action probabilities sum to 1 within 1e-12
- Mixed EV equals dot product of action probabilities and EVs within 1e-12
- Aggregate frequency is reach-weighted, not unweighted average
- Aggregate EV is matchup-weighted
- Class rows equal weighted sum of child combos
- NaN/infinity rejected

### 3.5 Tree editing

**Endpoint:** `edit_tree(config: dict) -> dict`

**Request:**

```json
{
  "version": 3,
  "base_config": <game configuration>,
  "edits": [
    {
      "selector": <deterministic public-history selector>,
      "operation": "replace_actions" | "add_action" | "remove_action",
      "actions": [<Action>, ...] | <Action>
    },
    ...
  ],
  "nodelock_remapping": <optional explicit remapping>
}
```

**Selector schema:**

```json
{
  "game_version": <str>,
  "street": <str>,
  "public_board": [<str>, ...],
  "public_history": [<Action>, ...],
  "acting_seat": <int>
}
```

**Response:**

```json
{
  "format": "tree-edit-result-v1",
  "edited_config": <new game configuration>,
  "validation": {
    "selectors_resolved": <int>,
    "infosets_affected": <int>,
    "action_consistency_verified": <bool>
  },
  "invalidated": {
    "solver_state": true,
    "nodelocks": [<affected keys>]
  }
}
```

**Validation rules:**

- Selector must resolve to at least one reachable decision
- All resolved occurrences must belong to same public decision class
- Histories sharing InfoKey must have identical ordered actions after edit
- Action kinds and amounts must be legal at every resolved occurrence
- No duplicate Action values
- At least one action must remain
- Child generation must succeed for each action
- Existing nodelocks on changed action tuples must be explicitly remapped or rejected
- Rebuilt root must pass `collect_infosets` consistency check
- All solver state invalidated after any structural edit

### 3.6 Nodelocking

**Endpoint:** `apply_nodelocks(config: dict) -> dict`

**Request:**

```json
{
  "version": 3,
  "game_config": <game configuration>,
  "locks": [
    {
      "information_key": <canonical InfoKey repr>,
      "distribution": [
        {"kind": <str>, "amount": <int>, "probability": <float>},
        ...
      ]
    },
    ...
  ]
}
```

**Response:**

```json
{
  "format": "nodelock-config-v1",
  "validated_locks": [
    {"information_key": <str>, "owner": <int>, "distribution": [...]},
    ...
  ],
  "game_fingerprint": <str>
}
```

**Validation rules:**

- InfoKey must exist in game tree
- InfoKey must have declared owner
- Distribution keys must equal complete legal action set
- Every probability must be finite and in [0, 1]
- Probabilities must sum to 1 within documented tolerance (1e-10 input, 1e-12 computation)
- Impossible or unreachable keys rejected during setup
- Multiple exact locks supported
- Locked information sets use fixed distribution in all traversals
- Regret updates skipped for locked owner at locked information set
- Strategy sums still accumulate locked distribution with owner-reach weighting
- Lock adherence checked independently at every locked key after solving

### 3.7 Player profiles

**Endpoint:** `apply_profile(config: dict) -> dict`

**Request:**

```json
{
  "version": 3,
  "game_config": <game configuration>,
  "profiles": [
    {
      "player": <int>,
      "incentives": {
        "check": <number>,
        "call": <number>,
        "fold": <number>,
        "aggressive": <number>
      }
    },
    ...
  ]
}
```

**Response:**

```json
{
  "format": "profile-config-v1",
  "validated_profiles": [
    {"player": <int>, "incentives": {...}},
    ...
  ],
  "game_fingerprint": <str>
}
```

**Incentive calculation:**

```
bonus = coefficient[action_category] * reference_pot
```

Reference pot is matched pot before action, excludes uncalled excess.

**Shaped utility:**

```
shaped_terminal_utility = actual_terminal_utility + sum(profile_bonuses_on_player_path)
```

**Validation rules:**

- Coefficients must be finite JSON numbers (not booleans)
- Unknown action categories rejected
- Solver trains against shaped utilities
- Reported poker EV recomputed from final strategy using original unshaped returns
- Output must expose both `actual_ev` and optional `profile_objective` (labeled virtual)
- Virtual bonuses never enter pots, stacks, rake, or conservation checks
- Exact nodelocks take precedence over profile optimization at same information set
- Precedence explicit in serialized configuration

### 3.8 Rake

**Endpoint:** `apply_rake_policy(config: dict) -> dict`

**Request:**

```json
{
  "version": 3,
  "rate_numerator": <int>,
  "rate_denominator": <int>,
  "cap_chips": <int> | null,
  "minimum_rakeable_pot": <int> | null,
  "no_flop_no_drop": <bool>,
  "rounding": "floor" | "ceiling" | "nearest_ties_to_even",
  "base": "matched_pot"
}
```

**Response:**

```json
{
  "format": "rake-policy-v1",
  "validated_policy": {...}
}
```

**Rake calculation:**

```
if no_flop_no_drop and not flop_seen: raw = 0
else if minimum_rakeable_pot is set and P < minimum: raw = 0
else raw = round_policy(P * numerator / denominator)
rake = min(P, raw, cap_chips if configured else P)
awardable = P - rake
```

**Validation rules:**

- `0 <= numerator <= denominator`
- `denominator > 0`
- Cap and minimum must be non-negative integers if set
- Rake computed once for hand, not per player or per side pot
- Rake allocated across layers by deterministic policy (default: top-down)
- Layer allocations must sum exactly to hand rake
- Conservation: `sum(final_stacks) + house_rake == initial_total`
- Player utilities: `sum(player_utilities) == -house_rake`

### 3.9 Opponent range inference

**Endpoint:** `infer_opponent_range(config: dict) -> dict`

**Request:**

```json
{
  "version": 3,
  "prior": [{"cards": [<str>, <str>], "weight": <number>}, ...],
  "dead_cards": [<str>, ...],
  "observations": [
    {
      "public_history": <canonical history>,
      "observed_action": <Action>,
      "likelihood_source": "strategy" | "nodelock" | "profile" | "explicit",
      "likelihood_data": <depends on source>
    },
    ...
  ],
  "output": "explicit-combos" | "explicit-and-classes"
}
```

**Response:**

```json
{
  "format": "poker-solver-posterior-v1",
  "posterior": [
    {"cards": [<str>, <str>], "probability": <float>},
    ...
  ],
  "evidence_probabilities": [<float>, ...],
  "removed_blockers": [[<str>, <str>], ...],
  "observation_history": [...],
  "model_provenance": <str>,
  "class_posterior": [...],
  "warning": "conditional_on_supplied_behavior_model"
}
```

**Bayesian update:**

```
P(h | a_1,...,a_T) = w(h) * product_t L_t(h) / Z
Z = sum_k w(k) * product_t L_t(k)
```

**Numerical stability (log-space):**

```
log_mass(h) = log(w(h)) + sum_t log(L_t(h))
m = max(log_mass)
scaled(h) = exp(log_mass(h) - m)
posterior(h) = scaled(h) / sum_k scaled(k)
```

**Validation rules:**

- Prior weights must be finite, non-negative
- Dead cards must be strict card strings
- Card collisions rejected
- Positive remaining prior mass required
- Likelihood coverage must be complete for all compatible combos
- Likelihoods must be in [0, 1]
- Zero total evidence probability (Z == 0) fails with impossible-evidence error
- NaN and infinity always invalid
- No epsilon, probability floor, clipping, or Laplace smoothing unless explicitly requested
- Sequential updates: `posterior_t(h) ∝ posterior_(t-1)(h) * L_t(h)`
- Both direct multiplication and log-space paths must agree within 1e-15 on fixtures

### 3.10 Three-way postflop solving

**Endpoint:** `solve_multiway(config: dict) -> dict`

**Request:**

```json
{
  "version": 3,
  "game": "holdem-multiway",
  "num_players": 3,
  "starting_street": "flop" | "turn" | "river",
  "starting_board": [<str>, ...],
  "button_seat": <int>,
  "stacks": [<int>, <int>, <int>],
  "pot": <int>,
  "player_combos": [
    [{"cards": [<str>, <str>], "weight": <number>}, ...],
    [...],
    [...]
  ],
  "allowed_runouts": [[<str>, ...], ...],
  "wager_targets": [<int>, ...],
  "rake_policy": <rake config> | null,
  "algorithm": "vanilla-nplayer-cfr" | "external-sampling-nplayer-mccfr",
  "iterations": <int>,
  "seed": <int> | null
}
```

**Response:**

```json
{
  "format": "multiway-solve-result-v1",
  "algorithm": <str>,
  "seed": <int> | null,
  "iterations": <int>,
  "values": [<float>, <float>, <float>],
  "generalized_nash_conv": <float>,
  "best_response_values": [<float>, <float>, <float>],
  "unilateral_incentives": [<float>, <float>, <float>],
  "strategy": <serialized strategy>,
  "metadata": {
    "num_players": 3,
    "game": "holdem-multiway",
    "exact_br_computed": <bool>,
    "no_nash_guarantee_warning": "CFR has no general Nash convergence guarantee for multiplayer games"
  }
}
```

**N-player protocol:**

- `num_players() -> int`
- `current_player() -> CHANCE | TERMINAL | player_index`
- `legal_actions()`
- `chance_outcomes()`
- `child(action)`
- `information_state_key(player)`
- `returns() -> tuple[float, ...]` of length `num_players`

**Generalized NashConv:**

```
generalized_nash_conv = sum_i (BR_i(sigma_-i) - u_i(sigma))
```

where `BR_i(sigma_-i)` is player i's best response value when all other players' strategies are fixed.

**Validation rules:**

- `num_players` must be 3 for Phase 3 Tier 1
- Stacks, pot must be non-negative integers
- Combo weights finite, in [0, 1]
- Card collisions rejected
- Root chance enumerates compatible ordered triples `(h0, h1, h2)` with mass `w0*w1*w2`
- Chance probabilities finite, non-negative, sum to 1 within 1e-12
- Pot layers constructed from total contributions
- Folded players fund layers but never eligible to win
- Odd-chip policy explicit (default: clockwise from button)
- No-rake chip EV: `sum_i returns_i == 0` exactly
- With rake: `sum_i returns_i == -rake`
- No `half_nash_conv` or two-player "exploitability" label
- Output must include Nash guarantee warning

### 3.11 Preset library

**Endpoint:** `load_preset(name: str) -> dict`

**Endpoint:** `list_presets() -> dict`

**Response:**

```json
{
  "format": "preset-library-v1",
  "presets": [
    {
      "name": <str>,
      "description": <str>,
      "game": <str>,
      "config": <game configuration>
    },
    ...
  ]
}
```

**Validation rules:**

- Preset names must be valid identifiers
- Each preset config must pass full validation for its game type
- Presets are read-only canonical examples
- No user modification of preset library via API

## Strict validation rules (all endpoints)

### Type strictness

1. **Booleans are not integers:** `isinstance(value, bool)` check before `isinstance(value, int)`
2. **Finite numbers only:** `isfinite(value)` required for all numeric fields
3. **No NaN, no infinity:** Explicit rejection
4. **Strict JSON types:** No silent type coercion

### Numeric validation

1. **Integer fields:** `_strict_int(value, field)` — rejects booleans and floats
2. **Positive integers:** `_strict_positive_int(value, field)` — `value > 0`
3. **Non-negative integers:** `_strict_nonnegative_int(value, field)` — `value >= 0`
4. **Finite numbers:** `_strict_number(value, field)` — rejects booleans, requires `isfinite`
5. **Non-negative numbers:** `_strict_nonnegative_number(value, field)` — `value >= 0`
6. **Probability bounds:** Weights and probabilities in `[0, 1]`
7. **Decimal precision:** Use decimal text representation for rounding, not binary float

### Card validation

1. **Strict two-character format:** `rank + suit`, no case normalization
2. **Valid ranks:** `23456789TJQKA`
3. **Valid suits:** `cdhs`
4. **No duplicates:** Card collision detection across board, dead cards, combos
5. **Blocker removal:** Compatible combos only after removing collisions

### Range validation

1. **Empty combo lists rejected**
2. **Zero total weight rejected**
3. **Weights in [0, 1]**
4. **Finite weights required**
5. **Combo uniqueness:** Sorted tuple identity, duplicates rejected

### Strategy validation

1. **Complete coverage:** All information sets must have policies
2. **Action probabilities sum to 1:** Within 1e-12 (computation) or 1e-10 (input)
3. **Probabilities in [0, 1]**
4. **Finite probabilities**
5. **Action set match:** Strategy actions must equal legal actions at information set

### Configuration validation

1. **Unknown fields rejected:** Exact field set required
2. **Missing required fields rejected**
3. **Duplicate JSON keys rejected:** Use `object_pairs_hook`
4. **Version mismatch rejected**
5. **Size limits enforced:** MAX_COMBOS, MAX_RUNOUTS, MAX_WAGERS, etc.

### Error handling

1. **Exit status 2:** Invalid input/configuration
2. **Exit status 1:** Internal runtime failure
3. **Structured error messages:** Field name, constraint violated, actual value
4. **No silent recovery:** No NaN replacement, no clamping, no partial results
5. **Fail-closed:** Invalid input rejected before tree construction

## Versioning and backward compatibility

### Version 1 (Phase 1)

- `solve-kuhn`
- `solve-spot` (river game)
- `evaluate`
- `equity`

**Status:** Unchanged, fully supported

### Version 2 (Phase 2)

- `load_multistreet_config`
- `solve_multistreet`
- `compute_exploitability`
- `serialize_strategy` / `deserialize_strategy`

**Status:** Unchanged, fully supported

### Version 3 (Phase 3)

All new endpoints listed in section "Phase 3 operation matrix" above.

**Compatibility rules:**

1. Version 1 and 2 APIs remain byte-identical
2. Version 3 requests must include `"version": 3`
3. Version 2 requests with `"version": 2` continue to work
4. Unknown version numbers rejected
5. New fields in version 3 do not appear in version 2 responses
6. Serialized strategies include format version
7. Strategy deserialization validates against exact game tree version
8. Configuration fingerprints prevent applying stale strategies to edited games

## Deterministic output rules

### Serialization

1. **Sorted keys:** `json.dumps(sort_keys=True)`
2. **Canonical ordering:** Information sets by `repr(key)`, actions by `(kind, amount)`
3. **No NaN:** `json.dumps(allow_nan=False)`
4. **Deterministic floats:** Shortest decimal text that round-trips
5. **Stable iteration order:** Deterministic combo/action/infoset enumeration

### Solver determinism

1. **Vanilla CFR:** Fully deterministic, no seed parameter
2. **MCCFR:** Deterministic for same seed on same platform/interpreter
3. **No cross-platform byte-identity claim**
4. **Stable action ordering:** Chance and legal actions in deterministic order
5. **Seeded RNG:** Solver-owned `random.Random(seed)` for MCCFR

### Numerical determinism

1. **Exact integer accounting:** No floating tolerance for chip amounts
2. **Probability sums:** Within 1e-12 for computation, 1e-10 for input validation
3. **EV comparisons:** Absolute tolerance 1e-12 unless fixture declares measured threshold
4. **Rounding:** Decimal round-half-up, applied once after complete formula
5. **Conservation:** Exact integer equality for chip conservation

## Module dependencies

### Core modules (existing, Phase 1+2)

- `model.py` — Generic game protocol
- `cards.py` — Card parsing and validation
- `evaluator.py` — Hand evaluation
- `equity.py` — Exact equity calculation
- `kuhn.py` — Kuhn poker game
- `river.py` — River Hold'em game
- `multistreet.py` — Multi-street postflop game
- `cfr.py` — Vanilla CFR solver
- `mccfr.py` — External-sampling MCCFR solver
- `best_response.py` — Exact best response and NashConv
- `audit.py` — Game tree validation
- `api.py` — Version 2 JSON API
- `cli.py` — Command-line interface

### New modules (Phase 3)

**Tier 1 (must implement):**

- `preflop.py` — Heads-up preflop game state
  - Depends on: `model.py`, `cards.py`, `evaluator.py`, `equity.py`
- `continuation.py` — Preflop continuation models (all-in-runout, table, checkdown-equity)
  - Depends on: `preflop.py`, `evaluator.py`, `equity.py`
- `sizing.py` — Bet sizing conversion and selection
  - Depends on: `model.py`
- `ranges.py` — Range editor, parser, serializer
  - Depends on: `cards.py`, `equity.py`
- `display.py` — Range/strategy table computation
  - Depends on: `model.py`, `ranges.py`, `best_response.py`
- `tree_edit.py` — Tree editing and validation
  - Depends on: `model.py`, `audit.py`
- `nodelock.py` — Exact nodelocking
  - Depends on: `model.py`, `cfr.py`
- `profiles.py` — Player profile incentives
  - Depends on: `model.py`, `cfr.py`
- `rake.py` — Rake policy and accounting
  - Depends on: `multistreet.py`
- `inference.py` — Bayesian opponent range inference
  - Depends on: `model.py`, `ranges.py`
- `multiway.py` — Three-way postflop game state
  - Depends on: `model.py`, `cards.py`, `evaluator.py`, `equity.py`
- `nplayer_cfr.py` — N-player CFR solver
  - Depends on: `model.py`, `multiway.py`
- `api_v3.py` — Version 3 JSON API (extends `api.py`)
  - Depends on: all Phase 3 modules

**Tier 2 (extended):**

- `presets.py` — Canonical spot preset library
  - Depends on: `api_v3.py`

**Tier 3 (documented boundary):**

- Nine-way preflop: Configuration model only, no strategic solving
- ICM/bounties: Documented boundary, not implemented
- DDLS/Fast engine: Documented boundary, not implemented

### Dependency graph (Phase 3 additions)

```
model.py  <--- preflop.py <--- continuation.py
  ^              ^                  ^
  |              |                  |
  |            sizing.py            |
  |              ^                  |
  |              |                  |
cards.py <--- ranges.py <--- display.py
  ^              ^              ^
  |              |              |
evaluator.py    |              |
  ^              |              |
  |              |              |
equity.py       |              |
  ^              |              |
  |              |              |
  +----------inference.py      |
                 ^              |
                 |              |
              tree_edit.py     |
                 ^              |
                 |              |
              nodelock.py      |
                 ^              |
                 |              |
              profiles.py      |
                 ^              |
                 |              |
multistreet.py <--- rake.py    |
  ^                             |
  |                             |
multiway.py <--- nplayer_cfr.py|
  ^                             |
  |                             |
  +-----------------------------+
                                |
                             api_v3.py <--- presets.py
```

## Acceptance tests

Each Phase 3 module requires:

### Unit tests

1. **Formula fixtures:** Hand-calculated expected values, exact integer matches
2. **Boundary tests:** Min/max values, edge cases, one-off errors
3. **Rejection tests:** Invalid input, malformed JSON, type errors
4. **Round-trip tests:** Serialize → deserialize → exact equality
5. **Determinism tests:** Input permutation cannot change canonical output

### Integration tests

1. **Cross-module identity:** Sizing targets match game actions exactly
2. **Conservation:** Chip accounting sums to zero (or negative rake)
3. **Strategy consistency:** Action probabilities sum to 1 within tolerance
4. **EV identity:** Aggregate EV matches raw expected_values within tolerance
5. **Blocker agreement:** Range filtering matches independent enumeration

### Oracle tests

1. **Independent reference:** Treys for evaluation, analytical Kuhn for CFR
2. **Exhaustive enumeration:** Small games compared to brute-force
3. **Cross-checker agreement:** Multiple implementations of same calculation
4. **Known-answer fixtures:** Predeclared values from external sources
5. **Adversarial audit:** Non-author reviewers attack new code

### Regression tests

1. **Phase 1 tests remain green:** 80 tests unchanged
2. **Phase 2 tests remain green:** 185 tests unchanged
3. **Byte-determinism:** Same input produces same output bytes
4. **Performance gates:** Runtime ceilings from measured medians
5. **No silent degradation:** Convergence thresholds maintained

### API contract tests

1. **Version rejection:** Unknown versions fail with status 2
2. **Field validation:** Unknown/missing fields rejected
3. **Type strictness:** Booleans as integers rejected
4. **Finite validation:** NaN/infinity rejected
5. **Size limits:** Oversized inputs rejected at tested limits
6. **Backward compatibility:** Version 1 and 2 requests unchanged

## Acceptance criteria summary

Phase 3 complete when:

1. ✓ All 185 Phase 1+2 tests remain green
2. ✓ Every Tier 1 feature has:
   - Complete implementation
   - Unit tests with exact fixtures
   - Integration tests with cross-module identity
   - Oracle tests with independent reference
   - Adversarial audit sign-off in review/phase3/
3. ✓ API v3 endpoints:
   - Strict validation per contracts above
   - Deterministic output
   - Backward compatibility verified
   - Error handling tested (status 2 for invalid input)
4. ✓ Documentation:
   - ARCHITECTURE_PHASE3.md implemented-vs-boundary matrix
   - README updated with feature list
   - API examples for each endpoint
5. ✓ No invented capabilities:
   - Exact existing API surface documented
   - No endpoints claimed without implementation
   - Documented boundaries explicit

---

**Report complete.** This document defines the strict JSON API v3 architecture for Phase 3 GTO Wizard feature parity. All contracts are derived from observed code, research reports, and mission requirements. No existing endpoints invented.
