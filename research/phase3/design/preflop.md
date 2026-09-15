# Phase 3 Heads-Up Preflop Subsystem Design

## 1. Executive summary

This design specifies the Phase 3 heads-up preflop subsystem and its integration contract. It addresses blind/ante accounting, HU action order, raise-tree representation, continuation semantics, and exact test oracles. All current APIs (`model.py`, `multistreet.py`, `equity.py`, `cards.py`) are preserved. The design is implementable, self-consistent, and explicitly bounded.

## 2. Public types and interfaces

### 2.1 Core state representation

```python
@dataclass(frozen=True, slots=True)
class PreflopConfig:
    """Immutable heads-up preflop configuration."""
    version: str  # "holdem-preflop-hu-v1"
    button_stack: int  # BTN starting stack before postings
    bb_stack: int      # BB starting stack before postings
    small_blind: int
    big_blind: int
    ante_mode: AnteMode
    ante_amount: int
    player0_range: tuple[WeightedCombo, ...]  # BTN range
    player1_range: tuple[WeightedCombo, ...]  # BB range
    sizing_spec: SizingSpec
    continuation_mode: ContinuationMode
    structural_limits: StructuralLimits

@dataclass(frozen=True, slots=True)
class AnteMode:
    kind: Literal["none", "per_player", "total", "bb_ante", "explicit"]
    # For "explicit": (BTN_ante, BB_ante)
    explicit_postings: tuple[int, int] | None = None

@dataclass(frozen=True, slots=True)
class ContinuationMode:
    kind: Literal["all_in_runout", "table", "checkdown_equity"]
    # For "all_in_runout": explicit legal boards or None for complete enumeration
    allowed_boards: tuple[tuple[int, ...], ...] | None = None
    # For "table": mapping from (deal_index, closing_history) to (u0, u1)
    payoff_table: dict[tuple[int, tuple[Action, ...]], tuple[float, float]] | None = None
    # Provenance required for table mode
    table_provenance: str | None = None

@dataclass(frozen=True, slots=True)
class StructuralLimits:
    max_deal_pairs: int = 10_000
    max_tree_nodes: int = 100_000
    max_runout_boards: int = 1_000

@dataclass(frozen=True, slots=True)
class PreflopState:
    """Immutable snapshot of preflop game state."""
    config: PreflopConfig
    private_deal: tuple[tuple[int, int], tuple[int, int]] | None
    acting_player: int  # CHANCE, TERMINAL, 0 (BTN), or 1 (BB)
    pot: int  # Accumulated pot from forced postings
    committed: tuple[int, int]  # Current-round commitments
    total_contributed: tuple[int, int]  # Total from start
    remaining: tuple[int, int]  # Remaining stacks
    highest_commitment: int
    last_raise_increment: int
    both_acted_since_last_raise: tuple[bool, bool]
    history: tuple[Action, ...]  # Complete public history
    terminal_reason: str | None
```

### 2.2 Integration with existing model.py

`PreflopState` implements the `GameState` protocol:

- `current_player() -> int`: returns `acting_player`
- `legal_actions() -> tuple[Action, ...]`: generates FOLD/CALL/RAISE per betting state
- `chance_outcomes() -> tuple[tuple[Action, float], ...]`: at root, enumerates compatible deal pairs with normalized blocker-aware mass
- `child(action: Action) -> PreflopState`: immutable transition
- `information_state_key(player: int) -> InfoKey`: `(version, player, sorted_own_cards, forced_postings, pot, committed, remaining, highest_commitment, last_raise_increment, public_history, sizing_identity, continuation_identity)`
- `returns() -> tuple[float, float]`: terminal payoff relative to pre-posting wealth baseline

### 2.3 Sizing integration

Sizing specification uses the contract from `research/phase3/bet-sizing.md`:

```python
@dataclass(frozen=True, slots=True)
class SizingSpec:
    mode: Literal["fixed", "dynamic", "automatic"]
    # Fixed: explicit size expressions
    fixed_sizes: tuple[SizeExpression, ...] | None = None
    # Dynamic: candidate list + retained count
    dynamic_candidates: tuple[SizeExpression, ...] | None = None
    dynamic_retain_count: int | None = None
    dynamic_selecting_player: int | None = None  # 0 or 1
    dynamic_tie_tolerance: float = 1e-12
    # Automatic: grid + EV tolerance
    automatic_max_sizes: int | None = None
    automatic_ev_tolerance: float | None = None
    automatic_selecting_player: int | None = None

@dataclass(frozen=True, slots=True)
class SizeExpression:
    unit: Literal["pot_percent", "geometric", "previous_bet_multiple", "big_blinds", "all_in"]
    value: float | None = None  # For pot_percent, previous_bet_multiple, big_blinds
    streets: int | None = None  # For geometric
    scale: float | None = None  # For geometric
```

