# D202 — Generic 2–9-player one-round postflop betting state

## Contract

Add a sibling generic implementation; do not change the two-player `GameState`,
`Action`, or the public 3-player constructors.  The new constructor is
`create_nplayer_root(config)` and accepts `N = len(config.starting_stacks)` with
`2 <= N <= 9`.  A postflop config has a fixed board, ordered seats
`0..N-1`, button, explicit weighted private ranges, baseline contributions,
fold flags, absolute raise-to targets, `max_raises`, `max_deals`, `max_nodes`,
odd-chip order, and showdown ranks.  All per-seat fields have length `N`.

This is one finite betting round.  There is no automatic turn/river chance
transition here: after betting closes, settle against the configured board and
showdown ranks (or award immediately when one live player remains).

Statuses are derived, avoiding contradictory duplicate state:

```text
FOLDED  := folded[i]
ALL_IN  := not folded[i] and remaining[i] == 0
ACTIVE  := not folded[i] and remaining[i] > 0
```

`total_contributed[i]` includes the baseline contribution and all payments in
this round; `street_committed[i]` starts at zero for this postflop round.
`pot` is the current ledger, including dead money.

## Immutable state and exact invariants

`NPlayerPostflopState` is frozen and contains at least:

```text
config, private_deal, acting_player
pot, street_committed[N], total_contributed[N], remaining[N]
folded[N], pending[tuple[int,...]], can_raise[N]
last_raise_increment, raise_count
history[tuple[PublicAction,...]], terminal_values[N] | None, house_rake
```

`PublicAction` is `(actor, Action)` (or an equivalent frozen record); actor
identity is never inferred away in the generic public history.  The legacy
3-player state may retain its old `Action`-only history.

Validate every constructed state, including children:

1. `N` is an integer in `[2, 9]`; every stack is a positive integer; every
   contribution is an integer in `[0, starting_stack[i]]`; at least two seats
   are nonfolded at the root.  Cards are integer, unique within the board and
   across a dealt private assignment; range products contain only compatible
   deals.
2. `pot >= 0`, `remaining[i] >= 0`, `total_contributed[i] >= 0`, and
   `street_committed[i] >= 0` are integers.  Always:
   `remaining[i] + total_contributed[i] == starting_stacks[i]` and
   `street_committed[i] <= total_contributed[i]` for every seat.
3. Before settlement, exactly:
   `pot == sum(total_contributed)`.  Settlement may refund unmatched excess;
   after refund, replace both `total_contributed` and `pot` with the matched
   ledger and add each refund to that player's `remaining`.
4. `pending` is a duplicate-free tuple containing exactly seats that are
   `ACTIVE` and still owe a response to the current live high-water mark.
   Folded and all-in seats never occur in `pending`.  A dealt nonterminal state
   has `acting_player in pending`; `pending == ()` is immediately terminal.
5. Let `L = {i: not folded[i]}` and
   `H = max(street_committed[i] for i in L)`.  For an acting seat `p`,
   `to_call = max(0, H - street_committed[p])`.  `H` and `to_call` are derived,
   not independently mutable.  The initial `pending` is all `ACTIVE` seats,
   ordered clockwise after the button; the initial actor is the first of them.
6. `can_raise[i]` is false for folded/all-in seats.  It means “raising remains
   entitled if this seat is later reopened,” not that a raise is currently
   affordable.  It is additionally gated by `raise_count < max_raises` and
   `remaining[i] > to_call` when legal actions are generated.
7. `last_raise_increment > 0`; it changes only on a full raise.  `raise_count`
   counts every `RAISE`, including a short all-in raise, and is in
   `[0, max_raises]`.  A call that consumes the stack is an all-in call, not a
   raise and does not change the increment.
8. `history` is immutable, ordered, and records every public action including
   actor; all action amounts are integer absolute street commitment targets.
9. Root has `acting_player == CHANCE`, no deal/history/terminal values, and
   `pot == sum(config.contributions)`.  A dealt nonterminal has a compatible
   deal, no terminal settlement, and a valid acting seat.  Terminal has
   `acting_player == TERMINAL`, `pending == ()`, exactly `N` utility values,
   and `sum(terminal_values) == -house_rake` exactly.
10. Chance outcomes are deterministic, finite, nonnegative, blocker-filtered,
    normalized once, and sum to one (compare exact `Fraction` mass before any
    float API conversion).  Deal and node limits fail before traversal when
    exceeded.

## Legal actions

For `p = acting_player`, return no actions at chance or terminal.  Otherwise:

```python
H = max(street_committed[i] for i in range(N) if not folded[i])
own = street_committed[p]
to_call = H - own
A = [FOLD, CALL(own + min(to_call, remaining[p]))] if to_call else [CHECK]

if (can_raise[p] and remaining[p] > to_call
        and raise_count < config.max_raises):
    maximum = own + remaining[p]
    minimum = H + last_raise_increment
    for target in config.wager_targets + (maximum,):
        if H < target <= maximum and (target >= minimum or target == maximum):
            A.append(RAISE(target))
```

Deduplicate targets while preserving declared order, then the all-in target.
`RAISE(maximum)` is an all-in raise; it is legal even when it is below the
normal minimum.  A `CALL(maximum)` is an all-in call.  Folding is not offered
when `to_call == 0`, matching the existing 3-player semantics.

## Transition algorithm

Use a fresh frozen state for every child.  `_next_after(seat, candidates)`
scans `(seat + 1) % N, ...` and returns the first candidate; it raises if the
set is empty.  Keep `old_pending` before changing it.

