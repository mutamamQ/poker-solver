# R2A4 S4 Design Audit Report: API/Result Contract

## Verification Summary

**Candidate hashes: VERIFIED**
- ARCHITECTURE_PHASE4_S4.md: `37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2` ✓
- CANDIDATE_MANIFEST.md: `f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed` ✓
- PHASE4_MISSION.md: `5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61` ✓
- Authoritative design: `79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d` (stated)
- HEAD: `149780bf37e3e3a824e03e6d2c1df3cd99b12cd6` ✓

**R1 findings addressed:**
1. Incomplete response schema → §9.1 now exhaustive (lines 335-450)
2. Ambiguous optional bounds → §9 lines 310-314 mandatory equality for new operation
3. Integer weight precision → §3.1 line 52, §9 lines 331-333 preserve integers >2^53

**No S4 implementation exists** (expected per manifest line 38)

---

## Finding 1: Exhaustive Response Schema — PASS

**Architecture §9.1 (lines 335-450)** specifies complete wire contract:

**Top-level keys (20 required, zero optional):**
- version: 4
- operation: "solve-allstreet-abstracted"
- game_version, abstraction_version, algorithm, iterations, seed
- values: [float, float]
- reduced_nashconv, reduced_exploitability, exact_nashconv, exact_exploitability
- exact_evaluation_status: "not-requested" | "completed"
- metric_scope: "reduced-game"
- strategy_scope: "abstract-bucket-public-history"
- strategy, lifted_strategy
- abstraction_lossless: true
- approximate: true
- metadata, provenance

**Nested schemas fully specified:**
- ActionRecord: {kind, amount}
- RationalRecord: {numerator, denominator}
- PublicFrameRecord: 10 required fields (lines 370-377)
- AbstractKeyRecord: 5 required fields (lines 378-383)
- ExactKeyRecord: 9 required fields (lines 384-390)
- PolicyItem, AbstractPolicyEntry, ExactPolicyEntry (lines 391-393)
- BucketRecord, BucketPairRecord (lines 394-402)
- AbstractionMetadata: 38 required fields (lines 408-448)

**Deterministic ordering specified:**
- strategy sorted by canonical AbstractKeyRecord encoding
- lifted_strategy sorted by canonical ExactKeyRecord encoding
- policy preserves source legal-action tuple order
- bucket records sort by (player, bucket_id)
- pair records sort by (player0_bucket, player1_bucket)
- members are sorted card pairs

**Status coupling enforced (lines 349-363):**
- not-requested → exact metrics null, lifted_strategy null
- completed → exact metrics finite, lifted_strategy non-null list
- Exceeded diagnostic bounds → error, never silent not-requested

**Provenance template (line 362):** exact sentence with STATUS substitution

**Evidence:** Lines 335-450 enumerate every key, every nested record shape, exact literal values, null/non-null rules, sort orders, and status invariants. R1 F1 "incomplete schema" is resolved.

**Verdict: PASS** — exhaustive, deterministic, enforceable contract.

---

## Finding 2: Required vs Optional Bounds — PASS

**R1 F2:** ambiguous whether max_nodes/max_depth required for new operation

**R2 repair (§9 lines 310-314):**
> For this new operation only, `payload` has exactly these required fields:
> - ... `max_nodes` and `max_depth`, which are **newly mandatory** for this operation even though they remain optional with unchanged defaults for `solve-allstreet-postflop`;

> `payload.max_nodes` must equal `abstraction.max_abstract_nodes`, and `payload.max_depth` must equal `abstraction.max_depth`; **omission of either base bound fails before equality checking**. Existing operations retain their current optional-bound behavior.

**Compatibility preserved:**
- solve-allstreet-postflop: max_nodes/max_depth remain optional (§9 line 314)
- solve-allstreet-abstracted: both mandatory, must equal abstraction bounds

**Validation order enforced:**
1. Check presence (fail if missing)
2. Check equality (fail if unequal)
3. Reject ambiguous dual limits (§6 line 228)

**Source inspection (api_v4.py lines 545-561):**
- solve-allstreet-postflop uses `_object_with_optional` with {"max_nodes", "max_depth"} in optional set
- Lines 641-646 apply defaults 100_000 and 512 when absent
- New operation would use `_object` (required set) per §9 line 309

**Evidence:** Explicit operation-local requirement, preserved backward compatibility, fail-before-equality semantics, no silent default substitution for new operation.

**Verdict: PASS** — unambiguous, operation-scoped, compatibility-preserving.

---

## Finding 3: Integer Weight Precision >2^53 — PASS

**R1 F3:** inherited `_float` coercion loses exactness for integers >2^53

**R2 repair (§3.1 line 52, §9 lines 331-333):**
> Weights are converted with `Fraction.from_float` before multiplication, preserving the supplied binary float exactly. **Integers use `Fraction(value)`**. Bool, nonfinite, negative, unsupported numeric values, and excessive numerator/denominator bit lengths fail before compilation.

