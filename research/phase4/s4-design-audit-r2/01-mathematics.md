# R2A1: S4 design audit — mathematical equivalence and error certificates

**Agent:** R2A1 (BryantGPT, wholly fresh non-author DESIGN auditor)  
**Task:** R2 S4 design audit after R1 architecture repair  
**Timestamp:** 2026-09-16T00:00:00Z  
**Status:** PASS

## 1. Candidate verification

All required input documents verified against declared SHA-256 hashes:

- `ARCHITECTURE_PHASE4_S4.md`: `37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2` ✓
- `research/phase4/s4-design-audit-r2/CANDIDATE_MANIFEST.md`: `f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed` ✓
- `PHASE4_MISSION.md`: `5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61` ✓
- `research/phase4/s4-design/02-engine-integration-codex.md`: `79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d` ✓

R2 repairs only contract surface issues from R1 C4D4-CODEX findings. No production/test/script changes. Missing S4 implementation is expected for a design-only audit.

## 2. Mathematical equivalence: exact-signature rectangular factorization

### 2.1 Complete labelled signature certificate (§3.2, §3 of 02-engine-integration-codex.md)

The architecture defines a **complete labelled signature** for each hand as a tuple with one cell per canonically ordered opponent hand. Each cell is:
- `(0, ())` if incompatible, or
- `(1, codes)` with one showdown code per configured ordered full runout: `-2` (blocked), `-1` (loss), `0` (tie), `+1` (win).

Bucket assignment: hands with **identical complete signature tuples** receive the same bucket ID. This is exact equality of the full tuple, not a hash collision or equity approximation.

**Rectangular-cell proof (§3.2, lines 64-66; §3 lines 48-50 of 02-engine-integration-codex.md):**
- Equal rows ⇒ identical opponent compatibility, runout legality, and payoff ordering against every labelled opponent hand.
- Equal columns ⇒ same property for the transposed player.
- Therefore, a positive bucket-pair cell is **rectangular**: all member hand pairs are compatible, have the same public chance kernel, and identical terminal ordering for every configured public continuation.

**Certificate strength:** Fold utility and legal betting transitions are card-independent (§3.2 line 66, §4.3). These are **behavioural twins** for the configured game. Scalar equity, made-hand category, hole-card ranks, or informal suit symmetry are explicitly rejected as certificates (§3.2 lines 67-68).

**Blocker separation (§3.2 lines 67-68, §8 lines 276-278 of 02-engine-integration-codex.md):** Equal-equity hands separated by an opponent blocker or public-runout blocker MUST remain in different buckets. Two mandatory blocker companions enforce this:
1. **Opponent-blocker fixture:** equal-showdown hands but three compatible deals; both players' signatures stay separate.
2. **Runout-blocker fixture:** one P0 hand blocks a declared runout; signatures stay separate and no positive deal is conditioned away.

**Finding:** The signature definition is mathematically sound. The rectangular factorization follows directly from row/column equality. Blocker counterexamples are explicit and mandatory.

### 2.2 Fixed buckets and perfect recall (§3.3)

A hand receives **one private bucket at root and retains it through every street**. No street-local rebucketing may merge distinct prior buckets (§3.3 lines 71-72).

The abstract information key contains (§3.3 lines 72-77):
- Policy version and canonical semantic config digest
- Acting player
- That player's own fixed bucket ID
- Full public frame: board, street, actor, pot, commitments, total contributions, remaining stacks, last-raise increment, betting history, public RUNOUT history, terminal marker

Excludes: opponent bucket, exact cards, world ID, pair ID, latent probabilities, root abstract-deal action, representative cards (§3.3 lines 78-79).

**Recall property:** Same abstract key ⇒ same own observation/action sequence and ordered legal actions. Compile-time recall and noninterference checks are required in addition to `validate_bounded_tree` (§3.3 lines 78-79).

**Finding:** Perfect recall is structurally enforced by fixed bucket assignment and complete public history retention. The key excludes all opponent-dependent and latent-world information, satisfying noninterference.

## 3. Chance kernels and terminal utility

### 3.1 Public chance kernels (§4.2)

For exact world `w=(h,g)`, raw mass is `r_w=f_h*f_g`; normalize by exact `Z=sum(r_w)`. Bucket-pair mass is the sum of world masses in the pair. Conditional member mass is normalized world mass divided by pair mass (§4.2 lines 129-130).

For revealed runout prefix `s`, let `R_w(s)` be the configured legal full runouts beginning with `s`. The world next-card law is:

