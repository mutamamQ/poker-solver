# Tree editing, nodelocks, and player profiles: Phase 3 design

## 1. Scope and correctness claim

This design defines the Phase 3 tree-editing, exact nodelock, and player-profile API for the poker-solver repository. It preserves the existing immutable `GameState` protocol, `CFRSolver` architecture, and `collect_infosets` consistency enforcement. Tree editing rebuilds games from modified action-generation configuration; nodelocks constrain CFR traversal at specified information sets; profiles shape terminal utilities through action-category incentives. All features operate on deterministic public selectors and `InfoKey` identities, never mutable UUID nodes.

**Implemented target:**

- Deterministic pre-build tree edits (add/remove/replace actions at public selectors)
- Fresh-solver invalidation after structural changes
- Multiple full-distribution information-set locks
- Seat-wide action-incentive profiles (check, call, fold, aggressive)
- Separate shaped training objective and actual EV reporting
- Deterministic serialization and exact toy-game cross-checkers

**Documented boundary:**

- Live mutation of an in-progress solver
- Safe regret warm starts after edits
- Partial/hand-specific/frequency-bound locks
- Claiming MinES/MaxES or proprietary GTO Wizard behavior
- Named population profiles beyond explicitly sourced demonstrations
- Forward-looking, learned, street/node/size-dependent behavioral models

## 2. Public selector identity

A **selector** is a deterministic public-history identifier used to target tree edits before game construction. It contains only public state:

```python
@dataclass(frozen=True)
class PublicSelector:
    version: str  # "selector-v1"
    street: Street | None  # "flop", "turn", "river", or None for any
    board: tuple[int, ...] | None  # exact board or None for any
    public_history: tuple[Action, ...]  # public actions only, no DEAL
    acting_player: int  # 0 or 1
    pot: int | None  # pot before action, or None for any
    committed: tuple[int, int] | None  # current-street commitments, or None
    remaining: tuple[int, int] | None  # remaining stacks, or None
```

A selector resolves to zero or more decision nodes during game traversal. Validation requires:

1. At least one reachable decision matches the selector.
2. All resolved occurrences belong to the same `InfoKey` (same owner, same ordered legal actions).
3. The selector does not include private cards when the edit is intended to apply across an information set.

**Wildcard semantics:** `None` fields match any value. A selector with `street=None, board=None, pot=None, committed=None, remaining=None` matches every occurrence of the given `public_history` and `acting_player` regardless of dynamic state.

**Canonical form:** Selectors are serialized in deterministic JSON order. Two selectors are equal if and only if their canonical JSON representations are byte-identical.

## 3. Tree editing

### 3.1 Semantics

Tree editing modifies the action-generation configuration for a deterministic public selector, then constructs a fresh root state and fresh solver. Supported edits:

- **Replace:** set the complete legal sizing set at a selector (replaces all previous actions).
- **Add:** insert an exact legal action into the existing set.
- **Remove:** delete an exact action, leaving at least one legal action.

**Change** is implemented as remove-old plus add-new, followed by full validation and rebuild.

### 3.2 Action identity

Actions are identified by `Action(kind, amount)` tuple identity. Monetary actions use integer total-to amounts (raise-to semantics from `multistreet.py`). Legality rules follow the existing game-structure contract:

- `kind` in `{"CHECK", "CALL", "FOLD", "RAISE"}`
- `amount` is the actor's new total commitment on the current street
- Minimum raise, pot-limit cap, stack bounds, and short all-in rules apply

### 3.3 Validation

Before accepting an edit:

1. The selector resolves to at least one reachable decision.
2. All resolved occurrences have the same `InfoKey`.
3. Generated occurrences with the same `InfoKey` retain identical ordered action tuples (perfect-recall consistency).
4. Action kinds and amounts are legal at every resolved occurrence.
5. No duplicate `Action` values exist.
6. At least one action remains after removal.
7. A child can be generated for each action without violating stack, contribution, street, terminal, or perfect-recall invariants.
8. Every existing nodelock targeting changed action tuples is rejected or explicitly remapped—never silently dropped.

The rebuilt root is passed through `collect_infosets`; its consistency check is an acceptance gate. Validation failure leaves the prior configuration and solution untouched (atomic edit).

### 3.4 Training-state rule

Phase 3 invalidates all solver state after any structural edit:

- Regrets, strategy sums, iteration count, and convergence claims are discarded.
- Warm-start remapping is a documented future optimization.
- Even an unchanged action label may lead to changed continuation payoffs.

Tree editing is atomic: validation builds a candidate root; failure leaves the prior configuration and solution untouched.

### 3.5 API schema

