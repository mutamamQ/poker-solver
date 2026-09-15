# S2-I1 repaired settlement audit A202 — parent reconciliation

Fresh non-author A202 read the architecture, repaired manifest, settlement test and production accounting code; verified the five initial hashes; ran `python -m pytest tests/test_nplayer_postflop_settlement.py -v` with 4/4 passing; and executed an additional 4/5/9-player settlement probe. Its extra probe imported shared production accounting primitives, so it was not accepted as the requested independent oracle, and its later refund code was printed rather than executed. It also failed to write its assigned report/heartbeat.

Parent reconciliation at 2026-09-15T23:02:36Z:
- all five frozen hashes still match the repaired manifest;
- permanent settlement tests import no settlement-calculation primitive and assert fixed expected ledgers;
- a separate parent pure-arithmetic check with no `poker_solver` import verified all four expected fixtures:
  - N=4 layers `(1200, 600, 600)`, 100 top-down rake, returns `(-300, -800, 1500, -500)`;
  - N=5 layers `(2000, 400, 300)`, one-chip rake from the final layer, odd order awards seat 1 the remainder, returns `(749, 750, -500, -400, -600)`;
  - N=9 layers `(1200, 250, 200, 150, 100)`, 190 rake, seat 1 utility 1310 and nine-seat padding;
  - N=2 pre-refund totals `(20, 100)` and streets `(10, 90)` yield an 80 refund bounded by 90 street chips, matched totals `(20, 20)` and streets `(10, 10)`.

Verdict: PASS after parent qualification. A202 supplies fresh non-author review and executable settlement-suite evidence; the parent supplies the missing independent arithmetic and post-hash verification.
