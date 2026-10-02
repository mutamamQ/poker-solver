# C4D2-CODEX: physically reduced, exact-signature belief game

Design only. Status: COMPLETE_DESIGN. Author: C4D2-CODEX.
Design timestamp: 2026-09-16T11:07:52Z. Final live UTC and this file's exact SHA-256 are in `.hb/C4D2-CODEX`.
Accepted baseline supplied by the task: `149780bf37e3e3a824e03e6d2c1df3cd99b12cd6`; no git command was used to independently inspect HEAD. The current suite baseline is 817 tests, not the mission document's historical 398. No implementation or test files were changed, and no full-suite pass is claimed.

## 1. Decision and acceptance scope

Implement one stdlib-only v1: **`exact-signature-belief-v1`**, a compiled distribution-state GameState for the existing heads-up chip-EV multistreet game. Automatically group private hands by exact, labelled opponent-compatibility/runout/showdown signatures. Aggregate compatible deals into bucket-pair chance outcomes. Compile ONE betting tree per bucket pair, with public card outcomes aggregated using exact conditional probabilities. Store exact worlds once as immutable data, not an exact GameState subtree per world. Reuse public transitions and precompute terminal winner distributions before CFR starts.

This is a conservative, lossless abstraction of supported configured games, not a fixed-k heuristic. It can find no reduction on asymmetric games and then reject a requested node cap. It does provide physical reduction in v1: the literal large fixture below has 4,356 exact deal outcomes and 348,481 tree nodes, versus TWO reduced deal outcomes and 161 tree nodes. Both games include flop, turn, and river betting. The same node cap is 10,000. Preprocessing also has separate finite world/signature/belief-entry limits.

S4 does not require lossy abstraction or guaranteed compression of every possible range. Exact strategic equivalence is a valid automatic hand abstraction and supplies a stronger error certificate than an uncalibrated equity heuristic. No user-supplied continuations or future physical-reduction milestone is required.

The proposed weighted-member state is sound with restrictions. A generic wrapper over arbitrary GameState is NOT the v1 interface: public/private decomposition, rational chance reconstruction, perfect recall, and card-independent public transitions are not discoverable from that protocol alone. Restrict the compiler to a defensively copied `MultiStreetConfig`, including the allstreet translation with `river_betting=True`. Heads-up, zero-sum, natural settlement only; unsupported game types fail explicitly.

## 2. Actual source contracts and rejected input

Inspected `model.py`, `cfr.py`, `bounded_tree.py`, `allstreet.py`, `multistreet.py`, `best_response.py`, `api.py`, `equity.py`; additionally `api_v4.py`, `cards.py`, and the MCCFR entry points. Relevant test inspection included model/CFR, multistreet blocker and information tests, allstreet config/state/oracle tests, bounded-tree failures, exact/range equity tests, best-response hidden-bit and phase-2 oracles, and v2/v4 API validation and isolation tests.

* `GameState` has the six methods shown below; `Action(kind: str, amount: int=0)` is frozen/ordered and rejects bool amounts. CHANCE=-1, TERMINAL=-2. Chance probabilities and two-player returns cross its boundary as floats.
* `MultiStreetState` stores exact private cards. Root chance enumerates positive, compatible product-weight deals using float multiplication and normalization. Root `child(DEAL)` reconstructs the pair list. Do not call those methods once per exact deal in the reduced compiler.
* Public runouts are ORDERED sequences. At a dealt chance state, the source filters sequences by already revealed prefix and private/board blockers, then counts the next card. A world with one legal full sequence gets probability one for it; a world with three legal sequences gets one-third per sequence. Root deal mass is NOT multiplied by its number of legal runouts. Positive deals with no legal sequence produce an invalid game; reject rather than silently remove or renormalize them.
* Legal betting actions, next actor, commitments, contributions, remaining stacks, min-raise increment, and fold reasons depend on public state, not the exact cards. Preserve the actual CHECK/CALL/RAISE/FOLD semantics, raise-to amounts, refunds, all-in chance transitions, and `river_betting` behavior. Do not substitute an idealized poker betting model.
* Exact information keys are `(config.version, player, sorted_own_cards, board, history_without_DEAL, pot, committed, remaining, betting_mode)`. Opponent cards and DEAL index are excluded. Tests explicitly check this.
* Terminal source settlement uses exact integer awards, including ties `contested//2` to P0 and the remainder to P1, then subtracts total contributions and half the initial dead pot. Reconstruct this arithmetic with Fraction; do not calculate a mean of rounded equities. `range_equity` returns a float and enumerates unrestricted remaining-deck runouts; it is not the configured-runout kernel needed here.
* `CFRSolver.__init__` calls full-tree `collect_infosets`. Ordered action tuples must agree at a key. `train` uses synchronous snapshots, chance-weighted regret updates, and owner-reach averaging. Its owner-reach equality check is useful but not a perfect-recall proof.
* `validate_bounded_tree` counts ALL visited history nodes, including chance and terminals, with root depth zero. It does not count just decisions or distinct infosets. It checks action SET consistency, while CFR requires ordered tuples. It checks recursion-stack identity cycles; it does not establish perfect recall or noninterference.
* `complete_strategy(root, strategy)` copies supplied policies and fills missing keys uniformly after a full collection walk; it neither repairs malformed existing policies nor proves a lift is complete. `nash_conv` validates, evaluates, and computes both infoset-consistent best responses. Its scalable response algorithm uses counterfactual reach and an infoset dependency DAG; the Cartesian pure-strategy function is only a tiny-game oracle.
* `solve_allstreet_postflop` currently constructs and bounds the exact root, trains, completes, and calls `nash_conv`. It returns deeply frozen `AllStreetSolveResult`, `approximate=False`, and exact configured-tree provenance. `api.solve_multistreet` has a separate 10,000 heuristic chance-leaf guard and returns a different `SolveResult`; do not mistake that guard for a physical count.
* The existing strict v4 dispatcher currently permits three named operations; allstreet payload optional fields are only max_nodes/max_depth. Its actual card format is integer cards, whereas v2 parses card strings. New abstraction fields require an explicit additive API contract, not silently ignored JSON. Existing allstreet imports `complete_strategy` from api; preserve an acyclic import direction.

