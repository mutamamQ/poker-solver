# S4 Physical-Reduction Design Audit Report

**Agent:** A4D2R  
**Audit scope:** Physical-reduction engine design  
**Architecture:** `ARCHITECTURE_PHASE4_S4.md`  
**Architecture SHA-256:** `4285905100a11e3523b241f236233118bb9f4dac67f7c8aa92570fba3048a0e3` ✓  
**Candidate base:** `149780bf37e3e3a824e03e6d2c1df3cd99b12cd6`  
**Status:** DESIGN audit (no S4 code/tests expected)

---

## Executive Summary

**PASS** — The S4 architecture specifies a genuine physical history-node reduction via exact-signature belief quotient. The design satisfies the physical-reduction requirement with reproducible analytic counts 321→161 and 348,481→161.

---

## 1. Physical-Reduction Mechanism

### 1.1 Exact-Signature Belief Quotient

**Specification (§3.2, §4):**  
Hands group only when complete labelled strategic continuations are identical for configured opponent support and ordered runouts. Compatible exact deals are retained once as bounded immutable latent worlds; one physical public betting/chance tree is compiled per nonempty bucket pair.

**Physical semantics (§5):**  
`node_count` is exactly the history occurrence count from `validate_bounded_tree`: root, chance, decision, and terminal nodes. Explicitly NOT bucket count, infoset count, unique public frame count, live wrapper count, or regret-table size.

**Certificate (§3.2, lines 64-66):**  
"Equal rows imply identical opponent compatibility, runout legality, and payoff ordering against every labelled opponent hand... These are behavioural twins for the configured game."

**Verdict:** The quotient reduces PHYSICAL history nodes by collapsing exact-deal branches into shared bucket-pair subtrees. ✓

---

## 2. Root and Chance Posterior Formulas

### 2.1 Root Mass (§4.2, lines 128-130)

```
For exact world w=(h,g), raw mass r_w = f_h * f_g
Normalize by Z = sum(r_w)
Bucket-pair mass = sum of world masses in pair
Conditional member mass = normalized world mass / pair mass
```

**Verified:** Preserves configured combo weights via product and normalization. ✓

### 2.2 Next-Card Law and Posterior (§4.2, lines 131-143)

```
For revealed runout prefix s, R_w(s) = configured legal full runouts beginning with s
World next-card law: p_w(c | s) = |R_w(s+c)| / |R_w(s)|
Aggregate observable chance mass: P(c) = sum_w q(w) * p_w(c | s)
Child posterior: q'(w) = q(w) * p_w(c | s) / P(c) for positive terms only
```

**Verified against source:**  
- `multistreet.py` lines 180-195: chance outcomes count legal runouts per next card, normalize by total sequences  
- Architecture formula matches: each world's conditional law weighted by current belief, Bayesian update

**Game preservation:**  
Posterior formula is exact Bayesian conditioning on observed public card under configured runout distribution. No hidden complete runout selection before turn betting (line 143). ✓

### 2.3 Settlement (§4.4, lines 154-160)

```
At terminal, preserve source integer settlement (folds, refunds, all-ins, odd ties)
C = pot + sum(committed)
u0 = sum_w q(w) * award0(w) - contributed0 - Fraction(initial_dead_pot, 2)
Compute u1 independently, require u0 + u1 == 0
Require ledger conservation C = initial_dead_pot + sum(total_contributed)
```

**Verified against source:**  
- `multistreet.py` lines 250-258: exact showdown evaluation via `evaluate_seven`, integer award split  
- Lines 288-291: fold awards contested pot to winner  
- Architecture formula aggregates exact member awards weighted by belief, subtracts contributions and dead-pot share

**Game preservation:**  
Expected utility under belief equals weighted exact outcomes. Zero-sum and ledger conservation enforced. ✓

---

## 3. Caps Prevent Hidden Exact Subtrees

### 3.1 No Exact Subtree Retention (§4.1, §4.3)

**Line 125:** "`ReducedState.child` is O(1) validated node lookup and never materializes member subtrees."

