# S2 deals/information audit — A2D4

**Auditor**: A2D4 (fresh non-author S2 design auditor)  
**UTC**: 2026-09-15T21:10:00Z  
**Manifest hash**: `86080aac1013ade96f2fab956f209ffc96cad984cc3c9a423982a8988868473a` ✓  
**Repository**: `/home/genomix-node/poker-solver`  
**Baseline tag**: `phase3-398-green`  

## Scope

Audit deterministic weighted-deal work bounds, chance normalization, showdown coverage, information noninterference, and strategy integrity for 2–9 seats. Find hidden unbounded/circular/leakage cases or PASS.

## Verdict

**FAIL — S2 implementation does not exist**

- No `src/poker_solver/nplayer_postflop.py` found
- No test files matching `test.*nplayer.*postflop` pattern
- S2-I1 batch (§10 of design) not started
- Cannot verify runtime behavior against design specification

## Design review (specification only)

### 1. Deterministic weighted-deal work bounds (§4)

**Status**: ✓ Design specifies finite bound

- **Work cap**: `prod(len(range_i)) <= max_deals` bounds Cartesian candidate enumeration **before** collision pruning
- **Termination guarantee**: Even if every candidate collides with board/other seats, enumeration halts at `max_deals` products
- **Fail-closed**: Zero compatible deals and zero total mass fail before solving; compatible results never silently truncated
- **Deal representation**: `DealN = tuple[tuple[int, int], ...]` of length N; deterministic result order for `Action("DEAL", index)`

**Potential hidden issue**:
- Design does not specify iterator implementation. If collision retry uses recursion without depth guard, unbounded stack growth possible despite candidate cap.
- **Recommendation**: Implementation must use iterative Cartesian walk with explicit used-card set, not recursive backtracking.

### 2. Chance normalization (§4)

**Status**: ✓ Design specifies exact-to-float pipeline

- Exact integer combo weights multiplied per deal
- Exact masses summed across all compatible deals
- Float probabilities computed from exact totals
- Public probabilities: finite, nonnegative, sum to 1.0 within `1e-12`
- No premature float conversion during weight accumulation

**No hidden issues identified** in specification.

### 3. Showdown coverage (§4)

**Status**: ✓ Design mandates fail-closed validation

- **Mandatory**: Root construction requires exact `showdown_ranks: Mapping[DealN, tuple[int, ...]]` coverage when >1 player can reach showdown
- **Validation**: Missing, duplicate, malformed, or extra deal records fail **before** solving
- **Rank semantics**: N strict integers per deal; larger value wins; ties allowed
- **Detachment**: Config detaches caller mapping into private dict, exposes via `MappingProxyType`

**Potential hidden issue**:
- Design does not specify whether showdown rank lookup occurs during information-key construction.
- If `information_state_key()` accidentally includes opponent showdown ranks (even indirectly via deal index), information leakage occurs.
- **Recommendation**: Permanent test must verify that changing opponent showdown ranks (while holding owner combo/public state fixed) does not change owner information key.

### 4. Information noninterference (§7)

**Status**: ✓ Design specifies inclusion/exclusion lists

**Information key INCLUDES**:
- version, N, owner seat, owner private combo, board
- button, public ledgers (pot, contributions, remaining, street_committed)
- fold flags, pending order, raise entitlements, last_raise_increment, raise_count
- acting_player, wager_targets, actor-labelled history

**Information key EXCLUDES**:
- opponent private cards
- deal index
- iterator position
- hidden showdown ranks

**Validation**:
- Permanent 4/9-player tests vary opponent cards with fixed owner/public state → require equal owner keys
- Changing owner combo → require different key
- `collect_nplayer_infosets` as owner/action-consistency oracle

**Potential hidden issues**:
1. **Pending order encoding**: If pending tuple includes seats that have folded/all-in (violating invariant 5), information key may leak opponent stack sizes indirectly.
2. **History actor labels**: `NPlayerPublicAction` includes explicit `actor: int`. If actor is derived from seat order rather than action semantics, identical `CHECK` from different seats correctly distinguished. Design correct here.
3. **Raise entitlement (`can_raise`)**: N-tuple of booleans. If short all-in raise grants entitlement to seats in `old_pending` but not to seats that already acted (§5.3), information key must snapshot `can_raise` **after** action application, not before.

**No specification leakage found**, but implementation must not accidentally include deal index or opponent combos in key construction.

