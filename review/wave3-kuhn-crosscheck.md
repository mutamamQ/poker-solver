# Wave 3 Kuhn independent derivation

Reviewer: BryantGPT / Claude Sonnet 4.5
Verdict: PASS

Canonical structure: six ordered distinct deals. Per deal there are four decision nodes and five terminals: check-check, check-bet-fold, check-bet-call, bet-fold, bet-call. Totals are one chance node, 24 decisions, 30 terminals, 55 nodes and 12 information sets. Showdown utility is ±1 without a called bet and ±2 after a call; folds are ±1. The first-player equilibrium value is -1/18.

Reproduction: `uv run pytest tests/test_kuhn.py tests/test_cfr.py -q`.

The tree auditor returns exactly 55/24/30/1/12, infoset keys hide the opponent card, all terminal utilities are zero-sum, and deterministic CFR reproduces -1/18 within the documented tolerance.

Blocking findings: none.

Signed: Wave 3 independent Kuhn cross-checker; execution reproduced by the orchestrator.
