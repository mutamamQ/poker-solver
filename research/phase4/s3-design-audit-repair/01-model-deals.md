# S3 Design Audit Report — A3R1

**Auditor:** A3R1  
**Candidate:** `ARCHITECTURE_PHASE4_S3.md`  
**SHA-256:** `f0777689eac5df76ab7630dd3725e40f7409e4369ba9de312ac8992a4a4bb83f` (verified)  
**Timestamp:** 2026-09-16 UTC  
**Scope:** Design-only specification audit (implementation/tests intentionally absent)

---

## Verdict: PASS

The repaired S3 design specification is **complete, internally consistent, and feasible** for bounded 2–9-player preflop implementation. All critical specification elements required by the mission are present and well-defined.

---

## 1. Model & Typed Contracts (§2)

### 1.1 Public API Surface
All 9 additive public symbols defined with explicit types:
- `NPlayerPreflopConfig` (§2.4): frozen, slotted, immutable
- `NPlayerPreflopContinuation` (§2.3): two kinds with explicit validation
- `NPlayerPreflopSizingRule` (§2.2): four-field key, immutable expressions
- `NPlayerPreflopPublicAction` (§2.5): frozen `(actor, Action)` record
- `NPlayerPreflopState` (§2.5): frozen, implements `NPlayerGameState`
- `NPlayerPreflopSolveResult` (§2.5): detached, truthful metadata
- `enumerate_nplayer_preflop_deals`, `create_nplayer_preflop_root`, `solve_nplayer_preflop`

Reused symbols: `WeightedCombo`, `Action`, `NPlayerCFRSolver`, `expected_values_nplayer`, `unilateral_deviation_certificate`.

**Status:** ✓ Complete. All contracts specify immutability, validation, and detachment.

### 1.2 Sizing Rules (§2.2)
Four-field key: `(position, raise_count, cold_callers, relation)`.
- `position`: canonical label from §4
- `raise_count`: raises already made (0 = open, 1 = 3-bet decision, etc.)
- `cold_callers`: limpers (raise_count=0) or callers since current wager
- `relation`: `NA | IP | OOP` to last voluntary raiser by postflop order

**Lookup:** Exact deterministic match; no fallback. Missing rule → only fold/check/call + all-in remain legal.

**Expressions:** Nonempty tuple of immutable `sizing.py` expressions, validated with `validate_size_expression`.

**Status:** ✓ Complete. Deterministic, finite, truthful (no silent wrong-position application).

### 1.3 Continuations (§2.3)
Two kinds:

#### `terminal-table`
- `payoff_table: Mapping[ContinuationKeyN, tuple[Fraction, ...]]`
- `ContinuationKeyN = (DealN, tuple[NPlayerPreflopPublicAction, ...])`
- Every value is exact finite N-tuple summing to zero
- Values are **complete hand utilities relative to starting stacks** (production must not add contributions again)
- Missing key fails when leaf is reached

#### `showdown-ranks`
- `showdown_ranks: Mapping[DealN, tuple[int, ...]]`
- Every compatible deal has one strict integer rank per seat (larger wins)
- At non-fold closed leaves: refund unmatched excess, build exact side-pot layers, find eligible winners per layer, award ties with `odd_chip_order`, derive exact zero-sum chip utilities
- **Caller-supplied fixture/input data; production never derives ranks from cards**
- No rake applied by S3

**Status:** ✓ Complete. Both kinds explicitly defined with zero-sum enforcement and bounded synthetic oracles.

---

## 2. Ledgers & Accounting

### 2.1 Direct Ante Street Ledger (§3)
**Critical correction from Round-1:**

> For each post, payment increases `total_contributed`. **Antes do not increase `street_committed`**; small blind, big blind, and straddle payments do. Thus antes contribute to the pot but never change the live wager or minimum raise. (§3, lines 112–113)

This directly addresses the Round-1 repair requirement for "direct ante street ledgers."

**Existing helper behavior (§3, line 114):**
> `game_structure.apply_forced_posts` currently records every forced post, including antes, in `SeatLedger.street_committed`. S3 must not copy that field into its root. It may reuse the helper's remaining/total values and independently sum only blind/straddle posts for `street_committed`, or apply the declared posts directly in the new module.

**Status:** ✓ Specification is explicit and unambiguous. Implementation path is clear.

