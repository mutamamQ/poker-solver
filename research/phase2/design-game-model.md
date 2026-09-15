# Multi-street game model design

## Overview

This document specifies the exact dataclasses, state transitions, action semantics, and invariants for a finite multi-street heads-up Hold'em game model compatible with the existing `GameState` protocol and CFR solver infrastructure.

## Scope and compatibility

**In scope:**
- Finite postflop heads-up Hold'em starting on flop, turn, or river
- Exact combo-weighted ranges with blocker conditioning
- Discrete check/bet/call/fold actions with configured pot-fraction sizes plus all-in
- Pot-limit and no-limit betting modes
- Deterministic chance outcomes for board runouts
- Zero-sum two-player utilities
- Perfect-recall information sets
- Protocol compatibility with `poker_solver.model.GameState`
- Compatibility with existing `CFRSolver` and `best_response` modules

**Out of scope:**
- Three or more players (see `three-player-scope.md`)
- Preflop action
- Raises (Phase 2 allows at most one bet per street)
- Continuous action spaces
- Suit isomorphism or card/action abstraction (deferred performance optimizations)

## Dataclasses

### MultiStreetConfig

```python
@dataclass(frozen=True, slots=True)
class MultiStreetConfig:
    """Immutable configuration for a finite multi-street heads-up spot."""
    
    starting_street: Literal["flop", "turn", "river"]
    board: tuple[int, ...]  # 3, 4, or 5 cards depending on starting_street
    initial_pot: float      # pot at the beginning of the spot
    effective_stack: int    # each player's remaining stack (equal stacks)
    bet_sizes: tuple[int, ...]  # discrete bet amounts in chips
    pot_limit: bool         # if True, cap bets by pot-limit rule; if False, no-limit
    range0: tuple[WeightedCombo, ...]
    range1: tuple[WeightedCombo, ...]
    
    def __post_init__(self) -> None:
        # Validate starting_street and board length
        street_cards = {"flop": 3, "turn": 4, "river": 5}
        if self.starting_street not in street_cards:
            raise ValueError("starting_street must be 'flop', 'turn', or 'river'")
        board = validate_unique(self.board)
        if len(board) != street_cards[self.starting_street]:
            raise ValueError(f"{self.starting_street} requires {street_cards[self.starting_street]} cards")
        object.__setattr__(self, "board", board)
        
        # Validate pot and stack
        if not isfinite(self.initial_pot) or self.initial_pot <= 0:
            raise ValueError("initial_pot must be finite and positive")
        if not isinstance(self.effective_stack, int) or self.effective_stack <= 0:
            raise ValueError("effective_stack must be a positive integer")
        
        # Validate bet sizes
        if not self.bet_sizes:
            raise ValueError("bet_sizes must be nonempty")
        for size in self.bet_sizes:
            if not isinstance(size, int) or size <= 0:
                raise ValueError("all bet sizes must be positive integers")
        if sorted(self.bet_sizes) != list(self.bet_sizes):
            raise ValueError("bet_sizes must be sorted ascending")
        
        # Validate ranges
        if not self.range0 or not self.range1:
            raise ValueError("both ranges must be nonempty")
```

### MultiStreetState

```python
@dataclass(frozen=True, slots=True)
class MultiStreetState:
    """Immutable state node in the multi-street game tree."""
    
    config: MultiStreetConfig
    deal: tuple[tuple[int, int], tuple[int, int]] | None = None  # None at chance root
    current_board: tuple[int, ...] = ()  # grows as streets complete
    current_street: Literal["flop", "turn", "river", "terminal"] = "flop"
    street_history: tuple[Action, ...] = ()  # actions on current street
    full_history: tuple[Action | str, ...] = ()  # complete public history including street markers
    contributions: tuple[int, int] = (0, 0)  # cumulative chips committed since spot start
    street_investment: tuple[int, int] = (0, 0)  # chips committed on current street
    pending_runout: bool = False  # True when waiting for next board card
    
    def __post_init__(self) -> None:
        # Initialize current_board from config if not set
        if not self.current_board:
            object.__setattr__(self, "current_board", self.config.board)
        # Initialize current_street from config if at root
        if self.deal is None and self.current_street == "flop":
            object.__setattr__(self, "current_street", self.config.starting_street)
```

## State transitions

### Chance nodes

