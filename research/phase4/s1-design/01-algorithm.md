# S1 Algorithm Design: Automatic All-Street Continuation

**Date:** 2026-09-15 (UTC)  
**Scope:** Phase 4 S1 — remove caller-supplied continuation values for standard flop solves  
**Status:** Design recommendation (implementation deferred)

---

## 1. Problem statement

Phase 3 delivers bounded exact finite-game solving where **every non-fold closed leaf requires caller-supplied continuation values**. This contract appears in:

- **Preflop** (`preflop.py` lines 338–355): `Continuation(kind="terminal-table", payoff_table={...}, provenance=...)` maps `(deal, history)` to exact zero-sum `(Fraction, Fraction)` payoffs. Missing coverage raises `ValueError`.
- **Three-way postflop** (`multiway.py` lines 304–306): `showdown_ranks: Mapping[Deal3, tuple[int,int,int]]` supplies caller-declared ranks; missing deals fail closed.
- **Checkdown-equity engine** (`engine.py` lines 52–60, 80–139): approximate rollout that forces `CHECK` at every decision, ignores future betting, and is explicitly labeled `approximate=True`.

The **gap** (PARITY_GAP_REPORT.md line 12, PHASE4_MISSION.md lines 9–11): GTO Wizard automatically computes flop→turn→river continuation without caller intervention. The user declares a flop spot; the solver recursively values turn and river leaves.

**S1 acceptance** (PHASE4_MISSION.md lines 11–12): solve a flop spot with a declared turn/river tree and **NO caller continuations**; zero-sum holds; policies sum to 1; on a fixed tree, auto-continuation results are within a derived bound of the explicit-continuation result; convergence-vs-iterations sweep if two methods differ.

---

## 2. Leaf-value semantics: the three approaches

### 2.1 Exact recursive continuation (full subtree solve)

**Mechanism:**  
When the flop solver reaches a closed non-fold leaf (e.g., check-check closing the flop street), it:

1. Constructs a **fresh turn root** with the current pot, stacks, ranges (conditioned on flop actions), and the next street's declared runouts/sizing.
2. Solves the turn subtree to a **fixed iteration budget** (or convergence threshold).
3. Returns the turn root's **expected values** as the flop leaf's continuation payoffs.
4. Recursively, turn leaves spawn river solves.

**Payoff/sign convention:**  
- Leaf returns are **net utility from the start of the original spot** (Phase 1/2/3 convention: `u_i = final_stack_i - starting_stack_i`).
- Zero-sum: `sum(u_i) = -rake` (exact integer rake from `game_structure.py`).
- Multiway: `returns() -> tuple[float, ...]` with `len == num_players`; two-player uses `tuple[float, float]`.

**Termination:**  
- River leaves are **showdown or fold** terminals; no further recursion.
- Showdown uses exact evaluator ranks (`evaluator.py` seven-card evaluation, deterministic).
- Fold awards pot to the last aggressor after refunding uncalled excess (`game_structure.refund_uncalled_excess`).

**Determinism:**  
- CFR/MCCFR: same seed, same iteration count, same tree → same output (Phase 2 contract, ARCHITECTURE.md lines 181–185).
- Runout order: deterministic enumeration (no random sampling of boards unless MCCFR chance sampling is used).
- Sizing: fixed candidate sets, deterministic dynamic/automatic selection (Phase 3 `sizing.py`).

**Multiway/rake:**  
- N-player protocol (`nplayer.py`, `multiway.py`): `num_players()`, `returns() -> tuple[float, ...]`.
- Rake applied once at showdown via `RakePolicy` (`game_structure.py` lines 60–71); `sum(utilities) == -rake`.
- Side pots, odd chips: exact integer accounting (`build_pot_layers`, `award_pot_layers`).

**Convergence:**  
- **Not a convergence certificate** (PHASE3_REPORT.md line 84, ARCHITECTURE.md line 19): `classic` means complete traversal of the declared finite tree for the configured CFR iterations.
- Nested solves compound approximation: flop uses turn's average strategy after `N_turn` iterations; turn uses river's after `N_river` iterations.
- No theoretical guarantee that the composed multi-street strategy is Nash; empirical exploitability via `best_response.py` is the acceptance gate.

**Pros:**  
- Exact finite-tree semantics: every declared runout/action is traversed.
- Matches Phase 3's "complete configured finite-tree CFR" claim.
- Deterministic, auditable, zero-sum by construction.