The entire rejected `02-engine-integration.md` was treated as partial input, not authority. Reject its key-only wrapper as S4 delivery, postponement of physical reduction, finite-CFR monotonicity assertion, ratio<50 test, equality-of-equity identity criterion, blanket rainbow-board suit-isomorphism example, and claim bounded-tree validation proves recall. Finer restrictions can change equilibrium sets; finite trained profiles have no required exploitability ordering. The sample guessed hand/history arithmetic is replaced below by exact combinatorics and an executed source counting probe.

## 3. Canonical, blocker-aware policy

First validate all source constraints, then defensively copy every sequence to tuples. Reject duplicate holdings rather than coalescing them. Omit zero-weight holdings from active support with explicit metadata counts; reject no-compatible-positive-mass input. Canonical order is sorted integer card pairs, sorted ordered runout tuples, and source-ordered legal betting actions. Do NOT sort cards WITHIN a runout: `(turn,river)` order is semantic. The allstreet facade currently rejects reversed duplicates as unordered pairs; retain that facade restriction, even though direct multistreet permits different ordered sequences.

Convert each finite positive input float weight with `Fraction.from_float(weight)` (integers with `Fraction(weight)`) BEFORE multiplication. Reject bools, unsupported numeric types, NaN, infinities, negative weights, and excessive numerator/denominator bit lengths. This preserves the actual binary-float input exactly; it does not pretend JSON 0.1 was exact decimal one-tenth. Serialize canonical fractions as numerator/denominator strings in provenance. Legacy exact-root float probabilities differ by rounding, addressed in section 8.

Let each player's active support be a sorted list H_i. For own hand h, build a signature row indexed by EVERY labelled opponent hand g in H_(1-i):

1. Incompatible cards: cell `(-2, ())`.
2. Compatible cards: cell `(1, codes)`, one code per configured ordered full runout. Code -2 means blocked; otherwise code -1/0/+1 is the player's showdown loss/tie/win on that final board. For a river start, use one synthetic empty runout `()` for this internal table, while the public config keeps allowed_runouts empty.

Compute comparisons from exact `evaluate_seven`, memoized per (hand, final board), never average equity. Opponent labels and blocked positions are significant. A compatible cell with every runout blocked fails construction. Assign bucket IDs by lexicographically sorted DISTINCT complete signature tuples; hands with the same tuple MUST have the same bucket. Store and compare complete tuples, not hashes alone. Hashes identify plans/results, not equivalence.

These are **exact behavioural twins with the same public labels**: they block the same opponent holdings, permit the same public runouts against each opponent, and have the same showdown ordering at every possible final board. Fold utilities and betting transitions are card-independent. Different own range weights do not change conditional opponent beliefs: the own weight cancels. This is stronger than equity equality, and insensitive to irrelevant card labels when their entire strategic effects agree.

Rectangular-cell proof: if h,h' have equal rows, compatibility with each g agrees. If g,g' have equal columns, compatibility with every h agrees. Thus a positive bucket pair contains a full Cartesian product of its hand members, not a hidden ragged compatibility subset. Its runout legality and payoff code at each final board are constant across all worlds. The conditional root mass within a pair factorizes into the two normalized own-hand masses. This establishes the lossless type quotient and permits the preprocessing optimization below. Keeping all exact members still permits independent checking of this certificate.

Blocker-distinct signatures stay in separate buckets, even when equity coincides. There is no lossy override and no target bucket count in v1. A signature mismatch cannot be overridden to meet the cap. No silent fallback to representative cards, random sampling, or a different board/range.

Identity guarantee is precise: all certified twins receive bit-for-bit equal lifted policies at the same public history, by copying the SAME normalized policy. Suit/rank labels alone never certify identity. A simultaneous suit permutation that changes labelled public histories or permutes strategically different opponent types is a game automorphism, not necessarily equality at the same information key. Do not advertise this v1 as a general automorphism minimizer or claim all equal-strength cards are twins. Where a purported equivalence needs a changed public label, comparison must include that label mapping; v1 makes no such merge. Within the accepted equality-of-labelled-continuations definition, ALL equal signatures merge, not just a selected representative subset.

## 4. Literal immutable data model and signatures

The following is an interface specification, not installed code. All construction is through validated factories. Dataclass `frozen=True` alone does not recursively freeze caller lists: factories must detach/tuple-convert all fields, enforce exact record types, and never retain caller dictionaries. Frozen result mappings require copied inner `MappingProxyType` mappings as in allstreet.

