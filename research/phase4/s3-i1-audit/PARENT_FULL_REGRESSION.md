# Parent current-hash full regression

Completed: 2026-09-16T05:35:59Z
Command: `uv run pytest -q`
Process: `proc_228358d80dd7`
Exit: `0`
Result: `679 passed in 369.87s (0:06:09)`

Frozen production and test hashes after completion:

```text
0e55fbce5f6934c8e2e63ee28ce9d01d9268792165d9318bc8c9ed03b5f73422  src/poker_solver/nplayer_preflop.py
5a214b900a7ad1b61aa67cd294d7000e3eef0023f82bb834d1e94035f815a867  tests/test_nplayer_preflop_config.py
d61a86d39f864d494f19a91698478c4af39b76d6ad0372321f18d69706349f69  tests/test_nplayer_preflop_betting.py
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
282112f2b88e57b1b8b25bbdd69d0f6fb90df714e92ccff80945f9724375e69d  tests/test_nplayer_preflop_information.py
```

Repository anchors:

- candidate base/HEAD: `65d411793d1d7767d86500d0adffe9f40b379108`
- preserved `phase3-398-green`: `feba8222a0b614b0c64eca59402403ce733195ea`
- `git diff --check`: PASS

This evidence does not accept S3-I1 by itself. Acceptance remains gated on six fresh non-author audit read-backs and parent verification.