**Deal chance (root):** When `deal is None`, the state is a chance node that pairs compatible weighted combos from both ranges, excluding board/card collisions. Each deal outcome has probability `w0 * w1 / Z` where `Z` normalizes over all legal pairs.

**Runout chance:** When `pending_runout is True`, the state is a chance node that deals the next board card uniformly from the deck excluding dealt private cards and current board. After flop betting closes, one turn card is dealt; after turn betting closes, one river card is dealt.

### Action nodes

**Player to act:** Determined by `street_history` and `current_street`. Player 0 acts first on each street. After player 0 acts, player 1 responds. Specific patterns:

- `street_history == ()`: player 0 acts
- `street_history == (CHECK,)`: player 1 acts
- `street_history == (bet_action,)`: player 1 acts (facing bet)
- `street_history == (CHECK, bet_action)`: player 0 acts (facing check-raise)
- Terminal patterns: `(CHECK, CHECK)`, `(bet, FOLD)`, `(bet, CALL)`, `(CHECK, bet, FOLD)`, `(CHECK, bet, CALL)`

### Street closure and runout

**Check-check or bet-call:**
- If `current_street == "river"`: transition to terminal showdown
- If either player is all-in: set `pending_runout = True` and deal remaining board cards without further betting
- Otherwise: set `pending_runout = True`, append street marker to `full_history`, reset `street_history = ()` and `street_investment = (0, 0)`, advance `current_street`

**Fold:** Immediate terminal.

**All-in detection:** A player is all-in when `contributions[player] >= config.effective_stack`.

## Action amount semantics

### Action.amount interpretation

- `Action("check")`: amount is 0 (ignored)
- `Action("fold")`: amount is 0 (ignored)
- `Action("call")`: amount is 0 (ignored); the actual chips committed equal the outstanding bet
- `Action("bet", amount)`: `amount` is the **new chips committed by the actor**, not a raise-to total

### Legal bet amounts

**Open bet (no outstanding wager):**
- Candidate sizes: `config.bet_sizes` plus all-in
- All-in amount: `config.effective_stack - contributions[actor]`
- Pot-limit cap (if `config.pot_limit`): current pot (before the bet)
- Legal amounts: intersection of candidates, stack constraint, and pot-limit cap

**Call amount:**
- Outstanding: `street_investment[opponent] - street_investment[actor]`
- Capped by remaining stack: `min(outstanding, config.effective_stack - contributions[actor])`

**No raises:** Phase 2 does not support re-raising. After a bet, only fold and call are legal.

### Pot-limit rule

**Open bet maximum:** `current_pot` where `current_pot = config.initial_pot + sum(contributions)`.

**Facing a bet:** Not applicable in Phase 2 (no raises).

**All-in override:** All-in is always legal if any chips remain, even if it exceeds the pot-limit cap. The all-in amount is `config.effective_stack - contributions[actor]`.

## Zero-sum utility

### Terminal returns

**Fold:** The folding player loses the pot contested on the current street. Net from spot start:
- If player 1 folds to a bet: `returns = (+initial_pot/2 + contributions[1], -initial_pot/2 - contributions[1])`
- If player 0 folds to a check-raise: `returns = (-initial_pot/2 - contributions[0], +initial_pot/2 + contributions[0])`

**Showdown:** Evaluate seven-card hands (private + board), compare ranks.
- Winner takes the pot: `pot = initial_pot + sum(contributions)`
- Net for player 0: `+pot/2 - contributions[0]` if win, `-pot/2 - contributions[0]` if loss
- Tie: each player's net is `-contributions[player]` (they recover their half of the initial pot)

**Zero-sum check:** `returns[0] + returns[1] == 0.0` within floating-point tolerance.

### Accounting invariants

- `contributions[0] == contributions[1]` at showdown (equal effective stacks, no unmatched side pot)
- `0 <= contributions[player] <= config.effective_stack`
- `street_investment[player]` resets to 0 at street transitions but `contributions` accumulate

## Information state keys

### Key structure

```python
def information_state_key(self, player: int) -> tuple[object, ...]:
    if self.current_player() != player:
        raise ValueError("information key requested for non-acting player")
    assert self.deal is not None
    own_hand = self.deal[player]
    return (
        "multistreet-v1",
        player,
        own_hand,
        self.current_board,
        self.full_history,  # includes street markers and all public actions/runouts
        self.config.initial_pot,
        self.config.effective_stack,
        self.config.bet_sizes,
        self.config.pot_limit,
        self.config.starting_street,
    )
```

