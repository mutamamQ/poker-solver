# 02 — Solver adapter, cache and action-value evaluator

Status: implementation design, not implemented practice code.
Scope: proposed `practice/adapter.py`, `cache.py`, `evaluate.py`; source and tests inspected read-only.
Authority: `PRACTICE_MODE_DESIGN.md` §§1–5. Aligns with reports 01 and 03; disagreements and extensions below require parent reconciliation.
Branch observed: `feat/practice-mode`. Existing changes in PROGRESS.md, STATE.txt and research/practice-mode/ were present; this investigation does not own them.

## 1. Proposed interface and responsibility boundaries

These practice signatures are proposals; the backend signatures in §2 are verified source surfaces.

```python
class SolverAdapter:
    def solve(self, spot: PracticeSpot) -> SolvedSpot: ...

# Internal resolved artifact, defensively frozen:
# root, complete typed profile, decision, provenance, backend diagnostics.

def locate_decision(root: GameState, spot: PracticeSpot) -> HeroDecision: ...
def action_values(root: GameState, profile: Strategy, hero: int,
                  target_key: InfoKey) -> tuple[Mapping[Action, float], float]: ...

class SolveCache:
    def get(self, params_hash: str) -> SolvedSpot | None: ...
    def put(self, params_hash: str, solved: SolvedSpot) -> None: ...
```

`solve` validates the spot, resolves exact backend parameters, constructs/preflights the tree, checks a compatible cache entry, obtains the runtime average profile on a miss, evaluates the hero decision and range view, then returns a frozen SolvedSpot. Cache access does not bypass validation. No literal strategy or Q tables are permitted.

Use report 03's HeroDecision record, with DecisionPoint an alias pending parent reconciliation: hero_seat, hero_hand, action_history, info_key, legal_actions, pot_at_decision, kuhn_card. Preserve actual Action objects and the actual typed InfoKey internally. Copy policies to nested MappingProxyType and sequences to tuples.

Return spot, provenance, decision, strategy at decision.info_key, action_values, range_strategy, optimal_action and optimal_size as required by the authoritative model. Match report 01: optimal_action is the highest-probability average-policy action, ties by legal-action order; the scorer separately identifies the highest-Q action. optimal_size is amount for bet/RAISE, otherwise None. Do not confuse a modal action with a best response at low iterations.

## 2. Verified solver signatures and routing

Source references: model.py:12–36; kuhn.py:63–88; river.py:19–25,117–154; allstreet.py:32–44,177–275; multistreet.py:19–32,439–500; api_v4.py:284–490; nplayer_preflop.py:240–253,952–1136.

Common protocol: current_player() -> int; legal_actions() -> tuple[Action,...]; chance_outcomes() -> tuple[tuple[Action,float],...]; child(action: Action) -> GameState; information_state_key(player: int) -> InfoKey; returns() -> tuple[float,...]. InfoKey is Hashable, not a string schema. CHANCE=-1, TERMINAL=-2. Action(kind: str, amount: int=0) is frozen; preserve amount=0 for unsized actions.

### 2.1 Kuhn

Verified `kuhn_root() -> KuhnState`; `CFRSolver(root).train(iterations: int) -> dict[InfoKey, dict[Action,float]]`. Use vanilla-cfr with seed=None. Compute diagnostics with `best_response.nash_conv(root, profile)` and its nash_conv field; expected_values is also available.

Report 03 proposes hero_hand=None and backend_extra.kuhn_card in J/Q/K, rather than pretending a Kuhn card is a Hold'em pair. Adopt only after parent reconciliation. Require heads-up/preflop, board/ranges empty, pot=2, stacks=(1,1), bet_sizes=(1,). Those fields describe the fixed game; they do not parameterize kuhn_root. A Kuhn BET is Action('bet',0), not Action('bet',1). Legal public histories are resolved through the tree.

### 2.2 River

Verified `RiverConfig(board, pot, stack, bet, range0, range1)` with fields board: tuple[int,int,int,int,int], pot: float, stack: int, bet: int and tuple[equity.WeightedCombo,...] ranges. Verified `river_root(config: RiverConfig) -> RiverState`.

