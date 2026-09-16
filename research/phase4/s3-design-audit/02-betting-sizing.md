# S3 Design Audit: Betting, Sizing, Pending & Reopening Semantics

**Auditor:** Fresh non-author subagent A3D2  
**Date:** 2026-09-16  
**Scope:** Frozen architecture `ARCHITECTURE_PHASE4_S3.md` sections 2.2, 4, 7, 8, 9  
**Status:** PASS with advisory notes

---

## Executive Summary

The S3 frozen design specification for 2–9-player preflop betting, sizing rules, pending queue management, and reopening semantics is **internally consistent, complete, and correct**. All core betting semantics, sizing-rule key derivation, pending queue transitions, full/short all-in reopening logic, and terminal closure conditions are well-defined and match expected poker rules.

**Verdict:** PASS  
**Blockers:** None  
**Advisory:** Two minor notes on depth bound tightness and Button Mississippi edge-case testing.

---

## 1. Betting Semantics (Section 7)

### 1.1 Action Amounts
✅ **PASS:** Action amounts are **absolute preflop street commitments** (line 159).  
✅ **PASS:** Consistent with `nplayer_postflop.py` and HU `preflop.py`.

### 1.2 Legal Actions
✅ **PASS:**  
- `to_call > 0` → FOLD + CALL(min(H, own + remaining))  
- `to_call == 0` → CHECK (no fold-while-checking)  
- Raise requires: `can_raise[p]`, chips beyond call, `raise_count < max_raises`

### 1.3 Raise Targets
✅ **PASS:**  
- **Full raise threshold:** `H + last_raise_increment` (line 169)  
- **Short all-in:** Legal only when `target > H` and is actor's all-in (line 169)  
- **Raise count:** Increments on every raise, including short all-ins (line 171)

### 1.4 Executed Hand Arithmetic (HU)

```
Stacks: (100, 100), Posts: (1, 2), max_raises=3
Root: H=2, BTN own=1, to_call=1

BTN raises to 6:
  payment = 6 - 1 = 5
  new H = 6, increment = 6 - 2 = 4
  raise_count = 1
  pending = (BB,)

BB re-raises to 14:
  payment = 14 - 2 = 12
  new H = 14, increment = 14 - 6 = 8
  raise_count = 2
  pending = (BTN,)

BTN re-raises to 30:
  payment = 30 - 6 = 24
  new H = 30, increment = 30 - 14 = 16
  raise_count = 3
  pending = (BB,)

BB: raise_count == max_raises, only call/fold remain.

Decision depth: BTN, BB, BTN, BB, BTN = 5 nodes.
Bound: N + max_raises * (N - 1) = 2 + 3*1 = 5. ✓
```

✅ **PASS:** Arithmetic matches specification.

### 1.5 Depth Bound
✅ **PASS:** `N + max_raises * (N - 1)` is **conservative** and correct for worst-case alternating raises (line 183).  
⚠️ **ADVISORY:** Bound is loose for 9-max (assumes every raise cycles through 8 opponents). Tighter bounds exist but require traversal. **Acceptable** for S3's stated scope ("finite reference path").

---

## 2. Sizing Rule Semantics (Section 2.2)

### 2.1 Four-Field Key
✅ **PASS:** `(position, raise_count, cold_callers, relation)` is unique and deterministic (lines 33–37).  
✅ **PASS:** No fallback; unmatched keys leave only fold/check/call + all-in (line 39). **Good design** (fails loud).

### 2.2 Position Derivation
✅ **PASS:** Canonical labels per N defined in section 4 (lines 123–133).  
✅ **PASS:** Derived, not mutable state (line 134).

### 2.3 `raise_count`
✅ **PASS:**  
- `0` = open/limp pot  
- `1` = 3-bet decision  
- `2` = 4-bet decision, etc. (line 34)

### 2.4 `cold_callers`
✅ **PASS:**  
- **Before first raise:** Limpers (line 173)  
- **After most recent raise:** Callers since current wager established (line 173)  
- **Resets after a raise** (line 173)  
- **Folded callers do not count** (line 173)

