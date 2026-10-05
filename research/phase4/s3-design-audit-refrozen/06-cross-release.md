# S3 Refrozen Cross-Release Audit A3K6

**Auditor:** A3K6 (corrective cross-release auditor after A3J6 ownership ended)  
**Candidate:** `/home/genomix-node/poker-solver/ARCHITECTURE_PHASE4_S3.md`  
**Pre-audit SHA-256:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6` ✓  
**Post-audit SHA-256:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6` ✓  
**Base:** `4b3f87f4e6cf38e9dc88aca744b23de2c44c08fe` ✓  
**Historical tag:** `phase3-398-green` → `feba8222a0b614b0c64eca59402403ce733195ea` ✓  
**Scope:** Independent adversarial cross-release attack on entire refrozen S3 design

---

## Executive Summary

**VERDICT: PASS**

The refrozen S3 architecture candidate survives comprehensive cross-release adversarial attack. All operational UTG/UTG+1 aliases, no-reopen pending/entitlement separation, uniform ante refund algebra, N=2 projection semantics, bounded synthetic ranges, TDD batch ownership, and API/CFR/information contracts are internally consistent and executable. The mandatory no-reopen trace correctly separates pending rebuild (all other live seats with chips) from raise-entitlement intersection (old_pending ∩ old_entitlement), proving action remains open with call/fold options even when no seat can raise.

**Blockers:** None.

---

## Attack Surface

### 1. Mandatory No-Reopen Trace: Pending vs Entitlement Separation (§7 lines 190–192)

**Claim:** §7 line 190 states "Any raise rebuilds pending as all other live seats with chips, clockwise after the raiser, because every such seat must respond or retain an unacted option." §7 line 192 states for no-reopen short all-in: "a seat may raise after it only when that seat was both still in the pre-action pending queue and raise-entitled before the short all-in. This is an intersection, not a union."

**Attack:** Does the intersection control pending membership or only raise entitlement?

**Mandatory trace (4-seat: SB/BB/CO/BTN, stacks [500,35,500,500], posts [(SB,5),(BB,10)]):**

**Root state:**
- `street_committed = [5, 10, 0, 0]`
- `pot = 15`
- `last_raise_increment = 10`
- `can_raise = [true, true, true, true]` (all seats have chips after posts)
- `pending = [CO, BTN, SB, BB]` (all seats, clockwise after BB)
- First actor: CO

**Step 1: CO raises to 30**
- `H = 10` (highest current wager)
- CO raises to 30 → `raise_size = 30 - 10 = 20 ≥ 10` → full raise
- New `last_raise_increment = 20`
- `raise_count = 1`
- §7 line 191: "A full raise updates `last_raise_increment`; every other live seat with chips is re-entitled to raise, while the raiser has consumed its entitlement"
- `can_raise = [true, true, false, true]` (SB/BB/BTN re-entitled; CO consumed)
- §7 line 190: "Any raise rebuilds pending as all other live seats with chips, clockwise after the raiser"
- `pending = [BTN, SB, BB]` (all other live seats with chips, clockwise after CO)
- `street_committed = [5, 10, 30, 0]`
- Next actor: BTN

**Step 2: BTN calls 30**
- §7 line 189: "CHECK/CALL removes the actor from the current pending queue and consumes its current raise entitlement"
- `can_raise[BTN] = false` (consumed)
- BTN removed from pending
- `pending = [SB, BB]`
- `street_committed = [5, 10, 30, 30]`
- Next actor: SB

**Step 3: SB calls 30**
- `can_raise[SB] = false` (consumed)
- SB removed from pending
- `pending = [BB]`
- `street_committed = [30, 10, 30, 30]`
- Next actor: BB

**Step 4: BB all-in raises to 35**
- `H = 30`
- BB has `remaining = 25` (started 35, posted 10)
- BB all-in target = `10 + 25 = 35`
- Minimum full raise-to = `30 + 20 = 50`
- `35 < 50` → short all-in
- `35 > 30` → legal (exceeds H per §7 line 182)
- `raise_size = 35 - 30 = 5 < 20` → does not update increment
- `raise_count = 2`
- **Snapshot state before BB's raise:**
  - `old_pending = [BB]`
  - `old_can_raise = [false, true, false, false]` (only BB entitled)