Conversion to `Action.amount` (integer raise-to) uses the exact formulas from `bet-sizing.md`. The sizing module is called during `legal_actions()` generation. Generated actions are validated against stack, minimum raise, and pot-limit constraints.

### 2.4 Factory and root creation

```python
def create_preflop_root(config: PreflopConfig) -> PreflopState:
    """Create root chance node with forced postings applied."""
    # Validate config
    # Compute forced postings
    # Return root CHANCE state with pot = sum(postings), remaining = stacks - postings
```

## 3. Forced-post and payoff invariants

### 3.1 Forced posting ledger

At root creation:

1. **Blind postings**: BTN posts `min(small_blind, button_stack)`, BB posts `min(big_blind, bb_stack)`.
2. **Ante postings** (applied after blinds):
   - `none`: no ante
   - `per_player`: each posts `min(ante_amount, remaining_after_blind)`
   - `total`: total ante `ante_amount` must be even; each posts `ante_amount // 2` capped by remaining stack
   - `bb_ante`: BB posts additional `min(ante_amount, remaining_after_blind)`
   - `explicit`: BTN posts `explicit_postings[0]`, BB posts `explicit_postings[1]`, each capped by remaining stack
3. **Initial pot**: `pot = btn_blind + bb_blind + btn_ante + bb_ante`
4. **Remaining stacks**: `remaining[i] = starting_stack[i] - blind[i] - ante[i]`
5. **Initial commitments**: `committed = (btn_blind + btn_ante, bb_blind + bb_ante)` for the preflop round
6. **Total contributions**: `total_contributed = committed` at root

**Invariant 1 (Conservation)**: At every state,
```
sum(remaining) + sum(committed) + pot == button_stack + bb_stack
```

**Invariant 2 (No double counting)**: Forced postings appear exactly once in `pot` and `total_contributed`. They are never added again as "dead money."

### 3.2 Heads-up action order

