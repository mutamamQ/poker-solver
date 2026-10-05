# S3 typed model, positions, forced-post ledger, and finite deal contracts

**Subagent:** D301 (design-only reviewer)  
**Workspace:** `/home/genomix-node/poker-solver`  
**Heartbeat:** `research/phase4/s3-design/.hb/D301`  
**Output:** `research/phase4/s3-design/01-model-posts-deals.md` (this file)  
**UTC:** 2026-09-16 00:27:02  

---

## 1. Scope and reconciliation

S3 delivers a bounded typed 2–9-player preflop configuration and state model with:

- immutable frozen dataclass config and state types;
- explicit seats, positions, button, arbitrary custom per-seat stacks;
- exact integer antes, blinds (SB/BB), and straddles with forced-post ledger;
- finite weighted private deals with deterministic blocker-aware enumeration;
- public history, initial-pot/remaining/contribution invariants;
- unmatched-root policy (reject pre-existing unmatched excess at root);
- exact input validation, information noninterference;
- backward compatibility with Phase-3 heads-up `PreflopConfig`/`PreflopState`.

S3 does NOT deliver multi-street preflop, automatic abstraction, continuous sizing, neural continuation, or practical unbounded 9-player solving. It reuses the existing `game_structure.py` primitives (`ForcedPost`, `apply_forced_posts`, `refund_uncalled_excess`, `build_pot_layers`, `award_pot_layers`, `RakePolicy`) and the generic `NPlayerCFRSolver` from `nplayer.py`.

The new module is `src/poker_solver/preflop_nplayer.py`. Existing `preflop.py` (heads-up) retains its public behavior. Equivalence is proved by tests, not by routing legacy through the new module.

---

## 2. Public typed contracts

### 2.1 `PreflopNPlayerConfig`

Frozen, slotted dataclass with:

- `version: str`, exactly `"preflop-nplayer-v1"`;
- `num_players: int`, strict integer 2 through 9;
- `button: int`, in `range(num_players)`;
- `starting_stacks: tuple[int, ...]`, length N, all positive strict integers;
- `forced_posts: tuple[ForcedPost, ...]`, arbitrary antes/blinds/straddles;
- `ranges: tuple[tuple[WeightedCombo, ...], ...]`, length N, each nonempty;
- `wager_targets: tuple[int, ...]`, absolute raise-to targets, positive, unique, increasing;
- `max_raises: int`, positive;
- `max_deals: int`, positive (bounds Cartesian product before enumeration);
- `max_nodes: int`, positive;
- `short_all_in_reopens: bool`;
- `odd_chip_order: tuple[int, ...]`, exactly a permutation of `range(N)`;
- `showdown_ranks: Mapping[DealN, tuple[int, ...]]`, where `DealN = tuple[tuple[int, int], ...]` of length N;
- `rake_policy: RakePolicy | None = None`.

**Validation (strict, fail-closed):**

1. Reject bool-as-int for all numeric fields.
2. `num_players` in `[2, 9]`.
3. `button` in `range(num_players)`.
4. `starting_stacks` has length N, all positive.
5. `forced_posts` is a tuple of `ForcedPost` values; each `post.seat` in `range(N)`; each `post.amount` nonnegative and does not exceed `starting_stacks[post.seat]`.
6. At least one forced post is positive (initial pot must be positive).
7. `ranges` has length N; each range is a nonempty tuple of unique `WeightedCombo` values with finite positive weights and normalized two-card combinations.
8. `wager_targets` is a tuple of positive, unique, strictly increasing integers.
9. `max_raises`, `max_deals`, `max_nodes` are positive strict integers.
10. `short_all_in_reopens` is boolean.
11. `odd_chip_order` has length N and is exactly a permutation of `range(N)` (check both length and set equality).
12. `showdown_ranks` is a mapping; each key is a length-N tuple of pairwise-disjoint two-card combos; each value is a length-N tuple of strict integers (larger wins). The config detaches the caller mapping into a private dictionary and exposes it through `MappingProxyType`.
13. Initial contribution ledger (after applying forced posts) must already be matched: `refund_uncalled_excess(initial_contributions).refunds == (0,) * N`. A preflop root carrying pre-existing unmatched excess is invalid because that excess should have been refunded on the preceding street. Reject it before deal enumeration or solving. This guarantees that unmatched excess created by the S3 round does not exceed the winner's current `street_committed` amount.
14. `rake_policy` is `RakePolicy | None`.

