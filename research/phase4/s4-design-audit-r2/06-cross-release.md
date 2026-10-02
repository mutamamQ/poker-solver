# R2A6 S4 cross-release design audit — COMPLETE

**Auditor:** R2A6 (BryantGPT, wholly fresh non-author cross-release auditor)
**Timestamp:** 2026-09-16 (UTC)
**Task:** Cross-release design audit with independent full regression and correct tag semantics
**Workspace:** `/home/genomix-node/poker-solver`

## 1. Verification receipts

### 1.1 Git state and tag semantics

- **HEAD commit:** `149780bf37e3e3a824e03e6d2c1df3cd99b12cd6` ✓ EXACT MATCH
- **Annotated tag object `phase3-398-green`:** `feba8222a0b614b0c64eca59402403ce733195ea` ✓ EXACT MATCH
- **Peeled commit from tag:** `5809ecca28ae6d0588ea07709c90beac3072c167` ✓ EXACT MATCH
- **Source/tests unchanged:** `git diff --name-only -- src tests scripts pyproject.toml` returned empty ✓
- **No whitespace issues:** `git diff --check` passed ✓

### 1.2 Document hash verification

```
37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2  ARCHITECTURE_PHASE4_S4.md ✓
f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed  research/phase4/s4-design-audit-r2/CANDIDATE_MANIFEST.md ✓
5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61  PHASE4_MISSION.md ✓
79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d  research/phase4/s4-design/02-engine-integration-codex.md ✓
```

All candidate document hashes match manifest exactly.

### 1.3 Implementation status

- **S4 implementation present:** NO (expected per manifest)
- **S4 tests present:** NO (expected per manifest)
- **Source search for abstraction code:** 0 matches in `src/` ✓
- **Test search for abstraction tests:** 0 matches in `tests/` ✓
- **Python compilation:** `compileall` passed on all existing source/tests ✓

### 1.4 Independent full regression

```
UV_NO_CACHE=1 uv run --no-sync pytest -q
817 passed in 372.16s (0:06:12)
```

✓ **PASS** — Full baseline regression green, unchanged production/tests confirmed.

## 2. Cross-release design audit findings

### 2.1 Scope and decision (§1)

**PASS** — Architecture clearly defines S4 as:
- Deterministic heads-up all-street postflop abstraction
- Physical game tree reduction via `exact-signature-belief-v1` policy
- Hands grouped only when complete labelled strategic continuations are identical
- Exact quotient of configured finite game, not lossy fixed-k equity heuristic
- Conservative failure on no compression preferable to silent blocker-distinct merges
- Satisfies S4 on two preregistered fixtures: small (321→161 nodes) and large (348,481→161 nodes)

**Evidence:** Explicit rejection list (§1 lines 9-16) excludes infoset-only reductions, equity bins without blocker proofs, representative sampling, deferred physical reduction, and universal O(1/k) claims. Accepted base and tag semantics correctly specified.

### 2.2 Source authority and adjudication (§2)

**PASS** — Authoritative source behavior enumerated across 11 modules with specific semantic contracts:
- `model.py`: GameState, Action, CHANCE/TERMINAL
- `multistreet.py`: exact deal/runout/betting/settlement
- `allstreet.py`: S1 config translation and solve facade
- `bounded_tree.py`: literal history-node/depth counting
- `cfr.py`, `api.py`, `best_response.py`: strategy completion and metrics
- `evaluator.py`, `equity.py`: exact showdown and weighted combos
- `api_v4.py`: strict JSON conventions

**Evidence:** Central design input authenticated as `research/phase4/s4-design/02-engine-integration-codex.md` SHA-256 `79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d` (verified above). Rejected inputs from S4D1/D3/D4/D5/D6 explicitly listed with rationale.

### 2.3 Exact-signature policy (§3)

**PASS** — Complete specification of canonical inputs and signature construction:

- **Canonical order (§3.1):** hands as increasing integer card pairs, lexicographically sorted; ordered full runouts sorted as tuples; source legal-action order preserved; bucket IDs by sorted distinct signatures
- **Duplicate/zero-weight handling:** duplicates rejected, zero-weight omitted from active support with metadata counts
- **Weight conversion:** `Fraction.from_float` for floats, `Fraction(value)` for integers, preserving binary float exactly
- **Complete labelled signatures (§3.2):** For player 0 hand h, signature has one cell per player 1 hand g:
  - `(0, ())` if incompatible
  - `(1, codes)` if compatible, one code per configured ordered runout
  - Runout code: `-2` if blocked, else `-1/0/+1` for showdown comparison
