# F3A1 final architecture/HU reconciliation audit

status=COMPLETE_PASS
provider=bryant
auditor=F3A1
production_sha256=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812
architecture_sha256=15b378ac224460ee8064e3c54f5925d3721d4ca38e4529cf84b7e82858975a78
blocker_count=0
utc=2026-09-16T07:12:00Z

Fresh final non-author audit against literal research/phase4/s3-i1-final-audit/CANDIDATE_MANIFEST.md. All work from /home/genomix-node/poker-solver. No source, tests, manifest, or git edits. Only this report and .hb/F3A1 are durable writes.

## Verdict

PASS. The final reconciled architecture is internally consistent, the known HU compatibility domain is explicit and narrow, the invalid legacy chipless-responder suffix is correctly excluded, and the N-player closure/refund is required and correct.

## Verification

### Manifest hashes (before and after)

All 10 raw SHA-256 entries verified before audit and again after:

```
15b378ac224460ee8064e3c54f5925d3721d4ca38e4529cf84b7e82858975a78  ARCHITECTURE_PHASE4_S3.md
a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812  src/poker_solver/nplayer_preflop.py
8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240  src/poker_solver/sizing.py
bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268  tests/test_nplayer_preflop_config.py
9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd  tests/test_nplayer_preflop_betting.py
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
49cf12eb1bd514a4bcaad4bae896f4a143407ceff71928cdaf5e8f05395e2e84  tests/test_nplayer_preflop_information.py
2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1  tests/test_sizing.py
61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11  research/phase4/s3-i1-repair/RED_RECEIPT.md
36a95b38ec1b6016bc46ca80307b2c9f4119c749fceb51cd822bccaf61965164  research/phase4/s3-i1-spec-reconciliation/RECEIPT.md
```

### Information tests

```sh
uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_information.py
```
Result: `8 passed in 0.14s`, exit 0.

### Focused S3-I1 plus sizing

```sh
uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py tests/test_sizing.py
```
Result: `81 passed in 0.39s`, exit 0.

### Production hash

```sh
sha256sum src/poker_solver/nplayer_preflop.py
```
Result: `a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812`, unchanged.

## Architecture reconciliation

### Context

C3I1-5R blocker report (research/phase4/s3-i1-repair-audit/05-settlement-info-hu.md) found one reproducible architecture/legacy closure conflict on unequal stacks (20,7) with trace CALL 2, RAISE 7, RAISE 20:

- Legacy leaves seat 1 actionable with remaining=(0,0) and actions FOLD/CALL 7.
- Candidate closes (actor=-2), refunds 13 to seat 0, pot=14, street=total=(7,7), remaining=(13,0), exact utilities=(7,-7).

Reconciliation receipt (research/phase4/s3-i1-spec-reconciliation/RECEIPT.md) resolved this as a specification conflict, not a production defect. The architecture now explicitly states the compatibility domain: frozen Phase-3 HU projection fixtures and aligned prefixes that remain valid in both machines. The invalid legacy chipless-responder suffix is outside that domain.

### Architecture sections 7–8 (closure/refund)

Architecture line 7 (section 1, paragraph 3):
> "The N-player path must instead obey sections 7–8 by closing when no actionable responder remains, refunding unmatched excess, and leaving the legacy module unchanged."

Architecture section 7 (lines 169–194) defines betting semantics: action closes when one live seat remains or no actionable pending responder remains.

Architecture section 8 (lines 197–208) defines terminal accounting: before any terminal is finalized, call `refund_uncalled_excess(total_contributed)`.

### Permanent regression

test_nplayer_preflop_information.py lines 304–386: `test_hu_projection_excludes_legacy_chipless_responder_suffix` freezes both the known legacy suffix and the correct N-player terminal state.

### Independent reproduction

Stacks (20,7), SB=1, BB=2, actions CALL 2, RAISE 7, RAISE 20:

```
BEFORE CALL 2:
  legacy: actor=0 actions=(FOLD, CALL 2, RAISE 20)
  generic: actor=0 actions=(FOLD, CALL 2, RAISE 20)
  legacy ledger: pot=3 street=(1, 2) total=(1, 2) remaining=(19, 5)
  generic ledger: pot=3 street=(1, 2) total=(1, 2) remaining=(19, 5)

AFTER CALL 2:
  legacy: actor=1 actions=(CHECK, RAISE 7)
  generic: actor=1 actions=(CHECK, RAISE 7)
  legacy ledger: pot=4 street=(2, 2) total=(2, 2) remaining=(18, 5)
  generic ledger: pot=4 street=(2, 2) total=(2, 2) remaining=(18, 5)

AFTER RAISE 7:
  legacy: actor=0 actions=(FOLD, CALL 7, RAISE 20)
  generic: actor=0 actions=(FOLD, CALL 7, RAISE 20)
  legacy ledger: pot=9 street=(2, 7) total=(2, 7) remaining=(18, 0)
  generic ledger: pot=9 street=(2, 7) total=(2, 7) remaining=(18, 0)

AFTER RAISE 20:
  legacy: actor=1 actions=(FOLD, CALL 7)
  generic: actor=-2 actions=()
  legacy ledger: pot=27 street=(20, 7) total=(20, 7) remaining=(0, 0)
  generic ledger: pot=14 street=(7, 7) total=(7, 7) remaining=(13, 0)
  generic terminal: values=(Fraction(7, 1), Fraction(-7, 1))
```

All actors and ordered legal actions align before the last action. Afterward, legacy leaves a chipless responder actionable; candidate closes, refunds 13, and returns exact zero-sum utilities.

## Adjudication

The final architecture is internally consistent:

1. Frozen valid legacy fixtures and prefixes match (architecture line 9, section 10 acceptance matrix line 298).
2. Invalid legacy chipless suffix is explicitly excluded (architecture line 9, section 1 paragraph 3).
3. N-player §§7–8 closure/refund is required (architecture lines 7, 169–194, 197–208).
4. Legacy remains unchanged (architecture line 7, section 1 paragraph 2).
5. Permanent regression freezes both behaviors (test lines 304–386).

This is a narrow evidence-backed reconciliation. It does not hide a production mismatch or weaken mission acceptance. The N-player path is authoritative for correct closure/refund. The legacy module is preserved unchanged. The compatibility domain is explicit and frozen.

## Scope

This audit verifies architecture/HU reconciliation only. No full regression, solver/CFR/API audit, or global HU equivalence claim is made.

## Commands

```sh
cd /home/genomix-node/poker-solver
sha256sum ARCHITECTURE_PHASE4_S3.md src/poker_solver/nplayer_preflop.py tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py tests/test_sizing.py research/phase4/s3-i1-repair/RED_RECEIPT.md research/phase4/s3-i1-spec-reconciliation/RECEIPT.md
uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_information.py
uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py tests/test_sizing.py
python3 - <<'PY'
[independent reproduction script]
PY
```

All commands exit 0. All hashes match manifest. No commits.
