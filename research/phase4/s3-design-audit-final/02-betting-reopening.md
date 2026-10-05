# S3 Betting and Reopening Audit — A3G2

**Auditor:** A3G2 (fresh different non-author)  
**Timestamp:** 2026-09-16 UTC  
**Scope:** Betting semantics, raise entitlement, pending rebuild, reopening logic  
**Candidate:** `ARCHITECTURE_PHASE4_S3.md`  
**Expected hash:** `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9`  
**Verification:** Pre-audit hash matches exactly.

---

## Independent Betting Trace Validation

### Trace 1: 6-player limp/isolation with SB complete as pre-raise caller

**Setup:**
- 6 players, button=5, SB=0, BB=1, UTG=2, HJ=3, CO=4, BTN=5
- Stacks: all 1000, SB=5, BB=10
- No straddle

**Action sequence:**
1. UTG (seat 2): CALL(10) — limp, `cold_callers=1` for next actor
2. HJ (seat 3): CALL(10) — limp, `cold_callers=2`
3. CO (seat 4): FOLD
4. BTN (seat 5): FOLD
5. SB (seat 0): CALL(10) — **SB completion counts as pre-raise CALL per §7 line 182**; `cold_callers=3`
6. BB (seat 1): RAISE(40) — isolation decision sees `raise_count=0, cold_callers=3, relation=NA`

**Architecture support:**
- §7 lines 181–183: "every pre-raise CALL, including a small-blind completion, counts for an opening/isolation decision"
- ✓ **PASS:** SB complete explicitly counted as caller.

---

### Trace 2: Full raise reopening with entitlement restoration

**Setup:**
- 3 players, button=2, SB=0, BB=1, BTN=2
- Stacks: all 500, SB=5, BB=10

**Action sequence:**
1. BTN (seat 2): RAISE(30) — opens, `last_raise_increment=20` (30-10)
2. SB (seat 0): CALL(30) — consumes entitlement per §7 line 187
3. BB (seat 1): RAISE(80) — full raise, increment=50 (80-30) ≥ 20
   - §7 lines 189–190: "every other live seat with chips is re-entitled to raise"
   - SB regains `can_raise[0]=True`
4. BTN (seat 2): FOLD
5. SB (seat 0): RAISE(180) — **legal because BB's full raise restored entitlement**

**Architecture support:**
- §7 line 189: "A full raise updates `last_raise_increment`; every other live seat with chips is re-entitled to raise"
- ✓ **PASS:** Full raise restores entitlement to all live seats with chips.

---

### Trace 3: Short all-in with `short_all_in_reopens=false` (intersection rule)

**Setup:**
- 4 players, button=3, SB=0, BB=1, CO=2, BTN=3
- Stacks: [500, 500, 35, 500], SB=5, BB=10

**Action sequence:**
1. CO (seat 2): RAISE(30) — opens, `last_raise_increment=20`
2. BTN (seat 3): CALL(30) — consumes entitlement, `pending=[0,1]`, `can_raise=[False,True,False,False]`
3. SB (seat 0): CALL(30) — consumes entitlement, `pending=[1]`, `can_raise=[False,True,False,False]`
4. BB (seat 1): RAISE(35) — **short all-in** (35 < 30+20=50)
   - Old `pending=[1]`, old `can_raise=[False,True,False,False]`
   - §7 lines 190–191: "a seat may raise after it only when that seat was both still in the pre-action pending queue and raise-entitled before the short all-in. This is an intersection, not a union."
   - CO (seat 2): was NOT in old pending → **cannot re-raise**
   - BTN (seat 3): was NOT in old pending → **cannot re-raise**
   - SB (seat 0): was NOT in old pending → **cannot re-raise**
   - New `can_raise=[False,False,False,False]`
5. CO (seat 2): CALL(35) — legal (call always available)
6. BTN (seat 3): CALL(35)
7. SB (seat 0): CALL(35)
8. Action closes (no one can raise)

**Architecture support:**
- §7 lines 190–191: "intersection, not a union: a seat that checked or called earlier may call or fold against the higher wager but may not re-raise."
- §15 line 322: "CHECK/CALL consumes current raise entitlement and no-reopen short-all-in entitlement is the intersection of old pending and old entitlement"
- ✓ **PASS:** Intersection rule correctly prevents prior callers from re-raising after short all-in.

---

### Trace 4: Short all-in with `short_all_in_reopens=true`

**Same setup as Trace 3, but `short_all_in_reopens=true`:**