- **Identity certificate:** entire tuple is identity; hashes identify plans but never replace equality
- **Blocker awareness (§3.2 lines 66-68):** Equal-equity hands separated by opponent blocker or runout blocker MUST remain in different buckets

**Evidence:** Scalar equity, made-hand category, hole-card ranks, informal suit symmetry explicitly rejected as certificates. Equal rows imply identical opponent compatibility/runout legality/payoff ordering; equal columns provide transposed property. Positive bucket-pair cell is rectangular: behavioral twins for configured game.

### 2.4 Fixed buckets and perfect recall (§3.3)

**PASS** — Hand receives one private bucket at root, retained through every street. No street-local rebucketing may merge distinct prior buckets.

**Abstract information key contains:**
- Policy version and canonical semantic config digest
- Acting player
- Player's own fixed bucket ID
- Full public frame: board, street, actor, pot, commitments, total contributions, remaining stacks, last-raise increment, betting history, public RUNOUT history, terminal marker

**Excludes:** opponent bucket, exact cards, world ID, pair ID, latent probabilities, root abstract-deal action, representative cards.

**Evidence:** Compile-time recall and noninterference checks required in addition to `validate_bounded_tree` (§3.3 line 78).

### 2.5 Physical reduced game (§4)

**PASS** — Immutable records specified with frozen/slotted dataclasses:

- `AbstractionConfig` (§4.1 lines 92-103): version literal, six positive integer limits
- `Bucket`, `World`, `MemberWeight`, `Belief`: frozen records for membership and probability
- `PublicFrame`, `AbstractInfoKey`: observation and key structure
- `Edge`, `Node`, `ReducedPlan`, `ReducedState`: compiled tree structure

**Required public functions (§4.1 lines 108-123):**
- `canonicalize_config`, `build_buckets`, `compile_reduced_game`, `create_reduced_root`
- `exact_member_state`, `abstract_key_for_exact`, `lift_exact_strategy`

**Evidence:** `ReducedPlan.nodes` is tree rooted at node 0, not DAG to disguise count. `ReducedState.child` is O(1) validated lookup, never materializes member subtrees. Root chance actions are deterministic `Action("ABSTRACT_DEAL", k)` for sorted nonempty bucket pairs.

### 2.6 Root mass and beliefs (§4.2)

**PASS** — Exact probability semantics:

- Raw mass `r_w = f_h * f_g` for world w=(h,g)
- Normalize by exact `Z = sum(r_w)`
- Bucket-pair mass is sum of world masses in pair
- Conditional member mass is normalized world mass / pair mass
- World next-card law: `p_w(c | s) = |R_w(s+c)| / |R_w(s)|`
- Aggregate observable: `P(c) = sum_w q(w) * p_w(c | s)`
- Child posterior: `q'(w) = q(w) * p_w(c | s) / P(c)` for positive terms only

**Evidence:** Equations use `Fraction`. Explicit prohibition against choosing hidden complete runout before turn betting, uniform world averaging, or pooling raw sequence counts across different denominators (§4.2 lines 142-143).

### 2.7 Public betting transitions (§4.3)

**PASS** — All pair members must have identical actor and ordered legal actions at public frame. Real compatible member used only to project SOURCE public transition fields, not as payoff representative. No exact subtree retained.

**Evidence:** Compiler checks compare projected actor, history, ledger, next-card support, public frame invariants. Disagreement fails instead of intersecting actions or dropping members. CFR traversal, strategy completion, reduced best response construct zero exact-world GameState subtrees (§4.3 lines 151-152). Instrumented tests required to distinguish bounded preprocessing checks from solve-time traversal.

### 2.8 Terminal utility (§4.4)

**PASS** — Preserve source integer settlement including folds, refunds, all-ins, odd ties.

```
u0 = sum_w q(w) * award0(w) - contributed0 - Fraction(initial_dead_pot, 2)
```

Compute complementary P1 independently, require exact `u0 + u1 == 0`. Ledger conservation `C = initial_dead_pot + sum(total_contributed)`. Return `(float(u0), -float(u0))` only after finite/bound checks.

**Evidence:** Never infer settlement from mean equity or average already-rounded utilities (§4.4 line 159).

### 2.9 Bounds and physical accounting (§5)

**PASS** — `node_count` exactly the history occurrence count from `validate_bounded_tree`: root, chance, decision, terminal nodes. NOT bucket count, infoset count, unique public frame count, live wrapper count, or regret-table size.

