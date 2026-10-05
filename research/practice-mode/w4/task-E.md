# W4 task E — solver-evaluation benchmark

Owner files (exclusive): `research/solver-evaluation/{benchmark.py,games.py,results.json,results.md,REPORT.md}`,
`scripts/solver_eval.sh`, `tests/test_solver_evaluation.py`. No `src/` edits; not committed.

## What was built
- `benchmark.py --mode quick|full [--out DIR] [--only ids]` runs **20 criteria (C1–C16)**. Their
  thresholds are declared up front in `THRESHOLDS`. It also grades the 8 mission capabilities and writes
  `results.json` (schema `solver-evaluation-v1`: host, git commit/branch/dirty, UTC start/finish,
  thresholds, per-criterion evidence + wall time, capabilities, overall/correctness verdicts) and
  `results.md`.
- `games.py` holds the benchmark-owned independent oracles:
  - 3-player Kuhn game (analytic −1/48 family)
  - n-player infoset-consistent best response / NashConv
  - action-value (Q) oracle
  - Malmuth-Harville ICM enumeration
  - a memoizing state proxy
- Verdict rule: capability = worst(evidence criteria / per-family sub-verdicts, scope cap);
  overall = worst(everything). A separate `correctness_verdict` excludes default-solve quality,
  timing and scale.
- Quick mode takes 25–60 s and is used by `tests/test_solver_evaluation.py` (5 tests). The tests check:
  - the benchmark runs and the JSON round-trips
  - the schema, with < 120 s wall time
  - the worst-case rule
  - C1 Kuhn PASS against −1/18 with NashConv decreasing
  - the threshold helper
- Full mode was run once (319 s). Outputs are saved in `research/solver-evaluation/`.

## Result (full run, 2026-10-05T05:39Z, commit ed886c8, dirty tree)
**Overall FAIL; correctness PARTIAL.** Capabilities:
- FAIL: 2-player NL, 3-max, preflop, postflop
- PARTIAL: multi-street, ICM, sizing
- PASS: mixed strategy

Failing / partial criteria:
- C14 scale **FAIL**: projected ≈ 2.4e5 s per 1000 iterations at 100 combos/side; 29 s/iteration measured at 48.
- C11 practice quality **FAIL**: preflop-3max-open is 7.18 % pot exploitable at its 100-iteration default.
  flop-cbet is 1.12 % (PARTIAL).
- C15 all-in **PARTIAL**: multistreet offers a RAISE equal to CALL facing an all-in and gives all-in
  seats CHECK-only nodes. This is value-neutral.

Everything else PASSes:
- Kuhn −1/18 (slope −0.52)
- MCCFR
- river closed form (freq err ≤ 0.015)
- sizing menu
- convergence on river/flop/turn/HU-preflop/3p-preflop
- BR oracle agreement 1.4e-14
- 3p Kuhn −1/48
- determinism
- R1 sensitivity
- practice score cross-check exact (0.0 error, 58 plays, 7 families)
- timing ≤ 11.8 s
- equity/ICM
- mixed strategies

Full table and gap list: `research/solver-evaluation/REPORT.md`.

## Notes / decisions
- Practice is used only via its public API (`generate_catalog`, `SolverAdapter.solve`, `score_play`,
  `preflop_config`). Families come from the live catalog, so C10–C12 track tasks A/B's state at run time.
- 3-max NashConv is measured with the benchmark's own n-player oracle. It is cross-checked against the
  repo's exhaustive `unilateral_deviation_certificate`, because the adapter reports `None` for 3-max.
- Tests: `tests/test_solver_evaluation.py` 5 passed. Full suite `.venv/bin/python -m pytest -q`: **1136 passed** (baseline 1026, plus other W4 tasks' tests running alongside), 604 s.