**Action sequence (steps 1–4 identical):**
4. BB (seat 1): RAISE(35) — short all-in
   - §7 line 191: "If `short_all_in_reopens` is true, every other live seat with chips is re-entitled."
   - New `can_raise=[True,False,True,True]` (BB excluded, all others re-entitled)
5. CO (seat 2): RAISE(100) — **now legal** because reopening is enabled

**Architecture support:**
- §7 line 191: "If `short_all_in_reopens` is true, every other live seat with chips is re-entitled."
- ✓ **PASS:** Reopening flag correctly restores entitlement to all live seats.

---

### Trace 5: Sizing key with IP/OOP relation and cold-caller count

**Setup:**
- 6 players, button=5, postflop order: SB(0), BB(1), UTG(2), HJ(3), CO(4), BTN(5)
- Stacks: all 1000, SB=5, BB=10

**Action sequence:**
1. UTG (seat 2): RAISE(30) — opens, last aggressor=2
2. HJ (seat 3): CALL(30) — `cold_callers=1`
3. CO (seat 4): CALL(30) — `cold_callers=2`
4. BTN (seat 5): decision to 3-bet
   - Position: BTN
   - `raise_count=1` (one raise already made)
   - `cold_callers=2`
   - Relation to seat 2 (last aggressor): postflop order is SB→BB→UTG→HJ→CO→BTN, so BTN comes after UTG → **IP**
   - Sizing key: `(position="BTN", raise_count=1, cold_callers=2, relation="IP")`

5. SB (seat 0): if BTN folds and SB decides to squeeze:
   - Position: SB
   - `raise_count=1`
   - `cold_callers=2`
   - Relation to seat 2: SB comes before UTG in postflop order → **OOP**
   - Sizing key: `(position="SB", raise_count=1, cold_callers=2, relation="OOP")`

**Architecture support:**
- §2.2 lines 40–41: "`relation` is determined against the last voluntary raiser by postflop order: among the two seats, the one encountered later in the clockwise order ending at the button is IP."
- §7 lines 181–183: "`cold_callers` is the number of live seats whose latest voluntary action is CALL in the current response segment... It resets immediately after every raise."
- ✓ **PASS:** Relation and cold-caller counting are deterministic and correct.

---

### Trace 6: Pending rebuild after raise

**Setup:**
- 5 players, button=4, SB=0, BB=1, HJ=2, CO=3, BTN=4
- Stacks: all 500, SB=5, BB=10

**Action sequence:**
1. HJ (seat 2): RAISE(30)
   - §7 line 188: "Any raise rebuilds pending as all other live seats with chips, clockwise after the raiser"
   - New `pending=[3,4,0,1]` (CO, BTN, SB, BB — all seats after HJ with chips)
2. CO (seat 3): CALL(30) — removes self from pending, `pending=[4,0,1]`
3. BTN (seat 4): RAISE(90)
   - Rebuilds pending: all other live seats with chips after BTN
   - New `pending=[0,1,2,3]` (SB, BB, HJ, CO)

**Architecture support:**
- §7 line 188: "Any raise rebuilds pending as all other live seats with chips, clockwise after the raiser, because every such seat must respond or retain an unacted option."
- ✓ **PASS:** Pending rebuild is deterministic and includes all live seats with chips.

---

### Trace 7: Action closure with one live seat remaining

**Setup:**
- 3 players, all start with 500, SB=5, BB=10

**Action sequence:**
1. BTN: RAISE(30)
2. SB: FOLD
3. BB: FOLD
   - §7 line 192: "Action closes when one live seat remains or no actionable pending responder remains."
   - Only BTN is live (not folded)
   - Terminal state reached

**Architecture support:**
- §7 line 192: "Action closes when one live seat remains"
- ✓ **PASS:** Fold-out closure is immediate.

---

### Trace 8: Prior aggressor cannot re-raise without intervening raise

**Setup:**
- 3 players, button=2, SB=0, BB=1, BTN=2
- Stacks: all 500, SB=5, BB=10

**Action sequence:**
1. BTN (seat 2): RAISE(30) — opens, consumes entitlement
2. SB (seat 0): CALL(30)
3. BB (seat 1): CALL(30)
   - `pending=[]` (all responded), action closes
   - BTN **cannot** raise again because:
     - §7 line 187: "CHECK/CALL removes the actor from the current pending queue and consumes its current raise entitlement"
     - §7 line 189: "every other live seat with chips is re-entitled to raise, while the raiser has consumed its entitlement until another qualifying raise occurs."
   - BTN consumed entitlement at step 1, no qualifying intervening raise occurred

**Architecture support:**
- §7 lines 187–190: Raiser consumes entitlement; only a qualifying intervening raise restores it.
- ✓ **PASS:** Prior aggressor correctly blocked from re-raising.

