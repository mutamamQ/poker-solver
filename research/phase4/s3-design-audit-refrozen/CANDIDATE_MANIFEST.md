# S3 refrozen design candidate

- candidate: `/home/genomix-node/poker-solver/ARCHITECTURE_PHASE4_S3.md`
- raw SHA-256: `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`
- accepted S2-complete base HEAD: `4b3f87f4e6cf38e9dc88aca744b23de2c44c08fe`
- preserved historical baseline: `phase3-398-green` -> `feba8222a0b614b0c64eca59402403ce733195ea`
- candidate type: design-only; S3 production and tests intentionally absent
- authority: this architecture alone; prior design streams and audit reports are non-authoritative historical inputs
- audit directory: `/home/genomix-node/poker-solver/research/phase4/s3-design-audit-refrozen/`
- required reports: `01-model-ledger-deals-positions.md`, `02-betting-reopening.md`, `03-straddles-order.md`, `04-settlement-information.md`, `05-solver-api-tdd.md`, `06-cross-release.md`
- required regular heartbeats: `.hb/A3J1` through `.hb/A3J6`
- release rule: all six fresh reports must independently hash this exact candidate pre/post, PASS without substantive contradiction, preserve base/tag, and survive parent verification

The repair since the rejected `ac14b51c...` candidate is intentionally narrow: operational UTG and UTG+1 aliases are now explicit for N=3/4/5 and consistent through N=9. Auditors must attack—not assume—these mappings, including standard at N=3, double at N=4, HU Mississippi rejection, and N=3 double rejection.
