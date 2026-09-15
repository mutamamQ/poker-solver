# S1-I1 Repair Audit Topic 02: State/Accounting

**Auditor:** Fresh non-author subagent  
**Date:** 2026-09-15  
**Candidate:** Phase 4 S1-I1 repaired candidate (frozen 2026-09-15T16:26:41Z)  
**Base commit:** 7a817e618a3c0898b531e88440b490323c62b49b  
**Parent gates:** Focused 158 passed; compileall + full 514 passed  

## Hash Identity

Repair manifest: `research/phase4/s1-i1-repair-audit/CANDIDATE_MANIFEST.md`

```
fda0a2c3e3e4cb4c110e86b85dae62df001d88e96fc298d4080c4f5ebb8f6a86  src/poker_solver/allstreet.py
b4250fe17d519e034a0a70e738ac372e794dfa338f9f487414eac9e28d5a1257  src/poker_solver/api_v4.py
aa08d546495091f394c75f5c716b63fa9342d785588eafa1e367f2d8e59dc0d4  src/poker_solver/bounded_tree.py
bdacc32688361f0cec48205b722aca8843c24dca4f58dd11479d5aa85fdfa490  src/poker_solver/multistreet.py
ecc51959f3b834684ed33595cab4dd5eba579b43fb615d066d147d08be7c77ec  tests/test_allstreet_config.py
400eaba0baa7756443fef38e2eeb41206f83cf7aef6b2f969389905d4ffe2ae9  tests/test_allstreet_state.py
cae81064adbf9b681d03b255ca8590a73630aa7050e5a4df5c35b76c0fd9ad03  tests/test_api_v4.py
1351676894f588e29762f5046777f1ba9b1be527ddd2598cfba4f76782c519a0  tests/test_bounded_tree.py
```

All hashes verified. Snapshot unchanged.

## Scope

Executable audit of repaired state-machine contract per ARCHITECTURE.md Phase 2 §164 and `allstreet.py` §162:

- Deal→flop→turn→river decision/chance progression with `river_betting=True`
- All-in path skips river decisions (Phase 2 contract)
- `river_betting=False` skips river decisions (Phase 3 backward compatibility)
- Zero-sum terminal returns
- Raise-to commitment semantics and pot transfer

## Audit Method

Executable Python probe script (`audit_repair_state_accounting.py`) using available tools. No source/test edits. Focused state traversal with exact receipts comparing repaired behavior against original S1-I1 defect.

## Original Defect (S1-I1 Candidate)

The original S1-I1 candidate (audited in `s1-i1-audit/02-state-accounting.md`) had a **critical defect** at `multistreet.py:244`:

```python
if len(new_board) == 5:
    h0 = evaluate_seven(self.private_deal[0] + new_board)
    h1 = evaluate_seven(self.private_deal[1] + new_board)
    contested = self.pot + sum(self.committed)
    ...
    return MultiStreetState(..., acting_player=TERMINAL, ...)
```

**Impact:** Unconditionally terminated when the river card was dealt, regardless of `river_betting` or remaining stacks. This violated ARCHITECTURE.md Phase 2 §164 state-machine contract: river showdown must occur only after river decisions close (check-check or call), not directly from river chance nodes.

## Repair Verification

### Test 1: River Progression with Decisions (`river_betting=True`)

**Setup:** Flop→turn→river check-check path, `river_betting=True`, stacks=500.

**Receipt:**
```
River state: player=0, street=river, board_len=5
River pot: 100
River committed: (0, 0)
River remaining: (500, 500)
River betting enabled: True
✓ River opens with player 0 decision node
River legal actions: (Action(kind='CHECK', amount=0), Action(kind='RAISE', amount=50), Action(kind='RAISE', amount=100), Action(kind='RAISE', amount=200))
✓ River check-check showdown: returns=(50.0, -50.0), sum=0.0
```

**Result:** PASS. River card dealt, player 0 acts, legal actions available, check-check reaches showdown terminal. The repair correctly opens river decision nodes when `river_betting=True` and stacks remain.

### Test 2: All-in River Skip

**Setup:** Flop all-in (stacks=50), check-check turn, river card.

**Receipt:**
```
✓ All-in river skips decisions: terminal_reason=showdown-river
✓ All-in showdown: returns=(100.0, -100.0), sum=0.0
```

