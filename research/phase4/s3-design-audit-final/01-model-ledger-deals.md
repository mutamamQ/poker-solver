# S3 Design Audit A3F1 — Model, Ledger, Deals, N=2 Projection

**Auditor:** A3F1 (fresh non-author BryantGPT subagent)  
**Candidate:** `ARCHITECTURE_PHASE4_S3.md`  
**Pre-audit SHA-256:** `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9`  
**Post-audit SHA-256:** `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9`  
**Audit scope:** Typed config/model, N=2..9 positions, exact posts, ante validation/algebra, deal bounding/masses, N=2 projection, refund bound proof.

---

## Executive Summary

**VERDICT: PASS**

The S3 architecture candidate is internally consistent, complete for its stated bounded scope, and ready for TDD implementation. All mandatory design elements are present and correct:

- Typed immutable contracts for 2–9 players with strict validation
- Uniform all-seat or absent ante ledger with exact forced posts
- Bounded deterministic deal enumeration with exact rational masses
- Explicit N=2 projection semantics (public trace alignment, not type equality)
- Refund boundedness proven by config validation and ledger algebra

No blocking gaps, contradictions, or unrepresentable configurations were found within the accepted scope.

---

## 1. Typed Config and Model (§2, §15)

### 1.1 Public Contracts

**Assessed:** Section 2 defines eight additive public symbols with frozen, slotted dataclasses:

- `NPlayerPreflopConfig` (§2.4): version, N ∈ [2,9], button, stacks, posts, straddle variant, ranges, sizing rules, bounds, reopening policy, continuation
- `NPlayerPreflopSizingRule` (§2.2): position, raise_count, cold_callers, relation, expressions
- `NPlayerPreflopContinuation` (§2.3): kind, provenance, source, payoff_table or showdown_ranks + odd_chip_order
- `NPlayerPreflopPublicAction` (§2.5): frozen (actor, Action) record
- `NPlayerPreflopState` (§2.5): config, deal, actor, pot, N-tuples for commitments/contributions/remaining/folded, pending, can_raise, last_raise_increment, raise_count, history, optional terminal
- `NPlayerPreflopSolveResult` (§2.5): strategy, N values, optional certificate, metadata, provenance
- `enumerate_nplayer_preflop_deals`, `create_nplayer_preflop_root`, `solve_nplayer_preflop`

**Finding:** All contracts are explicit, immutable, and type-safe. Validation rules reject bool-as-int, nonpositive/nonfinite values, wrong tuple lengths, and malformed nested data. No silent coercion or fallback.

**Status:** ✅ PASS

### 1.2 Reuse of Existing Types

**Assessed:** `WeightedCombo`, `Action`, `NPlayerCFRSolver`, `expected_values_nplayer`, `unilateral_deviation_certificate` are reused from S2/legacy without duplication.

**Cross-check:** `preflop.py` (HU legacy) defines `WeightedCombo`, `Action`, `Continuation`, `PreflopConfig`, `PreflopState`. S3 adds N-player variants with distinct names; no collision.

**Status:** ✅ PASS

---

## 2. N=2..9 Positions and Order (§4)

### 2.1 Canonical Position Labels

**Assessed:** Section 4 defines deterministic clockwise labels for each N:

- N=2: `BTN/SB, BB` (button is also SB, acts first preflop)
- N=3: `BTN, SB, BB`
- N=4: `CO, BTN, SB, BB`
- N=5: `HJ, CO, BTN, SB, BB`
- N=6: `UTG, HJ, CO, BTN, SB, BB`
- N=7: `UTG, MP, HJ, CO, BTN, SB, BB`
- N=8: `UTG, UTG+1, MP, HJ, CO, BTN, SB, BB`
- N=9: `UTG, UTG+1, MP, LJ, HJ, CO, BTN, SB, BB`

**Finding:** Labels are unambiguous and cover all player counts. SB = `(button + 1) % N`, BB = `(button + 2) % N` for N≥3. For N=2, button is SB.

**Status:** ✅ PASS

### 2.2 Action Order and Pending Queue

**Assessed:** §4 and §7 define `pending` as ordered actionable seats, starting at first actor, ending at last option seat. All-in-from-posts seats are excluded (no decision, no option).

**Finding:** `acting_player == pending[0]` is explicit. `_ordered_after(seat, candidates, N)` scans clockwise once with wraparound. Deterministic and complete.

**Status:** ✅ PASS

