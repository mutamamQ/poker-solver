# S2 Design Audit — Betting Round Transitions

**Auditor:** Subagent A2F2  
**Scope:** One-round N-player betting semantics (§5 ARCHITECTURE_PHASE4_S2.md)  
**Method:** Adversarial first-principles derivation with hand traces  
**Verdict:** PASS with clarifications

---

## 1. Initial order and pending responders

### Specification (§5.1)

- Chance root builds `pending` as active seats clockwise after button
- After deal, first pending seat acts
- `_ordered_after(seat, candidates)` scans clockwise with wraparound

### Derivation

For N players numbered 0..(N-1), button B, "clockwise after B" means seats (B+1) mod N, (B+2) mod N, ..., wrapping at N-1 → 0.

Active = not folded AND remaining > 0.

Root pending = [s for s in clockwise_order if active(s)].

After deal, acting_player = pending[0].

### Hand trace 1: 4-player, button=1, all active

```
Seats: 0,1,2,3  Button=1
Clockwise after 1: 2,3,0
All active → pending = (2,3,0)
First actor = 2
```

### Hand trace 2: 5-player, button=0, seat 2 folded preflop

```
Seats: 0,1,2,3,4  Button=0
Clockwise after 0: 1,2,3,4
Active: 1,3,4 (seat 2 folded)
pending = (1,3,4)
First actor = 1
```

**Finding:** None. Clockwise order is unambiguous and deterministic.

---

## 2. Check/call/fold transitions

### Specification (§5.2, §5.3)

- If to_call == 0, offer CHECK
- Otherwise FOLD + CALL(own + min(to_call, remaining))
- Check/call/fold remove actor from pending
- All-in caller becomes non-actionable
- Terminate when one live seat remains OR pending empty

### Derivation

H = max(street_committed)
to_call = H - street_committed[actor]

CHECK: to_call == 0, remove actor from pending  
CALL: transfer min(to_call, remaining[actor]) chips, remove from pending  
FOLD: mark folded, remove from pending

After action:
- live = {s : not folded[s]}
- If |live| == 1 → terminal
- If pending == [] → terminal
- Else acting_player = pending[0]

### Hand trace 3: 3-player check-check-check

```
Button=0, pending=(1,2,0), street_committed=(0,0,0)
P1 CHECK → pending=(2,0)
P2 CHECK → pending=(0,)
P0 CHECK → pending=()
→ Terminal (all checked, round closed)
```

### Hand trace 4: 4-player fold cascade

```
Button=0, P1 bets 4, pending=(2,3,0)
street_committed=(0,4,0,0)
P2 FOLD → pending=(3,0), live={0,1,3}
P3 FOLD → pending=(0,), live={0,1}
P0 FOLD → pending=(), live={1}
→ Terminal (one live seat)
```

**Finding:** None. Check/call/fold closure is correct.

---

## 3. Full raises and reopening

### Specification (§5.3)

- Full raise: `target - old_H >= last_raise_increment`
- Update increment, rebuild pending as every other active seat clockwise after raiser
- Reopen raising for all active seats

### Derivation

old_H = max(street_committed) before raise  
raise_size = target - old_H

If raise_size >= last_raise_increment:
  - last_raise_increment := raise_size
  - can_raise[s] := (not folded[s] AND remaining[s] > 0) for all s
  - pending := active_others_clockwise_after_raiser
  - raise_count += 1

### Hand trace 5: 5-player full raise reopening

```
Button=2, pending=(3,4,0,1), street_committed=(0,0,0,0,0)
P3 RAISE 4 → old_H=0, size=4, increment=4
  pending=(4,0,1,2), can_raise=all active
P4 RAISE 8 → old_H=4, size=4 >= 4 (full)
  increment=4, pending=(0,1,2,3), can_raise=all active
P0 CALL 8 → pending=(1,2,3)
P1 RAISE 12 → old_H=8, size=4 >= 4 (full)
  increment=4, pending=(2,3,4,0), can_raise=all active
```

**Finding:** None. Full raise semantics are consistent.

---

## 4. Short all-ins and reopening

### Specification (§5.3)

- Short all-in raise: target < old_H + last_raise_increment, but target == actor's all-in
- Do NOT update increment
- Seats still in old_pending retain prior entitlement
- Seats that had already acted cannot re-raise
- Short raiser has no chips, cannot raise

### Derivation

old_pending = pending before short raise  
old_H = max(street_committed)

If raise_size < last_raise_increment:
  - Do NOT update last_raise_increment
  - pending := active_others_clockwise_after_raiser
  - For s in active_others:
      if s NOT in old_pending:
        can_raise[s] := False
  - can_raise[raiser] := False (all-in)

### Hand trace 6: 4-player short all-in does not reopen prior actor

```
Button=0, stacks=(20,20,7,20), contributions=(2,2,2,2)
remaining=(18,18,5,18), pending=(1,2,3)
P1 RAISE 4 → old_H=2, size=2, increment=2
  pending=(2,3,0), old_pending=(2,3,0)
P2 RAISE 5 (all-in) → old_H=4, size=1 < 2 (short)
  increment stays 2
  pending=(3,0,1)
  P3,P0 were in old_pending → retain can_raise
  P1 was NOT in old_pending → can_raise[1]=False
  can_raise[2]=False (all-in)
P3 CALL 5 → pending=(0,1)
P0 CALL 5 → pending=(1)
P1 acts: to_call=5-4=1, can_raise[1]=False
  Legal: FOLD, CALL(5)
  NOT legal: RAISE (no entitlement)
```

