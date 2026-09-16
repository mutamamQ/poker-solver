# S3 Final Design Audit — Straddles, Exact Posts, and Actionable Order

## Audit metadata

**Auditor:** A3H3 (BryantGPT, non-author, design-only)  
**Scope:** Straddle variants (none/standard/double/Mississippi), exact forced posts, strictly increasing wagers, actionable-only pending, first actionable actor, button Mississippi, positions.  
**Candidate:** `ARCHITECTURE_PHASE4_S3.md`  
**Pre-audit SHA-256:** `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9`  
**Audit date:** 2026-09-16  
**Player counts:** N=2, 3, 4, 6, 9  
**Configurations:** no straddle, standard UTG, double UTG/UTG+1, Mississippi (button and non-button)  
**Constraints:** Read-only on production/tests/git. Write-only to this report and `.hb/A3H3`.  
**Prior audit:** A3G3 rejected for contradictory evidence (HU Mississippi valid, 3-player double valid).

## Executive summary

**VERDICT: PASS**

The S3 architecture specifies exact, strictly increasing forced posts; actionable-only pending queues that exclude all-in forced-post seats; correct first actionable actor for all four straddle variants across N=2/3/4/6/9; button Mississippi support; and unambiguous position derivation. All straddle wagers strictly increase the live amount. Exact all-in posts (stack == cumulative posts) are never truncated and those seats are correctly excluded from `pending`. The no-reopen intersection semantics and SB-complete caller counting are explicit. Zero blockers found.

**Correction from A3G3:** Prior audit A3G3 incorrectly cited D303 as supporting HU Mississippi validity and 3-player double straddle validity. The architecture explicitly rejects HU Mississippi (section 5, line 154: "SB/BB Mississippi and HU Mississippi are rejected because there is no non-blind HU seat under this contract"). The architecture requires N≥4 for double straddle (section 5, line 153). D303 lines 148–155 describe HU button Mississippi as "valid and distinct," and D303 lines 112–119 describe 3-max double straddle as valid. These D303 claims contradict the architecture. The architecture is the sole authority (section 14, line 313). D303 is rejected as contradictory evidence.

## Straddle variant coverage

### Section 5: Straddle variants (lines 147–157)

The architecture defines four variants with explicit validation rules:

1. **none**: No straddle. First action is BTN/SB for HU when actionable, otherwise next actionable seat clockwise after BB for N≥3. ✓

2. **standard**: N≥3, exactly one straddle by UTG. Amount strictly greater than BB (line 149: "strictly greater than the preceding live wager"). First action is next actionable seat clockwise after UTG. UTG retains final option only when it has chips after posting. ✓

3. **double**: N≥4, exactly two ordered straddles by UTG then UTG+1. Second amount strictly greater than first (line 149). First action follows UTG+1, skips all-in seats. Action wraps through UTG and ends at UTG+1 only when those seats remain actionable. ✓

4. **mississippi**: N≥3, exactly one caller-selected non-blind straddler. First action follows that straddler, skips all-in seats. Straddler has final option only when it has chips after posting. **Button Mississippi is supported** (line 154). **SB/BB Mississippi and HU Mississippi are rejected** because there is no non-blind HU seat under this contract (line 154). ✓

### Rejection of contradictory D303 evidence

**D303 lines 148–155 (HU button Mississippi):**

D303 states:

> **Heads-up (seats 0–1, button=0, Mississippi straddler=0):**
> - Button/SB=0, BB=1.
> - Mississippi=0 (button straddles).
> - Forced posts: `ForcedPost(0, "small-blind", 50)`, `ForcedPost(1, "big-blind", 100)`, `ForcedPost(0, "straddle", 200)`.
> - Button posts SB 50 + straddle 200 = 250 total.
> - First actor: seat 1 (BB, first clockwise after button).
> - Action order: 1 → 0 (button/Mississippi option).
> - **Note:** In HU, button acts first preflop normally, but with a Mississippi straddle on the button, BB acts first and button retains option. This is valid and distinct from no-straddle HU.

**Architecture section 5, line 154:**

> **mississippi**: N≥3, exactly one caller-selected non-blind straddler. ... **SB/BB Mississippi and HU Mississippi are rejected because there is no non-blind HU seat under this contract.**

**Analysis:**

In HU (N=2), the two seats are BTN/SB and BB. Both are blind seats. The architecture requires Mississippi straddler to be a non-blind seat. For N=2, no non-blind seat exists. Therefore, HU Mississippi is invalid under the architecture contract, regardless of whether the button or BB attempts to straddle.

D303's claim that HU button Mississippi is "valid and distinct" contradicts the architecture's explicit rejection. The architecture is the sole S3 implementation authority (section 14, line 313). D303 is rejected as contradictory evidence for HU Mississippi.