---

## 3. Exact Forced Posts and Ante Validation (§3, §15)

### 3.1 Uniform All-Seat or Absent Ante Contract

**Assessed:** §2.4 and §15 (post-audit corrections) state:

> "Antes are either absent or exactly one identical positive ante is posted by every seat. Unequal/per-seat-partial antes and a single-seat big-blind-ante representation are outside this ledger contract and fail validation."

**Finding:** This is a deliberate scope boundary. The architecture rejects:

- Unequal antes (e.g., BB-only ante)
- Partial-seat antes
- Single-seat big-blind-ante dead money

Representing table-paid dead money would require a separate common-pot ledger (acknowledged but out of S3 scope).

**Algebra check:** Under uniform all-seat antes, every seat's `total_contributed` = `ante + street_committed`. At a closed leaf, the unique leader's excess in `total_contributed` equals its excess in `street_committed`, which is bounded by its own `street_committed` (non-negative by invariant). Refund never exceeds the leader's current-street commitment. ✅

**Status:** ✅ PASS (within stated scope)

### 3.2 Exact Post Transfers

**Assessed:** §3 states:

> "Every declared post is transferred in full; a post is never truncated to the remaining stack. A seat may start all-in only when its stack exactly equals its cumulative declared posts."

**Validation:** §2.4 requires `cumulative posts ≤ stack` for every seat. Config validation rejects any post exceeding its seat's stack.

**Finding:** Exact short stacks are supported by declaring `stack == cumulative_posts`. No silent reduction. All-in post seats are excluded from `pending` (§4).

**Status:** ✅ PASS

### 3.3 Ante vs Blind/Straddle Ledger Semantics

**Assessed:** §3 states:

> "Antes do not increase `street_committed`; small blind, big blind, and straddle payments do."

**Cross-check with `game_structure.py`:** `apply_forced_posts` currently records every post (including antes) in `SeatLedger.street_committed`. §3 explicitly states:

> "S3 must not copy that field into its root. It may reuse the helper's remaining/total values and independently sum only blind/straddle posts for `street_committed`, or apply the declared posts directly in the new module."

**Finding:** The architecture acknowledges the discrepancy and mandates S3 implementation to handle it correctly. Existing shared helper behavior is unchanged (no breaking change to S2). ✅

**Status:** ✅ PASS (implementation guidance is clear)

### 3.4 Straddle Validation (§5)

**Assessed:** §5 defines four variants with explicit validation:

- `none`: no straddle
- `standard`: N≥3, exactly one straddle by UTG, strictly > BB
- `double`: N≥4, exactly two straddles by UTG then UTG+1, second > first
- `mississippi`: N≥3, exactly one non-blind straddler (button allowed, SB/BB/HU rejected)

**Finding:** "Each amount is a positive integer strictly greater than the preceding live wager; equal or decreasing declarations are not straddles under this contract and fail validation." ✅

**Status:** ✅ PASS

---

## 4. Deal Bounding and Exact Masses (§6)

### 4.1 Cartesian Product Precheck

**Assessed:** §2.4 states:

> "The Cartesian product `prod(len(range_i))` must not exceed `max_deals`; this precheck bounds work even if blockers eliminate every candidate. Compatible deals are never silently truncated."

**Finding:** Validation fails closed before traversal if the product exceeds `max_deals`. No silent truncation. ✅

**Status:** ✅ PASS

### 4.2 Exact Rational Masses

**Assessed:** §6 states:

> "Convert validated weights with `Fraction(str(weight))`; multiply and normalize exact masses before public float conversion."

**Finding:** Exact rational arithmetic prevents floating-point drift. Probabilities are finite, nonnegative, and sum to one within `1e-12`. ✅

**Cross-check with `preflop.py`:** HU legacy uses `Fraction(self.weight)` in `WeightedCombo.__post_init__`. S3 reuses `WeightedCombo`. ✅

**Status:** ✅ PASS

### 4.3 Collision Pruning

**Assessed:** §6 states:

> "Traverse the per-seat range Cartesian product in seat/range tuple order while carrying a used-card set. Prune a candidate immediately on collision. A valid deal has 2N unique cards."

**Finding:** Deterministic order, immediate pruning, exact 2N unique cards. No ambiguity. ✅

**Status:** ✅ PASS

---

## 5. N=2 Projection (§1, §13)

### 5.1 Explicit Projection Semantics

**Assessed:** §1 states:

> "The N=2 projection is explicit. Align states by deterministic chance outcome and public action path, then compare: normalized private deals and exact masses; acting seat; ordered legal `Action` tuples; pot, street commitments, total contributions, remaining stacks, and fold status; and exact terminal utilities. Project `NPlayerPreflopPublicAction` history to its ordered `Action` tuple before comparing with legacy history. Information compatibility compares partitions rather than key bytes: over aligned decision states, two histories are in the same information set in the legacy path if and only if their aligned histories are in the same information set in the N-player path. Version strings, concrete types, actor wrappers, and tuple layout are deliberately excluded."

**Finding:** Projection is **trace-based**, not type-based. It compares:

- Public action sequences (after stripping actor labels from N-player history)
- Ledger state (pot, commitments, contributions, remaining, folded)
- Legal actions (as ordered `Action` tuples)
- Terminal utilities
- Information partitions (not key bytes)

**Exclusions:** version strings, concrete types, actor wrappers, tuple layout. ✅

**Status:** ✅ PASS

### 5.2 Acceptance Criterion

**Assessed:** §13 (acceptance matrix) requires:

> "N=2 projected deals/actions/ledgers/terminals/information partitions match frozen Phase-3 HU fixtures."

**Finding:** Explicit test requirement. Projection is testable and falsifiable. ✅

**Status:** ✅ PASS

---

## 6. Refund Boundedness Proof

### 6.1 Claim

**Assessed:** §8 and §15 state:

> "Terminal refund boundedness is guaranteed by config validation and ledger algebra, not by accepting a valid config and failing only at its terminal."

### 6.2 Proof by Algebra

**Given:**

1. Uniform all-seat ante contract: every seat posts the same ante `A ≥ 0` (or `A = 0` if absent).
2. Every seat's `total_contributed[i] = A + street_committed[i]`.
3. At a closed leaf, call `refund_uncalled_excess(total_contributed)`.
4. Refund logic (from `game_structure.py` §200–213): if a unique leader exists, refund `excess = highest - second_highest` to the leader.

**To prove:** `excess ≤ street_committed[leader]`.

**Proof:**

Let `leader` be the unique seat with `total_contributed[leader] = max(total_contributed)`.

Let `second` be the second-highest `total_contributed` value.

```
excess = total_contributed[leader] - second
       = (A + street_committed[leader]) - (A + street_committed[second_seat])
       = street_committed[leader] - street_committed[second_seat]
```

Since `street_committed[leader] ≥ street_committed[second_seat]` (leader has the highest total), we have:

```
excess = street_committed[leader] - street_committed[second_seat] ≤ street_committed[leader]
```

By root invariant (§3), `street_committed[i] ≥ 0` for all seats. After refund, the leader's new `street_committed` is:

```
street_committed[leader] - excess = street_committed[leader] - (street_committed[leader] - street_committed[second_seat])
                                   = street_committed[second_seat] ≥ 0
```

**Conclusion:** Refund never exceeds the leader's current-street commitment. No negative `street_committed` can occur. ✅

**Counterexample search:** Attempted to construct a valid config where refund exceeds `street_committed[leader]`. All attempts violated the uniform-ante contract or produced `excess = street_committed[leader] - street_committed[second] ≤ street_committed[leader]`. No counterexample exists within accepted configs. ✅

**Status:** ✅ PASS

---

## 7. Betting Semantics and Sizing Rules (§2.2, §7)

### 7.1 Sizing Key Derivation

**Assessed:** §2.2 defines a four-field unique key: `(position, raise_count, cold_callers, relation)`.

**Finding:** 

- `position`: canonical label from §4
- `raise_count`: raises already made (0 = open/limp, 1 = 3-bet decision, etc.)
- `cold_callers`: live seats whose latest voluntary action is CALL in current response segment (resets after every raise; SB complete counts as pre-raise CALL)
- `relation`: `NA` (no aggressor), `IP`, or `OOP` (determined by postflop clockwise order to button)

**Finding:** Deterministic, unambiguous, and complete. No fallback or warning-based sizing. ✅

**Status:** ✅ PASS

### 7.2 Short All-In Reopening

**Assessed:** §7 states:

> "A short all-in does not update the increment. If `short_all_in_reopens` is false, a seat may raise after it only when that seat was both still in the pre-action pending queue and raise-entitled before the short all-in. This is an intersection, not a union: a seat that checked or called earlier may call or fold against the higher wager but may not re-raise."

