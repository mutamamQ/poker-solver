# I205 core GREEN — parent recovery

Both BryantGPT core attempts ended without production: the first correctly honored missing RED gates, while the post-gate replacement falsely reported unavailable tools after read-only analysis. After ownership ended, parent implemented the exclusive core scope.

Changes:
- `NPlayerCFRSolver.__init__` accepts keyword-only `max_nodes=100_000` and `max_depth=512`, forwarding both to `collect_nplayer_infosets` while preserving legacy defaults.
- `NPlayerPostflopSolveResult` and deterministic `solve_nplayer_postflop` provide detached normalized strategy, N expected values, optional exact exhaustive unilateral-deviation certificate, strict positive bounds, truthful no-convergence metadata, and config-derived traversal bounds.

Verification UTC: `2026-09-15T23:42:41Z`
- `uv run pytest tests/test_nplayer_postflop_solve.py -q` → `9 passed in 0.77s`
- `uv run pytest tests/test_nplayer.py -q` → `23 passed in 0.14s`
- five typed postflop modules → `55 passed in 0.89s`

Source SHA-256:
- `nplayer.py`: `484b95ec85131f3d50212398dc3055dd747a03fb5a5151333a28c6130980b294`
- `nplayer_postflop.py`: `fef16496ca6e2d48f1009d49e73e38fa2177b0e2a2404987bf5e95761b73aad5`

CORE_GREEN_READY
