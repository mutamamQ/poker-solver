# S3-I1 repair audit: release/TDD (R3A6R)

status=COMPLETE_PASS
completed_at=2026-09-16T06:31:27Z
auditor_role=R3A6R
base_head=65d411793d1d7767d86500d0adffe9f40b379108
phase3_baseline_tag=feba8222a0b614b0c64eca59402403ce733195ea

## Baseline verification

All 9 manifest hashes verified against /home/genomix-node/poker-solver:

- a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6  ARCHITECTURE_PHASE4_S3.md
- a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812  src/poker_solver/nplayer_preflop.py
- 8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240  src/poker_solver/sizing.py
- bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268  tests/test_nplayer_preflop_config.py
- 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd  tests/test_nplayer_preflop_betting.py
- e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
- 0d800d2f8fe797f29d8a347e1ab216bbc079fee0ede792ab253db23097819445  tests/test_nplayer_preflop_information.py
- 2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1  tests/test_sizing.py
- 61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11  research/phase4/s3-i1-repair/RED_RECEIPT.md

Git state:
- HEAD: 65d411793d1d7767d86500d0adffe9f40b379108
- phase3-398-green tag: feba8222a0b614b0c64eca59402403ce733195ea (exact immutable baseline)

## Test execution

### Four S3-I1 suites

Command:
```
uv run pytest tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py -v --tb=short
```

Result: 55 passed in 0.28s

### test_sizing suite

Command:
```
uv run pytest tests/test_sizing.py -v --tb=short
```

Result: 25 passed in 0.31s

### Full regression

Command:
```
uv run pytest -q -p no:cacheprovider
```

Result: 708 passed in 378.79s (0:06:18)

### Whitespace check

Command:
```
git diff --check
```

Result: exit 0 (clean)

## Architecture compliance

### Production imports

All four test suites import real production modules at module scope:
- `from poker_solver.nplayer_preflop import ...`
- `from poker_solver.sizing import ...`
- `from poker_solver.preflop import WeightedCombo`
- `from poker_solver.model import Action, CHANCE, TERMINAL`
- `from poker_solver.game_structure import ForcedPost`

No mocks, no placeholders, no import catches, no skip/xfail decorators.

### RED replay authenticity

RED_RECEIPT.md documents 15 failed, 59 passed against pre-repair production hashes:
- pre-repair nplayer_preflop.py: 0e55fbce5f6934c8e2e63ee28ce9d01d9268792165d9318bc8c9ed03b5f73422
- pre-repair sizing.py: 57cbb6e4027b82282c6ddd888ee06c8ce79d6eece0da053b5ed0fa8c841742e8

The 15 failures directly reproduced six C3I1-5 runtime blockers:
1. Unsupported forced-post kinds (3 failures)
2. Bool/float odd-chip seat aliases (2 failures)
3. Mutable sizing-expression backing/hash contract (1 failure)
4. Decimal NaN/Infinity sizing rejection and exception normalization (3 failures)
5. Invalid direct chance roots (5 failures)
6. Accepted structural depth beyond recursive solver limit (1 failure)

### Architecture-required permanent coverage

Verified present in test suites:

**Positive double/Mississippi straddles:**
- `test_double_and_mississippi_straddles_have_distinct_repeatable_roots` (config)
- Distinct ledgers, first actors, and trees confirmed

**All-in option exclusion:**
- `test_exact_all_in_straddler_has_no_pending_option` (config)
- Exact all-in posts never truncated, all-in seats absent from pending

**Strict configs:**
- `test_strict_config_boundary_matrix` (config)
- N=2 through N=9 acceptance
- Invalid ante arrangements rejected: `test_invalid_ante_arrangements_fail_closed`
- Non-increasing straddles rejected: `test_double_straddle_amounts_must_strictly_increase`

**Limp/SB caller counting:**
- `test_limp_counts_as_pre_raise_caller` (betting)
- `test_small_blind_completion_counts_as_pre_raise_caller` (betting)
- SB completion counted as pre-raise CALL for cold_callers

**Completed 3/4/5-bet:**
- `test_completed_three_four_five_bet_sizing_key_trace` (betting)
- Exact sizing-key selection through raise_count progression

**Direct roots:**
- `create_nplayer_preflop_root` used throughout
- No invalid chance root construction: `test_direct_chance_root_rejects_impossible_state`

**Mutation/hash stability:**
- `test_sizing_expression_backing_is_immutable_and_hash_stable` (config)
- Frozen expression backing, hashable, immutable

**Exact masses:**
- `test_blocker_pruning_exact_mass_and_candidate_product_bound` (config)
- Deterministic chance reach, normalized exact Fraction masses

**N=6/9 noninterference:**
- `test_information_key_excludes_opponent_cards_for_first_actor[6]` (information)
- `test_information_key_excludes_opponent_cards_for_first_actor[9]` (information)
- `test_information_key_excludes_hidden_showdown_ranks[6]` (information)
- `test_information_key_excludes_hidden_showdown_ranks[9]` (information)

**Expanded HU projection:**
- `test_projected_hu_trace_and_information_partitions_match_legacy` (information)
- `test_projected_hu_call_raise_reraise_traces_match_legacy` (information)
- Normalized private deals, exact masses, acting seat, ordered legal actions, pot/commitments/stacks/fold status, exact terminal utilities, information partition alignment

### Post-run hash verification

Production file after full test execution:
- src/poker_solver/nplayer_preflop.py: a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812

Matches expected production hash from CANDIDATE_MANIFEST.md exactly.

All test file hashes match manifest:
- tests/test_nplayer_preflop_config.py: bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268
- tests/test_nplayer_preflop_betting.py: 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd
- tests/test_nplayer_preflop_settlement.py: e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3
- tests/test_nplayer_preflop_information.py: 0d800d2f8fe797f29d8a347e1ab216bbc079fee0ede792ab253db23097819445
- tests/test_sizing.py: 2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1

## Conclusion

Status: COMPLETE_PASS
Blocker count: 0

All architecture-required coverage present and passing. Production imports real, RED replay authentic, full regression clean, exact baseline tag verified, post-run hashes stable.

Candidate ready for acceptance.
