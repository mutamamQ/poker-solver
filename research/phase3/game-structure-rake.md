# Game structure and rake: executable accounting contract

## Evidence status and corrections

A restricted-tool BryantGPT worker produced the first draft. Parent read it in full and rejected several unsafe claims and broken fixtures:

- blind action order was wrong (`SB -> BB -> UTG` is not a valid full-ring preflop order);
- antes, blind ratios, straddle sizes, rake percentages/caps, and strategic SPR bands were presented as universal defaults without adequate support;
- a heads-up rake fixture calculated rake as 3 but asserted conservation with rake 2;
- a raise-to amount was added as a fresh contribution, double-counting the posted blind;
- rake rounding and side-pot allocation were underspecified;
- odd-chip direction was treated as universal despite being house-rule dependent;
- `rake_cap > pot` is not inherently invalid;
- claimed GTO Wizard parity and verified URLs exceeded the evidence.

This reconciled contract uses explicit integer inputs and policies. It does not encode room defaults or claim proprietary parity.

## Verified public product semantics

GTO Wizard's public custom-solution documentation says its preflop builder exposes:

- number of dealt players;
- default and per-position stack sizes;
- configurable SB and BB values;
- per-player, total, and BB-ante modes;
- rake percentage and a cap in big blinds, applied to the matched pot;
- single, double, and Mississippi straddles;
- configurable limps and cold calls.

The same page describes a single straddle as UTG posting with action beginning at UTG+1; double as UTG and UTG+1 posting with action at UTG+2; and Mississippi as a configured non-blind straddler with action beginning to that player's left.

Source: https://help.gtowizard.com/how-to-build-custom-solutions/

Those public controls are product evidence, not evidence for private implementation details such as rounding, side-pot rake allocation, or every site's house rules.

## Numeric representation

Phase 3 accounting must use integer chip units. A caller chooses the smallest unit needed by the configuration; for example, blinds of 0.5/1 may be represented as 1/2 units.

A percentage must be represented as a rational numerator/denominator, decimal, or an equivalent exact type. Binary float is not accepted in accounting code because the rounding boundary is observable.

Every amount is non-negative. Player identifiers and seat order are explicit. Defaults must not silently infer a particular poker room.

## Structure model

A game structure contains:

- ordered seats and a button seat;
- starting stack for every seat;
- small-blind and big-blind seats and amounts;
- ante mode and amount;
- zero or more configured straddle posters and amounts;
- permitted limp/cold-call actions;
- an optional rake policy.

### Forced contributions

Forced contributions are debited exactly once before voluntary action.

Ante modes:

- `none`: no ante;
- `per_player(A)`: every dealt-in seat contributes up to `A`;
- `total(A, allocation_policy)`: table contributions sum to at most `A`, with a caller-selected deterministic allocation and short-stack policy;
- `bb_ante(A)`: the BB contributes up to `A` in addition to its blind.

The allocation and ordering of an all-in player's ante and blind are house rules and must be policy inputs. The engine must not invent missing chips when a player cannot cover all forced bets.

Blind and straddle postings are likewise `min(required, remaining_stack)`. A straddle is an explicit `(seat, amount)` entry; the public product labels do not justify hard-coding every straddle to twice the preceding blind.

### Action order

For no straddle in a game of three or more players, preflop action begins with the first active seat clockwise after the BB. In heads-up, the button/SB acts first preflop. Postflop action begins with the first active non-folded seat clockwise after the button.

With configured straddles, preflop action begins with the first eligible seat clockwise after the final straddler; that straddler retains its option when action returns, subject to normal closing/reopening rules.

All-in and folded seats are skipped. Action closes only when every non-folded, non-all-in player has acted since the last full raise and has matched the live wager or folded.

A short all-in raise changes the amount to call but does not necessarily reopen raising rights. The reopen policy must be represented explicitly and tested; `new wager > old wager` alone is insufficient.

### Amount-to accounting

All public raise/bet targets use total-to semantics unless the API names an added amount explicitly:

```text
additional = max(0, target_this_street - contributed_this_street[player])
actual = min(additional, remaining_stack[player])
```

The pot increases by `actual`, not by `target_this_street`. This prevents blind and prior-bet double counting.

A limp is a call of the live blind in an unopened pot. A cold call is metadata describing a call made without a prior voluntary contribution; it is not a different chip-transfer operation.

## Derived quantities

Stack depth in BB and stack-to-pot ratio are display/selection metrics, not accounting primitives.

Heads-up effective stack is the smaller remaining stack. In multiway play there is no single sufficient effective-stack scalar: the amount contestable against each opponent depends on contribution layers. APIs may expose pairwise effective stacks but must not use one global minimum to construct side pots.

For a positive pot, a decision-point SPR may be reported as a selected remaining stack divided by the pot. The API must say which player or pair it refers to. There is no Phase 3 strategic interpretation such as an automatic commitment threshold.

## Side pots

Given final non-negative contributions `c[i]`, let the distinct positive levels be
`0 = l[0] < l[1] < ... < l[k]`.

For every level `l[j]`:

```text
contributors_j = {i | c[i] >= l[j]}
amount_j = (l[j] - l[j-1]) * len(contributors_j)
eligible_j = contributors_j - folded_players
```

Zero-amount layers are omitted. A layer with no eligible player indicates an invalid hand history or unmatched excess that should have been returned before settlement.

Invariants:

```text
sum(layer.amount) == sum(final_matched_contributions)
folded players fund layers but are never eligible to win
eligibility can only shrink as levels increase
```

