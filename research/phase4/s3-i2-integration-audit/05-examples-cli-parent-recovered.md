# S3-I2 integration audit — canonical examples and generic CLI (parent-recovered receipt)

status=PASS_PARENT_RECOVERED
blocker_count=0
auditor=A3I2-I5R
provider=BryantGPT
role=fresh non-author examples/CLI auditor
canonical_transcript=/home/genomix-node/.hermes/cache/delegation/live/deleg_88a814cd/task-2.log
parent_recovery=the completed auditor verified the scope but incorrectly treated non-existent assigned output paths as unwritable and omitted its report/heartbeat; parent created this receipt only after ownership ended

## Frozen candidate

The auditor located the exact `research/phase4/s3-i2-integration-audit/CANDIDATE_MANIFEST.md` after initially searching the wrong root path, then verified all 20 literal hashes. Parent post-verification also found 20/20 with no mismatch. The auditor did not edit any candidate path.

Canonical files and frozen SHA-256 values:

- `examples/phase4/nplayer_2p_preflop.json`: `884bd673589224885feeafe8633fc9a4cdae69b18135e9ebf4cd1eae3d7fa8e5`
- `examples/phase4/nplayer_6p_preflop.json`: `3d46183d39b0bb905a3679a38776683c47db9657825c92e55bc239176dcc7365`
- `examples/phase4/nplayer_9p_preflop.json`: `1f7b26a0e3fee5912b9695a59a2a181dbd13f3b5df386a9fe15f07e690dcdfb9`
- `src/poker_solver/cli.py`: `3f4df8452f427757d11c7bcee8b44b783efe65290b2f18050cdeba67d94ada13`

## Permanent examples suite

Command recorded in the canonical transcript:

`python -m pytest tests/test_phase4_s3_examples.py -v`

Result: exit 0; `13 passed`.

This suite executes all three committed requests through typed construction, direct `dispatch_v4`, CLI file mode, stdin mode, missing-file and malformed-JSON failures, and finite normalized strategy assertions.

## Independent CLI executions

The canonical transcript additionally records successful direct CLI file execution for 2-, 6-, and 9-player examples; stdin execution for the 2-player example; missing-file exit 2; malformed-JSON exit 2; and an unchanged CLI hash.

Deterministic serialized CLI output hashes recorded by the auditor:

- 2-player: `6b60147bd90aad6cfb64e4615f6c188d8ec67589b9ce220a0fcdc9879c843477`
- 6-player: `bf0a68c62b2a45883012058999e78a3b4f78a88e5711ee3d4f5a8cff25e875a8`
- 9-player: `fe08db9e8f424b294c672e495929e0cf87d0f82d10615ba27ffdc539271bb7bf`
- 2-player direct dispatch serialization: `8111a8ab1d895870355eb73ed8535e78b1291ed68f07319a1beac6ab4f9bf2e0`

## Disposition

PASS with zero implementation blockers. The reported inability to persist because assigned files did not already exist was an auditor tooling misunderstanding, not a candidate defect. The generic CLI needed no production change and remained manifest-identical.
