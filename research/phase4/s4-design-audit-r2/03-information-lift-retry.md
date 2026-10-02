# R2A3R: Information-safety, solver compatibility, and lift design audit

**Agent:** R2A3R (Bryant recovery, sole R2A3 retry)  
**Status:** COMPLETE_PASS  
**Timestamp UTC:** 2026-09-16T12:40:48Z  
**Scope:** Design audit only; S4 implementation absent (expected)

## Executive summary

**PASS** — The S4 architecture design (SHA `37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2`) specifies a sound exact-signature belief abstraction with:

- **Fixed-bucket perfect recall** with complete public history retention
- **Abstract-key information safety** excluding opponent bucket/world/cards
- **Exact signature contracts** for blocker-aware behavioral twins
- **GameState solver compatibility** via immutable ReducedState protocol
- **Exact-key lift** with ordered-action coverage and twin-policy equality
- **Immutable detachment** throughout plan/result records
- **Reduced vs exact metric scope** explicitly distinguished
- **Exact diagnostics bounds** with separate optional evaluation
- **Rational certificate** for zero model error and value bounds
- **R1 repairs** addressing API schema, bounds, and integer weight preservation

No S4 production code exists in `src/poker_solver/`; this is a design checkpoint before implementation batches S4-I1 through S4-I4.

---

## 1. Frozen input verification

Recomputed SHA-256 hashes match task specification exactly:

```
37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2  ARCHITECTURE_PHASE4_S4.md
f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed  CANDIDATE_MANIFEST.md
5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61  PHASE4_MISSION.md
79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d  02-engine-integration-codex.md
```

All frozen inputs present. Output directory `.hb/` exists. Working directory confirmed `/home/genomix-node/poker-solver`.

---

## 2. Fixed-bucket perfect recall and noninterference

### Evidence: Architecture §3.3, §6

**Lines 71-78:** Fixed bucket assigned at root, retained through all streets. No rebucketing merges distinct prior buckets. Abstract key contains: policy version, config digest, acting player, own bucket ID, full public frame (board, street, actor, pot, commitments, contributions, stacks, last-raise, betting history, RUNOUT history, terminal marker).

**Lines 219-222:** PublicFrame.history retains every prior betting action and revealed card. Player reconstructs entire own bucket/public observation/action sequence from key. Same key implies same own observation/action sequence.

**Lines 126-132 (AbstractInfoKey schema):** Excludes opponent bucket, world IDs, member cards, member probabilities, pair mass, pair index, representative card, root ABSTRACT_DEAL action.

**Lines 221-223:** Config digest is constant across all states, conveys no realized private outcome.

### Finding

**PASS** — Design mandates fixed buckets, complete public history in keys, explicit exclusion of opponent/world state. Compile-time recall/noninterference checks required before solver construction (§4.1). Implementation batch S4-I2 RED must prove this before GREEN.

---

## 3. Abstract-key information safety

### Evidence: Architecture §6, §9

**Lines 221-223:** Key excludes opponent bucket, world IDs, member cards, member probabilities, pair mass, pair index, representative card, root ABSTRACT_DEAL action.

**Lines 222-223:** Digest identifies public configured ranges/policy; same digest in every state; conveys no realized private outcome.

**Lines 451-453:** Digest is SHA-256 over canonical JSON of normalized semantic source config + abstraction config. Includes digest_schema, sorted keys, canonical card/runout order, RationalRecord for weights/fractions.

**Lines 223-226 (lift projection):** Reconstruct source exact key, map own cards through certified bucket table, project public frame (remove DEAL only). Obtain abstract key's complete policy. Populate under ORIGINAL exact key.

### Finding

**PASS** — Abstract keys contain only own bucket + public observables. Config digest constant across states. Lift preserves exact keys while copying abstract policies. No opponent information leaks into acting player's key.

---

## 4. Exact signature and blocker contracts

### Evidence: Architecture §3.2

**Lines 54-64:** For player 0 hand h, signature has one cell per canonically ordered player 1 hand g. Cell is `(0, ())` if incompatible, or `(1, codes)` with one code per configured ordered full runout. Runout code is `-2` when blocked, else `-1/0/+1` for showdown loss/tie/win from owning player's perspective. Entire tuple is identity certificate. Hashes identify plans but never replace equality of complete tuple. Mismatch may not be overridden to meet cap.

