# S3 Preflop Betting & Sizing Design Contract

**Design reviewer:** D302 (replacement)  
**Scope:** S3 multiway preflop 2–9 players  
**Status:** Design-only; no implementation  
**UTC:** 2026-09-16 00:29 UTC  

---

## 1. Executive Summary

This contract specifies **exact finite preflop betting semantics** for 2–9 players, covering:

- Root first-actor determination and action order (position-based, post-button rotation)
- Open/limp/SB-complete/fold/cold-call mechanics
- Absolute CALL and RAISE-to street commitments
- Minimum full raise rule and short all-in reopening entitlements
- Pending responder queue management
- 3-bet/4-bet/5-bet+ depth with per-position IP/OOP sizing rules
- Per-cold-caller count sizing rule representation, selection, and deduplication
- Terminal closure conditions and structural bounds
- Worked HU/6-max/9-max traces with exact actors and amounts
- Validation rules and failure modes
- Public history representation and legal action order

The design **reuses** existing `Action`, `sizing.py` contracts, and `game_structure.py` patterns where possible, identifying necessary **additive types** for multiway preflop state.

---

## 2. Scope & Boundaries

### 2.1 In Scope

- **Players:** 2–9 seats
- **Positions:** Button, SB, BB, and optional straddles (standard, double, Mississippi)
- **Forced posts:** Blinds, antes, straddles with exact ledger accounting
- **Actions:** FOLD, CHECK (BB option), CALL (including limp, SB complete, cold-call), RAISE (open-raise, 3-bet, 4-bet, 5-bet+)
- **Sizing rules:** Per-position (IP/OOP), per-cold-caller-count, pot-percent/geometric/big-blind/all-in expressions
- **Raise semantics:** Minimum full raise, short all-in reopening policy
- **Pending queue:** Ordered responders, closure on all-acted or single-live
- **Terminal conditions:** All fold to one, all call/check with no pending, all-in coverage
- **Public history:** Ordered (actor, Action) tuples
- **Bounds:** max_raises, max_deals, max_nodes

### 2.2 Out of Scope

- Postflop streets (covered by S1/S2)
- Neural continuation values (S1)
- Automatic abstraction (S4)
- Continuous sizing (S5)
- ICM/bounty strategy (S6)
- PLO

---

## 3. Core Contracts

### 3.1 Reused Types (from existing modules)

#### 3.1.1 `Action` (from `model.py`)

```python
@dataclass(frozen=True, slots=True)
class Action:
    kind: str  # "FOLD", "CHECK", "CALL", "RAISE", "DEAL"
    amount: int = 0  # CALL/RAISE: absolute street commitment target
```

- **FOLD:** `Action("FOLD")`
- **CHECK:** `Action("CHECK")` — BB option when facing no raise
- **CALL:** `Action("CALL", target)` — `target` is absolute street commitment (includes limp to BB, SB complete, cold-call)
- **RAISE:** `Action("RAISE", target)` — `target` is absolute raise-to amount
- **DEAL:** `Action("DEAL", index)` — chance outcome

#### 3.1.2 Sizing Expressions (from `sizing.py`)

Reuse `validate_size_expression`, `convert_size_to_chips`, `fixed_sizes` with context:

```python
context = {
    "pot": int,
    "own_commitment": int,
    "highest_commitment": int,
    "remaining_stack": int,
    "big_blind": int,
    "minimum_raise_to": int,
    "pot_limit_max_raise_to": None,  # Hold'em: always None
    "short_all_in_allowed": bool,
}
```

Expressions: `{"unit": "pot-percent", "value": 50}`, `{"unit": "big-blinds", "value": 2.5}`, `{"unit": "geometric", "streets": 1, "scale": 1.0}`, `{"unit": "all-in"}`

#### 3.1.3 Game Structure Primitives (from `game_structure.py`)

- `ForcedPost(seat, kind, amount)` — "ante", "small-blind", "big-blind", "straddle"
- `refund_uncalled_excess(contributions)` — refund logic for unmatched bets
- Integer chip accounting, conservation checks

---

### 3.2 New Additive Types for Multiway Preflop

#### 3.2.1 `PreflopPosition`

```python
from typing import Literal

PreflopPosition = Literal[
    "BTN",  # Button
    "SB",   # Small blind
    "BB",   # Big blind
    "UTG",  # Under the gun
    "UTG+1", "UTG+2",  # Early position
    "MP",   # Middle position
    "MP+1", "MP+2",
    "HJ",   # Hijack
    "CO",   # Cutoff
    "STRADDLE",  # Any straddle position
]
```

**Mapping:** Given `num_players`, `button_seat`, and `forced_posts`, assign canonical position labels. For 2-player (HU): BTN acts first preflop (posts SB), BB acts second. For 3+: action starts left of BB (or leftmost straddle).

#### 3.2.2 `SizingRuleSet`

```python
@dataclass(frozen=True, slots=True)
class SizingRuleSet:
    """Per-position, per-cold-caller-count sizing rule collection."""
    
    position: PreflopPosition
    is_in_position: bool  # IP vs OOP relative to action flow
    cold_caller_count: int  # 0 = open, 1 = one cold-caller behind raiser, etc.
    expressions: tuple[dict[str, object], ...]  # Sizing expressions
    
    def __post_init__(self) -> None:
        if self.cold_caller_count < 0:
            raise ValueError("cold_caller_count must be non-negative")
        if not self.expressions:
            raise ValueError("expressions must be non-empty")
        for expr in self.expressions:
            validate_size_expression(dict(expr))
```

