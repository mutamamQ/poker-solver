# Wave 3 CLI adversarial review

Reviewer: BryantGPT / Claude Sonnet 4.5 (tool-free analysis)
Parent disposition: one confirmed blocker fixed

Attacks: malformed cards, duplicate cards, strict JSON schema, NaN/Inf, bool/int coercion, deterministic bytes, filesystem errors and exit codes.

Reproduction: `uv run pytest tests/test_cli.py -q`.

Confirmed finding: `_load_spot` previously coerced strings and booleans with `float()`/`int()`. Fixed by strict JSON number/integer validators, explicit bool rejection, and tests. JSON emission now sets `allow_nan=False`; domain validators already prevent non-finite solver output. Repeated Kuhn runs are byte-identical. Invalid domain/config input and local read errors return 2 on stderr. Arbitrary local paths are expected for a user-invoked local CLI and are not a privilege-boundary traversal flaw.

Blocking findings after fix: none.

Signed: Wave 3 CLI reviewer; fix reproduced and dispositioned by the orchestrator.