```python
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal, Mapping
from poker_solver.model import Action, InfoKey, Strategy
from poker_solver.multistreet import MultiStreetConfig, MultiStreetState, Street
from poker_solver.bounded_tree import BoundedTreeStats
from poker_solver.best_response import NashConvResult

Hand = tuple[int, int]
Deal = tuple[Hand, Hand]
BucketPair = tuple[int, int]
SignatureCell = tuple[int, tuple[int, ...]]
HandSignature = tuple[SignatureCell, ...]

@dataclass(frozen=True, slots=True)
class AbstractionConfig:
    version: Literal["exact-signature-belief-v1"]
    max_abstract_nodes: int = 10_000
    max_depth: int = 32
    max_worlds: int = 5_000
    max_signature_cells: int = 20_000
    max_belief_entries: int = 20_000
    max_fraction_bits: int = 4096

@dataclass(frozen=True, slots=True)
class Bucket:
    player: int
    bucket_id: int
    signature: HandSignature
    hands: tuple[Hand, ...]

@dataclass(frozen=True, slots=True)
class World:
    deal: Deal
    root_mass: Fraction            # normalized over all compatible deals
    runout_ids: tuple[int, ...]    # legal full sequences, sorted
    outcomes0: tuple[int, ...]     # P0 -1/0/+1, aligned with runout_ids

@dataclass(frozen=True, slots=True)
class MemberWeight:
    world_id: int
    probability: Fraction         # strictly positive conditional weight

@dataclass(frozen=True, slots=True)
class Belief:
    pair: BucketPair
    revealed: tuple[int, ...]
    members: tuple[MemberWeight, ...]
    next_cards: tuple[tuple[Action, Fraction], ...]
    showdown0: tuple[Fraction, Fraction, Fraction] | None # lose,tie,win

@dataclass(frozen=True, slots=True)
class PublicFrame:
    board: tuple[int, ...]
    street: Street
    acting_player: int
    pot: int
    committed: tuple[int, int]
    total_contributed: tuple[int, int]
    remaining: tuple[int, int]
    last_raise_increment: int
    history: tuple[Action, ...]    # only betting actions and RUNOUT
    terminal_reason: str | None

@dataclass(frozen=True, slots=True)
class AbstractInfoKey:
    version: Literal["exact-signature-belief-v1"]
    config_digest: str
    player: int
    own_bucket: int
    public: PublicFrame

@dataclass(frozen=True, slots=True)
class Edge:
    action: Action
    child_id: int
    probability: Fraction | None # Fraction at chance; None at decisions

@dataclass(frozen=True, slots=True)
class Node:
    actor: int
    public: PublicFrame | None    # None only at root private chance
    pair: BucketPair | None
    belief_id: int | None
    edges: tuple[Edge, ...]
    key: AbstractInfoKey | None   # acting player's key at decisions
    utility0: Fraction | None     # non-None exactly at terminals

@dataclass(frozen=True, slots=True)
class ReducedPlan:
    config: MultiStreetConfig     # defensive immutable canonical copy
    abstraction: AbstractionConfig
    config_digest: str            # canonical semantic inputs, not runtime counters
    buckets: tuple[Bucket, ...]
    worlds: tuple[World, ...]
    beliefs: tuple[Belief, ...]
    nodes: tuple[Node, ...]        # root at index zero; tree, not a merged DAG
    stats: BoundedTreeStats

@dataclass(frozen=True, slots=True)
class ReducedState:
    plan: ReducedPlan
    node_id: int = 0
    def current_player(self) -> int: ...
    def legal_actions(self) -> tuple[Action, ...]: ...
    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]: ...
    def child(self, action: Action) -> ReducedState: ...
    def information_state_key(self, player: int) -> InfoKey: ...
    def returns(self) -> tuple[float, float]: ...

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

`ReducedState.child` only checks/looks up an edge and returns the indicated node view. It never spawns a loop of exact child states. Chance actions are `Action("ABSTRACT_DEAL", k)` at root, k indexing sorted nonempty bucket pairs; runout actions remain `Action("RUNOUT", card)`. Legal actions at chance equal its outcomes' action tuple. Terminal legal/chance actions are empty. `returns` rejects nonterminals; keys reject root/terminal and invalid player requests. The key can be constructed for either valid player at a dealt nonterminal by replacing player/own_bucket; no opponent component is exposed.

## 5. Probability, transition, and observation semantics

For exact world w=(h,g), compute raw weight r_w=f_h*f_g and total Z=sum r_w using Fraction. Root pair mass M_b=sum_(w in b) r_w/Z. Root child b carries q_b(w)=(r_w/Z)/M_b. All retained masses are strictly positive; all relevant sums equal one EXACTLY before float conversion.

At public revealed prefix s, let R_w(s) be the world's legal full runouts beginning with s. Its next-card law is

`p_w(c | s) = |R_w(s+c)| / |R_w(s)|`.

For a belief q, the observable chance outcome mass is `P(c)=sum_w q(w)*p_w(c|s)`. The child belief contains only positive terms with `q'(w)=q(w)*p_w(c|s)/P(c)`. The child's members advance to that exact public card. Never pool `(turn,river)` as a hidden joint choice when turn betting is available, and never expose the selected world in the chance action. Do not average each world's next-card law uniformly without q, and do not take the ratio of pooled raw sequence counts: worlds can have different sequence denominators.

At a player action, every member has the same ordered legal-action tuple, actor, and public next frame. Apply the public action without changing q. This is valid because all members of a fixed pair use the same bucket policy at this public history; its likelihood cancels within the pair, even at zero-reach counterfactual histories. It would be wrong to apply this fixed belief law while allowing own-hand-dependent policies INSIDE a bucket. Inference between different hidden opponent buckets remains the solver's ordinary chance/opponent reach weighting across nodes sharing an infoset. No policy-dependent belief enters the information key.

For v1 exact twins, the certificate makes the per-world public chance kernels identical within a bucket pair, so posterior relative weights in that pair actually remain unchanged along surviving prefixes. Still implement/validate the formula above from exact counts. Share one immutable belief per `(pair, revealed_prefix)` across all betting histories; never replicate a world array at every betting node. Showdown distributions are precomputed at final prefixes. This also cleanly separates physical tree reduction from the number of exact latent deals scanned once.

Structural consistency is established without materializing D exact subtrees:

1. Every implicit exact member is `(shared PublicFrame, World.deal, shared config)`. Inspecting current `legal_actions` proves its decision result does not read private_deal. Thus every member has the identical signature by construction, not by selecting a favourable representative.
2. Build one temporary `MultiStreetState` from a real compatible member and the common frame; call source `child(action)` to obtain the next PUBLIC fields. Source betting branches are private-card independent. At public chance, choose a surviving member for the particular card, check it has that card outcome, and use its public transition. Source showdown evaluation may run but its award is not used for aggregation. Project all fields listed in PublicFrame, excluding DEAL. This keeps current refund, all-in, street-close, and pot rules without duplicating a second betting engine.
3. Validate parent and child actors, histories, ledger invariants, legal tuples, next-card sets and prefix advancement. Across all reduced nodes sharing a key, require actor and ORDERED actions equality and the same owner observation/action sequence. Unknown actions, mixed terminal/nonterminal membership, invalid prefix, absent runouts, or inconsistent signatures raise ValueError before solver construction. Do not intersect action sets, drop offending members, pick a representative payoff, or introduce a fallback terminal.
4. Future differential tests reconstruct every member on bounded fixtures and assert these field/signature equalities against source transitions. The compiler is explicitly tied to this supported multistreet version; any subsequent card-dependent rule requires revisiting the structural proof and those tests, not assuming the generic protocol guarantees it.

