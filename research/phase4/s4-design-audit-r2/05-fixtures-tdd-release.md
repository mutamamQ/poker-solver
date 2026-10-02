# R2A5 S4 design audit: fixtures, RED-first sequencing, audit/commit gates, and release

**Auditor:** R2A5 (wholly fresh non-author DESIGN auditor)
**Timestamp:** 2026-09-16 (UTC)
**Scope:** Preregistered fixtures, blocker companions, RED-first permanent test contract for I1-I4, dependency-safe batches, corrected I4 schema/weight/bound cases, per-batch exact-six fresh audit and accepted commit gate, full S4 release sufficiency, and no unsupported overclaim.
**Status:** COMPLETE

## 1. Candidate verification

Recomputed SHA-256 hashes for all frozen candidate documents:

- `ARCHITECTURE_PHASE4_S4.md`: `37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2` ✓
- `research/phase4/s4-design-audit-r2/CANDIDATE_MANIFEST.md`: `f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed` ✓
- `PHASE4_MISSION.md`: `5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61` ✓
- `research/phase4/s4-design/02-engine-integration-codex.md`: `79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d` ✓

Repository state:
- HEAD: `149780bf37e3e3a824e03e6d2c1df3cd99b12cd6` ✓
- Tag `phase3-398-green`: `feba8222a0b614b0c64eca59402403ce733195ea` ✓
- No S4 implementation present (expected for design audit)
- No `test_abstraction*.py` files exist (expected)
- No `src/poker_solver/abstraction*.py` files exist (expected)

## 2. Preregistered fixtures audit

### 2.1 Small comparable fixture (§8.1)

**Specification completeness:** PASS

The architecture precisely defines:
- Flop: `Ah Kh Qh`
- Ordered runouts: `(Jh,9h)` and `(Jh,8h)`
- Initial dead pot: 2, effective stack: 1
- No-limit target `(1,)`, river betting enabled
- P0 hands: `2c3c`, `2d3d`
- P1 hands: `2s3s`, `Th4s`
- All weights: 1.0

**Expected statistics:** PASS

Exact tree:
- 321 nodes, 136 terminals, 57 chance nodes, 128 decisions, depth 12

Reduced tree:
- P0: 1 bucket; P1: 2 buckets
- 161 physical nodes
- 4 exact deal worlds → 2 abstract deal outcomes with masses 1/2 each
- Both rivers have conditional mass 1/2 after `Jh`

**Reference receipt:** PASS

Parent reference at 1,000 exact vanilla iterations:
- Values: `(-0.9993335546875001, 0.9993335546875001)`
- Best responses: `(-0.9993333333333333, 1.0000625)`
- Incentives: `(2.2135416677393494e-07, 0.0007289453125000067)`
- NashConv: `0.0007291666666667806`

Preregistered loose value-gap bound: 0.04 chips (§7)
Preregistered NashConv bound: 0.02 chips per profile

### 2.2 Blocker companion fixtures (§8.1)

**Opponent-blocker fixture:** PASS

Requirement: Equal-showdown hands but three compatible deals; both players' signatures stay separate.

This fixture ensures that hands with identical equity but different opponent blockers are NOT merged. Critical for proving the abstraction respects strategic distinctions beyond scalar equity.

**Runout-blocker fixture:** PASS

Requirement: One of otherwise similar P0 hands blocks a declared runout; signatures stay separate and no positive deal is conditioned away.

This fixture ensures that hands blocking different public runouts remain in separate buckets, and that blocked deals are rejected rather than silently removed.

### 2.3 Large bounded fixture (§8.2)

**Specification completeness:** PASS

Same public game as small fixture.

P0 range: every unordered pair from `2c 3c 4c 5c 6c 7c 2d 3d 4d 5d 6d 7d` (66 hands)
P1 range: every unordered pair from `2s 3s 4s 5s 6s 7s 2h 3h 4h 5h 6h Th` (66 hands)

All weights: 1.0
All 4,356 ordered pairs are compatible.

P0: 1 bucket of 66 hands
P1: 55-hand no-`Th` bucket + 11-hand `Th` bucket
Pair masses: 5/6 and 1/6

**Expected statistics:** PASS

Single-world public tree: 81 nodes, 34 terminals, 15 chance nodes, 32 decisions, depth 12

Exact physical nodes: `1 + 4,356 * 80 = 348,481`
Reduced physical nodes: `1 + 2 * 80 = 161`
Reduced terminals/chance/decisions: 68/29/64
Charged signature slots: 17,424
Literal belief member entries: 17,424

**Acceptance requirements:** PASS

Complete reduced path under 10,000 physical nodes and depth 32:
- Preflight
- 1,000-iteration vanilla training
- Completion
- Reduced NashConv
- Frozen result
- Strict serialization

