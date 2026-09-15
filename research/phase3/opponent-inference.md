# Bayesian opponent-range inference from observed actions

## Evidence status

The restricted-tool BryantGPT researcher fetched sources but could not write its report. The parent retained the Bayes/log-space concepts but rejected weak secondary sources and any suggestion of default Laplace smoothing. Smoothing changes the supplied behavioral model and must never be a silent numerical fix.

## Verified references

1. Southey et al., “Bayes' Bluff: Opponent Modelling in Poker” separates uncertainty in game dynamics from uncertainty in opponent strategy and derives posterior inference from observed play: http://poker.cs.ualberta.ca/publications/UAI05.pdf
2. Archival copy of the same paper: https://arxiv.org/pdf/1207.1411
3. Google Research publication record for the same work: https://research.google/pubs/bayes-bluff-opponent-modelling-in-poker/
4. PioSOLVER's range/strategy explanation states that an action-specific range is the prior range weight multiplied by that hand's action probability: https://piosolver.com/docs/viewer/numbers_in_piosolver/
5. Zinkevich et al. define behavioral strategies at information sets in finite imperfect-information games: https://proceedings.neurips.cc/paper/2007/file/08d98638c6fcd194a4b1e6992063e944-Paper.pdf
6. SciPy documents `logsumexp` as stable computation of the logarithm of a sum of exponentials; Phase 3 implements the small needed form with the standard library rather than adding SciPy: https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.logsumexp.html
7. GTO Wizard's blocker article is product-level intuition for card-removal effects, not the numeric oracle: https://blog.gtowizard.com/understanding-blockers-in-poker/

## Meaning and honesty boundary

The inference result is a posterior **conditional on the supplied prior and behavioral likelihood model**. It does not discover an opponent's true cards or prove that the opponent follows the model. If the likelihoods come from an equilibrium strategy, the result is the equilibrium-model posterior; if they come from a nodelock or exploitative profile, it is that model's posterior.

This module updates uncertainty over private holdings. Learning a posterior distribution over an unknown opponent strategy from a database of hands, as in Bayes' Bluff, is a larger statistical task and is not Phase 3 scope.

## Canonical model

Let `H` be the finite set of explicit legal opponent combos after public-card and known-hole-card blockers. Let nonnegative finite source weight `w(h)` define prior mass. At observed public decision `t`, let `a_t` be the observed action and let

`L_t(h) = P_model(a_t | h, public_history_t)`.

Then:

`P(h | a_1,...,a_T) = w(h) * product_t L_t(h) / Z`,

where

`Z = sum_k w(k) * product_t L_t(k)`.

The model must use the information set and legal action tuple corresponding to combo `h` at the exact public history. It may not condition a likelihood on another unobserved private hand. If `Z == 0`, the evidence is impossible under the model and inference fails; it does not return a uniform range.

Weights need not initially sum to one. Multiplying all prior weights by the same positive constant leaves the posterior unchanged.

## Blockers and class aggregation

Blockers are applied before normalization and before likelihood multiplication:

1. remove combos intersecting the public board;
2. remove combos intersecting known hero cards or other declared dead cards;
3. reject duplicate cards/dead cards;
4. require positive remaining prior mass.

Inference operates on explicit combos. A 169-class posterior is obtained afterward by summing child-combo posterior probabilities. Class-level likelihood averaging before applying blockers is generally wrong because compatible combos can have different strategy probabilities.

## Obtaining likelihoods

### Raw solved strategy

At each observation, traverse the declared game to the exact public history for every compatible private combo, obtain that combo's information-state policy, verify the observed action is legal, and set `L_t(h)` to the policy probability of that action.

### Nodelock

If the observed node is locked, the lock's complete probability distribution is the likelihood model. Zero locked probability makes that combo incompatible with the observation.

### Profile

A named profile must first compile to explicit per-node/per-action probabilities or constraints and a resolved strategy. Labels such as `maniac` or `calling-station` are not likelihoods. Inference consumes the resolved probabilities and records the profile ID/version as provenance.

### Caller-supplied likelihood table

A low-level API may accept an explicit probability for each prior combo. It must require exact combo-key coverage, values in `[0,1]`, and no unknown combos. This path enables exact tests and external models without pretending those models are solver outputs.

## Sequential updates

Updating after each observation is equivalent to multiplying all likelihoods once, provided each `L_t` is conditioned on the correct preceding public history:

`posterior_t(h) proportional_to posterior_(t-1)(h) * L_t(h)`.

An action changes the posterior range even though no physical card is removed. A newly revealed board card first blocks incompatible combos, then the next action likelihood is applied. History order is material because later strategy probabilities depend on earlier actions.

## Numerical stability

For long observation sequences, calculate:

`log_mass(h) = log(w(h)) + sum_t log(L_t(h))`.