Mapping: spot.board -> board; spot.pot -> pot; equal spot.stacks[0:2] -> stack; the single spot.bet_sizes[0] -> bet; sanitized spot.ranges[0/1] -> range0/1. Require heads-up/river, five cards, equal positive stacks and exactly one positive bet <= stack. hero_seat does not reorder seats: P0 is OOP and acts first. action_history selects a decision after dealing; it is not applied by modifying root configuration.

Train CFRSolver from a fresh root for exactly spot.solve.iterations. Reject MCCFR and non-null seed on this route. Preserve average probabilities without clipping/renormalizing. Compute nash_conv after training and record diagnostic time in wall_time_s.

Important limitation: once stack >= bet, RiverState's actions/payoffs do not depend on stack. Changing stack alone changes identity but need not change strategy or Q. A test demanding universal river stack sensitivity would be incorrect; §8 supplies the necessary acceptance distinction.

### 2.3 Allstreet flop

Verified constructor fields:

```python
AllStreetPostflopConfig(
    version, starting_board, initial_dead_pot, effective_stack,
    player0_combos, player1_combos, allowed_runouts, betting_mode,
    wager_targets, max_nodes=100_000, max_depth=512,
)
create_allstreet_root(config: AllStreetPostflopConfig)
solve_allstreet_postflop(
    config: AllStreetPostflopConfig, *,
    algorithm: Literal['vanilla-cfr', 'external-sampling-mccfr'],
    iterations: int, seed: int | None = None,
) -> AllStreetSolveResult
```

Map spot.board of length three -> starting_board; spot.pot -> initial_dead_pot, requiring an integer-valued positive pot and an explicit checked conversion; equal stacks -> effective_stack; ranges -> player0_combos/player1_combos; bet_sizes -> wager_targets. backend_extra supplies version='allstreet-postflop-v1', allowed_runouts, betting_mode, max_nodes, max_depth. Resolve every default before hashing/recording parameters; do not silently round a fractional pot.

Use result.strategy and result.nash_conv. Reconstruct the identical root with create_allstreet_root for lookup/evaluation. The facade validates node/depth bounds, trains, completes the profile, computes exploitability and returns diagnostics including node_count and max_depth_reached. Vanilla requires seed=None; external-sampling-mccfr requires a strict integer seed.

Source caveat: allstreet calls api.complete_strategy(root,strategy), which inserts uniform policies for MCCFR infosets not visited during sampling. This is backend-owned completion, not equilibrium evidence. The adapter must not invent any additional fallback. Provenance must disclose this completion behavior for MCCFR; a stricter no-unvisited-policy interpretation requires parent reconciliation or initially offering vanilla only. Missing policies after the facade still fail closed.

### 2.4 Turn starts — PARTIAL at the practice route

MultiStreetConfig genuinely supports starting_street='turn', a four-card starting_board, and allowed_runouts containing one river card each. Its exact fields are version, starting_street, starting_board, initial_dead_pot, effective_stack, player0_combos, player1_combos, allowed_runouts, betting_mode, wager_targets, river_betting=False. `multistreet.create_root(config: MultiStreetConfig) -> MultiStreetState` constructs that tree.

However, AllStreetPostflopConfig requires exactly three starting cards, and create_allstreet_root hardcodes starting_street='flop' and river_betting=True. solve_allstreet_postflop also reports a flop start. Thus the named allstreet facade does NOT support direct turn starts despite the underlying engine supporting them. Do not insert a fourth card into its three-card constructor or relabel a flop solve as a turn solve.

Initial `backend='allstreet', street='turn'` must raise ValueError('turn start unsupported by allstreet facade'). Capability: PARTIAL, with underlying support verified but practice routing absent. Proposed parent-approved extension: construct MultiStreetConfig(version='multistreet-v1', starting_street='turn', starting_board=spot.board, river_betting=True, remaining mapped fields), run bounded validation plus CFR/MCCFR and diagnostics explicitly, and record the different entrypoint. Never silently switch entrypoints under unchanged canonical extras. Flop-derived turn decisions would additionally need explicit observed-board/start-board metadata, missing from the current spot contract.

### 2.5 Three-player preflop through API v4

