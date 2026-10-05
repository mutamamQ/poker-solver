# Phase 4 S2 reconciled architecture — bounded 2–9-player postflop

## 1. Scope and decision

S2 generalizes the existing exactly-three-player, one-betting-round postflop game to a new bounded 2–9-player typed path. It reuses the existing generic N-player CFR and exact settlement primitives. It does not refactor the Phase-3 three-player implementation.

S2 delivers:

- immutable typed config/state for two through nine contiguous seats;
- deterministic finite weighted private deals;
- one postflop betting round with exact action order and reopening rules;
- exact integer refunds, side pots, rake, ties, odd chips, and terminal conservation;
- deterministic bounded vanilla CFR through the existing `NPlayerCFRSolver`;
- exact bounded unilateral-deviation diagnostics through the existing `unilateral_deviation_certificate`;
- a strict additive v4 operation and the existing generic Phase-4 CLI path;
- permanent 4-, 5-, and 9-player acceptance fixtures.

S2 does not deliver multi-street multiway play, preflop multiway trees, sampled deviation estimates, abstraction, continuous sizing, a convergence certificate, or practical unbounded nine-player solving.

The new module is `src/poker_solver/nplayer_postflop.py`. Existing `MultiwayConfig`, `ThreePlayerPostflopState`, `create_three_player_root`, `src/poker_solver/multiway.py`, and all legacy tests retain their public behavior. Three-player equivalence is proved by tests, not by routing the legacy implementation through the new module.

## 2. Public typed contracts

### 2.1 `NPlayerPostflopConfig`

The config is a frozen, slotted dataclass with:

- `version: str`, exactly `"nplayer-postflop-v1"`;
- `num_players: int`, strict integer 2 through 9;
- `button: int`, in `range(num_players)`;
- `starting_stacks: tuple[int, ...]`;
- `contributions: tuple[int, ...]`;
- `folded: tuple[bool, ...]`;
- `board: tuple[int, ...]`, exactly 3, 4, or 5 unique card integers in `0..51`;
- `ranges: tuple[tuple[WeightedCombo, ...], ...]`;
- `wager_targets: tuple[int, ...]`, absolute street raise-to targets;
- `max_raises: int`;
- `max_deals: int`;
- `max_nodes: int`;
- `odd_chip_order: tuple[int, ...]`;
- `showdown_ranks: Mapping[DealN, tuple[int, ...]]`;
- `rake_policy: RakePolicy | None = None`.

`DealN` is `tuple[tuple[int, int], ...]` of length N.

Validation is strict and rejects bool-as-int. Every per-seat tuple has length N. Stacks are positive. Contributions are nonnegative and do not exceed stacks. The initial pot `sum(contributions)` is positive. Fold flags are booleans and at least two seats are initially live. Every range is a nonempty tuple of unique `WeightedCombo` values with finite positive weights and normalized two-card combinations. Targets are positive, unique, and increasing. `max_raises`, `max_deals`, and `max_nodes` are positive strict integers. Odd-chip order is checked by both length and set equality to be exactly a permutation of `range(N)`.

The initial contribution ledger must already be matched: `refund_uncalled_excess(config.contributions).refunds == (0,) * N`. A postflop root carrying pre-existing unmatched excess is invalid because that excess should have been refunded on the preceding street. Reject it before deal enumeration or solving. This guarantees that unmatched excess created by the S2 round does not exceed the winner's current `street_committed` amount.

Each showdown key has N pairwise-disjoint two-card combos; each rank vector has N strict integers, where a larger value wins. The config detaches the caller mapping into a private dictionary and exposes it through `MappingProxyType`. All other fields are already immutable tuples/frozen values.

### 2.2 `NPlayerPublicAction`

A frozen, slotted public-history record contains:

- `actor: int`;
- `action: Action`.

The actor is explicit because identical `CHECK`, `CALL`, or `FOLD` values from different seats are different public histories. The CFR legal-action interface remains `tuple[Action, ...]`.

### 2.3 `NPlayerPostflopState`

The frozen, slotted state contains:

- `config`, `private_deal`, and `acting_player`;
- exact integer `pot`;
- N-tuples `street_committed`, `total_contributed`, and `remaining`;
- N-tuple `folded`;
- ordered unique `pending` responders;
- N-tuple `can_raise`;
- positive `last_raise_increment`;
- bounded `raise_count`;
- `history: tuple[NPlayerPublicAction, ...]`;
- `terminal_values: tuple[int, ...] | None`;
- nonnegative integer `house_rake`.

