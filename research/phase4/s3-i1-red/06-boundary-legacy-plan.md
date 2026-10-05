# S3-I1 Boundary and Legacy Regression Audit Plan

## Architecture Authority

- **File:** `/home/genomix-node/poker-solver/ARCHITECTURE_PHASE4_S3.md`
- **Hash:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`
- **Design commit:** `65d411793d1d7767d86500d0adffe9f40b379108`
- **Baseline:** `phase3-398-green` at `feba8222a0b614b0c64eca59402403ce733195ea`

## Scope

This S3-I1 plan audits N=2/N=9 boundary validation, invalid type/bool/malformed input rejection, core bounds (`max_deals`, `max_nodes`, `max_raises`), exact deterministic `Fraction` arithmetic, Phase-3 HU projected trace compatibility, immutable config/state contracts, public API non-regression, and baseline tag preservation. Solver-result strategy, metadata, and `max_depth` checks belong to the later S3 solver batch and do not gate this core RED wave.

## Executable Test Commands

### 1. Boundary Validation (N=2, N=9, Invalid Inputs)

**Command:**
```bash
uv run pytest tests/test_nplayer_preflop_config.py -v
```

**Expected Result:**
- All config validation tests pass.
- Strict rejection of:
  - `bool` passed as `int`
  - Wrong tuple lengths for `starting_stacks`, `ranges`, `forced_posts`
  - Malformed card strings
  - `num_players` outside [2, 9]
  - Duplicate combinations within a seat range
  - Nonpositive or nonfinite weights
  - Duplicate sizing-rule keys
  - Invalid forced-post seats or types
  - Cumulative posts exceeding a seat's stack
  - Absent or duplicate SB/BB declarations
  - Unequal, partial, or single-seat antes
  - Non-increasing straddle amounts
  - Unsupported straddle variants
  - Cartesian product exceeding `max_deals`

**Architecture Oracle:**
- Section 2.4: "Validation rejects bool-as-int, wrong tuple lengths, duplicate combinations within a seat, nonpositive/nonfinite weights, malformed cards, duplicate sizing keys, invalid forced-post seats or types, cumulative posts above a seat's stack, absent or duplicate blind declarations, and unsupported straddle arrangements."
- Section 2.4: "Antes are either absent or exactly one identical positive ante is posted by every seat. Unequal/per-seat-partial antes and a single-seat big-blind-ante representation are outside this ledger contract and fail validation."
- Section 2.4: "The Cartesian product `prod(len(range_i))` must not exceed `max_deals`."

---

### 2. Deterministic Fraction Arithmetic

**Command:**
```bash
uv run pytest tests/test_nplayer_preflop_config.py -v
```

**Expected Result:**
- Deal enumeration produces exact `Fraction` masses via `Fraction(str(weight))`.
- Normalized probabilities sum to `1.0` within `1e-12`.
- Repeated enumerations yield identical deal order and masses.

**Architecture Oracle:**
- Section 6: "Convert validated weights with `Fraction(str(weight))`; multiply and normalize exact masses before public float conversion."
- Section 6: "Probabilities are finite, nonnegative, and sum to one within `1e-12`."

**Command:**
```bash
uv run pytest tests/test_nplayer_preflop_settlement.py -v
```

**Expected Result:**
- All terminal utility vectors are exact rationals summing to zero.
- Independent ledger oracles match production fold/refund/side-pot/showdown leaves.

**Architecture Oracle:**
- Section 8: "Every terminal utility vector is an N-tuple of finite exact rationals summing to zero."
- Section 13: "independent integer/rational oracles match fold, refund, side-pot, tie, odd-chip, terminal-table, and derived-showdown leaves."

---

### 3. Max Bounds Enforcement

**Command:**
```bash
uv run pytest tests/test_nplayer_preflop_config.py -v
```

**Expected Result:**
- Config validation fails when Cartesian product `prod(len(range_i))` exceeds `max_deals`.

**Architecture Oracle:**
- Section 2.4: "The Cartesian product `prod(len(range_i))` must not exceed `max_deals`; this precheck bounds work even if blockers eliminate every candidate."

**Command:**
```bash
uv run pytest tests/test_nplayer_preflop_betting.py -v
```

**Expected Result:**
- Betting logic enforces `raise_count < max_raises`.


**Architecture Oracle:**
- Section 7: "A raise requires `can_raise[p]`, chips beyond the call, and `raise_count < max_raises`."


---

### 4. Phase-3 HU Projected Trace Compatibility

**Command:**
```bash
uv run pytest tests/test_nplayer_preflop_information.py -v
```

**Expected Result:**
- N=2 `NPlayerPreflopState` projects to legacy `preflop.py` states via:
  - Aligned deterministic chance outcomes and public action paths.
  - Normalized private deals and exact masses.
  - Acting seat.
  - Ordered legal `Action` tuples.
  - Pot, street commitments, total contributions, remaining stacks, fold status.
  - Exact terminal utilities.
  - Information partition equivalence (not key-byte equality).
- `NPlayerPreflopPublicAction` history projects to ordered `Action` tuple before comparison.
- Version strings, concrete types, actor wrappers excluded from projection.

**Architecture Oracle:**
- Section 1: "The N=2 projection is explicit. Align states by deterministic chance outcome and public action path, then compare: normalized private deals and exact masses; acting seat; ordered legal `Action` tuples; pot, street commitments, total contributions, remaining stacks, and fold status; and exact terminal utilities. Project `NPlayerPreflopPublicAction` history to its ordered `Action` tuple before comparing with legacy history. Information compatibility compares partitions rather than key bytes."
- Section 13: "N=2 projected deals/actions/ledgers/terminals/information partitions match frozen Phase-3 HU fixtures."

---

### 5. Public API Non-Regression

**Commands:**
```bash
# Legacy HU preflop
uv run pytest tests/test_preflop.py -v