- **§7 line 190 applies first:** "Any raise rebuilds pending as all other live seats with chips, clockwise after the raiser"
  - New `pending = [CO, BTN, SB]` (all other live seats with chips, clockwise after BB)
- **§7 line 192 applies to entitlement only:** "If `short_all_in_reopens` is false, a seat may raise after it only when that seat was both still in the pre-action pending queue and raise-entitled before the short all-in. This is an intersection, not a union."
  - Intersection = `old_pending ∩ old_can_raise = {BB} ∩ {BB} = {BB}`
  - BB is all-in (no chips) → not actionable
  - CO: not in intersection → `can_raise[CO] = false`
  - BTN: not in intersection → `can_raise[BTN] = false`
  - SB: not in intersection → `can_raise[SB] = false`
- **Final state after BB's short all-in:**
  - `pending = [CO, BTN, SB]` (they must respond)
  - `can_raise = [false, false, false, false]` (none can raise)
  - `street_committed = [30, 35, 30, 30]`
  - Next actor: CO

**Step 5: Responders act**
- CO is in pending → must act → legal actions: CALL 35 or FOLD (cannot RAISE because `can_raise[CO] = false`)
- BTN is in pending → must act → legal actions: CALL 35 or FOLD
- SB is in pending → must act → legal actions: CALL 35 or FOLD
- **Action is NOT closed** until all pending seats respond

**Step 6: All call, action closes**
- CO calls 35, BTN calls 35, SB calls 35
- `pending = []` (all responded)
- Action closes
- `street_committed = [35, 35, 35, 35]`
- `pot = 140`

**Semantic proof:**
- §7 line 190 is unconditional: "**Any** raise rebuilds pending as **all other live seats with chips**"
- §7 line 192 controls **raise entitlement only**: "a seat **may raise** after it only when..."
- Pending membership ≠ raise entitlement
- A seat in pending with `can_raise=false` can still CALL or FOLD
- Action closure requires `pending = []` OR only one live seat remains (§7 line 194)
- After BB's short all-in, `pending = [CO, BTN, SB]` (three seats) → action is NOT closed
- CO/BTN/SB must respond (call or fold) even though they cannot raise

**Contradiction search:** Does any text conflate pending with can_raise?
- §7 line 190: "rebuilds pending" — membership operation ✓
- §7 line 192: "may raise" — entitlement operation ✓
- §7 line 194: "Action closes when one live seat remains or no actionable pending responder remains" — "actionable" means "can act" (call/fold/raise), not "can raise" ✓
- §4 line 147: "Seats all-in from exact forced posts are excluded: they have no CHECK, CALL, FOLD, or raise decision and do not retain an option" — all-in seats are non-actionable because they have no legal actions, not because `can_raise=false` ✓

**Status:** ✓ PASS — Pending rebuild and raise-entitlement intersection are separate operations. Action remains open with call/fold options even when no seat can raise.

---

### 2. Operational Position Aliases: Button-Relative UTG/UTG+1 (§4 lines 143–145, §5 lines 149–154, manifest line 14)

**Claim:** §4 lines 143–144 state operational UTG is the first non-blind seat clockwise after BB (N≥3), and operational UTG+1 is the next non-blind seat after operational UTG (N≥4). §4 line 145 states "Position is derived, not mutable state."

**Attack vectors:**

**N=2 (HU):**
- Seats: [SB/BTN, BB]
- Blinds: SB, BB
- Non-blind seats after BB: none (BTN is SB, a blind)
- Operational UTG: undefined
- Operational UTG+1: undefined
- §5 line 154: "HU Mississippi straddle is rejected: N=2 has no non-blind seat" ✓