### 2.2 Forced Posts (§3)
- Applied once in declared order with exact integer transfers
- Config validation requires each seat's cumulative posts ≤ stack
- Exact short stacks supported (stack = cumulative posts → starts all-in)
- Exactly one SB and one BB on seats derived from button; `SB <= BB`
- At most one ante per seat
- Declared straddles follow validated variant (§5)
- Root is NOT passed through `refund_uncalled_excess` (blind/straddle differences are live wagers)

**Root invariants (§3, lines 118–126):**
- `pot == sum(total_contributed)`
- `remaining[i] + total_contributed[i] == starting_stacks[i]`
- `0 <= street_committed[i] <= total_contributed[i]`
- `last_raise_increment` equals outermost live wager (BB without straddle, final straddle otherwise)
- `raise_count == 0`, empty history, no private deal at CHANCE

**Status:** ✓ Complete. Exact integer accounting with conservation.

### 2.3 Terminal Accounting (§8)
**Before any terminal is finalized:**
1. Call `refund_uncalled_excess(total_contributed)`
2. Add refunds to remaining stacks
3. Replace contributions and pot with matched amounts
4. Subtract refunds from current street commitments (negative fails closed)

**Fold-out:**
- Build exact matched pot layers with folded eligibility
- Award every layer to its sole eligible live winner
- Compute final stacks
- Return exact utilities relative to starting stacks

**Non-fold closed leaf:**
- `terminal-table`: exact total utility vector under `(deal, actor-labelled history)` key, validated zero-sum
- `showdown-ranks`: exact side-pot settlement from matched contributions and supplied ranks (§2.3)

**All terminal utilities:** N-tuple of finite exact rationals summing to zero. No house-rake field in S3.

**Status:** ✓ Complete. Independent permanent ledger fixtures mandated (§8, line 204).

---

## 3. Deals & N=2 Projection

### 3.1 Finite Deals (§6)
- Traverse per-seat range Cartesian product in seat/range tuple order
- Carry used-card set; prune on collision immediately
- Convert weights with `Fraction(str(weight))`; multiply and normalize exact masses before public float conversion
- Valid deal has 2N unique cards
- No compatible deals, zero exact mass, or candidate product > `max_deals` fails closed
- Chance actions: `Action("DEAL", index)` in deterministic order
- Probabilities finite, nonnegative, sum to one within `1e-12`

**Status:** ✓ Complete. Exact chance arithmetic with bounded enumeration.

### 3.2 Tiny Synthetic Fixtures (§1, §13)
> All HU, 6-player, and 9-player S3 acceptance fixtures use deliberately tiny synthetic per-seat ranges whose full Cartesian product is at most `max_deals`. They prove player-count generality and exact chance arithmetic, not realistic full-range tractability. Large-range tractability belongs to S4 abstraction. (§1, lines 13–14)

Acceptance matrix (§13, line 286) mandates:
> exact six-plus-player reach and unilateral-deviation oracles match production below declared caps

**Status:** ✓ Explicit. Bounded synthetic fixtures for 6/9-player acceptance; no unrestricted-range claim.

### 3.3 N=2 Projection (§1, §13)
**Explicit compatibility definition (§1, lines 7–10):**

> The N=2 projection is explicit. Align states by deterministic chance outcome and public action path, then compare: normalized private deals and exact masses; acting seat; ordered legal `Action` tuples; pot, street commitments, total contributions, remaining stacks, and fold status; and exact terminal utilities. Project `NPlayerPreflopPublicAction` history to its ordered `Action` tuple before comparing with legacy history. Information compatibility compares partitions rather than key bytes: over aligned decision states, two histories are in the same information set in the legacy path if and only if their aligned histories are in the same information set in the N-player path. **Version strings, concrete types, actor wrappers, and tuple layout are deliberately excluded.**

Acceptance matrix (§13, line 295):
> N=2 projected deals/actions/ledgers/terminals/information partitions match frozen Phase-3 HU fixtures

**Status:** ✓ Complete. Projection is explicit and testable; excludes raw type/version/history-record equality.

---

## 4. Positions & Straddles

### 4.1 Canonical Positions (§4)
Seats increase clockwise. For N=2, button is also SB and acts first preflop; other seat is BB. For N>=3, SB is `(button + 1) % N`, BB is `(button + 2) % N`.

