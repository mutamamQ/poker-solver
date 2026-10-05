# S3 Design: Multiway Preflop Solver, Information Noninterference, Reach and Bound Contract

**Heartbeat:** 2026-09-16 UTC 00:00 — Design recovery D305 active

## 1. Scope and Decision

S3 generalizes the existing heads-up preflop game (Phase 3) to a bounded 2–9-player preflop path. It reuses the existing generic N-player CFR, exact settlement primitives from S2, and the HU preflop information/sizing architecture. It does not refactor the Phase-3 HU implementation.

S3 delivers:

- Immutable typed config/state for 2–9 contiguous seats
- Deterministic finite weighted private deals with exact rational masses
- One preflop betting round with position-aware action order, forced posts (SB/BB/antes/straddles including double/Mississippi variants), limps, SB completes, cold-calls, and 3-bet/4-bet/5-bet+ sizing rules per position (IP/OOP, per cold-caller)
- Custom stacks per player
- Exact integer forced-post/refund ledgers and terminal conservation
- Deterministic bounded vanilla CFR through the existing `NPlayerCFRSolver`
- Exact bounded unilateral-deviation diagnostics through the existing `unilateral_deviation_certificate`
- Caller-supplied terminal continuation values (no automatic multi-street solving)
- A strict additive v4 operation and the existing generic Phase-4 CLI path
- Permanent 2-, 6-, and 9-player acceptance fixtures

S3 does not deliver automatic multi-street preflop-to-flop solving, sampled deviation estimates, abstraction, continuous sizing, a convergence certificate, or practical unbounded nine-player solving.

The new module is `src/poker_solver/nplayer_preflop.py`. Existing `PreflopConfig`, `PreflopState`, `create_preflop_root`, and all legacy HU tests retain their public behavior. HU equivalence is proved by tests, not by routing the legacy implementation through the new module.

## 2. Public Typed Contracts

### 2.1 `NPlayerPreflopConfig`

The config is a frozen, slotted dataclass with:

- `version: str`, exactly `"nplayer-preflop-v1"`
- `num_players: int`, strict integer 2 through 9
- `button: int`, in `range(num_players)`
- `starting_stacks: tuple[int, ...]`, N positive integers
- `forced_posts: tuple[int, ...]`, N nonnegative integers; at least one positive
- `ranges: tuple[tuple[WeightedCombo, ...], ...]`, N nonempty tuples of unique weighted combos
- `sizing_expressions: tuple[Mapping[str, object], ...]`, nonempty tuple of validated sizing expressions
- `max_raises: int`, positive
- `max_deals: int`, positive
- `max_nodes: int`, positive
- `short_all_in_reopens: bool`
- `continuation: NPlayerContinuation`

`WeightedCombo` is reused from `preflop.py` (exact rational weights, normalized two-card combos).

Validation is strict and rejects bool-as-int. Every per-seat tuple has length N. Stacks are positive. Forced posts are nonnegative and do not exceed stacks. At least one post is positive (the effective big blind). Every range is a nonempty tuple of unique `WeightedCombo` values with finite positive weights and normalized two-card combinations. Sizing expressions are validated per the existing `validate_size_expression` contract. `max_raises`, `max_deals`, and `max_nodes` are positive strict integers.

The config detaches the caller's nested sizing expressions into private immutable mappings.

### 2.2 `NPlayerContinuation`

A frozen, slotted dataclass:

- `kind: str`, exactly `"terminal-table"`
- `payoff_table: Mapping[ContinuationKeyN, tuple[Fraction, ...]]`
- `provenance: str`, nonempty

Where `ContinuationKeyN = tuple[DealN, tuple[Action, ...]]` and `DealN = tuple[tuple[int, int], ...]` of length N.

Validation requires:
- Each key is a valid N-deal plus action history
- Each value is an N-tuple of finite exact rationals summing to zero
- The config detaches the caller mapping into a private dictionary and exposes it through `MappingProxyType`

### 2.3 `NPlayerPreflopPublicAction`

A frozen, slotted public-history record:

- `actor: int`
- `action: Action`

