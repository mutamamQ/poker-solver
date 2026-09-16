# Repaired S3 design audit recovery reconciliation

Candidate SHA-256: `f0777689eac5df76ab7630dd3725e40f7409e4369ba9de312ac8992a4a4bb83f`.

The first repaired audit batch ended with one valid report and five scopes requiring recovery:

- A3R1: accepted design-audit evidence. It read the correct repaired manifest and `ARCHITECTURE_PHASE4_S3.md`, verified the correct raw hash, wrote its report, and returned PASS.
- A3R2: rejected as evidence. The transcript read repository-root `ARCHITECTURE.md`, not `ARCHITECTURE_PHASE4_S3.md`, and never verified the candidate hash or wrote its assigned files.
- A3R3: failed with `HTTP 502: Model returned neither an answer nor a tool call` after partial reads. Its premature heartbeat was removed.
- A3R4: rejected as evidence. It read repository-root `ARCHITECTURE.md`, did not verify the candidate hash, wrote no report/heartbeat, and supplied internally invalid arithmetic examples.
- A3R5: rejected as evidence. It read repository-root `ARCHITECTURE.md`, audited existing S2 tests instead of S3 authority, did not verify the candidate hash, and wrote no report/heartbeat.
- A3R6: rejected as evidence. It selected the superseded round-1 manifest despite an explicit repaired-manifest assignment, so its only blocker was fabricated by comparing against the wrong hash. Its report is retained as `06-cross-release-rejected-wrong-manifest.md` and is not acceptance evidence.

Fresh, different bounded recoveries must read literal absolute paths. They must specifically test the interaction between antes, total contribution, current-street refunds and side pots; whether equal-size or non-increasing straddles are coherent; and whether the two TDD batches have feasible, nonoverlapping ownership.