```python
p = acting_player
assert p in pending and action in legal_actions()
old_pending = pending
old_H = H
remove p from pending

if action == FOLD:
    folded[p] = True
    can_raise[p] = False
elif action == CHECK:
    pass
elif action == CALL(target):
    pay = target - street_committed[p]
    street_committed[p] += pay
    total_contributed[p] += pay
    remaining[p] -= pay
    pot += pay
    if remaining[p] == 0:
        can_raise[p] = False
elif action == RAISE(target):
    pay = target - street_committed[p]
    street_committed[p] += pay
    total_contributed[p] += pay
    remaining[p] -= pay
    pot += pay
    delta = target - old_H
    is_full = delta >= last_raise_increment
    if is_full:
        last_raise_increment = delta
        can_raise[i] = (not folded[i] and remaining[i] > 0) for every i
    else:                         # legal only as an all-in target
        # Seats that had acted before this short raise stay closed to raising.
        can_raise[i] = (old_can_raise[i] if i in old_pending else False)
    can_raise[p] = (not folded[p] and remaining[p] > 0)
    pending = all i != p with not folded[i] and remaining[i] > 0

if FOLD or CHECK or CALL:
    pending = old_pending minus p, then filter to ACTIVE seats

pending = canonical clockwise order after p
raise_count += 1 only for RAISE
live = [i for i in range(N) if not folded[i]]
if len(live) == 1 or not pending:
    return settle(updated_state)
return updated_state with acting_player = _next_after(p, set(pending))
```

The `FOLD` branch terminates immediately when one live seat remains.  An
all-in call removes that seat from future action; an all-in raise also removes
its raiser but rebuilds responders.  If all remaining live seats are all-in,
`pending` is empty and the round closes.  A full raise reopens all currently
`ACTIVE` seats, including players who acted earlier.  A short all-in raise
increases `H` and forces every other `ACTIVE` seat to answer, but preserves the
no-reopen rule: a seat not in `old_pending` cannot raise unless a later full
raise reopens it.  A seat in `old_pending` retains its prior `can_raise` flag.

Round closure therefore has one test, `pending == ()`, because `pending` is
maintained as the exact owed-responder set.  Three checks close exactly like a
bet/call sequence once the final responder acts.

## Settlement

On closure, apply the existing exact unmatched-excess refund rule, then build
contribution layers from the matched contributions.  For sorted positive
levels `prev < L`:

```text
amount(L) = (L - prev) * count(i where matched[i] >= L)
eligible(L) = {i: not folded[i] and matched[i] >= L}
```

Folded contributions remain in `amount` but folded seats are never eligible.
Award each layer to its highest-ranked eligible hand(s); a sole eligible seat
receives the layer.  Split ties independently with integer division and send
remainder chips one at a time in configured `odd_chip_order` (the legacy rule
is clockwise from immediately left of the button).  Apply the declared rake
per the existing rake module and record `house_rake`.  Final utility is

```text
remaining_after_refund[i] + awards[i] - starting_stacks[i]
```

Thus no-rake terminal returns sum exactly to zero; with operator rake, player
returns sum exactly to `-house_rake`.  No floating-point arithmetic is used for
chips, layers, refunds, or awards.

## Information partition and protocol compatibility

Generic `information_state_key(i)` contains rules/version identity, owner `i`,
that seat's private combo, fixed board, button, all public commitments and
remaining stacks, fold flags, `pending`, `can_raise`, increment, raise count,
acting seat, and actor-labelled public history.  It excludes every other
private combo and every unobserved card.  Any public field that can affect
`legal_actions()` or settlement must be present.  Keys for histories with
identical ordered public actions are identical; changing actor, fold, raise,
commitment, or rules identity changes the key.

Keep `ThreePlayerPostflopState`, `MultiwayConfig`, and
`create_three_player_root` as compatibility wrappers with their current
shapes, action amounts, `CHANCE`/`TERMINAL` sentinels, old information-key
shape, and return types.  The generic engine may use an internal N-seat core,
but the wrapper must preserve the old API rather than mutate it.  Existing
`collect_nplayer_infosets()` must continue to accept the legacy 3-player
object.

## Backward-compatible 3-player oracle suite

Run the legacy and generic implementations from the same fixture and compare
every reachable state (current actor, legal actions, chance deal order/mass,
pot, commitments, contributions, remaining stacks, fold flags, closure, and
terminal returns).  Keep these independent expected-value oracles from
`tests/test_multiway_phase3.py`:

| trace/fixture | required result |
|---|---|
| button 0, root deal | first actor 1; legal actions `CHECK`, `RAISE(4)`, `RAISE(8)`, `RAISE(18)` |
| three checks, ranks `(3,2,1)` | returns `(4,-2,-2)`, sum `0` |
| raise(4), call(4), fold | terminal immediately, sum `0` |
| raise(4), raise(8) | actor 0; increment `4`; `RAISE(18)` legal |
| stack `(20,20,7)`, raise(4), short all-in raise(5), call(5) | actor 1; prior actor has no legal `RAISE` |
| contributions `(5,10,10)`, ranks `(9,9,1)` | returns `(2,8,-10)` with configured odd chip order |
| folded seat 0 with rank `99` | returns `(-5,10,-5)`; folded seat cannot win |
| rake `1/10`, contributions `(10,10,10)` | returns `(17,-10,-10)`; sum `-3` |
| blocker-filtered ranges and alternate private cards | chance identities/mass and information noninterference match legacy tests |

Also run the same trace generator for `N = 2, 4, 5, 6, 7, 8, 9` and assert
all invariants after every child.  Exhaustive tiny trees must independently
check conservation, rotation of seat labels/button, skipped folded/all-in
seats, full-raise reopening, short-all-in non-reopening, and exact side-pot /
odd-chip awards.  A mismatch at `N=3` is a compatibility failure, not a
permitted generic-rule difference.
