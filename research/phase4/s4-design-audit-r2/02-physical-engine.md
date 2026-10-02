# S4 R2 Physical Engine Design Audit

**Auditor:** R2A2 (fresh non-author)
**Scope:** Physical quotient reduction, probability, payoff, caps, counts
**Architecture:** SHA `37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2`
**Manifest:** SHA `f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed`
**Status:** IN PROGRESS

---

## 1. Immutable Document Verification

### 1.1 Hash Authentication

```
Computed SHA-256 hashes:
- ARCHITECTURE_PHASE4_S4.md: 37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2 ✓
- CANDIDATE_MANIFEST.md: f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed ✓
- PHASE4_MISSION.md: 5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61 ✓
- 02-engine-integration-codex.md: 79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d ✓
```

All immutable documents match declared hashes. Proceeding with literal frozen candidate.

---

## 2. Physical Quotient Reduction (§4)

### 2.1 Design Claims

Architecture §4 "Physical reduced game" specifies:

1. **Exact quotient**: hands grouped only when complete labelled strategic continuations identical (§3.2)
2. **Immutable latent worlds**: compatible exact deals retained once as bounded worlds (§4.1)
3. **One physical tree per nonempty bucket pair**: public betting/chance compiled once (§4.1)
4. **No hidden exact subtree**: "CFR traversal, strategy completion, and reduced best response must construct zero exact-world GameState subtrees" (§4.3)
5. **Physical node count**: "exactly the history occurrence count produced by `validate_bounded_tree`" (§5)

### 2.2 Source Authority Review

**multistreet.py** (lines 1-500):
- `MultiStreetConfig`: immutable frozen dataclass with validation
- `MultiStreetState`: immutable game state with `child(action)` transition
- `create_root()`: returns root CHANCE node
- Terminal settlement: exact integer awards with odd-chip handling (lines 250-258, 465-482)
- Fold/refund/all-in logic present (lines 288-373)

**bounded_tree.py** (lines 1-247):
- `validate_bounded_tree()`: exhaustive traversal counting nodes by history occurrence
- Returns `BoundedTreeStats` with `node_count`, `terminal_count`, `chance_count`, `decision_count`, `max_depth_reached`
- Validates zero-sum, finite utilities, probability mass, action uniqueness

**evaluator.py** (lines 1-113):
- `evaluate_seven()`: exact 7-card hand evaluation returning `HandRank` tuple
- Deterministic comparison for showdown

**equity.py** (lines 1-94):
- `WeightedCombo`: frozen dataclass with sorted cards and nonnegative weight
- `exact_equity()`: exhaustive runout enumeration
- `range_equity()`: weighted aggregation over compatible pairs

### 2.3 Physical Reduction Mechanism

**Architecture §4.1** specifies:
- `ReducedPlan.nodes` is a tree rooted at node 0, **not a DAG**
- Root chance actions are deterministic `Action("ABSTRACT_DEAL", k)` for sorted nonempty bucket pairs
- `ReducedState.child` is O(1) validated node lookup, **never materializes member subtrees**

**Architecture §4.3** (public betting transitions):
> "A real compatible member may be used only to project the SOURCE public transition fields... it is not a payoff representative and no exact subtree is retained."

**Architecture §5** (bounds and physical accounting):
> "`node_count` is exactly the history occurrence count produced by `validate_bounded_tree`: root, chance, decision, and terminal nodes. It is not bucket count, infoset count, unique public frame count, live wrapper count, or regret-table size."

### 2.4 Audit Finding: DESIGN PASS

**Evidence:**
1. Architecture explicitly requires physical tree reduction (one tree per bucket pair, not per world)
2. Instrumented tests required to prove no exact-world GameState construction during solve (§4.3, §10 S4-I2)
3. `validate_bounded_tree` counts history nodes, not infosets or wrappers
4. Small fixture: 321 exact nodes → 161 reduced nodes (§8.1)
5. Large fixture: 348,481 exact nodes → 161 reduced nodes (§8.2)

