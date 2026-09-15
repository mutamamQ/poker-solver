# Multiway scope: bounded three-way postflop and nine-way preflop boundary

## Evidence status and critical corrections

The initial and restricted-tool BryantGPT attempts failed before tool execution; a tool-free draft was used only as adversarial input. Parent verification rejected its central game-theory claim and all invented performance/size estimates:

- Chip-EV poker with all players included is constant/zero-sum when no operator rake is removed. It is not general-sum merely because there are more than two players.
- Nevertheless, the two-player zero-sum convergence theorem for CFR does **not** extend to arbitrary three-player poker. CFR may perform well empirically, but its average behavioral profile has no general Nash-convergence guarantee in multiplayer games.
- “Exploitability” is not a coalition response. The relevant finite-game certificate here is generalized NashConv: sum of each player's unilateral best-response improvement while every other player's strategy is fixed.
- Pluribus is not an open-source oracle, and an unofficial reconstruction cannot establish agreement with it.
- Rake is not assumed to come only from the main pot.
- The draft's infoset/iteration/CPU/memory counts and tolerances had no executable derivation and are discarded.

## Verified sources

1. GTO Wizard's three-way postflop release describes product support for custom ranges, mixed stacks, arbitrary sizes, side pots, rake, bunching, and nodelocking: https://blog.gtowizard.com/now_live_3_way_solving_nodelocking_2_0_and_50k_icm_ft_sims/
2. GTO Wizard's multiway preflop release documents product support up to nine players and lists antes, straddles, stacks, limps/cold calls, rake, locks, and profiles: https://blog.gtowizard.com/introducing-multiway-preflop-solving/
3. Zinkevich et al. prove CFR's equilibrium relationship for two-player zero-sum finite extensive-form games, not a blanket multiplayer theorem: https://proceedings.neurips.cc/paper/2007/file/08d98638c6fcd194a4b1e6992063e944-Paper.pdf
4. Gibson, Burch, Lanctot, and Szafron analyze regret minimization outside two-player zero-sum games and emphasize that the strong guarantees are lost: https://arxiv.org/pdf/1305.0034
5. Ganzfried summarizes the lack of general CFR Nash-convergence guarantees in multiplayer games and reports a three-player Leduc counterexample: https://arxiv.org/html/2001.11165
6. Brown and Sandholm's Pluribus paper establishes strong empirical six-player play; it is evidence of feasibility with specialized methods, not an exact strategy oracle for this repository: https://www.science.org/doi/10.1126/science.aay2400
7. OpenSpiel supplies n-player extensive-game infrastructure and games suitable for independent tiny-game cross-checks: https://github.com/google-deepmind/open_spiel
8. OpenSpiel framework paper: https://arxiv.org/abs/1908.09453

## Scope decision

### Implemented target: bounded three-way postflop

Phase 3 should implement a dependency-free, explicit-range three-player Hold'em game with:

- starting street `flop`, `turn`, or `river`;
- exactly three seats and a declared button/action order;
- explicit combo-weighted private ranges;
- a fixed public starting board and an explicit finite runout list for non-river starts;
- integer stacks, previous contributions, and current pot ledger;
- finite configured raise-to targets;
- fold/check/call/raise/all-in legality, short all-ins, action reopening, and round closure;
- unequal stacks, main/side-pot layers, ties, and a declared odd-chip rule;
- no rake in the first multiway core batch, followed by composition with the separately verified rake module;
- full-tree N-player CFR as an empirical regret minimizer and a seeded sampling variant only if independently audited;
- exact generalized NashConv certification on tiny trees by exhaustive infoset-consistent unilateral best responses.

“Correct” means exact rules, chance mass, information partition, payoff accounting, regret equations, and measured unilateral-deviation certificate for the declared finite tree. It does not mean that CFR is guaranteed to find a Nash equilibrium for every three-player input.

### Documented boundary: up to nine-way preflop

A configuration model may represent up to nine seats and forced-bet structure, but Phase 3 does not claim strategic solving at that scale. The joint explicit deal space, public action branching, asymmetric stacks, and imperfect-information strategy space grow combinatorially. GTO Wizard reports a proprietary hybrid CFR/neural engine trained through massive self-play; this repository ships neither those value networks nor that corpus.

