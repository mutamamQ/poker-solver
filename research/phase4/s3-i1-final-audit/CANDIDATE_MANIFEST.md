# S3-I1 final reconciled candidate manifest

status=FROZEN_PENDING_FULL_AND_FRESH_AUDIT
frozen_at=2026-09-16T06:46:40Z
base_directory=/home/genomix-node/poker-solver
accepted_base_head=65d411793d1d7767d86500d0adffe9f40b379108
phase3_baseline_tag=feba8222a0b614b0c64eca59402403ce733195ea
supersedes=research/phase4/s3-i1-repair-audit/CANDIDATE_MANIFEST.md

Raw SHA-256 entries, relative to `base_directory`:

- 15b378ac224460ee8064e3c54f5925d3721d4ca38e4529cf84b7e82858975a78  ARCHITECTURE_PHASE4_S3.md
- a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812  src/poker_solver/nplayer_preflop.py
- 8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240  src/poker_solver/sizing.py
- bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268  tests/test_nplayer_preflop_config.py
- 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd  tests/test_nplayer_preflop_betting.py
- e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
- 49cf12eb1bd514a4bcaad4bae896f4a143407ceff71928cdaf5e8f05395e2e84  tests/test_nplayer_preflop_information.py
- 2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1  tests/test_sizing.py
- 61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11  research/phase4/s3-i1-repair/RED_RECEIPT.md
- 36a95b38ec1b6016bc46ca80307b2c9f4119c749fceb51cd822bccaf61965164  research/phase4/s3-i1-spec-reconciliation/RECEIPT.md

Verification already completed before freeze:

- focused S3-I1 plus sizing: 81 passed in 0.26s;
- production hash unchanged;
- git diff --check clean;
- accepted base and phase3-398-green unchanged.

No candidate file may change before parent full regression and the fresh final non-author audit complete.
