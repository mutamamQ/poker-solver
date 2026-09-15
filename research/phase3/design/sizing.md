# Phase 3 Bet Sizing Design: Fixed, Dynamic, and Automatic Modes

## 1. Scope and Contract

This design defines exact formulas, algorithms, APIs, and acceptance tests for Phase 3 bet-sizing modes: **Fixed**, **Dynamic**, and **Automatic**. It preserves the 185-test baseline API and extends `multistreet.py`'s existing `wager_targets` mechanism with unit conversion, legal-action filtering, deduplication, and bounded EV-driven simplification.

**Bounded contract:** All sizing is exact relative to a declared finite candidate set and a finite game tree. "Best EV" means the value of a fully re-solved bounded game using the project's CFR/MCCFR solvers, not a local hand-strength heuristic and not parity with GTO Wizard's proprietary Dynamic Sizing 2.0 ML model.

**Preservation:** `multistreet.py` already uses `wager_targets: tuple[int, ...]` as the ordered list of legal raise-to amounts (line 31, ARCHITECTURE.md §13). This design does not change that internal representation. It adds a conversion layer that produces `wager_targets` from structured size expressions and, for Dynamic/Automatic modes, a selection layer that chooses a subset by solving and comparing bounded trees.

## 2. Size Expression Schema

A size is a JSON object with a mandatory `unit` field and unit-specific parameters. Supported units:

### 2.1 Pot Percentage (`pot-percent`)

```json
{"unit": "pot-percent", "value": 75}
```

- `value`: non-negative finite number (percentage of pot).
- Semantics: `value / 100` of the pot after the actor hypothetically calls.

### 2.2 Geometric (`geometric`)

```json
{"unit": "geometric", "streets": 2, "scale": 1.0}
```

- `streets`: positive integer (number of equal-fraction bet/call opportunities including the current bet).
- `scale`: positive finite number (multiplier applied to the computed geometric fraction).
- Semantics: compute the fraction `g` that commits equal effective stacks over `streets` opportunities, multiply by `scale`, then convert to a raise-to amount.

### 2.3 Previous-Bet Multiple (`previous-bet-multiple`)

```json
{"unit": "previous-bet-multiple", "value": 3.0}
```

- `value`: positive finite number (multiplier).
- Semantics: `value * highest_current_street_commitment`, rounded once.

### 2.4 Big Blinds (`big-blinds`)

```json
{"unit": "big-blinds", "value": 2.5}
```

- `value`: positive finite number.
- Semantics: `value * BB` as a current-street raise-to amount.
- Context: primarily preflop opens; postflop use is allowed where the schema permits it and has the same raise-to meaning.

### 2.5 All-In (`all-in`)

```json
{"unit": "all-in"}
```

- Semantics: the actor's maximum legal raise-to (current commitment plus remaining stack).

### 2.6 Validation

Unknown fields, boolean values, non-finite numbers, nonpositive scales/multipliers, zero streets, and unsupported context (e.g., geometric with impossible stack asymmetry) fail with status 2 (invalid input).

Decimal JSON numbers are parsed through their decimal text representation using Python's `decimal.Decimal`, not binary-float arithmetic.

## 3. Unit Conversion Formulas

### 3.1 Notation

Let:

- `P` = pot immediately before the action, including all current-street commitments.
- `h` = highest current-street commitment.
- `own` = actor's current-street commitment.
- `c = h - own` = actor's call amount.
- `P_call = P + c` = pot after the actor hypothetically calls.
- `own_call = own + c` = actor's commitment after calling.
- `R` = chips remaining after that call.
- `BB` = big-blind chip value (from game configuration).

### 3.2 Pot Percentage

For fraction `q = value / 100`:

- **When not facing a wager** (`c = 0`): target = `own + q * P`.
- **When facing a wager** (`c > 0`): target = `own_call + q * P_call`.

The second formula means "call, then raise by `q` of the pot after calling." In the simple heads-up case with street-starting pot `P0`, a bet `B`, and no prior actor commitment, the pot before response is `P0 + B`; a 100% pot raise gives `B + (P0 + 2B) = P0 + 3B`, agreeing with GTO Wizard source 6 (research/phase3/bet-sizing.md line 25).

### 3.3 Previous-Bet Multiple

For multiplier `m`:

- target = `m * h`, rounded once.

This is a project convention for preflop opens and one prior postflop bet. The product documentation says only "multiple of the previous bet" and does not fully specify every multi-raise commitment context. The resolved target must still satisfy call, minimum-raise, pot-limit, and stack rules.

### 3.4 Big Blinds

- target = `value * BB`, rounded once.

It is a current-street raise-to amount, not additional chips. This makes `2.5bb` a preflop open to 2.5 big blinds. Postflop use is allowed where the schema permits it and has the same raise-to meaning.

