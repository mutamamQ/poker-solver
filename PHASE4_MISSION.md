# PHASE 4 MISSION — GTO Wizard Remaining Feature Parity + Web UI

**Baseline:** Phase 1+2+3 complete. 398/398 tests green. Git repo at `origin/main`, tag `phase3-398-green`.
**Orchestrator:** gpt-5.6-sol (openai-codex). **Subagents:** BryantGPT (`bryant` provider, `15d8cc8844/CLAUDE_V4_5_SONNET`).
**Wave width: EXACTLY 6 BryantGPT subagents max per wave (user-specified).** Do not exceed 6 concurrent children.

## Scope (implement ALL of the following, in the order listed)

### S1. Automatic all-street postflop (remove caller-supplied continuation values)
Flop→turn→river solving where the engine automatically computes continuation values at tree leaves (rollout recursion or bounded value function — choose via design wave). The caller must no longer supply continuation values for standard full-street solves.
- **Acceptance:** solve a flop spot with a declared turn/river tree and NO caller continuations; zero-sum holds; policies sum to 1; on a fixed tree, auto-continuation results are within a derived bound of the explicit-continuation result; convergence-vs-iterations sweep if two methods differ.
- **Invariant:** zero-sum on every multiway-capable configuration; determinism (same input/seed → same output).

### S2. Multiway postflop 4–9 players
Generalize the 3-player one-round postflop state machine to 2–9 players. Exact side-pot/rake settlement, reach probabilities, unilateral-deviation diagnostic for N players.
- **Acceptance:** 4-, 5-, 9-player spots solve; zero-sum including side pots; odd-chip settlement exact (integer ledger); deviation diagnostic runs for 5+ players; all prior 3-player tests still green.

### S3. Multiway preflop 2–9 players
Preflop tree builder: positions, blinds/antes/straddles (standard, double, Mississippi), limps, SB completes, cold-calls, 3-bet/4-bet/5-bet+ sizing rules per position (IP/OOP, per cold-caller), custom stacks per player, finite weighted deals.
- **Acceptance:** HU + 6-max + 9-max preflop spots solve with the sizing rules above; forced-post/refund ledgers exact; raise-to street commitment honored; straddle variants produce distinct, verifiable trees; zero-sum on closed leaves with supplied/derived continuations.

### S4. Automatic abstraction
Automatic hand abstraction to keep solves tractable (e.g., category-based or blocker-aware abstraction chosen via design wave), with a documented abstraction policy and determinism.
- **Acceptance:** an abstracted solve of a large spot completes with bounded state count; abstracted vs exact (on a small comparable spot) within a derived bound; abstraction policy is explicit in config; determinism; no silent strategy corruption (strategically identical combos stay identical).

### S5. Continuous sizing + single-size mode
Sizing selection that picks sizes from declared schemes (pot%, x, bb, geometric) including dynamic selection across a continuum of candidate sizes; plus a dedicated **single-size mode** that returns exactly ONE optimal size per node.
- **Acceptance:** single-size mode output has exactly one bet/raise size per decision node; sizes come from the declared scheme; zero-sum; deterministic; a regression test pins a known spot's single size.

### S6. Multi-street ICM / bounty strategy
ICM utility over multiple streets (not just one-hand settlement) and bounty strategy beyond immediate one-hand payments (e.g., elimination-value accounting across streets).
- **Acceptance:** ICM conservation on multi-street configs; bounty strategy changes equilibrium measurably vs chip-EV on a pinned spot (assert direction + bound); all existing ICM/bounty tests stay green.

### S7. Web UI (the product layer)
A local web app over the solver API:
- **Study mode:** board/street input, stacks, pot, positions, opponent range editor (132-combo grid), solve button, strategy tree view, range/heat display, per-combo action frequencies.
- **Trainer mode:** deal hands, play against the solved strategy, feedback on deviations.
- **Preset library:** list/load the canonical presets (existing catalog + new Phase 4 spots).
- **Stack:** FastAPI (or equivalent stdlib-adjacent choice decided in design wave) + vanilla JS/HTML frontend, NO build step. Served on localhost.
- **Acceptance:** HTTP API contract tests (httpx) for every solver operation exposed; UI smoke test (Playwright if available, else DOM-level assertions via a headless fetch of rendered state); study mode solves a canonical spot end-to-end in the browser flow; trainer mode completes one dealt hand against the solver.

## Out of scope (do NOT start)
- Neural DDLS / Fast (A1) — needs a trained model; separate project.
- PLO.
- Cloud/multi-user, auth, billing.

## HARD RULES (from the mission standard — non-negotiable)
1. **Adversarial cross-check after EVERY implementation batch:** a FRESH set of non-author BryantGPT auditors (different from the implementers) must RUN the code (focused tests + the suite + the new invariants) before the next batch starts. Width ≤ 6.
2. **Untrusted proposals:** child outputs (tool-free or not) are proposals. Parent inspects every owned path, reruns tests, checks oracles. Never accept "done" without parent-side evidence.
3. **Goal-check gate** before `PHASE4_REPORT.md`: scope inventory (S1–S7 each with implementing file + tests), behavioral spot-checks vs independent oracles, negative checks, invariant checks, cross-implementation agreement (auto vs explicit continuations, abstracted vs exact), per-item PASS/PARTIAL/FAIL.
4. **Heartbeat protocol:** write `STATE.txt` (updated / wave / waiting_on / next_action) on every resumed turn BEFORE other work. Per-child `.hb/<task-id>` heartbeats for dispatch waves.
5. **Quota discipline:** parent model (gpt-5.6-sol) has a usage quota. On `HTTP 429 usage limit`: PAUSE, log to PROGRESS.md with timestamp and exact resume point, do NOT retry-loop, do NOT reduce BryantGPT width because of it.
6. **502 triage:** unknown-tool → adapter issue (check `~/Bryant-GPT` logs); schema-validation → reduce width to 4 then 3; 503-busy → queue/backoff. Log receipts.
7. **Git:** after each accepted wave, commit with a descriptive message. Tag `phase4-complete` only after the goal-check gate passes.
8. **Preserve the 398-test baseline:** every batch ends with the prior suite green (new tests additive).

## Deliverables
- `PHASE4_REPORT.md` (verdict, evidence, boundaries)
- Updated `README.md`, `docs/PHASE4.md`, `SWARM_REPORT.md`
- Web UI under `web/` (server + static frontend)
- Full suite green + tagged commit

## Start
Read `PARITY_GAP_REPORT.md` (gap context), `PHASE3_REPORT.md` (boundaries), `ARCHITECTURE*.md` and `docs/` (existing contracts), then run the S1 design wave (6 subagents, non-overlapping topics) before any implementation.