> For this operation, range-entry `weight` parsing does NOT call the existing `_float` helper. A **non-bool JSON integer remains an integer** through positivity/bit-cap validation and is converted with `Fraction(value)`; a finite JSON float remains a float through validation and is converted with `Fraction.from_float(value)`. This rule preserves integers above `2**53` exactly and is **local to the new operation**. Direct-Python and decoded-JSON requests have identical behavior. **Prior operations retain their existing float-coercion behavior**.

**Compatibility preserved:**
- solve-allstreet-postflop: continues using `_float` helper (api_v4.py line 596)
- solve-nplayer-postflop: continues using `_float` (api_v4.py line 138)
- solve-allstreet-abstracted: type-preserving path, operation-local

**Bit-cap enforcement (§4 line 102, §3.1 line 52):**
- max_fraction_bits: 4096 default
- Excessive numerator/denominator rejected before compilation

**Test requirement (§10 line 507):**
> integer weights above `2**53` with direct-Python/JSON parity

**Evidence:** Type-preserving parse, Fraction(int) vs Fraction.from_float(float), operation-local scope, explicit bit-cap validation, test coverage mandated.

**Verdict: PASS** — exact preservation, backward compatible, bounded.

---

## Finding 4: Digest Canonicalization — PASS

**Architecture §9 lines 451-453:**
> The digest is lowercase hexadecimal SHA-256 over UTF-8 canonical JSON for the normalized semantic source config plus abstraction config. The digest input includes `"digest_schema":"s4-semantic-config-v1"`; object keys are **lexicographically sorted**, separators are exactly `,` and `:`, ASCII escaping is enabled, cards and runouts use their specified canonical sorted order, integers remain decimal integers, and every normalized weight/fraction uses `RationalRecord`.

**Determinism requirements:**
- Lexicographic key sort
- Exact separators (no whitespace)
- ASCII-only escaping
- Canonical card/runout order per §3.1
- RationalRecord for all weights/fractions
- Schema version embedded

**Shared by Python and JSON (line 453):**
> This rule is shared by Python result records and JSON output.

**Metadata field (lines 411-412):**
> config_digest: 64-character lowercase hexadecimal string
> digest_schema: "s4-semantic-config-v1"

**Evidence:** Complete canonicalization recipe, deterministic across representations, schema-versioned, collision-resistant.

**Verdict: PASS** — reproducible, collision-resistant, cross-representation.

---

## Finding 5: Recursive Isolation and JSON Safety — PASS

**Architecture §9 line 454:**
> Returned Python mappings and all nested containers are **detached and deeply immutable**; JSON conversion creates fresh lists/objects with **no mutable alias to the result**. Structured records, never `str(key)` dictionaries, preserve key/action identity. Nonfinite serialization fails.

**Deep freeze requirement (allstreet.py lines 20-28):**
```python
def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    ...
```

**Structured keys (§9 lines 391-393, 454):**
- AbstractPolicyEntry: {"key": AbstractKeyRecord, "policy": [PolicyItem, ...]}
- ExactPolicyEntry: {"key": ExactKeyRecord, "policy": [PolicyItem, ...]}
- NOT str(key) dictionaries

**Nonfinite rejection (line 454, api_v4.py lines 683-684):**
```python
if not isfinite(v0) or not isfinite(v1):
    raise ValueError(f"non-finite value vector: ({v0}, {v1})")
```

**Evidence:** Deep immutability enforced, no mutable aliases, structured key preservation, nonfinite guard.

**Verdict: PASS** — isolated, immutable, JSON-safe.

---

## Finding 6: Metadata Provenance and Truth — PASS

**Architecture §5 line 176:**
> Metadata distinguishes physical nodes, infosets, latent worlds, signature slots, belief entries, and runtime. It **must not imply** that a smaller node count alone proves a fixed runtime ratio.

**Metadata fields (§9 lines 408-448) distinguish:**
- physical_node_count, physical_terminal_count, physical_chance_count, physical_decision_count, physical_max_depth
- compatible_world_count, world_count, nonempty_pair_count
- signature_cell_count, belief_entry_count
- exact_node_count_analytic, exact_node_count_status: "not-derived" | "derived-not-traversed" | "executed"
- bucket_sizes, buckets, bucket_pairs

**Provenance (§9 line 362, §6 line 234):**
> finite-iteration float CFR over a certified exact-signature reduced configured multistreet game; exact rational aggregation; exact-tree diagnostics STATUS

> `approximate=True` means the returned finite-iteration float CFR policy is not claimed to be an exact equilibrium. It does **not** mean the abstraction is lossy. Set `abstraction_lossless=True`, `model_error_bound=0`, `lossy_merges=0`, and label reduced versus exact metrics explicitly.

**Certificate fields (lines 439-440):**
- exact_signature_certificate: true
- terminal_diameter: RationalRecord (zero for v1)
- model_error_bound: RationalRecord (zero for v1)