**Finding:** Intersection semantics are explicit and correct. A seat that already acted (checked/called) loses its raise entitlement even if it was in the old pending queue. ✅

**Status:** ✅ PASS

---

## 8. Terminal Accounting and Continuations (§2.3, §8)

### 8.1 Two Continuation Kinds

**Assessed:** §2.3 defines:

1. `terminal-table`: exact zero-sum N-tuples keyed by `(DealN, actor-labelled history)`. Missing keys fail at leaf.
2. `showdown-ranks`: caller-supplied integer ranks per deal, with exact side-pot settlement, tie-breaking via `odd_chip_order`, and derived zero-sum utilities.

**Finding:** Both are bounded and deterministic. No automatic board rollout or equity evaluation. Ranks are fixture/input data. ✅

**Status:** ✅ PASS

### 8.2 Fold-Out Settlement

**Assessed:** §8 states:

> "For fold-out, build exact matched pot layers with folded eligibility, award every layer to its sole eligible live winner, compute final stacks, and return exact utilities relative to starting stacks. This covers blinds, antes, straddles, side pots, and all-in contributors without a continuation lookup."

**Cross-check with `game_structure.py`:** `build_pot_layers` (§216–234) and `award_pot_layers` (§277–311) implement exact layer logic. S3 reuses these helpers. ✅

**Status:** ✅ PASS

---

## 9. Information Noninterference (§9)

### 9.1 Key Contents

**Assessed:** §9 lists included fields:

- version/rule identity, N, owner seat, owner's private combo
- button, starting stacks, forced posts, straddle variant, sizing-rule identity
- pot, public commitments/contributions/remaining/fold flags
- pending order, raise entitlements, last increment, raise count, acting seat
- actor-labelled public history
- continuation kind, source, provenance

**Excluded:** opponent cards, deal index/order, hidden payoff-table values, hidden showdown ranks, traversal state.

**Finding:** Exclusions are explicit. Varying hidden data while public state is fixed must preserve the key. ✅

**Status:** ✅ PASS

---

## 10. Acceptance Matrix (§13)

**Assessed:** Section 13 lists 18 mandatory acceptance criteria covering:

- Config validation (N=2..9, malformed types, ante/post/straddle rules)
- HU/6-max/9-max solve and deterministic chance mass
- Straddle variant trees and ledgers
- Limps, SB completes, cold calls, 3/4/5-bet+ sizing, IP/OOP relation
- Action amount semantics (absolute commitments)
- Full/short all-in pending/reopening rules
- Independent integer/rational oracles for fold/refund/side-pot/tie/odd-chip/terminal-table/showdown leaves
- Zero-sum terminals
- Opponent-card and hidden-continuation noninterference (6 and 9 players)
- Normalized, detached, deterministic policies
- Exact six-plus-player reach and unilateral-deviation oracles
- N=2 projected deals/actions/ledgers/terminals/information partitions vs frozen Phase-3 HU fixtures
- Strict v4 API, CLI, examples, exports, capability truth
- All S1/S2 and legacy tests green
- Fresh non-author audit and accepted-wave commit per batch
- `phase3-398-green` tag immutability

**Finding:** Comprehensive, testable, and falsifiable. No ambiguity. ✅

**Status:** ✅ PASS

---

## 11. Reconciliation and Post-Audit Corrections (§14, §15)

### 11.1 Design Stream Reconciliation

**Assessed:** §14 documents which design streams (D301–D306) contributed to the final candidate and which elements were rejected.

**Finding:** Transparent provenance. Rejected elements are explicitly listed (e.g., zero street commitment at root, initial-blind refund rejection, non-zero-sum fold tuple, HU Mississippi, nested double-option claims). ✅

**Status:** ✅ PASS

### 11.2 Post-Audit Corrections

**Assessed:** §15 lists five authoritative corrections from prior audit rounds:

1. Only absent or uniform all-seat antes are representable.
2. Every forced post is exact; straddles strictly increase; all-in post seats never in `pending`.
3. SB completion counts as pre-raise CALL for `cold_callers`.
4. CHECK/CALL consumes raise entitlement; no-reopen short-all-in uses intersection of old pending and old entitlement.
5. Terminal refund boundedness guaranteed by config validation and ledger algebra.

**Finding:** All corrections are incorporated into the main text (§2.4, §3, §7, §8, §15). No contradictions remain. ✅

**Status:** ✅ PASS

