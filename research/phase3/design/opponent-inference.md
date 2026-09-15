# Phase 3 Design: Bayesian opponent-range inference

## 1. Purpose and scope

This module implements exact Bayesian posterior inference over an opponent's private holdings, conditioning a prior combo-weighted range on observed public actions through a supplied behavioral likelihood model.

**In scope:**

- Blocker-first combo filtering (board, known hero cards, declared dead cards).
- Sequential likelihood multiplication from observed actions at public decision nodes.
- Log-space stable normalization for long observation sequences.
- Multiple likelihood-provenance paths: raw solved strategy, exact nodelocks, resolved profiles, and caller-supplied explicit tables.
- Explicit-combo and 169-class posterior output.
- Strict versioned JSON API with complete provenance metadata.
- Manual exact rational/float fixtures with stated absolute tolerances.

**Documented boundaries:**

- Learning an unknown opponent strategy posterior across a database of hands (Bayes' Bluff scope).
- Neural opponent modeling.
- Claiming real-opponent ground truth from a supplied behavioral model.
- Automatic Laplace smoothing, probability floors, epsilon clipping, or other silent numerical fixes.

## 2. Canonical inference model

### 2.1 Notation

Let `H` be the finite set of explicit legal opponent combos after public-card and known-hole-card blockers have been applied.

Let nonnegative finite source weight `w(h)` define prior mass for each `h ∈ H`. Weights need not sum to one; multiplying all weights by the same positive constant leaves the posterior unchanged.

At observed public decision `t`, let `a_t` be the observed action and let

```
L_t(h) = P_model(a_t | h, public_history_t)
```

be the behavioral likelihood: the probability that the model assigns to action `a_t` when the opponent holds combo `h` at the exact public history preceding observation `t`.

### 2.2 Posterior formula

The posterior probability after `T` sequential observations is:

```
P(h | a_1, ..., a_T) = w(h) * ∏_{t=1}^{T} L_t(h) / Z
```

where the evidence normalizer is:

```
Z = ∑_{k ∈ H} w(k) * ∏_{t=1}^{T} L_t(k)
```

### 2.3 Zero-evidence behavior

If `Z == 0`, the observed action sequence is impossible under the supplied prior and likelihood model. Inference **fails with a specific impossible-evidence error**. It does not return a uniform range, apply smoothing, or invent probability mass.

### 2.4 Sequential update equivalence

Updating after each observation is equivalent to multiplying all likelihoods once, provided each `L_t` is conditioned on the correct preceding public history:

```
posterior_t(h) ∝ posterior_{t-1}(h) * L_t(h)
```

An action changes the posterior range even though no physical card is removed. A newly revealed board card first blocks incompatible combos, then the next action likelihood is applied. History order is material because later strategy probabilities depend on earlier actions.

## 3. Blocker-first combo filtering

### 3.1 Filtering order

Blockers are applied **before normalization** and **before likelihood multiplication**:

1. Remove combos intersecting the public board.
2. Remove combos intersecting known hero cards or other declared dead cards.
3. Reject duplicate cards and dead cards.
4. Require positive remaining prior mass.

### 3.2 Explicit combos only

Inference operates on explicit combos. A 169-class posterior is obtained **afterward** by summing child-combo posterior probabilities. Class-level likelihood averaging before applying blockers is generally wrong because compatible combos within a class can have different strategy probabilities.

### 3.3 Exact blocker fixture

With hero `AsKd` and opponent range `AA,AKs,AKo`, exactly **12 explicit combos** survive:

- `AA`: 3 combos (AcAh, AcAd, AhAd — As blocked)
- `AKs`: 2 combos (AcKc, AhKh — As/Kd blocked)
- `AKo`: 7 combos (AcKh, AhKc, AcKs, AhKs, AdKc, AdKh, AdKs — As/Kd blocked)
- **Total: 12 combos**

Posterior normalization uses only these 12. This fixture is cross-referenced in `research/phase3/ranges-display.md` and must be independently enumerated in tests.

## 4. Likelihood provenance

### 4.1 Raw solved strategy

At each observation, traverse the declared game to the exact public history for every compatible private combo, obtain that combo's information-state policy via `GameState.information_state_key(player)`, verify the observed action is legal, and set `L_t(h)` to the policy probability of that action.

The model must use the information set and legal action tuple corresponding to combo `h` at the exact public history. It may not condition a likelihood on another unobserved private hand.

### 4.2 Nodelock

If the observed node is locked (per `research/phase3/nodelock-profiles.md`), the lock's complete probability distribution is the likelihood model. Zero locked probability makes that combo incompatible with the observation.

A nodelock is keyed by `InfoKey` (not a physical private-history occurrence) and applies uniformly across all hidden histories in that information set.

### 4.3 Profile

A named profile must first compile to explicit per-node/per-action probabilities or constraints and a resolved strategy (per `research/phase3/nodelock-profiles.md` shaped-game solution). Labels such as `maniac` or `calling-station` are not likelihoods. Inference consumes the resolved probabilities and records the profile ID/version as provenance.

### 4.4 Caller-supplied likelihood table

A low-level API may accept an explicit probability for each prior combo. It must require:

- Exact combo-key coverage (every combo in the filtered prior has exactly one likelihood entry).
- Values in `[0, 1]`.
- No unknown combos.

This path enables exact tests and external models without pretending those models are solver outputs.

## 5. Numerical stability: log-space Bayes

### 5.1 Log-space normalization

For long observation sequences, calculate:

```
log_mass(h) = log(w(h)) + ∑_t log(L_t(h))
```

Zero weight or likelihood maps to negative infinity. Let `m` be the largest finite log mass. Normalize with:

```
scaled(h) = exp(log_mass(h) - m)
posterior(h) = scaled(h) / ∑_{k ∈ H} scaled(k)
```

This is the standard log-sum-exp shift. If no finite mass exists, evidence is impossible.

### 5.2 Direct multiplication path

For a single short update, direct multiplication is acceptable:

```
unnormalized(h) = w(h) * L(h)
posterior(h) = unnormalized(h) / ∑_k unnormalized(k)
```

Both paths must agree within `1e-15` on fixtures.

### 5.3 Forbidden numerical fixes

NaN and infinity are always invalid. **No epsilon, probability floor, clipping, or Laplace smoothing is applied** unless a separately named caller-selected model explicitly requests it. Phase 3's base API has **no smoothing option**.

Smoothing changes the supplied behavioral model and must never be a silent numerical fix.

## 6. Strict API contract

### 6.1 Request format

A version-3 inference request contains exactly:

```json
{
  "version": 3,
  "prior": [
    {"cards": ["As", "Kd"], "weight": 1.0},
    ...
  ],
  "dead_cards": ["2c", "3h"],
  "observations": [
    {
      "public_history": "...",
      "observed_action": {"kind": "bet", "amount": 100},
      "likelihood_source": {"type": "strategy", "strategy_id": "..."}
    },
    ...
  ],
  "output": "explicit-combos"  // or "explicit-and-classes"
}
```

Alternatively, for low-level explicit likelihoods:

```json
{
  "version": 3,
  "prior": [...],
  "dead_cards": [...],
  "likelihood_steps": [
    {
      "public_history": "...",
      "observed_action": {"kind": "bet", "amount": 100},
      "likelihoods": {
        "AsKd": 0.75,
        "AcKc": 0.50,
        ...
      }
    },
    ...
  ],
  "output": "explicit-combos"
}
```

### 6.2 Response format

A successful response includes:

```json
{
  "format": "poker-solver-posterior-v1",
  "posterior": [
    {"cards": ["As", "Kd"], "probability": 0.123},
    ...
  ],
  "evidence_probability": 0.456,
  "per_step_evidence": [0.8, 0.57],
  "blocked_combos": [
    {"cards": ["As", "Ad"], "reason": "board_overlap"},
    ...
  ],
  "observation_history": [
    {"public_history": "...", "action": {...}, "source": "strategy:abc123"},
    ...
  ],
  "classes": [
    {"class": "AA", "probability": 0.05},
    ...
  ],
  "warning": "conditional_on_supplied_behavior_model"
}
```

### 6.3 Validation and errors

Unknown fields, duplicate JSON keys, bool-as-number, incomplete likelihood coverage, illegal observed actions, impossible evidence, zero prior mass, overlapping cards, and unresolvable game nodes fail with **exit status 2**.

The engine must not expose Python `repr` as a new public node identifier.

## 7. Exact validation fixtures

Unless stated otherwise, absolute tolerance is **`1e-15`**.

1. **Manual Bayes:** prior `(h1=1/4, h2=3/4)`, likelihood `(1, 1/3)`. Unnormalized masses are `(1/4, 1/12)`, evidence probability `1/3`, posterior `(3/4, 1/4)`.

2. **Zero likelihood:** prior `(1/2, 1/2)`, likelihood `(0, 1)` gives posterior `(0, 1)`, not an error.

3. **Impossible evidence:** all likelihoods zero raises a specific impossible-evidence error.

4. **Sequential identity:** prior `(1/2, 1/2)`; step 1 `(4/5, 1/5)` gives `(4/5, 1/5)`; step 2 `(1/4, 1)` produces equal unnormalized mass `(1/5, 1/5)` and posterior `(1/2, 1/2)`. One-pass products must match exactly in rational oracle code and within tolerance in floats.

5. **Prior scale:** replacing weights `(1, 3)` with `(10, 30)` cannot change posterior bytes after canonical float serialization.

6. **No observations:** output is the blocker-filtered normalized prior.

7. **Underflow:** equal priors with two likelihood steps of `1e-200` for both hands must return `(1/2, 1/2)` via log space rather than impossible evidence.

8. **Asymmetric underflow:** log masses differing by `log(2)` produce posterior `(1/3, 2/3)` even when their raw products underflow.

9. **Blocker oracle:** with hero `AsKd` and opponent range `AA,AKs,AKo`, exactly 12 explicit combos survive as enumerated in section 3.3; posterior normalization uses only those 12.

10. **Action split identity:** for every hand, prior mass times raw strategy action probability equals the unnormalized posterior mass reported for that action, matching PioSOLVER source 4 in `research/phase3/opponent-inference.md`.

11. **Class reduction:** summed explicit posterior equals 1; class sums equal explicit child sums and also total 1.

12. **Strategy integration:** on a tiny game, deriving likelihoods from raw policies must equal the low-level explicit likelihood-table result within `1e-15`.

13. **Information noninterference:** swapping an unobserved opponent card can select a different opponent policy row only through the opponent's own information key; it cannot alter another actor's information key at the same public history.

14. **Permutation determinism:** permuting input combo or likelihood-table order cannot change canonical output.

## 8. Privacy and noninterference

### 8.1 Information-set semantics

The likelihood model for combo `h` at public history `t` is derived from `GameState.information_state_key(opponent_player)` for that combo. Per `ARCHITECTURE.md` section 3, an information key "omits hidden opponent information and preserves the acting player's observations/actions."

Swapping an unobserved opponent card can select a different opponent policy row **only through the opponent's own information key**; it cannot alter another actor's information key at the same public history (fixture 13).

### 8.2 No hidden-information leakage

Inference must not condition a likelihood on another unobserved private hand. The model evaluates `P(action | own_combo, public_history)`, never `P(action | own_combo, hidden_hero_combo, public_history)`.

### 8.3 Boundary with exploitative solving

Inference itself does not alter a strategy or solve a game. A caller may use the posterior as a new opponent range for a subsequent bounded solve. That second solve must record the posterior/model provenance and remains exploitable if the behavioral model is wrong.

Nodelocking and profiles constrain or generate policies; Bayes conditions range mass on observed actions; these operations are related but not interchangeable.

## 9. Implementation boundaries

### 9.1 Module interface

The inference module exposes:

```python
from poker_solver.opponent_inference import (
    infer_posterior,
    InferenceRequest,
    InferenceResult,
    ImpossibleEvidenceError,
)
```

### 9.2 Integration with existing types

- `WeightedCombo` from `equity.py` is the prior combo representation.
- `Action` from `model.py` is the observed-action identity.
- `InfoKey` from `model.py` is the likelihood-source key.
- `Strategy` from `model.py` is the raw-policy likelihood source.

### 9.3 CLI and JSON

The CLI exposes:

```bash
poker-solver infer-opponent CONFIG.json --json
```

Successful JSON is sorted and contains deterministic fields only. Errors go to stderr; exit 2 is invalid input/config, exit 1 an internal runtime failure.

### 9.4 Testing and review gates

Every implementation sub-batch requires a fresh non-author audit under `review/phase3/` before the next feature batch starts. All 14 exact fixtures must pass with stated tolerances. The baseline 185 tests must remain green.

## 10. References

1. Southey et al., "Bayes' Bluff: Opponent Modelling in Poker": http://poker.cs.ualberta.ca/publications/UAI05.pdf
2. PioSOLVER range/strategy explanation: https://piosolver.com/docs/viewer/numbers_in_piosolver/
3. Zinkevich et al., CFR behavioral strategies: https://proceedings.neurips.cc/paper/2007/file/08d98638c6fcd194a4b1e6992063e944-Paper.pdf
4. SciPy `logsumexp` documentation: https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.logsumexp.html (Phase 3 implements the needed form with standard library rather than adding SciPy)
5. Repository `research/phase3/opponent-inference.md` for full evidence provenance.
6. Repository `research/phase3/nodelock-profiles.md` for nodelock and profile semantics.
7. Repository `research/phase3/ranges-display.md` for blocker fixture and combo enumeration.
8. Repository `ARCHITECTURE.md` for `GameState`, `InfoKey`, `Strategy`, and `WeightedCombo` contracts.

## 11. Meaning and honesty boundary

The inference result is a posterior **conditional on the supplied prior and behavioral likelihood model**. It does not discover an opponent's true cards or prove that the opponent follows the model.

If the likelihoods come from an equilibrium strategy, the result is the equilibrium-model posterior; if they come from a nodelock or exploitative profile, it is that model's posterior.

This module updates uncertainty over private holdings. Learning a posterior distribution over an unknown opponent strategy from a database of hands, as in Bayes' Bluff, is a larger statistical task and is not Phase 3 scope.
