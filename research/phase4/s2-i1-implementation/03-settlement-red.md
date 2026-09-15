# I103 settlement RED — parent recovery

The original I103 failed with a schema-class 502. Its recovery then produced a false-positive suite that passed only because production was absent; that result was rejected. After recovery ownership cleared, the parent replaced it with production-importing 4/5/9-player settlement contracts plus independently hand-derived refund, layer, rake, tie, odd-chip, trailing-seat, utility, and conservation expectations.

Command: `uv run pytest tests/test_nplayer_postflop_settlement.py -q`
Observed RED: collection error `ModuleNotFoundError: No module named 'poker_solver.nplayer_postflop'` (exit 2).
Production module remained absent.
SHA-256: `1b97dce26eaf98974f2039eddfdbff3dded600bf4e1fecd46e1047205c21f71d`.

Verdict: RED_READY, parent-verified at 2026-09-15T22:09:32Z.
