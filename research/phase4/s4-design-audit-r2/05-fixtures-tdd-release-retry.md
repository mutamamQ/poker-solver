# R2A5R: S4 Fixtures, TDD Contract, and Release Sufficiency Audit

**Agent**: R2A5R (Bryant recovery after R2A5 ended)
**Status**: COMPLETE_PASS
**Timestamp UTC**: 2026-09-16T12:26:07Z
**Scope**: Design-only audit of preregistered fixtures, RED-first TDD contracts, and S4 release gates

## 1. Authentication

Verified literal document SHAs against task-supplied values:

- Architecture: `ARCHITECTURE_PHASE4_S4.md`
  - Expected: `37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2`
  - Actual: `37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2` ✓
- Manifest: `research/phase4/s4-design-audit-r2/CANDIDATE_MANIFEST.md`
  - Expected: `f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed`
  - Actual: `f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed` ✓
- Mission: `PHASE4_MISSION.md`
  - SHA: `5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61` ✓
- Design authority: `research/phase4/s4-design/02-engine-integration-codex.md`
  - Expected: `79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d`
  - Actual: `79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d` ✓

## 2. Implementation Status

**Critical context**: This is a DESIGN-ONLY audit. No S4 implementation exists:

- Source inventory: 36 files in `src/poker_solver/`, ZERO matching `abstraction*.py`
- Test inventory: 51+ files in `tests/`, ZERO matching `test_abstraction*.py`
- Architecture §10 specifies four RED-first implementation batches (I1-I4)
- Architecture §12 lists S4 completion gates requiring implementation
- Manifest §39 explicitly states: "R2 is still DESIGN only; missing S4 implementation/tests is expected and is not a finding."

Per task context: "Missing future code/tests is expected."

## 3. Preregistered Fixtures (Architecture §8)

### 3.1 Small Comparable Fixture (§8.1)

**Specification**:
- Flop: `Ah Kh Qh`
- Ordered runouts: `(Jh,9h)`, `(Jh,8h)`
- Dead pot: 2, stack: 1
- No-limit target `(1,)`, river betting enabled
- P0 hands: `2c3c`, `2d3d` (weights 1.0)
- P1 hands: `2s3s`, `Th4s` (weights 1.0)

**Expected exact stats**: 321 nodes, 136 terminals, 57 chance, 128 decisions, depth 12
**Expected abstract stats**: 161 nodes (P0: 1 bucket, P1: 2 buckets)
**Quality gate**: Both exact-tree NashConv ≤0.02 chips at 1,000 vanilla iterations

**Parent reference receipt** (§8.1, line 273-274):
- Values: `(-0.9993335546875001, 0.9993335546875001)`
- Best responses: `(-0.9993333333333333, 1.0000625)`
- Incentives: `(2.2135416677393494e-07, 0.0007289453125000067)`
- NashConv: `0.0007291666666667806`

**Assessment**: ✓ PASS
- Fixture is completely specified with exact card IDs, weights, runouts
- Expected counts are deterministic and derived
- Quality gate is concrete (≤0.02 chips, not a ratio)
- Parent receipt demonstrates feasibility

### 3.2 Blocker Companions (§8.1, lines 276-279)

**Opponent-blocker fixture**:
- Equal-showdown hands, three compatible deals
- Both players' signatures must stay separate
- Tests that equity equality ≠ strategic identity

**Runout-blocker fixture**:
- One P0 hand blocks a declared runout
- Signatures stay separate
- No positive deal conditioned away

**Assessment**: ✓ PASS
- Companions are specified to prevent equity-only grouping
- Architecture §3.2 (lines 66-68) explicitly rejects equal-equity merging
- Design §3 (lines 46-52 of 02-engine-integration-codex.md) reinforces blocker-aware signatures

### 3.3 Large Bounded Fixture (§8.2)

**Specification**:
- Same public game as small fixture
- P0 range: all C(12,2)=66 unordered pairs from `{2c,3c,4c,5c,6c,7c,2d,3d,4d,5d,6d,7d}`
- P1 range: all C(12,2)=66 unordered pairs from `{2s,3s,4s,5s,6s,7s,2h,3h,4h,5h,6h,Th}`
- All 4,356 ordered pairs compatible
- P0: 1 bucket (66 hands)
- P1: 2 buckets (55 no-Th, 11 with-Th)

**Expected counts**:
- Exact physical nodes: `1 + 4,356 × 80 = 348,481`
- Reduced physical nodes: `1 + 2 × 80 = 161`
- Charged signature slots: 17,424
- Belief member entries: 17,424

**Acceptance requirements** (§8.2, lines 299-301):
- Complete reduced path under 10,000 nodes and depth 32
- Same exact config with 10,000 nodes must fail before training
- Result reports exact count as analytic certificate

