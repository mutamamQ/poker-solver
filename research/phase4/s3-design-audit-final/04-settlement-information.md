# S3 settlement, refund, continuation, and information design audit

**Auditor:** A3G4 (fresh non-author)
**Candidate:** `ARCHITECTURE_PHASE4_S3.md`
**Pre-audit SHA-256:** `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9`
**Scope:** Terminal-table continuation, caller-supplied showdown ranks, uniform-ante refund bound, fold/side-pot/tie/odd-chip/no-rake settlement, information noninterference, JSON feasibility

---

## 1. Terminal-table continuation contract

### Specification (§2.3, §8)

- `kind: "terminal-table"` with complete `payoff_table: Mapping[ContinuationKeyN, tuple[Fraction, ...]]`
- `ContinuationKeyN = (DealN, tuple[NPlayerPreflopPublicAction, ...])`
- Every value is exact finite N-tuple summing to zero
- Values are **complete hand utilities relative to starting stacks**; production must not add current contributions a second time
- Missing keys fail when their leaf is reached
- Root construction may optionally validate coverage by bounded tree traversal but must not claim coverage without traversing the exact bounded tree

### Assessment

**PASS.** The contract is explicit, zero-sum enforced, and correctly states that utilities are relative to starting stacks (not incremental pot deltas). The prohibition on double-counting contributions is clear. The optional coverage validation with mandatory traversal prevents false PASS claims. No blocker.

---

## 2. Caller-supplied showdown ranks

### Specification (§2.3, §8)

- `kind: "showdown-ranks"` with `showdown_ranks: Mapping[DealN, tuple[int, ...]]` and `odd_chip_order: tuple[int, ...]`
- Every compatible deal has one strict integer rank per seat, larger wins
- At every non-fold closed leaf: refund unmatched excess, build exact side-pot layers from current contributions, find eligible winners per layer, award ties with `odd_chip_order`, derive exact zero-sum chip utilities
- **Ranks are caller-supplied fixture/input data. Production never derives them from cards.**
- Permanent tests hand-declare tiny rank vectors and independently compute winners, layers, splits, odd-chip recipients; no production evaluator is used as the expected-value oracle
- This is a synthetic bounded continuation, not automatic board rollout or equity evaluation
- No rake is applied by S3; a caller that wants rake-adjusted future value supplies a zero-sum terminal table whose provenance describes its convention

### Assessment

**PASS.** The contract is unambiguous: ranks are caller input, not derived. The settlement procedure is exact and deterministic. The no-rake boundary is explicit and defers rake-adjusted continuations to the terminal-table path with documented provenance. Independent test oracles prevent circular validation. No blocker.

---

## 3. Uniform all-seat ante refund bound

### Specification (§2.4, §3, §8, post-audit correction §15)

- Config validation requires: antes are either absent or exactly one identical positive ante posted by every seat
- Unequal/per-seat-partial antes and single-seat big-blind-ante representation are outside this ledger contract and fail validation
- Terminal refund: call `refund_uncalled_excess(total_contributed)` before finalization
- The all-seats-equal ante contract guarantees that every seat's total contribution is the same dead ante plus its live street commitment, so a unique leader's total-contribution excess equals its street-commitment excess and is bounded by that street commitment
- A negative street commitment after refund is an invariant violation
- Unequal or single-seat antes are rejected at config validation rather than deferred to terminal failure

### Refund algebra verification

For N players with uniform ante `A` and street commitments `S[i]`:

```
total_contributed[i] = A + S[i]
```

After action closes, assume seat `L` is the unique leader with `S[L] = max(S)`.

Unmatched excess:
```
excess = S[L] - second_highest_S
```

Refund to leader:
```
refund[L] = excess
total_contributed'[L] = A + S[L] - excess = A + second_highest_S
street_committed'[L] = S[L] - excess = second_highest_S
```

Since `excess <= S[L]` (the second-highest is at least zero), we have:
```
street_committed'[L] = S[L] - excess >= 0
```

For all other seats `i != L`:
```
refund[i] = 0
street_committed'[i] = S[i] >= 0
```

