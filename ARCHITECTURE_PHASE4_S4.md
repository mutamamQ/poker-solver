# Phase 4 S4 reconciled architecture — bounded exact-signature hand abstraction

## 1. Scope and decision

S4 adds a deterministic heads-up all-street postflop abstraction that reduces the PHYSICAL configured game tree, not merely the number of information keys. The delivered policy is `exact-signature-belief-v1`: hands are grouped only when their complete labelled strategic continuations are identical for the configured opponent support and ordered runouts. Compatible exact deals are retained once as bounded immutable latent worlds, while one physical public betting/chance tree is compiled per nonempty bucket pair.

This is an exact quotient of each accepted configured finite game, not a lossy fixed-k equity heuristic. It may find no compression and then fail a declared cap. That conservative failure is preferable to silently merging blocker-distinct hands. It satisfies S4 on two preregistered finite all-street fixtures, including a 4,356-world fixture whose exact tree has 348,481 physical nodes and whose quotient has 161.

The following are explicitly not S4 implementations:

- replacing `information_state_key` while retaining every exact deal branch;
- counting unique infosets or regret entries as physical nodes;
- category/equity bins without a proof that blockers, future public-card laws, payoffs, and observations agree;
- representative-hand sampling or unlabelled chance renormalization;
- a proposal that defers physical reduction to a later version;
- a universal `O(1/k)` exploitability claim, a guessed percentage-of-pot error, or a post-measured ratio threshold.

Supported v1 scope is the existing two-player zero-sum `MultiStreetConfig`, including an exact translation of `AllStreetPostflopConfig` with natural terminal settlement. S2/S3 multiplayer integration, unrestricted-deck scale, arbitrary generic `GameState` wrapping, warm starts, and general game-automorphism search are not part of S4.

Accepted base is commit `149780bf37e3e3a824e03e6d2c1df3cd99b12cd6`. Historical tag `phase3-398-green` must remain exactly `feba8222a0b614b0c64eca59402403ce733195ea`. The live pre-S4 regression is 817 tests; 398 is the preserved historical baseline, not the current expected total.

## 2. Source authority and adjudication

Authoritative source behavior is in:

- `src/poker_solver/model.py` for `GameState`, `Action`, CHANCE and TERMINAL;
- `src/poker_solver/multistreet.py` for exact deal/runout/betting/settlement semantics;
- `src/poker_solver/allstreet.py` for S1 config translation and exact solve facade;
- `src/poker_solver/bounded_tree.py` for literal history-node/depth counting;
- `src/poker_solver/cfr.py`, `api.py`, and `best_response.py` for strategy completion and two-player metrics;
- `src/poker_solver/evaluator.py` and `equity.py` for exact showdown evaluation and weighted combos;
- `src/poker_solver/api_v4.py` for strict JSON conventions.

The central design input is authenticated `research/phase4/s4-design/02-engine-integration-codex.md`, SHA-256 `79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d`, whose completed heartbeat carries the same hash. Parent reproduced its small exact solve and large counts. Useful attack ideas from S4D1/D3/D4/D6 are retained only where consistent with this document. Their equity/category grouping, informal suit equivalence, guessed bounds, and infoset-only reductions are rejected. Original S4D5 is rejected because its final report hash does not match its heartbeat and its `max_buckets`/category API contradicts the physical exact-signature design.

No design report is production authority after this architecture is frozen.

## 3. Exact-signature policy

### 3.1 Canonical inputs

Construction first validates and defensively copies the source config. Canonical order is:

- each hand is an increasing pair of integer card IDs;
- active hands are lexicographically sorted;
- ordered full runouts are sorted as whole tuples, but card order within `(turn, river)` remains semantic;
- source legal-action tuple order is preserved exactly;
- bucket IDs are assigned by lexicographically sorted distinct complete signatures.

Duplicate holdings are rejected rather than coalesced. Zero-weight hands are omitted from active support and counted in metadata. Each player must retain positive active mass and at least one compatible positive-mass deal. Every positive deal must have at least one legal configured runout; a blocked-out deal is an error, not silently conditioned away.

