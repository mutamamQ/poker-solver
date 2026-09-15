# Nodelocking and player profiles: Phase 3 architecture

## 1. Scope and correctness claim

This design specifies the Phase 3 nodelocking and player-profile architecture for the poker-solver repository. It preserves the existing immutable `GameState` protocol, `InfoKey`-based solver architecture, and `collect_infosets` consistency enforcement. Nodelocks constrain CFR traversal at specified information sets using exact probability distributions. Player profiles shape terminal utilities through action-category incentives. Both features operate on `InfoKey` identities and deterministic public selectors, never mutable UUID nodes.

**Implemented target:**

- Multiple full-distribution information-set locks with exact probability validation
- Seat-wide action-incentive profiles (check, call, fold, aggressive categories)
- Separate shaped training objective and actual EV reporting
- Strict regret and average-policy accumulation under locks
- Deterministic profile composition and provenance tracking
- JSON/CLI contracts with schema versioning
- Exact matrix/toy-game tests with analytical oracles

**Documented boundary:**

- Partial/hand-specific/frequency-bound locks
- Live mutation of an in-progress solver
- Safe regret warm starts after configuration changes
- Claiming MinES/MaxES or proprietary GTO Wizard behavior
- Named population profiles beyond explicitly sourced demonstrations
- Forward-looking, learned, street/node/size-dependent behavioral models

## 2. Exact nodelocks

### 2.1 InfoKey lock semantics

An exact lock maps one `InfoKey` to a complete probability distribution over that information set's legal actions:

```python
locks: dict[InfoKey, dict[Action, float]]
```

Each lock entry specifies:

- **Key:** An `InfoKey` returned by `GameState.information_state_key(player)` for some player.
- **Value:** A dictionary mapping every legal `Action` at that information set to a probability in `[0, 1]`.

**Lock identity:** Locks are keyed by `InfoKey`, which is defined as `Hashable` in `model.py`. The repository's `collect_infosets` function enforces that every occurrence of an `InfoKey` has the same owner and identical ordered legal action tuple. This consistency guarantee is the foundation for lock semantics.

**Scope:** Phase 3 supports multiple exact locks. It does not support:

- Private-hand subsets (locking only specific hole cards within an information set)
- Probability bounds or ranges (e.g., "fold at least 20%")
- Relative-frequency shifts (e.g., "increase folding by 10%")
- Partial residual optimization (optimizing over a subset of actions)

### 2.2 Strict probability validation

Before accepting a lock configuration, validation requires:

1. **Key existence:** The `InfoKey` exists in the game tree (obtained via `collect_infosets(root)`).
2. **Owner consistency:** The key's owner matches the declared locked player.
3. **Action completeness:** The lock dictionary keys equal the complete legal action set for that information set (no missing actions, no extra actions).
4. **Finite probabilities:** Every probability is finite (`isfinite(p)` returns `True`).
5. **Non-negative probabilities:** Every probability satisfies `p >= 0`.
6. **Unit sum:** Probabilities sum to `1.0` within a documented numerical tolerance (default `1e-10`, matching `best_response.py:validate_strategy`).
7. **Reachability:** Impossible or unreachable keys are rejected during setup rather than silently ignored.

Validation uses the existing `collect_infosets` function from `cfr.py` to obtain the ground-truth action tuple for each `InfoKey`. The validation logic mirrors `validate_strategy` from `best_response.py` (lines 25-37), which already enforces action-set equality, finite non-negative probabilities, and unit sum.

**Rejection semantics:** Any validation failure produces a structured error (e.g., `ValueError` with a descriptive message citing the failing `InfoKey` and constraint). The solver configuration remains unchanged.

### 2.3 Regret and average-policy accumulation under locks

At a locked information set, CFR traversal behavior changes:

**During traversal (`CFRSolver._walk` and `MCCFRSolver._walk`):**