**Cons:**  
- **Exponential blowup:** a 10-leaf flop × 10-leaf turn × 10-leaf river = 1,000 river solves. Each river solve is cheap, but the turn solver calls 10 river solves per turn leaf, and the flop solver calls 10 turn solves per flop leaf.
- Iteration budget allocation: how many iterations per street? Fixed budget wastes compute on easy subtrees; adaptive budgets break determinism unless the adaptation rule is itself deterministic and declared.
- **Slowest of the three approaches** for large trees.

---

### 2.2 Rollout recursion (single-trajectory sampling)

**Mechanism:**  
When the flop solver needs a leaf value during CFR traversal:

1. **Sample one turn card** from the declared runouts (weighted by probability, using the solver's seeded RNG).
2. **Sample one action sequence** on the turn street by rolling out a **fixed policy** (e.g., uniform random, or a cached "blueprint" strategy from a prior coarse solve).
3. If the turn trajectory reaches a turn leaf, recursively sample one river card and one river action sequence.
4. Return the **terminal payoff** of that single sampled trajectory as the leaf's continuation estimate.

**Payoff/sign convention:**  
- Same as exact recursive: net utility from spot start, zero-sum minus rake.
- The estimate is **unbiased** (expectation over all rollouts equals the true subtree value) but **high variance** per sample.

**Termination:**  
- River showdown/fold terminals, same evaluator.
- Rollout stops at the first terminal (no further sampling).

**Determinism:**  
- **Seed-dependent:** same seed, same tree, same iteration, same rollout policy → same sampled trajectory → same leaf value.
- Rollout policy must be **deterministic given the seed** (e.g., seeded RNG for action selection).
- If the rollout policy is "uniform random," the RNG state must be saved/restored per information set to avoid order-dependence across CFR's two-player traversals.

**Multiway/rake:**  
- Same N-player protocol; rollout samples one path through the N-player tree.
- Rake applied at the sampled terminal.

**Convergence:**  
- **Monte Carlo CFR with rollout continuations:** the flop/turn solvers are MCCFR (external sampling at opponent/chance nodes), and leaves use rollout estimates instead of exact subtree traversal.
- Theoretical MCCFR convergence requires unbiased value estimates; rollout satisfies this **if the rollout policy's support covers all legal actions**.
- **Practical convergence is slower** than exact recursion because high-variance leaf estimates add noise to regret updates.
- Variance reduction: multiple rollouts per leaf (average `K` samples), or importance sampling, or a learned value function (out of scope for Phase 4 without a trained model).

**Pros:**  
- **Scalable:** one sampled trajectory per leaf evaluation, not a full subtree solve.
- Unbiased (in expectation), so MCCFR's convergence proof applies.
- Deterministic given seed and rollout policy.

**Cons:**  
- **High variance → slow convergence:** the flop solver's regrets are noisy, requiring more iterations to converge than exact recursion.
- **Rollout policy choice is critical:** uniform random is unbiased but ignores poker structure (e.g., always calling is legal but terrible); a "blueprint" policy (from a prior coarse solve) is better but adds a dependency and a hyperparameter (how was the blueprint solved?).
- **No finite-tree exactness claim:** even with infinite flop iterations, the result depends on the rollout policy, not the true subtree equilibrium.

---

### 2.3 Bounded value function (learned or tabular approximation)

**Mechanism:**  
When the flop solver reaches a leaf:

1. **Extract features** from the leaf state: pot, stacks, ranges (or range abstractions), board texture, street.
2. **Query a value function** `V(features) -> tuple[float, ...]` that approximates the subtree's equilibrium payoffs.
3. Return `V(features)` as the leaf's continuation.

**Payoff/sign convention:**  
- Same net-utility-from-start, zero-sum-minus-rake.
- The value function must be **trained or calibrated** to match this convention.

**Termination:**  
- No recursion; the value function is a **black box** that replaces the subtree.
- River leaves can still use exact showdown (no need for a value function at the final street).

**Determinism:**  
- **Deterministic if the value function is deterministic** (e.g., a fixed neural network, or a tabular lookup).
- Training the value function is a **separate, non-deterministic process** (SGD, random initialization, data sampling); the trained artifact must be versioned and shipped.

**Multiway/rake:**  
- Value function must output `num_players` values summing to `-rake`.
- Training data must include multiway and raked scenarios.

**Convergence:**  
- **Approximate by design:** the flop solver converges to an equilibrium *of the value-function-augmented game*, not the true poker game.
- Approximation error = `|V(leaf) - true_subtree_value|`; this error propagates into the flop strategy.
- **No finite-tree exactness:** even if the value function is perfect, the flop solver never "sees" the turn/river actions, so it cannot exploit turn/river mistakes.

**Pros:**  
- **Fastest:** O(1) leaf evaluation, no subtree solve or rollout.
- **Scalable to unrestricted trees:** a neural value function generalizes across unseen boards/stack depths.
- **This is how GTO Wizard Fast/DDLS works** (PARITY_GAP_REPORT.md line 11, ARCHITECTURE_PHASE3.md line 23).

**Cons:**  
- **Requires a trained model:** Phase 3 explicitly fails closed on `fast-ddls` because "no neural continuation-value model ships" (engine.py line 51, PHASE3_REPORT.md line 82).
- **Training is a separate project:** data generation (solve millions of subtrees), model architecture, hyperparameter tuning, validation.
- **Approximate and opaque:** the value function's errors are hard to audit; no exact oracle exists for large trees.
- **Out of scope for Phase 4 S1** unless the mission is revised to include model training (PHASE4_MISSION.md line 43 explicitly excludes "Neural DDLS / Fast (A1)").

---

## 3. Rejected alternatives and reasons

### 3.1 Bounded value function (learned)

**Reason for rejection:**  
PHASE4_MISSION.md line 43: "Neural DDLS / Fast (A1) — needs a trained model; separate project."  
No trained continuation-value model exists in the repository. Training one is a multi-month effort (data generation, architecture search, validation) and is explicitly out of scope.

**Boundary:**  
If a future phase trains a model, the integration contract is:
- `EngineConfig(mode="fast-ddls", model_path="...", iterations=...)` loads the model and uses it for leaf values.
- The model must output `num_players` values summing to `-rake`.
- Results are labeled `approximate=True, provenance="neural continuation model v{version}"`.
- A regression test pins the model's output on a canonical fixture to detect drift.

---

### 3.2 Rollout recursion

**Reason for rejection:**  
While unbiased and scalable, rollout recursion has **high variance and slow convergence**. The acceptance criterion (PHASE4_MISSION.md line 11) requires "on a fixed tree, auto-continuation results are within a derived bound of the explicit-continuation result." Rollout's variance makes this bound **loose and iteration-dependent**: after 1,000 flop iterations, the rollout-based strategy might still be far from the exact-recursion strategy, requiring a "convergence-vs-iterations sweep" to demonstrate eventual agreement. This adds complexity to the acceptance gate and makes the solver's output **less predictable** for users ("how many iterations do I need?").

**When rollout is appropriate:**  
- **Unrestricted trees** where exact recursion is infeasible (e.g., continuous bet sizing, or trees with millions of leaves).
- **Research/experimentation** where variance is acceptable and the goal is to explore large spaces cheaply.
- **Phase 4 S1 is bounded finite trees** (PHASE4_MISSION.md line 10: "declared turn/river tree"), so exact recursion is tractable.

**Boundary:**  
If a future phase needs rollout (e.g., for continuous sizing or abstraction experiments), the contract is:
- `EngineConfig(mode="rollout-recursion", rollout_policy="uniform" | "blueprint", rollout_samples=K, ...)`.
- Results labeled `approximate=True, provenance="rollout recursion with {policy}, {K} samples"`.
- A convergence study (exploitability vs. iterations) is mandatory.

---

### 3.3 Hybrid: exact recursion with depth limit

**Idea:**  
Solve flop→turn exactly (recursive subtree solves), but use rollout or a value function for turn→river leaves.

**Reason for rejection:**  
- **Adds a hyperparameter** (depth limit) without clear benefit: if the tree is small enough for exact flop→turn, it's likely small enough for exact turn→river.
- **Complicates the acceptance gate:** now we need bounds for both the exact and approximate portions.
- **Phase 4 S1 scope is "flop→turn→river"** (three streets total); a depth limit of 2 would only save river solves, which are the cheapest (smallest trees).

**Boundary:**  
If a future phase has deeper trees (e.g., preflop→flop→turn→river, four streets), a depth limit might be justified. The contract would be `EngineConfig(mode="recursive", max_recursion_depth=2, leaf_fallback="rollout" | "value-function", ...)`.

---

## 4. Recommended approach: exact recursive continuation

**Choice:** Exact recursive continuation (§2.1).  
**Rationale:**

1. **Matches Phase 3's correctness-first philosophy** (ARCHITECTURE.md line 3: "correctness-first reference implementation"; PHASE3_REPORT.md line 5: "exact finite accounting").
2. **Deterministic and auditable:** same input → same output; no variance, no trained model dependency.
3. **Finite-tree exactness:** the acceptance criterion "within a derived bound of the explicit-continuation result" is trivially satisfied—exact recursion **is** the explicit-continuation result, just computed automatically instead of caller-supplied.
4. **Tractable for Phase 4 S1 scope:** "declared turn/river tree" (PHASE4_MISSION.md line 10) implies bounded finite trees, not unrestricted poker. A 10×10×10 tree (10 leaves per street) = 1,000 river solves, feasible in seconds to minutes on modern hardware.
5. **No new approximation:** Phase 3 already has `checkdown-equity` for approximate rollout (labeled `approximate=True`). Exact recursion extends the `classic` engine's "complete configured finite-tree CFR" claim to multi-street games.
6. **Simplest acceptance gate:** no convergence sweep needed (deterministic), no rollout policy to justify, no model to validate.

**Trade-off acknowledged:**  
Exact recursion is **slower** than rollout or value functions. If Phase 4 later adds unrestricted trees or continuous sizing (S5, S6), a faster method will be needed. But **S1's scope is bounded finite trees**, so speed is not the bottleneck—correctness and determinism are.

---

## 5. Implementation contract (Phase 4 S1)

### 5.1 API changes (additive, backward-compatible)

**New `Continuation` kind:**

```python
# src/poker_solver/preflop.py, src/poker_solver/multiway.py
@dataclass(frozen=True, slots=True)
class Continuation:
    kind: str  # "terminal-table" | "auto-recursive"
    payoff_table: Mapping[ContinuationKey, tuple[Fraction, Fraction]] | None
    provenance: str
    # New fields for auto-recursive:
    next_street_config: MultiStreetConfig | None = None
    recursion_iterations: int | None = None
```

**Validation:**
- `kind == "terminal-table"`: `payoff_table` required, `next_street_config` must be `None` (Phase 3 behavior, unchanged).
- `kind == "auto-recursive"`: `payoff_table` must be `None`, `next_street_config` required (declares turn/river tree), `recursion_iterations` required (CFR budget per subtree).
- Unknown `kind` fails closed.

**Leaf-value computation:**

```python
# In PreflopState.child() or ThreePlayerPostflopState._settle():
if self.config.continuation.kind == "terminal-table":
    # Phase 3 path: lookup in payoff_table
    key = (self.private_deal, self.history)
    if key not in self.config.continuation.payoff_table:
        raise ValueError("missing continuation value")
    return self._replace(
        acting_player=TERMINAL,
        terminal_values=self.config.continuation.payoff_table[key],
        ...
    )
elif self.config.continuation.kind == "auto-recursive":
    # Phase 4 S1 path: solve next street
    next_config = self.config.continuation.next_street_config
    next_root = _build_next_street_root(
        current_state=self,
        next_config=next_config,
    )
    solver = _select_solver(next_root)  # CFRSolver or NPlayerCFRSolver
    strategy = solver.train(self.config.continuation.recursion_iterations)
    values = _expected_values(next_root, strategy)
    return self._replace(
        acting_player=TERMINAL,
        terminal_values=tuple(Fraction(v) for v in values),
        ...
    )
```

**Helper: `_build_next_street_root`:**
- Constructs a fresh `MultiStreetState` (or `PreflopState` / `ThreePlayerPostflopState` if next street is also bounded) with:
  - Current pot, stacks, ranges (conditioned on current street's actions via `range_table.py` reach probabilities).
  - Next street's board (from declared runouts).
  - Next street's sizing/actions (from `next_street_config`).
- Returns a `GameState` or `NPlayerGameState` root.

**Helper: `_select_solver`:**
- If `root.num_players()` exists → `NPlayerCFRSolver`.
- Else → `CFRSolver` (two-player).

**Helper: `_expected_values`:**
- If N-player → `expected_values_nplayer(root, strategy)`.
- Else → `expected_values(root, strategy)`.

---

### 5.2 Multiway and rake

**Zero-sum with rake:**
- River terminals use `game_structure.calculate_rake` and `allocate_rake` (Phase 3, unchanged).
- `sum(terminal_values) == -rake` (exact integer).
- Recursive continuation returns `values` from `expected_values_nplayer`, which already accounts for rake in the subtree.

**N-player protocol:**
- `Continuation.next_street_config` must declare `num_players` matching the current game.
- `_build_next_street_root` preserves `num_players` across streets.

---

### 5.3 Determinism and ordering

**Seed behavior:**
- `CFRSolver` is deterministic (no RNG; full-tree traversal).
- `MCCFRSolver` uses a seeded `random.Random(seed)` (Phase 2 contract).
- If `recursion_iterations` uses MCCFR, the seed must be **derived deterministically** from the parent solver's state (e.g., `hash(parent_infoset_key) % 2**32`) to avoid order-dependence.
- **Recommendation for S1:** use `CFRSolver` (deterministic full-tree) for recursive subtrees; defer MCCFR recursion to a later phase.

**Runout order:**
- `next_street_config.runouts` is a deterministic ordered tuple (Phase 3 `multistreet.py`).
- Chance outcomes are enumerated in declaration order.

**Action order:**
- `legal_actions()` returns a stable ordered tuple (Phase 1 contract, ARCHITECTURE.md line 32).
- Sizing candidates are deterministic (Phase 3 `sizing.py`).

---

### 5.4 Explicit boundaries

**What S1 does NOT do:**

1. **No automatic abstraction:** the caller must declare finite runouts and actions. If the turn has 44 possible cards and the river has 43, the caller must either:
   - Declare all 44×43 runouts (exact but large), or
   - Declare a subset (e.g., 5 turn cards × 5 river cards) and accept that the result is exact only for that abstraction.
   - Automatic abstraction is **S4** (PHASE4_MISSION.md line 22).

2. **No continuous sizing:** the caller must declare finite wager targets. Continuous sizing is **S5** (PHASE4_MISSION.md line 27).

3. **No neural value function:** `kind="auto-recursive"` uses exact CFR subtree solves, not learned approximations. Neural DDLS is **out of scope** (PHASE4_MISSION.md line 43).

4. **No convergence certificate:** `recursion_iterations` is a fixed budget, not an adaptive convergence threshold. The result is "complete traversal of the declared finite tree for the configured CFR iterations" (PHASE3_REPORT.md line 84), not a Nash equilibrium guarantee.

5. **No caller continuation for standard flop solves:** this is the **goal** of S1. After S1, a "standard flop solve" means `Continuation(kind="auto-recursive", next_street_config=..., recursion_iterations=...)`. The caller no longer supplies `payoff_table`. However, `kind="terminal-table"` remains supported for:
   - **Non-standard spots** (e.g., a flop solve where the turn is not played, or a custom terminal payoff rule).
   - **Backward compatibility** (Phase 3 configs still work).
   - **Testing** (explicit-continuation fixtures remain the oracle for auto-continuation).

---

### 5.5 Acceptance gates (from PHASE4_MISSION.md line 11)

1. **Solve a flop spot with NO caller continuations:**
   - Config: `Continuation(kind="auto-recursive", next_street_config=TurnRiverConfig(...), recursion_iterations=100)`.
   - No `payoff_table` supplied.
   - Solver completes without `ValueError("missing continuation")`.

2. **Zero-sum holds:**
   - `sum(root.returns()) == -rake` at every terminal (exact integer, tested via `game_structure` conservation).

3. **Policies sum to 1:**
   - `sum(strategy[infoset].values()) == 1.0` within `1e-9` (Phase 1 regret-matching contract).

4. **Within a derived bound of explicit-continuation:**
   - **Oracle:** solve the same flop spot with `kind="terminal-table"` where `payoff_table` is populated by **pre-solving every turn/river subtree** and recording their `expected_values`.
   - **Test:** solve the same spot with `kind="auto-recursive"` using the **same `recursion_iterations`** for subtrees.
   - **Bound:** the two flop strategies' root expected values must agree within **`1e-6`** (floating-point tolerance for `Fraction→float` conversion and CFR's regret-matching rounding).
   - **Why this bound:** exact recursion and explicit-continuation are **the same algorithm**—both solve subtrees with CFR for `N` iterations and use the resulting `expected_values`. The only difference is **when** the subtrees are solved (pre-computation vs. on-demand). Numerical differences arise from:
     - Floating-point rounding in `Fraction→float` conversions.
     - Regret-matching's `max(0, regret)` and normalization.
     - These are bounded by `1e-6` in Phase 1/2/3 tests (e.g., `test_cfr.py`, `test_kuhn.py`).

5. **Convergence-vs-iterations sweep if two methods differ:**
   - **Not needed for exact recursion vs. explicit-continuation:** they are the same method (see bound above).
   - **Needed if comparing exact recursion vs. rollout:** a future phase that adds rollout must show that rollout's exploitability decreases toward exact recursion's exploitability as iterations increase.

---

## 6. File and symbol mapping

**New/modified files:**

| File | Change | Reason |
|------|--------|--------|
| `src/poker_solver/preflop.py` | Add `Continuation.next_street_config`, `recursion_iterations`; modify `PreflopState.child()` to call recursive solver | Preflop→flop continuation |
| `src/poker_solver/multiway.py` | Add `Continuation` fields; modify `ThreePlayerPostflopState._settle()` | Three-way postflop→turn continuation |
| `src/poker_solver/multistreet.py` | Add `MultiStreetConfig` (if not already present) for turn/river tree declaration | Declares next street's runouts/sizing |
| `src/poker_solver/engine.py` | No change (recursive solving uses existing `CFRSolver` / `NPlayerCFRSolver`) | Reuse Phase 3 solvers |
| `tests/test_preflop.py` | Add `test_auto_recursive_continuation_matches_explicit` | Acceptance gate 4 |
| `tests/test_multiway_phase3.py` | Add `test_three_way_auto_continuation` | Three-way acceptance |
| `tests/test_integration_s1.py` | New file: end-to-end flop→turn→river solve, zero-sum, policy-sum, oracle agreement | Acceptance gates 1–4 |

**Existing symbols (unchanged):**

- `CFRSolver`, `NPlayerCFRSolver`, `expected_values`, `expected_values_nplayer` (reused for subtree solving).
- `game_structure.calculate_rake`, `allocate_rake`, `build_pot_layers`, `award_pot_layers` (reused for river terminals).
- `evaluator.evaluate_seven` (reused for river showdowns).
- `sizing.fixed_sizes`, `validate_size_expression` (reused for turn/river actions).
- `ranges.WeightedCombo` (reused for range conditioning).

**New helper (internal):**

- `_build_next_street_root(current_state, next_config) -> GameState | NPlayerGameState`: constructs a fresh root for the next street with conditioned ranges, updated pot/stacks, and next street's board/sizing.
- `_select_solver(root)`: returns `CFRSolver` or `NPlayerCFRSolver` based on `root.num_players()`.
- `_expected_values(root, strategy)`: returns `expected_values(root, strategy)` or `expected_values_nplayer(root, strategy)`.

---

## 7. Open questions and future work

**Q1: Iteration budget allocation across streets?**  
**A1 (S1 contract):** The caller supplies `recursion_iterations` (a single integer). Every subtree (turn and river) is solved for exactly that many iterations. This is simple and deterministic but **not optimal**—river subtrees might converge faster than turn subtrees, wasting compute. **Future work (post-S1):** adaptive budgets (e.g., "solve each subtree until exploitability < ε") or hierarchical budgets (e.g., "100 flop iterations, 50 turn iterations per flop leaf, 25 river iterations per turn leaf"). Adaptive budgets must remain deterministic (same tree → same budget) to preserve the Phase 3 determinism contract.

**Q2: Range conditioning—how are ranges updated for the next street?**  
**A2 (S1 contract):** Use `range_table.py` (Phase 3) to compute **reach-conditioned range probabilities** at the current leaf. For each combo in the original range, its weight in the next street is `original_weight × reach_probability_given_current_actions`. If a combo's reach is zero (blocked or folded), it is removed from the next street's range. This is **exact Bayesian conditioning** and matches Phase 3's inference semantics. **Implementation detail:** `_build_next_street_root` calls `build_range_table(current_root, current_strategy, seat=i, public_node=current_leaf)` to get reach probabilities, then constructs `WeightedCombo` tuples for the next street.

**Q3: What if a subtree exceeds `max_nodes` or `max_depth`?**  
**A3 (S1 contract):** Fail closed with `ValueError("subtree exceeds finite bounds")`. The caller must either:
- Increase `max_nodes` / `max_depth` in `next_street_config`, or
- Reduce the tree size (fewer runouts, fewer actions, abstraction).
No silent fallback to rollout or approximation—S1 is **exact finite-tree only**.

**Q4: Can the caller mix `auto-recursive` and `terminal-table` across different leaves?**  
**A4 (S1 contract):** No. `Continuation.kind` is a **config-level setting**, not a per-leaf setting. All non-fold leaves in a game use the same continuation kind. **Rationale:** per-leaf continuation would require a `Mapping[leaf_selector, Continuation]`, complicating validation and breaking the immutable-config contract. If a user needs mixed continuation (e.g., auto-recursive for most leaves, explicit for a few edge cases), they can:
- Use `kind="terminal-table"` and populate `payoff_table` by pre-solving subtrees (Phase 3 behavior), or
- Use `kind="auto-recursive"` and accept that all leaves are auto-solved.
**Future work (post-S1):** a `kind="hybrid"` that takes a `default_kind` and a `Mapping[leaf_selector, Continuation]` for overrides.

**Q5: How does this interact with tree editing (Phase 3 `tree_edit.py`)?**  
**A5 (S1 contract):** Tree edits apply to the **current street's action generation**, not to recursive subtrees. If the user edits the flop tree (e.g., removes a bet size), the flop solver sees the edited tree, but turn/river subtrees are built from `next_street_config` (unchanged). If the user wants to edit turn/river trees, they must:
- Edit `next_street_config` before solving the flop, or
- Solve the flop, then separately solve turn/river with edited configs.
**Rationale:** recursive subtrees are **ephemeral**—they are constructed on-demand during flop solving and discarded after their `expected_values` are returned. There is no persistent "turn tree object" to edit. **Future work (post-S1):** a `MultiStreetTreeEditor` that edits all streets' configs atomically.

---

## 8. Summary and recommendation

**Recommendation:** Implement **exact recursive continuation** (§2.1) as the Phase 4 S1 algorithm.

**Leaf-value semantics:**
- When a non-fold leaf is reached, construct a fresh next-street root, solve it with `CFRSolver` or `NPlayerCFRSolver` for `recursion_iterations`, and return `expected_values` as the leaf's continuation payoffs.
- Payoffs are net utility from spot start, zero-sum minus rake, exact integer accounting.
- Recursion terminates at river showdown/fold (exact evaluator, no further subtrees).

**Multiway and rake:**
- N-player protocol (`num_players()`, `returns() -> tuple[float, ...]`).
- Rake applied once at river terminals via `RakePolicy`; `sum(utilities) == -rake`.

**Determinism:**
- Same input (tree, seed, iterations) → same output.
- Use `CFRSolver` (deterministic full-tree) for recursive subtrees in S1; defer MCCFR recursion to a later phase.

**Explicit boundaries:**
- No automatic abstraction (caller declares finite runouts/actions).
- No continuous sizing (caller declares finite wager targets).
- No neural value function (exact CFR subtree solves only).
- No convergence certificate (fixed iteration budget, not adaptive).
- `kind="terminal-table"` remains supported for non-standard spots and backward compatibility.

**Acceptance:**
- Solve a flop spot with `kind="auto-recursive"`, no `payoff_table`.
- Zero-sum, policy-sum, and oracle agreement (within `1e-6` of explicit-continuation) all pass.

**Rejected alternatives:**
- Bounded value function: requires a trained model (out of scope).
- Rollout recursion: high variance, slow convergence, loose bounds (inappropriate for bounded finite trees).

**Files modified:**
- `preflop.py`, `multiway.py` (add `Continuation` fields, modify leaf logic).
- `multistreet.py` (declare turn/river configs).
- `tests/test_preflop.py`, `tests/test_multiway_phase3.py`, `tests/test_integration_s1.py` (acceptance gates).

**No implementation in this design document.** The next step is an **implementation wave** (separate from this design wave) that writes the code, tests, and adversarial audit.

---

**End of S1 algorithm design.**
