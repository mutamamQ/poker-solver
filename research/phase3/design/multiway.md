# Multiway Architecture: Bounded Correct Three-Way Postflop

## 1. Scope and correctness claim

Phase 3 implements a dependency-free, explicit-range **three-player Hold'em postflop game** with exact rules, chance mass, information partition, payoff accounting, regret equations, and measured unilateral-deviation certificate for declared finite trees.

**Implemented target:** bounded three-way postflop with:
- Starting street `flop`, `turn`, or `river`
- Exactly three seats with declared button and action order
- Explicit combo-weighted private ranges per player
- Fixed public starting board and explicit finite runout list for non-river starts
- Integer stacks, previous contributions, and current pot ledger
- Finite configured raise-to targets
- Fold/check/call/raise/all-in legality, short all-ins, action reopening, and round closure
- Unequal stacks, main/side-pot layers, ties, and declared odd-chip rule
- No rake in the first multiway core batch; composition with separately verified rake module follows
- Full-tree N-player CFR as an empirical regret minimizer
- Exact generalized NashConv certification on tiny trees by exhaustive infoset-consistent unilateral best responses

**"Correct"** means exact rules, chance mass, information partition, payoff accounting, regret equations, and measured unilateral-deviation certificate for the declared finite tree. It does **not** mean that CFR is guaranteed to find a Nash equilibrium for every three-player input.

**Documented boundary:** up to nine-way preflop configuration/rules representation may be supported, but Phase 3 does not claim strategic solving at that scale. GTO Wizard reports a proprietary hybrid CFR/neural engine trained through massive self-play; this repository ships neither those value networks nor that corpus. Nine-way strategic solving, neural continuation values, and distributed training remain documented Tier 3 boundaries.

## 2. Game-theory foundations and limitations

### Evidence status

1. **Chip-EV poker with all players included is constant/zero-sum** when no operator rake is removed. It is not general-sum merely because there are more than two players.
2. **CFR's Nash-convergence guarantee applies only to two-player zero-sum games.** The two-player zero-sum convergence theorem for CFR (Zinkevich et al., 2007) does **not** extend to arbitrary three-player poker. CFR may perform well empirically, but its average behavioral profile has no general Nash-convergence guarantee in multiplayer games (Gibson et al., 2013; Ganzfried, 2020).
3. **"Exploitability" is not a coalition response.** The relevant finite-game certificate here is **generalized NashConv**: sum of each player's unilateral best-response improvement while every other player's strategy is fixed.
4. **Pluribus** (Brown & Sandholm, 2019) establishes strong empirical six-player play; it is evidence of feasibility with specialized methods, not an exact strategy oracle for this repository.
5. **OpenSpiel** supplies n-player extensive-game infrastructure and games suitable for independent tiny-game cross-checks.

### Verified sources

- Zinkevich et al. (2007): CFR equilibrium relationship for two-player zero-sum finite extensive-form games: https://proceedings.neurips.cc/paper/2007/file/08d98638c6fcd194a4b1e6992063e944-Paper.pdf
- Gibson, Burch, Lanctot, and Szafron (2013): regret minimization outside two-player zero-sum games: https://arxiv.org/pdf/1305.0034
- Ganzfried (2020): lack of general CFR Nash-convergence guarantees in multiplayer games, three-player Leduc counterexample: https://arxiv.org/html/2001.11165
- Brown and Sandholm (2019): Pluribus six-player empirical play: https://www.science.org/doi/10.1126/science.aay2400
- OpenSpiel: https://github.com/google-deepmind/open_spiel, https://arxiv.org/abs/1908.09453
- GTO Wizard three-way postflop: https://blog.gtowizard.com/now_live_3_way_solving_nodelocking_2_0_and_50k_icm_ft_sims/
- GTO Wizard multiway preflop (up to nine players): https://blog.gtowizard.com/introducing-multiway-preflop-solving/

## 3. N-player protocol extension

**Do not mutate the established two-player `GameState` semantics in place.** Add a sibling protocol for N-player games:

```python
class NPlayerGameState(Protocol):
    def num_players(self) -> int: ...
    def current_player(self) -> int:  # CHANCE | TERMINAL | player index 0..N-1
    def legal_actions(self) -> tuple[Action, ...]: ...
    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]: ...
    def child(self, action: Action) -> NPlayerGameState: ...
    def information_state_key(self, player: int) -> InfoKey: ...
    def returns(self) -> tuple[float, ...]:  # length num_players()
```

Generic N-player audit/expected-value/CFR/BR code uses this protocol. Existing two-player APIs and return shapes stay untouched. An adapter may allow two-player games to use N-player utilities, but old serialized output cannot change.

**Constants:** `CHANCE = -1`, `TERMINAL = -2`; players are integers `0, 1, 2, ..., N-1`.

## 4. Three-way immutable state

`ThreeWayPostflopState` is frozen and carries:

- **Private deals:** three private combos `(h0, h1, h2)` or `None` before chance deal
- **Board and street:** public board cards and current street (`flop`, `turn`, `river`)
- **Button and acting seat:** button position and current acting player index (or `CHANCE`/`TERMINAL`)
- **Per-seat status:** active, folded, or all-in for each of three seats
- **Per-seat remaining stack:** uncommitted chips
- **Per-seat current-street commitment:** chips committed on the current betting round
- **Per-seat total contribution:** cumulative chips contributed from the declared payoff baseline
- **Pot carried from closed streets/dead money:** chips already in the pot before current-street commitments
- **Current highest commitment, last full-raise increment, and which active seats still owe action**
- **Complete public action/street history** including actor identity
- **Terminal reason and rules/tree identity**

**Actor identity and folded seats are public** and cannot be omitted from the information key. The acting player's key includes their own cards and all public fields needed to determine legal actions and payoffs, while excluding every other private combo and unobserved runout. Histories sharing a key must have the same ordered actions.

## 5. Chance and private deals

**Root chance** enumerates every compatible ordered triple `(h0, h1, h2)` with mass `w0 * w1 * w2`, excludes board/card collisions and zero-weight entries, then normalizes once.

**Non-river chance** enumerates only declared legal runout continuations compatible with all private cards and prior board cards.

Chance probabilities must be finite, nonnegative, deterministic in order, and sum to one within `1e-12`.

**Bunching from previously folded ranges** is not implemented unless those folded players were explicitly represented at root chance. Labeling ordinary three-player blocker conditioning as full bunching parity is forbidden.

## 6. Action order and betting-round closure

**Postflop action order:**
- Action begins with the first active, non-all-in seat clockwise after the button.
- After an action, advance clockwise to the next active seat that still owes action.
- A round closes only when every nonfolded, non-all-in player has either matched the highest live commitment or checked after the last full raise and no action is owed.

**Full raise:** updates the minimum raise increment and reopens action to players entitled under the declared no-limit rules.

**Short all-in:** may increase the call target without reopening raising for players who already acted.

**Immediate termination:** if only one nonfolded player remains, terminate immediately and award all contributed chips after any explicit rake rule.

**Showdown:** if multiple players remain but no further decisions are possible, deal the declared runout to showdown.

**Preflop order** belongs to the separate preflop module: normally first active seat clockwise after the big blind/last live straddle, with the blinds retaining action when it returns.

## 7. Pot layers and awards

At terminal showdown, use total contributions `c_i` including folded players. Sort distinct positive contribution levels. For each level `L` above previous level `p`:

```
layer_amount = (L - p) * count(i where c_i >= L)
```

Eligible contenders are nonfolded players with `c_i >= L`. Award that layer to the strongest eligible hand(s). A layer with one eligible contributor is returned/awarded to that contributor, covering unmatched excess deterministically. **Folded contributions remain in layer amounts but folded players can never win.**

Each layer is split independently among tied winners. **Phase 3's explicit odd-chip policy:** distribute indivisible one-chip remainders one at a time to tied winners in clockwise seat order beginning immediately left of the button. This is a project rule recorded in config/metadata; house-rule universality is not claimed.

**For no-rake chip EV,** let `initial_wealth_i` be the stack at the chosen baseline and let terminal wealth include uncommitted stack plus awards. Return `terminal_wealth_i - initial_wealth_i`. Therefore `sum_i returns_i == 0` exactly. If operator rake `r` is removed and the operator is not a modeled player, `sum_i returns_i == -r`.

