# 06 — Solver Evaluation Benchmark (design)

Status: design-wave report 06. Written read-only on `src/` and `tests/`. It refines PRACTICE_MODE_DESIGN.md §8.
Planned files: `research/solver-evaluation/benchmark.py`, which is seeded and writes `results.json` + `results.md`.
Also `tests/test_solver_evaluation.py`, a fast subset that must run in under 30 s.

## 1. Principles
- Every reference value comes from an INDEPENDENT source: a closed-form derivation, a published
  equilibrium, or a separate brute-force computation. It never comes from the solver's own output.
- Every tolerance is DERIVED from a measured or provable error bound: an exploitability bound, float
  epsilon, or a Monte Carlo standard error. No tolerance is an arbitrary constant.
- Numbers labelled **MEASURED** come from probes run on branch `feat/practice-mode` on 2026-10-02.
  Anything not labelled MEASURED is planned work.

## 2. Game facts used by the derivations (from source)
- `river.py`: P0 (OOP) acts first. At `()`, P0 chooses {check, bet B}. At `(check,)`, P1 chooses
  {check, bet B}. Facing a bet, a player chooses {fold, call}. There is no raise. Returns: each player
  already has `pot/2` in, so the game is zero-sum and the dead pot P = `pot` is split equally. On a
  fold the bettor wins `pot/2`. At showdown the stake is `pot/2`, plus B if a bet was called.

## 3. Existing oracles (do not duplicate)
TBD

## 4. Benchmark items
TBD

## 5. Measured probes
All probes ran via `uv run python /tmp/eval_probe_*.py`. Each one is single-threaded, on this host, on 2026-10-02.

### P1 — Kuhn, vanilla CFR (`CFRSolver(kuhn_root()).train(n)`, `nash_conv(root, prof)`) — MEASURED
| iters | train s | nash_conv | EV0 | \|EV0 − (−1/18)\| |
|---|---|---|---|---|
| 100 | 0.053 | 0.05135 | −0.055987 | 4.3e-4 |
| 1000 | 0.521 | 0.01454 | −0.055557 | 1.7e-6 |
| 5000 | 2.609 | 0.00660 | −0.055506 | 4.9e-5 |

- The fitted log-log slope from 100 to 5000 iterations is ln(0.0066/0.0513)/ln(50) ≈ **−0.52**. This matches the
  O(1/√T) average-strategy bound of CFR. Time per iteration is ≈ 0.52 ms, and it is linear in T.
- The alpha-family check at 5000 iterations: J bet α = 0.2094 (which is ≤ 1/3 ✓). K bet = 0.6071 against 3α = 0.6281, a gap of 0.021.
  Q call = 0.5508 against α + 1/3 = 0.5427, a gap of 0.008. P1: K always calls and bets, J never calls. P1 J bluffs
  0.338 (the reference is 1/3). Q calls 0.336 (the reference is 1/3). Every residual is ≤ about 3× nash_conv. This motivates the tolerance
  in B1: the tolerance is k·nash_conv, not a fixed constant.

### P2 — Polarized river toy, vanilla CFR 2000 iters — MEASURED
Config: board `Kh Kd 8s 5c 2h`. P0 range = {KsKc (nuts, quads), 3c4d (air)} with weight 1 each. P1 range = {QsQc}
(a bluff-catcher that beats air and loses to the nuts). `pot=P=10`, `stack=20`, `bet=B ∈ {5,10,20}`.
Call: `CFRSolver(river_root(cfg)).train(2000)`.

Derivation (zero-sum, P0 view, each side has P/2 in). P1 facing a bet: calling is worth +(P/2+B) against air and
−(P/2+B) against the nuts. Folding is worth −P/2. Indifference gives Pr(air | bet) = **B/(P+2B)**. With equal
prior weights, the air bet frequency is x = **B/(P+B)**. When air checks, P1 checks behind and air loses P/2 (if P1 bets, air folds,
which gives the same −P/2). Indifference for air between bet and check gives the P1 call frequency y = **P/(P+B)**. The nuts always bet.
The game value is EV0 = ½(P/2 + yB) − ½(P/2) = **PB / (2(P+B))**.

| B | s | nash_conv | air bet (ref B/(P+B)) | P1 call (ref P/(P+B)) | EV0 (ref) | \|ΔEV0\| |
|---|---|---|---|---|---|---|
| 5 | 1.59 | 0.0620 | 0.3224 (0.3333) | 0.6696 (0.6667) | 1.6622 (1.6667) | 0.0045 |
| 10 | 1.60 | 0.0907 | 0.5131 (0.5000) | 0.4983 (0.5000) | 2.4920 (2.5000) | 0.0080 |
| 20 | 1.58 | 0.1316 | 0.6536 (0.6667) | 0.3400 (0.3333) | 3.3235 (3.3333) | 0.0099 |

- The solver tracks the sizing sensitivity in the correct direction and magnitude for all three sizes. Every frequency is within 0.014
  of the closed form.
- Tolerance justification: for any profile, |u0(σ) − v*| ≤ max_i incentive_i ≤ nash_conv. This bound holds for every
  row (0.0045 ≤ 0.062, and so on). Frequencies use the same k·nash_conv rule as in B1. nash_conv grows with B because the
  stakes scale. Normalise by (P/2+B) when you compare across sizes.

## 6. Draft verdict table
TBD

## 7. tests/test_solver_evaluation.py
TBD

## 8. Output format (results.json / results.md)
TBD