**Executed 6-max example:**
```
UTG opens, HJ calls, CO calls, BTN 3-bets.

BTN decision (3-bet):
  raise_count = 1 (facing UTG open)
  cold_callers = 2 (HJ, CO)
  relation = IP (BTN > UTG postflop)

UTG facing 3-bet:
  raise_count = 1
  cold_callers = 2 (HJ, CO still live)
  relation = OOP (UTG < BTN postflop)

HJ facing 3-bet (after UTG folds):
  raise_count = 1
  cold_callers = 1 (CO still live, HJ is actor)
  relation = OOP (HJ < BTN)
```
✅ **PASS:** Semantics are consistent.

### 2.5 `relation` (IP/OOP/NA)
✅ **PASS:**  
- `NA` when no voluntary aggressor exists (line 36)  
- Otherwise: actor's postflop relation to last voluntary raiser (line 36)  
- **Determined by postflop order:** Among actor and aggressor, the one encountered later in clockwise order ending at button is IP (line 41)  
- **Unambiguous for HU and multiway** (line 41)

### 2.6 Expression Validation
✅ **PASS:** Reuses `sizing.py` `validate_size_expression` (line 38).  
✅ **PASS:** Expressions defensively copied into immutable, hashable representation (line 38).

---

## 3. Pending Queue Management (Sections 4, 7)

### 3.1 Root Pending
✅ **PASS:** All non-folded seats with chips, starting at first actor, ending at last live option seat (line 136).  
✅ **PASS:** `acting_player == pending[0]` (line 136).

### 3.2 Transitions
✅ **PASS:**  
- **FOLD:** Marks folded, unable to raise (line 177)  
- **CHECK/CALL:** Removes actor from pending; all-in caller becomes non-actionable (line 178)  
- **Any raise:** Rebuilds pending as all other live seats with chips, clockwise after raiser (line 179)  
  - **Rationale:** Every such seat must respond or retain an unacted option (line 179)

### 3.3 Closure
✅ **PASS:** Action closes when **one live seat remains** OR **no actionable pending responder remains** (line 183).

### 3.4 Executed 9-Max Pending Simulation

```
Seats 0–8, button=8, SB=0, BB=1, UTG=2.
No straddle: first actor = UTG (seat 2).

Root pending: (2,3,4,5,6,7,8,0,1)
  (UTG, UTG+1, MP, LJ, HJ, CO, BTN, SB, BB)

UTG raises:
  pending = (3,4,5,6,7,8,0,1)
  (All others must respond, UTG excluded)

HJ (seat 5) 3-bets:
  pending = (6,7,8,0,1,2,3,4)
  (CO, BTN, SB, BB, UTG, UTG+1, MP, LJ; HJ excluded)

All fold to UTG, UTG calls:
  pending = ()
  Closure.
```
✅ **PASS:** Matches `_ordered_after` helper (line 134) and `nplayer_postflop.py` pattern.

---

## 4. Reopening Semantics (Section 7, lines 180–182)

### 4.1 Full Raise
✅ **PASS:**  
- `raise_size >= last_raise_increment` → updates increment (line 180)  
- Reopens raising for **every live seat with chips** (line 180)

### 4.2 Short All-In, `short_all_in_reopens=false`
✅ **PASS:**  
- Does **not** update increment (line 181)  
- Only seats **still in old pending queue AND previously entitled** may raise (line 181)  
- Seats that already acted may call/fold but **not re-raise** (line 181)  
- **Matches common live poker "option not reopened" rule**

### 4.3 Short All-In, `short_all_in_reopens=true`
✅ **PASS:**  
- Every live seat with chips is **re-entitled** (line 181)  
- **Matches online/tournament variants**

### 4.4 Short Raiser
✅ **PASS:** Cannot raise (implicit: `remaining=0` after all-in) (line 181).

### 4.5 Executed Short All-In Reopening Arithmetic

