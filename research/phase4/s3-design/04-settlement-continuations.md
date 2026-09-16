# S3 Design: Settlement, Refunds, Continuations, and Independent Ledger Oracles

**Status:** Design specification for S3 (Phase 4 multiway postflop with explicit continuation architecture)

**Scope:** Settlement pipeline, refund mechanics, continuation contract, chip conservation, odd-chip allocation, all-in handling, and independent hand-ledger oracles for HU/6max/9max and straddle configurations.

**Exclusions:** Implementation, production code, tests, git operations, state management, progress tracking.

---

## 1. Settlement Pipeline (Reused from S2)

**Implementation location:** `game_structure.py` (already implemented and tested in S2)

**Pipeline stages:**

1. **Uncalled excess refund:** `refund_uncalled_excess(total_contributed)` → `(matched, refunds)`
   - Returns matched contributions and per-seat refund amounts
   - Refunds added to `remaining` stacks; subtracted from `street_committed`
   - **Fail-closed:** Reject negative street commitment after refund

2. **Pot layer construction:** `build_pot_layers(matched, folded=frozenset(...))`
   - Constructs exact integer side-pot layers
   - Each layer: `PotLayer(amount, contributors, eligible)`
   - **Fail-closed:** Reject all-folded layers (no eligible winners)

3. **Winner determination:**
   - **Fold-out (single live player):** Winner = lone live player for all layers, no showdown lookup
   - **Showdown (multiple live players):** Use `config.showdown_ranks[private_deal]` to determine per-layer winners
     - Best rank among `layer.eligible` wins that layer
     - Ties: multiple winners split the layer
   - **Fail-closed:** Reject missing showdown coverage for any compatible deal

4. **Rake calculation:** `calculate_rake(policy, eligible_pot, flop_seen=True)`
   - One hand-level integer rake using exact rational arithmetic
   - Respects floor/ceiling/nearest rounding, cap, minimum pot, NFND
   - **S3 constraint:** `flop_seen=True` always (postflop-only model)

5. **Rake allocation:** `allocate_rake(layers, total_rake, layer_order=policy.layer_order)`
   - Distributes rake across layers in top-down or bottom-up order
   - **Fail-closed:** Reject rake exceeding total pot

6. **Award distribution:** `award_pot_layers(layers, winners_by_layer, odd_chip_order, rake_by_layer)`
   - Awards each net layer (post-rake) by declared `odd_chip_order`
   - Remainder chips assigned to first `remainder` seats in `odd_chip_order` intersected with winners
   - **Fail-closed:** Reject winners not subset of `layer.eligible`

7. **Padding and finalization:**
   - Pad awards tuple with zeros to N seats (zero-contribution trailing seats may not appear in layers)
   - Final stack = `remaining[seat] + awards[seat]`
   - Utility = `final[seat] - starting_stacks[seat]`

8. **Conservation verification:** `verify_terminal_conservation(starting_stacks, final, house_rake=rake)`
   - **Invariant:** `sum(final) + rake == sum(starting_stacks)`
   - **Invariant:** `sum(utilities) + rake == 0` (zero-sum with house)
   - **Fail-closed:** Raise on conservation failure

**What is implemented in S3:** None (reuse existing `game_structure.py` primitives)

**What must fail closed:**
- Negative street commitment after refund
- All-folded pot layers
- Missing showdown rank coverage
- Rake exceeding pot
- Winners outside `layer.eligible`
- Chip conservation failure

---

## 2. Fold-Out vs. Closed-Leaf Settlement

### 2.1 Fold-Out Settlement (Immediate)

**Trigger:** `len(live) == 1` after a fold action

**Mechanism:**
- Winner = lone live player
- No showdown lookup required
- Settlement executes immediately in `child()` method
- All pot layers awarded to the single live player

**Example:**
```python
if len(live) == 1:
    return self._settle(**changes)  # Immediate terminal
```

### 2.2 Closed-Leaf Settlement (Pending Queue Empty)

**Trigger:** `not active_pending` (all active players have acted and street is closed)

**Mechanism:**
- Multiple live players → showdown required
- Lookup `config.showdown_ranks[private_deal]` for hand strength ranks
- Per-layer winner determination using integer rank comparison
- Settlement executes when betting round closes