At a terminal, let C=pot+sum(committed). For each member compute integer P0 award: C for a win, 0 for a loss, C//2 for a tie, and the source fold award for a fold. Set

`u0 = sum_w q(w)*award0(w) - contributed0 - Fraction(initial_dead_pot, 2)`.

Compute u1 independently from complementary integer awards and contributed1, require `u0+u1==0` as Fractions; then return `(float(u0), -float(u0))`. Ledger conservation requires `C = initial_dead_pot + sum(total_contributed)`. This handles odd dead pots/ties and refunds; never infer settlement from equity alone. Precomputed lose/tie/win fractions make terminal computation O(1) per node. Zero-sum is exact internally and maintained at the output pair.

All public float probabilities must be finite, strictly positive for retained edges, <=1, with ordinary sum within 1e-12 of one. Reject overflow/underflow or failed mass checks rather than changing probabilities. Cap chips conservatively at `initial_dead_pot + 2*effective_stack <= 2**40` for this v1 numerical boundary; reject bools and noninteger ledgers. No Fraction is handed directly to existing bounded-tree validation, which accepts only int/float. Record arithmetic semantics and bit cap. Float CFR is still finite precision, not an exact rational equilibrium solver.

## 6. Recall, noninterference, and lift

Use a FIXED private bucket from root through every street. PublicFrame.history retains every prior betting action and every revealed card. A player can reconstruct their entire sequence of own bucket/public observations and own actions from a key. Same key therefore implies the same own observation/action sequence; no forgetting or absent-minded recurrence is possible. No current-street rebucketing that merges distinct former buckets is permitted.

The key contains the acting player's bucket, public fields, player id, constant rule/version digest. It excludes opponent bucket, world IDs, member cards, member probabilities, pair mass, pair index, representative card, and root ABSTRACT_DEAL action. The digest identifies the public configured ranges/policy; it is the SAME digest in every state of that game and conveys no realized private outcome. Different private worlds/opponent buckets at the same public state and same own bucket must give identical keys. Buckets may depend on the publicly configured opponent range, not the realized opposing hand. Pot, contribution, last-raise, and actor fields are genuinely public and fixed by the retained history.

For each exact decision state, reconstruct its source exact key with `information_state_key(player)`, map sorted own cards through the player's certified bucket table, and project its full public frame/history (remove DEAL only). Obtain that abstract key's COMPLETE policy; require identical ordered actions. Populate a new dictionary under the ORIGINAL exact key. If that exact key occurs again, verify the mapped abstract key and policy agree. Missing bucket/policy, differing actions or inconsistent duplicate key is an error, never uniform repair.

Copy the same float values without recomputation into detached per-exact-key maps, and deep-freeze output. Strategically identical certified hands thus have EXACTLY equal values; modifying one returned policy must be impossible and must not alias another mutable dictionary. Opponent-card distinctions cannot change a lifted exact policy. No exact key is overwritten with an abstract key, and different exact keys remain individually addressable.

Full exact-tree materialization is OPTIONAL and separately bounded: first validate the exact root against explicit diagnostic max_nodes/max_depth, then lift and call `nash_conv(exact_root, lifted)`. This gives values AND deviations on the original exact information sets, not just reduced-game exploitability. Do not call complete_strategy on the lifted profile to mask omissions. For a large solve, store reduced strategy plus bucket membership and provide on-demand exact-state policy projection; never traverse the prohibited exact tree as an unconditional final result step. Exact keys supplied from a different config are rejected using canonical config identity before projection.

## 7. Physical bounds, complexity, and engine compatibility

Define physical node_count as the number of root/chance/decision/terminal HISTORY occurrences traversed by `validate_bounded_tree`, counting the root once. It is not number of bucket IDs, infosets, live wrapper objects, unique public boards, or Python allocator calls across iterations. The compiled structure is a tree: no DAG deduplication is used to evade this definition. A reduced node is a single physical betting/chance/terminal expansion; it does not contain a deferred exact-world subtree.

Compile iteratively with a reservation counter. Before allocating each Node/edge child, reject if its depth exceeds max_depth or its reservation would exceed max_abstract_nodes; equality with a cap is allowed. Validate strict positive non-bool limits before scans. For compatibility with existing recursive solver/validator, v1 rejects max_depth>128; deeper support needs an independent iterative engine change. Check max_worlds while enumerating positive compatible pairs; count prospective signature entries before creating tables; check total MemberWeight entries before caching beliefs and bound Fraction sizes after arithmetic. Define the charged signature budget precisely as `2*len(H0)*len(H1)*max(1,len(allowed_runouts))` scalar slots: a blocked/incompatible pair still consumes its full reserved runout slots, and its compatibility check is included in that reservation, not an additional charge. Thus incompatible inputs cannot evade preprocessing limits, and the large fixture charges 17,424 of 20,000 slots. Abort without returning a partial plan.

After freezing the plan, run `validate_bounded_tree(ReducedState(plan), max_nodes=max_abstract_nodes, max_depth=max_depth)` and compare all recorded counts/depths. Do this before constructing CFR, completing a strategy, or starting best response. Ensure compile-time ordered signature/recall/noninterference checks run in addition to the existing validator.

Let D be exact compatible worlds, R declared full runouts, N reduced physical nodes, B bucket pairs and P possible public runout prefixes. Preprocessing uses O(|H0|*|H1|*max(1,R)) signature work, with evaluator memoization reducing repeated seven-card evaluations to O((|H0|+|H1|)*R) valid hand-board evaluations. World/runout metadata costs O(DR). Belief tables cost at most O(DP); their separate entry cap is mandatory. Public tree compilation is O(N) structural transitions plus cached table access, rather than O(D*N) exact member transitions. Terminal tables are reused, not reevaluated per CFR visit. Persistent memory is O(N + DR + DP + signature storage + infosets/actions), all explicitly bounded; fractions have bounded bit lengths.

