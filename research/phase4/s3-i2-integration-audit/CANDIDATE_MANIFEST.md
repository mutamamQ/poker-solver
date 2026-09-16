# S3-I2 integration frozen candidate manifest

status=FROZEN_FOR_FRESH_NON_AUTHOR_AUDIT
frozen_at=2026-09-16T10:15:55Z
base_directory=/home/genomix-node/poker-solver
accepted_core_head=68e0ad2e9983928e666c3aabfa5d32161f7baca8
phase3_baseline_tag=feba8222a0b614b0c64eca59402403ce733195ea
entry_count=20

Every auditor must verify all 20 literal rows before executing its scope. A mismatch invalidates the audit. Candidate source, tests, examples, architecture, and the six reconciled build artifacts are immutable during the wave.

```text
6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db  ARCHITECTURE_PHASE4_S3.md
5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae  src/poker_solver/nplayer_preflop.py
70d378d6a52ae544615a5aa4dda6bd9e987f8161f08119914a0762ed0727a1a3  src/poker_solver/api_v4.py
01ad9f614a01a4b623a36d42b611d75050fbe3ebdead650fbd4272852e593a4a  src/poker_solver/api_v3.py
0c2a03813d375d362c582b3df0744d80802c5f008e2b42825f4afeaed5326159  src/poker_solver/__init__.py
3f4df8452f427757d11c7bcee8b44b783efe65290b2f18050cdeba67d94ada13  src/poker_solver/cli.py
45291a2e7537883acfcf35a3c700e50fe03225c4a00db3a75372ca243326d51c  tests/test_nplayer_preflop_solve.py
38b36491172a3152157ff369f680ba0a5bab25c5a551db3552ed7074f52ff50d  tests/test_api_v4_nplayer_preflop.py
8c3a416b298aa4bad0c902817500ccf7450f73636330cebc396fac8828f27061  tests/test_phase4_s3_examples.py
40df575dd72fd5b39a9bbd7c5f3b1358a2a344f92be0d5b587bdb1b4bc232c60  tests/test_phase4_s3_exports.py
884bd673589224885feeafe8633fc9a4cdae69b18135e9ebf4cd1eae3d7fa8e5  examples/phase4/nplayer_2p_preflop.json
3d46183d39b0bb905a3679a38776683c47db9657825c92e55bc239176dcc7365  examples/phase4/nplayer_6p_preflop.json
1f7b26a0e3fee5912b9695a59a2a181dbd13f3b5df386a9fe15f07e690dcdfb9  examples/phase4/nplayer_9p_preflop.json
14b8dd501d1a36d2ad3aac98d360c097504a17c175058668f248e67a3e3f31ff  research/phase4/s3-i2-integration-build/01-integration-author-codex.md
c1722069adc923e054cee5773e9d337a384e7749907757e2e2563ccc5d452add  research/phase4/s3-i2-integration-build/02-parser-contract-parent.md
adf2d65d46d032820ff7f2930f6dd00ac04433262f5335f42d46891703334f5b  research/phase4/s3-i2-integration-build/03-serialization.md
680b37a0f199fbb2ac9f51f407a3c3d168217eba190d67f3fabedb8d5f555710  research/phase4/s3-i2-integration-build/04-capability-exports.md
a15a2528a2c093d1ef91b2fc91b7e73e91de2abdc1d92770d0a23c38c61aa0c8  research/phase4/s3-i2-integration-build/05-examples-cli.md
2b5b61269322cb848c61f047e8e358507aa87cf62d8266775117ca865d8c04f3  research/phase4/s3-i2-integration-build/06-tdd-release.md
114945024fbf7d2f4356c5f1195fed4770557fb25058ebd23612d75684d9c39f  research/phase4/s3-i2-integration-audit/PARENT_FULL_REGRESSION.md
```

Parent gates before freeze:
- API/examples/exports: `56 passed`
- typed solve: `52 passed`
- adjacent API/v3/CLI controls: `95 passed`
- all-collected regression: `817 passed in 237.20s (0:03:57)`
- compileall and `git diff --check`: PASS