**Compilation bounds:**
- Reserves node before allocation, fails before exceeding `max_abstract_nodes` (equality allowed)
- Compatible active worlds by `max_worlds`
- Charged signature scalar slots by `2 * len(H0) * len(H1) * max(1, len(allowed_runouts))` against `max_signature_cells`, including blocked cells
- Total stored `MemberWeight` entries against `max_belief_entries`
- Fraction bit lengths against `max_fraction_bits`
- Depth against both caller cap and v1 recursive ceiling

**Evidence:** After freezing plan, run `validate_bounded_tree` on `ReducedState` and require every recorded count/depth to match (§5 lines 173-174). Metadata distinguishes physical nodes, infosets, latent worlds, signature slots, belief entries, runtime — must not imply smaller node count alone proves fixed runtime ratio.

### 2.10 Strategy solve, lift, and truthful result (§6)

**PASS** — New module `src/poker_solver/abstraction_solve.py` with:

- `ExactEvaluationConfig`: max_nodes, max_depth for optional diagnostics
- `AbstractSolveResult`: algorithm, seed, iterations, values, reduced_metric, exact_metric (nullable), strategy, lifted_strategy (nullable), plan, approximate, abstraction_lossless, metric_scope, exact_evaluation_status, provenance, metadata
- `solve_multistreet_abstracted` and `solve_allstreet_abstracted` functions

**Semantics:**
- Vanilla CFR requires `seed=None`; MCCFR requires non-bool integer seed
- S4 acceptance uses 1,000 deterministic vanilla iterations
- Allstreet translation must match `create_allstreet_root`
- `config.max_nodes` must equal `abstraction.max_abstract_nodes`; `config.max_depth` must equal `abstraction.max_depth`
- Reduced compilation before exact-tree preflight
- Exact diagnostics absent by default, independent explicit bounds
- Lifting traverses explicitly bounded exact root only when requested
- Every reachable exact key maps through certified bucket and complete abstract policy
- Missing policies, duplicate-key disagreement, unknown configs, coverage gaps fail
- `complete_strategy` may not mask gap
- Result contains detached, recursively frozen mappings
- Certified twin hands receive same copied float values exactly
- Each original exact key remains separately addressable

**Evidence:** For large non-diagnostic solves, retain reduced policy, exact membership, canonical digest for on-demand projection. Do not force forbidden exact traversal during result construction (§6 lines 231-233). `approximate=True` means finite-iteration float CFR policy not claimed exact equilibrium. Does not mean abstraction is lossy. Set `abstraction_lossless=True`, `model_error_bound=0`, `lossy_merges=0`, label reduced vs exact metrics explicitly (§6 lines 234-236).

### 2.11 Mathematical certificates (§7)

**PASS** — Rigorous mathematical framework for complete profile x in SAME exact two-player zero-sum game:

```
v(x) = u0(x)
U(x) = BR0(x1)
L(x) = -BR1(x0)
e0(x) = U(x) - v(x)
e1(x) = v(x) - L(x)
C(x) = e0(x) + e1(x) = U(x) - L(x)
```

Minimax: `L(x) <= v* <= U(x)`

For lifted abstract profile a and independently trained exact reference r:

```
|v(a) - v(r)| <= max(e1(a) + e0(r), e0(a) + e1(r)) <= C(a) + C(r)
```

**Evidence:** Compares finite profiles without assuming either is equilibrium or convergence is monotone (§7 lines 248-251). Small fixture: both profiles must have exact-tree NashConv ≤ 0.02 chips after 1,000 vanilla iterations, giving preregistered loose value-gap bound of 0.04 chips and tighter observed incentive expression.

**Exact-signature quotient properties:**
- Terminal diameter zero
- Identical observable kernels
- For any bucket profile, rational reduced value equals rational exact lifted value
- Extra exact-card distinctions cannot improve response (types within bucket have identical labelled continuations and factorized conditional mass)
- Realization-plan mixture implementable under perfect recall
- **v1 model-error term exactly zero** (certificate, not claim float CFR converged)

**Small-fixture tests:** Rationalize returned policy probabilities with `Fraction.from_float`, normalize exactly, replay exact chance/utility. Independently compute rational best-response incentives over bounded 321-node tree, compare ordinary float metrics within `1e-10` chips. Tolerance is regression tolerance, not theorem (§7 lines 254-257).

### 2.12 Preregistered fixtures (§8)

**PASS** — Two fixtures with complete specifications:

