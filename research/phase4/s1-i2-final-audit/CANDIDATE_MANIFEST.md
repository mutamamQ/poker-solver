# S1-I2 frozen candidate manifest

Frozen UTC: 2026-09-15T20:19:33Z
Base accepted HEAD: d90252315fa9c9ca9552ec303b51b3387694bb4f
Preserved baseline tag: phase3-398-green

Do not modify the following files while the fresh non-author audit owns this candidate.

3f4df8452f427757d11c7bcee8b44b783efe65290b2f18050cdeba67d94ada13  src/poker_solver/cli.py
dbcabc7b11f3b16396248acefe2f637e5407f983c5abf0c3af2835deed8432cb  src/poker_solver/__init__.py
178ba796db893529204c956876f2107575e1aeb7f15ac4346fe16bd0d0be43b4  src/poker_solver/api_v3.py
00e94199e800fb387500a0d552926241e3591de599b856fc2a82f2ed33b270de  tests/test_allstreet_oracle.py
38ac1484a0e1c4a53bf2fff865862fd658b19417d6cb71a96f947e590d7a51aa  tests/test_phase4_s1_example.py
1b06ae9ec10f4b8c96ee9641e19cb5b40b9891ac7b4333f4f6278eb50ccb34cf  tests/test_phase4_s1_cli.py
910ea48b2fc8242cfc05f3bd45a4576de28c96195a1045f7b6e073ad7a13f67b  tests/test_phase4_s1_exports.py
9e3ca2697e53d83351522fedf405c10f5233912ee0743df04f5ad674f7d6eea8  examples/phase4_s1_flop.json

Parent execution evidence before freeze

- oracle: 5 passed in 6.41s (later rerun 5 passed in 38.94s under load)
- example plus CLI: 14 passed in 4.28s
- S1 integration focus: 178 passed in 16.32s
- full repository: 556 passed in 324.87s

Audit acceptance boundary

S1-I2 is acceptable only if fresh non-author review independently validates both structural and strategic oracle premises/bounds, direct example behavior, CLI file/stdin/error/determinism behavior, exact five package exports, v3 capability deep-copy compatibility, unchanged frozen hashes, full baseline, and preservation of `phase3-398-green`.
