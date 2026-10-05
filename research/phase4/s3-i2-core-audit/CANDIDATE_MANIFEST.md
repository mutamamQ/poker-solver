# S3-I2 core frozen candidate manifest

status=FROZEN_PENDING_FULL_AND_FRESH_AUDIT
frozen_at=2026-09-16T08:52:39Z
base_directory=/home/genomix-node/poker-solver
accepted_base_head=7285335caad555a9a71bd5f4055c2e1c3ee0262f
phase3_baseline_tag=feba8222a0b614b0c64eca59402403ce733195ea
full_regression_process=proc_4aeb141c3d78

Reviewers must verify these literal raw SHA-256 identities from `base_directory` before using any evidence:

```text
6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db  ARCHITECTURE_PHASE4_S3.md
484b95ec85131f3d50212398dc3055dd747a03fb5a5151333a28c6130980b294  src/poker_solver/nplayer.py
5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae  src/poker_solver/nplayer_preflop.py
45291a2e7537883acfcf35a3c700e50fe03225c4a00db3a75372ca243326d51c  tests/test_nplayer_preflop_solve.py
bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268  tests/test_nplayer_preflop_config.py
9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd  tests/test_nplayer_preflop_betting.py
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
1217cf74f1468252fbc7f941621dc57154c910003eb27fbf8947b7bc5a42e289  tests/test_nplayer_preflop_information.py
1826b203fe264acd159e5efb35d07a5122ddb12fb75c405078833733a7c3bcec  research/phase4/s3-i2-core-build/01-core-author.md
a51dfcbc692fc434bbe5f485d526f83e411de6e837a4111d06a6c055822e7065  research/phase4/s3-i2-core-build/PARENT_CORE_GATE.md
```

Parent focused evidence before freeze:

- solve facade: 52 passed;
- exact core gate: 108 passed;
- compileall and diff check: passed;
- post-core combined RED: only API 29, examples 8, exports 11 remain, proving integration ownership stays gated.

No listed byte may change during the audit. Any change invalidates all audit verdicts and requires a new manifest and fresh wave.