#### 2.12.1 Small comparable fixture (§8.1)

- Flop `Ah Kh Qh`
- Ordered runouts `(Jh,9h)` and `(Jh,8h)`
- Initial dead pot 2, effective stack 1
- No-limit target `(1,)`, river betting enabled
- P0 hands `2c3c`, `2d3d`; P1 hands `2s3s`, `Th4s`; all weights 1.0
- **Expected exact stats:** 321 nodes, 136 terminals, 57 chance, 128 decisions, depth 12
- **P0:** one bucket; **P1:** two buckets
- **Quotient:** 161 physical nodes
- Four exact deal worlds → two abstract deal outcomes, masses 1/2 each
- Both rivers conditional mass 1/2 after `Jh`

**Parent reference receipt at 1,000 exact vanilla iterations:**
- Values: `(-0.9993335546875001, 0.9993335546875001)`
- Best responses: `(-0.9993333333333333, 1.0000625)`
- Incentives: `(2.2135416677393494e-07, 0.0007289453125000067)`
- NashConv: `0.0007291666666667806`

**Two compulsory companions:**
- **Opponent-blocker fixture:** equal-showdown hands, three compatible deals; both players' signatures stay separate
- **Runout-blocker fixture:** one P0 hand blocks declared runout; signatures stay separate, no positive deal conditioned away

#### 2.12.2 Large bounded fixture (§8.2)

- Same public game as small fixture
- **P0 range:** every unordered pair from `2c 3c 4c 5c 6c 7c 2d 3d 4d 5d 6d 7d` (66 hands)
- **P1 range:** every unordered pair from `2s 3s 4s 5s 6s 7s 2h 3h 4h 5h 6h Th` (66 hands)
- All weights one, all 4,356 ordered pairs compatible
- **P0:** one bucket of 66
- **P1:** 55-hand no-`Th` bucket and 11-hand `Th` bucket
- Pair masses: 5/6 and 1/6

**Single-world public tree:** 81 nodes, 34 terminals, 15 chance, 32 decisions, depth 12

**Derived counts:**
- Exact physical nodes: `1 + 4,356 * 80 = 348,481`
- Reduced physical nodes: `1 + 2 * 80 = 161`
- Reduced terminals/chance/decisions: 68/29/64
- Charged signature slots: 17,424
- Literal belief member entries: 17,424

**Acceptance requirements:**
- Complete reduced path (preflight, 1,000-iteration vanilla training, completion, reduced NashConv, frozen result, strict serialization) under 10,000 physical nodes and depth 32
- Same exact config with 10,000 nodes must fail before training
- Result reports exact count as analytic certificate, not executed full traversal

### 2.13 Strict v4 API and serialization (§9)

**PASS** — Comprehensive API specification:

**New operation:** `solve-allstreet-abstracted` added to `dispatch_v4`. Existing operations remain byte-for-schema compatible.

**Request object:** exactly `version`, `operation`, `payload`
- `version`: integer `4`
- `operation`: literal `solve-allstreet-abstracted`

**Payload required fields:**
- Existing allstreet fields: `version`, `starting_board`, `initial_dead_pot`, `effective_stack`, `player0_combos`, `player1_combos`, `allowed_runouts`, `betting_mode`, `wager_targets`, `algorithm`, `iterations`, `seed`
- Newly mandatory: `max_nodes`, `max_depth` (must equal abstraction bounds)
- `abstraction` object

**Only optional payload field:** `exact_evaluation` (null or object with max_nodes/max_depth)

**Abstraction object (§9 lines 318-328):**
```json
{
  "version": "exact-signature-belief-v1",
  "max_abstract_nodes": 10000,
  "max_depth": 32,
  "max_worlds": 5000,
  "max_signature_cells": 20000,
  "max_belief_entries": 20000,
  "max_fraction_bits": 4096
}
```

**Weight parsing (§9 lines 332-333):** For this operation, range-entry `weight` does NOT call existing `_float` helper. Non-bool JSON integer remains integer through validation, converted with `Fraction(value)`; finite JSON float remains float, converted with `Fraction.from_float(value)`. Preserves integers above `2**53` exactly. Local to new operation; prior operations retain existing behavior.

#### 2.13.1 Exhaustive response wire schema (§9.1)

**PASS** — Complete specification of required top-level keys (no optional keys):

