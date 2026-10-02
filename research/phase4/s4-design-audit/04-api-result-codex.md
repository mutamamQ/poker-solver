# C4D4-CODEX — API/result design audit

Final verdict: **REJECT**. One HIGH and two MEDIUM specification findings require resolution. This is a design verdict, not an implementation failure.

Auditor: C4D4-CODEX, alternate-provider non-author replacement auditor. Scope: typed abstraction configuration/results, additive strict v4 API, serialization, provenance and metric truthfulness, allstreet/export compatibility, and feasibility against current source. No sub-agents were used.

## Candidate authentication and method

The architecture SHA-256 matches the user-required value and candidate manifest:
`4285905100a11e3523b241f236233118bb9f4dac67f7c8aa92570fba3048a0e3`.

Read the complete frozen architecture, candidate manifest, mission, allstreet facade, and package exports; inspected the relevant strict dispatcher/parser/serializer source. Supplemental read-only checks inspected WeightedCombo, NashConvResult, and exact root chance normalization. Executed a small existing-parser probe with bytecode writes disabled. No S4 implementation or tests were required, created, or evaluated. No claims about fixture counts, convergence receipts, full regression, or the mathematical quotient proof are independently certified by this scoped report.

Observed input hashes:

| Input | SHA-256 |
| --- | --- |
| CANDIDATE_MANIFEST.md | db0932118f6370fcaf432fed35e9bd3e170974deb3a379bbe955e42a4b7fd76c |
| PHASE4_MISSION.md | 5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61 |
| src/poker_solver/api_v4.py | 70d378d6a52ae544615a5aa4dda6bd9e987f8161f08119914a0762ed0727a1a3 |
| src/poker_solver/allstreet.py | 30d94c226a82375afa2a10f4e3c3b785e37009257023b65da296742bf7cbd1ea |
| src/poker_solver/__init__.py | 0c2a03813d375d362c582b3df0744d80802c5f008e2b42825f4afeaed5326159 |

Line references below refer to these inspected bytes and the authenticated architecture. PASS means an adequate design obligation, not an implemented/tested S4 feature.

## Requirement assessment

| Requirement | Verdict | Evidence and assessment |
| --- | --- | --- |
| Typed AbstractionConfig | PASS | Architecture lines 91–105 give exact frozen/slotted fields, literal policy version, defaults, positive non-bool integer bounds, recursion ceiling, and arithmetic caps. Lines 42–52 require defensive canonicalization and strict support/weight validation. |
| Typed AbstractSolveResult | PASS | Lines 181–223 define diagnostic config, typed metrics, strategies, plan, flags, scope, status, provenance, and metadata. Lines 230–234 require recursively frozen detached mappings and distinguish finite training from abstraction loss. |
| Additive v4 operation | PASS | Lines 304 and 381 explicitly preserve prior operations and prohibit renaming/relaxing them. Existing dispatch branches at api_v4.py:530–545 permit an independent new branch. Missing new operation is expected. |
| Exact request schema | FAIL | Abstraction and exact_evaluation field sets are specified, but inherited base-bound optionality contradicts the description of “existing required” bounds. F2. |
| Exact response and nested wire schemas | FAIL | Architecture line 322 says fields “include” a mixture of exact identifiers and prose; lines 324–326 do not define record layouts or an exhaustive metadata schema. This cannot determine the exact-key tests required by line 379. F1. |
| Unknown-field and type rejection | PASS | Lines 105 and 320 expressly reject unknown/missing fields, bool-as-int, nonfinite values, duplicate holdings, invalid cards, incompatible limits, and algorithm/seed mismatch. Existing helpers support strict validation. Exact required/optional base-field membership remains F2. |
| Recursive JSON safety and detached containers | PASS | Lines 230 and 324 explicitly require deep isolation, frozen Python mappings, structured keys/actions, string-encoded rational masses, exclusion of internal arrays, and nonfinite rejection. Concrete wire layouts remain F1. |
| Finite values and arithmetic truth | PASS | Lines 52, 105, 172–175, and 320–324 bound arithmetic and reject nonfinite inputs/outputs. This applies to nested output floats, not merely values. The integer ingress ambiguity is separately F3. |
| Abstraction metadata/provenance semantics | PASS | Lines 234 and 326 require lossless/model-error labels, resource categories/caps, digests, membership counts, arithmetic semantics, diagnostic status, and restricted finite-game provenance. Exact names/types are F1. |
| Explicit reduced versus exact metrics | PASS | Typed reduced_metric/exact_metric and metric_scope at lines 193–201; distinct reduced/exact wire metric names at line 322. Existing NashConvResult fields and exploitability property support this mapping (best_response.py:13–22). |
| exact_evaluation_status consistency | PASS | Lines 201 and 228–230 permit not-requested or completed, prohibit silently missing requested diagnostics, and tie lift traversal to explicit bounded evaluation. Thus absent/null request implies not-requested with no exact metric/lift; successful requested evaluation implies completed with exact metric and lift; cap failure returns an error rather than a success status. Wire omission versus null for lifted_strategy still needs F1's schema resolution. |
| Existing allstreet/export compatibility | PASS | Architecture line 228 requires matching create_allstreet_root. allstreet.py:177–193 translates to multistreet-v1, flop start, river_betting=True, and the same game fields. __init__.py:3–29 exposes existing APIs via imports; additive abstraction imports are feasible. No deletion/change of old exports is required. |
| Implementation feasibility against source | PASS | Separate abstraction/compiler and solve modules can avoid the exact facade's mandatory preflight at allstreet.py:232–238. Existing metric structure is usable; isolated parsing/serialization can satisfy the new rules without changing old operations. F3 identifies a required ingress distinction that must be made explicit. |

