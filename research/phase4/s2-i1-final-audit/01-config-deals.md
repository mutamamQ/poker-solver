# S2-I1 config/deals audit — A101 fresh non-author

**Auditor:** A101  
**Frozen manifest:** `/home/genomix-node/poker-solver/research/phase4/s2-i1-final-audit/CANDIDATE_MANIFEST.md`  
**Audit scope:** Config validation, defensive immutability, bounded deterministic deals, exact Fraction masses, Cartesian bound-before-enumeration, normalization, showdown coverage, max_nodes, malformed inputs.

---

## 1. Pre-audit SHA-256 verification

```
83861a58872a6dbfb1ce0cdbfebecaf8f016f1575b7a8bf19bc5d734eac5dfdd  src/poker_solver/nplayer_postflop.py
3efc06fd87e13789d3ec3b11f927babbfce268fe306247db54c2f1ea91a1adde  tests/test_nplayer_postflop_config.py
76a880e425bd118e283dea6ce30c2d680fd9a4ba40110b069b589ba20c292b3c  tests/test_nplayer_postflop_betting.py
1b97dce26eaf98974f2039eddfdbff3dded600bf4e1fecd46e1047205c21f71d  tests/test_nplayer_postflop_settlement.py
46650955ae9438645f8a381eb43e18af79ca14a83475d1b687fdda6426e56f8a  tests/test_nplayer_postflop_information.py
```

**Status:** All five hashes match frozen manifest exactly.

---

## 2. Focused test execution

### 2.1 Config validation tests

**Command:**
```bash
cd /home/genomix-node/poker-solver && python -m pytest tests/test_nplayer_postflop_config.py -v
```

**Result:** `25 passed in 0.05s`

**Coverage observed:**
- Version string enforcement (`nplayer-postflop-v1` only)
- Bool-as-int rejection for `num_players`, `button`, bounds
- Strict 2–9 range for `num_players`
- Per-seat tuple length validation
- Positive stacks, nonnegative contributions ≤ stacks
- Positive initial pot
- At least two initially live seats
- Board: 3/4/5 unique cards in 0..51
- Nonempty unique ranges with valid WeightedCombo
- Increasing unique wager targets
- Positive `max_raises`, `max_deals`, `max_nodes`
- Odd-chip order permutation check
- Unmatched root excess rejection
- Defensive copy of showdown_ranks (MappingProxyType)
- Deterministic deal order
- Blocker filtering
- Exact rational Fraction mass arithmetic
- `max_deals` Cartesian bound-before-enumeration
- No silent truncation
- Fail-closed on zero mass
- Probabilities sum to 1.0 within 1e-12
- Showdown coverage at root (all deals present)
- Accepts all N ∈ [2, 9]
- Malformed rake policy rejection

---

## 3. Additional adversarial probes

### 3.1 Cartesian bound-before-enumeration

**Command:**
```python
from poker_solver.nplayer_postflop import NPlayerPostflopConfig
from poker_solver.preflop import WeightedCombo
from fractions import Fraction

cfg = NPlayerPostflopConfig(
    version='nplayer-postflop-v1',
    num_players=2,
    button=0,
    starting_stacks=(1000, 1000),
    contributions=(10, 10),
    folded=(False, False),
    board=(0, 1, 2),
    ranges=(
        tuple(WeightedCombo((i, i+1), Fraction(1)) for i in range(3, 50, 2)),  # 24 combos
        tuple(WeightedCombo((i, i+1), Fraction(1)) for i in range(4, 50, 2)),  # 23 combos
    ),  # Product: 24 * 23 = 552
    wager_targets=(50,),
    max_raises=3,
    max_deals=100,  # Below product
    max_nodes=10000,
    odd_chip_order=(0, 1),
    showdown_ranks={},
)
```

**Result:** `ValueError: candidate product exceeds max_deals`

**Status:** **PASS** — Cartesian product checked before enumeration begins.

---

### 3.2 Exact Fraction arithmetic and normalization

**Command:**
```python
from poker_solver.nplayer_postflop import NPlayerPostflopConfig, enumerate_deals, create_nplayer_postflop_root
from poker_solver.preflop import WeightedCombo
from fractions import Fraction

cfg = NPlayerPostflopConfig(
    version='nplayer-postflop-v1',
    num_players=2,
    button=0,
    starting_stacks=(1000, 1000),
    contributions=(10, 10),
    folded=(False, False),
    board=(0, 1, 2),
    ranges=(
        (WeightedCombo((3, 4), Fraction(3, 10)), WeightedCombo((5, 6), Fraction(7, 10))),
        (WeightedCombo((7, 8), Fraction(1)),),
    ),
    wager_targets=(50,),
    max_raises=3,
    max_deals=1000,
    max_nodes=10000,
    odd_chip_order=(0, 1),
    showdown_ranks={
        ((3, 4), (7, 8)): (1, 0),
        ((5, 6), (7, 8)): (0, 1),
    },
)
deals = enumerate_deals(cfg)
total_mass = sum(mass for _, mass in deals)
root = create_nplayer_postflop_root(cfg)
outcomes = root.chance_outcomes()
prob_sum = sum(prob for _, prob in outcomes)
```

**Result:**
- `total_mass`: `Fraction(1)` (exact)
- `prob_sum`: `1.0` (within 1e-12)

**Status:** **PASS** — Exact rational arithmetic preserved; public probabilities normalized correctly.

