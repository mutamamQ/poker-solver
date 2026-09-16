# A302 strict v4 API audit — parent reconciliation

Fresh non-author A302 recovery read the accepted architecture, frozen manifest, API implementation and permanent suite; verified all twelve initial hashes; and executed `tests/test_api_v4_nplayer.py` with `29 passed`. The worker then executed:

- a valid non-null rake request with finite 4-player output;
- a valid two-player request with zero-sum output;
- repeated 4-player solves proving deterministic, JSON-safe output.

Its custom 9-player probe exceeded the intentionally tiny `max_nodes` bound and failed closed; canonical bounded 9-player execution is independently green. Three subsequent shell probes had quoting defects. The worker ended with a schema-class HTTP 502 before finishing its report or post-hash, so this parent reconciliation does not accept those failed probe commands as evidence.

After recovery ownership ended, parent executed 26 API probes: 19 rejection cases covering strict envelope/payload fields, bool numerics, N-length arrays, nonfinite/negative weights, duplicate/out-of-range cards, duplicate ranges/showdowns, rank lengths, algorithm/seed, positive bounds, certificate booleans, and malformed rake; plus a valid full rake policy, finite JSON-safe response, repeated-response detachment/determinism, typed-vs-serialized infoset cardinality collision check, and valid canonical 5-/9-player execution. Result: `PARENT_API_PROBES=26 rejection_checks=19 status=PASS`.

Parent also verified all twelve frozen hashes post-audit and preserved `phase3-398-green`.

Verdict: PASS. No candidate blocker found.
