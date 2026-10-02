# S4 Design: Determinism, Equivalence Classes, and Strategy-Lift Corruption Defenses

**Author:** S4D3 (design-only determinism/equivalence/no-corruption analyst)  
**Status:** COMPLETE_DESIGN  
**Created:** 2026-09-16 UTC  
**Commit baseline:** 149780bf37e3e3a824e03e6d2c1df3cd99b12cd6

---

## Executive Summary

Automatic abstraction (S4) must preserve three invariants:

1. **Determinism:** Same input/seed → same bucketing, same strategy.
2. **Equivalence preservation:** Strategically identical combos remain identical post-abstraction.
3. **No strategy-lift corruption:** Missing/unreachable infosets, weight arithmetic errors, or ID collisions must not silently corrupt lifted strategies.

This document specifies the equivalence relation, threat model, and executable property tests required to enforce these invariants across bucket construction, suit canonicalization, weight arithmetic, collision-free IDs, and strategy lifting.

---

## 1. Threat Model

### 1.1 Determinism Failures

**Sources:**
- Non-deterministic iteration over dicts/sets (Python 3.7+ guarantees dict insertion order, but set iteration is not guaranteed across runs unless seeded).
- Floating-point non-associativity in weight sums (e.g., `sum([a, b, c])` vs. `(a + b) + c` with different orderings).
- Non-reproducible random sampling (unseeded RNG).
- Filesystem/directory traversal order (e.g., `os.listdir()` without sorting).
- Parallel/concurrent operations with race conditions.

**Defenses:**
- Explicit sorting of all combo/bucket/infoset collections before iteration.
- Deterministic weight accumulation (Kahan summation or sorted order + associative grouping).
- Seeded RNG for any sampling (e.g., `random.seed(config.abstraction_seed)`).
- Immutable outputs (frozen dataclasses, tuples).

### 1.2 Equivalence Violations

**Valid equivalences (must preserve):**
- **Suit isomorphism:** On a board with no flush draws, `AsKs` and `AhKh` are strategically identical. Suit relabeling that respects board texture is valid.
- **Rank isomorphism (rare):** On specific boards, certain rank permutations may be equivalent (e.g., on `222` rainbow, `A3` and `A4` are identical if no straights are possible). This is board-specific and fragile; abstraction should NOT assume rank equivalence without explicit proof.

**Invalid merges (must reject):**
- **Blocker effects:** `AsKs` vs. `AhKh` on a board with `Qs Js` (flush draw present) — the first blocks opponent flush draws, the second does not. These are NOT equivalent.
- **Equity cliffs:** Merging `AA` and `KK` preflop (different equity distributions).
- **Different infosets:** Combos that reach different public histories or have different legal actions cannot be merged.

**Defenses:**
- Suit canonicalization must respect board texture (flush draws, made flushes).
- Bucket construction must group only within the same infoset (same `info_key` modulo private cards).
- Metamorphic test: relabel suits in a valid way (e.g., swap clubs/diamonds on a rainbow board), verify bucketing is invariant.
- Negative test: relabel suits in an invalid way (e.g., swap a flush-draw suit with a non-draw suit), verify bucketing changes or raises an error.

### 1.3 Strategy-Lift Corruption

**Sources:**
- **Missing infosets:** Abstracted solve produces strategy for bucket representatives, but lifting to full combos encounters an infoset not covered by any bucket.
- **Unreachable infosets:** Abstraction removes a combo from a bucket, but the lifted strategy still references it.
- **Weight arithmetic errors:** Lifting averages bucket strategies weighted by combo reach, but floating-point errors cause probabilities to not sum to 1.0.
- **ID collisions:** Two distinct buckets hash to the same ID, causing strategy overwrites.

**Defenses:**
- **Coverage check:** Before solving, verify every reachable infoset (from `collect_nplayer_infosets`) is covered by at least one bucket.
- **Collision-free IDs:** Bucket IDs must be deterministic and injective (e.g., `hash(frozenset(canonical_combos))` or sequential assignment with a frozen order).
- **Weight normalization:** After lifting, renormalize action probabilities to sum to 1.0 (with a tolerance check that the error is < 1e-9, else raise).
- **Immutable outputs:** Lifted strategy is a frozen `Mapping[InfoKey, Mapping[Action, float]]` (same as `range_table.py` expects).

---

## 2. Equivalence Relation Specification

### 2.1 Formal Definition

Two combos `c1 = (card_a, card_b)` and `c2 = (card_c, card_d)` are **strategically equivalent** at a public state `s` (board, history, pot, stacks) if and only if:

1. **Same infoset structure:** `s.information_state_key(player)` with `c1` and `c2` differ only in the private-card component (i.e., same board, history, pot, stacks, legal actions).
2. **Suit isomorphism:** There exists a suit permutation `π: {0,1,2,3} → {0,1,2,3}` such that:
   - `π(suit(card_a)) = suit(card_c)` and `π(suit(card_b)) = suit(card_d)` (or vice versa for unordered combos).
   - `π` preserves board texture: if the board has a flush draw in suit `i`, then `π(i)` must also have a flush draw (or be `i` itself).
   - `π` preserves made flushes, straight draws, and pair textures.
3. **Same equity distribution:** `c1` and `c2` have identical equity against all opponent combos (within a tolerance, e.g., 0.001). This is the ground truth; suit isomorphism is a sufficient condition for this on most boards.

**Practical implementation:**
- Suit canonicalization: assign suits a canonical order based on board texture (e.g., flush-draw suits first, then paired suits, then singletons, then off-board suits).
- Rank canonicalization: ranks are NOT generally equivalent; only in degenerate cases (e.g., all ranks dead or board is `AAAA` and remaining cards are all kickers). Default: do NOT merge by rank.

### 2.2 Suit Canonicalization Algorithm

**Input:** Board `b = (c1, c2, ..., cn)`, combo `(card_a, card_b)`.  
**Output:** Canonical combo `(card_a', card_b')` where suits are relabeled.

**Steps:**
1. Count suits on board: `suit_counts = Counter(suit(c) for c in b)`.
2. Identify flush draws: suits with `>= 2` cards on flop, `>= 3` on turn, `== 4` on river (not yet made).
3. Identify made flushes: suits with `>= 5` cards (board + combo).
4. Assign canonical suit order:
   - Flush-draw suits (sorted by count descending, then by suit index ascending).
   - Paired suits (count >= 2, not flush draws).
   - Singleton suits (count == 1).
   - Off-board suits (count == 0).
5. Build permutation `π` mapping actual suits to canonical positions.
6. Apply `π` to combo cards: `(π(suit(card_a)) * 13 + rank(card_a), π(suit(card_b)) * 13 + rank(card_b))`.
7. Return sorted canonical combo.

**Determinism:** Suit order is fully specified (counts, then index); no arbitrary choices.

**Correctness:** Combos with the same canonical form are suit-isomorphic and have identical equity distributions (modulo board texture).

---

## 3. Bucket Construction Requirements

### 3.1 Immutability and Ordering

- **Bucket representation:** `Bucket = frozenset[tuple[int, int]]` (canonical combos, sorted).
- **Bucket ID:** `bucket_id = hash(bucket)` or sequential index from a sorted list of buckets.
- **Bucket collection:** `tuple[Bucket, ...]` (sorted by a deterministic key, e.g., lexicographic order of sorted combos).

### 3.2 Coverage Invariant

**Before solving:**
```python
infosets = collect_nplayer_infosets(root, max_nodes=config.max_nodes)
for info_key, (seat, actions) in infosets.items():
    combos_at_infoset = [combo for combo in config.ranges[seat] if reaches(combo, info_key)]
    covered = any(combo in bucket for bucket in buckets[seat] for combo in combos_at_infoset)
    assert covered, f"Infoset {info_key} has uncovered combos"
```

**Lifted strategy:**
```python
for info_key in infosets:
    for combo in combos_at_infoset:
        bucket = find_bucket(combo, buckets[seat])
        assert bucket is not None, f"Combo {combo} at {info_key} has no bucket"
        lifted_strategy[info_key][combo] = bucket_strategy[bucket_id][info_key]
```

### 3.3 Weight Arithmetic

**Lifting (bucket → combo strategy):**
```python
for action in actions:
    weighted_sum = sum(combo_weight[c] * bucket_strategy[bucket][action] for c in bucket)
    total_weight = sum(combo_weight[c] for c in bucket)
    lifted_strategy[combo][action] = weighted_sum / total_weight

# Normalize
total_prob = sum(lifted_strategy[combo].values())
assert abs(total_prob - 1.0) < 1e-9, f"Probabilities sum to {total_prob}, not 1.0"
for action in actions:
    lifted_strategy[combo][action] /= total_prob
```

**Deterministic summation:** Sort combos/actions before summing to avoid floating-point order dependence.

---

## 4. Reconciliation with Existing Code

### 4.1 `information_state_key` (multistreet.py:439)

**Current:**
```python
return (
    self.config.version,
    player,
    own_cards,  # tuple[int, int], sorted
    self.board,
    public_history,
    self.pot,
    self.committed,
    self.remaining,
    self.config.betting_mode,
)
```

**Abstraction impact:**
- Bucket construction groups combos with the same `info_key` (modulo `own_cards`).
- Canonical `own_cards` (suit-relabeled) can be used as a secondary key for bucketing.
- **No changes required** to `information_state_key` itself; abstraction is a layer above it.

