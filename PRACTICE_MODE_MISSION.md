# MISSION — GTO Wizard Practice Mode Clone (Poker Solver)

You are the **orchestrator** for the poker-solver project. Your job: build a
**complete, working "GTO Wizard practice mode clone"** on top of the existing
CFR/MCCFR solver, and **evaluate the solver itself** to determine whether it is
up to par / complete. Read this file in full before acting. It is the
authoritative scope.

## Project root
`/home/genomix-node/poker-solver`
- Branch: `main` (create `feat/practice-mode` for all work; tag the pre-work
  commit `practice-mode-baseline` first).
- Tests: ~531 green (verify; do not regress).
- Solver packages: `src/poker_solver/` (cfr, mccfr, multistreet, allstreet,
  nplayer, nplayer_preflop, nplayer_postflop, best_response, equity, sizing,
  model, game_structure, api_v3, api_v4, cli).
- Python: the repo `.venv`. Use `source .venv/bin/activate`.
- Prior docs: `STATE.txt`, `PROGRESS.md`, `ARCHITECTURE*.md`, `docs/`,
  `research/phase4/`. Read them for conventions and hard rules.

## What "GTO Wizard practice mode" means (the target product)
GTO Wizard's practice mode presents a **decision at a specific point in a hand**
(a preflop spot, a flop/turn/river spot, or a multi-street sequence) with a
defined **range, board, pot, stack, and action history**, then:
1. Solves that spot with a GTO solver to get the **optimal mixed strategy**.
2. Lets the user **play an action** (bet/raise with a size, call, check, fold,
   or a mixed line).
3. **Scores the user's play** against the optimal strategy — typically an
   **exploitability / EV loss** or a **GTO "accuracy" / score** — and gives
   **feedback** (what the optimal play was, how much EV the user lost, the
   optimal sizing).
4. Serves a **catalog of practice spots** the user can browse and attempt, and
   tracks progress/scores.

The clone must be **real**: it must be built **by calling the solver** to
generate each spot's optimal strategy and scoring, **NOT by hardcoding
puzzles** or hand-written "correct answers." Every practice item's optimal
strategy, optimal sizing, and the score of a user's play must be **derived from
a solver solve at runtime** (or a cached solver solve), so that changing the
range/pot/stack/iterations changes the result. A grader must be able to point
at any practice item and see the solve parameters + the solver output it came
from.

## Hard rules (from the user + project convention)
1. **ONLY bryant-gpt.** All subagent work goes through the bryant provider. Do
   not call Claude/Anthropic, OpenAI-direct, or any other provider. You (the
   orchestrator) run on a bryant model; your subagents are bryant models.
2. **6 bryant-gpt subagents max** per wave, in a single `delegate_task` call.
   Let **yourself** pick which bryant model each subagent uses from the pool.
3. **Use the solver to build practice mode.** No hardcoded puzzles. Optimal
   strategies, sizings, and user-play scores must come from solver solves.
4. **Evaluate the solver.** Produce a measured, evidence-backed verdict on
   whether the solver is up to par / complete (see Deliverable D below).
5. **Git discipline.** Commit after each accepted wave. Keep the test suite
   green. Never lose work. Rollback must always be possible (tags + clean
   worktree per accepted state).
6. **Adversarial non-author audit after every implementation batch** (a subagent
   that did not write the code reviews it against the frozen manifest).
7. **Code standards.** Typed, immutable public results, defensive copies,
   fail-closed validation, no silent `except Exception` swallowing, deterministic
   seeds, documented API. Match the existing code style.
8. **Known provider quirk:** bryant-gpt intermittently returns
   `HTTP 502: Model did not return valid tool/structured JSON` or
   `HTTP 502: Model returned neither an answer nor a tool call`. On a subagent
   transport failure: give it ONE retry (same exclusive output paths), read the
   canonical transcript to recover any work it actually did, and if it still
   fails, have the parent (you) integrate the exhausted path. **Log every
   bryant-gpt provider error** (model, subagent, exact error, time, wave) to
   `PROGRESS.md` under a `## bryant-gpt provider issues` section — the user
   explicitly wants to be informed of bryant-gpt issues.

## Subagent model pool (bryant ids, via `delegate_task` with
`provider="bryant"` and the exact `model=` id)
Pick per subagent based on the task. Suggested:
- `15d8cc8844/CLAUDE_V5_5_OPUS` — strongest; core solver integration,
  exploitability scoring, hard algorithm work.
- `15d8cc8844/CLAUDE_V5_1_FABLE` — strong, clean; API/schema, state, contracts.
- `15d8cc8844/OPENAI_GPT6_1_SOL` — strong reasoning; solver evaluation,
  adversarial review.
- `15d8cc8844/OPENAI_GPT6_ASTRA` — strong; adversarial review, red-team.
- `15d8cc8844/OPENAI_GPT6_LUNA` — good, fast; tests, CLI, docs, UI plumbing.
- `15d8cc8844/CLAUDE_V5_OPUS` / `15d8cc8844/CLAUDE_V4_8_OPUS` — backups.
(You may also use the newer GLM 5.3 / Deepseek V4 / Qwen3.8 / Grok 4.7 /
Gemini 3.8 ids if you want a second opinion — all are bryant. But the six
above are the proven strong set.)