**Lines 67-68:** Scalar equity, made-hand category, hole-card ranks, informal suit symmetry are NOT certificates. Equal-equity hands separated by opponent blocker or public-runout blocker MUST remain in different buckets.

**Lines 276-278:** Two compulsory blocker companions:
- Opponent-blocker fixture: equal-showdown hands but three compatible deals; both players' signatures stay separate.
- Runout-blocker fixture: one P0 hand blocks a declared runout; signatures stay separate, no positive deal conditioned away.

**Lines 65-66 (rectangular-cell proof):** Equal rows imply identical opponent compatibility, runout legality, payoff ordering against every labelled opponent hand. Equal columns provide same property for other player. Positive bucket-pair cell is rectangular: all member hand pairs compatible, same public chance kernel, identical terminal ordering for every configured public continuation.

### Finding

**PASS** — Signatures are complete labelled tuples including blocked cells. Blocker-distinct hands must separate even with equal equity. Rectangular-cell property proven. Companion tests enforce blocker safety. No lossy override permitted (line 63).

---

## 5. GameState solver compatibility

### Evidence: Source inspection + Architecture §4, §5

**Inspected files:**
- `model.py` (42 lines): GameState protocol with 6 methods, Action frozen dataclass, CHANCE=-1, TERMINAL=-2
- `multistreet.py` (500+ lines): MultiStreetConfig, MultiStreetState with exact private cards
- `cfr.py` (162 lines): CFRSolver with collect_infosets, regret_matching, train loop
- `best_response.py` (215+ lines): _scalable_best_response with dependency DAG, nash_conv
- `bounded_tree.py` (247 lines): validate_bounded_tree counting all history nodes

**Architecture lines 162-170 (ReducedState):** Implements GameState protocol with frozen plan, node_id, six methods. Lines 125-126: child is O(1) validated node lookup, never materializes member subtrees. Root chance actions are deterministic `Action("ABSTRACT_DEAL", k)` for sorted nonempty bucket pairs.

**Lines 150-151:** CFR traversal, strategy completion, reduced best response must construct zero exact-world GameState subtrees. Instrumented tests distinguish bounded preprocessing member checks from solve-time traversal.

**Lines 493-494 (S4-I3 RED):** Assert zero exact-world construction during train/complete/reduced-BR.

### Finding

**PASS** — ReducedState implements GameState protocol with immutable node-lookup child. Design explicitly forbids exact-world construction during solve. Instrumentation required in S4-I3 RED to prove zero exact subtrees during CFR/completion/BR.

---

## 6. Exact-key lift with ordered-action coverage

### Evidence: Architecture §6

**Lines 223-231:** For each exact decision state, reconstruct source exact key, map sorted own cards through certified bucket table, project full public frame/history (remove DEAL only). Obtain abstract key's COMPLETE policy; require identical ordered actions. Populate under ORIGINAL exact key. If exact key recurs, verify mapped abstract key and policy agree. Missing bucket/policy, differing actions, inconsistent duplicate key is error, never uniform repair. Copy same float values without recomputation into detached per-exact-key maps, deep-freeze output. Strategically identical certified hands have EXACTLY equal values; modifying one returned policy impossible, no mutable dictionary aliasing.

**Lines 227-228:** Full exact-tree materialization OPTIONAL, separately bounded. First validate exact root against explicit diagnostic max_nodes/max_depth, then lift and call nash_conv(exact_root, lifted). Gives values AND deviations on original exact information sets, not just reduced-game exploitability. Do not call complete_strategy on lifted profile to mask omissions.

**Lines 493-494 (S4-I3 RED):** Assert identical lifted policies for every P0 twin and every within-class P1 hand, no alias mutation, no hidden DEAL leakage, complete coverage of every reachable exact key, unknown-state and missing-policy errors.

### Finding

**PASS** — Lift maps exact keys through certified buckets, copies abstract policies to exact keys, requires ordered-action match, fails on missing/inconsistent policies. Twin hands receive bit-identical policy values. Deep-frozen detached output prevents aliasing. Optional exact diagnostics separately bounded.

---

## 7. Immutable detachment

### Evidence: Architecture §4.1, §9