1. **Policy override:** At a locked `InfoKey`, the traversal uses the fixed lock distribution instead of the regret-matched policy from `regret_matching(data.regrets, data.actions)`.
2. **Regret updates skipped:** Regret deltas for the locked owner at that information set are not accumulated. The locked player's regrets remain unchanged at that key.
3. **Strategy sum accumulation:** The locked distribution is still accumulated into `data.strategy_sum` with the same owner-reach weighting as unlocked information sets. This ensures the exported average strategy reports the constraint exactly.

**Rationale:** Skipping regret updates prevents the solver from "fighting" the lock. Accumulating the locked distribution into strategy sums ensures that `average_strategy()` returns the locked policy at that key, making the constraint visible in exported strategies.

**Implementation notes:**

- The existing `CFRSolver.train` method (lines 105-127 in `cfr.py`) performs two `_walk` calls per iteration, one per player. The `_walk` method (lines 129-158) computes action values, updates regrets via `deltas`, and accumulates strategy sums via `owner_reaches`.
- Lock support requires:
  - Checking if the current `key` is in the lock dictionary before calling `regret_matching`.
  - Using the locked distribution if present.
  - Skipping the regret delta accumulation (`deltas[key][action] += ...`) for locked keys.
  - Continuing to accumulate `data.strategy_sum[action] += owner_reaches[key] * policy[action]` using the locked policy.

- The existing `MCCFRSolver.train` method (lines 117-125 in `mccfr.py`) performs two `_walk` calls per iteration. The `_walk` method (lines 127-168) uses external sampling. Lock support requires:
  - Checking if the current `key` is locked before calling `regret_matching`.
  - Using the locked distribution if present.
  - Skipping regret updates (`data.regrets[action] += ...`) for locked keys.
  - Continuing to accumulate `data.strategy_sum[action] += policy[action]` using the locked policy (line 161).

**Reach arithmetic:** All other information sets update normally. Chance and reach arithmetic remain identical to the existing synchronous solver. The locked distribution participates in reach propagation exactly as an unlocked policy would.

### 2.4 Constrained-game equilibrium semantics

A lock constrains the modeled game. The resulting strategy is an equilibrium/no-regret solution of that constrained game to the extent supported by the underlying solver and iteration budget.

**What locks guarantee:**

- The locked player plays the specified distribution at the locked information set.
- The unlocked player (and unlocked information sets of the locked player) adapt via regret minimization.
- If the opponent is fully fixed (all opponent information sets locked), the unrestricted player should converge toward a best response.
- If only some opponent information sets are fixed, unfixed information sets continue adapting.

**What locks do NOT guarantee:**

- "Minimally exploitative" or "maximally exploitative" behavior (these are not API guarantees).
- Nash equilibrium of the original unconstrained game.
- Optimality claims beyond the CFR convergence properties.

**Actual EV computation:** After training, actual EV is computed with the existing `expected_values` traversal (defined in `cfr.py` lines 58-77 and `mccfr.py` lines 35-54) over the exported average strategy profile. Lock adherence is checked independently at every locked key by comparing the exported `average_strategy()[key]` against the lock distribution.

### 2.5 Exact oracle: one-step matrix game

Use a one-step zero-sum matrix game represented as imperfect information:

```text
P0 chooses A or B (private).
P1 then chooses X or Y without observing P0.
P0 payoff matrix:
        X   Y
A       2  -1
B       0   1
```

**Analytical expectations:**

1. **Lock P1 to `{X: 1.0, Y: 0.0}`:** P0's unique best response is `{A: 1.0, B: 0.0}` with EV = 2.
2. **Lock P1 to `{Y: 1.0, X: 0.0}`:** P0's unique best response is `{B: 1.0, A: 0.0}` with EV = 1.
3. **Lock P1 to `{X: 0.5, Y: 0.5}`:** P0's best response is `{A: 1.0, B: 0.0}` with EV = 0.5.
4. **No lock:** Cross-check against the existing `best_response` and `nash_conv` functions from `best_response.py`.

