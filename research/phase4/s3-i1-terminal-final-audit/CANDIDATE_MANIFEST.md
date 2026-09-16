# S3-I1 terminal-ledger reconciled candidate manifest

status=FROZEN_PENDING_FULL_AND_FRESH_AUDIT
frozen_at=2026-09-16T07:29:42Z
base_directory=/home/genomix-node/poker-solver
accepted_base_head=65d411793d1d7767d86500d0adffe9f40b379108
phase3_baseline_tag=feba8222a0b614b0c64eca59402403ce733195ea
supersedes=research/phase4/s3-i1-final-audit/CANDIDATE_MANIFEST.md

Raw SHA-256 entries relative to `base_directory`:

- 6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db  ARCHITECTURE_PHASE4_S3.md
- a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812  src/poker_solver/nplayer_preflop.py
- 8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240  src/poker_solver/sizing.py
- bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268  tests/test_nplayer_preflop_config.py
- 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd  tests/test_nplayer_preflop_betting.py
- e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
- 1217cf74f1468252fbc7f941621dc57154c910003eb27fbf8947b7bc5a42e289  tests/test_nplayer_preflop_information.py
- 2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1  tests/test_sizing.py
- 61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11  research/phase4/s3-i1-repair/RED_RECEIPT.md
- 36a95b38ec1b6016bc46ca80307b2c9f4119c749fceb51cd822bccaf61965164  research/phase4/s3-i1-spec-reconciliation/RECEIPT.md
- b631cc2b933c314c081a70e6b3aaa669ae15054145301d272e1a18967d68a42a  research/phase4/s3-i1-terminal-ledger-reconciliation/RECEIPT.md

Any mismatch is an audit blocker. The base HEAD is ancestry only; candidate identity is these 11 raw hashes.

Auditors may write only their exclusive report under `research/phase4/s3-i1-terminal-final-audit/` and matching heartbeat under `research/phase4/s3-i1-terminal-final-audit/.hb/`. Candidate paths, manifest, STATE.txt, PROGRESS.md, git metadata, and commits are read-only throughout the audit.