The actor is explicit because identical `CHECK`, `CALL`, or `FOLD` values from different seats are different public histories. The CFR legal-action interface remains `tuple[Action, ...]`.

### 2.4 `NPlayerPreflopState`

The frozen, slotted state contains:

- `config`, `private_deal`, and `acting_player`
- Exact integer `pot`
- N-tuples `street_committed`, `total_contributed`, and `remaining`
- Positive `last_raise_increment`
- Bounded `raise_count`
- N-tuple `acted: tuple[bool, ...]`
- N-tuple `can_raise: tuple[bool, ...]`
- `history: tuple[NPlayerPreflopPublicAction, ...]`
- `terminal_values: tuple[Fraction, ...] | None`

It implements `NPlayerGameState`: `num_players`, `current_player`, `legal_actions`, `chance_outcomes`, `child`, `information_state_key`, and `returns`.

## 3. Exact State Invariants

Every direct construction and every child validates:

1. All per-seat tuples have length N and strict element types.
2. `pot == sum(total_contributed)`.
3. `remaining[i] + total_contributed[i] == starting_stacks[i]`.
4. `0 <= street_committed[i] <= total_contributed[i]`.
5. `0 <= raise_count <= max_raises`; `last_raise_increment > 0`.
6. Chance root has no deal/history/settlement and uses baseline forced posts in the pot, posts as current-street commitments, and derived remaining stacks.
7. Every dealt state uses a compatible configured deal.
8. Terminal has exactly N exact rational utilities summing to zero.
9. Nonterminal has no terminal values.

## 4. Deterministic Bounded Private Deals

Reuse the S2 deal enumerator logic: iteratively walk the Cartesian product in seat/range tuple order while carrying a used-card set. Prune collisions immediately. A valid deal has 2N unique private cards. Before multiplication, each validated public float weight is converted deterministically with `Fraction(str(weight))`; deal masses and their total therefore use exact rational arithmetic until the final public probability conversion.

For the new API, `max_deals` bounds candidate Cartesian products before enumeration: `prod(len(range_i)) <= max_deals`. This gives a real work bound even when blockers make every candidate invalid. Compatible results are never silently truncated. No compatible deal and zero total mass fail closed.

Chance actions are `Action("DEAL", index)` in deterministic result order. Exact masses are summed before conversion; public float probabilities are finite, nonnegative, and sum to one within `1e-12`.

## 5. Betting Round Semantics

### 5.1 Root and Order

The chance root has:

- `pot = sum(config.forced_posts)`
- `total_contributed = config.forced_posts`
- `street_committed = config.forced_posts`
- `remaining = starting_stacks - forced_posts`
- `last_raise_increment = max(forced_posts)` (the effective big blind)
- `acted = (False,) * N`
- `can_raise = (True,) * N`

After a private deal, the first seat to act is the seat clockwise after the button. Action proceeds clockwise. `_ordered_after(seat, candidates, num_players)` scans clockwise with wraparound and returns every candidate in that canonical order.

### 5.2 Legal Actions

For acting seat `p`, derive the live high-water mark `H = max(street_committed)`, own street commitment, and `to_call = H - own`.

- If `to_call == 0`, offer `CHECK`.
- Otherwise offer `FOLD` and `CALL(own + min(to_call, remaining[p]))`.
- A raise requires current entitlement (`can_raise[p]`), chips beyond the call, and `raise_count < max_raises`.
- Deduplicate configured sizing expression targets in declared order, then consider the all-in target.
- A normal raise target is at least `H + last_raise_increment`.
- A below-minimum raise is legal only when it is the actor's all-in target.
- Action amounts are absolute current-street commitments.

Folding when checking is possible is not exposed, preserving the Phase-3 contract.

### 5.3 Transition and Closure

Keep `old_can_raise` and old acted flags before applying the action.

- Fold marks the actor as unable to raise.
- Check marks the actor as acted.
- Call transfers the exact target delta to pot/contribution and marks the actor as acted; an all-in caller becomes non-actionable.
- Raise transfers the exact delta, increments `raise_count`, and rebuilds acted/can_raise flags.

