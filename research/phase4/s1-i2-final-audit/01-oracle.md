# A201 independent oracle audit — parent-normalized

Verdict: PASS.

The sole recovery completed after the original A201 transport failure. Candidate identity matched all eight manifest hashes both before and after the audit.

Executed evidence

- `uv run pytest tests/test_allstreet_oracle.py -q`: 5 passed in 6.16s.
- A production-importing disposable traversal exercised the `MultiStreetState` protocol and observed terminal `(1.0, -1.0)`.
- No candidate or environment file was modified; only the assigned report/heartbeat and a disposable `/tmp` probe were written.

Oracle findings

- Structural fixture: automatic full-tree solve, separately implemented explicit terminal representation, and direct `evaluate_seven`/ledger enumeration agree at +1 for player 0.
- Strategic fixture: the test-only explicit flop game uses a manually backward-inducted +1 turn/river continuation; it never consumes automatic solver output.
- `initial_dead_pot=2`, `effective_stack=1`, and one-chip call/fold ledger produce +1 on a fold and +2 on a losing call for player 0, so backward induction gives equilibrium value +1.
- The finite-iteration assertion `|EV_auto-EV_explicit| <= NC_auto+NC_explicit+1e-12` passed, as did each profile's bound to the manually derived value.
- The 20/100/500 sweep proves first-to-last improvement of joint NashConv and value gap; it does not claim pointwise monotonicity.
- Permanent checks also establish policy normalization, deterministic vanilla repeats, finite terminals, and zero-sum terminal accounting.

Blockers: none.