### Perfect recall

- `full_history` contains the complete ordered sequence of public actions and chance outcomes (street markers, board cards)
- Two nodes with the same information key must have identical legal actions and identical action histories
- Opponent's private cards are excluded
- All game parameters affecting legality are included

## Tractability controls

### Complexity sources

- **Runout branching:** 45 turn cards × 44 river cards from a flop start = 1,980 public runouts before betting
- **Range size:** Combo pairs multiply the tree
- **Betting rounds:** Each street adds a betting layer

### Mitigation strategies

**Vanilla CFR:** Only tractable for tiny ranges and restricted runout decks (e.g., 2-3 combos per side, 10-card deck). Use as a correctness oracle, not a production solver.

**External-sampling MCCFR:** Sample one deal and one runout path per iteration. Scales to realistic range sizes and full 52-card runouts. Required for Phase 2 multi-street solving.

**Explicit abstractions (future):**
- Runout bucketing (group similar turn/river cards)
- Suit isomorphism (requires separate equivalence tests)
- Action abstraction (already applied: discrete bet sizes, no raises)

Phase 2 does **not** silently apply suit isomorphism or runout bucketing. The model represents the exact finite game defined by the configuration.

## Compatibility with existing infrastructure

### GameState protocol

`MultiStreetState` implements all six required methods:

1. `current_player() -> int`: returns `CHANCE`, `TERMINAL`, `0`, or `1`
2. `legal_actions() -> tuple[Action, ...]`: returns deal actions, runout actions, or player actions
3. `chance_outcomes() -> tuple[tuple[Action, float], ...]`: returns weighted deals or uniform runouts
4. `child(action: Action) -> GameState`: returns new immutable state
5. `information_state_key(player: int) -> InfoKey`: returns hashable perfect-recall key
6. `returns() -> tuple[float, float]`: returns zero-sum payoffs at terminal

### CFRSolver

The existing `CFRSolver` in `cfr.py` works unchanged:
- `collect_infosets(root)` walks the tree and validates perfect recall
- `train(iterations)` performs vanilla CFR traversal
- `average_strategy()` returns the time-averaged strategy

For large multi-street games, an MCCFR solver (external-sampling) is required. The MCCFR implementation will:
- Own a `random.Random(seed)` instance
- Sample one chance outcome per chance node per iteration
- Store only reached information sets
- Pass reach probabilities incrementally

### Best response

The existing `best_response` module computes exact counterfactual values by:
- Traversing the full tree for the responding player
- Maximizing over legal actions at each information set
- Respecting the opponent's fixed strategy

This works unchanged for multi-street games within tractable size limits. For large games, public-tree best response (future optimization) can cache public-node values.

## Invariants and validation

### Construction invariants

- Board length matches starting street (3/4/5 for flop/turn/river)
- `initial_pot > 0` and finite
- `effective_stack > 0` and integer
- `bet_sizes` nonempty, positive integers, sorted ascending
- Ranges nonempty with at least one positive-weight combo each
- All bet sizes `<= effective_stack`

### Transition invariants

- `current_player()` is deterministic from state
- `legal_actions()` is nonempty except at terminal
- `child(action)` raises `ValueError` if action not legal
- Chance outcomes sum to 1.0 within tolerance
- `returns()` raises `ValueError` if called at non-terminal
- `returns()` sums to zero within tolerance at terminal

### Perfect-recall invariant

- `information_state_key(player)` raises if `current_player() != player`
- Two states with equal keys have equal `(player, legal_actions())`
- `collect_infosets` validates this during tree walk

### Showdown invariant

- `contributions[0] == contributions[1]` at showdown (equal effective stacks)
- Both players' hands and board are disjoint
- Hand ranks are computed with `evaluate_seven(deal[player] + current_board)`

## TDD implementation sequence

### Phase 1: River-only model (already complete)

- ✅ `RiverConfig` and `RiverState` dataclasses
- ✅ Single-street betting (check/bet/fold/call)
- ✅ Exact combo-weighted ranges with blocker conditioning
- ✅ Zero-sum showdown utilities
- ✅ Perfect-recall information keys
- ✅ Protocol compatibility and CFR solving
- ✅ Tests: `test_river.py` with fixtures and NashConv < 0.01

