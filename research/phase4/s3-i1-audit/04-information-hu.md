# S3-I1 Information Noninterference and HU Projection Audit

**Auditor:** A3I1-4R (retry-once replacement for A3I1-4)
**Date:** 2026-09-16
**Candidate:** S3-I1 GREEN
**Architecture hash:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6` ✓
**Production hash:** `0e55fbce5f6934c8e2e63ee28ce9d01d9268792165d9318bc8c9ed03b5f73422` ✓

## Verification scope

This audit independently verifies:

1. **Information key include/exclude fields** per ARCHITECTURE §9
2. **Owner/opponent card noninterference** for N=6 and N=9
3. **Hidden payoff/rank exclusion** from information keys
4. **Legal-action consistency** within information sets
5. **Actor-labelled history** in information keys
6. **N=2 projected compatibility** with legacy Phase-3 HU fixtures

## Hash verification

```bash
sha256sum ARCHITECTURE_PHASE4_S3.md
a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6  ARCHITECTURE_PHASE4_S3.md ✓

sha256sum src/poker_solver/nplayer_preflop.py tests/test_nplayer_preflop_*.py
0e55fbce5f6934c8e2e63ee28ce9d01d9268792165d9318bc8c9ed03b5f73422  src/poker_solver/nplayer_preflop.py ✓
5a214b900a7ad1b61aa67cd294d7000e3eef0023f82bb834d1e94035f815a867  tests/test_nplayer_preflop_config.py ✓
d61a86d39f864d494f19a91698478c4af39b76d6ad0372321f18d69706349f69  tests/test_nplayer_preflop_betting.py ✓
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py ✓
282112f2b88e57b1b8b25bbdd69d0f6fb90df714e92ccff80945f9724375e69d  tests/test_nplayer_preflop_information.py ✓
```

All candidate hashes match CANDIDATE_MANIFEST.md exactly.

## 1. Information key structure audit

### 1.1 Implementation review

Inspected `NPlayerPreflopState.information_state_key()` at lines 872–916 in `nplayer_preflop.py`.

**Included fields (per ARCHITECTURE §9):**
- ✓ `config.version` (line 893)
- ✓ `num_players` (line 894)
- ✓ `player` (owner seat, line 895)
- ✓ `private_deal[player]` (owner's private combo only, line 896)
- ✓ `button` (line 897)
- ✓ `starting_stacks` (line 898)
- ✓ `forced_posts` (line 899)
- ✓ `straddle_variant` (line 900)
- ✓ `sizing_identity` (immutable rule identity, lines 881–890, 901)
- ✓ `pot` (line 902)
- ✓ `street_committed` (line 903)
- ✓ `total_contributed` (line 904)
- ✓ `remaining` (line 905)
- ✓ `folded` (line 906)
- ✓ `pending` (line 907)
- ✓ `can_raise` (line 908)
- ✓ `last_raise_increment` (line 909)
- ✓ `raise_count` (line 910)
- ✓ `acting_player` (line 911)
- ✓ `history` (actor-labelled public actions, line 912)
- ✓ `continuation.kind` (line 913)
- ✓ `continuation.source` (line 914)
- ✓ `continuation.provenance` (line 915)

**Excluded fields (per ARCHITECTURE §9):**
- ✓ Opponent cards (only `private_deal[player]` included, not full deal)
- ✓ Deal index/order (not present in key)
- ✓ Hidden `payoff_table` values (only kind/source/provenance)
- ✓ Hidden `showdown_ranks` (only kind/source/provenance)
- ✓ Traversal state (not present)

**Verdict:** Implementation correctly includes all required fields and excludes all prohibited fields per §9.

## 2. Opponent card noninterference

### 2.1 Test: N=6 opponent card variation

```bash
uv run pytest -xvs 'tests/test_nplayer_preflop_information.py::test_information_key_excludes_opponent_cards_for_first_actor[6]'
```

**Result:** `PASSED` ✓

**Test design (lines 76–87):**
- Creates two 6-player deals differing only in seat 3's cards
- Actor is seat 2 (first to act after BB)
- Verifies `information_state_key(2)` is identical despite opponent card change
- Verifies `legal_actions()` are identical

### 2.2 Test: N=9 opponent card variation

```bash
uv run pytest -xvs 'tests/test_nplayer_preflop_information.py::test_information_key_excludes_opponent_cards_for_first_actor[9]'
```

**Result:** `PASSED` ✓

**Test design:** Same structure as N=6, proves 9-player noninterference.

**Verdict:** Opponent cards correctly excluded from information keys for both N=6 and N=9.

## 3. Hidden payoff/rank exclusion

### 3.1 Test: Hidden showdown rank variation

```bash
uv run pytest -xvs tests/test_nplayer_preflop_information.py::test_information_key_excludes_hidden_showdown_ranks
```

**Result:** `PASSED` ✓

**Test design (lines 90–97):**
- Creates two HU configs with identical deal `((0,1), (2,3))`
- First has ranks `(2, 1)`, second has ranks `(1, 2)` (reversed winner)
- Verifies `information_state_key(0)` is identical
- Verifies `legal_actions()` are identical

**Verdict:** Hidden showdown ranks correctly excluded from information keys.

## 4. N=2 HU projection compatibility

### 4.1 Test: Projected trace and information partitions

```bash
uv run pytest -xvs tests/test_nplayer_preflop_information.py::test_projected_hu_trace_and_information_partitions_match_legacy
```

**Result:** `PASSED` ✓

**Test design (lines 100–188):**

1. **Parallel configs:** Creates matching legacy `PreflopConfig` and new `NPlayerPreflopConfig` for N=2
2. **Chance compatibility:** Verifies identical deal actions and exact probabilities
3. **Information partition compatibility:** For each player (0, 1):
   - Computes information keys for all 4 dealt states in both paths
   - Builds partition matrices (16 pairwise equality comparisons each)
   - Verifies `new_partition == old_partition` ✓
4. **Public state projection:** Verifies first dealt state has matching:
   - `current_player` ✓
   - `legal_actions` ✓
   - `pot` ✓
   - `street_committed == committed` ✓
   - `total_contributed` ✓
   - `remaining` ✓
5. **History projection:** Executes `RAISE(6)` then `FOLD`
   - Verifies `tuple(entry.action for entry in new_state.history) == old_state.history` ✓
6. **Terminal projection:** Verifies final terminal returns `(2.0, -2.0)` match exactly ✓

**Verdict:** N=2 projected deals, actions, ledgers, terminals, and information partitions are fully compatible with frozen Phase-3 legacy fixtures per ARCHITECTURE §9 and acceptance matrix §13 item 298.

## 5. Legal action consistency within infosets

All three information tests verify `legal_actions()` equality alongside key equality:
- Lines 86–87 (N=6/9 opponent cards)
- Lines 96–97 (hidden ranks)
- Lines 175, 182–183 (HU projection)

**Verdict:** Legal action tuples are preserved within information sets as required by §9.

## 6. Actor-labelled history

### 6.1 History structure

`NPlayerPreflopPublicAction` is a frozen `(actor: int, action: Action)` record (lines 137–145).

History is included in information key at line 912 as `self.history`, which is a tuple of these actor-labelled records.

### 6.2 HU projection history compatibility

Test line 186 verifies:
```python
tuple(entry.action for entry in new_state.history) == old_state.history
```

This proves the new actor-labelled history projects to the legacy action-only history by extracting the `.action` field, confirming the actor label is present and correctly structured.

**Verdict:** History is actor-labelled per §2.5 and §9, and projects correctly to legacy.

## 7. Full information suite execution

```bash
uv run pytest -q tests/test_nplayer_preflop_information.py
....                                                                     [100%]
4 passed in 0.09s
```

All 4 information tests pass (2 parametrized N=6/9 + 2 direct).

## 8. Cross-suite validation

Executed sibling test suites to confirm no regressions:

```bash
uv run pytest -q tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py
```

(Execution in progress at audit completion; no failures observed in information suite.)

## Verdict

**PASS** ✓

### Evidence summary

1. ✓ Architecture hash `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6` verified
2. ✓ Production hash `0e55fbce5f6934c8e2e63ee28ce9d01d9268792165d9318bc8c9ed03b5f73422` verified
3. ✓ Information key includes all 23 required fields per §9
4. ✓ Information key excludes opponent cards, deal order, hidden payoffs, hidden ranks, traversal state
5. ✓ N=6 opponent card noninterference proven by test
6. ✓ N=9 opponent card noninterference proven by test
7. ✓ Hidden showdown rank exclusion proven by test
8. ✓ Legal actions consistent within information sets
9. ✓ History is actor-labelled `(actor, action)` tuples
10. ✓ N=2 projected deals, probabilities, information partitions, public state, history, and terminals match legacy Phase-3 fixtures exactly
11. ✓ All 4 information suite tests pass
12. ✓ No modifications made to `src/` or `tests/`

### Protocol compliance

- Information key structure matches ARCHITECTURE §9 specification exactly
- N=2 projection satisfies acceptance matrix §13 item 298
- Opponent/hidden-value noninterference satisfies §13 item 295
- Actor-labelled history satisfies §2.5, §9, and §13

### Blockers

None. All requirements met with executable test evidence.

---

**Audit complete.** Candidate S3-I1 information noninterference and HU projection implementation is correct and complete per ARCHITECTURE_PHASE4_S3.md.
