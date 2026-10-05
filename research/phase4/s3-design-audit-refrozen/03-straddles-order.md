# S3 refrozen design audit — straddles and operational action order

**Auditor:** A3M3 (corrective re-audit after A3K3 button-relative arithmetic error)  
**Candidate:** `/home/genomix-node/poker-solver/ARCHITECTURE_PHASE4_S3.md`  
**Pre-audit SHA-256:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`  
**Post-audit SHA-256:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`  
**Audit date:** 2026-09-16  
**Scope:** Straddle variants (none/standard/double/Mississippi), operational UTG/UTG+1 aliases, exact untruncated posts, strict increase, all-in-post exclusion from pending, first actionable actor, last option, position derivation for N=2/3/4/5/6/7/8/9.

---

## 1. Straddle variant definitions and validation

### 1.1 None

**Architecture §5:**
- No straddle; first action is BTN/SB for HU when actionable, otherwise the next actionable seat clockwise after BB for N≥3.

**Attack:** Does the architecture define "actionable" and exclude all-in-post seats?

**Finding:** §4 states: "After a deal, `pending` contains every non-folded seat with positive remaining chips, starting at the first actionable actor and ending at the last actionable option seat. Seats all-in from exact forced posts are excluded: they have no CHECK, CALL, FOLD, or raise decision and do not retain an option."

**Verdict:** PASS. All-in-post seats are explicitly excluded from `pending` and have no option.

### 1.2 Standard

**Architecture §5:**
- N≥3, exactly one straddle by UTG; first action is the next actionable seat clockwise after UTG; UTG retains the final option only when it has chips after posting.

**Attack:** What is UTG at N=3, N=4, N=5, N=6?

**Architecture §4 operational aliases:**
- "For every N≥3, `UTG` is the first non-blind seat clockwise after BB: it is BTN at N=3, CO at N=4, HJ at N=5, and the displayed UTG seat at N≥6."

**Derived mappings (button-relative formulas):**

For N≥3: SB = (button+1) % N, BB = (button+2) % N, operational UTG = (button+3) % N.

- N=3, button=0: SB=1, BB=2, UTG=(0+3)%3=0. Seats: 0=BTN, 1=SB, 2=BB. **UTG=BTN at N=3.** ✓
- N=4, button=1: SB=2, BB=3, UTG=(1+3)%4=0. Seats: 0=CO, 1=BTN, 2=SB, 3=BB. First non-blind after BB is seat 0 (CO). **UTG=CO at N=4.** ✓
- N=5, button=2: SB=3, BB=4, UTG=(2+3)%5=0. Seats: 0=HJ, 1=CO, 2=BTN, 3=SB, 4=BB. **UTG=HJ at N=5.** ✓
- N=6, button=3: SB=4, BB=5, UTG=(3+3)%6=0. Seats: 0=UTG, 1=HJ, 2=CO, 3=BTN, 4=SB, 5=BB. **UTG=UTG at N≥6.** ✓

**Attack:** Standard straddle at N=3 means BTN straddles. Is button straddle valid?

**Architecture §5 Mississippi:** "Button Mississippi is supported."

**Inference:** Button can straddle under Mississippi; standard at N=3 also places the straddle on BTN. No contradiction.

**Attack:** Does standard require N≥3?

**Architecture §5:** "N≥3, exactly one straddle by UTG."

**Verdict:** PASS. Standard is defined N≥3, UTG operational alias is consistent, button straddle is valid.

### 1.3 Double

**Architecture §5:**
- N≥4, exactly two ordered straddles by UTG then UTG+1, with the second amount strictly greater than the first; first action follows UTG+1 and skips all-in seats; action wraps through UTG and ends at UTG+1 only when those seats remain actionable.

**Attack:** What is UTG+1 at N=4, N=5, N=6, N=7?

**Architecture §4 operational aliases:**
- "For every N≥4, `UTG+1` is the next non-blind seat clockwise after that operational UTG: it is BTN at N=4, CO at N=5, HJ at N=6, MP at N=7, and the displayed UTG+1 seat at N≥8."

**Derived mappings (button-relative formulas):**

For N≥4: UTG+1 = (button+4) % N.

