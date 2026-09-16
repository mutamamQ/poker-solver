# S3 Frozen Design Audit — Model, Positions, Posts, Finite Deals

**Auditor:** A3D1 (non-author)  
**Timestamp:** 2026-09-16 UTC  
**Scope:** `ARCHITECTURE_PHASE4_S3.md` frozen at `fcae1cb6ce9da8b4e4ccb7ef085c223369e76e2be6ead3c5170cd2d41c118a21`  
**Baseline:** `phase3-398-green` → `feba8222a0b614b0c64eca59402403ce733195ea`  
**Production/tests:** No changes during design (verified)  

---

## SHA-256 Verification

```
fcae1cb6ce9da8b4e4ccb7ef085c223369e76e2be6ead3c5170cd2d41c118a21  ARCHITECTURE_PHASE4_S3.md
```

✓ Hash matches `CANDIDATE_MANIFEST.md`.

---

## Implementation Status

**BLOCKING:** No implementation exists.

- `src/poker_solver/nplayer_preflop.py`: **missing**
- `tests/test_nplayer_preflop_config.py`: **missing**
- `tests/test_nplayer_preflop_betting.py`: **missing**
- `tests/test_nplayer_preflop_settlement.py`: **missing**
- `tests/test_nplayer_preflop_information.py`: **missing**
- `tests/test_nplayer_preflop_solve.py`: **missing**
- `tests/test_api_v4_nplayer_preflop.py`: **missing**
- `tests/test_phase4_s3_examples.py`: **missing**
- `tests/test_phase4_s3_exports.py`: **missing**

Architecture specifies 8 additive public symbols (§2.1) and full typed contracts; none are implemented. Audit cannot verify executable acceptance without implementation.

---

## Contradictions and Gaps

### 1. Ante vs Blind Street Commitment (§3 vs `game_structure.py`)

**Architecture (§3, lines 105–106):**
> Antes do not increase `street_committed`; small blind, big blind, and straddle payments do.

**Existing `game_structure.py` (lines 158–182):**
```python
def apply_forced_posts(
    starting_stacks: tuple[int, ...], posts: tuple[ForcedPost, ...]
) -> tuple[SeatLedger, ...]:
    ...
    for post in posts:
        ...
        stacks[post.seat] -= payment
        contributed[post.seat] += payment
    return tuple(
        SeatLedger(
            ...
            street_committed=contributed[seat],  # ← ALL posts, including antes
            total_contributed=contributed[seat],
            ...
        )
        for seat in range(len(stacks))
    )
```

**Contradiction:** Shared ledger helper applies uniform `street_committed=contributed` for all post kinds. S3 requires differential treatment: antes contribute to pot but not to street commitment (which determines live wager and minimum raise).

**Proposed correction:**
- Option A: Extend `apply_forced_posts` with a flag or filter to exclude ante amounts from `street_committed`.
- Option B: Have `nplayer_preflop.py` apply posts directly without the shared helper, implementing the differential logic inline.

---

### 2. N=2 Compatibility Projection (§7, §13 line 287)

**Architecture (§1, lines 7–8):**
> N=2 compatibility is established through projected public traces, not raw type, version, history-record, or information-key equality.

**Acceptance (§13, line 287):**
> N=2 projected deals/actions/ledgers/terminals/information partitions match frozen Phase-3 HU fixtures.

**Gap:** No projection function is defined. Existing `preflop.py` uses:
- `PreflopConfig.version = "holdem-preflop-hu-v1"`
- Information key includes `self.config.version` (line 361)

S3 uses:
- `NPlayerPreflopConfig.version = "nplayer-preflop-v1"` (§2.4, line 66)
- Information key includes `version` (§9, line 202)

When version strings differ, information keys cannot be equal. Architecture says "not raw ... information-key equality" but does not specify the projection mapping.

**Proposed correction:**
- Define explicit projection: "For N=2, strip version prefix and compare remaining key tuples" or
- Relax to: "N=2 compatibility means identical legal actions, ledgers, and terminal values on identical inputs; version and type identity are excluded."

---

### 3. Finite Deals Feasibility (§6, §2.4, §13)

**Architecture (§2.4, line 80):**
> The Cartesian product `prod(len(range_i))` must not exceed `max_deals`; this precheck bounds work even if blockers eliminate every candidate. Compatible deals are never silently truncated.

**Architecture (§6, line 80):**
> No compatible deals, zero exact mass, or candidate product above `max_deals` fails closed.

