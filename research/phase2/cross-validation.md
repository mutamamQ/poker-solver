# Independent cross-validation strategy

## Independence levels

1. External/published: different codebase or analytical result.
2. Independent in-project oracle: different algorithm/data path, suitable when exhaustive.
3. Internal agreement: useful regression evidence but not independent proof.

A cryptographic hash proves repeatability of bytes, not poker correctness. Wall-clock timing proves performance, not correctness. MCCFR-versus-vanilla agreement is Level 3 until both separately pass an external or analytical fixture.

## Gates

| Target | Oracle | Independence | Acceptance |
|---|---|---:|---|
| five-card evaluator | exhaustive 2,598,960 category census | 1 | exact counts |
| seven-card evaluator | deterministic Treys/PH-Evaluator comparison set | 1 | exact category/order |
| exact equity | 16 exact-card Treys count fixtures | 1 | exact wins/ties/losses/total |
| Kuhn | analytical value -1/18 plus exact BR | 1+2 | EV abs error <= 0.003; measured NashConv bound |
| scalable BR | existing Cartesian pure-policy enumerator on tiny games | 2 | both players/profiles abs error <= 1e-12 |
| MCCFR | vanilla CFR on Kuhn and one tiny spot, both checked by exact BR | 3 backed by 1/2 | predeclared seed matrix; mean/CI and EV tolerance reported |
| multi-street transitions | separately coded accounting/runout assertions and exhaustive tiny deck | 2 | exact terminal chips, probability mass, and zero-sum returns |
| JSON determinism | run same solve twice, hash exact bytes | repeatability only | identical hash locally |
| runtime | median fixed-fixture measurement | performance only | below parent-measured coarse ceiling |

## Sampling statistics

Do not assert monotonic exploitability; stochastic or even vanilla iteration metrics can rise locally. Use fixed integer seeds. For stochastic agreement, store every per-seed result, report sample mean and a 95% Student-t confidence interval, and require both the mean error and upper confidence bound to meet the fixture's predeclared tolerance. Tests should use a small deterministic seed matrix and a loose non-flaky gate; a separate evidence script can run more seeds.

## Tiny multi-street reference

Use a fully specified restricted-runout game with two compatible combos per player and a small public-card set. Enumerate every deal/runout/action branch. Validate probability mass = 1, exact terminal accounting, dynamic BR = pure enumeration, and vanilla/MCCFR values against those metrics. It is an independent small-game oracle, not a published commercial river EV.

## Anti-circular rules

- Never use this evaluator to generate the only expected equity values.
- Never call two wrappers around the same implementation independent.
- Never validate exploitability solely using the CFR strategy that is under test.
- Never infer accuracy from iteration count, strategy similarity, a screenshot, or runtime.
- Record all game conventions and tolerances before executing a comparison.

## Sources

- CFR: https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- MCCFR: https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html
- OpenSpiel algorithms and validation status: https://openspiel.readthedocs.io/en/latest/algorithms.html
- OpenSpiel exploitability: https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/algorithms/exploitability.py
- PokerStove: https://github.com/andrewprock/pokerstove
- Treys: https://github.com/ihendley/treys
- PH Evaluator: https://github.com/HenryRLee/PokerHandEvaluator
- RFC 8785: https://datatracker.ietf.org/doc/rfc8785/

## Rejected draft material

Invented fixture files/hashes, invalid hexadecimal seeds, cross-platform claims not run here, monotonic exploitability, and memory bounds based on raw float size while ignoring Python object overhead were removed.