---

## 12. TDD Batches and Ownership (§12)

### 12.1 S3-I1 (State and Ledger)

**Assessed:** Four exclusive RED owners for:

1. `test_nplayer_preflop_config.py`
2. `test_nplayer_preflop_betting.py`
3. `test_nplayer_preflop_settlement.py`
4. `test_nplayer_preflop_information.py`

A fifth owner implements `nplayer_preflop.py` only after all four parent-verified RED receipts exist.

**Finding:** Clear ownership, no shared legacy file edits, mandatory focused tests + full regression + frozen hashes + fresh audit + parent verification + commit. ✅

**Status:** ✅ PASS

### 12.2 S3-I2 (Facade/API/Examples)

**Assessed:** Four exclusive RED owners for:

1. `test_nplayer_preflop_solve.py`
2. `test_api_v4_nplayer_preflop.py`
3. `test_phase4_s3_examples.py`
4. `test_phase4_s3_exports.py`

Gated core owner extends `nplayer_preflop.py`; gated integration owner extends `api_v4.py`, `api_v3.py`, exports, examples. `cli.py` changes forbidden unless genuine failing contract proves necessity.

**Finding:** Clear gates, no premature integration edits, same focused/full/freeze/fresh-audit/parent/commit discipline. ✅

**Status:** ✅ PASS

---

## 13. Strict v4 API and CLI (§11)

### 13.1 Operation and Envelope

**Assessed:** §11 defines `solve-nplayer-preflop` operation with `{version: 4, operation, payload}` envelope (integer version 4).

**Payload:** config version, N, button, starting stacks, ordered forced-post objects, straddle variant, per-seat weighted ranges, strict sizing-rule objects, max raises/deals/nodes, short-all-in policy, one continuation object (terminal-table or showdown), algorithm, iterations, null seed, diagnostic flag, pure-strategy cap.

**Response:** operation/version, config/game versions, algorithm/iterations/bounds, detached serialized strategy, N values, optional certificate, metadata, provenance, `approximate: false`. No convergence claim.

**Finding:** Complete, strict, and unambiguous. Unknown/missing fields, bool numerics, nonfinite values, malformed arrays, duplicate keys, unsupported seeds/algorithms, and bound violations fail closed. ✅

**Status:** ✅ PASS

### 13.2 CLI and Examples

**Assessed:** §11 states:

> "The existing generic `phase4 FILE|- --json` CLI already forwards v4 and requires no new parser shape. Add canonical synthetic bounded examples: `examples/phase4/nplayer_2p_preflop.json`, `examples/phase4/nplayer_6p_preflop.json`, `examples/phase4/nplayer_9p_preflop.json`."

**Finding:** No CLI changes required (generic forwarding). Examples are synthetic and non-presolved. ✅

**Status:** ✅ PASS

---

## 14. Solver and Diagnostics (§10)

### 14.1 Algorithm and Iterations

**Assessed:** §10 states:

> "`solve_nplayer_preflop` accepts only `algorithm='vanilla-cfr'`, positive strict integer iterations, an optional exhaustive deviation diagnostic, and an optional positive `max_pure_strategies`."

**Finding:** Single algorithm, no convergence claim, exhaustive diagnostic (never sampled, never called exploitability or Nash certificate). ✅

**Status:** ✅ PASS

### 14.2 Determinism

**Assessed:** §10 states:

> "Repeated identical solves produce identical strategies, N values, metadata, and diagnostics."

**Finding:** Explicit determinism requirement. Testable. ✅

**Status:** ✅ PASS

---

## 15. Scope Boundaries (§1, §2.3)

### 15.1 Explicit Out-of-Scope

**Assessed:** §1 states:

> "S3 is a finite reference path. It does not claim unrestricted range solving, practical large-range nine-player performance, equilibrium convergence, automatic abstraction, continuous sizing, or automatic multi-street solving."

**Finding:** Clear boundaries. S3 is a bounded, deterministic, exact-arithmetic reference implementation. Large-range tractability belongs to S4 abstraction. ✅

**Status:** ✅ PASS

### 15.2 Synthetic Bounded Fixtures

**Assessed:** §1 states:

> "All HU, 6-player, and 9-player S3 acceptance fixtures use deliberately tiny synthetic per-seat ranges whose full Cartesian product is at most `max_deals`. They prove player-count generality and exact chance arithmetic, not realistic full-range tractability."