**Usage:** A `MultiwayPreflopConfig` contains a tuple of `SizingRuleSet` entries. When a player acts, the engine:

1. Determines their position
2. Counts cold-callers (players who called but did not open/raise)
3. Filters `SizingRuleSet` by `(position, cold_caller_count)` or falls back to `(position, 0)` if no exact match
4. Applies `fixed_sizes(expressions, context)` to get legal raise targets
5. Deduplicates by target amount

#### 3.2.3 `PreflopPublicAction`

```python
@dataclass(frozen=True, slots=True)
class PreflopPublicAction:
    """Public history entry: actor seat + action."""
    actor: int  # Seat index 0..(num_players-1)
    action: Action
    
    def __post_init__(self) -> None:
        if not isinstance(self.actor, int) or self.actor < 0:
            raise ValueError("actor must be non-negative int")
        if not isinstance(self.action, Action):
            raise ValueError("action must be Action")
```

#### 3.2.4 `MultiwayPreflopConfig`

```python
@dataclass(frozen=True, slots=True)
class MultiwayPreflopConfig:
    """Immutable 2–9 player preflop configuration."""
    
    version: str = "multiway-preflop-v1"
    num_players: int  # 2..9
    button: int  # Seat index
    starting_stacks: tuple[int, ...]  # Length num_players
    forced_posts: tuple[ForcedPost, ...]  # Blinds, antes, straddles
    ranges: tuple[tuple[WeightedCombo, ...], ...]  # Per-seat weighted combos
    sizing_rules: tuple[SizingRuleSet, ...]  # All position/cold-caller rules
    max_raises: int  # Cap on raise count (e.g., 4 for open/3-bet/4-bet/5-bet)
    max_deals: int  # Bound on compatible deal enumeration
    max_nodes: int  # Tree size bound
    short_all_in_reopens: bool  # Whether short all-in reopens action
    continuation: Continuation  # Terminal payoff table
    
    def __post_init__(self) -> None:
        # Validation: num_players in 2..9, button valid, stacks positive,
        # forced_posts valid, ranges non-empty and disjoint per deal,
        # sizing_rules non-empty, max_raises/deals/nodes positive,
        # continuation kind "terminal-table"
        ...
```

#### 3.2.5 `MultiwayPreflopState`

```python
@dataclass(frozen=True, slots=True)
class MultiwayPreflopState:
    """Immutable multiway preflop state snapshot."""
    
    config: MultiwayPreflopConfig
    private_deal: tuple[tuple[int, int], ...] | None  # None at chance root
    acting_player: int  # CHANCE=-1, TERMINAL=-2, or seat 0..(num_players-1)
    pot: int
    street_committed: tuple[int, ...]  # Current street (preflop) commitment per seat
    total_contributed: tuple[int, ...]  # Lifetime contribution (includes posts)
    remaining: tuple[int, ...]  # Remaining stack per seat
    folded: tuple[bool, ...]  # Folded status per seat
    pending: tuple[int, ...]  # Ordered queue of seats yet to act this round
    can_raise: tuple[bool, ...]  # Raise entitlement per seat
    last_raise_increment: int  # Size of last full raise (for min-raise calc)
    raise_count: int  # Number of raises so far (open=1, 3-bet=2, etc.)
    history: tuple[PreflopPublicAction, ...]  # Ordered public actions
    terminal_values: tuple[Fraction, ...] | None  # Zero-sum payoffs at TERMINAL
    
    def __post_init__(self) -> None:
        # Validation: config valid, acting_player in {CHANCE, TERMINAL, 0..num_players-1},
        # pot = sum(total_contributed), remaining + total_contributed = starting_stacks,
        # street_committed <= total_contributed, folded/pending/can_raise consistent,
        # raise_count <= max_raises, history valid, terminal_values zero-sum if TERMINAL
        ...
    
    def current_player(self) -> int: ...
    def chance_outcomes(self) -> tuple[tuple[Action, Fraction], ...]: ...
    def legal_actions(self) -> tuple[Action, ...]: ...
    def child(self, action: Action) -> MultiwayPreflopState: ...
    def information_state_key(self, player: int): ...
    def returns(self) -> tuple[float, ...]: ...
```

---

## 4. Betting Semantics

### 4.1 Root First Actor & Action Order

**Initialization (after forced posts applied):**

1. **Chance root:** `acting_player = CHANCE`, no private deal, `history = ()`
2. **After DEAL:** `private_deal` set, `acting_player` = first live seat with `remaining > 0` **left of the rightmost forced post** (typically left of BB or straddle)
3. **Pending queue:** All live seats in position order (left of first actor wrapping around), excluding first actor (who is acting now)

**Position order (3+ players):** Start from seat left of button, wrap clockwise. For HU: BTN acts first preflop.

**Example (6-max, button=5, SB=0, BB=1):**  
Action order: 2 (UTG), 3 (MP), 4 (CO), 5 (BTN), 0 (SB), 1 (BB)  
First actor after deal: seat 2 (UTG)  
Pending at start: `(3, 4, 5, 0, 1)`

### 4.2 Action Types & Street Commitment

#### 4.2.1 FOLD

