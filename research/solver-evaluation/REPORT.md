# Solver evaluation — REPORT and VERDICT (W4 task E; refreshed for the W5 re-run)

Benchmark: `research/solver-evaluation/benchmark.py` (oracles in `games.py`). Wrapper:
`scripts/solver_eval.sh [quick|full]`. Canonical outputs from the full run are
`results.json` (machine-readable: host, git commit, timestamps, thresholds, all evidence)
and `results.md` (tables). Permanent test: `tests/test_solver_evaluation.py`. It runs quick
mode, which takes about 25–60 s on this host (34 s in the W6 check).

Full run (current `results.md`, committed at `72f0053`, tag `practice-mode-w5`):
2026-10-05T07:50:44Z → 07:59:03Z (499 s). Commit `2a6f57c` (the W5 practice code) on
`feat/practice-mode`, **clean tree** (`dirty=False`). `72f0053` only adds the regenerated
`results.json` / `results.md`, so the numbers describe the code at the tag. Host: Linux 6.8 x86_64,
Python 3.11.16, 2 CPUs, load ≈ 3.1 / 2.4 / 2.3 at start. Timings are host-dependent.

The previous full run (W4, `ed886c8` with a dirty tree, 319 s) is superseded; its differences are
listed under "Changes since the W4 run" below.

## VERDICT

**Overall: FAIL** (worst-case rule). **Correctness-only: PARTIAL.** 17 of 20 criteria PASS,
2 PARTIAL (C11, C15), 1 FAIL (C14).

- The solver core is correct where it can be checked. It matches every independent analytic reference:
  - Kuhn −1/18
  - the polarized river closed form
  - the 3-player Kuhn −1/48 family
  - Malmuth-Harville ICM
  - hand-counted equities
- The solver converges on every backend. Its best response agrees with an independent oracle to 1.4e-14.
- Practice scores are re-derived exactly, with error 0.0 over 58 plays across 18 spots (all 7 families).
- Every practice family is ≤ 1 % pot exploitable at its default solve except `flop-cbet` (1.122 %).
  `preflop-3max-open` is now 0.143 % (5000-iteration default with the W5 flat trainer).
- It is **not a complete, up-to-par NLHE solver**:
  1. It does not scale to realistic ranges. C14 FAIL projects ≈ 1.8e5 s for 1000 iterations at
     100 combos per side.
  2. `flop-cbet` ships at 1.122 % pot exploitability at its 200-iteration default (C11 PARTIAL).
  3. Every capability is bounded by abstraction. Each one except mixed strategy has a PARTIAL scope cap.
  4. The `multistreet` engine still has a value-neutral all-in tree defect (C15 PARTIAL). Practice
     output hides it by merging the pseudo-raise into `CALL`, but the engine tree is unchanged.

Verdict rule (fixed before running, in `THRESHOLDS` / `VERDICT_RULE`):
- Each criterion is graded from its declared thresholds.
- A capability = worst(its evidence criteria, or per-family sub-verdicts, and its documented scope cap).
- overall = worst(all criteria + all capabilities), with FAIL > PARTIAL > PASS.
- `correctness_verdict` excludes C11 (default-solve quality), C12 (timing) and C14 (scale).

### Capability classification

| capability | verdict | evidence (criterion ids) | gaps |
|---|---|---|---|
| 2-player NL | **FAIL** | C3, C4, C5-river/flop/turn/preflop-hu, C6, C10 PASS; C11 river/preflop-hu/turn PASS; C14 FAIL; C15 PARTIAL; C11[flop-cbet] PARTIAL | no full-range solve; tiny ranges, fixed menus, runout subsets; does not scale (C14) |
| 3-max | **PARTIAL** | C5-preflop-3p, C6, C7 PASS; C11[preflop-3max-open] PASS (0.143 % pot); C12[preflop-3max-open] PASS (11.4 s) | preflop only (scope cap). since W5 the adapter reports a finite n-player NashConv (scope-cap string in `benchmark.py`/`results.*` corrected in W6) |
| preflop | **PARTIAL** | C5-preflop-hu/3p PASS; C11[preflop-hu-open] PASS (0.34 %); C11[preflop-3max-open] PASS (0.143 %); C12 PASS | leaves settled by sampled-board equity, with no postflop play |
| postflop | **FAIL** | C3, C5-river/flop/turn, C10 PASS; C11 river/turn PASS, flop PARTIAL (1.12 %); C12 PASS; C14 FAIL | one size per spot; ≤ 4 runouts; scale |
| multi-street | **PARTIAL** | C5-flop/turn PASS; C11[flop-cbet] PARTIAL, [turn-barrel] PASS; C12 PASS | explicit runout subsets only (not all 49×48) |
| ICM | **PARTIAL** | C13 PASS (ICM == Malmuth-Harville to 7.8e-14) | evaluator only; no ICM-aware solving anywhere |
| mixed strategy | **PASS** | C1, C3, C16 PASS | — |
| sizing | **PARTIAL** | C4, C9 PASS | fixed menus; practice spots expose one size; off-tree sizes are snapped, never solved |

