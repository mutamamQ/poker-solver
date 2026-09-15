# Phase 3 mission: GTO Wizard feature parity (solver backend)

Goal: extend the poker-solver backend toward **GTO Wizard feature parity** on the tractable solver-backend surface. Build it correctly, ground accuracy in independent references, and have subagents audit and cross-check each other. Work in /home/genomix-node/poker-solver. The BryantGPT subagent route is confirmed working (see PROBE_REPORT.md) — use tool-enabled parallel subagents; parent-verify every child claim.

## Non-negotiable ground rules
- All prior tests stay green (Phase 1 = 80, Phase 2 = 185). Add, don't break.
- Parallel subagents: batches of up to 10 in ONE delegate_task call. Exclusive file ownership, absolute paths, named required tools, explicit acceptance test. Reviewer tasks: no extra files beyond their report; prefer write_file + pytest over python -c one-liners.
- **Adversarial cross-check after EVERY development batch (hard rule):** whenever an implementation sub-batch finishes, BEFORE starting the next feature batch, dispatch a DIFFERENT set of subagents (fresh, not the authors) to adversarially audit the new code — they must run the code and tests, attack the newest module, and cross-check it against the rest of the codebase. A batch is not "done" until a non-author adversarial wave signs off. Log each audit in review/phase3/.
- Use as many BryantGPT subagents as possible at once (concurrency cap = 10).
- Accuracy claims need a named reference (analytical value, independent implementation, or brute force) + tolerance. No gut answers.
- Honesty: where a GTO Wizard feature is research-grade (neural DDLS, full 9-way, PLO), either implement a bounded+correct version or document a clear, justified scope boundary. Never silently claim full parity you didn't build.

## Wave A — Feature research (parallel, up to 10 bryant subagents)
For each GTO Wizard feature below, research: exact semantics, what "correct" means, a reference to validate against, and tractability in pure Python. Write research/phase3/<feature>.md. The feature list (use GTO Wizard's own names):
1. Preflop solving (heads-up) — deal, positions, blind/ante structure, raise tree.
2. Bet sizing modes: **Automatic** (solver picks best-EV sizes), **Dynamic** (choose N sizes, solver keeps top-EV), **Fixed** (exact sizes). Input units: % of pot, geometric (e), multiple (x), big blinds (bb).
3. Range editor: add/remove hands, per-hand weights, save/load named ranges, import/export range text.
4. Tree / node editing: add/remove actions, change sizes at specific decision nodes.
5. Nodelocking: lock a player's range/strategy at a node for exploitative solving.
6. Player profiles: exploitative tendencies (maniac, calling station, loose opener, etc.) as constraints on the opponent's strategy.
7. Game structure: stack depth, pot ratio, effective stack, blinds, per-player antes, straddles (standard/double/Mississippi), limps, cold-calls (CC 2b, CC 3b+).
8. Rake: chip-EV vs raked games (per-player rake, total rake, min/max).
9. Multiway: heads-up and 3-way postflop; up to 9-way preflop (document the 3-max postflop / 9-max preflop boundary).
10. ICM tournaments + bounties (PKO/TKO/Mystery) — scope: is this tractable, or a documented boundary?
11. Engine modes: **Classic** (street-by-street, full accuracy) vs **Fast / DDLS** (depth-limited + neural value approx). Scope: implement Classic exactly; assess DDLS feasibility.
12. Range/strategy display: per-hand EV + action breakdown (range tables), frequency breakdowns — the "our own range display" + opponent-range view.
13. Opponent range inference: given observed actions, update the opponent's range (exploitative / Bayesian).
14. Prefill + spot library: a small set of canonical spot presets (BTN vs BB 25bb, SB vs BB 15bb, etc.) as example configs.
15. Accuracy/validation method per feature: what independent oracle or reference validates it.

## Wave B — Design + scope decision (you, with subagent design help)
Read Wave A. Write ARCHITECTURE_PHASE3.md: the exact feature set to build, tiered as:
- **Tier 1 (must, correctness-critical):** preflop heads-up, Fixed/Dynamic/Automatic sizing, range editor, node editing, nodelocking, profiles, rake, 3-way postflop, range tables (our + opponent), opponent range inference.
- **Tier 2 (extended):** full multiway, ICM, bounties, DDLS/Fast, straddles/limps/cold-call full tree.
- **Tier 3 (research-grade, document boundary):** 9-way, PLO, neural value approximation, full presolved library.
For each: the module, exclusive file ownership, the acceptance test, and the accuracy reference. Give a clear "implemented vs documented-boundary" matrix.

## Wave C — Implementation (parallel, up to 10 subagents, exclusive modules)
Build Tier 1 fully (correct + tested). Build Tier 2 where justified. For Tier 3, implement a bounded version OR add a clear, tested scope note + working approximation. Expected deliverables:
- Preflop street + full blind/ante/position structure; raise tree with the three sizing modes and %/e/x/bb units
- Range editor (weights, save/load, import/export)
- Node/tree editing + nodelocking + player profiles
- Rake (chip-EV and raked)
- 3-way postflop solving
- Range tables: per-hand EV + action for our range AND opponent range
- Opponent range inference from observed actions
- CLI subcommands + strict JSON API for every new feature; keep Phase 1+2 API stable
- A small canonical spot preset library (examples/)
Each module ships with its own pytest tests.

## Wave D — Adversarial accuracy wave (parallel, up to 10 subagents)
Genuinely adversarial, cross-checking, tool-enabled:
- Adversarial reviewers: each attacks one module (preflop, sizing modes, range editor, nodelock/profiles, rake, multiway, range tables, inference) — must RUN the code + tests, find bugs/invariants/off-by-ones, report with reproduction.
- Cross-checkers: independently verify agreement between (a) our solver vs an independent reference on a known preflop/postflop spot, (b) the three sizing modes vs each other at the same EV, (c) nodelocked solution vs a hand-built constraint check, (d) range tables vs the raw per-hand strategy, (e) opponent-range inference vs a manual Bayes calculation on a tiny game. Each writes a signed-off review/phase3/<area>-<role>.md.
- Collect, dedupe, drive a fix wave for every confirmed bug, then re-run Wave D until a full wave reports zero blocking findings.

## Definition of done (all verified, all evidenced)
- Full pytest green (Phase 1 + 2 + 3), including regression, determinism, benchmark, and known-answer fixtures.
- CLI + strict JSON API for every new feature; backward-compatible with Phase 1+2.
- Accuracy evidence: independent-reference agreement per feature, cross-checker sign-offs in review/phase3/.
- ARCHITECTURE_PHASE3.md implemented-vs-boundary matrix; README updated with the full GTO Wizard feature list (implemented vs documented-boundary); SWARM_REPORT.md updated with the Phase 3 swarm findings.
- PROGRESS.md updated.
