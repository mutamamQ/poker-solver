# S3 API, examples, TDD batches, and release matrix

Status: design-only; no production/test/git/state/progress edits authorized.

## 1. Strict typed and versioned public API surface

### 1.1 JSON v4 nplayer-postflop operation

**Exact request schema:**

```json
{
  "version": 4,
  "operation": "solve-nplayer-postflop",
  "payload": {
    "version": "nplayer-postflop-v1",
    "num_players": int (2-9 inclusive),
    "button": int (non-negative seat index),
    "starting_stacks": [int, ...] (N positive integers),
    "contributions": [int, ...] (N non-negative integers),
    "folded": [bool, ...] (N booleans),
    "board": [int, ...] (card indices, non-negative),
    "ranges": [
      [{"cards": [int, int], "weight": float}, ...],
      ...
    ] (N non-empty range arrays),
    "wager_targets": [int, ...] (positive integers),
    "max_raises": int (positive),
    "max_deals": int (positive),
    "max_nodes": int (positive),
    "odd_chip_order": [int, ...] (N non-negative seat indices),
    "showdowns": [
      {
        "deal": [[int, int], ...] (N two-card combos),
        "ranks": [int, ...] (N integers, lower=better)
      },
      ...
    ] (non-empty, unique deals),
    "rake_policy": null | {
      "rate_numerator": int (non-negative),
      "rate_denominator": int (positive),
      "cap": int | null (non-negative if present),
      "minimum_pot": int | null (non-negative if present),
      "no_flop_no_drop": bool,
      "rounding": "floor" | "ceiling" | "nearest",
      "layer_order": "top-down" | "bottom-up"
    },
    "algorithm": "vanilla-cfr",
    "iterations": int (positive),
    "seed": null,
    "include_deviation_certificate": bool,
    "max_pure_strategies": int (positive)
  }
}
```

**Exact response schema:**

```json
{
  "version": 4,
  "operation": "solve-nplayer-postflop",
  "config_version": "nplayer-postflop-v1",
  "game_version": "nplayer-postflop-v1",
  "algorithm": "vanilla-cfr",
  "iterations": int,
  "seed": null,
  "max_nodes": int,
  "max_depth": int,
  "strategy": {
    "<infoset_key>": {
      "<action>": float,
      ...
    },
    ...
  },
  "values": [float, ...] (N player values),
  "certificate": null | {
    "values": [float, ...] (N values),
    "best_response_values": [float, ...] (N BR values),
    "incentives": [float, ...] (N non-negative incentives),
    "total_incentive": float (non-negative),
    "provenance": string
  },
  "metadata": {<string: any>},
  "provenance": string,
  "approximate": bool
}
```

**Field semantics:**

- `num_players`: Total seats at table (2-9); determines array lengths.
- `button`: Dealer position; action order derived from this.
- `starting_stacks`: Initial chip counts before any action.
- `contributions`: Chips already committed to pot (posts, antes, straddles).
- `folded`: Per-seat fold status; folded seats have empty action sets.
- `board`: Community cards as integer indices (0-51 standard encoding).
- `ranges`: Per-seat weighted combo distributions; weights must be positive floats.
- `wager_targets`: Allowed raise-to amounts in chips (absolute, not incremental).
- `max_raises`: Cap on number of raises per decision sequence.
- `max_deals`: Fail-closed bound on compatible deal enumeration.
- `max_nodes`: Fail-closed bound on game-tree node count.
- `odd_chip_order`: Seat priority for indivisible chip allocation.
- `showdowns`: Explicit hand-strength oracle; deal must match range combos exactly.
- `rake_policy`: Optional rake structure; null means chip-EV.
- `algorithm`: Only "vanilla-cfr" supported; deterministic full traversal.
- `iterations`: CFR iteration count; not a convergence guarantee.
- `seed`: Must be null for vanilla-cfr.
- `include_deviation_certificate`: If true, response includes exhaustive unilateral-deviation diagnostic.
- `max_pure_strategies`: Bound on pure-strategy enumeration in certificate.
- `strategy`: Normalized mixed policies; keys are opaque infoset identifiers.
- `values`: Expected values for each seat under the returned strategy.
- `certificate`: Optional bounded diagnostic; not a Nash guarantee for N>2.
- `metadata`: Solver-generated statistics (nodes, depth, deals, etc.).
- `provenance`: Human-readable solver configuration summary.
- `approximate`: True if any approximation was used.

