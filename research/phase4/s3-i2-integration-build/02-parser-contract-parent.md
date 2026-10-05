# S3-I2 strict parser parent recovery

owner=PARENT
source_owner=C3I2-IG2/C3I2-IG2R
status=COMPLETE_ANALYSIS_PARENT_RECOVERED
verified_at=2026-09-16T10:14:18Z

Both Bryant analyst attempts ended without writing their assigned report or heartbeat. This parent recovery uses the canonical retry transcript, the current source, and a parent execution of the permanent tests; it does not attribute a repository artifact to either child.

## Exact request contract

`solve-nplayer-preflop` requires exactly these 18 payload fields:

`version`, `num_players`, `button`, `starting_stacks`, `forced_posts`, `straddle_variant`, `ranges`, `sizing_rules`, `max_raises`, `max_deals`, `max_nodes`, `short_all_in_reopens`, `continuation`, `algorithm`, `iterations`, `seed`, `include_deviation_certificate`, `max_pure_strategies`.

The implementation uses the existing strict v4 helpers to reject extra or missing fields, bool-as-int values, non-finite numbers, invalid positive/non-negative bounds, unsupported enum values, malformed or colliding cards, malformed histories, duplicate terminal/showdown keys, malformed sizing expressions, unsupported algorithms, and non-null vanilla-CFR seeds. Nested continuation fields are exact for `terminal-table` and `showdown-ranks` variants before typed construction.

## Typed and response boundary

The parser constructs real `ForcedPost`, `WeightedCombo`, `NPlayerPreflopSizingRule`, `NPlayerPreflopPublicAction`, `NPlayerPreflopContinuation`, and `NPlayerPreflopConfig` objects, then calls `solve_nplayer_preflop`. It returns fresh JSON containers with 15 top-level fields: `version`, `operation`, `config_version`, `game_version`, `algorithm`, `iterations`, `seed`, `max_nodes`, `max_depth`, `strategy`, `values`, `certificate`, `metadata`, `provenance`, and `approximate`. The certificate field is always present and nullable.

## Executable evidence

Parent command:
`PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_api_v4_nplayer_preflop.py tests/test_phase4_s3_exports.py`

Result: `43 passed in 0.31s`, exit 0.

Current `src/poker_solver/api_v4.py` SHA-256: `70d378d6a52ae544615a5aa4dda6bd9e987f8161f08119914a0762ed0727a1a3`.

blocker_count=0