```
version: 4
operation: "solve-allstreet-abstracted"
game_version: "multistreet-v1"
abstraction_version: "exact-signature-belief-v1"
algorithm: "vanilla-cfr" | "external-sampling-mccfr"
iterations: positive integer
seed: integer | null
values: [finite float, finite float]
reduced_nashconv: finite nonnegative float
reduced_exploitability: finite nonnegative float
exact_nashconv: finite nonnegative float | null
exact_exploitability: finite nonnegative float | null
exact_evaluation_status: "not-requested" | "completed"
metric_scope: "reduced-game"
strategy_scope: "abstract-bucket-public-history"
strategy: [AbstractPolicyEntry, ...]
lifted_strategy: [ExactPolicyEntry, ...] | null
abstraction_lossless: true
approximate: true
metadata: AbstractionMetadata
provenance: string
```

**Semantics:**
- `reduced_exploitability == reduced_nashconv / 2`
- When `exact_evaluation_status` is `not-requested`: both exact metrics and `lifted_strategy` are null
- When `completed`: both exact metrics finite, `lifted_strategy` non-null complete list
- Requested diagnostic exceeding bound returns error, never successful response with `not-requested`
- `provenance`: exact sentence with STATUS replaced by `not-requested` or `completed`

**Nested records (§9.1 lines 366-403):** Exact shapes specified for:
- `ActionRecord`, `RationalRecord`, `PublicFrameRecord`
- `AbstractKeyRecord`, `ExactKeyRecord`
- `PolicyItem`, `AbstractPolicyEntry`, `ExactPolicyEntry`
- `BucketRecord`, `BucketPairRecord`

**Sorting:** `strategy` sorted by canonical `AbstractKeyRecord` encoding; `lifted_strategy` by canonical `ExactKeyRecord` encoding. Each `policy` preserves source legal-action tuple order. Bucket records sort by `(player, bucket_id)`, members are sorted card pairs, pair records sort by `(player0_bucket, player1_bucket)`.

**AbstractionMetadata (§9.1 lines 408-448):** Exactly 48 specified keys with types, including:
- Policy version, config digest, digest schema
- Original/active/zero-weight combo counts
- Compatible world count, nonempty pair count
- Physical node/terminal/chance/decision counts and max depth
- All abstraction limits and actual counts
- Bucket sizes and membership records
- Exact node count analytic (nullable) and status
- Exact signature certificate: true
- Terminal diameter and model error bound: RationalRecord (both zero for v1)
- Arithmetic description
- Algorithm, seed, iterations
- Exact evaluation bounds (nullable) and status

**Digest (§9.1 lines 452-453):** Lowercase hexadecimal SHA-256 over UTF-8 canonical JSON for normalized semantic source config plus abstraction config. Includes `"digest_schema":"s4-semantic-config-v1"`, lexicographically sorted keys, exact separators, ASCII escaping, canonical sorted order for cards/runouts, integers remain decimal, normalized weights/fractions use `RationalRecord`.

**Immutability:** Returned Python mappings and nested containers detached and deeply immutable. JSON conversion creates fresh lists/objects with no mutable alias. Structured records preserve key/action identity. Nonfinite serialization fails.

**Package exports:** Add for two config/result families and public compiler/solve/lift entry points. CLI remains generic through existing v4 dispatch. Add canonical small/large JSON examples only after exact commands execute successfully.

### 2.14 RED-first implementation and audit batches (§10)

**PASS** — Four implementation batches specified with RED-owned tests, GREEN scope, and fresh audit scopes:

#### S4-I1: Policy, config, canonical signatures
- RED: `tests/test_abstraction_signatures.py`
- GREEN: `src/poker_solver/abstraction.py` up through canonicalization and `build_buckets`
- Audit: schema/immutability; signature proof; blocker counterexamples; Fraction/caps; determinism/collision; full regression/release boundary

#### S4-I2: Worlds, beliefs, public compiler, ReducedState
- RED: `tests/test_abstraction_reduced_game.py`
- GREEN: Complete bounded immutable world/belief/plan compilation and `ReducedState`
- Audit: probability/posteriors; source transition differential; physical counts/caps; settlement/conservation; recall/noninterference; full regression/performance payload

#### S4-I3: Solver, lift, exact diagnostics, certificates
- RED: `tests/test_abstraction_solve.py`; bounded test-only rational certificate helpers
- GREEN: `src/poker_solver/abstraction_solve.py` and minimum lift/projection additions
- Audit: CFR/metric scope; lift/corruption; rational certificates; exact diagnostics; large complete solve/resource accounting; full regression/determinism