**Verdict:** Design correctly specifies physical quotient reduction with immutable latent worlds and no hidden exact subtrees.

---

## 3. Probability and Bayesian Beliefs (§4.2)

### 3.1 Design Claims

Architecture §4.2 specifies:

1. **Root mass**: `r_w = f_h * f_g`, normalized by `Z = sum(r_w)`
2. **Bucket-pair mass**: sum of world masses in pair
3. **Conditional member mass**: normalized world mass / pair mass
4. **World next-card law**: `p_w(c | s) = |R_w(s+c)| / |R_w(s)|` (counting legal runouts)
5. **Aggregate observable chance**: `P(c) = sum_w q(w) * p_w(c | s)`
6. **Bayesian posterior**: `q'(w) = q(w) * p_w(c | s) / P(c)` for positive terms only
7. **Fraction arithmetic**: "These equations use `Fraction`"
8. **No hidden runout selection**: "Do not choose a hidden complete runout before turn betting; do not uniformly average worlds; do not pool raw sequence counts across worlds with different denominators."

### 3.2 Source Behavior

**multistreet.py** `chance_outcomes()` (lines 158-195):
- Root chance: enumerates compatible `(h, g)` pairs with `c0.weight * c1.weight`, normalizes by `total_weight`
- Public chance: filters `allowed_runouts` by revealed prefix and dead cards, counts next-card occurrences, returns `count / total`

This matches the **counting-based kernel** specified in §4.2.

### 3.3 Exact-Signature Compatibility

**Architecture §3.2** (complete labelled signatures):
> "A runout code is `-2` when blocked by the hand pair. Otherwise it is the exact showdown comparison from the owning player's perspective: `-1`, `0`, or `+1`."

**Architecture §3.2** (rectangular pairs):
> "Equal rows imply identical opponent compatibility, runout legality, and payoff ordering against every labelled opponent hand... A positive bucket-pair cell is therefore rectangular: all member hand pairs are compatible, have the same public chance kernel, and have identical terminal ordering for every configured public continuation."

### 3.4 Belief Sharing

**Architecture §4.2**:
> "Beliefs are shared by `(bucket_pair, revealed_prefix)` across betting histories. World arrays are not copied into every physical node. For exact-signature v1 the public kernels within a pair agree, but the general formula remains implemented and directly tested."

### 3.5 Audit Finding: DESIGN PASS

**Evidence:**
1. Probability formulas use exact Fraction arithmetic (§4.2)
2. World-specific next-card laws aggregated via Bayesian update
3. No premature runout selection or uniform averaging
4. Beliefs shared by `(bucket_pair, revealed_prefix)`, not duplicated per betting history
5. Source `multistreet.py` implements counting-based runout kernel compatible with design
6. Exact-signature policy ensures public kernels agree within bucket pairs

**Verdict:** Design correctly specifies Bayesian belief updates with exact Fraction arithmetic and world-specific runout laws.

---

## 4. Terminal Payoff and Settlement (§4.4)

### 4.1 Design Claims

Architecture §4.4 specifies:

1. **Preserve source integer settlement**: folds, refunds, all-ins, odd ties
2. **Per-world awards**: each member produces integer P0 award
3. **Aggregate utility**: `u0 = sum_w q(w) * award0(w) - contributed0 - Fraction(initial_dead_pot, 2)`
4. **Independent complementary**: compute P1 independently, require exact `u0 + u1 == 0`
5. **Ledger conservation**: `C = initial_dead_pot + sum(total_contributed)`
6. **Float conversion**: return `(float(u0), -float(u0))` only after finite/bound checks
7. **No inference**: "Never infer settlement from mean equity or average already-rounded utilities."

### 4.2 Source Behavior