Weights are converted with `Fraction.from_float` before multiplication, preserving the supplied binary float exactly. Integers use `Fraction(value)`. Bool, nonfinite, negative, unsupported numeric values, and excessive numerator/denominator bit lengths fail before compilation.

### 3.2 Complete labelled signatures

For player 0 hand `h`, its signature has one cell for every canonically ordered player 1 hand `g`. Player 1 uses the transposed opponent labeling. Each cell is:

- `(0, ())` if the two hands are incompatible; or
- `(1, codes)` when compatible, with one code for every configured ordered full runout.

A runout code is `-2` when blocked by the hand pair. Otherwise it is the exact showdown comparison from the owning player's perspective: `-1`, `0`, or `+1`. River-start support uses one internal empty runout cell while preserving the public source config.

The entire tuple is the identity certificate. Hashes may identify serialized plans but never replace equality of the complete tuple. A mismatch may not be overridden to meet a cap.

Equal rows imply identical opponent compatibility, runout legality, and payoff ordering against every labelled opponent hand. Equal columns provide the same property for the other player. A positive bucket-pair cell is therefore rectangular: all member hand pairs are compatible, have the same public chance kernel, and have identical terminal ordering for every configured public continuation. Fold utility and legal betting transitions are card-independent. These are behavioural twins for the configured game.

Scalar equity, made-hand category, hole-card ranks, or informal suit symmetry are not certificates. Equal-equity hands separated by an opponent blocker or public-runout blocker MUST remain in different buckets.

### 3.3 Fixed buckets and perfect recall

A hand receives one private bucket at root and retains it through every street. No street-local rebucketing may merge distinct prior buckets. The abstract information key contains:

- policy version and a canonical semantic config digest;
- acting player;
- that player's own fixed bucket ID;
- full public frame: board, street, actor, pot, commitments, total contributions, remaining stacks, last-raise increment, betting history, public RUNOUT history, and terminal marker where applicable.

It excludes opponent bucket, exact cards, world ID, pair ID, latent probabilities, root abstract-deal action, and representative cards. Same abstract key therefore implies the same own observation/action sequence and ordered legal actions. Compile-time recall and noninterference checks are required in addition to `validate_bounded_tree`.

## 4. Physical reduced game

### 4.1 Immutable records

Add `src/poker_solver/abstraction.py` with frozen/slotted, defensively detached records equivalent to:

- `AbstractionConfig`;
- `Bucket`, `World`, `MemberWeight`, `Belief`;
- `PublicFrame`, `AbstractInfoKey`;
- `Edge`, `Node`, `ReducedPlan`, `ReducedState`.

`AbstractionConfig` is exactly:

```python
@dataclass(frozen=True, slots=True)
class AbstractionConfig:
    version: Literal["exact-signature-belief-v1"]
    max_abstract_nodes: int = 10_000
    max_depth: int = 32
    max_worlds: int = 5_000
    max_signature_cells: int = 20_000
    max_belief_entries: int = 20_000
    max_fraction_bits: int = 4096
```

Every limit is a positive non-bool integer. For compatibility with existing recursive traversal, v1 rejects `max_depth > 128`. It also rejects `initial_dead_pot + 2 * effective_stack > 2**40` and any Fraction that exceeds the bit cap.

Required public functions are:

```python
def canonicalize_config(config: MultiStreetConfig) -> MultiStreetConfig: ...
def build_buckets(config: MultiStreetConfig,
                  abstraction: AbstractionConfig) -> tuple[Bucket, ...]: ...
def compile_reduced_game(config: MultiStreetConfig,
                         abstraction: AbstractionConfig) -> ReducedPlan: ...
def create_reduced_root(plan: ReducedPlan) -> ReducedState: ...
def exact_member_state(config: MultiStreetConfig, world: World,
                       public: PublicFrame) -> MultiStreetState: ...
def abstract_key_for_exact(state: MultiStreetState, player: int,
                           plan: ReducedPlan) -> AbstractInfoKey: ...
def lift_exact_strategy(exact_root: MultiStreetState, plan: ReducedPlan,
                        profile: Strategy, *, max_nodes: int,
                        max_depth: int) -> Mapping[InfoKey, Mapping[Action, float]]: ...
```