**Test assertions:**

- Exported `average_strategy()[p1_key]` matches the lock distribution exactly (within tolerance).
- P0's exported strategy matches the analytical best response (within tolerance).
- `expected_values(root, average_strategy())` returns the analytical EV (within tolerance).
- Exhaustive pure-strategy enumeration agrees with CFR output.
- Locks remain unchanged over repeated `train` calls.
- Malformed distributions (missing actions, NaN, negative, non-unit sum) are rejected with structured errors.

**Implementation:** The matrix game can be implemented as a `GameState` with two decision nodes (P0's choice, then P1's choice) and four terminal nodes. The `InfoKey` for P1 is the same regardless of P0's choice (imperfect information).

### 2.6 Additional lock tests

- **Unchanged locks over training:** Lock a key, train for N iterations, verify the exported strategy at that key equals the lock distribution. Train for another M iterations, verify again.
- **Multiple locks:** Lock two or more information sets simultaneously, verify all are respected.
- **Tree-edit invalidation:** After a tree edit that changes the action set at a locked key, the lock must be rejected or explicitly remapped (never silently dropped). This is enforced by the tree-editing validation (see `tree-editing.md` section 3.3, rule 8).

## 3. Player profiles through action incentives

### 3.1 Contract and action categories

A profile assigns a seat a finite incentive coefficient for each supported action category:

```python
profile: dict[int, dict[str, float]]
# profile[seat][category] = coefficient
```

**Supported categories:**

- `"check"`: Check actions (`Action("CHECK", 0)`).
- `"call"`: Call actions (`Action("CALL", amount)`).
- `"fold"`: Fold actions (`Action("FOLD", 0)`).
- `"aggressive"`: Bet and raise actions (`Action("RAISE", amount)`).

**Validation:**

- Coefficients must be finite (`isfinite(c)`).
- Unknown action kinds fail validation with a structured error.
- Coefficients are explicit inputs; Phase 3 does not invent named Fish/Nit/TAG/LAG presets.

**Demonstration profile:** A documented `maniac_demo` may reproduce the public GTO Wizard Maniac example:

```python
maniac_demo = {
    "aggressive": 0.06,
    "call": 0.03,
    "fold": -0.06,
    "check": 0.0,
}
```

This is clearly labeled as a product-derived demonstration rather than a calibrated population model. Source: https://blog.gtowizard.com/exploiting-profiles-episode-iii-the-maniac/

### 3.2 Reference pot and bonus computation

At a decision with reference pot `P`, choosing category `c` contributes virtual reward:

```text
bonus = coefficient[c] * P
```

**Reference pot definition:** The matched pot before the action, excluding uncalled excess. For a two-player game, this is the sum of both players' current-street commitments up to the smaller of the two, plus the pot carried forward from previous streets.

**Example:** If P0 has committed 10 and P1 has committed 10 on the current street, and the pot from previous streets is 20, then `P = 10 + 10 + 20 = 40`.

**Coefficient representation:** Coefficients use an exact decimal/rational input at the API boundary and convert to solver numeric type (`float`) deliberately. Input validation ensures finite values.

### 3.3 Shaped-game solution

Profiles define a shaped behavioral game. A player's shaped terminal utility is:

```text
shaped_utility[player] = actual_terminal_utility[player] + sum(profile_bonuses_on_player_path)
```

**Implementation requirements:**

1. **Separate value channels:** The solver must carry accumulated per-player bonuses through traversal or use an equivalent exact transformation.
2. **No `-child_value` shortcuts:** For the existing two-player solver, the implementation must keep separate value channels or expose a utility wrapper that returns each player's shaped payoff. It must not rely on zero-sum `-child_value` shortcuts, because shaped utilities are not zero-sum.
3. **Exact accumulation:** Adding a bonus to a child value and then returning an unrelated "actual" recursion is invalid. The shaped value must be the actual terminal utility plus the exact sum of bonuses on that player's path.

