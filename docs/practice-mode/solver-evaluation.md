# How to read the solver evaluation

The benchmark in `research/solver-evaluation/` checks how far the solver behind practice mode can
be trusted. It compares the solver against independent references and measures convergence,
default-solve quality, timing and scale. Then it assigns PASS / PARTIAL / FAIL to each criterion
and to 8 capability areas.

**Source of truth:** `research/solver-evaluation/results.md` (tables) and `results.json`
(machine-readable: host, git commit, timestamps, thresholds, all evidence). Both are rewritten
by every full run. `research/solver-evaluation/REPORT.md` is the written verdict and gap list.
If anything on this page disagrees with `results.md`, `results.md` is correct.

## Files

| file | content |
|---|---|
| `benchmark.py` | criteria C1–C16 (20 criterion ids), `THRESHOLDS`, `CAPABILITY_RULES`, `VERDICT_RULE`, the run modes |
| `games.py` | the benchmark's own oracles: 3-player Kuhn, n-player best response / NashConv, a Q-value oracle, Malmuth-Harville ICM |
| `results.json`, `results.md` | output of the last full run |
| `REPORT.md` | human verdict, per-criterion measurements, concrete gap list |
| `scripts/solver_eval.sh` | wrapper; sets temp `POKER_PRACTICE_CACHE_DIR` / `POKER_PRACTICE_DATA_DIR` |
| `tests/test_solver_evaluation.py` | runs quick mode inside the test suite |

## Running it

```bash
scripts/solver_eval.sh quick              # ~35 s here (25-60 s); writes to a temp dir, prints the path
scripts/solver_eval.sh quick /tmp/se      # quick mode into a chosen dir
scripts/solver_eval.sh full               # ~8 min on the 2-CPU host (499 s at W5); REWRITES research/solver-evaluation/results.{json,md}
.venv/bin/python research/solver-evaluation/benchmark.py --mode quick --out /tmp/se --only C1-kuhn-analytic
.venv/bin/python -m pytest -q tests/test_solver_evaluation.py
```

Quick mode uses fewer iterations and checkpoints, and covers only 3 practice families in C10–C12.
Its verdicts can differ from full mode. Only full-mode output belongs in `results.md`.

## Verdict levels

- **PASS**: the measured value meets the criterion's PASS threshold.
- **PARTIAL**: it misses PASS but meets the PARTIAL threshold. For some criteria the PARTIAL
  condition is a separate rule. For example, C15 is PARTIAL when the value checks pass and the
  structural defect is value-neutral.
- **FAIL**: it misses both thresholds, or the measurement was not finite.

Thresholds are fixed in `THRESHOLDS` before the run. Every `results.json` records the exact values
used. Examples:

| criterion | metric | PASS | PARTIAL |
|---|---|---|---|
| C1 Kuhn analytic | \|EV0 − (−1/18)\|, final NashConv, log-log slope | err ≤ 1e-3, NashConv ≤ 0.02, slope ≤ −0.35 | err ≤ 1e-2 |
| C3 river closed form | frequency error vs B/(P+B), P/(P+B) | ≤ 0.03 | ≤ 0.08 |
| C5 convergence | NashConv(last) / NashConv(first checkpoint) | ≤ 0.5 | ≤ 1.0 |
| C6 BR oracle | relative error vs independent best response | ≤ 1e-9 | ≤ 1e-6 |
| C10 score cross-check | abs error of Q/σ/score/grade vs recomputation | ≤ 1e-9 | ≤ 1e-6 |
| C11 practice solve quality | 100 × (NashConv / n_players) / pot at the family default | ≤ 1 % pot | ≤ 5 % pot |
| C12 practice timing | cold `SolverAdapter.solve` seconds | ≤ 20 s | ≤ 90 s |
| C14 scale | projected s for 1000 iterations, 100 combos/side river | ≤ 60 s | ≤ 3600 s |

## The worst-case rule

The rule is quoted from `VERDICT_RULE`:

> Each criterion is graded from its THRESHOLDS entry. A capability's verdict is the worst of its
> evidence criteria and its documented scope cap. overall = worst(all criteria + all capabilities)
> with FAIL > PARTIAL > PASS. correctness_verdict = worst over the correctness criteria only
> (excludes timing, default-solve quality and scale).

What this means in practice:

- **Capability = worst(evidence, scope cap).** Each capability has a fixed list of evidence
  criteria. Some are per-family sub-verdicts such as `C11-practice-solve-quality[flop-cbet]`.
  Each capability also has a *scope cap*: the best verdict it can reach given what the solver
  structurally covers. Every capability except "mixed strategy" is capped at PARTIAL. Tiny explicit
  ranges, a single bet size, runout subsets and equity-settled preflop leaves rule out a PASS
  regardless of how accurate the numbers are.