**N=3:**
- Seats: [SB, BB, BTN] (clockwise)
- Blinds: SB, BB
- First non-blind seat clockwise after BB: BTN
- Operational UTG: BTN ✓
- Next non-blind seat after BTN: none (only one non-blind seat)
- Operational UTG+1: undefined
- §5 line 153: "Standard straddle is defined for N≥3; double straddle requires N≥4" ✓
- Standard straddle at N=3: BTN may straddle (operational UTG) ✓
- Double straddle at N=3: rejected (no operational UTG+1) ✓

**N=4:**
- Seats: [SB, BB, CO, BTN] (clockwise)
- Blinds: SB, BB
- First non-blind seat clockwise after BB: CO
- Operational UTG: CO ✓
- Next non-blind seat after CO: BTN
- Operational UTG+1: BTN ✓
- Standard straddle: CO may straddle ✓
- Double straddle: CO and BTN may straddle ✓

**N=5:**
- Seats: [SB, BB, HJ, CO, BTN] (clockwise)
- Operational UTG: HJ (first non-blind after BB) ✓
- Operational UTG+1: CO (next non-blind after HJ) ✓

**N=6:**
- Seats: [SB, BB, UTG, HJ, CO, BTN] (clockwise)
- Operational UTG: displayed UTG seat (first non-blind after BB) ✓
- Operational UTG+1: displayed HJ seat (next non-blind after UTG) ✓

**N=9:**
- Seats: [SB, BB, UTG, UTG+1, UTG+2, LJ, HJ, CO, BTN] (clockwise)
- Operational UTG: displayed UTG seat (first non-blind after BB) ✓
- Operational UTG+1: displayed UTG+1 seat (next non-blind after UTG) ✓

**Display label collision at N=3:**
- Display label: "BTN"
- Operational UTG: BTN
- Collision? No — §4 line 145: "Position is derived, not mutable state." Display labels are for human readability; operational aliases are for straddle validation. They serve different purposes ✓

**Status:** ✓ PASS — Operational aliases are consistent, unambiguous, and correctly reject HU Mississippi and N=3 double straddle.

---

### 3. Uniform Ante Refund Boundedness (§3, §8, §15)

**Claim:** §8 line 197 states "The all-seats-equal ante contract guarantees that every seat's total contribution is the same dead ante plus its live street commitment, so a unique leader's total-contribution excess equals its street-commitment excess and is bounded by that street commitment."

**Attack:** Construct a valid config where refund exceeds the leader's street commitment.

**Algebraic proof:**
- With uniform all-seat ante `A`, every seat's `total[i] = A + street[i]` (§3 line 120)
- Leader `L` has `total[L] = max(total)`
- Second-highest `total[2]` satisfies `total[2] ≤ total[L]`
- Refund = `total[L] - total[2] = (A + street[L]) - (A + street[2]) = street[L] - street[2]`
- Since `street[2] ≥ 0` (invariant §3 line 120), `refund ≤ street[L]` QED ✓

**Counterexample attempt:**
- Config: `A=10`, `street=(0, 50, 100)` → `total=(10, 60, 110)`
- Refund = `110 - 60 = 50`
- Leader's street commitment = `100`
- `50 ≤ 100` ✓

**Unequal ante rejection:**
- §8 line 197: "Unequal or single-seat antes are rejected at config validation rather than deferred to terminal failure" ✓
- §3 line 120: "All seats pay the same ante" ✓

**Status:** ✓ PASS — Refund is algebraically bounded by leader's street commitment under uniform ante.

---

### 4. SB Completion as Pre-Raise Caller (§7 line 184)

**Claim:** §7 line 184 states "every pre-raise CALL, including a small-blind completion, counts for an opening/isolation decision."

**Attack:** Is SB completion semantically a call?

**Semantic check:**
- SB posts 1, BB posts 2
- SB completes to 2 (adds 1 chip)
- SB has called the live wager (2) without raising
- Functionally identical to a limp from a non-blind seat ✓
- For BB's isolation decision, SB completion is a caller ✓

**Sizing-key impact:**
- UTG limps, HJ limps, SB completes → BB sees `cold_callers = 3` (UTG, HJ, SB) ✓
- BB's isolation sizing key includes `cold_callers = 3` ✓

**Status:** ✓ PASS — SB completion is correctly counted as a pre-raise caller.

---