```python
class TreeEditRequest:
    selector: PublicSelector
    operation: Literal["replace", "add", "remove"]
    actions: list[Action]  # complete set for replace, single action for add/remove

class TreeEditResponse:
    success: bool
    error: str | None
    affected_infosets: list[InfoKey]
    invalidated_locks: list[InfoKey]
    new_root_fingerprint: str
```

**CLI schema:**

```bash
poker-solver edit-tree CONFIG.json \
  --selector SELECTOR.json \
  --operation replace \
  --actions '[{"kind":"RAISE","amount":50},{"kind":"RAISE","amount":100}]' \
  --output EDITED_CONFIG.json
```

### 3.6 Tests

Strictly reject:

- Selectors resolving to no target or heterogeneous legal decisions.
- Edits that create illegal/empty/inconsistent action sets.
- Removal of the last legal action.
- Edits that violate perfect-recall (same `InfoKey`, different action tuples).
- Stale lock keys after an edit (must be explicitly remapped or removed).

Acceptance oracle:

- A replace edit followed by `collect_infosets` produces the exact declared action tuple at every resolved occurrence.
- An add edit inserts the action in canonical increasing-target order.
- A remove edit deletes the action and leaves the remaining set in canonical order.
- Editing a game with active locks fails unless locks are explicitly updated.

## 4. Exact nodelocks

### 4.1 Data contract

An exact lock maps one `InfoKey` to a complete probability distribution over that information set's legal actions:

```python
locks: dict[InfoKey, dict[Action, float]]
```

Validation requires:

- The key exists and has the declared owner.
- Keys in the distribution equal the complete legal action set.
- Every probability is finite and in `[0, 1]`.
- Probabilities sum to one within a documented numerical tolerance (default `1e-9`).
- Impossible or unreachable keys are rejected during setup rather than ignored.

Phase 3 supports multiple exact locks. It does not support:

- Private-hand subsets (lock applies to entire `InfoKey`, not individual histories)
- Bounds or relative-frequency shifts
- Partial residual optimization

### 4.2 CFR semantics

At a locked information set:

1. Every traversal uses the fixed distribution instead of regret matching.
2. Regret updates for the locked owner at that information set are skipped.
3. Strategy sums still accumulate the locked distribution with the same owner-reach weighting as unlocked information sets.
4. Exported average strategy reports the constraint exactly.

All other information sets update normally. Chance and reach arithmetic remain identical to the existing synchronous solver.

**Equilibrium interpretation:** A lock constrains the modeled game. The resulting strategy is an equilibrium/no-regret solution of that constrained game to the extent supported by the underlying solver and iteration budget. "Minimally exploitative" and "maximally exploitative" are not API guarantees. If the opponent is fully fixed, the unrestricted player should converge toward a best response; if only some opponent information sets are fixed, unfixed information sets continue adapting.

Actual EV is computed with the existing `expected_values` traversal over the exported profile. Lock adherence is checked independently at every locked key.

### 4.3 Implementation

```python
class CFRSolverWithLocks(CFRSolver):
    def __init__(self, root: GameState, locks: dict[InfoKey, dict[Action, float]]):
        super().__init__(root)
        self.locks = self._validate_locks(locks)
    
    def current_strategy(self) -> dict[InfoKey, dict[Action, float]]:
        result = {}
        for key, data in self.infosets.items():
            if key in self.locks:
                result[key] = self.locks[key]
            else:
                result[key] = regret_matching(data.regrets, data.actions)
        return result
    
    def _walk(self, state, updating, p0, p1, pc, profile, deltas, owner_reaches):
        # ... existing traversal logic ...
        if player == updating and key not in self.locks:
            # Only update regrets for unlocked information sets
            counterfactual_reach = (p1 if player == 0 else p0) * pc
            for action in actions:
                deltas[key][action] += counterfactual_reach * (action_values[action] - node_value)
        # Strategy sums accumulate for all information sets, locked or not
        return node_value
```

### 4.4 Exact oracle

Use a one-step zero-sum matrix game represented as imperfect information:

```text
P0 chooses A or B.
P1 then chooses X or Y without observing P0.
P0 payoff:
        X   Y
A       2  -1
B       0   1
```

**Test cases:**

1. Lock P1 to `X:1, Y:0`. P0's unique best response is `A:1`. Expected P0 value: `2`.
2. Lock P1 to `Y:1`. P0's unique best response is `B:1`. Expected P0 value: `1`.
3. Lock P1 to `X:0.5, Y:0.5`. P0's best response is `A:1`. Expected P0 value: `0.5`.
4. No lock: cross-check against existing best-response/exploitability code.

Additional tests:

- Exact exported locked frequencies match input distribution within `1e-12`.
- Unchanged locks over repeated training calls.
- Malformed-distribution rejection (negative, NaN, non-unit sum).
- Tree-edit invalidation (lock on removed action fails).