**Acceptance (§13, line 277):**
> HU, 6-max, and 9-max roots build and solve, return N values, and use exact deterministic chance mass.

**Feasibility issue:**
- Realistic 6-max range: 169 combos/seat (all pairs, suited, offsuit) → 169⁶ ≈ **1.4e13 deals**
- Modest 6-max: 20 combos/seat → 20⁶ = **64M deals**
- Realistic 9-max: 169⁹ ≈ **1.8e19 deals**
- Modest 9-max: 10 combos/seat → 10⁹ = **1B deals**

Architecture provides no abstraction, sampling, or bucketing (all out-of-scope per `PHASE4_MISSION.md` §4). Acceptance requires solving 6-max and 9-max but provides no realistic path under finite enumeration.

**Proposed correction:**
Add explicit acceptance language:
> 6-max and 9-max acceptance examples use small synthetic ranges (total product ≤ `max_deals`, e.g., 3–5 combos/seat) and are not representative of realistic range sizes. Practical large-range multiway solving requires automatic abstraction (S4, out of S3 scope).

---

### 4. Showdown-Ranks Oracle (§2.3, §8, §13 line 282)

**Architecture (§2.3, lines 52, 58):**
> For `showdown-ranks`, every compatible deal has one strict integer rank per seat, larger wins. ... This is a synthetic bounded continuation, not automatic board rollout or equity evaluation.

**Acceptance (§13, line 282):**
> Independent integer/rational oracles match fold, refund, side-pot, tie, odd-chip, terminal-table, and derived-showdown leaves.

**Gap:** How do test authors generate ground-truth showdown ranks for arbitrary 2N-card private deals without equity evaluation, which S3 explicitly disavows?

**Proposed correction:**
- Specify that test fixtures supply ranks as **input data** (not derived from cards), or
- Provide a reference equity evaluator for **test use only** (not production), with clear boundary that S3 production never calls it.

---

### 5. Canonical Positions N=2 (§4, lines 125, existing `preflop.py`)

**Architecture (§4, lines 121–125):**
> For N=2, the button is also SB and acts first preflop; the other seat is BB.
> Canonical labels: `BTN/SB, BB`

**Existing `preflop.py` (lines 400–421):**
```python
def create_preflop_root(config: PreflopConfig) -> PreflopState:
    ...
    return PreflopState(
        ...
        acting_player=CHANCE,  # then seat 0 after deal
        committed=posts,  # posts[0] < posts[1], button=0 posts smaller
        ...
    )
```

Button (seat 0) posts `forced_posts[0]` (smaller, SB) and acts first after deal ✓. Architecture and legacy align on mechanics. Label "BTN/SB" is descriptive, not a type field.

**No contradiction**, but N=2 projection (item 2 above) must clarify version/key mapping.

---

## Missing Executable Acceptance

Architecture §13 lists 18 acceptance criteria (lines 275–291). Without implementation, none are verifiable. Critical missing evidence:

- Typed contract validation (malformed inputs rejected)
- Deterministic deal enumeration and exact Fraction chance mass
- Straddle variant trees (no/standard/double/Mississippi) produce distinct ledgers and first actors
- Sizing-key selection (position, raise_count, cold_callers, IP/OOP relation)
- Full/short all-in pending/reopening rules
- Independent ledger oracles (refund, side-pot, showdown)
- Zero-sum terminals
- Information noninterference (opponent cards, hidden continuation values)
- N=2 projected equivalence with Phase-3 HU fixtures
- v4 API, CLI, examples, exports

---

## Verdict

**FAIL**

### Blocking Issues

1. **No implementation exists.** Cannot verify executable acceptance.
2. **Ante street-commitment contradiction** between architecture (§3) and shared `game_structure.py` helper.
3. **Undefined N=2 projection** when version strings and types differ.
4. **Infeasible finite 6/9-max deal enumeration** without abstraction (out-of-scope).
5. **Showdown-ranks oracle undefined** for test ground-truth generation.

### Recommendations

1. Implement S3-I1 and S3-I2 TDD batches (§12) before re-audit.
2. Resolve ante ledger semantics (extend shared helper or apply posts inline).
3. Define N=2 projection explicitly or relax to behavioral equivalence.
4. Bound 6/9-max acceptance to small synthetic ranges with explicit non-realism disclaimer.
5. Specify showdown-ranks test oracle as input data or reference evaluator (test-only).

---

**End of Report**
