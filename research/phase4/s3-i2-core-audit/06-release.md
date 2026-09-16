# S3-I2 release/full-regression audit

status=PASS
verified_at=2026-09-16T09:19:23Z
candidate_manifest=research/phase4/s3-i2-core-audit/CANDIDATE_MANIFEST.md
candidate_manifest_sha256=81ef2c2af67792e6d1c5f5ae0ba2b2d6d433dc8c4bcca8ab662dd93100993d84
manifest_entries_verified=10/10
phase3_398_green_hash=feba8222a0b614b0c64eca59402403ce733195ea

## Pre-flight verification

```bash
git rev-parse phase3-398-green
# feba8222a0b614b0c64eca59402403ce733195ea ✓

sha256sum research/phase4/s3-i2-core-audit/CANDIDATE_MANIFEST.md
# 81ef2c2af67792e6d1c5f5ae0ba2b2d6d433dc8c4bcca8ab662dd93100993d84 ✓

python3 -m compileall -q .
# exit 0 ✓

git diff --check
# exit 0 ✓
```

## Core+legacy regression (excluding gated integration RED)

Command from PARENT_FULL_REGRESSION.md:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider \
  --ignore=tests/test_api_v4_nplayer_preflop.py \
  --ignore=tests/test_phase4_s3_examples.py \
  --ignore=tests/test_phase4_s3_exports.py
```

Result: **761 passed in 234.70s (0:03:54)**, exit 0 ✓

This is the valid full regression gate for the core-only batch. It includes the 52-test solve suite and all legacy/S1/S2/S3-I1 tests while leaving API/examples/exports RED for the architecture-gated integration owner.

## S3-I2 integration RED (gated next-batch suites)

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider \
  tests/test_api_v4_nplayer_preflop.py \
  tests/test_phase4_s3_examples.py \
  tests/test_phase4_s3_exports.py
```

Result: **48 failed, 8 passed in 1.30s**, exit 1

Failure breakdown by file:
- `tests/test_api_v4_nplayer_preflop.py`: 29 failures (all ValueError: operation must be one of ['solve-allstreet-postflop', 'solve-nplayer-postflop'])
- `tests/test_phase4_s3_examples.py`: 8 failures (all ValueError: operation must be one of ['solve-allstreet-postflop', 'solve-nplayer-postflop'])
- `tests/test_phase4_s3_exports.py`: 11 failures (9 AssertionError: symbol not exported from package root, 2 KeyError: 'nplayer-preflop' capability missing)

Total: 29 + 8 + 11 = 48 failures ✓

These are exactly the separately gated integration RED suites. There were zero solve failures and no failures outside these three unimplemented integration suites.

## Post-flight verification

```bash
sha256sum research/phase4/s3-i2-core-audit/CANDIDATE_MANIFEST.md
# 81ef2c2af67792e6d1c5f5ae0ba2b2d6d433dc8c4bcca8ab662dd93100993d84 ✓
```

Candidate hash remains stable at 10/10 entries.

## Verdict

**PASS**: Core-plus-legacy regression GREEN (761 tests), integration RED as expected and gated for the integration owner (48 failures across API/examples/exports). Candidate manifest stable. No regressions in core or legacy tests.