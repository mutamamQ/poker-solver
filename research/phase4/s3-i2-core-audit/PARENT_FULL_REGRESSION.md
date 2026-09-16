# S3-I2 core parent full regression

status=CORE_AND_LEGACY_GREEN
verified_at=2026-09-16T09:00:08Z
candidate_manifest=research/phase4/s3-i2-core-audit/CANDIDATE_MANIFEST.md
candidate_manifest_sha256=81ef2c2af67792e6d1c5f5ae0ba2b2d6d433dc8c4bcca8ab662dd93100993d84
manifest_entries_verified=10/10

The first all-collected run returned `48 failed, 769 passed in 230.58s (0:03:50)`. Parent's pre-run focused taxonomy had already established that those 48 failures are exactly the separately gated integration RED: API 29, examples 8, exports/capability 11. There were zero solve failures and no failures outside those three unimplemented integration suites.

Parent then ran the complete core-plus-legacy regression while explicitly excluding only those three gated next-batch suites:

`PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider --ignore=tests/test_api_v4_nplayer_preflop.py --ignore=tests/test_phase4_s3_examples.py --ignore=tests/test_phase4_s3_exports.py`

Result: `761 passed in 223.30s (0:03:43)`, exit 0.

This is the valid full regression gate for the core-only batch. It includes the 52-test solve suite and all legacy/S1/S2/S3-I1 tests while leaving API/examples/exports RED for the architecture-gated integration owner. HEAD remains `7285335caad555a9a71bd5f4055c2e1c3ee0262f`; `phase3-398-green` remains `feba8222a0b614b0c64eca59402403ce733195ea`.
