# A3I2-I6R Release Audit Report

## Audit Metadata
- **Auditor**: A3I2-I6R (fresh non-author release auditor, retry)
- **Candidate**: S3-I2 integration frozen working-tree (20 files)
- **Base**: 68e0ad2e9983928e666c3aabfa5d32161f7baca8
- **Baseline Tag**: feba8222a0b614b0c64eca59402403ce733195ea (phase3-398-green)
- **Audit Start**: 2026-09-16T10:25:18Z
- **Audit End**: 2026-09-16T10:33:30Z
- **Duration**: ~8m12s

## Candidate Integrity
- **Pre-audit verification**: 20/20 hashes PASS (2026-09-16T10:25:18Z)
- **Post-audit verification**: 20/20 hashes PASS (2026-09-16T10:33:30Z)
- **Status**: IMMUTABLE (no candidate mutation during audit)

## Test Execution

### Focused integration plus solve tests (108 tests)
- **Command**: `python -m pytest tests/test_api_v4_nplayer_preflop.py tests/test_nplayer_preflop_solve.py tests/test_phase4_s3_examples.py tests/test_phase4_s3_exports.py -v --tb=short`
- **Result**: 108 passed in 3.88s
- **Status**: PASS
- **Scope**: API v4 contract (30), solve core (52), examples (13), exports (13); 56 integration tests plus 52 solve tests

### Full Regression (817 tests)
- **Command**: `python -m pytest --tb=short -q`
- **Result**: 817 passed in 387.31s (0:06:27)
- **Status**: PASS
- **Exclusions**: NONE
- **Collection**: 817 tests collected in 0.81s

### Syntax & Quality Gates
- **compileall**: `python -m compileall -q src/poker_solver tests examples` → PASS (exit 0, no output)
- **git diff --check**: PASS (exit 0, no whitespace errors)

## Verdict
**RELEASE APPROVED**

All gates passed:
- ✓ 20/20 candidate hashes verified (pre/post)
- ✓ Baseline tag feba8222a0b614b0c64eca59402403ce733195ea confirmed
- ✓ 56 integration tests passed
- ✓ 52 solve tests passed
- ✓ 817 full regression tests passed (no exclusions)
- ✓ compileall clean
- ✓ git diff --check clean
- ✓ Candidate immutable throughout audit

## Blockers
NONE
