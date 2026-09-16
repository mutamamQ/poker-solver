# S3-I2 integration parent full regression

status=FULL_GREEN
verified_at=2026-09-16T10:08:40Z
accepted_base_head=68e0ad2e9983928e666c3aabfa5d32161f7baca8
phase3_baseline_tag=feba8222a0b614b0c64eca59402403ce733195ea

Command:
`PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider`

Result:
`817 passed in 237.20s (0:03:57)`
exit_code=0

Preceding focused parent gates:
- integration API/examples/exports: `56 passed`
- typed solve: `52 passed`
- adjacent API/v3/CLI controls: `95 passed`
- compileall without bytecode writes: PASS
- `git diff --check`: PASS

Frozen identities at verification:
- `src/poker_solver/api_v4.py`: `70d378d6a52ae544615a5aa4dda6bd9e987f8161f08119914a0762ed0727a1a3`
- `src/poker_solver/api_v3.py`: `01ad9f614a01a4b623a36d42b611d75050fbe3ebdead650fbd4272852e593a4a`
- `src/poker_solver/__init__.py`: `0c2a03813d375d362c582b3df0744d80802c5f008e2b42825f4afeaed5326159`
- `src/poker_solver/nplayer_preflop.py`: `5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae`
- `src/poker_solver/cli.py`: `3f4df8452f427757d11c7bcee8b44b783efe65290b2f18050cdeba67d94ada13`

The full suite contains the accepted S1/S2/S3-I1/core tests plus all S3-I2 integration and example tests; no exclusions were used.
