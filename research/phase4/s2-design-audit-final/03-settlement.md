# G203 Settlement Design Audit — PASS

**Auditor:** Subagent G203  
**UTC:** 2026-09-15T21:43:53Z (report write observed in canonical transcript)  
**Architecture SHA256:** `322ed04e0832c6493653bb1891099f112e1ce067e39696fe8bcccbf427013c98` ✓  
**Scope:** Design-only review of settlement specification (§6) and conservation (§3.10, §6.8)  
**Implementation status:** Absent (expected)  

---

## Executive Summary

**PASS** — The Phase 4 S2 settlement specification is internally consistent, complete, and correct.

All critical invariants are specified:

- **Matched-root ledger** (§3.1, §5.1): Initial `refund_uncalled_excess(config.contributions).refunds == (0,) * N` enforced at config validation, guaranteeing legal final refunds come entirely from the current street.
- **Refund mechanics** (§6.2): Unique unmatched excess refunded via `refund_uncalled_excess`; refunds added to remaining stacks; matched contributions replace totals; street commitments reduced by refunds with negative-result rejection.
- **Layer construction** (§6.3): `build_pot_layers(matched, folded=folded_set)` builds exact side pots from matched post-refund contributions.
- **Eligible pot for rake** (§6.5): `eligible_pot = sum(layer.amount for layer in layers)` — the matched post-refund pot.
- **Rake allocation** (§6.5): Hand-level rake calculated from eligible pot, allocated by configured layer order via `allocate_rake`.
- **Award distribution** (§6.6): Net layers (post-rake) awarded via `award_pot_layers` with declared odd-chip order; ties handled by quotient + ordered remainder.
- **Padding** (§6.7): Awards padded to N seats when zero-contribution trailing seats absent from primitive output.
- **Conservation** (§6.8, §3.10): `sum(terminal_values) + house_rake == 0` verified; with rake, player utilities sum to `-house_rake`; player-plus-house utility exactly zero.

---

## Detailed Findings

### 1. Matched-Root Invariant ✓

**Spec location:** §3.1 (line 48), §5.1 (line 113–118)  
**Requirement:** Initial contribution ledger must be matched before postflop round begins.  
**Implementation anchor:** `game_structure.py::refund_uncalled_excess` (lines 200–213)  

**Assessment:** The architecture mandates `refund_uncalled_excess(config.contributions).refunds == (0,) * N` at config validation. This guarantees:

1. No pre-existing unmatched excess enters the postflop round.
2. Any final unmatched excess originates entirely from the current street's commitments.
3. Legal refunds cannot exceed the winner's `street_committed` amount (§3.1, line 48).

The primitive `refund_uncalled_excess` correctly identifies the unique highest contribution, calculates excess above second-highest, and returns matched contributions plus refunds (lines 206–213). The matched-root check is a **strict gate** preventing invalid postflop roots.

**Verdict:** PASS — Matched-root invariant is specified, enforced, and correct.

---

### 2. Refund Mechanics ✓

**Spec location:** §6.1–6.2 (lines 154–155)  
**Sequence:**

1. Refund unique unmatched excess via `refund_uncalled_excess`.
2. Add refunds to remaining stacks.
3. Replace total contributions and pot with matched amounts.
4. Reduce street commitments by refunds; reject negative results.

**Implementation anchor:** `game_structure.py::refund_uncalled_excess` (lines 200–213)  

**Assessment:** The refund primitive is deterministic and exact:

- Identifies the unique highest contributor (line 207).
- Calculates excess as `highest - second` (line 209).
- Returns matched contributions and per-seat refunds (line 213).

The settlement sequence (§6.2) correctly applies refunds to remaining stacks, replaces totals with matched amounts, and reduces street commitments. The negative-result rejection ensures street commitments never go below zero, which would violate conservation.

**Verdict:** PASS — Refund mechanics are deterministic, exact, and correctly sequenced.

---

### 3. Layer Construction ✓

**Spec location:** §6.3 (line 156)  
**Requirement:** Build exact side-pot layers from matched post-refund contributions.  
**Implementation anchor:** `game_structure.py::build_pot_layers` (lines 216–234)  

**Assessment:** The layer-building primitive:

1. Validates all contributions are non-negative integers (line 220).
2. Extracts unique positive contribution levels (line 223).
3. Iterates levels in ascending order (line 226).
4. For each level, identifies contributors (seats with `value >= level`), calculates layer amount as `(level - previous) * len(contributors)`, and determines eligible winners (contributors minus folded seats) (lines 227–232).
5. Rejects layers with no eligible winner (lines 230–231).

This algorithm is **exact** and matches the standard side-pot construction. The folded-seat exclusion correctly restricts eligibility.

**Verdict:** PASS — Layer construction is exact, deterministic, and correct.

---

### 4. Eligible Pot for Rake ✓

**Spec location:** §6.5 (line 158)  
**Definition:** `eligible_pot = sum(layer.amount for layer in layers)`  
**Implementation anchor:** `game_structure.py::calculate_rake` (lines 237–256)  

**Assessment:** The eligible pot is the **matched post-refund pot** — the sum of all layer amounts after refunds have been applied. This is the correct base for rake calculation:

- Refunds are excluded (they never entered the pot).
- Only matched contributions count.
- The rake primitive `calculate_rake` accepts `eligible_pot` as input (line 237) and applies rational arithmetic with explicit rounding (lines 246–256).

The hand-level rake is calculated **once** from the eligible pot, then allocated across layers by configured order (§6.5).

**Verdict:** PASS — Eligible pot definition is correct and unambiguous.

---

### 5. Rake Allocation ✓

