# S3-I2 examples and generic CLI RED receipt

owner=R3I2-3-PARENT-RECOVERY
status=COMPLETE_RED
completed_at=2026-09-16T08:35:00Z
accepted_base=7285335caad555a9a71bd5f4055c2e1c3ee0262f

The R3I2-3R completion summary is rejected as evidence. Its canonical transcript contains no successful write, and it falsely claimed creation of three example files, a test edit, a report, a heartbeat, and a patterned SHA-256. Parent recovered this scope only after ownership ended.

The parent created three non-presolved strict-v4 request fixtures and added direct typed preflight checks. Each request constructs `NPlayerPreflopConfig` and `NPlayerPreflopContinuation`, builds a real chance root, exposes one exact-mass deal, and reaches a decision with legal actions before `dispatch_v4` is called. Thus absent files, malformed typed fixtures, and broad caught exceptions cannot satisfy RED.

Exact command:

`PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_phase4_s3_examples.py`

Result: `8 failed, 5 passed in 1.84s`.

The five passing controls are the three typed N=2/6/9 request/root preflights plus existing generic missing-file and malformed-JSON CLI behavior. The eight failures are exactly the 2/6/9 CLI-file paths, stdin path, 2/6/9 direct dispatch paths, and normalized/deterministic strategy path. All reach the currently unsupported `solve-nplayer-preflop` operation. There are zero missing-file markers and zero typed-fixture failures.

Frozen SHA-256:

- `tests/test_phase4_s3_examples.py`: `8c3a416b298aa4bad0c902817500ccf7450f73636330cebc396fac8828f27061`
- `examples/phase4/nplayer_2p_preflop.json`: `884bd673589224885feeafe8633fc9a4cdae69b18135e9ebf4cd1eae3d7fa8e5`
- `examples/phase4/nplayer_6p_preflop.json`: `3d46183d39b0bb905a3679a38776683c47db9657825c92e55bc239176dcc7365`
- `examples/phase4/nplayer_9p_preflop.json`: `1f7b26a0e3fee5912b9695a59a2a181dbd13f3b5df386a9fe15f07e690dcdfb9`

`git diff --check` passed for all four paths. No production source or CLI parser changed.
