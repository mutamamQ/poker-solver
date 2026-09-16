# S3-I1 final acceptance

status=ACCEPTED
accepted_at=2026-09-16T07:58:01Z
accepted_base_head=65d411793d1d7767d86500d0adffe9f40b379108
phase3-398-green=feba8222a0b614b0c64eca59402403ce733195ea
candidate_manifest=research/phase4/s3-i1-terminal-final-audit/CANDIDATE_MANIFEST.md
manifest_rows=11
manifest_verified=11/11
production_sha256=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812
architecture_sha256=6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db
sizing_sha256=8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240
focused_result=81 passed
parent_full_result=709 passed in 429.62s
independent_full_result=709 passed in 387.47s
blocker_count=0

## Accepted final non-author slots

1. CTA3A1 architecture/HU, openai-codex, COMPLETE_PASS.
   - report_sha256=8dcd03637933d858c077d9a510a4c94e617006a04e7e8dc8d368a23b316678f4
   - 8 information tests, both named HU boundaries, 64 aligned decisions, 120 terminals, and 8,192 information-partition comparisons.
2. CTA3A2 config/sizing, openai-codex, COMPLETE_PASS.
   - report_sha256=07425984b80669748848f42f97a839f5a491958976ebd7439d50cb6e4b4b69d1
   - 56 focused tests and 197 independent strict/positive/boundary/Decimal checks.
3. CTA3A3 state/posts/bounds, openai-codex, COMPLETE_PASS.
   - report_sha256=f2e01cd4f105931758c290c01b7e7fa10d3ad3dac7764477626b03dba9fae91b
   - 31 config tests, exact state/post/chance probes, HU/N=9 traversal and CFR probes, exact minus-one bound rejection.
4. CTA3A4 betting, openai-codex, COMPLETE_PASS.
   - report_sha256=42160be33648d8e5526436e36ea45e9a3a596c7d540e4c30ac1da3ff5929569a
   - 11 betting tests, 352 decision checks, 352 transfer checks, and 54 terminal closures.
5. CTA3A5 settlement/information, openai-codex, COMPLETE_PASS.
   - report_sha256=17b4e6f2ce8654e5979bab984c15ba8fd2e1a6132aff40549b9b753ccc149ac5
   - 14 tests, independent settlement/noninterference oracles, both HU terminal boundaries, and 20,150 tiny-tree leaves.
6. TA3A6R release/TDD, BryantGPT non-author, COMPLETE_PASS.
   - parent-normalized-report_sha256=1b9217676ee3c8685a045fc6578e5fb1e15256241db36c0a23c485aa0391cbc9
   - 81 focused tests, independent 709-test full regression, compileall, diff check, baseline tag and TDD chronology.

All six reports and six final heartbeats were read and hashed by the parent. Failed/rejected Bryant attempts supplied no acceptance evidence. The final exact-six wave used bounded one-retry provider recovery followed by explicit alternate-provider fallback; no frozen candidate path was edited during ownership.

## Parent gates

- Permanent fold regression freezes decision-state raw-ledger alignment and terminal canonical refund projection for equal-stack `RAISE 6 -> FOLD`.
- Permanent unequal-stack regression freezes the invalid legacy chipless-responder suffix outside the compatibility domain and the N-player engine's correct closure/refund.
- Candidate manifest remained 11/11 through parent and independent full regressions and all accepted audits.
- `git diff --check` and `python3 -m compileall -q src/poker_solver` passed.
- `phase3-398-green` remains exactly `feba8222a0b614b0c64eca59402403ce733195ea`.
- S3-I1 is accepted for commit; S3-I2 remains required before S3 is complete.
