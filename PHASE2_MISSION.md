# Phase 2 mission: feature-complete, accurate poker-solver backend

Context: Phase 1 delivered a working single-street solver (vanilla CFR), Kuhn, river-spot, equity, evaluator, CLI — 80/80 tests green. Phase 2 makes the BACKEND feature-complete against industry-standard poker solvers and proves accuracy against independent references. Continue in /home/genomix-node/poker-solver. The BryantGPT subagent route is confirmed working for tool-enabled coding (see PROBE_REPORT.md) — use it for the parallel work.

## Ground rules
- Keep all 80 existing tests passing at the end (regression gate). You may extend, not delete.
- Parallel subagents: dispatch in batches of up to 10 in ONE delegate_task call. Each task: exclusive file ownership (absolute paths), explicit required tools, explicit acceptance test. Reviewer tasks: prohibit extra files beyond their owned report; prefer `write_file` + `pytest` over `python -c` one-liners (Agent D lesson from the probe).
- Every subagent's "done" claim must be parent-verified by you: run the tests yourself, read the artifacts yourself.
- Accuracy claims need a named reference (published value, independent implementation, or brute force) and tolerance — no gut answers.

## Wave A — Research: what "feature complete" means (parallel, up to 8 bryant subagents, tool-free or tool-enabled)
Write to research/phase2/<topic>.md. Cover at minimum:
1. Feature inventory of industry-standard solvers (PokerStove, PokerEquity, GTO+ / GTD, CFR implementations like cfr/pypoker, OpenSpiel endgame) — list concrete features: multi-street solving, bet-sizing (limit/all-in/pot-limit), 2p vs 3p, ranges/weights, exploitability metrics, strategy/JSON output, performance techniques (MCCFR, incremental CF, reachability caching, isomorphic CFR).
2. Accuracy references usable as fixtures: published Kuhn values, published 2p river-spot EVs, equity tables (PokerStove/Treys), and how solvers validate themselves (exploitability/Nash convergence, best-response).
3. MCCFR vs vanilla CFR: expected speedup, when MCCFR is safe (zero-sum, single-action-per-inform-set caveats), what breaks it (multi-bet streets, non-zero-sum).
4. Multi-street heads-up modeling: info-set construction, reachability, action sets (bet/call/fold, pot-limit sizing), terminal payouts.
5. Exploitability computation for 2p zero-sum: best-response EV via forward induction, formula, pitfalls.
6. 3-player support: what changes (non-zero-sum, MCCFR inapplicable, strategy space), or argue for a documented 2p scope.
7. Determinism and performance: how to keep solves reproducible, expected runtime for 1 street of 2p river, and scaling to full flop/turn/river.
8. Cross-validation strategy: independent second implementation for small games (e.g., brute-force minimax or a reference CFR) to cross-check EV/strategy, plus exploitability thresholds for "100% correct" claims.

## Wave B — Design + gap reconciliation (you, with subagent design help if useful)
Read Wave A, then write ARCHITECTURE_PHASE2.md: the exact feature set to build, the module plan with exclusive file ownership, the accuracy/acceptance gates, and the 2p-vs-3p scope decision with rationale.

## Wave C — Implementation (parallel, up to 10 subagents, exclusive modules)
Build the Phase 2 backend per ARCHITECTURE_PHASE2.md. Expected features (final list per your design):
- Multi-street (flop/turn/river) heads-up spot solving with bet/call/fold and pot-limit/all-in sizing
- MCCFR (fast path) with vanilla CFR as reference path; expose which is used
- Exploitability + best-response computation for solved strategies
- Ranges with weights (already partial — make it first-class and tested)
- Programmatic JSON API (input spot spec → strategy + values + exploitability) and CLI subcommands for each new feature
- 3-player: implement if Wave A justifies; otherwise document the scope boundary explicitly in README + ARCHITECTURE
- Determinism (same input → same output; add a test that solves twice and compares hashes)
- Performance: incremental CF or caching where justified; add a runtime benchmark test with a sane ceiling
Each module ships with its own pytest tests. Keep the public API stable for Phase 1 features.

## Wave D — Adversarial accuracy wave (parallel, up to 10 subagents)
Genuinely adversarial, cross-checking, tool-enabled:
- Adversarial reviewers: each attacks one module (multi-street, MCCFR, exploitability, ranges, API) — must RUN the code and tests, find bugs/invariants/off-by-ones, report with reproduction.
- Cross-checkers: independently verify agreement between (a) MCCFR vs vanilla CFR EV on the same spot (tolerance), (b) our multi-street solver vs a brute-force/reference equilibrium on a small game, (c) equity vs the Treys/PokerStove fixtures in research/. Each writes a signed-off review/phase2/<area>-<role>.md.
- Collect, dedupe, drive a fix wave for every confirmed bug, then re-run Wave D on fixed code until a full wave reports zero blocking findings.

## Definition of done (all verified, all evidenced)
- Full pytest green (Phase 1 + Phase 2), including regression, determinism, benchmark, and known-answer fixtures.
- CLI + programmatic API for: evaluate, equity, solve (multi-street), exploitability, JSON in/out.
- Accuracy evidence: exploitability numbers per solved spot, known-value fixtures passing, MCCFR≈vanilla agreement, cross-checker sign-offs in review/phase2/.
- README.md updated with the full feature list, usage, accuracy section; SWARM_REPORT.md updated with the Phase 2 swarm usage findings.
- PROGRESS.md updated.
