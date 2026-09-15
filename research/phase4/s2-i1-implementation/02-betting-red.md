# I102 betting RED — parent recovery

Original I102 failed at the provider boundary after its ownership warning did not land. The surviving file was I101's unauthorized placeholder-only content and was rejected completely.

The parent replaced it after all I102 ownership cleared with a production-importing behavioral suite covering clockwise pending order, legal actions, actor-labelled history, full raises, calls, short all-ins, closure, direct-state invariants, and the structural depth bound.

Command: `uv run pytest tests/test_nplayer_postflop_betting.py -q`
Observed RED: collection error `ModuleNotFoundError: No module named 'poker_solver.nplayer_postflop'` (exit 2).
Production module remained absent.
SHA-256: `93c7a7ace70197a5389ce6dc4cf199bbe2a7191fac25df4ad93da0a70618e57a`.

Verdict: RED_READY, parent-verified at 2026-09-15T22:09:32Z.