Each full CFR iteration now traverses the reduced N-node tree twice. collect_infosets, complete_strategy and expected_values also traverse that reduced tree. The existing scalable best-response discovery stores reduced states and uses its dependency algorithm; do not promise it is O(N), since continuation evaluations can revisit subtrees per infoset/action. With the literal 161-node fixture, the complete CFR AND completion AND best-response path is bounded and small. Runtime/memory receipts remain required when implementation exists; node count alone is not a universal runtime theorem.

World records are real retained payload and must be reported separately. The large fixture retains 4,356 latent World records, not 4,356 traversable GameState roots. Reconstructing them at EVERY public history would preserve O(DH) work and fail this design even if a superficial wrapper count were 161. A future test must instrument member-state constructions: O(N) public templates during compile, zero exact member-state constructions during CFR/complete_strategy/reduced best response. Repeated ReducedState views are O(N) visits per traversal and not an exact hidden tree.

No CFR or best_response core change is required for this new finite, perfect-recall GameState. Existing invariants must pass unmodified. MCCFR can operate on the same graph and requires integer seed, same-seed determinism and complete_strategy before metrics; its samples need not match an exact-deal run's RNG path. v1 acceptance uses deterministic vanilla CFR with seed=None. Seed validation stays at the public boundary, including bool rejection (the vanilla CFR class itself is less strict).

## 8. Derived small-game acceptance bounds

For any complete profile x in the SAME finite two-player zero-sum exact game, write v(x)=u0(x), U(x)=BR0(x1), L(x)=-BR1(x0). Define incentives e0(x)=U(x)-v(x), e1(x)=v(x)-L(x). Both are nonnegative and NashConv C(x)=e0(x)+e1(x)=U(x)-L(x). Minimax gives `L(x) <= v* <= U(x)` for the unknown equilibrium value v*. Therefore

`v(x)-v* <= e1(x)` and `v*-v(x) <= e0(x)`.

For the lifted abstract average profile a and independently trained exact-reference profile r:

`|v(a)-v(r)| <= max(e1(a)+e0(r), e0(a)+e1(r)) <= C(a)+C(r)`.

Proof: bound v(a)-v(r) by (v(a)-v*)+(v*-v(r)), then swap a/r. All four incentives and both values are executable outputs of `nash_conv` on the EXACT tree. The reference is a finite-iteration profile, NOT an equilibrium oracle: its incentive/error terms cannot be dropped. Half-NashConv is not the appropriate replacement for C in the loose inequality. No division by a tiny reference error and no monotonicity premise appear.

This inequality is a universal certificate but can be loose/vacuous if both solvers are bad. Fix a separate quality gate BEFORE the future reduced solve: for the small fixture below, both exact-tree C(a) and C(r) must be <=0.02 chips, one percent of its initial pot. Consequently the profile value gap is <=0.04 chips, tightened by the observed incentive expression above. These are chosen accuracy targets in chip units, not measured ratios. Use 1,000 vanilla iterations each; if the reduced run fails, report failure/investigate, not tune the bound to the observed answer. Optional iteration sweep (20,100,500,1000) reports all values/certificates; do not assert per-step monotonicity.

Two additional certificates prevent a value-only test from hiding corruption:

* **Simulation equality for any bucket profile:** multiplying pair root mass, Bayesian chance probabilities and terminal conditional means telescopes to the exact world sum. Public actions have common likelihoods within a pair. Hence `V_reduced(p) = V_exact(lift(p))` in rational arithmetic, even for an otherwise legal lossy bucket grouping. This identity by itself proves neither optimality nor low exact-tree NashConv.
* **v1 lossless-response certificate:** within an exact-signature pair, all public kernels and all member terminal utilities coincide. Root conditional private-type masses factorize. Against a bucket-constant opponent profile, extra own-card distinctions cannot improve response value: replacing an exact type-dependent behavioural response by its conditional realization-plan mixture inside the own bucket preserves outcome value. Recall makes that mixture implementable as a behavioural bucket strategy. Thus both best-response values, and C, agree between the quotient and the exact lifted profile. Uniform fallback at zero own-reach histories is harmless in this existence proof. This is a response-space argument, not just an equality of showdown averages.

A fixed terminal-diameter/simulation statement is also available with explicit hypotheses. For a common exact tree where a surrogate changes ONLY leaf utility, set `delta=max_z |u0(z)-u0_surrogate(z)|`. Every profile value changes by <=delta; each best-response value changes by <=delta; NashConv changes by <=2*delta in zero sum. If each leaf is replaced by a convex member mean in a group of diameter D_z, then delta<=max D_z. This does NOT alone justify restricting private policies or altering chance kernels. To compare a private-type quotient, one additionally needs the identical observable kernels and factorized, payoff-irrelevant hidden-type property used above for the surrogate. With those hypotheses, its lifted equilibrium has exact NashConv <=2*delta; a finite reduced profile adds its reduced NashConv. A diameter-only claim without those hypotheses is rejected. In this v1, every group's aligned terminal diameter is EXACTLY ZERO: delta=0, so there is no abstraction error term, only finite training and numerical error.

Numerical certification: existing metrics use float arithmetic. Future small-fixture tests must also rationalize each returned nonnegative action policy by `Fraction.from_float(p)` followed by exact per-policy normalization; certify the SAME rationalized lifted/reference profiles on an exact Fraction chance/utility replay of the tree. Use the scalable BR's selected actions as candidates, and verify rational counterfactual action sums at EVERY responder infoset in reverse dependency order; choose the rational maximizer if the float tie selection differs. This computes true incentives for the rational replay, permitting the displayed inequality with NO epsilon. It is bounded to 321 nodes, not a normal-form enumeration of every pure strategy. Independently compare ordinary engine values/BR values with this certificate to 1e-10 chips on this fixture. That tolerance is an engineering regression tolerance, not the mathematical theorem. Record actual discrepancies and rational certificate values. Exact Fraction aggregation does not make existing float CFR exact.

