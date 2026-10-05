# C3I2-G6R TDD/release chronology and post-build gate

Status: COMPLETE_ANALYSIS; blocker_count=0.
Live UTC: 2026-09-16T08:39:53Z

## Authenticated chronology

Parent observed final S3-I2 RED suite against accepted base `7285335caad555a9a71bd5f4055c2e1c3ee0262f` (tag `phase3-398-green` at `feba8222a0b614b0c64eca59402403ce733195ea`):

- **RED_MANIFEST.md frozen:** 2026-09-16T08:36:00Z
- **Combined command:** `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_solve.py tests/test_api_v4_nplayer_preflop.py tests/test_phase4_s3_examples.py tests/test_phase4_s3_exports.py`
- **Authenticated result:** 89 failed, 19 passed in 1.96s, exit 1, zero collection errors
- **Failure split:** solve 41, API 29, examples 8, exports/capability 11
- **Passing controls:** typed N=2/6/9 fixture construction/traversal, independent six-player deviation arithmetic, legacy envelope validation, generic CLI errors, S1/S2 export/capability preservation

**Solve suite detail (01-solve.md):**
- 41 failed, 11 passed
- 1 missing `NPlayerPreflopSolveResult` import, 40 missing `solve_nplayer_preflop` imports
- Zero fixture/config/root/traversal/bound/oracle failures
- Independent rational oracle verified: six-player pure counts (1,4,4,1,1,1), baseline EV (5,1/8,-17/8,-1,-1,-1), incentives (0,3/8,3/8,0,0,0)
- Exact cap 4 succeeds; cap 3 fails closed in generic control
- SHA-256: `45291a2e7537883acfcf35a3c700e50fe03225c4a00db3a75372ca243326d51c`

No production source changed during RED. Core GREEN ownership transferred to implementation agent after parent verification.

## Core GREEN checklist (mandatory before integration)

### 1. Frozen core candidate

- [ ] Extend **ONLY** `src/poker_solver/nplayer_preflop.py`
- [ ] Implement missing symbols: `NPlayerPreflopSolveResult`, `solve_nplayer_preflop`
- [ ] Zero edits outside the owned source, core-author report, and heartbeat
- [ ] Verify final RED hashes (four test files, three examples, six research docs per RED_MANIFEST.md)
- [ ] Rerun the exact core command: `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_solve.py tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py`
- [ ] Target: 108 passed, exit 0; parent collection independently confirms this core command contains 108 tests
- [ ] Rerun the four-suite combined command only to confirm remaining failures belong exclusively to the still-gated API/examples/exports integration scope; it is not expected to be all green before integration
- [ ] Verify S1/S2 preservation: all prior tests green
- [ ] Document: core GREEN receipt with SHA-256 `nplayer_preflop.py`, exact command, exit code, pass count, live UTC

### 2. Mandatory wholly fresh different exact-six post-build non-author audit

**ARCHITECTURE_PHASE4_S3.md § 12:**
> A gated core owner may extend only `nplayer_preflop.py`; a core-gated integration owner may extend `api_v4.py`, `api_v3.py`, package exports, and examples after the RED and core receipts. The same focused/full/freeze/fresh-audit/parent/commit gate applies.

**PHASE4_MISSION.md § 1 (HARD RULES):**
> **Adversarial cross-check after EVERY implementation batch:** a FRESH set of non-author BryantGPT auditors (different from the implementers) must RUN the code (focused tests + the suite + the new invariants) before the next batch starts. Width ≤ 6.

**Audit requirements:**
- [ ] Spawn exactly 6 fresh BryantGPT subagents (different from RED/core GREEN authors)
- [ ] Each auditor: independent read of ARCHITECTURE § 2.5, 10, 12, 13; run the focused core gate; verify independent oracle; check one distinct core acceptance criterion from § 13
- [ ] A combined-suite run may document that only gated integration behavior remains RED; do not require API/examples/exports GREEN before their owner is assigned
- [ ] Audit scope: HU/6/9 deterministic policies, exact structural depth, N expected values, normalized strategies, exhaustive diagnostic below cap, independent six-player deviation oracle match
- [ ] Zero skips, xfails, mocks, placeholders in audit runs
- [ ] Document: six audit receipts with SHA-256 verification, exact commands, exit codes, live UTC, distinct acceptance evidence
- [ ] Parent verification: inspect all six receipts, confirm different agents, confirm executable evidence

### 3. Integration gate (after core GREEN + audit accepted)

- [ ] Core-gated integration owner extends: `api_v4.py`, `api_v3.py`, package exports, examples
- [ ] Forbidden: `cli.py` changes unless genuine failing generic-CLI contract proves necessity
- [ ] Rerun full combined suite: 108 passed, exit 0
- [ ] Verify baseline tag: `phase3-398-green` at `feba8222a0b614b0c64eca59402403ce733195ea` unchanged
- [ ] Accepted-wave commit: descriptive message, no tag yet
- [ ] Document: integration receipt with SHA-256 all modified files, exact command, exit code, live UTC

## Post-build gate summary

S3-I2 is complete only when:
1. Core GREEN: `nplayer_preflop.py` implements missing symbols, the 108-test core command passes, parent-verified receipt
2. Fresh audit: 6 different non-author BryantGPT agents run code, verify oracles, confirm acceptance criteria, parent-verified receipts
3. Integration: API/exports/examples extended, full suite green, accepted-wave commit

No production ownership. No `phase4-complete` tag until PHASE4_MISSION.md § 3 goal-check gate passes for all S1–S7.

## Parent reconciliation

The parent accepted the pre-implementation chronology and frozen test hashes. It corrected the original checklist's category error: the core-only source change cannot make the strict API/examples/package-export suites green before the separately gated integration owner runs. The 108-pass target belongs to the solve-plus-S3-I1 core command, whose collection count the parent verified independently. The child heartbeat predates the report write and is not completion evidence; parent-authored completion evidence is stored separately.

---

**Authenticated by:** C3I2-G6R (TDD/release analyst, retry)
**Live UTC:** 2026-09-16T08:39:53Z
**Exclusive writable paths:** /home/genomix-node/poker-solver/research/phase4/s3-i2-core-build/06-tdd-release.md, /home/genomix-node/poker-solver/research/phase4/s3-i2-core-build/.hb/C3I2-G6R
**No edits:** source/tests/examples/APIs/other reports/STATE/PROGRESS/git; no commit