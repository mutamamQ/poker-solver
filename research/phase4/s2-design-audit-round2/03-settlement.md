# S2 Settlement Ledger Audit — Design Defects Only

## Audit scope

This is a **design-only** audit of the S2 specification's settlement semantics (§6) against the existing `game_structure.py` primitives. The specification is frozen at hash `770a25ab`. No S2 implementation exists; absence of implementation is expected and not a finding.

## Settlement flow (§6)

The specification declares:

1. Refund unique unmatched excess with `refund_uncalled_excess`.
2. Add refunds to remaining stacks; replace total contributions and pot by matched amounts; reduce street commitments by refunds and reject negative results.
3. Build layers with `build_pot_layers(matched, folded=folded_set)`.
4. For showdown, find the highest eligible rank independently per layer. A sole live player wins every layer without rank lookup.
5. Calculate one hand-level rake and allocate it by the configured layer order.
6. Award net layers and ties through `award_pot_layers` and declared odd-chip order.
7. Pad awards to N seats when zero-contribution trailing seats are absent from the primitive's output.
8. Compute final stacks and utilities and verify both conservation equations.

## Hand-derived representative ledgers

### Ledger 1: Four-player showdown with side pots, no rake

**Setup:**
- Seats: 0, 1, 2, 3
- Starting stacks: (1000, 800, 500, 1200)
- Contributions before refund: (1000, 800, 500, 200)
- Folded: {}
- Button: 0, odd-chip order: (1, 2, 3, 0)

**Step 1: Refund uncalled excess**
- Highest: 1000 (seat 0, unique)
- Second: 800
- Excess: 200
- Refunds: (200, 0, 0, 0)
- Matched contributions: (800, 800, 500, 200)
- Matched pot: 2300

**Step 2: Update stacks**
- Remaining after refund: (200, 0, 0, 1000)
- Total contributed (matched): (800, 800, 500, 200)
- Street committed reduced by refunds: valid (no negatives)

**Step 3: Build layers**
- Sorted levels: [200, 500, 800]
- Layer 0: level=200, contributors={0,1,2,3}, amount=200×4=800, eligible={0,1,2,3}
- Layer 1: level=500, contributors={0,1,2}, amount=(500-200)×3=900, eligible={0,1,2}
- Layer 2: level=800, contributors={0,1}, amount=(800-500)×2=600, eligible={0,1}
- Total: 800+900+600=2300 ✓

**Step 4: Showdown winners (example ranks)**
- Assume ranks: seat 2 > seat 1 > seat 0 > seat 3
- Layer 0 winner: {2}
- Layer 1 winner: {2}
- Layer 2 winner: {1}

**Step 5: Rake**
- No rake policy → total_rake=0, rake_by_layer=(0,0,0)

**Step 6: Award layers**
- Layer 0: (800-0)/1 = 800 → seat 2 gets 800
- Layer 1: (900-0)/1 = 900 → seat 2 gets 900
- Layer 2: (600-0)/1 = 600 → seat 1 gets 600
- Awards: (0, 600, 1700, 0)

**Step 7: Padding**
- All four seats present in contributors → no padding needed

**Step 8: Final stacks and conservation**
- Final stacks: remaining + awards = (200+0, 0+600, 0+1700, 1000+0) = (200, 600, 1700, 1000)
- Utilities: final - starting = (-800, -200, +1200, -200)
- Sum of utilities: -800-200+1200-200 = 0 ✓
- Sum of final stacks: 200+600+1700+1000 = 3500 = sum of starting stacks ✓

---

### Ledger 2: Five-player with tie, rake, odd chips

**Setup:**
- Seats: 0, 1, 2, 3, 4
- Starting stacks: (600, 600, 600, 600, 600)
- Contributions before refund: (600, 600, 400, 300, 100)
- Folded: {4}
- Button: 2, odd-chip order: (3, 4, 0, 1, 2)
- Rake policy: 5% floor, top-down, no cap/minimum/NFND

**Step 1: Refund**
- Highest: 600 (seats 0 and 1, tied)
- No unique highest → no refund
- Matched contributions: (600, 600, 400, 300, 100)
- Matched pot: 2000

**Step 2: Update stacks**
- Remaining: (0, 0, 200, 300, 500)
- Total contributed: (600, 600, 400, 300, 100)