**Solver training:** The solver trains against shaped utilities. The regret updates and strategy accumulation use shaped values. This is labeled behavioral modeling, not Nash solving of the original poker game.

### 3.4 Actual EV versus shaped EV reporting

After training, reported poker EV is always recomputed from the final strategy using original, unshaped terminal returns.

**Required reports:**

- `actual_ev`: Real chip/money utility, computed via `expected_values(root, average_strategy())` using the original `GameState.returns()` without bonuses.
- `shaped_ev` (optional diagnostic): Virtual utility including bonuses, clearly labeled as non-monetary.

**Separation enforcement:** The virtual bonuses never enter pots, stacks, rake, ICM prizes, or conservation checks. Reports must expose both values and clearly distinguish them. Attempting to report shaped value as actual EV is a validation error.

### 3.5 Scope and precedence

Initial support is seat-wide across the solved tree. Street-specific, node-specific, private-hand-specific, learned, state-dependent, and bet-size-dependent incentives are documented boundaries.

**Lock precedence:** Exact nodelocks take precedence over profile optimization at the same information set. If a key is locked, the locked policy is used unchanged, while path bonuses may still be accumulated for diagnostic shaped value. This precedence must be explicit in serialized configuration.

**Model interpretation:** The model captures preferences encoded by the coefficients; it is not evidence about a real opponent.

### 3.6 Profile oracle: one-player choice

Use a one-player choice with actual payoffs:

```text
P0 chooses CHECK or CALL.
Actual payoffs: CHECK = 0, CALL = -1.
Reference pot: 10.
```

**Analytical expectations:**

1. **No profile:** Unique choice is CHECK (EV = 0).
2. **Call coefficient 0.2:** Shaped CALL payoff is `-1 + 0.2 * 10 = 1`, so the unique shaped choice is CALL. Exported actual EV under the CALL policy is `-1`, while shaped EV is `1`.
3. **Call coefficient -0.05:** Shaped CALL payoff is `-1 + (-0.05) * 10 = -1.5`, so the unique shaped choice is CHECK. Exported actual EV is `0`, shaped EV is `0`.

**Test assertions:**

- Exported `average_strategy()[p0_key]` matches the analytical shaped best response.
- `actual_ev` matches the analytical actual payoff.
- `shaped_ev` matches the analytical shaped payoff.
- The two EVs differ when the profile is active.

**Two-player matrix fixture:** A second fixture verifies that the unprofiled opponent adapts to the profile-shaped policy and that exhaustive enumeration agrees with the bounded solver. Use a 2x2 matrix game where P0 has a profile and P1 is unprofiled. Verify that P1's exported strategy is a best response to P0's shaped strategy.

## 4. Deterministic profile composition and provenance

### 4.1 Configuration fingerprint

A configuration fingerprint uniquely identifies a game and constraint set:

```python
@dataclass(frozen=True)
class ConfigFingerprint:
    schema_version: str  # "nodelock-profile-v1"
    game_hash: str  # deterministic hash of game structure
    locks: tuple[tuple[InfoKey, tuple[tuple[Action, float], ...]], ...]  # sorted
    profiles: tuple[tuple[int, tuple[tuple[str, float], ...]], ...]  # sorted by seat
    lock_precedence: bool  # True if locks override profiles
```

**Deterministic serialization:**

- Locks are sorted by `InfoKey` (using a canonical string representation).
- Within each lock, actions are sorted by `(kind, amount)`.
- Profiles are sorted by seat.
- Within each profile, categories are sorted alphabetically.
- The fingerprint is serialized to canonical JSON with sorted keys.

**Game hash:** The game structure hash includes the root state's configuration (stack sizes, blinds, deck, allowed runouts, etc.) but excludes solver state (regrets, strategy sums, iteration count).

### 4.2 Solution metadata

A solution metadata record includes:

```python
@dataclass
class SolutionMetadata:
    config_fingerprint: ConfigFingerprint
    solver_mode: str  # "vanilla_cfr" or "mccfr"
    iterations: int
    seed: int | None  # for MCCFR
    value_type: str  # "actual" or "shaped"
    timestamp: str  # ISO 8601
```

**Fingerprint mismatch:** A solution fingerprint mismatch prevents applying old strategies, locks, or convergence metadata to an edited game. Loading a solution with a mismatched fingerprint produces a structured error.

### 4.3 Provenance tracking

Each lock and profile entry records its source:

```python
@dataclass
class LockEntry:
    key: InfoKey
    distribution: dict[Action, float]
    source: str  # "user", "imported", "maniac_demo", etc.
    timestamp: str  # ISO 8601

@dataclass
class ProfileEntry:
    seat: int
    coefficients: dict[str, float]
    source: str  # "user", "maniac_demo", etc.
    timestamp: str  # ISO 8601
```

**Source labels:**

- `"user"`: Manually specified by the user.
- `"imported"`: Loaded from a file or external source.
- `"maniac_demo"`: The documented GTO Wizard Maniac demonstration.
- Custom labels for other sources.

**Audit trail:** The configuration file includes a provenance section listing all lock and profile entries with their sources and timestamps. This enables auditing and debugging.

## 5. JSON/CLI contracts

### 5.1 JSON schema for locks

```json
{
  "locks": [
    {
      "info_key": "<canonical_string_representation>",
      "distribution": {
        "CHECK:0": 0.5,
        "RAISE:20": 0.5
      },
      "source": "user",
      "timestamp": "2026-09-14T12:00:00Z"
    }
  ]
}
```

**InfoKey representation:** The `InfoKey` is serialized to a canonical string representation. For tuple-based keys, this is a deterministic JSON array. For custom hashable keys, a deterministic string encoding is defined.

**Action representation:** Actions are serialized as `"kind:amount"` strings (e.g., `"CHECK:0"`, `"RAISE:20"`).

### 5.2 JSON schema for profiles

```json
{
  "profiles": [
    {
      "seat": 0,
      "coefficients": {
        "aggressive": 0.06,
        "call": 0.03,
        "fold": -0.06,
        "check": 0.0
      },
      "source": "maniac_demo",
      "timestamp": "2026-09-14T12:00:00Z"
    }
  ]
}
```

### 5.3 CLI commands

**Lock management:**

```bash
# Add a lock
poker-solver lock add --key <key_repr> --distribution <json_file> --source user

# Remove a lock
poker-solver lock remove --key <key_repr>

# List locks
poker-solver lock list

# Validate locks against current game
poker-solver lock validate
```

**Profile management:**

```bash
# Set a profile
poker-solver profile set --seat 0 --coefficients <json_file> --source user

# Remove a profile
poker-solver profile remove --seat 0

# List profiles
poker-solver profile list

# Load a demonstration profile
poker-solver profile load --name maniac_demo --seat 0
```

**Solving with constraints:**

```bash
# Solve with locks and profiles
poker-solver solve --iterations 10000 --locks locks.json --profiles profiles.json --output solution.json

# Report actual and shaped EV
poker-solver report --solution solution.json --ev-type actual
poker-solver report --solution solution.json --ev-type shaped
```

### 5.4 API error codes

- `LOCK_KEY_NOT_FOUND`: The specified `InfoKey` does not exist in the game tree.
- `LOCK_ACTION_MISMATCH`: The lock distribution actions do not match the legal actions at the key.
- `LOCK_INVALID_PROBABILITY`: A probability is NaN, infinite, negative, or the sum is not 1.0.
- `LOCK_STALE_AFTER_EDIT`: A lock references a key that was invalidated by a tree edit.
- `PROFILE_INVALID_COEFFICIENT`: A coefficient is NaN or infinite.
- `PROFILE_UNKNOWN_CATEGORY`: An action category is not in the supported set.
- `FINGERPRINT_MISMATCH`: The solution fingerprint does not match the current configuration.
- `SHAPED_EV_AS_ACTUAL`: Attempted to report shaped EV as actual EV.