# S2 N-player postflop
uv run pytest tests/test_nplayer_postflop_config.py -v
uv run pytest tests/test_nplayer_postflop_betting.py -v
uv run pytest tests/test_nplayer_postflop_settlement.py -v
uv run pytest tests/test_nplayer_postflop_information.py -v
uv run pytest tests/test_nplayer_postflop_solve.py -v

# S1 all-street
uv run pytest tests/test_allstreet_config.py -v
uv run pytest tests/test_allstreet_state.py -v
```

**Expected Result:**
- All legacy tests remain green.
- No public behavior changes in:
  - `preflop.py` (HU)
  - `nplayer_postflop.py` (S2)
  - `allstreet.py` (S1)
  - `nplayer.py` (generic)

**Architecture Oracle:**
- Section 1: "The implementation is additive. Existing heads-up `preflop.py`, S1 all-street postflop, S2 N-player postflop, generic `nplayer.py`, and all legacy APIs keep their public behavior."
- Section 13: "all S1/S2 and legacy tests remain green."

---

### 6. Immutable Core Inputs and States

**Command:**
```bash
uv run pytest tests/test_nplayer_preflop_config.py -v
```

**Expected Result:**
- Nested caller inputs (ranges, sizing rules, continuation tables) are detached at config construction.

**Architecture Oracle:**
- Section 2.4: "Nested caller inputs are detached."
- Section 2.3: "All nested mappings are detached and exposed read-only."

The information suite separately verifies that immutable public states and information keys do not expose mutable continuation mappings. Strategy/result detachment and deterministic solver metadata are deferred to the later S3 solver batch.

---

### 7. Baseline Tag Preservation

**Command:**
```bash
git rev-parse phase3-398-green
```

**Expected Result:**
```
feba8222a0b614b0c64eca59402403ce733195ea
```

**Architecture Oracle:**
- Section 13: "`phase3-398-green` remains exactly at `feba8222a0b614b0c64eca59402403ce733195ea`."

---

## Acceptance Criteria

All seven test groups pass with zero failures. Baseline tag remains at the expected commit. No production modules or in-progress owner tests are inspected or edited.

---

**Status:** `PASS_PLAN/0`
**Architecture hash:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`
**Blockers:** 0
