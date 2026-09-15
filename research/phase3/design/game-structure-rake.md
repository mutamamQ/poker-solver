# Phase 3 Design: Game Structure and Rake Subsystem

## Design status

This is the authoritative Phase 3 design for game structure, forced contributions, side pots, rake, and conservation accounting. It extends the Phase 2 multistreet model with preflop forced postings, configurable antes/blinds/straddles, exact side-pot construction, rational rake with multiple rounding modes, and deterministic odd-chip allocation.

Evidence base: existing `research/phase3/game-structure-rake.md` (reconciled contract), `research/phase3/preflop-heads-up.md` (HU setup), ARCHITECTURE.md Phase 2 accounting, `src/poker_solver/multistreet.py` (amount-to semantics, zero-sum utilities), and `tests/test_multistreet.py` (unmatched refunds, conservation).

## Numeric representation and validation

All chip amounts are non-negative integers. A caller chooses the smallest unit needed by the configuration; for example, blinds of 0.5/1 may be represented as 1/2 units.

Rake percentage must be represented as a rational numerator/denominator pair, `Decimal`, or equivalent exact type. Binary `float` is not accepted in accounting code because rounding boundaries are observable and must be deterministic.

Player identifiers and seat order are explicit. Defaults must not silently infer a particular poker room's rules. Invalid configurations (negative amounts, overlapping cards, zero total ante mass, rake numerator > denominator) fail before tree construction with status 2.

## Game structure model

A game structure contains:

- ordered seats and a button seat;
- starting stack for every seat (before forced postings);
- small-blind and big-blind seats and amounts;
- ante mode and amount;
- zero or more configured straddle posters and amounts;
- permitted action tree (limp/fold/call/raise targets);
- an optional rake policy.

### Forced contributions

Forced contributions are debited exactly once before voluntary action begins.

**Ante modes:**

- `none`: no ante.
- `per_player(A)`: every dealt-in seat contributes up to `min(A, remaining_stack)`.
- `total(A, allocation_policy)`: table contributions sum to at most `A`, with a caller-selected deterministic allocation and short-stack policy. The allocation policy is explicit input; the engine does not invent a default split.
- `bb_ante(A)`: the BB contributes up to `min(A, remaining_stack)` in addition to its blind.

The allocation and ordering of an all-in player's ante and blind are house rules and must be policy inputs. The engine must not invent missing chips when a player cannot cover all forced bets.

Blind and straddle postings are likewise `min(required, remaining_stack)`. A straddle is an explicit `(seat, amount)` entry in the configuration; the public GTO Wizard product labels ("standard", "double", "Mississippi") do not justify hard-coding every straddle to twice the preceding blind. Callers needing standard 2×BB or UTG+1 4×BB straddles supply those exact amounts.

**Heads-up setup:**

Seats are player 0 `BTN_SB` and player 1 `BB`. Stacks are integer chips before forced postings. BTN posts the small blind and BB posts the big blind, each capped by remaining stack. BTN acts first preflop if able to act. If a matched non-all-in preflop round transitions postflop, BB is first postflop.

Antes in HU: `per-player` posts from both; `total` with even split posts half from each (odd totals require explicit allocation); `bb-ante` posts from BB only.

Total starting pot equals the exact sum of blind and ante postings. Remaining stack equals starting stack minus that player's postings. "Effective stack" metadata is the maximum matched contribution still contestable; it is derived from ledgers, not used to erase unmatched chips or double-count posted blinds.

### Action order

**Preflop:**

For no straddle in a game of three or more players, preflop action begins with the first active seat clockwise after the BB. In heads-up, the button/SB acts first preflop.

With configured straddles, preflop action begins with the first eligible seat clockwise after the final straddler; that straddler retains its option when action returns, subject to normal closing/reopening rules.

**Postflop:**

Postflop action begins with the first active non-folded seat clockwise after the button.

**Action close:**

All-in and folded seats are skipped. Action closes only when every non-folded, non-all-in player has acted since the last full raise and has matched the live wager or folded.

A short all-in raise changes the amount to call but does not necessarily reopen raising rights. The reopen policy must be represented explicitly and tested; `new wager > old wager` alone is insufficient. Phase 3 default: a short all-in does not reopen for a player who already acted unless it meets the full minimum-raise increment.

### Amount-to accounting

All public raise/bet targets use total-to semantics unless the API names an added amount explicitly:

```text
additional = max(0, target_this_street - contributed_this_street[player])
actual = min(additional, remaining_stack[player])
```

The pot increases by `actual`, not by `target_this_street`. This prevents blind and prior-bet double counting. Phase 2 `multistreet.py` already implements this for postflop; Phase 3 extends it to preflop forced postings.

A **limp** is a call of the live blind in an unopened pot. A **cold call** is metadata describing a call made without a prior voluntary contribution in the current betting round; it is not a different chip-transfer operation.

## Derived quantities

Stack depth in BB and stack-to-pot ratio (SPR) are display/selection metrics, not accounting primitives.

Heads-up effective stack is the smaller remaining stack. In multiway play there is no single sufficient effective-stack scalar: the amount contestable against each opponent depends on contribution layers. APIs may expose pairwise effective stacks but must not use one global minimum to construct side pots.

