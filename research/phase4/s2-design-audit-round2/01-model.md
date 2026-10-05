# F201 S2 Design-Specification Audit

Frozen: 2026-09-15T21:16:30Z  
Hash: 770a25ab95381da7b38e1e0d2604ad513a202daa8b9a54c79f7b762e990c4eba  
Auditor: F201 (model)  
Verdict: **PASS**

## Scope

Design-only review of ARCHITECTURE_PHASE4_S2.md against existing source (multiway.py, nplayer.py, game_structure.py) for specification completeness, internal correctness, and N=3 compatibility before S2 implementation. Absence of S2 implementation/tests is expected and is not a finding.

## Findings

The S2 specification is complete, internally consistent, and feasible:

### 1. Strict 2–9 config

§2.1 defines `NPlayerPostflopConfig` with:

- Explicit N-length tuple validation for all per-seat fields
- Strict integer/bool type guards rejecting bool-as-int (precedent: multiway.py lines 31–40, 61–112)
- Positive stack/contribution bounds, nonnegative contributions ≤ stacks
- Exact permutation check for `odd_chip_order` (length and set equality to `range(N)`)
- Unique increasing `wager_targets`
- Positive strict integers for `max_raises`, `max_deals`, `max_nodes`
- Detached showdown-rank mapping via `MappingProxyType`

### 2. Immutable state

§2.3 frozen dataclass `NPlayerPostflopState` with:

- All per-seat tuples, pot, terminal values as strict integers
- Exact invariants (§3) enforced at construction and every transition:
  - Pot = sum(total_contributed)
  - remaining[i] + total_contributed[i] = starting_stacks[i]
  - 0 ≤ street_committed[i] ≤ total_contributed[i]
  - Pending seats unique, in range, live, have chips, clockwise ordered
  - Terminal: sum(terminal_values) + house_rake = 0
  - Nonterminal: terminal_values = None, house_rake = 0

Matches `ThreePlayerPostflopState` pattern (multiway.py lines 126–183).

### 3. Actor-labelled history

§2.2 `NPlayerPublicAction` records explicit `(actor, action)` pairs, correctly distinguishing identical actions (CHECK, CALL, FOLD) from different seats for information-set integrity.

### 4. Card/weight validation

§4 deterministic deal enumeration:

- Iterative Cartesian product in seat/range tuple order
- Immediate collision pruning with board-seeded used-card set
- Exact rational arithmetic: `Fraction(str(weight))` for all weights, exact mass sum before final probability conversion
- `max_deals` bounds candidate products **before** enumeration (fail-closed even when all candidates invalid)
- No compatible deal or zero total mass fails closed
- Showdown-rank coverage required when >1 player can reach showdown (§4 end)
- Precedent: multiway.py lines 365–378

### 5. Public/private information

§7 information key includes:

- Rules/version identity, N, owner, owner private combo, fixed board, button
- All public ledgers, fold flags, pending order, raise entitlements, last increment, raise count, acting seat
- Wager targets, actor-labelled history

Excludes:

- Opponent private cards, deal index, iterator position, hidden showdown ranks

Matches multiway.py lines 337–351 pattern. Permanent 4- and 9-player tests vary opponent cards/ranks while holding owner/public state fixed and require equal owner keys (§7).

### 6. N=3 compatibility

§10 (S2-I1) mandates:

- Projected trace equivalence tests comparing new N=3 path against frozen Phase-3 fixtures
- Projection to: chance deals/probabilities, clockwise actors, legal `Action` tuples, pot/commitment/remaining/fold ledgers, terminal rake/utilities, owner information partitions
- **Not** raw object, version-string, history-record, or information-key equality
- Preserves legacy `MultiwayConfig`, `ThreePlayerPostflopState`, `create_three_player_root` public behavior (§1)

### 7. Existing primitives reused

§6 settlement:

- `refund_uncalled_excess`, `build_pot_layers`, `calculate_rake`, `allocate_rake`, `award_pot_layers` from game_structure.py (lines 200–311)
- Independent 4/5/9 hand-derived oracles (§6 end)

§8 solver:

- `NPlayerCFRSolver`, `expected_values_nplayer`, `unilateral_deviation_certificate` from nplayer.py (lines 141–344)
- S2-I2 adds keyword-only `max_nodes`/`max_depth` to solver constructor; defaults unchanged for legacy callers

### 8. Betting semantics

§5 defines:

- Clockwise pending order via `_ordered_after` with wraparound (§5.1)
- Legal actions: CHECK when to_call=0, else FOLD+CALL; raises require entitlement, chips beyond call, raise_count < max_raises (§5.2)
- Full raise (≥ last_raise_increment) updates increment and reopens all active seats; short all-in raise does not update increment, retains old_pending entitlements, excludes seats that already acted (§5.3 lines 144–146)
- Structural depth bound: N + max_raises * (N - 1) (§5.3 end)
- Exact ledger transitions matching multiway.py lines 218–291

### 9. Acceptance matrix

§11 enumerates executable gates:

- Strict configs accept 2–9, reject malformed lengths/types/bounds
- 4-, 5-, 9-player spots build, validate, train/evaluate, return N values
- Chance mass, blocker filtering, deterministic deal order, `max_deals` fail-closed
- Every transition conserves stacks/pot, obeys clockwise pending/reopening
- Hand-derived multi-layer refunds, side pots, rake, ties, odd chips match exactly
- Terminal utility + house_rake conserves exactly
- 4- and 9-player opponent-card noninterference
- Policies normalized and deterministic
- Five-plus-player exact unilateral-deviation diagnostic matches independent enumeration below cap
- Generic N=3 projected trace matches frozen Phase-3 deals, actions, ledgers, settlement, utilities, information partitions (not raw key/history identity)
- All old three-player tests and entire prior suite green
- Strict v4, generic CLI, examples, exports, capability truth
- Every batch has fresh different non-author audit and accepted-wave commit
- Tag `phase3-398-green` remains present

Correctly notes `max_deals` fail-closed already included.

### 10. TDD batches

§10 splits implementation:

**S2-I1** (state/ledger):

- New `nplayer_postflop.py` only
- 4 nonoverlapping test modules: config, betting, settlement, information
- Three-player equivalence via projected trace, not raw equality
- RED-first, parent runs all new + legacy, fresh non-author audit, accepted-wave commit

**S2-I2** (solve/API):

- `nplayer_postflop.py`, bound plumbing in `nplayer.py`, `api_v4.py`, `api_v3.py`, package exports
- 4 nonoverlapping test modules: solve, v4 API, examples, exports
- RED-first, parent integrates shared exports after RED, focused + full regression, fresh non-author audit, accepted-wave commit

### 11. Provenance

§12 truthful bounded claim:

> bounded deterministic 2-9-player one-round postflop CFR with exact integer side-pot settlement and optional exhaustive finite unilateral-deviation diagnostic

Explicit non-claims: no GTO convergence guarantee, no practical large-range nine-player performance, no multi-street play, no automatic rank evaluation, no sampled exploitability, no unrestricted solving.

## Verdict

**PASS** — The S2 specification is complete, internally consistent, and feasible against existing source. Proceed to S2-I1 RED test authoring.

---

Audit completed: 2026-09-15 (UTC)
