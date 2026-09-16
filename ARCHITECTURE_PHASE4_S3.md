# Phase 4 S3 reconciled architecture — bounded 2–9-player preflop

## 1. Scope and decision

S3 adds an immutable, bounded, deterministic 2–9-player preflop game in `src/poker_solver/nplayer_preflop.py`. It supports standard positions, custom integer stacks, antes, blinds, standard/double/Mississippi straddles, limps, small-blind completes, cold calls, and finite per-position raise sizing through 3-bet/4-bet/5-bet+ branches.

The implementation is additive. Existing heads-up `preflop.py`, S1 all-street postflop, S2 N-player postflop, generic `nplayer.py`, and all legacy APIs keep their public behavior. N=2 compatibility is established through projected public traces, not raw type, version, history-record, or information-key equality.

The N=2 projection is explicit. Align states by deterministic chance outcome and public action path, then compare: normalized private deals and exact masses; acting seat; ordered legal `Action` tuples; pot, street commitments, total contributions, remaining stacks, and fold status; and exact terminal utilities. Project `NPlayerPreflopPublicAction` history to its ordered `Action` tuple before comparing with legacy history. Information compatibility compares partitions rather than key bytes: over aligned decision states, two histories are in the same information set in the legacy path if and only if their aligned histories are in the same information set in the N-player path. Version strings, concrete types, actor wrappers, and tuple layout are deliberately excluded.

S3 is a finite reference path. It does not claim unrestricted range solving, practical large-range nine-player performance, equilibrium convergence, automatic abstraction, continuous sizing, or automatic multi-street solving. Closed non-fold leaves use caller-supplied exact continuation values or caller-supplied ranks for a bounded derived showdown continuation.

All HU, 6-player, and 9-player S3 acceptance fixtures use deliberately tiny synthetic per-seat ranges whose full Cartesian product is at most `max_deals`. They prove player-count generality and exact chance arithmetic, not realistic full-range tractability. Large-range tractability belongs to S4 abstraction.

## 2. Public typed contracts

### 2.1 Names and module

The additive public symbols are:

- `NPlayerPreflopConfig`
- `NPlayerPreflopContinuation`
- `NPlayerPreflopSizingRule`
- `NPlayerPreflopPublicAction`
- `NPlayerPreflopState`
- `NPlayerPreflopSolveResult`
- `enumerate_nplayer_preflop_deals`
- `create_nplayer_preflop_root`
- `solve_nplayer_preflop`

`WeightedCombo` and `Action` are reused. `NPlayerCFRSolver`, `expected_values_nplayer`, and `unilateral_deviation_certificate` are reused without a second reach implementation.

### 2.2 `NPlayerPreflopSizingRule`

A frozen, slotted rule contains:

- `position: str`: one canonical label from section 4;
- `raise_count: int`: raises already made before this decision (`0` means open/limp pot, `1` means a 3-bet decision, and so on);
- `cold_callers: int`: callers since the current wager was established, or limpers when `raise_count == 0`;
- `relation: Literal["NA", "IP", "OOP"]`: `NA` when no voluntary aggressor exists; otherwise the actor's postflop relation to the last aggressor;
- `expressions: tuple[Mapping[str, object], ...]`: nonempty strict `sizing.py` expressions.

Every expression is defensively copied into an immutable, hashable representation and validated with `validate_size_expression`. The four-field key is unique within a config. Runtime lookup is exact and deterministic; there is no warning-based or open-size fallback. If no rule matches, only fold/check/call and the legal all-in raise candidate remain. This keeps incomplete rule tables finite and truthful rather than silently applying a wrong position rule.

`relation` is determined against the last voluntary raiser by postflop order: among the two seats, the one encountered later in the clockwise order ending at the button is IP. It is `NA` for an unopened pot. Multiway opponents do not produce a vague table-wide IP flag; the relation is specifically to the aggressor whose wager is being faced.

### 2.3 `NPlayerPreflopContinuation`

A frozen, slotted continuation has:

- `kind: Literal["terminal-table", "showdown-ranks"]`;
- `provenance: str`, nonempty;
- `source: Literal["supplied", "derived"]`;
- `payoff_table: Mapping[ContinuationKeyN, tuple[Fraction, ...]]` for `terminal-table`, otherwise empty;
- `showdown_ranks: Mapping[DealN, tuple[int, ...]]` for `showdown-ranks`, otherwise empty;
- `odd_chip_order: tuple[int, ...]` for `showdown-ranks`, exactly a seat permutation.

