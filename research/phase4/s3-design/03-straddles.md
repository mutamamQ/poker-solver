# S3 Straddle Variants and Forced-Action Order

## Design status

**Reviewer:** D303  
**Scope:** Design-only specification for standard UTG, double, and Mississippi straddles across HU/6-max/9-max configurations.  
**Constraints:** Read-only on production/tests/git/state/progress. Exclusive write to this file and `.hb/D303`.

## Evidence base

From `research/phase3/game-structure-rake.md` lines 27–30:

> GTO Wizard's public custom-solution documentation says its preflop builder exposes:
> - single, double, and Mississippi straddles;
>
> The same page describes a single straddle as UTG posting with action beginning at UTG+1; double as UTG and UTG+1 posting with action at UTG+2; and Mississippi as a configured non-blind straddler with action beginning to that player's left.

From `PHASE4_MISSION.md` line 19:

> Preflop tree builder: positions, blinds/antes/straddles (standard, double, Mississippi), limps, SB completes, cold-calls, 3-bet/4-bet/5-bet+ sizing rules per position (IP/OOP, per cold-caller), custom stacks per player, finite weighted deals.

From `PHASE4_MISSION.md` line 20:

> **Acceptance:** HU + 6-max + 9-max preflop spots solve with the sizing rules above; forced-post/refund ledgers exact; raise-to street commitment honored; straddle variants produce distinct, verifiable trees; zero-sum on closed leaves with supplied/derived continuations.

From `research/phase3/game-structure-rake.md` lines 69–70:

> Blind and straddle postings are likewise `min(required, remaining_stack)`. A straddle is an explicit `(seat, amount)` entry; the public product labels do not justify hard-coding every straddle to twice the preceding blind.

From `research/phase3/game-structure-rake.md` lines 73–76:

> For no straddle in a game of three or more players, preflop action begins with the first active seat clockwise after the BB. In heads-up, the button/SB acts first preflop. Postflop action begins with the first active non-all-in seat clockwise after the button.
>
> With configured straddles, preflop action begins with the first eligible seat clockwise after the final straddler; that straddler retains its option when action returns, subject to normal closing/reopening rules.

Existing implementation in `src/poker_solver/game_structure.py` lines 13–17:

```python
@dataclass(frozen=True)
class ForcedPost:
    """Immutable forced contribution: ante, small-blind, big-blind, or straddle."""
    seat: int
    kind: Literal["ante", "small-blind", "big-blind", "straddle"]
    amount: int
```

The `GameStructure` dataclass (lines 51–83) already accepts `forced_posts: tuple[ForcedPost, ...]` and validates seat membership.

## Straddle variant specifications

### 1. Standard UTG straddle (single straddle)

**Eligibility:** The UTG seat (first seat clockwise after BB) may post a straddle.  
**Posting order:** SB → BB → UTG straddle, all before any voluntary action.  
**Amount:** Explicit caller-supplied integer; common convention is 2×BB but not enforced.  
**Button/blind interaction:** Button and blinds post normally; straddle is an additional forced post.  
**First preflop actor:** First active seat clockwise after UTG (UTG+1 in full ring, or wraps to SB/BB if fewer seats).  
**Action wrap order:** Clockwise from first actor; UTG retains option when action returns unopened or at the straddle amount.  
**Multiple straddles:** Not applicable (single straddle only).  
**Short-stack forced all-ins:** Straddle debits `min(straddle_amount, remaining_stack[UTG])` after blinds posted.  
**Dead/live posts:** All straddles are live (straddler has option to raise when action returns).  
**Validation:** UTG seat must exist; straddle amount > 0; UTG stack after blind/ante posts must be ≥ 0.

#### Concrete seat-index examples

**6-max (seats 0–5, button=0):**
- Button=0, SB=1, BB=2, UTG=3, UTG+1=4, UTG+2=5.
- Forced posts: `ForcedPost(1, "small-blind", 50)`, `ForcedPost(2, "big-blind", 100)`, `ForcedPost(3, "straddle", 200)`.
- First actor: seat 4 (UTG+1).
- Action order: 4 → 5 → 0 → 1 → 2 → 3 (UTG option).

