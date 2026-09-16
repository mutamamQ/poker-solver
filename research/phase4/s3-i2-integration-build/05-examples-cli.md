# S3-I2 examples and generic CLI integration authentication

Parent reconciliation (2026-09-16T10:05:24Z): this is authenticated pre-implementation RED attribution. The current candidate now supplies the dispatcher operation, the example suite passes 13/13, and `src/poker_solver/cli.py` remains unchanged at SHA-256 `3f4df8452f427757d11c7bcee8b44b783efe65290b2f18050cdeba67d94ada13`.

owner=C3I2-IG5
status=AUTHENTICATED
completed_at=2026-09-16T09:36:00Z
accepted_base=7285335caad555a9a71bd5f4055c2e1c3ee0262f

## Scope

Validate committed 2/6/9 JSON request examples with typed constructors and state traversal, map generic file/stdin/--json/error/determinism assertions, and identify whether CLI code changes are necessary.

## Findings

### Canonical examples (2/6/9 player preflop)

**Status:** Authenticated as valid typed fixtures with RED attribution to missing operation handler.

All three example files (`examples/phase4/nplayer_2p_preflop.json`, `nplayer_6p_preflop.json`, `nplayer_9p_preflop.json`) construct valid `NPlayerPreflopConfig` and `NPlayerPreflopContinuation` objects. Each:

- Parses to strict v4 request envelope: `{"version": 4, "operation": "solve-nplayer-preflop", "payload": {...}}`
- Builds a real chance root via `create_nplayer_preflop_root(config)`
- Exposes exactly one exact-mass deal (probability 1.0)
- Reaches a decision node with legal actions before `dispatch_v4` is invoked

Typed preflight tests pass for all three player counts (2/6/9).

**Frozen SHA-256:**

- `examples/phase4/nplayer_2p_preflop.json`: `884bd673589224885feeafe8633fc9a4cdae69b18135e9ebf4cd1eae3d7fa8e5`
- `examples/phase4/nplayer_6p_preflop.json`: `3d46183d39b0bb905a3679a38776683c47db9657825c92e55bc239176dcc7365`
- `examples/phase4/nplayer_9p_preflop.json`: `1f7b26a0e3fee5912b9695a59a2a181dbd13f3b5df386a9fe15f07e690dcdfb9`

### Generic CLI integration contract

**Status:** Authenticated. No CLI code changes required.

The test suite `tests/test_phase4_s3_examples.py` validates:

1. **File input:** `phase4 <path> --json` for all three examples
2. **Stdin input:** `phase4 - --json` with 2p example piped to stdin
3. **Error handling:** Missing file returns exit code 2 with error message
4. **Error handling:** Malformed JSON returns exit code 2 with error message
5. **Direct dispatch:** `dispatch_v4(request)` for all three examples returns strict v4 envelope
6. **Determinism:** Repeated dispatch returns identical results
7. **Strategy normalization:** All policies sum to 1.0 and contain finite non-negative probabilities

Existing CLI parser in `src/poker_solver/cli.py` already implements:

- `phase4` subcommand accepting file path or `-` for stdin
- `--json` flag for JSON output
- Generic error handling with exit code 2
- Stdin support via `api.load_json_from_source(args.request)` which handles `-` as stdin marker

**No CLI code changes are necessary.** The generic contract is already satisfied by existing implementation.

### RED attribution

**Blocker:** `api_v4.dispatch_v4()` does not recognize `"solve-nplayer-preflop"` operation.

Current allowed operations (line 330 of `api_v4.py`):

```python
allowed={"solve-allstreet-postflop", "solve-nplayer-postflop"}
```

The operation `"solve-nplayer-preflop"` is not in the allowed set. All eight RED failures are attributable to this missing operation handler, not to:

- Missing example files
- Malformed typed fixtures
- CLI parser defects
- Generic stdin/file/error handling gaps

### Test execution

**Command:**

```bash
cd /home/genomix-node/poker-solver && python -m pytest tests/test_phase4_s3_examples.py -v
```

**Result:** 5 passed, 8 failed in ~1.8s

**Passing (5):**

- `test_example_request_constructs_a_valid_bounded_typed_root[2]`
- `test_example_request_constructs_a_valid_bounded_typed_root[6]`
- `test_example_request_constructs_a_valid_bounded_typed_root[9]`
- `test_phase4_preflop_missing_file_error`
- `test_phase4_preflop_malformed_json_error`

**Failing (8):** All fail with `ValueError: operation must be one of ['solve-allstreet-postflop', 'solve-nplayer-postflop']`

- `test_phase4_nplayer_2p_preflop_example_file`
- `test_phase4_nplayer_6p_preflop_example_file`
- `test_phase4_nplayer_9p_preflop_example_file`
- `test_phase4_nplayer_preflop_stdin_execution`
- `test_2p_example_direct_dispatch`
- `test_6p_example_direct_dispatch`
- `test_9p_example_direct_dispatch`
- `test_example_strategies_normalized`

### Frozen test SHA-256

- `tests/test_phase4_s3_examples.py`: `8c3a416b298aa4bad0c902817500ccf7450f73636330cebc396fac8828f27061`

### Legacy example naming

The task referenced `02-hand-evaluation.json`, `06-game-state.json`, and `09-equity-calculation.json`. These files do not exist. The actual canonical examples are the phase4 N-player preflop fixtures listed above.

## Conclusion

Canonical examples are authenticated as valid typed fixtures. Generic CLI integration contract is authenticated as already satisfied by existing implementation. RED is attributable to missing `"solve-nplayer-preflop"` operation handler in `api_v4.dispatch_v4()`. No CLI code changes are required.