## 6. Exact matrix/toy-game tests

### 6.1 Matrix game: lock test

**Game:** One-step matrix game (P0 chooses A/B, P1 chooses X/Y, payoff matrix as in section 2.5).

**Tests:**

1. Lock P1 to `{X: 1.0, Y: 0.0}`, train CFR for 1000 iterations, verify P0 plays `{A: 1.0, B: 0.0}` and EV = 2.
2. Lock P1 to `{Y: 1.0, X: 0.0}`, train CFR for 1000 iterations, verify P0 plays `{B: 1.0, A: 0.0}` and EV = 1.
3. Lock P1 to `{X: 0.5, Y: 0.5}`, train CFR for 1000 iterations, verify P0 plays `{A: 1.0, B: 0.0}` and EV = 0.5.
4. No lock, train CFR for 10000 iterations, verify `nash_conv` is low and agrees with `best_response`.
5. Lock P1 to `{X: 0.7, Y: 0.3}`, verify exported `average_strategy()[p1_key]` equals `{X: 0.7, Y: 0.3}` exactly.

**Tolerance:** `1e-3` for strategy probabilities, `1e-2` for EV (CFR convergence is approximate).

### 6.2 Matrix game: profile test

**Game:** One-player choice (P0 chooses CHECK/CALL, payoffs as in section 3.6).

**Tests:**

1. No profile, verify P0 plays `{CHECK: 1.0, CALL: 0.0}` and actual EV = 0.
2. Profile `{"call": 0.2}`, verify P0 plays `{CALL: 1.0, CHECK: 0.0}`, actual EV = -1, shaped EV = 1.
3. Profile `{"call": -0.05}`, verify P0 plays `{CHECK: 1.0, CALL: 0.0}`, actual EV = 0, shaped EV = 0.
4. Profile `{"call": 0.1}`, verify P0 plays `{CALL: 1.0, CHECK: 0.0}`, actual EV = -1, shaped EV = 0.

**Tolerance:** `1e-6` for strategy probabilities (deterministic one-player choice), `1e-6` for EV.

### 6.3 Two-player profile adaptation test

**Game:** 2x2 matrix game where P0 has a profile and P1 is unprofiled.

```text
P0 chooses A or B.
P1 chooses X or Y.
P0 payoff matrix:
        X   Y
A       1   0
B       0   1

P1 payoff matrix (zero-sum):
        X   Y
A      -1   0
B       0  -1
```

**Profile:** P0 has `{"aggressive": 0.1}` (assume A is aggressive, B is not). Reference pot = 10.

**Analytical expectation:**

- P0's shaped payoff for A is `1 + 0.1 * 10 = 2` (if P1 plays X) or `0 + 0.1 * 10 = 1` (if P1 plays Y).
- P0's shaped payoff for B is `0` (if P1 plays X) or `1` (if P1 plays Y).
- P0's shaped best response to uniform P1 is A (shaped EV = 1.5).
- P1's best response to P0 playing A is Y (EV = 0).
- Shaped equilibrium: P0 plays A, P1 plays Y. P0 actual EV = 0, P0 shaped EV = 1.

**Test:** Train CFR with P0 profiled, verify P0 plays A and P1 plays Y. Verify actual EV and shaped EV match analytical expectations.

### 6.4 Kuhn poker lock test

**Game:** Kuhn poker (existing `kuhn_root()` from `kuhn.py`).

**Test:** Lock one information set (e.g., P0 with Jack after P1 bets) to a specific distribution, train CFR for 10000 iterations, verify:

1. The locked key's exported strategy matches the lock distribution.
2. Other information sets adapt normally.
3. `expected_values` using the exported strategy is consistent.
4. Repeated training does not change the locked distribution.

