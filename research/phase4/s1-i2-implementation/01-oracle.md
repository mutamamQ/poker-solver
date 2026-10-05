# I201 automatic-versus-explicit oracle — parent recovery

Status: GREEN_READY.

The original and correction workers did not deliver an executable complete gate. After their ownership cleared, the parent replaced the broken 602-line structural-only test with a concise permanent production-importing oracle at `tests/test_allstreet_oracle.py`.

Permanent evidence

`uv run pytest tests/test_allstreet_oracle.py -q`

Result at 2026-09-15T19:53:50Z: `5 passed in 6.41s`.

Structural exact fixture

- One combo per player, two complete two-card runouts, positive stack, and `wager_targets=(0,)` force one legal action at each decision.
- Terminal values are independently enumerated with `evaluate_seven`; neither automatic solver output nor serialized output supplies the explicit leaf.
- Player 0 has a wheel on each runout, so manual EV is exactly `+1.0` from a dead pot of 2.
- The separate explicit GameState truncates after flop check/check at that independently computed continuation.
- Automatic and explicit root values both equal `+1.0` within `1e-12`; both NashConv values are zero; every policy is finite, nonnegative, and normalized.

Strategic fixture

- One combo per player, one complete deterministic two-card runout, stack 1, `wager_targets=(1,)`, and the real automatic all-street tree produce nontrivial check/raise/fold/call choices on flop, turn, and river.
- A separate explicit flop GameState uses independently backward-induced continuation leaves. Player 0 wins every showdown: call utility is `+2`, player-0-bet/fold utility is `+1`, player-1-bet/player-0-fold utility is `-1`; minimax backward induction gives continuation value `+1` on every street.
- At 1,000 CFR iterations the root gap obeys the fixed derived bound `|EV_auto - EV_explicit| <= NC_auto + NC_explicit + 1e-12`; each representation is also within its own NashConv plus numerical tolerance of the exact equilibrium value.
- A 20/100/500 iteration sweep proves the bound at every point and confirms both total NashConv and root-value gap improve from first to last.

Additional gates

- Exhaustive production terminal traversal is finite and zero-sum for both fixtures.
- Repeated production vanilla-CFR runs are exactly deterministic.
- The explicit representation is test-only; no unsupported public continuation field or production API was introduced.