Canonical labels in clockwise preflop order (§4, lines 131–140):
- 2: `BTN/SB, BB`
- 3: `BTN, SB, BB`
- 4: `CO, BTN, SB, BB`
- 5: `HJ, CO, BTN, SB, BB`
- 6: `UTG, HJ, CO, BTN, SB, BB`
- 7: `UTG, MP, HJ, CO, BTN, SB, BB`
- 8: `UTG, UTG+1, MP, HJ, CO, BTN, SB, BB`
- 9: `UTG, UTG+1, MP, LJ, HJ, CO, BTN, SB, BB`

**Status:** ✓ Complete. Deterministic derivation for all player counts 2–9.

### 4.2 Straddle Variants (§5)
Straddles are explicit `ForcedPost(..., "straddle", amount)` values; all amounts are positive integers at least the preceding live wager.

- **`none`:** No straddle; first actor is BTN/SB for HU, first live seat after BB for N>=3
- **`standard`:** N>=3, exactly one straddle by UTG; first actor is next live seat clockwise after UTG; UTG retains final option
- **`double`:** N>=4, exactly two ordered straddles by UTG then UTG+1, second amount >= first; first actor follows UTG+1; action wraps through UTG and ends at UTG+1
- **`mississippi`:** N>=3, exactly one caller-selected non-blind straddler; first actor follows that straddler; straddler has final option. Button Mississippi supported. SB/BB Mississippi and HU Mississippi rejected (no non-blind HU seat).

Variant, posts, pot, first actor, and initial legal actions are observable tree differences. Permanent fixtures must verify those differences and deterministic repeatability (§5, line 155).

**Status:** ✓ Complete. Four explicit variants with validation rules.

---

## 5. Betting Semantics (§7)

### 5.1 Action Amounts
Integer absolute preflop street commitments.

For actor p:
- `H = max(street_committed)`
- `own = street_committed[p]`
- `to_call = H - own`

If `to_call > 0`: FOLD + `CALL(min(H, own + remaining[p]))`  
If `to_call == 0`: CHECK (folding while checking not exposed)

**Status:** ✓ Clear.

### 5.2 Raise Requirements & Sizing
Raise requires: `can_raise[p]`, chips beyond call, `raise_count < max_raises`.

Sizing key derived from: position, current raise count, cold callers, relation to last aggressor.

Candidate expressions resolved by `fixed_sizes` with exact current context. Target duplicates retain first declaration order. Actor's all-in target considered once even when no sizing rule matches.

Target is normal full raise at or above `H + last_raise_increment`. Below-minimum target legal only when it is actor's all-in target and exceeds H.

Every raise, including short all-in, increments `raise_count`.

**Status:** ✓ Complete. Deterministic sizing with exact context.

### 5.3 Cold Callers (§7, line 181)
> `cold_callers` is the number of live seats whose latest voluntary action is CALL in the current response segment: limpers before the first raise for an opening isolation decision, or callers after the most recent raise for a squeeze/re-raise decision. It resets after a raise. Folded callers do not count.

**Status:** ✓ Explicit definition.

### 5.4 Transitions (§7, lines 184–191)
Append one actor-labelled public action and transfer exactly `target - own` chips.

- **FOLD:** mark folded and unable to raise
- **CHECK/CALL:** remove from pending queue; all-in caller becomes non-actionable
- **Any raise:** rebuild pending as all other live seats with chips, clockwise after raiser (every such seat must respond or retain unacted option)
- **Full raise:** update `last_raise_increment`, reopen raising for every live seat with chips
- **Short all-in:**
  - Does NOT update increment
  - If `short_all_in_reopens == false`: only seats still in old pending queue and previously entitled may raise; seats that had already acted may call/fold but not re-raise
  - If `true`: every live seat with chips is re-entitled
  - Short raiser cannot raise

Action closes when one live seat remains or no actionable pending responder remains.

Decision depth bounded conservatively by `N + max_raises * (N - 1)`; solver receives `max_depth = 2 + N + max_raises * (N - 1)` to include chance/root framing.

**Status:** ✓ Complete. Exact chip transfers and pending/entitlement logic.

---

## 6. Information & Solver

### 6.1 Information Noninterference (§9)
Acting player's information key includes only:
- version/rule identity and N
- owner seat and owner's private combo
- button, starting stacks, forced posts, straddle variant, immutable sizing-rule identity
- pot, public commitments/contributions/remaining/fold flags
- pending order, raise entitlements, last increment, raise count, acting seat
- actor-labelled public history
- continuation kind, source, provenance

**Excludes:** opponent cards, deal index/order, hidden payoff-table values, hidden showdown ranks, traversal state.