`ContinuationKeyN` is `(DealN, tuple[NPlayerPreflopPublicAction, ...])`.

For `terminal-table`, every value is an exact finite N-tuple that sums to zero. Values are complete hand utilities relative to starting stacks; production must not add current contributions a second time. Missing keys fail when their leaf is reached. Root construction may optionally perform complete coverage validation by bounded tree traversal, but it must not claim coverage without traversing the exact bounded tree.

For `showdown-ranks`, every compatible deal has one strict integer rank per seat, larger wins. At every non-fold closed leaf, production refunds unmatched excess, builds exact side-pot layers from the current contributions, finds eligible winners per layer, awards ties with `odd_chip_order`, and derives exact zero-sum chip utilities. This is a synthetic bounded continuation, not automatic board rollout or equity evaluation. No rake is applied by S3; a caller that wants rake-adjusted future value supplies a zero-sum terminal table whose provenance describes its convention.

Ranks are caller-supplied fixture/input data. Production never derives them from cards. Permanent tests hand-declare tiny rank vectors and independently compute winners, layers, splits, and odd-chip recipients; no production evaluator is used as the expected-value oracle.

All nested mappings are detached and exposed read-only. Neither payoff values nor hidden rank vectors appear in an information key.

### 2.4 `NPlayerPreflopConfig`

A frozen, slotted config contains:

- `version: str`, exactly `"nplayer-preflop-v1"`;
- `num_players: int`, strict 2 through 9;
- `button: int`, a valid seat;
- `starting_stacks: tuple[int, ...]`, N positive strict integers;
- `forced_posts: tuple[ForcedPost, ...]`;
- `straddle_variant: Literal["none", "standard", "double", "mississippi"]`;
- `ranges: tuple[tuple[WeightedCombo, ...], ...]`, N nonempty immutable ranges;
- `sizing_rules: tuple[NPlayerPreflopSizingRule, ...]`;
- `max_raises: int`, `max_deals: int`, and `max_nodes: int`, all positive strict integers;
- `short_all_in_reopens: bool`;
- `continuation: NPlayerPreflopContinuation`.

Validation rejects bool-as-int, wrong tuple lengths, duplicate combinations within a seat, nonpositive/nonfinite weights, malformed cards, duplicate sizing keys, invalid forced-post seats or types, cumulative posts above a seat's stack, absent or duplicate blind declarations, and unsupported straddle arrangements. Antes are either absent or exactly one identical positive ante is posted by every seat. Unequal/per-seat-partial antes and a single-seat big-blind-ante representation are outside this ledger contract and fail validation; representing table-paid dead money would require a separate common-pot ledger. At least two seats must have chips after posts or the game is already degenerate and is rejected.

Nested caller inputs are detached. The Cartesian product `prod(len(range_i))` must not exceed `max_deals`; this precheck bounds work even if blockers eliminate every candidate. Compatible deals are never silently truncated.

### 2.5 State and result

`NPlayerPreflopPublicAction` is a frozen `(actor: int, action: Action)` record.

`NPlayerPreflopState` is frozen and contains:

- config, optional private deal, and acting player;
- integer pot;
- N-tuples `street_committed`, `total_contributed`, `remaining`, and `folded`;
- ordered unique `pending` responders;
- N raise-entitlement booleans `can_raise`;
- positive `last_raise_increment`;
- bounded `raise_count`;
- actor-labelled public history;
- optional exact terminal N-tuple.

It implements `NPlayerGameState`.

`NPlayerPreflopSolveResult` is frozen and contains detached strategy, N expected values, optional `UnilateralDeviationCertificate`, `config_version`, `game_version`, algorithm, iterations, `max_nodes`, structural `max_depth`, immutable metadata, and truthful provenance. Metadata states `converged=False` and `convergence_claim="none"`.

## 3. Forced-post ledger

Forced posts are applied once in declared order with exact integer transfers. S3 config validation requires each seat's cumulative declared posts to fit its stack, so no post is silently reduced. Exact short stacks remain supported by declaring a stack equal to its cumulative posts; that seat starts all-in.

For each post, payment increases `total_contributed`. Antes do not increase `street_committed`; small blind, big blind, and straddle payments do. Thus antes contribute to the pot but never change the live wager or minimum raise.

