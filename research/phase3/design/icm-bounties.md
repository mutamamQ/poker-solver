# Phase 3 ICM and bounty implementation design

## 1. Scope and correctness claim

This design specifies a bounded, correct implementation of Independent Chip Model (ICM) equity evaluation and immediate bounty accounting for small-field tournaments. It is a utility evaluator and accounting engine, not a full tournament strategy solver.

**Implemented exactly:**
- Standalone ICM equity evaluator for positive stacks and nonincreasing nonnegative placement payouts
- Immediate bounty transition accounting for KO/PKO/TKO/Mystery formats with explicit rules
- One-hand terminal utility integration: `post_ICM - pre_ICM + immediate_bounty_cash`

**Documented boundaries:**
- Full-field optimal PKO/TKO/Mystery strategy solving
- GTO Wizard neural future-bounty EV parity
- Future Game Simulation and continuation models
- Unrestricted postflop/preflop ICM strategy solving
- Site-specific hidden Mystery-bounty assignment rules

Research basis: `research/phase3/icm-bounties.md` contains verified sources, exact ICM fixtures, bounty conservation tests, and the implemented-versus-boundary matrix.

## 2. Module ownership and dependencies

**New modules:**
- `src/poker_solver/icm.py`: ICM equity evaluator (subset-DP algorithm, Fraction oracle)
- `src/poker_solver/bounty.py`: Bounty transition accounting and format rules
- `src/poker_solver/tournament.py`: One-hand tournament utility integration
- `tests/test_icm.py`: ICM tests (permutation oracle, fixtures, conservation)
- `tests/test_bounty.py`: Bounty accounting tests (KO/PKO/TKO/Mystery, conservation)
- `tests/test_tournament.py`: One-hand integration tests

**Dependencies:**
- `fractions.Fraction` for exact test oracles
- No external dependencies; pure Python standard library
- API integration via `src/poker_solver/api.py` (new endpoints)
- CLI integration via `src/poker_solver/cli.py` (new subcommands)

**Dependency graph:**
```
    icm.py  <--- tournament.py
       ^            ^
       |            |
    bounty.py ------+
       ^
       |
    api.py, cli.py
```

## 3. ICM equity evaluator (`icm.py`)

### 3.1 Algorithm and correctness

**ICM definition:**
For `N` remaining players with positive stacks `s_i` and total `S = sum(s_i)`, first-place probability is `P(i first) = s_i / S`. Conditioned on player `i` taking first, remove `i` and recurse. For complete finish order `(i1,...,in)`:

```
P(order) = product_{k=1..n} s_ik / (S - sum_{j<k} s_ij)
```

Player `i`'s equity is `sum over finish places k of P(i finishes k) * payout_k`.

**Assumptions:**
- Equal skill and future opportunity
- Stack-only finish chances (no position, blind growth, or strategic dynamics)
- Fixed payout schedule
- Zero-sum among remaining payouts

**Production algorithm:**
Subset dynamic programming over eliminated/placed-player masks and paid positions, with deterministic player order. Equivalent remaining-stack totals are reused. Time and memory bounds are measured from actual mask/state count.

**Independent oracle:**
Permutation enumeration using `fractions.Fraction` for exact rational arithmetic. This is the test oracle for small `n`, not the production algorithm.

### 3.2 API contract

```python
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True, slots=True)
class ICMResult:
    """ICM equity evaluation result."""
    equities: tuple[float, ...]  # One per player, sums to payout pool
    finish_probabilities: tuple[tuple[float, ...], ...]  # [player][place]
    algorithm: str  # "subset-dp" or "permutation-oracle"
    metadata: dict[str, Any]

def compute_icm(
    stacks: Sequence[float],
    payouts: Sequence[float],
    *,
    algorithm: str = "subset-dp",
) -> ICMResult:
    """Compute ICM equity for positive stacks and nonincreasing payouts.
    
    Args:
        stacks: Positive stack sizes (length N >= 2)
        payouts: Nonincreasing nonnegative placement prizes (length <= N)
        algorithm: "subset-dp" (default) or "permutation-oracle" (tests only)
    
    Returns:
        ICMResult with equities and finish probabilities
    
    Raises:
        ValueError: Invalid input (non-positive stack, negative payout,
                    increasing payouts, zero total stack, too many payouts)
    """
```

