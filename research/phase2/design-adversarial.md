# Phase 2 adversarial architecture reconciliation

## Executive summary

Phase 2 research documents propose multi-street solving, MCCFR, pot-limit betting, and exploitability computation. The current codebase implements vanilla CFR, exact best response, and a single-street river game with one discrete bet size. This report attacks feasibility, interface conflicts, semantic gaps, scalability claims, dependency risks, and test runtime to recommend the smallest honest feature-complete backend.

**Recommendation**: Implement external-sampling MCCFR, multi-street state machine (flop/turn/river), pot-limit bet sizing, and exploitability CLI. Reject three-player, continuous action abstraction, and commercial full-game performance claims. Explicit non-goals prevent scope creep.

## Feasibility attacks

### Multi-street state complexity

Research doc `multistreet-modeling.md` specifies flop/turn/river with exact runouts and one bet per street. A flop with fixed private cards exposes up to 45 turn cards × 44 river cards = 1,980 public runout branches before any betting actions. With two weighted ranges of even 10 combos each (100 deal pairs), vanilla CFR must traverse 198,000 chance-action paths per iteration.

**Attack**: The research correctly identifies this as intractable for vanilla CFR but proposes MCCFR as the "normal path." MCCFR samples one runout per iteration, reducing work by ~2000× per street, but increases variance. The research provides no concrete iteration budget, convergence threshold, or runtime ceiling for a realistic multi-street fixture.

**Mitigation**: Require a tiny multi-street reference game with ≤4 turn cards, ≤3 river cards, and 2 combos per player. Vanilla CFR must solve it exactly as the oracle; MCCFR must approach the same exploitability within a pre-measured seed-matrix tolerance. No multi-street fixture ships without this cross-validation.

### Pot-limit semantics

Research doc `multistreet-modeling.md` states: "A pot-limit mode caps a wager using the pot-limit rule; an all-in action is additionally capped by effective remaining stack." The current `river.py` has no pot-limit logic; it accepts one fixed integer `bet` amount. The research references `https://barge.org/rulebook/pot-limit.html` but provides no formula.

**Attack**: Pot-limit maximum is `pot + to_call + to_call` (the pot after calling, plus the call amount again). This depends on current pot, cumulative contributions, and outstanding wager. The current `RiverState` tracks `pot`, `stack`, and `bet` but not per-player `committed` or `to_call`. Multi-street resets action legality after each street but cumulative contributions persist for all-in accounting.

**Conflict**: The `RiverConfig` is immutable and frozen. Pot-limit requires mutable per-street state: current pot grows with each action, contributions reset after street closure, and remaining stack decreases. The current `information_state_key` includes `pot, stack, bet` as immutable config parameters, not dynamic state.

**Mitigation**: Extend `RiverState` (not `RiverConfig`) with mutable `current_pot`, `committed: tuple[int, int]`, `remaining: tuple[int, int]`. Recompute pot-limit maximum at each decision node. Information keys must include these dynamic values to preserve perfect recall. This breaks the current immutable-config assumption and requires careful zero-sum accounting tests.

### Best-response scalability

Current `best_response.py` enumerates the Cartesian product of all pure strategies (line 70: `for choices in product(*action_sets)`). For a game with 10 information sets and 2 actions each, this is 2^10 = 1,024 pure strategies. A multi-street game with 100 information sets per player is 2^100 ≈ 10^30 pure strategies.

**Attack**: The research doc `exploitability-best-response.md` proposes a "dynamic best-response implementation" (lines 11-19) that processes information sets from deepest to shallowest and is "linear in a tree evaluation per candidate action/information set." This is the standard public-tree dynamic programming algorithm, not the current exhaustive enumeration.

**Gap**: The current codebase has no dynamic best-response implementation. The research doc states "Retain existing exhaustive pure-strategy enumeration as the tiny-game oracle" and "Add a public-tree/infoset dynamic best-response implementation" but provides no code, no module ownership, and no acceptance test beyond "dynamic BR and enumeration differ by at most 1e-12 for both players."

