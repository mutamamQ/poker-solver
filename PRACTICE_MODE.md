# Practice mode

Practice mode works like GTO Wizard's puzzle mode, on top of this repo's solver. You get a spot
(board, ranges, pot, stacks, the line so far, your hand) and choose an action. The score is the
EV you lost compared with the solver's best action. Every strategy, action value, score and
grade comes from a real solve of that spot, run at request time or loaded from a cache entry
that such a solve wrote. Nothing is pre-solved or hardcoded.

Branch `feat/practice-mode`. This document describes commit `72f0053` (tag `practice-mode-w5`).
The practice code is the W5 code from `2a6f57c`; `72f0053` only adds the re-run benchmark results.

Detailed docs:
- [docs/practice-mode/api.md](docs/practice-mode/api.md): every `practice-*` v4 operation, with request/response examples captured from real calls.
- [docs/practice-mode/architecture.md](docs/practice-mode/architecture.md): modules, backend routing, families, caching, the R1 no-hardcode rule.
- [docs/practice-mode/operations.md](docs/practice-mode/operations.md): cache warm/stats/clear, the API CLI, env vars, troubleshooting.
- [docs/practice-mode/solver-evaluation.md](docs/practice-mode/solver-evaluation.md): how to read the solver benchmark and its verdict.
- Background: `PRACTICE_MODE_DESIGN.md` (design), `PRACTICE_MODE_REPORT.md` (wave 1–3 report), `research/practice-mode/w4/` (W4 contract and task reports), `research/practice-mode/w5/` (W5 repair reports).

## Run it

```bash
cd poker-solver
uv sync                                   # once; creates .venv
.venv/bin/python -m poker_solver.practice.server --host 127.0.0.1 --port 7777
# prints: Practice server on http://127.0.0.1:7777/  -> open it in a browser
```

Optionally keep the solve cache and progress database out of your home directory:

```bash
export POKER_PRACTICE_CACHE_DIR=/tmp/practice/cache   # default ~/.cache/poker-solver/practice
export POKER_PRACTICE_DATA_DIR=/tmp/practice/data     # default ~/.local/share/poker-solver/practice
```

Pre-solve spots so the first click is instant. A cold `preflop-3max-open` solve (5000 iterations)
takes about 11–26 s on the 2-CPU reference host depending on load; `flop-cbet` about 4–14 s:

```bash
.venv/bin/python -m poker_solver.practice.solve_cache warm --families flop-cbet,preflop-3max-open
.venv/bin/python -m poker_solver.practice.solve_cache stats
```

Smoke test (starts its own server on the given port, runs 7 checks, then stops it):

```bash
scripts/practice_smoke.sh 7794
```

Command line, no browser:

```bash
.venv/bin/python -m poker_solver.practice.api list --family river-oop-bet-or-check --limit 3
.venv/bin/python -m poker_solver.practice.api solve river-oop-bet-or-check/e79981f9d62d --iterations 40
.venv/bin/python -m poker_solver.practice.api submit river-oop-bet-or-check/e79981f9d62d check --user alice
.venv/bin/python -m poker_solver.practice.api progress --user alice
.venv/bin/python -m poker_solver.practice.api leaderboard --limit 10
```

`spot_id`s are deterministic for a given catalog seed (default 0). The ones above exist at
`72f0053` (all 72 spot_ids are unchanged since `5a3e61f`). Run `list` to see the current catalog.

**Only family-default solves count for progress.** A submit without `--iterations` (or with a
solve override that produces the same `params_hash` as the family default) is recorded. A submit
with a different solve, e.g. `--iterations 40`, is still solved and scored, but `progress` is
`null` and nothing is stored. This stops a user from earning leaderboard points on a cheap,
under-converged solve.

## Using the UI

1. Optional: enter a user name (`[A-Za-z0-9_.-]`, up to 32 characters). It is saved in the browser and used for progress.
2. Pick a spot. The list can be filtered by family, street (preflop/flop/turn/river) and game type (heads-up/3-max).
3. Choose an action and, for a wager, a size. Buttons are labelled Fold/Check/Call/Bet/Raise.
   Keyboard shortcuts: f (fold), c (check/call), b (bet/raise; press again to cycle sizes, focus
   moves to the size box), Enter (submit). They work on every family, including the upper-case
   `FOLD`/`CALL`/`RAISE` kinds of the preflop, flop and turn backends.