**Finding:** Fixtures are proofs of correctness, not performance benchmarks. ✅

**Status:** ✅ PASS

---

## 16. Cross-Check: Legacy HU Preflop (`preflop.py`)

### 16.1 Type Comparison

**Assessed:** `preflop.py` defines:

- `WeightedCombo` (reused by S3)
- `Continuation` (HU-specific, 2-tuple values)
- `PreflopConfig` (HU-specific, 2-tuple stacks/posts/ranges)
- `PreflopState` (HU-specific, 2-tuple ledgers, no actor-labelled history)

**S3 defines:**

- `NPlayerPreflopContinuation` (N-tuple values, showdown-ranks option)
- `NPlayerPreflopConfig` (N-tuple stacks/posts/ranges, straddle variants, sizing rules)
- `NPlayerPreflopState` (N-tuple ledgers, actor-labelled history, pending queue)

**Finding:** No type collision. S3 is additive. N=2 projection is trace-based, not type-based. ✅

**Status:** ✅ PASS

### 16.2 Ledger Semantics

**Assessed:** HU `preflop.py` uses `committed` for street commitments, `total_contributed` for cumulative contributions. S3 uses `street_committed` and `total_contributed`.

**Finding:** Naming is consistent. Semantics align (antes do not increase street commitment in S3; HU has no antes in its current contract). ✅

**Status:** ✅ PASS

---

## 17. Cross-Check: `game_structure.py`

### 17.1 `apply_forced_posts` Discrepancy

**Assessed:** `game_structure.py` line 158–182 defines `apply_forced_posts`, which currently records every post (including antes) in `SeatLedger.street_committed`.

**S3 requirement (§3):** Antes do not increase `street_committed`.

**Architecture guidance (§3):**

> "S3 must not copy that field into its root. It may reuse the helper's remaining/total values and independently sum only blind/straddle posts for `street_committed`, or apply the declared posts directly in the new module. Existing shared-helper behavior is unchanged."

**Finding:** S3 implementation must handle this correctly. No breaking change to S2 or legacy. Guidance is clear. ✅

**Status:** ✅ PASS (implementation guidance is sufficient)

### 17.2 `refund_uncalled_excess`

**Assessed:** `game_structure.py` line 200–213 implements exact refund logic: unique leader's excess above second-highest is refunded.

**S3 reuse:** §8 states S3 calls this helper before finalizing terminals.

**Finding:** Reuse is safe. Refund boundedness proven in §6.2 above. ✅

**Status:** ✅ PASS

---

## 18. Final Checks

### 18.1 Internal Consistency

**Assessed:** No contradictions found between sections. Post-audit corrections (§15) are incorporated into main text.

**Status:** ✅ PASS

### 18.2 Completeness

**Assessed:** All mandatory elements for TDD implementation are present:

- Typed contracts (§2)
- Positions and order (§4)
- Forced posts and antes (§3, §15)
- Straddles (§5)
- Deals and masses (§6)
- Betting semantics (§7)
- Terminal accounting (§8)
- Information keys (§9)
- Solver (§10)
- API/CLI (§11)
- TDD batches (§12)
- Acceptance matrix (§13)
- N=2 projection (§1, §13)

**Status:** ✅ PASS

### 18.3 Testability

**Assessed:** Every requirement is testable and falsifiable. Acceptance matrix (§13) provides explicit pass/fail criteria.

**Status:** ✅ PASS

---

## Conclusion

**VERDICT: PASS**

The S3 architecture candidate is **ready for TDD implementation**. All design elements are internally consistent, complete, and testable. The uniform all-seat ante contract is a deliberate scope boundary (unequal/BB-only antes require a future common-pot ledger). Refund boundedness is proven by config validation and ledger algebra. N=2 projection is explicit and trace-based. No blocking gaps or contradictions exist.

**Blockers:** None.

**Recommendations:**

1. Implementers must follow §12 TDD batch ownership strictly (RED before GREEN, fresh non-author audit per batch).
2. Implementers must handle the `apply_forced_posts` / `street_committed` discrepancy per §3 guidance (do not copy ante posts into `street_committed`).
3. Permanent tests must use independent integer/rational oracles (§13) — no production settlement helpers as expected-value oracles.
4. N=2 projection tests must compare public traces, not types or key bytes (§1).

**Post-audit architecture hash:** `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9` (unchanged). ✅

---

**Audit complete.**  
**A3F1 / 2026-09-16**