**Mitigation**: Implement `dynamic_best_response(root, opponent_profile, player)` in `best_response.py` using depth-first traversal with memoization. Require exact agreement with exhaustive enumeration on Kuhn and the current river fixture before exposing it as the scalable path. Add a hidden-bit trap test (research doc line 24) to ensure information-set aggregation, not per-history maximization.

### MCCFR convergence claims

Research doc `mccfr-vs-cfr.md` states: "The paper explicitly reports the tradeoff: sampled methods can need more iterations, while lower iteration cost can reduce wall time in some games. There is no universal speedup number." Yet `design-api-cli.md` line 44 defaults to 20,000 iterations for both vanilla and MCCFR with no justification.

**Attack**: MCCFR on Kuhn with 20,000 iterations may converge to ≤0.01 exploitability, but a multi-street game with 1,980 runout branches has 1,980× higher variance per iteration. The research provides no iteration scaling formula, no per-game convergence threshold, and no runtime budget.

**False claim**: Research doc `determinism-performance.md` line 22 states "Phase 2 therefore offers exact finite spots, vanilla reference solves only when tractable, and sampled fast solves for larger trees. It does not claim commercial full-game throughput." This is honest scope limitation, but `PHASE2_MISSION.md` line 27 promises "Multi-street (flop/turn/river) heads-up spot solving" without qualifying "small restricted-runout games only."

**Mitigation**: Require explicit iteration budgets and exploitability thresholds per fixture. A multi-street fixture must specify: number of streets, runout deck size, range sizes, iteration count, seed matrix, expected exploitability mean and 95% CI. No fixture ships without pre-measured convergence evidence. README must state: "Multi-street solving is limited to small restricted-runout games; full unrestricted Hold'em is out of scope."

## Interface conflicts

### GameState protocol vs multi-street state

Current `model.py` defines `GameState` protocol with `returns() -> tuple[float, float]`. Research doc `three-player-scope.md` line 29 proposes `returns() -> tuple[float, ...]` for multiplayer but confirms Phase 2 remains heads-up.

**Conflict**: Multi-street state needs `street: int`, `board: tuple[int, ...]` (growing from 3 to 5 cards), `current_pot: float`, `committed: tuple[int, int]`, `remaining: tuple[int, int]`. The current `RiverState` has `config: RiverConfig` (immutable) and `history: tuple[Action, ...]`. Extending to multi-street requires either:

1. Mutable `MultiStreetState` with dynamic pot/stack fields (breaks immutability)
2. Immutable state with pot/stack in history (bloats information keys)
3. Separate `FlopState`, `TurnState`, `RiverState` (code duplication)

**Recommendation**: Option 1. Add `@dataclass(frozen=True)` `StreetState` with `street`, `board`, `pot`, `committed`, `remaining` as immutable snapshots. Each action returns a new `StreetState`. Information keys include the full `StreetState` tuple. This preserves immutability while allowing dynamic state.

### Action representation

Current `Action` is `@dataclass(frozen=True, order=True)` with `kind: str, amount: int = 0`. Research doc `multistreet-modeling.md` line 17 states: "A bet action's `amount` means chips newly committed by the actor, not raise-to."

**Conflict**: Pot-limit maximum depends on `to_call`, which is `max(committed) - committed[player]`. If player 0 bets 50 into a pot of 100, player 1's pot-limit maximum is `(100 + 50) + 50 + 50 = 250` (pot after calling + call + call again). But `Action("bet", 250)` is ambiguous: is it 250 newly committed, or raise-to 250?

**Current code**: `river.py` line 43 defines `bet_action = Action("bet", self.bet)` where `self.bet` is the configured amount. Line 141 uses `stake += self.config.bet` for called-bet payoff, treating `bet` as the newly committed amount.

**Recommendation**: Keep `amount` as newly committed chips. Pot-limit validation computes `max_bet = pot_after_call + to_call` and rejects `Action("bet", amount)` if `amount > max_bet`. All-in is `Action("bet", min(max_bet, remaining[player]))`. This is consistent with current semantics.

### Information key bloat

Current `river.py` line 123 information key is:
```python
("river-v1", player, own, self.config.board, self.history,
 self.config.pot, self.config.stack, self.config.bet)
```