### 1.2 JSON v3 capability query

**Request:**

```json
{
  "version": 3,
  "operation": "capabilities",
  "payload": {}
}
```

**Response includes:**

```json
{
  "version": 3,
  "operation": "capabilities",
  "features": {
    "nplayer-postflop": {
      "status": "implemented-bounded",
      "players": [2, 9],
      "streets": "one-betting-round",
      "interfaces": ["typed", "json-v4", "cli-phase4"],
      "deviation": "exhaustive-diagnostic-only"
    },
    ...
  }
}
```

### 1.3 CLI phase4 subcommand

**Invocation:**

```bash
poker-solver phase4 <request.json> [--json]
poker-solver phase4 - [--json]  # stdin
```

**Behavior:**

- Reads JSON request from file or stdin.
- Validates strict v4 envelope: `version` must be integer 4.
- Dispatches to `dispatch_v4(data)`.
- Emits compact JSON response (no whitespace) if `--json`.
- Returns exit code 0 on success, 2 on validation/execution error.
- Stderr contains error messages only.

### 1.4 Python typed API

**Package exports (`poker_solver/__init__.py`):**

```python
from .nplayer_postflop import (
    NPlayerPostflopConfig,
    NPlayerPostflopSolveResult,
    NPlayerPostflopState,
    NPlayerPublicAction,
    DealN,
    create_nplayer_postflop_root,
    enumerate_deals,
    solve_nplayer_postflop,
)
from .api_v4 import dispatch_v4
```

**Typed solve function:**

```python
def solve_nplayer_postflop(
    config: NPlayerPostflopConfig,
    *,
    algorithm: Literal["vanilla-cfr"],
    iterations: int,
    include_deviation_certificate: bool = False,
    max_pure_strategies: int = 100_000,
) -> NPlayerPostflopSolveResult:
    """Solve bounded N-player one-round postflop game.
    
    Returns immutable result with normalized strategy, values, and optional certificate.
    Raises ValueError on invalid config or exceeded bounds.
    """
```

**Config immutability:**

- All `NPlayerPostflopConfig` fields are frozen dataclass attributes.
- Sequence fields (`starting_stacks`, `ranges`, `showdowns`, etc.) are stored as tuples.
- Nested mutable inputs (lists, dicts) are defensively copied to tuples/MappingProxyType.
- Caller mutation after construction does not affect config or solve behavior.

**Result immutability:**

- `NPlayerPostflopSolveResult` is a frozen dataclass.
- `strategy` is `MappingProxyType[Any, MappingProxyType[Any, float]]`.
- `metadata` is recursively frozen (nested dicts → MappingProxyType).
- `certificate` fields are immutable sequences/mappings.

## 2. Canonical examples

### 2.1 HU (heads-up) flop example

**File:** `examples/phase4/nplayer_2p_flop.json`

**Scenario:**

- 2 players, button seat 0.
- Starting stacks: [100, 100].
- Contributions: [1, 2] (SB/BB).
- Board: [0, 1, 2] (flop).
- Ranges: 2 combos each (non-overlapping with board).
- Wager targets: [4, 8] (pot-sized and 2x pot).
- Max raises: 2.
- Showdowns: 4 explicit deals (2×2 combos).
- Rake: null.
- Iterations: 100.
- Certificate: true.

**Purpose:** Minimal HU postflop with explicit showdown oracle and deviation diagnostic.

### 2.2 6-max (6-player) flop example

**File:** `examples/phase4/nplayer_6p_flop.json`

**Scenario:**

- 6 players, button seat 0.
- Starting stacks: [50, 50, 50, 50, 50, 50].
- Contributions: [1, 2, 0, 0, 0, 0] (SB/BB, others folded preflop).
- Folded: [false, false, false, true, true, true].
- Board: [0, 1, 2].
- Ranges: 3 active seats with 1 combo each.
- Wager targets: [5].
- Max raises: 1.
- Showdowns: 1 deal (deterministic).
- Rake: {rate: 5%, cap: 3, no_flop_no_drop: true, rounding: "floor", layer_order: "top-down"}.
- Iterations: 50.
- Certificate: false.