`ReducedPlan.nodes` is a tree rooted at node 0, not a DAG used to disguise node count. `ReducedState.child` is an O(1) validated node lookup and never materializes member subtrees. Root chance actions are deterministic `Action("ABSTRACT_DEAL", k)` values for sorted nonempty bucket pairs. Public chance retains `Action("RUNOUT", card)`. Terminal APIs and invalid player/action requests fail closed like existing states.

### 4.2 Root mass and beliefs

For exact world `w=(h,g)`, raw mass is `r_w=f_h*f_g`; normalize by exact `Z=sum(r_w)`. Bucket-pair mass is the sum of world masses in the pair. Conditional member mass is the normalized world mass divided by pair mass.

For revealed runout prefix `s`, let `R_w(s)` be the configured legal full runouts beginning with `s`. The world next-card law is:

`p_w(c | s) = |R_w(s+c)| / |R_w(s)|`.

For belief `q`, aggregate observable chance mass is:

`P(c) = sum_w q(w) * p_w(c | s)`.

The child posterior is:

`q'(w) = q(w) * p_w(c | s) / P(c)`

for positive terms only. These equations use `Fraction`. Do not choose a hidden complete runout before turn betting; do not uniformly average worlds; do not pool raw sequence counts across worlds with different denominators.

Beliefs are shared by `(bucket_pair, revealed_prefix)` across betting histories. World arrays are not copied into every physical node. For exact-signature v1 the public kernels within a pair agree, but the general formula remains implemented and directly tested.

### 4.3 Public betting transitions

All members of a pair must have identical actor and ordered legal actions at a public frame. A real compatible member may be used only to project the SOURCE public transition fields produced by `MultiStreetState.child`; it is not a payoff representative and no exact subtree is retained. Compiler checks compare projected actor, history, ledger, next-card support, and public frame invariants. Any disagreement fails instead of intersecting actions or dropping members.

CFR traversal, strategy completion, and reduced best response must construct zero exact-world GameState subtrees. Instrumented tests distinguish bounded preprocessing member checks from solve-time traversal.

### 4.4 Terminal utility

At a terminal, preserve source integer settlement, including folds, refunds, all-ins, and odd ties. If `C=pot+sum(committed)`, each member produces an integer P0 award. Aggregate:

`u0 = sum_w q(w) * award0(w) - contributed0 - Fraction(initial_dead_pot, 2)`.

Compute the complementary P1 result independently and require exact `u0+u1==0`. Also require ledger conservation `C=initial_dead_pot+sum(total_contributed)`. Return `(float(u0), -float(u0))` only after finite/bound checks. Never infer settlement from mean equity or average already-rounded utilities.

## 5. Bounds and physical accounting

`node_count` is exactly the history occurrence count produced by `validate_bounded_tree`: root, chance, decision, and terminal nodes. It is not bucket count, infoset count, unique public frame count, live wrapper count, or regret-table size.

Compilation reserves a node before allocation and fails before exceeding `max_abstract_nodes`; equality is allowed. It separately bounds:

- compatible active worlds by `max_worlds`;
- charged signature scalar slots by `2 * len(H0) * len(H1) * max(1, len(allowed_runouts))` against `max_signature_cells`, including blocked cells;
- total stored `MemberWeight` entries against `max_belief_entries`;
- Fraction bit lengths against `max_fraction_bits`;
- depth against both the caller cap and v1 recursive ceiling.

After freezing the plan, run `validate_bounded_tree` on `ReducedState` and require every recorded count/depth to match. This preflight occurs before solver construction.

Metadata distinguishes physical nodes, infosets, latent worlds, signature slots, belief entries, and runtime. It must not imply that a smaller node count alone proves a fixed runtime ratio.

## 6. Strategy solve, lift, and truthful result

Add `src/poker_solver/abstraction_solve.py` with:

```python
@dataclass(frozen=True, slots=True)
class ExactEvaluationConfig:
    max_nodes: int
    max_depth: int

@dataclass(frozen=True, slots=True)
class AbstractSolveResult:
    algorithm: str
    seed: int | None
    iterations: int
    values: tuple[float, float]
    reduced_metric: NashConvResult
    exact_metric: NashConvResult | None
    strategy: Mapping[InfoKey, Mapping[Action, float]]
    lifted_strategy: Mapping[InfoKey, Mapping[Action, float]] | None
    plan: ReducedPlan
    approximate: bool
    abstraction_lossless: bool
    metric_scope: Literal["reduced-game"]
    exact_evaluation_status: Literal["not-requested", "completed"]
    provenance: str
    metadata: Mapping[str, object]

def solve_multistreet_abstracted(
    config: MultiStreetConfig,
    abstraction: AbstractionConfig,
    *,
    algorithm: Literal["vanilla-cfr", "external-sampling-mccfr"],
    iterations: int,
    seed: int | None = None,
    exact_evaluation: ExactEvaluationConfig | None = None,
) -> AbstractSolveResult: ...

def solve_allstreet_abstracted(
    config: AllStreetPostflopConfig,
    abstraction: AbstractionConfig,
    *,
    algorithm: Literal["vanilla-cfr", "external-sampling-mccfr"],
    iterations: int,
    seed: int | None = None,
    exact_evaluation: ExactEvaluationConfig | None = None,
) -> AbstractSolveResult: ...
```

Vanilla CFR requires `seed=None`; MCCFR requires a non-bool integer seed. S4 acceptance uses 1,000 deterministic vanilla iterations. The old exact APIs and result semantics are unchanged.

Allstreet translation must match `create_allstreet_root`. `config.max_nodes` must equal `abstraction.max_abstract_nodes`, and `config.max_depth` must equal `abstraction.max_depth`; ambiguous dual limits fail. Reduced compilation happens before any exact-tree preflight. Exact diagnostics are absent by default and have independent explicit bounds; requested diagnostics that exceed them fail rather than returning silently missing fields.

Lifting traverses an explicitly bounded exact root only when requested. Every reachable exact key maps through its own hand's certified bucket and complete abstract policy. Ordered actions must match. Missing policies, duplicate-key disagreement, unknown configs, and coverage gaps fail; `complete_strategy` may not mask a gap. The result contains detached, recursively frozen mappings. Certified twin hands receive the same copied float values exactly, while each original exact key remains separately addressable.

For large non-diagnostic solves, retain reduced policy, exact membership, and canonical digest for on-demand projection. Do not force a forbidden exact traversal during result construction.

`approximate=True` means the returned finite-iteration float CFR policy is not claimed to be an exact equilibrium. It does not mean the abstraction is lossy. Set `abstraction_lossless=True`, `model_error_bound=0`, `lossy_merges=0`, and label reduced versus exact metrics explicitly.

## 7. Mathematical certificates

For a complete profile `x` evaluated in the SAME exact two-player zero-sum game, define:

- `v(x)=u0(x)`;
- `U(x)=BR0(x1)`;
- `L(x)=-BR1(x0)`;
- `e0(x)=U(x)-v(x)`;
- `e1(x)=v(x)-L(x)`;
- `C(x)=e0(x)+e1(x)=U(x)-L(x)`.

Minimax gives `L(x) <= v* <= U(x)`. For a lifted abstract profile `a` and independently trained exact reference `r`:

`|v(a)-v(r)| <= max(e1(a)+e0(r), e0(a)+e1(r)) <= C(a)+C(r)`.

This compares finite profiles and does not assume either is equilibrium or convergence is monotone. On the preregistered small fixture, both profiles must have exact-tree NashConv at most 0.02 chips after 1,000 vanilla iterations, giving a preregistered loose value-gap bound of 0.04 chips and the tighter observed incentive expression above.

The exact-signature quotient has terminal diameter zero and identical observable kernels. For any bucket profile, rational reduced value equals rational exact lifted value. Extra exact-card distinctions cannot improve a response because types within a bucket have identical labelled continuations and factorized conditional mass; their realization-plan mixture is implementable under perfect recall. Therefore the v1 model-error term is exactly zero. This is a certificate, not a claim that float CFR has converged.