It implements `NPlayerGameState`: `num_players`, `current_player`, `legal_actions`, `chance_outcomes`, `child`, `information_state_key`, and `returns`.

## 3. Exact state invariants

Every direct construction and every child validates:

1. All per-seat tuples have length N and strict element types.
2. `pot == sum(total_contributed)`.
3. `remaining[i] + total_contributed[i] == starting_stacks[i]`.
4. `0 <= street_committed[i] <= total_contributed[i]`.
5. Folded/all-in seats are not pending. Pending seats are unique, in range, live, have chips, and ordered clockwise for their current response cycle.
6. A dealt nonterminal has nonempty pending and `acting_player == pending[0]`.
7. Folded/all-in seats cannot raise. `0 <= raise_count <= max_raises`; `last_raise_increment > 0`.
8. Chance root has no deal/history/settlement and uses baseline contributions in the pot, zero current-street commitments, and derived remaining stacks.
9. Every dealt state uses a compatible configured deal.
10. Terminal has empty pending, exactly N integer utilities, and `sum(terminal_values) + house_rake == 0`.
11. Nonterminal has no terminal values and zero house rake.

Status is derived, not duplicated: folded from `folded[i]`, all-in from live plus `remaining[i] == 0`, and active from live plus positive remaining.

## 4. Deterministic bounded private deals

The deal enumerator iteratively walks the Cartesian product in seat/range tuple order while carrying a used-card set seeded by the board. It prunes collisions immediately. A valid deal has 2N unique private cards disjoint from the board. Before multiplication, each validated public float weight is converted deterministically with `Fraction(str(weight))`; deal masses and their total therefore use exact rational arithmetic until the final public probability conversion. Recursive retry-until-compatible enumeration is forbidden.

For the new API, `max_deals` bounds candidate Cartesian products before enumeration: `prod(len(range_i)) <= max_deals`. This gives a real work bound even when blockers make every candidate invalid. Compatible results are never silently truncated. No compatible deal and zero total mass fail closed.

Chance actions are `Action("DEAL", index)` in deterministic result order. Exact masses are summed before conversion; public float probabilities are finite, nonnegative, and sum to one within `1e-12`.

At root construction, every compatible deal must have exact showdown-rank coverage because strict config validation requires at least two initially live seats. Missing, duplicate, malformed, or extra deal records fail before solving; later fold-out branches do not weaken this root coverage rule.

## 5. Betting round semantics

### 5.1 Root and order

The chance root has:

- `pot = sum(config.contributions)`;
- `total_contributed = config.contributions`;
- `street_committed = (0,) * N`;
- `remaining = starting_stacks - contributions`;
- `pending` equal to active seats clockwise after the button;
- `can_raise[i]` true exactly for active seats;
- `last_raise_increment = wager_targets[0]` when present, otherwise `1`.

After a private deal, the first pending seat acts. `_ordered_after(seat, candidates)` scans clockwise with wraparound and returns every candidate in that canonical order.

### 5.2 Legal actions

For acting seat `p`, derive the live high-water mark `H`, own street commitment, and `to_call = H - own`.

- If `to_call == 0`, offer `CHECK`.
- Otherwise offer `FOLD` and `CALL(own + min(to_call, remaining[p]))`.
- A raise requires current entitlement, chips beyond the call, and `raise_count < max_raises`.
- Deduplicate configured targets in declared order, then consider the all-in target.
- A normal raise target is at least `H + last_raise_increment`.
- A below-minimum raise is legal only when it is the actor's all-in target.
- Action amounts are absolute current-street commitments.

Folding when checking is possible is not exposed, preserving the Phase-3 contract.

### 5.3 Transition and closure

Keep `old_pending` and old raise entitlements before applying the action.

- Fold marks the actor folded and unable to raise.
- Check removes the actor from pending.
- Call transfers the exact target delta to pot/contribution and removes the actor; an all-in caller becomes non-actionable.
- Raise transfers the exact delta, increments `raise_count`, and rebuilds pending as every other active seat clockwise after the raiser.

For a full raise (`target - old_H >= last_raise_increment`), update the increment and reopen raising for all active seats. For a short all-in raise, do not update the increment: seats still in `old_pending` retain their prior entitlement, while seats that had already acted cannot re-raise. The short raiser has no chips and cannot raise.

