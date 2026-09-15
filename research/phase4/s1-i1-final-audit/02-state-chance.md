# F02: MultiStreetState All-Street Chance and River Transitions

**Audit Date:** 2026-09-15  
**Auditor:** BryantGPT (non-author retry)  
**Scope:** Executable final adversarial audit of MultiStreetState/all-street chance and river transitions, accounting, noninterference, strict construction, backward compatibility, zero-sum, and determinism  
**Manifest:** S1-I1 frozen candidate (2026-09-15T17:04:52Z)  
**Status:** ✓ PASS

---

## Executive Summary

All manifest hashes verified. All 17 existing tests passed. All 11 executable probes passed. Zero blockers, zero majors. Production APIs execute correctly. Backward compatibility preserved. Zero-sum invariant holds. Information noninterference verified. Determinism confirmed.

---

## Manifest Verification

### Files and Hashes

All manifest entries verified against frozen S1-I1 candidate:

```
96a5beb6f498346a28f4da511e65fbe14c24539de68b32ff03053532c6635d32  research/phase4/s1-i1-final-audit/CANDIDATE_MANIFEST.md
bdacc32688361f0cec48205b722aca8843c24dca4f58dd11479d5aa85fdfa490  src/poker_solver/multistreet.py
b632e5d72c19679e591a1ef1e743af08c3ea50772c0712441d0703d925cd63da  tests/test_allstreet_state.py
5cfac6f10b4f03e9e209e74912032abfff025efef6a8113d5f362a2268b50295  src/poker_solver/allstreet.py
49677a0fc488a1fcff351766362b66ddcd6d59564d06ee9c501b46efbc6c3bd4  src/poker_solver/api_v4.py
aa08d546495091f394c75f5c716b63fa9342d785588eafa1e367f2d8e59dc0d4  src/poker_solver/bounded_tree.py
e16125a2daef23b9e6fcde099bfa99d0ef124530bce351c99be6e8e93499fd67  tests/test_allstreet_config.py
f2d3c579ce4678f516a9409afac9676690178cc7a5c3b2dfe03c1d6d7e0bf7c2  tests/test_api_v4.py
1351676894f588e29762f5046777f1ba9b1be527ddd2598cfba4f76782c519a0  tests/test_bounded_tree.py
```

**Result:** ✓ All hashes match manifest exactly.

---

## Test Suite Execution

### Command

```bash
uv run pytest tests/test_allstreet_state.py -v
```

### Results

17 tests collected, **17 passed** in 0.08s:

- `test_flop_to_turn_progression` ✓
- `test_turn_to_river_progression` ✓
- `test_river_check_check_terminal` ✓
- `test_compatible_runout_chance_mass` ✓
- `test_blocked_runout_filtering` ✓
- `test_fold_handling` ✓
- `test_call_close_handling` ✓
- `test_all_in_handling` ✓
- `test_raise_to_accounting` ✓
- `test_zero_sum_terminals` ✓
- `test_opponent_card_noninterference` ✓
- `test_vanilla_determinism` ✓
- `test_complete_flop_to_river_path` ✓
- `test_river_betting_false_immediate_showdown` ✓
- `test_river_betting_default_false` ✓
- `test_river_betting_strict_bool_validation` ✓
- `test_create_allstreet_root_enables_river_betting` ✓

**Result:** ✓ All existing tests pass.

---

## Executable Probes

### Probe 1: Backward Compatibility

**Objective:** Verify `river_betting` defaults to `False` when omitted.

**Method:** Construct `MultiStreetConfig` without `river_betting` parameter; verify default is `False`; verify river card immediately terminates to showdown.

**Expected:** `config.river_betting is False`; river state reaches `TERMINAL` with `terminal_reason == "showdown-river"`.

**Actual:** ✓ Default is `False`; river immediately terminates.

**Result:** ✓ PASS — Backward compatibility preserved.

---

### Probe 2: AllStreet Opt-In

**Objective:** Verify `create_allstreet_root` explicitly sets `river_betting=True`.

**Method:** Construct `AllStreetPostflopConfig`; call `create_allstreet_root`; verify underlying `MultiStreetConfig` has `river_betting=True`; verify river opens action.

**Expected:** `root.config.river_betting is True`; river state has `current_player() == 0`.

**Actual:** ✓ `river_betting=True`; river opens action to player 0.

**Result:** ✓ PASS — AllStreet adapter opts in correctly.

---

### Probe 3: River Chips-Behind

**Objective:** After fifth board card, chips-behind opens river betting when `river_betting=True`.

**Method:** Construct config with `river_betting=True`; traverse flop→turn→river with check-check; verify river state has `remaining[0] > 0` and `remaining[1] > 0`; verify `current_player() == 0`.

**Expected:** River state opens action when both players have chips behind.

**Actual:** ✓ Both players have chips; river opens action.

**Result:** ✓ PASS — Chips-behind opens river betting.

---

### Probe 4: River All-In

**Objective:** True all-in reaches showdown immediately, skipping river action.

**Method:** Construct config with `river_betting=True`; all-in on flop; verify `remaining == (0, 0)`; verify turn and river skip action and reach terminal.

**Expected:** Turn and river are `CHANCE` nodes; final river state is `TERMINAL` with `terminal_reason == "showdown-river"`.

**Actual:** ✓ All-in skips turn/river action; reaches showdown terminal.

**Result:** ✓ PASS — All-in reaches showdown immediately.

---

### Probe 5: Legal Actions / Chance Outcomes Separation

**Objective:** `legal_actions()` and `chance_outcomes()` are separate methods; at chance nodes, `legal_actions()` returns actions matching `chance_outcomes()`.