Small-fixture tests rationalize returned policy probabilities with `Fraction.from_float`, normalize each policy exactly, and replay exact chance/utility. They independently compute rational best-response incentives over the bounded 321-node tree and compare ordinary float metrics within `1e-10` chips. That tolerance is a regression tolerance, not the theorem.

## 8. Preregistered fixtures

### 8.1 Small comparable fixture

Use:

- flop `Ah Kh Qh`;
- ordered runouts `(Jh,9h)` and `(Jh,8h)`;
- initial dead pot 2, effective stack 1;
- no-limit target `(1,)`, river betting enabled;
- P0 hands `2c3c`, `2d3d`;
- P1 hands `2s3s`, `Th4s`;
- all weights 1.0.

Expected exact stats are 321 nodes, 136 terminals, 57 chance nodes, 128 decisions, depth 12. P0 has one bucket; P1 has two. The quotient has 161 physical nodes. Four exact deal worlds become two abstract deal outcomes with masses one-half each. Both rivers have conditional mass one-half after `Jh`.

Parent reference receipt at 1,000 exact vanilla iterations is values `(-0.9993335546875001, 0.9993335546875001)`, best responses `(-0.9993333333333333, 1.0000625)`, incentives `(2.2135416677393494e-07, 0.0007289453125000067)`, and NashConv `0.0007291666666667806`.

Two compulsory companions pin blocker safety:

- opponent-blocker fixture: equal-showdown hands but three compatible deals; both players' signatures stay separate;
- runout-blocker fixture: one of otherwise similar P0 hands blocks a declared runout; signatures stay separate and no positive deal is conditioned away.

### 8.2 Large bounded fixture

Use the same public game. P0 range is every unordered pair from:

`2c 3c 4c 5c 6c 7c 2d 3d 4d 5d 6d 7d`.

P1 range is every unordered pair from:

`2s 3s 4s 5s 6s 7s 2h 3h 4h 5h 6h Th`.

Each player has 66 hands, all weights one, and all 4,356 ordered pairs are compatible. P0 has one bucket of 66. P1 has a 55-hand no-`Th` bucket and an 11-hand `Th` bucket. Pair masses are `5/6` and `1/6`.

A single-world public tree has 81 nodes, 34 terminals, 15 chance nodes, 32 decisions, depth 12. Thus:

- exact physical nodes: `1 + 4,356 * 80 = 348,481`;
- reduced physical nodes: `1 + 2 * 80 = 161`;
- reduced terminals/chance/decisions: 68/29/64;
- charged signature slots: 17,424;
- literal belief member entries: 17,424.

Acceptance requires the complete reduced path — preflight, 1,000-iteration vanilla training, completion, reduced NashConv, frozen result, and strict serialization — under 10,000 physical nodes and depth 32. The same exact config with 10,000 nodes must fail before training. The result reports the exact count as an analytic certificate, not as an executed full traversal.

## 9. Strict v4 API and serialization

Add operation `solve-allstreet-abstracted` to `dispatch_v4`. Existing operations remain byte-for-schema compatible.

The request object has exactly `version`, `operation`, and `payload`. `version` is integer `4` and `operation` is literal `solve-allstreet-abstracted`.

For this new operation only, `payload` has exactly these required fields:

- `version`, `starting_board`, `initial_dead_pot`, `effective_stack`, `player0_combos`, `player1_combos`, `allowed_runouts`, `betting_mode`, `wager_targets`, `algorithm`, `iterations`, and `seed`, with the existing allstreet meanings;
- `max_nodes` and `max_depth`, which are newly mandatory for this operation even though they remain optional with unchanged defaults for `solve-allstreet-postflop`;
- `abstraction`.

The only optional payload field is `exact_evaluation`, whose value is null or the exact object described below. Unknown or missing fields fail. `payload.max_nodes` must equal `abstraction.max_abstract_nodes`, and `payload.max_depth` must equal `abstraction.max_depth`; omission of either base bound fails before equality checking. Existing operations retain their current optional-bound behavior.

The required `abstraction` object is exactly:

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