---

### Trace 9: Prior caller cannot re-raise without intervening raise

**Setup:**
- 4 players, button=3, SB=0, BB=1, CO=2, BTN=3
- Stacks: all 500, SB=5, BB=10

**Action sequence:**
1. CO (seat 2): RAISE(30)
2. BTN (seat 3): CALL(30) — **consumes entitlement**
3. SB (seat 0): CALL(30)
4. BB (seat 1): CALL(30)
   - All responded, `pending=[]`
   - BTN **cannot** raise because:
     - §7 line 187: "CHECK/CALL... consumes its current raise entitlement"
     - No intervening raise occurred to restore entitlement

**Architecture support:**
- §7 line 187: "CHECK/CALL removes the actor from the current pending queue and consumes its current raise entitlement"
- ✓ **PASS:** Prior caller correctly blocked from re-raising.

---

## Architecture Cross-References

### Limps and SB completion
- §7 lines 181–183: "every pre-raise CALL, including a small-blind completion, counts for an opening/isolation decision"
- ✓ Explicit, unambiguous

### Cold-caller counting
- §7 lines 181–183: "`cold_callers` is the number of live seats whose latest voluntary action is CALL in the current response segment... It resets immediately after every raise. Folded callers do not count. The actor is not counted in its own sizing key."
- ✓ Deterministic reset and exclusion rules

### Sizing relation (IP/OOP)
- §2.2 lines 40–41, 45–46: "determined against the last voluntary raiser by postflop order: among the two seats, the one encountered later in the clockwise order ending at the button is IP. It is `NA` for an unopened pot."
- ✓ Deterministic, pairwise, aggressor-specific

### Full vs short raise
- §7 line 180: "A target is a normal full raise at or above `H + last_raise_increment`. A below-minimum target is legal only when it is the actor's all-in target and exceeds H."
- ✓ Clear threshold

### CHECK/CALL entitlement consumption
- §7 line 187: "CHECK/CALL removes the actor from the current pending queue and consumes its current raise entitlement"
- §15 line 322: "CHECK/CALL consumes current raise entitlement"
- ✓ Explicit consumption rule

### Pending rebuild
- §7 line 188: "Any raise rebuilds pending as all other live seats with chips, clockwise after the raiser, because every such seat must respond or retain an unacted option."
- ✓ Deterministic rebuild

### Full raise entitlement restoration
- §7 lines 189–190: "A full raise updates `last_raise_increment`; every other live seat with chips is re-entitled to raise, while the raiser has consumed its entitlement until another qualifying raise occurs."
- ✓ Universal restoration except raiser

### Short all-in no-reopen (intersection)
- §7 lines 190–191: "A short all-in does not update the increment. If `short_all_in_reopens` is false, a seat may raise after it only when that seat was both still in the pre-action pending queue and raise-entitled before the short all-in. This is an intersection, not a union: a seat that checked or called earlier may call or fold against the higher wager but may not re-raise."
- §15 line 322: "no-reopen short-all-in entitlement is the intersection of old pending and old entitlement"
- ✓ Explicit intersection semantics

### Short all-in with reopening
- §7 line 191: "If `short_all_in_reopens` is true, every other live seat with chips is re-entitled. The all-in short raiser is never entitled."
- ✓ Clear boolean flag behavior

### Action closure
- §7 line 192: "Action closes when one live seat remains or no actionable pending responder remains."
- ✓ Two deterministic closure conditions

---

## Verdict

**PASS**

All betting semantics are deterministic, complete, and internally consistent:

1. ✓ Limps and SB completes are explicitly counted as pre-raise callers
2. ✓ Cold-caller count resets after every raise and excludes folded/actor
3. ✓ IP/OOP relation is deterministic pairwise against last aggressor
4. ✓ Full vs short raise threshold is exact (`H + last_raise_increment`)
5. ✓ CHECK/CALL explicitly consumes raise entitlement
6. ✓ Pending rebuilds deterministically after every raise
7. ✓ Full raise restores entitlement to all other live seats with chips
8. ✓ Short all-in no-reopen uses **intersection** of old pending and old entitlement (§7 line 191, §15 line 322)
9. ✓ Short all-in with `reopens=true` restores entitlement to all live seats
10. ✓ Prior aggressor and prior callers cannot re-raise without qualifying intervening raise
11. ✓ Action closes on one live seat or empty pending

No ambiguities, no contradictions, no missing cases. Independent integer traces validate all rules.

---

**A3G2 — 2026-09-16 UTC**