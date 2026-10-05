# Practice mode

Practice mode works like GTO Wizard's puzzle mode, on top of this repo's solver. You get a spot
(board, ranges, pot, stacks, the line so far, your hand) and choose an action. The score is the
EV you lost compared with the solver's best action. Every strategy, action value, score and
grade comes from a real solve of that spot, run at request time or loaded from a cache entry
that such a solve wrote. Nothing is pre-solved or hardcoded.

Branch `feat/practice-mode`. This document describes commit `5a3e61f`.

Detailed docs:
- [docs/practice-mode/api.md](docs/practice-mode/api.md): every `practice-*` v4 operation, with request/response examples captured from real calls.
- [docs/practice-mode/architecture.md](docs/practice-mode/architecture.md): modules, backend routing, families, caching, the R1 no-hardcode rule.
- [docs/practice-mode/operations.md](docs/practice-mode/operations.md): cache warm/stats/clear, the API CLI, env vars, troubleshooting.
- [docs/practice-mode/solver-evaluation.md](docs/practice-mode/solver-evaluation.md): how to read the solver benchmark and its verdict.
- Background: `PRACTICE_MODE_DESIGN.md` (design), `PRACTICE_MODE_REPORT.md` (wave 1–3 report), `research/practice-mode/w4/` (W4 contract and task reports).

## Run it

```bash
cd poker-solver
uv sync                                   # once; creates .venv
.venv/bin/python -m poker_solver.practice.server --host 127.0.0.1 --port 7777
# open http://127.0.0.1:7777/
```

Optionally keep the solve cache and progress database out of your home directory:

```bash
export POKER_PRACTICE_CACHE_DIR=/tmp/practice/cache   # default ~/.cache/poker-solver/practice
export POKER_PRACTICE_DATA_DIR=/tmp/practice/data     # default ~/.local/share/poker-solver/practice
```

Pre-solve spots so the first click is instant. Flop and 3-max spots take roughly 9–16 s each
when solved cold:

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
.venv/bin/python -m poker_solver.practice.api submit river-oop-bet-or-check/e79981f9d62d check --iterations 40 --user alice
.venv/bin/python -m poker_solver.practice.api progress --user alice
.venv/bin/python -m poker_solver.practice.api leaderboard --limit 10
```

`spot_id`s are deterministic for a given catalog seed (default 0). The ones above exist at
`5a3e61f`. Run `list` to see the current catalog.

## Using the UI

1. Optional: enter a user name (`[A-Za-z0-9_.-]`, up to 32 characters). It is saved in the browser and used for progress.
2. Pick a spot. The list can be filtered by family, street (preflop/flop/turn/river) and game type (heads-up/3-max).
3. Choose an action and, for a wager, a size. Keyboard shortcuts: f, c, b, Enter.
4. The result panel shows:
   - score (0–100), grade and EV loss in chips and % pot;
   - the solver's mix for your hand and the Q value of every legal action;
   - the strategy across the whole range;
   - feedback;
   - solve provenance: algorithm, iterations, `params_hash`, entry point, NashConv.
5. To re-solve, change the iterations and press Re-solve. That gives a different `params_hash` and a new solve.
6. The progress panel shows attempts, best and last score per spot. The leaderboard ranks users by the sum of their per-spot best scores.

## Spot families (72 spots at seed 0)

| family | street / players | solver backend | default iterations |
|---|---|---|---|
| `kuhn-intro` | Kuhn poker, 2 | CFR on Kuhn | 200 |
| `river-oop-bet-or-check` | river, heads-up | river CFR | 200 |
| `river-ip-facing-bet` | river, heads-up | river CFR | 200 |
| `preflop-hu-open` | preflop, heads-up | n-player preflop CFR | 300 |
| `preflop-3max-open` | preflop, 3-max | n-player preflop CFR | 100 |
| `flop-cbet` | flop → river, heads-up | allstreet CFR | 200 |
| `turn-barrel` | turn → river, heads-up | multistreet CFR | 200 |

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

- `solver_self_loss` = best Q − Q of the solver's own mix. It measures solver noise, and if it is large the spot needs more iterations.
- A size that isn't in the solved menu is snapped to the nearest solved size, and the snap is reported. The solver never makes up an EV for an unsolved size.

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

**Verdict as recorded in `results.md` at commit `5a3e61f`: overall FAIL, correctness-only PARTIAL.**
That run had 17 of 20 criteria PASS. The exceptions:
- **C14 scale: FAIL.** Projected ≈ 2.4e5 s per 1000 iterations at 100 combos per side.
- **C11 practice solve quality: FAIL.** `preflop-3max-open` is exploitable by ≈ 7.18 % of the pot at its 100-iteration default. `flop-cbet` is at 1.12 %, which is PARTIAL.
- **C15 all-in: PARTIAL.** There is a value-neutral tree defect.

Capability verdicts:

| verdict | capabilities |
|---|---|
| FAIL | 2-player NL, 3-max, preflop, postflop |
| PARTIAL | multi-street, ICM, sizing |
| PASS | mixed strategy |

Later repair work may change C11/C15. Check `results.md` for the current numbers.
[docs/practice-mode/solver-evaluation.md](docs/practice-mode/solver-evaluation.md) explains every
criterion and threshold.

```bash
scripts/solver_eval.sh quick     # ~1 min, temp output dir
scripts/solver_eval.sh full      # ~5 min, rewrites research/solver-evaluation/results.{json,md}
```

## Known limitations

- **Scale.** The solver is pure-Python, full-tree vanilla CFR. Cost grows faster than linearly in
  the number of deals: at 48 combos per side a single river iteration takes about 29 s. Full-range
  spots in the style of GTO Wizard are out of reach (C14 FAIL).
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
- **3-max quality.** At the default 100 iterations, `preflop-3max-open` is noticeably exploitable,
  and its provenance reports no NashConv (`null`), so the UI cannot show it.
- **Algorithms.** Only `flop-cbet` (allstreet) accepts `external-sampling-mccfr`. Every other
  backend is vanilla CFR only.
- **Cold solves.** On the reference host, flop and 3-max spots take about 9–16 s when solved cold.
  The server gives up after 90 s (504) and the adapter after 60 s. The disk cache makes repeat
  requests instant.
- **Single machine.** Progress is stored in local SQLite with no authentication. A user name is a
  label, not an account.