## Deliverables (all must be present, tested, committed)
**A. Practice-mode core (`practice/` package or equivalent):**
- A `PracticeSpot` spec (dataclass/pydantic): game type (heads-up / 3-max),
  street (preflop/flop/turn/river), board, hero+villain ranges, pot, stacks,
  action history, solver + iterations.
- A **spot generator** that can produce a catalog of practice spots from
  solver-driven parameters (e.g. "all preflop OOP open-raise spots", "flop
  c-bet vs 3-bet", "turn continuation") — generated, not hand-written.
- A **solver adapter** that takes a `PracticeSpot`, calls the existing
  `dispatch_v4` / `solve_*` solver entrypoints (correct `{version, operation,
  payload}` envelope), and returns the **optimal mixed strategy + optimal sizing**
  for the decision point(s).
- A **scorer** that, given the user's action (and bet/raise size), computes
  the **EV loss / exploitability** vs the optimal strategy and returns a
  **score** (0–100 accuracy or EV-based) + **feedback** (optimal action,
  optimal size, EV delta, the mixed strategy the user deviated from).
- A **progress tracker** (per-spot history, best score, attempts) — persisted.

**B. Solver evaluation (`research/solver-evaluation/`):**
- A reproducible **solver benchmark**: correctness vs **known/independent
  references** (e.g. hand-computed EVs, small 2x2 or Kuhn-poker analytic
  solutions, known Nash values), convergence over iterations, exploitability
  trend, timing, and edge cases (all-in, no-limit, mixed strategies, n-player).
- A written **verdict**: is the solver **up to par / complete**? Classify each
  capability (2-player NL, 3-max, preflop, postflop, multi-street, ICM, mixed
  strategy, sizing) as PASS / PARTIAL / FAIL with evidence, and list concrete
  gaps. This directly answers the user's "evaluate the solver to see if it is
  up to par or complete."

**C. Practice-mode API + CLI + minimal UI:**
- Expose practice mode through `api_v4` (new operations) and `cli.py`
  (e.g. `list spots`, `solve spot`, `submit play`, `score`, `leaderboard`).
- A **minimal web UI** (HTML+JS, served or static) that renders a practice
  spot, lets the user pick an action + size, and shows the score + feedback +
  optimal strategy. Must be driven by the API, not hardcoded.

**D. Tests + docs:**
- Permanent, production-importing tests for every new surface (spot gen,
  solver adapter, scorer, API, CLI). No print-only "harnesses."
- Update `STATE.txt`, `PROGRESS.md`, `docs/`, and a top-level
  `PRACTICE_MODE.md` describing how to run the practice mode clone and read the
  solver evaluation.

## Definition of Done (the user's bar)
1. A user can, from the CLI or web UI: **browse generated practice spots →
   solve one with the solver → submit a play → receive a solver-derived score,
   feedback, and the optimal strategy.**
2. **No hardcoded puzzles** — every optimal strategy/score is provably produced
   by a solver solve (a test asserts this: changing a solver parameter changes
   the output; the output carries its solve params).
3. A **measured solver evaluation** with a clear up-to-par / complete verdict
   and a gap list.
4. Full test suite green (baseline + all new tests), committed, with a clean
   worktree and a rollback tag.
5. A `## bryant-gpt provider issues` log in `PROGRESS.md` if any provider
   errors occurred (the user must be informed).

## Workflow (follow the established project discipline)
1. **Wave 0:** verify baseline (`pytest -q`), create `feat/practice-mode`, tag
   `practice-mode-baseline`, read the architecture/STATE/PROGRESS docs, and
   write `PRACTICE_MODE_DESIGN.md` (spot spec, solver adapter interface,
   scoring metric definition, API/CLI/UI surface, test plan).
2. **Design wave (6 subagents, non-overlapping):** spec/spot-gen, solver
   adapter, scorer/metric, API/CLI, web UI, solver-evaluation benchmark.
3. **Implementation waves (6 subagents each, exclusive file ownership, parent
   integrates shared files):** implement A, then B, then C, then D.
4. **After each implementation batch:** adversarial non-author audit (6
   subagents) against a frozen manifest; repair only reproduced findings;
   re-audit until clean; commit the accepted state.
5. **Finish:** full suite green, update STATE/PROGRESS/docs, commit, tag
   `practice-mode-done`, and write the final summary for the user (including
   the solver verdict and any bryant-gpt issues).

## Reporting
- Write `STATE.txt` every resumed turn (updated=, wave=, waiting_on=,
  next_action=).
- Append to `PROGRESS.md` with UTC timestamps (use `date -u`).
- Keep a `## bryant-gpt provider issues` section current.
- When done (or blocked), write the final user-facing summary to
  `PRACTICE_MODE_REPORT.md` and print a concise status to stdout.

Go.