For a positive pot, a decision-point SPR may be reported as a selected remaining stack divided by the pot. The API must say which player or pair it refers to. There is no Phase 3 strategic interpretation such as an automatic commitment threshold.

## Side pots

Given final non-negative contributions `c[i]` after all action and uncalled refunds, let the distinct positive contribution levels be `0 = l[0] < l[1] < ... < l[k]`.

For every level `l[j]`:

```text
contributors_j = {i | c[i] >= l[j]}
amount_j = (l[j] - l[j-1]) * len(contributors_j)
eligible_j = contributors_j - folded_players
```

Zero-amount layers are omitted. A layer with no eligible player indicates an invalid hand history or unmatched excess that should have been returned before settlement.

**Invariants:**

```text
sum(layer.amount) == sum(final_matched_contributions)
folded players fund layers but are never eligible to win
eligibility can only shrink as levels increase
```

**Uncalled excess** is returned to the contributor before layer construction and is neither pot nor rake base.

**Fixture:**

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
rate_numerator: int
rate_denominator: int
cap_chips: int | none
minimum_rakeable_pot: int | none
no_flop_no_drop: bool
rounding: "floor" | "ceiling" | "nearest_ties_to_even"
base: "matched_pot"
```

Validation requires `0 <= numerator <= denominator`, a positive denominator, and non-negative cap/minimum values.

For terminal matched pot `P` (after uncalled refunds):

```text
if no_flop_no_drop and not flop_seen:
    raw = 0
else if minimum_rakeable_pot is set and P < minimum:
    raw = 0
else:
    raw = round_policy(P * numerator / denominator)
rake = min(P, raw, cap_chips if configured else P)
awardable = P - rake
```

`P` includes only matched contributions after refunds. Rake is computed **once** for the hand, not independently per player and not once per side pot. This avoids multiplying caps and rounding errors. The resulting rake can be allocated across layers by a deterministic repository policy solely to preserve eligibility during payout; that allocation must sum exactly to the hand rake.

**Phase 3 default layer allocation:** top-down. Remove rake from the highest contribution layer first, then lower layers if needed. This is a project convention, not a claimed room or GTO Wizard rule. Alternative allocation policies remain a documented extension.

A zero rate is chip-EV accounting. `no_flop_no_drop` is optional behavior, not assumed universal.

**Unsupported:** time collection, jackpot drops, promotional drops, tournament entry fees, weighted-contributed attribution, rakeback, and room-specific preflop exceptions.

## Odd chips and split awards

For each net layer (after rake allocation), determine tied winners among that layer's eligible players. Give each winner `amount // winner_count`; distribute the remainder one chip at a time using an explicit ordered `odd_chip_priority` list.

The **default project policy** is clockwise from the button: the first eligible winner left of the button receives the first odd chip. This is configurable and must not be advertised as a universal room rule.

**Invariants:**

```text
sum(layer_awards) == net_layer_amount
award recipient is eligible for that layer
awards are deterministic for a fixed priority
```

## Conservation and utilities

Let `initial_total` include all player stacks before forced postings. At every nonterminal state:

```text
sum(stacks) + sum(committed) == initial_total
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

**Exact fixtures:**

1. **HU no rake:** initial stacks 100/100. SB 1 and BB 2. SB raises to 6 (adds 5). BB calls (adds 4). Pot is 12 and stacks are 94/94. At 5% floor rake with cap 3 after a flop, if `no_flop_no_drop=true` and no flop seen, rake is 0 and awardable pot is 12. Conservation: `188 + 12 = 200` before settlement and final player stacks sum to 200.

2. **HU with rake:** same fixture with rate 1/10, ceiling rounding, cap 3, flop seen: `ceil(12 * 0.1) = 2`, capped at 2. Rake is 2 and awardable pot 10. Final player stacks plus house rake equal 200.

3. **Three-way side pots:** final contributions 100/300/300; 5% floor rake capped at 5. Gross pot 700, `floor(700 * 0.05) = 35`, capped at 5. Rake 5, net awards 695. If C wins both layers, final settlement awards C 695. Utilities: A loses 100, B loses 300, C wins 395, rake 5. Sum: `-100 - 300 + 395 = -5 = -rake`. Conservation holds.

4. **NFND:** matched preflop pot 17 with 5% ceiling rate and no cap. If `no_flop_no_drop=true` and no flop seen, rake 0. If `no_flop_no_drop=false`, `ceil(17 * 0.05) = 1`, rake 1.

5. **Uncalled excess:** contributions A:100, B:300 after all others fold/cannot match beyond 100. Return 200 to B before side-pot construction; matched pot is 200. Rake uses 200 as base, not 400.

## Acceptance criteria

Tests must establish:

- exact forced-posting debits in every ante mode, including short stacks;
- full-ring, heads-up, and straddled preflop order;
- no double counting across raise-to/call sequences;
- short all-in reopening behavior under the declared policy;
- exact layer construction, folded-player exclusion, and uncalled refunds;
- rational rake with every rounding mode, cap, minimum, and NFND branch;
- hand rake computed once and layer deductions summing to it;
- deterministic odd-chip payouts under an injected priority;
- conservation at every transition and `sum(utilities) == -rake` terminally;
- invalid configurations rejected before tree construction.

No floating tolerance is permitted for integer accounting. Probability/value arithmetic uses absolute tolerance `1e-12` unless an iterative fixture declares a measured threshold.

## Tractability and boundary

Accounting is tractable: forced posting and conservation are linear in seats; sorted side-pot construction is `O(n log n)` and `n <= 9` is trivial. The hard problem is game-tree growth, not these transfers.

**Implemented target:**

- explicit stacks, blinds, three ante modes (per-player, total, bb-ante), and configured straddles;
- legal amount-to contribution accounting and action order;
- exact side pots/refunds/odd chips;
- rational percentage/cap/minimum/NFND rake with three rounding modes;
- conservation and payoff reporting.

**Documented boundary:**

- arbitrary room-rule emulation (e.g., specific card-room short-blind policies);
- time rake, drops, fees, and rakeback;
- claiming GTO Wizard's private rounding or side-pot-rake allocation method;
- using these accounting primitives as evidence that a large preflop tree is computationally solved.

## Integration points

### Compatibility with Phase 2 multistreet

Phase 2 `multistreet.py` already implements:

- integer chip amounts;
- amount-to semantics (`Action.amount` is new total commitment on current street);
- unmatched heads-up refunds;
- zero-sum terminal utilities measured from spot start.

Phase 3 extends this with:

- preflop forced postings (antes, blinds, straddles) before voluntary action;
- multiway side-pot construction;
- rake computation and layer allocation;
- odd-chip distribution.

The existing `MultiStreetConfig` and `MultiStreetState` can be extended with optional `ante_mode`, `rake_policy`, and `odd_chip_priority` fields. Existing Phase 2 tests (185 total) must remain green.

### New modules and ownership

Phase 3 game structure and rake will be implemented in:

- `src/poker_solver/game_structure.py`: forced postings, side pots, rake, odd chips, conservation utilities.
- `tests/test_game_structure.py`: exhaustive unit tests for every ante mode, rake rounding, side-pot fixture, and conservation invariant.

Exclusive file ownership: one subagent owns the implementation pair, a different subagent owns adversarial review.

### API and CLI

Version-3 JSON configurations will include:

```json
{
  "version": 3,
  "game": "holdem-preflop-heads-up",
  "stacks": [2500, 2500],
  "button": 0,
  "blinds": {"small": 50, "big": 100},
  "ante_mode": {"type": "per_player", "amount": 10},
  "straddles": [],
  "rake_policy": {
    "rate_numerator": 1,
    "rate_denominator": 20,
    "cap_chips": 30,
    "minimum_rakeable_pot": null,
    "no_flop_no_drop": true,
    "rounding": "floor"
  },
  "odd_chip_priority": [0, 1],
  "ranges": [...],
  "tree": [...]
}
```

Existing version-1 and version-2 APIs remain unchanged.

## Tier decisions

| Capability | Tier | Disposition |
|---|---|---|
| Integer chip accounting | 1 | Implement |
| Explicit stacks, blinds, button | 1 | Implement |
| Per-player, total, bb-ante modes | 1 | Implement |
| Configured straddles (explicit seat/amount) | 1 | Implement |
| Amount-to semantics, no double-counting | 1 | Implement (Phase 2 baseline) |
| Exact side pots, folded exclusion | 1 | Implement |
| Uncalled refunds | 1 | Implement (Phase 2 baseline) |
| Rational rake (numerator/denominator) | 1 | Implement |
| Three rounding modes (floor/ceiling/nearest) | 1 | Implement |
| Rake cap, minimum pot, NFND | 1 | Implement |
| Top-down layer rake allocation | 1 | Implement (project default) |
| Deterministic odd-chip priority | 1 | Implement |
| Conservation invariants and tests | 1 | Implement |
| Preflop action order (HU, ring, straddle) | 1 | Implement |
| Short all-in reopen policy | 1 | Implement with explicit policy |
| Alternative rake allocation policies | 2 | Document extension point |
| Room-specific short-blind rules | 2 | Explicit policy input or boundary |
| Time rake, drops, fees, rakeback | 3 | Documented boundary |
| GTO Wizard private implementation parity | 3 | Not claimed |

## References

- GTO Wizard, How to Build Custom Solutions: https://help.gtowizard.com/how-to-build-custom-solutions/
- Poker TDA rules (rules vary by edition and venue): https://www.pokertda.com/poker-tda-rules/
- Robert's Rules of Poker archive (independent rules reference): https://www.briggsoft.com/docs/pmavens/Rules_Roberts.htm
- Phase 2 multistreet accounting: `src/poker_solver/multistreet.py`, `tests/test_multistreet.py`
- Existing research: `research/phase3/game-structure-rake.md`, `research/phase3/preflop-heads-up.md`
- ARCHITECTURE.md Phase 2 reconciled architecture

Only the GTO Wizard page is used for product-control claims. Independent rule references motivate explicit policy injection where house rules vary.
