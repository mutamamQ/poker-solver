# S3-I2 exports and capability-truth RED receipt

owner=R3I2-4-PARENT-RECOVERY
status=COMPLETE_RED
completed_at=2026-09-16T08:16:54Z
accepted_base=7285335caad555a9a71bd5f4055c2e1c3ee0262f
test_path=tests/test_phase4_s3_exports.py
test_sha256=40df575dd72fd5b39a9bbd7c5f3b1358a2a344f92be0d5b587bdb1b4bc232c60

The original R3I2-4 canonical transcript proves it read the correct architecture and analogous tests, wrote the permanent 13-test suite, and ran it before its transport ended with HTTP 502. The delegation status incorrectly summarized that no tools executed. Its sole retry R3I2-4R found the correct source files but then falsely claimed the repository had no tests and produced no artifact. Parent rejected the retry blocker after reading both transcripts and the actual workspace.

Authenticated command:

`PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_phase4_s3_exports.py`

Result: `11 failed, 2 passed in 0.17s`, exit 1.

The 11 failures are exact expected S3-I2 RED behavior:

- seven existing S3 typed state/deal/root symbols are not exported at package root;
- future `NPlayerPreflopSolveResult` and `solve_nplayer_preflop` do not exist;
- `nplayer-preflop` capability truth is absent, including its detached-response test.

The two passes preserve existing S1/S2 package exports and capability entries. All nine public S3 names from architecture section 2.1 and all six exact capability fields are asserted. The suite imports production normally, invokes `dispatch_v3`, and contains no caught absence, skip, xfail, mock, or placeholder. `git diff --check` passes for the test path. Production remains unmodified.
