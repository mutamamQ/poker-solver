# I101 config/deals RED — parent reconciliation

I101 recovery replaced the original placeholder suite with production-importing validation and deterministic-deal contracts, but stalled after writing and left no report/heartbeat. After ownership cleared, the parent corrected missing `isfinite`, isolated validation cases from the matched-root invariant, bound normalized probability checks to root chance outcomes, asserted exact raw Fraction masses, and moved showdown coverage to root construction.

Command: `uv run pytest tests/test_nplayer_postflop_config.py -q`
Observed RED: collection error `ModuleNotFoundError: No module named 'poker_solver.nplayer_postflop'` (exit 2).
Production module remained absent.
SHA-256: `3efc06fd87e13789d3ec3b11f927babbfce268fe306247db54c2f1ea91a1adde`.

Verdict: RED_READY, parent-verified at 2026-09-15T22:13:15Z.