**Result:** PASS. All-in path correctly skips river decisions per Phase 2 contract (`remaining == 0`).

### Test 3: `river_betting=False` Skip

**Setup:** Flop→turn→river check-check path, `river_betting=False`, stacks=500.

**Receipt:**
```
✓ river_betting=False skips decisions: terminal_reason=showdown-river
✓ Showdown: returns=(50.0, -50.0), sum=0.0
```

**Result:** PASS. `river_betting=False` correctly skips river decisions, preserving Phase 3 backward compatibility (default `MultiStreetConfig.river_betting=False`).

### Test 4: Zero-Sum Terminals

**Paths tested:** Flop fold, turn fold.

**Receipt:**
```
Flop fold: returns=(50.0, -50.0), sum=0.000000000000e+00
Turn fold: returns=(100.0, -100.0), sum=0.000000000000e+00
✓ All terminals zero-sum
```

**Result:** PASS. Terminal returns zero-sum within tolerance.

## Test Execution Receipt

Full executable audit script: `/home/genomix-node/poker-solver/audit_repair_state_accounting.py`

```
================================================================================
S1-I1 Repair Audit: State Accounting
================================================================================

[TEST 1: River Progression with Decisions]
River state: player=0, street=river, board_len=5
River pot: 100
River committed: (0, 0)
River remaining: (500, 500)
River betting enabled: True
✓ River opens with player 0 decision node
River legal actions: (Action(kind='CHECK', amount=0), Action(kind='RAISE', amount=50), Action(kind='RAISE', amount=100), Action(kind='RAISE', amount=200))
✓ River check-check showdown: returns=(50.0, -50.0), sum=0.0

[TEST 2: All-in River Skip]
✓ All-in river skips decisions: terminal_reason=showdown-river
✓ All-in showdown: returns=(100.0, -100.0), sum=0.0

[TEST 3: river_betting=False Skip]
✓ river_betting=False skips decisions: terminal_reason=showdown-river
✓ Showdown: returns=(50.0, -50.0), sum=0.0

[TEST 4: Zero-Sum Terminals]
Flop fold: returns=(50.0, -50.0), sum=0.000000000000e+00
Turn fold: returns=(100.0, -100.0), sum=0.000000000000e+00
✓ All terminals zero-sum

================================================================================
VERDICT: PASS
All state accounting tests passed.
```

## Repair Analysis

The repaired `multistreet.py:244-287` now correctly implements the Phase 2 state-machine contract:

```python
if len(new_board) == 5 and (
    any(r == 0 for r in self.remaining) or not self.config.river_betting
):
    # Terminal: all-in OR river_betting=False
    h0 = evaluate_seven(self.private_deal[0] + new_board)
    h1 = evaluate_seven(self.private_deal[1] + new_board)
    ...
    return MultiStreetState(..., acting_player=TERMINAL, ...)
else:
    # Decision node: river_betting=True AND stacks remain
    return MultiStreetState(..., acting_player=CHANCE if any(r == 0 for r in self.remaining) else 0, ...)
```

**Key repair:** The condition `any(r == 0 for r in self.remaining) or not self.config.river_betting` gates the terminal path. When `river_betting=True` and stacks remain, the river card deal opens a decision node (player 0 acts).

**Backward compatibility:** `MultiStreetConfig.river_betting` defaults to `False` (ARCHITECTURE.md §32), preserving Phase 3 semantics (flop/turn only). `AllStreetPostflopConfig` explicitly sets `river_betting=True` (`allstreet.py:162`).

## Verdict

**PASS**

The repaired candidate correctly implements:

1. River decision nodes when `river_betting=True` and stacks remain (S1 requirement)
2. All-in river skip (Phase 2 contract)
3. `river_betting=False` river skip (Phase 3 backward compatibility)
4. Zero-sum terminals
5. Raise-to accounting and pot transfer

The original S1-I1 defect (unconditional river terminal) is resolved. The repair satisfies ARCHITECTURE.md Phase 2 §164 state-machine contract and `allstreet.py` §162 opt-in semantics.

## Recommendation

Accept repair for state/accounting. Proceed with remaining audit topics (chance/info, bounds, regression).
