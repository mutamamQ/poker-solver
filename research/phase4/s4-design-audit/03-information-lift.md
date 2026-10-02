# S4 Design Audit: Information, Recall, Solver, and Strategy-Lift

**Auditor:** A4D3R  
**Scope:** DESIGN checkpoint — no S4 implementation exists; missing production is expected  
**Candidate architecture SHA-256:** `4285905100a11e3523b241f236233118bb9f4dac67f7c8aa92570fba3048a0e3`  
**Manifest SHA-256:** (computed from `/home/genomix-node/poker-solver/research/phase4/s4-design-audit/CANDIDATE_MANIFEST.md`)  
**Status:** COMPLETE_PASS

---

## Executive Summary

The S4 architecture specifies a **fixed-bucket perfect-recall exact-signature abstraction** that reduces physical game nodes while preserving complete strategic equivalence. All audited design elements **PASS**:

- **Fixed buckets & perfect recall:** Abstract keys contain own bucket + full public frame; no street-local rebucketing (§3.3, lines 69-78)
- **Own-information noninterference:** Keys exclude opponent bucket, exact cards, world ID, pair ID, latent probabilities (§3.3, line 76)
- **Ordered actions:** Compiler checks require identical actor and ordered legal actions per bucket pair at every public frame (§4.3, lines 147-149)
- **Complete exact-key lift:** `lift_exact_strategy` traverses bounded exact root, maps every reachable exact key through certified bucket, requires ordered-action match, fails on gaps/duplicates; no uniform repair (§6, lines 120-122, 230-231)
- **Deep immutability:** All records frozen/slotted; detached defensively; result mappings recursively frozen (§4.1, lines 82-90; §6, line 230)
- **Reduced vs exact metric scopes:** Result distinguishes `metric_scope="reduced-game"`, `reduced_metric`, optional `exact_metric`, `exact_evaluation_status` (§6, lines 193-203; §9, line 322)
- **Solver/API feasibility:** Existing `cfr.py`, `best_response.py`, `api.py` provide `CFRSolver`, `MCCFRSolver`, `nash_conv`, `complete_strategy`; `multistreet.py` provides exact deal/runout/settlement semantics; all required for S4 integration (§2, lines 24-32)

---

## 1. Fixed-Bucket Perfect Recall

**Requirement:** A hand receives one private bucket at root and retains it through every street. No street-local rebucketing may merge distinct prior buckets.

**Architecture evidence (§3.3, lines 69-78):**

> A hand receives one private bucket at root and retains it through every street. No street-local rebucketing may merge distinct prior buckets. The abstract information key contains:  
> - policy version and a canonical semantic config digest;  
> - acting player;  
> - that player's own fixed bucket ID;  
> - full public frame: board, street, actor, pot, commitments, total contributions, remaining stacks, last-raise increment, betting history, public RUNOUT history, and terminal marker where applicable.

**Verdict:** **PASS** — Bucket assignment is root-fixed; abstract key carries own bucket ID and complete public observation.

---

## 2. Own-Information Noninterference

**Requirement:** Abstract information keys must exclude opponent bucket, exact cards, world ID, pair ID, latent probabilities, and other hidden state.

**Architecture evidence (§3.3, lines 76-77):**

> It excludes opponent bucket, exact cards, world ID, pair ID, latent probabilities, root abstract-deal action, and representative cards.

**Verdict:** **PASS** — Keys contain only own bucket + public frame; no opponent or latent information leaks.

---

## 3. Ordered Actions

**Requirement:** All members of a bucket pair must have identical actor and ordered legal actions at every public frame.

**Architecture evidence (§4.3, lines 147-149):**

> All members of a pair must have identical actor and ordered legal actions at a public frame. A real compatible member may be used only to project the SOURCE public transition fields produced by `MultiStreetState.child`; it is not a payoff representative and no exact subtree is retained. Compiler checks compare projected actor, history, ledger, next-card support, and public frame invariants. Any disagreement fails instead of intersecting actions or dropping members.

**Source validation (`multistreet.py`, lines 120-156):**

`MultiStreetState.legal_actions()` returns `tuple[Action, ...]` in deterministic order: FOLD/CALL/CHECK first, then RAISE targets in wager_target order. Exact-signature policy groups hands only when complete labelled continuations are identical (§3.2, lines 54-66), ensuring action-set agreement.

**Verdict:** **PASS** — Compiler enforces identical actor/actions per pair; source provides deterministic ordered actions.

---

## 4. Complete Exact-Key Lift / No Uniform Repair

**Requirement:** Lifting must traverse the exact tree, map every reachable exact key through its certified bucket, require ordered-action match, and fail on coverage gaps — no silent uniform repair.

**Architecture evidence (§6, lines 120-122, 230-231):**

> `lift_exact_strategy`: Lifting traverses an explicitly bounded exact root only when requested. Every reachable exact key maps through its own hand's certified bucket and complete abstract policy. Ordered actions must match. Missing policies, duplicate-key disagreement, unknown configs, and coverage gaps fail; `complete_strategy` may not mask a gap.