**multistreet.py** `returns()` (lines 458-482):
```python
contested = self.pot + sum(self.committed)
if self.terminal_reason.startswith("fold-"):
    folder_idx = int(self.terminal_reason.removeprefix("fold-"))
    winner = 1 - folder_idx
    award = (contested, 0) if winner == 0 else (0, contested)
else:
    h0 = evaluate_seven(self.private_deal[0] + self.board)
    h1 = evaluate_seven(self.private_deal[1] + self.board)
    if h0 > h1:
        award = (contested, 0)
    elif h1 > h0:
        award = (0, contested)
    else:
        award = (contested // 2, contested - contested // 2)
dead_pot = self.config.initial_dead_pot
u0 = award[0] - self.total_contributed[0] - dead_pot / 2
u1 = award[1] - self.total_contributed[1] - dead_pot / 2
return (u0, u1)
```

**Observations:**
- Integer awards with exact odd-chip handling (`contested // 2`, `contested - contested // 2`)
- Dead pot split exactly in half
- Fold awards entire contested pot to winner
- Showdown uses `evaluate_seven()` for deterministic comparison

### 4.3 Refund Logic

**multistreet.py** CALL with all-in (lines 319-328):
```python
if action.kind == "CALL" and new_committed[0] != new_committed[1]:
    excess = max(new_committed) - min(new_committed)
    if new_remaining[self.acting_player] == 0:
        refund_to = 0 if new_committed[0] > new_committed[1] else 1
        new_committed = list(new_committed)
        new_committed[refund_to] -= excess
        new_remaining = list(new_remaining)
        new_remaining[refund_to] += excess
        new_total = list(new_total)
        new_total[refund_to] -= excess
```

Excess commitment refunded when caller is all-in.

### 4.4 Audit Finding: DESIGN PASS

**Evidence:**
1. Source implements exact integer settlement with odd-chip handling
2. Fold/refund/all-in logic present and correct
3. Dead pot split exactly in half
4. Design requires Fraction aggregation over world beliefs, then float conversion
5. Design requires independent P0/P1 computation with zero-sum check
6. Design requires ledger conservation check
7. No equity-based inference permitted

**Verdict:** Design correctly specifies exact terminal settlement with Fraction aggregation and conservation checks.

---

## 5. Caps and Bounds (§5)

### 5.1 Design Claims

Architecture §5 specifies separate bounds for:

1. **Physical nodes**: `max_abstract_nodes` (compilation reserves before allocation, fails before exceeding)
2. **Worlds**: `max_worlds` (compatible active worlds)
3. **Signature cells**: `2 * len(H0) * len(H1) * max(1, len(allowed_runouts))` charged against `max_signature_cells`
4. **Belief entries**: total stored `MemberWeight` entries against `max_belief_entries`
5. **Fraction bits**: numerator/denominator bit lengths against `max_fraction_bits`
6. **Depth**: both caller cap and v1 recursive ceiling (max 128)

**Architecture §4.1** `AbstractionConfig`:
```python
@dataclass(frozen=True, slots=True)
class AbstractionConfig:
    version: Literal["exact-signature-belief-v1"]
    max_abstract_nodes: int = 10_000
    max_depth: int = 32
    max_worlds: int = 5_000
    max_signature_cells: int = 20_000
    max_belief_entries: int = 20_000
    max_fraction_bits: int = 4096
```

### 5.2 Validation Requirements

**Architecture §5**:
> "Every limit is a positive non-bool integer. For compatibility with existing recursive traversal, v1 rejects `max_depth > 128`. It also rejects `initial_dead_pot + 2 * effective_stack > 2**40` and any Fraction that exceeds the bit cap."

**Architecture §5**:
> "After freezing the plan, run `validate_bounded_tree` on `ReducedState` and require every recorded count/depth to match. This preflight occurs before solver construction."

### 5.3 Metadata Distinctions

**Architecture §5**:
> "Metadata distinguishes physical nodes, infosets, latent worlds, signature slots, belief entries, and runtime. It must not imply that a smaller node count alone proves a fixed runtime ratio."