**Example:**
```python
if not active_pending:
    return self._settle(**changes)  # Showdown terminal
```

**Distinction:**
- **Fold-out:** Deterministic, no showdown oracle needed
- **Closed-leaf:** Requires supplied showdown ranks for all compatible deals

---

## 3. Chip Conservation and Odd Chips

### 3.1 Chip Conservation Invariants

**Global conservation:**
```python
sum(final_stacks) + house_rake == sum(starting_stacks)
```

**Zero-sum with house:**
```python
sum(utilities) + house_rake == 0
```

**Per-seat accounting:**
```python
remaining[seat] + total_contributed[seat] == starting_stacks[seat]
```

**Enforcement:** `verify_terminal_conservation()` called at every terminal state before returning utilities

### 3.2 Odd-Chip Allocation

**Mechanism:** `award_pot_layers()` uses `odd_chip_order` to break remainder ties

**Algorithm:**
1. Compute `quotient, remainder = divmod(layer.amount - rake, len(winners))`
2. Award `quotient` to all winners
3. Award `+1` to first `remainder` seats in `odd_chip_order` that are also in `winners`

**Example:**
- Layer amount: 103 chips (post-rake)
- Winners: seats {2, 5, 7}
- `odd_chip_order = (5, 2, 7, ...)`
- Quotient: 34, remainder: 1
- Awards: seat 5 gets 35, seats 2 and 7 get 34 each

**Fail-closed:** Reject if `odd_chip_order` does not include all winners

---

## 4. All-In Handling

### 4.1 Side-Pot Construction

**Mechanism:** `build_pot_layers()` constructs layers based on contribution levels

**Algorithm:**
1. Sort unique positive contribution amounts → `levels`
2. For each level, compute:
   - `contributors = {seat | contribution[seat] >= level}`
   - `amount = (level - previous_level) * len(contributors)`
   - `eligible = contributors - folded`
3. **Fail-closed:** Reject if `eligible` is empty for any layer

**Example (4 players):**
- Contributions: [100, 50, 50, 0]
- Folded: {3}
- Levels: [50, 100]
- Layer 0: amount=150 (50×3), contributors={0,1,2}, eligible={0,1,2}
- Layer 1: amount=50 (50×1), contributors={0}, eligible={0}

### 4.2 All-In Player Eligibility

**Rule:** All-in players are eligible for layers up to their contribution level

**Implementation:** `layer.eligible` computed as `contributors - folded`

**Example:**
- Seat 1 all-in for 50 chips
- Seat 0 bets 100 chips
- Seat 1 eligible for main pot (layer 0) only
- Seat 0 eligible for both main pot and side pot (layer 1)

---

## 5. Continuation Contract for Zero-Sum Closed Leaves

### 5.1 Supplied vs. Derived Continuation

**S3 model:** Postflop-only, single betting round

**Continuation requirement:** None for natural terminals (fold-out or showdown within the modeled round)

**Future extension (multi-street):** Would require explicit continuation values at street boundaries

**Contract (if extended):**
- Continuation values must be **zero-sum**: `sum(continuation_values) == 0`
- Continuation values must be **information-set consistent**: identical for all histories in the same infoset
- Continuation values must be **supplied** via `config.continuation_table` or **derived** from a reference solve

**S3 constraint:** No continuation table needed; all leaves close within the single postflop round

### 5.2 Zero-Sum Verification

**Enforcement point:** `_settle()` method

**Check:**
```python
if sum(utilities) + house_rake != 0:
    raise ValueError("terminal utility and rake conservation failed")
```

**Tolerance:** Exact integer arithmetic; no floating-point drift

---

## 6. Independent Hand-Ledger Oracles

### 6.1 Purpose

Independent oracles verify settlement correctness by computing expected final stacks from first principles, without relying on the production `game_structure.py` implementation.

### 6.2 Oracle Specification

**Input:**
- `starting_stacks: tuple[int, ...]`
- `forced_posts: tuple[ForcedPost, ...]`
- `action_sequence: tuple[Action, ...]`
- `showdown_ranks: tuple[int, ...]` (if showdown reached)
- `rake_policy: RakePolicy | None`
- `odd_chip_order: tuple[int, ...]`

**Output:**
- `final_stacks: tuple[int, ...]`
- `house_rake: int`
- `utilities: tuple[int, ...]`

