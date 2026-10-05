# S3-I2 core final acceptance

status=ACCEPTED
accepted_at=2026-09-16T09:28:26Z
accepted_base=7285335caad555a9a71bd5f4055c2e1c3ee0262f
phase3_baseline_tag=feba8222a0b614b0c64eca59402403ce733195ea
candidate_manifest_sha256=81ef2c2af67792e6d1c5f5ae0ba2b2d6d433dc8c4bcca8ab662dd93100993d84
candidate_manifest_entries=10/10
production_sha256=5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae
solve_test_sha256=45291a2e7537883acfcf35a3c700e50fe03225c4a00db3a75372ca243326d51c

## Parent gates

- solve facade: 52 passed
- core gate: 108 passed
- core-plus-legacy regression: 761 passed
- separately gated integration RED: 48 failed, 8 passed, exact breakdown API/examples/exports 29/8/11
- compileall: passed
- git diff --check: passed
- phase3 baseline tag: exact
- frozen candidate after audit: 10/10

## Fresh non-author audit slots

1. strictness/immutability: `63edf18f686636f4adda8c067628c03d79c7ce2e0896db6ba6a4109175d563f4  research/phase4/s3-i2-core-audit/01-result-strictness-r.md`
2. determinism/independent oracle: `aa5be7c72696903d831cfecf37b4490249a301328c676eedc9949ad2e8cecaa7  research/phase4/s3-i2-core-audit/02-determinism-oracle-r.md`
3. depth/node/certificate bounds: `07fa699ba8d71e195416f89ded5e551da656f1b9356956e6aaaa2b248ba4a232  research/phase4/s3-i2-core-audit/03-bounds-certificate.md`
4. accepted-state compatibility: `9342242db98a0f8b383a9df49688fab3e37c75feb6a1c869ddc3b638ec32ea76  research/phase4/s3-i2-core-audit/04-state-compatibility.md`
5. direct result/certificate invariants: `0ddf5386c5da2663abe1af49efa34c71945a44f74867d267984be19036a66e09  research/phase4/s3-i2-core-audit/05-result-invariants-codex.md`
6. release/full regression/integration isolation: `4cae8697e6b00f3b6a199e0c41be93c797087238853f8e65ed637ca6cab62f1d  research/phase4/s3-i2-core-audit/06-release.md`

The original exact-six Bryant wave supplied the six distinct non-author scopes. Invalid/missing artifacts received at most one Bryant retry. C5's retry executed valid evidence but exhausted transport before persistence, so a fresh Codex non-author replacement produced the accepted sixth report. No auditor edited candidate source or tests.

## Decision

The typed S3-I2 core facade is accepted. Integration ownership may now extend only the strict v4 API, v3 capability truth, package exports, and canonical examples. The frozen solve/core state must remain unchanged.