**Assessment**: ✓ PASS
- Fixture is completely specified with explicit 12-card sets
- Counts are deterministic (verified by read-only probe in design §9, lines 299-337)
- Demonstrates 2,164× physical node reduction (348,481 → 161)
- Acceptance criteria are concrete and testable

## 4. RED-First TDD Contract (Architecture §10)

### 4.1 Batch Structure

Architecture §10 specifies four implementation batches with strict RED-first discipline:

**S4-I1** (§10, lines 463-472): Policy, config, canonical signatures
- RED-owned: `tests/test_abstraction_signatures.py`
- Required cases: config/immutability, Fraction conversion, blocker counterexamples, small/large membership
- GREEN scope: `src/poker_solver/abstraction.py` up through `build_buckets` only
- Audit scope: schema/immutability, signature proof, blocker counterexamples, Fraction/caps, determinism, regression

**S4-I2** (§10, lines 474-485): Worlds, beliefs, public compiler, ReducedState
- RED-owned: `tests/test_abstraction_reduced_game.py`
- Required cases: root mass, posterior arithmetic, physical bounds (160 fail/161 pass), settlement/conservation, recall/noninterference
- GREEN scope: Complete `abstraction.py` compilation and `ReducedState`
- Audit scope: probability/posteriors, source transition differential, physical counts/caps, recall/noninterference, regression

**S4-I3** (§10, lines 487-497): Solver, lift, exact diagnostics, certificates
- RED-owned: `tests/test_abstraction_solve.py` + rational certificate helpers
- Required cases: vanilla/MCCFR contracts, rational simulation equality, lift coverage, rational incentive theorem, small quality gates, large complete solve
- GREEN scope: `src/poker_solver/abstraction_solve.py` and lift additions
- Audit scope: CFR/metric scope, lift/corruption, rational certificates, exact diagnostics, large solve, regression

**S4-I4** (§10, lines 499-511): API, exports, examples, S4 docs
- RED-owned: `tests/test_api_v4_abstraction.py`, `tests/test_phase4_s4_examples.py`, `tests/test_phase4_s4_exports.py`
- Required cases: exhaustive schema validation, diagnostic-status cases, structured serialization, integer weights >2^53, CLI paths
- GREEN scope: Additive edits to `api_v4.py`, `__init__.py`, examples, docs
- Audit scope: strict parser, serialization/isolation, exports/compatibility, examples/CLI, docs truth, regression

**Assessment**: ✓ PASS
- Each batch has explicit RED-owned test files
- Test requirements are concrete and behavioral
- GREEN scope is bounded to prevent premature implementation
- Architecture §10 line 460: "No production bytes may precede each batch's behavioral RED"
- Architecture §10 line 461: "Every permanent test imports and invokes production, contains no placeholder/pass/caught-import trick"

### 4.2 Dependency Sequence

Batches form a genuine dependency sequence:
- I1 (signatures) → I2 (compiler) → I3 (solver) → I4 (API)
- Each batch's GREEN is prerequisite for next batch's RED
- No circular dependencies or parallel implementation

**Assessment**: ✓ PASS

### 4.3 Per-Batch Gates (Architecture §11)

Architecture §11 specifies 12 gates per batch:
1. Prove final test bytes are genuine pre-production RED
2. Record literal test/source/report hashes
3. Run focused tests (no skipped/xfail)
4. Run relevant S1/API compatibility tests
5. Run `uv run python -m compileall -q src tests scripts`
6. Run `uv run pytest -q` (no exclusions)
7. Run `git diff --check`
8. Freeze candidate manifest from repository root
9. Dispatch exactly six fresh BryantGPT non-authors
10. Parent-authenticate transcripts, hashes, receipts, HEAD, tag
11. Repair every finding via new RED and repeat audit
12. Commit accepted batch before next

**Assessment**: ✓ PASS
- Gates are concrete and enforceable
- Exact-six non-author audit requirement is explicit
- Repair loop prevents accumulation of findings
- Mission §48 reinforces adversarial cross-check after every batch

## 5. I4 Schema and Weight Cases (Architecture §9, Design §10-11)

### 5.1 Exhaustive Response Schema (Architecture §9.1)

Architecture §9.1 (lines 336-448) specifies exhaustive wire schema:
- Top-level: 20 required keys, no optional keys
- Nested records: `ActionRecord`, `RationalRecord`, `PublicFrameRecord`, `AbstractKeyRecord`, `ExactKeyRecord`, `PolicyItem`, `AbstractPolicyEntry`, `ExactPolicyEntry`, `BucketRecord`, `BucketPairRecord`
- `AbstractionMetadata`: 48 exact keys with specified types
- Deterministic sorting: abstract keys by canonical encoding, exact keys by canonical encoding, buckets by `(player, bucket_id)`, pairs by `(player0_bucket, player1_bucket)`

