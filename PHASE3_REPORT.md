# Phase 3 completion report

## Verdict

Phase 3 is complete for the bounded solver-backend scope reconciled in `ARCHITECTURE_PHASE3.md`. It adds exact finite accounting and range utilities, bounded heads-up preflop and exactly-three-player one-round postflop state machines, deterministic finite 2–9-player CFR, constraints, inference, structural editing, range tables, truthful engine dispatch, a strict additive version-3 facade, and synthetic examples.

This is not unrestricted Hold'em solving or commercial GTO Wizard parity. It does not ship neural DDLS, unrestricted all-street postflop solving, continuous actions, automatic abstraction, nine-player production strategy solving, PLO, presolved charts, room defaults, or future-bounty strategic valuation.

## Implemented scope

| Feature | Delivered boundary |
|---|---|
| Game structure | Exact integer contribution ledgers, refunds, side pots, odd chips, blinds/antes/straddles, declared rake |
| Sizing | Strict finite fixed, dynamic, and automatic candidate selection with percent-pot, geometric, multiple, and big-blind expressions |
| Ranges | Exact weighted two-card parsing, editing, persistence, export, and blocker filtering |
| ICM | Bounded exact subset recursion for 1–10 players |
| Bounties | Immediate one-hand accounting only |
| N-player solving | Deterministic full traversal on caller-declared finite 2–9-player games |
| Nodelocks/profiles | Complete fixed policies and bounded behavior shaping |
| Inference | Exact finite Bayesian updates over caller-supplied hypotheses and likelihoods |
| Tree editing | Immutable atomic add/remove/replace with explicit invalidation metadata |
| Preflop | Heads-up positions, forced posts, finite weighted deals, and raise tree with caller-supplied terminal continuations |
| Multiway postflop | Exactly three players, one betting round, caller-supplied ranks, exact side-pot/rake settlement |
| Range tables | Reach-conditioned per-combo action frequencies and force-action EVs for acting and opponent views |
| Deviation diagnostic | Exhaustive pure information-set unilateral deviations on bounded finite policy profiles; no multiplayer Nash guarantee |
| Engine | `classic` configured finite-tree CFR; approximate check-only `checkdown-equity`; Fast/DDLS fails closed |
| API/CLI | Backward-compatible v1/v2 plus strict additive v3 operations and typed Python APIs for game-tree objects |
| Presets/examples | Two catalog presets plus seven canonical synthetic, non-presolved fixture wrappers/templates |

## Main production modules

- Foundations: `game_structure.py`, `sizing.py`, `ranges.py`, `icm.py`, `bounties.py`.
- Solver cores: `nplayer.py`, `constraints.py`, `preflop.py`, `multiway.py`.
- Derived systems: `inference.py`, `tree_edit.py`, `range_table.py`, `engine.py`.
- Integration: `api_v3.py`, `presets.py`, additive `cli.py` dispatch.
- Benchmark: packaged `benchmark_phase3.py` with a thin script wrapper.

All prior public v1/v2 modules and commands remain present. Arbitrary Python game trees and strategy objects use typed APIs rather than pretending to have a safe universal JSON representation.

## Accuracy and adversarial evidence

The verification ladder used exact accounting identities, exhaustive combo expansion, sizing subset comparisons, finite pure-strategy oracles, lock checks, manual Bayes calculations, raw range-table aggregation identities, ICM/bounty conservation, direct Classic solver equivalence, and an independent checkdown recursion.

Every implementation sub-batch was followed by fresh non-author review before later implementation. Provider completion claims were not treated as evidence without parent inspection or execution. Confirmed defects were converted to regressions and re-audited. Consolidated dispositions include `review/phase3/c1-audit-summary.md` and `review/phase3/c3-audit-summary.md`; full chronological routing, failures, retries, corrections, and receipts are in `PROGRESS.md`.

The final C3 audit sequence was:

- `deleg_37494708`: six fresh auditors; engine attacks, direct equivalence, independent checkdown oracle, examples/docs, and full regression gate;
- one valid wrapper-labeling issue repaired with a RED regression;
- `deleg_bd4efa8d`: post-repair wording and focused gate passed; one provider failure retried once;
- `deleg_7f76cb64`: three wrappers, six dispatches, deterministic JSON-valid outputs, no discrepancy.

## Final parent verification

```text
uv run python -m compileall -q src tests scripts && uv run pytest -q
398 passed in 193.72s (0:03:13)
```

Exact original Phase 1+2 17-file command:

```text
185 passed in 191.63s (0:03:11)
```

Focused Phase-3 integration before final repair:

```text
213 passed in 1.03s
```

Post-repair C3 gate:

```text
23 passed in 0.08s
```

The packaged semantic benchmark executed four bounded synthetic workloads: ten-player ICM, 64-hypothesis inference, a three-player deviation diagnostic, and checkdown rollout. Every result returned `semantic_check=true`. Timings are host/workload observations, not production-throughput claims.

## Explicit boundaries

- Fast/DDLS is unavailable because no neural continuation-value model ships.
- MCCFR is an algorithm selection, not an accuracy mode.
- `classic` means complete traversal of the declared finite tree for the configured CFR iterations; it is not a convergence certificate.
- Checkdown rollout is approximate and ignores future betting.
- Preflop continuation values and multiway showdown ranks are caller supplied.
- Three-player postflop is one betting round only.
- N-player CFR and unilateral-deviation diagnostics are bounded finite-game tools, not a nine-player commercial equilibrium claim.
- Bounties account for immediate one-hand payments only.
- Example ranges, likelihoods, stacks, and sizes are synthetic fixtures, not recommendations or room defaults.

## Goal-check

- Prior 185-test Phase 1+2 baseline preserved: yes.
- Full Phase 1+2+3 suite and compile gate green: yes, 398 tests.
- Reconciled implemented-vs-boundary matrix matches live modules: yes.
- Strict additive v3 facade and backward-compatible old API/CLI: yes.
- Typed access for non-JSON game-tree/strategy objects documented truthfully: yes.
- Independent/adversarial evidence and retry dispositions recorded: yes.
- Canonical examples deterministic, synthetic, and non-presolved: yes.
- README, Phase-3 docs, SWARM_REPORT, PROGRESS, and audit summary current: yes.
- Open reproduced blockers or major findings: none.

Release verdict: complete for the declared bounded Phase-3 scope.