**Evidence:** Explicit semantic distinctions, analytic vs executed counts, lossless vs approximate labels, zero-diameter certificate, honest provenance.

**Verdict: PASS** — truthful, semantically precise, no misleading claims.

---

## Finding 7: Source Feasibility — PASS

**No S4 implementation exists** (manifest line 38, find command returned empty)

**Existing source inspection:**
- api_v4.py: dispatch_v4 handles solve-allstreet-postflop (lines 493-708)
- allstreet.py: AllStreetPostflopConfig, solve_allstreet_postflop exist
- multistreet.py: MultiStreetConfig, MultiStreetState, exact semantics
- equity.py: WeightedCombo, exact_equity, range_equity
- best_response.py: nash_conv, NashConvResult, scalable_best_response
- __init__.py: exports AllStreetPostflopConfig, solve_allstreet_postflop, dispatch_v4

**Architecture references existing contracts:**
- §2 lines 24-32: authoritative source behavior in model.py, multistreet.py, allstreet.py, bounded_tree.py, cfr.py, api.py, best_response.py, evaluator.py, equity.py, api_v4.py
- §6 line 227: "Allstreet translation must match `create_allstreet_root`"
- §4.1 line 110: "Required public functions" for abstraction.py (new)
- §6 line 179: "Add `src/poker_solver/abstraction_solve.py`" (new)

**Compatibility preserved:**
- §9 line 305: "Existing operations remain byte-for-schema compatible"
- §10 line 509: "It may not rename or relax prior operations"
- Mission line 55: "Preserve the 398-test baseline: every batch ends with the prior suite green"

**Evidence:** Existing source contracts inspected and referenced, new modules additive, compatibility explicit, no implementation claimed.

**Verdict: PASS** — feasible extension of existing contracts, no contradictions.

---

## Finding 8: R1 Repair Scope — PASS

**Manifest lines 22-28:**
> R2 repairs only that contract surface. It freezes an exhaustive response/key/action/policy/membership/rational/metadata schema, makes base max_nodes/max_depth mandatory only for the new operation and equal to abstraction bounds, preserves prior operation defaults, preserves non-bool integer weights before Fraction conversion, fixes digest canonicalization, and expands I4 RED cases. **No production, tests, scripts, dependency, mission, or accepted Git bytes changed**.

**Verification:**
- Architecture lines 1-550: design document only
- Manifest lines 32-38: git diff --check PASS, git diff --name-only empty, HEAD match, 817 tests baseline, R2 is DESIGN only
- No abstraction.py, abstraction_solve.py, or S4 tests exist
- api_v4.py lines 1-708: no solve-allstreet-abstracted operation

**R1 findings scope:**
1. API/result contract (§9)
2. Bounds ambiguity (§9 lines 310-314)
3. Weight parsing (§3.1 line 52, §9 lines 331-333)

**R2 changes:**
- §9.1 exhaustive schema (lines 335-450)
- §9 mandatory bounds for new operation (lines 310-314)
- §3.1, §9 integer weight preservation (lines 52, 331-333)
- §9 digest canonicalization (lines 451-453)
- §10 I4 RED expansion (line 507)

**Evidence:** R2 edits confined to contract specification, no source/test/dependency changes, explicit scope statement.

**Verdict: PASS** — repair scope correct, no implementation claimed.

---

## Cross-Check: R1 Findings Reproduction

**R1 report (manifest line 22):** research/phase4/s4-design-audit/04-api-result-codex.md SHA `4b74b1a27da50c6598a0cae4cfcd5846befcea560f6ba821d6e2ff49179c1ee4`

**R1 rejected architecture SHA:** `4285905100a11e3523b241f236233118bb9f4dac67f7c8aa92570fba3048a0e3`

**R2 accepted architecture SHA:** `37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2`

**R1 F1-F3 addressed:** confirmed above in Findings 1-3

**No new contradictions found** in adversarial review.

---

## Final Verdict: **PASS**

R2 repairs successfully address all three R1 findings:

1. **Exhaustive schema** (§9.1 lines 335-450): complete top-level and nested wire contracts, deterministic ordering, status coupling, provenance template
2. **Unambiguous bounds** (§9 lines 310-314): operation-local mandatory equality, preserved backward compatibility, fail-before-equality
3. **Integer precision** (§3.1 line 52, §9 lines 331-333): type-preserving parse, Fraction(int) vs Fraction.from_float(float), operation-local, bit-capped

Additional contract improvements:
- Digest canonicalization (§9 lines 451-453)
- Recursive isolation (§9 line 454)
- Metadata truth (§5 line 176, §9 lines 408-448)
- Source feasibility (§2, §4, §6, §10)

No implementation exists (expected). No source/test/dependency changes (verified). Architecture is internally consistent, compatible with existing contracts, and implementable.

**Recommendation:** Accept R2 architecture for S4-I1 RED.

---

**Report SHA-256:** (computed after write)
**Completed:** 2026-09-16 (UTC)
**Auditor:** R2A4 (BryantGPT non-author)