**Method:** At a chance node, call both methods; verify `legal_actions()` equals `tuple(action for action, _ in chance_outcomes())`.

**Expected:** Actions match; both non-empty.

**Actual:** ✓ 1 outcome; actions match exactly.

**Result:** ✓ PASS — Separation and equality verified.

---

### Probe 6: Board/Deck Depletion

**Objective:** Runouts blocked by private cards are filtered; unique board/deck depletion.

**Method:** Construct config where player0 holds `2c`; runouts include `[2c, 3d]` and `[4h, 5s]`; verify turn chance outcomes exclude `2c` and include `4h`.

**Expected:** `2c` not in turn outcomes; `4h` in turn outcomes.

**Actual:** ✓ `2c` blocked; `4h` available.

**Result:** ✓ PASS — Blocked cards filtered correctly.

---

### Probe 7: Pot/Stack Accounting

**Objective:** Exact pot, stack, street/total commitments and transitions.

**Method:** Traverse initial→raise→call→street-close; verify `pot`, `committed`, `total_contributed`, `remaining` at each step.

**Expected:**  
- Initial: `pot=100`, `committed=(0,0)`, `total_contributed=(0,0)`, `remaining=(500,500)`  
- After raise 50: `committed=(50,0)`, `total_contributed=(50,0)`, `remaining=(450,500)`, `pot=100`  
- After call 50: `committed=(50,50)`, `total_contributed=(50,50)`, `remaining=(450,450)`, `pot=100`  
- After street close: `pot=200`, `committed=(0,0)`, `total_contributed=(50,50)`

**Actual:** ✓ All values match expected exactly.

**Result:** ✓ PASS — Accounting exact and correct.

---

### Probe 8: Zero-Sum

**Objective:** All terminal returns satisfy `u0 + u1 = 0`.

**Method:** Reach fold terminal and showdown terminal; call `returns()`; verify sum within `1e-9`.

**Expected:** `abs(u0 + u1) < 1e-9` for both terminals.

**Actual:** ✓ Fold terminal: zero-sum. Showdown terminal: zero-sum.

**Result:** ✓ PASS — Zero-sum invariant holds.

---

### Probe 9: Information Noninterference

**Objective:** Information keys do not vary with opponent's hidden cards.

**Method:** Construct two configs differing only in player1's combos; deal and compute `information_state_key(0)` for both; verify keys are identical.

**Expected:** `key_a == key_b`.

**Actual:** ✓ Keys identical.

**Result:** ✓ PASS — Noninterference verified.

---

### Probe 10: Determinism

**Objective:** Repeated traversals produce identical states.

**Method:** Construct same config twice; traverse same actions; verify `board`, `pot`, `committed`, `remaining`, `history` match.

**Expected:** All fields identical.

**Actual:** ✓ All fields match.

**Result:** ✓ PASS — Determinism confirmed.

---

### Probe 11: Malformed Construction

**Objective:** Direct malformed state/config construction raises documented `ValueError`.

**Method:** Attempt to construct `MultiStreetConfig` with invalid `river_betting=1` (int) and invalid `starting_street="preflop"`; verify `ValueError` raised with correct message.

**Expected:** `ValueError` with "river_betting must be a boolean" and "invalid starting_street".

**Actual:** ✓ Both raised `ValueError` with expected messages.

**Result:** ✓ PASS — Strict construction validated.

---

## Findings

### Blockers

None.

### Majors

None.

### Minors

None.

### Observations

1. **Backward Compatibility:** `river_betting` defaults to `False`, preserving existing behavior for callers who do not specify it.

2. **Opt-In Design:** `create_allstreet_root` explicitly sets `river_betting=True`, enabling full flop→turn→river action.

3. **Transition Logic:** After the fifth board card:  
   - If `river_betting=False` OR any player is all-in (`remaining[i] == 0`), state reaches `TERMINAL` immediately.  
   - If `river_betting=True` AND both players have chips behind, state opens river action.

4. **Accounting Precision:** Pot, stack, and commitment tracking is exact. Street-level `committed` resets to `(0, 0)` at street close; cumulative `total_contributed` persists.

5. **Zero-Sum Invariant:** All terminal returns satisfy `u0 + u1 = 0` within floating-point tolerance.

6. **Information Noninterference:** Player information keys depend only on own cards, public board, and public history—never on opponent's hidden cards.

7. **Determinism:** Repeated traversals with identical configs and actions produce identical states.

8. **Strict Construction:** Invalid inputs to `MultiStreetConfig` raise `ValueError` with clear messages; no silent coercion or internal exceptions leaked.

---

## Unauthorized Artifacts

None. Probe script written to `/tmp/f02_probes.py` and removed after execution. No repository paths modified except:

- `/home/genomix-node/poker-solver/research/phase4/s1-i1-final-audit/.hb/F02` (heartbeat, authorized)
- `/home/genomix-node/poker-solver/research/phase4/s1-i1-final-audit/02-state-chance.md` (this report, authorized)

---

## Conclusion

**Status:** ✓ PASS

All manifest hashes match. All 17 existing tests pass. All 11 executable probes pass. Zero blockers. Zero majors. Production APIs execute correctly. Backward compatibility preserved. Zero-sum invariant holds. Information noninterference verified. Determinism confirmed. Strict construction validated.

**Recommendation:** Approve S1-I1 candidate for MultiStreetState all-street chance and river transitions.

---

**Audit Completed:** 2026-09-15T18:05:30Z  
**Auditor Signature:** BryantGPT (non-author retry F02)