Literal small fixture:

* `MultiStreetConfig(version="multistreet-v1", starting_street="flop", starting_board=parse_cards("Ah Kh Qh".split()), initial_dead_pot=2, effective_stack=1, betting_mode="no-limit", wager_targets=(1,), river_betting=True)`.
* P0: `2c 3c`, `2d 3d`; P1: `2s 3s`, `Th 4s`. Every hand weight=1.0. Runouts `(Jh,9h)` and `(Jh,8h)`, in that specified order before canonicalization.
* Four compatible deals, each mass 1/4; P0's two hands form one bucket. P1 no-Th and Th hands are separate buckets, each weight 1/2. Two abstract outcomes, each mass 1/2. Both public rivers are legal in every world and each has conditional mass 1/2 following Jh.
* Exact nodes=321, abstract nodes=161, max depth=12. Limits: max_nodes/max_abstract_nodes=10,000, max_depth=32, diagnostic max_nodes=10,000. Vanilla iterations=1,000, seed=None, all other abstraction limits as declared in AbstractionConfig.
* At either showdown P0 ties no-Th and loses to Th; board supplies A-K-Q-J-(8 or 9) hearts, Th makes the opponent a royal flush. This is not a check-only tree or a game with no private strategic distinction.

Literal blocker-separation companion test: retain that public game, set P0 hands to `2c 3c` and `2d 3d`, and P1 hands to `2c 4s` and `5s 6s`, all weights one. Every legal showdown ties, so all active hands have equal showdown equity. There are THREE compatible deals, each mass 1/3; P0 `2c 3c` blocks P1 `2c 4s` while `2d 3d` does not. Both players' two signatures must remain distinct, and root outcome count must be three, not one. This pins the difference between equity equality and identical strategic information. A runout-blocker companion replaces the two runouts with `(Jh,2c)` and `(Jh,8h)`, uses the original small P1 range, and requires P0's two signatures to separate because their legal observable runout supports differ. Both worlds still have at least one legal runout; no conditioning-away of a positive deal is allowed.

Read-only evidence from the current engine (not an implemented reduced solve): the exact small root preflight returned 321 nodes, 136 terminals, 57 chance nodes, 128 decisions, depth 12. At 1,000 vanilla iterations it returned values `(-0.9993335546875001, 0.9993335546875001)`, BR values `(-0.9993333333333333, 1.0000625)`, incentives `(2.2135416677393494e-07, 0.0007289453125000067)`, NashConv `0.0007291666666667806`. This is a feasibility receipt for the fixed reference budget; it is not the acceptance bound or proof of future implementation correctness.

## 9. Literal large fixture and reproducible counts

Use the SAME public game as the small fixture: flop Ah Kh Qh, ordered runouts Jh 9h and Jh 8h, pot=2, stack=1, no-limit target=(1,), river_betting=True, allstreet automatic natural terminals, vanilla iterations=1,000, seed=None. Public actions reachable on each street are CHECK and RAISE-to-1 while unopened, FOLD or CALL-to-1 facing the raise; after call stacks are exhausted and remaining cards run out. CHECK-CHECK preserves stacks for the next street. No other target/action is configured.

P0 range is **all unordered two-card combinations** of the literal 12-card set
`{2c,3c,4c,5c,6c,7c,2d,3d,4d,5d,6d,7d}`.
P1 range is all unordered two-card combinations of
`{2s,3s,4s,5s,6s,7s,2h,3h,4h,5h,6h,Th}`.
All 132 listed-by-rule hands have weight 1.0. These are explicit finite sets, not a 169-class shorthand. Card pools are disjoint and disjoint from board/runouts. Each player has C(12,2)=66 hands; EVERY ordered player-pair is compatible: D=66*66=4,356, each root mass 1/4,356. No guessed blocker subtraction is involved.

Exact bucket membership is fully specified by:

* P0 bucket: all 66 hands; all have the same compatibility and payoff row.
* P1 no-Th bucket: all C(11,2)=55 hands not containing Th, all tie P0 at both final boards.
* P1 Th bucket: `{Th,x}` for EACH of the other eleven listed P1 cards, all beat P0 at both final boards.

Numerical bucket IDs are assigned by sorted signatures (P1 tie codes sort before win codes). Thus root outcome k=0 is `(P0_bucket0,P1_bucket0)` with 3,630 worlds and exact mass 5/6; k=1 is `(0,1)` with 726 worlds and mass 1/6. After Jh, RUNOUT 8h and 9h each have probability 1/2. These 4,356 worlds compress to two physical deal branches and four prefix beliefs per pair (empty, Jh, Jh8h, Jh9h): eight Belief records with 17,424 total member entries if all prefix weights are stored literally. Sharing identical weight tuples is permitted but not required to meet the 20,000-entry cap.

Counts were derived by running the following READ-ONLY source probe with bytecode disabled. It is also a reproducible command for a reviewer; it creates no implementation files:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
from itertools import combinations
from poker_solver.cards import parse_cards
from poker_solver.equity import WeightedCombo
from poker_solver.multistreet import MultiStreetConfig, create_root
from poker_solver.bounded_tree import validate_bounded_tree
from poker_solver.evaluator import evaluate_seven

p0 = parse_cards('2c 3c 4c 5c 6c 7c 2d 3d 4d 5d 6d 7d'.split())
p1 = parse_cards('2s 3s 4s 5s 6s 7s 2h 3h 4h 5h 6h Th'.split())
board = parse_cards('Ah Kh Qh'.split())
runs = tuple(parse_cards(s.split()) for s in ('Jh 9h', 'Jh 8h'))
a = tuple(WeightedCombo(c) for c in combinations(p0, 2))
b = tuple(WeightedCombo(c) for c in combinations(p1, 2))
D = sum(not set(c.cards).intersection(d.cards) for c in a for d in b)
bucket_sizes = []
for own, opp in ((a, b), (b, a)):
    groups = {}
    for c in own:
        sig = tuple(tuple(
            (evaluate_seven(c.cards+board+r) > evaluate_seven(d.cards+board+r))
            - (evaluate_seven(c.cards+board+r) < evaluate_seven(d.cards+board+r))
            for r in runs) for d in opp)
        groups.setdefault(sig, []).append(c)
    bucket_sizes.append(sorted(map(len, groups.values())))
