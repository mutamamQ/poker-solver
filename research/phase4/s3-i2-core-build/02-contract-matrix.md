# S3-I2 typed-solve contract-to-test matrix

generated=2026-09-16T08:42:08Z
status=COMPLETE_ANALYSIS
blocker_count=0

## Scope

Maps every typed solve/result requirement from ARCHITECTURE_PHASE4_S3.md sections 2.2–2.6 to exact test names and intended production fields in `tests/test_nplayer_preflop_solve.py`.

## Contract-to-test mapping

### 2.2 `NPlayerPreflopSolveResult` type existence

| Requirement | Test | Production field/behavior |
|-------------|------|---------------------------|
| Result type exists in `nplayer_preflop` module | `test_result_type_exists` | `NPlayerPreflopSolveResult.__module__` |

### 2.3 `solve_nplayer_preflop` strict validation

| Requirement | Test | Production field/behavior |
|-------------|------|---------------------------|
| Only `algorithm="vanilla-cfr"` accepted | `test_strict_algorithm` | Rejects unknown/cfr+/empty/None/bool/int |
| Positive strict integer iterations | `test_strict_iterations` | Rejects 0/-1/bool/float/str/None |
| Boolean `include_deviation_certificate` | `test_strict_include_certificate` | Rejects 0/1/str/None |
| Positive strict integer `max_pure_strategies` | `test_strict_pure_cap_even_when_not_requested` | Validates even when certificate=False |

### 2.4 Result structure and immutability

| Requirement | Test | Production field/behavior |
|-------------|------|---------------------------|
| Deterministic repeated solves | `test_solve_deterministic_finite_immutable_result` | Identical strategy/values/metadata across calls |
| Frozen result type | `test_solve_deterministic_finite_immutable_result` | `FrozenInstanceError` on field mutation |
| Detached strategy (outer+inner maps) | `test_solve_deterministic_finite_immutable_result` | Caller mutations don't affect result |
| Detached metadata (nested) | `test_solve_deterministic_finite_immutable_result` | Nested list/dict mutations isolated |
| `config_version=4` | `test_solve_deterministic_finite_immutable_result` | `result.config_version == 4` |
| `game_version=config.version` | `test_solve_deterministic_finite_immutable_result` | `result.game_version == "nplayer-preflop-v1"` |
| `algorithm="vanilla-cfr"` | `test_solve_deterministic_finite_immutable_result` | `result.algorithm` |
| `iterations` echoed | `test_solve_deterministic_finite_immutable_result` | `result.iterations == 3` |
| `max_nodes` from config | `test_solve_deterministic_finite_immutable_result` | `result.max_nodes == config.max_nodes` |
| Structural `max_depth` | `test_exact_structural_depth` | `2 + N + max_raises*(N-1)` |
| Nonempty provenance | `test_solve_deterministic_finite_immutable_result` | `result.provenance` truthy |
| Exactness claim | architecture §2.5 | `result.approximate is False` |
| `metadata["converged"]=False` | `test_solve_deterministic_finite_immutable_result` | Exact boolean False |
| `metadata["convergence_claim"]="none"` | `test_solve_deterministic_finite_immutable_result` | Exact string |
| `metadata["deterministic"]=True` | `test_solve_deterministic_finite_immutable_result` | Exact boolean True |
| Diagnostic status metadata | architecture §2.5 | `deviation_certificate` is `not-requested` or `exhaustive-diagnostic-only` |

### 2.5 Expected values

| Requirement | Test | Production field/behavior |
|-------------|------|---------------------------|
| N-tuple of finite floats | `test_solve_deterministic_finite_immutable_result` | `len(expected_values)==N`, all `isfinite` |
| Zero-sum | `test_solve_deterministic_finite_immutable_result` | `sum(expected_values) ≈ 0` |
| Match independent tree expectation | `test_solve_deterministic_finite_immutable_result` | `_values(root, strategy)` oracle |