**Validation:**
- Reject booleans, NaN, infinity
- Reject non-positive stacks, negative payouts
- Reject increasing payouts: `payouts[i] < payouts[i-1]` for any `i > 0`
- Reject zero total stack
- Reject `len(payouts) > len(stacks)`
- Busted players (zero stack) must be excluded before calling; core evaluator requires strictly positive stacks

**Numerical precision:**
- Production uses `float` arithmetic
- Test oracle uses `fractions.Fraction`
- Agreement tolerance: `1e-12` absolute error
- Equity sum must equal payout pool sum within `1e-12`

### 3.3 Exact ICM fixtures

From `research/phase3/icm-bounties.md`, parent-generated via independent permutation enumeration:

1. **Equal stacks, winner-take-all:**
   - Stacks: `(1, 1)`, Payouts: `(100, 0)`
   - Equities: `(50, 50)`

2. **Equal stacks, three-way:**
   - Stacks: `(1, 1, 1)`, Payouts: `(100, 60, 30)`
   - Equities: `(190/3, 190/3, 190/3)` = `(63.333..., 63.333..., 63.333...)`
   - Total: `190`

3. **Unequal stacks, two paid:**
   - Stacks: `(50, 30, 20)`, Payouts: `(100, 60, 0)`
   - Equities: `(985/14, 105/2, 260/7)` ≈ `(70.357142857, 52.5, 37.142857143)`
   - Total: `160`

4. **Chip leader advantage:**
   - Stacks: `(2, 1, 1)`, Payouts: `(100, 60, 20)`
   - Equities: `(220/3, 160/3, 160/3)` ≈ `(73.333..., 53.333..., 53.333...)`
   - Total: `180`

**Invariant tests:**
- Equal stacks → equal equities
- Seat permutation only permutes output
- Common stack scaling (multiply all stacks by constant `c > 0`) leaves equities unchanged
- Equities sum to payout pool within `1e-12`

### 3.4 Complexity limits

The architectural input limit is measured and tested, not assumed. Subset-DP state count grows with `2^N * len(payouts)`. Document the measured limit (e.g., `N <= 10` for typical payout structures) and fail explicitly when exceeded.

```python
MAX_ICM_PLAYERS = 10  # Measured limit for subset-DP
MAX_ICM_PAYOUTS = 10  # Measured limit for subset-DP
```

Oversized inputs fail with:
```python
raise ValueError(f"ICM input exceeds limit: {len(stacks)} players, {len(payouts)} payouts")
```

## 4. Bounty accounting (`bounty.py`)

### 4.1 Bounty formats and rules

All monetary quantities are nonnegative finite values in one declared currency unit. Integer minor units (cents) are preferred to avoid floating-point rounding.

**Standard knockout (KO/SKO):**
- Eliminated player's current bounty is paid immediately to declared recipient(s)
- Regular placement prize pool remains separate
- Recipient shares are explicit and sum to one

**Progressive knockout (PKO):**
- For eliminated player bounty `b` and configured immediate fraction `f ∈ [0,1]`:
  - `f * b` is immediate cash split by declared recipient shares
  - `(1-f) * b` is added to recipients' bounty heads using the same shares
  - Eliminated player's bounty becomes zero
- Many events use `f = 0.5`, but this is NOT hard-coded
- Winner self-bounty treatment is an explicit terminal rule

**Total knockout (TKO):**
- Regular placement payout vector is empty/zero
- Tournament value is allocated through bounties
- TKO is an economic format flag; bounty transfer mechanics (standard vs progressive) must be explicit

**Mystery bounty:**
- Random award drawn from explicitly supplied finite distribution or remaining multiset
- Two bounded modes:
  - `expected-value`: immediate award is exact distribution mean
  - `enumerated-chance`: create one chance outcome per distinct award with exact probability; update remaining multiset for draws without replacement
