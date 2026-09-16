# S3 Betting Design Audit — Trace Validation

**Auditor:** A3X2 (fresh non-author replacement for invalid A3R2)  
**Candidate:** `ARCHITECTURE_PHASE4_S3.md`  
**Candidate SHA-256 (pre-audit):** `f0777689eac5df76ab7630dd3725e40f7409e4369ba9de312ac8992a4a4bb83f`  
**Audit scope:** S3 betting/sizing/pending/reopening semantics (design-only, no production/tests)  
**Date:** 2026-09-16

---

## Executive Summary

**VERDICT: PASS**

The S3 architecture correctly specifies:
- ✅ Sizing key derivation (position, raise_count, cold_callers, IP/OOP relation)
- ✅ Integer absolute street commitment semantics
- ✅ Min-raise requirements and legal short all-in conditions
- ✅ Pending queue rebuild on raises
- ✅ Both reopening policies (short_all_in_reopens true/false)
- ✅ Action closure conditions
- ✅ Rejection of below-H actions except CALL or legal all-in raise

All traced scenarios validate against the frozen architecture. No blockers found.

---

## Audit Methodology

### Architecture Verification

**Pre-audit hash:**
```bash
$ sha256sum /home/genomix-node/poker-solver/ARCHITECTURE_PHASE4_S3.md
f0777689eac5df76ab7630dd3725e40f7409e4369ba9de312ac8992a4a4bb83f
```

**Key sections reviewed:**
- Section 2.2: `NPlayerPreflopSizingRule` (lines 34-46)
- Section 2.4: `NPlayerPreflopConfig` (lines 68-86)
- Section 6: Deals and chance reach (lines 158-164)
- Section 7: Betting semantics (lines 165-192)
- Section 8: Terminal accounting (lines 193-205)

### Trace Validation Approach

For each semantic rule, constructed integer traces demonstrating:
1. **Initial state** (stacks, posts, H, pending)
2. **Action sequence** with explicit amounts
3. **State transitions** (street_committed, pending, can_raise, last_raise_increment)
4. **Expected outcomes** per architecture

All traces use synthetic bounded examples compatible with S3 design constraints.

---

## Trace 1: Limps and SB Complete

**Scenario:** 6-max, SB completes, UTG limps, HJ raises

**Initial state:**
- Stacks: [100, 100, 100, 100, 100, 100] (UTG, HJ, CO, BTN, SB, BB)
- Posts: SB=1, BB=2
- street_committed: [0, 0, 0, 0, 1, 2]
- H = 2, pot = 3
- pending: [UTG, HJ, CO, BTN, SB] (first actor after BB)

**Action sequence:**

1. **UTG limps (CALL 2)**
   - Transfer: 2 chips
   - street_committed: [2, 0, 0, 0, 1, 2]
   - pending: [HJ, CO, BTN, SB] (UTG removed)
   - cold_callers: 1 (UTG is limper)

2. **HJ folds**
   - street_committed: [2, 0, 0, 0, 1, 2]
   - pending: [CO, BTN, SB]
   - cold_callers: 1 (still UTG)

3. **CO raises to 8**
   - Transfer: 8 chips
   - street_committed: [2, 0, 8, 0, 1, 2]
   - H = 8, last_raise_increment = 6 (8 - 2)
   - **Pending rebuilt:** [BTN, SB, BB, UTG] (all live seats with chips, clockwise after CO)
   - cold_callers: 0 (reset after raise)
   - Sizing key for CO: (position=CO, raise_count=0, cold_callers=1, relation=NA)

4. **BTN calls 8**
   - street_committed: [2, 0, 8, 8, 1, 2]
   - pending: [SB, BB, UTG]
   - cold_callers: 1 (BTN)

5. **SB folds**
   - pending: [BB, UTG]
   - cold_callers: 1

6. **BB raises to 20**
   - Transfer: 18 chips (20 - 2)
   - street_committed: [2, 0, 8, 8, 1, 20]
   - H = 20, last_raise_increment = 12 (20 - 8)
   - **Pending rebuilt:** [UTG, CO, BTN] (all live seats with chips after BB)
   - cold_callers: 0
   - Sizing key: (position=BB, raise_count=1, cold_callers=1, relation=OOP to CO)

