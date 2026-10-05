# S2 betting-semantics design audit — PASS

**Auditor**: Hermes subagent G202  
**UTC**: 2026-09-15  
**Manifest SHA-256**: 322ed04e (verified)  
**Scope**: Design-only review of ARCHITECTURE_PHASE4_S2.md § 5 betting semantics  

## Executive summary

**PASS** — betting-round specification (§ 5) is model-complete, deterministic, and internally consistent.

## Detailed findings

### 5.1 Root and order — ✓ PASS

- **Clockwise order**: Explicit `_ordered_after(seat, candidates)` with wraparound (line 121).
- **Initial pending**: Active seats clockwise after button (line 117).
- **Initial raise entitlement**: All active seats `can_raise[i] = true` (line 118).
- **Increment bootstrap**: `last_raise_increment = wager_targets[0]` when present, else `1` (line 119).
- **Root ledger**: Zero street commitments, baseline contributions in pot, derived remaining (lines 113–116).

**No ambiguity**. Order, entitlement, and increment are fully specified.

### 5.2 Legal actions — ✓ PASS

- **Check vs fold**: Check offered when `to_call == 0`; fold not exposed when check available (lines 127, 135).
- **Call amount**: `own + min(to_call, remaining[p])` — exact all-in clamping (line 128).
- **Raise preconditions**: Current entitlement, chips beyond call, `raise_count < max_raises` (line 129).
- **Target deduplication**: Configured targets deduplicated in declared order (line 130).
- **Minimum raise**: `H + last_raise_increment`; below-minimum legal only for actor's all-in (lines 131–132).
- **Action amounts**: Absolute current-street commitments (line 133).

**No gaps**. All-in edge cases, deduplication, and minimum-raise exemption are explicit.

### 5.3 Transition and closure — ✓ PASS

- **Pending cycles**: Preserved `old_pending` before action (line 139); raise rebuilds pending as "every other active seat clockwise after raiser" (line 144).
- **Full raise reopening**: `target - old_H >= last_raise_increment` updates increment and reopens for all active seats (line 146).
- **Short all-in raise**: Does not update increment; `old_pending` seats retain entitlement, already-acted seats cannot re-raise, short raiser has no chips (lines 146–147).
- **Closure**: Terminates when one live seat remains or pending empty (line 148).
- **All-in closure**: "All live all-in seats being non-actionable therefore closes the round" (line 148).
- **Depth bound**: `N + max_raises * (N - 1)` (line 148).

**No ambiguity**. Full vs short reopening, pending reconstruction, and closure conditions are deterministic.

## Model-check summary

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Clockwise order | ✓ | § 5.1 line 121, § 5.3 line 144 |
| Pending cycles | ✓ | § 5.3 lines 139, 144, 148 |
| Call/fold/check | ✓ | § 5.2 lines 127–128, 135 |
| Full raise reopening | ✓ | § 5.3 line 146 |
| Short all-in reopening | ✓ | § 5.3 lines 146–147 |
| Closure conditions | ✓ | § 5.3 line 148 |
| Depth bound | ✓ | § 5.3 line 148 |

## Conclusion

No specification blockers. Betting semantics are implementation-ready.

**Recommendation**: Proceed to S2-I1 TDD.
