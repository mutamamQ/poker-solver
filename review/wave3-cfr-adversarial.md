# Wave 3 CFR adversarial review

Reviewer: BryantGPT / Claude Sonnet 4.5 (tool-free analysis)
Parent disposition: PASS after execution

Attacks: chance reach multiplication, accumulation over histories in one infoset, acting-player reach weighting, frozen simultaneous updates, zero reach, traversal mutation and convergence wording.

Reproduction: `uv run pytest tests/test_cfr.py -q`.

The implementation freezes one regret-matched profile per iteration, traverses both updating players against it, accumulates deltas by `+=`, and applies them only after both traversals. Regret weight is opponent reach times cumulative chance reach. Average strategy uses acting-player reach once per infoset/iteration and explicitly rejects imperfect-recall owner-reach mismatches. Deterministic Kuhn at 5,000 iterations is within 0.003 of -1/18 and below 0.03 NashConv. No monotonic-exploitability claim is made.

Blocking findings: none.

Signed: Wave 3 CFR reviewer; reproduced and dispositioned by the orchestrator.