Zero weight or likelihood maps to negative infinity. Let `m` be the largest finite log mass. Normalize with:

`scaled(h) = exp(log_mass(h) - m)` and

`posterior(h) = scaled(h) / sum_k scaled(k)`.

This is the log-sum-exp shift. If no finite mass exists, evidence is impossible. For a single short update, direct multiplication is acceptable, but both paths must agree within `1e-15` on fixtures. NaN and infinity are always invalid. No epsilon, probability floor, clipping, or Laplace smoothing is applied unless a separately named caller-selected model explicitly requests it; Phase 3's base API has no smoothing option.

## Strict API contract

A version-3 inference request contains exactly:

- `version: 3`;
- `prior`: canonical explicit combo/weight entries;
- `dead_cards`: strict card strings;
- exactly one of:
  - `observations` plus a strict serialized game strategy from which likelihoods are derived, or
  - `likelihood_steps`, each with public-history provenance and a complete combo-to-probability table;
- `output`: `explicit-combos` or `explicit-and-classes`.

A successful response includes:

- `format: "poker-solver-posterior-v1"`;
- normalized explicit combo probabilities in canonical order;
- per-step evidence probability/normalizer;
- removed blocker combos;
- observation history and model provenance;
- optional class sums;
- warning: `conditional_on_supplied_behavior_model`.

Unknown fields, duplicate JSON keys, bool-as-number, incomplete likelihood coverage, illegal observed actions, impossible evidence, zero prior mass, overlapping cards, and unresolvable game nodes fail with status 2. The engine must not expose Python `repr` as a new public node identifier.

## Exact validation fixtures

Unless stated otherwise, absolute tolerance is `1e-15`.

1. **Manual Bayes:** prior `(h1=1/4, h2=3/4)`, likelihood `(1, 1/3)`. Unnormalized masses are `(1/4,1/4)`, evidence probability `1/2`, posterior `(1/2,1/2)`.
2. **Zero likelihood:** prior `(1/2,1/2)`, likelihood `(0,1)` gives posterior `(0,1)`, not an error.
3. **Impossible evidence:** all likelihoods zero raises a specific impossible-evidence error.
4. **Sequential identity:** prior `(1/2,1/2)`; step 1 `(4/5,1/5)` gives `(4/5,1/5)`; step 2 `(1/4,1)` produces equal unnormalized mass `(1/5,1/5)` and posterior `(1/2,1/2)`. One-pass products must match exactly in rational oracle code and within tolerance in floats.
5. **Prior scale:** replacing weights `(1,3)` with `(10,30)` cannot change posterior bytes after canonical float serialization.
6. **No observations:** output is the blocker-filtered normalized prior.
7. **Underflow:** equal priors with two likelihood steps of `1e-200` for both hands must return `(1/2,1/2)` via log space rather than impossible evidence.
8. **Asymmetric underflow:** log masses differing by `log(2)` produce posterior `(1/3,2/3)` even when their raw products underflow.
9. **Blocker oracle:** with hero `AsKd` and opponent range `AA,AKs,AKo`, exactly 12 explicit combos survive as enumerated in `ranges-display.md`; posterior normalization uses only those 12.
10. **Action split identity:** for every hand, prior mass times raw strategy action probability equals the unnormalized posterior mass reported for that action, matching source 4.
11. **Class reduction:** summed explicit posterior equals 1; class sums equal explicit child sums and also total 1.
12. **Strategy integration:** on a tiny game, deriving likelihoods from raw policies must equal the low-level explicit likelihood-table result within `1e-15`.
13. **Information noninterference:** swapping an unobserved opponent card can select a different opponent policy row only through the opponent's own information key; it cannot alter another actor's information key at the same public history.
14. **Permutation determinism:** permuting input combo or likelihood-table order cannot change canonical output.

## Relationship to exploitative solving

Inference itself does not alter a strategy or solve a game. A caller may use the posterior as a new opponent range for a subsequent bounded solve. That second solve must record the posterior/model provenance and remains exploitable if the behavioral model is wrong. Nodelocking and profiles constrain or generate policies; Bayes conditions range mass on observed actions; these operations are related but not interchangeable.

## Scope matrix

| Capability | Phase 3 disposition |
|---|---|
| Exact combo posterior from prior and action likelihoods | Implement |
| Sequential public-history updates | Implement |
| Board/known-card blocker conditioning | Implement |
| Raw strategy, nodelock, and resolved-profile likelihood sources | Implement for bounded trees |
| Log-space normalization | Implement with standard library |
| Explicit and 169-class output | Implement |
| Learning an unknown strategy posterior across hands | Documented boundary |
| Neural opponent modeling | Documented boundary |
| Claiming real-opponent truth from a supplied model | Explicitly forbidden |

Every implementation sub-batch requires a fresh non-author audit under `review/phase3/` before the next feature batch starts.
