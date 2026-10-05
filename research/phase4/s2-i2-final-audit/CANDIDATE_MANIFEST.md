# S2-I2 frozen candidate manifest

Frozen at: 2026-09-15T23:52:05Z
Base commit: `b6bd7efac58d6063b8d7aa01f3ec2f9c95540ee3`
Preserved baseline tag: `phase3-398-green` → `feba8222a0b614b0c64eca59402403ce733195ea`

Candidate files use raw SHA-256:

| SHA-256 | Path |
|---|---|
| `484b95ec85131f3d50212398dc3055dd747a03fb5a5151333a28c6130980b294` | `src/poker_solver/nplayer.py` |
| `fef16496ca6e2d48f1009d49e73e38fa2177b0e2a2404987bf5e95761b73aad5` | `src/poker_solver/nplayer_postflop.py` |
| `e70584d5ead154011a70b13572eaa55cdfee2f76c408e5f5e7866b2ae672069a` | `src/poker_solver/api_v4.py` |
| `76d167748fb96da731397646ea37176ee31dd4c8f16515e2d01b09a404c4df32` | `src/poker_solver/api_v3.py` |
| `e6bd13a97cac37aaf20ebc81c85b43680ff5502cde732077e80d51d86c975b95` | `src/poker_solver/__init__.py` |
| `d606c5fb011905b4df0c3df76874e5e5c4922b0a8a91d9d3d4adfcdf9f51fcce` | `tests/test_nplayer_postflop_solve.py` |
| `e91bebe61b60115b18bff02c7d6101e99774ca8472fe42d75cdd9f4ad554aa2c` | `tests/test_api_v4_nplayer.py` |
| `5fe5360933516bec3320d5baeb8ab73c8841e72152f68abf577e781d188d336d` | `tests/test_phase4_s2_examples.py` |
| `8556d99f10bee1dc3c7ab69314fc8e7ef6d8b2e8d8fa75e4be64b30bd8348f14` | `tests/test_phase4_s2_exports.py` |
| `a119e0b08ad53efe99180ccfa714c28455c37f8577e1140747007cbaa2f86a4a` | `examples/phase4/nplayer_4p_flop.json` |
| `8bae730f59db4f95ac4c7d91554189a81ae23f7bcad648a294b471bd291c80c5` | `examples/phase4/nplayer_5p_flop.json` |
| `81c8437a0bd3cf20ee28beddff70424e4b83ae9f6c29e28442915a0a16d25338` | `examples/phase4/nplayer_9p_flop.json` |

Pre-freeze parent evidence:
- S2-I2 focused: `51 passed in 3.39s`
- relevant legacy-focused: `96 passed in 3.03s`
- full regression: `653 passed in 229.45s`
- `git diff --check`: pass
- baseline tag identity: preserved

The twelve candidate files are read-only during audit. Reports and heartbeats are outside the candidate.