Verified `dispatch_v4(data: dict[str,Any]) -> dict[str,Any]`. Call with integer version 4, operation='solve-nplayer-preflop', flat payload. The payload has exactly version, num_players, button, starting_stacks, forced_posts, straddle_variant, ranges, sizing_rules, max_raises, max_deals, max_nodes, short_all_in_reopens, continuation, algorithm, iterations, seed, include_deviation_certificate, max_pure_strategies.

Map game_type='3-max' -> num_players=3; stacks -> starting_stacks; ranges -> lists of {cards:[c0,c1], weight:w}; solve -> algorithm/iterations/seed. Require board empty/preflop. Extra fields supply version='nplayer-preflop-v1', button, forced_posts, straddle_variant, sizing_rules, max_raises, max_deals, max_nodes, short_all_in_reopens, continuation, include_deviation_certificate and max_pure_strategies. Generation metadata such as catalog_seed/cell_seed is retained in spot canonical identity but stripped from the payload.

There is no arbitrary initial-dead-pot payload field. Require spot.pot to equal the sum of forced-post amounts at root; reject mismatch instead of ignoring the requested pot. bet_sizes is descriptive sizing metadata: verify agreement with actual resolved legal targets at the drill, not a replacement for sizing_rules. Action amounts for CALL/RAISE are cumulative targets, not incremental payments.

forced_posts records contain seat/kind/amount. sizing_rules records contain position/raise_count/cold_callers/relation/expressions. Expressions use the exact parser schema in api_v4.py: unit plus value for big-blinds/pot-percent/previous-bet-multiple, unit alone for all-in, or unit/streets/scale for geometric. Do not synthesize unspecified rules.

continuation contains kind/provenance/source/entries; showdown-ranks additionally requires odd_chip_order. Each showdown entry is {deal:[hand per seat], ranks:[rank per seat]}. Derive ranks using the production hand evaluator on the sampled continuation board as report 03 specifies. This is a finite sampled-showdown continuation, not full-deck preflop GTO. Require coverage of all compatible joint deals. Reject arbitrary manually supplied answer/payoff tables for the catalog.

Verified typed config constructor: NPlayerPreflopConfig(version,num_players,button,starting_stacks,forced_posts,straddle_variant,ranges,sizing_rules,max_raises,max_deals,max_nodes,short_all_in_reopens,continuation). Typed ranges use preflop.WeightedCombo, distinct from equity.WeightedCombo; mirror the dispatcher's conversion, not direct substitution.

Verified `create_nplayer_preflop_root(config: NPlayerPreflopConfig) -> NPlayerPreflopState` and `solve_nplayer_preflop(config: NPlayerPreflopConfig, *, algorithm: str, iterations: int, include_deviation_certificate: bool=False, max_pure_strategies: int=100_000) -> NPlayerPreflopSolveResult`. Only vanilla-cfr and seed=null are accepted by dispatch.

The dispatcher returns string-labeled keys/actions, not typed profile objects. Construct the identical typed root/config for walking. Enumerate real infosets and legal Actions, construct labels with exactly str(key)/str(action), detect label collisions, require exact returned key/action coverage, and attach returned probabilities to those real objects by exact equality. This is a checked transport join, NOT parsing a string to recover an infoset. No eval, literal_eval, splitting or tuple-position extraction from labels. Use a dedicated n-player tree collector because chance legal_actions() is empty: expand chance_outcomes() at CHANCE.

Three-player result has no nash_conv field; use provenance.nash_conv=None, never 0. Certificate total_incentive is a separately labeled diagnostic when requested. The source explicitly records converged=False and no convergence guarantee. Disable certificates for the bounded interactive default unless explicitly requested.

## 3. Authoritative hero decision lookup

Walk root chance outcomes to dealt states, preserving probability and selecting the hero's actual private cards: KuhnState.deal[hero] is a symbol; RiverState.deal[hero] is a pair; MultiStreetState.private_deal[hero] and NPlayerPreflopState.private_deal[hero] are pairs. Compare canonical sorted Hold'em pairs, not deal indices. Do not choose one villain hand and call it the infoset.

For each compatible hero deal, replay spot.action_history by exact Action membership in legal_actions(), checking the actor each step. Private DEAL actions are not public history. If chance arises between public actions, branch on chance_outcomes; observed runouts must be constrained by explicit board metadata, not arbitrary selection. Initial supported flop/river/preflop drill histories do not require an unspecified intermediate board.