### 6.5 Failure tests

Strictly reject:

1. **Missing action in lock:** Lock distribution omits a legal action.
2. **Extra action in lock:** Lock distribution includes an action not in the legal set.
3. **NaN probability:** Lock distribution contains `float('nan')`.
4. **Infinite probability:** Lock distribution contains `float('inf')`.
5. **Negative probability:** Lock distribution contains a negative value.
6. **Non-unit sum:** Lock distribution sums to 0.99 or 1.01 (outside tolerance).
7. **Stale lock after edit:** Tree edit changes the action set at a locked key, lock is not remapped.
8. **Invalid profile coefficient:** Profile contains `float('nan')` or `float('inf')`.
9. **Unknown action category:** Profile contains `{"unknown": 0.5}`.
10. **Shaped EV reported as actual:** API call requests actual EV but returns shaped EV.
11. **Fingerprint mismatch:** Load a solution with a different game hash.

Each failure produces a structured error with a descriptive message and error code.

## 7. Dependencies

### 7.1 Existing repository symbols

**From `model.py`:**

- `Action`: Frozen dataclass with `kind: str` and `amount: int`.
- `InfoKey`: Type alias for `Hashable`.
- `Strategy`: Type alias for `Mapping[InfoKey, ActionPolicy]`.
- `GameState`: Protocol with `current_player()`, `legal_actions()`, `information_state_key(player)`, `returns()`, `child(action)`, `chance_outcomes()`.
- `CHANCE`, `TERMINAL`: Constants for special player values.

**From `cfr.py`:**

- `collect_infosets(root: GameState) -> dict[InfoKey, tuple[int, tuple[Action, ...]]]`: Validates perfect recall and returns owner and action tuple for each key.
- `expected_values(root: GameState, profile: Strategy) -> tuple[float, float]`: Computes both players' expected values under a fixed strategy.
- `regret_matching(regrets: dict[Action, float], actions: tuple[Action, ...]) -> dict[Action, float]`: Converts cumulative regrets to a strategy.
- `CFRSolver`: Class with `__init__(root)`, `train(iterations)`, `current_strategy()`, `average_strategy()`, `iterations` attribute.
- `InfoData`: Dataclass with `player`, `actions`, `regrets`, `strategy_sum`.

**From `mccfr.py`:**

- `MCCFRSolver`: Class with `__init__(root, seed)`, `train(iterations)`, `current_strategy()`, `average_strategy()`, `iterations` attribute, `infosets` attribute.
- `regret_matching`: Same signature as `cfr.py`.
- `expected_values`: Same signature as `cfr.py`.

**From `best_response.py`:**

- `validate_strategy(root: GameState, profile: Strategy, tolerance: float = 1e-10) -> None`: Validates that a strategy is well-formed (correct actions, finite non-negative probabilities, unit sum).
- `best_response(root: GameState, opponent_profile: Strategy, player: int) -> tuple[float, dict[InfoKey, Action]]`: Computes infoset-consistent best response.
- `nash_conv(root: GameState, profile: Strategy) -> NashConvResult`: Computes Nash convergence metric.

### 7.2 New modules

**`nodelock.py`:**

- `LockConfig`: Dataclass for lock configuration.
- `validate_locks(root: GameState, locks: dict[InfoKey, dict[Action, float]]) -> None`: Validates lock configuration.
- `apply_locks(solver: CFRSolver | MCCFRSolver, locks: dict[InfoKey, dict[Action, float]]) -> None`: Applies locks to a solver instance.

**`profile.py`:**

- `ProfileConfig`: Dataclass for profile configuration.
- `validate_profile(profile: dict[str, float]) -> None`: Validates profile coefficients.
- `ShapedGameState`: Wrapper around `GameState` that adds profile bonuses to terminal utilities.
- `compute_actual_ev(root: GameState, strategy: Strategy) -> tuple[float, float]`: Computes actual EV without bonuses.
- `compute_shaped_ev(root: GameState, strategy: Strategy, profiles: dict[int, dict[str, float]]) -> tuple[float, float]`: Computes shaped EV with bonuses.

