# S2-I1 rejected-audit repair

Parent reconciled the first frozen audit and rejected acceptance despite a green full regression.

Repaired permanent coverage:

1. `tests/test_nplayer_postflop_information.py`
   - six projected legacy/generic traces covering check, raise, call, fold, fold-out, and full re-raise;
   - per-step actors, legal actions, public ledgers, raise state, and action history projection;
   - terminal utility equivalence;
   - multi-deal information-partition equivalence for all three seats.

2. `tests/test_nplayer_postflop_settlement.py`
   - removed shared settlement primitives from expected-value computation;
   - retained hand-derived fixed 4/5/9-player terminal ledgers;
   - created a one-chip rake remainder in the five-player tied layer and asserted that declared order awards it to seat 1;
   - added a production betting transition whose 80-chip refund is bounded by 90 current-street chips, asserting matched ledgers `(20, 20)`, post-refund streets `(10, 10)`, remaining `(0, 80)`, pot 40, and returns `(-20, 20)`.

Parent verification: 46 focused, 44 legacy-focused, and 602 full-suite tests passed; whitespace and baseline tag checks passed.