At the end require current_player()==hero_seat, nonempty actions, matching target street/board and real hero cards. Call information_state_key(hero_seat) only after that actor check; multistreet and nplayer methods do not themselves require the player to be acting. Collect every compatible state, require one unique typed key and identical ordered actions/pot. Zero matches, multiple keys, terminal histories or wrong actor fail closed. Replay semantic validation across compatible deals, not only the first one.

Actual key structures, returned by source rather than reconstructed by the adapter:

- Kuhn: ('kuhn-v1', player, deal[player], history).
- River: ('river-v1', player, own, config.board, history, config.pot, config.stack, config.bet).
- Allstreet's MultiStreetState: (config.version, player, sorted own_cards, board, history excluding DEAL, pot, committed, remaining, betting_mode). RUNOUT remains in public_history.
- N-player preflop: (config.version, n, player, own_cards, button, starting_stacks, forced_posts, straddle_variant, sizing_identity, pot, street_committed, total_contributed, remaining, folded, pending, can_raise, last_raise_increment, raise_count, acting_player, history, continuation.kind, continuation.source, continuation.provenance). sizing_identity contains each rule's position/raise_count/cold_callers/relation and expression identities. history contains NPlayerPreflopPublicAction records with actor and Action.

Pot at decision comes from walked state: Kuhn 2 plus outstanding bets; river config.pot plus prior bet amounts; multistreet state.pot + sum(state.committed); nplayer state.pot alone because it already includes posts and subsequent payments. Do not double-count nplayer street_committed.

Whole-range UI view: repeat the same public-line walk for each compatible positive-weight hero hand, read its real solved policy, and use a deterministic formatted hand label for display only. Preserve unreachable-hand status explicitly rather than fabricating Q; no policy string is an internal lookup identifier. The generic range_table helper is not a river/IP-history drop-in, as report 03 notes.

## 4. Exact hero-perspective Q evaluation

For hero i and target infoset I, define w(h)=chance_reach(h) times the product of solved action probabilities for every acting opponent before h. Exclude hero's own reach. Root deal probabilities already encode compatible range-weight products; never multiply ranges again. Future public-card chance follows the backend's conditional probabilities.

$$M(I)=\sum_{h\in I}w(h),\qquad Q(a)=\frac{\sum_{h\in I}w(h)V_i^{\sigma^*}(\operatorname{child}(h,a))}{M(I)}.$$

Terminal returns()[i] supplies chip EV including backend contribution/dead-pot accounting. This is not equity, total pot award, a one-step best response, or a negated P0 value for every seat. After the forced action, ALL players including hero follow the solved average profile.

Implementation pseudocode; checked_policy validates exact legal-action coverage, finite nonnegative probabilities and sum within 1e-9 without repairing them:

```python
def value(state):
    actor = state.current_player()
    if actor == TERMINAL:
        return checked_terminal_returns(state)[hero]
    if actor == CHANCE:
        return fsum(p * value(state.child(a))
                    for a, p in checked_chance_outcomes(state))
    policy = checked_policy(state, profile)
    return fsum(policy[a] * value(state.child(a))
                for a in state.legal_actions() if policy[a] > 0)

def walk(state, weight):
    if weight == 0:
        return
    actor = state.current_player()
    if actor == TERMINAL:
        return
    if actor == CHANCE:
        for action, probability in checked_chance_outcomes(state):
            walk(state.child(action), weight * probability)
        return
    key = state.information_state_key(actor)
    actions = state.legal_actions()
    if actor == hero and key == target_key:
        require_same_actions(actions)
        mass_terms.append(weight)
        for action in actions:
            numerator_terms[action].append(weight * value(state.child(action)))
        return
    policy = checked_policy(state, profile)
    for action in actions:
        multiplier = 1.0 if actor == hero else policy[action]
        walk(state.child(action), weight * multiplier)

walk(root, 1.0)
mass = fsum(mass_terms)
if not isfinite(mass) or mass <= 0:
    raise ValueError('hero infoset has zero counterfactual reach')
Q = MappingProxyType({a: fsum(numerator_terms[a]) / mass for a in actions_at_I})
```

