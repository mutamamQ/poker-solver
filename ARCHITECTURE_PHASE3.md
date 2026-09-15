# Phase 3 reconciled architecture

## 1. Contract and claim boundary

Phase 3 extends the dependency-free finite-game backend toward the tractable solver surface of GTO Wizard. It does not claim product parity, chart parity, or unrestricted Hold'em solving. Correctness means exact accounting and traversal for the declared finite abstraction, plus explicit labeling wherever continuation or behavior is approximate.

The Phase 1+2 public contracts remain unchanged:

- `model.Action`, `model.GameState`, the two-player `returns() -> tuple[float, float]` protocol, and existing CFR/MCCFR behavior remain backward-compatible.
- Version-1 river and version-2 multistreet JSON requests and CLI commands retain their schemas and output fields.
- `Action.amount` remains an integer raise-to commitment for the current street.
- Existing two-player `best_response`, NashConv, and half-NashConv labels are used only for two-player zero-sum games.
- All 185 Phase 1+2 tests are a permanent regression gate.

Phase 3 uses additive modules and a separate version-3 facade. New N-player algorithms use a separate protocol rather than widening `GameState.returns()` and silently changing old solvers.

## 2. Reconciliation decisions

The Wave A reports are authoritative about researched semantics after parent correction. Wave B design reports are advisory. Conflicts are resolved as follows.

1. Profiles are explicit behavioral constraints, not invented psychological truth. A profile transforms a supplied baseline policy into a fixed opponent policy by category multipliers and normalization. Solving then computes a best response or constrained-game strategy. The proposed non-zero-sum action-bonus CFR is not the Tier-1 contract because the existing solvers are two-player regret minimizers over terminal utilities and a shaped objective would require a separate, validated general-sum algorithm. Actual chip EV is always evaluated with unmodified terminal returns.
2. Nodelocks are complete distributions over the exact legal actions of an observed `InfoKey`. Partial locks, bounds, and warm-start remapping are boundaries. Structural edits always produce a fresh game and fresh solver.
3. Fast/DDLS neural continuation is not implemented. `classic` traverses the complete configured finite tree. `checkdown-equity` is a working, explicitly approximate continuation whose result must say that it ignores future betting and has no unrestricted-game exploitability guarantee.
4. Dynamic and Automatic sizing are exact only relative to a bounded candidate set and fully re-solved bounded games. No proprietary GTO Wizard search, continuous optimization, or neural heuristic is claimed.
5. Three-way postflop uses a separate N-player protocol and generalized unilateral-deviation certificate. It never reports two-player exploitability or a general multiplayer Nash-convergence guarantee.
6. ICM and immediate bounty accounting are bounded Tier-2 implementations. Full strategic future-bounty solving is a boundary, not a reason to omit exact small-field ICM.
7. Alternative private combos may share cards because they are mutually exclusive chance alternatives. Collisions are removed when constructing a particular joint deal; they are not a configuration-wide error.
8. Total antes need not divide evenly unless the selected ante policy explicitly requires equal allocation. Explicit per-seat forced contributions are the ground truth.
9. Deterministic output excludes wall-clock timestamps. Provenance is caller-supplied stable text. Arbitrary hashable `InfoKey` objects are not generically serialized; version-3 games expose canonical JSON-safe key labels and resolve them against the exact rebuilt tree.
10. Exact chip conservation uses integer equality. Floating probability and EV tolerances are fixture-specific; iterative CFR outputs never receive an unearned universal `1e-12` convergence claim.

## 3. Shared foundations

### 3.1 Game structure and accounting

New module: `src/poker_solver/game_structure.py`.

Core immutable types:

- `ForcedPost(seat, kind, amount)` where kind is ante, small-blind, big-blind, or straddle.
- `SeatLedger(starting_stack, remaining, street_committed, total_contributed, folded, all_in)`.
- `GameStructure(button, seats, forced_posts, odd_chip_order, short_all_in_reopens)`.
- `PotLayer(amount, contributors, eligible)`.

Rules:

- Starting stacks are before forced posts. Each post is transferred exactly once from remaining stack to contribution.
- `sum(remaining) + sum(total_contributed)` equals the initial player-chip total at every state.
- Calls and raises use amount-to semantics; paid chips are `target - own street commitment`.
- Uncalled excess is refunded before pot-layer construction.
- Side pots are built from sorted distinct contribution levels. Folded seats fund layers but cannot win them.
- Odd chips follow an explicit deterministic seat order. No room-specific default is claimed.
- Heads-up preflop: button posts the small blind and acts first. Heads-up postflop: the big blind acts first.
- Ring structures and up to nine seats may be represented and accounted for, but strategic preflop solving is bounded as stated in the matrix.

Independent oracle: hand-calculated integer ledgers and exhaustive layer allocation. Tolerance: exact integer equality.

### 3.2 Rake

Rake is a pure policy in `game_structure.py`, not embedded as floating room folklore:

`RakePolicy(rate_numerator, rate_denominator, cap, minimum_pot, no_flop_no_drop, rounding, layer_order)`.

The rate is rational. The policy computes one hand-level rake from the declared eligible matched pot, applies the declared rounding once, applies the cap, and allocates the exact integer amount across layers by the declared policy. Disabled rake reproduces chip-EV accounting exactly. At terminal states:

- `sum(final_stacks) + house_rake == initial_total`;
- equivalently, `sum(player_utilities) == -house_rake` when utilities are net changes.

Per-player rake display is an attribution of the one total rake, never multiple collection. Room-specific eligibility, jackpot drops, time rake, fees, rakeback, and private rounding behavior are boundaries.

### 3.3 Bet sizing

New module: `src/poker_solver/sizing.py`.

Input expressions are strict objects:

- `{"unit":"pot-percent","value":q}`
- `{"unit":"geometric","streets":n,"scale":s}`
- `{"unit":"previous-bet-multiple","value":m}`
- `{"unit":"big-blinds","value":b}`
- `{"unit":"all-in"}`

Decimal text is used for conversion and round-half-up is applied once at the end. Let `P` be the pot including current commitments, `c` the call amount, `P_call = P + c`, and `own_call = own + c`.

- Pot percent `q` is interpreted as a fraction after dividing the entered percentage by 100. With no wager, target is `own + q*P`; facing a wager, target is `own_call + q*P_call`.
- Previous-bet multiple is the project convention `target = m * highest_commitment`.
- Big blinds is `target = b * BB`.
- At an unopened equal-stack node with remaining matched stack `S` and `n` equal bet/call opportunities, geometric fraction is `g = ((1 + 2*S/P) ** (1/n) - 1)/2`; `scale` multiplies `g`. Facing a wager uses the hypothetical post-call pot and matched remaining stack.
- All-in resolves exactly to the actor's maximum raise-to.

Converted targets are filtered by call, minimum-full-raise, short-all-in, reopening, stack, and pot-limit rules. There is no clamping or near-all-in rewrite. Equal integer targets deduplicate by target while preserving first-expression provenance.

Modes:

- Fixed retains every legal converted target.
- Dynamic evaluates every subset of requested cardinality from at most 10 distinct legal candidates, retains at most 5, fully re-solves each bounded tree, maximizes the selecting player's declared root EV, and breaks ties lexicographically by increasing target tuple.
- Automatic evaluates a deterministic documented candidate grid and chooses the smallest-cardinality subset whose EV is within caller-declared tolerance of the all-candidate tree; ties use the same order. The grid and every evaluated EV are returned.

Independent oracle: Decimal formula fixtures and exhaustive Python subset enumeration. Integer targets compare exactly; solved EV selection uses a tolerance declared by the fixture and justified by the solver iteration/error bound.

## 4. Tier-1 modules

### 4.1 Weighted range editor

New module: `src/poker_solver/ranges.py`.

The canonical internal representation is an ordered map from sorted explicit two-card combo to finite weight in `[0,1]`. It supports all 1,326 Hold'em combos and strict 169-class expansion (`AA`, `AKs`, `AKo`). Add, remove, and set-weight operations are atomic. Duplicate or overlapping text entries are rejected rather than order-dependently overwritten.