Optional `exact_evaluation` is absent, null, or exactly `{"max_nodes": int, "max_depth": int}`. Its integers and every bound are positive and non-bool. All nested schemas reject unknown or missing fields, bool-as-int, nonfinite values, duplicate holdings, invalid cards, incompatible limits, and algorithm/seed mismatch.

For this operation, range-entry `weight` parsing does NOT call the existing `_float` helper. A non-bool JSON integer remains an integer through positivity/bit-cap validation and is converted with `Fraction(value)`; a finite JSON float remains a float through validation and is converted with `Fraction.from_float(value)`. This rule preserves integers above `2**53` exactly and is local to the new operation. Direct-Python and decoded-JSON requests have identical behavior. Prior operations retain their existing float-coercion behavior.

### 9.1 Exhaustive response wire schema

The successful response is an object with exactly these required top-level keys; no key is optional:

```text
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

`reduced_exploitability == reduced_nashconv / 2`. When `exact_evaluation_status` is `not-requested`, both exact metrics and `lifted_strategy` are null. When it is `completed`, both exact metrics are finite and `lifted_strategy` is a non-null complete list. A requested diagnostic that exceeds a bound returns an error, never a successful response with `not-requested`. `provenance` is the exact sentence `finite-iteration float CFR over a certified exact-signature reduced configured multistreet game; exact rational aggregation; exact-tree diagnostics STATUS`, with `STATUS` replaced by `not-requested` or `completed`.

Nested records have these exact shapes and no additional keys:

```text
ActionRecord = {"kind": string, "amount": integer}
RationalRecord = {"numerator": decimal integer string,
                  "denominator": positive decimal integer string}