Use explicit accumulator initialization and checked finite outputs in production; the above is algorithm pseudocode, not implemented code. Report 01's hero validation of 0/1 must generalize to range(num_players) for this evaluator; do not call other_player for three players. Opponent reach is a product across both villains.

Hero policy probability zero earlier on the public line does not invalidate counterfactual Q. Zero opponent/chance reach does. Keep any optional hero-actual-reach diagnostic separate from M; adding that field to HeroDecision requires a coordinated contract change.

Complexity: O(N_prefix + sum_h N_descendants(h)) visited edges with O(depth) recursion plus accumulators. In a genuine tree with perfect recall and non-repeated target infoset along a path, target-member descendant subtrees are disjoint, so one target is O(N), not automatically |A| full-tree passes. A general repeated/reconvergent traversal can incur additional repeated work; never memoize only by InfoKey because hidden villain cards affect payoff. Whole-range repeated evaluation is O(HN) for H hands; a single pass aggregating by typed target key can reduce duplication. Enforce existing finite-tree bounds and recursion-depth safety.

Compute solver_mix_q from the unmodified decision policy and Q; best_q=max(Q); solver_self_loss=best_q-solver_mix_q. Scorer 01 owns grades, snapping, normalization and numerical clamps. No EV interpolation for off-tree sizes.

## 5. Solve provenance and canonical identity

Proposed frozen SolveProvenance fields: backend:str; entrypoint:str; params: immutable mapping of the full canonical spot; params_hash:str; algorithm:str; iterations:int; seed:int|None; nash_conv:float|None; wall_time_s:float; solver_package_version:str. Additional explicit fields recommended: resolved_solver_params, evaluator_version, cache_schema, solver_build_identity, diagnostics. These additions require coordination with spot.py/service serialization.

params is report 03's canonical PracticeSpot, including hand/history, sanitized ranges, pot/stacks, sizes, solve settings, typed extras and their resolved defaults. Exclude spot_id, timing, strategy, Q and derived hash. resolved_solver_params separately records the actual typed config or exact v4 envelope; it must be deterministically derived from params, never silently contain un-hashed solve-changing defaults.

```python
canonical_bytes = json.dumps(
    spot.canonical(), sort_keys=True, separators=(',', ':'),
    ensure_ascii=True, allow_nan=False,
).encode('utf-8')
params_hash = hashlib.sha256(canonical_bytes).hexdigest()
```

Do not replace report 03's full-spot hash with a game-only hash: different hero/history drills are intentionally separate identities. Normalize declared float fields before canonical serialization, preserve chronological board/history ordering and canonical-sort hand/range records. Reject duplicate JSON keys and non-JSON extras.

Read package version using importlib.metadata.version('poker-solver'); pyproject.toml declares 0.1.0, but query the actual installation for provenance rather than assuming that constant. On PackageNotFoundError, fail closed unless an explicitly verified source-version mechanism is supplied. Package version alone is insufficient when source changes without a release; disk compatibility should additionally compare a verified build/revision identity or digest of solver sources, supplied/read rather than guessed.

wall_time_s measures miss-time solve plus required tree validation/diagnostics/evaluation, excludes cache-hit latency, and is retained unchanged on a hit. Expose cache-hit status separately. Record None for unsupported nash_conv, not a fabricated convergence value.

## 6. Content-addressed cache

Default process-local dictionary keyed by the full 64-character params_hash, storing defensively frozen SolvedSpot. put verifies supplied key equals solved.spot.params_hash() and solved.provenance.params_hash. get verifies canonical params equality, package/build/evaluator/schema compatibility and finite complete result invariants before reuse. A changed solver implementation cannot reuse an old artifact merely because package version stayed 0.1.0.

Optional explicit cache directory: use <params_hash>.json, JSON only, no pickle or executable deserialization. Persist canonical params, provenance, structured decision metadata, legal-action records, hero policy/Q and range view; do not persist a GameState or require reconstructing InfoKeys from string syntax. On load rebuild the identical typed root/decision and bind structured actions to its actual legal set. If full profiles are persisted, use the same exact tree-enumeration transport join as §2.5, with collision and coverage checks.