### Hand trace 7: 5-player short all-in, pending responder can still raise

```
Button=1, stacks=(20,20,20,9,20), pending=(2,3,4,0)
P2 RAISE 4 → old_H=0, increment=4, pending=(3,4,0,1)
P3 RAISE 7 (all-in) → old_H=4, size=3 < 4 (short)
  increment stays 4, pending=(4,0,1,2)
  P4,P0,P1 were in old_pending → retain can_raise
  P2 was NOT in old_pending → can_raise[2]=False
P4 acts: can_raise[4]=True, to_call=7
  Legal: FOLD, CALL(7), RAISE(11+) if 11 <= remaining
```

**Finding:** None. Short all-in reopening logic is correct and matches Phase-3 test `test_short_all_in_is_legal_and_does_not_reopen_prior_actor`.

---

## 5. Closure and depth

### Specification (§5.3)

- Terminate when one live seat remains OR pending empty
- All live all-in seats being non-actionable closes the round
- Max depth: N + max_raises * (N - 1)

### Derivation

After each action:
- live = {s : not folded[s]}
- actionable_pending = [s in pending : not folded[s] AND remaining[s] > 0]
- If |live| == 1 → terminal
- If actionable_pending == [] → terminal
- Else acting_player = actionable_pending[0]

Depth bound:
- Initial round: N seats act (checks or first aggression)
- Each raise: up to (N-1) responders
- max_raises raises → N + max_raises*(N-1) decisions

### Hand trace 8: 4-player all-in closure

```
Button=0, stacks=(10,10,10,10), pending=(1,2,3)
P1 RAISE 10 (all-in) → pending=(2,3,0)
P2 CALL 10 (all-in) → pending=(3,0)
P3 CALL 10 (all-in) → pending=(0)
P0 CALL 10 (all-in) → pending=()
actionable_pending=[] → terminal
```

### Hand trace 9: 6-player depth bound, max_raises=2

```
N=6, max_raises=2
Max depth = 6 + 2*5 = 16 decisions
Scenario:
- P0 CHECK, P1 CHECK, P2 CHECK, P3 CHECK, P4 CHECK, P5 RAISE (6 actions)
- P0 RAISE, P1 RAISE (capped), P2 CALL, P3 CALL, P4 CALL, P5 CALL (6 actions)
Total = 12 < 16 ✓
```

**Finding:** None. Closure and depth are structurally sound.

---

## 6. Specification contradictions

### Cross-reference checks

1. **§5.2 vs §5.3 raise legality:**  
   §5.2: "A raise requires current entitlement, chips beyond the call, and raise_count < max_raises."  
   §5.3: "can_raise[p]" tracks entitlement.  
   **Consistent.** Entitlement is explicit state.

2. **§5.1 pending initialization vs §5.3 rebuild:**  
   §5.1: "pending equal to active seats clockwise after the button"  
   §5.3: "rebuild pending as every other active seat clockwise after the raiser"  
   **Consistent.** Root uses button as reference; raises use raiser.

3. **§5.3 short all-in vs §3 invariant 5:**  
   §5.3: "seats still in old_pending retain their prior entitlement"  
   §3.5: "Folded/all-in seats are not pending."  
   **Consistent.** Short raiser is removed from pending and marked can_raise=False. Old_pending refers to seats *before* the short raise.

4. **§5.2 fold-when-check-possible vs legal_actions:**  
   §5.2: "Folding when checking is possible is not exposed"  
   Phase-3 `legal_actions`: `[Action("CHECK")]` when to_call==0, no FOLD offered.  
   **Consistent.** Specification matches implementation.

5. **§5.3 all-in closure vs §3 invariant 6:**  
   §5.3: "All live all-in seats being non-actionable therefore closes the round."  
   §3.6: "A dealt nonterminal has nonempty pending and acting_player == pending[0]."  
   **Consistent.** When actionable_pending becomes empty (all remaining live seats are all-in), the state terminates.

### Edge case: simultaneous all-in and fold

```
Button=0, N=3, stacks=(10,10,10), pending=(1,2)
P1 RAISE 10 (all-in) → pending=(2,0)
P2 FOLD → pending=(0), live={0,1}
P0 acts: to_call=10, remaining[0]=10
  CALL 10 (all-in) → pending=(), live={0,1}
  Both live, both all-in → terminal ✓
```

**Finding:** None. Specification is internally consistent.

---

## 7. Summary

**Verdict:** PASS

The one-round N-player betting specification (§5 ARCHITECTURE_PHASE4_S2.md) is:

- **Complete:** Initial order, pending management, check/call/fold, full raises, short all-ins, reopening, and closure are fully specified.
- **Consistent:** No contradictions found between §5 and invariants (§3), settlement (§6), or Phase-3 behavior.
- **Deterministic:** Clockwise order, pending rebuild, and entitlement tracking are unambiguous.
- **Bounded:** Depth bound N + max_raises*(N-1) is structurally enforced.

**Clarifications (not findings):**

1. "old_pending" in §5.3 refers to the pending set *before* the short all-in raise is applied.
2. "Seats that had already acted" means seats NOT in old_pending at the time of the short raise.
3. "All live all-in seats being non-actionable" is equivalent to "actionable_pending == []" after filtering for chips.

**Hand traces:** 9 traces covering 3–6 players, checks, folds, calls, full raises, short all-ins, reopening, and closure. All traces are consistent with the specification.

**No specification contradictions found.**