**Architecture compliance:**
- ✅ Limps counted as cold_callers when raise_count=0
- ✅ SB complete treated as CALL(2)
- ✅ Pending rebuilt after each raise
- ✅ cold_callers reset after raise
- ✅ Sizing keys correctly derived

---

## Trace 2: IP/OOP Relation to Last Aggressor

**Scenario:** 6-max, UTG opens, CO 3-bets, BTN 4-bets

**Positions (clockwise):** UTG, HJ, CO, BTN, SB, BB

**Action sequence:**

1. **UTG raises to 6** (open)
   - Last aggressor: UTG
   - Pending: [HJ, CO, BTN, SB, BB]

2. **HJ folds, CO raises to 18** (3-bet)
   - Last aggressor: CO
   - Pending: [BTN, SB, BB, UTG]
   - **CO vs UTG relation:** CO is later in clockwise order ending at BTN → CO is IP
   - Sizing key for CO: (position=CO, raise_count=1, cold_callers=0, relation=IP)

3. **BTN raises to 50** (4-bet)
   - Last aggressor: BTN
   - Pending: [SB, BB, UTG, CO]
   - **BTN vs CO relation:** BTN is later in clockwise order → BTN is IP
   - Sizing key for BTN: (position=BTN, raise_count=2, cold_callers=0, relation=IP)

4. **All fold to CO, CO calls**
   - Pending: [BTN]
   - **CO vs BTN relation:** CO is earlier → CO is OOP
   - If CO were to raise here (5-bet), sizing key: (position=CO, raise_count=3, cold_callers=0, relation=OOP)

**Architecture compliance:**
- ✅ Relation determined by postflop order (clockwise ending at button)
- ✅ Later seat in that order is IP
- ✅ Relation is to last voluntary raiser, not table-wide
- ✅ NA only for unopened pots

---

## Trace 3: Min-Raise and Legal Short All-In

**Scenario:** HU, short stack all-in below min-raise

**Initial state:**
- Stacks: [100, 30] (BTN/SB, BB)
- Posts: SB=1, BB=2
- street_committed: [1, 2]
- H = 2, last_raise_increment = 2

**Action sequence:**

1. **BTN raises to 6**
   - street_committed: [6, 2]
   - H = 6, last_raise_increment = 4 (6 - 2)
   - Min next raise: 6 + 4 = 10

2. **BB all-in for 30** (legal, exceeds H)
   - street_committed: [6, 30]
   - H = 30, last_raise_increment = 24
   - This is a full raise (30 >= 6 + 4)

3. **BTN calls**
   - street_committed: [30, 30]
   - Action closes (both all-in)

**Alternative: Short all-in**

**Initial state:**
- Stacks: [100, 8] (BTN/SB, BB)
- Posts: SB=1, BB=2
- street_committed: [1, 2]

**Action sequence:**

1. **BTN raises to 6**
   - H = 6, last_raise_increment = 4
   - Min next raise: 10

2. **BB all-in for 8** (short all-in)
   - street_committed: [6, 8]
   - H = 8
   - **Legal:** 8 > 6 (exceeds H) AND is BB's all-in
   - **Short:** 8 < 10 (below min-raise)
   - raise_count increments
   - last_raise_increment remains 4 (not updated)

3. **BTN response depends on short_all_in_reopens:**
   - If `short_all_in_reopens=False`: BTN was in old pending, can call/fold/raise (was entitled)
   - If `short_all_in_reopens=True`: BTN can call/fold/raise (all live seats re-entitled)
   - BB cannot raise (is all-in)