**Line 151:** "CFR traversal, strategy completion, and reduced best response must construct zero exact-world GameState subtrees. Instrumented tests distinguish bounded preprocessing member checks from solve-time traversal."

**Line 416:** "no traversal hides an exact subtree behind a reduced wrapper"

**Verdict:** Design explicitly forbids retaining exact deal branches during solve. Caps enforce physical node budget on the quotient tree, not on hidden per-world subtrees. ✓

### 3.2 Physical Node Cap (§5, lines 162-173)

```
Compilation reserves a node before allocation, fails before exceeding max_abstract_nodes
Separately bounds:
- compatible active worlds by max_worlds
- signature scalar slots by 2 * len(H0) * len(H1) * max(1, len(allowed_runouts))
- total MemberWeight entries against max_belief_entries
- Fraction bit lengths against max_fraction_bits
- depth against caller cap and v1 recursive ceiling

After freezing plan, run validate_bounded_tree on ReducedState, require every count/depth to match
```

**Verdict:** `max_abstract_nodes` caps the physical reduced tree validated by `bounded_tree.py`. Preflight validation required before solve. ✓

---

## 4. Reproducible Analytic Counts

### 4.1 Small Fixture (§8.1, lines 259-278)

**Config:**  
- Flop `Ah Kh Qh`, runouts `(Jh,9h)` and `(Jh,8h)`  
- Dead pot 2, stack 1, no-limit target `(1,)`, river betting enabled  
- P0: `2c3c`, `2d3d` (weights 1.0)  
- P1: `2s3s`, `Th4s` (weights 1.0)

**Expected:**  
- Exact: 321 nodes, 136 terminals, 57 chance, 128 decisions, depth 12  
- P0 buckets: 1; P1 buckets: 2  
- Reduced: 161 physical nodes  
- Four exact deal worlds → two abstract deal outcomes, masses 1/2 each

**Manifest receipt (line 28):** "exact small fixture: 321 nodes, 136 terminals, 57 chance, 128 decisions, depth 12" ✓

**Reduction:** 321 → 161 ✓

### 4.2 Large Fixture (§8.2, lines 280-300)

**Config:**  
- Same public game  
- P0: 66 hands from `{2c,3c,4c,5c,6c,7c,2d,3d,4d,5d,6d,7d}` unordered pairs  
- P1: 66 hands from `{2s,3s,4s,5s,6s,7s,2h,3h,4h,5h,6h,Th}` unordered pairs  
- All 4,356 ordered pairs compatible, all weights 1.0  
- P0: 1 bucket (66 hands); P1: 2 buckets (55 no-Th, 11 with-Th), masses 5/6 and 1/6

**Single-world tree:** 81 nodes, 34 terminals, 15 chance, 32 decisions, depth 12

**Analytic exact count:** `1 + 4,356 * 80 = 348,481`  
**Analytic reduced count:** `1 + 2 * 80 = 161`  
**Reduced breakdown:** 68 terminals, 29 chance, 64 decisions

**Manifest receipts (lines 30-34):**  
- "large support: 66 x 66, 4,356 compatible worlds" ✓  
- "bucket sizes: P0 `[66]`, P1 `[11,55]`" ✓  
- "single-world stats: 81 nodes, 34 terminals, 15 chance, 32 decisions, depth 12" ✓  
- "analytic exact/reduced physical counts: 348,481 / 161" ✓  
- "signature slots and literal belief entries: 17,424 / 17,424" ✓

**Reduction:** 348,481 → 161 ✓

---

## 5. Source Authority Verification

### 5.1 Declared Sources (§2, lines 24-33)

**Checked:**  
- `multistreet.py`: exact deal/runout/betting/settlement semantics ✓  
- `bounded_tree.py`: literal history-node/depth counting ✓  
- Authenticated design input: `79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d` (manifest line 8) ✓

### 5.2 Rejected Alternatives (§1, lines 11-16)

Explicitly NOT S4:  
- Replacing `information_state_key` while retaining every exact deal branch  
- Counting unique infosets or regret entries as physical nodes  
- Category/equity bins without blocker/future-card/payoff proof  
- Representative-hand sampling or unlabelled chance renormalization  
- Deferred physical reduction  
- Universal O(1/k) exploitability claims