PublicFrameRecord = {
  "board": [integer, ...], "street": "flop" | "turn" | "river",
  "acting_player": integer, "pot": integer,
  "committed": [integer, integer],
  "total_contributed": [integer, integer],
  "remaining": [integer, integer], "last_raise_increment": integer,
  "history": [ActionRecord, ...], "terminal_reason": string | null
}
AbstractKeyRecord = {
  "policy_version": "exact-signature-belief-v1",
  "config_digest": 64-character lowercase hexadecimal string,
  "player": 0 | 1, "own_bucket": nonnegative integer,
  "public": PublicFrameRecord
}
ExactKeyRecord = {
  "game_version": "multistreet-v1", "player": 0 | 1,
  "own_cards": [integer, integer], "board": [integer, ...],
  "history": [ActionRecord, ...], "pot": integer,
  "committed": [integer, integer], "remaining": [integer, integer],
  "betting_mode": "no-limit" | "pot-limit"
}
PolicyItem = {"action": ActionRecord, "probability": finite float}
AbstractPolicyEntry = {"key": AbstractKeyRecord, "policy": [PolicyItem, ...]}
ExactPolicyEntry = {"key": ExactKeyRecord, "policy": [PolicyItem, ...]}
BucketRecord = {
  "player": 0 | 1, "bucket_id": nonnegative integer,
  "members": [[integer, integer], ...], "exact_mass": RationalRecord
}
BucketPairRecord = {
  "player0_bucket": nonnegative integer,
  "player1_bucket": nonnegative integer,
  "world_count": positive integer, "exact_mass": RationalRecord
}
```

`strategy` is sorted by the canonical encoding of `AbstractKeyRecord`; `lifted_strategy` is sorted by the canonical encoding of `ExactKeyRecord`. Each `policy` preserves source legal-action tuple order. Bucket records sort by `(player, bucket_id)`, members are sorted card pairs, and pair records sort by `(player0_bucket, player1_bucket)`. Probabilities are finite, nonnegative, and each policy sums to one within the solver's declared numeric tolerance; serializers never emit NaN or infinity.

`AbstractionMetadata` has exactly these keys and value types:

```text
policy_version: "exact-signature-belief-v1"
config_digest: 64-character lowercase hexadecimal string
digest_schema: "s4-semantic-config-v1"
source_game_version: "multistreet-v1"
original_combo_counts: [nonnegative integer, nonnegative integer]
active_combo_counts: [positive integer, positive integer]
zero_weight_combo_counts: [nonnegative integer, nonnegative integer]
compatible_world_count: positive integer
nonempty_pair_count: positive integer
physical_node_count: positive integer
physical_terminal_count: positive integer
physical_chance_count: nonnegative integer
physical_decision_count: nonnegative integer
physical_max_depth: nonnegative integer
max_abstract_nodes: positive integer
max_depth: positive integer
world_count: positive integer
max_worlds: positive integer
signature_cell_count: nonnegative integer
max_signature_cells: positive integer
belief_entry_count: nonnegative integer
max_belief_entries: positive integer
max_fraction_bits: positive integer
bucket_sizes: [[positive integer, ...], [positive integer, ...]]
buckets: [BucketRecord, ...]
bucket_pairs: [BucketPairRecord, ...]
exact_node_count_analytic: positive integer | null
exact_node_count_status: "not-derived" | "derived-not-traversed" | "executed"
exact_signature_certificate: true
terminal_diameter: RationalRecord
model_error_bound: RationalRecord
arithmetic: "exact-fraction-aggregation-float-cfr"
algorithm: "vanilla-cfr" | "external-sampling-mccfr"
seed: integer | null
iterations: positive integer
exact_evaluation_max_nodes: positive integer | null
exact_evaluation_max_depth: positive integer | null
exact_evaluation_status: "not-requested" | "completed"
```

For this v1 lossless policy, `terminal_diameter` and `model_error_bound` are exactly zero rational records. Diagnostic bounds are null exactly when status is `not-requested`; otherwise they reproduce the requested exact-evaluation bounds. Internal world, belief, and node arrays are never serialized.

The digest is lowercase hexadecimal SHA-256 over UTF-8 canonical JSON for the normalized semantic source config plus abstraction config. The digest input includes `"digest_schema":"s4-semantic-config-v1"`; object keys are lexicographically sorted, separators are exactly `,` and `:`, ASCII escaping is enabled, cards and runouts use their specified canonical sorted order, integers remain decimal integers, and every normalized weight/fraction uses `RationalRecord`. This rule is shared by Python result records and JSON output.

Returned Python mappings and all nested containers are detached and deeply immutable; JSON conversion creates fresh lists/objects with no mutable alias to the result. Structured records, never `str(key)` dictionaries, preserve key/action identity. Nonfinite serialization fails.

Add package exports for the two config/result families and public compiler/solve/lift entry points. CLI remains generic through existing v4 dispatch. Add canonical small and large JSON examples only after their exact commands execute successfully.

## 10. RED-first implementation and audit batches

No production bytes may precede each batch's behavioral RED. Every permanent test imports and invokes production, contains no placeholder/pass/caught-import trick, and is statically read by parent before GREEN. Existing baseline controls run separately during RED. Each accepted implementation candidate is hash-frozen, runs focused plus full regression, and receives a wholly fresh exact-six BryantGPT non-author audit before the next batch.

### S4-I1 — policy, config, canonical signatures

RED-owned tests:

- `tests/test_abstraction_signatures.py`.

Required cases cover strict config/direct construction, deep immutability, input permutation determinism, Fraction conversion and caps, duplicate/zero/blocked support, exact labelled row/column grouping, opponent blockers, runout blockers, equal-equity separation, bucket ID collision freedom, and the small/large membership tables.

GREEN owns only `src/poker_solver/abstraction.py` up through canonicalization and `build_buckets`. No state compiler or solver stubs that falsely pass later gates.

Fresh audit scopes: schema/immutability; signature proof; blocker counterexamples; Fraction/caps; determinism/collision; full regression/release boundary.

### S4-I2 — worlds, beliefs, public compiler, ReducedState

RED-owned tests:

- `tests/test_abstraction_reduced_game.py`.

Required cases cover root mass, generalized posterior arithmetic, public turn-before-river chance, physical node/depth boundaries 160 fail/161 pass, expected small/large stats, source differential transitions, actor/action ordering, folds/refunds/all-ins/pot-limit/river-betting variants, exact odd-tie settlement, zero sum, perfect recall, hidden-state noninterference, and instrumentation proving no exact-world GameState construction during traversal.

GREEN completes bounded immutable world/belief/plan compilation and `ReducedState`. No solve/API edits.

Fresh audit scopes: probability/posteriors; source transition differential; physical counts/caps; settlement/conservation; recall/noninterference; full regression/performance payload.

### S4-I3 — solver, lift, exact diagnostics, certificates

RED-owned tests:

- `tests/test_abstraction_solve.py`;
- bounded test-only rational certificate helpers.

Required cases cover vanilla and MCCFR seed contracts, reduced solve determinism, arbitrary nonuniform bucket-profile rational simulation equality, exact lift coverage and ordered actions, bit-identical twin policy values without mutable aliasing, exact diagnostic cap failures, scalable versus exhaustive tiny best response, rational incentive theorem, small 1,000-iteration quality gates, large complete solve, exact large preflight failure, and zero exact-world construction during train/complete/reduced-BR.

GREEN owns `src/poker_solver/abstraction_solve.py` and the minimum lift/projection additions in `abstraction.py`.

Fresh audit scopes: CFR/metric scope; lift/corruption; rational certificates; exact diagnostics; large complete solve/resource accounting; full regression/determinism.

### S4-I4 — API, exports, examples, S4 docs

RED-owned tests:

- `tests/test_api_v4_abstraction.py`;
- `tests/test_phase4_s4_examples.py`;
- `tests/test_phase4_s4_exports.py`.

At least one valid positive request must fail only because the new operation is absent; malformed-input cases are controls until GREEN and then must reach specific nested validation. Tests cover the exhaustive top-level and nested schemas above, both diagnostic-status cases, deterministic list ordering, integer weights above `2**53` with direct-Python/JSON parity, omitted/one-omitted/equal/unequal base and abstraction bounds, structured key/action serialization, JSON finite safety, deep response isolation, existing-operation compatibility, CLI file/stdin/error paths, and executable examples.

GREEN owns additive edits to `api_v4.py`, `__init__.py`, canonical examples, and only S4-specific README/docs text. It may not rename or relax prior operations.

Fresh audit scopes: strict parser; serialization/collision/isolation; exports/compatibility; examples/CLI; docs truth; full regression/release.

## 11. Per-batch parent gates

For every S4 implementation batch:

1. prove final test bytes are a genuine pre-production RED against the exact prior production snapshot;
2. record literal test/source/report hashes;
3. run focused tests with no skipped/xfail placeholder coverage;
4. run relevant S1/API compatibility tests;
5. run `uv run python -m compileall -q src tests scripts`;
6. run `uv run pytest -q` with no exclusions;
7. run `git diff --check` before freezing;
8. freeze a candidate manifest from repository root;
9. dispatch exactly six fresh BryantGPT non-authors with exclusive reports/flat completed heartbeats;
10. parent-authenticate transcripts, report/heartbeat hashes, probes, candidate pre/post hashes, focused/full receipts, HEAD and tag;
11. repair every reproduced finding via a new behavioral RED and repeat a wholly fresh audit of changed bytes;
12. commit the accepted batch before starting the next.

The design checkpoint itself is frozen and audited before S4-I1. Design auditors judge specification correctness/feasibility; missing implementation at that stage is expected and not a blocker.

## 12. S4 completion gate

S4 is complete only when all of the following are parent-verified:

- exact-signature policy is explicit in typed config and strict JSON;
- small exact tree count is 321 and small quotient count is 161;
- small lifted and exact-reference profiles satisfy the preregistered NashConv and incentive bound on the exact tree;
- blocker companions prove equal equity is not treated as identity;
- large exact count certificate is 348,481 while complete reduced solve uses exactly 161 physical nodes under cap 10,000;
- exact same-game preflight fails under that cap before training;
- deterministic repeated vanilla solve and same-seed MCCFR tests pass;
- every certified twin lifts to exactly equal policy values with complete, immutable exact-key coverage;
- no traversal hides an exact subtree behind a reduced wrapper;
- every metadata field distinguishes physical, infoset, latent-world, preprocessing, metric-scope, and finite-iteration semantics;
- all pre-S4 tests plus additive S4 tests pass;
- every implementation batch has a fresh different exact-six non-author audit and accepted commit;
- `phase3-398-green` remains unchanged.

Only then may S5 design begin.