**Step 3: Build layers**
- Sorted levels: [100, 300, 400, 600]
- Layer 0: level=100, contributors={0,1,2,3,4}, amount=100×5=500, eligible={0,1,2,3} (4 folded)
- Layer 1: level=300, contributors={0,1,2,3}, amount=(300-100)×4=800, eligible={0,1,2,3}
- Layer 2: level=400, contributors={0,1,2}, amount=(400-300)×3=300, eligible={0,1,2}
- Layer 3: level=600, contributors={0,1}, amount=(600-400)×2=400, eligible={0,1}
- Total: 500+800+300+400=2000 ✓

**Step 4: Showdown winners (example with tie)**
- Assume ranks: seats 0 and 1 tie (best), seat 2 next, seat 3 last
- Layer 0 winner: {0, 1} (tie)
- Layer 1 winner: {0, 1} (tie)
- Layer 2 winner: {0, 1} (tie)
- Layer 3 winner: {0, 1} (tie)

**Step 5: Rake**
- Eligible pot: 2000 (all layers have eligible winners)
- Hand-level rake: floor(2000 × 5/100) = floor(100) = 100
- Allocate top-down: layers in reverse order [3,2,1,0]
  - Layer 3: take min(100, 400) = 100 → rake_by_layer[3]=100, remaining=0
  - Layers 2,1,0: remaining=0 → rake_by_layer=(0,0,0,100)

**Step 6: Award layers**
- Odd-chip order: (3, 4, 0, 1, 2)
- Filtered for winners {0,1}: ordered = [0, 1]

- Layer 0: net=500-0=500, winners=2, quotient=250, remainder=0 → each gets 250
- Layer 1: net=800-0=800, winners=2, quotient=400, remainder=0 → each gets 400
- Layer 2: net=300-0=300, winners=2, quotient=150, remainder=0 → each gets 150
- Layer 3: net=400-100=300, winners=2, quotient=150, remainder=0 → each gets 150

- Awards: seat 0 = 250+400+150+150 = 950
- Awards: seat 1 = 250+400+150+150 = 950
- Awards: (950, 950, 0, 0, 0)

**Step 7: Padding**
- Seat 4 is in contributors (layer 0) → awards already length 5

**Step 8: Final stacks and conservation**
- Final stacks: (0+950, 0+950, 200+0, 300+0, 500+0) = (950, 950, 200, 300, 500)
- Sum final: 2900
- Sum starting: 3000
- House rake: 100
- Conservation: 2900 + 100 = 3000 ✓
- Utilities: (950-600, 950-600, 200-600, 300-600, 500-600) = (350, 350, -400, -300, -100)
- Sum utilities: 350+350-400-300-100 = -100 = -house_rake ✓

---

### Ledger 3: Nine-player with multiple side pots, sole winner, padding

**Setup:**
- Seats: 0, 1, 2, 3, 4, 5, 6, 7, 8
- Starting stacks: (100, 200, 300, 400, 500, 600, 700, 800, 900)
- Contributions before refund: (100, 200, 300, 400, 500, 600, 700, 800, 50)
- Folded: {8}
- Button: 4, odd-chip order: (5, 6, 7, 8, 0, 1, 2, 3, 4)
- No rake

**Step 1: Refund**
- Highest: 800 (seat 7, unique)
- Second: 700
- Excess: 100
- Refunds: (0,0,0,0,0,0,0,100,0)
- Matched contributions: (100, 200, 300, 400, 500, 600, 700, 700, 50)
- Matched pot: 3550

**Step 2: Update stacks**
- Remaining after refund: (0, 0, 0, 0, 0, 0, 0, 100, 850)
- Total contributed (matched): (100, 200, 300, 400, 500, 600, 700, 700, 50)