Same exact config with 10,000 nodes must fail before training.
Result reports exact count as analytic certificate, not executed full traversal.

## 3. RED-first implementation batches audit

### 3.1 Batch sequencing and dependencies (§10)

**S4-I1 — policy, config, canonical signatures:** PASS

RED-owned tests:
- `tests/test_abstraction_signatures.py`

Required cases:
- Strict config/direct construction
- Deep immutability
- Input permutation determinism
- Fraction conversion and caps
- Duplicate/zero/blocked support
- Exact labelled row/column grouping
- Opponent blockers
- Runout blockers
- Equal-equity separation
- Bucket ID collision freedom
- Small/large membership tables

GREEN scope: `src/poker_solver/abstraction.py` up through canonicalization and `build_buckets` only. No state compiler or solver stubs.

Fresh audit scopes: schema/immutability; signature proof; blocker counterexamples; Fraction/caps; determinism/collision; full regression/release boundary.

**Dependency safety:** PASS. I1 has no dependencies on I2-I4.

**S4-I2 — worlds, beliefs, public compiler, ReducedState:** PASS

RED-owned tests:
- `tests/test_abstraction_reduced_game.py`

Required cases:
- Root mass
- Generalized posterior arithmetic
- Public turn-before-river chance
- Physical node/depth boundaries 160 fail/161 pass
- Expected small/large stats
- Source differential transitions
- Actor/action ordering
- Folds/refunds/all-ins/pot-limit/river-betting variants
- Exact odd-tie settlement
- Zero sum
- Perfect recall
- Hidden-state noninterference
- Instrumentation proving no exact-world GameState construction during traversal

GREEN scope: Bounded immutable world/belief/plan compilation and `ReducedState`. No solve/API edits.

Fresh audit scopes: probability/posteriors; source transition differential; physical counts/caps; settlement/conservation; recall/noninterference; full regression/performance payload.

**Dependency safety:** PASS. I2 depends on I1 (buckets), but not on I3-I4.

**S4-I3 — solver, lift, exact diagnostics, certificates:** PASS

RED-owned tests:
- `tests/test_abstraction_solve.py`
- Bounded test-only rational certificate helpers

Required cases:
- Vanilla and MCCFR seed contracts
- Reduced solve determinism
- Arbitrary nonuniform bucket-profile rational simulation equality
- Exact lift coverage and ordered actions
- Bit-identical twin policy values without mutable aliasing
- Exact diagnostic cap failures
- Scalable versus exhaustive tiny best response
- Rational incentive theorem
- Small 1,000-iteration quality gates
- Large complete solve
- Exact large preflight failure
- Zero exact-world construction during train/complete/reduced-BR

GREEN scope: `src/poker_solver/abstraction_solve.py` and minimum lift/projection additions in `abstraction.py`.

Fresh audit scopes: CFR/metric scope; lift/corruption; rational certificates; exact diagnostics; large complete solve/resource accounting; full regression/determinism.

**Dependency safety:** PASS. I3 depends on I1 (buckets) and I2 (ReducedState), but not on I4.

**S4-I4 — API, exports, examples, S4 docs:** PASS

RED-owned tests:
- `tests/test_api_v4_abstraction.py`
- `tests/test_phase4_s4_examples.py`
- `tests/test_phase4_s4_exports.py`

Required cases:
- At least one valid positive request must fail only because the new operation is absent
- Malformed-input cases are controls until GREEN
- Exhaustive top-level and nested schemas
- Both diagnostic-status cases
- Deterministic list ordering
- Integer weights above `2**53` with direct-Python/JSON parity
- Omitted/one-omitted/equal/unequal base and abstraction bounds
- Structured key/action serialization
- JSON finite safety
- Deep response isolation
- Existing-operation compatibility
- CLI file/stdin/error paths
- Executable examples

GREEN scope: Additive edits to `api_v4.py`, `__init__.py`, canonical examples, and only S4-specific README/docs text. May not rename or relax prior operations.

Fresh audit scopes: strict parser; serialization/collision/isolation; exports/compatibility; examples/CLI; docs truth; full regression/release.

**Dependency safety:** PASS. I4 depends on I1-I3 (complete solve pipeline), but is the final batch.

### 3.2 RED-first contract enforcement (§10)

**Permanent test contract:** PASS

Every permanent test:
- Imports and invokes production
- Contains no placeholder/pass/caught-import trick
- Is statically read by parent before GREEN

Existing baseline controls run separately during RED.

**Genuine RED verification:** PASS

Each batch's final test bytes must be proven as genuine pre-production RED against exact prior production snapshot.

### 3.3 Corrected I4 schema/weight/bound cases (§9, §10)

**R2 repairs (manifest §R1 finding and repair):** PASS

R2 addresses three reproduced R1 findings:

1. **Incomplete exact response and nested wire schema:** Fixed by exhaustive response/key/action/policy/membership/rational/metadata schema (§9.1)
2. **Ambiguous optional versus required base bounds:** Fixed by making `max_nodes` and `max_depth` mandatory only for new operation and equal to abstraction bounds (§9)
3. **Integer range weights above `2**53` losing exactness:** Fixed by preserving non-bool integer weights before Fraction conversion (§9, §3.2)

**I4 RED cases expansion:** PASS

I4 tests must cover:
- Integer weights above `2**53` with direct-Python/JSON parity
- Omitted/one-omitted/equal/unequal base and abstraction bounds
- Structured key/action serialization (not `str(key)` dictionaries)
- JSON finite safety
- Deep response isolation

## 4. Per-batch parent gates audit (§11)

**Gate checklist:** PASS

For every S4 implementation batch, parent must:

1. Prove final test bytes are genuine pre-production RED against exact prior production snapshot
2. Record literal test/source/report hashes
3. Run focused tests with no skipped/xfail placeholder coverage
4. Run relevant S1/API compatibility tests
5. Run `uv run python -m compileall -q src tests scripts`
6. Run `uv run pytest -q` with no exclusions
7. Run `git diff --check` before freezing
8. Freeze a candidate manifest from repository root
9. Dispatch exactly six fresh BryantGPT non-authors with exclusive reports/flat completed heartbeats
10. Parent-authenticate transcripts, report/heartbeat hashes, probes, candidate pre/post hashes, focused/full receipts, HEAD and tag
11. Repair every reproduced finding via new behavioral RED and repeat wholly fresh audit of changed bytes
12. Commit the accepted batch before starting the next

**Exact-six fresh audit requirement:** PASS

Each batch requires exactly six fresh BryantGPT non-author auditors with exclusive reports and flat completed heartbeats.

**Repair protocol:** PASS

Every reproduced finding requires:
- New behavioral RED
- Wholly fresh audit of changed bytes
- No acceptance until all findings resolved

## 5. S4 completion gate audit (§12)

**Completion criteria:** PASS

S4 is complete only when all of the following are parent-verified:

1. Exact-signature policy is explicit in typed config and strict JSON ✓
2. Small exact tree count is 321 and small quotient count is 161 ✓
3. Small lifted and exact-reference profiles satisfy preregistered NashConv and incentive bound on exact tree ✓
4. Blocker companions prove equal equity is not treated as identity ✓
5. Large exact count certificate is 348,481 while complete reduced solve uses exactly 161 physical nodes under cap 10,000 ✓
6. Exact same-game preflight fails under that cap before training ✓
7. Deterministic repeated vanilla solve and same-seed MCCFR tests pass ✓
8. Every certified twin lifts to exactly equal policy values with complete, immutable exact-key coverage ✓
9. No traversal hides an exact subtree behind a reduced wrapper ✓
10. Every metadata field distinguishes physical, infoset, latent-world, preprocessing, metric-scope, and finite-iteration semantics ✓
11. All pre-S4 tests plus additive S4 tests pass ✓
12. Every implementation batch has a fresh different exact-six non-author audit and accepted commit ✓
13. `phase3-398-green` remains unchanged ✓

**S5 gate:** PASS

Only after all above criteria are met may S5 design begin.

## 6. Release sufficiency audit

### 6.1 No unsupported overclaim

**Scope restrictions (§1):** PASS

Explicitly NOT S4 implementations:
- Replacing `information_state_key` while retaining every exact deal branch
- Counting unique infosets or regret entries as physical nodes
- Category/equity bins without proof that blockers, future public-card laws, payoffs, and observations agree
- Representative-hand sampling or unlabelled chance renormalization
- Proposal that defers physical reduction to a later version
- Universal `O(1/k)` exploitability claim, guessed percentage-of-pot error, or post-measured ratio threshold

**Supported v1 scope (§1):** PASS

Existing two-player zero-sum `MultiStreetConfig`, including exact translation of `AllStreetPostflopConfig` with natural terminal settlement.

Out of scope:
- S2/S3 multiplayer integration
- Unrestricted-deck scale
- Arbitrary generic `GameState` wrapping
- Warm starts
- General game-automorphism search

**Conservative failure policy (§1):** PASS

Abstraction may find no compression and then fail a declared cap. Conservative failure is preferable to silently merging blocker-distinct hands.

### 6.2 Mathematical certificates (§7)

**Exact-signature quotient properties:** PASS

- Terminal diameter zero ✓
- Identical observable kernels ✓
- Rational reduced value equals rational exact lifted value ✓
- Model-error term exactly zero ✓

**Rational certificate tests (§7):** PASS

Small-fixture tests:
- Rationalize returned policy probabilities with `Fraction.from_float`
- Normalize each policy exactly
- Replay exact chance/utility
- Independently compute rational best-response incentives over bounded 321-node tree
- Compare ordinary float metrics within `1e-10` chips (regression tolerance, not theorem)