- No external probability library needed
- Full hidden-assignment tournament dynamics are a boundary

### 4.2 API contract

```python
from dataclasses import dataclass
from typing import Literal, Sequence

@dataclass(frozen=True, slots=True)
class BountyState:
    """Current bounty state for all players."""
    heads: tuple[float, ...]  # Current bounty on each player's head
    mystery_pool: tuple[float, ...] | None  # Remaining Mystery awards (if applicable)

@dataclass(frozen=True, slots=True)
class BountyTransition:
    """Result of a bounty transition (elimination accounting)."""
    immediate_cash: tuple[float, ...]  # Cash awarded to each player
    next_state: BountyState  # Updated bounty state
    metadata: dict[str, Any]

def apply_bounty_transition(
    current_state: BountyState,
    eliminations: Sequence[tuple[int, Sequence[tuple[int, float]]]],
    format_rule: Literal["ko", "pko", "mystery"],
    *,
    pko_immediate_fraction: float | None = None,
    mystery_mode: Literal["expected-value", "enumerated-chance"] | None = None,
) -> BountyTransition:
    """Apply bounty accounting for one or more eliminations.
    
    Args:
        current_state: Current bounty state
        eliminations: List of (eliminated_player, [(recipient, share), ...])
                      Shares must sum to 1.0 for each elimination
        format_rule: "ko" (standard), "pko" (progressive), or "mystery"
        pko_immediate_fraction: Required for "pko"; fraction paid immediately
        mystery_mode: Required for "mystery"; "expected-value" or "enumerated-chance"
    
    Returns:
        BountyTransition with immediate cash and updated state
    
    Raises:
        ValueError: Invalid input (shares don't sum to 1, missing required params,
                    duplicate eliminations, invalid player indices)
    """
```

**Validation:**
- Reject booleans, NaN, infinity
- Reject negative bounties, cash, or shares
- Reject shares that don't sum to `1.0` within `1e-9`
- Reject duplicate eliminations
- Reject invalid player indices
- Reject missing `pko_immediate_fraction` for PKO
- Reject missing `mystery_mode` for Mystery
- Reject `pko_immediate_fraction` outside `[0, 1]`

### 4.3 Bounty conservation fixtures

From `research/phase3/icm-bounties.md`:

1. **KO single recipient:**
   - Bounty: `100`, one recipient
   - Immediate cash: `100`, eliminated head: `0`
   - Conservation: total bounty/cash value conserved

2. **KO split (odd units):**
   - Bounty: `101`, shares `(0.5, 0.5)` with integer minor units
   - Requires explicit odd-unit recipient; no floating loss

3. **PKO half example:**
   - `b = 80`, `f = 0.5`
   - Immediate cash: `40`, recipient head increase: `40`

4. **PKO configurable:**
   - `b = 100`, `f = 0.25`, shares `(0.75, 0.25)`
   - Total immediate cash: `25`, head increases: `75` (apportioned by shares)

5. **PKO winner self-bounty:**
   - Winner-self-bounty unlock applied only when explicit
   - Otherwise no implicit final cash

6. **TKO:**
   - Zero placement payouts plus KO awards
   - Total declared tournament value equals cumulative bounty cash plus live bounty heads

7. **Mystery mean:**
   - Awards `(10, 10, 80)` with equal probabilities
   - Expected award: `100/3` ≈ `33.333...`
   - Exact `Fraction` oracle and `float` differ by at most `1e-12`

8. **Mystery without replacement:**
   - After drawing `80`, remaining distribution: `(10, 10)` with mean `10`
   - Probabilities and value conserved exactly

9. **Multiple eliminations:**
   - Each eliminated player maps to independently validated recipient-share vector
   - No bounty awarded twice

**Conservation test:**
```python
total_value_before = sum(current_state.heads) + sum(mystery_pool or [])
transition = apply_bounty_transition(...)
total_value_after = sum(transition.next_state.heads) + sum(transition.next_state.mystery_pool or []) + sum(transition.immediate_cash)
assert abs(total_value_before - total_value_after) < 1e-9
```