- N=4, button=1: UTG=0 (CO), UTG+1=(1+4)%4=1. Seats: 0=CO, 1=BTN, 2=SB, 3=BB. Next non-blind after CO is BTN. **UTG+1=BTN at N=4.** ✓
- N=5, button=2: UTG=0 (HJ), UTG+1=(2+4)%5=1. Seats: 0=HJ, 1=CO, 2=BTN, 3=SB, 4=BB. **UTG+1=CO at N=5.** ✓
- N=6, button=3: UTG=0 (UTG), UTG+1=(3+4)%6=1. Seats: 0=UTG, 1=HJ, 2=CO, 3=BTN, 4=SB, 5=BB. **UTG+1=HJ at N=6.** ✓
- N=7, button=4: UTG=0 (UTG), UTG+1=(4+4)%7=1. Seats: 0=UTG, 1=MP, 2=HJ, 3=CO, 4=BTN, 5=SB, 6=BB. **UTG+1=MP at N=7.** ✓
- N=8, button=5: UTG=0 (UTG), UTG+1=(5+4)%8=1. Seats: 0=UTG, 1=UTG+1, 2=MP, 3=HJ, 4=CO, 5=BTN, 6=SB, 7=BB. **UTG+1=UTG+1 at N≥8.** ✓

**Attack:** Is double valid at N=3?

**Architecture §5:** "N≥4, exactly two ordered straddles."

**Verdict:** PASS. Double requires N≥4, UTG+1 operational alias is consistent.

### 1.4 Mississippi

**Architecture §5:**
- N≥3, exactly one caller-selected non-blind straddler; first action follows that straddler and skips all-in seats; the straddler has the final option only when it has chips after posting. Button Mississippi is supported. SB/BB Mississippi and HU Mississippi are rejected because there is no non-blind HU seat under this contract.

**Attack:** Is HU Mississippi (N=2) valid?

**Architecture §5:** "HU Mississippi are rejected because there is no non-blind HU seat."

**Architecture §4 N=2:** "For N=2, the button is also SB and acts first preflop; the other seat is BB."

**Inference:** At N=2, both seats are blinds (BTN/SB and BB). No non-blind seat exists. Mississippi requires a non-blind straddler.

**Verdict:** PASS. HU Mississippi is correctly rejected.

**Attack:** Is button Mississippi valid at N≥3?

**Architecture §5:** "Button Mississippi is supported."

**Architecture §4 N=3:** "BTN, SB, BB." BTN is non-blind.

**Verdict:** PASS. Button is non-blind at N≥3 and can straddle under Mississippi.

---

## 2. Exact untruncated posts and strict increase

### 2.1 Exact posts

**Architecture §3:**
- "Every declared post is transferred in full; a post is never truncated to the remaining stack. A seat may start all-in only when its stack exactly equals its cumulative declared posts."

**Architecture §2.4 config validation:**
- "cumulative posts above a seat's stack" is rejected.

**Verdict:** PASS. The architecture requires config validation to reject cumulative posts exceeding a stack, ensuring no truncation occurs in valid configs.

### 2.2 Strict increase

**Architecture §5:**
- "Each amount is a positive integer strictly greater than the preceding live wager; equal or decreasing declarations are not straddles under this contract and fail validation."

**Architecture §2.4:**
- "unsupported straddle arrangements" are rejected.

**Attack:** Does the architecture define "preceding live wager"?

**Architecture §3:**
- "Antes do not increase `street_committed`; small blind, big blind, and straddle payments do. Thus antes contribute to the pot but never change the live wager or minimum raise."

**Inference:** Live wager is `street_committed`. Straddles must strictly increase the live wager. BB is the first live wager; first straddle must exceed BB; second straddle must exceed first straddle.

**Verdict:** PASS. Strict increase is defined and enforced by validation.

---

## 3. All-in-post exclusion from pending

**Architecture §4:**
- "After a deal, `pending` contains every non-folded seat with positive remaining chips, starting at the first actionable actor and ending at the last actionable option seat. Seats all-in from exact forced posts are excluded: they have no CHECK, CALL, FOLD, or raise decision and do not retain an option."

**Architecture §3 root invariants:**
- "`can_raise[i]` is true exactly for seats with positive remaining chips before any voluntary action."

**Attack:** If a seat posts exactly its stack, does it have positive remaining chips?

**Architecture §3:** "A seat may start all-in only when its stack exactly equals its cumulative declared posts."

**Inference:** Such a seat has `remaining=0` after posts. It is not in `pending` because `pending` requires "positive remaining chips."

