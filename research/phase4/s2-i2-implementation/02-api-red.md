# I202 strict v4 API RED — parent recovery

Original I202 produced a false completion summary, no report/heartbeat, and a suite whose supposed RED cases mostly expected the current unsupported-operation error. After ownership ended, parent replaced it with a permanent strict direct-v4 contract.

Test: `tests/test_api_v4_nplayer.py`
RED-gate SHA-256: `14f36bc6a2ebd15c3eed1babf640c8db07f55ac24abeeddadf05296a19c4a7d3`
Final candidate SHA-256: `e91bebe61b60115b18bff02c7d6101e99774ca8472fe42d75cdd9f4ad554aa2c`
Verified UTC: `2026-09-15T23:35:39Z`
Legacy control: `uv run pytest tests/test_api_v4_nplayer.py::test_legacy_v4_allstreet_control_is_green -q` → `1 passed in 0.06s`.
RED command: `uv run pytest tests/test_api_v4_nplayer.py -q` → `3 failed, 26 passed in 0.10s` (exit 1).

The positive operation/response/certificate cases fail because `solve-nplayer-postflop` is absent; the duplicate-showdown case also requires the future parser to reject at the correct layer. Permanent green validation cases enforce exact fields, N-array lengths, bool rejection, finite positive weights, deterministic `showdowns` list conversion and duplicate rejection, rake-policy shape, seedless vanilla-only behavior, positive bounds, response detachment, normalized strategies, N values, exact optional certificate, and truthful non-convergence metadata. No placeholders or skips.

During GREEN verification the positive certificate fixture's all-active tree correctly exceeded its deliberately small cap. Parent narrowed only that positive fixture to two live seats and raised its explicit cap, preserving the pre-implementation missing-operation RED while making the intended exact diagnostic bounded. No production expectation or malformed-input assertion was weakened.

RED_READY