## Findings

### F1 — HIGH — Exact response contract is not actually frozen

Evidence: architecture lines 322–326 and 379. The response specifies required fields that “include” operation/version, several precise metric names, and prose items “reduced strategy,” “optional lifted strategy,” and “abstraction metadata.” It never enumerates the exact top-level key set. It also leaves the key/action structured-record layout, policy-entry container, bucket membership layout, rational mass container, and metadata field names/types unstated. “Numerator/denominator strings” does not determine whether a mass is a two-field object, a two-element array, or one rational string. Section 3.3 specifies semantic key content but does not define its JSON record.

Concrete ambiguity: one implementation can return a top-level strategy list with entries containing key and policy records; another can return reduced_strategy with different entry names. Both satisfy the prose. A response without a lifted_strategy key and one with lifted_strategy=null both fit “optional lifted strategy” when diagnostics are absent. The architecture also does not establish whether metric_scope and abstraction_lossless are top-level wire keys or represented only inside metadata. Consequently independent authors cannot write one authoritative exact response-key assertion before implementation, despite the explicit S4-I4 gate.

Impact: incompatible client contracts can each claim compliance with this frozen design; serialization/collision/isolation tests must invent the schema they are supposed to verify. This blocks the requested exact-schema design checkpoint.

Required correction: provide an exhaustive response schema with exact key names, types, required/nullable rules, the two diagnostic-status cases, and nested strategy/key/action/membership/mass/metadata record definitions. Specify deterministic ordering where list order carries identity or affects canonical output. Include the digest encoding/version rules needed for interoperable provenance. This is a design clarification, not a request to implement S4 now.

### F2 — MEDIUM — Inherited base limits are described as required although existing v4 makes them optional

Evidence: architecture line 306 inherits the existing allstreet base payload and conventions, while line 320 calls max_nodes/max_depth “Existing required base” fields. Actual api_v4.py:545–563 puts both in the optional set, and lines 640–646 supply defaults 100000 and 512. AllStreetPostflopConfig has the same defaults at allstreet.py:43–44. New abstraction defaults are 10000 and 32 (architecture lines 97–98), and line 228 mandates equality.

Concrete ambiguity: a payload containing every existing required field plus the full abstraction object, but omitting base max_nodes/max_depth, satisfies the inherited base schema. Applying old defaults makes it fail equality; requiring the fields makes it fail missing-field validation; deriving them from abstraction makes it pass. The frozen document does not clearly select a new-operation rule while inaccurately describing the old one.

Impact: the accepted request set and first validation failure are indeterminate. Requiring limits in shared old parsing would violate the additive compatibility requirement.

Required correction: explicitly state that these fields are newly mandatory only for solve-allstreet-abstracted, or specify a single omission/default rule for that operation. Preserve existing operations' optional bounds and defaults. Pin omitted, one-omitted, equal, and unequal cases in future RED tests.

### F3 — MEDIUM — Inherited weight parsing conflicts with exact integer ingress unless explicitly specialized

Evidence: architecture line 52 requires integers to use Fraction(value), preserving their exact value, while line 306 inherits existing base conventions. api_v4.py:596 parses each weight with _float; lines 55–65 unconditionally perform float(value). WeightedCombo itself does not coerce a weight to float (equity.py:30–41), so the loss occurs at the API ingress.

Read-only executable probe of the existing helper:

```text
integer_weight: 9007199254740993
existing_parser: 9007199254740992.0
design_integer_fraction: 9007199254740993
existing_parser_fraction: 9007199254740992
```

The input is positive and fits the declared default Fraction bit cap. Paired with other unequal weights, rounding changes rational masses and their provenance. This is a demonstrated current-parser behavior, not a claim that absent S4 code contains a defect. Section 3.1 supplies a good arithmetic rule, but Section 9 must explicitly exclude the old coercion when inheriting conventions.

Required correction: state that the new operation retains non-bool JSON integers as integers and finite floats as floats through weight validation, before the prescribed Fraction conversion. Do not globally change _float or prior request semantics. Add a future direct-Python versus JSON integer-weight parity case above 2**53, alongside bool/nonfinite rejection. If a narrower integer domain is intended instead, freeze that domain and its rejection behavior explicitly.

## Feasibility notes and limits

The existing allstreet serializer is not an adequate implementation template for the new response: api_v4.py:672–678 stringifies keys/actions; lines 680–685 check only the value vector; line 703 makes only a shallow metadata dict. Architecture line 324 already requires stronger behavior, so these are integration constraints rather than additional design failures. A separate recursive serializer is feasible without altering old schemas.

The result's finite-iteration approximate=True and lossless abstraction flag are consistent. Existing allstreet approximate=False at allstreet.py:268 has a different established contract, which the architecture explicitly preserves. No contradiction is inferred merely from these different flags on different operations.

The frozen mappings requirement is substantive: dataclass(frozen=True) alone cannot freeze nested policy/metadata contents. Architecture line 230 supplies the missing behavioral obligation; future implementation tests should enforce it. Existing allstreet.py:20–28 and 166–174 demonstrate relevant defensive-copy patterns, but arbitrary opaque metadata objects must not leak through the new JSON conversion.

No full solver regression was run because this assignment assesses a frozen design and permits only two output artifacts. Existing parser probes and source comparisons suffice for these findings. No production, tests, architecture, manifest, mission, state, progress, Git history, or other worker artifacts were edited.

## Final decision

**REJECT** pending F1–F3 design clarification. The typed model, metric/status semantics, provenance requirements, and additive integration approach are viable. The blocking issue is the incomplete exact API contract and its unresolved inheritance rules. Missing future S4 symbols are expected and contribute no finding.