**9-max (seats 0–8, button=4):**
- Button=4, SB=5, BB=6, UTG=7, UTG+1=8, UTG+2=0, …
- Forced posts: `ForcedPost(5, "small-blind", 50)`, `ForcedPost(6, "big-blind", 100)`, `ForcedPost(7, "straddle", 200)`.
- First actor: seat 8 (UTG+1).
- Action order: 8 → 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 (UTG option).

**Heads-up (seats 0–1, button=0):**
- Button/SB=0, BB=1.
- UTG does not exist in HU; standard UTG straddle is **invalid** for HU.
- Validation must reject UTG straddle when `len(seats) == 2`.

### 2. Double straddle

**Eligibility:** UTG and UTG+1 both post straddles.  
**Posting order:** SB → BB → UTG straddle → UTG+1 straddle, all before voluntary action.  
**Amounts:** Two explicit caller-supplied integers; common convention UTG=2×BB, UTG+1=4×BB, but not enforced.  
**Button/blind interaction:** Button and blinds post normally; straddles are additional forced posts.  
**First preflop actor:** First active seat clockwise after UTG+1 (UTG+2 in full ring, or wraps).  
**Action wrap order:** Clockwise from first actor; UTG+1 retains final option, then UTG retains option if action returns at UTG straddle amount after UTG+1 acts.  
**Multiple straddles:** Exactly two straddle posts (UTG, UTG+1).  
**Short-stack forced all-ins:** Each straddle debits `min(amount, remaining_stack)` after all prior forced posts.  
**Dead/live posts:** Both straddles are live; UTG+1 has option first, UTG second.  
**Validation:** UTG and UTG+1 seats must exist; both amounts > 0; UTG+1 amount ≥ UTG amount (caller responsibility, not enforced by engine but documented as expected); stacks sufficient.

#### Concrete seat-index examples

**6-max (seats 0–5, button=0):**
- Button=0, SB=1, BB=2, UTG=3, UTG+1=4, UTG+2=5.
- Forced posts: `ForcedPost(1, "small-blind", 50)`, `ForcedPost(2, "big-blind", 100)`, `ForcedPost(3, "straddle", 200)`, `ForcedPost(4, "straddle", 400)`.
- First actor: seat 5 (UTG+2).
- Action order: 5 → 0 → 1 → 2 → 3 (UTG option) → 4 (UTG+1 option).

**9-max (seats 0–8, button=4):**
- Button=4, SB=5, BB=6, UTG=7, UTG+1=8, UTG+2=0.
- Forced posts: `ForcedPost(5, "small-blind", 50)`, `ForcedPost(6, "big-blind", 100)`, `ForcedPost(7, "straddle", 200)`, `ForcedPost(8, "straddle", 400)`.
- First actor: seat 0 (UTG+2).
- Action order: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 (UTG option) → 8 (UTG+1 option).

**Heads-up:** Invalid (UTG does not exist).

**3-max (seats 0–2, button=0):**
- Button=0, SB=1, BB=2, UTG=0 (button is UTG in 3-max).
- UTG+1=1 (SB).
- Double straddle would require button and SB to straddle; this is **valid** but unusual.
- Forced posts: `ForcedPost(1, "small-blind", 50)`, `ForcedPost(2, "big-blind", 100)`, `ForcedPost(0, "straddle", 200)`, `ForcedPost(1, "straddle", 400)`.
- SB posts blind 50, then straddle 400 (total 450 from SB).
- First actor: seat 2 (BB, who is UTG+2 in this wrap).
- Action order: 2 → 0 (button/UTG option) → 1 (SB/UTG+1 option).

### 3. Mississippi straddle

