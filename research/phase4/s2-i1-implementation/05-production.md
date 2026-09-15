# S2-I1 production — parent recovery

The replacement GREEN worker `deleg_38937da1` read the architecture/tests but produced no source, report, heartbeat, or executable result. Parent verification confirmed zero live workers and absent production before recovery.

The parent implemented only `src/poker_solver/nplayer_postflop.py` after all four parent-verified RED receipts. It provides strict immutable 2–9-player config/state, exact deterministic deal masses, root chance normalization and coverage validation, actor-labelled public history, bounded betting with full/short all-in reopening, exact refund/side-pot/rake/odd-chip settlement, N-seat padding, conservation, and information-safe keys.

One parent-authored betting test had contradicted the accepted contract by requesting `FOLD` when `CHECK` was available. After production exposed this, the test was corrected to create a wager before folding; production retained the required no-fold-when-checking behavior. Current betting test SHA-256 is `76a880e425bd118e283dea6ce30c2d680fd9a4ba40110b069b589ba20c292b3c`.

Verification:
- `uv run pytest tests/test_nplayer_postflop_config.py tests/test_nplayer_postflop_betting.py tests/test_nplayer_postflop_settlement.py tests/test_nplayer_postflop_information.py -q` → `40 passed in 0.17s`.
- `uv run pytest tests/test_multiway_phase3.py tests/test_nplayer.py tests/test_game_structure.py -q` → `44 passed in 0.19s`.
- `uv run pytest -q` → `596 passed in 208.28s (0:03:28)`.
- `git diff --check` passed.
- `phase3-398-green` remained present.

Production SHA-256: `83861a58872a6dbfb1ce0cdbfebecaf8f016f1575b7a8bf19bc5d734eac5dfdd`.

Verdict: GREEN_READY, parent-verified at 2026-09-15T22:27:24Z.