After each action, terminate when one live seat remains or pending is empty. Otherwise `acting_player` is the first pending seat. All live all-in seats being non-actionable therefore closes the round. The maximum decision depth is structurally bounded by `N + max_raises * (N - 1)`.

## 6. Settlement and independent accounting oracle

Settlement is integer-only:

1. Refund unique unmatched excess with `refund_uncalled_excess`.
2. Add refunds to remaining stacks; replace total contributions and pot by matched amounts; reduce street commitments by refunds and reject negative results. The validated matched root ledger guarantees that a legal final refund comes entirely from this round's commitment.
3. Build layers with `build_pot_layers(matched, folded=folded_set)`.
4. For showdown, find the highest eligible rank independently per layer. A sole live player wins every layer without rank lookup.
5. Calculate one hand-level rake from `eligible_pot = sum(layer.amount for layer in layers)`, the matched post-refund pot, and allocate it by the configured layer order.
6. Award net layers and ties through `award_pot_layers` and declared odd-chip order.
7. Pad awards to N seats when zero-contribution trailing seats are absent from the primitive's output.
8. Compute final stacks and utilities and verify both conservation equations.

Independent permanent fixtures hand-derive contribution levels, contributors, eligibility, winners, rake, remainder recipients, awards, final stacks, and utilities for 4/5/9 seats. The tests do not use the settlement functions to calculate expected results.

With no rake, player utilities sum to zero. With rake, player utilities sum to negative house rake and player-plus-house utility is exactly zero. This is the mission's “zero-sum including side pots” contract.

## 7. Information and strategy integrity

An information key includes rules/version identity, N, owner, owner private combo, fixed board, button, all public ledgers/fold flags, pending order, raise entitlements, last increment, raise count, acting seat, wager targets, and actor-labelled history.

It excludes all opponent private cards, deal index, iterator position, and hidden showdown ranks. If a public field can change legal actions or settlement, it is part of the key.

Permanent 4- and 9-player tests vary opponent cards and hidden showdown ranks while holding owner/public state fixed and require equal owner keys; changing the owner's combo requires a different key. `collect_nplayer_infosets` remains the owner/action-consistency oracle.

Strategies returned by the solve facade are detached nested mappings with finite nonnegative probabilities summing to one. Repeated deterministic runs produce equal values, diagnostics, and serialized strategy.

## 8. Solver, reach, and exact deviation diagnostic

Reuse `NPlayerCFRSolver`, `expected_values_nplayer`, and `unilateral_deviation_certificate`.

`NPlayerCFRSolver` already carries one realization reach per player and chance reach. A regret update for player i is weighted by chance times every opponent reach, excluding i's own reach. S2 adds no duplicate reach tracker.

S2-I2 adds keyword-only `max_nodes`/`max_depth` parameters to `NPlayerCFRSolver`; defaults remain unchanged for legacy callers. The constructor forwards both values to `collect_nplayer_infosets`, and the solve facade passes `config.max_nodes` plus the structural depth bound.

`NPlayerPostflopSolveResult` contains detached strategy, N expected values, optional `UnilateralDeviationCertificate`, and truthful metadata. `solve_nplayer_postflop` supports deterministic `vanilla-cfr` only, positive iterations, and an optional positive `max_pure_strategies`. When requested, the exact exhaustive diagnostic runs or fails closed on its cap. It is never sampled and is never described as Nash convergence.

A five-player permanent oracle manually enumerates each player's tiny pure-deviation set and compares profile values, best-response values, incentives, and total incentive. A separate one-iteration five-player reach oracle checks the exact counterfactual scaling. Nine-player acceptance uses a deliberately tiny finite tree and makes no scalability claim.

## 9. Strict v4 and CLI surface

Add direct v4 operation `solve-nplayer-postflop`. It follows the existing strict envelope and direct request style. The JSON request uses arrays for N-length fields and a deterministic `showdowns` list whose entries contain `deal` and `ranks`; JSON never attempts tuple-key maps.

The parser rejects unknown/missing fields, bool numerics, nonfinite weights, wrong N-length arrays, duplicate showdown deals, malformed rake objects, unsupported algorithms/seeds, and all bound violations. It constructs immutable tuples and a detached typed mapping.