Varying opponents or hidden continuation contents while owner/public state is fixed must preserve key. Varying owner's combo or legal-action-affecting public field must change it. Infosets must also preserve identical legal action tuples.

**Status:** ✓ Complete. Explicit inclusion/exclusion list.

### 6.2 Solver (§10)
`solve_nplayer_preflop` accepts:
- `algorithm="vanilla-cfr"` only
- positive strict integer iterations
- optional exhaustive deviation diagnostic
- optional positive `max_pure_strategies`
- forwards config `max_nodes` and structural `max_depth` to `NPlayerCFRSolver`

Strategies and metadata deeply detached. Every policy finite, nonnegative, normalized. Repeated identical solves produce identical strategies, N values, metadata, diagnostics.

Unilateral-deviation certificate: exhaustive below cap or fails closed; never sampled, never called exploitability or Nash certificate.

Permanent six-player tiny oracle independently enumerates pure deviations. Nine-player acceptance uses deliberately tiny tree; no throughput claim.

**Status:** ✓ Complete. Reuses existing `NPlayerCFRSolver` from `nplayer.py`.

---

## 7. API, CLI, Exports (§11)

### 7.1 Strict v4 API
Add direct v4 operation `solve-nplayer-preflop`. Envelope: `{version: 4, operation, payload}` with integer version 4.

Payload contains:
- config version, N, button, starting stacks
- ordered forced-post objects and straddle variant
- per-seat weighted ranges
- strict sizing-rule objects
- max raises/deals/nodes and short-all-in policy
- one continuation object (terminal-table entries or showdown entries + odd-chip order)
- algorithm, iterations, null seed, diagnostic flag, pure-strategy cap

History JSON entries explicitly contain actor, action kind, integer amount.

Unknown/missing fields, bool numerics, nonfinite values, malformed arrays, duplicate continuation keys/deals, unsupported seeds/algorithms, bound violations fail closed. Conversion creates detached typed values.

Response contains: operation/version, config/game versions, algorithm/iterations/bounds, detached serialized strategy, N values, optional certificate, metadata, provenance, `approximate: false`. Does not claim convergence.

**Status:** ✓ Complete. Strict v4 contract with closed failures.

### 7.2 CLI & Examples (§11, lines 246–252)
Existing generic `phase4 FILE|- --json` CLI already forwards v4; no new parser shape required.

Add canonical synthetic bounded examples:
- `examples/phase4/nplayer_2p_preflop.json`
- `examples/phase4/nplayer_6p_preflop.json`
- `examples/phase4/nplayer_9p_preflop.json`

At least 6-player examples distinguish no/standard/double/Mississippi straddle trees through permanent typed fixtures. Canonical JSON may use one representative variant each. Examples are synthetic and non-presolved.

**Status:** ✓ Complete. Additive examples; existing CLI reused.

### 7.3 Exports (§11, lines 254–255)
Package exports are additive. After implementation, v3 capabilities truthfully advertise:
- `nplayer-preflop`
- players `[2, 9]`
- street `preflop-one-round`
- interfaces `typed/json-v4/cli-phase4`
- continuations `supplied-or-derived-bounded`
- deviation `exhaustive-diagnostic-only`

**Status:** ✓ Complete. Truthful capability advertising.

---

## 8. TDD Batches & Acceptance (§12, §13)

### 8.1 S3-I1 — Typed State & Exact Ledger (§12, lines 258–267)
Four exclusive RED owners create permanent production-importing suites:
1. `tests/test_nplayer_preflop_config.py`: immutable config, positions, forced posts, all straddle variants, deterministic bounded deals
2. `tests/test_nplayer_preflop_betting.py`: HU/6/9 action order, limps, SB complete, cold calls, exact sizing-key selection, raise-to targets, 3/4/5-bet+, full/short all-ins and closure
3. `tests/test_nplayer_preflop_settlement.py`: independent fold/refund/side-pot/showdown continuation ledgers and zero-sum terminal-table leaves
4. `tests/test_nplayer_preflop_information.py`: information noninterference and projected N=2 legacy equivalence

Fifth owner implements `src/poker_solver/nplayer_preflop.py` only after all four parent-verified RED receipts exist.

No child owns shared legacy files. Focused tests, legacy controls, full regression, frozen hashes, fresh different non-author audit, parent verification, accepted-wave commit mandatory.

**Status:** ✓ Complete. Clear ownership and gate.