### 5. N=2 Projection vs Raw Equality (§1 lines 9–10, §13 line 296)

**Claim:** §1 states N=2 compatibility is "explicit projection" over aligned public traces, not raw type/version/history/key equality.

**Attack:** Does projection paper over a structural incompatibility?

**Projection elements (§1 lines 9–10):**
- Normalized private deals and exact masses ✓
- Acting seat ✓
- Ordered legal `Action` tuples ✓
- Pot, street commitments, total contributions, remaining stacks, fold status ✓
- Exact terminal utilities ✓
- Information partitions (not key bytes) ✓

**Exclusions:**
- Version strings, concrete types, actor wrappers, tuple layout ✓

**Semantic equivalence:**
- Two game trees are equivalent if, for every aligned decision state, they have identical public state, legal actions, and terminal outcomes ✓
- Information compatibility requires partition equality (same infosets), not key-byte equality ✓

**Acceptance criterion (§13 line 296):**
- "N=2 projected deals/actions/ledgers/terminals/information partitions match frozen Phase-3 HU fixtures" ✓
- Testable and falsifiable ✓

**Status:** ✓ PASS — N=2 projection is sound semantic equivalence.

---

### 6. Bounded Synthetic Ranges vs Tractability Claims (§1 lines 11–13, §13 line 286)

**Claim:** §1 states "All HU, 6-player, and 9-player S3 acceptance fixtures use deliberately tiny synthetic per-seat ranges whose full Cartesian product is at most `max_deals`. They prove player-count generality and exact chance arithmetic, not realistic full-range tractability."

**Attack:** Does §13 or any boundary contradict this by requiring large-range performance?

**§13 line 286:**
- "HU, 6-max, and 9-max roots build and solve, return N values, and use exact deterministic chance mass" — no range size specified ✓

**§1 line 13:**
- "Large-range tractability belongs to S4 abstraction" ✓

**Contradiction search:** None found. S3 is explicitly a bounded reference path ✓

**Status:** ✓ PASS — Bounded synthetic ranges are explicit and consistent.

---

### 7. Continuation Kind and Convergence Claims (§2.6, §10, §13)

**Claim:** §2.6 states result metadata has `converged=False` and `convergence_claim="none"`. §10 line 227 states deviation certificate "is never sampled and never called exploitability or a Nash certificate."

**Attack:** Does §13 or any boundary require convergence?

**§13 lines 294–295:**
- "policies are normalized, detached, and deterministic" and "exact six-plus-player reach and unilateral-deviation oracles match production below declared caps" — no convergence requirement ✓

**§1 line 11:**
- S3 "does not claim ... equilibrium convergence" ✓

**Status:** ✓ PASS — No convergence claim is made or required.

---

### 8. TDD Batch Ownership and Feasibility (§12)

**Claim:** §12 assigns four exclusive RED owners to S3-I1, then a fifth gated core owner for production.

**Attack:** Is the betting/settlement boundary clean?

**S3-I1 batch 2 (betting):**
- "HU/6/9 action order, limps, SB complete, cold calls, exact sizing-key selection, raise-to targets, 3/4/5-bet+, full/short all-ins and closure" — owns action legality and transitions ✓

**S3-I1 batch 3 (settlement):**
- "independent fold/refund/side-pot/showdown continuation ledgers and zero-sum terminal-table leaves" — owns terminal accounting after action closes ✓

**Boundary:**
- Batch 2 does not compute terminal utilities; batch 3 does not generate action trees ✓
- Clean separation ✓

**Status:** ✓ PASS — TDD batch ownership is clean and feasible.

---

### 9. Straddle Strict-Increase and All-In Option Exclusion (§3, §4, §5)

**Claim:** §5 line 149 requires every straddle amount strictly greater than preceding live wager. §4 line 147 excludes all-in post seats from `pending`.

**Attack:** Does spec permit equal or non-increasing straddles as degenerate edge case?

**§5 line 149:**
- "Each amount is a positive integer strictly greater than the preceding live wager; equal or decreasing declarations are not straddles under this contract and fail validation." Unambiguous rejection ✓