`game_structure.apply_forced_posts` currently records every forced post, including antes, in `SeatLedger.street_committed`. S3 must not copy that field into its root. It may reuse the helper's remaining/total values and independently sum only blind/straddle posts for `street_committed`, or apply the declared posts directly in the new module. Existing shared-helper behavior is unchanged.

The config must contain exactly one SB and one BB on the seats derived from the button. Their positive integer amounts satisfy `SB <= BB`. Antes obey the all-seats-equal contract in section 2.4. Declared straddles follow the validated variant in section 5. Every declared post is transferred in full; a post is never truncated to the remaining stack. A seat may start all-in only when its stack exactly equals its cumulative declared posts. The root is not passed through `refund_uncalled_excess`: blind and straddle differences are live wagers, not terminal unmatched excess.

Root invariants are:

- `pot == sum(total_contributed)`;
- `remaining[i] + total_contributed[i] == starting_stacks[i]`;
- `0 <= street_committed[i] <= total_contributed[i]`;
- `last_raise_increment` equals the outermost live wager amount (BB without a straddle, final straddle otherwise);
- the current high-water mark is `max(street_committed)`;
- `can_raise[i]` is true exactly for seats with positive remaining chips before any voluntary action;
- `raise_count == 0`, empty history, and no private deal at CHANCE.

## 4. Canonical positions and order

Seats increase clockwise. For N=2, the button is also SB and acts first preflop; the other seat is BB. For N>=3, SB is `(button + 1) % N`, BB is `(button + 2) % N`, and no-straddle action starts after BB.

Canonical labels in clockwise preflop order are:

- 2: `BTN/SB, BB`
- 3: `BTN, SB, BB`
- 4: `CO, BTN, SB, BB`
- 5: `HJ, CO, BTN, SB, BB`
- 6: `UTG, HJ, CO, BTN, SB, BB`
- 7: `UTG, MP, HJ, CO, BTN, SB, BB`
- 8: `UTG, UTG+1, MP, HJ, CO, BTN, SB, BB`
- 9: `UTG, UTG+1, MP, LJ, HJ, CO, BTN, SB, BB`.

Operational straddle aliases are derived independently of those display labels. For every N>=3, `UTG` is the first non-blind seat clockwise after BB: it is BTN at N=3, CO at N=4, HJ at N=5, and the displayed UTG seat at N>=6. For every N>=4, `UTG+1` is the next non-blind seat clockwise after that operational UTG: it is BTN at N=4, CO at N=5, HJ at N=6, MP at N=7, and the displayed UTG+1 seat at N>=8. Standard- and double-straddle validation, posting order, first action, and final-option order use these operational aliases. Thus standard is defined at N=3 and double first becomes defined at N=4 without inventing an extra mutable position field.

Position is derived, not mutable state. `_ordered_after(seat, candidates, N)` scans clockwise once with wraparound.

After a deal, `pending` contains every non-folded seat with positive remaining chips, starting at the first actionable actor and ending at the last actionable option seat. Seats all-in from exact forced posts are excluded: they have no CHECK, CALL, FOLD, or raise decision and do not retain an option. `acting_player == pending[0]`.

## 5. Straddle variants

Straddles are explicit `ForcedPost(..., "straddle", amount)` values. Each amount is a positive integer strictly greater than the preceding live wager; equal or decreasing declarations are not straddles under this contract and fail validation.

- `none`: no straddle; first action is BTN/SB for HU when actionable, otherwise the next actionable seat clockwise, and the first actionable seat after BB for N>=3.
- `standard`: N>=3, exactly one straddle by UTG; first action is the next actionable seat clockwise after UTG; UTG retains the final option only when it has chips after posting.
- `double`: N>=4, exactly two ordered straddles by UTG then UTG+1, with the second amount strictly greater than the first; first action follows UTG+1 and skips all-in seats; action wraps through UTG and ends at UTG+1 only when those seats remain actionable.
- `mississippi`: N>=3, exactly one caller-selected non-blind straddler; first action follows that straddler and skips all-in seats; the straddler has the final option only when it has chips after posting. Button Mississippi is supported. SB/BB Mississippi and HU Mississippi are rejected because there is no non-blind HU seat under this contract.

