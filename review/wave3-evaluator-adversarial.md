# Wave 3 evaluator adversarial review

Reviewer: BryantGPT / Claude Sonnet 4.5 (tool-free analysis)
Parent disposition: PASS after execution

Attacks: wheel, wheel straight flush, seven-card straight flush, double trips, three pairs, quads kicker, six-card flush, straight plus trips, duplicates.

Reproduction: `uv run pytest tests/test_evaluator.py -q`.

The nine explicit adversarial seven-card vectors pass. The exhaustive five-card category test covers all 2,598,960 hands and matches canonical frequencies. A deterministic Treys cross-check additionally passed 100,000 random seven-card category cases and 50,000 random heads-up comparisons. Treys maps rank 1 (royal flush) to class 0, so the cross-check deliberately folds that library quirk into straight-flush class 1 before comparing categories.

Blocking findings: none.

Signed: Wave 3 evaluator reviewer; reproduced and dispositioned by the orchestrator.
