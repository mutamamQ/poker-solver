# S3-I1 HU compatibility specification reconciliation

status=RESOLVED_PENDING_FRESH_AUDIT
completed_at=2026-09-16T06:46:09Z
accepted_base_head=65d411793d1d7767d86500d0adffe9f40b379108
phase3-398-green=feba8222a0b614b0c64eca59402403ce733195ea
old_architecture_sha256=a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6
new_architecture_sha256=15b378ac224460ee8064e3c54f5925d3721d4ca38e4529cf84b7e82858975a78
production_sha256=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812
old_information_test_sha256=0d800d2f8fe797f29d8a347e1ab216bbc079fee0ede792ab253db23097819445
new_information_test_sha256=49cf12eb1bd514a4bcaad4bae896f4a143407ceff71928cdaf5e8f05395e2e84

## Trigger

Fresh non-author audit C3I1-5R found an unequal-stack N=2 trace with stacks `(20, 7)` and public actions `CALL 2`, `RAISE 7`, `RAISE 20`. Its report and heartbeat are:

- `research/phase4/s3-i1-repair-audit/05-settlement-info-hu.md` SHA-256 `837f7497a2785c621c5bd3ba4ea7d5f6e726e7915ffcf91ce1b24e86de9b824a`;
- `research/phase4/s3-i1-repair-audit/.hb/C3I1-5R` SHA-256 `981c86013e095f23ee592db26393e98cf980a9976cb114c7fcd48b7c68188277`.

Parent independently reproduced the exact trace. All actors and ordered legal actions align before the last action. Afterward:

- legacy `preflop.py` leaves seat 1 actionable with `remaining=(0, 0)` and actions `FOLD`, `CALL 7`;
- `nplayer_preflop.py` follows architecture sections 7–8: it closes because no actionable responder remains, refunds 13, matches contributions at `(7, 7)`, leaves `(13, 0)`, pot 14, and returns exact `(7, -7)`.

## Decision

This is a specification conflict, not a production defect. Universal custom-stack legacy equivalence conflicts with:

- additive preservation of the legacy module;
- required pending/closure semantics in section 7;
- mandatory unmatched-excess refund in section 8;
- the acceptance matrix's frozen Phase-3 fixture language.

The architecture now makes the compatibility domain explicit: frozen Phase-3 HU projection fixtures and aligned prefixes that remain valid in both machines. The known legacy chipless-responder suffix is outside that domain. The new N-player path remains authoritative for correct closure/refund, and legacy behavior is unchanged.

Permanent regression `test_hu_projection_excludes_legacy_chipless_responder_suffix` freezes both the known legacy suffix and the correct N-player terminal state. No production code changed.

## Verification

- `uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_information.py`: `8 passed in 0.16s`.
- Four S3-I1 suites plus `tests/test_sizing.py`: `81 passed in 0.26s`.
- `git diff --check`: clean.
- Production hash remains `a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812`.

Disposition: refreeze architecture, permanent tests, production, original RED receipt, and this receipt together; rerun full regression; obtain a fresh different non-author audit before acceptance.