### 4.2 `range_table.py` (build_range_table:103)

**Current:**
- Accepts a `strategy: Mapping[Hashable, Mapping[Action, float]]`.
- Validates that strategy keys match `collect_nplayer_infosets`.
- Groups by `combo = deal[seat]` (line 137).

**Abstraction impact:**
- Lifted strategy must produce the SAME `info_key` format (no changes to keys).
- Lifted strategy must cover ALL combos in the original range (coverage invariant).
- **No changes required** to `range_table.py`; it consumes the lifted strategy as-is.

### 4.3 `ranges.py` (RangeEditor)

**Current:**
- Canonical combo: `(c1, c2) if c1 <= c2 else (c2, c1)` (line 243).
- No suit canonicalization (explicit combos like `AsKs` are distinct from `AhKh`).

**Abstraction impact:**
- Suit canonicalization is ONLY for bucketing, not for range representation.
- `RangeEditor` remains unchanged; abstraction operates on `WeightedCombo` tuples internally.

---

## 5. Executable Property Tests

### 5.1 Determinism Test

**Test:** `test_abstraction_determinism`

```python
def test_abstraction_determinism():
    config = build_test_config(seed=42)
    buckets_1 = build_buckets(config)
    buckets_2 = build_buckets(config)
    assert buckets_1 == buckets_2, "Non-deterministic bucketing"
    
    strategy_1 = solve_abstracted(config, buckets_1, seed=42)
    strategy_2 = solve_abstracted(config, buckets_1, seed=42)
    assert strategy_1 == strategy_2, "Non-deterministic solving"
```

### 5.2 Suit Isomorphism Test (Metamorphic)

**Test:** `test_suit_relabeling_invariance`

```python
def test_suit_relabeling_invariance():
    # Rainbow board (no flush draws)
    board = (0, 5, 10)  # Ac, 2d, 3h
    combo = (1, 6)      # Ad, 2h
    
    # Valid relabeling: swap clubs and spades (both off-board or singleton)
    pi = {0: 3, 1: 1, 2: 2, 3: 0}  # c<->s, d->d, h->h
    relabeled_combo = apply_suit_permutation(combo, pi)
    
    buckets_original = build_buckets(config_with_board(board))
    buckets_relabeled = build_buckets(config_with_board(apply_suit_permutation(board, pi)))
    
    # Buckets should be isomorphic (same structure, relabeled combos)
    assert buckets_are_isomorphic(buckets_original, buckets_relabeled, pi)
```

### 5.3 Blocker Counterexample Test (Negative)

**Test:** `test_flush_draw_blocker_distinction`

```python
def test_flush_draw_blocker_distinction():
    # Board with flush draw
    board = (0, 4, 8)   # Ac, Cc, 3c (three clubs)
    combo_blocker = (12, 16)    # 4c, 5c (blocks club flush)
    combo_no_blocker = (13, 17) # 4d, 5d (does not block)
    
    buckets = build_buckets(config_with_board(board))
    
    # These combos must NOT be in the same bucket
    bucket_blocker = find_bucket(combo_blocker, buckets)
    bucket_no_blocker = find_bucket(combo_no_blocker, buckets)
    assert bucket_blocker != bucket_no_blocker, "Blocker effect ignored"
```

### 5.4 Coverage Test

**Test:** `test_abstraction_coverage`

```python
def test_abstraction_coverage():
    config = build_test_config()
    root = create_root(config)
    buckets = build_buckets(config)
    infosets = collect_nplayer_infosets(root, max_nodes=config.max_nodes)
    
    for info_key, (seat, actions) in infosets.items():
        combos_at_infoset = get_combos_reaching(info_key, config.ranges[seat])
        for combo in combos_at_infoset:
            bucket = find_bucket(combo, buckets[seat])
            assert bucket is not None, f"Uncovered combo {combo} at {info_key}"
```

### 5.5 Strategy-Lift Integrity Test

**Test:** `test_lifted_strategy_validity`

```python
def test_lifted_strategy_validity():
    config = build_test_config()
    buckets = build_buckets(config)
    bucket_strategy = solve_abstracted(config, buckets, seed=42)
    lifted_strategy = lift_strategy(bucket_strategy, buckets, config)
    
    # Validate against range_table expectations
    root = create_root(config)
    infosets = collect_nplayer_infosets(root, max_nodes=config.max_nodes)
    
    assert set(lifted_strategy.keys()) == set(infosets.keys()), "Missing/extra infosets"
    
    for info_key, (seat, actions) in infosets.items():
        policy = lifted_strategy[info_key]
        assert set(policy.keys()) == set(actions), f"Action mismatch at {info_key}"
        total_prob = sum(policy.values())
        assert abs(total_prob - 1.0) < 1e-9, f"Probabilities sum to {total_prob} at {info_key}"
        for prob in policy.values():
            assert 0 <= prob <= 1, f"Invalid probability {prob}"
```

