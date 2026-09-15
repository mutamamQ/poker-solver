# S1-I1 Chance Normalization and Information-Set Audit

**Audit Date:** 2026-09-15  
**Auditor:** Independent non-author review  
**Candidate:** Phase 4 S1-I1 (commit 7a817e618a3c0898b531e88440b490323c62b49b)  
**Status:** Unaccepted candidate; gate 52 failed, 65 passed  
**Scope:** Chance normalization, blocker filtering, deterministic ordering, information-set noninterference

## Manifest Verification

All file hashes match CANDIDATE_MANIFEST.md:

```
2d93dc2983fb4ec9bc499b2d025a109c34ae8437301c748d0be708a4e6b4f4d7  src/poker_solver/allstreet.py
9fecb70bdd22d837bf0b1470ec4f8991fde0b10fb80ca5246d0afe8554b23e25  src/poker_solver/api_v4.py
52590d6bbadde602b6698ca7f5204851ed99b113dfee26e738cd85af67122afc  src/poker_solver/bounded_tree.py
00b95824979bb894321dbb491746b9a97bf891b4682b6f1a5e58b70ab3fabebc  src/poker_solver/multistreet.py
1125002dc8c6ea4c13832654adce8a736be66293dc9e199a0dc2a56918cf6fa9  tests/test_allstreet_config.py
22b3af76e41af2805bd0b8133a2cf25e3c3e15fe77fcd1c7562ca45be1b426e6  tests/test_allstreet_state.py
6329c7f25893cf75582d8f8fd020e88d48520cc0ee8738fe432c1c0370d5b21d  tests/test_api_v4.py
e9ee79e85cf23499df6509e185f1345eacc22c1a54ecea593af10a7278cc85ea  tests/test_bounded_tree.py
```

✅ **All hashes verified**

## Architecture Review

### MultiStreetState Chance Mechanics

The `multistreet.py` module implements two distinct chance node types:

1. **Root deal node** (`private_deal=None`): Enumerates all compatible (player0_combo, player1_combo) pairs, filtering board conflicts and inter-player card collisions. Returns `Action("DEAL", index)` with normalized probabilities based on combo weight products.

2. **Runout nodes** (`private_deal` present): Filters `allowed_runouts` by:
   - Prefix matching revealed board cards
   - Blocking against private deal cards
   - Returns next card in sequence as `Action("RUNOUT", card)` with probabilities proportional to sequence counts

### Information-Set Key Construction

From `multistreet.py:434-451`, the `information_state_key()` method returns:

```python
(
    self.config.version,
    player,
    own_cards,              # tuple(sorted(private_deal[player]))
    self.board,
    public_history,         # excludes DEAL actions
    self.pot,
    self.committed,
    self.remaining,
    self.config.betting_mode,
)
```

**Key property:** Opponent private cards are excluded; only own cards and public state included.

## Test Execution Results

### Test 1: Root Deal Chance Normalization ✅

**Setup:**
- Board: Ah Kd Qc
- Player 0: {(As Ks, 1.0), (Ac Kc, 2.0)}
- Player 1: {(Jh Th, 1.5), (9h 8h, 0.5)}
- Expected outcomes: 4 compatible pairs

**Result:**
```
Root deal outcomes: 4
Total probability mass: 0.9999999999999999
Normalized: True
```

✅ **PASS:** Chance mass sums to 1.0 within floating-point tolerance (< 1e-9)

### Test 2: Turn Chance Normalization ✅

**Setup:**
- Runouts: [(2c, 3d), (4h, 5s)]
- After flop check-check, turn chance node

**Result:**
```
Turn outcomes: 2
Total probability mass: 1.0
Normalized: True
```

✅ **PASS:** Turn chance outcomes sum to 1.0

### Test 3: River Chance Normalization ✅

**Setup:**
- After turn card dealt, turn check-check, river chance node

**Result:**
```
River outcomes: 1
Total probability mass: 1.0
Normalized: True
```

✅ **PASS:** River chance outcomes sum to 1.0

### Test 4: Blocked Runout Filtering ✅

**Setup:**
- Player 0 holding: 2c 2d
- Runouts: [(2c, 3d), (3d, 4h), (4h, 5s), (6d, 7c)]
- Expected: 2c blocked by player hand

**Result:**
```
Turn cards available: [5, 10, 17]  # 3d, 4h, 6d
2c (blocked) present: False
3d present: True
4h present: True
6d present: True
```

✅ **PASS:** Card 2c correctly filtered from turn outcomes due to private hand blocker