**§3 line 110:**
- "A seat may start all-in only when its stack exactly equals its cumulative declared posts" ✓

**§4 line 147:**
- "Seats all-in from exact forced posts are excluded: they have no CHECK, CALL, FOLD, or raise decision and do not retain an option" ✓

**Status:** ✓ PASS — Straddle strict-increase and all-in exclusion are unambiguous.

---

### 10. Reconciliation vs Spec Body Contradictions (§14)

**Rejected elements scan:**
- D301 zero street commitment at root: rejected. §3 requires blinds/straddles increase `street_committed` ✓
- D301 initial-blind refund rejection: rejected. §8 applies refund before terminal ✓
- D302 decimal-chip examples: rejected. All amounts are strict integers ✓
- D302 non-zero-sum fold tuple: rejected. §8 requires exact zero-sum ✓
- D303 HU Mississippi: rejected. §5 line 154 rejects HU Mississippi ✓
- D303 nested double-option claims: rejected. §5 defines explicit variant rules ✓
- D304 "S3 needs no continuation": rejected. §2.3 requires continuation ✓
- D306 replayed S2 postflop: rejected as S3 evidence ✓

**Contradiction search:** None found in spec body ✓

**Status:** ✓ PASS — Reconciliation correctly rejects all contradictory elements.

---

### 11. Executable Acceptance Matrix (§13)

**18 criteria feasibility check:**
1. Config validation rejection: feasible via pytest parametrize ✓
2. HU/6/9 solve with exact chance: feasible with tiny synthetic ranges ✓
3. Straddle variant trees: feasible via independent ledger oracles ✓
4. Sizing-key selection: feasible via traced decision contexts ✓
5. Action amount conservation: feasible via pot/stack invariants ✓
6. Pending/reopening rules: feasible via traced action sequences ✓
7. Independent terminal oracles: feasible via hand-calculated rational arithmetic ✓
8. Zero-sum terminals: feasible via sum assertion ✓
9. Information noninterference: feasible via key stability under hidden-value variation ✓
10. Policy normalization: feasible via sum assertion ✓
11. Reach/deviation oracles: feasible via exhaustive enumeration on tiny trees ✓
12. N=2 projection: feasible via frozen Phase-3 HU fixture alignment ✓
13. v4/CLI/examples/exports: feasible via contract tests ✓
14. S1/S2 regression: feasible via full suite run ✓
15. Fresh audit per batch: this audit is one instance ✓
16. Historical tag preservation: feasible via `git rev-parse` ✓
17. Each batch has fresh non-author audit: procedural requirement ✓
18. Accepted-wave commit: procedural requirement ✓

**Status:** ✓ PASS — All 18 acceptance criteria are executable.

---

### 12. Migration Hazards and Regression Risk (§13)

**S1/S2 regression (§13 line 298):**
- "all S1/S2 and legacy tests remain green" ✓

**Current state:**
- S3 is design-only. No production/test paths modified. Candidate manifest confirms zero production changes ✓

**S3-I1/I2 implementation risk:**
- New `nplayer_preflop.py` module is additive. Existing `preflop.py` (HU), `nplayer_postflop.py` (S2), `allstreet.py` (S1), and generic `nplayer.py` keep public behavior per §1 line 7 ✓

**Historical baseline (§13 line 300):**
- "`phase3-398-green` remains exactly at `feba8222a0b614b0c64eca59402403ce733195ea`" ✓

**Verification:**
- Current HEAD `4b3f87f4` is S2-complete descendant of historical tag. Tag immutability is a future S3-I1/I2 requirement, not violated by design acceptance ✓

**Status:** ✓ PASS — No regression risk from design acceptance.

---

### 13. API Contract and Boundary Truth (§11, §13)

**v4 operation:**
- `solve-nplayer-preflop` with strict `{version: 4, operation, payload}` envelope ✓

**Payload validation:**
- Unknown/missing fields, bool numerics, nonfinite values, malformed arrays, duplicate keys, unsupported seeds/algorithms, bound violations fail closed per §11 line 243 ✓