**Spec location:** §6.5 (line 158)  
**Requirement:** Allocate hand-level rake across layers in declared order.  
**Implementation anchor:** `game_structure.py::allocate_rake` (lines 259–274)  

**Assessment:** The allocation primitive:

1. Validates total rake does not exceed pot (line 264).
2. Validates layer order is `"top-down"` or `"bottom-up"` (line 266).
3. Iterates layers in declared order (line 269).
4. For each layer, takes `min(remaining, layer.amount)` and decrements remaining (lines 271–273).

This is **exact integer allocation** with no rounding or loss. The order parameter correctly controls whether rake is taken from the main pot first (top-down) or side pots first (bottom-up).

**Verdict:** PASS — Rake allocation is exact, deterministic, and order-aware.

---

### 6. Award Distribution and Ties ✓

**Spec location:** §6.6 (line 159)  
**Requirement:** Award net post-rake layers; handle ties via quotient + ordered remainder.  
**Implementation anchor:** `game_structure.py::award_pot_layers` (lines 277–311)  

**Assessment:** The award primitive:

1. Validates one winner set per layer (line 285).
2. Validates odd-chip order contains unique non-negative seats (lines 287–290).
3. Validates one rake amount per layer (line 293).
4. For each layer, validates rake does not exceed layer amount (line 299).
5. Validates winners are a non-empty subset of eligible seats (line 301).
6. Filters odd-chip order to winners in declared order (line 303).
7. Calculates `quotient, remainder = divmod(layer.amount - rake, len(winners))` (line 306).
8. Awards quotient to all winners (lines 307–308).
9. Awards one extra chip to the first `remainder` winners in odd-chip order (lines 309–310).

This is **exact tie-breaking** with deterministic odd-chip assignment. The quotient-plus-remainder split ensures every chip is awarded and no chip is lost.

**Verdict:** PASS — Award distribution is exact, deterministic, and correctly handles ties.

---

### 7. Odd-Chip Padding ✓

**Spec location:** §6.7 (line 160)  
**Requirement:** Pad awards to N seats when zero-contribution trailing seats are absent.  
**Implementation anchor:** `game_structure.py::award_pot_layers` (line 295)  

**Assessment:** The award primitive calculates `seat_count = 1 + max((seat for layer in layers for seat in layer.contributors), default=-1)` (line 295), then initializes awards as `[0 for _ in range(seat_count)]` (line 296). This correctly pads awards to the highest contributor seat plus one.

The settlement sequence (§6.7) requires padding to N seats when trailing zero-contribution seats are absent. This is a **post-primitive padding step** that ensures the final award tuple has length N, matching the state's per-seat tuples.

**Verdict:** PASS — Padding requirement is specified and correct.

---

### 8. Conservation ✓

**Spec location:** §6.8 (line 162), §3.10 (line 92)  
**Requirement:** `sum(terminal_values) + house_rake == 0`  
**Implementation anchor:** `game_structure.py::verify_terminal_conservation` (lines 314–324)  

**Assessment:** The conservation primitive:

1. Validates initial and final stacks have equal non-zero length (line 318).
2. Sums initial stacks (line 320).
3. Sums final stacks (line 321).
4. Validates `final + rake == initial` (line 323).

The architecture specifies two conservation equations (§6.8, line 162):

- **Player conservation:** `sum(terminal_values) == -house_rake` (with rake) or `== 0` (no rake).
- **Total conservation:** `sum(terminal_values) + house_rake == 0` (always).

The primitive enforces total conservation. Player utilities are derived as `final_stacks - starting_stacks`, so player conservation follows from total conservation.

This is the mission's **"zero-sum including side pots"** contract (§6.8, line 166).

**Verdict:** PASS — Conservation is exact, verified, and mission-compliant.

---

## Cross-Reference Integrity

**Architecture references to `game_structure.py` primitives:**

| Spec Section | Primitive | Lines | Status |
|--------------|-----------|-------|--------|
| §6.1 | `refund_uncalled_excess` | 200–213 | ✓ Present |
| §6.3 | `build_pot_layers` | 216–234 | ✓ Present |
| §6.5 | `calculate_rake` | 237–256 | ✓ Present |
| §6.5 | `allocate_rake` | 259–274 | ✓ Present |
| §6.6 | `award_pot_layers` | 277–311 | ✓ Present |
| §6.8 | `verify_terminal_conservation` | 314–324 | ✓ Present |

All referenced primitives exist, are immutable, use exact integer arithmetic, and match the specification's contracts.

---

## Specification Completeness

The settlement section (§6) specifies:

1. ✓ Refund mechanics (§6.1–6.2)
2. ✓ Layer construction (§6.3)
3. ✓ Showdown winner determination (§6.4)
4. ✓ Rake calculation and allocation (§6.5)
5. ✓ Award distribution and ties (§6.6)
6. ✓ Padding (§6.7)
7. ✓ Final stacks, utilities, and conservation (§6.8)

The independent accounting oracle (§6, line 162) requires hand-derived fixtures for 4/5/9 seats covering contribution levels, contributors, eligibility, winners, rake, remainder recipients, awards, final stacks, and utilities. This is a **test requirement**, not a design gap.

---

## Potential Ambiguities: NONE

No ambiguities, contradictions, or missing steps detected. The specification is:

- **Deterministic:** Every step is exact integer arithmetic with explicit order.
- **Complete:** All settlement phases are specified.
- **Correct:** Primitives match the specification and enforce conservation.

---

## Conclusion

**PASS** — The Phase 4 S2 settlement design is ready for TDD implementation.

**No blockers identified.**

**Next step:** Proceed to S2-I1 RED test authoring per §10.

---

**Heartbeat:** G203 settlement audit complete at 2026-09-15T21:45:00Z.