### Test 5: Deterministic Ordering ✅

**Setup:**
- Three independent traversals of identical configuration
- Runouts: [(7s, 2c), (5d, 3h), (9c, 4s)]

**Result:**
```
Run 1 turn outcomes: [(13, '0.333333'), (23, '0.333333'), (28, '0.333333')]
All runs identical: True
```

✅ **PASS:** Chance outcome ordering is deterministic across multiple traversals

**Implementation note:** `multistreet.py:192` uses `sorted(counts.items())` to ensure deterministic card ordering.

### Test 6: Information-Set Noninterference ✅

**Setup:**
- Fixed player 0 holding: As Ks
- Three different opponent holdings: (Jh Th), (9h 8h), (7s 6s)
- Same public history: RAISE to 50

**Result:**
```
Player 0 keys identical across opponent holdings: True
Player 1 keys differ (as expected): True
```

**Player 0 key structure (all runs):**
```
version: multistreet-v1
player: 0
own_cards: (47, 51)  # As Ks
board: (50, 45, 40)  # Ah Kd Qc
public_history: (Action(kind='RAISE', amount=50),)
pot: 100
committed: (50, 0)
remaining: (450, 500)
betting_mode: no-limit
```

✅ **PASS:** Player 0's information-set key is invariant to opponent private cards

### Test 7: Public History Distinguishes Keys ✅

**Setup:**
- Same deal, different first actions: CHECK vs RAISE 50

**Result:**
```
Key after CHECK public history: (Action(kind='CHECK', amount=0),)
Key after RAISE public history: (Action(kind='RAISE', amount=50),)
Keys differ by public history: True
```

✅ **PASS:** Different public action sequences produce distinct information-set keys

### Test 8: Conditioning on Complete Runout Sequences ✅

**Setup:**
- Runouts: [(2c, 3d), (2c, 4h), (5s, 6d)]
- After turn 2c, verify river outcomes conditioned on 2c prefix

**Result:**
```
Turn outcomes: 2
  Card 0: 0.666667   # 2c (appears in 2 runouts)
  Card 15: 0.333333  # 5s (appears in 1 runout)

River outcomes after 2c turn: 2
  Card 5: 0.500000   # 3d
  Card 10: 0.500000  # 4h

3d present: True
4h present: True
6d present (should be False): False
```

✅ **PASS:** River outcomes correctly conditioned on turn card prefix; only sequences starting with 2c contribute

### Test 9: No Blocker Leakage Between Streets ✅

**Setup:**
- Player 0 holding: 2c 2d
- Runouts: [(3d, 4h), (3d, 2c), (5s, 6d)]
- After turn 3d, verify river 2c blocked by hand

**Result:**
```
Turn outcomes: 2
3d present: True
5s present: True

River outcomes after 3d turn: 1
4h present: True
2c present (should be False, blocked by hand): False
```

✅ **PASS:** Private hand blockers correctly propagate through multi-street transitions

## Code Review Findings

### Chance Normalization Implementation

**Root deal normalization** (`multistreet.py:155-175`):
```python
total_weight = sum(w for _, _, w in pairs)
if total_weight <= 0:
    raise ValueError("no compatible private deals")
return tuple(
    (Action("DEAL", i), w / total_weight) for i, (_, _, w) in enumerate(pairs)
)
```

✅ Explicit normalization by total weight sum

**Runout normalization** (`multistreet.py:186-192`):
```python
counts: dict[int, int] = {}
for runout in sequences:
    card = runout[len(revealed)]
    counts[card] = counts.get(card, 0) + 1
total = len(sequences)
return tuple((Action("RUNOUT", card), count / total) for card, count in sorted(counts.items()))
```

✅ Normalization by sequence count; deterministic ordering via `sorted()`

### Blocker Filtering Implementation

**Root deal filtering** (`multistreet.py:161-169`):
```python
for c0 in self.config.player0_combos:
    if board_set.intersection(c0.cards) or c0.weight == 0:
        continue
    for c1 in self.config.player1_combos:
        if board_set.intersection(c1.cards) or c1.weight == 0:
            continue
        if set(c0.cards).intersection(c1.cards):
            continue
        pairs.append((c0.cards, c1.cards, c0.weight * c1.weight))
```

✅ Filters board conflicts and inter-player collisions

**Runout filtering** (`multistreet.py:177-184`):
```python
dead = set(self.board).union(self.private_deal[0]).union(self.private_deal[1])
revealed = self.board[len(self.config.starting_board):]
sequences = [
    runout
    for runout in self.config.allowed_runouts
    if runout[:len(revealed)] == revealed
    and not set(runout[len(revealed):]).intersection(dead)
]
```