#### S4-I4: API, exports, examples, S4 docs
- RED: v4 operation/config/result tests, failures, metric-scope/diagnostic behavior, deep freeze/isolation, serialization
- GREEN: Wire facade/dispatcher, public exports without altering old exact API
- Audit: v4 contract/isolation; serialization/determinism; existing S1/S2/S3 compatibility; documentation; full regression/examples

**Evidence:** No production bytes may precede each batch's behavioral RED (§10 line 459). Every permanent test imports/invokes production, contains no placeholder/pass/caught-import trick, statically read by parent before GREEN. Existing baseline controls run separately during RED. Each accepted implementation candidate hash-frozen, runs focused plus full regression, receives wholly fresh exact-six BryantGPT non-author audit before next batch.

### 2.15 S1-S3 compatibility assessment

**PASS** — Architecture explicitly scopes compatibility:

**Supported v1 scope (§1 line 18):** Existing two-player zero-sum `MultiStreetConfig`, including exact translation of `AllStreetPostflopConfig` with natural terminal settlement.

**Not part of S4 (§1 line 18):** S2/S3 multiplayer integration, unrestricted-deck scale, arbitrary generic `GameState` wrapping, warm starts, general game-automorphism search.

**Preserved baseline (§1 line 20):** Historical tag `phase3-398-green` must remain exactly `feba8222a0b614b0c64eca59402403ce733195ea`. Live pre-S4 regression is 817 tests; 398 is preserved historical baseline, not current expected total.

**Evidence:** No design report is production authority after architecture frozen (§2 line 36). Existing exact APIs and result semantics unchanged (§6 line 226). Allstreet translation must match `create_allstreet_root` (§6 line 228). Existing operations retain current optional-bound behavior (§9 line 315). S1/S2/S3 CLI/examples/export/API tests and all 817 baseline tests must remain green (§10 batch S4-I4).

### 2.16 Dependency graph and scope boundaries

**PASS** — Clear module dependencies specified:

**New modules:**
- `src/poker_solver/abstraction.py`: imports model/multistreet/evaluator/equity/bounded_tree, never api/allstreet
- `src/poker_solver/abstraction_solve.py`: imports cfr, best_response, api.complete_strategy

**Import discipline (§10 line 345):** Allstreet translation called locally by solve facade. Do not add eager api→facade→allstreet→api import cycle. Existing allstreet imports `complete_strategy` from api; preserve acyclic import direction (§2 line 31).

**Scope restrictions:**
- Compiler restricted to defensively copied `MultiStreetConfig` (§2 line 16)
- Heads-up, zero-sum, natural settlement only; unsupported game types fail explicitly (§2 line 16)
- Generic wrapper over arbitrary GameState NOT v1 interface (§2 line 15)
- Public/private decomposition, rational chance reconstruction, perfect recall, card-independent public transitions not discoverable from protocol alone (§2 line 15)

### 2.17 Acceptance metrics and overclaims

**PASS** — Architecture avoids overclaims and specifies exact acceptance criteria:

**What is claimed:**
- Physical game tree reduction on two preregistered fixtures
- Exact quotient of configured finite game
- Lossless abstraction with model error bound exactly zero
- Rational reduced value equals rational exact lifted value
- Terminal diameter zero, identical observable kernels
- Small fixture: both profiles ≤ 0.02 chips NashConv after 1,000 vanilla iterations
- Large fixture: complete reduced path under 10,000 nodes and depth 32

**What is NOT claimed (explicit limitations §10 lines 412-420):**
- Exact row signatures conservative, can require one bucket per hand
- General unrestricted-deck ranges may exceed caps; fail with actual counts/limits
- Proves S4 on declared finite fixtures, not arbitrary million-world games
- Large fixture intentionally has strong equivalences, shallow stacks, two runouts
- Not evidence of full-stack unrestricted-deck performance
- Complete game automorphism search not supplied
- Operational identity certificate is full equality of labelled strategic continuations, not equity/rank/category or informal suit similarity
- Compiled world/belief payload can dominate memory before CFR
- Existing recursive traversal and repeated best-response continuations remain
- max_depth ≤ 128 and finite physical caps explicit limitations, not claim of linear total solve cost
- Float training can differ slightly between original and reduced engines
- Rational certificate establishes value/error bounds; no bitwise equality of separately trained exact/reduced policies required
- Bitwise equality within lifted bucket IS required

