# W4+ COMPLETION BRIEF — finish practice mode to the full mission

Owner directive (2026-10-05): complete the feature against PRACTICE_MODE_MISSION.md.
`practice-mode-done` (f1eb720) shipped a working slice; these mission deliverables are
still missing and are now in scope. Same rules as the mission (bryant subagents, ≤6 per
wave in one delegate_task call, exclusive file ownership, adversarial non-author audit
after every implementation batch, commit + tag each accepted wave, suite stays green).

## Gaps to close (verified against the mission, 2026-10-05)
1. **Street/game coverage in the catalog (Deliverable A).** Catalog is Kuhn + river only.
   Add solver-generated families for **preflop** (nplayer_preflop), **flop** and **turn**
   (allstreet / multistreet), and at least one **3-max** family (nplayer). Flop solves take
   ~10 s: make that work properly — pre-solve on first request with a persistent on-disk
   solve cache keyed by full params_hash, async/progress in the UI, or reduced trees — not
   by dropping the street. Each new family needs parameter-sensitivity tests (R1).
2. **Progress tracker (Deliverable A).** Persisted per-spot history: attempts, best score,
   last score, timestamps. API operations + CLI (`progress`, `leaderboard`) + a UI panel.
3. **Solver evaluation (Deliverable B).** `research/solver-evaluation/` does not exist.
   Reproducible benchmark: correctness vs known references (Kuhn analytic Nash, hand-computed
   river EVs, small closed-form games), convergence vs iterations, exploitability trend,
   timing, edge cases (all-in, mixed strategies, n-player). Written VERDICT classifying
   2-player NL, 3-max, preflop, postflop, multi-street, ICM, mixed strategy, sizing as
   PASS/PARTIAL/FAIL with evidence and a concrete gap list.
4. **Docs (Deliverable D).** Top-level `PRACTICE_MODE.md` (how to run, how to read the
   solver evaluation), update `docs/`, `STATE.txt`, `PROGRESS.md`.

## Done when
- Mission Definition of Done items 1–5 all hold for preflop/flop/turn/river + 3-max spots.
- Full suite green (≥1026 + new), audits clean, committed, tagged `practice-mode-complete`,
  pushed to origin `feat/practice-mode` with tags.
- Final summary includes the solver verdict and any bryant-gpt provider issues.

## Run discipline
- Keep STATE.txt current every turn (updated=, wave=, waiting_on=, next=).
- Do not stop to ask questions; decide, log the decision in PROGRESS.md, continue.
- A heartbeat re-enters this session when idle: on each heartbeat, check STATE.txt and live
  subagents; if work is in flight, reply briefly; if idle and not done, start the next step;
  if a provider error occurred, retry once, then fall back to another bryant model and log it.