Formats:

- `poker-solver-range-v1`: canonical comma-separated explicit combos with explicit decimal weights. Class shorthand is accepted as input but export is lossless explicit-combo text.
- `poker-solver-range-library-v1`: strict JSON mapping validated names to ranges. Duplicate JSON keys are rejected. File saves use same-directory temporary write plus `os.replace`; names are identifiers, never paths.

Independent oracle: 169 classes expand to exactly 1,326 unique combos (6 per pair, 4 per suited class, 12 per offsuit class), and parse/export/parse preserves exact combo weights.

### 4.2 Heads-up preflop

New module: `src/poker_solver/preflop.py`.

`PreflopConfig` contains two seats, button, starting stacks, explicit forced posts, weighted ranges, finite sizing policy, betting mode, structural limits, and continuation. `PreflopState` implements the existing two-player `GameState` without modifying its protocol.

The root chance node enumerates compatible ordered private deals with probability proportional to the product of combo weights. Joint-deal collision filtering happens here. Information keys contain only own private cards plus public configuration/history/accounting; changing only the opponent's private cards cannot change a player's key.

The finite raise tree supports fold, check where legal, call, full raises, and exact short all-ins. A short all-in below a full raise does not reopen raising unless the explicit policy says the cumulative action reopens. Structural limits bound candidate actions, raises per street, chance leaves, and total audited nodes before solving.

Continuation choices:

- `all-in-runout`: exact exhaustive declared runouts to showdown after all players are all-in.
- `terminal-table`: exact caller-supplied payoff table keyed by public terminal and private deal, validated for complete coverage and zero-sum values where required.
- `checkdown-equity`: exhaustive declared runouts under no-further-betting; labeled approximate.

A non-all-in leaf without a continuation is invalid. Classic means exact traversal of the resulting finite model, not exact unrestricted poker.

Independent oracles: forced-post ledger; HU action-order fixture; pure fold/call/all-in values; exhaustive runout equity; information noninterference; chance probability normalization; tree audit; and brute-force best response on tiny trees.

### 4.3 Configuration-level tree editing

New module: `src/poker_solver/tree_edit.py`.

An edit targets a canonical public selector consisting of game kind/version, street, public board, public action history, and acting seat. It edits the action-generation configuration, never a mutable physical node. Supported operations add one action, remove one action, or replace the complete sizing set.

The selector must resolve, every resulting action must be legal at every matching occurrence, at least one action must remain, and all occurrences of an `InfoKey` must retain the same ordered actions. Rebuild must pass `collect_infosets` or the edit fails atomically.

Every structural edit invalidates root, regrets, average-policy sums, iteration count, cached EVs, tables, and locks whose action signatures changed. A fresh solver is mandatory. Live mutation and regret warm-start remapping are boundaries.

Independent oracle: rebuild an exact toy tree, enumerate reachable public selectors/action sets before and after, confirm unaffected branches are identical, and confirm stale locks fail.

### 4.4 Nodelocking and profiles

New module: `src/poker_solver/constraints.py`.

A nodelock maps a canonical key label, resolved against the exact root, to a complete distribution over that key's legal `Action` tuple. Validation rejects missing/extra actions, booleans, non-finite/negative probabilities, non-unit mass, wrong owner, unknown key, and stale fingerprint.

Constrained full-tree CFR is implemented in a new additive `ConstrainedCFRSolver`; the existing `CFRSolver` and `MCCFRSolver` are unchanged. At a locked key the fixed policy is used, regrets at that key are not updated, and average-policy accumulation records the fixed distribution. All unlocked keys adapt normally. Phase 3 does not promise MCCFR lock support unless separately implemented and audited.

A `BehaviorProfile` contains a target seat, a supplied complete baseline policy (or an explicitly selected uniform baseline), and finite non-negative multipliers for `fold`, `check`, `call`, and `aggressive`. For each target-seat information set:

`q(a) = p(a) * multiplier(category(a)) / sum_b p(b) * multiplier(category(b))`.