**Bound satisfied.** The uniform-ante constraint ensures that the refund never exceeds the leader's street commitment, so `street_committed'[i] >= 0` for all seats.

### Assessment

**PASS.** The uniform-ante validation at config construction prevents the degenerate case where a refund could exceed street commitment. The algebra is sound. The rejection of unequal/single-seat antes is explicit and occurs at validation, not at terminal. No accepted config can fail only at terminal due to refund boundedness. No blocker.

---

## 4. Fold, side-pot, tie, odd-chip, no-rake settlement

### Specification (§8)

**Fold-out:**
- Build exact matched pot layers with folded eligibility
- Award every layer to its sole eligible live winner
- Compute final stacks and return exact utilities relative to starting stacks
- Covers blinds, antes, straddles, side pots, all-in contributors without continuation lookup

**Non-fold closed leaf (showdown-ranks):**
- Perform exact side-pot settlement from matched contributions and supplied ranks
- For each layer: find best rank among eligible seats, award to all seats with that rank (tie)
- Split tied awards with `odd_chip_order`: quotient to all winners, remainder to first `remainder` winners in order
- No rake applied by S3

### Integer example: 3-player side pot with tie

**Setup:**
- N=3, starting stacks `[100, 100, 100]`
- Contributions after action: `[30, 50, 50]`
- Seat 0 folded
- Showdown ranks: `[0, 10, 10]` (seats 1 and 2 tie)
- `odd_chip_order = (0, 1, 2)`

**Refund:**
- Unique leader: seat 1 or 2 (both at 50)
- No unique leader, no refund
- Matched contributions: `[30, 50, 50]`

**Layers:**
- Layer 0: amount = 30 * 3 = 90, contributors = {0,1,2}, eligible = {1,2} (0 folded)
- Layer 1: amount = (50-30) * 2 = 40, contributors = {1,2}, eligible = {1,2}

**Winners:**
- Layer 0: best rank among {1,2} is 10, winners = {1,2}
- Layer 1: best rank among {1,2} is 10, winners = {1,2}

**Awards (no rake):**
- Layer 0: 90 / 2 = 45 each, no remainder
- Layer 1: 40 / 2 = 20 each, no remainder
- Total awards: seat 1 = 65, seat 2 = 65, seat 0 = 0

**Final stacks:**
- Seat 0: (100 - 30) + 0 = 70
- Seat 1: (100 - 50) + 65 = 115
- Seat 2: (100 - 50) + 65 = 115
- Sum: 70 + 115 + 115 = 300 ✓

**Utilities:**
- Seat 0: 70 - 100 = -30
- Seat 1: 115 - 100 = +15
- Seat 2: 115 - 100 = +15
- Sum: -30 + 15 + 15 = 0 ✓

### Integer example: 4-player side pot with odd chip

**Setup:**
- N=4, starting stacks `[100, 100, 100, 100]`
- Contributions after action: `[20, 50, 50, 50]`
- No folds
- Showdown ranks: `[5, 10, 10, 8]` (seats 1 and 2 tie for best)
- `odd_chip_order = (0, 1, 2, 3)`

**Refund:**
- No unique leader (three seats at 50), no refund
- Matched: `[20, 50, 50, 50]`

**Layers:**
- Layer 0: amount = 20 * 4 = 80, contributors = {0,1,2,3}, eligible = {0,1,2,3}
- Layer 1: amount = (50-20) * 3 = 90, contributors = {1,2,3}, eligible = {1,2,3}

**Winners:**
- Layer 0: best rank = 10, winners = {1,2}
- Layer 1: best rank = 10, winners = {1,2}

**Awards (no rake):**
- Layer 0: 80 / 2 = 40 quotient, 0 remainder → seat 1 = 40, seat 2 = 40
- Layer 1: 90 / 2 = 45 quotient, 0 remainder → seat 1 = 45, seat 2 = 45
- Total awards: seat 0 = 0, seat 1 = 85, seat 2 = 85, seat 3 = 0

**Final stacks:**
- Seat 0: (100 - 20) + 0 = 80
- Seat 1: (100 - 50) + 85 = 135
- Seat 2: (100 - 50) + 85 = 135
- Seat 3: (100 - 50) + 0 = 50
- Sum: 80 + 135 + 135 + 50 = 400 ✓

**Utilities:**
- Seat 0: 80 - 100 = -20
- Seat 1: 135 - 100 = +35
- Seat 2: 135 - 100 = +35
- Seat 3: 50 - 100 = -50
- Sum: -20 + 35 + 35 - 50 = 0 ✓

### Integer example: odd chip with 3-way tie

**Setup:**
- N=3, starting stacks `[100, 100, 100]`
- Contributions: `[50, 50, 50]`
- No folds
- Ranks: `[10, 10, 10]` (3-way tie)
- `odd_chip_order = (2, 0, 1)`

**Layers:**
- Layer 0: amount = 150, contributors = {0,1,2}, eligible = {0,1,2}

**Winners:**
- Best rank = 10, winners = {0,1,2}

**Awards:**
- 150 / 3 = 50 quotient, 0 remainder
- Each seat gets 50

**Final stacks:**
- Each: (100 - 50) + 50 = 100
- Utilities: all zero ✓

### Integer example: odd chip with 2-way tie, odd pot

**Setup:**
- N=2, starting stacks `[100, 100]`
- Contributions: `[51, 51]`
- Ranks: `[10, 10]`
- `odd_chip_order = (1, 0)`

**Layers:**
- Layer 0: amount = 102, contributors = {0,1}, eligible = {0,1}

**Winners:**
- Best rank = 10, winners = {0,1}

**Awards:**
- 102 / 2 = 51 quotient, 0 remainder
- Each gets 51

**Final stacks:**
- Each: (100 - 51) + 51 = 100
- Utilities: zero ✓

**Correction:** Let me recalculate with an actual odd pot:

**Setup (corrected):**
- N=3, starting stacks `[100, 100, 100]`
- Contributions: `[50, 50, 51]`
- No folds
- Ranks: `[10, 10, 5]` (seats 0 and 1 tie)
- `odd_chip_order = (1, 0, 2)`

**Refund:**
- Unique leader: seat 2 at 51
- Second highest: 50
- Excess: 1
- Refund to seat 2: 1
- Matched: `[50, 50, 50]`

**Layers:**
- Layer 0: amount = 150, contributors = {0,1,2}, eligible = {0,1,2}

**Winners:**
- Best rank = 10, winners = {0,1}

**Awards:**
- 150 / 2 = 75 quotient, 0 remainder
- Seat 0 = 75, seat 1 = 75

**Final stacks:**
- Seat 0: (100 - 50) + 75 = 125
- Seat 1: (100 - 50) + 75 = 125
- Seat 2: (100 - 51) + 1 (refund) + 0 = 50
- Sum: 125 + 125 + 50 = 300 ✓

**Utilities:**
- Seat 0: +25
- Seat 1: +25
- Seat 2: -50
- Sum: 0 ✓

**True odd-chip example:**

**Setup:**
- N=3, contributions `[50, 50, 50]`, pot = 150
- After refund, matched pot = 151 (hypothetical, requires unequal antes which are rejected, so construct via different path)
- Actually, with uniform antes and integer street commitments, matched pot is always even when N is even and can be odd when N is odd.

**Setup (valid odd pot):**
- N=3, starting `[100, 100, 100]`
- Contributions: `[50, 51, 51]`
- No folds
- Ranks: `[5, 10, 10]`
- `odd_chip_order = (0, 1, 2)`

**Refund:**
- Leaders: seats 1 and 2 at 51
- No unique leader, no refund
- Matched: `[50, 51, 51]`

Wait, `refund_uncalled_excess` requires a unique leader. Let me re-read:

§8: "Refund the unique highest contribution above the second-highest amount."

From `game_structure.py` lines 200-213:
```python
if len(leaders) == 1:
    second = max(value for seat, value in enumerate(values) if seat != leaders[0])
    excess = highest - second
    values[leaders[0]] -= excess
    refunds[leaders[0]] = excess