Multi-street key must include: `street`, `board` (length 3-5), `current_pot`, `committed`, `remaining`, `history`. For a 3-street game with 10 actions, this is a 20+ element tuple per information set.

**Attack**: Python dict keys are hashed. Long tuples with floats (`current_pot`) have hash collisions and equality checks on every lookup. CFR accesses information sets millions of times per solve.

**Mitigation**: Use `@dataclass(frozen=True, slots=True)` `InfoKey` with `__hash__` and `__eq__` instead of raw tuples. Intern common sub-structures (board tuples, history tuples). Profile hash performance on a multi-street fixture before claiming "production-ready."

## Payoff and pot-limit semantics

### Zero-sum accounting

Current `river.py` lines 132-143 compute terminal returns as net from spot start: `±pot/2` baseline, `±(pot/2 + bet)` for called bets, fold returns `+pot/2` to bettor and `-pot/2` to folder. This is zero-sum.

**Multi-street extension**: After a flop bet-call, pot grows by `2 * bet_amount`. Turn betting starts with `new_pot = old_pot + 2 * flop_bet`. Cumulative contributions track total chips committed since spot start. Terminal payoff is `winner_award - own_contribution + initial_pot/2`.

**Attack**: If `committed` resets after each street (for action legality), but cumulative contributions persist (for payoff), the code needs two separate trackers. Research doc `multistreet-modeling.md` line 13 states: "contributions for action legality reset but cumulative contributions do not." This is ambiguous.

**Clarification**: `committed[p]` is chips committed **this street** (resets to 0 after street closure). `total_contributed[p]` is chips committed **since spot start** (never resets). Pot grows by `sum(committed)` after each street closure. Terminal payoff uses `total_contributed`. Information keys include `committed` (for pot-limit calculation) but not `total_contributed` (redundant with pot and history).

### Fold payoff edge case

Current `river.py` line 133: `if self.history == (b, FOLD): value = self.config.pot / 2.0`. This assumes folder loses their initial pot share and bettor wins it. But if player 0 bets and player 1 folds, player 0 gets `+pot/2` (their initial share) plus player 1's `-pot/2` (their initial share), net zero-sum.

**Multi-street edge case**: If player 0 bets flop, player 1 calls, player 0 bets turn, player 1 folds, player 0 should win `pot/2 + flop_bet + turn_bet` (their initial share plus both streets' bets). Player 1 loses `pot/2 + flop_bet + turn_bet` (their initial share plus both streets' calls).

**Formula**: Fold payoff is `winner = +pot/2 + own_total_contributed`, `loser = -pot/2 - own_total_contributed`. This is zero-sum: `(pot/2 + c0) + (-pot/2 - c1) = c0 - c1`, and pot growth is `c0 + c1`, so total contested is `pot + c0 + c1`, awarded to winner.

**Test requirement**: Add exhaustive zero-sum check to multi-street audit: every terminal return pair sums to exactly 0.0 within 1e-12. Every street-closure pot increment equals `sum(committed)`. Every all-in branch deals remaining cards without further betting.

## Dependency risks

### No runtime dependencies

Current `pyproject.toml` line 7: `dependencies = []`. Research docs reference Treys, PH Evaluator, OpenSpiel as **oracles and references**, not runtime dependencies.

**Risk**: MCCFR requires `random.Random(seed)` (stdlib). Multi-street requires no new dependencies. Exploitability uses existing `best_response.py`. Pot-limit is pure arithmetic. **No new dependencies needed.**

**Attack**: Research doc `feature-inventory.md` mentions "PyPokerEngine" and "pycfr/OpenCFR" as "must be evaluated at a pinned revision before becoming references." These are **not** proposed as dependencies, but a careless implementer might `pip install` them.

**Mitigation**: Reject any PR that adds runtime dependencies. Treys is a **test-time** oracle (already in `scripts/crosscheck_treys.py`). OpenSpiel is a **reference** for algorithm correctness, not a library to import.

### Test runtime explosion

Current test suite: 80 tests, 140 seconds (2:20). Research doc `determinism-performance.md` line 28 proposes "median of at least three runs" for benchmarks. Multi-street MCCFR with 10,000 iterations on a 4×3 runout deck may take 10+ seconds per run.