**Purpose:** Multiway postflop with rake and side-pot accounting.

### 2.3 9-max (9-player) flop example

**File:** `examples/phase4/nplayer_9p_flop.json`

**Scenario:**

- 9 players, button seat 8.
- Starting stacks: [20, 20, 20, 20, 20, 20, 20, 20, 20].
- Contributions: [1, 2, 0, 0, 0, 0, 0, 0, 0].
- Folded: [false, false, true, true, true, true, true, true, true].
- Board: [0, 1, 2].
- Ranges: 2 active seats with 1 combo each.
- Wager targets: [4].
- Max raises: 1.
- Showdowns: 1 deal.
- Rake: null.
- Iterations: 10.
- Certificate: false.

**Purpose:** Maximum table size with minimal tree complexity.

### 2.4 Example determinism and non-presolved status

- All examples use synthetic fixture ranges and showdowns.
- Iteration counts are illustrative, not production recommendations.
- No example claims equilibrium convergence or room-default ranges.
- All examples are deterministic: repeated execution produces identical JSON output.

## 3. TDD batch architecture

### 3.1 Batch independence and RED-first discipline

**Principles:**

- Each batch writes permanent production-importing tests BEFORE touching production.
- Tests must observe intended RED (missing symbols, wrong behavior) before GREEN.
- Batches are non-overlapping: distinct source files, distinct test files.
- No batch depends on another batch's production code.
- Parent verifies RED/GREEN chronology and receipts before acceptance.

### 3.2 Batch B1: Core solver and state machine

**Owned production:** `src/poker_solver/nplayer_postflop.py`

**Owned tests:** `tests/test_nplayer_postflop_solve.py`

**RED contracts:**

- Missing `solve_nplayer_postflop` function.
- Missing `NPlayerPostflopSolveResult` dataclass.
- Missing `create_nplayer_postflop_root` function.
- Missing `enumerate_deals` function.
- Missing `NPlayerPostflopState` class.
- Missing `NPlayerPublicAction` class.
- Missing `DealN` type.

**GREEN contracts:**

- Deterministic 4/5/9-player solves with normalized strategies.
- N-player expected values sum to zero (within 1e-9).
- `max_nodes` and `max_depth` forwarding to bounded tree.
- Hand-derived 5-player counterfactual-reach oracle with exact regret bounds.
- Independent traversal/pure-deviation enumerator compared to facade certificate.
- Fail-closed on exceeded bounds.
- Immutable config and result (tested separately in B3).

**Acceptance:** `uv run pytest tests/test_nplayer_postflop_solve.py -q` passes all tests.

### 3.3 Batch B2: JSON v4 API and validation

**Owned production:** `src/poker_solver/api_v4.py` (nplayer dispatch only)

**Owned tests:** `tests/test_api_v4_nplayer.py`

**RED contracts:**

- Missing `solve-nplayer-postflop` operation in `dispatch_v4`.
- Missing `_dispatch_nplayer_postflop` helper.

**GREEN contracts:**

- Strict v4 envelope: `version` must be integer 4 (reject 4.0, "4", true).
- Exact required/optional field validation.
- N-array length consistency (stacks, contributions, folded, ranges, odd_chip_order).
- Boolean type enforcement (folded, no_flop_no_drop, include_deviation_certificate).
- Finite positive weight validation.
- Deterministic showdowns list conversion and duplicate rejection.
- Rake-policy shape validation.
- Seedless vanilla-cfr enforcement.
- Positive bounds validation.
- Response detachment (caller mutation does not affect returned strategy/metadata).
- Normalized strategies (probabilities sum to 1.0 within 1e-9).
- N-player values in response.
- Optional certificate with exact fields.
- Truthful non-convergence metadata.

**Acceptance:** `uv run pytest tests/test_api_v4_nplayer.py -q` passes all tests.

### 3.4 Batch B3: Immutability and defensive copies

**Owned production:** `src/poker_solver/nplayer_postflop.py` (config/result only)

**Owned tests:** `tests/test_nplayer_postflop_immutability.py`

**RED contracts:**

- Config accepts mutable list inputs and retains aliases.
- Result exposes mutable strategy/metadata.

