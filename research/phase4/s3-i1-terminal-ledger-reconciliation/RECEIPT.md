# S3-I1 terminal-ledger projection reconciliation

status=RESOLVED_PENDING_FRESH_AUDIT
completed_at=2026-09-16T07:28:22Z
accepted_base_head=65d411793d1d7767d86500d0adffe9f40b379108
phase3-398-green=feba8222a0b614b0c64eca59402403ce733195ea
old_architecture_sha256=15b378ac224460ee8064e3c54f5925d3721d4ca38e4529cf84b7e82858975a78
new_architecture_sha256=6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db
old_information_test_sha256=49cf12eb1bd514a4bcaad4bae896f4a143407ceff71928cdaf5e8f05395e2e84
new_information_test_sha256=1217cf74f1468252fbc7f941621dc57154c910003eb27fbf8947b7bc5a42e289
production_sha256=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812

## Accepted blocker

Fresh non-author auditor FC3I1-5 reproduced a specification conflict on the frozen equal-stack HU fixture `(20,20)`, `RAISE 6 -> FOLD`:

- both engines terminate with exact utilities `(2,-2)`;
- legacy preserves raw terminal `pot=8`, commitments/contributions `(6,2)`, remaining `(14,18)`;
- the N-player engine obeys architecture section 8 and stores canonical refunded `pot=4`, commitments/contributions `(2,2)`, remaining `(18,18)`.

FC3I1-5 report SHA-256: `ca41436ed4e390535d947ba02c1605db115740480232e4004ba775a08fbe423d`.
FC3I1-5 heartbeat SHA-256: `fbedc22b4b0cfc1de98685fea01462e6ac97c93f4c0b9e6721566d65db6eef53`.

## Resolution

The architecture now defines the N=2 projection by state phase:

1. aligned decision states compare raw ledgers, actors, ordered actions, projected histories, and information partitions;
2. aligned terminal states compare exact utilities and independently canonicalized section-8 refunded ledgers;
3. legacy raw terminal storage is not the terminal accounting oracle;
4. legacy production remains unchanged;
5. correct N-player refund behavior remains unchanged.

The permanent information regression now freezes the equal-stack fold divergence, the exact four-chip legacy normalization, canonical N-player ledger, and exact utilities. The earlier unequal-stack chipless-responder regression remains in place.

This is a specification/characterization repair. The added assertions passed immediately against invariant-correct production and are not claimed as behavioral RED. The original S3-I1 production repair retains its separately verified RED-first receipt.

## Parent verification

- information suite: `8 passed in 0.09s`;
- all S3-I1 focused suites plus sizing: `81 passed in 0.29s`;
- independent production-importing probe:
  - `PARENT_EQUAL_STACK_FOLD_PROJECTION=PASS`;
  - legacy raw `(8, (6,2), (6,2), (14,18))`;
  - canonical `(4, (2,2), (2,2), (18,18))`;
  - utilities `(Fraction(2,1), Fraction(-2,1))`;
- temporary probe deleted;
- `git diff --check`: PASS;
- production and sizing hashes unchanged;
- baseline tag preserved exactly.

Any previous audit or full-regression receipt against architecture hash `15b378ac...` is historical only. The new snapshot requires a new manifest, full regression, and wholly fresh exact-six non-author audit.
