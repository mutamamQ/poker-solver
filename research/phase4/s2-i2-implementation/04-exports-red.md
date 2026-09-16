# I204 exports/capability RED — parent recovery

Both the original I204 and its single provider retry ended without writing owned artifacts; the retry falsely summarized files it had not created. After ownership ended, parent recovered the permanent suite without touching production.

Test: `tests/test_phase4_s2_exports.py`
SHA-256: `8556d99f10bee1dc3c7ab69314fc8e7ef6d8b2e8d8fa75e4be64b30bd8348f14`
Verified UTC: `2026-09-15T23:22:13Z`

Compatibility control:
`uv run pytest tests/test_phase4_s1_exports.py tests/test_api_v3.py -q`
Result: `14 passed in 0.05s`.

RED command:
`uv run pytest tests/test_phase4_s2_exports.py -q`
Result: `4 failed, 2 passed in 0.06s` (exit 1).

Every failure is intended missing S2-I2 behavior: package-root N-player state exports, defining-module/result/facade solve contracts, and exact detached `nplayer-postflop` v3 capability. The two legacy compatibility controls pass. There are no skips, caught imports, placeholder assertions, syntax errors, or source-absence tests.

RED_READY