### 2.6 Strategy policies

| Requirement | Test | Production field/behavior |
|-------------|------|---------------------------|
| Complete infoset coverage | `test_solve_deterministic_finite_immutable_result` | `set(strategy) == set(infosets)` |
| Complete action coverage per infoset | `test_solve_deterministic_finite_immutable_result` | `set(policy) == set(legal_actions)` |
| Finite nonnegative probabilities | `test_solve_deterministic_finite_immutable_result` | `0 <= p <= 1`, `isfinite(p)` |
| Normalized policies | `test_solve_deterministic_finite_immutable_result` | `sum(policy.values()) ≈ 1` |
| Immutable nested policy dicts | `test_solve_deterministic_finite_immutable_result` | `TypeError` on mutation |

### 2.7 Solver bounds forwarding

| Requirement | Test | Production field/behavior |
|-------------|------|---------------------------|
| Direct solver node bound | `test_direct_solver_bounds` | `NPlayerCFRSolver` rejects `max_nodes=1` |
| Direct solver depth bound | `test_direct_solver_bounds` | `NPlayerCFRSolver` rejects `max_depth=1` |
| Facade forwards node bound | `test_facade_forwards_node_bound` | `solve_nplayer_preflop` propagates `config.max_nodes` |

### 2.8 Deviation certificate

| Requirement | Test | Production field/behavior |
|-------------|------|---------------------------|
| None when not requested | `test_solve_deterministic_finite_immutable_result` | `result.certificate is None` |
| Exhaustive six-player certificate | `test_six_player_exhaustive_certificate_and_exact_cap` | Matches independent `_oracle` enumeration |
| Deterministic certificate | `test_six_player_exhaustive_certificate_and_exact_cap` | Identical across repeated solves |
| Certificate values match baseline | `test_six_player_exhaustive_certificate_and_exact_cap` | `cert.values ≈ baseline` |
| Certificate best-response values | `test_six_player_exhaustive_certificate_and_exact_cap` | `cert.best_response_values ≈ best` |
| Certificate incentives | `test_six_player_exhaustive_certificate_and_exact_cap` | `cert.incentives ≈ incentives` |
| Certificate total incentive | `test_six_player_exhaustive_certificate_and_exact_cap` | `cert.total_incentive ≈ sum(incentives)` |
| Certificate provenance | `test_six_player_exhaustive_certificate_and_exact_cap` | `"exhaustive finite pure unilateral deviations; diagnostic only"` |
| Cap enforcement | `test_certificate_cap_fails_closed` | Rejects when any seat exceeds cap |
| Exact cap boundary | `test_six_player_exhaustive_certificate_and_exact_cap` | Accepts `cap`, rejects `cap-1` |

### 2.9 Independent oracle validation

| Requirement | Test | Production field/behavior |
|-------------|------|---------------------------|
| Six-player oracle runs before facade | `test_six_player_oracle_runs_independently_before_facade` | `_oracle` enumerates pure deviations |
| Oracle baseline zero-sum | `test_six_player_oracle_runs_independently_before_facade` | `sum(baseline) == 0` |
| Oracle best-response dominance | `test_six_player_oracle_runs_independently_before_facade` | `best[i] >= baseline[i]` |
| Oracle pure-strategy counts | `test_six_player_oracle_runs_independently_before_facade` | `counts == (1,4,4,1,1,1)` |
| Oracle exact baseline values | `test_six_player_oracle_runs_independently_before_facade` | `baseline == (5, 1/8, -17/8, -1, -1, -1)` |
| Oracle exact incentives | `test_six_player_oracle_runs_independently_before_facade` | `incentives == (0, 3/8, 3/8, 0, 0, 0)` |
| Production matches oracle | `test_six_player_oracle_runs_independently_before_facade` | `unilateral_deviation_certificate` agrees |

### 2.10 Fixture construction and traversal (controls)