# All worlds have exactly the same public tree; use one compatible world.
cfg = MultiStreetConfig('multistreet-v1', 'flop', board, 2, 1,
                       (a[0],), (b[0],), runs, 'no-limit', (1,), True)
s = validate_bounded_tree(create_root(cfg), max_nodes=10_000, max_depth=32)
print(len(a), len(b), D, bucket_sizes)
print(s)
print('exact', 1+D*(s.node_count-1), 'abstract', 1+2*(s.node_count-1))
PY
```

Observed output: `66 66 4356 [[66], [11, 55]]`; single-world stats `node_count=81, max_depth_reached=12, terminal_count=34, chance_count=15, decision_count=32`. Output counts: exact=348481; abstract=161. The signature shortcut in this probe is valid only for these explicitly disjoint card pools/runouts; the production signature must include blocked cells as in section 3.

Analytic extension: the single-world tree consists of root plus 80 history nodes. All worlds have identical public branching, including both runouts, regardless of win/tie result. Exact N=1+4356*80=348,481; reduced N=1+2*80=161. Exact terminals=148,104; chance=1+4356*14=60,985; decisions=139,392. Reduced terminals=68; chance=29; decisions=64. Both max depths=12. This is a same-game comparison, not a different action tree or a suppressed runout set.

Future large acceptance must run the COMPLETE reduced public solve (training, complete_strategy, reduced nash_conv, frozen result serialization) under max_abstract_nodes=10,000 and max_depth=32. The exact allstreet config with max_nodes=10,000 must raise the existing physical-bound error before training. Exact full-tree evaluation is disabled for this solve and marked not requested; optional separate diagnostics with their own increased cap are not part of the bounded solve. Report both actual reduced preflight stats and the analytic exact count/certificate, labelled derived rather than an executed full exact traversal.

## 10. Public configuration and truthful results

Add `abstraction.py` for config/signatures/immutable plan/compiler/state/lift, and a small `abstraction_solve.py` facade. The state module imports model/multistreet/evaluator/equity/bounded_tree, never api/allstreet. The solve facade imports cfr, best_response and api.complete_strategy. Allstreet translation is called locally by the facade; do not add an eager api->facade->allstreet->api import cycle.

Literal public interface:

```python
from poker_solver.allstreet import AllStreetPostflopConfig

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
    strategy: Mapping[InfoKey, Mapping[Action, float]] # reduced keys
    lifted_strategy: Mapping[InfoKey, Mapping[Action, float]] | None
    plan: ReducedPlan
    approximate: bool
    abstraction_lossless: bool
    metric_scope: Literal["reduced-game"]
    exact_evaluation_status: Literal["not-requested", "completed"]
    provenance: str
    metadata: Mapping[str, object]

def solve_multistreet_abstracted(
    config: MultiStreetConfig, abstraction: AbstractionConfig, *,
    algorithm: Literal["vanilla-cfr", "external-sampling-mccfr"],
    iterations: int, seed: int | None = None,
    exact_evaluation: ExactEvaluationConfig | None = None,
) -> AbstractSolveResult: ...

