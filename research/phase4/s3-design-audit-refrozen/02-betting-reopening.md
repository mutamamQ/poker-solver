# S3 refrozen design audit — betting and reopening

**Auditor:** parent-corrected candidate for A3P2 verification  
**Candidate:** `/home/genomix-node/poker-solver/ARCHITECTURE_PHASE4_S3.md`  
**Pre-audit SHA-256:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`  
**Scope:** Betting semantics, reopening, sizing keys, raise-to targets, limps, SB completion, cold callers, IP/OOP relation, 3/4/5-bet+, pending rebuild, entitlement consumption, full/short all-in reopening, closure, and mandatory no-reopen trace.

---

## 1. Betting semantics (section 7)

The architecture defines action amounts as **absolute preflop street commitments**. For actor `p`:

- `H = max(street_committed)`  
- `own = street_committed[p]`  
- `to_call = H - own`

When `to_call > 0`, legal actions begin with FOLD and `CALL(min(H, own + remaining[p]))`. When `to_call == 0`, CHECK is legal; folding while checking is not exposed.

**Trace 1: Basic call semantics (4-seat, no straddle)**  
Config: 4 seats (CO, BTN, SB, BB), stacks `[100, 100, 50, 100]`, posts `[(SB, 1), (BB, 2)]`, no straddle.  
Root after posts: `street_committed = [0, 0, 1, 2]`, `pot = 3`, first actor CO.

- CO: `H=2, own=0, to_call=2`. Legal: FOLD, CALL(2), RAISE candidates.  
- CO calls 2 → `street_committed = [2, 0, 1, 2]`, `pot=5`, next BTN.  
- BTN: `H=2, own=0, to_call=2`. Legal: FOLD, CALL(2), RAISE candidates.  
- BTN calls 2 → `street_committed = [2, 2, 1, 2]`, `pot=7`, next SB.  
- SB: `H=2, own=1, to_call=1`. Legal: FOLD, CALL(2), RAISE candidates.  
- SB calls 1 → `street_committed = [2, 2, 2, 2]`, `pot=8`, next BB.  
- BB: `H=2, own=2, to_call=0`. Legal: CHECK, RAISE candidates.

**Verdict:** Absolute commitment semantics are consistent. ✓

---

## 2. Sizing keys and cold callers (section 7)

The sizing key is `(position, raise_count, cold_callers, relation)`. `cold_callers` counts live seats whose latest voluntary action is CALL in the current response segment:

- Pre-raise CALLs (including SB completion) count for opening/isolation decisions.  
- After a raise, callers of that wager count for squeeze/re-raise decisions.  
- Resets immediately after every raise.  
- Folded callers do not count.  
- The actor is not counted in its own key.

**Trace 2: SB completion counts as pre-raise caller (6-seat)**  
Config: 6 seats (UTG, HJ, CO, BTN, SB, BB), stacks all 100, posts `[(SB, 1), (BB, 2)]`, no straddle.  
Root: `street_committed = [0,0,0,0,1,2]`, first actor UTG.

- UTG calls 2 → 1 pre-raise caller.  
- HJ calls 2 → 2 pre-raise callers.  
- CO folds.  
- BTN folds.  
- SB calls 1 (completion) → 3 pre-raise callers (UTG, HJ, SB).  
- BB acts: `raise_count=0`, `cold_callers=3` (UTG, HJ, SB; BB is actor, not counted).  
  Sizing key: `(position=BB, raise_count=0, cold_callers=3, relation=NA)`.

**Verdict:** SB completion correctly counts as a pre-raise caller. ✓

**Trace 3: Cold caller reset after raise (4-seat)**  
Config: 4 seats, stacks all 100, posts `[(SB,1),(BB,2)]`.  
Root: first actor CO.

- CO calls 2 → 1 pre-raise caller.  
- BTN raises to 10 → `raise_count=1`, cold callers reset.  
- SB folds.  
- BB calls 10 → 1 post-raise caller (BB).  
- CO acts: `raise_count=1`, `cold_callers=1` (BB called the 10; CO is actor, not counted).  
  Sizing key: `(position=CO, raise_count=1, cold_callers=1, relation=OOP)` (CO is OOP to BTN).

**Verdict:** Cold caller reset after raise is correct. ✓

---

## 3. IP/OOP relation (section 2.2)

`relation` is determined against the last voluntary raiser by postflop order: among the two seats, the one encountered later in clockwise order ending at the button is IP. It is `NA` for an unopened pot.

**Trace 4: IP/OOP relation (6-seat)**  
Config: 6 seats (UTG, HJ, CO, BTN, SB, BB), button seat 3 (BTN).  
Postflop clockwise order: SB, BB, UTG, HJ, CO, BTN.

- UTG raises to 6 → last aggressor UTG.  
- HJ acts: HJ is later than UTG in postflop order → HJ is IP to UTG.  
  Sizing key: `(position=HJ, raise_count=1, cold_callers=0, relation=IP)`.  
- SB acts: SB is earlier than UTG in postflop order → SB is OOP to UTG.  
  Sizing key: `(position=SB, raise_count=1, cold_callers=0, relation=OOP)`.

**Verdict:** IP/OOP relation is correctly derived from postflop order. ✓

---

## 4. Raise-to targets and full/short all-in (section 7)

A raise requires `can_raise[p]`, chips beyond the call, and `raise_count < max_raises`. A target is a **normal full raise** at or above `H + last_raise_increment`. A **below-minimum target** is legal only when it is the actor's all-in target and exceeds H. Every raise, including a short all-in, increments `raise_count`.

**Trace 5: Full raise updates increment (4-seat)**  
Config: 4 seats, stacks all 100, posts `[(SB,1),(BB,2)]`, `max_raises=4`.  
Root: `last_raise_increment=2` (BB amount).

- CO raises to 10 → `raise_size = 10 - 2 = 8 >= 2` → full raise.  
  New `last_raise_increment = 8`.  
  `raise_count = 1`.  
- BTN acts: minimum raise-to = `10 + 8 = 18`.

**Verdict:** Full raise updates increment. ✓

**Trace 6: Short all-in does not update increment (4-seat)**  
Config: 4 seats, stacks `[100, 100, 50, 15]`, posts `[(SB,1),(BB,2)]`.  
Root: `last_raise_increment=2`.

- CO raises to 10 → full raise, `last_raise_increment=8`, `raise_count=1`.  
- BTN folds.  
- SB folds.  
- BB all-in raises to 15 → `raise_size = 15 - 10 = 5 < 8` → short all-in.  
  `last_raise_increment` remains 8 (not updated).  
  `raise_count = 2`.  
- CO acts: minimum raise-to = `15 + 8 = 23` (if CO had entitlement and chips).

**Verdict:** Short all-in does not update increment. ✓

---

## 5. Pending rebuild and entitlement consumption (section 7)

- **FOLD** marks the actor folded and unable to raise.  
- **CHECK/CALL** removes the actor from pending and consumes current raise entitlement; an all-in caller becomes non-actionable.  
- Any **raise** rebuilds pending as all other live seats with chips, clockwise after the raiser.  
- A **full raise** re-entitles every other live seat with chips; the raiser consumes its entitlement.  
- A **short all-in** does not re-entitle unless `short_all_in_reopens=true`.

**Trace 7: CHECK/CALL consumes entitlement (4-seat)**  
Config: 4 seats, stacks all 100, posts `[(SB,1),(BB,2)]`.  
Root: `can_raise = [true, true, true, true]` (all seats have chips after posts).

- CO calls 2 → `can_raise[CO] = false` (consumed).  
- BTN raises to 10 → full raise, `can_raise = [true, false, true, true]` (all except BTN re-entitled; CO was already false but is now true again; BTN consumed).  
- SB calls 10 → `can_raise[SB] = false`.  
- BB calls 10 → `can_raise[BB] = false`.  
- CO acts: `can_raise[CO] = true` (re-entitled by BTN's full raise).

**Verdict:** Entitlement consumption and re-entitlement are correct. ✓

---

## 6. Short all-in reopening: no-reopen intersection (section 7)

If `short_all_in_reopens=false`, a seat may raise after a short all-in only when that seat was **both** still in the pre-action pending queue **and** raise-entitled before the short all-in. This is an **intersection**, not a union: a seat that checked or called earlier may call or fold against the higher wager but may not re-raise.

**Trace 8: Mandatory no-reopen trace (4-seat, BB stack exactly 35)**  
Config: 4 seats (SB, BB, CO, BTN), stacks `[500, 35, 500, 500]`, posts `[(SB,5),(BB,10)]`, `short_all_in_reopens=false`, `max_raises=4`.  
Root: `street_committed = [5, 10, 0, 0]`, `pot=15`, `last_raise_increment=10`, `can_raise=[true,true,true,true]`, `pending=[CO,BTN,SB,BB]`, first actor CO.

**Step 1: CO raises to 30**  
- `H=10`, CO raises to 30 → `raise_size = 30 - 10 = 20 >= 10` → full raise.  
- New `last_raise_increment = 20`.  
- `raise_count = 1`.  
- In absolute `(SB=0, BB=1, CO=2, BTN=3)` seat order, `can_raise = [true, true, false, true]` (CO consumed, all other live seats re-entitled).  
- `pending = [BTN, SB, BB]` (all live seats with chips after CO, clockwise).  
- Next actor: BTN.

**Step 2: BTN calls 30**  
- BTN calls 30 → `can_raise[BTN] = false`, removed from pending.  
- `pending = [SB, BB]`.  
- Next actor: SB.

**Step 3: SB calls 30**  
- SB calls 30 → `can_raise[SB] = false`, removed from pending.  
- `pending = [BB]`.  
- Next actor: BB.

**Step 4: BB all-in raises to 35**  
- `H=30`, BB has `remaining=25` (started 35, posted 10).  
- BB all-in target = `10 + 25 = 35`.  
- Minimum full raise-to = `30 + 20 = 50`.  
- `35 < 50` → short all-in.  
- `35 > 30` → legal (exceeds H).  
- `raise_size = 35 - 30 = 5 < 20` → does not update increment.  
- `raise_count = 2`.  
- **Reopening logic (`short_all_in_reopens=false`):**  
  - Old pending before BB's action: `[BB]`.  
  - Old entitlement before BB's action in absolute `(SB, BB, CO, BTN)` order: `can_raise = [false, true, false, false]` (only BB, seat 1, was entitled).  
  - Intersection: seats in old pending AND old entitled = `{BB}`.  
  - BB is now all-in (no chips), so BB is not actionable.  
  - **Architecture line 190 requires:** Any raise rebuilds pending as all other live seats with chips, clockwise after the raiser, because every such seat must respond or retain an unacted option.  
  - New pending: `[CO, BTN, SB]` (all live seats with chips after BB, clockwise).  
  - **Architecture line 192 restricts raise entitlement:** Intersection = `{BB}`, BB is all-in → no seat may re-raise.  
  - New `can_raise = [false, false, false, false]` in absolute `(SB, BB, CO, BTN)` order.  
  - CO, BTN, SB are in pending (must respond) but not in intersection (may not raise).

**Step 5: Responders act**  
- CO: in pending (must respond), not in intersection → may CALL or FOLD, but **not RAISE**.  
- BTN: in pending (must respond), not in intersection → may CALL or FOLD, but **not RAISE**.  
- SB: in pending (must respond), not in intersection → may CALL or FOLD, but **not RAISE**.

**Step 6: All call, action closes**  
- CO calls 35, BTN calls 35, SB calls 35.  
- `pending = []`, action closes.  
- `street_committed = [35, 35, 35, 35]`, `pot = 140`.

**Legality proof:**  
- `H = 30` (before BB's raise).  
- `last_raise_increment = 20` (from CO's raise).  
- Minimum full raise-to = `30 + 20 = 50`.  
- BB's all-in target = 35.  
- `35 < 50` → below minimum.  
- `35 > 30` → exceeds H.  
- BB is all-in → legal short all-in.

**Intersection semantics:**  
- Old pending: `[BB]`.  
- Old entitlement in absolute `(SB, BB, CO, BTN)` order: `can_raise = [false, true, false, false]`.  
- Intersection: `{BB}`.  
- BB is all-in → not actionable.  
- **Architecture line 190:** Any raise rebuilds pending as all other live seats with chips → new pending = `[CO, BTN, SB]`.  
- **Architecture line 192:** Raise entitlement restricted to intersection minus all-in raiser → CO, BTN, SB are not in intersection → **may not re-raise**.  
- **Pending vs. entitlement distinction:** CO, BTN, SB are pending responders (must act) but not raise-entitled (may only CALL/FOLD).

**Verdict:** Mandatory no-reopen trace is legal and correctly applies intersection semantics. Architecture line 190 requires pending rebuild to all live seats with chips (CO, BTN, SB must respond); line 192 restricts raise entitlement to intersection (none may raise). ✓

---

## 7. Short all-in reopening: reopen=true (4-seat)

**Trace 9: Short all-in with `short_all_in_reopens=true`**  
Same config as Trace 8, but `short_all_in_reopens=true`.

After BB's short all-in to 35:
- `short_all_in_reopens=true` → every other live seat with chips is re-entitled.  
- In absolute `(SB, BB, CO, BTN)` seat order, `can_raise = [true, false, true, true]` (SB, CO, BTN re-entitled; BB all-in, not entitled).  
- `pending = [CO, BTN, SB]` (all live seats with chips, clockwise after BB).  
- CO, BTN, SB may now RAISE (if `raise_count < max_raises`).

**Verdict:** Reopen=true correctly re-entitles all live seats with chips. ✓

---

## 8. 3-bet/4-bet/5-bet+ raise counts (6-seat)

**Trace 10: Raise count progression**  
Config: 6 seats, stacks all 200, posts `[(SB,1),(BB,2)]`, `max_raises=5`.  
Root: `raise_count=0`.

- UTG raises to 6 → `raise_count=1` (open, counts as first raise).  
  Sizing key for next raiser: `raise_count=1` (3-bet decision).  
- HJ raises to 20 → `raise_count=2` (3-bet).  
  Sizing key for next raiser: `raise_count=2` (4-bet decision).  
- CO raises to 60 → `raise_count=3` (4-bet).  
  Sizing key for next raiser: `raise_count=3` (5-bet decision).  
- BTN raises to 150 → `raise_count=4` (5-bet).  
  Sizing key for next raiser: `raise_count=4` (6-bet decision, if allowed).  
- SB raises to 200 (all-in) → `raise_count=5` (6-bet, at `max_raises`).  
- No further raises allowed (`raise_count >= max_raises`).

**Verdict:** Raise count progression through 3/4/5-bet+ is correct. ✓

---

## 9. Closure (section 7)

Action closes when one live seat remains or no actionable pending responder remains.

**Trace 11: Closure by fold-out (4-seat)**  
Config: 4 seats, stacks all 100, posts `[(SB,1),(BB,2)]`.

- CO raises to 10.  
- BTN folds.  
- SB folds.  
- BB folds.  
- One live seat remains (CO) → action closes, CO wins pot.

**Verdict:** Closure by fold-out is correct. ✓

**Trace 12: Closure by empty pending (4-seat)**  
Config: 4 seats, stacks all 100, posts `[(SB,1),(BB,2)]`.

- CO calls 2.  
- BTN calls 2.  
- SB calls 1.  
- BB checks.  
- `pending = []` (all seats have acted, no pending responders) → action closes.

**Verdict:** Closure by empty pending is correct. ✓

---

## 10. Below-minimum non-all-in rejection

**Trace 13: Below-minimum non-all-in is illegal (4-seat)**  
Config: 4 seats, stacks all 100, posts `[(SB,1),(BB,2)]`.  
Root: `last_raise_increment=2`.

- CO raises to 10 → `last_raise_increment=8`.  
- BTN attempts to raise to 15 (not all-in, has 100 chips).  
  - Minimum raise-to = `10 + 8 = 18`.  
  - `15 < 18` and BTN is not all-in → **illegal**.

**Verdict:** Below-minimum non-all-in raises are correctly rejected. ✓

---

## 11. Limps (section 7)

A limp is a CALL to the big blind when `raise_count=0`. Limpers count as `cold_callers` for subsequent opening/isolation decisions.

**Trace 14: Limps count as cold callers (6-seat)**  
Config: 6 seats, stacks all 100, posts `[(SB,1),(BB,2)]`.

- UTG calls 2 (limp) → 1 cold caller.  
- HJ calls 2 (limp) → 2 cold callers.  
- CO raises to 10 → `raise_count=1`, sizing key at decision: `(position=CO, raise_count=0, cold_callers=2, relation=NA)`.

**Verdict:** Limps correctly count as cold callers. ✓

---

## 12. Post-audit hash

```bash
sha256sum ARCHITECTURE_PHASE4_S3.md
```
**Post-audit SHA-256:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`

---

## Summary

**PASS.** Zero blockers.

- Absolute commitment semantics: ✓  
- SB completion counts as pre-raise caller: ✓  
- Cold caller reset after raise: ✓  
- IP/OOP relation from postflop order: ✓  
- Full raise updates increment: ✓  
- Short all-in does not update increment: ✓  
- CHECK/CALL consumes entitlement: ✓  
- Pending rebuild after raise: ✓  
- No-reopen intersection semantics: ✓  
- Mandatory no-reopen trace (BB stack 35, CO raises 30, BB all-in 35, pending rebuilds to [CO,BTN,SB], no re-raise entitlement): ✓  
- Reopen=true re-entitles all live seats: ✓  
- Raise count progression (3/4/5-bet+): ✓  
- Closure by fold-out and empty pending: ✓  
- Below-minimum non-all-in rejection: ✓  
- Limps count as cold callers: ✓  

All independent traces are legal, deterministic, and consistent with the architecture. Pre/post hash match. No contradictions. Architecture line 190 requires pending rebuild to all live seats with chips after any raise (responders must act); line 192 restricts raise entitlement via intersection (responders may only CALL/FOLD when not in intersection).