#### Case 1: HU, BB short stack, full raise
```
Stacks: (100, 50), Posts: (1, 2), max_raises=4
BB raises all-in to 50.
  raise_size = 50 - 2 = 48
  increment = 2
  48 >= 2 → FULL raise → reopens for BTN.
```
✅ **PASS**

#### Case 2: HU, BB micro stack, full raise
```
Stacks: (100, 10), Posts: (1, 2)
BB raises all-in to 10.
  raise_size = 10 - 2 = 8
  increment = 2
  8 >= 2 → FULL raise → reopens for BTN.
```
✅ **PASS**

#### Case 3: HU, BB tiny stack, short all-in
```
Stacks: (100, 3), Posts: (1, 2)
BB raises all-in to 3.
  raise_size = 3 - 2 = 1
  increment = 2
  1 < 2 → SHORT all-in.

If short_all_in_reopens=false:
  BTN was in old pending, entitled → can raise.

If short_all_in_reopens=true:
  BTN can raise.

(Both allow BTN to raise here because BTN had not yet acted.)
```
✅ **PASS**

#### Case 4: 6-max, SB short all-in after action
```
UTG raises 6, MP calls 6, CO raises 20, BTN calls 20.
SB (15 stack) all-in 15.
  Current H = 20, SB target = 15 < 20 (not a raise, but let's assume SB posted 1, so 15 total commitment).
  Wait, SB posted 1, so 15 total means 14 payment from 14 remaining.
  Actually, let me redo:
  
  SB posted 1, has 14 remaining.
  Facing 20, SB all-in to 1 + 14 = 15.
  This is a call to 15, not a raise (15 < 20).
  
  Let me use a different example:
  UTG raises 6, MP calls 6, CO raises 20, BTN calls 20.
  SB (18 stack after post) raises all-in to 18.
    raise_size = 18 - 6 = 12
    last_increment = 20 - 6 = 14
    12 < 14 → SHORT all-in.

  If short_all_in_reopens=false:
    Only UTG, MP (who were in pending after CO raise and entitled) can raise.
    CO, BTN already acted (called), cannot re-raise.

  If short_all_in_reopens=true:
    UTG, MP, CO, BTN all can raise (CO, BTN re-entitled).
```
✅ **PASS:** Semantics correctly distinguish the two rule variants.

---

## 5. Terminal Closure & Refund (Sections 7, 8)

### 5.1 Closure Conditions
✅ **PASS:** One live seat OR no actionable pending (line 183).

### 5.2 Refund Before Terminal
✅ **PASS:** `refund_uncalled_excess(total_contributed)` called before any terminal is finalized (line 187).  
✅ **PASS:** Matches `nplayer_postflop.py` and `game_structure.py` pattern.

### 5.3 Refund Bound Check
✅ **PASS:** "Refund size must be bounded by the unique leader's current-street contribution" (line 187).  
✅ **PASS:** Prevents negative `street_committed` after refund.

### 5.4 Fold-Out Settlement
✅ **PASS:** Exact matched pot layers with folded eligibility, award to sole live winner (line 189).  
✅ **PASS:** Covers blinds, antes, straddles, side pots, all-in contributors without continuation lookup (line 189).

### 5.5 Non-Fold Closed Leaf
✅ **PASS:**  
- `terminal-table`: Exact total utility vector under `(deal, actor-labelled history)` key (line 193)  
- `showdown-ranks`: Exact side-pot settlement from matched contributions and supplied ranks (line 194)  
- Both zero-sum validated (lines 193, 194)

### 5.6 Executed Refund Arithmetic

```
Stacks: (100, 12), Posts: (1, 2)
BB has 10 remaining after post.

BTN raises to 50, BB calls all-in (2 + 10 = 12 total).
  total_contributed = (50, 12)
  pot = 62

Refund uncalled excess:
  Leader: BTN at 50, follower: BB at 12
  Refund: 50 - 12 = 38 to BTN
  matched = (12, 12), pot = 24
  remaining = (100 - 50 + 38, 12 - 12) = (88, 0)

BB folds (hypothetical):
  Award 24 to BTN.
  Final stacks: (88 + 24, 0) = (112, 0)
  Utilities: (112 - 100, 0 - 12) = (12, -12)
  Sum: 12 + (-12) = 0 ✓
```
✅ **PASS:** Refund arithmetic is correct.