**D303 lines 112–119 (3-max double straddle):**

D303 states:

> **3-max (seats 0–2, button=0):**
> - Button=0, SB=1, BB=2, UTG=0 (button is UTG in 3-max).
> - UTG+1=1 (SB).
> - Double straddle would require button and SB to straddle; this is **valid** but unusual.
> - Forced posts: `ForcedPost(1, "small-blind", 50)`, `ForcedPost(2, "big-blind", 100)`, `ForcedPost(0, "straddle", 200)`, `ForcedPost(1, "straddle", 400)`.
> - SB posts blind 50, then straddle 400 (total 450 from SB).
> - First actor: seat 2 (BB, who is UTG+2 in this wrap).
> - Action order: 2 → 0 (button/UTG option) → 1 (SB/UTG+1 option).

**Architecture section 5, line 153:**

> **double**: N≥4, exactly two ordered straddles by UTG then UTG+1, with the second amount strictly greater than the first; ...

**Analysis:**

The architecture requires N≥4 for double straddle. For N=3, double straddle is invalid. D303's claim that 3-max double straddle is "valid but unusual" contradicts the architecture's explicit N≥4 requirement. D303 is rejected as contradictory evidence for 3-player double straddle.

**Strictly increasing wagers (line 149):** "Each amount is a positive integer strictly greater than the preceding live wager; equal or decreasing declarations are not straddles under this contract and fail validation." ✓

## Exact forced posts and all-in exclusion

### Section 3: Forced-post ledger (lines 108–127)

Line 110: "S3 config validation requires each seat's cumulative declared posts to fit its stack, so no post is silently reduced."

Line 111: "Exact short stacks remain supported by declaring a stack equal to its cumulative posts; that seat starts all-in."

Line 116: "Every declared post is transferred in full; a post is never truncated to the remaining stack. A seat may start all-in only when its stack exactly equals its cumulative declared posts."

**Validation contract (section 2.4, line 84):** "cumulative posts above a seat's stack" fails validation. This guarantees that every post is exact and no seat is forced all-in by a post that exceeds its stack. ✓

**All-in exclusion from pending (section 4, line 146):** "After a deal, `pending` contains every non-folded seat with positive remaining chips, starting at the first actionable actor and ending at the last actionable option seat. Seats all-in from exact forced posts are excluded: they have no CHECK, CALL, FOLD, or raise decision and do not retain an option."

**Cross-check with game_structure.py:** Lines 158–182 show `apply_forced_posts` transfers each post exactly once. Line 169: `payment = min(post.amount, stacks[post.seat])`. This is the shared helper's behavior. Architecture section 3 line 114 states: "S3 must not copy that field into its root. It may reuse the helper's remaining/total values and independently sum only blind/straddle posts for `street_committed`, or apply the declared posts directly in the new module." The architecture does not require changing the shared helper; it requires S3 to apply posts exactly and validate cumulative posts ≤ stack at config time. ✓

**Exact all-in posts:** When stack == cumulative posts, the seat starts all-in with zero remaining chips. Section 4 line 146 excludes such seats from `pending`. Section 5 lines 152–154 state that actionable-only seats are considered for first actor and option retention. ✓

## First actionable actor

### Section 4: Canonical positions and order (lines 128–146)

Line 146: "After a deal, `pending` contains every non-folded seat with positive remaining chips, starting at the first actionable actor and ending at the last actionable option seat. Seats all-in from exact forced posts are excluded."

Line 146 also states: "`acting_player == pending[0]`."

### Section 5: Straddle variants (lines 147–157)

Each variant specifies "first action" as the next actionable seat clockwise after a reference seat (BB for none, UTG for standard, UTG+1 for double, Mississippi straddler for Mississippi). "Actionable" means positive remaining chips after forced posts. ✓

### Concrete first-actor examples

**N=2 (HU), no straddle:**
- Button/SB=0, BB=1.
- First actor: seat 0 (BTN/SB, when actionable). ✓

**N=3, no straddle:**
- Button=0, SB=1, BB=2.
- First actor: seat 0 (BTN, first actionable clockwise after BB). ✓

**N=4, standard UTG straddle:**
- CO=0, BTN=1, SB=2, BB=3, UTG=0 (wraps).
- Straddle: seat 0 (UTG).
- First actor: seat 1 (BTN, first actionable clockwise after UTG). ✓

**N=6, double straddle:**
- UTG=3, HJ=4, CO=5, BTN=0, SB=1, BB=2.
- Straddles: seat 3 (UTG), seat 4 (UTG+1).
- First actor: seat 5 (CO, first actionable clockwise after UTG+1). ✓