### 4.5 API schema

```python
class NodelockRequest:
    locks: dict[str, dict[str, float]]  # JSON-serialized InfoKey -> Action -> probability

class NodelockResponse:
    success: bool
    error: str | None
    validated_locks: dict[InfoKey, dict[Action, float]]
```

**CLI schema:**

```bash
poker-solver solve-spot CONFIG.json \
  --iterations 10000 \
  --locks LOCKS.json \
  --output SOLUTION.json
```

## 5. Player profiles through action incentives

### 5.1 Contract

A profile assigns a seat a finite incentive coefficient for each supported action category:

```python
class ProfileConfig:
    seat: int  # 0 or 1
    coefficients: dict[str, Decimal]  # {"check": 0, "call": 0.03, "fold": -0.06, "aggressive": 0.06}
```

Supported categories:

- `check`: CHECK actions
- `call`: CALL actions
- `fold`: FOLD actions
- `aggressive`: RAISE actions (bet and raise)

Unknown action kinds fail validation. Coefficients are explicit inputs; Phase 3 does not invent named Fish/Nit/TAG/LAG presets. A documented `maniac_demo` may reproduce the public `aggressive +0.06`, `call +0.03`, `fold -0.06` example, clearly labeled as a product-derived demonstration rather than a calibrated population model.

At a decision with reference pot `P`, choosing category `c` contributes virtual reward:

```python
bonus = coefficient[c] * P
```

The reference pot is the matched pot before the action and excludes uncalled excess. Coefficients use an exact decimal/rational input at the API boundary and convert to solver numeric type deliberately.

### 5.2 Shaped-game solution

Profiles define a shaped behavioral game. A player's shaped terminal utility is:

```python
actual_terminal_utility + sum(profile_bonuses_on_that_player_path)
```

The solver trains against shaped utilities. Implementing this correctly requires carrying accumulated per-player bonuses through traversal or an equivalent exact transformation. For the existing two-player solver, the implementation must keep separate value channels or expose a utility wrapper that returns each player's shaped payoff. It must not rely on `-child_value` shortcuts.

After training, reported poker EV is always recomputed from the final strategy using original, unshaped terminal returns. Reports must expose both:

- `actual_ev`: real chip/money utility
- `shaped_ev`: optional diagnostic, clearly labeled virtual

The virtual bonuses never enter pots, stacks, rake, ICM prizes, or conservation checks.

### 5.3 Scope

Initial support is seat-wide across the solved tree. Street-specific, node-specific, private-hand-specific, learned, state-dependent, and bet-size-dependent incentives are documented boundaries.

Exact nodelocks take precedence over profile optimization at the same information set: locked policy is used unchanged, while path bonuses may still be accumulated for diagnostic shaped value. This precedence must be explicit in serialized configuration.

### 5.4 Profile oracle

Use a one-player choice with actual payoffs `check=0`, `call=-1`. With reference pot 10:

- No profile: unique choice is check (EV = 0).
- Call coefficient `0.2`: shaped call payoff is `-1 + 0.2*10 = 1`, so the unique shaped choice is call.
- Exported actual EV under the call policy is `-1`, while shaped EV is `1`.

This fixture proves strategy shaping and EV separation without relying on qualitative poker frequencies. A second two-player matrix fixture verifies that the unprofiled opponent adapts to the profile-shaped policy and that exhaustive enumeration agrees with the bounded solver.

### 5.5 Implementation

```python
class CFRSolverWithProfiles(CFRSolver):
    def __init__(self, root: GameState, profiles: dict[int, ProfileConfig]):
        super().__init__(root)
        self.profiles = profiles
    
    def _walk(self, state, updating, p0, p1, pc, profile, deltas, owner_reaches, bonuses):
        # bonuses: dict[int, float] = accumulated per-player bonuses on current path
        player = state.current_player()
        if player == TERMINAL:
            u0, u1 = state.returns()
            return (u0 + bonuses[0], u1 + bonuses[1])[updating]
        
        # ... existing chance/player logic ...
        
        if player in (0, 1):
            pot = self._compute_reference_pot(state)
            for action in actions:
                new_bonuses = bonuses.copy()
                if player in self.profiles:
                    category = self._action_category(action)
                    new_bonuses[player] += self.profiles[player].coefficients[category] * pot
                action_values[action] = self._walk(
                    state.child(action), updating, 
                    p0 * policy[action] if player == 0 else p0,
                    p1 * policy[action] if player == 1 else p1,
                    pc, profile, deltas, owner_reaches, new_bonuses
                )
        # ... rest of traversal ...
    
    def actual_values(self) -> tuple[float, float]:
        # Recompute with zero bonuses
        return expected_values(self.root, self.average_strategy())
    
    def shaped_values(self) -> tuple[float, float]:
        # Compute with profile bonuses
        return self._walk(self.root, 0, 1.0, 1.0, 1.0, self.average_strategy(), {}, {}, {0: 0.0, 1: 0.0})
```