A zero denominator is invalid. The resolved `q` policies become exact locks for that seat. Named examples such as `maniac-demo` or `calling-station-demo` are transparent multiplier configurations, not population calibration claims. Outputs include baseline provenance, multipliers, resolved policy, constrained strategy, and actual chip EV evaluated on original returns.

Independent oracles: one-step matrix games with hand-computed locked best responses; exact exported lock adherence; brute-force constrained pure strategies; profile normalization and scale invariance; and actual-EV recomputation.

### 4.5 Opponent range inference

New module: `src/poker_solver/inference.py`.

The posterior is conditional on supplied behavioral likelihoods:

`P(h | a_1...a_T) proportional to w(h) * product_t L_t(h)`.

Board, hero cards, and explicit dead cards remove blocked combos before prior normalization. Likelihood sources are explicit solved policy, resolved nodelock/profile policy, or caller-supplied complete table. Missing likelihood coverage is an error. Updates use log-sum-exp; zero evidence fails without smoothing. Sequential and batch updates must agree.

Information noninterference is mandatory: a likelihood lookup may depend on candidate opponent combo and public history, but never on another player's hidden realization.

Independent oracle: manual two-combo Bayes calculation with rational probabilities, direct multiplication for short sequences, blocker enumeration, prior-scale invariance, impossible-evidence rejection, and permutation-deterministic output. Normal fixture tolerance is `1e-15` only where the exact arithmetic and operation order justify it.

### 4.6 Range and strategy tables

New module: `src/poker_solver/range_table.py`.

For a canonical public node and seat, the exact table enumerates compatible private deals and public paths. Each explicit combo row includes source weight, conditional reach, normalized range probability, legal actions where the seat acts, action probabilities, action EVs from forcing that action then following the supplied profile, and mixed EV. Opponent view uses the same engine and may omit actions when that opponent does not act at the selected node.

Aggregates are reach-weighted, never an unweighted mean:

- action frequency is `sum_h reach(h)*sigma(h,a) / sum_h reach(h)`;
- mixed EV is `sum_a sigma(h,a)*EV(h,a)`;
- class rows are weighted aggregations of their explicit combo rows.

Zero-reach rows are marked unavailable or omitted according to an explicit request option; a wholly unreachable node is an error. No NaN sentinel is emitted.

Independent oracle: manual tiny-river enumeration, raw-strategy reproduction, force-action EV identity, class-to-combo aggregation, own/opponent Bayes agreement, blockers, and root expected-value identity.

### 4.7 Three-way postflop

New modules: `src/poker_solver/nplayer.py` and `src/poker_solver/multiway.py`.

`NPlayerGameState` is a separate protocol with `num_players()` and `returns() -> tuple[float, ...]`. `NPlayerCFRSolver` implements synchronous full-tree regret updates using counterfactual reach `pi_chance * product(reach_j for j != i)`. It makes no general multiplayer Nash-convergence claim.

The executable poker state supports exactly three players, flop/turn/river starts, explicit weighted ranges, declared runouts, integer ledgers, folds/all-ins, finite wager targets, side pots, ties, odd chips, and optional rake. Action order is clockwise from the button among eligible seats; a round closes only after all nonfolded/non-all-in players have responded to the last full raise and matched or checked.

A generalized diagnostic is `sum_i (BR_i(sigma_-i) - u_i(sigma))`, computed only where exhaustive infoset-consistent best response is within configured limits. It is called generalized NashConv/unilateral-deviation sum, not exploitability.

Independent oracles: exhaustive three-seat terminal allocation, chance triple enumeration, permutation symmetry with corresponding odd-chip policy, information noninterference, utility-plus-rake conservation, and pure-strategy unilateral enumeration on a tiny three-player game.

## 5. Tier-2 bounded extensions

### 5.1 ICM and bounties

New modules: `src/poker_solver/icm.py` and `src/poker_solver/bounties.py`.

ICM accepts positive integer stacks and a non-increasing finite payout vector. Production uses subset dynamic programming for at most 10 players. Tests use an independent exact `Fraction` permutation enumerator. Equal stacks must be symmetric, probabilities/EVs conserve the payout pool, zero-stack players are placed/excluded by explicit policy, and malformed payouts fail.

