# R05 strict v4 envelope RED recovery

Status: RED_READY

Ownership

- Test: `tests/test_api_v4.py`
- Production remains owned by R06: `src/poker_solver/api_v4.py`
- Original worker: `sa-4-86c68a70` in `deleg_cf0f8a8d`
- Retry: `sa-0-a3ccc8dd` in `deleg_96c745dc`

Chronology and evidence

The original R05 worker added the single production-importing test `test_float_envelope_version_rejected` and ran it before any paired production edit. Its canonical transcript records the intended RED at 2026-09-15T18:24:28Z. The worker then ended with HTTP 502 before writing this report or the required marker. Its retry inspected the preserved test but likewise ended at the provider boundary without editing it.

Parent recovery reran the exact test against unchanged production:

    uv run pytest tests/test_api_v4.py::test_float_envelope_version_rejected -q

Receipt at 2026-09-15T18:29:19Z:

    FAILED tests/test_api_v4.py::test_float_envelope_version_rejected
    Failed: DID NOT RAISE ValueError
    1 failed in 0.15s
    exit code 1

The test keeps the canonical flat payload valid and changes only top-level `version` from integer `4` to float `4.0`. Current production compares equality without first requiring an actual integer, and Python treats `4.0 == 4` as true. The failure is therefore the intended behavioral RED, not a fixture or environment defect.

No production file was changed by R05 or parent recovery. R06 may now apply the minimum integer-type guard and run the focused GREEN gate.