All nested mutable inputs (sizing expressions, showdown mapping) are defensively copied into immutable tuples/proxies.

### 2.2 `PreflopNPlayerPublicAction`

Frozen, slotted public-history record:

- `actor: int`;
- `action: Action`.

The actor is explicit because identical `CHECK`, `CALL`, or `FOLD` values from different seats are different public histories. The CFR legal-action interface remains `tuple[Action, ...]`.

### 2.3 `PreflopNPlayerState`

Frozen, slotted state:

- `config: PreflopNPlayerConfig`;
- `private_deal: DealN | None`;
- `acting_player: int` (CHANCE, TERMINAL, or seat index);
- exact integer `pot`;
- N-tuples `street_committed`, `total_contributed`, `remaining`;
- N-tuple `folded: tuple[bool, ...]`;
- ordered unique `pending: tuple[int, ...]` responders;
- N-tuple `can_raise: tuple[bool, ...]`;
- positive `last_raise_increment: int`;
- bounded `raise_count: int`;
- `history: tuple[PreflopNPlayerPublicAction, ...]`;
- `terminal_values: tuple[int, ...] | None`;
- nonnegative integer `house_rake`.

Implements `NPlayerGameState`: `num_players`, `current_player`, `legal_actions`, `chance_outcomes`, `child`, `information_state_key`, `returns`.

---

## 3. Exact state invariants

Every direct construction and every child validates:

1. All per-seat tuples have length N and strict element types.
2. `pot == sum(total_contributed)`.
3. `remaining[i] + total_contributed[i] == starting_stacks[i]`.
4. `0 <= street_committed[i] <= total_contributed[i]`.
5. Folded/all-in seats are not pending. Pending seats are unique, in range, live, have chips, and ordered clockwise for their current response cycle.
6. A dealt nonterminal has nonempty pending and `acting_player == pending[0]`.
7. Folded/all-in seats cannot raise. `0 <= raise_count <= max_raises`; `last_raise_increment > 0`.
8. Chance root has no deal/history/settlement and uses baseline contributions (after forced posts) in the pot, zero current-street commitments, and derived remaining stacks.
9. Every dealt state uses a compatible configured deal.
10. Terminal has empty pending, exactly N integer utilities, and `sum(terminal_values) + house_rake == 0`.
11. Nonterminal has no terminal values and zero house rake.

Status is derived, not duplicated: folded from `folded[i]`, all-in from live plus `remaining[i] == 0`, and active from live plus positive remaining.

---

## 4. Deterministic bounded private deals

The deal enumerator iteratively walks the Cartesian product in seat/range tuple order while carrying a used-card set seeded by an empty set (preflop has no board). It prunes collisions immediately. A valid deal has 2N unique private cards.

Before multiplication, each validated public float weight is converted deterministically with `Fraction(str(weight))`; deal masses and their total therefore use exact rational arithmetic until the final public probability conversion. Recursive retry-until-compatible enumeration is forbidden.

For the new API, `max_deals` bounds candidate Cartesian products before enumeration: `prod(len(range_i)) <= max_deals`. This gives a real work bound even when blockers make every candidate invalid. Compatible results are never silently truncated. No compatible deal and zero total mass fail closed.

Chance actions are `Action("DEAL", index)` in deterministic result order. Exact masses are summed before conversion; public float probabilities are finite, nonnegative, and sum to one within `1e-12`.

At root construction, every compatible deal must have exact showdown-rank coverage because strict config validation requires at least one positive forced post (initial pot positive) and at least two initially live seats. Missing, duplicate, malformed, or extra deal records fail before solving; later fold-out branches do not weaken this root coverage rule.

---

## 5. Positions and forced-post ledger

### 5.1 Positions

Positions are derived from `button` and `num_players`:

- **Heads-up (N=2):** button is seat 0, acts first preflop; big blind is seat 1, acts second preflop (postflop order reverses, but S3 is preflop-only).
- **3+ players:** button is the dealer; small blind (SB) is the first seat clockwise after button; big blind (BB) is the second seat clockwise after button; action starts with the seat after BB (under-the-gun, UTG) and proceeds clockwise.