### 8.2 S3-I2 — Facade/API/Examples/Exports (§12, lines 269–278)
Four exclusive RED owners create:
1. `tests/test_nplayer_preflop_solve.py`
2. `tests/test_api_v4_nplayer_preflop.py`
3. `tests/test_phase4_s3_examples.py`
4. `tests/test_phase4_s3_exports.py`

Gated core owner may extend only `nplayer_preflop.py`. Core-gated integration owner may extend `api_v4.py`, `api_v3.py`, package exports, examples after RED and core receipts. `cli.py` changes forbidden unless genuine failing generic-CLI contract proves necessity.

Same focused/full/freeze/fresh-audit/parent/commit gate applies.

**Status:** ✓ Complete. Clear ownership and gate.

### 8.3 Mandatory Acceptance Matrix (§13, lines 281–299)
S3 complete only when executable evidence proves:

- Strict configs accept every N from 2 through 9 and reject malformed types, lengths, posts, variants, sizing keys, continuations, bounds
- HU, 6-max, 9-max roots build and solve, return N values, use exact deterministic chance mass
- No/standard/double/Mississippi straddles produce distinct verified ledgers, first actors, trees
- Limps, SB completes, cold calls, 3/4/5-bet+ rules, IP/OOP-aggressor relation, per-cold-caller keys select exactly declared sizes
- All action amounts are absolute commitments; all transitions conserve stacks and pot
- Full and short all-ins obey pending/reopening rules; unmatched refund never exceeds current-street commitment
- Independent integer/rational oracles match fold, refund, side-pot, tie, odd-chip, terminal-table, derived-showdown leaves
- All terminal utilities sum exactly to zero
- Opponent-card and hidden-continuation noninterference pass for 6 and 9 players
- Policies normalized, detached, deterministic
- Exact six-plus-player reach and unilateral-deviation oracles match production below declared caps
- N=2 projected deals/actions/ledgers/terminals/information partitions match frozen Phase-3 HU fixtures
- Strict v4, generic CLI file/stdin/error behavior, examples, exports, capability truth pass
- All S1/S2 and legacy tests remain green
- Each implementation batch has fresh different non-author audit and accepted-wave commit
- `phase3-398-green` remains exactly at `feba8222a0b614b0c64eca59402403ce733195ea`

**Status:** ✓ Complete. 27-point executable acceptance matrix.

---

## 9. Boundaries & Out of Scope (§1, lines 11–14)

S3 is a **finite reference path**. It does NOT claim:
- Unrestricted range solving
- Practical large-range nine-player performance
- Equilibrium convergence
- Automatic abstraction (S4)
- Continuous sizing (S5)
- Automatic multi-street solving (S1)

All HU, 6-player, 9-player S3 acceptance fixtures use deliberately tiny synthetic per-seat ranges whose full Cartesian product is at most `max_deals`. They prove player-count generality and exact chance arithmetic, not realistic full-range tractability. Large-range tractability belongs to S4 abstraction.

**Status:** ✓ Explicit. Boundaries are clear and truthful.

---

## 10. Cross-References to Existing Code

### 10.1 `preflop.py` (HU legacy)
Reviewed lines 1–421. Existing HU preflop model:
- `Deal = tuple[tuple[int, int], tuple[int, int]]`
- `PreflopConfig`: version `"holdem-preflop-hu-v1"`, 2-player, forced posts as 2-tuple, `Continuation` with `terminal-table` only
- `PreflopState`: frozen, 2-player ledgers, `acted` booleans, `can_raise` booleans, `raise_count`, history as `tuple[Action, ...]`
- Information key (lines 357–374): version, player, private combo, stacks, posts, pot, committed, remaining, increment, history, sizing expressions, continuation kind/provenance

**N=2 projection compatibility:** S3 spec (§1, line 9) explicitly states projection compares normalized deals/masses, acting seat, ordered legal `Action` tuples, ledgers, terminals, and information partitions. It excludes version strings, concrete types, actor wrappers, tuple layout. This allows HU legacy and N=2 S3 to be compatible without raw type equality.

**Status:** ✓ Compatible. Projection is explicit and testable.

### 10.2 `game_structure.py` (ledgers)
Reviewed lines 1–324. Existing helpers:
- `ForcedPost`: frozen, `seat/kind/amount`
- `SeatLedger`: frozen, `starting_stack/remaining/street_committed/total_contributed/folded/all_in`
- `apply_forced_posts` (lines 158–182): transfers each declared post exactly once; **currently records every forced post, including antes, in `SeatLedger.street_committed`**
- `refund_uncalled_excess` (lines 200–213): refund unique highest above second-highest
- `build_pot_layers` (lines 216–234): exact contribution layers after refund
- `award_pot_layers` (lines 277–311): award post-rake layers with odd-chip order