No imperfect-recall hand bucketing is introduced merely to claim scale. A 169-class preflop abstraction is not automatically sound in multiway games because suit-specific blockers and card removal couple players' ranges. Nine-way strategic solving, neural continuation values, and distributed training remain documented Tier 3 boundaries.

## N-player protocol

Do not mutate the established two-player `GameState` semantics in place. Add a sibling protocol:

- `num_players() -> int`;
- `current_player() -> CHANCE | TERMINAL | player index`;
- `legal_actions()`;
- `chance_outcomes()`;
- `child(action)`;
- `information_state_key(player)`;
- `returns() -> tuple[float, ...]` of length `num_players`.

Generic N-player audit/expected-value/CFR/BR code uses this protocol. Existing two-player APIs and return shapes stay untouched. An adapter may allow two-player games to use N-player utilities, but old serialized output cannot change.

## Three-way immutable state

The state must carry at least:

- three private combos or `None` before chance deal;
- board and street;
- button and acting seat;
- per-seat status: active, folded, or all-in;
- per-seat remaining stack;
- per-seat current-street commitment;
- per-seat total contribution from the declared payoff baseline;
- pot carried from closed streets/dead money;
- current highest commitment, last full-raise increment, and which active seats still owe action;
- complete public action/street history including actor identity;
- terminal reason and rules/tree identity.

Actor identity and folded seats are public and cannot be omitted from the information key. The acting player's key includes their own cards and all public fields needed to determine legal actions and payoffs, while excluding every other private combo and unobserved runout. Histories sharing a key must have the same ordered actions.

## Chance and private deals

Root chance enumerates every compatible ordered triple `(h0,h1,h2)` with mass `w0*w1*w2`, excludes board/card collisions and zero-weight entries, then normalizes once. Non-river chance enumerates only declared legal runout continuations compatible with all private cards and prior board cards. Chance probabilities must be finite, nonnegative, deterministic in order, and sum to one within `1e-12`.

Bunching from previously folded ranges is not implemented unless those folded players were explicitly represented at root chance. Labeling ordinary three-player blocker conditioning as full bunching parity is forbidden.

## Action order and betting-round closure

Postflop, action begins with the first active, non-all-in seat clockwise after the button. After an action, advance clockwise to the next active seat that still owes action. A round closes only when every nonfolded, non-all-in player has either matched the highest live commitment or checked after the last full raise and no action is owed.

A full raise updates the minimum raise increment and reopens action to players entitled under the declared no-limit rules. A short all-in may increase the call target without reopening raising for players who already acted. If only one nonfolded player remains, terminate immediately and award all contributed chips after any explicit rake rule. If multiple players remain but no further decisions are possible, deal the declared runout to showdown.

Preflop order belongs to the separate preflop module: normally first active seat clockwise after the big blind/last live straddle, with the blinds retaining action when it returns. The rejected draft's “SB → BB → button” rule was wrong.

## Pot layers and awards

At terminal showdown, use total contributions `c_i` including folded players. Sort distinct positive contribution levels. For each level `L` above previous level `p`:

`layer_amount = (L-p) * count(i where c_i >= L)`.

Eligible contenders are nonfolded players with `c_i >= L`. Award that layer to the strongest eligible hand(s). A layer with one eligible contributor is returned/awarded to that contributor, covering unmatched excess deterministically. Folded contributions remain in layer amounts but folded players can never win.

Each layer is split independently among tied winners. Phase 3's explicit odd-chip policy is: distribute indivisible one-chip remainders one at a time to tied winners in clockwise seat order beginning immediately left of the button. This is a project rule recorded in config/metadata; house-rule universality is not claimed.

For no-rake chip EV, let `initial_wealth_i` be the stack at the chosen baseline and let terminal wealth include uncommitted stack plus awards. Return `terminal_wealth_i - initial_wealth_i`. Therefore `sum_i returns_i == 0` exactly. If operator rake `r` is removed and the operator is not a modeled player, `sum_i returns_i == -r`.

Dead blinds/antes are player contributions. They do not create a conservation deficit when the payoff baseline includes pre-posting wealth.

## N-player CFR and certification

For updating player `i`, counterfactual reach at an information set is chance reach multiplied by every other player's reach:

`pi_-i = pi_chance * product(j != i, pi_j)`.

Regret deltas are `pi_-i * (v_i(I,a)-v_i(I))`. Average strategy accumulation uses player `i`'s own reach under one clearly documented averaging convention. Synchronous full-tree iterations freeze the profile before traversals to avoid branch-order dependence.