**Response truth:**
- `approximate: false`, no convergence claim, metadata states `converged=False` and `convergence_claim="none"` per §2.6 line 106 ✓

**CLI:**
- Generic `phase4 FILE|- --json` forwards v4, no new parser shape required per §11 line 248 ✓

**Examples:**
- Synthetic, non-presolved, bounded per §11 line 253 ✓

**Exports (§11 line 255):**
- Additive, truthful capabilities: `nplayer-preflop` with players `[2, 9]`, street `preflop-one-round`, interfaces `typed/json-v4/cli-phase4`, continuations `supplied-or-derived-bounded`, deviation `exhaustive-diagnostic-only` ✓

**Status:** ✓ PASS — API contract is truthful and bounded.

---

### 14. Information Noninterference (§9, §13)

**Included fields (§9 lines 211–220):**
- version/rule identity, N, owner seat, owner's private combo, button, starting stacks, forced posts, straddle variant, sizing-rule identity, pot, public commitments/contributions/remaining/fold flags, pending order, raise entitlements, last increment, raise count, acting seat, actor-labelled public history, continuation kind/source/provenance ✓

**Excluded fields (§9 line 222):**
- opponent cards, deal index/order, hidden payoff-table values, hidden showdown ranks, traversal state ✓

**Acceptance criterion (§13 line 291):**
- "opponent-card and hidden-continuation noninterference pass for 6 and 9 players" ✓

**Attack:**
- Vary opponent cards while owner/public state fixed → key must be stable ✓
- Vary hidden payoff values while public state fixed → key must be stable ✓

**Status:** ✓ PASS — Information noninterference is correctly specified.

---

### 15. Solver and Diagnostics (§10, §13)

**Algorithm:**
- Only `vanilla-cfr` accepted per §10 line 223 ✓

**Iterations:**
- Positive strict integer ✓

**Deviation diagnostic:**
- Exhaustive below cap or fails closed; never sampled, never called exploitability or Nash certificate per §10 line 227 ✓

**Determinism (§10 line 226):**
- "Repeated identical solves produce identical strategies, N values, metadata, and diagnostics" ✓

**Acceptance criterion (§13 line 294):**
- "exact six-plus-player reach and unilateral-deviation oracles match production below declared caps" — requires independent oracle, not production as oracle ✓

**Status:** ✓ PASS — Solver and diagnostics are correctly specified.

---

## Boundary Truth

**§1 explicit boundaries:**
- Additive, not a replacement ✓
- Finite reference path, not unrestricted solving ✓
- Caller-supplied continuations or bounded derived showdown ✓
- Tiny synthetic ranges for acceptance, not production-scale claims ✓
- S4 abstraction is separate ✓
- No equilibrium convergence claim ✓
- No automatic abstraction ✓
- No continuous sizing ✓
- No automatic multi-street solving ✓

**Overclaim search:** None detected ✓

---

## Final Verdict

**PASS**

The refrozen S3 architecture candidate (SHA-256 `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`) survives comprehensive cross-release adversarial attack. All 15 attack vectors resolve to spec consistency.

The mandatory no-reopen trace proves the critical separation: §7 line 190 unconditionally rebuilds pending to all other live seats with chips (ensuring they must respond), while §7 line 192 applies intersection semantics only to raise entitlement (preventing prior callers from re-raising). After BB's short all-in to 35, `pending=[CO,BTN,SB]` (they must act) and `can_raise=[false,false,false]` (they cannot raise), so action remains open with call/fold options until all pending seats respond. This is the correct no-reopen poker rule.

Operational UTG/UTG+1 aliases correctly define standard straddle at N=3 and double straddle at N≥4. Uniform ante refund boundedness is algebraically proven. N=2 projection is sound semantic equivalence. All 18 acceptance criteria are executable with bounded synthetic inputs. Zero substantive contradictions, overclaims, or unrepresentable configurations exist within stated scope.

**Blockers:** None.

**S3-I1 and S3-I2 implementation may proceed** under the TDD batch gates in §12, with mandatory fresh non-author audits after each batch and parent verification before the next batch starts.

---

**A3K6 / 2026-09-16 UTC**