**Algorithm:**
1. Apply forced posts → initial ledgers
2. Process each action:
   - FOLD: mark seat as folded
   - CHECK: no state change
   - CALL: transfer chips from remaining to street_committed and total_contributed
   - RAISE: transfer chips, update highest commitment
3. At terminal:
   - Refund uncalled excess
   - Build pot layers
   - Determine winners (fold-out or showdown)
   - Calculate and allocate rake
   - Award layers with odd-chip tiebreaker
   - Verify conservation

**Independence:** Oracle implemented in a separate module (e.g., `tests/oracles/hand_ledger.py`) using only Python stdlib and explicit arithmetic, **not** importing `game_structure.py`.

### 6.3 HU (Heads-Up) Oracle

**Configuration:**
- 2 players
- Button posts small blind, other seat posts big blind
- Single betting round (flop/turn/river)
- Finite raise count

**Test cases:**
- Fold preflop → BB wins SB post
- All-in call → showdown with exact pot split or winner-take-all
- Raise-fold → raiser wins pot
- Uncalled excess refund when short stack calls all-in

**Oracle fixture:** `oracle_hu_ledger(starting_stacks, posts, actions, ranks, rake_policy, odd_chip_order)`

### 6.4 6-Max Oracle

**Configuration:**
- 6 players
- Standard blind structure: SB, BB, optional straddle
- Multiple all-in scenarios creating 2-3 side pots
- Rake with cap and minimum pot

**Test cases:**
- 3-way all-in with distinct contribution levels
- Fold cascade leaving 2 players
- Tie on main pot, distinct winner on side pot
- Odd-chip allocation with 3-way split

**Oracle fixture:** `oracle_6max_ledger(...)`

### 6.5 9-Max Oracle

**Configuration:**
- 9 players
- Full ring blind structure
- All-in cascade creating 4+ side pots
- Rake with top-down allocation

**Test cases:**
- 5-way all-in with distinct contribution levels
- Fold-out after 4 folds
- Showdown with 3 live players, 2-way tie on main pot
- Maximum side-pot depth

**Oracle fixture:** `oracle_9max_ledger(...)`

### 6.6 Straddle Hand-Ledger Oracle

**Configuration:**
- 6 or 9 players
- Straddle post (2× BB or 3× BB)
- Action order: UTG first (after straddle)
- Straddle has option to raise when action returns

**Test cases:**
- Straddle folds to raise
- Straddle raises when checked to
- All-in over straddle
- Uncalled straddle refund

**Oracle fixture:** `oracle_straddle_ledger(...)`

### 6.7 Oracle Test Strategy

**Approach:**
1. Generate 10-20 hand scenarios per configuration (HU/6max/9max/straddle)
2. Compute expected final stacks using independent oracle
3. Run same scenario through production `NPlayerPostflopState._settle()`
4. Assert exact integer equality: `production_final == oracle_final`
5. Assert conservation: `sum(production_final) + rake == sum(starting_stacks)`

**Failure mode:** Any discrepancy indicates a bug in production settlement or oracle

**Test location:** `tests/test_s3_settlement_oracles.py`

---

## 7. What Is Implemented in S3 vs. Reused

### 7.1 Reused from Existing Modules

**From `game_structure.py` (S1/S2):**
- `ForcedPost`, `SeatLedger`, `GameStructure`, `PotLayer`, `RakePolicy` (immutable types)
- `apply_forced_posts()`
- `refund_uncalled_excess()`
- `build_pot_layers()`
- `calculate_rake()`
- `allocate_rake()`
- `award_pot_layers()`
- `verify_terminal_conservation()`

**From `nplayer_postflop.py` (S2):**
- `NPlayerPostflopConfig`, `NPlayerPostflopState`, `NPlayerPublicAction`
- `enumerate_deals()`
- `create_nplayer_postflop_root()`
- `solve_nplayer_postflop()`
- Betting logic: `legal_actions()`, `child()`, `_settle()`
- Information-set keys: `information_state_key()`, `information_state_string()`

**From `icm.py` (S1):**
- `calculate_icm_equity()` (not directly used in S3, but available for tournament extensions)

**From `preflop.py` (S1):**
- `WeightedCombo`, `Continuation`, `PreflopConfig`, `PreflopState` (reference for continuation contract design)

