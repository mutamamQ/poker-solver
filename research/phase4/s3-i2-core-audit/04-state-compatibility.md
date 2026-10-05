# A3I2-C4 fresh compatibility audit receipt

status=PASS_PARENT_RECONCILED
blocker_count=0
Audit-start UTC from `date -u '+%Y-%m-%d %H:%M:%S UTC'`: 2026-09-16 09:01:27 UTC

## Manifest verification

All 10 literal SHA-256 rows in CANDIDATE_MANIFEST.md verified byte-for-byte:

```sh
cd /home/genomix-node/poker-solver && sha256sum ARCHITECTURE_PHASE4_S3.md src/poker_solver/nplayer.py src/poker_solver/nplayer_preflop.py tests/test_nplayer_preflop_solve.py tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py research/phase4/s3-i2-core-build/01-core-author.md research/phase4/s3-i2-core-build/PARENT_CORE_GATE.md
```

All 10 hashes match manifest exactly. Candidate frozen at accepted_base_head=7285335caad555a9a71bd5f4055c2e1c3ee0262f confirmed as current HEAD.

## Source change scope audit

S3-I1 accepted state implementation: 1033 lines (commit 7285335).
Current candidate: 1136 lines (+103 lines appended).

The child ran `git diff <accepted-base> HEAD`, which only established that
the committed base and current committed HEAD are identical; it did not include
the uncommitted candidate. Parent reconciliation after ownership ended ran
`git diff --unified=0 7285335caad555a9a71bd5f4055c2e1c3ee0262f --
src/poker_solver/nplayer_preflop.py` against the worktree. That diff contains
only the required `Hashable`/generic solver imports and the appended 97-line
result/freezing/facade block.

Inspected lines 1–50 and 937–1136 of current nplayer_preflop.py:
- Lines 1–1039: exact S3-I1 state implementation (config, state, betting, settlement, information, root creation)
- Lines 1040–1136: appended facade and result helpers:
  - `_freeze_result_metadata` (lines 1042–1052)
  - `NPlayerPreflopSolveResult` dataclass (lines 1055–1078)
  - `solve_nplayer_preflop` facade (lines 1080–1136)
- New imports added at top (lines 20–25): `NPlayerCFRSolver`, `UnilateralDeviationCertificate`, `expected_values_nplayer`, `unilateral_deviation_certificate` from `.nplayer`

**Verdict**: Parent worktree diff verification proves that only imports and the
appended facade/result code were added. The accepted S3-I1 state/config/betting/
settlement/information implementation is byte-identical.

## S3-I1 suite execution

Four S3-I1 state suites:
```sh
pytest tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py -v
```
Exit 0: **56 passed in 0.15s**.

Solve suite:
```sh
pytest tests/test_nplayer_preflop_solve.py -v
```
Exit 0: **52 passed in 1.05s**.

Total: **108 passed**, matching parent core gate count from 01-core-author.md.

## Regression spot checks

Equal-stack fold ledger and unequal-stack closure/refund:
```sh
pytest tests/test_nplayer_preflop_settlement.py::TestUncalledRefunds::test_three_player_uncalled_raise tests/test_nplayer_preflop_settlement.py::TestSidePotLayers::test_three_level_side_pot -v
```
Exit 0: **2 passed in 0.04s**.

N=9 traversal:
```sh
pytest tests/test_nplayer_preflop_solve.py::test_fixtures_construct_and_traverse_without_facade -k 'False-1-9' -v
```
Exit 0: **1 passed in 0.06s**.

## Compatibility verdict

The appended solve facade and result helpers **did not alter** accepted S3-I1 state, config, betting, settlement, or information behavior. All 108 core tests green. Manifest byte identities confirmed. Source diff proves append-only change.

**PASS**: S3-I2 candidate preserves exact S3-I1 compatibility.

Parent reconciliation completed at 2026-09-16T09:13:26Z. Baseline tag
`phase3-398-green` was independently verified at
`feba8222a0b614b0c64eca59402403ce733195ea`.
