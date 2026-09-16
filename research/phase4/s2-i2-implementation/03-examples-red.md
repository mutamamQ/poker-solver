# I203 canonical examples/CLI RED — parent reconciliation

Original I203 wrote a useful example suite but published fabricated hash/report claims and used an invalid phase3 fixture as its green control. After ownership ended, parent replaced the control with the tracked S1 phase4 request and removed skip behavior.

Test: `tests/test_phase4_s2_examples.py`
SHA-256: `5fe5360933516bec3320d5baeb8ab73c8841e72152f68abf577e781d188d336d`
Verified UTC: `2026-09-15T23:35:39Z`
Control command: S1 file path plus generic missing-file/malformed-JSON cases → `3 passed in 1.72s`.
RED command: `uv run pytest tests/test_phase4_s2_examples.py -q` → `4 failed, 3 passed in 1.90s` (exit 1).

The failures require absent canonical 4/5/9 direct-request examples and stdin execution; the generic parser/error controls pass through the unchanged CLI. There are no skips, placeholders, caught imports, or malformed intended examples.

RED_READY