## Criteria (thresholds declared up front; full numbers in results.json)

| id | verdict | measured (full mode) | PASS threshold |
|---|---|---|---|
| C1 Kuhn analytic | PASS | NashConv 0.0514→0.00464 over 100→10k iterations, log-log slope −0.52; \|EV0+1/18\| ≤ NashConv at every checkpoint; all 11 alpha-family structure checks hold (α=0.208, K bet 0.613≈3α, Q call 0.551≈α+1/3, P1 J-bluff 0.335, Q-call 0.339) | value err ≤ 1e-3, NashConv ≤ 0.02, ratio ≤ 0.5, slope ≤ −0.35, structure within 5×NashConv |
| C2 Kuhn MCCFR | PASS | seed 0: NashConv 0.0487→0.0055 (1k→20k); EV0 err 3.8e-5 at 20k | err ≤ 5e-3, NashConv ≤ 0.05, decreasing |
| C3 river closed form | PASS | B∈{5,10,20}, P=10: air-bet / call frequencies within 0.015 of B/(P+B), P/(P+B); EV0 within NashConv of PB/(2(P+B)); monotone in B | freq err ≤ 0.03, value err ≤ NashConv, nuts bet ≥ 0.95 |
| C4 sizing menu | PASS | menu {5,20}: nuts put 0.5 % on size 5; EV0 3.315 vs closed-form 3.333 (err 0.019 ≤ NashConv 0.104) | small size ≤ 5 %, value within NashConv |
| C5 convergence river | PASS | catalog river spot: 2.95→0.20 (25→1600 iterations) | last/first ≤ 0.5 |
| C5 convergence flop (allstreet) | PASS | 36.2→3.61 (10→640) | ≤ 0.5 |
| C5 convergence turn (multistreet) | PASS | 28.4→3.02 (10→640) | ≤ 0.5 |
| C5 convergence preflop HU | PASS | 0.888→0.041 (10→2560) | ≤ 0.5 |
| C5 convergence preflop 3p | PASS | 3.09→0.055 (10→2560), independent n-player NashConv | ≤ 0.5 |
| C6 BR oracle agreement | PASS | 13 comparisons (Kuhn ×5, river toy ×3, river catalog, flop, turn, preflop HU, preflop 3p): repo `nash_conv` / 3p `unilateral_deviation_certificate` vs the benchmark's own infoset-consistent BR; max rel err 1.4e-14 | ≤ 1e-9 |
| C7 3-player Kuhn | PASS | NashConv 0.0895→0.00217 (100→10k); seat1 −0.0201 vs −1/48 (err 7e-4 ≤ NashConv); seats 0 and 2 inside the analytic ranges | NashConv ≤ 0.02, seat1 err ≤ NashConv |
| C8 determinism | PASS | adapter repeat solves give identical `to_json` (minus wall time) and `params_hash`; catalog stable; CFR, n-player CFR and MCCFR(seed) repeatable; MCCFR seeds 0≠1 | exact equality |
| C9 param sensitivity (R1) | PASS | iterations, pot, bet size, villain weight and stack (allstreet) each change `params_hash` and the strategy/Q (Q deltas 1.2–62 chips) | every perturbation changes hash and output |
| C10 score cross-check | PASS | 18 spots (12 Kuhn plus 1 per other family, all 7 families), 58 plays (every pure action plus the solver mix): Q, σ, pot, EV loss, score and grade from an independent solve plus a Q-oracle; max abs error 0.0 | ≤ 1e-9 |
| C11 practice solve quality | **PARTIAL** | exploitability (NashConv/n)/pot at the family default: kuhn 0.865 %, river-oop 0.254 %, river-ip 0.868 %, preflop-hu 0.340 %, preflop-3max 0.143 % (5000 iterations), **flop-cbet 1.122 % (PARTIAL)**, turn 0.580 % | ≤ 1 % pass, ≤ 5 % partial |
| C12 practice timing | PASS | cold solves 0.31–11.4 s at the family defaults (3-max 11.4 s at 5000 iterations, flop-cbet 3.8 s, river 1.6–2.1 s, turn 2.8 s) at load ≈ 3 | ≤ 20 s (contract), ≤ 90 s partial |
| C13 equity / ICM | PASS | AhKh vs QsQc on 2h7h9cJd = 15/0/29 (hand-counted); royal board = 1 tie; ICM vs Malmuth-Harville over 7 cases, err 7.8e-14 | exact / ≤ 1e-9 |
| C14 scale | **FAIL** | river with one bet size: s/iteration grows as deals^1.48; 48 combos/side (2113 deals) = 20.5 s/iteration (measured); projected 100 combos/side ≈ 181 s/iteration → 1.81e5 s per 1000 iterations | ≤ 60 s (≤ 3600 s partial) |
| C15 all-in | PARTIAL | zero-sum (96 terminals, 64 all-in showdowns), NashConv 19.3→6.0 (10→160). Defect: `multistreet` offers `RAISE(target == call target)` facing an all-in (24 such actions), then gives the all-in seats CHECK-only decision nodes (48). Value gap call vs that "raise" = 0.0. The W5 practice adapter merges these into `CALL` in its output, but this criterion checks the engine tree | no degenerate RAISE, no decisions for all-in seats |
| C16 mixed strategy | PASS | Kuhn P1 J-bluff and Q-call, river-toy air bet (3 sizes) all strictly inside (0.05, 0.95) | — |