- **Precondition:** Facing a bet (highest street commitment > own)
- **Effect:** `folded[actor] = True`, `can_raise[actor] = False`, actor removed from pending
- **Terminal check:** If only one live (non-folded) seat remains, proceed to settlement

#### 4.2.2 CHECK

- **Precondition:** No outstanding bet (own street commitment == highest among live players)
- **Effect:** Actor marked as acted, removed from pending
- **BB option:** BB can check if no raise (all limped or SB completed)

#### 4.2.3 CALL

**Absolute commitment semantics:**  
`Action("CALL", target)` where `target = min(highest_street_commitment, own_street_commitment + remaining_stack)`

**Subcases:**

- **Limp:** First voluntary action, calling the BB amount (e.g., `target = BB` when `own_street_commitment = 0` for non-blind seats)
- **SB complete:** SB calling BB (e.g., SB posted 0.5 BB, calls to 1 BB: `target = 1 BB`)
- **Cold-call:** Calling a raise without having opened/raised (e.g., UTG opens 3BB, MP calls 3BB)
- **All-in call:** `remaining_stack < (highest - own)`, so `target = own + remaining`

**Effect:**  
```python
payment = target - street_committed[actor]
street_committed[actor] = target
total_contributed[actor] += payment
remaining[actor] -= payment
pot += payment
if remaining[actor] == 0:
    can_raise[actor] = False
```

Actor removed from pending. If `street_committed[actor] < highest` (short all-in call), apply **uncalled excess refund** logic before terminal settlement.

#### 4.2.4 RAISE

**Absolute raise-to semantics:**  
`Action("RAISE", target)` where `target` is the new absolute street commitment.

**Minimum full raise:**  
`minimum_raise_to = highest_street_commitment + last_raise_increment`

**Legal raise targets:**  
From `sizing_rules` filtered by `(position, cold_caller_count)`, apply `fixed_sizes(expressions, context)` to get candidate targets `T`. A target `t ∈ T` is legal if:

1. `highest_street_commitment < t <= own_street_commitment + remaining_stack`
2. `t >= minimum_raise_to` **OR** `t == own_street_commitment + remaining_stack` (all-in exception)

**Full vs. short raise:**

- **Full raise:** `raise_size = target - highest_street_commitment >= last_raise_increment`  
  **Effect:** `last_raise_increment = raise_size`, reset `acted` flags for all live seats (except raiser), `can_raise = [True for live seats with remaining > 0]`, rebuild pending queue (all live seats except raiser, in position order after raiser)
  
- **Short all-in raise:** `raise_size < last_raise_increment` and `remaining[actor] == 0` after payment  
  **Effect (if `short_all_in_reopens = False`):** `can_raise[other_seats_in_pending] = False` (action does NOT reopen to seats who already acted)  
  **Effect (if `short_all_in_reopens = True`):** `can_raise` unchanged for pending seats (action reopens)

**Raise count:** Increment `raise_count` by 1. If `raise_count >= max_raises`, no further raises allowed (only FOLD/CALL/CHECK).

**Effect:**  
```python
payment = target - street_committed[actor]
street_committed[actor] = target
total_contributed[actor] += payment
remaining[actor] -= payment
pot += payment
raise_count += 1
if full_raise:
    last_raise_increment = raise_size
    pending = ordered_live_seats_after(actor, excluding=actor)
    can_raise = [not folded[s] and remaining[s] > 0 for s in range(num_players)]
else:  # short all-in
    if not short_all_in_reopens:
        can_raise[other_pending] = False
    # pending unchanged (actor already removed)
if remaining[actor] == 0:
    can_raise[actor] = False
```

### 4.3 Pending Responder Queue

**Invariant:** `pending` is an ordered tuple of seat indices who have not yet acted (or must act again after a raise) in the current betting round.

**Update rules:**

- **After FOLD/CHECK/CALL (non-raise):** Remove actor from pending
- **After full RAISE:** Rebuild pending = all live seats (not folded, remaining > 0) in position order after raiser, excluding raiser
- **After short all-in RAISE:** Remove actor from pending; other pending seats retain their order

**Next actor:** `acting_player = pending[0]` if `pending` non-empty, else proceed to terminal settlement.

### 4.4 Terminal Closure Conditions

**A state transitions to TERMINAL when:**

1. **All fold to one:** Only one seat has `folded = False` → award pot to that seat
2. **All acted, no pending:** `pending == ()` and all live seats have acted (either checked or called to highest commitment) → proceed to showdown/continuation
3. **All-in coverage:** All live seats except at most one have `remaining == 0`, and `pending == ()` → showdown/continuation

**Settlement:**

1. Apply `refund_uncalled_excess(total_contributed)` to refund unmatched bets
2. If multiple live seats: look up `continuation.payoff_table[(private_deal, history)]` for zero-sum payoffs
3. If single live seat: award pot minus contributions to that seat
4. Set `terminal_values` (zero-sum tuple), `acting_player = TERMINAL`

---

## 5. Sizing Rule Representation & Selection

### 5.1 Per-Position IP/OOP Rules

**Position determination:**  
Given `button`, `num_players`, and action order, classify each seat as:

- **IP (In Position):** Acts after most opponents postflop (BTN, CO, HJ in 6-max)
- **OOP (Out of Position):** Acts before most opponents postflop (SB, BB, UTG, MP in 6-max)

**Sizing rule lookup:**  
When seat `s` acts, find `SizingRuleSet` where:

1. `position` matches seat's canonical position (e.g., "CO", "BB")
2. `is_in_position` matches IP/OOP classification
3. `cold_caller_count` matches current count of cold-callers in the pot

If no exact match on `cold_caller_count`, fall back to `cold_caller_count = 0` (default open-raise sizing).

### 5.2 Per-Cold-Caller Count

**Cold-caller definition:** A seat that called a bet/raise but did not itself open or raise.

**Counting:**  
At any decision node, `cold_caller_count = number of seats who called (not opened/raised) since the last raise (or since the start if no raises)`.

**Example (6-max):**  
- UTG opens 3BB → `cold_caller_count = 0` for UTG  
- MP calls 3BB → MP is a cold-caller  
- CO raises to 10BB → `cold_caller_count = 1` for CO (one cold-caller behind: MP)  
- BTN calls 10BB → BTN is a cold-caller  
- SB calls 10BB → SB is a cold-caller  
- BB raises to 30BB → `cold_caller_count = 2` for BB (two cold-callers behind: BTN, SB)

**Sizing adjustment:** A `SizingRuleSet` with `cold_caller_count = 2` might specify tighter (smaller) 3-bet sizes than `cold_caller_count = 0` (isolation raise).

### 5.3 Deduplication

After applying `fixed_sizes(expressions, context)` to get `tuple[SizingChoice, ...]`, deduplicate by `target` amount (already done by `fixed_sizes`). If multiple expressions yield the same chip target, keep one `SizingChoice` (first by expression order).

---

## 6. Worked Examples

### 6.1 Heads-Up (HU) Trace

**Setup:**  
- `num_players = 2`, `button = 0` (BTN/SB), seat 1 = BB  
- Stacks: `(100, 100)` BB  
- Forced posts: SB = 0.5 BB (seat 0), BB = 1 BB (seat 1)  
- Sizing rules: BTN open 2.5BB or 3BB, BB 3-bet 9BB or 12BB  

**Trace:**

1. **Chance root:** `acting_player = CHANCE`, `pot = 1.5 BB`, `street_committed = (0.5, 1.0)`, `total_contributed = (0.5, 1.0)`, `remaining = (99.5, 99.0)`, `pending = (1,)` (BB will act after BTN), `history = ()`

2. **DEAL:** `Action("DEAL", 0)` → `private_deal = ((0,1), (2,3))`, `acting_player = 0` (BTN acts first HU preflop), `pending = (1,)`

3. **BTN raises to 3BB:** `Action("RAISE", 3.0)` (absolute commitment 3 BB)  
   - Payment: `3.0 - 0.5 = 2.5 BB`  
   - New state: `pot = 4.0 BB`, `street_committed = (3.0, 1.0)`, `remaining = (97.0, 99.0)`, `last_raise_increment = 3.0 - 1.0 = 2.0 BB`, `raise_count = 1`, `pending = (1,)`, `history = ((0, RAISE 3.0),)`

4. **BB 3-bets to 12BB:** `Action("RAISE", 12.0)`  
   - Payment: `12.0 - 1.0 = 11.0 BB`  
   - New state: `pot = 15.0 BB`, `street_committed = (3.0, 12.0)`, `remaining = (97.0, 88.0)`, `last_raise_increment = 12.0 - 3.0 = 9.0 BB`, `raise_count = 2`, `pending = (0,)` (BTN must act again), `history = ((0, RAISE 3.0), (1, RAISE 12.0))`

5. **BTN calls 12BB:** `Action("CALL", 12.0)`  
   - Payment: `12.0 - 3.0 = 9.0 BB`  
   - New state: `pot = 24.0 BB`, `street_committed = (12.0, 12.0)`, `remaining = (88.0, 88.0)`, `pending = ()`, `history = ((0, RAISE 3.0), (1, RAISE 12.0), (0, CALL 12.0))`  
   - **Terminal:** No pending, all commitments equal → settlement via continuation table

### 6.2 Six-Max Trace (with limps and cold-calls)

**Setup:**  
- `num_players = 6`, `button = 5`, SB = 0, BB = 1  
- Stacks: `(100, 100, 100, 100, 100, 100)` BB  
- Forced posts: SB = 0.5 BB (seat 0), BB = 1 BB (seat 1)  
- Sizing rules: UTG open 2.5BB/3BB, CO 3-bet 10BB (0 cold-callers) or 12BB (1+ cold-callers), BB 3-bet 9BB/12BB  

**Trace:**

1. **Chance root:** `pot = 1.5 BB`, `street_committed = (0.5, 1.0, 0, 0, 0, 0)`, `total_contributed = (0.5, 1.0, 0, 0, 0, 0)`, `remaining = (99.5, 99.0, 100, 100, 100, 100)`, `pending = (2, 3, 4, 5, 0, 1)` (UTG first, then MP, CO, BTN, SB, BB)

2. **DEAL:** `private_deal` set, `acting_player = 2` (UTG)

3. **UTG limps (calls 1BB):** `Action("CALL", 1.0)`  
   - Payment: `1.0 - 0 = 1.0 BB`  
   - New state: `pot = 2.5 BB`, `street_committed = (0.5, 1.0, 1.0, 0, 0, 0)`, `remaining = (99.5, 99.0, 99.0, 100, 100, 100)`, `pending = (3, 4, 5, 0, 1)`, `history = ((2, CALL 1.0),)`  
   - UTG is now a **cold-caller** (limped, did not open)

