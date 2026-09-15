# MCCFR versus vanilla CFR

Vanilla CFR traverses every branch per sweep and gives the deterministic reference path. MCCFR samples a block of histories and updates unbiased estimators under the sampling distribution specified by Lanctot et al. The paper explicitly reports the tradeoff: sampled methods can need more iterations, while lower iteration cost can reduce wall time in some games. There is no universal speedup number.

## Selected fast path

Implement external-sampling MCCFR for two-player zero-sum sequential perfect-recall games:

1. For each iteration and each updating player, start at the root.
2. Sample one outcome at chance nodes from the declared chance distribution.
3. Sample one action from the current strategy at opponent nodes.
4. Traverse every action at updating-player nodes; compute the strategy-weighted node value and add `child_value - node_value` to sampled counterfactual regret.
5. Accumulate the average strategy at opponent nodes using the standard two-player simple-averaging convention.
6. Use a dedicated `random.Random(seed)` instance and stable action/outcome order.

OpenSpiel's implementation provides a readable independent reference for this exact traversal. Phase 2 keeps vanilla regret matching; CFR+ is a separate alternating/vector algorithm with clipped cumulative regret and is not silently mixed into MCCFR.

## Preconditions and pitfalls

The game must be finite, sequential, two-player zero-sum, and perfect recall. Every history in one information set must have the same ordered legal-action tuple. “Single action per information set” is wrong: an information set may have many actions, but a behavioral policy must be shared across its hidden histories.

A multi-street tree is safe when those conditions remain true. More streets increase variance and runtime but do not invalidate MCCFR. Multiplayer/general-sum use is explicitly outside the Phase 2 correctness claim because the two-player Nash-convergence guarantee does not transfer.

## Acceptance

- Same seed/input/iterations gives byte-identical canonical JSON.
- Different seeds are allowed to differ.
- On Kuhn, a fixed seed matrix must approach -1/18 and meet a measured NashConv bound.
- On a tiny Hold'em game, MCCFR and vanilla CFR EV must agree within a tolerance fixed before running the comparison.
- Sampling frequencies for a synthetic chance game must pass a deterministic count fixture for the selected seed.
- The vanilla path remains available and unchanged.

## Sources

- Original CFR: https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- MCCFR paper: https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html
- OpenSpiel algorithm inventory: https://openspiel.readthedocs.io/en/latest/algorithms.html
- OpenSpiel external-sampling implementation: https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/algorithms/external_sampling_mccfr.py
- CFR+ specification: https://arxiv.org/abs/1407.5042
- Discounted CFR (distinct from CFR+): https://ojs.aaai.org/index.php/AAAI/article/view/4007