| Requirement | Test | Production field/behavior |
|-------------|------|---------------------------|
| N=2/6/9 configs construct | `test_fixtures_construct_and_traverse_without_facade` | `_config(n)` succeeds |
| Weighted/unweighted deals | `test_fixtures_construct_and_traverse_without_facade` | `enumerate_nplayer_preflop_deals` |
| Deal mass normalization | `test_fixtures_construct_and_traverse_without_facade` | `(1/4, 3/4)` or `(1,)` |
| Root chance outcomes deterministic | `test_fixtures_construct_and_traverse_without_facade` | Repeated `create_nplayer_preflop_root` identical |
| Chance mass sums to 1 | `test_fixtures_construct_and_traverse_without_facade` | `sum(mass for _, mass in root.chance_outcomes()) == 1` |
| Structural depth bound | `test_fixtures_construct_and_traverse_without_facade` | `max(depth) <= 2 + N + max_raises*(N-1)` |
| Solver trains without facade | `test_fixtures_construct_and_traverse_without_facade` | `NPlayerCFRSolver.train(1)` |
| Independent tree expectation zero-sum | `test_fixtures_construct_and_traverse_without_facade` | `sum(_values(root, strategy)) == 0` |

## Test coverage summary

- **15 test functions** exercise all typed solve/result contracts
- **11 passing solve-suite controls** prove fixture construction/traversal and independent oracle behavior. The **19 passing controls** in RED_MANIFEST are the aggregate across all four S3-I2 RED suites and must not be attributed to this file alone.
  These controls prove:
  - Typed N=2/6/9 fixture construction/traversal
  - Independent six-player deviation arithmetic
  - Deterministic deal enumeration and chance mass
  - Zero-sum terminal utilities and tree expectations
- **41 RED failures** (per RED_MANIFEST.md) are exactly missing typed result/facade symbols in production

## Production implementation requirements

### Missing symbols (causing 41 RED failures)

1. `NPlayerPreflopSolveResult` dataclass with fields:
   - `strategy: Mapping[InfoKey, Mapping[Action, float]]`
   - `expected_values: tuple[float, ...]`
   - `certificate: UnilateralDeviationCertificate | None`
   - `config_version: int`
   - `game_version: str`
   - `algorithm: str`
   - `iterations: int`
   - `max_nodes: int`
   - `max_depth: int`
   - `metadata: Mapping[str, object]`
   - `provenance: str`

2. `solve_nplayer_preflop(config, *, algorithm, iterations, include_deviation_certificate=False, max_pure_strategies=100_000)` function:
   - Validate `algorithm == "vanilla-cfr"`
   - Validate `iterations` is positive strict int
   - Validate `include_deviation_certificate` is bool
   - Validate `max_pure_strategies` is a positive strict int; explicit `None` is rejected
   - Compute structural `max_depth = 2 + N + max_raises*(N-1)`
   - Forward `config.max_nodes` and `max_depth` to `NPlayerCFRSolver`
   - Train for `iterations`
   - Deeply detach strategy (outer+inner maps) and metadata (nested)
   - Compute expected values via `expected_values_nplayer`
   - Optionally compute `unilateral_deviation_certificate` with exact cap
   - Return frozen `NPlayerPreflopSolveResult` with:
     - `config_version=4`
     - `game_version=config.version`
     - `metadata={"converged": False, "convergence_claim": "none", "deterministic": True}`
     - Nonempty provenance
   - `approximate=False`

## Blockers

None. All requirements are testable and mapped.

## Parent reconciliation

The parent accepted the requirement-to-test mapping after correcting three facts: the solve suite has 11 passing controls rather than the four-suite aggregate 19; the pure-strategy cap defaults to `100_000` and explicitly rejects `None`; and the architecture also requires `approximate=False` plus diagnostic-status metadata. The child heartbeat predates the report write and is not accepted as completion evidence; parent-authored evidence is stored separately.

---

End of contract-to-test matrix.