```

So if there are multiple leaders (tie for highest), no refund occurs. Matched contributions remain as-is.

**Corrected:**
- Matched: `[50, 51, 51]` (no refund because two leaders)
- Total pot: 152

**Layers:**
- Layer 0: amount = 50 * 3 = 150, contributors = {0,1,2}, eligible = {0,1,2}
- Layer 1: amount = (51-50) * 2 = 2, contributors = {1,2}, eligible = {1,2}

**Winners:**
- Layer 0: best rank = 10, winners = {1,2}
- Layer 1: best rank = 10, winners = {1,2}

**Awards:**
- Layer 0: 150 / 2 = 75 quotient, 0 remainder → seat 1 = 75, seat 2 = 75
- Layer 1: 2 / 2 = 1 quotient, 0 remainder → seat 1 = 1, seat 2 = 1
- Total: seat 0 = 0, seat 1 = 76, seat 2 = 76

**Final stacks:**
- Seat 0: (100 - 50) + 0 = 50
- Seat 1: (100 - 51) + 76 = 125
- Seat 2: (100 - 51) + 76 = 125
- Sum: 50 + 125 + 125 = 300 ✓

**Utilities:**
- Seat 0: -50
- Seat 1: +25
- Seat 2: +25
- Sum: 0 ✓

**True odd-chip example (actual remainder):**

**Setup:**
- N=3, contributions `[50, 50, 51]`
- No folds
- Ranks: `[10, 10, 5]`
- `odd_chip_order = (1, 0, 2)`

**Refund:**
- Unique leader: seat 2 at 51
- Second: 50
- Excess: 1
- Refund to seat 2: 1
- Matched: `[50, 50, 50]`

**Layers:**
- Layer 0: 150, eligible {0,1,2}

**Winners:**
- Best = 10, winners = {0,1}

**Awards:**
- 150 / 2 = 75, remainder 0

Still no odd chip. Let me force it:

**Setup:**
- N=3, contributions `[33, 34, 34]`
- No folds
- Ranks: `[10, 10, 5]`
- `odd_chip_order = (1, 0, 2)`

**Refund:**
- No unique leader (two at 34), no refund
- Matched: `[33, 34, 34]`
- Total: 101

**Layers:**
- Layer 0: 33 * 3 = 99, contributors {0,1,2}, eligible {0,1,2}
- Layer 1: (34-33) * 2 = 2, contributors {1,2}, eligible {1,2}

**Winners:**
- Layer 0: best = 10, winners = {0,1}
- Layer 1: best = 10, winners = {1,2} (seat 0 not in contributors)

Wait, layer 1 contributors are {1,2}, so eligible for layer 1 are {1,2} intersect live = {1,2}. Best rank among {1,2} is 10, so winners = {1,2}.

**Awards:**
- Layer 0: 99 / 2 = 49 quotient, 1 remainder
  - Ordered winners in `odd_chip_order`: seat 1, seat 0
  - Seat 1 gets 49 + 1 = 50
  - Seat 0 gets 49
- Layer 1: 2 / 2 = 1, remainder 0
  - Seat 1 gets 1
  - Seat 2 gets 1
- Total: seat 0 = 49, seat 1 = 51, seat 2 = 1

**Final stacks:**
- Seat 0: (100 - 33) + 49 = 116
- Seat 1: (100 - 34) + 51 = 117
- Seat 2: (100 - 34) + 1 = 67
- Sum: 116 + 117 + 67 = 300 ✓

**Utilities:**
- Seat 0: +16
- Seat 1: +17
- Seat 2: -33
- Sum: 0 ✓

**Odd chip awarded correctly to seat 1 (first in `odd_chip_order` among winners {0,1}).**

### Assessment

**PASS.** The settlement procedure is exact, deterministic, and zero-sum. Fold-out, side pots, ties, and odd-chip allocation are correctly specified. The no-rake boundary is explicit. Integer examples verify correctness. No blocker.

---

## 5. Information noninterference

### Specification (§9)

An acting player's information key includes only:
- version/rule identity and N
- owner seat and owner's private combo
- button, starting stacks, forced posts, straddle variant, immutable sizing-rule identity
- pot, public commitments/contributions/remaining/fold flags
- pending order, raise entitlements, last increment, raise count, acting seat
- actor-labelled public history
- continuation kind, source, and provenance

It excludes:
- opponent cards
- deal index/order
- hidden payoff-table values
- hidden showdown ranks
- traversal state

Varying opponents or hidden continuation contents while owner/public state is fixed must preserve the key; varying the owner's combo or a legal-action-affecting public field must change it. Infosets must also preserve identical legal action tuples.

### Assessment

**PASS.** The information key contract is explicit and complete. Opponent cards, deal order, and hidden continuation values are excluded. The preservation and variation rules are clear. The requirement that infosets preserve identical legal action tuples is stated. No blocker.

---

## 6. JSON feasibility

### Specification (§11)

Strict v4 API operation `solve-nplayer-preflop` with payload:
- config version, N, button, starting stacks
- ordered forced-post objects and straddle variant
- per-seat weighted ranges
- strict sizing-rule objects
- max raises/deals/nodes and short-all-in policy
- one continuation object:
  - terminal-table entries as JSON lists of `{deal, history, values}`, or
  - showdown entries as `{deal, ranks}` plus odd-chip order
- algorithm, iterations, null seed, diagnostic flag, pure-strategy cap

History JSON entries explicitly contain actor, action kind, and integer amount. Unknown/missing fields, bool numerics, nonfinite values, malformed arrays, duplicate continuation keys/deals, unsupported seeds/algorithms, and bound violations fail closed. Conversion creates detached typed values.

### Assessment

**PASS.** The JSON contract is explicit and complete. Continuation objects are representable as JSON with explicit structure. History entries are actor-labelled with kind and amount. Validation is strict and fails closed. No blocker.

---

## 7. Post-audit hash verification

```
sha256sum /home/genomix-node/poker-solver/ARCHITECTURE_PHASE4_S3.md
```

Expected: `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9`

---

## Verdict

**PASS.** All audited contracts are explicit, complete, and feasible. No accepted configuration can fail only at terminal. Integer examples verify settlement correctness. Information noninterference is well-defined. JSON representation is explicit and strict.

**Blockers:** None.

---

**Post-audit SHA-256:** (to be verified after write)