**GREEN contracts:**

- Config defensive tuple conversion for all sequence fields.
- Config recursive metadata freezing.
- Caller mutation of input lists/dicts after config creation does not affect config.
- Result strategy is `MappingProxyType[Any, MappingProxyType[Any, float]]`.
- Result metadata is recursively frozen.
- Caller mutation of result.strategy/metadata raises or has no effect.

**Acceptance:** `uv run pytest tests/test_nplayer_postflop_immutability.py -q` passes all tests.

### 3.5 Batch B4: CLI and stdin dispatch

**Owned production:** `src/poker_solver/cli.py` (phase4 subcommand only)

**Owned tests:** `tests/test_phase4_cli.py`

**RED contracts:**

- Missing `phase4` subcommand in CLI parser.
- Missing `dispatch_v4` invocation.

**GREEN contracts:**

- File input: `poker-solver phase4 examples/phase4/nplayer_4p_flop.json --json` succeeds.
- Stdin input: `cat examples/phase4/nplayer_4p_flop.json | poker-solver phase4 - --json` succeeds.
- Malformed JSON returns exit code 2 with stderr message.
- Invalid v4 envelope returns exit code 2.
- Valid request returns exit code 0 with compact JSON response.
- Legacy v3 `phase3` subcommand remains green.

**Acceptance:** `uv run pytest tests/test_phase4_cli.py -q` passes all tests.

### 3.6 Batch B5: Package exports and v3 capability

**Owned production:** `src/poker_solver/__init__.py`, `src/poker_solver/api_v3.py`

**Owned tests:** `tests/test_phase4_exports.py`

**RED contracts:**

- Missing `NPlayerPostflopConfig` in package root.
- Missing `solve_nplayer_postflop` in package root.
- Missing `nplayer-postflop` feature in v3 capabilities.

**GREEN contracts:**

- Exactly 5 nplayer exports in `__init__.py`: config, result, state, action, deal, create_root, enumerate, solve.
- `dispatch_v4` is exported.
- `from poker_solver import NPlayerPostflopConfig` succeeds.
- v3 `capabilities` operation includes `nplayer-postflop` with correct status/bounds.
- Legacy v3 operations remain green.

**Acceptance:** `uv run pytest tests/test_phase4_exports.py -q` passes all tests.

### 3.7 Batch B6: Canonical examples and determinism

**Owned production:** None (examples only)

**Owned tests:** `tests/test_phase4_examples.py`

**RED contracts:**

- Missing `examples/phase4/nplayer_2p_flop.json`.
- Missing `examples/phase4/nplayer_6p_flop.json`.
- Missing `examples/phase4/nplayer_9p_flop.json`.

**GREEN contracts:**

- All three examples parse and solve without error.
- Repeated solves produce identical JSON output (determinism).
- Response fields match schema exactly.
- Strategies are normalized.
- Values sum to zero.
- Metadata is non-empty.

**Acceptance:** `uv run pytest tests/test_phase4_examples.py -q` passes all tests.

### 3.8 Batch execution order

B1 → B2 → B3 → B4 → B5 → B6

- B1 must complete before B2 (API depends on solver).
- B3 can run in parallel with B2 (distinct test surfaces).
- B4 depends on B2 (CLI invokes dispatch_v4).
- B5 depends on B1 (exports solver symbols).
- B6 depends on B2 and B4 (examples use JSON API and CLI).

**Recommended parallel waves:**

- Wave 1: B1 alone (core solver).
- Wave 2: B2 and B3 together (API and immutability).
- Wave 3: B4, B5, B6 together (CLI, exports, examples).

## 4. Frozen audit and release matrix

### 4.1 Audit gates

**Pre-implementation audit (design-only):**

- This document reviewed by non-author design auditor.
- Confirms: no production/test edits, strict schema, exact batch boundaries, RED-first discipline.

**Post-batch audit (per batch):**

- Fresh non-author reviewer runs RED receipt, inspects GREEN diff, reruns tests.
- Confirms: chronology, no skipped tests, no caught-import fallbacks, exact contracts.

**Integration audit (after all batches):**

- Fresh non-author reviewer runs full suite, compileall, focused gates.
- Confirms: baseline preserved, new tests green, no regressions.