### 7.2 New in S3 (Design Only)

**Settlement design clarifications:**
- Explicit fold-out vs. closed-leaf distinction
- Forced-post ledger initialization for multiway games
- Showdown rank oracle contract for N-player games
- Rake integration with multiway side pots

**Independent oracle specifications:**
- HU/6max/9max/straddle hand-ledger oracles
- Oracle test strategy and acceptance criteria
- Independence requirement (no `game_structure.py` imports)

**Continuation contract (future-proofing):**
- Zero-sum requirement
- Information-set consistency requirement
- Supplied vs. derived continuation values

### 7.3 What Must Fail Closed (Comprehensive List)

**Configuration validation:**
- Invalid `num_players` (not in 2..9)
- Invalid `button` (not in seats)
- Contribution exceeds starting stack
- Initial pot non-positive
- Fewer than 2 live players initially
- Invalid board (not 3/4/5 unique cards in 0..51)
- Range combos collide with board
- Unmatched initial contributions (uncalled excess at root)
- Missing showdown rank coverage for any compatible deal
- Duplicate showdown deals
- Invalid rake policy (rate > 1, negative cap/minimum)

**Runtime validation:**
- Illegal action (not in `legal_actions()`)
- Negative street commitment after refund
- All-folded pot layer (no eligible winners)
- Winners not subset of `layer.eligible`
- Rake exceeds total pot
- Chip conservation failure at terminal
- Zero-sum failure: `sum(utilities) + rake != 0`
- Missing showdown ranks when showdown reached
- Invalid rank vector (wrong dimension, bool ranks)

**Information-set consistency:**
- Continuation values differ for histories in the same infoset (future extension)
- Private deal not in compatible deal set
- Acting player not in `pending[0]` for dealt nonterminal states

---

## 8. Exact Forced-Post, Refund, Pot, Side-Pot, and Rake Ledgers

### 8.1 Forced-Post Ledger

**Input:** `starting_stacks`, `forced_posts`

**Output:** `tuple[SeatLedger, ...]`

**Algorithm:** `apply_forced_posts(starting_stacks, forced_posts)`

**Example (6-max with straddle):**
```python
starting_stacks = (1000, 1000, 1000, 1000, 1000, 1000)
forced_posts = (
    ForcedPost(seat=0, kind="small-blind", amount=5),
    ForcedPost(seat=1, kind="big-blind", amount=10),
    ForcedPost(seat=2, kind="straddle", amount=20),
)
ledgers = apply_forced_posts(starting_stacks, forced_posts)
# ledgers[0]: starting=1000, remaining=995, street_committed=5, total_contributed=5, folded=False, all_in=False
# ledgers[1]: starting=1000, remaining=990, street_committed=10, total_contributed=10, folded=False, all_in=False
# ledgers[2]: starting=1000, remaining=980, street_committed=20, total_contributed=20, folded=False, all_in=False
# ledgers[3..5]: starting=1000, remaining=1000, street_committed=0, total_contributed=0, folded=False, all_in=False
```

### 8.2 Refund Ledger

**Input:** `total_contributed` (after all actions)

**Output:** `(matched, refunds)`

**Algorithm:** `refund_uncalled_excess(total_contributed)`

**Example (short-stack all-in call):**
```python
total_contributed = (100, 50, 0, 0)  # Seat 0 raised to 100, seat 1 called all-in for 50
matched, refunds = refund_uncalled_excess(total_contributed)
# matched = (50, 50, 0, 0)
# refunds = (50, 0, 0, 0)  # Seat 0 gets 50 chips back
```

### 8.3 Pot and Side-Pot Ledger

**Input:** `matched` contributions, `folded` set

**Output:** `tuple[PotLayer, ...]`

**Algorithm:** `build_pot_layers(matched, folded=folded_set)`

**Example (3-way all-in):**
```python
matched = (100, 50, 30, 0)
folded = frozenset({3})
layers = build_pot_layers(matched, folded=folded)
# Layer 0: amount=120 (30×4), contributors={0,1,2,3}, eligible={0,1,2}
# Layer 1: amount=40 (20×2), contributors={0,1}, eligible={0,1}
# Layer 2: amount=50 (50×1), contributors={0}, eligible={0}
```

