# S3-I1 repair RED receipt

status=RED_VERIFIED
completed_at=2026-09-16T06:04:28Z
base_architecture_sha256=a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6
pre_repair_nplayer_preflop_sha256=0e55fbce5f6934c8e2e63ee28ce9d01d9268792165d9318bc8c9ed03b5f73422
pre_repair_sizing_sha256=57cbb6e4027b82282c6ddd888ee06c8ce79d6eece0da053b5ed0fa8c841742e8

Command:

`PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_information.py tests/test_sizing.py`

Result: expected exit 1; 15 failed, 57 passed in 0.34s.

The 15 failures directly reproduced the six C3I1-5 runtime blockers before production repair:

- unsupported forced-post kinds: 3 failures;
- bool/float odd-chip seat aliases: 2 failures;
- mutable sizing-expression backing/hash contract: 1 failure;
- Decimal NaN/Infinity sizing rejection and exception normalization: 3 failures across S3 and shared sizing validation;
- invalid direct chance roots: 5 failures;
- accepted structural depth beyond the recursive solver limit: 1 failure.

The added positive double/Mississippi, exact all-in post option, invalid ante/non-increasing straddle, exact chance mass, limp, SB-completion, completed 3/4/5-bet, and N=6/9 information fixtures were already green and are coverage-only additions required by the accepted architecture.

Frozen test hashes at RED:

- tests/test_nplayer_preflop_config.py d1beedead9299191ba5f27c51460c43c005233db5e278db49810c73538dee6c7
- tests/test_nplayer_preflop_betting.py 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd
- tests/test_nplayer_preflop_information.py fc084fbfcd104e5ab0154d270fb25a96ca6899212440d4da226fca04669e69b3
- tests/test_nplayer_preflop_settlement.py e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3
- tests/test_sizing.py 2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1

## Final-test replay

After one coverage-only strict-config matrix was added, the final test bytes were replayed at 2026-09-16T06:12Z against an isolated copy of the exact pre-repair production hashes above. The repository production files were not changed during replay.

Command:

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/s3-i1-red-replay/src uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_information.py tests/test_sizing.py`

Result after the final HU projection coverage addition: expected exit 1; 15 failed, 59 passed in 0.44s. The same six repair behaviors failed; all added coverage-only cases passed. Exact replay identity:

- pre-repair nplayer_preflop.py 0e55fbce5f6934c8e2e63ee28ce9d01d9268792165d9318bc8c9ed03b5f73422
- pre-repair sizing.py 57cbb6e4027b82282c6ddd888ee06c8ce79d6eece0da053b5ed0fa8c841742e8
- final tests/test_nplayer_preflop_config.py bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268
- final tests/test_nplayer_preflop_betting.py 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd
- final tests/test_nplayer_preflop_information.py 0d800d2f8fe797f29d8a347e1ab216bbc079fee0ede792ab253db23097819445
- final tests/test_sizing.py 2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1