**Eligibility:** Any single non-blind seat specified by caller (not restricted to UTG).  
**Posting order:** SB → BB → Mississippi straddle (order among multiple forced posts is declaration order).  
**Amount:** Explicit caller-supplied integer.  
**Button/blind interaction:** Button and blinds post normally; Mississippi straddle is independent.  
**First preflop actor:** First active seat clockwise after the Mississippi straddler.  
**Action wrap order:** Clockwise from first actor; Mississippi straddler retains option when action returns.  
**Multiple straddles:** Only one Mississippi straddle per hand (multiple Mississippi straddles would require explicit ordering and option rules; out of scope for Phase 4 S3).  
**Short-stack forced all-ins:** Straddle debits `min(amount, remaining_stack)` after prior forced posts.  
**Dead/live posts:** Live (straddler has option).  
**Validation:** Straddler seat must not be SB or BB (Mississippi straddle is a non-blind straddle); amount > 0; stack sufficient.

#### Concrete seat-index examples

**6-max (seats 0–5, button=2, Mississippi straddler=5):**
- Button=2, SB=3, BB=4, Mississippi=5.
- Forced posts: `ForcedPost(3, "small-blind", 50)`, `ForcedPost(4, "big-blind", 100)`, `ForcedPost(5, "straddle", 300)`.
- First actor: seat 0 (first seat clockwise after 5).
- Action order: 0 → 1 → 2 → 3 → 4 → 5 (Mississippi option).

**9-max (seats 0–8, button=4, Mississippi straddler=0):**
- Button=4, SB=5, BB=6, Mississippi=0 (UTG+2 position).
- Forced posts: `ForcedPost(5, "small-blind", 50)`, `ForcedPost(6, "big-blind", 100)`, `ForcedPost(0, "straddle", 250)`.
- First actor: seat 1 (first seat clockwise after 0).
- Action order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 0 (Mississippi option).

**Heads-up (seats 0–1, button=0, Mississippi straddler=0):**
- Button/SB=0, BB=1.
- Mississippi=0 (button straddles).
- Forced posts: `ForcedPost(0, "small-blind", 50)`, `ForcedPost(1, "big-blind", 100)`, `ForcedPost(0, "straddle", 200)`.
- Button posts SB 50 + straddle 200 = 250 total.
- First actor: seat 1 (BB, first clockwise after button).
- Action order: 1 → 0 (button/Mississippi option).
- **Note:** In HU, button acts first preflop normally, but with a Mississippi straddle on the button, BB acts first and button retains option. This is valid and distinct from no-straddle HU.

**Validation edge case:** Mississippi straddler cannot be SB or BB (those seats already have forced blind posts; a straddle on top of a blind is a distinct concept and requires separate design). For Phase 4 S3, **reject** Mississippi straddle if `straddler_seat == SB_seat or straddler_seat == BB_seat`.

## Forced-action order algorithm

### Preflop first-actor determination

1. **No straddles:**
   - HU: button (seat with SB) acts first.
   - 3+ players: first active seat clockwise after BB.

2. **With straddle(s):**
   - Identify the **final straddler** (last straddle in posting order, which is the last `ForcedPost` with `kind="straddle"` in the `forced_posts` tuple).
   - First actor: first active seat clockwise after final straddler.
   - If final straddler is all-in or folded (impossible preflop, but for generality), skip to next active seat.

3. **Clockwise traversal:**
   - Given button seat `b` and total seats `n`, seat order is `(b+1) % n, (b+2) % n, ..., b`.
   - "First active seat clockwise after seat `s`" means the first seat in `(s+1) % n, (s+2) % n, ...` that is not folded and not all-in (preflop: all seats active unless short-stacked to zero after forced posts).

### Action wrap and option retention

- Action proceeds clockwise from first actor.
- A player "has option" if they posted a live straddle and action returns to them unopened (all others folded or called to the straddle amount) or at exactly the straddle amount.
- When action returns to a straddler at their straddle amount and they have not yet acted voluntarily, they may check (close action) or raise.
- If multiple straddles exist (double straddle), the **outermost** (last/largest) straddler has option first, then the next inner straddler if action returns at their amount.
- Standard action-closing rules apply: action closes when all non-folded, non-all-in players have acted since the last full raise and all have matched the current highest commitment or folded.

### Short-stack forced all-ins

- If a player's stack after prior forced posts is less than a required straddle, they post `min(straddle_amount, remaining_stack)` and are marked all-in.
- An all-in straddle is still a live post (the player retains option if action returns), but the player cannot raise further.
- If a straddler is all-in for less than the declared straddle amount, the "live amount" for option purposes is the amount they actually posted, not the declared amount.
- First actor determination: if the final straddler is all-in, first actor is still the next seat clockwise (all-in players are skipped in action order but not in determining the starting point).

