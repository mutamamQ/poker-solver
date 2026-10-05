# Solver evaluation — REPORT and VERDICT (W4 task E)

Benchmark: `research/solver-evaluation/benchmark.py` (oracles in `games.py`). Wrapper:
`scripts/solver_eval.sh [quick|full]`. Canonical outputs from the full run are
`results.json` (machine-readable: host, git commit, timestamps, thresholds, all evidence)
and `results.md` (tables). Permanent test: `tests/test_solver_evaluation.py`. It runs quick
mode, which takes about 25–60 s on this host.

Full run: 2026-10-05T05:39:12Z → 05:44:31Z (319 s). Commit `ed886c8` on `feat/practice-mode`.
The worktree was dirty: W4 tasks A–D were editing `practice/*` at the same time. Host: Linux 6.8 x86_64,
Python 3.11.16, 2 CPUs, load ≈ 5. Timings are therefore pessimistic.

## VERDICT

**Overall: FAIL** (worst-case rule). **Correctness-only: PARTIAL.**

- The solver core is correct where it can be checked. It matches every independent analytic reference:
  - Kuhn −1/18
  - the polarized river closed form
  - the 3-player Kuhn −1/48 family
  - Malmuth-Harville ICM
  - hand-counted equities
- The solver converges on every backend. Its best response agrees with an independent oracle to 1e-14.
- Practice scores are re-derived exactly, with error 0.0 over 58 plays across 18 spots.
- It is **not a complete, up-to-par NLHE solver**:
  1. It does not scale to realistic ranges. C14 FAIL projects ≈ 2.4e5 s for 1000 iterations at
     100 combos per side.
  2. The 3-max preflop practice family ships at its default solve with exploitability ≈ 7.2 % of the pot.
     That is a C11 FAIL. The solver itself is fine: it is the 100-iteration default.
  3. Every capability is bounded by abstraction. Each one has a PARTIAL scope cap.
  4. There is a value-neutral all-in tree defect (C15 PARTIAL).

Verdict rule (fixed before running, in `THRESHOLDS` / `VERDICT_RULE`):
- Each criterion is graded from its declared thresholds.
- A capability = worst(its evidence criteria, or per-family sub-verdicts, and its documented scope cap).
- overall = worst(all criteria + all capabilities), with FAIL > PARTIAL > PASS.
- `correctness_verdict` excludes C11 (default-solve quality), C12 (timing) and C14 (scale).

### Capability classification

| capability | verdict | evidence (criterion ids) | gaps |
|---|---|---|---|
| 2-player NL | **FAIL** | C3, C4, C5-river/flop/turn/preflop-hu, C6, C10 PASS; C14 FAIL; C15 PARTIAL; C11[flop-cbet] PARTIAL | no full-range solve; tiny ranges, fixed menus, runout subsets; does not scale (C14) |
| 3-max | **FAIL** | C5-preflop-3p, C6, C7 PASS; C11[preflop-3max-open] FAIL (7.18 % pot); C12 PASS | preflop only; default 100 iterations too few; adapter reports `nash_conv=None` for 3-max |
| preflop | **FAIL** | C5-preflop-hu/3p PASS; C11[preflop-hu-open] PASS (0.34 %); C11[preflop-3max-open] FAIL | leaves settled by sampled-board equity, with no postflop play |
| postflop | **FAIL** | C3, C5-river/flop/turn, C10 PASS; C11 river/turn PASS, flop PARTIAL (1.12 %); C14 FAIL | one size per spot; ≤ 4 runouts; scale |
| multi-street | **PARTIAL** | C5-flop/turn PASS; C11[flop-cbet] PARTIAL, [turn-barrel] PASS | explicit runout subsets only (not all 49×48) |
| ICM | **PARTIAL** | C13 PASS (ICM == Malmuth-Harville to 1e-13) | evaluator only; no ICM-aware solving anywhere |
| mixed strategy | **PASS** | C1, C3, C16 PASS | — |
| sizing | **PARTIAL** | C4, C9 PASS | fixed menus; practice spots expose one size; off-tree sizes are snapped, never solved |

## Criteria (thresholds declared up front; full numbers in results.json)