## 5. One-hand tournament utility integration (`tournament.py`)

### 5.1 Integration contract

```python
@dataclass(frozen=True, slots=True)
class TournamentHandResult:
    """Result of one-hand tournament utility evaluation."""
    utilities: tuple[float, ...]  # Net utility for each player
    icm_delta: tuple[float, ...]  # Post-ICM minus pre-ICM
    immediate_cash: tuple[float, ...]  # Bounty cash awarded
    metadata: dict[str, Any]

def evaluate_tournament_hand(
    pre_stacks: Sequence[float],
    post_stacks: Sequence[float],
    payouts: Sequence[float],
    bounty_state: BountyState | None = None,
    eliminations: Sequence[tuple[int, Sequence[tuple[int, float]]]] | None = None,
    format_rule: Literal["ko", "pko", "mystery"] | None = None,
    **bounty_kwargs,
) -> TournamentHandResult:
    """Evaluate one-hand tournament utility: ICM delta + immediate bounty cash.
    
    Args:
        pre_stacks: Stacks before hand (positive)
        post_stacks: Stacks after hand (nonnegative; zero for busted players)
        payouts: Placement prize schedule
        bounty_state: Current bounty state (if applicable)
        eliminations: Eliminations during hand (if applicable)
        format_rule: Bounty format (if applicable)
        **bounty_kwargs: Additional bounty parameters (pko_immediate_fraction, etc.)
    
    Returns:
        TournamentHandResult with utilities, ICM delta, and immediate cash
    
    Raises:
        ValueError: Invalid input (chip non-conservation, ambiguous simultaneous
                    eliminations, busted player in pre_stacks)
    """
```

**Computation:**
1. Verify chip conservation: `sum(pre_stacks) == sum(post_stacks)` within `1e-9`
2. Filter busted players (zero post-stack) from ICM evaluation
3. Compute `pre_ICM = compute_icm(pre_stacks, payouts)`
4. Compute `post_ICM = compute_icm(post_stacks[alive], payouts)`
5. If bounties: `transition = apply_bounty_transition(bounty_state, eliminations, format_rule, **bounty_kwargs)`
6. For each player `i`: `u_i = post_ICM[i] - pre_ICM[i] + immediate_cash[i]`
7. Busted players have zero post-ICM placement equity unless payout schedule assigns a prize

**Validation:**
- Reject ambiguous simultaneous eliminations (Phase 3 simplest integration)
- Reject non-conservation of chips
- Reject busted players (zero stack) in `pre_stacks`

**Conservation:**
- `sum(post_ICM - pre_ICM) = 0` when same remaining payout pool (within `1e-12`)
- Immediate bounty cash comes from separately tracked bounty pool
- Total test includes bounty pool conservation

### 5.2 One-hand integration fixtures

1. **Chip-EV baseline:**
   - Pre: `(100, 100, 100)`, Post: `(120, 90, 90)`, Payouts: `(300, 0, 0)`
   - ICM delta: `(+20, -10, -10)` (chip-EV when only first pays)

2. **ICM pressure:**
   - Pre: `(50, 30, 20)`, Post: `(60, 25, 15)`, Payouts: `(100, 60, 0)`
   - ICM delta computed from exact ICM fixtures

3. **Elimination with KO:**
   - Pre: `(50, 30, 20)`, Post: `(70, 30, 0)`, Payouts: `(100, 60, 0)`
   - Bounty: player 2 eliminated, bounty `50`, recipient player 0
   - Utility: `post_ICM[0] - pre_ICM[0] + 50`

4. **PKO split:**
   - Pre: `(50, 30, 20)`, Post: `(60, 40, 0)`, Payouts: `(100, 60, 0)`
   - Bounty: player 2 eliminated, bounty `80`, `f=0.5`, shares `(0.5, 0.5)`
   - Immediate cash: `(20, 20)`, head increases: `(20, 20)`

## 6. JSON API and CLI integration

### 6.1 New API endpoints

**ICM equity endpoint:**
```json
{
  "version": 3,
  "command": "icm-equity",
  "stacks": [50, 30, 20],
  "payouts": [100, 60, 0]
}
```