### 3.5 Geometric

At an unopened betting node with equal effective remaining stack `S`, current pot `P > 0`, and `n` intended equal-fraction bet/call opportunities including the current bet, the geometric fraction is:

```
g = ((1 + 2*S/P) ** (1/n) - 1) / 2
```

**Proof:** After each bet and call, the pot is multiplied by `1 + 2g`. One player's total contribution after `n` opportunities is `P/2 * ((1 + 2g)^n - 1)`, which equals `S` by construction.

`scale` multiplies `g` before conversion; the ordinary geometric size has `scale = 1`.

At a facing-wager node, compute geometry after the hypothetical call using `P_call`, the effective matched stack remaining after the call, and the explicitly supplied number of opportunities. If stack asymmetry makes the requested equal-bet construction impossible, reject it rather than silently substituting all-in.

The project never infers `n` from prose. API callers provide `streets`; preset builders may derive it deterministically from starting street and record the resolved number.

### 3.6 All-In

- target = `own + R` (actor's current commitment plus remaining stack).

This is the actor's maximum legal raise-to.

### 3.7 Rounding

The project uses `decimal.ROUND_HALF_UP` to the nearest chip after the complete formula is evaluated. Intermediate pot fractions are not rounded. The unrounded `Decimal` amount and rounding rule are metadata when a user-facing Phase 3 endpoint explains a conversion.

## 4. Legal-Action Filtering and Deduplication

After conversion:

1. **Clamp is forbidden:** an amount above stack is illegal unless the expression was `all-in`, which converts exactly to the actor's maximum raise-to.
2. **Below minimum raise:** an amount below the minimum legal full raise is illegal unless it is the actor's exact short all-in and the poker state permits it.
3. **Deduplication:** equal integer targets produced by distinct expressions are deduplicated by target, retaining the first expression in input order as provenance.
4. **No near-all-in threshold:** no "near all-in" threshold rewrites a legal target to all-in.

The resulting legal integer targets are sorted in increasing order and become the `wager_targets` tuple for `MultiStreetConfig`.

## 5. Sizing Modes

### 5.1 Fixed

**Input:** Ordered size expressions at a declared node or node pattern.

**Algorithm:**

1. Convert each expression to an integer target using the formulas in §3.
2. Validate legality (stack, minimum raise, pot-limit cap).
3. Deduplicate by target, retaining first expression in input order.
4. Sort targets in increasing order.
5. Every surviving legal target becomes an action.

**Acceptance oracle:** The output action tuple equals the hand-converted legal targets exactly, in canonical increasing-target order after fold/check/call base actions.

**Fixed never removes a target based on EV.**

### 5.2 Dynamic

**Input:**

- Ordered finite candidate list (size expressions).
- Exact retained count `N` (positive integer).
- Selecting player (0 or 1).
- Solver algorithm/budget (e.g., `vanilla-cfr`, iterations).
- Deterministic tie tolerance `tie_tolerance` (non-negative float).

**Bounded reference algorithm:**

1. Convert and validate all candidates to legal integer targets.
2. Enumerate every size subset of cardinality `N` (combinatorial: `C(len(candidates), N)`).
3. For each subset:
   a. Materialize a fresh edited tree with `wager_targets` set to that subset.
   b. Solve the tree using the same algorithm/budget.
   c. Measure the selecting player's root EV under the solved profile.
4. Choose the subset with maximum EV.
5. Values within `tie_tolerance` tie; resolve by lexicographically increasing integer targets.
6. Return the selected subset and all measured EVs as evidence.

**Constraints:**

- This exhaustive algorithm is exponential in candidate count and therefore accepts at most a small architecture-defined limit (e.g., 10 candidates, `N <= 5`).
- It is exact with respect to the enumerated subsets and measured finite-iteration solver outputs.
- It does not claim that "the top N sizes individually" equals the best joint subset; interactions require subset evaluation.

**Determinism:** For a fixed candidate list, `N`, solver seed (if MCCFR), and tie tolerance, the output is deterministic.

### 5.3 Automatic

GTO Wizard's automatic candidate generation and size-count rule are proprietary. The bounded project uses a transparent substitute:

**Input:**

- Candidate grid generation policy (documented finite grid from pot, stack, legal bounds, allowed units).
- `max_sizes` (positive integer, maximum retained cardinality).
- `ev_tolerance` (non-negative float, acceptable EV loss from full tree).
- Selecting player.
- Solver algorithm/budget.
- Deterministic tie tolerance.

**Bounded reference algorithm:**

1. Generate a documented finite candidate grid (e.g., pot percentages [25, 50, 75, 100, 150], geometric with `streets=2`, all-in).
2. Convert and validate all candidates to legal integer targets.
3. Solve the all-candidate tree to obtain reference EV `V_full` for the selecting player.
4. Exhaustively evaluate subsets from size 1 through `max_sizes`:
   a. For each cardinality `k` from 1 to `max_sizes`, enumerate all subsets of size `k`.
   b. Solve each subset tree and measure selecting-player EV.
5. Choose the smallest-cardinality subset whose selecting-player EV is within `ev_tolerance` of `V_full`.
6. Among equal-cardinality qualifying subsets, maximize EV and use the Dynamic lexicographic tie-break.
7. If no subset qualifies, use the best `max_sizes` subset and report the measured EV gap.

**Rationale:** This is an explainable bounded Automatic mode, not GTO Wizard algorithm parity. Without an EV tolerance or complexity objective, "automatically choose N" is under-specified: adding actions generally makes a player's action set no worse in the exact zero-sum game.

## 6. APIs

### 6.1 Conversion API

```python
def convert_size_expression(
    expr: dict,
    pot: int,
    highest_commitment: int,
    own_commitment: int,
    remaining_stack: int,
    big_blind: int,
) -> tuple[int, dict]:
    """Convert a size expression to an integer raise-to target.
    
    Returns:
        (target, metadata) where metadata includes unrounded Decimal and provenance.
    
    Raises:
        ValueError: invalid expression, unsupported context, or impossible geometry.
    """
```

### 6.2 Fixed Sizing API

```python
def fixed_sizing(
    expressions: list[dict],
    state: MultiStreetState,
    big_blind: int,
) -> tuple[int, ...]:
    """Convert, validate, deduplicate, and sort size expressions.
    
    Returns:
        Sorted tuple of legal integer raise-to targets.
    
    Raises:
        ValueError: invalid expression or illegal target.
    """
```

### 6.3 Dynamic Sizing API

```python
def dynamic_sizing(
    candidates: list[dict],
    retained_count: int,
    selecting_player: int,
    state: MultiStreetState,
    big_blind: int,
    solver_config: dict,
    tie_tolerance: float = 1e-12,
) -> dict:
    """Select best EV subset of size retained_count.
    
    Returns:
        {
            "selected_targets": tuple[int, ...],
            "selected_ev": float,
            "all_subsets": list[{"targets": tuple, "ev": float}],
        }
    
    Raises:
        ValueError: invalid input, retained_count > len(candidates), or combinatorial limit exceeded.
    """
```

### 6.4 Automatic Sizing API

```python
def automatic_sizing(
    grid_policy: str,
    max_sizes: int,
    ev_tolerance: float,
    selecting_player: int,
    state: MultiStreetState,
    big_blind: int,
    solver_config: dict,
    tie_tolerance: float = 1e-12,
) -> dict:
    """Generate grid, solve full tree, select smallest qualifying subset.
    
    Returns:
        {
            "selected_targets": tuple[int, ...],
            "selected_cardinality": int,
            "selected_ev": float,
            "full_tree_ev": float,
            "ev_gap": float,
            "qualified": bool,
        }
    
    Raises:
        ValueError: invalid input or combinatorial limit exceeded.
    """
```

## 7. Acceptance Tests and Oracles

### 7.1 Formula Fixtures

Hand-calculate `%`, `x`, `bb`, and `e` targets using `decimal.Decimal` arithmetic. Assert integer targets exactly.

**Fixture 1: Pot percentage raise identity**

- Street-starting pot 100, opponent bet 50, actor committed 0.
- 100% pot raise-to: `P = 150`, `h = 50`, `own = 0`, `c = 50`, `P_call = 200`, `own_call = 50`.
- Target = `50 + 1.0 * 200 = 250`.
- This follows both the general project formula and GTO Wizard source 6's `3B + P0` identity.

**Fixture 2: Geometric conservation**

- For integer-friendly `P, S, n` fixtures, simulate all bet/call rounds and assert final remaining stack and pot against the formula.
- For irrational targets, test the unrounded `Decimal` value separately and the declared one-time rounding exactly.

**Fixture 3: Previous-bet multiple**

- `h = 50`, `m = 3`: target = `150`.

**Fixture 4: Big blinds**

- `BB = 2`, `value = 2.5`: target = `5`.

### 7.2 Legality Boundaries

- Exact min raise accepted.
- One chip below rejected unless exact short all-in.
- Exact stack target accepted.
- One chip above rejected.
- Pot-limit cap enforced by the game state.

### 7.3 Deduplication

- Distinct expressions resolving to the same integer target produce one action.
- Targets one chip apart remain distinct.

### 7.4 Fixed Invariant

No legal configured target is pruned.

### 7.5 Dynamic Oracle

On a tiny game with at most five candidates, compare selected subset and EV to an independent brute-force enumerator:

- Tolerance `1e-12` for exact expected-value games.
- Fixture-specific predeclared tolerance for iterative CFR.

### 7.6 Cross-Mode Identities

- Dynamic with `N == candidate_count` equals Fixed on the same candidates.
- Automatic with `max_sizes == candidate_count` and zero EV tolerance may choose a smaller exactly equivalent subset but must match full-tree EV within the declared solver tolerance.

### 7.7 Order and Determinism

Candidate input permutation cannot change selected integer targets, measured EVs, or canonical JSON.

### 7.8 API Rejection

Malformed units, booleans, NaN/infinity, unsupported geometric context, impossible retained counts, and combinatorial limits fail with status 2.

## 8. Tolerances and References

### 8.1 Rounding Tolerance

Integer targets are exact after `ROUND_HALF_UP`. No floating tolerance is permitted for integer accounting.

### 8.2 EV Tolerance

- **Dynamic tie tolerance:** default `1e-12` for exact games; fixture-specific for iterative CFR.
- **Automatic EV tolerance:** caller-declared, typically `0.001` (0.1% of pot) or `0.0001` (0.01% of pot).

### 8.3 Solver Tolerance

CFR/MCCFR convergence is measured by NashConv. Phase 2 acceptance gates (ARCHITECTURE.md §13) establish measured thresholds. Dynamic/Automatic use the same solver and budget as the baseline.

### 8.4 References

- GTO Wizard, "How To Calculate Raises in Poker": https://blog.gtowizard.com/how-to-calculate-raises-in-poker/
- GTO Wizard, "Pot Geometry": https://blog.gtowizard.com/pot-geometry/
- GTO Wizard, "Dynamic Sizing: A GTO Breakthrough": https://blog.gtowizard.com/dynamic-sizing-a-gto-breakthrough/
- GTO Wizard, "Introducing Dynamic Sizing 2.0": https://blog.gtowizard.com/introducing_dynamic_sizing_2/
- Project research: `research/phase3/bet-sizing.md`, `research/phase3/game-structure-rake.md`.
- Project architecture: `ARCHITECTURE.md` §13 (Phase 2 multi-street model).

## 9. Scope Boundaries

| Capability | Phase 3 Disposition |
|------------|---------------------|
| `%`, `e`, `x`, and `bb` conversion | Implement with formulas and explicit rounding above |
| Fixed sizing | Implement fully for bounded trees |
| Dynamic sizing | Implement exhaustive best-subset selection for small candidate sets |
| Automatic sizing | Implement transparent EV-tolerance subset selection over a documented generated grid |
| GTO Wizard proprietary ML sizing selection | Documented boundary |
| Continuous bet-size optimization | Documented boundary |
| Magic near-size merging or all-in thresholds | Not implemented |
| Large candidate sets | Reject at a tested limit |

**Combinatorial limits:**

- Dynamic: at most 10 candidates, `N <= 5` (max 252 subsets).
- Automatic: at most 10 candidates, `max_sizes <= 5` (max 637 subsets across all cardinalities 1..5).

These limits are architecture constants and tested.

## 10. Implementation Notes

### 10.1 Module Structure

New module: `src/poker_solver/sizing.py`.

Tests: `tests/test_sizing.py`.

No edits to `multistreet.py`, `model.py`, or existing Phase 2 modules. The sizing module consumes `MultiStreetState` and produces `wager_targets` tuples.

### 10.2 Decimal Arithmetic

Use `decimal.Decimal` for all intermediate calculations. Convert JSON numbers via `Decimal(str(value))`. Round once at the end with `quantize(Decimal('1'), rounding=ROUND_HALF_UP)`.

### 10.3 Solver Integration

Dynamic/Automatic call `cfr.CFRSolver` or `mccfr.MCCFRSolver` with a fresh `MultiStreetConfig` per subset. The solver budget (iterations) is a caller input.

### 10.4 Determinism

For MCCFR, the seed is part of `solver_config`. For vanilla CFR, no seed is needed. Subset enumeration order is deterministic (lexicographic by sorted targets).

### 10.5 Error Handling

All validation errors raise `ValueError` with a descriptive message. CLI wraps these as exit status 2.

## 11. Review and Validation

Every implementation batch for this module requires a fresh non-author review under `review/phase3/` before another feature batch begins (research/phase3/bet-sizing.md line 158).

Review must verify:

- Formula correctness against hand-calculated fixtures.
- Legality filtering and deduplication.
- Dynamic/Automatic determinism and EV measurement.
- Combinatorial limit enforcement.
- No silent clamping, merging, or threshold rewrites.
- Preservation of the 185-test baseline API.

---

**End of Design Document**