4. The result panel shows:
   - score (0–100), grade and EV loss in chips and % pot;
   - the solver's mix for your hand and the Q value of every legal action;
   - the strategy across the whole range;
   - feedback;
   - solve provenance: algorithm, iterations, `params_hash`, entry point, NashConv (shown for every family, 3-max included).
5. To re-solve, change the iterations and press Re-solve. That gives a different `params_hash` and a new solve. Submits made against such a custom solve are scored but not recorded.
6. The progress panel shows attempts, best and last score per spot (the "Best" badge is neutral-coloured; the API has no grade for the best attempt). The leaderboard ranks users by the sum of their per-spot best scores.

## Spot families (72 spots at seed 0)

| family | street / players | solver backend | default iterations |
|---|---|---|---|
| `kuhn-intro` | Kuhn poker, 2 | CFR on Kuhn | 200 |
| `river-oop-bet-or-check` | river, heads-up | river CFR | 200 |
| `river-ip-facing-bet` | river, heads-up | river CFR | 200 |
| `preflop-hu-open` | preflop, heads-up | n-player preflop CFR (flat trainer) | 300 |
| `preflop-3max-open` | preflop, 3-max | n-player preflop CFR (flat trainer) | 5000 |
| `flop-cbet` | flop → river, heads-up | allstreet CFR | 200 |
| `turn-barrel` | turn → river, heads-up | multistreet CFR | 200 |

The preflop families train with `practice/nplayer_metrics.FlatNPlayerCFR`, a vectorised trainer
whose profiles are bit-identical (`==`) to `nplayer.NPlayerCFRSolver` but run about 30× faster.
That is what makes the 5000-iteration 3-max default affordable.

## Scoring

- Q(a) is your expected payoff in chips for taking action `a`, after which everyone plays the solved strategy.
- EV loss = max(0, best Q − Q of your play). A mixed play uses the probability-weighted Q.
- Score = 100 × (1 − EV loss / (best Q − worst Q)). This scale is relative, so playing the worst action scores 0 even when the chip loss is small.
- Grade comes from EV loss as % of the pot at the decision:

  | EV loss (% pot) | grade |
  |---|---|
  | ≤ 0.25 | Perfect |
  | ≤ 1 | Good |
  | ≤ 3 | Inaccuracy |
  | ≤ 8 | Mistake |
  | > 8 | Blunder |

- `optimal_action` is the highest-Q action among the actions the solver's strategy actually plays
  (probability > 0); ties go to the higher probability, then legal order. It is never an action the
  solver does not play.
- `solver_self_loss` = best Q − Q of the solver's own mix. It measures solver noise, and if it is large the spot needs more iterations.
- A size that isn't in the solved menu is snapped to the nearest solved size, and the snap is reported. The solver never makes up an EV for an unsolved size.
- Facing an all-in, the flop/turn engines internally list a "raise" to the same amount as the call.
  Practice output merges that pseudo-raise into `CALL` (strategy, Q, range strategy, legal actions),
  so you are never offered a "raise" that is really a call.

## How to read the solver evaluation

The benchmark is in `research/solver-evaluation/`. It checks the solver behind practice mode
against independent references (Kuhn −1/18, a polarized-river closed form, 3-player Kuhn, an
independent best-response oracle, ICM enumeration). It also measures convergence,
default-solve quality, timing and scale, and grades each of these PASS / PARTIAL / FAIL.

- **Source of truth:** `research/solver-evaluation/results.md` and `results.json`, regenerated by
  `scripts/solver_eval.sh full`. The written verdict and gap list are in
  `research/solver-evaluation/REPORT.md`.
- **Worst-case rule:** each capability gets the worst verdict among its evidence criteria and its
  scope cap. The overall verdict is the worst of all criteria and capabilities. A single FAIL
  anywhere makes the overall verdict FAIL.
- **Two headline verdicts:**
  - `overall` asks whether this is a complete, up-to-par solver.
  - `correctness-only` excludes timing, default-solve quality and scale, and asks whether the numbers it produces are right.

