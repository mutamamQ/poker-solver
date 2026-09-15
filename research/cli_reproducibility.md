# CLI and reproducibility

The reference CLI is intentionally small and noninteractive:

- `poker-solver solve-kuhn --iterations N [--json]`
- `poker-solver evaluate CARD... [--json]`
- `poker-solver equity --hero As,Ah --villain Ks,Kh [--board CARD,...] [--json]`
- `poker-solver solve-spot CONFIG.json --iterations N [--json]`

All card notation is strict two-character rank `23456789TJQKA` plus lowercase suit `shdc`. Exact combo ranges in spot JSON are arrays such as `{"cards":["As","Kh"],"weight":1.0}`; shorthand like `ATs+` is out of scope until separately specified and tested.

A spot config contains schema version, five-card river board, initial pot, equal remaining stacks, player-to-act, each player's exact weighted combos, and deterministic finite action sizes expressed as integer `raise_to` amounts. Unknown fields and incompatible cards are errors.

Machine-readable output uses sorted JSON keys and contains schema version, algorithm, requested/completed iterations, utility convention, player values, `nash_conv`, optional `exploitability_half_nash_conv`, and strategies keyed by collision-free information-state strings. Progress goes to stderr only; `--json` stdout contains one JSON document. No wall-clock timestamp or runtime appears in deterministic result JSON.

Exit codes: 0 success, 2 input/validation error, 1 internal/runtime failure, 130 interrupt. Error text identifies the field/card/history but never returns a partial strategy as success.

## Reproducibility

Vanilla full-tree CFR has no randomness, so a seed flag is unnecessary. Legal actions, chance outcomes, cards, information sets, and JSON keys are sorted canonically. Python is 3.11; dependencies are locked with `uv.lock`; build and tests use `uv sync --frozen` after the lock exists and `uv run pytest`. Floating results are emitted as JSON numbers with stable traversal order; tests compare meaningful numeric fields rather than environment metadata.

## Smoke tests

- `uv run poker-solver evaluate As Ks Qs Js Ts --json` reports straight flush.
- `uv run poker-solver equity --hero As,Ah --villain Ks,Kh --json` reports exact total 1,712,304 and checked win/tie/loss counts.
- `uv run poker-solver solve-kuhn --iterations 20000 --json` parses and approaches -1/18 with a tested NashConv bound.
- Duplicate cards exit 2 and write diagnostics to stderr.
- Running the same deterministic command twice yields identical stdout bytes.

## Sources

- uv project/lock documentation: https://docs.astral.sh/uv/
- Python packaging metadata (PEP 621): https://peps.python.org/pep-0621/
- JSON Schema: https://json-schema.org/
- PokerStove evaluator CLI precedent: https://github.com/andrewprock/pokerstove
- OpenSpiel game/algorithm CLI and reproducibility precedent: https://github.com/google-deepmind/open_spiel
