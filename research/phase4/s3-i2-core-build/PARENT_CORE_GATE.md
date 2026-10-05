# S3-I2 core parent gate

status=FOCUSED_GREEN_FULL_PENDING
verified_at=2026-09-16T08:52:12Z
accepted_base=7285335caad555a9a71bd5f4055c2e1c3ee0262f
baseline_tag=phase3-398-green
baseline_target=feba8222a0b614b0c64eca59402403ce733195ea
source_sha256=5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae

Parent-executed results:

- `tests/test_nplayer_preflop_solve.py`: `52 passed in 2.30s`, exit 0.
- solve plus four accepted S3-I1 suites: `108 passed in 1.19s`, exit 0.
- compileall `src tests`: exit 0.
- owned `git diff --check`: exit 0.
- four-suite post-core matrix: `48 failed, 60 passed in 3.89s`, exit 1. The remaining failures split exactly into API 29, examples 8, and exports/capability 11; solve has zero failures and there are zero collection errors. This is the expected core-gated integration RED, not a core defect.
- All four frozen RED test hashes and three example hashes remain identical to `research/phase4/s3-i2-red/RED_MANIFEST.md`.
- HEAD remains `7285335caad555a9a71bd5f4055c2e1c3ee0262f` and `phase3-398-green` remains `feba8222a0b614b0c64eca59402403ce733195ea`.

Full regression runs separately as tracked process `proc_4aeb141c3d78`. Core acceptance remains blocked until it passes and a fresh exact-six non-author audit is parent-accepted.