The existing `phase4 REQUEST --json` command already forwards to `dispatch_v4`; no new parser shape is introduced. Add canonical synthetic 4-, 5-, and 9-player direct-request examples with tiny bounded trees.

After typed/API acceptance, update the v3 capability manifest truthfully:

- status `implemented-bounded`;
- players `[2, 9]`;
- streets `one-betting-round`;
- interfaces `typed`, `json-v4`, `cli-phase4`;
- deviation `exhaustive-diagnostic-only`.

Package-root exports are additive. Legacy v1-v4 operations and three-player capability behavior remain covered by regression tests.

## 10. TDD implementation batches

### S2-I1 — typed state and exact ledger

Implementation files: new `src/poker_solver/nplayer_postflop.py` only. Legacy multiway and generic solver files remain unchanged.

Permanent RED owners cover these nonoverlapping files:

1. `tests/test_nplayer_postflop_config.py`: config validation, defensive copy, bounded deterministic deals;
2. `tests/test_nplayer_postflop_betting.py`: betting order, pending closure, full/short all-in reopening, direct-state invariants;
3. `tests/test_nplayer_postflop_settlement.py`: 4/5/9 side pots, refunds, rake, ties, odd chips, and hand ledgers;
4. `tests/test_nplayer_postflop_information.py`: information noninterference and old/new three-player observational trace equivalence.

Three-player equivalence is not raw object, version-string, history-record, or information-key equality. The oracle projects both paths to chance deals/probabilities, clockwise actors, legal `Action` tuples, pot/commitment/remaining/fold ledgers, terminal rake/utilities, and owner information partitions, then requires equal projected traces for frozen Phase-3 fixtures.

Only after the RED receipts may production be implemented. Parent runs all four new modules, `test_multiway_phase3.py`, `test_game_structure.py`, and the full suite. The frozen candidate then receives a fresh different non-author audit. Accepted S2-I1 is committed before S2-I2 begins.

### S2-I2 — solve facade, diagnostics, API, examples

Potential implementation files are `nplayer_postflop.py`, additive bound plumbing in `nplayer.py`, `api_v4.py`, `api_v3.py`, and package exports. The CLI parser should not need modification.

Permanent RED owners cover:

1. `tests/test_nplayer_postflop_solve.py`: 4/5/9 deterministic typed solves, normalized strategies, values, reach oracle, exact 5+ deviation certificate, and mandatory solver constructor bounds;
2. `tests/test_api_v4_nplayer.py`: strict v4 schema and response isolation;
3. `tests/test_phase4_s2_examples.py`: canonical examples and generic CLI file/stdin/error behavior;
4. `tests/test_phase4_s2_exports.py`: package exports, capability truth, legacy v1-v4 compatibility.

Production ownership is nonoverlapping; parent integrates shared exports/capability fields after RED. Focused and full regression precede a frozen candidate, fresh different non-author audit, parent verification, and accepted-wave commit.

## 11. Mandatory acceptance matrix

S2 is complete only when all are executable and green:

- strict configs accept every N from 2 through 9 and reject malformed lengths/types/bounds or pre-existing unmatched root excess;
- 4-, 5-, and 9-player spots build, validate, train/evaluate, and return N values;
- chance mass, blocker filtering, deterministic deal order, and `max_deals` fail-closed behavior pass;
- every transition conserves stacks/pot and obeys clockwise pending/reopening rules;
- hand-derived multi-layer refunds, side pots, rake, ties, and odd chips match exactly;
- terminal utility plus house rake conserves exactly;
- 4- and 9-player opponent-card noninterference passes;
- policies are normalized and deterministic;
- a five-plus-player exact unilateral-deviation diagnostic matches independent enumeration below its cap;
- the generic N=3 projected trace matches the frozen Phase-3 deals, actions, public ledgers, settlement, utilities, and information partitions without requiring raw key/history identity;
- all old three-player tests and the entire prior suite remain green;
- strict v4, generic CLI, examples, exports, and capability truth pass;
- every implementation batch has a fresh, different non-author adversarial audit and an accepted-wave commit;
- tag `phase3-398-green` remains present.

## 12. Provenance and boundaries

Truthful provenance:

`bounded deterministic 2-9-player one-round postflop CFR with exact integer side-pot settlement and optional exhaustive finite unilateral-deviation diagnostic`

Do not claim GTO convergence, practical large-range nine-player performance, multi-street play, automatic rank evaluation, sampled exploitability, or unrestricted solving.