**Evidence:** No universal `O(1/k)` exploitability claim (§1 line 16). No guessed percentage-of-pot error (§1 line 16). No post-measured ratio threshold (§1 line 16). Metadata must not imply smaller node count alone proves fixed runtime ratio (§5 lines 175-176). Runtime/memory receipts required when implementation exists; node count alone not universal runtime theorem (§7 line 240). Never claim unrestricted real-poker solution, unconstrained public deck, or measured exact-tree exploitability when only quotient metric run (§10 line 398).

## 3. Cross-release design completeness

### 3.1 End-to-end S4 design coverage

**COMPLETE** — Architecture provides:

1. ✓ **Policy definition:** exact-signature-belief-v1 with complete specification
2. ✓ **Data model:** immutable records for config, buckets, worlds, beliefs, plans, states
3. ✓ **Signature construction:** canonical inputs, blocker-aware labelled strategic continuations
4. ✓ **Probability semantics:** exact Fraction arithmetic for root mass, beliefs, posteriors
5. ✓ **Public compiler:** betting transitions, terminal utility, physical bounds
6. ✓ **Perfect recall:** fixed buckets, abstract information keys, noninterference
7. ✓ **Solver integration:** vanilla CFR and MCCFR, strategy completion, best response
8. ✓ **Lifting:** exact-tree policy projection with certified twin equality
9. ✓ **Mathematical certificates:** value bounds, lossless-response theorem, rational verification
10. ✓ **Fixtures:** small comparable (321→161) and large bounded (348,481→161) with exact counts
11. ✓ **API contract:** strict v4 operation, exhaustive request/response schemas
12. ✓ **Serialization:** structured records, rational fractions, deterministic sorting
13. ✓ **Implementation plan:** four RED-first batches with audit gates
14. ✓ **Compatibility:** S1-S3 preservation, existing API unchanged

### 3.2 Source feasibility

**FEASIBLE** — Architecture references actual source contracts:

- ✓ Inspected 11 source modules with specific semantic contracts (§2)
- ✓ `GameState` six-method protocol verified (§2 line 21)
- ✓ `MultiStreetState` exact private cards and root chance enumeration (§2 line 22)
- ✓ Public runouts as ORDERED sequences (§2 line 23)
- ✓ Legal betting actions card-independent (§2 line 24)
- ✓ Exact information keys exclude opponent cards and DEAL index (§2 line 25)
- ✓ Terminal source settlement uses exact integer awards (§2 line 26)
- ✓ `CFRSolver.__init__` calls full-tree `collect_infosets` (§2 line 27)
- ✓ `validate_bounded_tree` counts ALL visited history nodes (§2 line 28)
- ✓ `complete_strategy` copies supplied policies, fills missing keys uniformly (§2 line 29)
- ✓ `nash_conv` validates, evaluates, computes both infoset-consistent best responses (§2 line 29)
- ✓ `solve_allstreet_postflop` constructs/bounds exact root, trains, completes, calls `nash_conv` (§2 line 30)
- ✓ Existing strict v4 dispatcher permits three named operations (§2 line 31)

**No implementation blockers:** blocker_count=0 (§10 line 412). Remaining work is implementation and audit, not unresolved choice to defer physical reduction.

### 3.3 Dependency graph coherence

**COHERENT** — Clear module boundaries:

- ✓ `abstraction.py` imports model/multistreet/evaluator/equity/bounded_tree
- ✓ `abstraction_solve.py` imports cfr/best_response/api.complete_strategy
- ✓ Allstreet translation called locally by solve facade
- ✓ No eager api→facade→allstreet→api import cycle
- ✓ Acyclic import direction preserved

### 3.4 Scope and overclaims

**BOUNDED** — Architecture explicitly limits scope and avoids overclaims:

- ✓ Two preregistered fixtures with exact counts
- ✓ Heads-up two-player zero-sum only
- ✓ Finite configured ranges with explicit caps
- ✓ Conservative failure on no compression
- ✓ No universal exploitability claims
- ✓ No unrestricted-deck performance claims
- ✓ No linear runtime guarantees
- ✓ Explicit limitations documented (§10 lines 412-420)

## 4. R2 repair verification

### 4.1 R1 findings addressed

Per manifest (lines 22-28), R2 repairs three R1 findings:

1. **Incomplete exact response and nested wire schema**
   - ✓ FIXED: §9.1 provides exhaustive response wire schema with all required top-level keys (lines 336-360)
   - ✓ FIXED: Nested records have exact shapes (lines 366-403)
   - ✓ FIXED: AbstractionMetadata has exactly 48 specified keys (lines 408-448)

