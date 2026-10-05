# I203 additive Phase-4 CLI RED — parent recovery

Status: RED_READY.

The original correction removed some false positives but retained an invalid v3 control and incorrect v4 response paths. After ownership cleared, the parent replaced `tests/test_phase4_s1_cli.py` with a concise production-facing contract.

Permanent test contract

- Registers `phase4 REQUEST [--json]` without changing the `phase3` command.
- Accepts JSON from a file or stdin (`-`).
- Dispatches a complete strict-v4 request and emits compact JSON.
- Requires correct top-level v4 identity/provenance fields.
- Requires byte-identical vanilla-CFR and same-seed MCCFR output.
- Requires malformed JSON, v4 validation errors, and missing files to return 2 with an `error:` stderr prefix.
- Executes `examples/phase4_s1_flop.json` through the real CLI.
- Uses the existing valid v3 `capabilities` operation as a GREEN compatibility control.

RED execution

`uv run pytest tests/test_phase4_s1_cli.py -q`

Result at 2026-09-15T19:53:50Z: `9 failed, 1 passed in 3.95s`, expected nonzero exit. Every failure is caused by argparse rejecting the absent `phase4` subcommand; the v3 compatibility control passes. No production file was changed before this RED.