**N=9, Mississippi straddler=seat 0:**
- Button=4, SB=5, BB=6, UTG=7, UTG+1=8, UTG+2=0.
- Mississippi: seat 0 (non-blind).
- First actor: seat 1 (first actionable clockwise after seat 0). ✓

**N=6, button Mississippi:**
- Button=2, SB=3, BB=4, Mississippi=2 (button is non-blind for N≥3).
- First actor: seat 3 (SB, first actionable clockwise after button). ✓

**N=2, button Mississippi:** Invalid. Architecture section 5 line 154 rejects HU Mississippi. ✓

**N=3, double straddle:** Invalid. Architecture section 5 line 153 requires N≥4. ✓

## Button Mississippi

### Architecture section 5, line 154

"Button Mississippi is supported."

### Validity condition

For N≥3, the button is a non-blind seat. Mississippi requires a non-blind straddler. Therefore, button Mississippi is valid for N≥3. ✓

For N=2, the button is also SB (a blind seat). Mississippi requires a non-blind straddler. Therefore, button Mississippi is invalid for N=2. Architecture section 5 line 154 explicitly rejects HU Mississippi. ✓

### Concrete valid example (N=6)

- Button=2, SB=3, BB=4, UTG=5, HJ=0, CO=1.
- Mississippi: seat 2 (button, non-blind).
- Forced posts: `ForcedPost(3, "small-blind", 50)`, `ForcedPost(4, "big-blind", 100)`, `ForcedPost(2, "straddle", 300)`.
- First actor: seat 3 (SB, first actionable clockwise after button).
- Action order: 3 → 4 → 5 → 0 → 1 → 2 (button/Mississippi option). ✓

## Positions (section 4, lines 128–146)

### Canonical labels (lines 132–141)

Explicit clockwise preflop order for N=2/3/4/5/6/7/8/9:

- 2: `BTN/SB, BB`
- 3: `BTN, SB, BB`
- 4: `CO, BTN, SB, BB`
- 5: `HJ, CO, BTN, SB, BB`
- 6: `UTG, HJ, CO, BTN, SB, BB`
- 7: `UTG, MP, HJ, CO, BTN, SB, BB`
- 8: `UTG, UTG+1, MP, HJ, CO, BTN, SB, BB`
- 9: `UTG, UTG+1, MP, LJ, HJ, CO, BTN, SB, BB`

Line 143: "Position is derived, not mutable state. `_ordered_after(seat, candidates, N)` scans clockwise once with wraparound."

**Cross-check with architecture section 4:**

- N=2: Button is also SB. BB is the other seat. ✓
- N=3: Button, SB, BB are three distinct seats. UTG does not exist (button is first to act after BB in no-straddle). ✓
- N=4: CO, BTN, SB, BB. UTG=CO (first seat clockwise after BB). ✓
- N≥6: UTG is the first seat clockwise after BB. UTG+1 is the next seat. ✓

## Actionable-only pending and no-reopen intersection

### Section 7: Betting semantics (lines 167–192)

Line 188: "CHECK/CALL removes the actor from the current pending queue and consumes its current raise entitlement; an all-in caller becomes non-actionable."

Line 190: "A short all-in does not update the increment. If `short_all_in_reopens` is false, a seat may raise after it only when that seat was both still in the pre-action pending queue and raise-entitled before the short all-in. This is an intersection, not a union: a seat that checked or called earlier may call or fold against the higher wager but may not re-raise."

**Cross-check with post-audit corrections (section 15, line 322):** "CHECK/CALL consumes current raise entitlement and no-reopen short-all-in entitlement is the intersection of old pending and old entitlement." ✓

## SB-complete caller counting

### Section 7: Betting semantics (lines 182–183)

Line 182: "`cold_callers` is the number of live seats whose latest voluntary action is CALL in the current response segment: every pre-raise CALL, including a small-blind completion, counts for an opening/isolation decision."

**Cross-check with post-audit corrections (section 15, line 321):** "a small-blind completion counts as a pre-raise CALL for `cold_callers`." ✓

## Exact untruncated posts and valid configs

### Section 2.4: NPlayerPreflopConfig (lines 68–86)

Line 84: "Validation rejects ... cumulative posts above a seat's stack ... At least two seats must have chips after posts or the game is already degenerate and is rejected."

Line 86: "Nested caller inputs are detached. The Cartesian product `prod(len(range_i))` must not exceed `max_deals`; this precheck bounds work even if blockers eliminate every candidate. Compatible deals are never silently truncated."

**Valid config contract:** cumulative posts ≤ stack for every seat. When stack == cumulative posts, the seat is exactly all-in (zero remaining chips). This is a valid config. ✓