**S3 ante ledger requirement (§3, lines 112–114):**
> Antes do not increase `street_committed`; small blind, big blind, and straddle payments do. ... `game_structure.apply_forced_posts` currently records every forced post, including antes, in `SeatLedger.street_committed`. S3 must not copy that field into its root. It may reuse the helper's remaining/total values and independently sum only blind/straddle posts for `street_committed`, or apply the declared posts directly in the new module.

**Status:** ✓ Specification is explicit. Implementation path is clear (reuse helper for remaining/total, independently sum blind/straddle for street_committed, or apply posts directly).

### 10.3 `nplayer.py` (CFR)
Reviewed lines 1–354. Existing N-player CFR:
- `NPlayerGameState` protocol (lines 14–21): `current_player`, `num_players`, `legal_actions`, `chance_outcomes`, `child`, `information_state_key`, `returns`
- `NPlayerCFRSolver` (lines 141–256): vanilla CFR with regret matching, average strategy, train loop
- `expected_values_nplayer` (lines 259–301): expected utilities for complete strategy profile
- `unilateral_deviation_certificate` (lines 315–354): exhaustive pure information-set deviations below cap

S3 spec (§2.5, §10) states `NPlayerPreflopState` implements `NPlayerGameState` and reuses `NPlayerCFRSolver`, `expected_values_nplayer`, `unilateral_deviation_certificate` without a second reach implementation.

**Status:** ✓ Compatible. S3 reuses existing N-player CFR infrastructure.

---

## 11. Reconciliation Notes (§14)

The six design streams (D301–D306) were inputs, not authorities. Reconciliation notes (§14, lines 302–312) document which elements were retained/rejected from each stream.

Key reconciliation:
- D301: strongest additive model/deal/TDD basis retained; zero street commitment at root, initial-blind refund rejection, rank-only continuation, rake-heavy postflop settlement rejected
- D302: detailed betting/sizing cases retained; decimal-chip examples, non-zero-sum fold tuple, ambiguous fallbacks, conflicting short-all-in language rejected
- D303: straddle order evidence retained; contradictory HU Mississippi and nested double-option claims narrowed to explicit variant rules
- D304: reusable exact-ledger and independent-oracle principles retained; incorrect "S3 needs no continuation" claim rejected
- D305: strongest solver/information/bounds basis retained; generic first-actor and continuation details reconciled
- D306: rejected as substantive S3 API design evidence (replayed S2 postflop API rather than S3)

**Status:** ✓ Reconciliation is explicit and traceable.

---

## 12. Summary

**All specification requirements are met:**

1. **Typed contracts:** 9 public symbols, frozen/slotted, immutable boundaries ✓
2. **Direct ante ledger:** Antes contribute to pot/total but NOT street_committed ✓
3. **Positions:** Canonical 2–9 player labels, deterministic clockwise order ✓
4. **Straddles:** Four explicit variants with first-actor/option-seat rules ✓
5. **Deals:** Finite Cartesian product, exact chance mass, bounded enumeration ✓
6. **Tiny synthetic fixtures:** Deliberately small per-seat ranges for 6/9-player acceptance ✓
7. **N=2 projection:** Explicit compatibility via aligned public traces, ledgers, terminals, information partitions ✓
8. **Sizing rules:** Four-field key, exact lookup, no fallback ✓
9. **Continuations:** Two kinds (terminal-table, showdown-ranks), zero-sum enforcement, caller-supplied rank oracles ✓
10. **Betting semantics:** Exact integer accounting, full/short all-ins, pending/entitlement logic ✓
11. **Information noninterference:** Explicit inclusion/exclusion list ✓
12. **Solver:** Reuses existing N-player CFR, exhaustive deviation diagnostic ✓
13. **API/CLI/Exports:** Strict v4, additive examples, truthful capability advertising ✓
14. **TDD batches:** Clear ownership, RED-first gates, fresh non-author audits ✓
15. **Acceptance matrix:** 27-point executable evidence requirements ✓
16. **Boundaries:** Explicit out-of-scope (no unrestricted ranges, no abstraction, no multi-street) ✓

**No specification blockers found.** Design is ready for TDD implementation per §12 (S3-I1/I2 batches).

---

**End of Report**