| id | verdict | measured (full mode) | PASS threshold |
|---|---|---|---|
| C1 Kuhn analytic | PASS | NashConv 0.0514→0.00464 over 100→10k iterations, log-log slope −0.52; \|EV0+1/18\| ≤ NashConv at every checkpoint; all 11 alpha-family structure checks hold (α=0.208, K bet 0.613≈3α, Q call 0.551≈α+1/3, P1 J-bluff 0.335, Q-call 0.339) | value err ≤ 1e-3, NashConv ≤ 0.02, ratio ≤ 0.5, slope ≤ −0.35, structure within 5×NashConv |
| C2 Kuhn MCCFR | PASS | seed 0: NashConv 0.0487→0.0055 (1k→20k); EV0 err < 5e-3 | err ≤ 5e-3, NashConv ≤ 0.05, decreasing |
| C3 river closed form | PASS | B∈{5,10,20}, P=10: air-bet / call frequencies within 0.015 of B/(P+B), P/(P+B); EV0 within NashConv of PB/(2(P+B)); monotone in B | freq err ≤ 0.03, value err ≤ NashConv, nuts bet ≥ 0.95 |
| C4 sizing menu | PASS | menu {5,20}: nuts put 0.5 % on size 5; EV0 3.315 vs closed-form 3.333 (err 0.019 ≤ NashConv 0.104) | small size ≤ 5 %, value within NashConv |
| C5 convergence river | PASS | catalog river spot: 2.95→0.20 (25→1600 iterations) | last/first ≤ 0.5 |
| C5 convergence flop (allstreet) | PASS | 36.2→3.61 (10→640) | ≤ 0.5 |
| C5 convergence turn (multistreet) | PASS | 28.4→3.02 (10→640) | ≤ 0.5 |
| C5 convergence preflop HU | PASS | 0.888→0.041 (10→2560) | ≤ 0.5 |
| C5 convergence preflop 3p | PASS | 3.09→0.055 (10→2560), independent n-player NashConv | ≤ 0.5 |
| C6 BR oracle agreement | PASS | 13 comparisons: repo `nash_conv` / 3p `unilateral_deviation_certificate` vs the benchmark's own infoset-consistent BR; max rel err 1.4e-14 | ≤ 1e-9 |
| C7 3-player Kuhn | PASS | NashConv 0.0895→0.00217 (100→10k); seat1 −0.0201 vs −1/48 (err 7e-4 ≤ NashConv); seats 0 and 2 inside the analytic ranges | NashConv ≤ 0.02, seat1 err ≤ NashConv |
| C8 determinism | PASS | adapter repeat solves give identical `to_json` (minus wall time) and `params_hash`; catalog stable; CFR, n-player CFR and MCCFR(seed) repeatable; MCCFR seeds 0≠1 | exact equality |
| C9 param sensitivity (R1) | PASS | iterations, pot, bet size, villain weight and stack (allstreet) each change `params_hash` and the strategy/Q (Q deltas 1.1–62 chips) | every perturbation changes hash and output |
| C10 score cross-check | PASS | 18 spots (12 Kuhn plus 1 per other family, all 7 families), 58 plays (every pure action plus the solver mix): Q, σ, pot, EV loss, score and grade from an independent solve plus a Q-oracle; max abs error 0.0 | ≤ 1e-9 |
| C11 practice solve quality | **FAIL** | exploitability (NashConv/n)/pot at the family default: kuhn 0.87 %, river-oop 0.25 %, river-ip 0.87 %, preflop-hu 0.34 %, **preflop-3max 7.18 %**, flop-cbet 1.12 %, turn 0.58 % | ≤ 1 % pass, ≤ 5 % partial |
| C12 practice timing | PASS | cold solves 0.6–11.8 s (flop-cbet 11.8 s, 3-max 9.8 s) under load ≈ 5 | ≤ 20 s (contract) |
| C13 equity / ICM | PASS | AhKh vs QsQc on 2h7h9cJd = 15/0/29 (hand-counted); royal board = 1 tie; ICM vs Malmuth-Harville over 7 cases, err 7.8e-14 | exact / ≤ 1e-9 |
| C14 scale | **FAIL** | river with one bet size: s/iteration grows as deals^1.44; 48 combos/side = 29 s/iteration (measured); projected 100 combos/side ≈ 242 s/iteration → 2.4e5 s per 1000 iterations | ≤ 60 s (≤ 3600 s partial) |
| C15 all-in | PARTIAL | zero-sum, reaches all-in showdowns, NashConv decreases. Defect: `multistreet` offers `RAISE(target == call target)` facing an all-in (24 such actions), then gives the all-in seats CHECK-only decision nodes (48). Value gap call vs that "raise" = 0.0 | no degenerate RAISE, no decisions for all-in seats |
| C16 mixed strategy | PASS | Kuhn P1 J-bluff and Q-call, river-toy air bet (3 sizes) all strictly inside (0.05, 0.95) | — |

## Concrete gap list

1. **Scale.** Pure-Python full-tree vanilla CFR is superlinear in deals. A 100-combo river with one size
   needs about 4 min per iteration on this host. Fixing this needs vectorised/array CFR (range-vs-range
   per public node, not per deal), CFR+/DCFR, and card abstraction.
2. **3-max preflop default budget.** `FAMILY_DEFAULT_SOLVE["preflop-3max-open"]` is 100 iterations,
   giving ≈ 7 % pot exploitability. The C5 3p toy shows ~640+ iterations are needed for under 1 %. The
   adapter also records `nash_conv=None` for 3-max, even though an n-player NashConv is computable
   (this benchmark's `games.nash_conv_n` already does it).
3. **flop-cbet** is at 1.12 % pot at its 200-iteration default (catalog at run time). A few hundred more iterations would get it under 1 %.
4. **multistreet all-in tree** (C15): drop `RAISE` when target == call target, and skip decisions
   when the actor has 0 behind. This is value-neutral today, but it lets a practice user pick a "raise"
   that is really a call.
5. **ICM is evaluator-only.** No solver or practice path uses ICM utilities.
6. **Sizing.** Practice spots offer one solved size. User sizes off the menu are snapped, never solved.
   There is no automatic size selection in the practice solve path.
7. **Abstraction scope.** There are tiny explicit ranges (≤ 5 combos/side), runout subsets (≤ 4), and
   preflop leaves settled by sampled equity. 3-way play exists only preflop.
8. **Coverage of C10/C11.** Only the first spot per non-Kuhn family is re-derived. Families are
   evaluated as the live catalog generates them, so their numbers move with tasks A/B.

## Reproduce

```
scripts/solver_eval.sh quick              # < 2 min, temp dir
scripts/solver_eval.sh full               # ~5 min here, rewrites results.json / results.md
.venv/bin/python -m pytest -q tests/test_solver_evaluation.py
```

The benchmark imports solver modules directly. Practice is used only through its public API:
`generate_catalog`, `SolverAdapter.solve`, `score_play`, and `preflop_config` (the last one only to build
the identical game for the independent recomputation). No numbers are copied: every reference is a
closed form or an enumeration computed at run time.
