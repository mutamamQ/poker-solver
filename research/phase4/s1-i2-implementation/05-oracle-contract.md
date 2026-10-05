# I205 independent oracle contract — parent adjudication

Status: SATISFIED by `tests/test_allstreet_oracle.py`.

Non-circularity rules

1. The explicit continuation representation must not consume values or policies emitted by `solve_allstreet_postflop`.
2. Terminal payoffs must come from independent card enumeration or manual pot/contribution accounting.
3. A forced-action structural fixture may establish exact tree/chance/accounting equivalence, but cannot replace a strategic fixture.
4. The strategic fixture must contain real check/raise/fold/call choices and a separately implemented explicit-continuation GameState.
5. For equivalent finite zero-sum games, compare root profile values using:
   `|EV_auto - EV_explicit| <= NC_auto + NC_explicit + delta_num`,
   where `delta_num = 1e-12` for these integer-payoff fixtures.
6. Require finite zero-sum terminals, normalized policies, deterministic vanilla-CFR, and a measured convergence sweep.

Production facts verified

- `AllStreetPostflopConfig.effective_stack` must be a positive integer.
- `wager_targets=(0,)` is valid and forces check-only decisions; an empty tuple does not satisfy this oracle contract.
- `evaluate_seven` uses larger rank tuples as stronger hands, matching production comparisons `h0 > h1`.
- With `As5s` versus `KhQh` on `2c3d4h`, both selected runouts leave player 0 with the winning wheel. With dead pot 2 and no contributions, player-0 utility is exactly `+1.0`.

Strategic backward induction

For stack 1 and a player-0 winning showdown:

- player-0 bet followed by fold: `+1`;
- bet/call showdown: `+2`;
- player-0 fold to a player-1 bet: `-1`.

At each street, player 0 can secure `+1`; player 1 can hold player 0 to `+1`. Therefore river, turn, and flop equilibrium continuation values are each exactly `+1`. The permanent explicit fixture uses those manually derived leaves and never calls the automatic solve path to generate them.

Execution receipt

At 2026-09-15T19:53:50Z, `uv run pytest tests/test_allstreet_oracle.py -q` returned `5 passed in 6.41s`.