**Lines 82-91:** Add abstraction.py with frozen/slotted, defensively detached records: AbstractionConfig, Bucket, World, MemberWeight, Belief, PublicFrame, AbstractInfoKey, Edge, Node, ReducedPlan, ReducedState.

**Lines 454-455:** Returned Python mappings and all nested containers detached and deeply immutable. JSON conversion creates fresh lists/objects with no mutable alias to result. Structured records, never str(key) dictionaries, preserve key/action identity.

**Line 508 (S4-I4 RED):** Tests cover deep response isolation, structured key/action serialization, JSON finite safety.

### Finding

**PASS** — All records frozen/slotted with defensive detachment. Factories must tuple-convert caller sequences. Result mappings recursively frozen. S4-I4 RED must test deep isolation and no mutable aliasing.

---

## 8. Reduced vs exact metrics

### Evidence: Architecture §9, §10

**Lines 351-353, 393-395:** metric_scope: Literal["reduced-game"], exact_evaluation_status: Literal["not-requested", "completed"]. Return explicitly named reduced_nashconv, reduced_exploitability, exact_nashconv (null unless evaluated), exact_evaluation_status. strategy_scope="abstract-bucket-public-history"; optional lifted strategy labelled exact-key scope. Do not reuse unqualified existing nashconv field for different metric scope.

**Lines 361-362:** provenance is exact sentence "finite-iteration float CFR over a certified exact-signature reduced configured multistreet game; exact rational aggregation; exact-tree diagnostics STATUS", with STATUS replaced by not-requested or completed.

**Lines 175-176:** Metadata distinguishes physical nodes, infosets, latent worlds, signature slots, belief entries, runtime. Must not imply smaller node count alone proves fixed runtime ratio.

### Finding

**PASS** — Reduced and exact metrics explicitly named and scoped. Provenance distinguishes reduced solve from exact diagnostics. Metadata separates physical nodes, worlds, signature/belief entries, exact counts. No conflation of reduced/exact scopes.

---

## 9. Exact diagnostics bounds and status

### Evidence: Architecture §6, §9

**Lines 227-229:** Exact diagnostics absent by default, have independent explicit bounds. Requested diagnostics exceeding bounds fail rather than returning silently missing fields.

**Lines 329-330:** Optional exact_evaluation is absent, null, or exactly {"max_nodes": int, "max_depth": int}. Integers and every bound positive, non-bool.

**Lines 361-362:** When exact_evaluation_status is not-requested, both exact metrics and lifted_strategy are null. When completed, both exact metrics finite and lifted_strategy non-null complete list. Requested diagnostic exceeding bound returns error, never successful response with not-requested.

### Finding

**PASS** — Exact diagnostics optional with separate bounds. Requested diagnostics exceeding bounds must fail (not return partial/unlabelled). Status field distinguishes not-requested vs completed. Null metrics when not-requested, non-null when completed.

---

## 10. Rational certificate and zero model error

### Evidence: Architecture §7

**Lines 252-254:** Exact-signature quotient has terminal diameter zero and identical observable kernels. For any bucket profile, rational reduced value equals rational exact lifted value. Extra exact-card distinctions cannot improve response because types within bucket have identical labelled continuations and factorized conditional mass; realization-plan mixture implementable under perfect recall. Therefore v1 model-error term exactly zero. This is certificate, not claim float CFR converged.

**Lines 246-251:** For complete profile x in SAME exact two-player zero-sum game: v(x)=u0(x), U(x)=BR0(x1), L(x)=-BR1(x0), e0(x)=U(x)-v(x), e1(x)=v(x)-L(x), C(x)=e0(x)+e1(x)=U(x)-L(x). Minimax gives L(x) <= v* <= U(x). For lifted abstract profile a and independently trained exact reference r: |v(a)-v(r)| <= max(e1(a)+e0(r), e0(a)+e1(r)) <= C(a)+C(r).

**Lines 255-256:** Small-fixture tests rationalize returned policy probabilities with Fraction.from_float, normalize each policy exactly, replay exact chance/utility. Independently compute rational best-response incentives over bounded 321-node tree, compare ordinary float metrics within 1e-10 chips.

**Lines 493-494 (S4-I3 RED):** Required cases cover rational incentive theorem, small 1,000-iteration quality gates.