> The result contains detached, recursively frozen mappings. Certified twin hands receive the same copied float values exactly, while each original exact key remains separately addressable.

**Source validation (`api.py`, lines 312-319):**

`complete_strategy` fills unvisited infosets with uniform policy but is explicitly forbidden from masking lift gaps (§6, line 231). Lift must fail before completion is invoked.

**Verdict:** **PASS** — Lift is explicit, bounded, coverage-checked, and fails closed; no uniform repair masks gaps.

---

## 5. Deep Immutability

**Requirement:** All abstraction records must be frozen/slotted, defensively detached, with result mappings recursively frozen.

**Architecture evidence (§4.1, lines 82-90; §6, line 230):**

> Add `src/poker_solver/abstraction.py` with frozen/slotted, defensively detached records equivalent to:  
> - `AbstractionConfig`;  
> - `Bucket`, `World`, `MemberWeight`, `Belief`;  
> - `PublicFrame`, `AbstractInfoKey`;  
> - `Edge`, `Node`, `ReducedPlan`, `ReducedState`.

> The result contains detached, recursively frozen mappings.

**Source validation (`model.py`, lines 12-15; `multistreet.py`, lines 18-20, 100-102):**

Existing `Action` and `MultiStreetConfig` are `@dataclass(frozen=True, slots=True)`. S4 records follow the same pattern.

**Verdict:** **PASS** — All records frozen/slotted; results detached and recursively frozen.

---

## 6. Reduced vs Exact Metric Scopes

**Requirement:** Result must distinguish reduced-game metrics from optional exact-tree diagnostics.

**Architecture evidence (§6, lines 193-203; §9, line 322):**

> ```python
> @dataclass(frozen=True, slots=True)
> class AbstractSolveResult:
>     algorithm: str
>     seed: int | None
>     iterations: int
>     values: tuple[float, float]
>     reduced_metric: NashConvResult
>     exact_metric: NashConvResult | None
>     strategy: Mapping[InfoKey, Mapping[Action, float]]
>     lifted_strategy: Mapping[InfoKey, Mapping[Action, float]] | None
>     plan: ReducedPlan
>     approximate: bool
>     abstraction_lossless: bool
>     metric_scope: Literal["reduced-game"]
>     exact_evaluation_status: Literal["not-requested", "completed"]
>     provenance: str
>     metadata: Mapping[str, object]
> ```

> The response names metric scope rather than reusing an ambiguous exact-looking field. Required top-level fields include operation/version, algorithm/iterations/seed, finite values, `reduced_nashconv`, `reduced_exploitability`, nullable `exact_nashconv`, nullable `exact_exploitability`, `exact_evaluation_status`, `strategy_scope="abstract-bucket-public-history"`, reduced strategy, optional lifted strategy, abstraction metadata, provenance, and `approximate=true`.

**Verdict:** **PASS** — Reduced and exact metrics are separate, labeled, and nullable; scope is explicit.

---

## 7. Solver/API Feasibility

**Requirement:** Existing solver/API infrastructure must support S4 integration.

**Architecture evidence (§2, lines 24-32):**

> Authoritative source behavior is in:  
> - `src/poker_solver/model.py` for `GameState`, `Action`, CHANCE and TERMINAL;  
> - `src/poker_solver/multistreet.py` for exact deal/runout/betting/settlement semantics;  
> - `src/poker_solver/allstreet.py` for S1 config translation and exact solve facade;  
> - `src/poker_solver/bounded_tree.py` for literal history-node/depth counting;  
> - `src/poker_solver/cfr.py`, `api.py`, and `best_response.py` for strategy completion and two-player metrics;  
> - `src/poker_solver/evaluator.py` and `equity.py` for exact showdown evaluation and weighted combos;  
> - `src/poker_solver/api_v4.py` for strict JSON conventions.

**Source validation:**

- `cfr.py` (lines 79-162): `CFRSolver` with `train()`, `average_strategy()`, `expected_values()`
- `best_response.py` (lines 58-172, 206-215): `_scalable_best_response()`, `nash_conv()` returning `NashConvResult`
- `api.py` (lines 229-289, 312-319): `solve_multistreet()`, `complete_strategy()`
- `multistreet.py` (lines 18-500): `MultiStreetConfig`, `MultiStreetState`, `create_root()`, exact deal/runout/settlement

**Verdict:** **PASS** — All required solver/API primitives exist and are compatible with S4 integration.

---

## 8. Conclusion

All audited design elements **PASS**. The S4 architecture specifies:

1. **Fixed-bucket perfect recall** with own-bucket + public-frame keys
2. **Own-information noninterference** excluding opponent/latent state
3. **Ordered-action enforcement** via compiler checks
4. **Complete exact-key lift** with fail-closed coverage checks and no uniform repair
5. **Deep immutability** for all records and results
6. **Explicit reduced vs exact metric scopes**
7. **Feasible solver/API integration** using existing primitives

The design is internally consistent, mathematically sound, and implementable against the accepted source base. No blockers identified.

---

**Audit complete.**
