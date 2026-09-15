# Phase 2 accuracy fixtures

## Fixture policy

Every fixture must fully specify game rules, exact cards/ranges, utility baseline, expected value, oracle, and tolerance. Rounded GUI percentages and screenshots are rejected. Iteration count alone is never an accuracy proof.

| Area | Expected result | Oracle class | Tolerance / gate |
|---|---|---|---|
| Five-card evaluator census | category counts sum to 2,598,960 and match the published frequency vector already tested in Phase 1 | exhaustive combinatorics + published table | exact integer equality |
| Seven-card evaluator | project category/comparison agrees with PH Evaluator or Treys cross-check vectors | independent implementation; Treys is independent of this project but not of Deuces | exact category and ordering |
| Exact equity | the 16 exact-card win/tie/loss/total rows in `research/equity_fixtures.md` | exhaustive Treys 0.1.8 generation, independently recomputed here | exact integer equality |
| Kuhn value | player 0 value = -1/18 under this repository's stated ante/bet convention | published analytical game | absolute EV error <= 0.003 for finite CFR acceptance; oracle value exact |
| Tiny-game best response | dynamic/scalable BR equals existing pure-strategy enumeration | independent algorithmic implementation inside project | absolute value error <= 1e-12 |
| Hidden-bit game | legal infoset-consistent responder value = 0, while illegal per-history maximization would be +1 | exhaustive brute force | absolute error <= 1e-12 |
| Vanilla vs MCCFR | average EVs agree on Kuhn and a bounded Hold'em spot | independent update paths, not an external correctness proof | seed-matrix 95% CI and pre-registered absolute tolerance; initial gate 0.03 game units on Kuhn |
| Solved spot | reported NashConv computed from exact BR | best response against both profile components | nonnegative within 1e-9; threshold stated per fixture |

Kuhn equilibrium strategy is not a unique vector; testing a remembered single strategy table is unsafe. Test the value and exact exploitability of any explicitly supplied analytical profile instead. Generic labels such as “AA vs KK” are also insufficient because suits affect exact counts; the checked-in fixtures use exact cards.

No portable published river EV table was found. A Hold'em strategy fixture must therefore use a completely specified tiny game and a second implementation (pure-strategy enumeration or independent sequence-form solver) as its oracle.

## Sources

- Kuhn original material/reprint: https://www.rand.org/content/dam/rand/pubs/reports/2006/R1654.pdf
- CFR paper: https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- OpenSpiel algorithms/known-value validation: https://openspiel.readthedocs.io/en/latest/algorithms.html
- PokerStove evaluator: https://github.com/andrewprock/pokerstove
- Treys fixture oracle: https://github.com/ihendley/treys
- PH Evaluator independent candidate: https://github.com/HenryRLee/PokerHandEvaluator
- Best-response reference: https://www.ijcai.org/Proceedings/11/Papers/054.pdf

## Rejected draft values

Unspecified Leduc EVs, generic preflop class percentages, “monotonic exploitability,” and proprietary solver screenshots are not accepted fixtures.