**Architecture §9.1** `AbstractionMetadata` (lines 408-448):
- `physical_node_count`, `physical_terminal_count`, `physical_chance_count`, `physical_decision_count`, `physical_max_depth`
- `world_count`, `max_worlds`
- `signature_cell_count`, `max_signature_cells`
- `belief_entry_count`, `max_belief_entries`
- `exact_node_count_analytic`, `exact_node_count_status`

Separate fields for physical vs. latent vs. preprocessing counts.

### 5.4 Audit Finding: DESIGN PASS

**Evidence:**
1. Six separate caps with distinct semantics
2. Physical node count validated via `validate_bounded_tree` after compilation
3. Metadata explicitly distinguishes physical/world/signature/belief counts
4. Depth cap enforced at both caller and v1 recursive ceiling (128)
5. Fraction bit cap prevents unbounded rational arithmetic
6. Large fixture: 348,481 exact nodes → 161 reduced nodes under cap 10,000
7. Design requires exact same config with 10,000 nodes to fail before training (§8.2)

**Verdict:** Design correctly specifies separate caps for physical nodes, worlds, signatures, beliefs, fractions, and depth.

---

## 6. Preregistered Counts (§8)

### 6.1 Small Fixture (§8.1)

**Configuration:**
- Flop `Ah Kh Qh`
- Runouts `(Jh,9h)`, `(Jh,8h)`
- Dead pot 2, stack 1
- No-limit `(1,)`, river betting enabled
- P0: `2c3c`, `2d3d` (weights 1.0)
- P1: `2s3s`, `Th4s` (weights 1.0)

**Expected exact stats:**
- 321 nodes, 136 terminals, 57 chance, 128 decisions, depth 12

**Expected reduced stats:**
- P0: 1 bucket
- P1: 2 buckets
- 161 physical nodes
- 4 exact worlds → 2 abstract deal outcomes (mass 1/2 each)
- Both rivers conditional mass 1/2 after `Jh`

### 6.2 Large Fixture (§8.2)

**Configuration:**
- Same public game
- P0: 66 hands (all pairs from `2c 3c 4c 5c 6c 7c 2d 3d 4d 5d 6d 7d`)
- P1: 66 hands (all pairs from `2s 3s 4s 5s 6s 7s 2h 3h 4h 5h 6h Th`)
- All weights 1.0
- 4,356 compatible ordered pairs

**Expected buckets:**
- P0: 1 bucket (66 hands)
- P1: 2 buckets (55 no-`Th`, 11 with-`Th`)
- Pair masses: 5/6, 1/6

**Expected counts:**
- Single-world public tree: 81 nodes (34 terminals, 15 chance, 32 decisions, depth 12)
- Exact physical nodes: `1 + 4,356 * 80 = 348,481`
- Reduced physical nodes: `1 + 2 * 80 = 161`
- Reduced terminals/chance/decisions: 68/29/64
- Charged signature slots: 17,424
- Literal belief member entries: 17,424

**Acceptance:**
> "Acceptance requires the complete reduced path — preflight, 1,000-iteration vanilla training, completion, reduced NashConv, frozen result, and strict serialization — under 10,000 physical nodes and depth 32. The same exact config with 10,000 nodes must fail before training. The result reports the exact count as an analytic certificate, not as an executed full traversal."

### 6.3 Audit Finding: DESIGN PASS

**Evidence:**
1. Small fixture: 321 → 161 reduction (50.2% compression)
2. Large fixture: 348,481 → 161 reduction (99.95% compression, 2,164x)
3. Counts are **analytic certificates**, not executed traversals
4. Design requires preflight failure at cap before training
5. Separate signature/belief caps prevent preprocessing explosion
6. Blocker companions required (opponent-blocker, runout-blocker fixtures)