4. **MP folds:** `Action("FOLD")`  
   - New state: `folded[3] = True`, `pending = (4, 5, 0, 1)`, `history = ((2, CALL 1.0), (3, FOLD))`

5. **CO raises to 3BB:** `Action("RAISE", 3.0)`  
   - Payment: `3.0 - 0 = 3.0 BB`  
   - New state: `pot = 5.5 BB`, `street_committed = (0.5, 1.0, 1.0, 0, 3.0, 0)`, `remaining = (99.5, 99.0, 99.0, 100, 97.0, 100)`, `last_raise_increment = 3.0 - 1.0 = 2.0 BB`, `raise_count = 1`, `pending = (5, 0, 1, 2)` (BTN, SB, BB, UTG must act), `history = ((2, CALL 1.0), (3, FOLD), (4, RAISE 3.0))`  
   - CO opened (first raise), so `cold_caller_count = 0` for CO's sizing lookup

6. **BTN calls 3BB:** `Action("CALL", 3.0)`  
   - Payment: `3.0 - 0 = 3.0 BB`  
   - New state: `pot = 8.5 BB`, `street_committed = (0.5, 1.0, 1.0, 0, 3.0, 3.0)`, `remaining = (99.5, 99.0, 99.0, 100, 97.0, 97.0)`, `pending = (0, 1, 2)`, `history = ((2, CALL 1.0), (3, FOLD), (4, RAISE 3.0), (5, CALL 3.0))`  
   - BTN is now a **cold-caller**

7. **SB folds:** `Action("FOLD")`  
   - New state: `folded[0] = True`, `pending = (1, 2)`, `history = ((2, CALL 1.0), (3, FOLD), (4, RAISE 3.0), (5, CALL 3.0), (0, FOLD))`

