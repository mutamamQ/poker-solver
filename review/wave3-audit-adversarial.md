# Wave 3 tree-audit adversarial review

Reviewer: BryantGPT / Claude Sonnet 4.5 (tool-free analysis)
Parent disposition: PASS with documented protocol assumptions

Attacks: cycles, terminal children, invalid chance mass, inconsistent infosets, node limits, mutable/unhashable states, transpositions and deep recursion.

Reproduction: `uv run pytest tests/test_audit.py tests/test_kuhn.py -q`.

The auditor rejects cycles, terminal actions, invalid chance distributions, non-finite/non-zero-sum returns, inconsistent owner/action signatures and oversized trees. It traverses every action path; DAG transpositions are deliberately counted per history, matching full-tree solver work. Immutable value-semantic states are a protocol invariant; unhashable states fall back to object identity. Generic code cannot infer poker-specific hidden-card leakage or prove perfect recall, so those are checked in game-specific tests and CFR owner-reach assertions. Recursive depth is bounded by the finite reference games.

Blocking findings: none.

Signed: Wave 3 audit reviewer; reproduced and dispositioned by the orchestrator.