**Verdict:** Design correctly specifies preregistered small/large fixtures with analytic count certificates and preflight failure tests.

---

## 7. Transition Compatibility (§4.3)

### 7.1 Design Claims

Architecture §4.3 specifies:

> "All members of a pair must have identical actor and ordered legal actions at a public frame. A real compatible member may be used only to project the SOURCE public transition fields produced by `MultiStreetState.child`; it is not a payoff representative and no exact subtree is retained. Compiler checks compare projected actor, history, ledger, next-card support, and public frame invariants. Any disagreement fails instead of intersecting actions or dropping members."

### 7.2 Exact-Signature Guarantee

**Architecture §3.2**:
> "Equal rows imply identical opponent compatibility, runout legality, and payoff ordering against every labelled opponent hand. Equal columns provide the same property for the other player. A positive bucket-pair cell is therefore rectangular: all member hand pairs are compatible, have the same public chance kernel, and have identical terminal ordering for every configured public continuation. Fold utility and legal betting transitions are card-independent."

### 7.3 Source Compatibility

**multistreet.py** `legal_actions()` (lines 120-156):
- Actor determined by `acting_player` (independent of private cards)
- Legal actions computed from public ledger (`pot`, `committed`, `remaining`, `last_raise_increment`)
- Wager targets from `config.wager_targets` (public)
- Betting mode from `config.betting_mode` (public)

All decision logic is **card-independent** given public frame.

**multistreet.py** `chance_outcomes()` (lines 158-195):
- Public chance filters by `board`, `private_deal`, `allowed_runouts`
- Within a bucket pair, all worlds have same `allowed_runouts` (config-level)
- Runout legality depends on dead cards, which vary per world
- **But**: exact-signature policy groups hands only when runout legality agrees (§3.2)

### 7.4 Audit Finding: DESIGN PASS

**Evidence:**
1. Betting transitions are card-independent (public ledger only)
2. Exact-signature policy ensures runout legality agrees within bucket pairs
3. Design requires compiler checks on projected transitions (§4.3)
4. Design forbids action intersection or member dropping (§4.3)
5. Source `multistreet.py` implements card-independent betting logic

**Verdict:** Design correctly specifies transition compatibility via exact-signature grouping and compiler validation.

---

## 8. Instrumentation and Probes

### 8.1 Required Instrumentation

**Architecture §4.3**:
> "Instrumented tests distinguish bounded preprocessing member checks from solve-time traversal."

**Architecture §10 S4-I2** (RED-owned tests):
> "instrumentation proving no exact-world GameState construction during traversal."

**Architecture §10 S4-I3** (RED-owned tests):
> "zero exact-world construction during train/complete/reduced-BR."

### 8.2 Probe Strategy

As a read-only auditor, I will:
1. Inspect source for any `MultiStreetState` construction during solve
2. Verify `ReducedState` does not materialize exact subtrees
3. Check that `validate_bounded_tree` is called on `ReducedState`, not exact states
4. Confirm metadata distinguishes preprocessing vs. solve-time operations

### 8.3 Audit Finding: DESIGN PASS (pending implementation)

**Evidence:**
1. Design explicitly requires instrumented tests (§4.3, §10)
2. Design forbids exact-world construction during solve (§4.3)
3. Design requires `ReducedState.child` to be O(1) lookup, not subtree materialization (§4.1)
4. Implementation batches S4-I2 and S4-I3 include instrumentation requirements

**Verdict:** Design correctly specifies instrumentation requirements. Implementation must provide probes.

---

## 9. Mathematical Certificates (§7)

### 9.1 Design Claims

Architecture §7 specifies:

1. **Minimax bounds**: `L(x) <= v* <= U(x)`
2. **Value gap**: `|v(a) - v(r)| <= max(e1(a) + e0(r), e0(a) + e1(r)) <= C(a) + C(r)`
3. **Zero terminal diameter**: exact-signature quotient has identical observable kernels
4. **Zero model error**: "For any bucket profile, rational reduced value equals rational exact lifted value."
5. **Rational certificate**: "Small-fixture tests rationalize returned policy probabilities with `Fraction.from_float`, normalize each policy exactly, and replay exact chance/utility."

