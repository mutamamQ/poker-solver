# How to read the solver evaluation

The benchmark in `research/solver-evaluation/` checks how far the solver behind practice mode can
be trusted. It compares the solver against independent references and measures convergence,
default-solve quality, timing and scale. Then it assigns PASS / PARTIAL / FAIL to each criterion
and to 8 capability areas.

**Source of truth:** `research/solver-evaluation/results.md` (tables) and `results.json`
(machine-readable: host, git commit, timestamps, thresholds, all evidence). Both are rewritten
by every full run. `research/solver-evaluation/REPORT.md` is the written verdict and gap list.
If anything on this page disagrees with `results.md`, `results.md` is correct. A repair task may
change C11/C15 after this page was written.

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
scripts/solver_eval.sh quick              # 25-60 s here; writes to a temp dir, prints the path
scripts/solver_eval.sh quick /tmp/se      # quick mode into a chosen dir
scripts/solver_eval.sh full               # ~5 min on the 2-CPU host; REWRITES research/solver-evaluation/results.{json,md}
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

## Current verdict (results.md as committed at `5a3e61f`)

The numbers below come from `research/solver-evaluation/results.md` as committed at `5a3e61f`.
The run was recorded on 2026-10-05 against commit `ed886c8` with the W4 changes present in the worktree
(`dirty=True`) on a 2-CPU host under load ≈ 5. Re-run `scripts/solver_eval.sh full` and read the
regenerated `results.md` for current values.

- **Overall: FAIL.** **Correctness-only: PARTIAL.**
- Criteria: 17 PASS, 1 PARTIAL (C15 all-in), 2 FAIL (C11 practice solve quality, C14 scale).

| failing / partial item | measured | why |
|---|---|---|
| C11 practice solve quality: FAIL | `preflop-3max-open` 7.179 % pot at its 100-iteration default. `flop-cbet` 1.122 % (PARTIAL). Others 0.25–0.87 % | the default iteration budget is too low for 3-max. The solver converges with more iterations (C5 3p: 3.09 → 0.055 over 10 → 2560 iterations) |
| C14 scale: FAIL | ≈ 29 s/iteration measured at 48 combos/side; projected 2.4e5 s per 1000 iterations at 100 combos/side | pure-Python full-tree vanilla CFR is superlinear in deals (≈ deals^1.44) |
| C15 all-in: PARTIAL | `multistreet` offers a `RAISE` whose target equals the call target when facing an all-in, and gives all-in seats CHECK-only decision nodes; value gap 0.0 | structural defect, value-neutral |

Capabilities at that commit:

| capability | verdict |
|---|---|
| 2-player NL | FAIL (C14 FAIL, C15 PARTIAL, flop-cbet C11 PARTIAL; cap PARTIAL) |
| 3-max | FAIL (C11 `preflop-3max-open` FAIL; cap PARTIAL) |
| preflop | FAIL (C11 `preflop-3max-open` FAIL; cap PARTIAL) |
| postflop | FAIL (C14 FAIL; cap PARTIAL) |
| multi-street | PARTIAL |
| ICM | PARTIAL (evaluator only; no ICM-aware solving) |
| mixed strategy | PASS |
| sizing | PARTIAL (fixed menus, one size per practice spot) |

What passes, all against independent references computed at run time:
- Kuhn value −1/18 under CFR (C1) and MCCFR (C2).
- The polarized-river closed form within 0.015 (C3) and the sizing-menu value (C4).
- NashConv decreasing on all five backends (C5).
- The repo's best response matching an independent oracle to 1.4e-14 (C6).
- The 3-player Kuhn −1/48 family (C7).
- Determinism (C8) and parameter sensitivity (C9).
- Practice Q / score / grade re-derived with error 0.0 over 58 plays (C10).
- Cold solves at most 11.8 s (C12).
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
- The 3-max family at its default budget is noticeably exploitable (≈ 7 % pot at `5a3e61f`). Its
  provenance has no NashConv, so the UI cannot show this.