### 8.4 Rake Ledger

**Input:** `rake_policy`, `eligible_pot`, `flop_seen=True`

**Output:** `total_rake: int`

**Algorithm:** `calculate_rake(policy, eligible_pot, flop_seen=True)`

**Example (5% rake, $5 cap, $10 minimum, floor rounding):**
```python
policy = RakePolicy(
    rate_numerator=5,
    rate_denominator=100,
    cap=500,  # $5 in cents
    minimum_pot=1000,  # $10 in cents
    no_flop_no_drop=True,
    rounding="floor",
    layer_order="top-down",
)
rake = calculate_rake(policy, eligible_pot=5000, flop_seen=True)
# rake = 250 (5% of 5000, capped at 500, floor rounding)
```

### 8.5 Rake Allocation Ledger

**Input:** `layers`, `total_rake`, `layer_order`

**Output:** `tuple[int, ...]` (rake per layer)

**Algorithm:** `allocate_rake(layers, total_rake, layer_order=policy.layer_order)`

**Example (top-down allocation):**
```python
layers = (
    PotLayer(amount=300, contributors=frozenset({0,1,2}), eligible=frozenset({0,1,2})),
    PotLayer(amount=200, contributors=frozenset({0,1}), eligible=frozenset({0,1})),
)
total_rake = 150
rake_by_layer = allocate_rake(layers, total_rake, layer_order="top-down")
# rake_by_layer = (150, 0)  # All rake from top layer
```

### 8.6 Award Ledger

**Input:** `layers`, `winners_by_layer`, `odd_chip_order`, `rake_by_layer`

**Output:** `tuple[int, ...]` (awards per seat)

**Algorithm:** `award_pot_layers(layers, winners_by_layer, odd_chip_order, rake_by_layer)`

**Example (3-way tie with odd chip):**
```python
layers = (PotLayer(amount=103, contributors=frozenset({0,1,2}), eligible=frozenset({0,1,2})),)
winners_by_layer = (frozenset({0,1,2}),)
odd_chip_order = (1, 0, 2)
rake_by_layer = (0,)
awards = award_pot_layers(layers, winners_by_layer=winners_by_layer, odd_chip_order=odd_chip_order, rake_by_layer=rake_by_layer)
# awards = (34, 35, 34)  # Seat 1 gets the odd chip (first in odd_chip_order among winners)
```

---

## 9. Summary and Acceptance Criteria

### 9.1 Design Completeness

**Specified:**
- ✅ Settlement pipeline (8 stages, all primitives identified)
- ✅ Fold-out vs. closed-leaf distinction
- ✅ Chip conservation invariants (global, zero-sum, per-seat)
- ✅ Odd-chip allocation algorithm
- ✅ All-in side-pot construction and eligibility
- ✅ Continuation contract (zero-sum, information-set consistency)
- ✅ Independent oracle specifications (HU/6max/9max/straddle)
- ✅ Exact ledger examples (forced-post, refund, pot, rake, award)
- ✅ Fail-closed requirements (comprehensive list)
- ✅ Reused vs. new components (clear boundaries)

### 9.2 Implementation Boundaries

**S3 design scope:**
- Settlement mechanics clarification
- Oracle test strategy
- Continuation contract specification

**S3 implementation scope (future):**
- Independent oracle modules (`tests/oracles/hand_ledger.py`)
- Oracle test suite (`tests/test_s3_settlement_oracles.py`)
- Integration tests for HU/6max/9max/straddle configurations

**Out of scope for S3:**
- Production code changes (all primitives already implemented in S1/S2)
- Multi-street continuation (deferred to future phase)
- Tournament ICM integration (deferred)

### 9.3 Acceptance Criteria

**Design acceptance:**
- ✅ All settlement stages specified with exact primitives
- ✅ All fail-closed conditions enumerated
- ✅ Independent oracle contract defined
- ✅ Reused vs. new components clearly separated
- ✅ Exact ledger examples provided for each stage

**Implementation acceptance (future):**
- All oracle tests pass with exact integer equality
- All conservation checks pass at every terminal
- All fail-closed conditions trigger appropriate exceptions
- No production code changes required (primitives already correct)

---

**End of S3 settlement, refunds, continuations, and independent ledger oracle design.**