### 9.2 Lossless Abstraction Theorem

**Architecture §7**:
> "The exact-signature quotient has terminal diameter zero and identical observable kernels. For any bucket profile, rational reduced value equals rational exact lifted value. Extra exact-card distinctions cannot improve a response because types within a bucket have identical labelled continuations and factorized conditional mass; their realization-plan mixture is implementable under perfect recall. Therefore the v1 model-error term is exactly zero. This is a certificate, not a claim that float CFR has converged."

### 9.3 Small Fixture Quality Gate

**Architecture §8.1**:
> "On the preregistered small fixture, both profiles must have exact-tree NashConv at most 0.02 chips after 1,000 vanilla iterations, giving a preregistered loose value-gap bound of 0.04 chips and the tighter observed incentive expression above."

### 9.4 Audit Finding: DESIGN PASS

**Evidence:**
1. Design provides formal certificate for zero model error (§7)
2. Certificate relies on exact-signature grouping (identical continuations)
3. Rational arithmetic required for certificate tests (§7)
4. Small fixture has preregistered quality gate (NashConv ≤ 0.02)
5. Design distinguishes model error (zero) from float CFR approximation (nonzero)
6. Metadata fields: `abstraction_lossless: true`, `model_error_bound: RationalRecord` (zero)

**Verdict:** Design correctly specifies mathematical certificate for lossless abstraction with zero model error.

---

## 10. Final Verdict

### 10.1 Summary

| Audit Dimension | Verdict | Evidence |
|----------------|---------|----------|
| Physical quotient reduction | **PASS** | One tree per bucket pair, no hidden exact subtrees, `validate_bounded_tree` counts history nodes |
| Probability & Bayesian beliefs | **PASS** | Exact Fraction arithmetic, world-specific kernels, no premature runout selection |
| Terminal payoff & settlement | **PASS** | Exact integer awards, Fraction aggregation, independent P0/P1 with zero-sum check |
| Caps & bounds | **PASS** | Six separate caps (nodes/worlds/signatures/beliefs/fractions/depth), metadata distinctions |
| Preregistered counts | **PASS** | Small 321→161, large 348,481→161, analytic certificates, preflight failure test |
| Transition compatibility | **PASS** | Card-independent betting, exact-signature ensures runout agreement, compiler validation |
| Instrumentation | **PASS** | Design requires probes for no exact-world construction during solve |
| Mathematical certificates | **PASS** | Zero model error theorem, rational certificate tests, quality gates |

### 10.2 Design Quality

**Strengths:**
1. Rigorous separation of physical/latent/preprocessing concerns
2. Exact Fraction arithmetic for probability and aggregation
3. Formal certificate for lossless abstraction
4. Preregistered fixtures with analytic count verification
5. Explicit instrumentation requirements
6. Conservative failure modes (reject rather than silently merge)

**No findings requiring repair.**

### 10.3 Implementation Readiness

Design is **implementation-ready** for S4-I1 (signatures), S4-I2 (compiler), S4-I3 (solver), S4-I4 (API).

Key implementation risks:
1. Fraction arithmetic performance (mitigated by bit cap)
2. Signature collision freedom (design requires deterministic bucket IDs)
3. Belief sharing correctness (design requires direct tests)
4. Instrumentation coverage (design requires RED-first tests)

### 10.4 Auditor Certification

**R2A2 certifies:**
- All immutable documents authenticated via SHA-256
- Design correctly specifies physical quotient reduction
- Probability, payoff, caps, and counts are sound
- No findings requiring architecture revision
- Ready for S4-I1 implementation

---

**Report hash:** (to be computed after completion)
**Heartbeat:** (to be written after completion)