Response:
```json
{
  "version": 3,
  "equities": [70.357142857, 52.5, 37.142857143],
  "finish_probabilities": [[0.5, 0.3, 0.2], ...],
  "algorithm": "subset-dp",
  "metadata": {}
}
```

**Bounty transition endpoint:**
```json
{
  "version": 3,
  "command": "bounty-transition",
  "current_heads": [50, 50, 50],
  "eliminations": [
    {"eliminated": 2, "recipients": [{"player": 0, "share": 1.0}]}
  ],
  "format_rule": "pko",
  "pko_immediate_fraction": 0.5
}
```

Response:
```json
{
  "version": 3,
  "immediate_cash": [25, 0, 0],
  "next_heads": [75, 50, 0],
  "metadata": {}
}
```

**Tournament hand evaluation:**
Integrated into existing `solve-spot` or new `evaluate-tournament-hand` endpoint.

### 6.2 CLI subcommands

```bash
poker-solver icm-equity --stacks 50,30,20 --payouts 100,60,0 --json
poker-solver bounty-transition --config bounty.json --json
poker-solver evaluate-tournament-hand --config hand.json --json
```

### 6.3 Strict validation

- Integer `version: 3` required
- Exact allowed fields; reject unknown fields
- Deterministic ordering
- Explicit units (chips, currency)
- Structural limits: `MAX_ICM_PLAYERS`, `MAX_BOUNTY_PLAYERS`
- Reject duplicate JSON keys (via `json.loads` with `object_pairs_hook`)
- Reject bool-as-number
- Reject malformed shares (don't sum to 1)
- Reject ambiguous eliminators
- Reject unknown TKO transfer mode
- Reject impossible Mystery distributions
- Reject unsupported future-EV requests with documented-boundary message

## 7. Acceptance gates

All tests must pass before Phase 3 ICM/bounty batch is complete:

1. **ICM correctness:**
   - Subset-DP agrees with independent `Fraction` permutation enumeration within `1e-12` on all fixtures
   - Equities sum to payout pool within `1e-12`
   - Equal stacks produce equal equities
   - Seat permutation only permutes output
   - Common stack scaling leaves output unchanged within `1e-12`

2. **Bounty conservation:**
   - Bounty cash + live heads + consumed/declared terminal value conserves configured bounty pool exactly in integer-unit fixtures
   - PKO immediate fraction and recipient shares never defaulted silently
   - Mystery enumeration probabilities sum to one
   - Without-replacement updates exact counts

3. **One-hand integration:**
   - One-hand tournament utilities match hand-calculated pre/post ICM differences
   - Chip conservation verified independently
   - Busted players handled correctly

4. **Complexity limits:**
   - Oversized ICM inputs fail at documented mask/state limit
   - Limit is measured, not assumed

5. **API/CLI:**
   - Strict JSON validation (version, fields, types, limits)
   - Deterministic output
   - Error messages reference documented boundaries

6. **Boundary enforcement:**
   - Requests for full strategic ICM/bounty solving fail closed with documented-boundary message
   - Requests for neural future-bounty parity fail closed with Tier 3 boundary message

## 8. Implemented-versus-boundary matrix

| Capability | Phase 3 disposition |
|---|---|
| Small-field exact ICM equity | **Implement** |
| Independent permutation oracle | **Implement in tests** |
| KO/SKO immediate bounty accounting | **Implement** |
| Configurable PKO immediate/head transfer | **Implement** |
| TKO as zero regular pool plus explicit bounty rule | **Implement accounting** |
| Finite Mystery expected/enumerated one-draw model | **Implement** |
| Tiny one-hand terminal utility integration | **Implement bounded version** |
| Full tournament strategic solving | **Documented boundary** |
| Future bounty capture EV | **Documented boundary** |
| Neural continuation/value approximation | **Tier 3 boundary** |
| Universal site/house bounty rules | **Not claimed** |

## 9. Testing strategy

### 9.1 Unit tests

**`tests/test_icm.py`:**
- Permutation oracle vs subset-DP on all fixtures
- Equal stacks, seat permutation, stack scaling invariants
- Equity sum conservation
- Oversized input rejection
- Invalid input rejection (negative, zero, increasing payouts)

**`tests/test_bounty.py`:**
- KO/PKO/TKO/Mystery conservation fixtures
- Share validation (sum to 1, non-negative)
- Multiple eliminations
- Mystery expected-value vs enumerated-chance
- Without-replacement updates

**`tests/test_tournament.py`:**
- One-hand ICM delta + bounty cash
- Chip conservation
- Busted player handling
- Simultaneous elimination rejection

### 9.2 Integration tests

**`tests/test_api.py` (extended):**
- ICM equity endpoint
- Bounty transition endpoint
- Tournament hand evaluation endpoint
- Strict JSON validation
- Boundary message enforcement

**`tests/test_cli.py` (extended):**
- `icm-equity` subcommand
- `bounty-transition` subcommand
- `evaluate-tournament-hand` subcommand
- JSON output determinism

### 9.3 Cross-validation

After implementation, a separate adversarial wave must:
- Run all tests and verify green
- Attack ICM with adversarial stack/payout combinations
- Attack bounty accounting with edge cases (zero bounty, all-in splits)
- Cross-check ICM against an independent implementation (if available)
- Cross-check bounty conservation with hand calculations
- Report findings in `review/phase3/icm-bounties-adversarial.md`

## 10. Strategic boundaries and future work

This design implements **utility evaluation and accounting**, not **strategy solving**. The following are explicit boundaries:

**Not implemented (documented boundaries):**
- Full-field optimal PKO/TKO/Mystery strategy: requires modeling future bounty capture EV, field skill distribution, and continuation values beyond one hand
- GTO Wizard neural future-bounty EV parity: requires learned prediction models and extensive training data
- Future Game Simulation: requires modeling blind growth, position rotation, and multi-hand dynamics
- Unrestricted postflop/preflop ICM strategy solving: current integration is one-hand terminal utility only
- Site-specific hidden Mystery-bounty assignment rules: requires reverse-engineering operator-specific implementations

**Future Tier 2/3 extensions (if justified):**
- Multi-hand ICM-aware strategy solving for tiny trees
- Proportional future-bounty EV approximation (GTO Wizard's proportional model)
- Learned continuation value approximation (neural network, requires training data)
- Full tournament simulation with blind growth and field dynamics

**Honesty principle:**
Where a GTO Wizard feature is research-grade or requires proprietary data/models, implement a bounded+correct version or document a clear, justified scope boundary. Never silently claim full parity without evidence.

## 11. File manifest

**New files:**
- `src/poker_solver/icm.py` (ICM evaluator)
- `src/poker_solver/bounty.py` (bounty accounting)
- `src/poker_solver/tournament.py` (one-hand integration)
- `tests/test_icm.py` (ICM tests)
- `tests/test_bounty.py` (bounty tests)
- `tests/test_tournament.py` (tournament integration tests)
- `research/phase3/design/icm-bounties.md` (this file)

**Modified files:**
- `src/poker_solver/api.py` (new endpoints)
- `src/poker_solver/cli.py` (new subcommands)
- `tests/test_api.py` (API integration tests)
- `tests/test_cli.py` (CLI integration tests)

**No other edits.**

## 12. Definition of done

- [ ] All new modules implemented with complete docstrings
- [ ] All unit tests pass (ICM, bounty, tournament)
- [ ] All integration tests pass (API, CLI)
- [ ] All Phase 1+2 tests remain green (265 total)
- [ ] Permutation oracle agrees with subset-DP within `1e-12` on all fixtures
- [ ] Bounty conservation holds exactly in integer-unit fixtures
- [ ] One-hand utilities match hand-calculated ICM deltas
- [ ] Oversized inputs fail at documented limits
- [ ] Boundary requests fail closed with documented messages
- [ ] Adversarial wave reports zero blocking findings in `review/phase3/icm-bounties-adversarial.md`
- [ ] CLI help updated with new subcommands
- [ ] API documentation updated with new endpoints
