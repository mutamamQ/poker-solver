# S3-I1 Config/Positions/Deals RED Receipt

Owner R3I1-1R ended after writing an overbroad 645-line suite with function-local production imports, causing fifteen caught `ModuleNotFoundError` test failures rather than the required collection-stage RED. It wrote no receipt/heartbeat and incorrectly attempted to begin production before the four-RED gate. Production remained absent.

After ownership cleared, the parent replaced only this scope with five narrow permanent behavioral functions (seven parametrized cases):

1. N=2 and N=9 root/deal/action order through the architecture protocol.
2. `num_players` strict rejection of bool, 1, and 10.
3. Uniform all-seat ante accounting, proving antes do not enter `street_committed`.
4. The N=3 standard-straddle boundary plus HU Mississippi rejection.
5. Deterministic blocker pruning, exact normalized masses, and candidate-product `max_deals` fail-closed behavior.

The suite has a direct module-scope import from `poker_solver.nplayer_preflop`, valid integer card IDs, `ForcedPost` values, `WeightedCombo` values, and protocol `chance_outcomes`/`child`/`current_player` calls. It contains no caught imports, skips, xfails, placeholders, vacuous assertions, or invented APIs.

Parent verification:

- command: `uv run pytest -q tests/test_nplayer_preflop_config.py`
- exit: 2
- sole reason: `ModuleNotFoundError: No module named 'poker_solver.nplayer_preflop'`
- test SHA-256: `5a214b900a7ad1b61aa67cd294d7000e3eef0023f82bb834d1e94035f815a867`
- architecture SHA-256: `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`
- design commit: `65d411793d1d7767d86500d0adffe9f40b379108`

Disposition: `RED_CONFIRMED`.

Post-GREEN correction/revalidation at `2026-09-16T05:28:29Z`: the N=3 ante and standard-straddle fixtures had inherited the helper's button rather than the blind-derived button. The parent corrected only those two public fixture values, temporarily removed production, and reproduced isolated exit 2 with the exact missing-module cause before restoring production and obtaining GREEN.