## Concrete gap list

1. **Scale.** Pure-Python full-tree vanilla CFR is superlinear in deals. A 100-combo river with one size
   needs about 3 min per iteration on this host. Fixing this needs vectorised/array CFR (range-vs-range
   per public node, not per deal), CFR+/DCFR, and card abstraction. The W5 flat vectorised trainer
   (`practice/nplayer_metrics.py`) covers only the n-player preflop backend.
2. **flop-cbet** is at 1.122 % pot at its 200-iteration default. More iterations would get it under
   1 % (C5-flop shows NashConv still falling at 640 iterations); it was out of scope in W5.
3. **multistreet all-in tree** (C15): drop `RAISE` when target == call target, and skip decisions
   when the actor has 0 behind. This is value-neutral. Since W5 the practice adapter merges the
   pseudo-raise into `CALL` (fail-closed if the Qs differ), so users can no longer pick it, but
   `multistreet.py` itself is unchanged and C15 stays PARTIAL.
4. **MCCFR coverage.** Only the allstreet backend (`flop-cbet`) accepts `external-sampling-mccfr` in
   practice; every other backend is vanilla CFR.
5. **ICM is evaluator-only.** No solver or practice path uses ICM utilities.
6. **Sizing.** Practice spots offer one solved size. User sizes off the menu are snapped, never solved.
   There is no automatic size selection in the practice solve path.
7. **Abstraction scope.** There are tiny explicit ranges (≤ 5 combos/side), runout subsets (≤ 4), and
   preflop leaves settled by sampled equity. 3-way play exists only preflop.
8. **Coverage of C10/C11.** Only the first spot per non-Kuhn family is re-derived and graded. For
   `preflop-3max-open` that is `a4b66447a35b` (0.143 %); the slowest-converging 3-max spot,
   `ce0eddffc9af`, measured 0.861 % in the W5 repair report, still under 1 %.
9. **Scope-cap text (fixed in W6).** The 3-max capability gap string in `benchmark.py` said the adapter
   reports `nash_conv=None`; it was corrected in W6 (string-only, no verdict change) in `benchmark.py`,
   `results.md` and `results.json`.

## Changes since the W4 run

| item | W4 run (`ed886c8`, dirty) | W5 run (`2a6f57c`, clean) |
|---|---|---|
| `preflop-3max-open` default | 100 iterations, 7.18 % pot, `nash_conv=None` | 5000 iterations (flat trainer), 0.143 % pot, finite NashConv |
| C11 | FAIL | PARTIAL (flop-cbet 1.122 % only) |
| 3-max / preflop capabilities | FAIL / FAIL | PARTIAL / PARTIAL |
| C12 max cold solve | 11.8 s (load ≈ 5) | 11.4 s (load ≈ 3) |
| C14 projection | 2.4e5 s (deals^1.44, 29 s/iter at 48 combos) | 1.81e5 s (deals^1.48, 20.5 s/iter at 48 combos); timing noise, no scale work |
| C15 | PARTIAL | PARTIAL (engine unchanged; practice output merges the pseudo-raise) |
| overall / correctness-only | FAIL / PARTIAL | FAIL / PARTIAL |

## Reproduce

```
scripts/solver_eval.sh quick              # ~35 s here, temp dir
scripts/solver_eval.sh full               # ~8 min here (499 s at W5), rewrites results.json / results.md
.venv/bin/python -m pytest -q tests/test_solver_evaluation.py
```

The benchmark imports solver modules directly. Practice is used only through its public API:
`generate_catalog`, `SolverAdapter.solve`, `score_play`, and `preflop_config` (the last one only to build
the identical game for the independent recomputation). No numbers are copied: every reference is a
closed form or an enumeration computed at run time.