**Attack**: If every multi-street test runs 10,000 MCCFR iterations × 3 runs for median, and there are 10 multi-street tests, that's 300,000 iterations = 5+ minutes. Total suite time could exceed 10 minutes, breaking CI.

**Mitigation**: Mark multi-street MCCFR tests as `@pytest.mark.slow`. Default suite runs fast smoke tests (100 iterations, 1 run). Slow suite runs convergence tests (10,000 iterations, 3-run median). CI runs both, but developers can `pytest -m "not slow"` for fast feedback. Benchmark ceiling is 3× measured baseline, not an invented number.

## False "industry accuracy" claims

### No commercial solver fixtures

Research doc `feature-inventory.md` lines 9-10: "GTO+'s public home page confirms the product exists but did not expose enough machine-readable detail in this research pass to substantiate claims about algorithms, player counts, JSON export, or exact accuracy. 'GTD' could not be identified as a distinct industry solver and is treated as unresolved."

**Attack**: `PHASE2_MISSION.md` line 13 lists "GTO+ / GTD" as industry-standard solvers to match. But the research found **no usable fixtures** from these products. Claiming "industry accuracy" without a single GTO+ comparison is false advertising.

**Mitigation**: Remove "industry accuracy" from all claims. Replace with: "Correctness verified against published analytical values (Kuhn -1/18), independent implementations (Treys equity, OpenSpiel CFR reference), and exhaustive enumeration oracles (five-card evaluator, pure-strategy best response)."

### PokerStove is not a solver

Research doc `feature-inventory.md` lines 4-5: "PokerStove describes itself as poker evaluation/enumeration software and exposes an evaluation library/tool; it does not claim to solve betting strategies."

**Attack**: `PHASE2_MISSION.md` line 13 lists "PokerStove" as an industry-standard solver. This is incorrect. PokerStove is an **equity calculator**, not a **strategy solver**.

**Correction**: PokerStove is a valid **equity oracle** (cross-check for `equity.py`), not a **strategy oracle**. Do not claim to match PokerStove's solving capabilities (it has none).

## Recommended feature-complete finite backend

### In scope (Phase 2)

1. **External-sampling MCCFR**: Implement per `mccfr-vs-cfr.md` spec, lines 6-15. Dedicated `random.Random(seed)`, stable action order, opponent-node simple averaging. Vanilla CFR remains available and unchanged. Both paths tested on Kuhn and tiny multi-street fixture.

2. **Multi-street state machine**: Flop/turn/river with exact runout sampling. State includes `street`, `board`, `current_pot`, `committed`, `remaining`. Street closure advances board, resets `committed`, updates pot. All-in skips remaining streets. Zero-sum accounting tested exhaustively.

3. **Pot-limit bet sizing**: Compute `max_bet = (pot + to_call) + to_call` at each decision node. Validate configured bet sizes against pot-limit and stack. All-in is `min(max_bet, remaining[player])`. No continuous action space; discrete configured sizes only.

4. **Dynamic best response**: Depth-first DP per `exploitability-best-response.md` lines 11-19. Exact agreement with exhaustive enumeration on Kuhn and river fixture. Hidden-bit trap test. Scalable to multi-street games with 100+ information sets.

5. **Exploitability CLI**: `poker-solver exploitability strategy.json spot.json --json`. Output includes `nash_conv`, `exploitability_half_nash_conv`, `values`, `best_response_values`, `incentives`. Validates strategy completeness and probability normalization.

6. **Version 2 spot schema**: Per `design-api-cli.md` lines 7-44. Supports `algorithm`, `seed`, `iterations` fields. Backward-compatible with version 1. Strict numeric type validation (reject bool for int).

7. **Determinism tests**: Vanilla CFR byte-identical on same input. MCCFR byte-identical on same seed/input/iterations locally. Hash verification per `design-api-cli.md` lines 295-299.

8. **Tiny multi-street reference**: 3-card flop, 4-card turn deck, 3-card river deck, 2 combos per player, 1 pot-limit bet per street. Vanilla CFR oracle, MCCFR cross-validation, exact zero-sum accounting, dynamic BR agreement.

### Explicit non-goals (out of scope)

