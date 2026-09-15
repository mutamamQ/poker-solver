# Wave 3 evaluator/equity independence assessment

Reviewer: BryantGPT / Claude Sonnet 4.5 (tool-free analysis)
Parent disposition: initial coverage concern resolved for two-player scope

Independent paths:

1. Treys/Deuces lookup evaluator generated integer win/tie/loss counts for 16 fixed scenarios.
2. The project evaluator uses original rank histograms and direct seven-card category logic.
3. Exhaustive internal five-card enumeration checks canonical category totals.
4. `scripts/crosscheck_treys.py` compares 100,000 deterministic random seven-card categories and 50,000 random heads-up winners against Treys.

Reproduction: `uv run --with treys python scripts/crosscheck_treys.py`; `uv run pytest -q`.

The cross-check passed. Requests for multiway grids and all 1,326 range-class matchups exceed the mission's deliberately finite two-player reference scope and do not expose a specific discrepancy. The two exact preflop fixtures each enumerate 1,712,304 boards.

Blocking findings: none.

Signed: Wave 3 cross-check reviewer; expanded validation executed by the orchestrator.