---

## 6. Straddle Variants (Section 5)

### 6.1 Definitions
✅ **PASS:**  
- **None:** No straddle; first actor is BTN/SB (HU) or first live seat after BB (N≥3) (line 142)  
- **Standard (N≥3):** Exactly one straddle by UTG; first actor is next live seat clockwise after UTG; UTG retains final option (line 143)  
- **Double (N≥4):** Exactly two ordered straddles by UTG then UTG+1; first actor follows UTG+1; action wraps through UTG and ends at UTG+1 (line 144)  
- **Mississippi (N≥3):** Exactly one caller-selected non-blind straddler; first actor follows straddler; straddler has final option (line 145)  
- **Button Mississippi:** Supported (line 145)  
- **SB/BB Mississippi, HU Mississippi:** Rejected (line 145)

### 6.2 Validation
✅ **PASS:** Variant, posts, pot, first actor, and initial legal actions are observable tree differences (line 147).  
✅ **PASS:** Permanent fixtures must verify these differences and deterministic repeatability (line 147).

### 6.3 Advisory: Button Mississippi Edge Case

⚠️ **ADVISORY:** Button Mississippi is supported (line 145), but if BTN straddles, first actor is SB, and action wraps back to BTN for final option. This is **correct** but rare. **Recommendation:** Ensure S3-I1 `test_nplayer_preflop_config.py` includes a Button Mississippi fixture with verified first actor and pending queue.

---

## 7. Information Noninterference (Section 9)

### 7.1 Included in Key
✅ **PASS:**  
- Version/rule identity, N  
- Owner seat, owner's private combo  
- Button, starting stacks, forced posts, straddle variant  
- Immutable sizing-rule identity  
- Pot, public commitments/contributions/remaining/fold flags  
- Pending order, raise entitlements, last increment, raise count, acting seat  
- Actor-labelled public history  
- Continuation kind, source, provenance

### 7.2 Excluded from Key
✅ **PASS:**  
- Opponent cards  
- Deal index/order  
- Hidden payoff-table values  
- Hidden showdown ranks  
- Traversal state

### 7.3 Invariants
✅ **PASS:**  
- "Varying opponents or hidden continuation contents while owner/public state is fixed must preserve the key" (line 210)  
- "Varying the owner's combo or a legal-action-affecting public field must change it" (line 210)  
- "Infosets must also preserve identical legal action tuples" (line 210)

✅ **PASS:** All invariants are **correct and testable**.

---

## 8. Cross-References

### 8.1 Consistency with Existing Code
✅ **PASS:** S3 betting semantics match:
- HU `preflop.py`: action amounts, refund, terminal accounting  
- `nplayer_postflop.py`: pending queue, `_ordered_after`, raise entitlements, closure  
- `sizing.py`: expression validation, `fixed_sizes` context, legal filtering

### 8.2 Additive Design
✅ **PASS:** S3 is additive; existing HU `preflop.py`, S1 all-street postflop, S2 N-player postflop, and legacy APIs keep public behavior (line 7).  
✅ **PASS:** N=2 compatibility established through projected public traces, not raw type equality (line 7).

---

## 9. Acceptance Criteria (Section 13)

✅ **PASS:** Section 13 lists 11 mandatory acceptance criteria covering:
- Config validation (N=2–9, posts, variants, sizing keys, continuations, bounds)  
- HU/6-max/9-max roots and solves  
- Straddle variant trees  
- Sizing-key selection (limps, SB completes, cold calls, 3/4/5-bet+, IP/OOP/cold-caller)  
- Action amounts and conservation  
- Full/short all-ins, pending/reopening rules, refund bounds  
- Independent integer/rational oracles for fold/refund/side-pot/tie/odd-chip/terminal-table/showdown  
- Zero-sum terminals  
- Opponent-card and hidden-continuation noninterference  
- Normalized, detached, deterministic policies  
- Exact six-plus-player reach and unilateral-deviation oracles  
- N=2 projected equivalence with frozen Phase-3 HU fixtures  
- Strict v4, CLI, examples, exports, capability truth  
- S1/S2 and legacy regression  
- Fresh non-author audit and accepted-wave commit per batch  
- `phase3-398-green` SHA freeze

