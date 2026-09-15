# Solver algorithms

## Recommendation

Implement deterministic full-tree vanilla Counterfactual Regret Minimization (CFR) first. It is the clearest standard reference algorithm for finite two-player zero-sum perfect-recall games: every chance outcome and action is traversed, all arithmetic is reproducible, and sampling variance cannot hide reach-probability bugs. CFR+ or DCFR can be added only after the baseline agrees with exact tiny-game oracles.

At information set I owned by i, regret matching uses σ(I,a)=R⁺(I,a)/Σ_b R⁺(I,b), or uniform if the denominator is zero. For a traversal with player reaches π0,π1 (chance is already integrated by weighted chance branches), action values v(a) and node value v=Σ_a σ(a)v(a), accumulate R(I,a) += π_{-i}(v_i(a)-v_i). Accumulate the reported average strategy with the owner's reach: S(I,a) += π_i σ(I,a). Normalize S per information set. Vanilla CFR retains negative cumulative regrets; only regret matching clips them.

CFR guarantees that average external regret tends to zero and the average profile approaches Nash in two-player zero-sum games. It does not guarantee exploitability decreases every iteration.

## Variants

- CFR+: clips cumulative regrets after each update and commonly uses alternating updates and delayed/linear averaging. It converges much faster empirically but adds convention-sensitive details.
- DCFR discounts positive regrets, negative regrets, and strategy weights with separate schedules. It is effective but easier to implement incorrectly.
- External-sampling MCCFR samples opponent/chance branches while enumerating the updating player's actions. It is unbiased under the paper's estimator, but noisier.
- Outcome-sampling MCCFR samples one trajectory and requires exact importance weights; it has the highest audit risk here.
- Public-chance sampling exploits poker's public-card structure, but needs a correct public/private decomposition.
- Endgame/subgame solving requires reach distributions and, for safety, a gadget or equivalent constraints. A standalone river spot is a complete specified game, not automatically a safe refinement of an upstream blueprint.
- “Spot solving” describes on-demand subgame construction; it is not a distinct convergence theorem.

## Complexity

Full traversal is O(number of histories) per sweep and table storage is O(total information-set actions). This intentionally limits the project to tiny games and compact river spots rather than full no-limit Hold'em.

## Sources

- Zinkevich et al. (2007), CFR: https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- Lanctot et al. (2009), MCCFR: https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html
- Tammelin et al., CFR+: https://arxiv.org/abs/1407.5042
- Brown & Sandholm (2019), DCFR: https://ojs.aaai.org/index.php/AAAI/article/view/4007
- Burch et al., decomposition: https://ojs.aaai.org/index.php/AAAI/article/view/9044
- Brown & Sandholm, safe/nested subgame solving: https://proceedings.neurips.cc/paper/2017/hash/3df1d4b96d8976ff5986393e8767f5b2-Abstract.html