**`config_fingerprint.py`:**

- `ConfigFingerprint`: Dataclass for configuration fingerprint.
- `compute_fingerprint(root: GameState, locks: dict[InfoKey, dict[Action, float]], profiles: dict[int, dict[str, float]]) -> ConfigFingerprint`: Computes deterministic fingerprint.
- `serialize_fingerprint(fingerprint: ConfigFingerprint) -> str`: Serializes to canonical JSON.

### 7.3 Test dependencies

**Existing test utilities:**

- `kuhn_root()` from `kuhn.py`: Kuhn poker root state.
- `tiny_multistreet_root()` from `phase2_fixture.py`: Bounded multi-street fixture.
- `audit_game(root, max_nodes)` from `audit.py`: Game tree audit.
- `exhaustive_best_response(root, opponent_profile, player)` from `best_response.py`: Exhaustive best response for small games.

**New test fixtures:**

- `matrix_game_root()`: One-step matrix game for lock tests.
- `one_player_choice_root()`: One-player choice for profile tests.
- `two_player_profile_game_root()`: 2x2 matrix game for profile adaptation tests.

## 8. Explicit boundaries

### 8.1 Implemented in Phase 3

- Exact full-distribution locks keyed by `InfoKey`.
- Strict probability validation (finite, non-negative, unit sum, complete action set).
- Regret updates skipped for locked keys; strategy sums accumulated normally.
- Seat-wide action-incentive profiles (check, call, fold, aggressive).
- Shaped terminal utilities via exact bonus accumulation.
- Separate actual EV and shaped EV reporting.
- Deterministic configuration fingerprinting and provenance tracking.
- JSON/CLI contracts with schema versioning and error codes.
- Exact matrix/toy-game tests with analytical oracles.
- Lock precedence over profiles at the same information set.

### 8.2 Documented future work

- Partial locks (probability bounds, relative shifts).
- Hand-specific locks (locking subsets of an information set).
- Warm-start regret remapping after tree edits.
- Live mutation of an in-progress solver.
- Street/node/size-dependent profile coefficients.
- Learned or state-dependent behavioral models.
- Forward-looking opponent modeling.
- Named population profiles beyond sourced demonstrations.
- MinES/MaxES guarantees or proprietary GTO Wizard behavior.

### 8.3 Explicit non-goals

- Claiming Nash equilibrium of the original game when locks or profiles are active.
- Claiming optimality beyond CFR convergence properties.
- Inventing named profiles (Fish, Nit, TAG, LAG) without public sources.
- Reusing trained state after configuration changes without validation.
- Silently dropping locks after tree edits.
- Reporting shaped EV as actual EV.

## 9. Tractability and honest boundary

Map lookup for locks and profile coefficients is constant-time per visited information set/action. The asymptotic traversal remains dominated by the game tree. Validation requires a finite traversal comparable to `collect_infosets`.

**Implemented target:** Deterministic pre-build configuration, fresh-solver invalidation after edits, multiple full-distribution information-set locks, seat-wide action-incentive profiles, separate shaped training objective and actual EV, deterministic serialization, and exact toy-game cross-checkers.

**Documented boundary:** Live mutation, safe regret warm starts, partial/hand-specific/frequency-bound locks, claiming MinES/MaxES or proprietary behavior, named population profiles beyond sourced demonstrations, forward-looking/learned/state-dependent models.

## 10. Independent algorithm reference

- Zinkevich et al., "Regret Minimization in Games with Incomplete Information," NIPS 2007: https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html

The CFR paper supports regret-minimization foundations. It does not validate GTO Wizard's private profile or locking implementation. The design above is an independent bounded implementation grounded in the repository's existing `InfoKey`-based architecture and validated against exact toy-game oracles.