Uncalled excess is returned to the contributor before layer construction and is neither pot nor rake base.

Fixture:

```text
contributions = A:100, B:300, C:300
folded = none
layers =
  300 eligible {A,B,C}
  400 eligible {B,C}
```

With `A` folded, the amounts remain 300 and 400, but eligibility is `{B,C}` for both.

## Rake policy

The bounded implementation supports terminal pot rake with explicit fields:

```text
rate_numerator
rate_denominator
cap_chips | none
minimum_rakeable_pot | none
no_flop_no_drop: bool
rounding: floor | ceiling | nearest_ties_to_even
base: matched_pot
```

Validation requires `0 <= numerator <= denominator`, a positive denominator, and non-negative cap/minimum values.

For terminal matched pot `P`:

```text
if no_flop_no_drop and not flop_seen: raw = 0
else if minimum_rakeable_pot is set and P < minimum: raw = 0
else raw = round_policy(P * numerator / denominator)
rake = min(P, raw, cap_chips if configured else P)
awardable = P - rake
```

`P` includes only matched contributions after refunds. Rake is computed once for the hand, not independently per player and not once per side pot. This avoids multiplying caps and rounding errors. The resulting rake can be allocated across layers by a deterministic repository policy solely to preserve eligibility during payout; that allocation must sum exactly to the hand rake.

Phase 3's default layer allocation is top-down: remove rake from the highest contribution layer first, then lower layers if needed. This is a project convention, not a claimed room or GTO Wizard rule. Alternative allocation policies remain a documented extension.

A zero rate is chip-EV accounting. `no_flop_no_drop` is optional behavior, not assumed universal.

Time collection, jackpot drops, promotional drops, tournament entry fees, weighted-contributed attribution, rakeback, and room-specific preflop exceptions are unsupported.

## Odd chips and split awards

For each net layer, determine tied winners among that layer's eligible players. Give each winner `amount // winner_count`; distribute the remainder one chip at a time using an explicit ordered `odd_chip_priority` list.

The default project policy is clockwise from the button (the first eligible winner left of the button receives the first odd chip). This is configurable and must not be advertised as a universal room rule.

Invariants:

```text
sum(layer_awards) == net_layer_amount
award recipient is eligible for that layer
awards are deterministic for a fixed priority
```

## Conservation and utilities

Let `initial_total` include all player stacks before forced postings. At every nonterminal state:

```text
sum(stacks) + sum(committed_chips) == initial_total
```

After settlement:

```text
sum(final_stacks) + house_rake == initial_total
```

Player utility is `final_stack - initial_stack`. Therefore:

```text
sum(player_utilities) == -house_rake
```

If the house is represented as an additional account, all utilities sum to zero.

Exact fixtures:

1. HU, initial stacks 100/100. SB 1 and BB 2. SB raises to 6: SB adds 5. BB calls: BB adds 4. Pot is 12 and stacks are 94/94. At 5% floor rake with cap 3 after a flop, rake is 0 and awardable pot is 12. Conservation: `188 + 12 = 200` before settlement and final player stacks sum to 200.

2. Same fixture with rate 1/10, ceiling rounding, cap 3: rake is 2 and awardable pot 10. Final player stacks plus house rake equal 200.

3. Three-way final contributions 100/300/300; 5% floor rake capped at 5. Gross pot 700, rake 5, net awards 695. If C wins both layers, final settlement awards C 695. Utilities plus rake conserve exactly.

4. NFND: matched preflop pot 17 with 5% ceiling rate and no cap returns rake 0 when `no_flop_no_drop=true`; the same policy with `false` returns rake 1.

5. Uncalled excess: contributions A:100, B:300 after all others fold/cannot match beyond 100. Return 200 to B; matched pot is 200 and rake uses 200, not 400.

## Acceptance criteria

Tests must establish:

- exact forced-posting debits in every ante mode, including short stacks;
- full-ring, heads-up, and straddled preflop order;
- no double counting across raise-to/call sequences;
- short all-in reopening behavior;
- exact layer construction, folded-player exclusion, and uncalled refunds;
- rational rake with every rounding mode, cap, minimum, and NFND branch;
- hand rake computed once and layer deductions summing to it;
- deterministic odd-chip payouts under an injected priority;
- conservation at every transition and `sum(utilities) == -rake` terminally;
- invalid configurations rejected before tree construction.

No floating tolerance is permitted for integer accounting.

## Tractability and boundary

Accounting is tractable: forced posting and conservation are linear in seats; sorted side-pot construction is `O(n log n)` and `n <= 9` is trivial. The hard problem is game-tree growth, not these transfers.

Implemented target:

- explicit stacks, blinds, three ante modes, and configured straddles;
- legal amount-to contribution accounting and action order;
- exact side pots/refunds/odd chips;
- rational percentage/cap/minimum/NFND rake;
- conservation and payoff reporting.

Documented boundary:

- arbitrary room-rule emulation;
- time rake, drops, fees, and rakeback;
- claiming GTO Wizard's private rounding or side-pot-rake method;
- using these accounting primitives as evidence that a large preflop tree is computationally solved.

## References

- GTO Wizard, How to Build Custom Solutions: https://help.gtowizard.com/how-to-build-custom-solutions/
- Poker TDA rules (rules vary by edition and venue): https://www.pokertda.com/poker-tda-rules/
- Robert's Rules of Poker archive (independent rules reference): https://www.briggsoft.com/docs/pmavens/Rules_Roberts.htm

Only the GTO Wizard page is used for the product-control claims above. Independent rule references motivate explicit policy injection where house rules vary.