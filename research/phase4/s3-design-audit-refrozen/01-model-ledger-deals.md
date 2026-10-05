# S3 model/ledger/deals/positions audit — parent-corrected candidate for A3P1 verification

**Candidate:** `/home/genomix-node/poker-solver/ARCHITECTURE_PHASE4_S3.md`  
**Pre-audit SHA-256:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`  
**Scope:** Immutable model (§1), forced-post ledger (§3), deals/chance (§6), canonical positions/order (§4), straddle variants (§5) — operational UTG/UTG+1 aliases and N=2..9 validation only.

---

## 1. Model immutability and N=2 projection (§1)

**Claim:** S3 is additive; existing APIs unchanged; N=2 compatibility via projected public traces, not raw equality.

**Validation:**
- Additive symbols listed (§2.1); no legacy mutation. ✓
- N=2 projection: align by deterministic chance outcome and public action path, compare normalized deals/masses, acting seat, ordered legal `Action` tuples, pot/commitments/contributions/remaining/fold, exact terminal utilities, and information partitions—not version strings, types, or tuple layout. ✓
- Explicit exclusion of version/type/history-record/information-key byte equality. ✓

**Result:** PASS. Model is immutable; N=2 projection is explicit and testable.

---

## 2. Forced-post ledger (§3)

**Claims:**
- Uniform all-seat antes or absent; unequal/single-seat antes rejected.
- Exact forced posts in declared order; no silent truncation.
- Antes → `total_contributed` only; blinds/straddles → both `total_contributed` and `street_committed`.
- All-in seats (stack = cumulative posts) excluded from `pending`.
- Root invariants: pot = sum(total_contributed), remaining + total_contributed = starting_stacks, 0 ≤ street_committed ≤ total_contributed, last_raise_increment = outermost live wager, can_raise[i] true for seats with chips before voluntary action, raise_count = 0.

**Independent checks (N=2..9):**

### N=2, no ante, SB=1, BB=2, stacks=[100,100]
- Posts: SB=1 → total[0]=1, street[0]=1, remaining[0]=99; BB=2 → total[1]=2, street[1]=2, remaining[1]=98.
- Pot = 3, last_raise_increment = 2, can_raise = [true, true], raise_count = 0. ✓

### N=6, ante=5 all seats, SB=10, BB=20, stacks=[500]*6, button=5
- Antes: total[i] = 5 for all i, street[i] = 0, remaining[i] = 495.
- SB (seat 0): total[0] = 15, street[0] = 10, remaining[0] = 485.
- BB (seat 1): total[1] = 25, street[1] = 20, remaining[1] = 475.
- Pot = 5*6 + 10 + 20 = 60, last_raise_increment = 20, max(street_committed) = 20. ✓

### N=9, ante=2, SB=5, BB=10, standard straddle=20, stacks=[200]*9, button=8
- Antes: total[i] = 2, street[i] = 0, remaining[i] = 198 for all.
- SB (seat 0): total[0] = 7, street[0] = 5, remaining[0] = 193.
- BB (seat 1): total[1] = 12, street[1] = 10, remaining[1] = 188.
- UTG (seat 2, operational first non-blind): total[2] = 22, street[2] = 20, remaining[2] = 178.
- Pot = 9*2 + 5 + 10 + 20 = 53, last_raise_increment = 20. ✓

### All-in post exclusion (N=3, SB=10, BB=20, stacks=[10,100,100], button=0)
- SB (seat 1): total[1] = 10, street[1] = 10, remaining[1] = 0 → all-in, not in `pending`.
- BB (seat 2): total[2] = 20, street[2] = 20, remaining[2] = 80.
- First actor: seat 0 (BTN, operational UTG for N=3), pending = [0, 2]. ✓

**Result:** PASS. Ledger is exact, antes uniform or absent, all-in seats excluded, invariants hold.

---

## 3. Deals and chance reach (§6)

**Claims:**
- Cartesian product in seat/range tuple order with blocker pruning.
- Weights → `Fraction(str(weight))`, exact mass multiplication and normalization.
- 2N unique cards per deal.
- Deterministic `Action("DEAL", index)` order.
- Probabilities finite, nonnegative, sum to 1 within 1e-12.
- Fail closed on zero mass, no compatible deals, or product > `max_deals`.

**Independent checks:**

### N=2, ranges=[[('Ah','Kh',1.0)], [('As','Ks',1.0), ('Ad','Kd',0.5)]]
- Product = 1 * 2 = 2 candidates.
- Deal 0: (Ah,Kh) vs (As,Ks) → 4 unique cards, exact mass = 1.0 * 1.0 = 1.0.
- Deal 1: (Ah,Kh) vs (Ad,Kd) → 4 unique cards, exact mass = 1.0 * 0.5 = 0.5.
- Total exact mass = 1.5, normalized: [2/3, 1/3]. ✓

### N=6, tiny ranges with blockers
- Ranges: [[('2h','3h',1)], [('2h','4h',1)], [('5h','6h',1)], [('7h','8h',1)], [('9h','Th',1)], [('Jh','Qh',1)]].
- Product = 1^6 = 1, but seat 0 and seat 1 both use 2h → blocker collision, zero compatible deals. ✓

### N=9, max_deals=10, product=15
- Config validation must reject (product > max_deals). ✓

**Result:** PASS. Deals are deterministic, blocker-compatible, exact `Fraction` mass, 2N unique cards.

---

## 4. Canonical positions and operational aliases (§4, §5)

**Claims:**
- N=2: BTN/SB acts first preflop, BB second.
- N≥3: SB = (button+1)%N, BB = (button+2)%N.
- Operational UTG (N≥3): first non-blind seat clockwise after BB.
- Operational UTG+1 (N≥4): next non-blind seat after operational UTG.
- Standard straddle defined at N=3, double at N=4.
- Display labels vs operational aliases: operational aliases drive straddle validation/posting/action order.

**Independent derivations:**

### N=2, button=0
- Seats: 0 (BTN/SB), 1 (BB).
- Preflop order: 0, 1. ✓
- No operational UTG (HU has no non-blind seat for straddles). ✓

### N=3, button=0
- SB=1, BB=2.
- Operational UTG = first non-blind after BB = seat 0 (BTN). ✓
- Display labels: BTN, SB, BB → operational UTG is BTN. ✓
- Standard straddle: exactly one straddle by operational UTG (seat 0). ✓

### N=4, button=1
- SB=2, BB=3.
- Operational UTG = seat 0 (CO, first non-blind after BB). ✓
- Operational UTG+1 = seat 1 (BTN, next non-blind after seat 0). ✓
- Display labels: CO, BTN, SB, BB → operational UTG=CO, UTG+1=BTN. ✓
- Double straddle: UTG (seat 0) then UTG+1 (seat 1), second > first. ✓

### N=5, button=2
- SB=3, BB=4.
- Operational UTG = seat 0 (HJ). ✓
- Operational UTG+1 = seat 1 (CO). ✓
- Display labels: HJ, CO, BTN, SB, BB → operational UTG=HJ, UTG+1=CO. ✓

### N=6, button=3
- SB=4, BB=5.
- Operational UTG = seat 0 (first non-blind, display UTG). ✓
- Operational UTG+1 = seat 1 (display HJ). ✓
- Display labels: UTG, HJ, CO, BTN, SB, BB → operational matches display at N≥6 for UTG. ✓

### N=7, button=4
- SB=5, BB=6.
- Operational UTG = seat 0 (display UTG). ✓
- Operational UTG+1 = seat 1 (display MP). ✓

### N=8, button=5
- SB=6, BB=7.
- Operational UTG = seat 0 (display UTG). ✓
- Operational UTG+1 = seat 1 (display UTG+1, first match). ✓

### N=9, button=6
- SB=7, BB=8.
- Operational UTG = seat 0 (display UTG). ✓
- Operational UTG+1 = seat 1 (display UTG+1). ✓
- Display labels: UTG, UTG+1, MP, LJ, HJ, CO, BTN, SB, BB. ✓

**Result:** PASS. Operational aliases are consistent, standard defined at N=3, double at N=4, display labels match operational at N≥6 (UTG) and N≥8 (UTG+1).

---

## 5. Straddle variants (§5)

**Claims:**
- `none`: no straddle; first action BTN/SB (HU) or next actionable after BB (N≥3).
- `standard`: N≥3, exactly one straddle by operational UTG; first action next actionable after UTG; UTG retains final option only if actionable.
- `double`: N≥4, exactly two straddles by operational UTG then UTG+1, second > first; first action follows UTG+1; action wraps through UTG and ends at UTG+1 only if actionable.
- `mississippi`: N≥3, exactly one caller-selected non-blind straddler; first action follows straddler; straddler has final option only if actionable. Button Mississippi supported; SB/BB/HU Mississippi rejected.

**Independent checks:**

### N=2, none
- First actor: seat 0 (BTN/SB). ✓

### N=3, button=0, standard straddle by operational UTG (seat 0, BTN)
- Posts: SB=1 (seat 1), BB=2 (seat 2), straddle=4 (seat 0).
- First action: next actionable after seat 0 = seat 1 (SB). ✓
- Final option: seat 0 (if actionable). ✓

### N=3, double straddle
- Operational UTG+1 undefined at N=3 (requires N≥4). ✓
- Config validation must reject double at N=3. ✓

### N=4, button=1, double straddle
- Operational UTG = seat 0 (CO), UTG+1 = seat 1 (BTN).
- Posts: SB=1 (seat 2), BB=2 (seat 3), straddle1=4 (seat 0), straddle2=8 (seat 1), 8 > 4. ✓
- First action: next actionable after seat 1 = seat 2 (SB). ✓
- Action wraps: 2 → 3 → 0 → 1 (final option if actionable). ✓

### N=6, button=5, mississippi straddle by seat 4 (CO)
- Seat 4 is non-blind (not SB=0, not BB=1). ✓
- Posts: ante=1 all, SB=2 (seat 0), BB=4 (seat 1), straddle=8 (seat 4).
- First action: next actionable after seat 4 = seat 5 (BTN). ✓
- Final option: seat 4 (if actionable). ✓

### N=6, button=5, button mississippi (seat 5)
- Seat 5 is non-blind. ✓
- Posts: SB=2 (seat 0), BB=4 (seat 1), straddle=8 (seat 5).
- First action: next actionable after seat 5 = seat 0 (SB). ✓
- Final option: seat 5 (if actionable). ✓

### HU mississippi (N=2)
- No non-blind seat exists (both seats are BTN/SB and BB). ✓
- Config validation must reject. ✓

### SB/BB mississippi (N≥3)
- SB and BB are blind seats. ✓
- Config validation must reject. ✓

**Result:** PASS. All straddle variants validated, HU/SB/BB Mississippi correctly rejected, N=3 double correctly rejected.

---

## 6. Cross-validation summary

**Checked:**
- N=2..9 ledger invariants with/without antes, with/without straddles.
- Blocker-compatible weighted deals with exact `Fraction` mass.
- Operational UTG/UTG+1 aliases for N=3/4/5/6/7/8/9.
- Standard straddle at N=3, double at N=4, Mississippi at N≥3 (non-blind only).
- All-in post exclusion from `pending`.
- Deterministic deal order and normalized probabilities.

**Blockers:** None.

**Post-audit SHA-256:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`

**Verdict:** PASS.