**Lines 439-440, 450 (metadata):** terminal_diameter: RationalRecord, model_error_bound: RationalRecord. For v1 lossless policy, both exactly zero rational records.

### Finding

**PASS** — Design proves zero model error via lossless-response theorem (identical kernels, factorized mass, rectangular twins). Value-gap bound uses finite-profile incentives without equilibrium assumption. S4-I3 RED must implement rational certificate with Fraction replay. Metadata reports terminal_diameter=0, model_error_bound=0.

---

## 11. R1 repairs

### Evidence: CANDIDATE_MANIFEST.md lines 20-28

R1 alternate API auditor C4D4-CODEX report rejected earlier architecture SHA `4285905100a11e3523b241f236233118bb9f4dac67f7c8aa92570fba3048a0e3` for three reproduced findings:

1. Incomplete exact response and nested wire schema
2. Ambiguous optional versus required base bounds
3. Integer range weights above 2^53 losing exactness through inherited _float parsing

R2 repairs only contract surface. Freezes exhaustive response/key/action/policy/membership/rational/metadata schema, makes base max_nodes/max_depth mandatory only for new operation and equal to abstraction bounds, preserves prior operation defaults, preserves non-bool integer weights before Fraction conversion, fixes digest canonicalization, expands I4 RED cases. No production, tests, scripts, dependency, mission, or accepted Git bytes changed.

### Verification

**Architecture §9.1 (lines 304-333):** Exhaustive wire schema with all required/optional fields, nested record shapes, RationalRecord for weights/fractions, integer weight preservation via Fraction(value) for non-bool JSON integers and Fraction.from_float(value) for finite JSON floats. Local to new operation; prior operations retain existing float-coercion.

**Architecture lines 227-229, 389-391:** Allstreet facade requires config.max_nodes == abstraction.max_abstract_nodes and config.max_depth == abstraction.max_depth; ambiguous dual bounds fail. Existing exact functions/result classes semantically unchanged.

**Architecture lines 451-453:** Digest canonical JSON with sorted keys, RationalRecord for weights/fractions.

### Finding

**PASS** — R1 findings addressed. Exhaustive wire schema specified (§9.1). Base bounds mandatory for new operation, equal to abstraction bounds; prior operations unchanged. Integer weights preserved before Fraction conversion. Digest canonicalization fixed. S4-I4 RED expanded.

---

## 12. Implementation absence (expected)

No abstraction.py or abstraction_solve.py exists in src/poker_solver/. Search returned 0 files matching "abstraction". This is a design checkpoint before implementation batches S4-I1 through S4-I4 (Architecture §10, §11).

**Architecture lines 460-512:** Four RED-first implementation batches with focused tests, fresh non-author audits, full regression. S4 completion gate (§12) requires all batches accepted, exact counts verified, blocker companions passing, twin-policy equality, zero exact-world construction during solve, metadata distinctions, phase3-398-green unchanged.

---

## 13. Conclusion

**PASS** — S4 architecture design is sound, complete, and ready for implementation. All audit dimensions satisfied:

1. **Fixed-bucket perfect recall:** Mandated, compile-time checks required
2. **Abstract-key information safety:** Opponent/world state excluded, digest constant
3. **Exact signature contracts:** Complete labelled tuples, blocker separation, rectangular proof
4. **GameState solver compatibility:** ReducedState protocol, zero exact-world construction during solve
5. **Exact-key lift:** Ordered-action coverage, twin-policy equality, deep-frozen detachment
6. **Immutable detachment:** Frozen/slotted records, defensive factories, deep isolation
7. **Reduced vs exact metrics:** Explicit scope labeling, provenance, metadata distinctions
8. **Exact diagnostics bounds:** Optional, separate bounds, fail on exceed, status field
9. **Rational certificate:** Zero model error proven, value-gap bound, Fraction replay
10. **R1 repairs:** Wire schema, bounds, integer weights, digest canonicalization

No blockers. Implementation batches S4-I1 through S4-I4 may proceed with RED-first discipline and fresh non-author audits per Architecture §10-11.

---

**Report path:** `/home/genomix-node/poker-solver/research/phase4/s4-design-audit-r2/03-information-lift-retry.md`  
**Timestamp UTC:** 2026-09-16T12:40:48Z  
**Agent:** R2A3R  
**Status:** COMPLETE_PASS  
**Blocked:** false