`p_w(c | s) = |R_w(s+c)| / |R_w(s)|` (§4.2 line 133)

For belief `q`, aggregate observable chance mass is:

`P(c) = sum_w q(w) * p_w(c | s)` (§4.2 line 137)

The child posterior is:

`q'(w) = q(w) * p_w(c | s) / P(c)` (§4.2 line 141)

for positive terms only. These equations use `Fraction`. Do not choose a hidden complete runout before turn betting; do not uniformly average worlds; do not pool raw sequence counts across worlds with different denominators (§4.2 lines 143-144).

**Kernel agreement within bucket pairs (§4.2 lines 145-147):** For exact-signature v1, the public kernels within a pair agree, but the general formula remains implemented and directly tested. Beliefs are shared by `(bucket_pair, revealed_prefix)` across betting histories.

**Finding:** The chance kernel is exact combinatorial counting over configured ordered runouts, using rational arithmetic. The general formula handles worlds with different denominators; v1's signature certificate ensures kernel agreement within pairs, but the implementation does not shortcut the general case.

### 3.2 Terminal utility (§4.4)

At a terminal, preserve source integer settlement, including folds, refunds, all-ins, and odd ties. If `C=pot+sum(committed)`, each member produces an integer P0 award. Aggregate:

`u0 = sum_w q(w) * award0(w) - contributed0 - Fraction(initial_dead_pot, 2)` (§4.4 line 157)

Compute the complementary P1 result independently and require exact `u0+u1==0`. Also require ledger conservation `C=initial_dead_pot+sum(total_contributed)`. Return `(float(u0), -float(u0))` only after finite/bound checks. Never infer settlement from mean equity or average already-rounded utilities (§4.4 lines 158-160).

**Finding:** Terminal utility is exact rational aggregation of integer source awards, with mandatory zero-sum and ledger-conservation checks. No equity approximation or float rounding before aggregation.

## 4. Lossless response theorem and model-error bound

### 4.1 Terminal diameter (§7, lines 252-256)

The exact-signature quotient has **terminal diameter zero** and identical observable kernels. For any bucket profile, rational reduced value equals rational exact lifted value. Extra exact-card distinctions cannot improve a response because types within a bucket have identical labelled continuations and factorized conditional mass; their realization-plan mixture is implementable under perfect recall. Therefore the v1 model-error term is **exactly zero**. This is a certificate, not a claim that float CFR has converged (§7 lines 252-256).

**Proof sketch (§8 lines 262-265 of 02-engine-integration-codex.md):**
- **Simulation equality:** multiplying pair root mass, Bayesian chance probabilities, and terminal conditional means telescopes to the exact world sum. Public actions have common likelihoods within a pair. Hence `V_reduced(p) = V_exact(lift(p))` in rational arithmetic.
- **Lossless-response certificate:** within an exact-signature pair, all public kernels and all member terminal utilities coincide. Root conditional private-type masses factorize. Against a bucket-constant opponent profile, extra own-card distinctions cannot improve response value: replacing an exact type-dependent behavioural response by its conditional realization-plan mixture inside the own bucket preserves outcome value. Recall makes that mixture implementable as a behavioural bucket strategy. Thus both best-response values, and NashConv, agree between the quotient and the exact lifted profile.

**Finding:** The lossless-response theorem is correctly stated and follows from rectangular factorization, kernel agreement, and perfect recall. The model-error bound is exactly zero, not an approximation.

### 4.2 Minimax and incentive bounds (§7, lines 237-251)

For a complete profile `x` evaluated in the SAME exact two-player zero-sum game:
- `v(x)=u0(x)`
- `U(x)=BR0(x1)`
- `L(x)=-BR1(x0)`
- `e0(x)=U(x)-v(x)`
- `e1(x)=v(x)-L(x)`
- `C(x)=e0(x)+e1(x)=U(x)-L(x)`

Minimax gives `L(x) <= v* <= U(x)`. For a lifted abstract profile `a` and independently trained exact reference `r`:

`|v(a)-v(r)| <= max(e1(a)+e0(r), e0(a)+e1(r)) <= C(a)+C(r)` (§7 lines 248-251)

This compares finite profiles and does not assume either is equilibrium or convergence is monotone. On the preregistered small fixture, both profiles must have exact-tree NashConv at most 0.02 chips after 1,000 vanilla iterations, giving a preregistered loose value-gap bound of 0.04 chips and the tighter observed incentive expression above (§7 lines 251-252).

