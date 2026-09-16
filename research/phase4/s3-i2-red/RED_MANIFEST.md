# S3-I2 authenticated RED manifest

status=RED_ACCEPTED
accepted_base=7285335caad555a9a71bd5f4055c2e1c3ee0262f
baseline_tag=phase3-398-green
baseline_target=feba8222a0b614b0c64eca59402403ce733195ea
frozen_at=2026-09-16T08:36:00Z

Paths are relative to `/home/genomix-node/poker-solver`; digests are raw SHA-256.

```text
45291a2e7537883acfcf35a3c700e50fe03225c4a00db3a75372ca243326d51c  tests/test_nplayer_preflop_solve.py
38b36491172a3152157ff369f680ba0a5bab25c5a551db3552ed7074f52ff50d  tests/test_api_v4_nplayer_preflop.py
8c3a416b298aa4bad0c902817500ccf7450f73636330cebc396fac8828f27061  tests/test_phase4_s3_examples.py
40df575dd72fd5b39a9bbd7c5f3b1358a2a344f92be0d5b587bdb1b4bc232c60  tests/test_phase4_s3_exports.py
884bd673589224885feeafe8633fc9a4cdae69b18135e9ebf4cd1eae3d7fa8e5  examples/phase4/nplayer_2p_preflop.json
3d46183d39b0bb905a3679a38776683c47db9657825c92e55bc239176dcc7365  examples/phase4/nplayer_6p_preflop.json
1f7b26a0e3fee5912b9695a59a2a181dbd13f3b5df386a9fe15f07e690dcdfb9  examples/phase4/nplayer_9p_preflop.json
64558006d6aa933b726a431cda429bba0a5207b1e50ab44080406f434f64332e  research/phase4/s3-i2-red/01-solve.md
465cbd6eee22556acae5e63cad2958cbbe45bb832b8d7ba1a2467e5fa52132d0  research/phase4/s3-i2-red/02-api-v4.md
a842ab07513aadffe972397874676a751f075a6fa67fc391cf24680fb00d5726  research/phase4/s3-i2-red/03-examples-cli.md
09e9e8e8a4463e1efc49e6e49bce31ebe55c8d4fcaea3ddcf3d77cc4f0a91adc  research/phase4/s3-i2-red/04-exports.md
ee725d3ebbc85b7203e0f3668aa197e906e1374e5b584b7d5328d73559b80a09  research/phase4/s3-i2-red/05-red-authenticity-plan.md
0fcf46d1305ecf883dad87e86a965e9bb32fe7bd8a0f003447bc5cce827d8898  research/phase4/s3-i2-red/06-oracles-boundaries.md
```

Exact combined command:

`PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_solve.py tests/test_api_v4_nplayer_preflop.py tests/test_phase4_s3_examples.py tests/test_phase4_s3_exports.py`

Authenticated result: `89 failed, 19 passed in 1.96s`, exit 1, zero collection errors, zero invalid-fixture markers.

Failure split:

- solve: 41, exactly missing typed result/facade symbols;
- API: 29, missing strict `solve-nplayer-preflop` operation/validation behavior;
- examples: 8, all valid typed fixtures reaching the missing operation through direct or generic CLI paths;
- exports/capability truth: 11, missing additive exports/capability metadata.

Passing controls prove typed N=2/6/9 fixture construction/traversal, independent six-player deviation arithmetic, legacy envelope validation, generic CLI errors, and S1/S2 export/capability preservation.

No production source changed during RED. Core GREEN may extend only `src/poker_solver/nplayer_preflop.py`. Integration remains gated until parent accepts core GREEN and its fresh non-author audit.
