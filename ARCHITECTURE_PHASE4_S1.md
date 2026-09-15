# Phase 4 S1 reconciled architecture — automatic all-street postflop

## 1. Scope and decision

S1 delivers a bounded heads-up flop-to-river solve with a caller-declared finite public runout/action tree and no caller-supplied continuation values. It preserves the Phase 1–3 APIs and the 398-test baseline.

The design wave's useful consensus is correctness-first, deterministic, finite-tree traversal; learned value functions and neural DDLS are out of scope. The parent rejects the drafts' proposed nested independent street solvers. The live `MultiStreetState` already composes flop, turn and river into one extensive-form tree and reaches natural fold/showdown terminals. S1 therefore uses one composite tree and one solver traversal. This is the only design here that preserves strategic coupling and information-set reach across streets without inventing subgame gadgets.

Claim boundary: “automatic” means terminal values are computed from the declared tree's natural river/fold outcomes. “Classic” means complete traversal of that configured finite tree for the requested iterations; it is not a convergence certificate, unrestricted poker, automatic abstraction, continuous sizing, or neural continuation.

## 2. Reconciliation of the six design topics

1. Algorithm: adopt exact composite-tree traversal. Reject neural/value-function work (mission out of scope), stochastic leaf rollout as the standard path, and nested per-leaf solving.
2. State integration: reuse `multistreet.py` transitions and terminal accounting; no solver calls from state methods.
3. Oracles: use exact tiny trees first, then measured two-player NashConv bounds. Reject circular “solve full tree, copy its values, then call the copy independent” claims unless the fixture makes the continuation strategically independent.
4. Bounds: enforce declared node/depth/chance limits on the real built tree. Reject guessed formulas, invented runtimes/memory numbers, hash-collision fallback, and unmeasured performance thresholds from the draft.
5. API migration: add a strict S1 envelope/facade. Do not modify v2 semantics, silently ignore unknown S1 fields in v2, or label finite-iteration CFR “exact equilibrium.”
6. Red team: retain S1-specific attacks, but replace the proposed four broad cache-heavy batches with the two smallest dependency-safe implementation batches below. Caching is optional and deferred unless measurement proves it necessary.

The advisory reports remain under `research/phase4/s1-design/`; this document is authoritative when they conflict.

## 3. Public contract

### 3.1 Typed configuration

Add `src/poker_solver/allstreet.py` with immutable additive types:

    @dataclass(frozen=True, slots=True)
    class AllStreetPostflopConfig:
        version: str                       # exactly "allstreet-postflop-v1"
        starting_board: tuple[int, int, int]
        initial_dead_pot: int
        effective_stack: int
        player0_combos: tuple[WeightedCombo, ...]
        player1_combos: tuple[WeightedCombo, ...]
        allowed_runouts: tuple[tuple[int, int], ...]
        betting_mode: Literal["no-limit", "pot-limit"]
        wager_targets: tuple[int, ...]
        max_nodes: int = 100_000
        max_depth: int = 512

    def create_allstreet_root(config: AllStreetPostflopConfig) -> MultiStreetState
    def solve_allstreet_postflop(
        config: AllStreetPostflopConfig,
        *,
        algorithm: Literal["vanilla-cfr", "external-sampling-mccfr"],
        iterations: int,
        seed: int | None = None,
    ) -> AllStreetSolveResult

The initial S1 action scheme is shared across streets because that is the existing verified `MultiStreetConfig` contract. Per-street/dynamic/continuous schemes are deferred to S5. The adapter must defensively copy nested input into tuples and translate to `MultiStreetConfig(version="multistreet-v1", starting_street="flop", ...)`.

No continuation field exists in the standard S1 type. Adding `continuation_mode="automatic"` would falsely suggest a leaf callback is used. Explicit continuation is exposed only through an additive reference/test API after its semantics are proven.

### 3.2 Strict JSON and CLI

Add a version-4 operation rather than changing strict v2/v3 envelopes:

    {"version":4,"operation":"solve-allstreet-postflop","payload":{...}}

Payload fields exactly mirror the public config plus `algorithm`, `iterations`, and `seed`. Unknown/missing fields fail closed. Numeric fields reject booleans; weights must be finite/nonnegative with positive compatible mass; cards/runouts must be unique and blocker-valid when realized; limits and iterations are strict positive integers. Vanilla rejects a seed; MCCFR requires an integer seed.

The CLI receives one additive command (final spelling chosen centrally with existing parser conventions):

    poker-solver phase4 REQUEST.json --json

Existing v1, v2 and v3 API/CLI behavior remains unchanged. Old strict loaders continue rejecting unknown fields; they never “ignore S1 fields.”

Result metadata must include `config_version=4`, `game_version="allstreet-postflop-v1"`, `starting_street="flop"`, `continuation="automatic-natural-terminal"`, the algorithm/iterations/seed, enforced bounds, and truthful provenance `complete configured flop-to-river finite-tree traversal`. It must not say “converged,” “exact equilibrium,” “GTO parity,” or “unrestricted.” `approximate=false` may mean no leaf approximation, but documentation must separately state finite-iteration error.

## 4. State-machine contract

`create_allstreet_root` produces the existing root chance node. The automatic path is:

    private deal -> flop decisions -> public turn chance ->
    turn decisions -> public river chance -> river decisions -> fold/showdown

All-in closures traverse remaining public chance without further decisions. Folds terminate immediately. River showdown uses `evaluate_seven`. The existing net-utility convention remains `award - total_contributed - initial_dead_pot/2` and sums to zero.

The adapter and tests must preserve:

- stable deal/action/runout ordering;
- chance mass one at every chance node;
- raise-to commitment semantics and one-time street pot transfer;
- full compatible runout-sequence conditioning;
- information keys that vary with observable board/history/accounting and never with opponent private cards or private deal index;
- immutable accepted input;
- complete, normalized policies;
- deterministic vanilla output and same-seed MCCFR output.

S1 does not modify `preflop.py`, `multiway.py`, `nplayer.py`, `game_structure.py`, ICM, or bounty utilities. That avoids silently claiming S2/S3/S6.

## 5. Resource and error contract

Before training, exhaustively collect/audit the actual composite tree using explicit `max_nodes` and `max_depth`; estimates may provide diagnostics but may not be the sole acceptance/rejection mechanism. The two-player classic path must gain bounded collection equivalent in behavior to N-player collection. A limit breach raises documented `ValueError` at the API boundary with no partial strategy/result and CLI exit 2.

Pre-parse caps remain explicit for input text, combo count, runout count, wager count and iteration count. Exact values must be selected from measured repository behavior during implementation; the unmeasured numbers in advisory report 04 are not contractual except the existing engine defaults of 100,000 nodes and depth 512.

No cache is required for acceptance. If a later measured optimization adds one, its key must contain the complete immutable config, public state, algorithm, iterations/seed and code/schema version; cached results must be immutable defensive copies. Any cache change forms its own implementation batch and audit.

## 6. Independent oracle and acceptance math

### 6.1 Exact structural fixture

Create a one-combo-per-player flop fixture with a small complete two-card runout set and forced/check-only future actions (empty or otherwise non-aggressive legal sizing). Enumerate compatible runouts independently and calculate each river award with the evaluator and net-utility ledger. Build:

- the automatic composite tree, and
- an explicit truncated flop reference whose closed-flop leaves use the independently enumerated per-deal/history values.

Because future play is forced and private deals are singleton, the representations are strategically identical. Require terminal/chance values to agree within floating accumulation tolerance derived from the exact enumeration (target `1e-12` if measured green), not a guessed CFR tolerance.

### 6.2 Strategic fixture

Use a tiny nontrivial declared betting tree. Compare the automatic composite representation with a separately implemented explicit-continuation representation whose continuation table is generated without calling the automatic solve path and whose conditional range premise is controlled (singleton deals or exact public-state enumeration).

For two strategically equivalent zero-sum games, let `NC_auto` and `NC_explicit` be measured NashConv and `delta_num` the independently measured evaluation/serialization tolerance. The acceptance bound is:

    abs(EV0_auto - EV0_explicit) <= NC_auto + NC_explicit + delta_num

Reason: each profile value lies inside its game’s best-response interval, whose width is NashConv; equivalent games share the equilibrium value. If the bound fails, run a checkpoint sweep with increasing iterations. Accept under-convergence only when both NashConv values and the cross-method gap close consistently; a persistent converged gap is a defect.

### 6.3 Mandatory gates

- standard flop request contains no continuation/payoff table and reaches river terminals;
- every terminal and solved value vector is zero-sum;
- every policy is finite, nonnegative and sums to one;
- repeated vanilla runs are exactly equal; MCCFR same-seed runs are exactly equal;
- opponent-card-only changes preserve the acting player’s information key;
- blocked runouts never appear and conditional chance mass is one;
- fold, call, check-close, all-in, refund and raise-to fixtures retain existing behavior;
- automatic and explicit fixtures satisfy the derived bounds;
- focused tests, then all prior 398 tests plus additive tests, pass.

No wall-clock limit is a correctness gate until measured on a pinned fixture/host. Benchmark observations must be labeled observations.

## 7. Implementation batches and mandatory audits

### Batch S1-I1 — core typed facade and bounded composite solve

Exclusive ownership, at most six BryantGPT authors:

1. `src/poker_solver/allstreet.py` only (typed config/adapter/root/result).
2. `tests/test_allstreet_config.py` only (strict construction, defensive copies, malformed inputs).
3. `tests/test_allstreet_state.py` only (street progression, accounting, blockers, noninterference, determinism).
4. `src/poker_solver/api_v4.py` only (strict envelope; no CLI/shared exports).
5. `tests/test_api_v4.py` only (schema and programmatic end-to-end).
6. `src/poker_solver/bounded_tree.py` + `tests/test_bounded_tree.py` (two-player node/depth preflight).

Parent integrates interfaces and runs focused plus full tests. Then a fresh six-topic non-author audit attacks config mutation/direct construction, state/accounting, chance/noninterference, API strictness/response isolation, resource bounds, and full regression. No S1-I2 begins until I1 is accepted and committed.

### Batch S1-I2 — independent oracle, CLI and canonical example

After I1 audit only:

1. `tests/test_allstreet_oracle.py` exact explicit-continuation oracle and convergence sweep.
2. `examples/phase4_s1_flop.json` + example test, synthetic/non-presolved provenance.
3. Parent-only shared integration: `cli.py`, package exports and capability manifest after exclusive owners finish.

Parent runs focused oracle/API/CLI gates and full suite. A fresh non-author audit attacks oracle independence and premises, convergence math, CLI/error behavior, example truthfulness/determinism, compatibility, and full regression. Any repair requires a regression RED, focused/full GREEN, and a fresh different-agent repair audit before S1 acceptance.

Documentation is a later implementation batch and receives its own fresh audit under the mission hard rule.

## 8. S1 definition of done

S1 is accepted only when the no-continuation browser-independent typed/API/CLI flow solves the canonical flop fixture through declared turn/river trees; all structural, accounting, information and determinism invariants pass; the automatic/explicit comparison satisfies its derived bound; every implementation batch has a fresh non-author executable audit; the complete prior baseline remains green; and the accepted wave is committed. This does not complete S2–S7 or Phase 4.
