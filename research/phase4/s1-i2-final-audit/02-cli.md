# A202 CLI and legacy-compatibility audit — parent-normalized

Verdict: PASS.

The fresh non-author A202 reviewer executed the frozen candidate and wrote `CLI_AUDIT_REPORT.md`; this normalized report preserves only verified claims.

Evidence

- `tests/test_phase4_s1_cli.py`: 10/10 passed in 3.23s, then again in 8.29s.
- `tests/test_phase4_s1_example.py`: 4/4 passed in 9.58s.
- `tests/test_phase4_s1_exports.py`: 6/6 passed.
- Direct `python -m poker_solver.cli phase4 examples/phase4_s1_flop.json --json` succeeded with strict v4 identity, finite zero-sum values, bounded metadata and truthful provenance.
- Direct stdin execution through `phase4 - --json` succeeded.
- The permanent tests require byte-identical vanilla-CFR and same-seed external-sampling-MCCFR output.
- Malformed JSON, invalid v4 payload and missing file paths return code 2 with `error:` stderr.
- Existing `phase3` capability dispatch remains operational.

Compactness is defined structurally: stdout equals sorted `json.dumps(..., separators=(",", ":"), allow_nan=False)` plus newline. Spaces inside JSON string values are permitted and do not violate compact encoding.

All eight frozen hashes remained unchanged. No candidate defect was found.
