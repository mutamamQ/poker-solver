# S1-I1 Audit Topic 02: State/Accounting

**Auditor:** Subagent (retry after first auditor incorrectly claimed unavailable tools)  
**Date:** 2026-09-15  
**Candidate:** Phase 4 S1-I1 failed candidate (frozen 2026-09-15T15:53:19Z)  
**Base commit:** 7a817e618a3c0898b531e88440b490323c62b49b  

## Hash Identity

Candidate manifest: `research/phase4/s1-i1-audit/CANDIDATE_MANIFEST.md`

```
2d93dc2983fb4ec9bc499b2d025a109c34ae8437301c748d0be708a4e6b4f4d7  src/poker_solver/allstreet.py
00b95824979bb894321dbb491746b9a97bf891b4682b6f1a5e58b70ab3fabebc  src/poker_solver/multistreet.py
22b3af76e41af2805bd0b8133a2cf25e3c3e15fe77fcd1c7562ca45be1b426e6  tests/test_allstreet_state.py
```

All hashes match CANDIDATE_MANIFEST.md. Snapshot unchanged.

## Scope

Executable audit of state-machine contract per ARCHITECTURE_PHASE4_S1.md §4 and §6.3:

- Deal→flop→turn→river decision/chance progression
- Chance mass = 1.0 at every chance node
- Raise-to commitment semantics and one-time street pot transfer
- Zero-sum terminal returns
- Information-key noninterference (opponent cards)

## Audit Method

Executable Python probe script (`audit_state_accounting.py`) using available `terminal`, `read_file`, `write_file` tools. No source/test edits. Focused state traversal with exact receipts.

## Findings

### Finding 1: River all-in closure defect (CRITICAL)

**Probe:** Check-check path flop→turn→river with singleton runout.

**Expected:** River card dealt, player 0 acts.

**Actual receipt:**
```
River state: player=-2, street=river, board_len=5
River pot: 100
River committed: (0, 0)
River remaining: (500, 500)
```

**Analysis:** `multistreet.py:274` sets `acting_player=CHANCE if any(r == 0 for r in self.remaining) else 0`. After turn check-check with no betting, `remaining=(500, 500)` (no all-in), so river should open with player 0 acting. Instead, `acting_player=-2` (TERMINAL). The river card was dealt (board_len=5, street=river), but the state incorrectly transitioned to TERMINAL instead of decision node.

**Root cause:** Line 244 in `multistreet.py` handles the river runout card case:
```python
if len(new_board) == 5:
    h0 = evaluate_seven(self.private_deal[0] + new_board)
    h1 = evaluate_seven(self.private_deal[1] + new_board)
    contested = self.pot + sum(self.committed)
    ...
    return MultiStreetState(..., acting_player=TERMINAL, ...)
```

This unconditionally terminates when the 5th board card is dealt, regardless of whether players are all-in. The contract requires river decisions when `remaining > 0` for both players.

**Impact:** Violates ARCHITECTURE_PHASE4_S1.md §4 state-machine contract: "River showdown uses evaluate_seven" only after river decisions close (check-check or call). The automatic path must be `private deal -> flop decisions -> public turn chance -> turn decisions -> public river chance -> river decisions -> fold/showdown`. This defect skips river decisions entirely.

**Gate violation:** §6.3 mandatory gate "standard flop request contains no continuation/payoff table and reaches river terminals" — the path reaches a river terminal, but bypasses the required river decision nodes.

### Finding 2: Raise-to accounting correct

**Probe:** Raise 50, call, verify committed/remaining/pot transfer.

**Receipt:**
```
✓ Raise committed: (50, 0)
✓ Raise remaining: (450, 500)
✓ Call committed: (50, 50)
✓ Turn pot after transfer: 200
✓ Turn committed reset: (0, 0)
```

**Result:** PASS. Raise-to semantics, pot transfer, and committed reset correct.

### Finding 3: Fold accounting correct

**Probe:** Raise, fold, verify zero-sum.

**Receipt:**
```
✓ Fold zero-sum: u0=50.0, u1=-50.0, sum=0.000000000000e+00
```

**Result:** PASS. Fold terminal zero-sum within tolerance.

### Finding 4: Information-key noninterference correct

**Probe:** Two configs differing only in player1 combos, verify player 0 info key identical.

**Receipt:**
```
✓ Information keys match when opponent cards differ: True
```

**Result:** PASS. Opponent cards do not affect acting player's information key.

### Finding 5: Chance mass correct (where reachable)

**Probe:** Flop and turn chance mass.

**Receipt:**
```
✓ Flop chance mass: 1.000000000000
✓ Turn chance mass: 1.000000000000
```

**Result:** PASS. Chance outcomes sum to 1.0 within tolerance.

## Test Execution Receipt

Full executable audit script: `/home/genomix-node/poker-solver/audit_state_accounting.py`

```
================================================================================
S1-I1 State/Accounting Audit
================================================================================

[HASH IDENTITY]
2d93dc2983fb4ec9bc499b2d025a109c34ae8437301c748d0be708a4e6b4f4d7  src/poker_solver/allstreet.py
00b95824979bb894321dbb491746b9a97bf891b4682b6f1a5e58b70ab3fabebc  src/poker_solver/multistreet.py
22b3af76e41af2805bd0b8133a2cf25e3c3e15fe77fcd1c7562ca45be1b426e6  tests/test_allstreet_state.py

[TEST 1: Street Progression & Accounting]
✗ FAILED: Player 0 acts on river

[TEST 2: Raise-to Accounting]
✓ Raise committed: (50, 0)
✓ Raise remaining: (450, 500)
✓ Call committed: (50, 50)
✓ Turn pot after transfer: 200
✓ Turn committed reset: (0, 0)

[TEST 3: Fold Accounting]
✓ Fold zero-sum: u0=50.0, u1=-50.0, sum=0.000000000000e+00

[TEST 4: Information Key Noninterference]
✓ Information keys match when opponent cards differ: True

================================================================================
VERDICT: FAIL
One or more state/accounting tests failed.
```

## Verdict

**FAIL**

Critical defect: `multistreet.py` line 244 unconditionally terminates when the river card is dealt, skipping river decision nodes. This violates the state-machine contract (ARCHITECTURE_PHASE4_S1.md §4) and the mandatory gate requiring river terminals to be reached through river decisions, not directly from river chance nodes.

Raise-to accounting, fold accounting, information-key noninterference, and chance mass are correct where reachable.

## Recommendation

Reject candidate. Repair `multistreet.py:244-267` to open river decision node when `remaining > 0` for both players, and only terminate immediately on all-in river runout.