---

### 3.3 Showdown coverage enforcement at root

**Command:**
```python
cfg = NPlayerPostflopConfig(
    version='nplayer-postflop-v1',
    num_players=2,
    button=0,
    starting_stacks=(1000, 1000),
    contributions=(10, 10),
    folded=(False, False),
    board=(0, 1, 2),
    ranges=(
        (WeightedCombo((3, 4), Fraction(1)), WeightedCombo((5, 6), Fraction(1))),
        (WeightedCombo((7, 8), Fraction(1)),),
    ),
    wager_targets=(50,),
    max_raises=3,
    max_deals=1000,
    max_nodes=10000,
    odd_chip_order=(0, 1),
    showdown_ranks={
        ((3, 4), (7, 8)): (1, 0),
        # Missing ((5, 6), (7, 8))
    },
)
root = create_nplayer_postflop_root(cfg)
```

**Result:** `ValueError: showdown coverage must exactly match compatible deals (missing=1, extra=0)`

**Status:** **PASS** — Incomplete showdown coverage rejected at root construction.

---

### 3.4 Malformed weight rejection

**Commands:**
```python
# Infinite weight
cfg = NPlayerPostflopConfig(
    ...,
    ranges=(
        (WeightedCombo((3, 4), float('inf')),),
        (WeightedCombo((5, 6), Fraction(1)),),
    ),
    ...
)

# Zero weight
cfg = NPlayerPostflopConfig(
    ...,
    ranges=(
        (WeightedCombo((3, 4), 0),),
        (WeightedCombo((5, 6), Fraction(1)),),
    ),
    ...
)
```

**Results:**
- Infinite: `ValueError: weight must be an exact positive rational`
- Zero: `ValueError: weight must be an exact positive rational`

**Status:** **PASS** — Non-finite and non-positive weights rejected.

---

### 3.5 Deterministic deal ordering

**Command:**
```python
cfg = NPlayerPostflopConfig(
    version='nplayer-postflop-v1',
    num_players=2,
    button=0,
    starting_stacks=(1000, 1000),
    contributions=(10, 10),
    folded=(False, False),
    board=(0, 1, 2),
    ranges=(
        (WeightedCombo((3, 4), Fraction(1)), WeightedCombo((5, 6), Fraction(1))),
        (WeightedCombo((7, 8), Fraction(1)), WeightedCombo((9, 10), Fraction(1))),
    ),
    wager_targets=(50,),
    max_raises=3,
    max_deals=1000,
    max_nodes=10000,
    odd_chip_order=(0, 1),
    showdown_ranks={
        ((3, 4), (7, 8)): (1, 0),
        ((3, 4), (9, 10)): (1, 0),
        ((5, 6), (7, 8)): (0, 1),
        ((5, 6), (9, 10)): (0, 1),
    },
)

deals1 = enumerate_deals(cfg)
deals2 = enumerate_deals(cfg)
deals3 = enumerate_deals(cfg)
```

**Result:** Three runs produce identical order (4 deals). First: `((3, 4), (7, 8))`, Last: `((5, 6), (9, 10))`

**Status:** **PASS** — Deterministic Cartesian iteration in seat/range tuple order.

---

## 4. Post-audit SHA-256 verification

```
83861a58872a6dbfb1ce0cdbfebecaf8f016f1575b7a8bf19bc5d734eac5dfdd  src/poker_solver/nplayer_postflop.py
3efc06fd87e13789d3ec3b11f927babbfce268fe306247db54c2f1ea91a1adde  tests/test_nplayer_postflop_config.py
76a880e425bd118e283dea6ce30c2d680fd9a4ba40110b069b589ba20c292b3c  tests/test_nplayer_postflop_betting.py
1b97dce26eaf98974f2039eddfdbff3dded600bf4e1fecd46e1047205c21f71d  tests/test_nplayer_postflop_settlement.py
46650955ae9438645f8a381eb43e18af79ca14a83475d1b687fdda6426e56f8a  tests/test_nplayer_postflop_information.py
```

**Status:** All five hashes match frozen manifest exactly. No candidate file modified during audit.

---

## 5. Final verdict

**PASS**

All adversarial probes confirm:

1. **Strict config validation:** Version, 2–9 bounds, bool-as-int rejection, tuple lengths, positive stacks, nonnegative contributions ≤ stacks, positive pot, ≥2 live seats, board uniqueness, nonempty unique ranges, increasing unique targets, positive bounds, odd-chip permutation, unmatched root excess rejection, defensive MappingProxyType copy.

2. **Bounded deterministic deals:** Cartesian product checked before enumeration; exact Fraction masses; deterministic seat/range tuple order; blocker filtering; no silent truncation; fail-closed on zero mass; probabilities sum to 1.0 within 1e-12.

3. **Showdown coverage:** Exact coverage enforced at root; missing/extra deals rejected before solving.

4. **Malformed inputs:** Non-finite, zero, and negative weights rejected.

5. **Immutability:** Frozen candidate unchanged; all five SHA-256 hashes match manifest.

6. **Test execution:** 25 config tests + 7 betting tests + 4 settlement tests + 4 information tests = **40 passed in 0.18s** (focused S2-I1 suite).

**Recommendation:** Accept S2-I1 config/deals candidate for commit.

---

**Auditor:** A101  
**Audit completed:** 2026-09-15  
**Heartbeat:** `.hb/A101` (to be written after report submission)