**Release audit (final):**

- Fresh non-author reviewer verifies: examples deterministic, CLI functional, exports correct, capability truth.
- Confirms: no presolved claims, no convergence guarantees, bounded scope documented.

### 4.2 Release matrix

| Component | Status | Scope | Interface | Tests | Audit |
|-----------|--------|-------|-----------|-------|-------|
| N-player solver | Implemented-bounded | 2-9 players, one betting round, explicit showdowns | Typed Python | Permanent, independent oracle | Required |
| JSON v4 API | Implemented | `solve-nplayer-postflop` operation | Strict schema | Permanent, validation suite | Required |
| CLI phase4 | Implemented | File and stdin dispatch | `poker-solver phase4` | Permanent, behavioral | Required |
| Package exports | Implemented | 5 nplayer symbols + dispatch_v4 | `from poker_solver import ...` | Permanent, import tests | Required |
| v3 capability | Implemented | `nplayer-postflop` feature truth | `capabilities` operation | Permanent, integration | Required |
| HU example | Implemented | 2-player synthetic fixture | JSON file | Permanent, determinism | Required |
| 6-max example | Implemented | 6-player with rake | JSON file | Permanent, determinism | Required |
| 9-max example | Implemented | 9-player maximum table | JSON file | Permanent, determinism | Required |
| Deviation certificate | Implemented-bounded | Exhaustive diagnostic only, not Nash guarantee | Optional response field | Permanent, independent enumerator | Required |
| Immutability | Implemented | Config and result deep freeze | Typed API contract | Permanent, mutation tests | Required |

### 4.3 Legacy controls

**Preserved baselines:**

- Tag `phase3-398-green` must remain present.
- `uv run pytest -q` on original 17-file Phase 1+2 subset must pass 185/185.
- `uv run pytest tests/test_api_v3.py -q` must pass all v3 tests.
- `uv run pytest tests/test_phase4_s1_*.py -q` must pass all S1 tests.
- `poker-solver phase3 <v3-request.json> --json` must remain functional.

**Additive-only discipline:**

- No existing test may be weakened, skipped, or removed.
- No existing API field may change semantics.
- No existing CLI subcommand may break.

### 4.4 Migration boundaries

**S1 → S2 boundary:**

- S1 (allstreet-postflop) is heads-up automatic continuation.
- S2 (nplayer-postflop) is 2-9 player explicit showdowns.
- No shared production code between S1 and S2 solvers.
- Both use common `bounded_tree`, `game_structure`, `equity` foundations.
- Both expose v4 operations through `dispatch_v4`.
- Both export typed APIs through package root.

**S2 → S3 boundary (future):**

- S3 will add preflop solving, automatic postflop continuation for N>2, or other extensions.
- S2 nplayer API remains stable and backward-compatible.
- New S3 features use new v4 operations or v5 envelope.

### 4.5 Scope documentation

**Explicit boundaries in release notes:**

- "N-player postflop solving is bounded to one betting round with caller-supplied explicit showdown ranks."
- "Deviation certificate is an exhaustive unilateral-deviation diagnostic, not a Nash equilibrium guarantee for N>2."
- "Examples use synthetic fixture ranges and illustrative iteration counts, not production recommendations or room defaults."
- "Convergence is not certified; `iterations` is a traversal count, not a quality guarantee."
- "Rake accounting is exact per declared policy; no room-specific defaults are included."

## 5. Design-only deliverable checklist

- [x] Strict typed JSON v4 request/response schema with exact field semantics.
- [x] Exact payload fields: posts, positions, straddles (via contributions), sizing (wager_targets), continuations (showdowns).
- [x] Package exports and capability truth (5 symbols + dispatch_v4, v3 feature).
- [x] Canonical HU/6max/9max examples with determinism and non-presolved status.
- [x] Permanent independent tests per batch (oracle, validation, immutability, CLI, exports, examples).
- [x] RED-first nonoverlapping implementation batches (B1-B6).
- [x] Frozen audit/release matrix with legacy controls.
- [x] Migration boundaries (S1/S2/S3).
- [x] Scope documentation (bounded, diagnostic-only, synthetic fixtures).

**Live heartbeat:** 2026-09-16T00:00:00Z (design-only, no production edits).
