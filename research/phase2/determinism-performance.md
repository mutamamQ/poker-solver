# Determinism and performance

## Reproducibility contract

Vanilla CFR is deterministic under stable traversal. External-sampling MCCFR owns a dedicated `random.Random(seed)` object; the seed is required in API/CLI output. Stable action/chance ordering and sorted-key compact JSON make two runs with the same interpreter, input, seed, and iteration count byte-identical. Cross-platform floating-point byte identity is not claimed without an RFC 8785-compatible number serializer; numerical agreement uses explicit tolerances.

Python documents `Random` instances as deterministic pseudorandom generators independent of the module-global instance. JSON sorted keys are sufficient for the local regression contract but are not a claim of full RFC 8785 conformance.

## Safe optimizations

- pass reach probabilities incrementally down traversal;
- cache immutable `child(action)` transitions where profiling proves benefit;
- cache seven-card ranks keyed by canonical seven-card tuple;
- precompute legal deal/runout lists and cumulative chance probabilities;
- store only reached MCCFR information sets;
- use stable summation order.

Do not clip vanilla regrets, cap values, replace NaNs, use lossy 16-bit tables, or add abstractions as silent performance fixes. CFR+, discounted CFR, pruning, suit isomorphism, and hand/action abstraction are separate algorithms requiring separate tests and output labels.

## Scaling

Full-tree work is proportional to histories visited per iteration. Starting at a flop with fixed private cards still exposes up to 45 turn and 44 river cards before betting branches; range pairs multiply that tree. Published no-limit game-size work confirms that unrestricted solving requires abstraction. Phase 2 therefore offers exact finite spots, vanilla reference solves only when tractable, and sampled fast solves for larger trees. It does not claim commercial full-game throughput.

## Determinism and benchmark gates

- Canonical JSON from identical MCCFR runs must hash identically locally.
- A seed change must be accepted and usually changes the trajectory; correctness is based on metrics, not difference itself.
- Benchmark a fixed tiny multi-street fixture after a warm-up, taking the median of at least three runs.
- Set the CI ceiling from a measured parent baseline with generous noise margin (at least 3x baseline), not an invented industry number.
- Benchmark tests assert completion and a coarse ceiling; algorithmic accuracy is checked separately.

## Sources

- Python random: https://docs.python.org/3/library/random.html
- RFC 8785 JSON canonicalization: https://datatracker.ietf.org/doc/rfc8785/
- Original CFR: https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- MCCFR: https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html
- CFR+: https://arxiv.org/abs/1407.5042
- Discounted CFR: https://ojs.aaai.org/index.php/AAAI/article/view/4007
- No-limit game size: https://arxiv.org/abs/1302.7008
- Accelerated/public-tree BR and isomorphism: https://www.ijcai.org/Proceedings/11/Papers/054.pdf

## Parent corrections

Unsupported street-size/runtime tables, arbitrary regret clipping, and universal cache/isomorphism factors from the subagent draft were removed.