**Verdict:** PASS. All-in-post seats are excluded from `pending` and have no option.

---

## 4. First actionable actor

### 4.1 None (no straddle)

**Architecture §5:**
- "first action is BTN/SB for HU when actionable, otherwise the next actionable seat clockwise after BB for N≥3."

**Architecture §4 N=2:**
- "For N=2, the button is also SB and acts first preflop."

**Attack:** At N=2, if BTN/SB is all-in from posts, who acts first?

**Architecture §4:** "`pending` contains every non-folded seat with positive remaining chips."

**Inference:** If BTN/SB is all-in, `pending` contains only BB (if BB has chips). If BB also all-in, `pending` is empty and action closes immediately.

**Verdict:** PASS. First actor is the first seat in `pending`, which is derived from actionable seats.

### 4.2 Standard

**Architecture §5:**
- "first action is the next actionable seat clockwise after UTG."

**Attack:** At N=3, UTG=BTN. Next actionable seat clockwise after BTN is SB (if actionable), else BB.

**Verdict:** PASS. First action follows the straddler and skips all-in seats.

### 4.3 Double

**Architecture §5:**
- "first action follows UTG+1 and skips all-in seats."

**Attack:** At N=4, UTG+1=BTN. Next actionable seat clockwise after BTN is SB (if actionable), else BB, else CO (UTG), else BTN (UTG+1).

**Verdict:** PASS. First action follows the second straddler.

### 4.4 Mississippi

**Architecture §5:**
- "first action follows that straddler and skips all-in seats."

**Verdict:** PASS. First action is consistent across all variants.

---

## 5. Last option

**Architecture §5:**
- Standard: "UTG retains the final option only when it has chips after posting."
- Double: "action wraps through UTG and ends at UTG+1 only when those seats remain actionable."
- Mississippi: "the straddler has the final option only when it has chips after posting."

**Architecture §4:**
- "`pending` contains every non-folded seat with positive remaining chips, starting at the first actionable actor and ending at the last actionable option seat."

**Attack:** If a straddler is all-in from posting, is it in `pending`?

**Architecture §4:** "Seats all-in from exact forced posts are excluded."

**Inference:** An all-in straddler is not in `pending` and has no option.

**Verdict:** PASS. Last option is conditional on the straddler having chips after posting.

---

## 6. Position derivation for N=2 through N=9

**Architecture §4 canonical labels:**
- 2: `BTN/SB, BB`
- 3: `BTN, SB, BB`
- 4: `CO, BTN, SB, BB`
- 5: `HJ, CO, BTN, SB, BB`
- 6: `UTG, HJ, CO, BTN, SB, BB`
- 7: `UTG, MP, HJ, CO, BTN, SB, BB`
- 8: `UTG, UTG+1, MP, HJ, CO, BTN, SB, BB`
- 9: `UTG, UTG+1, MP, LJ, HJ, CO, BTN, SB, BB`

**Architecture §4:**
- "For N>=3, SB is `(button + 1) % N`, BB is `(button + 2) % N`."

**Button-relative formulas:**
- N≥3: SB = (button+1) % N, BB = (button+2) % N
- N≥3: operational UTG = (button+3) % N
- N≥4: operational UTG+1 = (button+4) % N

**Verification examples:**

N=2, button=0:
- SB=0 (BTN/SB), BB=1
- Seats: 0=BTN/SB, 1=BB. **HU special case.** ✓

N=3, button=0:
- SB=(0+1)%3=1, BB=(0+2)%3=2, UTG=(0+3)%3=0
- Seats: 0=BTN, 1=SB, 2=BB. **UTG=BTN.** ✓

N=4, button=1:
- SB=(1+1)%4=2, BB=(1+2)%4=3, UTG=(1+3)%4=0, UTG+1=(1+4)%4=1
- Seats: 0=CO, 1=BTN, 2=SB, 3=BB. **UTG=CO, UTG+1=BTN.** ✓

N=5, button=2:
- SB=(2+1)%5=3, BB=(2+2)%5=4, UTG=(2+3)%5=0, UTG+1=(2+4)%5=1
- Seats: 0=HJ, 1=CO, 2=BTN, 3=SB, 4=BB. **UTG=HJ, UTG+1=CO.** ✓

