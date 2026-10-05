# S2 betting semantics audit — A2D2

Auditor: A2D2 (fresh non-author design auditor)  
UTC: 2026-09-15T21:10:00Z  
Candidate: ARCHITECTURE_PHASE4_S2.md (frozen hash 86080aac...)  
Scope: root commitments, clockwise pending order, checks, calls, folds, full raises, short all-ins, reopening, all-in closure, depth bounds, actor-labelled history

## Verdict: FAIL — implementation does not exist

### Critical blocker

The frozen design document specifies a new module `src/poker_solver/nplayer_postflop.py` (§1, §2) containing:

- `NPlayerPostflopConfig` (§2.1)
- `NPlayerPublicAction` (§2.2)  
- `NPlayerPostflopState` (§2.3)

This module **does not exist** in the repository at base commit `a9d99effadbb4bfbb36179115c7e6bdf6efe8509`.

### Evidence

```
$ search_files pattern="class NPlayerPostflopState" → 0 matches
$ search_files pattern="nplayer_postflop" → 0 matches
$ ls src/poker_solver/*.py → multiway.py exists (Phase-3 three-player only)
```

The only existing multiway implementation is `src/poker_solver/multiway.py`, which implements the Phase-3 exactly-three-player `ThreePlayerPostflopState` and `MultiwayConfig`. It does not support 2–9 players, does not use `NPlayerPublicAction`, and does not match the S2 typed contracts.

### Architecture violations

Cannot audit betting semantics specified in §5 because:

1. **Root commitments (§5.1):** No `NPlayerPostflopState` constructor or `create_nplayer_root` function exists to verify initial pot, pending order, or raise entitlements.

2. **Clockwise pending order (§5.1):** No `_ordered_after(seat, candidates)` helper exists. Cannot verify wraparound or canonical ordering.

3. **Legal actions (§5.2):** No `legal_actions()` method exists for N-player states. Cannot verify check/call/fold/raise logic, target deduplication, or all-in short-raise handling.

4. **Transition and closure (§5.3):** No `child(action)` method exists. Cannot verify fold/check/call/raise transitions, pending rebuilds, full vs. short reopening rules, or all-in closure.

5. **Actor-labelled history (§2.2, §7):** No `NPlayerPublicAction` dataclass exists. Cannot verify that identical actions from different seats produce different public histories.

6. **Depth bounds (§5.3):** Cannot verify the structural bound `N + max_raises * (N - 1)` without a working state machine.

### TDD batch status

Section 10 mandates:

- **S2-I1:** Permanent RED tests for config validation, betting order, pending closure, reopening, side pots, refunds, rake, and information keys. These tests must exist and fail **before** production implementation.
  
- **S2-I2:** Permanent RED tests for solve facade, diagnostics, v4 API, and examples.

No RED tests exist. No production code exists. The design describes unbuilt architecture.

### Acceptance matrix (§11)

Cannot verify any acceptance criterion:

- ❌ Strict 2–9 config validation  
- ❌ 4-, 5-, 9-player spots  
- ❌ Chance mass, blocker filtering, deterministic deal order  
- ❌ Transition conservation, clockwise pending, reopening rules  
- ❌ Hand-derived multi-layer refunds, side pots, rake, ties, odd chips  
- ❌ Terminal utility conservation  
- ❌ 4- and 9-player opponent-card noninterference  
- ❌ Normalized deterministic policies  
- ❌ Five-plus-player exact unilateral-deviation diagnostic  
- ❌ Generic N=3 trace equivalence with Phase-3  
- ❌ Strict v4, CLI, examples, exports, capability truth  

### Conclusion

The S2 design audit cannot proceed. The candidate architecture describes a bounded 2–9-player postflop game with exact betting semantics, but the implementation does not exist. No counterexamples can be published because there is no code to attack.

**Recommendation:** Implement S2-I1 per §10 TDD batches before requesting a betting-semantics audit.

---

**Audit status:** BLOCKED  
**Counterexamples:** None (no implementation to test)  
**Next action:** Implement `nplayer_postflop.py` and permanent RED tests per §10