Variant, posts, pot, first actor, and initial legal actions are observable tree differences. Permanent no/single/double/Mississippi fixtures must verify those differences and deterministic repeatability.

## 6. Deals and chance reach

Traverse the per-seat range Cartesian product in seat/range tuple order while carrying a used-card set. Prune a candidate immediately on collision. Convert validated weights with `Fraction(str(weight))`; multiply and normalize exact masses before public float conversion. A valid deal has 2N unique cards.

No compatible deals, zero exact mass, or candidate product above `max_deals` fails closed. Chance actions are `Action("DEAL", index)` in deterministic order. Probabilities are finite, nonnegative, and sum to one within `1e-12`.

The reused N-player CFR propagates one realization reach per player plus chance reach. Player i's regret weight is chance reach times every opponent reach and excludes i's own reach. Permanent six-player arithmetic tests prove this independently.

## 7. Betting semantics

Action amounts are integer absolute preflop street commitments.

For actor p:

- `H = max(street_committed)`;
- `own = street_committed[p]`;
- `to_call = H - own`.

If `to_call > 0`, legal actions begin with FOLD and `CALL(min(H, own + remaining[p]))`. If `to_call == 0`, legal actions begin with CHECK; folding while checking is not exposed.

A raise requires `can_raise[p]`, chips beyond the call, and `raise_count < max_raises`. The sizing key is derived from position, current raise count, cold callers, and relation to the last aggressor. Candidate expressions are resolved by `fixed_sizes` with the exact current context. Target duplicates retain first declaration order. The actor's all-in target is considered once even when no sizing rule matches.

A target is a normal full raise at or above `H + last_raise_increment`. A below-minimum target is legal only when it is the actor's all-in target and exceeds H. Every raise, including a short all-in, increments `raise_count`.

`cold_callers` is the number of live seats whose latest voluntary action is CALL in the current response segment: every pre-raise CALL, including a small-blind completion, counts for an opening/isolation decision; after a raise, callers of that wager count for a squeeze/re-raise decision. It resets immediately after every raise. Folded callers do not count. The actor is not counted in its own sizing key.

Transitions append one actor-labelled public action and transfer exactly `target - own` chips.

- FOLD marks the actor folded and unable to raise.
- CHECK/CALL removes the actor from the current pending queue and consumes its current raise entitlement; an all-in caller becomes non-actionable.
- Any raise rebuilds pending as all other live seats with chips, clockwise after the raiser, because every such seat must respond or retain an unacted option.
- A full raise updates `last_raise_increment`; every other live seat with chips is re-entitled to raise, while the raiser has consumed its entitlement until another qualifying raise occurs.
- A short all-in does not update the increment. If `short_all_in_reopens` is false, a seat may raise after it only when that seat was both still in the pre-action pending queue and raise-entitled before the short all-in. This is an intersection, not a union: a seat that checked or called earlier may call or fold against the higher wager but may not re-raise. If `short_all_in_reopens` is true, every other live seat with chips is re-entitled. The all-in short raiser is never entitled.

Action closes when one live seat remains or no actionable pending responder remains. The decision depth is bounded conservatively by `N + max_raises * (N - 1)`; the solver receives `max_depth = 2 + N + max_raises * (N - 1)` to include chance/root framing.

## 8. Terminal accounting and continuations

Before any terminal is finalized, call `refund_uncalled_excess(total_contributed)`. Add refunds to remaining stacks, replace contributions and pot with matched amounts, and subtract refunds from current street commitments. A negative street commitment is an invariant violation. The all-seats-equal ante contract guarantees that every seat's total contribution is the same dead ante plus its live street commitment, so a unique leader's total-contribution excess equals its street-commitment excess and is bounded by that street commitment. Unequal or single-seat antes are rejected at config validation rather than deferred to terminal failure.

For fold-out, build exact matched pot layers with folded eligibility, award every layer to its sole eligible live winner, compute final stacks, and return exact utilities relative to starting stacks. This covers blinds, antes, straddles, side pots, and all-in contributors without a continuation lookup.

For a non-fold closed leaf:

- `terminal-table` returns the exact total utility vector under the exact `(deal, actor-labelled history)` key after validating zero-sum;
- `showdown-ranks` performs exact side-pot settlement from matched contributions and supplied ranks as defined in section 2.3.

Every terminal utility vector is an N-tuple of finite exact rationals summing to zero. The S3 path has no house-rake field. Independent permanent ledger fixtures must calculate expected refunds, layers, awards, final stacks, and utilities without importing production settlement helpers.