For a full raise (`target - old_H >= last_raise_increment`), update the increment and reopen raising for all seats with chips. For a short all-in raise, do not update the increment: seats that had already acted retain their prior entitlement if `short_all_in_reopens` is true, otherwise they cannot re-raise. The short raiser has no chips and cannot raise.

After each action, terminate when:
1. All seats have acted and commitments are matched, OR
2. All but one seat have folded, OR
3. All active seats are all-in and commitments are matched.

Before closing, refund any unmatched excess (e.g., a short all-in call leaves the rich player with excess). The maximum decision depth is structurally bounded by `N + max_raises * (N - 1)`.

## 6. Settlement and Continuation

When the betting round closes:

1. Refund unique unmatched excess with `refund_uncalled_excess`.
2. Add refunds to remaining stacks; replace total contributions and pot by matched amounts; reduce street commitments by refunds.
3. If all but one seat have folded, award the pot to the sole live player and compute exact utilities.
4. Otherwise, look up the continuation key `(private_deal, history)` in `config.continuation.payoff_table` and use the supplied exact rational utilities.
5. Verify zero-sum conservation.

Independent permanent fixtures hand-derive contribution levels, refunds, fold outcomes, continuation keys, and utilities for 2/6/9 seats. The tests do not use the settlement functions to calculate expected results.

## 7. Information and Strategy Integrity

An information key includes rules/version identity, N, owner, owner private combo, button, all public ledgers, last increment, raise count, acted flags, raise entitlements, acting seat, sizing expressions, continuation kind/provenance, and actor-labelled history.

It excludes all opponent private cards, deal index, iterator position, and hidden continuation values. If a public field can change legal actions or settlement, it is part of the key.

Permanent 6- and 9-player tests vary opponent cards and hidden continuation values while holding owner/public state fixed and require equal owner keys; changing the owner's combo requires a different key. `collect_nplayer_infosets` remains the owner/action-consistency oracle.

Strategies returned by the solve facade are detached nested mappings with finite nonnegative probabilities summing to one. Repeated deterministic runs produce equal values, diagnostics, and serialized strategy.

## 8. Solver, Reach, and Exact Deviation Diagnostic

Reuse `NPlayerCFRSolver`, `expected_values_nplayer`, and `unilateral_deviation_certificate`.

`NPlayerCFRSolver` already carries one realization reach per player and chance reach. A regret update for player i is weighted by chance times every opponent reach, excluding i's own reach. S3 adds no duplicate reach tracker.

S3 passes `config.max_nodes` and the structural depth bound `2 + N + max_raises * (N - 1)` to `NPlayerCFRSolver`.

`NPlayerPreflopSolveResult` contains detached strategy, N expected values, optional `UnilateralDeviationCertificate`, and truthful metadata. `solve_nplayer_preflop` supports deterministic `vanilla-cfr` only, positive iterations, and an optional positive `max_pure_strategies`. When requested, the exact exhaustive diagnostic runs or fails closed on its cap. It is never sampled and is never described as Nash convergence.

A six-player permanent oracle manually enumerates each player's tiny pure-deviation set and compares profile values, best-response values, incentives, and total incentive. A separate one-iteration six-player reach oracle checks the exact counterfactual scaling. Nine-player acceptance uses a deliberately tiny finite tree and makes no scalability claim.

## 9. Strict v4 and CLI Surface

Add direct v4 operation `solve-nplayer-preflop`. It follows the existing strict envelope and direct request style. The JSON request uses arrays for N-length fields and a deterministic `continuations` list whose entries contain `deal` and `values`; JSON never attempts tuple-key maps.

The parser rejects unknown/missing fields, bool numerics, nonfinite weights, wrong N-length arrays, duplicate continuation deals, malformed sizing objects, unsupported algorithms/seeds, and all bound violations. It constructs immutable tuples and a detached typed mapping.

The existing `phase4 REQUEST --json` command already forwards to `dispatch_v4`; no new parser shape is introduced. Add canonical synthetic 2-, 6-, and 9-player direct-request examples with tiny bounded trees.

After typed/API acceptance, update the v3 capability manifest truthfully:

- status `implemented-bounded`
- players `[2, 9]`
- streets `preflop-one-round`
- interfaces `typed`, `json-v4`, `cli-phase4`
- deviation `exhaustive-diagnostic-only`

Package-root exports are additive. Legacy v1-v4 operations and HU preflop capability behavior remain covered by regression tests.

## 10. TDD Implementation Batches

### S3-I1 — Typed state and exact ledger

Implementation files: new `src/poker_solver/nplayer_preflop.py` only. Legacy preflop and generic solver files remain unchanged.

Permanent RED owners cover these nonoverlapping files:

1. `tests/test_nplayer_preflop_config.py`: config validation, defensive copy, bounded deterministic deals
2. `tests/test_nplayer_preflop_betting.py`: betting order, pending closure, full/short all-in reopening, direct-state invariants
3. `tests/test_nplayer_preflop_settlement.py`: 2/6/9 refunds, fold outcomes, continuation lookup, and hand ledgers
4. `tests/test_nplayer_preflop_information.py`: information noninterference and old/new HU observational trace equivalence

HU equivalence is not raw object, version-string, history-record, or information-key equality. The oracle projects both paths to chance deals/probabilities, clockwise actors, legal `Action` tuples, pot/commitment/remaining ledgers, terminal utilities, and owner information partitions, then requires equal projected traces for frozen Phase-3 fixtures.

Only after the RED receipts may production be implemented. Parent runs all four new modules, `test_preflop.py`, `test_game_structure.py`, and the full suite. The frozen candidate then receives a fresh different non-author audit. Accepted S3-I1 is committed before S3-I2 begins.

### S3-I2 — Solve facade, diagnostics, API, examples

Potential implementation files are `nplayer_preflop.py`, additive bound plumbing in `nplayer.py`, `api_v4.py`, `api_v3.py`, and package exports. The CLI parser should not need modification.

Permanent RED owners cover:

1. `tests/test_nplayer_preflop_solve.py`: 2/6/9 deterministic typed solves, normalized strategies, values, reach oracle, exact 6+ deviation certificate, and mandatory solver constructor bounds
2. `tests/test_api_v4_nplayer_preflop.py`: strict v4 schema and response isolation
3. `tests/test_phase4_s3_examples.py`: canonical examples and generic CLI file/stdin/error behavior
4. `tests/test_phase4_s3_exports.py`: package exports, capability truth, legacy v1-v4 compatibility

Production ownership is nonoverlapping; parent integrates shared exports/capability fields after RED. Focused and full regression precede a frozen candidate, fresh different non-author audit, parent verification, and accepted-wave commit.

## 11. Mandatory Acceptance Matrix

S3 is complete only when all are executable and green:

- Strict configs accept every N from 2 through 9 and reject malformed lengths/types/bounds
- 2-, 6-, and 9-player spots build, validate, train/evaluate, and return N values
- Chance mass, blocker filtering, deterministic deal order, and `max_deals` fail-closed behavior pass
- Every transition conserves stacks/pot and obeys clockwise action/reopening rules
- Hand-derived refunds, fold outcomes, and continuation lookups match exactly
- Terminal utility conserves exactly (zero-sum)
- 6- and 9-player opponent-card noninterference passes
- Policies are normalized and deterministic
- A six-plus-player exact unilateral-deviation diagnostic matches independent enumeration below its cap
- The generic N=2 projected trace matches the frozen Phase-3 HU deals, actions, public ledgers, settlement, utilities, and information partitions without requiring raw key/history identity
- All old HU preflop tests and the entire prior suite remain green
- Strict v4, generic CLI, examples, exports, and capability truth pass
- Every implementation batch has a fresh, different non-author adversarial audit and an accepted-wave commit
- Tag `phase3-398-green` remains present

## 12. Provenance and Boundaries

Truthful provenance:

`bounded deterministic 2-9-player one-round preflop CFR with exact integer forced-post settlement, caller-supplied terminal continuations, and optional exhaustive finite unilateral-deviation diagnostic`

Do not claim GTO convergence, practical large-range nine-player performance, automatic multi-street solving, automatic rank evaluation, sampled exploitability, or unrestricted solving.