### Phase 2: Multi-street extension

**Step 1: Dataclasses and validation (TDD)**

- Write `test_multistreet_config_validation()`: invalid street, board length, pot, stack, bet sizes, ranges
- Implement `MultiStreetConfig.__post_init__` to pass tests
- Write `test_multistreet_state_initialization()`: default field values, immutability
- Implement `MultiStreetState` dataclass

**Step 2: Chance nodes (TDD)**

- Write `test_deal_chance_outcomes()`: root chance pairs, probabilities sum to 1, blocker conditioning
- Implement `_deal_outcomes()` and `current_player()` for deal chance
- Write `test_runout_chance_uniform()`: turn/river card probabilities, deck exclusions
- Implement `_runout_outcomes()` and `current_player()` for runout chance

**Step 3: Single-street actions (TDD)**

- Write `test_flop_betting_actions()`: player 0 opens, player 1 responds, fold/call terminals
- Implement `legal_actions()` for flop betting
- Write `test_pot_limit_caps()`: open bet capped by pot, all-in override
- Implement pot-limit logic in `legal_actions()`
- Write `test_no_limit_mode()`: no pot cap, only stack cap
- Implement no-limit mode

**Step 4: Street transitions (TDD)**

- Write `test_check_check_advances_street()`: flop → turn, turn → river, river → terminal
- Implement `child()` for check-check transitions
- Write `test_bet_call_advances_street()`: contributions accumulate, street_investment resets
- Implement `child()` for bet-call transitions
- Write `test_all_in_runout()`: remaining streets dealt without betting
- Implement all-in detection and runout logic

**Step 5: Terminal utilities (TDD)**

- Write `test_fold_payoffs()`: bet-fold, check-raise-fold, correct pot accounting
- Implement `returns()` for fold terminals
- Write `test_showdown_payoffs()`: hand evaluation, winner/loser/tie, zero-sum check
- Implement `returns()` for showdown terminals
- Write `test_contributions_invariant()`: equal contributions at showdown
- Add assertion in `returns()`

**Step 6: Information keys (TDD)**

- Write `test_infoset_hides_opponent()`: same own hand, different opponent hands → same key
- Implement `information_state_key()`
- Write `test_perfect_recall_history()`: different action paths → different keys
- Validate `full_history` inclusion
- Write `test_collect_infosets_validates()`: inconsistent keys raise error
- Run `collect_infosets()` on test tree

**Step 7: Integration and solving (TDD)**

- Write `test_tiny_multistreet_cfr()`: 2-combo ranges, 10-card deck, vanilla CFR, NashConv < threshold
- Implement complete `MultiStreetState` protocol
- Write `test_multistreet_mccfr()`: realistic ranges, seeded MCCFR, convergence check
- Implement `MCCFRSolver` (external-sampling)
- Write `test_deterministic_output()`: same seed → identical JSON strategy
- Validate reproducibility contract

**Step 8: Benchmark and documentation**

- Write `test_multistreet_benchmark()`: fixed fixture, median runtime, CI ceiling
- Measure baseline and set gate (see `determinism-performance.md`)
- Update `README.md` with multi-street API examples
- Document MCCFR seed parameter and convergence metrics

## References

- Existing river model: `src/poker_solver/river.py`
- GameState protocol: `src/poker_solver/model.py`
- CFR solver: `src/poker_solver/cfr.py`
- Best response: `src/poker_solver/best_response.py`
- Evaluator: `src/poker_solver/evaluator.py`
- Phase 2 research: `research/phase2/multistreet-modeling.md`, `feature-inventory.md`, `three-player-scope.md`, `accuracy-fixtures.md`, `determinism-performance.md`
- Pot-limit rule: https://barge.org/rulebook/pot-limit.html
- CFR paper: https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- MCCFR paper: https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html
- OpenSpiel framework: https://github.com/google-deepmind/open_spiel

## Summary

This design extends the proven river model to multi-street Hold'em while preserving protocol compatibility, perfect recall, zero-sum utilities, and deterministic solving. The TDD sequence builds incrementally from validated river foundations through chance nodes, street transitions, and terminal accounting to full CFR integration. Tractability is managed through explicit MCCFR sampling, not silent abstractions. All invariants are testable and enforced.
