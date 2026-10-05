# I201 solve/diagnostic RED — parent reconciliation

Original I201 wrote a large suite but included two forbidden caught-ImportError absence tests, a non-exact reach assertion, no independent certificate oracle, and no final receipt. After its ownership ended, parent replaced those defects with permanent production-facing behavioral contracts.

Test: `tests/test_nplayer_postflop_solve.py`
SHA-256: `d606c5fb011905b4df0c3df76874e5e5c4922b0a8a91d9d3d4adfcdf9f51fcce`
Verified UTC: `2026-09-15T23:35:39Z`
Command: `uv run pytest tests/test_nplayer_postflop_solve.py -q`
Result: `9 failed in 0.11s` (exit 1).

The failures are exactly missing defining-module solve/result symbols and missing keyword-only solver bound plumbing. Permanent tests cover deterministic detached normalized 4/5/9-player solves; N values; max_nodes/max_depth forwarding; a hand-derived five-player counterfactual-reach oracle with exact +/-1 regrets; an independent traversal/pure-deviation enumerator compared to the facade certificate; and cap fail-closed. No skips, placeholders, caught imports, or source-absence tests remain.

RED_READY