## 9. Information noninterference

An acting player's information key includes only:

- version/rule identity and N;
- owner seat and owner's private combo;
- button, starting stacks, forced posts, straddle variant, and immutable sizing-rule identity;
- pot, public commitments/contributions/remaining/fold flags;
- pending order, raise entitlements, last increment, raise count, and acting seat;
- actor-labelled public history;
- continuation kind, source, and provenance.

It excludes opponent cards, deal index/order, hidden payoff-table values, hidden showdown ranks, and traversal state. Varying opponents or hidden continuation contents while owner/public state is fixed must preserve the key; varying the owner's combo or a legal-action-affecting public field must change it. Infosets must also preserve identical legal action tuples.

## 10. Solver and diagnostics

`solve_nplayer_preflop` accepts only `algorithm="vanilla-cfr"`, positive strict integer iterations, an optional exhaustive deviation diagnostic, and an optional positive `max_pure_strategies`. It forwards config `max_nodes` and the structural `max_depth` to `NPlayerCFRSolver`.

Strategies and metadata are deeply detached. Every policy is finite, nonnegative, and normalized. Repeated identical solves produce identical strategies, N values, metadata, and diagnostics.

The unilateral-deviation certificate is exhaustive below its cap or fails closed; it is never sampled and never called exploitability or a Nash certificate. A permanent six-player tiny oracle independently enumerates pure deviations. Nine-player acceptance uses a deliberately tiny tree and makes no throughput claim.

## 11. Strict v4 API, CLI, exports, and examples

Add direct v4 operation `solve-nplayer-preflop`. The envelope remains exactly `{version: 4, operation, payload}` with integer version 4. The payload contains:

- config version, N, button, starting stacks;
- ordered forced-post objects and straddle variant;
- per-seat weighted ranges;
- strict sizing-rule objects;
- max raises/deals/nodes and short-all-in policy;
- one continuation object:
  - terminal-table entries as JSON lists of `{deal, history, values}`, or
  - showdown entries as `{deal, ranks}` plus odd-chip order;
- algorithm, iterations, null seed, diagnostic flag, and pure-strategy cap.

History JSON entries explicitly contain actor, action kind, and integer amount. Unknown/missing fields, bool numerics, nonfinite values, malformed arrays, duplicate continuation keys/deals, unsupported seeds/algorithms, and bound violations fail closed. Conversion creates detached typed values.

The response contains operation/version, config/game versions, algorithm/iterations/bounds, detached serialized strategy, N values, optional certificate, metadata, provenance, and `approximate: false`. It does not claim convergence.

The existing generic `phase4 FILE|- --json` CLI already forwards v4 and requires no new parser shape. Add canonical synthetic bounded examples:

- `examples/phase4/nplayer_2p_preflop.json`
- `examples/phase4/nplayer_6p_preflop.json`
- `examples/phase4/nplayer_9p_preflop.json`.

At least the 6-player examples distinguish no, standard, double, and Mississippi straddle trees through permanent typed fixtures; canonical JSON may use one representative variant each. Examples are synthetic and non-presolved.

Package exports are additive. After implementation, v3 capabilities truthfully advertise `nplayer-preflop` with players `[2, 9]`, street `preflop-one-round`, interfaces `typed/json-v4/cli-phase4`, continuations `supplied-or-derived-bounded`, and deviation `exhaustive-diagnostic-only`.

## 12. TDD batches and ownership

### S3-I1 — typed state and exact ledger

Four exclusive RED owners create permanent production-importing suites:

1. `tests/test_nplayer_preflop_config.py`: immutable config, positions, forced posts, all straddle variants, deterministic bounded deals;
2. `tests/test_nplayer_preflop_betting.py`: HU/6/9 action order, limps, SB complete, cold calls, exact sizing-key selection, raise-to targets, 3/4/5-bet+, full/short all-ins and closure;
3. `tests/test_nplayer_preflop_settlement.py`: independent fold/refund/side-pot/showdown continuation ledgers and zero-sum terminal-table leaves;
4. `tests/test_nplayer_preflop_information.py`: information noninterference and projected N=2 legacy equivalence.