Positions are labels, not stored state. The config stores `button` and `num_players`; the state machine derives action order from `button`, `pending`, and clockwise traversal.

### 5.2 Forced-post ledger

The config's `forced_posts` is a tuple of `ForcedPost(seat, kind, amount)` where `kind` is `"ante"`, `"small-blind"`, `"big-blind"`, or `"straddle"`.

**Ledger construction (at root):**

1. Start with `starting_stacks`.
2. Apply each forced post exactly once using `apply_forced_posts(starting_stacks, forced_posts)`, which returns a tuple of `SeatLedger` values.
3. Extract `total_contributed` and `remaining` from the ledgers.
4. Validate that `refund_uncalled_excess(total_contributed).refunds == (0,) * N` (unmatched-root policy).
5. Set `pot = sum(total_contributed)`, `street_committed = (0,) * N`, and derive initial `pending` as active seats clockwise after the button.

**Straddles:**

- A straddle is a voluntary blind larger than the BB, posted by a seat (typically UTG or button in some variants).
- The config explicitly declares straddles via `ForcedPost(seat, "straddle", amount)`.
- Multiple straddles are supported (e.g., double straddle, Mississippi straddle) as long as each is explicitly declared.
- The initial `last_raise_increment` is the largest forced post amount (typically the straddle or BB if no straddle).

**Antes:**

- Antes are posted by every seat (or a subset, as declared).
- The config explicitly declares antes via `ForcedPost(seat, "ante", amount)`.
- Antes do not affect the initial raise increment; the increment is derived from blinds/straddles.

---

## 6. Betting round semantics

### 6.1 Root and order

The chance root has:

- `pot = sum(initial_contributions)` (after forced posts);
- `total_contributed = initial_contributions`;
- `street_committed = (0,) * N`;
- `remaining = starting_stacks - initial_contributions`;
- `pending` equal to active seats clockwise after the button (or after the last straddle, if any);
- `can_raise[i]` true exactly for active seats;
- `last_raise_increment = max(post.amount for post in forced_posts if post.kind in {"big-blind", "straddle"})` when present, otherwise `1`.

After a private deal, the first pending seat acts. `_ordered_after(seat, candidates)` scans clockwise with wraparound and returns every candidate in that canonical order.

### 6.2 Legal actions

For acting seat `p`, derive the live high-water mark `H`, own street commitment, and `to_call = H - own`.

- If `to_call == 0`, offer `CHECK`.
- Otherwise offer `FOLD` and `CALL(own + min(to_call, remaining[p]))`.
- A raise requires current entitlement, chips beyond the call, and `raise_count < max_raises`.
- Deduplicate configured targets in declared order, then consider the all-in target.
- A normal raise target is at least `H + last_raise_increment`.
- A below-minimum raise is legal only when it is the actor's all-in target.
- Action amounts are absolute current-street commitments.

Folding when checking is possible is not exposed, preserving the Phase-3 contract.

### 6.3 Transition and closure

Keep `old_pending` and old raise entitlements before applying the action.

- Fold marks the actor folded and unable to raise.
- Check removes the actor from pending.
- Call transfers the exact target delta to pot/contribution and removes the actor; an all-in caller becomes non-actionable.
- Raise transfers the exact delta, increments `raise_count`, and rebuilds pending as every other active seat clockwise after the raiser.

For a full raise (`target - old_H >= last_raise_increment`), update the increment and reopen raising for all active seats. For a short all-in raise, do not update the increment: seats still in `old_pending` retain their prior entitlement, while seats that had already acted cannot re-raise. The short raiser has no chips and cannot raise.

After each action, terminate when one live seat remains or pending is empty. Otherwise `acting_player` is the first pending seat. All live all-in seats being non-actionable therefore closes the round. The maximum decision depth is structurally bounded by `N + max_raises * (N - 1)`.

---

## 7. Settlement and independent accounting oracle

Settlement is integer-only:

1. Refund unique unmatched excess with `refund_uncalled_excess`.
2. Add refunds to remaining stacks; replace total contributions and pot by matched amounts; reduce street commitments by refunds and reject negative results. The validated matched root ledger guarantees that a legal final refund comes entirely from this round's commitment.
3. Build layers with `build_pot_layers(matched, folded=folded_set)`.
4. For showdown, find the highest eligible rank independently per layer. A sole live player wins every layer without rank lookup.
5. Calculate one hand-level rake from `eligible_pot = sum(layer.amount for layer in layers)`, the matched post-refund pot, and allocate it by the configured layer order.
6. Award net layers and ties through `award_pot_layers` and declared odd-chip order.
7. Pad awards to N seats when zero-contribution trailing seats are absent from the primitive's output.
8. Compute final stacks and utilities and verify both conservation equations.

Independent permanent fixtures hand-derive contribution levels, contributors, eligibility, winners, rake, remainder recipients, awards, final stacks, and utilities for 2/3/6/9 seats. The tests do not use the settlement functions to calculate expected results.

With no rake, player utilities sum to zero. With rake, player utilities sum to negative house rake and player-plus-house utility is exactly zero. This is the mission's "zero-sum including side pots" contract.

---

## 8. Information and strategy integrity

An information key includes rules/version identity, N, owner, owner private combo, button, all public ledgers/fold flags, pending order, raise entitlements, last increment, raise count, acting seat, wager targets, and actor-labelled history.

It excludes all opponent private cards, deal index, iterator position, and hidden showdown ranks. If a public field can change legal actions or settlement, it is part of the key.

Permanent 3-, 6-, and 9-player tests vary opponent cards and hidden showdown ranks while holding owner/public state fixed and require equal owner keys; changing the owner's combo requires a different key. `collect_nplayer_infosets` remains the owner/action-consistency oracle.

Strategies returned by the solve facade are detached nested mappings with finite nonnegative probabilities summing to one. Repeated deterministic runs produce equal values, diagnostics, and serialized strategy.

---

## 9. Solver, reach, and exact deviation diagnostic

Reuse `NPlayerCFRSolver`, `expected_values_nplayer`, and `unilateral_deviation_certificate`.

`NPlayerCFRSolver` already carries one realization reach per player and chance reach. A regret update for player i is weighted by chance times every opponent reach, excluding i's own reach. S3 adds no duplicate reach tracker.

The constructor forwards `max_nodes`/`max_depth` to `collect_nplayer_infosets`, and the solve facade passes `config.max_nodes` plus the structural depth bound.

`PreflopNPlayerSolveResult` contains detached strategy, N expected values, optional `UnilateralDeviationCertificate`, and truthful metadata. `solve_preflop_nplayer` supports deterministic `vanilla-cfr` only, positive iterations, and an optional positive `max_pure_strategies`. When requested, the exact exhaustive diagnostic runs or fails closed on its cap. It is never sampled and is never described as Nash convergence.

A six-player permanent oracle manually enumerates each player's tiny pure-deviation set and compares profile values, best-response values, incentives, and total incentive. A separate one-iteration six-player reach oracle checks the exact counterfactual scaling. Nine-player acceptance uses a deliberately tiny finite tree and makes no scalability claim.

---

## 10. Strict v4 and CLI surface

Add direct v4 operation `solve-preflop-nplayer`. It follows the existing strict envelope and direct request style. The JSON request uses arrays for N-length fields and a deterministic `showdowns` list whose entries contain `deal` and `ranks`; JSON never attempts tuple-key maps.

The parser rejects unknown/missing fields, bool numerics, nonfinite weights, wrong N-length arrays, duplicate showdown deals, malformed rake objects, unsupported algorithms/seeds, and all bound violations. It constructs immutable tuples and a detached typed mapping.

The existing `phase4 REQUEST --json` command already forwards to `dispatch_v4`; no new parser shape is introduced. Add canonical synthetic 2-, 3-, 6-, and 9-player direct-request examples with tiny bounded trees.

After typed/API acceptance, update the v3 capability manifest truthfully:

- status `implemented-bounded`;
- players `[2, 9]`;
- streets `preflop-one-round`;
- interfaces `typed`, `json-v4`, `cli-phase4`;
- deviation `exhaustive-diagnostic-only`.

Package-root exports are additive. Legacy v1-v4 operations and heads-up preflop capability behavior remain covered by regression tests.

---

## 11. TDD implementation batches

### S3-I1 — typed state and exact ledger

