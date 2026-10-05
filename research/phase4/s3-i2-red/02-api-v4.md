# S3-I2 strict v4 preflop API RED receipt

owner=R3I2-2R-PARENT-RECOVERY
status=COMPLETE_RED
completed_at=2026-09-16T08:10:49Z
accepted_base=7285335caad555a9a71bd5f4055c2e1c3ee0262f
test_path=tests/test_api_v4_nplayer_preflop.py
test_sha256=38b36491172a3152157ff369f680ba0a5bab25c5a551db3552ed7074f52ff50d

The original R3I2-2 failed before tools with `HTTP 502: Model did not return valid tool/structured JSON; no tools executed`. Its sole retry wrote the test file but failed to write the required report or heartbeat and left 24 broad `pytest.raises(ValueError)` cases falsely green because the existing dispatcher rejected the unknown operation before reaching payload validation. Parent rejected that evidence after reading the canonical transcript and rerunning the file.

After retry ownership ended, the parent narrowly repaired the exclusive API test path:

- replaced invalid posts, sizing expressions, and short-all-in field names with the literal architecture schema;
- supplied both required blinds and strict continuation provenance/source;
- supplied all three reachable non-fold terminal-table histories for the bounded HU fixture;
- retained a supplied-ranks fixture;
- added field-specific error-message assertions so unknown-operation rejection cannot make nested payload tests falsely pass;
- independently constructed equivalent typed configs and exhaustively traversed both 11-node/6-terminal trees, proving both fixture families valid and zero-sum.

Authenticated RED command:

`PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_api_v4_nplayer_preflop.py`

Result: `29 failed, 1 passed in 0.25s`, exit 1. All 29 failures reached the current unsupported-operation boundary. Twenty-five payload-negative tests additionally failed their field-specific regex rather than accepting that unrelated exception. The sole pass is the already-supported strict request-envelope extra-field rejection; it is valid characterization, not claimed S3 behavior.

The suite contains no skip, xfail, mock, caught absence, or placeholder assertion. Production remains unmodified. This RED receipt gates future API GREEN implementation; it does not authorize editing the test path while another owner exists.