**Verdict as recorded in `results.md` at `72f0053` (full run of the W5 code, commit `2a6f57c`,
clean tree): overall FAIL, correctness-only PARTIAL.** 17 of 20 criteria PASS. The exceptions:
- **C14 scale: FAIL.** Projected ≈ 1.8e5 s per 1000 iterations at 100 combos per side (48 combos/side measured at ≈ 20 s per iteration).
- **C11 practice solve quality: PARTIAL**, only because `flop-cbet` is at 1.122 % of the pot at its
  200-iteration default. `preflop-3max-open` is now 0.143 % (PASS; it was 7.18 % at 100 iterations
  before W5). All other families are 0.25–0.87 %.
- **C15 all-in: PARTIAL.** The `multistreet` tree still builds the value-neutral pseudo-raise
  facing an all-in. Practice output hides it, but the benchmark checks the engine tree.

Capability verdicts:

| verdict | capabilities |
|---|---|
| FAIL | 2-player NL, postflop (both via C14 scale) |
| PARTIAL | 3-max, preflop, multi-street, ICM, sizing |
| PASS | mixed strategy |

[docs/practice-mode/solver-evaluation.md](docs/practice-mode/solver-evaluation.md) explains every
criterion and threshold.

```bash
scripts/solver_eval.sh quick     # ~35 s here, temp output dir
scripts/solver_eval.sh full      # ~8 min here, rewrites research/solver-evaluation/results.{json,md}
```

## Known limitations

- **Scale.** The solver is pure-Python, full-tree vanilla CFR. Cost grows faster than linearly in
  the number of deals (≈ deals^1.48): at 48 combos per side a single river iteration takes about
  20 s. Full-range spots in the style of GTO Wizard are out of reach (C14 FAIL). The fast flat
  trainer only covers the preflop backend.
- **Tiny ranges.** Practice spots use 3–5 explicit combos per seat. The solutions are correct for
  those toy games, not for realistic ranges.
- **One bet size per spot.** Each spot offers the solver a single wager size, plus all-in in
  preflop trees. Sizes off that menu are snapped, never solved. There is no automatic size
  selection.
- **Abstraction caps.**
  - Flop and turn spots enumerate only 2 or 4 runouts, not every runout.
  - Preflop leaves are settled by sampled-board showdown equity (256 samples), with no postflop play.
  - 3-way play exists only preflop.
  - ICM is an evaluator only; no practice spot uses it.
- **flop-cbet convergence.** At its 200-iteration default `flop-cbet` is exploitable by ≈ 1.12 % of
  the pot (C11 PARTIAL for that family).
- **All-in pseudo-raise.** `multistreet.py` (and `allstreet`, built on it) still creates
  `RAISE(target == call target)` facing an all-in, plus CHECK-only nodes for all-in seats. Practice
  merges it into `CALL` at the presentation layer; the engine tree, profile and NashConv are
  unchanged, and C15 stays PARTIAL.
- **Algorithms.** Only `flop-cbet` (allstreet) accepts `external-sampling-mccfr`. Every other
  backend is vanilla CFR only.
- **Cold solves.** The benchmark measured 11.4 s for a cold 3-max solve and ≤ 3.8 s for the other
  families (load ≈ 3). Under heavier load a 3-max solve can exceed 20 s (22–26 s seen while
  warming). The adapter budget is 60 s and the server answers 504 after 90 s. Identical
  concurrent requests share one solve (single flight), and the disk cache makes repeat requests
  instant.
- **Single machine.** Progress is stored in local SQLite with no authentication. A user name is a
  label, not an account.

### Leaderboard and shared-cache caveats (W6)

- The leaderboard is an honour-system self-study aid, not a competitive ranking: `practice-solve-spot`
  intentionally exposes the solver's action values, the best score per spot counts (retries allowed), and
  `seed` generates new spots, so a determined user can inflate it with default settings.
- Two processes running different solver code against the same `POKER_PRACTICE_CACHE_DIR` treat each
  other's records as stale (code fingerprint mismatch) and evict them, forcing re-solves. Give each code
  version its own cache directory.