1. **Three-player**: Research doc `three-player-scope.md` confirms Phase 2 is heads-up only. Multiplayer requires vector returns, side pots, and loses two-player Nash convergence guarantees. Future work.

2. **Continuous action space**: Only discrete configured bet sizes. No automatic generation of "optimal" bet sizes. No action abstraction beyond explicit pot-fraction list.

3. **Full unrestricted Hold'em**: Research doc `determinism-performance.md` line 22: "unrestricted solving requires abstraction." Phase 2 offers small restricted-runout games only. No 52-card deck, no full game trees.

4. **Suit isomorphism / card abstraction**: Research doc `determinism-performance.md` line 18: "suit isomorphism, and hand/action abstraction are separate algorithms requiring separate tests and output labels." Deferred to future work.

5. **CFR+ / Discounted CFR**: Research doc `mccfr-vs-cfr.md` line 16: "CFR+ is a separate alternating/vector algorithm with clipped cumulative regret and is not silently mixed into MCCFR." Out of scope.

6. **Commercial throughput**: No claims about solving full game trees in seconds. No performance comparisons to GTO+ or commercial solvers. Honest scope: small games, exact correctness, research-grade performance.

7. **Preflop solving**: Research doc `design-api-cli.md` line 35 allows `"board": []` for preflop, but no preflop fixture is specified. Defer to future work; Phase 2 focuses on postflop (flop/turn/river).

8. **Rake / ICM / side pots**: Zero-sum chip-conserving heads-up only. No tournament equity, no rake, no multiway side pots.

### Module ownership (Phase 2 extensions)

- `src/poker_solver/mccfr.py` + `tests/test_mccfr.py`: External-sampling MCCFR solver class, seed handling, determinism.
- `src/poker_solver/multistreet.py` + `tests/test_multistreet.py`: Flop/turn/river state machine, pot-limit logic, street closure, all-in handling.
- `src/poker_solver/best_response.py` (extend) + `tests/test_best_response.py` (extend): Add `dynamic_best_response`, hidden-bit trap test, scalability test.
- `src/poker_solver/cli.py` (extend) + `tests/test_cli.py` (extend): Version 2 schema, algorithm selection, seed validation, exploitability command.
- `research/phase2/design-adversarial.md` (this file): Adversarial review, no code ownership.

### Acceptance gates (Phase 2)

1. All 80 Phase 1 tests pass (regression gate).
2. MCCFR on Kuhn: seed-matrix mean EV within 0.003 of -1/18, 95% CI within pre-measured bound.
3. MCCFR determinism: same seed/input/iterations produces identical JSON hash locally.
4. Tiny multi-street fixture: vanilla CFR oracle, MCCFR agreement within tolerance, exact zero-sum, dynamic BR = exhaustive BR.
5. Pot-limit validation: configured bet rejected if exceeds pot-limit or stack, all-in capped correctly.
6. Exploitability CLI: strategy validation, NashConv ≥ 0, exploitability = NashConv/2.
7. Version 2 schema: strict numeric types, backward compatibility with version 1, algorithm selection.
8. Benchmark: tiny multi-street fixture median runtime ≤ 3× measured baseline (not an invented ceiling).
9. README: explicit scope (small restricted-runout games), explicit non-goals (no full game, no three-player, no commercial throughput).
10. No new runtime dependencies (stdlib only).

## Conclusion

Phase 2 research is thorough and honest about limitations. The proposed feature set is achievable with careful implementation: MCCFR, multi-street state, pot-limit, dynamic best response, exploitability CLI. The main risks are:

- **Scope creep**: Claiming "industry accuracy" or "full Hold'em" without evidence.
- **Interface conflicts**: Multi-street state vs immutable config, pot-limit vs fixed bet.
- **Test runtime**: MCCFR convergence tests may exceed 10 minutes without `@pytest.mark.slow`.
- **False convergence**: MCCFR iteration budgets must be pre-measured, not guessed.

Recommendation: **Proceed with explicit non-goals and tiny reference fixtures.** Every multi-street claim must be backed by a concrete fixture with pre-measured convergence. No "industry accuracy" claims without machine-readable commercial solver outputs. Honest scope prevents overpromising.
