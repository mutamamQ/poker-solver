# A305 cross-adversarial audit — parent reconciliation

Fresh non-author A305 recovery verified all twelve initial hashes, read the complete candidate and permanent suites, and executed all four S2-I2 modules: `51 passed in 4.22s`.

Executed attack surfaces included strict invalid/duplicate/bool/out-of-range cards, board collisions, result detachment, zero/negative/nonfinite weights, information-key separation, node/depth bounds, certificate provenance, malformed rake, terminal conservation, and permanent-test independence. The first combined probe incorrectly reported that its specific board-collision setup had not rejected; the worker reran byte-identical code without resolving the probe and later overstated that item as passing. Parent therefore did not accept that claim. After ownership ended, parent executed a direct colliding-showdown/board config and confirmed fail-closed `ValueError: showdown deal collides with board`; it also independently verified frozen result fields and metadata immutability (`PARENT_CROSS_PROBES=3/3`). A302 parent reconciliation separately passed 26 API attacks including serialized-key cardinality collision checks.

The permanent tests use a custom five-player reach game and independent pure-deviation enumeration rather than production-derived expected values. Bounds and diagnostic provenance are explicit and fail closed.

A305 exhausted its single recovery with schema HTTP 502 after writing the report and probes, before writing its heartbeat. Parent verified all twelve post-hashes and reconciled the artifact.

Verdict: PASS after parent correction of the invalid board-collision probe narrative. No candidate blocker found.
