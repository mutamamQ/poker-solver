# Parent full regression — S3-I1 terminal-ledger reconciled candidate

status=COMPLETE_PASS
completed_recorded_at=2026-09-16T07:38:45Z
process=proc_82f0f612f412
command=PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider
exit_code=0
result=709 passed in 429.62s (0:07:09)

Post-run verification:

- authoritative manifest: `research/phase4/s3-i1-terminal-final-audit/CANDIDATE_MANIFEST.md`;
- raw manifest entries: `11/11` match;
- mismatches: none;
- accepted base HEAD: `65d411793d1d7767d86500d0adffe9f40b379108`;
- `phase3-398-green`: `feba8222a0b614b0c64eca59402403ce733195ea`;
- `git diff --check`: PASS.

This receipt certifies only the frozen 11-file candidate. Audit reports and heartbeats are outside the manifest and do not alter candidate identity.