### 5.6 Collision-Free ID Test

**Test:** `test_bucket_id_uniqueness`

```python
def test_bucket_id_uniqueness():
    config = build_test_config()
    buckets = build_buckets(config)
    ids = [bucket_id(b) for b in buckets]
    assert len(ids) == len(set(ids)), "Bucket ID collision detected"
```

---

## 6. Design Decisions and Open Questions

### 6.1 Abstraction Granularity

**Decision required (implementation wave):**
- **Coarse (category-based):** Group by hand strength category (e.g., `FLUSH`, `TWO_PAIR`) + kicker bins. Fast, large buckets.
- **Fine (equity-based):** Cluster by equity distribution against opponent range. Slower, smaller buckets, higher fidelity.

**Recommendation:** Start with category-based (simpler, deterministic), add equity-based as an option later.

### 6.2 Suit Canonicalization Edge Cases

**Q:** On a board like `As Ks Qs` (three spades), how do we canonicalize `Ah Kh` vs. `Ac Kc`?  
**A:** Both are off the flush draw (hearts and clubs are equivalent). Canonical order: spades (flush draw) > hearts/clubs/diamonds (off-draw, sorted by index). `Ah Kh` and `Ac Kc` map to the same canonical form (e.g., suit 1 and suit 2 in the canonical order).

**Q:** What about `Js Ts` (on the flush draw) vs. `Jh Th` (off the draw)?  
**A:** These are NOT equivalent (blocker effect). `Js Ts` canonicalizes with spades in position 0 (flush-draw suit), `Jh Th` with hearts in position 1 (off-draw). Different canonical forms → different buckets.

### 6.3 Rank Equivalence

**Decision:** Do NOT merge by rank in the initial implementation. Rank equivalence is rare and board-specific (e.g., on `222` rainbow, `A3` and `A4` are identical only if no straights are possible). This requires complex analysis and is error-prone. Suit canonicalization alone provides sufficient abstraction for tractability.

---

## 7. Implementation Checklist (for S4 implementation wave)

- [ ] Implement `canonicalize_suit(board, combo) -> tuple[int, int]` (deterministic, respects flush draws).
- [ ] Implement `build_buckets(config) -> tuple[Bucket, ...]` (deterministic, sorted, immutable).
- [ ] Implement `bucket_id(bucket) -> Hashable` (collision-free, deterministic).
- [ ] Implement `solve_abstracted(config, buckets, seed) -> Mapping[BucketID, Mapping[InfoKey, Mapping[Action, float]]]`.
- [ ] Implement `lift_strategy(bucket_strategy, buckets, config) -> Mapping[InfoKey, Mapping[Action, float]]` (normalized, coverage-checked).
- [ ] Add `abstraction_policy` field to config (e.g., `"category-based"`, `"equity-based"`, `"none"`).
- [ ] Add `abstraction_seed` field to config (for deterministic RNG).
- [ ] Write all six property tests (determinism, suit isomorphism, blocker counterexample, coverage, lift integrity, ID uniqueness).
- [ ] Document abstraction policy in `docs/ABSTRACTION.md`.
- [ ] Verify `range_table.py` consumes lifted strategy without changes.

---

## 8. Acceptance Criteria (from PHASE4_MISSION.md S4)

- [x] **Design complete:** Abstraction policy explicit (category-based recommended).
- [x] **Determinism specified:** Same input/seed → same buckets, same strategy.
- [x] **Equivalence relation defined:** Suit isomorphism with board-texture respect; rank equivalence excluded.
- [x] **Corruption defenses specified:** Coverage check, collision-free IDs, weight normalization, immutable outputs.
- [x] **Property tests specified:** Six executable tests (determinism, metamorphic, negative, coverage, lift integrity, ID uniqueness).
- [x] **Reconciliation with existing code:** No changes required to `information_state_key`, `range_table.py`, or `ranges.py`.

**Status:** COMPLETE_DESIGN. Ready for implementation wave (S4I1–S4I6).

---

## 9. References

- `multistreet.py:439` — `information_state_key` definition.
- `range_table.py:47` — `_validate_strategy` contract.
- `ranges.py:243` — `_canonical_combo` (card-level, not suit-level).
- `evaluator.py` — Hand strength categories (used for category-based abstraction).
- PHASE4_MISSION.md S4 — Acceptance criteria.

---

**Document hash (for heartbeat):** `sha256:` (to be computed on write)