Writes use a same-directory temporary file, flush/fsync as appropriate, atomic os.replace, and cleanup on failure; serialize after all validation. Concurrent misses may duplicate solves but must never expose partial writes. Optional locking is an optimization, not permission to serve incomplete data. Bound file size, validate filename/hash, reject traversal and malformed/duplicate-key JSON. A corrupt or incompatible record fails closed with a specific error or explicit invalidation-and-runtime-resolve policy; never serve it as solved. Do not cache timeouts, invalid histories, zero reach or partial solves.

The shortened spot_id is a display/catalog identifier only. Compare full hash on collisions. Persisting final per-drill results suffices for scoring; retaining a complete profile/root is an internal optional optimization.

## 7. Measured small-solve timings

Executed in `/home/genomix-node/poker-solver` using `.venv/bin/python -B`, PYTHONDONTWRITEBYTECODE=1, Python 3.11.16. Output redirected to `/tmp/probe_02.out` and read in a bounded chunk. Fresh solver per row, vanilla-cfr, seed=None; one sample per configuration/iteration count, no claim of statistical medians or portable latency guarantees.

Exact common ranges: P0=(WeightedCombo((45,49),1.0), WeightedCombo((14,50),0.5)); P1=(WeightedCombo((40,43),1.0), WeightedCombo((41,42),0.75)). Both configurations have four compatible private deals.

River: RiverConfig(board=(33,26,51,19,23), pot=150.0, stack=300, bet=112, range0=P0, range1=P1). Timed root construction+CFRSolver construction+train, then separately total including nash_conv. Eight infosets.

Allstreet: AllStreetPostflopConfig(version='allstreet-postflop-v1', starting_board=(33,26,51), initial_dead_pot=150, effective_stack=150, player0_combos=P0, player1_combos=P1, allowed_runouts=((19,23),), betting_mode='no-limit', wager_targets=(50,150), max_nodes=1500, max_depth=32). Timed the whole solve_allstreet_postflop facade, including bounded validation/completion/nash_conv. Reported 949 nodes, depth 14, 208 infosets.

| Backend | Iterations | Root + train seconds | Total including diagnostics seconds | NashConv chips |
|---|---:|---:|---:|---:|
| river | 10 | 0.017022 | 0.021693 | 28.671293 |
| river | 50 | 0.082724 | 0.087341 | 5.734259 |
| river | 200 | 0.324854 | 0.329519 | 1.433565 |
| allstreet | 10 | not separately measured | 0.681077 | 66.787675 |
| allstreet | 50 | not separately measured | 2.573981 | 13.357535 |
| allstreet | 200 | not separately measured | 9.637813 | 3.339384 |

Values above are rounded representations of real perf_counter output. They exclude practice decision lookup, Q/range evaluation, canonicalization and cache serialization because those modules are not implemented. The 200-iteration allstreet example already consumes nearly the suggested 10-second interactive budget before adapter overhead; do not certify catalog defaults as under budget. Smaller trees or iteration settings need explicit user-facing provenance, not silent reductions of the requested solve.

Reproduction recipe: instantiate exactly the two configs above; for n in (10,50,200), start perf_counter, construct/train fresh river CFRSolver, record train elapsed, call nash_conv and record total; then independently call solve_allstreet_postflop(config, algorithm='vanilla-cfr', iterations=n, seed=None) and record its total/result counts. No practice artifact performance or nplayer timing was measured.

## 8. Fail-closed validation and permanent tests

Validation at practice boundary must be stricter than some older backends: bool is not int/float; iterations >0; cards valid/distinct; finite positive pot; stack/size bounds; supported backend/game/street; canonical extras allowlist; equal HU stacks; positive compatible range mass; hero membership and compatible opponents; no chance actions in public history. Unknown config keys and fractional allstreet dead pots fail rather than coercing away intent.

Validate every consulted chance distribution and policy, exact legal action coverage, finite terminal vector of the correct seat count, consistent infoset actions and pot, and strictly positive finite counterfactual reach. Missing key/action must become descriptive ValueError, not uniform fallback. Catch only specific expected exceptions at serialization/config boundaries; never bare except Exception. Node/depth exhaustion, recursion safety limits and service deadline failures produce no scored artifact. Do not truncate trees or lower requested iterations.

`tests/test_practice_adapter.py` proposed production-importing cases:

1. Runtime solves for Kuhn, river, small allstreet and three-player preflop; assert legal complete policy, sum within 1e-9, finite Q, immutable records and complete provenance, without literal strategy fixtures.
2. Param mapping checks against real constructors; OOP/IP actor identity; typed config/v4 envelope contents; real integer envelope version=4 and flat payload.
3. Tree lookup for every Kuhn card/public node; river OOP root, IP facing bet, OOP facing bet; allstreet hero after CHECK; preflop pending actor and uppercase cumulative targets. Verify multiple opponent deals share one hero key and never parse str(InfoKey).
4. Illegal/terminal/wrong-actor histories, absent hero cards, card collisions, empty compatible mass, unknown extras, bool/nonfinite values, unsupported algorithms/seeds and turn facade start raise ValueError.
5. Q cross-check against an independent explicit conditional-deal enumeration; asymmetric ranges and opponent betting reach must change the posterior. Verify root weighted mixed Q matches production expected_values, both hero seats, and all three nplayer seats.
6. Hero-own zero reach remains evaluable; opponent-zero reach fails; no double application of range weights; chance conditional runout probabilities; positive mass and identical actions across hidden histories.
7. Compare reference exact traversal with any memoized/batched version; hidden hands must not be merged solely by InfoKey. Terminal chip units, dead-pot baseline and decision-pot accounting are pinned to real tree state.
8. Nplayer dispatch transport join round-trips real keys/actions, detects unknown/missing/colliding labels, and never calls eval/literal_eval. nash_conv is None; no three-player convergence claim. CALL/RAISE target amounts and continuation coverage are checked.
9. Backend-owned MCCFR completion is disclosed and deterministic for fixed seed; adapter never supplies its own uniform policy. Resolve the stricter-parent policy before enabling this route.
10. Cache hit equals runtime result, makes no new train call, keeps original provenance timing; changed hash misses; canonical identity, package/build/evaluator mismatch, corruption, atomic write failure, mutation resistance and short-ID collision handling.
11. DoD sensitivity: create a small nondegenerate real allstreet or preflop game, run fresh production solves for each independent mutation of iterations, one opponent range weight, pot and effective stack; require a new full params_hash and a measurable strategy difference and/or Q-derived score difference. Choose stack mutations that actually change legal targets/payoffs, and update dependent continuation/sizing only when semantics require it. Assert numeric differences with a justified tolerance, not just distinct labels or different array length. No hardcoded expected policies.
12. Add the complementary invariance test: river stack changes above fixed bet produce different params_hash but identical normalized hero strategy and Q to numerical tolerance. This documents the model instead of falsifying sensitivity. The authoritative DoD says strategy and/or score, not every parameter universally changes strategy; coordinate this test with test_practice_no_hardcode.py.
13. Constant-action-value and one-action decisions; modal-policy action versus best-Q action at finite iterations; complete range view binds policies to the same public decision rather than root-only labels.
14. Runtime limits: bounded validation failure and deadline/worker cancellation must not populate cache or emit a partial SolvedSpot. Keep the permanent test suite within the shared <60-second added budget; do not turn the 200-iteration timing probe into every parametrized unit test.

No new src/ or tests/ files were created by this design task. Timings verify existing solver routes only; proposed adapter/cache/evaluator behavior still requires implementation and the tests above.

## 9. Parent decisions and concrete gaps

- Reconcile Kuhn card representation and HeroDecision/DecisionPoint naming across spot/scorer/service.
- Mark turn practice support PARTIAL: underlying MultiStreetConfig supports it, named allstreet facade does not.
- Approve exact tree-label transport joining for nplayer typed profile recovery, or expose a typed dispatcher result in a later parent-owned integration.
- Decide whether backend uniform completion for unvisited MCCFR infosets is acceptable and disclose it; initial vanilla-only practice is the fail-closed alternative.
- Generalize report 01's evaluator hero-seat check to n-player without using two-player CFR helpers.
- Enforce preflop pot/post and sizing consistency, and report bounded sampled continuation rather than full preflop GTO.
- Treat mutation sensitivity as evidence on a deliberately sensitive game, not an impossible universal requirement for fixed-bet river stack changes.
- Budget adapter evaluation overhead separately: measured allstreet 200-iteration facade is already close to 10 seconds on this environment.