- **Overall = worst of everything.** One FAIL anywhere (one criterion, or one family's sub-verdict)
  makes the overall verdict FAIL. That is why overall FAIL can coexist with 17 of 20 criteria at PASS.
- **Correctness-only verdict** drops C11 (default-solve quality), C12 (timing) and C14 (scale). It
  answers whether the solver computes the right thing where it can be checked, separately from
  whether it is fast or converged enough at the shipped defaults.

Read the two headline verdicts together:
- `overall`: is this a complete, up-to-par solver for the listed capabilities? Currently no.
- `correctness`: are the numbers it produces right? Yes where independently checkable, apart from the
  value-neutral all-in tree defect (C15).

## Current verdict (results.md at `72f0053`, tag `practice-mode-w5`)

The numbers below come from `research/solver-evaluation/results.md` as committed at `72f0053`. The
full run was recorded on 2026-10-05 (07:50:44 → 07:59:03 UTC, 499 s) against commit `2a6f57c`
(the W5 code) with a clean tree (`dirty=False`) on a 2-CPU host, load ≈ 3 at start. `72f0053`
changes only `results.json` / `results.md`, so the numbers describe the code at the tag.

- **Overall: FAIL.** **Correctness-only: PARTIAL.**
- Criteria: 17 PASS, 2 PARTIAL (C11 practice solve quality, C15 all-in), 1 FAIL (C14 scale).

| failing / partial item | measured | why |
|---|---|---|
| C14 scale: FAIL | ≈ 20.5 s/iteration measured at 48 combos/side; s/iteration grows as deals^1.48; projected ≈ 181 s/iteration → 1.81e5 s per 1000 iterations at 100 combos/side | pure-Python full-tree vanilla CFR is superlinear in deals |
| C11 practice solve quality: PARTIAL | `flop-cbet` 1.122 % pot at its 200-iteration default (PARTIAL). Every other family PASS: `preflop-3max-open` 0.143 %, others 0.25–0.87 % | flop-cbet needs more iterations; not changed in W5 |
| C15 all-in: PARTIAL | `multistreet` offers 24 `RAISE` actions whose target equals the call target when facing an all-in, and gives all-in seats 48 CHECK-only decision nodes; value gap 0.0 | engine-tree defect, value-neutral. Practice output merges the pseudo-raise into `CALL`, but the benchmark checks the engine tree |

Capabilities at that commit:

| capability | verdict |
|---|---|
| 2-player NL | FAIL (C14 FAIL; C15 PARTIAL; C11 `flop-cbet` PARTIAL; cap PARTIAL) |
| 3-max | PARTIAL (all evidence PASS incl. C11 `preflop-3max-open` 0.143 %; cap PARTIAL: preflop only) |
| preflop | PARTIAL (all evidence PASS; cap PARTIAL: equity-settled leaves) |
| postflop | FAIL (C14 FAIL; C11 `flop-cbet` PARTIAL; cap PARTIAL) |
| multi-street | PARTIAL (C11 `flop-cbet` PARTIAL; cap PARTIAL) |
| ICM | PARTIAL (evaluator only; no ICM-aware solving) |
| mixed strategy | PASS |
| sizing | PARTIAL (fixed menus, one size per practice spot) |

Note: since W5 the adapter reports a finite n-player NashConv for 3-max (`nplayer_metrics.nash_conv_nplayer`,
equal to the benchmark oracle `games.nash_conv_n` in `tests/test_practice_w5_repairs.py`); the stale
"nash_conv=None" scope-cap string in `benchmark.py`/`results.*` was corrected in W6 (text only). The
practice-spot comparisons are not part of the recorded C6 evidence (C6 runs before C10 collects
them), but the value captured from the live API on `preflop-3max-open/a4b66447a35b`
(0.012866 chips → 0.143 % pot) matches the C11 oracle figure for that spot.

What changed versus the W4 run (recorded at `ed886c8`, dirty): `preflop-3max-open` went from
7.18 % (100 iterations, FAIL) to 0.143 % (5000 iterations, PASS), so C11 moved FAIL → PARTIAL and
the 3-max and preflop capabilities FAIL → PARTIAL. The C14 projection moved from 2.4e5 s to
1.8e5 s purely from host timing noise (no scale work was done). Overall and correctness-only
verdicts are unchanged.

What passes, all against independent references computed at run time:
- Kuhn value −1/18 under CFR (C1) and MCCFR (C2).
- The polarized-river closed form within 0.015 (C3) and the sizing-menu value (C4).
- NashConv decreasing on all five backends (C5).
- The repo's best response matching an independent oracle to 1.4e-14 (C6, 13 comparisons).
- The 3-player Kuhn −1/48 family (C7).
- Determinism (C8) and parameter sensitivity (C9).
- Practice Q / score / grade re-derived with error 0.0 over 58 plays on 18 spots (C10).
- Cold solves at most 11.4 s at the family defaults (C12; 3-max 11.4 s, flop-cbet 3.8 s).
- Exact equity and ICM (C13).
- Strictly mixed equilibria reproduced (C16).

## Reading `results.json`

The top-level keys are `schema` (`solver-evaluation-v1`), host/git/timestamps, `thresholds`,
`verdict_rule`, per-criterion entries (verdict, evidence, wall time), `capabilities` (verdict,
scope cap, evidence list, gaps), `overall` and `correctness_verdict`. Check `git` and `dirty`
first: if the commit there is not the one you are evaluating, the numbers are stale.

## What the verdict means for practice users

- Spots are tiny toy abstractions of real poker: ranges of 3–5 combos per seat, one bet size, a
  few runouts. They do not reproduce full-range GTO Wizard solutions.
- Grades are exact with respect to the solve that was run (C10). That solve is only as converged
  as its iteration count. `solver_self_loss` in each score shows the solver noise. Raise the
  iterations (UI Re-solve, `solve.iterations`, or `warm --iterations`) when it is large.
- At the family defaults every family is ≤ 0.87 % pot exploitable except `flop-cbet` (≈ 1.12 %).
  The 3-max family now reports its NashConv, so the UI shows it in the provenance.