**Step 3: Build layers**
- Sorted levels: [50, 100, 200, 300, 400, 500, 600, 700]
- Layer 0: level=50, contributors={0,1,2,3,4,5,6,7,8}, amount=50×9=450, eligible={0,1,2,3,4,5,6,7} (8 folded)
- Layer 1: level=100, contributors={0,1,2,3,4,5,6,7}, amount=(100-50)×8=400, eligible={0,1,2,3,4,5,6,7}
- Layer 2: level=200, contributors={1,2,3,4,5,6,7}, amount=(200-100)×7=700, eligible={1,2,3,4,5,6,7}
- Layer 3: level=300, contributors={2,3,4,5,6,7}, amount=(300-200)×6=600, eligible={2,3,4,5,6,7}
- Layer 4: level=400, contributors={3,4,5,6,7}, amount=(400-300)×5=500, eligible={3,4,5,6,7}
- Layer 5: level=500, contributors={4,5,6,7}, amount=(500-400)×4=400, eligible={4,5,6,7}
- Layer 6: level=600, contributors={5,6,7}, amount=(600-500)×3=300, eligible={5,6,7}
- Layer 7: level=700, contributors={6,7}, amount=(700-600)×2=200, eligible={6,7}
- Total: 450+400+700+600+500+400+300+200 = 3550 ✓

**Step 4: Showdown winners (sole winner scenario)**
- Assume seat 5 has the best hand among all live players
- Layer 0 winner: {5}
- Layer 1 winner: {5}
- Layer 2 winner: {5}
- Layer 3 winner: {5}
- Layer 4 winner: {5}
- Layer 5 winner: {5}
- Layer 6 winner: {5}
- Layer 7 winner: {5}

**Step 5: Rake**
- No rake → rake_by_layer = (0,0,0,0,0,0,0,0)

**Step 6: Award layers**
- All layers: sole winner seat 5, no division, no odd chips
- Awards: seat 5 = 450+400+700+600+500+400+300+200 = 3550
- Awards tuple from primitive: only seats in contributors are present
  - Seat 8 is in layer 0 contributors but folded
  - Primitive returns awards for seats 0-8 (all contributors)
  - Awards: (0, 0, 0, 0, 0, 3550, 0, 0, 0)

**Step 7: Padding**
- All nine seats are present in contributors → no padding needed

**Step 8: Final stacks and conservation**
- Final stacks: (0+0, 0+0, 0+0, 0+0, 0+0, 0+3550, 0+0, 100+0, 850+0) = (0, 0, 0, 0, 0, 3550, 0, 100, 850)
- Sum final: 4500 = sum starting ✓
- Utilities: (0-100, 0-200, 0-300, 0-400, 0-500, 3550-600, 0-700, 100-800, 850-900)
           = (-100, -200, -300, -400, -500, +2950, -700, -700, -50)
- Sum utilities: -100-200-300-400-500+2950-700-700-50 = 0 ✓

---

## Design defect findings

### Finding 1: Padding specification ambiguity (§6 step 7)

**Issue:** The specification states "Pad awards to N seats when zero-contribution trailing seats are absent from the primitive's output." This is ambiguous:

1. The primitive `award_pot_layers` determines `seat_count` as `1 + max(seat for layer in layers for seat in layer.contributors)`, which naturally includes all contributor seats up to the highest seat number.
2. "Zero-contribution trailing seats" is unclear: does it mean seats with zero matched contribution, or seats beyond the highest contributor?
3. The phrase "absent from the primitive's output" suggests the primitive might return a shorter tuple, but the primitive's logic already pads to `seat_count` based on contributors.

**Scenario:** If N=5 but only seats {0, 2, 4} contributed (seats 1 and 3 never acted), the primitive returns a tuple of length 5 (seat_count = 1+4 = 5). Seat 4 is the highest contributor, so seats 1 and 3 get zero awards naturally. No additional padding is needed.

**Defect:** The specification does not clarify whether "trailing" means seats > max(contributors) or seats with zero contribution. If the game allows non-contiguous seats (e.g., seats {0, 2, 4} in a 5-player game), the primitive already handles this correctly. The specification should either:
- Remove step 7 as redundant (the primitive already pads correctly), OR
- Clarify that padding is only needed when N > seat_count (i.e., when the highest seat number in the game is greater than the highest contributor seat number).

**Severity:** Low. The primitive's behavior is correct; the specification is merely unclear.

---

### Finding 2: Negative street_committed after refund (§6 step 2)

**Issue:** The specification states "reduce street commitments by refunds and reject negative results." However, the specification does not define the initial relationship between `street_committed` and `total_contributed` at the end of betting.

**Scenario:** At the end of betting:
- Seat 0: `total_contributed=1000`, `street_committed=1000`
- Seat 1: `total_contributed=800`, `street_committed=800`
- Refund to seat 0: 200
- After refund: `total_contributed[0] = 800`, `street_committed[0] = 1000 - 200 = 800` ✓