### 5. Strategy integrity (§7, §8)

**Status**: ✓ Design specifies deterministic normalization

- Strategies returned as detached nested mappings
- Finite nonnegative probabilities summing to 1.0
- Repeated deterministic runs produce equal values, diagnostics, serialized strategy
- `NPlayerCFRSolver` reuses existing generic N-player CFR with per-player reach and chance reach
- Regret update for player i weighted by chance × all opponent reaches, excluding i's own reach (§8)

**No hidden issues identified** in specification.

### 6. Structural bounds for 2–9 seats (§3, §5.3, §8)

**Status**: ✓ Design specifies finite depth and optional node cap

- **Decision depth**: `N + max_raises * (N - 1)` (§5.3)
  - Initial pending: up to N active seats
  - Each full raise: up to (N-1) responders
  - Maximum raises: `max_raises`
  - Structural bound independent of stack sizes
- **Node cap**: Optional `max_nodes` passed to `NPlayerCFRSolver` constructor (§8)
- **Exact invariants**: 11 strict per-state checks (§3), including:
  - Conservation: `pot == sum(total_contributed)` and `remaining[i] + total_contributed[i] == starting_stacks[i]`
  - Pending closure: folded/all-in seats not pending; pending seats unique, in range, live, have chips, ordered clockwise
  - Raise bounds: `0 <= raise_count <= max_raises`; `last_raise_increment > 0`
  - Terminal conservation: `sum(terminal_values) + house_rake == 0`

**Potential hidden issue**:
- **Short all-in raise pending rebuild** (§5.3): "seats still in `old_pending` retain their prior entitlement, while seats that had already acted cannot re-raise."
  - Design does not specify whether `old_pending` snapshot is taken **before** or **after** removing the short raiser from pending.
  - If snapshot taken after removal, short raiser (now all-in, zero chips) correctly excluded from new pending.
  - If snapshot taken before removal, short raiser might incorrectly remain in new pending despite having zero chips.
  - **Recommendation**: Implementation must snapshot `old_pending` **before** applying the raise action, then rebuild new pending from `old_pending - {raiser}` union with clockwise active seats.

### 7. Settlement and conservation (§6)

**Status**: ✓ Design specifies exact integer pipeline with independent oracle

- Integer-only refunds, side pots, rake, ties, odd chips
- Step 2: "reduce street_committed by refunds and reject negative results" — fail-closed on arithmetic error
- Independent permanent fixtures for 4/5/9 seats hand-derive all intermediate values
- Tests do not use settlement functions to calculate expected results (true oracle)
- Conservation: `sum(terminal_values) + house_rake == 0`

**Potential hidden issue**:
- Design does not specify exception type or rollback behavior when "reject negative results" triggered in step 2.
- If negative `street_committed` occurs due to refund > commitment, state is invalid but design does not mandate how to surface this.
- **Recommendation**: Implementation should raise `ValueError` with diagnostic message; caller (settlement) should never construct such state.

## Summary of potential implementation risks

1. **Deal enumeration**: Recursive collision retry without depth guard → unbounded stack
2. **Showdown rank leakage**: Accidental inclusion of opponent ranks in information key
3. **Pending snapshot timing**: Short all-in raise `old_pending` captured before vs. after actor removal
4. **Negative street_committed**: Refund validation failure mode unspecified
5. **Odd-chip permutation validation**: No algorithm specified for verifying `odd_chip_order` is exactly `range(N)` permutation

## Recommendation

**Cannot PASS without implementation.** Design specification shows no obvious unbounded/circular/leakage flaws, but real code may:
- Use recursive deal enumeration (risk 1)
- Leak showdown ranks into information keys (risk 2)
- Mishandle short all-in pending rebuild (risk 3)
- Silently produce negative street commitments (risk 4)
- Accept invalid odd-chip orders (risk 5)

**Next step**: Await S2-I1 implementation, then re-audit with:
- Code inspection of deal enumerator (iterative vs. recursive)
- `information_state_key()` construction (explicit exclusion of deal index, opponent combos, showdown ranks)
- Pending rebuild logic (snapshot timing, short all-in handling)
- Settlement validation (negative-result exception)
- Config validation (odd-chip permutation check)
- Execution of permanent 4/5/9-player tests with opponent-card variation

---

**Audit incomplete — implementation does not exist.**