Implementation files: new `src/poker_solver/preflop_nplayer.py` only. Legacy `preflop.py` and generic solver files remain unchanged.

Permanent RED owners cover these nonoverlapping files:

1. `tests/test_preflop_nplayer_config.py`: config validation, defensive copy, bounded deterministic deals;
2. `tests/test_preflop_nplayer_betting.py`: betting order, pending closure, full/short all-in reopening, direct-state invariants;
3. `tests/test_preflop_nplayer_settlement.py`: 2/3/6/9 side pots, refunds, rake, ties, odd chips, and hand ledgers;
4. `tests/test_preflop_nplayer_information.py`: information noninterference and old/new heads-up observational trace equivalence.

Heads-up equivalence is not raw object, version-string, history-record, or information-key equality. The oracle projects both paths to chance deals/probabilities, clockwise actors, legal `Action` tuples, pot/commitment/remaining/fold ledgers, terminal rake/utilities, and owner information partitions, then requires equal projected traces for frozen Phase-3 fixtures.

Only after the RED receipts may production be implemented. Parent runs all four new modules, `test_preflop.py`, `test_game_structure.py`, and the full suite. The frozen candidate then receives a fresh different non-author audit. Accepted S3-I1 is committed before S3-I2 begins.

### S3-I2 — solve facade, diagnostics, API, examples

Potential implementation files are `preflop_nplayer.py`, additive bound plumbing in `nplayer.py`, `api_v4.py`, `api_v3.py`, and package exports. The CLI parser should not need modification.

Permanent RED owners cover:

1. `tests/test_preflop_nplayer_solve.py`: 2/3/6/9 deterministic typed solves, normalized strategies, values, reach oracle, exact 6+ deviation certificate, and mandatory solver constructor bounds;
2. `tests/test_api_v4_preflop_nplayer.py`: strict v4 schema and response isolation;
3. `tests/test_phase4_s3_examples.py`: canonical examples and generic CLI file/stdin/error behavior;
4. `tests/test_phase4_s3_exports.py`: package exports, capability truth, legacy v1-v4 compatibility.

Production ownership is nonoverlapping; parent integrates shared exports/capability fields after RED. Focused and full regression precede a frozen candidate, fresh different non-author audit, parent verification, and accepted-wave commit.

---

## 12. Mandatory acceptance matrix

S3 is complete only when all are executable and green:

- strict configs accept every N from 2 through 9 and reject malformed lengths/types/bounds or pre-existing unmatched root excess;
- 2-, 3-, 6-, and 9-player spots build, validate, train/evaluate, and return N values;
- chance mass, blocker filtering, deterministic deal order, and `max_deals` fail-closed behavior pass;
- every transition conserves stacks/pot and obeys clockwise pending/reopening rules;
- hand-derived multi-layer refunds, side pots, rake, ties, and odd chips match exactly;
- terminal utility plus house rake conserves exactly;
- 3-, 6-, and 9-player opponent-card noninterference passes;
- policies are normalized and deterministic;
- a six-plus-player exact unilateral-deviation diagnostic matches independent enumeration below its cap;
- the generic N=2 projected trace matches the frozen Phase-3 deals, actions, public ledgers, settlement, utilities, and information partitions without requiring raw key/history identity;
- all old heads-up preflop tests and the entire prior suite remain green;
- strict v4, generic CLI, examples, exports, and capability truth pass;
- every implementation batch has a fresh, different non-author adversarial audit and an accepted-wave commit;
- tag `phase3-398-green` remains present.

---

## 13. Provenance and boundaries

Truthful provenance:

> bounded deterministic 2-9-player one-round preflop CFR with explicit positions, arbitrary stacks, antes/blinds/straddles, finite weighted deals, exact integer forced-post ledger, and optional exhaustive finite unilateral-deviation diagnostic

Do not claim GTO convergence, practical large-range nine-player performance, multi-street play, automatic rank evaluation, sampled exploitability, or unrestricted solving.

---

## 14. Backward compatibility

The existing `preflop.py` (heads-up) remains unchanged. The new `preflop_nplayer.py` is additive. Tests prove observational equivalence for N=2 by projecting both paths to public traces, not by requiring raw object identity.

---

**End of S3 design document.**
