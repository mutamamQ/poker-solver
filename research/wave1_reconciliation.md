# Wave 1 design reconciliation

The ten Wave 1 designers returned protocol, CFR, evaluator, validation, CLI, river-game, exploitability, packaging, adversarial-critique, and integration proposals. `ARCHITECTURE.md` is the orchestrator's reconciled authority.

Accepted: generic immutable protocol; exact evaluator; vanilla full-tree CFR; exact pure-strategy BR for small games; explicit NashConv normalization; fixed-board combo-weighted river game; standard-library runtime; deterministic CLI.

Rejected from drafts: sampled boards/hands in the exact river game; card bucketing; automatic bet clamping; regret clipping/pruning; claims of monotonic exploitability; guessed convergence thresholds; incorrect AA-vs-KK percentages; timestamps/seeds for deterministic full traversal; multithreading; Monte Carlo equity; range shorthand; raises and all-in reopening in the shipped minimal tree; testing one arbitrary Kuhn equilibrium strategy rather than value/NashConv.