Bounty support computes immediate one-hand cash transfers only:

- knockout bounty with explicit recipient/tie policy;
- PKO with caller-supplied immediate-cash and progressive fractions;
- TKO as an explicit transfer policy, not a brand-name assumption;
- Mystery bounty as either exact enumeration over a supplied finite prize distribution or its stated expectation.

One-hand tournament utility is post-hand ICM value minus pre-hand ICM value plus immediate bounty cash. Simultaneous-elimination and tie policies must be explicit. Full future bounty equity, field strategy, neural Future Game Simulation, and site-private rules are boundaries.

### 5.2 Classic and bounded rollout

New module: `src/poker_solver/engine.py`.

`classic` is a metadata-bearing dispatch to exact traversal of the configured finite game. `checkdown-equity` builds the bounded continuation described above and always emits `approximation: true`, `continuation_model: checkdown-equity`, cutoff description, and warning. `fast-ddls` fails closed with a stable documented-boundary error because no trained neural continuation model is shipped.

Exact identity tests compare Classic with direct legacy solver calls on the same root and compare checkdown rollout with Classic on a check-only continuation. A counterexample fixture proves that checkdown value can differ when future betting matters.

### 5.3 Game-structure extensions

Up-to-nine-seat configs, explicit straddles, limps, and cold-call histories are parsed, validated, accounted for, and can build structurally bounded trees. Phase 3 guarantees full strategic solving only for heads-up preflop and up-to-three-way postflop. Arbitrary 9-way strategic solving is a Tier-3 boundary.

## 6. Strict JSON v3 and CLI

New facade: `src/poker_solver/api_v3.py`. Existing `api.py` stays compatible; shared strict-number helpers may be imported but are not behaviorally changed.

Every operation has an exact top-level field set, integer schema version 3, finite strict numbers, booleans rejected in numeric fields, size limits checked before tree construction, duplicate-key-aware file loading, deterministic list ordering, and `allow_nan=False` serialization. Invalid input raises `ValueError`; the CLI prints `error: ...` to stderr and returns 2, matching existing behavior.

Programmatic operations and CLI subcommands:

| Feature | API v3 operation | CLI |
|---|---|---|
| Range editor/library | `load_range`, `edit_range`, `load_range_library` | `range-import`, `range-export`, `range-library` |
| Sizing | `convert_sizing`, `select_sizing` | `size-tree` |
| Preflop / engine | `load_preflop_config`, `solve_preflop` | `solve-preflop` |
| Tree editing | `apply_tree_edits` | `edit-tree` |
| Locks/profiles | `load_constraints`, `solve_constrained` | `solve-constrained` |
| Rake/accounting | `load_game_structure`, `settle_terminal` | `settle-hand` |
| Three-way | `load_multiway_config`, `solve_multiway` | `solve-multiway` |
| Range tables | `build_range_table` | `strategy-table` |
| Inference | `infer_range` | `infer-range` |
| ICM/bounties | `compute_icm`, `compute_bounty_utility` | `icm`, `bounty-value` |
| Presets | `load_phase3_preset`, `validate_phase3_preset` | `validate-preset`, `solve-preset` |

Shared-file ownership: only the parent integrator edits `src/poker_solver/cli.py`, `src/poker_solver/__init__.py`, README.md, SWARM_REPORT.md, and pyproject.toml. Feature workers own additive modules and exclusive tests.

Version-3 serialized strategies retain `poker-solver-strategy-v1` where the underlying key/action contract is compatible. New N-player strategies have a distinct format. Canonical public selectors and key labels are resolved against a rebuilt exact tree; they are not deserialized into arbitrary Python objects.

## 7. Canonical examples

Examples are executable synthetic inputs, never presolved strategy claims:

- `examples/phase3_btn_vs_bb_25bb.json`
- `examples/phase3_sb_vs_bb_15bb.json`
- `examples/phase3_three_way_river.json`
- `examples/phase3_ranges.json`
- `examples/phase3_exploitative.json`
- `examples/phase3_icm_bounty.json`
- `examples/phase3_checkdown_rollout.json`