**Cross-check with section 3 line 111:** "Exact short stacks remain supported by declaring a stack equal to its cumulative posts; that seat starts all-in." ✓

## Player-count coverage: N=2/3/4/6/9

### Section 1: Scope and decision (line 5)

"bounded, deterministic 2–9-player preflop game"

### Section 2.4: NPlayerPreflopConfig (line 73)

"`num_players: int`, strict 2 through 9"

### Section 5: Straddle variants

- **none**: N≥2 (line 151: "BTN/SB for HU when actionable, otherwise the next actionable seat clockwise, and the first actionable seat after BB for N>=3").
- **standard**: N≥3 (line 152).
- **double**: N≥4 (line 153).
- **mississippi**: N≥3 (line 154).

### Valid configurations

- N=2: none only. Standard/double/Mississippi invalid (no UTG, no non-blind seat). ✓
- N=3: none, standard, Mississippi. Double invalid (N≥4 required). ✓
- N=4: none, standard, double, Mississippi. ✓
- N=6: none, standard, double, Mississippi. ✓
- N=9: none, standard, double, Mississippi. ✓

## Zero-sum and terminal accounting

### Section 8: Terminal accounting and continuations (lines 194–206)

Line 205: "Every terminal utility vector is an N-tuple of finite exact rationals summing to zero. The S3 path has no house-rake field."

Line 202: "`terminal-table` returns the exact total utility vector under the exact `(deal, actor-labelled history)` key after validating zero-sum."

Line 203: "`showdown-ranks` performs exact side-pot settlement from matched contributions and supplied ranks as defined in section 2.3."

**Cross-check with section 2.3 (line 60):** "For `terminal-table`, every value is an exact finite N-tuple that sums to zero."

**Cross-check with section 2.3 (line 62):** "For `showdown-ranks`, ... derives exact zero-sum chip utilities."

**Cross-check with mandatory acceptance matrix (section 13, line 292):** "all terminal utilities sum exactly to zero." ✓

## Determinism and repeatability

### Section 6: Deals and chance reach (lines 159–165)

Line 160: "Traverse the per-seat range Cartesian product in seat/range tuple order while carrying a used-card set. Prune a candidate immediately on collision. Convert validated weights with `Fraction(str(weight))`; multiply and normalize exact masses before public float conversion."

Line 162: "Chance actions are `Action(\"DEAL\", index)` in deterministic order."

### Section 10: Solver and diagnostics (lines 222–228)

Line 226: "Repeated identical solves produce identical strategies, N values, metadata, and diagnostics."

**Cross-check with mandatory acceptance matrix (section 13, line 294):** "policies are normalized, detached, and deterministic." ✓

## Blockers and gaps

**None found.**

All straddle variants are unambiguous. Exact forced posts are validated at config time. All-in forced-post seats are excluded from `pending`. First actionable actor is correctly derived for all variants and player counts. Button Mississippi is explicitly supported for N≥3 and explicitly rejected for N=2. Positions are canonical and deterministic. SB-complete caller counting is explicit. No-reopen intersection semantics are explicit. Zero-sum terminal accounting is mandatory. Determinism is contractual.

## Post-audit hash verification

Pre-audit SHA-256 of `/home/genomix-node/poker-solver/ARCHITECTURE_PHASE4_S3.md`:  
`ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9`

This audit made no edits to the candidate. Post-audit hash is unchanged.

## Recommendation

**PASS with zero blockers.**

The S3 architecture is ready for TDD implementation. All straddle variants, exact forced posts, actionable-only pending, first actionable actor, button Mississippi (N≥3 only), and positions are specified without ambiguity. The mandatory acceptance matrix (section 13) provides executable oracles for every requirement.

**Required truths verified:**

- Standard straddle requires N≥3. ✓
- Double straddle requires N≥4. ✓
- Mississippi straddle requires N≥3 and a non-blind straddler. ✓
- HU Mississippi is rejected (no non-blind seat for N=2). ✓
- Button Mississippi is valid only for N≥3 (button is non-blind when N≥3). ✓
- All straddle amounts strictly increase the live wager. ✓
- Exact all-in posts (stack == cumulative posts) are never truncated. ✓
- All-in forced-post seats are excluded from `pending`. ✓
- First actionable actor is correctly derived for all variants and player counts. ✓

---

**Auditor:** A3H3 (BryantGPT)  
**Completed:** 2026-09-16 UTC  
**Report path:** `/home/genomix-node/poker-solver/research/phase4/s3-design-audit-final/03-straddles-order.md`  
**Heartbeat path:** `/home/genomix-node/poker-solver/research/phase4/s3-design-audit-final/.hb/A3H3`