A fifth owner may implement `src/poker_solver/nplayer_preflop.py` only after all four parent-verified RED receipts exist. No child owns shared legacy files. Focused tests, legacy controls, full regression, frozen hashes, a fresh different non-author audit, parent verification, and an accepted-wave commit are mandatory.

### S3-I2 — facade/API/examples/exports

Four exclusive RED owners create:

1. `tests/test_nplayer_preflop_solve.py`;
2. `tests/test_api_v4_nplayer_preflop.py`;
3. `tests/test_phase4_s3_examples.py`;
4. `tests/test_phase4_s3_exports.py`.

A gated core owner may extend only `nplayer_preflop.py`; a core-gated integration owner may extend `api_v4.py`, `api_v3.py`, package exports, and examples after the RED and core receipts. `cli.py` changes are forbidden unless a genuine failing generic-CLI contract proves they are necessary. The same focused/full/freeze/fresh-audit/parent/commit gate applies.

## 13. Mandatory acceptance matrix

S3 is complete only when executable evidence proves:

- strict configs accept every N from 2 through 9 and reject malformed types, lengths, posts, variants, sizing keys, continuations, and bounds, including incomplete/unequal/single-seat ante sets, non-increasing straddles, and any declared post exceeding its seat's stack;
- HU, 6-max, and 9-max roots build and solve, return N values, and use exact deterministic chance mass;
- no/standard/double/Mississippi straddles produce distinct verified ledgers, first actionable actors, and trees; exact all-in posts are never truncated and all-in option seats are absent from `pending`;
- limps, SB completes, cold calls, 3/4/5-bet+ rules, IP/OOP-aggressor relation, and per-cold-caller keys select exactly the declared sizes, with an SB completion counted as a pre-raise caller;
- all action amounts are absolute commitments and all transitions conserve stacks and pot;
- full and short all-ins obey pending/reopening rules, the no-reopen policy uses the old-pending/old-entitlement intersection, and unmatched refund never exceeds current-street commitment;
- independent integer/rational oracles match fold, refund, side-pot, tie, odd-chip, terminal-table, and derived-showdown leaves;
- all terminal utilities sum exactly to zero;
- opponent-card and hidden-continuation noninterference pass for 6 and 9 players;
- policies are normalized, detached, and deterministic;
- exact six-plus-player reach and unilateral-deviation oracles match production below declared caps;
- N=2 projected deals/actions/ledgers/terminals/information partitions match frozen Phase-3 HU fixtures;
- strict v4, generic CLI file/stdin/error behavior, examples, exports, and capability truth pass;
- all S1/S2 and legacy tests remain green;
- each implementation batch has a fresh different non-author audit and accepted-wave commit;
- `phase3-398-green` remains exactly at `feba8222a0b614b0c64eca59402403ce733195ea`.

## 14. Reconciliation notes

The six design streams were inputs, not authorities.

- D301 supplied the strongest additive model/deal/TDD basis, but its zero street commitment at root, initial-blind refund rejection, rank-only continuation, and rake-heavy postflop settlement were rejected.
- D302 supplied detailed betting and sizing cases, but decimal-chip examples, a non-zero-sum fold tuple, ambiguous fallbacks, and conflicting short-all-in language were rejected.
- D303 supplied straddle order evidence; contradictory HU Mississippi and nested double-option claims were narrowed to the explicit variant rules above.
- D304 largely replayed postflop settlement and incorrectly said S3 needed no continuation; only reusable exact-ledger and independent-oracle principles were retained.
- D305 supplied the strongest solver/information/bounds basis; its generic first-actor and continuation details were reconciled here.
- D306 replayed the already-completed S2 postflop API rather than S3 and is rejected as substantive S3 API design evidence.

This document is the sole S3 implementation authority after a fresh frozen design audit accepts it.

## 15. Post-audit parent corrections

The first two design-audit rounds exposed false PASS traces and one real ledger gap. The authoritative corrections are:

- only absent or uniform all-seat antes are representable; unequal and big-blind-ante dead money require a future common-pot ledger;
- every forced post is exact, straddles strictly increase the live wager, and all-in post seats are never placed in `pending`;
- a small-blind completion counts as a pre-raise CALL for `cold_callers`;
- CHECK/CALL consumes current raise entitlement and no-reopen short-all-in entitlement is the intersection of old pending and old entitlement;
- terminal refund boundedness is guaranteed by config validation and ledger algebra, not by accepting a valid config and failing only at its terminal.
