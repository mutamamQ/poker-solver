# S3-I2 independent oracle and boundary plan

owner=R3I2-6-PARENT-RECOVERY
status=COMPLETE_PLAN
accepted_base=7285335caad555a9a71bd5f4055c2e1c3ee0262f

The R3I2-6 and R3I2-6R child outputs are not artifact evidence. The original left only a timestamp; the retry's canonical transcript wrote neither its assigned report nor heartbeat. This parent-authored plan resolves the two reported ambiguities against the accepted architecture and existing generic/S2 contracts.

## Resolved semantics

1. `solve_nplayer_preflop(..., max_pure_strategies=100_000)` uses the same default as `unilateral_deviation_certificate` and `solve_nplayer_postflop`. The strict JSON API still requires an explicit positive strict integer because the v4 payload schema is exact.
2. A player's pure-policy count equal to the cap is accepted. Only `count > max_pure_strategies` raises `ValueError` containing `pure-strategy bound exceeded`.
3. Integer showdown ranks may tie. Larger ranks win; equal largest ranks split each exact side-pot layer. Indivisible chips are awarded by the declared full-seat `odd_chip_order`. Ties are required behavior, not malformed input.
4. Duplicate rejection means duplicate semantic terminal-table keys and duplicate showdown deals. The architecture does not require detection of duplicate raw JSON object keys after ordinary JSON parsing.
5. All bool-as-int, nonfinite numeric, malformed history/deal, unknown/missing nested-field, unsupported algorithm/seed, and nonpositive-bound cases fail at the strict v4 boundary with documented `ValueError`, never an unrelated low-level exception.
6. The facade is bounded deterministic vanilla CFR only. Metadata must state no convergence claim; `approximate` is false because the finite game, chance enumeration, and settlement are exact even though a finite-iteration strategy is not claimed converged.

## Executable oracle map

### Typed solve and deviation

Permanent file: `tests/test_nplayer_preflop_solve.py`.

- `_tree` independently traverses every edge of tiny N=2/6/9 fixtures, enforces the node cap, checks exact pot/contribution conservation, exact terminal zero-sum utilities, information-set action consistency, and observed depth.
- `_values` independently computes full-tree expected values without importing production expectation helpers.
- `_oracle` Cartesian-enumerates every complete pure information-set choice for each player. The six-player fixture proves counts `(1, 4, 4, 1, 1, 1)`, baseline `(5, 1/8, -17/8, -1, -1, -1)`, and incentives `(0, 3/8, 3/8, 0, 0, 0)`.
- Compare the independent result to both the generic production certificate and future preflop facade certificate. Cap 4 must pass; cap 3 must fail. This proves the inclusive boundary.
- Run deterministic repeated solves, finite normalized policy checks, exact structural depth, deep detachment, strict parameters, node-bound forwarding, and optional certificate behavior.

### Settlement, ties, and odd chips

Permanent files: `tests/test_nplayer_preflop_settlement.py` and `tests/test_nplayer_preflop_information.py`.

- Independently layer contributions by sorted contribution thresholds.
- For every layer, derive eligible non-folded contributors, select the largest rank, split by integer division, and assign remainders in `odd_chip_order` restricted to tied winners.
- Compare exact rational/chip utilities to production for unequal stacks, ties, odd chips, folds, and canonical unmatched-chip refunds.
- Keep the equal-stack fold-ledger and unequal-stack chipless-responder regressions as compatibility boundaries.

### API and examples

Permanent files: `tests/test_api_v4_nplayer_preflop.py` and `tests/test_phase4_s3_examples.py`.

- Before interpreting API RED/GREEN, construct both terminal-table and showdown-rank payloads as typed production configs and traverse their real roots.
- For 2/6/9 JSON examples, reconstruct typed configs from the literal request files, build a chance root, verify one exact-mass compatible deal, then invoke direct dispatch and generic CLI file/stdin paths.
- Require exact response keys, N finite values summing within `1e-9`, every policy normalized within `1e-12`, deterministic equality, detached nested responses, provenance, no convergence claim, and `approximate: false`.
- Existing generic missing-file and malformed-JSON CLI controls remain green. `cli.py` may change only if one of those generic paths proves a real defect after the new operation exists.

### Exports and capability truth

Permanent file: `tests/test_phase4_s3_exports.py`.

- Import all nine architecture symbols from both their defining module and package root and require identity.
- Require exact `nplayer-preflop` capability metadata while preserving S1/S2 entries.
- Mutation of a returned capability catalog must not affect a later response.

## Parent gate commands

Pre-GREEN authenticity:

`PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_solve.py tests/test_api_v4_nplayer_preflop.py tests/test_phase4_s3_examples.py tests/test_phase4_s3_exports.py`

Core GREEN first:

`PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_solve.py tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py`

Integration GREEN second:

`PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_api_v4_nplayer_preflop.py tests/test_phase4_s3_examples.py tests/test_phase4_s3_exports.py tests/test_api_v4.py tests/test_api_v4_nplayer.py tests/test_phase4_s2_examples.py`

Frozen candidate gate:

`PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider`

Also require `python -m compileall -q src tests`, `git diff --check`, literal candidate SHA-256 verification, unchanged `phase3-398-green`, a fresh different exact-six non-author audit, parent adjudication, and an accepted-wave commit.