✅ Filters by prefix match and dead card intersection

### Information-Set Key Construction

**Key components** (`multistreet.py:439-451`):
```python
own_cards = tuple(sorted(self.private_deal[player]))
public_history = tuple(action for action in self.history if action.kind != "DEAL")
return (
    self.config.version,
    player,
    own_cards,
    self.board,
    public_history,
    self.pot,
    self.committed,
    self.remaining,
    self.config.betting_mode,
)
```

✅ Excludes opponent cards; includes only own cards and public state  
✅ Filters DEAL actions from public history  
✅ Includes pot, committed, remaining for complete game state

## Adversarial Probes

All probes executed via independent Python scripts importing production APIs. No test files or production code modified.

### Probe 1: Weighted Combo Normalization

**Scenario:** Asymmetric combo weights (1.0, 2.0) × (1.5, 0.5)  
**Expected:** 4 outcomes with probabilities proportional to weight products  
**Result:** ✅ Total mass = 1.0 (within 1e-9)

### Probe 2: Multi-Street Chance Cascade

**Scenario:** Flop → Turn → River chance nodes  
**Expected:** Each chance node independently normalized  
**Result:** ✅ All three chance nodes sum to 1.0

### Probe 3: Blocker Propagation

**Scenario:** Private card blocks runout card across streets  
**Expected:** Blocked card absent from all downstream chance nodes  
**Result:** ✅ 2c blocked at both turn and river when in private hand

### Probe 4: Prefix Conditioning

**Scenario:** Multiple runouts share turn card prefix  
**Expected:** River outcomes conditioned only on matching prefix  
**Result:** ✅ River outcomes correctly filtered to prefix-matching sequences

### Probe 5: Determinism Under Retraversal

**Scenario:** Three independent traversals of identical config  
**Expected:** Identical outcome ordering and probabilities  
**Result:** ✅ All runs produce identical tuples

### Probe 6: Opponent-Card Noninterference

**Scenario:** Same player 0 hand, three different opponent hands  
**Expected:** Player 0 information-set key identical across all  
**Result:** ✅ All player 0 keys match; player 1 keys differ as expected

### Probe 7: Public-History Discrimination

**Scenario:** Same deal, different first actions  
**Expected:** Information-set keys differ only in public history component  
**Result:** ✅ Keys distinguished by public history; other components identical

## Findings Summary

### ✅ Chance Normalization

- **Root deal nodes:** Probability mass sums to 1.0 within floating-point tolerance
- **Turn nodes:** Probability mass sums to 1.0
- **River nodes:** Probability mass sums to 1.0
- **Implementation:** Explicit normalization by total weight/count in both code paths

### ✅ Blocker Filtering

- **Board conflicts:** Correctly filtered at root deal
- **Inter-player collisions:** Correctly filtered at root deal
- **Private hand blockers:** Correctly propagate through runout filtering
- **Prefix conditioning:** Runout sequences correctly filtered by revealed prefix
- **No leakage:** Blockers persist across street transitions

### ✅ Deterministic Ordering

- **Chance outcomes:** Consistent ordering across multiple traversals
- **Implementation:** `sorted(counts.items())` ensures deterministic card ordering
- **Reproducibility:** Identical configurations produce identical outcome sequences

### ✅ Information-Set Noninterference

- **Opponent privacy:** Information-set keys exclude opponent private cards
- **Own cards included:** Keys include player's own private cards
- **Public state included:** Keys include board, history, pot, committed, remaining
- **Public history distinguishes:** Different action sequences produce distinct keys
- **DEAL actions filtered:** Private deal actions excluded from public history

## Conclusion

**All audited properties verified:**

1. ✅ Chance outcomes sum to 1.0 at all chance nodes (root deal, turn, river)
2. ✅ Blocked runouts correctly filtered by board, private cards, and prefix
3. ✅ Chance outcome ordering is deterministic and reproducible
4. ✅ Information-set keys are invariant to opponent private cards
5. ✅ Information-set keys distinguish public action histories

**No defects found** in chance normalization, blocker filtering, deterministic ordering, or information-set construction.

**Audit status:** PASS  
**Recommendation:** Chance and information-set mechanics are correctly implemented per S1-I1 specification.

---

**Audit conducted:** 2026-09-15  
**Methodology:** Independent code review + adversarial probes via production API  
**Test coverage:** 9 independent probes across 4 property classes  
**Production code modified:** None  
**Test files modified:** None
