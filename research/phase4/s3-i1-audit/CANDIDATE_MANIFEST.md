# S3-I1 GREEN candidate manifest

Frozen: 2026-09-16T05:28:29Z
Accepted design authority: `ARCHITECTURE_PHASE4_S3.md`
Design SHA-256: `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`
Accepted design commit/base HEAD: `65d411793d1d7767d86500d0adffe9f40b379108`
Preserved baseline: `phase3-398-green` -> `feba8222a0b614b0c64eca59402403ce733195ea`

## Candidate hashes

```text
0e55fbce5f6934c8e2e63ee28ce9d01d9268792165d9318bc8c9ed03b5f73422  src/poker_solver/nplayer_preflop.py
5a214b900a7ad1b61aa67cd294d7000e3eef0023f82bb834d1e94035f815a867  tests/test_nplayer_preflop_config.py
d61a86d39f864d494f19a91698478c4af39b76d6ad0372321f18d69706349f69  tests/test_nplayer_preflop_betting.py
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
282112f2b88e57b1b8b25bbdd69d0f6fb90df714e92ccff80945f9724375e69d  tests/test_nplayer_preflop_information.py
```

## Parent evidence at freeze

- Each final test independently re-proved exit 2 with direct `ModuleNotFoundError` while production was temporarily absent; production was then restored.
- `python3 -m py_compile` passed for production and all four suites.
- strict sizing-expression AST validation passed.
- final focused command `uv run pytest -q tests/test_nplayer_preflop_*.py`: `26 passed`.
- focused legacy/control command before final immutable-map hardening: `149 passed`; the current full regression is the authoritative final control.
- parent N=2..9 call/check showdown and fold path oracle: PASS with stack/pot/street/pending/zero-sum invariants.
- frozen sizing expressions are defensively copied, immutable, and hashable.
- current-candidate full regression was started as background process `proc_228358d80dd7`; acceptance remains blocked until its exact final result is recorded.

Auditors are read-only over production/tests/this manifest. A PASS requires independent checks against the exact hashes above, not trust in this narrative.