8. **BB 3-bets to 12BB:** `Action("RAISE", 12.0)`  
   - **Cold-caller count for BB:** 2 (BTN and UTG are cold-callers behind the CO's open)  
   - Sizing lookup: `SizingRuleSet(position="BB", cold_caller_count=2, expressions=...)` → 12BB selected  
   - Payment: `12.0 - 1.0 = 11.0 BB`  
   - New state: `pot = 19.5 BB`, `street_committed = (0.5, 12.0, 1.0, 0, 3.0, 3.0)`, `remaining = (99.5, 88.0, 99.0, 100, 97.0, 97.0)`, `last_raise_increment = 12.0 - 3.0 = 9.0 BB`, `raise_count = 2`, `pending = (2, 4, 5)` (UTG, CO, BTN must act again), `history = ((2, CALL 1.0), (3, FOLD), (4, RAISE 3.0), (5, CALL 3.0), (0, FOLD), (1, RAISE 12.0))`

9. **UTG folds:** `Action("FOLD")`  
   - New state: `folded[2] = True`, `pending = (4, 5)`, `history = ((2, CALL 1.0), (3, FOLD), (4, RAISE 3.0), (5, CALL 3.0), (0, FOLD), (1, RAISE 12.0), (2, FOLD))`

10. **CO folds:** `Action("FOLD")`  
    - New state: `folded[4] = True`, `pending = (5,)`, `history = ((2, CALL 1.0), (3, FOLD), (4, RAISE 3.0), (5, CALL 3.0), (0, FOLD), (1, RAISE 12.0), (2, FOLD), (4, FOLD))`

11. **BTN folds:** `Action("FOLD")`  
    - New state: `folded[5] = True`, `pending = ()`, only seat 1 (BB) live  
    - **Terminal:** All fold to BB → BB wins pot  
    - Settlement: BB awarded `pot - total_contributed[1] = 19.5 - 1.0 = 18.5 BB` profit  
    - `terminal_values = (-0.5, +18.5, -1.0, 0, -3.0, -3.0)` (zero-sum check: sum = 11.0 BB collected - 11.0 BB contributed by losers = 0 after accounting)

### 6.3 Nine-Max Trace (with straddle)

**Setup:**  
- `num_players = 9`, `button = 8`, SB = 0, BB = 1, UTG straddle = 2  
- Stacks: `(100, 100, 100, 100, 100, 100, 100, 100, 100)` BB  
- Forced posts: SB = 0.5 BB (seat 0), BB = 1 BB (seat 1), Straddle = 2 BB (seat 2)  
- Sizing rules: UTG+1 open 6BB/8BB (facing straddle), straddle 3-bet 18BB/24BB  

**Trace:**

1. **Chance root:** `pot = 3.5 BB`, `street_committed = (0.5, 1.0, 2.0, 0, 0, 0, 0, 0, 0)`, `total_contributed = (0.5, 1.0, 2.0, 0, 0, 0, 0, 0, 0)`, `remaining = (99.5, 99.0, 98.0, 100, 100, 100, 100, 100, 100)`, `pending = (3, 4, 5, 6, 7, 8, 0, 1, 2)` (UTG+1 first, then MP, MP+1, MP+2, HJ, CO, BTN, SB, BB, Straddle)

2. **DEAL:** `private_deal` set, `acting_player = 3` (UTG+1, left of straddle)

3. **UTG+1 raises to 8BB:** `Action("RAISE", 8.0)`  
   - Payment: `8.0 - 0 = 8.0 BB`  
   - New state: `pot = 11.5 BB`, `street_committed = (0.5, 1.0, 2.0, 8.0, 0, 0, 0, 0, 0)`, `remaining = (99.5, 99.0, 98.0, 92.0, 100, 100, 100, 100, 100)`, `last_raise_increment = 8.0 - 2.0 = 6.0 BB`, `raise_count = 1`, `pending = (4, 5, 6, 7, 8, 0, 1, 2)`, `history = ((3, RAISE 8.0),)`

4. **All fold to straddle (seats 4–8, 0, 1):** Seven FOLD actions  
   - New state: `folded = (True, True, False, False, True, True, True, True, True)`, `pending = (2,)`, `history = ((3, RAISE 8.0), (4, FOLD), (5, FOLD), (6, FOLD), (7, FOLD), (8, FOLD), (0, FOLD), (1, FOLD))`

5. **Straddle 3-bets to 24BB:** `Action("RAISE", 24.0)`  
   - Payment: `24.0 - 2.0 = 22.0 BB`  
   - New state: `pot = 33.5 BB`, `street_committed = (0.5, 1.0, 24.0, 8.0, 0, 0, 0, 0, 0)`, `remaining = (99.5, 99.0, 76.0, 92.0, 100, 100, 100, 100, 100)`, `last_raise_increment = 24.0 - 8.0 = 16.0 BB`, `raise_count = 2`, `pending = (3,)`, `history = ((3, RAISE 8.0), (4, FOLD), ..., (1, FOLD), (2, RAISE 24.0))`

6. **UTG+1 calls 24BB:** `Action("CALL", 24.0)`  
   - Payment: `24.0 - 8.0 = 16.0 BB`  
   - New state: `pot = 49.5 BB`, `street_committed = (0.5, 1.0, 24.0, 24.0, 0, 0, 0, 0, 0)`, `remaining = (99.5, 99.0, 76.0, 76.0, 100, 100, 100, 100, 100)`, `pending = ()`, `history = ((3, RAISE 8.0), ..., (2, RAISE 24.0), (3, CALL 24.0))`  
   - **Terminal:** No pending, two live seats (2, 3) with equal commitments → settlement via continuation table

---

## 7. Validation Rules & Failure Modes

### 7.1 Configuration Validation

**`MultiwayPreflopConfig.__post_init__` must enforce:**

1. `num_players` in `2..9`
2. `button` in `0..(num_players-1)`
3. `starting_stacks` length == `num_players`, all positive integers
4. `forced_posts` valid: each `ForcedPost.seat` in `0..(num_players-1)`, amounts non-negative, at least one positive BB
5. `ranges` length == `num_players`, each range non-empty tuple of `WeightedCombo`, combos unique per seat
6. `sizing_rules` non-empty tuple of `SizingRuleSet`, each with valid expressions
7. `max_raises`, `max_deals`, `max_nodes` positive integers
8. `short_all_in_reopens` boolean
9. `continuation.kind == "terminal-table"`, payoff table covers all compatible `(deal, history)` keys, values zero-sum

**Failure modes:**

- `ValueError("num_players must be 2..9")` if out of range
- `ValueError("button must be valid seat index")` if invalid
- `ValueError("starting_stacks must be positive integers")` if non-positive or wrong length
- `ValueError("forced_posts must include positive BB")` if no BB or all zero
- `ValueError("ranges must be non-empty tuples of WeightedCombo")` if empty or wrong type
- `ValueError("sizing_rules must be non-empty")` if empty
- `ValueError("continuation must be terminal-table")` if wrong kind
- `ValueError("missing continuation value for closed preflop leaf")` if payoff table incomplete

### 7.2 State Validation

**`MultiwayPreflopState.__post_init__` must enforce:**

1. `acting_player` in `{CHANCE, TERMINAL, 0..(num_players-1)}`
2. `pot == sum(total_contributed)`
3. `remaining[s] + total_contributed[s] == starting_stacks[s]` for all seats
4. `street_committed[s] <= total_contributed[s]` for all seats
5. `folded`, `pending`, `can_raise` consistent: folded seats not in pending, pending seats not folded and have `remaining > 0`, `can_raise[s] = False` if folded or all-in
6. `raise_count <= max_raises`
7. `history` valid: all `PreflopPublicAction` with `actor` in `0..(num_players-1)`
8. If `acting_player == CHANCE`: `private_deal == None`, `history == ()`, `terminal_values == None`
9. If `acting_player == TERMINAL`: `pending == ()`, `terminal_values` non-None, zero-sum
10. If `acting_player` in `0..(num_players-1)`: `private_deal` in compatible deals, `acting_player == pending[0]`

**Failure modes:**

- `ValueError("invalid acting player")` if out of range
- `ValueError("pot must equal sum(total_contributed)")` if conservation fails
- `ValueError("remaining plus contribution must equal starting stack")` if stack conservation fails
- `ValueError("street_committed must not exceed total contribution")` if violated
- `ValueError("folded or all-in seats cannot raise")` if `can_raise` inconsistent
- `ValueError("raise_count exceeds max_raises")` if over limit
- `ValueError("invalid chance root baseline")` if chance root has deal/history/values
- `ValueError("terminal state must have empty pending")` if terminal with pending
- `ValueError("terminal utility and rake conservation failed")` if not zero-sum
- `ValueError("dealt nonterminal acting player must be first pending")` if actor not pending[0]

### 7.3 Action Validation

**`legal_actions()` must return only actions satisfying:**

1. **FOLD:** Only if facing a bet (`highest_street_commitment > own`)
2. **CHECK:** Only if no bet (`own == highest`)
3. **CALL:** Target is `min(highest, own + remaining)`
4. **RAISE:** Target from `fixed_sizes(sizing_rules, context)`, legal if `highest < target <= own + remaining` and (`target >= minimum_raise_to` OR `target == own + remaining`)
5. No RAISE if `raise_count >= max_raises` or `can_raise[actor] == False`

**`child(action)` must raise `ValueError` if:**

- `action not in legal_actions()`
- `action` is not an `Action` instance
- At CHANCE, `action` not in `chance_outcomes()`

---

## 8. Public History & Information State

### 8.1 Public History

**Representation:** `history: tuple[PreflopPublicAction, ...]`  
Each entry: `PreflopPublicAction(actor: int, action: Action)`

**Ordering:** Chronological, appended on each `child(action)` call.

**Example:**  
```python
history = (
    PreflopPublicAction(2, Action("CALL", 1.0)),  # UTG limps
    PreflopPublicAction(3, Action("FOLD")),        # MP folds
    PreflopPublicAction(4, Action("RAISE", 3.0)), # CO raises to 3BB
    PreflopPublicAction(5, Action("CALL", 3.0)),  # BTN calls
    PreflopPublicAction(0, Action("FOLD")),        # SB folds
    PreflopPublicAction(1, Action("RAISE", 12.0)),# BB 3-bets to 12BB
)
```

### 8.2 Information State Key

**`information_state_key(player: int)` returns a hashable tuple uniquely identifying the player's information set:**

```python
(
    config.version,
    num_players,
    player,
    private_deal[player],  # Player's own hole cards
    button,
    forced_posts,  # Immutable tuple
    street_committed,
    total_contributed,
    remaining,
    folded,
    pending,
    can_raise,
    last_raise_increment,
    raise_count,
    acting_player,
    sizing_rules,  # Immutable tuple (or hash thereof)
    history,  # Public action sequence
)
```

**Usage:** CFR solver uses this key to aggregate regrets/strategies across game trees with identical player information.

---

## 9. Structural Bounds

### 9.1 Tree Size Estimation

**Chance outcomes:** `C = number of compatible deals <= max_deals`  
**Decision depth:** `D = num_players + max_raises * (num_players - 1)`  
**Branching factor:** `B = max(|legal_actions|) ≈ 2 (FOLD/CALL) + |sizing_rules| ≈ 5–10`  

**Worst-case nodes:** `N ≈ C * B^D`  
**Bound check:** `create_multiway_preflop_root` must verify `1 + C + estimated_decision_nodes <= max_nodes`, else raise `ValueError("node bound too small for tree expansion")`

### 9.2 Deal Enumeration

**Compatible deals:** Product of per-seat range sizes, filtered for card disjointness.  
**Bound:** `prod(len(ranges[s]) for s in range(num_players)) <= max_deals`  
**Failure:** `ValueError("candidate product exceeds max_deals")` if over limit.

### 9.3 Raise Depth

**Raise count cap:** `max_raises` (e.g., 4 for open/3-bet/4-bet/5-bet)  
**Enforcement:** `legal_actions()` returns no RAISE actions if `raise_count >= max_raises`.  
**Typical values:** 3–5 for cash games, 10+ for tournament late stages.

---

## 10. Integration with Existing Modules

### 10.1 Reuse from `preflop.py` (HU)

- `WeightedCombo` dataclass (cards, weight validation)
- `Continuation` dataclass (terminal-table payoff lookup)
- `_positive_int`, `_chips` validation helpers
- Forced post application logic (adapted for N players)
- Uncalled excess refund logic (from `game_structure.py`, already used in HU)

### 10.2 Reuse from `sizing.py`

- `validate_size_expression(expr)`
- `convert_size_to_chips(expr, context)`
- `fixed_sizes(expressions, context)` → `tuple[SizingChoice, ...]`
- `SizingChoice` dataclass (expression, target)

### 10.3 Reuse from `nplayer_postflop.py`

- `NPlayerPublicAction` pattern → `PreflopPublicAction`
- `pending` queue management (ordered responders)
- `can_raise` entitlement tracking
- `last_raise_increment` for min-raise calculation
- `raise_count` cap enforcement
- `enumerate_deals` pattern (adapted for preflop ranges)

### 10.4 Reuse from `game_structure.py`

- `ForcedPost` dataclass
- `refund_uncalled_excess(contributions)`
- `verify_terminal_conservation(initial, final, house_rake=0)`
- Integer chip accounting primitives

### 10.5 New Additive Types

- `PreflopPosition` (Literal type for position labels)
- `SizingRuleSet` (per-position, per-cold-caller sizing rules)
- `MultiwayPreflopConfig` (N-player preflop configuration)
- `MultiwayPreflopState` (N-player preflop state machine)
- `create_multiway_preflop_root(config)` factory function

---

## 11. Open Design Questions (for Implementation Wave)

1. **Position label assignment:** Should `PreflopPosition` be computed dynamically from `(num_players, button, seat)` or stored in config? **Recommendation:** Compute dynamically via helper `def assign_position(seat, button, num_players, forced_posts) -> PreflopPosition`.

2. **Sizing rule fallback:** If no exact `(position, cold_caller_count)` match, fall back to `(position, 0)` or raise error? **Recommendation:** Fall back to `(position, 0)` (default open-raise sizing), log warning if strict mode enabled.

3. **Straddle handling:** Mississippi straddle (button straddle) changes action order. Should `forced_posts` order determine first actor, or explicit `first_actor` field in config? **Recommendation:** Derive first actor as "left of rightmost straddle or BB", encoded in `forced_posts` order.

4. **Cold-caller count edge case:** If a player limps, then another player raises, is the limper a cold-caller for the raiser's sizing? **Recommendation:** Yes, limper is a cold-caller (called without opening/raising).

5. **Short all-in reopening:** Should `short_all_in_reopens` be global (config-level) or per-action (context-dependent)? **Recommendation:** Global config flag (matches existing HU `PreflopConfig.short_all_in_reopens`).

6. **Continuation table size:** For 6-max with 1326^6 deal combinations and exponential action histories, continuation table is intractable. Should S3 design require **abstracted/sampled continuations** or **postflop solver integration**? **Recommendation:** Design supports full table for small trees (HU, 3-max); implementation wave must add "continuation provider" abstraction (e.g., `continuation.get(deal, history)` with lazy evaluation or neural lookup). Mark as **S3 + S1 integration point**.

---

## 12. Summary of Contracts

### 12.1 Core Types

| Type | Module | Purpose |
|------|--------|---------|
| `Action` | `model.py` | FOLD/CHECK/CALL/RAISE/DEAL with absolute commitment amounts |
| `WeightedCombo` | `preflop.py` | Private card combo with exact rational weight |
| `Continuation` | `preflop.py` | Terminal payoff table (deal, history) → zero-sum values |
| `ForcedPost` | `game_structure.py` | Ante/blind/straddle forced contribution |
| `SizingChoice` | `sizing.py` | Expression + resolved chip target |
| `PreflopPosition` | **NEW** | Canonical position label (BTN/SB/BB/UTG/MP/CO/HJ/STRADDLE) |
| `SizingRuleSet` | **NEW** | Per-position, per-cold-caller sizing expressions |
| `PreflopPublicAction` | **NEW** | (actor, Action) public history entry |
| `MultiwayPreflopConfig` | **NEW** | Immutable 2–9 player preflop configuration |
| `MultiwayPreflopState` | **NEW** | Immutable preflop state snapshot with pending/can_raise/raise_count |

### 12.2 Key Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `create_multiway_preflop_root` | `(config) -> MultiwayPreflopState` | Factory for chance root state |
| `state.chance_outcomes` | `() -> tuple[(Action, Fraction), ...]` | Weighted deal outcomes at chance node |
| `state.legal_actions` | `() -> tuple[Action, ...]` | Legal FOLD/CHECK/CALL/RAISE for acting player |
| `state.child` | `(action) -> MultiwayPreflopState` | Immutable state transition |
| `state.information_state_key` | `(player) -> Hashable` | CFR information set key |
| `state.returns` | `() -> tuple[float, ...]` | Zero-sum payoffs at terminal |
| `assign_position` | `(seat, button, num_players, forced_posts) -> PreflopPosition` | Position label assignment |
| `count_cold_callers` | `(history, current_actor) -> int` | Count cold-callers for sizing lookup |
| `lookup_sizing_rules` | `(sizing_rules, position, cold_caller_count) -> tuple[dict, ...]` | Filter sizing expressions |

### 12.3 Validation Invariants

1. **Conservation:** `pot == sum(total_contributed)`, `remaining + total_contributed == starting_stacks`
2. **Zero-sum:** `sum(terminal_values) == 0` at TERMINAL
3. **Pending consistency:** `pending` contains only live (not folded, remaining > 0) seats, `acting_player == pending[0]` if non-terminal
4. **Raise entitlement:** `can_raise[s] == False` if `folded[s] or remaining[s] == 0`
5. **Raise count:** `raise_count <= max_raises`, no RAISE actions if at limit
6. **Street commitment:** `street_committed[s] <= total_contributed[s]` for all seats
7. **History validity:** All `PreflopPublicAction.actor` in `0..(num_players-1)`, actions match state transitions

---

## 13. Next Steps (for Implementation Wave)

1. **Implement additive types:** `PreflopPosition`, `SizingRuleSet`, `PreflopPublicAction`, `MultiwayPreflopConfig`, `MultiwayPreflopState` in new `src/poker_solver/multiway_preflop.py`
2. **Implement helper functions:** `assign_position`, `count_cold_callers`, `lookup_sizing_rules`
3. **Implement state machine:** `create_multiway_preflop_root`, `chance_outcomes`, `legal_actions`, `child`, `information_state_key`, `returns`
4. **Write unit tests:** HU trace (reuse existing HU tests as regression), 6-max trace (limps, cold-calls, 3-bet), 9-max trace (straddle), validation failures
5. **Integration tests:** Solve small HU/3-max preflop trees with vanilla CFR, verify zero-sum, determinism, continuation lookup
6. **Adversarial audit:** Fresh non-author reviewers run tests, attack edge cases (short all-in reopening, uncalled excess refund, max_raises boundary, cold-caller count off-by-one)
7. **Documentation:** Update `docs/PHASE4.md` with S3 contracts, worked examples, API reference

---

**End of S3 Preflop Betting & Sizing Design Contract**  
**UTC:** 2026-09-16 00:29 UTC  
**Reviewer:** D302 (replacement)  
**Status:** Design complete, ready for implementation wave