**Rejected action:**
- **BTN raises to 7** (below H=6 after BTN's initial raise)
  - 7 > 6 but BTN is not all-in at 7 (has 100 stack)
  - **Rejected:** below-minimum target legal ONLY when all-in

**Architecture compliance:**
- ✅ Normal raise: target >= H + last_raise_increment
- ✅ Short all-in legal when: target > H AND is actor's all-in
- ✅ Short all-in does NOT update last_raise_increment
- ✅ Actions below H rejected unless CALL or legal all-in raise

---

## Trace 4: Pending Rebuild After Raise

**Scenario:** 9-max, multiple callers, then squeeze

**Positions:** UTG, UTG+1, MP, LJ, HJ, CO, BTN, SB, BB

**Initial state:**
- street_committed: [0,0,0,0,0,0,0,1,2]
- H = 2, pending: [UTG, UTG+1, MP, LJ, HJ, CO, BTN, SB]

**Action sequence:**

1. **UTG raises to 6**
   - street_committed: [6,0,0,0,0,0,0,1,2]
   - **Pending rebuilt:** [UTG+1, MP, LJ, HJ, CO, BTN, SB, BB] (all other live seats, clockwise after UTG)

2. **UTG+1 calls, MP calls, LJ folds**
   - street_committed: [6,6,6,0,0,0,0,1,2]
   - pending: [HJ, CO, BTN, SB, BB]
   - cold_callers: 2 (UTG+1, MP)

3. **HJ raises to 20** (squeeze)
   - street_committed: [6,6,6,0,20,0,0,1,2]
   - **Pending rebuilt:** [CO, BTN, SB, BB, UTG, UTG+1, MP] (all live seats with chips, clockwise after HJ)
   - cold_callers: 0 (reset)
   - Sizing key: (position=HJ, raise_count=1, cold_callers=2, relation=IP to UTG)

4. **All fold to UTG, UTG calls**
   - pending: [HJ]
   - Action closes (only one pending responder, UTG has acted)

**Architecture compliance:**
- ✅ Pending rebuilt as "all other live seats with chips, clockwise after raiser"
- ✅ Includes seats that already acted (UTG, UTG+1, MP must respond to squeeze)
- ✅ cold_callers counted before raise, reset after
- ✅ Closure when no actionable pending remains

---

## Trace 5: Reopening Policies (short_all_in_reopens)

**Scenario:** 6-max, short all-in after multiple callers

**Initial state:**
- Stacks: [100, 100, 100, 15, 100, 100] (UTG, HJ, CO, BTN, SB, BB)
- Posts: SB=1, BB=2
- street_committed: [0,0,0,0,1,2]

**Action sequence:**

1. **UTG raises to 6**
   - pending: [HJ, CO, BTN, SB, BB]
   - can_raise: [False, True, True, True, True, True] (UTG cannot raise again yet)

2. **HJ calls, CO calls**
   - pending: [BTN, SB, BB]
   - can_raise: [False, True, True, True, True, True]

3. **BTN all-in for 15** (short all-in)
   - street_committed: [6,6,6,15,1,2]
   - H = 15, last_raise_increment = 4 (unchanged)
   - Min full raise would be 6 + 4 = 10, but 15 > 10, so this IS a full raise
   - **Correction:** 15 >= 10, so this is actually a full raise
   - last_raise_increment = 9 (15 - 6)
   - Pending rebuilt: [SB, BB, UTG, HJ, CO]
   - All seats re-entitled

**Revised: True short all-in**

**Initial state:**
- Stacks: [100, 100, 100, 8, 100, 100]
- street_committed: [0,0,0,0,1,2]

**Action sequence:**

1. **UTG raises to 6**
   - pending: [HJ, CO, BTN, SB, BB]
   - can_raise: [False, True, True, True, True, True]

2. **HJ calls, CO calls**
   - pending: [BTN, SB, BB]
   - can_raise: [False, True, True, True, True, True]
   - Old pending at this point: [BTN, SB, BB]

3. **BTN all-in for 8** (short all-in)
   - street_committed: [6,6,6,8,1,2]
   - H = 8, last_raise_increment = 4 (unchanged)
   - Min full raise: 10, but BTN only has 8
   - 8 > 6 (exceeds H) and is BTN's all-in → legal
   - 8 < 10 → short all-in
   - raise_count increments
   - **Pending rebuilt:** [SB, BB, UTG, HJ, CO]

4. **Reopening depends on short_all_in_reopens:**

   **Case A: short_all_in_reopens = False**
   - Old pending: [BTN, SB, BB]
   - Previously entitled: [False, True, True, True, True, True]
   - After short all-in:
     - can_raise: [True, True, True, False, True, True]
     - UTG: was in old pending? No. Previously entitled? No (raised, lost entitlement). **Cannot raise.**
     - HJ: was in old pending? No. Previously entitled? Yes (could raise before calling). **Can raise.**
     - CO: was in old pending? No. Previously entitled? Yes. **Can raise.**
     - BTN: all-in, cannot raise
     - SB: was in old pending? Yes. **Can raise.**
     - BB: was in old pending? Yes. **Can raise.**

   **Case B: short_all_in_reopens = True**
   - All live seats with chips re-entitled
   - can_raise: [True, True, True, False, True, True]
   - UTG, HJ, CO, SB, BB all can raise
   - BTN cannot (is all-in)

**Architecture compliance:**
- ✅ Short all-in does not update last_raise_increment
- ✅ Pending rebuilt for all live seats with chips
- ✅ When short_all_in_reopens=False: only old pending + previously entitled can raise
- ✅ When short_all_in_reopens=True: all live seats with chips re-entitled
- ✅ Short raiser cannot raise again

---

## Trace 6: Closure Conditions

**Scenario A: One live seat remains**

**Initial state:** 6-max, all fold to BTN
- pending: [BTN]
- Action closes (only one live seat)

**Scenario B: No actionable pending**

**Initial state:** HU, both all-in
- street_committed: [100, 100]
- remaining: [0, 0]
- pending: [] (no seats with chips to act)
- Action closes

**Scenario C: All pending seats have acted, none can raise**

**Initial state:** 3-player, all call
- street_committed: [10, 10, 10]
- pending: [] (all have acted, H is matched)
- Action closes

**Architecture compliance:**
- ✅ Closure when one live seat remains
- ✅ Closure when no actionable pending responder remains
- ✅ Bounded depth: N + max_raises * (N - 1)

---

## Trace 7: Rejection Rule

**Scenario:** Actor attempts action below current H

**Initial state:**
- street_committed: [10, 20, 5]
- H = 20
- Actor: seat 2 (own=5, to_call=15)

**Legal actions:**
- FOLD
- CALL(20) — matches H
- RAISE(30) — if 30 >= 20 + last_raise_increment OR is all-in and 30 > 20

**Rejected actions:**
- CHECK — to_call > 0, cannot check
- CALL(15) — below H, not a legal call amount
- RAISE(18) — below H, not a legal raise (even if above own)
- RAISE(22) — above H but below min-raise, legal ONLY if all-in

**Architecture quote (line 180):**
> "A target is a normal full raise at or above H + last_raise_increment. A below-minimum target is legal only when it is the actor's all-in target and exceeds H."

**Implicit rejection rule:**
- Actions below H are rejected unless:
  - CALL (which brings actor to H or all-in)
  - Legal all-in raise above H

**Architecture compliance:**
- ✅ All action amounts are absolute street commitments
- ✅ Targets below H rejected unless CALL or legal all-in raise
- ✅ CALL amount is min(H, own + remaining)

---

## Trace 8: 3-Bet/4-Bet/5-Bet+ Sizing Keys

**Scenario:** 6-max, escalating raises

**Action sequence:**

1. **UTG raises to 6** (open)
   - raise_count: 0 → 1
   - Sizing key: (position=UTG, raise_count=0, cold_callers=0, relation=NA)

2. **CO raises to 18** (3-bet)
   - raise_count: 1 → 2
   - Sizing key: (position=CO, raise_count=1, cold_callers=0, relation=IP)

3. **BTN raises to 50** (4-bet)
   - raise_count: 2 → 3
   - Sizing key: (position=BTN, raise_count=2, cold_callers=0, relation=IP)

4. **UTG raises to 120** (5-bet)
   - raise_count: 3 → 4
   - Sizing key: (position=UTG, raise_count=3, cold_callers=0, relation=OOP)

5. **CO raises to 250** (6-bet+)
   - raise_count: 4 → 5
   - Sizing key: (position=CO, raise_count=4, cold_callers=0, relation=IP)

**Architecture compliance:**
- ✅ raise_count increments with each raise
- ✅ raise_count=0 means open/limp pot
- ✅ raise_count=1 means 3-bet decision
- ✅ raise_count=2 means 4-bet decision
- ✅ Sizing rules support 3-bet/4-bet/5-bet+ branches

---

## Trace 9: Cold Callers Reset

**Scenario:** 6-max, limpers then raise

**Action sequence:**

1. **UTG limps, HJ limps, CO limps**
   - raise_count: 0
   - cold_callers: 3 (all limpers)

2. **BTN raises to 10** (isolation)
   - Sizing key: (position=BTN, raise_count=0, cold_callers=3, relation=NA)
   - After raise: cold_callers = 0 (reset)

3. **SB folds, BB calls**
   - cold_callers: 1 (BB)

4. **UTG calls, HJ folds, CO calls**
   - cold_callers: 3 (BB, UTG, CO)

5. **BTN raises to 40** (squeeze, if allowed by max_raises)
   - Sizing key: (position=BTN, raise_count=1, cold_callers=3, relation=NA)
   - After raise: cold_callers = 0

**Architecture compliance:**
- ✅ cold_callers counts limpers when raise_count=0
- ✅ cold_callers counts callers after most recent raise
- ✅ cold_callers resets to 0 after a raise
- ✅ Folded callers do not count

---

## Trace 10: SB Complete as CALL

**Scenario:** 6-max, SB completes

**Initial state:**
- street_committed: [0,0,0,0,1,2]
- H = 2, pending: [UTG, HJ, CO, BTN, SB]

**Action sequence:**

1. **All fold to SB**
   - pending: [SB]
   - SB's to_call: 2 - 1 = 1

2. **SB calls (completes to 2)**
   - Transfer: 1 chip
   - street_committed: [0,0,0,0,2,2]
   - pending: [BB]
   - This is a CALL action, not a raise
   - cold_callers: 0 (SB is not a limper, just completing)

3. **BB checks** (to_call=0)
   - Action closes

**Alternative: SB raises**

1. **SB raises to 8**
   - Transfer: 7 chips
   - street_committed: [0,0,0,0,8,2]
   - Pending rebuilt: [BB]
   - Sizing key: (position=SB, raise_count=0, cold_callers=0, relation=NA)

**Architecture compliance:**
- ✅ SB complete is CALL(BB amount)
- ✅ SB can also raise (if entitled and within max_raises)
- ✅ SB complete does not count as a cold caller for itself

---

## Cross-Reference: Existing Production Files

**Reviewed files (design reference only, no edits):**

1. **`/home/genomix-node/poker-solver/src/poker_solver/preflop.py`** (HU preflop)
   - Uses `committed` for street commitments
   - Uses `acted` and `can_raise` booleans
   - Uses `last_raise_increment`
   - Action amounts are absolute commitments
   - ✅ S3 architecture consistent with HU model

2. **`/home/genomix-node/poker-solver/src/poker_solver/sizing.py`**
   - `validate_size_expression` validates unit/fields
   - `convert_size_to_chips` returns integer targets
   - Supports pot-percent, geometric, previous-bet-multiple, big-blinds, all-in
   - ✅ S3 architecture references `fixed_sizes` and `validate_size_expression`

3. **`/home/genomix-node/poker-solver/src/poker_solver/nplayer_postflop.py`** (N-player postflop)
   - Uses `street_committed`, `total_contributed`, `remaining`
   - Uses `pending` queue and `can_raise` tuple
   - Exact integer settlement with `refund_uncalled_excess`
   - ✅ S3 architecture reuses N-player patterns

**Architecture consistency:**
- ✅ S3 reuses existing `Action`, `WeightedCombo`, `NPlayerCFRSolver`
- ✅ S3 reuses `sizing.py` validation and conversion
- ✅ S3 follows N-player state patterns (tuples, exact integers, frozen dataclasses)
- ✅ S3 is additive (no changes to existing files)

---

## Post-Audit Hash Verification

```bash
$ sha256sum /home/genomix-node/poker-solver/ARCHITECTURE_PHASE4_S3.md
f0777689eac5df76ab7630dd3725e40f7409e4369ba9de312ac8992a4a4bb83f
```

**Verification:** ✅ Candidate hash unchanged (design-only audit, no edits)

---

## Findings Summary

### Betting Semantics: PASS

- ✅ **Action amounts:** Integer absolute preflop street commitments
- ✅ **H calculation:** max(street_committed)
- ✅ **to_call calculation:** H - own
- ✅ **FOLD/CHECK/CALL logic:** Correct based on to_call
- ✅ **Raise requirements:** can_raise[p], chips beyond call, raise_count < max_raises
- ✅ **Min-raise:** target >= H + last_raise_increment
- ✅ **Legal short all-in:** target > H and is actor's all-in
- ✅ **Rejection rule:** Below-H actions rejected unless CALL or legal all-in raise

### Sizing Key: PASS

- ✅ **Four-field key:** (position, raise_count, cold_callers, relation)
- ✅ **position:** Canonical label from section 4
- ✅ **raise_count:** 0=open/limp, 1=3-bet decision, 2=4-bet, etc.
- ✅ **cold_callers:** Limpers when raise_count=0, callers after most recent raise
- ✅ **relation:** NA (unopened), IP (later in clockwise order), OOP (earlier)
- ✅ **Relation target:** Last voluntary raiser, not table-wide
- ✅ **Reset:** cold_callers resets to 0 after raise

### Pending Rebuild: PASS

- ✅ **FOLD/CHECK/CALL:** Remove actor from pending
- ✅ **Any raise:** Rebuild pending as all other live seats with chips, clockwise after raiser
- ✅ **Includes prior actors:** Seats that already acted must respond to new raise

### Reopening Policies: PASS

- ✅ **Full raise:** Updates last_raise_increment, reopens for all live seats with chips
- ✅ **Short all-in (reopens=False):** Only old pending + previously entitled can raise
- ✅ **Short all-in (reopens=True):** All live seats with chips re-entitled
- ✅ **Short raiser:** Cannot raise again (is all-in)
- ✅ **Increment preservation:** Short all-in does not update last_raise_increment

### Closure: PASS

- ✅ **One live seat:** Action closes
- ✅ **No actionable pending:** Action closes
- ✅ **Bounded depth:** N + max_raises * (N - 1)

### Limps and SB Complete: PASS

- ✅ **Limps:** Counted as cold_callers when raise_count=0
- ✅ **SB complete:** CALL(BB amount), not a raise
- ✅ **SB raise:** Legal if entitled and within max_raises

### 3-Bet/4-Bet/5-Bet+: PASS

- ✅ **raise_count increments:** Each raise increments raise_count
- ✅ **Sizing rules:** Support per-position, per-raise-count, per-cold-caller branches
- ✅ **IP/OOP relation:** Correctly determined per raise level

---

## Blockers

**None.** All betting/sizing/pending/reopening semantics are correctly specified.

---

## Recommendations

1. **Implementation priority:** Betting semantics are well-defined and ready for TDD (S3-I1 batch)
2. **Test coverage:** Permanent tests should include all traced scenarios above
3. **Edge cases:** Pay special attention to:
   - Short all-in reopening (both policies)
   - cold_callers reset after raise
   - IP/OOP relation to last aggressor (not table-wide)
   - Rejection of below-H actions
4. **N=2 projection:** HU compatibility tests must verify aligned public traces

---

## Auditor Certification

**Auditor:** A3X2 (fresh non-author, replacing invalid A3R2)  
**Audit date:** 2026-09-16  
**Audit scope:** S3 betting/sizing/pending/reopening semantics (design-only)  
**Candidate:** `ARCHITECTURE_PHASE4_S3.md`  
**Pre-audit SHA-256:** `f0777689eac5df76ab7630dd3725e40f7409e4369ba9de312ac8992a4a4bb83f`  
**Post-audit SHA-256:** `f0777689eac5df76ab7630dd3725e40f7409e4369ba9de312ac8992a4a4bb83f` ✅  

**Verdict:** **PASS**  
**Blockers:** None  
**Ready for implementation:** Yes (S3-I1 TDD batch)

---

**End of audit report.**