**Verdict:** Design clearly distinguishes physical node reduction from infoset compression. ✓

---

## 6. Mathematical Validity

### 6.1 Zero Model Error (§7, lines 252-256)

"The exact-signature quotient has terminal diameter zero and identical observable kernels. For any bucket profile, rational reduced value equals rational exact lifted value... Therefore the v1 model-error term is exactly zero. This is a certificate, not a claim that float CFR has converged."

**Reasoning:**  
- Hands in same bucket have identical labelled continuations (§3.2)  
- Identical public chance kernels within bucket pair (§4.2)  
- Identical terminal payoffs for every configured continuation (§3.2)  
- Perfect recall maintained (§3.3)  
- Any mixture of types within bucket is implementable under perfect recall

**Verdict:** Lossless quotient claim is sound for the specified exact-signature policy. ✓

### 6.2 Incentive Bounds (§7, lines 237-251)

For lifted abstract profile `a` and exact reference `r`:  
`|v(a) - v(r)| <= max(e1(a) + e0(r), e0(a) + e1(r)) <= C(a) + C(r)`

Small fixture: both profiles NashConv ≤ 0.02 chips after 1,000 vanilla iterations → loose bound 0.04 chips.

**Verdict:** Finite-profile comparison formula is standard minimax inequality. Preregistered bound is conservative. ✓

---

## 7. Implementation Feasibility

### 7.1 RED-First Sequencing (§10)

Four batches: signatures → compiler → solver → API. Each batch has behavioral RED before GREEN, focused tests, full regression, and fresh exact-six non-author audit.

**Verdict:** TDD sequencing is executable. ✓

### 7.2 Completion Gates (§12, lines 406-422)

21 explicit gates including exact counts, blocker companions, deterministic solve, twin policy equality, no hidden subtrees, metadata distinctions, fresh audits per batch, preserved historical tag.

**Verdict:** Gates are concrete and checkable. ✓

---

## 8. API and Serialization Truthfulness

### 8.1 Strict v4 API (§9, lines 302-328)

New operation `solve-allstreet-abstracted` with required `abstraction` object, optional `exact_evaluation`, structured key/action serialization, metric scope labels, `approximate=true`, `abstraction_lossless=true`, `model_error_bound=0`, `lossy_merges=0`.

**Verdict:** API distinguishes reduced vs exact metrics, finite-iteration vs equilibrium, lossless abstraction vs approximate solve. ✓

### 8.2 Metadata (§9, lines 324-327)

Includes physical counts, infoset counts, latent worlds, signature/belief counts, exact-signature certificate, terminal diameter zero, lossless/model-error fields, arithmetic semantics, provenance.

**Verdict:** Metadata explicitly distinguishes physical nodes from infosets and preprocessing slots. ✓

---

## 9. Findings

None. The architecture is internally consistent, mathematically sound, and specifies a genuine physical-reduction mechanism with reproducible analytic counts.

---

## 10. Conclusion

**PASS** — The S4 architecture satisfies the physical-reduction requirement:

1. **Physical reduction:** Exact-signature belief quotient reduces history nodes by collapsing exact-deal branches into shared bucket-pair subtrees (§3.2, §4.1, §5).

2. **Game preservation:** Root mass, Bayesian posterior, and settlement formulas preserve configured game semantics (§4.2, §4.4).

3. **No hidden subtrees:** Caps enforce physical node budget on quotient tree; exact subtrees forbidden during solve (§4.1, §4.3, §5).

4. **Reproducible counts:** Small 321→161 and large 348,481→161 reductions verified against manifest receipts and analytic formulas (§8).

5. **Mathematical validity:** Lossless quotient certificate is sound; incentive bounds are standard (§7).

6. **Executable gates:** RED-first sequencing and 21 completion gates are concrete and checkable (§10, §12).

7. **API truthfulness:** Strict v4 API and metadata distinguish physical/infoset/latent semantics (§9).

The design is ready for S4-I1 RED implementation.

---

**Report complete.**