## Tree evidence and acceptance oracles

### Distinct tree verification

Each straddle variant must produce a **distinct, deterministic game tree** that differs observably from the others and from no-straddle configurations.

**Observable differences:**

1. **Forced-post ledger:** After forced posts applied, `SeatLedger.street_committed` and `SeatLedger.remaining` must reflect the straddle amounts exactly.
2. **Pot size at first decision:** No straddle (6-max, SB=50, BB=100) → pot=150. Standard UTG straddle (+200) → pot=350. Double straddle (+200+400) → pot=750. Mississippi straddle (button, +300) → pot=450.
3. **First actor seat:** No straddle (6-max, BTN=0) → first actor=3 (UTG). Standard UTG straddle → first actor=4 (UTG+1). Double straddle → first actor=5 (UTG+2). Mississippi on button → first actor=1 (SB).
4. **Action sequence length:** With straddle option, an unopened pot requires one additional decision (straddler's option) before closing.
5. **Information-set count:** Straddle configurations produce distinct information sets due to different pot sizes and action histories.

**Deterministic tree oracle:**

Given a fixed configuration (seats, button, stacks, blinds, straddles, ranges, sizing rules), the preflop tree builder must produce:

- Identical node count, edge count, and information-set count across repeated builds with the same seed.
- Identical first-actor seat and action order.
- Identical forced-post ledger (exact integer amounts per seat).
- Zero-sum terminal payoffs when supplied continuations are zero-sum.

**Acceptance test template:**

```python
def test_straddle_tree_distinct():
    # 6-max, BTN=0, stacks=10000, SB=50, BB=100
    base_config = {"seats": 6, "button": 0, "stacks": [10000]*6, "sb": 50, "bb": 100}
    
    # No straddle
    tree_none = build_preflop_tree(**base_config, straddles=[])
    assert tree_none.first_actor == 3  # UTG
    assert tree_none.pot_at_root == 150
    
    # Standard UTG straddle
    tree_single = build_preflop_tree(**base_config, straddles=[(3, 200)])
    assert tree_single.first_actor == 4  # UTG+1
    assert tree_single.pot_at_root == 350
    assert tree_single.node_count != tree_none.node_count
    
    # Double straddle
    tree_double = build_preflop_tree(**base_config, straddles=[(3, 200), (4, 400)])
    assert tree_double.first_actor == 5  # UTG+2
    assert tree_double.pot_at_root == 750
    assert tree_double.node_count != tree_single.node_count
    
    # Mississippi on button
    tree_miss = build_preflop_tree(**base_config, straddles=[(0, 300)])
    assert tree_miss.first_actor == 1  # SB
    assert tree_miss.pot_at_root == 450
    assert tree_miss.node_count != tree_none.node_count
    
    # All trees deterministic
    tree_single_repeat = build_preflop_tree(**base_config, straddles=[(3, 200)])
    assert tree_single.node_count == tree_single_repeat.node_count
    assert tree_single.infoset_count == tree_single_repeat.infoset_count
```

**Zero-sum oracle:**

For every terminal node in the preflop tree (fold, all-in, or closed action leading to supplied continuation):

```python
sum(player_payoffs) == -house_rake  # or == 0 if no rake
```

If continuations are supplied as zero-sum, the preflop tree's terminal payoffs must also be zero-sum (or sum to `-rake` if rake is applied at the preflop stage, though typically rake is applied postflop).

**Forced-post ledger oracle:**

After `apply_forced_posts(starting_stacks, forced_posts)` with straddles included:

```python
for seat in seats:
    assert ledger[seat].starting_stack == starting_stacks[seat]
    assert ledger[seat].remaining + ledger[seat].street_committed == starting_stacks[seat]
    assert ledger[seat].total_contributed == ledger[seat].street_committed  # preflop, no prior streets

# Straddle seats have non-zero street_committed beyond blinds
for post in forced_posts:
    if post.kind == "straddle":
        expected = min(post.amount, starting_stacks[post.seat] - prior_posts_at_seat)
        assert ledger[post.seat].street_committed >= expected
```

**Raise-to commitment oracle:**

When a player raises to amount `R`, their `street_committed` becomes `R` (total-to semantics), not `R + prior_committed`. The tree builder must use:

```python
additional_payment = max(0, raise_target - current_committed[player])
actual_payment = min(additional_payment, remaining_stack[player])
```

This prevents double-counting the straddle post when a straddler raises.

## Implementation notes for tree builder

1. **Extend `GameStructure.forced_posts`:** Already supports `tuple[ForcedPost, ...]` with `kind="straddle"`. No schema change needed.

2. **First-actor logic:** In the preflop tree builder, replace hard-coded "first actor = UTG" with:
   ```python
   straddle_posts = [p for p in forced_posts if p.kind == "straddle"]
   if straddle_posts:
       final_straddler_seat = straddle_posts[-1].seat  # last in posting order
       first_actor = next_active_seat_after(final_straddler_seat, button, seats)
   else:
       if len(seats) == 2:
           first_actor = button  # HU: button acts first
       else:
           bb_seat = [p.seat for p in forced_posts if p.kind == "big-blind"][0]
           first_actor = next_active_seat_after(bb_seat, button, seats)
   ```

3. **Option retention:** Track `has_option` per player. A straddler has option if:
   - They posted a live straddle.
   - Action returns to them with `current_highest_commitment == their_straddle_amount`.
   - They have not yet acted voluntarily this street.
   
   When action reaches a player with option at their straddle amount, they may check (close) or raise. If they check, action closes only if all others have acted and matched.

4. **Multiple straddles (double):** Process in posting order. Each straddle debits after the prior. The last straddle in the list is the final straddler for first-actor purposes. Option order: last straddler has option first, then prior straddlers if action returns at their amounts.

5. **Validation:**
   - Standard/double straddle: UTG and UTG+1 seats must exist (reject if `len(seats) < 3` for standard, `< 4` for double, adjusted for button position).
   - Mississippi: straddler seat must not be SB or BB.
   - All straddle amounts > 0.
   - Stacks sufficient after all forced posts (if not, player is all-in but hand proceeds).

6. **Testing priority:**
   - HU with no straddle (baseline).
   - HU with Mississippi on button (distinct tree).
   - 6-max with no straddle, standard UTG, double, Mississippi on button, Mississippi on CO.
   - 9-max with standard UTG, double.
   - Short-stack cases: UTG has 150 chips, BB=100, straddle=200 → UTG posts 150 and is all-in.
   - Zero-sum verification on all terminal nodes.
   - Determinism: same config → same tree (node count, infoset count, first actor).

## Boundary and out-of-scope

**In scope for Phase 4 S3:**
- Standard UTG straddle (single).
- Double straddle (UTG + UTG+1).
- Mississippi straddle (any non-blind seat, single).
- Exact forced-post accounting.
- Correct first-actor determination and action wrap.
- Distinct, deterministic trees with verification oracles.

**Out of scope (document as future extensions):**
- Triple or unlimited straddles.
- Multiple simultaneous Mississippi straddles.
- "Sleeper" straddles (posted out of turn, conditional on no raise).
- Button straddle in full-ring games (distinct from Mississippi; some rooms allow button to straddle in addition to blinds).
- Straddle amount restrictions (e.g., must be exactly 2×BB; current design allows any positive integer).
- Straddle eligibility restrictions (e.g., some rooms require UTG to act first even with a straddle; current design follows GTO Wizard's public description).
- Interaction with limps and cold-calls (separate S3 design document).
- Postflop straddles (not a real poker concept; straddles are preflop only).

## References

- GTO Wizard custom solutions help page: https://help.gtowizard.com/how-to-build-custom-solutions/
- `research/phase3/game-structure-rake.md` (forced-post accounting contract)
- `src/poker_solver/game_structure.py` (existing `ForcedPost` and `GameStructure` schema)
- `PHASE4_MISSION.md` S3 acceptance criteria (line 20)