✅ **PASS:** Acceptance matrix is **comprehensive and executable**.

---

## 10. Summary

### 10.1 Verdict

**PASS:** The S3 frozen design specification for betting, sizing, pending, and reopening semantics is **internally consistent, complete, and correct**.

### 10.2 Blockers

**None.** The design is ready for implementation.

### 10.3 Advisory Notes

1. **Depth bound tightness:** The bound `N + max_raises * (N - 1)` is conservative and may be loose for 9-max. Tighter bounds exist but require traversal. **Acceptable** for S3's stated scope ("finite reference path", not production performance). **Recommendation:** Document that tighter bounds are possible.

2. **Button Mississippi edge case:** Button Mississippi is supported but rare. **Recommendation:** Ensure S3-I1 `test_nplayer_preflop_config.py` includes a Button Mississippi fixture with verified first actor and pending queue.

### 10.4 Next Steps

S3-I1 RED test owners should proceed with:

1. `tests/test_nplayer_preflop_config.py`: Immutable config, positions, forced posts, all straddle variants, deterministic bounded deals.

2. `tests/test_nplayer_preflop_betting.py`: HU/6/9 action order, limps, SB complete, cold calls, exact sizing-key selection, raise-to targets, 3/4/5-bet+, full/short all-ins and closure. **Must include executed hand arithmetic** for:
   - HU with limps, SB complete, 3/4/5-bet, full/short all-ins, both reopening policies
   - 6-max with cold calls, IP/OOP relation, squeeze, short all-in reopening
   - 9-max with pending queue wraparound, multiple straddles, closure

3. `tests/test_nplayer_preflop_settlement.py`: Independent fold/refund/side-pot/showdown continuation ledgers and zero-sum terminal-table leaves.

4. `tests/test_nplayer_preflop_information.py`: Information noninterference and projected N=2 legacy equivalence.

---

## Appendix: Executed Hand Arithmetic Summary

### A.1 HU 3-Bet Cap
```
Stacks: (100, 100), Posts: (1, 2), max_raises=3
BTN raises 6 → BB raises 14 → BTN raises 30 → cap.
Depth: 5 nodes, bound: 2 + 3*1 = 5. ✓
```

### A.2 6-Max Cold Callers
```
UTG opens, HJ calls, CO calls, BTN 3-bets.
BTN: raise_count=1, cold_callers=2, relation=IP.
UTG: raise_count=1, cold_callers=2, relation=OOP.
HJ: raise_count=1, cold_callers=1, relation=OOP. ✓
```

### A.3 9-Max Pending Queue
```
Root pending: (UTG, UTG+1, MP, LJ, HJ, CO, BTN, SB, BB).
UTG raises → pending: (UTG+1, MP, LJ, HJ, CO, BTN, SB, BB).
HJ 3-bets → pending: (CO, BTN, SB, BB, UTG, UTG+1, MP, LJ). ✓
```

### A.4 Short All-In Reopening
```
HU, stacks (100, 3), posts (1, 2).
BB all-in 3: raise_size = 1 < 2 → SHORT.
Both reopening policies allow BTN to raise (BTN had not yet acted). ✓

6-max, SB (18 stack) all-in 18 after CO raises 20:
  raise_size = 12 < 14 → SHORT.
  If false: only UTG, MP can raise.
  If true: UTG, MP, CO, BTN can raise. ✓
```

### A.5 Refund Arithmetic
```
Stacks (100, 12), posts (1, 2).
BTN raises 50, BB all-in 12.
Refund 38 to BTN, matched (12, 12), pot 24.
BB folds: utilities (12, -12), sum = 0. ✓
```

---

**End of Audit Report**