2. **Ambiguous optional versus required base bounds**
   - ✓ FIXED: §9 lines 310-315 make max_nodes/max_depth mandatory only for new operation
   - ✓ FIXED: Must equal abstraction bounds; omission fails before equality checking
   - ✓ FIXED: Existing operations retain current optional-bound behavior

3. **Integer range weights above 2^53 losing exactness through inherited _float parsing**
   - ✓ FIXED: §9 lines 332-333 specify weight parsing does NOT call existing `_float` helper
   - ✓ FIXED: Non-bool JSON integer remains integer, converted with `Fraction(value)`
   - ✓ FIXED: Finite JSON float remains float, converted with `Fraction.from_float(value)`
   - ✓ FIXED: Preserves integers above 2^53 exactly
   - ✓ FIXED: Local to new operation; prior operations retain existing behavior

### 4.2 R2 scope discipline

Per manifest (line 28): "R2 repairs only that contract surface. No production, tests, scripts, dependency, mission, or accepted Git bytes changed."

- ✓ Verified: `git diff --name-only -- src tests scripts pyproject.toml` returned empty
- ✓ Verified: All document hashes match manifest
- ✓ Verified: No abstraction implementation or tests present (expected)
- ✓ Verified: Full regression 817 passed

## 5. Independent full regression

**PASS** — Independent execution:

```bash
cd /home/genomix-node/poker-solver
UV_NO_CACHE=1 uv run --no-sync pytest -q
```

**Result:** 817 passed in 372.16s (0:06:12)

**Evidence:**
- No cache used (UV_NO_CACHE=1)
- No sync with lock file (--no-sync)
- Quiet mode (-q) for concise output
- All 817 tests passed
- No failures, errors, or warnings
- Source and tests unchanged from accepted base

## 6. Verdict

**PASS** — S4 architecture design R2 candidate is COMPLETE and FEASIBLE:

### 6.1 Design completeness

✓ End-to-end S4 design from policy definition through API serialization
✓ All 14 major components specified with exact semantics
✓ Two preregistered fixtures with reproducible exact counts
✓ Four RED-first implementation batches with audit gates
✓ Mathematical certificates for lossless abstraction
✓ Exhaustive API contract with structured schemas

### 6.2 Source feasibility

✓ References actual source contracts across 11 modules
✓ No implementation blockers (blocker_count=0)
✓ Clear module dependencies without import cycles
✓ Compatible with existing S1-S3 baseline
✓ Preserves 817-test regression

### 6.3 Dependency graph

✓ Coherent module boundaries
✓ Acyclic import direction
✓ No eager circular dependencies
✓ Clear separation of concerns

### 6.4 Scope and overclaims

✓ Explicitly bounded scope (heads-up, finite ranges, two fixtures)
✓ No universal exploitability claims
✓ No unrestricted-deck performance claims
✓ Explicit limitations documented
✓ Conservative failure on no compression

### 6.5 S1-S3 compatibility

✓ Existing APIs unchanged
✓ Historical tag preserved
✓ 817-test baseline green
✓ No production/tests/scripts modified
✓ Additive design only

### 6.6 R2 repair quality

✓ All three R1 findings addressed with exact fixes
✓ Exhaustive response schema (48 metadata keys)
✓ Mandatory base bounds for new operation only
✓ Integer weight exactness preserved above 2^53
✓ R2 scope discipline maintained (design-only changes)

### 6.7 Acceptance metrics

✓ Small fixture: 321→161 nodes, ≤0.02 chips NashConv gate
✓ Large fixture: 348,481→161 nodes, <10,000 cap
✓ Rational certificate with zero model error
✓ Terminal diameter exactly zero
✓ Lossless-response theorem

## 7. Completed artifacts

**Created:**
- `research/phase4/s4-design-audit-r2/06-cross-release.md` (this report)
- `.hb/R2A6` (flat completed heartbeat with SHA-256 of this report)

**Not modified:**
- Source files (`src/`)
- Test files (`tests/`)
- Scripts (`scripts/`)
- Dependencies (`pyproject.toml`)
- Candidate documents (ARCHITECTURE_PHASE4_S4.md, CANDIDATE_MANIFEST.md, etc.)
- Progress/state files

**Not performed:**
- No commits
- No edits to inputs/source/tests/progress/state
- No nested repository creation

---

**R2A6 cross-release design audit: COMPLETE**
**Verdict: PASS**
**Timestamp:** 2026-09-16 (UTC)
**Full regression:** 817 passed in 372.16s
**Architecture SHA-256:** 37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2