Dead blinds/antes are player contributions. They do not create a conservation deficit when the payoff baseline includes pre-posting wealth.

## 8. N-player CFR regret updates

For updating player `i`, counterfactual reach at an information set is chance reach multiplied by every other player's reach:

```
pi_-i = pi_chance * product(j != i, pi_j)
```

Regret deltas are `pi_-i * (v_i(I, a) - v_i(I))`. Average strategy accumulation uses player `i`'s own reach under one clearly documented averaging convention. Synchronous full-tree iterations freeze the profile before traversals to avoid branch-order dependence.

**This correctly implements regret updates but does not create a universal multiplayer Nash guarantee.**

### Algorithm: Vanilla full-tree N-player CFR

1. Freeze current strategies from cumulative regrets using regret matching.
2. Traverse separately for each updating player `i` with reaches `(pi_0, pi_1, pi_2, pi_chance)` and the same frozen profile.
3. At chance nodes, multiply `pi_chance` and sum all outcomes.
4. At player nodes, recurse over every action after multiplying that player's reach.
5. At an information set `I` owned by updating player `i`, accumulate (do not immediately apply) `delta_R[I, a] += pi_-i * (v_i(I, a) - v_i(I))` across all underlying histories.
6. Apply all three players' complete regret deltas only after all three traversals. This prevents chance-deal traversal order from changing the strategy mid-iteration.
7. Accumulate average strategy once per information set per iteration as `S[I, a] += pi_i(I) * sigma(I, a)`. Perfect recall implies owner reach is equal at every history in `I`; the implementation asserts this when auditing/collecting.

Regret matching clips cumulative regrets only when forming the strategy; negative vanilla regrets remain stored. There is no sampling, random seed, discounting, pruning, or CFR+ behavior in the deterministic full-tree variant.

## 9. Exact generalized NashConv certification

Results must report:
- Algorithm and iterations
- Expected value for all three players
- Whether exact unilateral best responses were computed
- **Generalized NashConv** `sum_i (BR_i(sigma_-i) - u_i(sigma))` where available
- **No `half_nash_conv` or two-player "exploitability" label**

For tiny trees, enumerate one action per responder infoset and evaluate it against all other fixed behavioral policies. Generalized NashConv is nonnegative and is zero exactly when no player can profitably deviate, subject to exact enumeration/numeric tolerance.

Larger trees for which exact BR is unavailable are labeled **uncertified** rather than assigned a sampled "exploitability" number.

### Best response extension

Extend `best_response.py` to support N-player games:
- **Exhaustive pure-strategy enumeration** (tiny-game oracle): enumerate the Cartesian product of one legal action per responder infoset, evaluate each pure response against the fixed behavioral strategies of all other players.
- **Scalable infoset-consistent dynamic path** (if tractable): choose one action per responder information set, weighted by all-other-players-plus-chance counterfactual reach.

## 10. Independent oracles and acceptance tests

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

## 11. Tractability limits

Use structural limits, not invented runtime predictions:

- **Maximum players for executable postflop Phase 3 game:** 3
- **Maximum explicit compatible private-deal triples:** architecture-defined and checked before solve
- **Maximum public chance branches and tree nodes:** checked by audit
- **Maximum pure unilateral strategies for exact BR:** checked as product of responder action counts
- All limits are emitted as metadata and covered at boundary and boundary+1

Benchmarks are measured after implementation on this machine. No CPU-hour, memory, infoset, or convergence figure from discarded drafts is accepted.

## 12. APIs and CLI

### JSON configuration (version `threeway-v1`)

```json
{
  "version": "threeway-v1",
  "starting_street": "flop" | "turn" | "river",
  "starting_board": ["Ah", "Kd", "Qc", ...],
  "button": 0 | 1 | 2,
  "initial_pot": 150,
  "stacks": [500, 450, 600],
  "player0_combos": [["As", "Ks"], 1.0], ...,
  "player1_combos": [["Jh", "Th"], 1.0], ...,
  "player2_combos": [["9c", "8c"], 1.0], ...,
  "allowed_runouts": [["2c", "3d"], ...],
  "betting_mode": "no-limit" | "pot-limit",
  "wager_targets": [50, 100, 200, ...],
  "odd_chip_rule": "clockwise_from_button"
}
```

