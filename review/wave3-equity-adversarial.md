# Wave 3 equity adversarial review

Reviewer: BryantGPT / Claude Sonnet 4.5 (tool-free analysis)
Parent disposition: PASS for the documented heads-up scope

Attacks: collision filtering, invalid board lengths, tie shares, empty compatible ranges, zero/NaN weights, duplicate weighted entries, enumeration counts and suit symmetry.

Reproduction: `uv run pytest tests/test_equity.py -q`; `uv run --with treys python .wave0_equity_oracle.py`.

All 16 Treys-derived exact fixtures pass internally, including two C(48,5)=1,712,304 preflop enumerations. WeightedCombo rejects negative/NaN weights. Zero-weight and blocked pairs are skipped; no compatible positive-weight pair raises ValueError. Repeated combos deterministically contribute additive weight. Multiway tie splitting proposed by the reviewer is outside the explicitly heads-up protocol.

Blocking findings: none.

Signed: Wave 3 equity reviewer; reproduced and dispositioned by the orchestrator.