**At root after forced postings**:
- BTN has posted `small_blind` (+ optional ante)
- BB has posted `big_blind` (+ optional ante)
- `highest_commitment = max(committed)` (initially BB's total posting)
- `last_raise_increment = big_blind` (BB's blind establishes the initial raise increment)
- **BTN acts first** if able to act

**Postflop** (if preflop transitions to postflop): BB acts first. This is recorded in continuation metadata even when postflop streets are not expanded.

### 3.3 Payoff baseline

Payoff is measured relative to each player's wealth **before forced postings**.

At a terminal:
```python
contested = pot + sum(committed)
award[winner] = contested  # or split for ties
award[loser] = 0
u[i] = award[i] - total_contributed[i]
```

For fold:
```python
winner = 1 - folder
award = (contested, 0) if winner == 0 else (0, contested)
u[i] = award[i] - total_contributed[i]
```

For all-in runout:
```python
# Enumerate legal boards, evaluate showdowns, average by exact probability
# Odd-chip policy: first odd chip to BTN (configurable)
```

For table continuation:
```python
# Look up (deal_index, closing_history) in payoff_table
# Validate sum(u0, u1) == 0 within 1e-12 (or -rake if composed)
```

For checkdown approximation:
```python
# Enumerate boards, evaluate showdowns, average
# Output metadata: approximation=true, continuation_model="checkdown_equity"
```

**Invariant 3 (Zero-sum)**: `u[0] + u[1] == 0` within `1e-12` for no-rake games.

**Invariant 4 (Unmatched refund)**: Heads-up unmatched excess is returned before terminal evaluation. If one player is all-in and the other has more committed, refund the excess:
```python
if committed[0] != committed[1]:
    excess = abs(committed[0] - committed[1])
    refund_to = 0 if committed[0] > committed[1] else 1
    committed[refund_to] -= excess
    remaining[refund_to] += excess
    total_contributed[refund_to] -= excess
```

## 4. Raise-tree representation and action generation

### 4.1 Betting state

At a decision node:

- `to_call = highest_commitment - committed[acting_player]`
- `call_target = min(highest_commitment, committed[acting_player] + remaining[acting_player])`

### 4.2 Legal actions

**Facing a wager** (`to_call > 0`):
1. `FOLD`
2. `CALL(call_target)` if `call_target > committed[acting_player]`
3. For each legal raise-to target `T` from sizing spec:
   - `additional = T - committed[acting_player]`
   - Skip if `additional > remaining[acting_player]`
   - `min_raise = highest_commitment + last_raise_increment`
   - Skip if `T < min_raise` unless `T == committed[acting_player] + remaining[acting_player]` (exact all-in)
   - Emit `RAISE(T)`

**Not facing a wager** (`to_call == 0`):
1. `CHECK` (or `FOLD` if BTN at root and wants to fold immediately)
2. For each legal raise-to target `T`:
   - Same validation as above
   - Emit `RAISE(T)` (or `BET(T)` for display; internally `Action("RAISE", T)`)

### 4.3 Action closing and reopening

Preflop closes when:
- Both players have acted since the last full raise, AND
- `committed[0] == committed[1]`, AND
- Both players are live (not folded, not all-in)

OR one player folds.

OR both players are all-in with matched commitments.

A full raise increases `highest_commitment` by at least `last_raise_increment` and sets `both_acted_since_last_raise = (False, False)`. A short all-in that increases `highest_commitment` but by less than `last_raise_increment` does NOT reopen action for a player who already acted (standard no-limit rule).

### 4.4 Sizing mode integration

**Fixed**: Convert all `fixed_sizes` to integer targets, validate, deduplicate, emit as actions.

**Dynamic**: 
1. Enumerate all subsets of `dynamic_candidates` of size `dynamic_retain_count`
2. For each subset, build a fresh `PreflopState` tree with only those sizes, solve with the configured algorithm/iterations
3. Measure `dynamic_selecting_player`'s root EV
4. Choose max EV subset; ties broken by lexicographically smallest integer targets
5. Return selected subset as legal actions

**Automatic**:
1. Generate candidate grid (e.g., `[0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]` pot-percent, `2.5bb`, `3bb`, `all-in`)
2. Solve full-candidate tree → `V_full`
3. Enumerate subsets of size 1 through `automatic_max_sizes`
4. Choose smallest subset where selecting player's EV ≥ `V_full - automatic_ev_tolerance`
5. Among equal-size qualifying subsets, maximize EV

**Note**: Dynamic and Automatic require solving multiple trees. This is exponential in candidate count and limited by `StructuralLimits`. For large candidate sets, reject at validation.

## 5. Bounded continuation semantics

### 5.1 All-in runout

**Trigger**: Preflop closes with both players all-in (matched commitments, zero remaining stacks).

**Procedure**:
1. If `allowed_boards` is specified, enumerate only those boards
2. Otherwise, enumerate all `C(48, 5)` legal five-card boards (no collision with private deals)
3. For each board, evaluate both seven-card hands with `evaluator.evaluate_seven`
4. Determine winner/tie, apply odd-chip policy
5. Average terminal returns by exact uniform probability over legal boards

**Output metadata**: `continuation_model: "all_in_runout"`, `exact: true`

### 5.2 Table continuation

**Trigger**: Preflop closes with non-all-in commitments (at least one player has chips remaining).

**Procedure**:
1. Identify `(deal_index, closing_history)` where `deal_index` is the integer index from root chance enumeration
2. Look up `payoff_table[(deal_index, closing_history)]`
3. If missing, fail with status 2
4. Validate `u[0] + u[1] == 0` within `1e-12`
5. Return `(u[0], u[1])`

**Output metadata**: `continuation_model: "table"`, `provenance: <table_provenance>`, `exact_for_declared_game: true`

**Requirement**: Caller must supply payoffs for every reachable non-all-in closing leaf. Incomplete tables are rejected.

### 5.3 Checkdown equity

**Trigger**: Preflop closes with non-all-in commitments, no table provided.

**Procedure**:
1. Enumerate all legal five-card boards
2. Evaluate showdowns with no further betting
3. Average terminal returns

**Output metadata**: `continuation_model: "checkdown_equity"`, `approximation: true`, `warning: "No postflop betting modeled"`

**Restriction**: Output must never claim GTO Wizard parity or unrestricted-game Nash equilibrium. This is a working approximation for bounded testing.

### 5.4 Validation

A `PreflopConfig` with non-all-in closing paths and `continuation_mode.kind` not in `{"table", "checkdown_equity"}` fails validation with a clear error: "Non-all-in preflop requires explicit continuation model."

## 6. Dependency order and module boundaries

### 6.1 New modules

**`src/poker_solver/preflop.py`**: Implements `PreflopConfig`, `PreflopState`, `create_preflop_root`. Depends on:
- `model.py` (Action, GameState protocol, CHANCE, TERMINAL)
- `cards.py` (validate_unique, FULL_DECK)
- `equity.py` (WeightedCombo)
- `evaluator.py` (evaluate_seven)
- `sizing.py` (new module, see below)

**`src/poker_solver/sizing.py`**: Implements `SizingSpec`, `SizeExpression`, conversion functions, Fixed/Dynamic/Automatic logic. Depends on:
- `model.py` (Action)
- Standard library (decimal, itertools)

Does NOT depend on `preflop.py` or `multistreet.py` directly. Sizing conversion is a pure function: `convert_size(expr: SizeExpression, context: SizingContext) -> int`.

**`tests/test_preflop.py`**: Comprehensive test suite for preflop module.

**`tests/test_sizing.py`**: Comprehensive test suite for sizing module.

### 6.2 Preserved APIs

**No changes to**:
- `model.py` (Action, GameState protocol, CHANCE, TERMINAL, other_player)
- `cards.py` (parse_card, format_card, validate_unique, RANKS, SUITS, FULL_DECK)
- `equity.py` (WeightedCombo, exact_equity, range_equity, EquityResult)
- `evaluator.py` (evaluate_five, evaluate_seven)
- `multistreet.py` (MultiStreetConfig, MultiStreetState, create_root)
- `cfr.py` (CFRSolver)
- `mccfr.py` (MCCFRSolver)
- `best_response.py` (expected_values, nash_conv, NashConvResult)
- `api.py` (SolveResult, ExploitabilityResult, existing solve/exploitability functions)
- `cli.py` (existing subcommands)

**Extension points**:
- `api.py`: Add `solve_preflop(config: PreflopConfig, algorithm, iterations, seed) -> SolveResult`
- `api.py`: Add `exploitability_preflop(config: PreflopConfig, strategy: Strategy) -> ExploitabilityResult`
- `cli.py`: Add `solve-preflop CONFIG.json --iterations N [--seed S] [--json]`

### 6.3 Dependency graph

```
model.py  <--- kuhn.py
  ^            river.py <--- evaluator.py
  |            multistreet.py <--- evaluator.py, equity.py, cards.py
  |            preflop.py <--- evaluator.py, equity.py, cards.py, sizing.py
  |                 ^
  |                 |
  +--- sizing.py ---+
  |
  +--- cfr.py, mccfr.py, best_response.py
  |
  +--- audit.py
  |
  +--- api.py <--- cfr.py, mccfr.py, best_response.py, kuhn.py, river.py, multistreet.py, preflop.py
  |
  +--- cli.py <--- api.py
```

All solver code depends only on the generic `GameState` protocol. `preflop.py` does not import `multistreet.py` or vice versa.

## 7. Exact tests, oracles, and tolerances

### 7.1 Forced posting and action order

**Test 1: Basic HU setup**
- Stacks: `(2500, 2500)`, SB 50, BB 100, no ante
- Expected root: `pot=150`, `remaining=(2450, 2400)`, `committed=(50, 100)`, `highest_commitment=100`, `last_raise_increment=100`, BTN acts first
- Oracle: hand calculation
- Tolerance: exact integer equality

**Test 2: Per-player ante**
- Stacks: `(2500, 2500)`, SB 50, BB 100, per-player ante 10
- Expected: `pot=170`, `remaining=(2440, 2390)`, `committed=(60, 110)`
- Oracle: hand calculation
- Tolerance: exact

**Test 3: Total ante**
- Stacks: `(2500, 2500)`, SB 50, BB 100, total ante 20
- Expected: `pot=170`, `remaining=(2440, 2390)`, `committed=(60, 110)`
- Oracle: hand calculation
- Tolerance: exact

**Test 4: BB ante**
- Stacks: `(2500, 2500)`, SB 50, BB 100, BB ante 20
- Expected: `pot=170`, `remaining=(2450, 2380)`, `committed=(50, 120)`
- Oracle: hand calculation
- Tolerance: exact

**Test 5: Explicit ante**
- Stacks: `(2500, 2500)`, SB 50, BB 100, explicit `(15, 25)`
- Expected: `pot=190`, `remaining=(2435, 2375)`, `committed=(65, 125)`
- Oracle: hand calculation
- Tolerance: exact

### 7.2 Limp, fold, raise sequences

**Test 6: Limp/check**
- BTN calls to 100 (pays 50), BB checks
- Expected: `total_contributed=(100, 100)`, `pot=200` before continuation
- Oracle: hand calculation
- Tolerance: exact

**Test 7: Immediate fold**
- BTN folds immediately
- Expected: awards `(0, 150)`, returns `(-50, +50)`
- Oracle: hand calculation
- Tolerance: exact

**Test 8: Raise increments**
- BTN raises to 300 (increment 200 over BB 100)
- BB's next full raise target ≥ 500
- BB raise to 499 is illegal unless exact all-in
- Oracle: hand calculation
- Tolerance: exact

**Test 9: Unmatched all-in refund**
- Stacks: `(5000, 10000)` after postings
- Both commit 5000
- BB's excess 5000 is refunded before terminal evaluation
- Expected: contested pot = 10000 (5000 from each), BB remaining = 5000
- Oracle: hand calculation
- Tolerance: exact

**Test 10: Conservation**
- At every state: `sum(remaining) + sum(committed) + pot == initial_total`
- At terminal: `sum(returns) == 0` (no rake)
- Oracle: invariant check
- Tolerance: exact for integers, `1e-12` for float returns

### 7.3 Chance enumeration and blockers

**Test 11: Root chance mass**
- Two ranges: BTN `{(As,Kd):1.0}`, BB `{(Qh,Qc):1.0, (Jh,Jc):1.0}`
- Expected: 2 compatible pairs, each probability 0.5
- Oracle: manual enumeration
- Tolerance: `1e-12`

**Test 12: Blocker removal**
- BTN `{(As,Kd):1.0}`, BB `{(As,Ah):1.0, (Kd,Kh):1.0, (Qh,Qc):1.0}`
- Expected: 1 compatible pair `(As,Kd) vs (Qh,Qc)`, probability 1.0
- Oracle: manual enumeration
- Tolerance: `1e-12`

**Test 13: Weighted mass**
- BTN `{(As,Kd):0.5}`, BB `{(Qh,Qc):1.0}`
- Expected: 1 pair, unnormalized mass 0.5, normalized probability 1.0
- Oracle: manual calculation
- Tolerance: `1e-12`

### 7.4 All-in runout

**Test 14: Exact equity**
- BTN `(As,Kd)` vs BB `(Qh,Qc)`, all-in preflop
- Enumerate all `C(48, 5)` boards, evaluate showdowns
- Expected: integer win/tie/loss counts match `equity.exact_equity`
- Oracle: existing `equity.py` module
- Tolerance: exact integer counts

**Test 15: Odd-chip policy**
- Contested pot 201, tie
- Expected: BTN gets 101, BB gets 100 (first odd chip to BTN)
- Oracle: hand calculation
- Tolerance: exact

### 7.5 Table continuation

**Test 16: Tiny table game**
- Two deals, one action each (fold or call), table provides 4 payoffs
- Solve with vanilla CFR, compare root EV with hand-calculated normal-form solution
- Oracle: manual normal-form game solution
- Tolerance: `1e-12` for exact expected-value game

**Test 17: Incomplete table rejection**
- Omit one reachable leaf from table
- Expected: validation fails with status 2
- Oracle: negative test

**Test 18: Zero-sum validation**
- Table entry `(deal, history) -> (1.5, -1.4)`
- Expected: validation fails (sum != 0 within `1e-12`)
- Oracle: negative test

### 7.6 Checkdown approximation

**Test 19: Checkdown identity**
- Generate table by exact checkdown equity for a tiny game
- Solve with table mode and checkdown mode
- Expected: root EVs agree within `1e-12`
- Oracle: cross-mode comparison

**Test 20: Approximation disclosure**
- Checkdown output includes `approximation: true`, `continuation_model: "checkdown_equity"`
- Expected: metadata present
- Oracle: output inspection

### 7.7 Sizing conversion

**Test 21: Pot-percent formula**
- Pot 100, facing bet 50, actor committed 0
- 100% pot raise-to = `0 + 50 + 1.0 * (100 + 50) = 200`
- Oracle: hand calculation per `bet-sizing.md` formula
- Tolerance: exact integer

**Test 22: Big-blinds**
- BB = 100, `2.5bb` = 250
- Oracle: hand calculation
- Tolerance: exact

**Test 23: Geometric**
- Pot 100, stack 200, 2 streets, scale 1.0
- `g = ((1 + 2*200/100)^(1/2) - 1) / 2 = (sqrt(3) - 1) / 2 ≈ 0.366`
- Target ≈ `0 + 0.366 * 100 = 36.6`, rounded to 37
- Oracle: hand calculation with decimal arithmetic
- Tolerance: exact integer after rounding

**Test 24: Deduplication**
- Sizes `[{pot_percent: 75}, {big_blinds: 2.5}]` both resolve to 250
- Expected: one action `RAISE(250)`, provenance = first expression
- Oracle: deduplication rule
- Tolerance: exact

**Test 25: Legality boundaries**
- Min raise accepted, min-1 rejected unless exact all-in
- Exact stack target accepted, stack+1 rejected
- Oracle: boundary tests
- Tolerance: exact

### 7.8 Sizing modes

**Test 26: Fixed invariant**
- Fixed sizes `[0.5, 1.0, 2.0]` pot-percent
- Expected: all three legal targets present in actions
- Oracle: Fixed mode contract
- Tolerance: exact

**Test 27: Dynamic oracle**
- Tiny game, 3 candidates, retain 2
- Enumerate all 3 subsets, solve each, compare EVs
- Expected: selected subset matches max EV
- Oracle: exhaustive enumeration
- Tolerance: `1e-12` for exact games, fixture-specific for iterative CFR

**Test 28: Automatic EV tolerance**
- Full tree EV = 10.0, tolerance 0.5
- Subset with EV 9.6 qualifies, subset with EV 9.4 does not
- Oracle: Automatic mode contract
- Tolerance: `1e-12`

### 7.9 Information noninterference

**Test 29: Hidden hand independence**
- Change only BB's hidden hand
- Expected: BTN's information key and legal actions unchanged
- Oracle: information-set consistency
- Tolerance: exact equality

**Test 30: Public history dependence**
- Change public raise amount
- Expected: information key changes
- Oracle: information-set consistency
- Tolerance: exact inequality

### 7.10 Solver integration

**Test 31: Vanilla CFR convergence**
- Tiny preflop game with table continuation
- Solve with vanilla CFR, 10,000 iterations
- Compare with exhaustive best response
- Expected: NashConv < predeclared threshold (e.g., 0.01)
- Oracle: existing `best_response.py` module
- Tolerance: fixture-specific measured threshold

**Test 32: MCCFR determinism**
- Same seed, same config, same iterations
- Expected: byte-identical JSON output
- Oracle: determinism contract
- Tolerance: exact

**Test 33: Baseline preservation**
- All 185 existing tests remain green
- Oracle: regression suite
- Tolerance: existing thresholds

### 7.11 API and CLI

**Test 34: JSON validation**
- Unknown fields, duplicate keys, bool-as-int, NaN, infinity, invalid cards, negative chips, missing continuation
- Expected: fail with status 2
- Oracle: negative tests

**Test 35: Deterministic output**
- Canonical JSON: sorted keys, deterministic float formatting, stable action order
- Expected: byte-identical output for identical input
- Oracle: determinism contract
- Tolerance: exact

**Test 36: CLI smoke test**
- `poker-solver solve-preflop config.json --iterations 1000 --json`
- Expected: valid JSON, exit 0
- Oracle: CLI contract
- Tolerance: valid JSON schema

## 8. Implemented vs. boundary decisions

### 8.1 Implemented (Tier 1)

| Capability | Disposition |
|------------|-------------|
| HU BTN/BB positions and forced postings | Implement with exact chip ledger |
| Per-player, total, BB, explicit antes | Implement |
| Limp/fold/call/raise/all-in finite tree | Implement |
| Fixed/Dynamic/Automatic sizing | Implement per `bet-sizing.md` contract |
| Pot-percent, geometric, previous-bet-multiple, big-blinds, all-in units | Implement |
| Exact explicit-range all-in runouts | Implement within structural limits |
| Caller-supplied continuation table | Implement; exact for declared finite game |
| Checkdown-equity continuation | Implement and label approximation |
| Vanilla CFR and MCCFR solving | Implement via existing solvers |
| Exact best response and NashConv | Implement via existing `best_response.py` |
| Strict JSON API and CLI | Implement |
| Deterministic output and serialization | Implement |

### 8.2 Documented boundary (Tier 2/3)

| Capability | Disposition |
|------------|-------------|
| Full unrestricted postflop continuation | Documented boundary; requires neural value model |
| GTO Wizard neural preflop parity | Not claimed |
| Arbitrary 1,326-combo × full-board scale | Reject beyond tested limits |
| Ring-game bunching | Not part of HU model |
| Multiway preflop (3+ players) | Phase 3 scope boundary |
| Pot-limit preflop | Not implemented; no-limit only |
| Rake | Deferred to game-structure module |
| ICM/bounties | Phase 3 scope boundary |
| Straddles/limps beyond HU | Phase 3 scope boundary |
| Continuous bet sizing | Documented boundary |
| Large candidate sets (>10) for Dynamic/Automatic | Reject at validation |

### 8.3 Explicit non-goals

- Claiming GTO Wizard algorithm parity without identical machine-readable trees/continuations
- Inventing "known GTO" range percentages or solver-agreement tolerances
- Arbitrary fixed raise-depth limits (limits are explicit input)
- Silent clipping, NaN replacement, or partial results
- Mutable game state or in-place tree editing
- Warm-start regret preservation across structural edits (future optimization)

## 9. Integration checklist

### 9.1 Pre-implementation validation

- [ ] All 185 existing tests pass
- [ ] `model.py`, `cards.py`, `equity.py`, `evaluator.py` APIs unchanged
- [ ] `multistreet.py` APIs unchanged
- [ ] `cfr.py`, `mccfr.py`, `best_response.py` APIs unchanged
- [ ] `api.py`, `cli.py` existing subcommands unchanged

### 9.2 Implementation deliverables

- [ ] `src/poker_solver/sizing.py` with `SizingSpec`, `SizeExpression`, conversion functions
- [ ] `src/poker_solver/preflop.py` with `PreflopConfig`, `PreflopState`, `create_preflop_root`
- [ ] `tests/test_sizing.py` with all sizing formula/mode tests (Tests 21-28)
- [ ] `tests/test_preflop.py` with all preflop tests (Tests 1-20, 29-36)
- [ ] `api.py` extensions: `solve_preflop`, `exploitability_preflop`
- [ ] `cli.py` extension: `solve-preflop` subcommand
- [ ] All 36 acceptance tests passing
- [ ] All 185 baseline tests still passing

### 9.3 Post-implementation validation

- [ ] Adversarial review by non-author subagent under `review/phase3/preflop-adversarial.md`
- [ ] Cross-check: tiny preflop game vs. hand-solved normal form
- [ ] Cross-check: checkdown mode vs. independently generated table
- [ ] Cross-check: all-in equity vs. existing `equity.py` oracle
- [ ] Determinism: same seed → byte-identical JSON
- [ ] Conservation: every state and terminal satisfies invariants
- [ ] Documentation: `ARCHITECTURE.md` updated with preflop module
- [ ] Documentation: `README.md` updated with preflop capabilities and boundaries

## 10. Open questions and resolutions

**Q1: Should preflop support pot-limit mode?**
**A1**: No. Preflop is no-limit by default. Pot-limit is a documented boundary. If needed later, add `betting_mode: Literal["no_limit", "pot_limit"]` to `PreflopConfig` and validate raise caps.

**Q2: Should Dynamic/Automatic sizing be implemented in Phase 3?**
**A2**: Yes, but with strict limits. Dynamic/Automatic require solving multiple trees (exponential in candidate count). Implement for small candidate sets (≤5 for Dynamic, ≤7 for Automatic). Reject larger sets at validation. This demonstrates the feature correctly without claiming unrestricted scalability.

**Q3: How to handle non-all-in preflop without a postflop model?**
**A3**: Three explicit modes: (1) `all_in_runout` for all-in spots (exact), (2) `table` for caller-supplied payoffs (exact for declared game), (3) `checkdown_equity` for testing (approximation, labeled). A config with non-all-in paths and no continuation mode fails validation. This is honest and bounded.

**Q4: Should preflop reuse `multistreet.py` or be a separate module?**
**A4**: Separate module. `multistreet.py` is postflop-focused (flop/turn/river streets, runout chance). Preflop has different structure (forced postings, BTN-first action, no board yet). Separate modules avoid coupling and preserve existing `multistreet.py` API. Both implement `GameState` protocol and work with existing solvers.

**Q5: How to validate continuation table completeness?**
**A5**: During `PreflopConfig` validation, enumerate all reachable non-all-in closing leaves (deal × history). For each, check `payoff_table` has an entry. If any missing, fail with status 2 and list missing keys. This is fail-closed and explicit.

**Q6: Should preflop support rake?**
**A6**: Not in initial implementation. Rake accounting is specified in `research/phase3/game-structure-rake.md` and applies to terminal pots. Preflop module computes zero-sum payoffs; rake is a future extension via a `RakePolicy` field in `PreflopConfig`. This keeps the initial design simple and testable.

**Q7: What is the acceptance threshold for iterative CFR tests?**
**A7**: Use a predeclared measured threshold from a reference run. For example, vanilla CFR on a tiny preflop game with 10,000 iterations reaches NashConv < 0.01. Record this threshold in the test fixture. Do not invent thresholds; measure them from a working implementation and independent best-response validation.

## 11. References

### 11.1 Project documents

- `PHASE3_MISSION.md`: Phase 3 goals, ground rules, wave structure
- `ARCHITECTURE.md`: Existing architecture, dependency graph, acceptance gates
- `research/phase3/preflop-heads-up.md`: Preflop research, verified references, continuation boundary
- `research/phase3/bet-sizing.md`: Sizing modes, units, formulas, oracles
- `research/phase3/game-structure-rake.md`: Accounting, forced postings, conservation, rake
- `research/phase3/nodelock-profiles.md`: Tree editing, nodelocks, profiles (future integration)
- `research/phase3/ranges-display.md`: Range editor, strategy tables (future integration)

### 11.2 Existing modules

- `src/poker_solver/model.py`: Action, GameState protocol, CHANCE, TERMINAL
- `src/poker_solver/cards.py`: parse_card, format_card, validate_unique, RANKS, SUITS, FULL_DECK
- `src/poker_solver/equity.py`: WeightedCombo, exact_equity, range_equity, EquityResult
- `src/poker_solver/evaluator.py`: evaluate_five, evaluate_seven
- `src/poker_solver/multistreet.py`: MultiStreetConfig, MultiStreetState, create_root
- `src/poker_solver/cfr.py`: CFRSolver
- `src/poker_solver/mccfr.py`: MCCFRSolver
- `src/poker_solver/best_response.py`: expected_values, nash_conv, NashConvResult
- `src/poker_solver/api.py`: SolveResult, ExploitabilityResult
- `src/poker_solver/cli.py`: CLI subcommands

### 11.3 External references

- Zinkevich et al., Counterfactual Regret Minimization: https://proceedings.neurips.cc/paper/2007/file/08d98638c6fcd194a4b1e6992063e944-Paper.pdf
- GTO Wizard HU preflop release: https://blog.gtowizard.com/introducing-gto-wizard-ai-heads-up-preflop-solver/
- GTO Wizard solution builder: https://help.gtowizard.com/how-to-build-custom-solutions/
- GTO Wizard raise calculation: https://blog.gtowizard.com/how-to-calculate-raises-in-poker/
- Upswing HU action order: https://upswingpoker.com/who-goes-first-in-texas-holdem-poker/
- OpenSpiel: https://github.com/google-deepmind/open_spiel

## 12. Summary

This design specifies a self-consistent, implementable heads-up preflop subsystem that:

1. **Preserves all current APIs**: No changes to `model.py`, `cards.py`, `equity.py`, `evaluator.py`, `multistreet.py`, `cfr.py`, `mccfr.py`, `best_response.py`, existing `api.py`/`cli.py` subcommands.

2. **Addresses blind/ante double counting**: Forced postings are debited exactly once, appear in `pot` and `total_contributed`, and are never added again as "dead money." Payoff baseline is pre-posting wealth. Conservation invariant holds at every state.

3. **Addresses HU action order**: BTN posts SB, BB posts BB, BTN acts first preflop. BB acts first postflop (recorded in metadata). `highest_commitment` and `last_raise_increment` are explicit state.

4. **Specifies raise-tree representation**: `Action.amount` is integer raise-to. Sizing modes (Fixed/Dynamic/Automatic) convert `SizeExpression` to integer targets using exact formulas from `bet-sizing.md`. Legality validated against stack, minimum raise, and pot-limit constraints.

5. **Specifies bounded continuation semantics**: Three explicit modes: `all_in_runout` (exact), `table` (exact for declared game), `checkdown_equity` (approximation, labeled). Non-all-in configs without continuation mode fail validation. No unrestricted postflop parity claimed.

6. **Specifies dependency order**: New modules `sizing.py` and `preflop.py`. `sizing.py` depends only on `model.py` and stdlib. `preflop.py` depends on `model.py`, `cards.py`, `equity.py`, `evaluator.py`, `sizing.py`. No circular dependencies. Both integrate with existing solvers via `GameState` protocol.

7. **Specifies exact tests/oracles/tolerances**: 36 acceptance tests with hand-calculated oracles, existing module cross-checks, exhaustive enumeration, and measured iterative thresholds. Integer accounting is exact. Float comparisons use `1e-12` unless fixture-specific.

8. **Specifies implemented vs. boundary decisions**: Tier 1 (implemented): HU positions, antes, finite tree, Fixed/Dynamic/Automatic sizing, all-in runout, table continuation, checkdown approximation, existing solvers, strict JSON API. Tier 2/3 (boundary): unrestricted postflop, neural parity, large-scale, multiway, rake, ICM, continuous sizing.

The design is ready for parallel implementation by exclusive-ownership subagents, followed by adversarial review.