**Assessment**: ✓ PASS
- Schema is complete and unambiguous
- Every field has explicit type and nullability
- Unknown/missing fields must fail (§9, line 330)
- I4 RED must cover "exhaustive top-level and nested schemas" (§10, line 507)

### 5.2 Integer Weight Preservation (Architecture §9, lines 332-333)

For `solve-allstreet-abstracted` operation only:
- Non-bool JSON integer → `Fraction(value)` (preserves integers >2^53)
- Finite JSON float → `Fraction.from_float(value)` (preserves binary float exactly)
- Direct-Python and decoded-JSON requests have identical behavior
- Prior operations retain existing float-coercion

**Assessment**: ✓ PASS
- Requirement is explicit and local to new operation
- Design §3 (lines 38-39) reinforces `Fraction.from_float` for floats, `Fraction(value)` for integers
- I4 RED must cover "integer weights above 2^53 with direct-Python/JSON parity" (§10, line 507)

### 5.3 Bound Equality (Architecture §9, lines 311-315)

For `solve-allstreet-abstracted` operation:
- `payload.max_nodes` and `payload.max_depth` are newly mandatory
- Must equal `abstraction.max_abstract_nodes` and `abstraction.max_depth`
- Omission of either base bound fails before equality checking
- Existing operations retain optional-bound behavior

**Assessment**: ✓ PASS
- Requirement prevents ambiguous dual limits
- Design §10 (line 390) reinforces: "ambiguous dual bounds fail instead of silently overriding"
- I4 RED must cover "omitted/one-omitted/equal/unequal base and abstraction bounds" (§10, line 507)

## 6. S4 Release Sufficiency (Architecture §12)

Architecture §12 lists 14 completion gates. Key gates:

1. **Exact-signature policy explicit** in typed config and strict JSON ✓
2. **Small exact tree count 321, quotient 161** ✓ (specified §8.1)
3. **Small lifted and exact-reference profiles** satisfy preregistered NashConv ≤0.02 and incentive bound ✓ (§8.1)
4. **Blocker companions** prove equal equity ≠ identity ✓ (§8.1)
5. **Large exact count certificate 348,481**, reduced solve uses exactly 161 under cap 10,000 ✓ (§8.2)
6. **Exact same-game preflight fails** under cap before training ✓ (§8.2, line 301)
7. **Deterministic repeated vanilla solve and same-seed MCCFR** tests pass ✓ (I3 requirement)
8. **Certified twin lifts** to exactly equal policy values with complete coverage ✓ (I3 requirement)
9. **No traversal hides exact subtree** behind reduced wrapper ✓ (I2/I3 instrumentation requirement)
10. **Metadata distinguishes** physical/infoset/latent-world/preprocessing/metric-scope/finite-iteration ✓ (§9.1)
11. **All pre-S4 tests plus additive S4 tests pass** ✓ (§11 gate 6)
12. **Every batch has fresh exact-six non-author audit** ✓ (§11 gate 9)
13. **`phase3-398-green` remains unchanged** ✓ (§1, line 20; manifest §7)

**Assessment**: ✓ PASS
- Gates are concrete and testable
- No "ratio<50" or guessed bounds
- No lossy abstraction or universal compression claim
- Bounded claims: "satisfies S4 on two preregistered finite all-street fixtures" (§1, line 7)

## 7. Findings

**Zero blocking findings**. The design specification is:
- Complete for the declared scope (exact-signature belief v1, heads-up multistreet)
- Internally consistent (fixtures, TDD contracts, release gates align)
- Testable (concrete counts, quality gates, behavioral requirements)
- Bounded (explicit limitations in §1, design §12)

**Non-blocking observations**:
1. Implementation does not exist (expected per manifest §39)
2. Future I1-I4 auditors must verify actual test/source bytes against these specifications
3. Rational certificate helpers (I3) are test-only and not production exports

## 8. Conclusion

**Status**: COMPLETE_PASS

**Scope**: Design-only audit of:
- Preregistered fixtures (small, blocker companions, large)
- RED-first TDD contracts (I1-I4 batch structure, test requirements, dependency sequence)
- S4 release sufficiency (completion gates, bounded claims)

**Evidence**:
- All referenced documents authenticate to supplied SHAs
- Fixtures are completely specified with deterministic expected counts
- TDD contracts are genuine RED-first with concrete behavioral requirements
- Release gates are testable and bounded
- No implementation blocking issues in design specification

**Blocked**: No

**Next**: Implementation batches I1-I4 per Architecture §10-11, each with fresh exact-six non-author audit per Architecture §11 gate 9 and Mission §48.