N=6, button=3:
- SB=(3+1)%6=4, BB=(3+2)%6=5, UTG=(3+3)%6=0, UTG+1=(3+4)%6=1
- Seats: 0=UTG, 1=HJ, 2=CO, 3=BTN, 4=SB, 5=BB. **UTG=UTG, UTG+1=HJ.** ✓

N=7, button=4:
- SB=(4+1)%7=5, BB=(4+2)%7=6, UTG=(4+3)%7=0, UTG+1=(4+4)%7=1
- Seats: 0=UTG, 1=MP, 2=HJ, 3=CO, 4=BTN, 5=SB, 6=BB. **UTG=UTG, UTG+1=MP.** ✓

N=8, button=5:
- SB=(5+1)%8=6, BB=(5+2)%8=7, UTG=(5+3)%8=0, UTG+1=(5+4)%8=1
- Seats: 0=UTG, 1=UTG+1, 2=MP, 3=HJ, 4=CO, 5=BTN, 6=SB, 7=BB. **UTG=UTG, UTG+1=UTG+1.** ✓

N=9, button=6:
- SB=(6+1)%9=7, BB=(6+2)%9=8, UTG=(6+3)%9=0, UTG+1=(6+4)%9=1
- Seats: 0=UTG, 1=UTG+1, 2=MP, 3=LJ, 4=HJ, 5=CO, 6=BTN, 7=SB, 8=BB. **UTG=UTG, UTG+1=UTG+1.** ✓

**Verdict:** PASS. Position derivation is consistent and deterministic for N=2 through N=9.

---

## 7. Operational aliases summary

| N | UTG (operational) | UTG+1 (operational) | Display label UTG | Display label UTG+1 |
|---|-------------------|---------------------|-------------------|---------------------|
| 2 | N/A               | N/A                 | N/A               | N/A                 |
| 3 | BTN               | N/A                 | N/A               | N/A                 |
| 4 | CO                | BTN                 | N/A               | N/A                 |
| 5 | HJ                | CO                  | N/A               | N/A                 |
| 6 | UTG               | HJ                  | UTG               | N/A                 |
| 7 | UTG               | MP                  | UTG               | N/A                 |
| 8 | UTG               | UTG+1               | UTG               | UTG+1               |
| 9 | UTG               | UTG+1               | UTG               | UTG+1               |

**Architecture §4:**
- "Operational straddle aliases are derived independently of those display labels."

**Verdict:** PASS. Operational aliases are explicit, consistent, and independent of display labels.

---

## 8. Straddle variant validity matrix

| Variant     | N=2 | N=3 | N=4 | N=5 | N=6 | N=7 | N=8 | N=9 |
|-------------|-----|-----|-----|-----|-----|-----|-----|-----|
| None        | ✓   | ✓   | ✓   | ✓   | ✓   | ✓   | ✓   | ✓   |
| Standard    | ✗   | ✓   | ✓   | ✓   | ✓   | ✓   | ✓   | ✓   |
| Double      | ✗   | ✗   | ✓   | ✓   | ✓   | ✓   | ✓   | ✓   |
| Mississippi | ✗   | ✓   | ✓   | ✓   | ✓   | ✓   | ✓   | ✓   |

**Architecture §5:**
- Standard: N≥3
- Double: N≥4
- Mississippi: N≥3, non-blind straddler

**Verdict:** PASS. Validity matrix matches architecture.

---

## 9. Final verdict

**PASS.** The refrozen S3 architecture defines straddle variants, operational UTG/UTG+1 aliases, exact untruncated posts, strict increase, all-in-post exclusion from pending, first actionable actor, and last option consistently and without contradiction for N=2 through N=9. Position derivation is deterministic and explicit using button-relative formulas: N≥3 SB=(b+1)%N, BB=(b+2)%N, operational UTG=(b+3)%N; N≥4 UTG+1=(b+4)%N. Standard is valid at N≥3 (including N=3 where UTG=BTN). Double is valid at N≥4 (where UTG+1 first exists). Mississippi is valid at N≥3 for non-blind straddlers, including button Mississippi, and correctly rejects HU Mississippi. All-in-post seats are excluded from `pending` and have no option. Config validation ensures no post truncation in valid configs.

---

**Audit complete.**  
**Output:** `/home/genomix-node/poker-solver/research/phase4/s3-design-audit-refrozen/03-straddles-order.md`  
**Heartbeat:** `/home/genomix-node/poker-solver/research/phase4/s3-design-audit-refrozen/.hb/A3M3`