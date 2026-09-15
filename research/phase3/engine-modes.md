# Engine modes: Classic versus Fast / DDLS

## Evidence status

This report separates public GTO Wizard product semantics from the correctness contract for this repository. The initial tool-enabled and restricted-tool BryantGPT attempts both failed before tool execution. A tool-free BryantGPT draft was therefore treated only as design input. The parent fetched the sources below and removed unsupported claims from that draft, including invented fixed exploitability targets, solve times, training-set sizes, and a nonexistent `classic-vs-fast-solver` URL.

## Product semantics

GTO Wizard's February 2026 multiway-preflop article defines two engine modes:

- **Classic** is its standard street-by-street mode: it solves one street at a time.
- **Fast** looks only a few moves ahead and resolves repeatedly within a street. GTO Wizard calls this Dynamic-Depth-Limited Solving (DDLS).
- The same article says Fast depends more on neural-network approximations, while Classic relies more on search; consequently Fast has a higher degree of approximation.
- GTO Wizard's AI explainer says learned expected values replace computation of future streets. Those values are trained through self-play.

These statements do **not** imply that Classic traverses an unabstracted game from the current node to the end of the hand. GTO Wizard expressly describes its AI mode as solving one street at a time and using learned continuation values. In this repository, therefore, `classic` means an exact full traversal of the **declared finite model**, not exact unrestricted Hold'em and not a claim to reproduce GTO Wizard's private engine.

Primary product sources:

1. GTO Wizard, “GTO Wizard AI Custom Multiway Solving” (2026): https://blog.gtowizard.com/gto-wizard-ai-custom-multiway-solving/
2. GTO Wizard, “GTO Wizard AI Explained” (2023, subsequently updated): https://blog.gtowizard.com/gto-wizard-ai-explained/
3. GTO Wizard, “GTO Wizard AI Custom Multiway Solving” section “Dynamic-Depth-Limited Solving (Fast Mode)”: same URL as source 1.

## Independent algorithmic references

4. Zinkevich et al., “Regret Minimization in Games with Incomplete Information” (NeurIPS 2007): https://proceedings.neurips.cc/paper/2007/file/08d98638c6fcd194a4b1e6992063e944-Paper.pdf
5. Moravčík et al., “DeepStack: Expert-level artificial intelligence in heads-up no-limit poker” (Science 2017): https://www.science.org/doi/10.1126/science.aam6960
6. Brown, Sandholm, and Amos, “Depth-Limited Solving for Imperfect-Information Games” (NeurIPS 2018): https://proceedings.neurips.cc/paper/2018/hash/34306d99c63613fad5b2a140398c0420-Abstract.html
7. Brown and Sandholm, “Safe and Nested Subgame Solving for Imperfect-Information Games” (NeurIPS 2017): https://proceedings.neurips.cc/paper/2017/hash/3df1d4b96d8976ff5986393e8767f5b2-Abstract.html

The parent fetched sources 1, 2, 4, 5, and the paper PDF linked by source 6. Source 4 establishes CFR for finite extensive-form games and its equilibrium relationship in the two-player zero-sum setting. Source 5 explains depth truncation with learned approximate continuation values. Source 6 is important because it shows that a single scalar “state value” is generally insufficient at an imperfect-information depth boundary: continuation treatment must preserve strategic uncertainty, for example through opponent continuation strategies or counterfactual values.

## Correctness contract for this repository

### `classic`

`classic` is a presentation-level engine mode over the existing exact finite-tree solver:

1. The complete configured chance and action tree is traversed to every terminal state; no depth cutoff or learned leaf evaluator is used.
2. All legal actions are from the declared finite action abstraction. “Full” refers to this configured tree only.
3. Heads-up zero-sum outputs report exact-tree expected values and NashConv against an infoset-consistent best response.
4. Iteration count is explicit. The backend does not claim convergence merely because a fixed iteration budget elapsed.
5. The output includes `engine_mode: "classic"`, the solver algorithm, configured tree limits, iteration count, values, and measured NashConv where the metric is supported.
6. Deterministic full-tree CFR remains byte-repeatable for the same input and interpreter. Seeded MCCFR remains a stochastic solver algorithm, not a distinct Fast/DDLS mode.

A bounded finite model can be solved exactly with respect to traversal and payoff accounting while its iterative strategy is still only an approximate equilibrium. Documentation and JSON must preserve that distinction.

### `fast-ddls`

Faithful GTO Wizard Fast/DDLS parity is a **documented boundary** in Phase 3:

- No trained neural continuation-value model or verified training corpus ships with this dependency-free project.
- A cutoff plus showdown equity is not equivalent to a strategic continuation value. It ignores future betting, information revelation, and range-dependent responses.
- A cutoff plus the value of one fixed blueprint can be useful, but accuracy is conditional on that blueprint and is not a general equilibrium guarantee.
- The NeurIPS 2018 depth-limited-solving result cautions that ordinary state-value substitution is not sufficient in imperfect-information games.

The API must reject `engine_mode: "fast-ddls"` with a stable documented-boundary error unless a future implementation names and validates its continuation model. It must not silently route Fast to MCCFR or to Classic.

### Working bounded approximation

The only acceptable Phase 3 approximation is explicitly named `depth-limited-equity-rollout`, never `fast` or `ddls`:

1. Traverse the declared game to a caller-specified public depth boundary.
2. At each cutoff, enumerate legal remaining board runouts exactly and compute showdown equity for each compatible private deal.
3. Convert that equity to a terminal utility under an explicit **no-further-betting** continuation assumption.
4. Tag every result with:
   - `engine_mode: "depth-limited-equity-rollout"`;
   - `approximation: true`;
   - cutoff definition;
   - `continuation_model: "checkdown-equity"`;
   - a warning that there is no unrestricted-game exploitability guarantee.
5. Do not report exact-tree NashConv for the original untruncated game. NashConv may be reported only for the induced truncated game and must be labeled as such.

This approximation is useful as a working, testable boundary artifact. No universal numeric error bound is claimed. Its observed error is fixture-specific and must be reported by comparison with Classic on instances where Classic is tractable.

## Acceptance tests and independent oracles

All comparisons use `abs(actual - expected) <= 1e-12` unless a test explicitly documents a looser iterative convergence tolerance.

1. **Classic equals legacy exact tree.** On Kuhn and the existing tiny river/multistreet fixtures, `classic` must produce the same strategy serialization, values, and NashConv as direct `CFRSolver` for the same iterations. Deterministic fields must be byte-identical.
2. **No-cutoff identity.** A depth-limited evaluator whose boundary is at or below every terminal must equal Classic exactly. This checks traversal plumbing without relying on a heuristic.
3. **Checkdown identity.** On a game where all future nodes have only `CHECK`/chance actions, `depth-limited-equity-rollout` at the start of the remaining streets must equal exact Classic value within `1e-12`.
4. **Heuristic counterexample.** Ship a tiny game with a strategically meaningful future bet where checkdown equity and exact continuation value differ. The test proves that the approximation is not mislabeled as exact or Fast parity.
5. **Unsupported Fast fails closed.** Strict JSON and CLI requests for `fast-ddls` return validation/usage status 2 and a stable message explaining that trained continuation values are not shipped. Unknown mode names and booleans also fail.
6. **Metadata honesty.** Classic has `approximation: false`; equity rollout has `approximation: true`; unsupported Fast never emits a result object.
7. **Monotonicity is not required.** Tests must not assert per-iteration monotonic NashConv for vanilla CFR; regret guarantees concern averages/rates, not monotonic improvement at every finite iteration.
8. **Cross-module preservation.** Existing Phase 1 and 2 solve requests, which omit `engine_mode`, retain their previous schema and behavior. A new Phase 3 endpoint may default explicitly to Classic, but old endpoints may not gain output fields silently.

## Feasibility and scope matrix

| Capability | Phase 3 disposition | Accuracy claim |
|---|---|---|
| Full traversal of a declared finite tree | Implement as `classic` | Exact traversal/payoffs; iterative strategy quality measured by supported NashConv |
| GTO Wizard Classic proprietary behavior | Documented external product | No implementation-parity claim |
| Seeded external-sampling MCCFR | Already implemented solver algorithm | Not Fast/DDLS |
| GTO Wizard Fast/DDLS with learned continuation values | Documented boundary; reject explicitly | Not implemented |
| Neural value training/inference | Tier 3 research boundary | Not implemented |
| Checkdown-equity depth-limited rollout | Bounded working approximation | Exact only for the induced checkdown model; no general error bound |
| Unrestricted NLHE or multiway Nash-distance guarantee | Boundary | Not claimed |

## Implementation guidance

Keep engine mode separate from solver algorithm. A suitable strict schema has two orthogonal fields: `engine_mode` (`classic` or the explicitly heuristic rollout) and `algorithm` (`vanilla-cfr` or `external-sampling-mccfr` where valid). This prevents the common but incorrect mapping “MCCFR = Fast.” Reject unsupported combinations rather than coercing them. The architecture document must retain the product/implementation distinction above.
