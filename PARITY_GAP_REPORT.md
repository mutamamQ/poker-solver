# GTO Wizard Parity Gap Report

**Date:** 2026-09-15 (UTC)
**Baseline:** Phase 3 complete — `PHASE3_REPORT.md`, full suite 398/398 green, adversarial audit waves passed.
**Purpose:** Authoritative record of what the solver does NOT yet have compared to GTO Wizard. Use this as the scope source for any future Phase 4.

## A. Engine gaps (solver capability)

| # | Gap | GTO Wizard | Ours (current) | Priority note |
|---|---|---|---|---|
| A1 | Neural solver (Fast/DDLS) | Core product: neural continuation values, full postflop spots in seconds | Absent — engine fails closed (`Fast/DDLS is unavailable because no neural continuation-value model ships`) | Biggest practical gap: speed + full-tree coverage |
| A2 | Unrestricted all-street postflop | Automatic flop→turn→river, dynamic sizing, no user-declared tree | Bounded finite trees only; leaves need **caller-supplied continuation values** | Auto-continuation layer (rollout or value function) is the highest-value single build |
| A3 | Multiway postflop 4–9 players | Up to 9 players | Exactly 3 players, one betting round | Breadth |
| A4 | Multiway preflop | Up to 9 players; straddles, limps, cold-calls, SB completes | Heads-up preflop only (positions, forced posts, raise tree) | Breadth |
| A5 | Automatic abstraction | Automatic hand abstraction for tractability | None — game must be finite as-declared | Needed for A1/A2 at scale |
| A6 | Continuous/dynamic sizing | Picks sizes dynamically, single-size solutions mode | Strict finite candidate sets (fixed/dynamic/automatic selection from declared set) | Single-size derivable from existing machinery |
| A7 | Multi-street ICM/bounty strategy | Postflop ICM + bounties (roadmap, some live) | ICM = exact subset recursion (1–10p); bounties = immediate one-hand payments only | Depth |
| A8 | PLO (Omaha) | HU custom, postflop ICM, nodelocking | Absent | Separate game; out of scope unless requested |
| A9 | Convergence certificate | Implied by their engine | `classic` = complete traversal of declared tree; **not** a convergence certificate (documented) | Theoretical, not blocking |

## B. Product gaps (GTO Wizard is an app; we are a backend)

| # | Gap | Note |
|---|---|---|
| B1 | Trainer (play vs the solver) | UI + deal simulation against solved strategy |
| B2 | 1-click hand history analysis | Import → spot → solved comparison |
| B3 | Range/solution visualization | Heatmaps, strategy trees, EV buckets, Compare-Nodes UI |
| B4 | Prefill/solution library | Thousands of presolved charts vs our 2 catalog presets + 7 synthetic fixture templates |
| B5 | Saved-range management, tags, import/export UX | Backend supports persistence/export; no management layer |
| B6 | Web/mobile app, sharing links | Ours: Python CLI + typed API (v1/v2/v3 facades) |

## C. What we DO have (parity-confirmed areas)

- Exact integer accounting: side pots, odd chips, blinds/antes/straddles, declared rake
- CFR 2–9 players (bounded finite games), MCCFR, vanilla CFR, best response, exploitability
- Range editor: weighted parsing, editing, persistence, export, blocker filtering
- ICM exact subset recursion; bounties (one-hand)
- Nodelocks/profiles (fixed policies + behavior shaping)
- Bayesian inference over caller hypotheses
- Tree editing (atomic add/remove/replace, invalidation metadata)
- Range tables (reach-conditioned frequencies, force-action EVs)
- Deviation diagnostic (exhaustive unilateral, bounded)
- Kuhn exact oracles (−1/18), Treys cross-check 100k categories, 47/47 battery, 398/398 suite
- Adversarial audit waves (different agents, execution-required) + parent-verified receipts

## D. Suggested Phase-4 order (if resumed)

1. **A2 auto-continuation layer** — rollout/value function at tree leaves so the caller stops supplying continuation values. Highest leverage, unlocks A1-style UX.
2. **A4 multiway preflop** — 3→9 player preflop (straddles/limps/cold-call rules already partially in `game_structure`).
3. **A6 single-size mode** — derive one optimal size/node from existing candidate machinery.
4. **A3 multiway postflop 4–9** — generalizes the 3-player state machine.
5. **A1 neural DDLS** — largest build; only after 1–4 are stable.
6. **B-layer** — only if the product (not backend) is the goal.

## E. Open items at time of stop

- No git repository in `~/poker-solver` — recommend `git init` + tagged baseline commit before any Phase 4 work.
- Orchestrator quota (gpt-5.6-sol / openai-codex) will need another reset for large waves; run at width ≤10 to stretch quota.
- Heartbeat cron `poker-health-1h` paused with the orchestrator (resume both together).