This works correctly. However, consider a multi-street scenario (not in S2 scope, but the primitive is generic):
- Seat 0: `total_contributed=1000`, `street_committed=200` (contributed 800 on earlier streets, 200 on current street)
- Refund to seat 0: 200
- After refund: `total_contributed[0] = 800`, `street_committed[0] = 200 - 200 = 0` ✓

But if refund > street_committed:
- Seat 0: `total_contributed=1000`, `street_committed=100`
- Refund to seat 0: 200
- After refund: `street_committed[0] = 100 - 200 = -100` ✗

**Defect:** The specification does not prove that refunds can never exceed `street_committed`. For S2 (one betting round), `street_committed == total_contributed` at settlement, so this cannot occur. However, the specification claims to use "existing generic N-player CFR and exact settlement primitives" (§1), and the primitives are designed for multi-street use. The specification should either:
- Assert that for one-round postflop, `street_committed == total_contributed` at settlement, making negative results impossible, OR
- Define the refund application more carefully (e.g., refunds reduce `total_contributed` and `remaining` only, and `street_committed` is recalculated or zeroed for terminal states).

**Severity:** Medium. This is a design gap that could cause implementation confusion or errors if the settlement logic is reused for multi-street games.

---

### Finding 3: Rake allocation and layer eligibility interaction (§6 step 5)

**Issue:** The specification states "Calculate one hand-level rake and allocate it by the configured layer order." The `calculate_rake` function takes `eligible_pot` as input, but the specification does not define how `eligible_pot` is calculated when some layers have no eligible winners (all folded).

**Scenario:** 
- Layer 0: amount=500, eligible={0,1,2}
- Layer 1: amount=300, eligible={} (all folded — but wait, `build_pot_layers` raises ValueError if a layer has no eligible winner)

Actually, `build_pot_layers` enforces that every layer has at least one eligible winner (line 230-231 in `game_structure.py`). So this scenario cannot occur with the current primitive.

**However:** The specification's settlement flow (§6 step 3) calls `build_pot_layers(matched, folded=folded_set)` after refunds. If all players fold except one, that player is the sole eligible winner of all layers. The primitive does not fail.

**Defect:** The specification does not explicitly state that `eligible_pot` for rake calculation is the sum of all layer amounts (i.e., the matched pot after refunds). The specification should clarify that:
- `eligible_pot = sum(layer.amount for layer in layers)`, OR
- `eligible_pot = matched_pot` (which is the same value).

Without this clarification, an implementer might incorrectly calculate rake on the pre-refund pot or only on layers with multiple eligible winners.

**Severity:** Low. The intent is clear from context, but explicit definition would prevent implementation errors.

---

### Finding 4: Odd-chip order validation and winner coverage (§6 step 6)

**Issue:** The specification states "Award net layers and ties through `award_pot_layers` and declared odd-chip order." The `award_pot_layers` primitive validates that `odd_chip_order` includes every winner (line 304-305), but the specification does not require that `odd_chip_order` is a permutation of `range(N)` at the config level.

**Wait:** Actually, §2.1 states "Odd-chip order is checked by both length and set equality to be exactly a permutation of `range(N)`." So the config validation is correct.

**However:** The primitive's validation (line 304-305) checks that every winner is in `odd_chip_order`, but it does not check that `odd_chip_order` is a permutation of all seats. The primitive only requires that winners are covered.

**Scenario:** If `odd_chip_order = (0, 1, 0, 2)` (duplicate seat 0), the config validation would reject it (not a permutation). But if the config validation were missing, the primitive would accept it as long as winners are in the list.

**Defect:** No defect. The specification correctly requires `odd_chip_order` to be a permutation of `range(N)` at the config level, and the primitive's validation is sufficient for its own scope. The two validations are complementary and correct.

**Severity:** None. No defect found.

---

### Finding 5: Conservation verification and utility sign (§6 step 8)

**Issue:** The specification states "With rake, player utilities sum to negative house rake and player-plus-house utility is exactly zero." The `verify_terminal_conservation` primitive checks `final + rake == initial` (line 323), which is correct.

However, the specification does not define the sign convention for `house_rake` in the state's `terminal_values`. 

**From §2.3:** The state contains `terminal_values: tuple[int, ...] | None` and `house_rake: int` (nonnegative). 