**Finding:** The incentive bound is a standard minimax inequality and does not assume equilibrium or monotonicity. The preregistered quality gate (C(a), C(r) ≤ 0.02 chips) is explicit and precedes the reduced solve.

## 5. Physical node accounting and bounds (§5)

### 5.1 Physical node count definition (§5, lines 162-165)

`node_count` is exactly the history occurrence count produced by `validate_bounded_tree`: root, chance, decision, and terminal nodes. It is not bucket count, infoset count, unique public frame count, live wrapper count, or regret-table size (§5 lines 162-165).

Compilation reserves a node before allocation and fails before exceeding `max_abstract_nodes`; equality is allowed. It separately bounds (§5 lines 166-172):
- Compatible active worlds by `max_worlds`
- Charged signature scalar slots by `2 * len(H0) * len(H1) * max(1, len(allowed_runouts))` against `max_signature_cells`, including blocked cells
- Total stored `MemberWeight` entries against `max_belief_entries`
- Fraction bit lengths against `max_fraction_bits`
- Depth against both the caller cap and v1 recursive ceiling

After freezing the plan, run `validate_bounded_tree` on `ReducedState` and require every recorded count/depth to match. This preflight occurs before solver construction (§5 lines 173-174).

**Finding:** Physical node count is unambiguous and verified by `validate_bounded_tree`. Preprocessing bounds (worlds, signature cells, belief entries, fraction bits) are separate and explicit.

### 5.2 Large fixture physical counts (§8, lines 281-301 of ARCHITECTURE_PHASE4_S4.md; §9 lines 281-342 of 02-engine-integration-codex.md)

Large fixture: same public game as small fixture. P0 range is all unordered pairs from 12 cards `{2c,3c,4c,5c,6c,7c,2d,3d,4d,5d,6d,7d}`. P1 range is all unordered pairs from 12 cards `{2s,3s,4s,5s,6s,7s,2h,3h,4h,5h,6h,Th}`. Each player has C(12,2)=66 hands, all weights one, and all 4,356 ordered pairs are compatible.

Exact bucket membership:
- P0 bucket: all 66 hands (one bucket)
- P1 no-Th bucket: C(11,2)=55 hands (all tie P0 at both final boards)
- P1 Th bucket: 11 hands `{Th,x}` (all beat P0 at both final boards)

Root outcome k=0 is `(P0_bucket0, P1_bucket0)` with 3,630 worlds and exact mass 5/6; k=1 is `(0,1)` with 726 worlds and mass 1/6.

A single-world public tree has 81 nodes, 34 terminals, 15 chance nodes, 32 decisions, depth 12. Thus:
- **Exact physical nodes:** `1 + 4,356 * 80 = 348,481`
- **Reduced physical nodes:** `1 + 2 * 80 = 161`
- Reduced terminals/chance/decisions: 68/29/64
- Charged signature slots: 17,424
- Literal belief member entries: 17,424

Acceptance requires the complete reduced path under 10,000 physical nodes and depth 32. The same exact config with 10,000 nodes must fail before training. The result reports the exact count as an analytic certificate, not as an executed full traversal (§8 lines 299-301).

**Finding:** The large fixture physical counts are derived from explicit combinatorics and a read-only source probe (§9 lines 299-337 of 02-engine-integration-codex.md). The 348,481 → 161 reduction is a same-game comparison with identical public branching. The analytic certificate is valid and does not require full exact traversal.

## 6. R2 wire changes and certificate preservation

### 6.1 R1 findings and R2 repairs (CANDIDATE_MANIFEST.md lines 20-28)

R1 C4D4-CODEX rejected the earlier architecture for three findings:
1. Incomplete exact response and nested wire schema
2. Ambiguous optional versus required base bounds
3. Integer range weights above `2**53` losing exactness through inherited `_float` parsing

R2 repairs:
- Freezes exhaustive response/key/action/policy/membership/rational/metadata schema (§9.1)
- Makes base `max_nodes`/`max_depth` mandatory only for the new operation and equal to abstraction bounds (§9 lines 311-315)
- Preserves prior operation defaults
- Preserves non-bool integer weights before Fraction conversion (§9 lines 331-333)
- Fixes digest canonicalization (§9 lines 451-453)
- Expands I4 RED cases (§10)

No production, tests, scripts, dependency, mission, or accepted Git bytes changed.

### 6.2 Impact on mathematical certificates