This correctly implements regret updates but does not create a universal multiplayer Nash guarantee. Results must report:

- algorithm and iterations;
- expected value for all three players;
- whether exact unilateral best responses were computed;
- generalized NashConv `sum_i (BR_i(sigma_-i)-u_i(sigma))` where available;
- no `half_nash_conv` or two-player “exploitability” label.

For tiny trees, enumerate one action per responder infoset and evaluate it against all other fixed behavioral policies. Generalized NashConv is nonnegative and is zero exactly when no player can profitably deviate, subject to exact enumeration/numeric tolerance. Larger trees for which exact BR is unavailable are labeled uncertified rather than assigned a sampled “exploitability” number.

## Independent oracles and acceptance tests

Default arithmetic tolerance is `1e-12`; integer chip ledgers and action targets compare exactly.

1. **Pot-layer table oracle:** hand-written contribution/status/strength fixtures cover equal contributions, one and two side pots, folded dead money, unmatched excess, two-way and three-way ties, and odd chips. Compare exact layer membership and awards.
2. **Conservation:** exhaustively traverse each tiny game; no-rake terminal returns sum exactly to zero. With rake, player returns plus operator rake sum to zero.
3. **Permutation symmetry:** relabel seats, button, ranges, and strengths together; chance mass, terminal awards, and expected values rotate exactly. Odd-chip fixtures either rotate the button too or declare the expected asymmetry.
4. **Action rotation:** hand-enumerated traces verify skips over folded/all-in seats, round closure, short-all-in reopening rules, and immediate termination with one survivor.
5. **Chance oracle:** independently enumerate compatible range triples with `itertools.product`; compare triple identities and normalized weights within `1e-12`.
6. **Showdown evaluator:** reuse exhaustive/equity evidence from Phases 1–2; each eligible hand rank is the existing seven-card evaluator output.
7. **Information noninterference:** states differing only in another seat's private cards have the same acting-player key and legal actions; changing a public fold/raise actor or contribution must remain distinguishable.
8. **Three-player Kuhn/reference game:** implement or adapt a tiny known game and compare full-tree expected values and unilateral BR values with an independent OpenSpiel script. OpenSpiel is a development oracle, not a runtime dependency.
9. **CFR equations:** on a one-step three-player game, calculate one iteration's reaches/regret deltas by hand and compare within `1e-12`.
10. **Exact certificate:** a trivial dominance-solvable three-player game must reach generalized NashConv below a predeclared fixture threshold; a known multiplayer CFR nonconvergence/cycling fixture or literature-backed limitation must remain labeled uncertified.
11. **Two-player regression:** all existing Phase 1/2 strategy values, APIs, and 185 tests remain unchanged.
12. **Limits:** oversized explicit deal products, runout lists, action trees, or BR strategy products fail before expensive traversal with tested messages.

## Tractability limits

Use structural limits, not invented runtime predictions:

- maximum players for executable postflop Phase 3 game: 3;
- maximum explicit compatible private-deal triples: architecture-defined and checked before solve;
- maximum public chance branches and tree nodes: checked by audit;
- maximum pure unilateral strategies for exact BR: checked as product of responder action counts;
- all limits are emitted as metadata and covered at boundary and boundary+1.

Benchmarks are measured after implementation on this machine. No CPU-hour, memory, infoset, or convergence figure from the discarded draft is accepted.

## Scope matrix

| Capability | Phase 3 disposition |
|---|---|
| Variable-length generic game protocol | Implement alongside two-player protocol |
| Three-way postflop fixed finite game | Implement for explicit ranges/runouts/actions |
| Unequal stacks, folds, all-ins, side pots, ties, odd chips | Implement and exhaustively test |
| N-player CFR regret updates | Implement, with no blanket Nash-convergence claim |
| Exact tiny-game unilateral BR/generalized NashConv | Implement |
| Large-tree multiplayer equilibrium certificate | Documented boundary |
| Full bunching from unmodeled folded ranges | Documented boundary |
| Four-to-nine-way postflop | Documented boundary |
| Up-to-nine-way preflop config/rules representation | May be represented/tested, not strategically solved |
| Nine-way neural/distributed solver | Tier 3 boundary |

Every implementation sub-batch requires a fresh non-author adversarial wave under `review/phase3/` before the next feature batch starts.