def solve_allstreet_abstracted(
    config: AllStreetPostflopConfig, abstraction: AbstractionConfig, *,
    algorithm: Literal["vanilla-cfr", "external-sampling-mccfr"],
    iterations: int, seed: int | None = None,
    exact_evaluation: ExactEvaluationConfig | None = None,
) -> AbstractSolveResult: ...
```

Allstreet facade must require `config.max_nodes == abstraction.max_abstract_nodes` and `config.max_depth == abstraction.max_depth`; ambiguous dual bounds fail instead of silently overriding a caller cap. Translate exactly as create_allstreet_root does, but invoke the reduced compiler BEFORE exact-tree preflight. If explicitly requested exact diagnostics exceed their separate bound, fail the request, not return an unlabelled missing diagnostic. No diagnostics are requested by default. Existing exact functions/result classes stay semantically unchanged.

Add a distinct strict v4 operation `solve-allstreet-abstracted`, using the existing allstreet base payload/card conventions plus REQUIRED `abstraction` and optional `exact_evaluation` objects. Reuse underlying strict scalar/list parsers, not the existing exact-solving branch. The abstraction object contains version and all six limit fields from its literal dataclass; reject unknown/missing fields and bool numeric fields. Required max_nodes/max_depth in the base payload must agree as above. exact_evaluation is null/absent or exactly `{max_nodes,max_depth}`. Preserve all existing operations and strict unknown-field behavior.

Return explicitly named `reduced_nashconv`, `reduced_exploitability`, `exact_nashconv` (null unless evaluated), and `exact_evaluation_status`. `strategy_scope="abstract-bucket-public-history"`; optional lifted strategy is labelled exact-key scope. Do not reuse an unqualified existing `nashconv` field for a different metric scope. Serialize keys as structured records (version/digest/player/bucket/public fields), actions as kind/amount records, membership as exact integer-card pairs, rational masses as numerator/denominator strings, sorted deterministically. Do not dump the internal plan/world arrays into ordinary JSON results. Python result's plan supports on-demand projection; JSON provides the policy/membership/rule digest sufficient to identify that projection. Result construction copies and recursively freezes strategy/metadata; JSON serialization creates detached lists/dicts and rejects nonfinite numbers.

Recommended metadata: policy/version and canonical config/bucket digest; original and active combo counts; zero-weight/unsupported hand counts; exact compatible-world count; nonempty pair count and pair masses; reduced physical stats and bounds; world/signature/member-entry counts and caps; largest bucket sizes; exact-signature certificate and terminal diameter=0; `abstraction_lossless=True`, `lossy_merges=0`; `chance_arithmetic="Fraction of input binary floats; configured per-world runouts"`; iterations, algorithm, seed; numeric boundary checks; source game version; exact diagnostics scope/status; any exact count labelled `derived` or `preflight-observed`.

Set new result `approximate=True` because the delivered finite-iteration strategy is not claimed to be an exact Nash equilibrium; distinguish `abstraction_lossless=True` and `model_error_bound=0`. Provenance: “finite-iteration solve of a certified exact-signature reduced configured multistreet game; exact rational aggregation, float CFR; exact-tree diagnostics [completed/not requested]”. Existing allstreet's approximate=False convention remains unchanged for its old exact-tree result. Never claim an unrestricted real-poker solution, unconstrained public deck, or measured exact-tree exploitability when only the quotient metric was run. The lossless-response theorem may justify a certified equality, but label it as a certificate, not an executed exact traversal.

## 11. Dependency-safe RED-first implementation batches

These are future implementation instructions, not actions taken in this design task. After each batch, follow the mission's independent fresh non-author audit gate and run the focused tests plus the current full 817-test baseline with additive tests. No next batch starts before the prior batch's receipt is accepted. This document does not claim those audits or executions occurred.

1. **Policy/config and arithmetic RED.** Add failing tests for exact labelled signatures, weight conversion, order invariance, duplicate/zero/blocked input handling, Fraction limits, one small and one large membership table. Implement only immutable config/canonicalization/signature construction. Counterexample: add a runout containing one of two equal-equity hands' cards and require separation; test swapped win/loss patterns with identical average equity also remain separate. Add zero-legal-runout failure without silent root conditioning.
2. **Beliefs/public reduction RED.** Add failing probability/posterior, physical-node cap/depth, per-member action-transition and settlement tests. Then implement world/belief tables, public-template compiler and ReducedState. Test odd dead pots, ties, folds, refunds, all-ins, pot-limit and river_betting False/True. Test generalized belief arithmetic with q=(1/3,2/3), next-card probabilities (1,1/2): aggregate=2/3 and posterior=(1/2,1/2). Production exact signatures keep such kernel-distinct members separate; the arithmetic unit test must not bypass that constructor rule. Reject actor/action ordering/public transition corruption and terminal zero-sum failure. Require reduced large stats 161/68/29/64/depth12 and strict cap boundary 160 fails/161 succeeds.
3. **Recall/solver/lift RED.** Add failing opponent-bucket/member-weight/noninterference tests, retained public-history/own-action recall checks, and deliberately illegal rebucketing fixture. Implement projection and solver plumbing only after state tests pass. Assert identical lifted policies for every P0 twin and every within-class P1 hand, no alias mutation, no hidden DEAL leakage, complete coverage of every reachable exact key, unknown-state and missing-policy errors. Test arbitrary nonuniform complete bucket profiles for rational simulation equality on all terminals, not only a trained profile. On a truly tiny river subfixture compare scalable and exhaustive best responses for independent infoset correctness.
4. **Acceptance certificates RED.** Pin the literal small reference/abstract training budgets and <=0.02 exact-tree NC gates; implement the rational evaluation/BR certificate in bounded test helpers, prove/check the displayed incentive bound without epsilon, compare float diagnostics to it, and require terminal diameter=0. Full exact-tree lifted evaluation must be exercised here. Large complete solve must fit the cap; exact same-game preflight must reject it. Instrument public-template constructions and assert CFR/completion/BR never construct exact-world GameStates. Record startup sizes and timings; no speedup ratio assertion based on a guessed cost model. Determinism checks cover input permutations, repeated vanilla solve, repeated seed for MCCFR, serialized membership and probabilities.
5. **API/result integration RED.** Add new operation/config/result tests, unsupported-operation/game failures, explicit metric-scope/null diagnostic behavior, exact diagnostic cap failure, algorithm/seed mismatch, dual-bound mismatch, deep freeze/response isolation, and deterministic structured serialization. Then wire the facade/dispatcher and public exports without altering old exact API semantics. Existing S1/S2/S3 CLI/examples/export/API tests and all 817 baseline tests must remain green. Documentation of the physical and preprocessing caps is part of this batch.

## 12. Limits and remaining verification

There is no implementation blocker in the recommended scope: blocker_count=0. Remaining work is implementation and audit, not an unresolved choice to defer physical reduction. The following limitations must remain visible:

* Exact row signatures are conservative and can require one bucket per hand. General unrestricted-deck ranges may exceed preprocessing or node caps; fail with actual counts/limits. This v1 proves S4 on declared finite fixtures, not arbitrary million-world games.
* The large fixture intentionally has strong equivalences, shallow stacks and two declared runouts. It is a legitimate 4,356-world allstreet betting game with a private winning/tie distinction, not evidence of full-stack unrestricted-deck performance. More realistic fixtures can be added after this acceptance, without substituting guessed counts for the literal gate.
* A complete game automorphism search is not supplied. The operational identity certificate is full equality of labelled strategic continuations, not equity/rank/category or informal suit similarity. It guarantees exact equality for the fixture's strategically identical hands and every hand pair certified by this rule.
* Compiled world/belief payload can dominate memory before CFR. Its bounded, reported allocation and shared public transition design are essential; rebuilding member subtrees would violate the v1 contract.
* Existing recursive traversal and repeated best-response continuations remain; max_depth<=128 and finite physical caps are explicit limitations, not a claim of linear total solve cost.
* Float training can differ slightly between the original and reduced engines, including chance summation order and finite-iteration average strategies. The rational certificate establishes value/error bounds for the delivered profiles; no bitwise equality of separately trained exact/reduced policies is required. Bitwise equality within a lifted bucket IS required.
* The reported counts/signature sizes and small exact-reference solve were executed against current source with bytecode disabled. No reduced solver was implemented or run, no source/tests/rejected report were edited, and no candidate suite pass or measured reduced runtime is claimed. The final heartbeat hashes this completed design, not a proposed implementation.