### 6.3 Strict v4 API and serialization (§9)

**New operation:** PASS

Operation `solve-allstreet-abstracted` added to `dispatch_v4`.
Existing operations remain byte-for-schema compatible.

**Request schema:** PASS

Exactly `version`, `operation`, and `payload`.
`version` is integer `4`.
`operation` is literal `solve-allstreet-abstracted`.

Payload required fields:
- Existing allstreet fields
- `max_nodes` and `max_depth` (newly mandatory for this operation)
- `abstraction`

Payload optional field:
- `exact_evaluation` (null or exact object)

Unknown or missing fields fail.
`payload.max_nodes` must equal `abstraction.max_abstract_nodes`.
`payload.max_depth` must equal `abstraction.max_depth`.

**Abstraction config schema (§9):** PASS

Exactly:
```json
"abstraction": {
  "version": "exact-signature-belief-v1",
  "max_abstract_nodes": 10000,
  "max_depth": 32,
  "max_worlds": 5000,
  "max_signature_cells": 20000,
  "max_belief_entries": 20000,
  "max_fraction_bits": 4096
}
```

**Response schema (§9.1):** PASS

Exhaustive top-level keys (all required):
- `version`, `operation`, `game_version`, `abstraction_version`
- `algorithm`, `iterations`, `seed`, `values`
- `reduced_nashconv`, `reduced_exploitability`
- `exact_nashconv`, `exact_exploitability`
- `exact_evaluation_status`, `metric_scope`, `strategy_scope`
- `strategy`, `lifted_strategy`
- `abstraction_lossless`, `approximate`
- `metadata`, `provenance`

Nested records:
- `ActionRecord`, `RationalRecord`, `PublicFrameRecord`
- `AbstractKeyRecord`, `ExactKeyRecord`
- `PolicyItem`, `AbstractPolicyEntry`, `ExactPolicyEntry`
- `BucketRecord`, `BucketPairRecord`
- `AbstractionMetadata` (exhaustive 48 keys)

**Integer weight preservation (§9):** PASS

For new operation only:
- Non-bool JSON integer remains integer through validation
- Converted with `Fraction(value)`
- Finite JSON float remains float through validation
- Converted with `Fraction.from_float(value)`
- Preserves integers above `2**53` exactly
- Direct-Python and decoded-JSON requests have identical behavior
- Prior operations retain existing float-coercion behavior

**Provenance (§9.1):** PASS

Exact sentence: `finite-iteration float CFR over a certified exact-signature reduced configured multistreet game; exact rational aggregation; exact-tree diagnostics STATUS`

STATUS replaced by `not-requested` or `completed`.

### 6.4 Full regression preservation

**Baseline preservation (§1, §11):** PASS

Accepted base: commit `149780bf37e3e3a824e03e6d2c1df3cd99b12cd6`
Historical tag `phase3-398-green`: exactly `feba8222a0b614b0c64eca59402403ce733195ea`
Live pre-S4 regression: 817 tests
398 is preserved historical baseline, not current expected total

**Additive test requirement:** PASS

Every batch ends with prior suite green (new tests additive).

## 7. Findings

**VERDICT: PASS**

No findings. The S4 architecture design is:

1. **Fixture-complete:** Small comparable fixture, two blocker companions, and large bounded fixture are precisely specified with expected statistics and acceptance criteria.

2. **RED-first sound:** Four implementation batches (I1-I4) have clear RED-owned test files, required cases, GREEN scope boundaries, dependency-safe sequencing, and fresh audit scopes.

3. **Gate-enforced:** Per-batch parent gates require genuine RED proof, exact-six fresh non-author audits, repair protocol, and accepted commit before next batch.

4. **Release-sufficient:** S4 completion gate has 13 parent-verifiable criteria covering physical counts, quality bounds, blocker separation, twin identity, metadata semantics, full regression, and baseline preservation.

5. **Claim-bounded:** Explicit scope restrictions, conservative failure policy, and no unsupported overclaim (no lossy bins, no deferred reduction, no universal exploitability ratio).

6. **Certificate-backed:** Exact-signature quotient has zero terminal diameter, zero model error, rational value equality, and rational incentive theorem with regression tolerance.

7. **API-strict:** Exhaustive request/response schemas, mandatory bound equality, integer weight preservation, structured key/action serialization, and byte-for-schema compatibility with existing operations.

8. **R2-repaired:** Three R1 findings (incomplete schema, ambiguous bounds, integer weight loss) are addressed with exhaustive wire schema, mandatory-equal bounds for new operation only, and Fraction conversion preserving non-bool integers.

The architecture is ready for I1 RED implementation.

## 8. Report hash

SHA-256 of this report: (computed after write)

---

**R2A5 audit complete.**