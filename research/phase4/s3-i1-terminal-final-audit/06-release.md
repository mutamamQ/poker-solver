# TA3A6R final release integrity audit

status=COMPLETE_PASS
completed_at=2026-09-16T07:49:17Z
completion_time_normalized_by=parent_from_canonical_write_receipt
auditor=TA3A6R
base_directory=/home/genomix-node/poker-solver
accepted_base_head=65d411793d1d7767d86500d0adffe9f40b379108
phase3_baseline_tag=feba8222a0b614b0c64eca59402403ce733195ea
candidate_manifest=research/phase4/s3-i1-terminal-final-audit/CANDIDATE_MANIFEST.md

## Manifest integrity

All 11 candidate hashes verified before and after test execution:

- 6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db  ARCHITECTURE_PHASE4_S3.md
- a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812  src/poker_solver/nplayer_preflop.py
- 8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240  src/poker_solver/sizing.py
- bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268  tests/test_nplayer_preflop_config.py
- 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd  tests/test_nplayer_preflop_betting.py
- e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
- 1217cf74f1468252fbc7f941621dc57154c910003eb27fbf8947b7bc5a42e289  tests/test_nplayer_preflop_information.py
- 2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1  tests/test_sizing.py
- 61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11  research/phase4/s3-i1-repair/RED_RECEIPT.md
- 36a95b38ec1b6016bc46ca80307b2c9f4119c749fceb51cd822bccaf61965164  research/phase4/s3-i1-spec-reconciliation/RECEIPT.md
- b631cc2b933c314c081a70e6b3aaa669ae15054145301d272e1a18967d68a42a  research/phase4/s3-i1-terminal-ledger-reconciliation/RECEIPT.md

## TDD chronology verification

RED_RECEIPT.md confirms:
- Pre-repair production hashes: nplayer_preflop.py 0e55fbce..., sizing.py 57cbb6e4...
- RED command: `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_information.py tests/test_sizing.py`
- RED result: 15 failed, 57 passed in 0.34s
- Final replay after coverage addition: 15 failed, 59 passed in 0.44s
- Six behavioral repair categories: forced-post kinds, odd-chip aliases, sizing hash contract, Decimal NaN/Infinity, invalid chance roots, recursive depth
- Added coverage-only fixtures were already green

Spec reconciliation receipts distinguish:
- Behavioral RED: the six C3I1-5 runtime blockers repaired in production
- Immediate-green characterization: HU chipless-responder suffix and equal-stack fold terminal ledger normalization added as permanent regression without production change

## Baseline verification

- HEAD: 65d411793d1d7767d86500d0adffe9f40b379108 ✓
- phase3-398-green tag: feba8222a0b614b0c64eca59402403ce733195ea ✓

## Focused regression

Command: `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py tests/test_sizing.py`

Result: 81 passed in 0.37s ✓

## Full regression

Command: `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider --tb=no`

Result: 709 passed in 387.47s (0:06:27) ✓

Total test files: 53

## Code quality

- `python3 -m compileall -q src tests`: PASS ✓
- `git diff --check`: PASS ✓
- No unauthorized probes or modifications detected
- Candidate files read-only throughout audit

## Disposition

COMPLETE_PASS: All 11 candidate hashes verified, HEAD and baseline tag confirmed, TDD chronology validated with behavioral RED distinguished from immediate-green characterization, focused 81-test suite green, full 709-test regression green, code quality checks passed, no blockers.