R2 changes affect only the API contract surface:
- **Exhaustive wire schema (§9.1):** All top-level and nested response keys are now explicit and mandatory. This does not change the internal mathematical definitions or certificates.
- **Mandatory base bounds (§9 lines 311-315):** `payload.max_nodes` must equal `abstraction.max_abstract_nodes`, and `payload.max_depth` must equal `abstraction.max_depth`. This removes ambiguity but does not alter the physical node count definition or validation.
- **Integer weight preservation (§9 lines 331-333):** Non-bool JSON integers remain integers through validation and are converted with `Fraction(value)`; finite JSON floats use `Fraction.from_float(value)`. This preserves integers above `2**53` exactly and is local to the new operation. Prior operations retain existing float-coercion behavior. This strengthens the rational arithmetic guarantee without changing the signature or belief formulas.
- **Digest canonicalization (§9 lines 451-453):** The digest is lowercase hexadecimal SHA-256 over UTF-8 canonical JSON for the normalized semantic source config plus abstraction config. This affects result identity but not the mathematical equivalence or error bounds.

**Finding:** R2 repairs strengthen the API contract and rational arithmetic without altering the core mathematical certificates. The lossless-response theorem, terminal diameter zero, rectangular factorization, and incentive bounds remain unchanged.

## 7. Blocker counterexamples and physical-count claims

### 7.1 Blocker counterexamples (§8.1 lines 276-278)

Two mandatory blocker companions:
1. **Opponent-blocker fixture:** retain public game, set P0 hands to `2c 3c` and `2d 3d`, P1 hands to `2c 4s` and `5s 6s`, all weights one. Every legal showdown ties, so all active hands have equal showdown equity. There are THREE compatible deals, each mass 1/3; P0 `2c 3c` blocks P1 `2c 4s` while `2d 3d` does not. Both players' two signatures must remain distinct, and root outcome count must be three, not one.
2. **Runout-blocker fixture:** replace the two runouts with `(Jh,2c)` and `(Jh,8h)`, use the original small P1 range, and require P0's two signatures to separate because their legal observable runout supports differ. Both worlds still have at least one legal runout; no conditioning-away of a positive deal is allowed.

**Finding:** The blocker counterexamples are explicit, mandatory, and enforce the distinction between equity equality and identical strategic information. They prevent silent lossy merges.

### 7.2 Physical-count claims (§8.2 lines 281-301, §9 lines 299-342 of 02-engine-integration-codex.md)

The large fixture physical counts are derived from:
- Explicit combinatorics: C(12,2)=66 hands per player, 4,356 compatible deals, 2 bucket pairs
- Read-only source probe (§9 lines 299-337 of 02-engine-integration-codex.md): single-world stats `node_count=81, max_depth_reached=12, terminal_count=34, chance_count=15, decision_count=32`
- Analytic extension: exact N=1+4356*80=348,481; reduced N=1+2*80=161

The probe is reproducible and creates no implementation files. The analytic certificate is valid because all worlds have identical public branching.

**Finding:** The physical-count claims are substantiated by explicit combinatorics and a reproducible read-only probe. The 348,481 → 161 reduction is a same-game comparison, not a different action tree or suppressed runout set.

## 8. Verdict

**PASS.** No blocking issues found.

The R2 S4 architecture provides:
1. **Exact-signature rectangular factorization:** Complete labelled signatures with mandatory blocker separation. Rectangular-cell proof is sound.
2. **Chance kernels:** Exact combinatorial counting over configured ordered runouts, using rational arithmetic. General formula handles worlds with different denominators.
3. **Terminal utility:** Exact rational aggregation of integer source awards, with mandatory zero-sum and ledger-conservation checks.
4. **Lossless response theorem:** Terminal diameter zero, model-error bound exactly zero. Follows from rectangular factorization, kernel agreement, and perfect recall.
5. **Minimax/incentive bounds:** Standard minimax inequality with explicit preregistered quality gate (C(a), C(r) ≤ 0.02 chips).
6. **Perfect recall:** Structurally enforced by fixed bucket assignment and complete public history retention.
7. **Terminal diameter:** Exactly zero for v1 exact-signature policy.
8. **Blocker counterexamples:** Two mandatory companions enforce equity ≠ identity.
9. **Physical-count claims:** Substantiated by explicit combinatorics and reproducible read-only probe. 348,481 → 161 reduction is a same-game comparison.
10. **R2 wire changes:** Strengthen API contract and rational arithmetic without altering core mathematical certificates.

All mathematical certificates are correctly stated, substantiated, and preserved across R2 repairs. The design is ready for implementation.

---

**Report SHA-256:** (computed after file write)
