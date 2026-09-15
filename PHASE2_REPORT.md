# Phase 2 completion report

## Verdict

The backend is feature-complete for the finite, heads-up Phase 2 scope defined in `ARCHITECTURE.md` section 13. It now solves bounded flop/turn/river games with exact weighted private deals, explicitly configured public runouts, discrete no-limit or pot-limit raise-to targets, vanilla CFR or seeded external-sampling MCCFR, scalable infoset-consistent best response, and strict round-trippable JSON/CLI integration.

This is not evidence of parity with GTO+, PioSOLVER, or unrestricted full-game Hold'em. Commercial products did not provide a machine-readable independent fixture in this mission. Industry-standard validation is separated correctly: Treys independently validates hand evaluation/equity; analytical Kuhn values and exhaustive independent best-response enumeration validate equilibrium machinery.

## Delivered backend

- `src/poker_solver/multistreet.py`: immutable heads-up flop/turn/river state machine; exact range/deal chance; blocker-conditioned runouts; check, call, fold, full raise and short all-in semantics; no-limit/pot-limit caps; unmatched-chip refund; automatic all-in runout; zero-sum net utility payoff.
- `src/poker_solver/mccfr.py`: external-sampling MCCFR with an isolated seeded RNG, stable traversal, lazy infoset discovery, and a deterministic same-seed average-policy result.
- `src/poker_solver/best_response.py`: dynamic infoset-consistent best response plus the retained exhaustive Cartesian oracle; explicit NashConv and half-NashConv naming.
- `src/poker_solver/api.py`: strict version-2 parser, strict field/type/range/card validation, solver selection, strategy reconstruction, strategy serialization/deserialization and exploitability computation.
- `src/poker_solver/phase2_fixture.py`: bounded independently auditable multi-street fixture.
- `src/poker_solver/cli.py`: `solve-multistreet` and `exploitability`, stdin support, and backward-compatible Phase 1 commands.
- `scripts/benchmark_phase2.py`: stable-schema local throughput/RSS benchmark without a correctness claim.
- `examples/multistreet_spot.json`: executable Phase 2 example.

## Parent verification

Final compile and full regression gate:

```text
uv run python -m compileall -q src tests scripts && uv run pytest -q
185 passed in 192.59s (0:03:12)
```

Fast gate:

```text
uv run pytest -m 'not slow' -q
181 passed, 4 deselected in 72.03s (0:01:12)
```

Independent external evaluator/equity gate:

```text
uv run --with treys python scripts/crosscheck_treys.py
treys cross-check passed: categories=100000 comparisons=50000 seed=0xC0FFEE
```

End-to-end serialized MCCFR solve and independent exploitability recomputation:

```text
values = [1.0075144497000672, -1.0075144497000672]
best_response_values = [1.0079470693492119, -1.0]
nash_conv = 0.007947069349211855
exploitability_half_nash_conv = 0.0039735346746059275
```

That result used `examples/multistreet_spot.json`, 1,000 MCCFR iterations and seed 42. It is a smoke/convergence receipt, not a universal quality threshold.

Final local benchmark, Kuhn, 1,000 iterations per trial, five trials:

```text
vanilla-cfr median = 1978.0342578545878 iterations/s
mccfr median = 13875.393147377512 iterations/s
peak RSS = 27648 KiB
schema_version = 1
```

The throughput comparison applies only to this implementation, game, host and workload.

## Independent correctness gates

- Exact five-card category census remains green over all 2,598,960 five-card hands.
- Existing exhaustive exact-card equity fixtures remain green.
- Treys cross-check passed 150,000 independently evaluated seven-card/category or pairwise cases.
- Kuhn analytical value and CFR regression tests remain green.
- Dynamic best response agrees with exhaustive pure-strategy enumeration to `1e-12` across Kuhn, compact river and bounded multi-street profiles.
- A 30-responder-infoset test demonstrates dynamic best response without enumerating more than one billion pure strategies.
- Hidden-bit and private-deal tests verify one action per information set and prevent opponent-card/deal-index leakage.
- Bounded multi-street audit visits the complete fixture tree and checks finite zero-sum terminal utilities.
- MCCFR seed matrices, same-seed byte determinism, different-seed trajectory evidence and vanilla agreement gates pass.
- Pot-limit regression locks the facing-bet rule: with pot 100 and a bet of 50, calling makes the pot 200 and a pot-sized raise has raise-to target 250; 300 is illegal.

## Research and design evidence

Eight parent-reconciled research reports live under `research/phase2/`:

- feature inventory;
- accuracy fixtures;
- MCCFR versus vanilla CFR;
- multi-street modeling;
- exploitability/best response;
- determinism/performance;
- cross-validation;
- three-player scope.

Six Wave B design/adversarial reports in the same directory informed the reconciled contract. Child claims were not accepted without parent source inspection and execution. Incorrect claims about payoff accounting, pot-limit caps, CFR variants, solver capabilities, fixtures and best-response scalability were rejected or corrected.

Wave D found two real blockers, both fixed and regression-tested:

1. MCCFR average policy had been accumulated on the wrong traversal nodes; it now follows the verified two-player external-sampling schedule.
2. Private deal identity appeared in public action history used by information keys; `DEAL` actions are now excluded so opponent cards cannot leak.

The final six-role clean review completed with substantive PASS results for poker rules, best response, accuracy/scope and engineering. Two transport-invalid reviews were replaced; substantive replacement reviews passed MCCFR and API/CLI.

## Explicit limitations

- Heads-up only; no three-player claim.
- Postflop start only; no preflop game construction.
- Finite exact combo ranges and explicitly enumerated complete runouts.
- Discrete configured raise-to targets; no continuous action solving or automatic action abstraction.
- No rake, side pots, ICM or tournament utility.
- No automatic card bucketing, suit isomorphism or production distributed solver.
- Vanilla CFR and exhaustive best response are tiny-tree validation oracles. Exact vanilla inputs are guarded by a conservative chance-leaf limit.
- MCCFR is stochastic and must be assessed with declared seeds and exploitability/oracle gates; no universal speedup or commercial parity is claimed.
