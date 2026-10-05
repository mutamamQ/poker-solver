# S3-I2 integration final acceptance

status=ACCEPTED
accepted_at=2026-09-16T10:36:06Z
accepted_core_head=68e0ad2e9983928e666c3aabfa5d32161f7baca8
phase3_baseline_tag=feba8222a0b614b0c64eca59402403ce733195ea
candidate_manifest=research/phase4/s3-i2-integration-audit/CANDIDATE_MANIFEST.md
candidate_manifest_rows=20
candidate_manifest_result=20/20_PASS

## Candidate production

- `src/poker_solver/api_v4.py`: `70d378d6a52ae544615a5aa4dda6bd9e987f8161f08119914a0762ed0727a1a3`
- `src/poker_solver/api_v3.py`: `01ad9f614a01a4b623a36d42b611d75050fbe3ebdead650fbd4272852e593a4a`
- `src/poker_solver/__init__.py`: `0c2a03813d375d362c582b3df0744d80802c5f008e2b42825f4afeaed5326159`
- Committed typed core `src/poker_solver/nplayer_preflop.py`: `5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae`
- Generic CLI remained unchanged: `3f4df8452f427757d11c7bcee8b44b783efe65290b2f18050cdeba67d94ada13`

## Fresh non-author audit slots

All six slots are fresh relative to the implementation authors. Every final report is backed by its canonical transcript or fresh alternate-provider process, an exact report hash in a heartbeat, and parent post-verification of the literal frozen manifest.

1. Strict parser and fail-closed malformed requests
   - auditor: `A3I2-I1R` (BryantGPT retry)
   - report: `01-strict-parser-parent-recovered.md`
   - report SHA-256: `c882cd73652197b3ea5d873268d51d09b7befcf1059fdcc0296285c86a99d9ca`
   - evidence: 30 permanent API tests; 45 independent malformed-request probes; probe SHA-256 `85f7b33b958f0de6143545f309829855b81ffa1a85557a5030ebb083f656036e`
   - disposition: PASS, zero blockers

2. Typed solver/API numerical and certificate correctness
   - auditor: `C3I2-CODEX-I2` (fresh alternate-provider replacement after Bryant retry exhaustion)
   - report: `02-solver-api-codex.md`
   - report SHA-256: `a02620dc02ca60f0e36388ed29b1c99afede4c7ee8029c41ad37afb8a3f58edc`
   - evidence: 52 solve and 56 integration tests; independent 2/6/9 public-dispatch value and unilateral-deviation oracles; six-player inclusive certificate cap 8 passes and cap 7 fails closed
   - disposition: PASS, zero blockers

3. Deterministic finite detached serialization
   - auditor: `C3I2-CODEX-I3` (fresh alternate-provider replacement after Bryant retry exhaustion)
   - report: `03-serialization-codex.md`
   - report SHA-256: `92772534e7bc22398328b6bfa48497bd455903dda9b7724b0b905b8f9942a2c8`
   - evidence: 87 existing tests; six independent 2/6/9 certificate-off/on exact-envelope, strict-JSON, domain, value, certificate and mutation-isolation cases
   - disposition: PASS, zero blockers

4. Exports, capability truth and backward compatibility
   - auditor: `A3I2-I4R` (BryantGPT correction retry)
   - report: `04-exports-capability.md`
   - report SHA-256: `1eedbbe2452289c17913056f2cf5bd9f8cb37ccc57cfe6ea4b9750322748fa2b`
   - evidence: nine identity exports; exact detached capability; S1/S2 preservation; 87 focused and adjacent tests
   - disposition: PASS, zero blockers

5. Canonical examples and unchanged generic CLI
   - auditor: `A3I2-I5R` (BryantGPT artifact retry)
   - report: `05-examples-cli-parent-recovered.md`
   - report SHA-256: `ded7951b1b0479e396c889610f568a19002d572c1a5617711556da5d60ce7b00`
   - evidence: 13 example tests; 2/6/9 file execution; stdin and error paths; deterministic serialized hashes; unchanged CLI hash
   - disposition: PASS, zero implementation blockers

6. Release gates and independent complete regression
   - auditor: `A3I2-I6R` (BryantGPT correction retry)
   - report: `06-release.md`
   - report SHA-256: `7e16ddf8e2ebf283786783fef98f6d3b51f3fe35f37f2e7ba8e32f7252d04954`
   - evidence: pre/post manifest 20/20; 108 focused tests; 817 tests collected; `817 passed in 387.31s (0:06:27)` with no exclusions; compileall and `git diff --check` PASS; baseline tag exact
   - disposition: PASS, zero blockers

## Parent verification

- Original parent complete regression receipt: `PARENT_FULL_REGRESSION.md`, `817 passed in 237.20s (0:03:57)`.
- Independent release complete regression: `817 passed in 387.31s (0:06:27)` with no exclusions.
- Final parent focused rerun after all auditors ended: `108 passed in 3.11s`.
- Final parent manifest check: 20/20, no mismatch.
- Final parent report/heartbeat authentication: 6/6 exact report SHA-256 matches and PASS states.
- Final parent `compileall`: PASS.
- Final parent `git diff --check`: PASS.
- Accepted base HEAD before integration commit: `68e0ad2e9983928e666c3aabfa5d32161f7baca8`.
- Preserved baseline tag: `phase3-398-green` -> `feba8222a0b614b0c64eca59402403ce733195ea`.
- Live child ownership at acceptance: none.

## Decision

ACCEPT the frozen S3-I2 integration candidate. The integration wave may be committed without further production changes. Parent-recovered receipts explicitly distinguish missing child artifacts and invalid tooling blockers from implementation defects; they do not fabricate child writes or test runs.