### 5.6 API schema

```python
class ProfileRequest:
    profiles: dict[int, ProfileConfig]

class ProfileResponse:
    success: bool
    error: str | None
    actual_ev: tuple[float, float]
    shaped_ev: tuple[float, float]
```

**CLI schema:**

```bash
poker-solver solve-spot CONFIG.json \
  --iterations 10000 \
  --profile-0 '{"check":0,"call":0.03,"fold":-0.06,"aggressive":0.06}' \
  --output SOLUTION.json
```

## 6. Serialization and API behavior

A saved configuration includes:

- Schema version (`tree-edit-v1`, `nodelock-v1`, `profile-v1`)
- Deterministic selectors (canonical JSON order)
- Exact actions (kind, amount tuples)
- Exact locks (InfoKey -> Action -> probability)
- Profile coefficients (seat -> category -> Decimal)
- Precedence (locks override profiles at the same information set)

Serialization order is canonical. Loading validates against a freshly built game; stale keys/actions produce a structured error.

Solution metadata records:

- Game/configuration fingerprint (SHA-256 of canonical config JSON)
- Structural edit set (list of applied selectors and operations)
- Active locks and profiles (full specification)
- Iteration count and solver mode (`vanilla-cfr`, `external-sampling-mccfr`)
- Whether values are actual or shaped

A solution fingerprint mismatch prevents applying old strategies, locks, or convergence metadata to an edited game.

## 7. Failure tests

Strictly reject:

- Selectors resolving to no target or heterogeneous legal decisions.
- Edits that create illegal/empty/inconsistent action sets.
- A lock on a physical private-history occurrence instead of a valid `InfoKey`.
- Missing/extra actions, NaN/infinite/negative probabilities, or non-unit lock sums.
- Stale lock keys after an edit.
- NaN/infinite profile coefficients or unsupported action categories.
- Attempts to report shaped value as actual EV.
- Attempts to reuse trained state after structural edits.

## 8. Tractability and honest boundary

Map lookup for locks and profile coefficients is constant-time per visited information set/action. The asymptotic traversal remains dominated by the game tree. Validation requires a finite traversal comparable to `collect_infosets`; rebuilding and re-solving are intentionally required after edits.

## 9. Independent algorithm reference

- Zinkevich et al., "Regret Minimization in Games with Incomplete Information" (NeurIPS 2007): https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html

The CFR paper supports regret-minimization foundations. It does not validate GTO Wizard's private profile or locking implementation.

## 10. Acceptance gates

All comparisons use `abs(actual - expected) <= 1e-12` unless a test explicitly documents a looser iterative convergence tolerance.

1. **Tree edit identity:** A replace edit followed by `collect_infosets` produces the exact declared action tuple at every resolved occurrence.
2. **Lock oracle:** The one-step matrix game with locked P1 produces P0 best-response values within `1e-12` of the analytical expectation.
3. **Profile oracle:** The one-player choice fixture produces shaped strategy and actual/shaped EV separation within `1e-12`.
4. **Lock adherence:** Exported average strategy at locked information sets matches the input distribution within `1e-12`.
5. **Edit invalidation:** Attempting to solve with stale locks after a tree edit fails with a structured error.
6. **Zero-sum preservation:** Actual EV (not shaped EV) sums to zero within `1e-9` for all two-player zero-sum games.
7. **Deterministic serialization:** Canonical JSON for configs, locks, and profiles is byte-identical across repeated serialization.
8. **Malformed rejection:** All documented failure cases produce exit status 2 and structured error messages.

## 11. Module ownership and integration

Phase 3 adds:

- `src/poker_solver/tree_edit.py`: selector resolution, edit validation, config rebuilding
- `src/poker_solver/nodelock.py`: lock validation, CFRSolverWithLocks
- `src/poker_solver/profile.py`: profile validation, CFRSolverWithProfiles, bonus accumulation
- `tests/test_tree_edit.py`: selector resolution, edit validation, atomic failure
- `tests/test_nodelock.py`: matrix oracle, lock adherence, malformed rejection
- `tests/test_profile.py`: one-player oracle, two-player adaptation, EV separation

No existing module is modified except:

- `cli.py`: add `edit-tree`, `--locks`, `--profile-0`, `--profile-1` flags
- `api.py`: add `TreeEditRequest`, `NodelockRequest`, `ProfileRequest` schemas

All Phase 1 and Phase 2 tests remain green. The orchestrator resolves integration conflicts.
