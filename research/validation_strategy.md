# Correctness-validation strategy

Correctness is layered; convergence output is not a proof by itself.

1. Pure functions: card parser rejects malformed/duplicate cards; five-card rank tuples obey category and kicker ordering; range weights and chance probabilities are finite, nonnegative, and normalized.
2. Exhaustive evaluator oracle: enumerate all C(52,5) sets and match the nine exact category counts. Compare selected 7-card hands to a separately packaged evaluator.
3. State invariants: legal actions are deterministic; terminal nodes have no actions; every terminal payoff is finite and zero-sum; chance probabilities sum to one; every information-set key has one owner and one legal-action tuple.
4. Tiny exact games: matching pennies/RPS normal-form wrappers have value 0. Standard Kuhn poker has player-0 value -1/18. Compare CFR's average profile to exact best responses rather than requiring one particular non-unique equilibrium strategy.
5. Independent best response: choose one action per information set after aggregating counterfactual values across all histories in it. A per-hidden-card maximizer is an illegal perfect-information oracle. Define `NashConv = Σ_i (BR_i(σ_-i)-u_i(σ))`. For a two-player constant-zero-sum game this equals the sum of the two best-response values. If reporting “exploitability” as average incentive, explicitly use `NashConv/2`; tests must name the convention.
6. CFR convergence: test checkpoints or final thresholds, not strict iteration-by-iteration monotonicity. Vanilla CFR's average strategy converges asymptotically but individual measurements can increase.
7. Hold'em known answers: equity fixtures use exhaustive legal runouts and exact win/tie/loss counts. A compact river game is checked against a separately coded normal-form/sequence-form oracle where tractable.
8. Metamorphic checks: suit permutations preserve ranks/equities; swapping players and negating utilities preserves value; scaling every terminal utility by positive c scales values/NashConv by c; card-order permutation does not change rank.
9. CLI: same deterministic configuration produces the same strategy/value fields; JSON parses; invalid cards/config exit nonzero; a Kuhn solve reaches its documented NashConv threshold.

Suggested tolerances: exact integer counts; 1e-12 probability normalization; 1e-10 zero-sum arithmetic; 1e-8 for exact matrix/LP values; measured finite-iteration thresholds for CFR (for example Kuhn value error <1e-3 and NashConv below a test-calibrated bound). Do not invent a tolerance before timing the implementation.

## Sources

- CFR theorem and counterfactual values: https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- MCCFR estimators: https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html
- Kuhn's game: https://www.rand.org/content/dam/rand/pubs/reports/2006/R1654.pdf
- OpenSpiel algorithms/reference games: https://github.com/google-deepmind/open_spiel
- OpenSpiel exploitability implementation (normalization conventions): https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/algorithms/exploitability.py
- Sequence form: https://doi.org/10.1006/game.1996.0051