### CLI commands

```bash
poker-solver solve-threeway CONFIG.json --iterations N --json
poker-solver exploitability-threeway CONFIG.json STRATEGY.json --json
```

### Output format

```json
{
  "algorithm": "vanilla-cfr-3player",
  "iterations": 10000,
  "values": [0.12, -0.05, -0.07],
  "generalized_nash_conv": 0.023,
  "best_response_values": [0.14, -0.03, -0.06],
  "incentives": [0.02, 0.02, 0.01],
  "certified": true,
  "strategy": { ... }
}
```

Successful JSON is sorted and contains deterministic fields only. Errors go to stderr; exit 2 is invalid input/config, exit 1 an internal runtime failure.

## 13. Module ownership and file structure

```
src/poker_solver/
  nplayer_model.py          # N-player protocol, constants
  threeway_postflop.py      # ThreeWayPostflopState, create_root
  nplayer_cfr.py            # N-player vanilla CFR solver
  nplayer_best_response.py  # N-player exhaustive/scalable BR, generalized NashConv
  nplayer_audit.py          # N-player tree validation
  nplayer_api.py            # JSON config/strategy serialization
  nplayer_cli.py            # CLI commands for three-way solving

tests/
  test_nplayer_model.py
  test_threeway_postflop.py
  test_nplayer_cfr.py
  test_nplayer_best_response.py
  test_nplayer_audit.py
  test_nplayer_api.py
  test_nplayer_cli.py
  test_threeway_oracle.py   # Pot-layer, conservation, symmetry, chance oracles
```

## 14. Complexity limits and 3-way-vs-9-way boundary

### Three-way postflop (implemented)

- **Explicit private-deal enumeration:** all compatible ordered triples `(h0, h1, h2)` with product weights
- **Exact chance mass:** normalized within `1e-12`
- **Full-tree CFR:** synchronous traversals for all three players
- **Exact generalized NashConv:** exhaustive pure-strategy enumeration on tiny trees
- **Side pots, ties, odd chips:** exact layer-by-layer awards

### Up-to-nine-way preflop (configuration representation only)

- **Configuration model** may represent up to nine seats and forced-bet structure
- **No strategic solving** at that scale in Phase 3
- **Joint explicit deal space, public action branching, asymmetric stacks, and imperfect-information strategy space grow combinatorially**
- GTO Wizard reports a proprietary hybrid CFR/neural engine trained through massive self-play; this repository ships neither those value networks nor that corpus
- **No imperfect-recall hand bucketing** is introduced merely to claim scale
- A 169-class preflop abstraction is not automatically sound in multiway games because suit-specific blockers and card removal couple players' ranges
- **Nine-way strategic solving, neural continuation values, and distributed training remain documented Tier 3 boundaries**

## 15. Scope matrix

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

## 16. Acceptance gates

- All 185 existing Phase 1/2 tests remain green
- Pot-layer oracle: exact layer membership and awards for all fixtures
- Conservation: no-rake terminal returns sum exactly to zero; with rake, player returns plus operator rake sum to zero
- Permutation symmetry: chance mass, terminal awards, and expected values rotate exactly
- Action rotation: hand-enumerated traces verify skips, closure, reopening, termination
- Chance oracle: compatible range triples match independent enumeration within `1e-12`
- Showdown evaluator: reuses exhaustive/equity evidence from Phases 1–2
- Information noninterference: states differing only in another seat's private cards have the same acting-player key and legal actions
- Three-player reference game: full-tree expected values and unilateral BR values match independent OpenSpiel script
- CFR equations: one-step three-player game reaches/regret deltas match hand calculation within `1e-12`
- Exact certificate: trivial dominance-solvable three-player game reaches generalized NashConv below predeclared threshold
- Two-player regression: all existing Phase 1/2 strategy values, APIs, and tests unchanged
- Limits: oversized inputs fail before expensive traversal with tested messages
- Fresh non-author adversarial wave under `review/phase3/` before next feature batch

---

**End of multiway architecture design.**