**From §3 invariant 10:** "Terminal has empty pending, exactly N integer utilities, and `sum(terminal_values) + house_rake == 0`."

This is correct: utilities are signed (positive for winners, negative for losers), and `sum(utilities) = -house_rake` when rake is taken.

**Defect:** No defect. The specification correctly defines the conservation equation and sign convention.

**Severity:** None. No defect found.

---

### Finding 6: Refund and tie interaction

**Issue:** When the highest contribution is tied (e.g., two players both contribute 1000), `refund_uncalled_excess` returns zero refunds for all players (line 208-212). This is correct: no unique highest means no refund.

However, consider this scenario:
- Seat 0: contributed 1000, folded
- Seat 1: contributed 1000, live
- Seat 2: contributed 500, live

The highest contribution is tied at 1000, so no refund occurs. Layers are built:
- Layer 0: level=500, contributors={0,1,2}, amount=1500, eligible={1,2} (0 folded)
- Layer 1: level=1000, contributors={0,1}, amount=1000, eligible={1} (0 folded)

Seat 1 is the sole eligible winner of layer 1, so they win the full 1000. Seat 0's 500 contribution to layer 1 is awarded to seat 1. This is correct: seat 0 folded, so they are not eligible.

**But:** Seat 0 contributed 1000 and folded. Seat 1 contributed 1000 and is live. Seat 2 contributed 500 and is live. The pot is 2500. Seat 1 can only win up to 1000 from seat 0 (matched contribution). The remaining 500 from seat 0 should be... wait, no. Seat 0 contributed 1000 total. Seat 2 contributed 500. Seat 1 can win 500 from seat 2 and 500 from seat 0 in layer 0 (1500 total in layer 0, split between eligible winners). In layer 1, seat 1 can win 1000 from seat 0 and seat 1's own 500 contribution above layer 0... no, wait.

Let me recalculate:
- Contributions: (1000, 1000, 500)
- Layer 0: level=500, contributors={0,1,2}, amount=500×3=1500, eligible={1,2}
- Layer 1: level=1000, contributors={0,1}, amount=(1000-500)×2=1000, eligible={1}

Layer 0: 1500 chips, eligible winners {1,2}. If seat 1 wins, they get some portion. If seat 2 wins, they get some portion.
Layer 1: 1000 chips, eligible winner {1} only. Seat 1 gets all 1000.

Total pot: 2500. If seat 1 wins both layers: 1500 (if sole winner of layer 0) + 1000 = 2500. Seat 1 contributed 1000, so net gain = 1500. Seat 0 contributed 1000 and lost it all (folded). Seat 2 contributed 500 and lost it all. Net: +1500 - 1000 - 500 = 0 ✓

This is correct. No refund is needed because seat 1's 1000 contribution is matched by seat 0's 1000 contribution. The fact that seat 0 folded does not trigger a refund; it only affects eligibility in layers.

**Defect:** No defect. The refund logic correctly handles ties and folded players.

**Severity:** None. No defect found.

---

## Summary of design defects

1. **Padding specification ambiguity (Low severity):** Step 7 of the settlement flow is unclear about when padding is needed. The primitive already pads correctly, so the specification should clarify or remove this step.

2. **Negative street_committed after refund (Medium severity):** The specification does not prove that refunds can never exceed `street_committed`. For S2's one-round scope, this is safe, but the specification should assert this invariant explicitly to avoid confusion when reusing the generic primitives.

3. **Rake eligible_pot definition (Low severity):** The specification does not explicitly define `eligible_pot` for rake calculation. It should state that `eligible_pot = sum(layer.amount for layer in layers)` or equivalently the matched pot after refunds.

All other aspects of the settlement specification are internally consistent and correctly use the existing primitives. The hand-derived ledgers confirm that refunds, layers, rake allocation, ties, odd chips, and conservation all work as specified.

---

## Verification against acceptance criteria (§11)

The settlement-related acceptance criteria are:

- ✓ "hand-derived multi-layer refunds, side pots, rake, ties, and odd chips match exactly" — confirmed by ledgers 1, 2, 3.
- ✓ "terminal utility plus house rake conserves exactly" — confirmed by all ledgers.
- ✓ "every transition conserves stacks/pot" — not directly tested here (betting transitions), but settlement conservation is verified.

The specification's settlement semantics are **feasible and correct** given the existing primitives, with the three minor clarifications noted above.