Each includes stable provenance text and `accuracy_claim: "synthetic input fixture; no equilibrium chart claim"`. No timestamps or authenticated/product-private URLs enter deterministic output.

## 8. Implemented-versus-boundary matrix

| Capability | Tier | Phase 3 disposition | Module | Acceptance reference |
|---|---:|---|---|---|
| HU preflop postings, positions, raise tree | 1 | Implement bounded exact tree | `preflop.py` | ledger + pure-strategy/runout oracle |
| Fixed sizing and `%/e/x/bb` units | 1 | Implement | `sizing.py` | Decimal formula fixtures |
| Dynamic sizing | 1 | Implement exhaustive bounded subset search | `sizing.py` | independent subset enumeration |
| Automatic sizing | 1 | Implement transparent deterministic bounded grid | `sizing.py` | all-grid EV/tolerance oracle |
| Weighted range editor | 1 | Implement all 1,326 combos | `ranges.py` | 169-class combinatorics + round trip |
| Named range save/load/import/export | 1 | Implement versioned strict formats | `ranges.py` | byte-stable round trip |
| Tree/node editing | 1 | Implement config rebuild by public selector | `tree_edit.py` | before/after tree enumeration |
| Nodelocking | 1 | Implement complete InfoKey distributions | `constraints.py` | matrix constrained-BR oracle |
| Player profiles | 1 | Implement transparent baseline-policy multipliers | `constraints.py` | normalization + brute-force BR |
| Rake | 1 | Implement rational policy, cap and rounding | `game_structure.py` | exact integer conservation |
| Three-way postflop | 1 | Implement finite 3-player tree | `multiway.py`, `nplayer.py` | terminal/pure-strategy enumeration |
| Own/opponent range tables | 1 | Implement combo/class action EV tables | `range_table.py` | raw-strategy and EV identities |
| Opponent range inference | 1 | Implement blocker-first log-space Bayes | `inference.py` | manual Bayes oracle |
| Strict JSON and CLI for Tier 1 | 1 | Implement additively | `api_v3.py`, parent CLI edit | strict rejection + smoke matrix |
| Stack/blind/ante/straddle ledger | 2 | Implement up to 9 seats | `game_structure.py` | exact posting/conservation oracle |
| Limp/cold-call bounded tree representation | 2 | Implement structural configs and tiny fixtures | preflop/game structure | action-order enumeration |
| ICM | 2 | Implement exact small-field, max 10 | `icm.py` | Fraction permutation oracle |
| PKO/TKO/Mystery bounties | 2 | Implement immediate one-hand accounting | `bounties.py` | exact pool conservation |
| Classic engine | 2 | Implement exact configured-tree dispatch | `engine.py` | direct solver identity |
| Checkdown depth-limited rollout | 2 | Implement labeled approximation | `engine.py` | check-only identity + counterexample |
| Full future-bounty strategy | 2/3 | Document boundary | docs | no unsupported output |
| Up-to-9-way strategic preflop solve | 3 | Configuration/accounting only; solver boundary | docs | explicit rejection/limit test |
| More than 3-way postflop | 3 | Document boundary | docs | explicit rejection |
| PLO | 3 | Document boundary | docs | explicit rejection |
| Neural Fast/DDLS value approximation | 3 | Document boundary; `fast-ddls` fails closed | `engine.py` | stable boundary test |
| Full presolved spot library / product charts | 3 | Synthetic examples only | `examples/` | provenance assertions |
| Proprietary GTO Wizard sizing/profile behavior | 3 | No parity claim | docs | accuracy-label assertions |

## 9. Implementation batches and mandatory audit gates

No later implementation batch may start until a fresh non-author BryantGPT review wave has accepted the preceding batch. Authors from a batch cannot provide its required sign-off. A code or test edit after audit starts invalidates affected verdicts and requires focused retest plus fresh review.

### Batch C1: independent pure foundations

Parallel owners:

1. `game_structure.py` + `tests/test_game_structure.py` (including rake)
2. `sizing.py` + `tests/test_sizing.py`
3. `ranges.py` + `tests/test_ranges_phase3.py`
4. `icm.py` + `tests/test_icm.py`
5. `bounties.py` + `tests/test_bounties.py`

Parent gate: focused tests, all 185 regression tests, exact fixture review.

Audit A1: fresh reviewers independently attack ledger conservation/side pots/rake, every sizing formula and subset tie, all 1,326 range expansion, Fraction ICM, bounty conservation, strict invalid values, and API independence. Reports go under `review/phase3/c1-*`. Fix and re-audit until zero blockers.

### Batch C2: game and constraint cores

Parallel owners:

1. `preflop.py` + `tests/test_preflop.py`
2. `nplayer.py` + `tests/test_nplayer.py`
3. `multiway.py` + `tests/test_multiway_phase3.py`
4. `constraints.py` + `tests/test_constraints.py`
5. `inference.py` + `tests/test_inference.py`
6. `tree_edit.py` + `tests/test_tree_edit.py`

Parent gate: tree audit, noninterference tests, tiny pure-strategy oracles, focused and full suite.

Audit A2: different non-authors attack action order/reopening, hidden-card leakage, N-player counterfactual reach, side pots/folds/ties, lock accumulation, profile conditioning, Bayes zero evidence, edit invalidation, and integration with C1. Reports `review/phase3/c2-*`; converge before C3.

### Batch C3: derived views, engine, and v3 facade

Parallel owners:

1. `range_table.py` + `tests/test_range_table.py`
2. `engine.py` + `tests/test_engine_phase3.py`
3. `api_v3.py` + `tests/test_api_v3.py`
4. canonical example JSON + `tests/test_phase3_examples.py`
5. deterministic/benchmark oracle scripts + tests

Parent alone integrates CLI and exports after all owners finish. Parent gate runs every new command, strict malformed input cases, deterministic repeated outputs, focused tests, and full pytest.

Audit A3: fresh non-authors attack table EV/reach identities, Classic/checkdown labels, every v3 schema, every CLI command, old API byte compatibility, examples, size limits, and benchmarks. Reports `review/phase3/c3-*`; converge before documentation/final review.

### Batch C4: documentation integration

Parent updates README and SWARM_REPORT and finalizes boundary/error text. Because this batch changes no solver semantics, it still receives a fresh audit A4 for feature-matrix truthfulness, executable command examples, provenance, and stale claims. Any code change discovered here returns to the affected prior audit gate.

## 10. Verification ladder

After each author batch:

1. read every owned source and test file;
2. run focused tests for the batch;
3. run `uv run pytest -m 'not slow' -q` when available;
4. run `uv run pytest -q` before audit acceptance;
5. dispatch the non-author adversarial wave;
6. reproduce every claimed blocker parent-side;
7. fix confirmed blockers with exclusive ownership;
8. rerun affected focused/full gates and a clean non-author review.

Final accuracy gates:

- exact integer ledger/rake/side-pot conservation;
- exhaustive 1,326-combo range expansion;
- Decimal sizing conversion and subset enumeration agreement;
- preflop and three-way tiny-game pure-strategy oracles;
- locked matrix-game best response;
- manual Bayes posterior;
- range-table raw strategy/action-EV aggregation identities;
- Fraction ICM and bounty-pool conservation;
- Classic direct-call identity and honest rollout counterexample;
- deterministic same-platform JSON and seeded MCCFR tests;
- all Phase 1+2+3 tests green.

Provider policy: use width 12 after the repeated Wave B HTTP 502; retry a BryantGPT provider failure once, then reduce to 10 only after another observed 502/503. Every failure, retry, accepted artifact, test receipt, and audit disposition is recorded in PROGRESS.md.

## 11. Definition of done

Phase 3 is complete only when the matrix matches the live implementation, every implemented feature has strict JSON and CLI access, every module has an independent oracle and non-author sign-off, all confirmed blockers are fixed and cleanly re-reviewed, all 185 prior tests plus new tests pass, examples execute, README and SWARM_REPORT are current, and no boundary is presented as implemented parity.
