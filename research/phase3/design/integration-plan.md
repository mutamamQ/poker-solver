# Phase 3 Integration and Audit Plan

## Mission alignment

This plan implements the Wave B architecture only. It defines dependency-safe implementation sub-batches with exclusive source/test ownership, shared-file parent integration points, mandatory fresh non-author adversarial audits after each sub-batch, exact acceptance/oracle/tolerance gates, API compatibility hazards, deterministic/benchmark/documentation gates, and the 14→12→10 retry policy only for observed 502/503.

**Hard rule:** A batch is not "done" until a non-author adversarial wave signs off. No later feature batch may start before the preceding audit passes.

## Baseline state

- Working directory: `/home/genomix-node/poker-solver`
- Baseline: 185 tests green (Phase 1 = 80, Phase 2 = 105)
- Existing modules: 15 source files, 17 test files
- Shared integration surfaces: `api.py`, `cli.py`, `model.py`, `best_response.py`
- All prior tests must stay green

## Implementation sub-batches

### Batch 1: Core sizing and range foundations

**Exclusive ownership:**

- `src/poker_solver/sizing.py` (new)
- `src/poker_solver/range_editor.py` (new)
- `tests/test_sizing.py` (new)
- `tests/test_range_editor.py` (new)

**Shared integration points (parent only):**

- None yet; these are leaf modules

**Acceptance gates:**

1. All 185 baseline tests remain green
2. Sizing formula fixtures (pot-percent, geometric, previous-bet-multiple, big-blinds, all-in) match hand-calculated Decimal oracle within exact integer target equality
3. Geometric conservation: for integer-friendly `(P,S,n)` fixtures, simulated bet/call rounds match formula within `1e-12`
4. Legality boundaries: exact min-raise accepted, one chip below rejected unless exact short all-in, exact stack accepted, one chip above rejected
5. Deduplication: distinct expressions → same integer target produce one action; targets one chip apart remain distinct
6. Fixed invariant: no legal configured target is pruned
7. Dynamic oracle: on tiny game with ≤5 candidates, selected subset and EV match independent brute-force enumerator within `1e-12` (exact games) or fixture-specific predeclared tolerance (iterative CFR)
8. Cross-mode identities: Dynamic with `N==candidate_count` equals Fixed; Automatic with `max_sizes==candidate_count` and zero EV tolerance matches full-tree EV within declared solver tolerance
9. Order/determinism: candidate input permutation cannot change selected integer targets, measured EVs, or canonical JSON
10. API rejection: malformed units, booleans, NaN/infinity, unsupported geometric context, impossible retained counts, combinatorial limits fail with status 2
11. Range combinatorics: expanding all 169 classes yields exactly 1,326 unique combos (pair 78, suited 312, offsuit 936)
12. Single classes: `AA` yields 6, `AKs` yields 4, `AKo` yields 12 with exact expected cards
13. Range parser rejection: duplicate/overlapping entries, lowercase, shorthand, malformed decimal, bool JSON weights, out-of-range weights fail
14. Range round-trip: text import → canonical explicit export → import is exactly equal
15. Range library round-trip: save/load is object-equal and byte-deterministic; duplicate JSON keys fail
16. Blocker fixture: `AsKd` against `AA,AKs,AKo` leaves exactly 12 independently enumerated combos

**Tolerance:** `1e-12` absolute for arithmetic; exact integer equality for targets/counts; fixture-specific predeclared tolerance for iterative CFR Dynamic mode

**Oracle references:**

- Hand-calculated Decimal arithmetic for sizing formulas
- Independent brute-force subset enumerator for Dynamic mode
- Exhaustive combo enumeration for range operations
- Treys/existing equity fixtures for blocker validation

**API compatibility hazards:** None; new modules

**Determinism gates:**

- Canonical JSON output sorted and deterministic
- Input permutation cannot change output
- Same seed/input → byte-identical output

**Benchmark gates:** None required for pure computation modules; measure and record baseline for future regression detection

**Documentation gates:**

- Docstrings for all public functions
- Module-level contract documentation
- Explicit rounding policy documented
- Unit semantics and formulas documented

**Mandatory adversarial audit after Batch 1:**

- Dispatch fresh non-author BryantGPT subagents (not the Batch 1 implementers)
- Audit scope: run all tests, attack sizing formula edge cases, verify Dynamic subset selection correctness, cross-check range blocker arithmetic
- Audit deliverable: `review/phase3/batch1-audit.md` with reproduction for any confirmed bug
- Batch 1 is not "done" until audit passes
- No Batch 2 work may start before audit sign-off

---

### Batch 2: Game structure, accounting, and N-player protocol

**Exclusive ownership:**

- `src/poker_solver/game_structure.py` (new)
- `src/poker_solver/nplayer_protocol.py` (new)
- `tests/test_game_structure.py` (new)
- `tests/test_nplayer_protocol.py` (new)

**Shared integration points (parent only):**

- `model.py`: add N-player protocol alongside existing two-player protocol (parent integrates)

**Acceptance gates:**

1. All 185 baseline tests + Batch 1 tests remain green
2. Blind/action order: HU stacks `(2500,2500)`, SB 50, BB 100, no ante → root pot 150, remaining `(2450,2400)`, commitments `(50,100)`, BTN acts first
3. Ante ledgers: per-player 10 produces postings `(60,110)` and pot 170; total ante 20 produces same; BB ante 20 produces `(50,120)` and pot 170
4. Limp/check: BTN call-to 100 pays 50; BB check closes with total contributions `(100,100)` and pot 200
5. Fold: BTN immediate fold → awards `(0,150)`, returns `(-50,+50)` under pre-posting baseline
6. Raise increments: BTN raise-to 300 has increment 200 over BB 100; BB next full raise ≥500
7. Unmatched all-in: stacks `(5000,10000)` after forced postings → at most 5000 from each contested; BB excess returned; no-rake returns sum exactly zero
8. Chance enumeration: root pair identities/weights match independent `itertools.product` blocker oracle
9. Information noninterference: changing only BB hidden hand leaves BTN key/actions unchanged; changing public raise changes key
10. Conservation: `sum(stacks) + sum(committed) == initial_total` at every nonterminal; `sum(final_stacks) + house_rake == initial_total` terminally
11. Side-pot layer oracle: hand-written contribution/status/strength fixtures cover equal contributions, one/two side pots, folded dead money, unmatched excess, two-way/three-way ties, odd chips
12. Three-player conservation: no-rake terminal returns sum exactly to zero; with rake, player returns + operator rake sum to zero
13. Three-player permutation symmetry: relabel seats/button/ranges/strengths together → chance mass, terminal awards, EVs rotate exactly
14. Action rotation: hand-enumerated traces verify skips over folded/all-in seats, round closure, short-all-in reopening, immediate termination with one survivor
15. Three-player chance oracle: independently enumerate compatible range triples with `itertools.product`; compare identities and normalized weights within `1e-12`
16. Showdown evaluator: reuse exhaustive/equity evidence from Phases 1–2
17. Information noninterference (3-way): states differing only in another seat's private cards have same acting-player key and legal actions

**Tolerance:** Exact integer equality for chip accounting; `1e-12` absolute for probabilities

**Oracle references:**

- Hand-calculated ledger arithmetic
- Independent `itertools.product` for chance enumeration
- Existing Phase 1/2 evaluator/equity fixtures

**API compatibility hazards:**

- New N-player protocol must not break existing two-player `GameState` semantics
- Existing `returns() -> tuple[float,float]` stays unchanged for two-player games
- New protocol uses `returns() -> tuple[float, ...]` of length `num_players()`

**Determinism gates:**

- Chance outcomes in deterministic order
- Canonical action ordering
- Deterministic odd-chip allocation under explicit priority

**Benchmark gates:** Measure and record baseline for future regression

**Documentation gates:**

- Ante mode semantics documented
- Action-order rules documented
- Amount-to accounting documented
- Side-pot algorithm documented
- Conservation invariants documented

**Mandatory adversarial audit after Batch 2:**

- Dispatch fresh non-author BryantGPT subagents
- Audit scope: run all tests, attack accounting edge cases, verify conservation at every transition, cross-check side-pot layer construction, verify N-player protocol compatibility
- Audit deliverable: `review/phase3/batch2-audit.md`
- Batch 2 is not "done" until audit passes
- No Batch 3 work may start before audit sign-off

---

### Batch 3: Preflop game and three-way postflop game

**Exclusive ownership:**

- `src/poker_solver/preflop.py` (new)
- `src/poker_solver/three_way.py` (new)
- `tests/test_preflop.py` (new)
- `tests/test_three_way.py` (new)

**Shared integration points (parent only):**

- `game_structure.py`: compose with preflop/three-way state (parent integrates)
- `sizing.py`: compose with action generation (parent integrates)
- `range_editor.py`: compose with chance deals (parent integrates)

**Acceptance gates:**

1. All baseline + Batch 1 + Batch 2 tests remain green
2. Preflop blind/action order oracle (from Batch 2 fixtures)
3. Preflop ante ledgers (from Batch 2 fixtures)
4. Preflop limp/check/fold/raise (from Batch 2 fixtures)
5. Preflop chance enumeration (from Batch 2 fixtures)
6. Preflop information noninterference (from Batch 2 fixtures)
7. All-in equity: tiny exact-combo all-in games compare integer win/tie/loss runout counts against existing Treys fixtures/oracle
8. Continuation completeness: omit one deal/history table leaf → assert fail-closed; exact table values reproduce hand-solved tiny normal-form game
9. Checkdown identity: where supplied table is independently generated by exact checkdown equity, table and checkdown modes agree within `1e-12`
10. Approximation disclosure: checkdown output has `approximation:true`; table output names provenance; all-in-runout is exact for declared runouts
11. Solver oracle: vanilla CFR on deliberately tiny preflop/table game compared with exhaustive infoset-consistent best response; committed fixture sets convergence threshold from independently solved game
12. Sizing integration: generated legal actions match sizing module targets exactly; Dynamic with all candidates equals Fixed
13. Determinism/limits: input ordering cannot change canonical output; limit and limit+1 cases tested
14. Three-way pot-layer table oracle (from Batch 2 fixtures)
15. Three-way conservation (from Batch 2 fixtures)
16. Three-way permutation symmetry (from Batch 2 fixtures)
17. Three-way action rotation (from Batch 2 fixtures)
18. Three-way chance oracle (from Batch 2 fixtures)
19. Three-way information noninterference (from Batch 2 fixtures)
20. Three-player Kuhn/reference game: implement or adapt tiny known game; compare full-tree expected values and unilateral BR values with independent OpenSpiel script
21. Three-player CFR equations: on one-step three-player game, calculate one iteration's reaches/regret deltas by hand; compare within `1e-12`
22. Exact certificate: trivial dominance-solvable three-player game reaches generalized NashConv below predeclared fixture threshold
23. Two-player regression: all existing Phase 1/2 strategy values, APIs, and 185 tests unchanged
24. Limits: oversized explicit deal products, runout lists, action trees, or BR strategy products fail before expensive traversal with tested messages

**Tolerance:** `1e-12` absolute for arithmetic; exact integer equality for chip accounting; fixture-specific predeclared tolerance for iterative convergence

**Oracle references:**

- Existing Treys fixtures for all-in equity
- Hand-solved tiny normal-form games for continuation tables
- Independent OpenSpiel script for three-player reference game
- Hand-calculated CFR iteration for three-player equations

**API compatibility hazards:**

- New preflop/three-way games must use N-player protocol
- Existing two-player APIs unchanged
- Version-3 API must not break version-1/version-2

**Determinism gates:**

- Canonical JSON output
- Same seed/input → byte-identical output for deterministic solvers
- Seeded MCCFR repeatable on same interpreter/platform

**Benchmark gates:** Measure and record baseline for tiny fixtures; no performance claims for large trees

**Documentation gates:**

- Continuation mode semantics documented
- Preflop terminal-value boundary documented
- Three-way generalized NashConv semantics documented
- Approximation labels documented

**Mandatory adversarial audit after Batch 3:**

- Dispatch fresh non-author BryantGPT subagents
- Audit scope: run all tests, attack preflop continuation-value edge cases, verify three-way CFR regret updates, cross-check generalized NashConv computation, verify two-player regression
- Audit deliverable: `review/phase3/batch3-audit.md`
- Batch 3 is not "done" until audit passes
- No Batch 4 work may start before audit sign-off

---

### Batch 4: Tree editing, nodelocks, and profiles

**Exclusive ownership:**

- `src/poker_solver/tree_editor.py` (new)
- `src/poker_solver/nodelock.py` (new)
- `src/poker_solver/profiles.py` (new)
- `tests/test_tree_editor.py` (new)
- `tests/test_nodelock.py` (new)
- `tests/test_profiles.py` (new)

**Shared integration points (parent only):**

- `cfr.py`: extend to support nodelocks and profiles (parent integrates)
- `mccfr.py`: extend to support nodelocks and profiles (parent integrates)

**Acceptance gates:**

1. All baseline + Batch 1–3 tests remain green
2. Tree-edit validation: selector resolves to ≥1 reachable decision; all resolved occurrences belong to same public decision class; generated occurrences with same `InfoKey` retain identical ordered action tuples; action kinds/amounts legal at every resolved occurrence; no duplicate `Action` values; ≥1 action remains; child can be generated for each action; every existing nodelock targeting changed action tuples rejected or explicitly remapped
3. Rebuilt root passes `collect_infosets` consistency check
4. Training-state invalidation: all solver state invalidated after any structural edit
5. Tree editing atomic: validation builds candidate root; failure leaves prior configuration/solution untouched
6. Exact lock validation: key exists and has declared owner; keys in distribution equal complete legal action set; every probability finite and in `[0,1]`; probabilities sum to one within documented tolerance; impossible/unreachable keys rejected during setup
7. CFR lock semantics: at locked information set, every traversal uses fixed distribution instead of regret matching; regret updates for locked owner at that information set skipped; strategy sums accumulate locked distribution with same owner-reach weighting
8. Exact oracle (one-step zero-sum matrix game): lock P1 to `X:1,Y:0` → P0 unique best response `A:1`; lock P1 to `Y:1` → P0 unique best response `B:1`; expectations obtained directly from payoff table; compare with CFR output and exhaustive pure-strategy best response
9. Exact exported locked frequencies, unchanged locks over repeated training calls, malformed-distribution rejection, tree-edit invalidation
10. Profile contract: seat assigns finite incentive coefficient for each supported action category (check, call, fold, aggressive); unknown action kinds fail validation; coefficients explicit inputs
11. Shaped-game solution: player's shaped terminal utility = actual terminal utility + sum(profile bonuses on that player's path); solver trains against shaped utilities
12. Reported poker EV recomputed from final strategy using original unshaped terminal returns; reports expose both `actual_ev` and optional `profile_objective` (clearly labeled virtual)
13. Exact nodelocks take precedence over profile optimization at same information set
14. Profile oracle (one-player choice): actual payoffs `check=0`, `call=-1`, reference pot 10; no profile → unique choice check; call coefficient `0.2` → shaped call payoff `1`, unique shaped choice call; exported actual EV under call policy `-1`, shaped EV `1`
15. Two-player matrix fixture: unprofiled opponent adapts to profile-shaped policy; exhaustive enumeration agrees with bounded solver
16. Serialization: saved configuration includes schema version, deterministic selectors, exact actions, exact locks, profile coefficients, precedence; serialization order canonical; loading validates against freshly built game; stale keys/actions produce structured error
17. Solution metadata records: game/configuration fingerprint, structural edit set, active locks/profiles, iteration count/solver mode, whether values actual or shaped
18. Solution fingerprint mismatch prevents applying old strategies/locks/convergence metadata to edited game
19. Failure tests: strictly reject selectors resolving to no target or heterogeneous legal decisions; edits creating illegal/empty/inconsistent action sets; lock on physical private-history occurrence instead of valid `InfoKey`; missing/extra actions, NaN/infinite/negative probabilities, non-unit lock sums; stale lock keys after edit; NaN/infinite profile coefficients or unsupported action categories; attempts to report shaped value as actual EV; attempts to reuse trained state after structural edits

**Tolerance:** `1e-12` absolute for probabilities; exact equality for action tuples

**Oracle references:**

- Hand-solved one-step zero-sum matrix game for nodelocks
- Hand-solved one-player choice for profiles
- Exhaustive pure-strategy best response for cross-check

**API compatibility hazards:**

- Extending `cfr.py` and `mccfr.py` must not break existing solver behavior when no locks/profiles active
- Existing Phase 1/2 solve outputs unchanged when locks/profiles absent

**Determinism gates:**

- Canonical serialization order
- Deterministic selector resolution
- Byte-identical output for same configuration

**Benchmark gates:** Measure and record baseline; lock/profile overhead should be negligible per visited information set

**Documentation gates:**

- Tree-edit semantics documented
- Nodelock CFR semantics documented
- Profile shaped-game semantics documented
- Precedence rules documented
- Actual vs shaped EV distinction documented

**Mandatory adversarial audit after Batch 4:**

- Dispatch fresh non-author BryantGPT subagents
- Audit scope: run all tests, attack tree-edit validation, verify lock adherence in CFR traversal, verify profile bonus accumulation, cross-check actual vs shaped EV separation, verify training-state invalidation
- Audit deliverable: `review/phase3/batch4-audit.md`
- Batch 4 is not "done" until audit passes
- No Batch 5 work may start before audit sign-off

---

### Batch 5: Range tables and opponent inference

**Exclusive ownership:**

- `src/poker_solver/range_tables.py` (new)
- `src/poker_solver/opponent_inference.py` (new)
- `tests/test_range_tables.py` (new)
- `tests/test_opponent_inference.py` (new)

**Shared integration points (parent only):**

- `range_editor.py`: compose with range tables (parent integrates)
- `cfr.py`/`mccfr.py`: compose with strategy extraction (parent integrates)

**Acceptance gates:**

1. All baseline + Batch 1–4 tests remain green
2. Range table semantics: for each compatible explicit hand, report source range weight, conditional reach/matchup mass, normalized conditional probability, action strategy probabilities and conditional action EVs (if player acts), mixed hand EV
3. Aggregation identities: each displayed acting-hand action distribution sums to one within `1e-12`; each hand mixed EV equals dot product of action probabilities and action EVs within `1e-12`; aggregate frequency for action `a` is `sum_h reach(h)*sigma(h,a) / sum_h reach(h)`; aggregate EV matchup/reach-weighted; when selected node is root and same payoff baseline used, aggregating per-hand EVs reproduces raw `expected_values` within `1e-12`; class rows equal weighted aggregation of explicit child combos
4. Bayes/action split: prior combo masses multiplied by observed action probabilities produce expected action-specific range; sums match inference module
5. Tiny tree table: enumerate every terminal manually; compare each hand/action EV and mixed EV within `1e-12`
6. Raw-strategy identity: per-hand action rows exactly reproduce corresponding raw information-set policy
7. Aggregation: own and opponent explicit rows independently aggregate to raw root EV and action frequencies within `1e-12`
8. Noninterference: changing only opponent hidden hand may change terminal strength but never acting player's information key or legal action tuple
9. Unreachable node: zero conditional mass fails clearly; must not emit NaN rows
10. Inference manual Bayes: prior `(h1=1/4,h2=3/4)`, likelihood `(1,1/3)` → unnormalized masses `(1/4,1/4)`, evidence probability `1/2`, posterior `(1/2,1/2)`
11. Zero likelihood: prior `(1/2,1/2)`, likelihood `(0,1)` → posterior `(0,1)`, not error
12. Impossible evidence: all likelihoods zero raises specific impossible-evidence error
13. Sequential identity: prior `(1/2,1/2)`; step 1 `(4/5,1/5)` → `(4/5,1/5)`; step 2 `(1/4,1)` → equal unnormalized mass `(1/5,1/5)`, posterior `(1/2,1/2)`; one-pass products match exactly in rational oracle, within tolerance in floats
14. Prior scale: replacing weights `(1,3)` with `(10,30)` cannot change posterior bytes after canonical float serialization
15. No observations: output is blocker-filtered normalized prior
16. Underflow: equal priors with two likelihood steps of `1e-200` for both hands → `(1/2,1/2)` via log space rather than impossible evidence
17. Asymmetric underflow: log masses differing by `log(2)` → posterior `(1/3,2/3)` even when raw products underflow
18. Blocker oracle: with hero `AsKd` and opponent range `AA,AKs,AKo`, exactly 12 explicit combos survive; posterior normalization uses only those 12
19. Action split identity: for every hand, prior mass times raw strategy action probability equals unnormalized posterior mass reported for that action
20. Class reduction: summed explicit posterior equals 1; class sums equal explicit child sums and also total 1
21. Strategy integration: on tiny game, deriving likelihoods from raw policies equals low-level explicit likelihood-table result within `1e-15`
22. Information noninterference: swapping unobserved opponent card can select different opponent policy row only through opponent's own information key; cannot alter another actor's information key at same public history
23. Permutation determinism: permuting input combo or likelihood-table order cannot change canonical output

**Tolerance:** `1e-12` absolute for range tables; `1e-15` absolute for inference (tighter due to log-space stability)

**Oracle references:**

- Hand-enumerated tiny tree for range table validation
- Hand-calculated Bayes updates for inference
- Rational arithmetic oracle for sequential updates

**API compatibility hazards:**

- Range tables must work with existing Phase 1/2 strategies
- Inference must work with existing Phase 1/2 game states

**Determinism gates:**

- Canonical combo ordering
- Deterministic aggregation
- Permutation-invariant output

**Benchmark gates:** Measure and record baseline; table generation should be linear in compatible combos

**Documentation gates:**

- Range table semantics documented
- Aggregation formulas documented
- Inference Bayes model documented
- Log-space stability documented
- Conditional-on-model warning documented

**Mandatory adversarial audit after Batch 5:**

- Dispatch fresh non-author BryantGPT subagents
- Audit scope: run all tests, attack range table aggregation, verify inference Bayes arithmetic, cross-check log-space stability, verify blocker conditioning
- Audit deliverable: `review/phase3/batch5-audit.md`
- Batch 5 is not "done" until audit passes
- No Batch 6 work may start before audit sign-off

---

### Batch 6: Rake and ICM/bounty evaluators

**Exclusive ownership:**

- `src/poker_solver/rake.py` (new)
- `src/poker_solver/icm.py` (new)
- `src/poker_solver/bounty.py` (new)
- `tests/test_rake.py` (new)
- `tests/test_icm.py` (new)
- `tests/test_bounty.py` (new)

**Shared integration points (parent only):**

- `game_structure.py`: compose with rake accounting (parent integrates)
- Terminal utility computation: compose with ICM/bounty (parent integrates)

**Acceptance gates:**

1. All baseline + Batch 1–5 tests remain green
2. Rake fixtures (from game-structure-rake.md): HU initial stacks 100/100, SB 1, BB 2, SB raises to 6, BB calls → pot 12, stacks 94/94; at 5% floor rake cap 3 after flop, rake 0, awardable pot 12; conservation `188+12=200` before settlement, final player stacks sum to 200
3. Same fixture with rate 1/10, ceiling rounding, cap 3 → rake 2, awardable pot 10; final player stacks + house rake = 200
4. Three-way final contributions 100/300/300; 5% floor rake cap 5 → gross pot 700, rake 5, net awards 695; if C wins both layers, final settlement awards C 695; utilities + rake conserve exactly
5. NFND: matched preflop pot 17 with 5% ceiling rate and no cap → rake 0 when `no_flop_no_drop=true`; same policy with `false` → rake 1
6. Uncalled excess: contributions A:100, B:300 after all others fold/cannot match beyond 100 → return 200 to B; matched pot 200, rake uses 200 not 400
7. Exact forced-posting debits in every ante mode, including short stacks
8. Full-ring, heads-up, and straddled preflop order
9. No double counting across raise-to/call sequences
10. Short all-in reopening behavior
11. Exact layer construction, folded-player exclusion, uncalled refunds
12. Rational rake with every rounding mode, cap, minimum, NFND branch
13. Hand rake computed once, layer deductions sum to it
14. Deterministic odd-chip payouts under injected priority
15. Conservation at every transition, `sum(utilities) == -rake` terminally
16. Invalid configurations rejected before tree construction
17. ICM fixtures: stacks `(1,1)`, payouts `(100,0)` → equities `(50,50)`; stacks `(1,1,1)`, payouts `(100,60,30)` → each `190/3`, total `190`; stacks `(50,30,20)`, payouts `(100,60,0)` → `(985/14,105/2,260/7)`, total `160`; stacks `(2,1,1)`, payouts `(100,60,20)` → `(220/3,160/3,160/3)`, total `180`
18. Production float output agrees with Fraction permutation oracle within `1e-12`
19. Equities sum to payout pool within `1e-12`
20. Equal stacks produce equal equities; seat permutation only permutes output
21. Common stack scaling leaves output unchanged within `1e-12`
22. Bounty conservation: KO bounty 100, one recipient → immediate cash 100, eliminated head 0, total conserved; KO split bounty 101, shares `(1/2,1/2)` with integer minor units requires explicit odd-unit recipient, no floating loss; PKO half example `b=80`, `f=1/2` → cash 40, recipient head increase 40; PKO configurable `b=100`, `f=1/4`, shares `(3/4,1/4)` → total immediate cash 25, head increases 75, each apportioned exactly by shares
23. PKO winner: winner-self-bounty unlock applied only when explicit
24. TKO: zero placement payouts + KO awards; total declared tournament value equals cumulative bounty cash + live bounty heads under declared transfer model
25. Mystery mean: awards `(10,10,80)` with equal probabilities → expected award `100/3`; exact Fraction oracle and float differ by at most `1e-12`
26. Mystery without replacement: after drawing 80, remaining distribution `(10,10)` with mean 10; probabilities and value conserved exactly
27. Multiple eliminations: each eliminated player maps to independently validated recipient-share vector; no bounty awarded twice
28. One-hand tournament utility: `u_i = ICM(post)_i - ICM(pre)_i + immediate_cash_i`; sum of `ICM(post)-ICM(pre)` is zero when same remaining payout pool represented on both sides

**Tolerance:** Exact integer equality for chip accounting; `1e-12` absolute for ICM equity and probabilities

**Oracle references:**

- Hand-calculated rake fixtures
- Independent Fraction permutation enumeration for ICM
- Hand-calculated bounty conservation

**API compatibility hazards:**

- Rake composition with existing game states must preserve chip conservation
- ICM/bounty evaluators are new utilities, no existing API conflict

**Determinism gates:**

- Deterministic rake rounding
- Deterministic odd-chip allocation
- Deterministic ICM computation

**Benchmark gates:** Measure and record baseline; ICM subset DP should be tractable for tested limits

**Documentation gates:**

- Rake policy semantics documented
- ICM assumptions documented
- Bounty format semantics documented
- Conservation invariants documented

**Mandatory adversarial audit after Batch 6:**

- Dispatch fresh non-author BryantGPT subagents
- Audit scope: run all tests, attack rake accounting edge cases, verify ICM permutation oracle agreement, cross-check bounty conservation, verify composition with game structure
- Audit deliverable: `review/phase3/batch6-audit.md`
- Batch 6 is not "done" until audit passes
- No Batch 7 work may start before audit sign-off

---

### Batch 7: Engine modes and API v3 integration

**Exclusive ownership:**

- `src/poker_solver/engine_modes.py` (new)
- `tests/test_engine_modes.py` (new)

**Shared integration points (parent only):**

- `api.py`: extend with version-3 endpoints (parent integrates)
- `cli.py`: extend with version-3 commands (parent integrates)

**Acceptance gates:**

1. All baseline + Batch 1–6 tests remain green
2. Classic equals legacy exact tree: on Kuhn and existing tiny river/multistreet fixtures, `classic` produces same strategy serialization, values, NashConv as direct `CFRSolver` for same iterations; deterministic fields byte-identical
3. No-cutoff identity: depth-limited evaluator whose boundary at or below every terminal equals Classic exactly
4. Checkdown identity: on game where all future nodes have only `CHECK`/chance actions, `depth-limited-equity-rollout` at start of remaining streets equals exact Classic value within `1e-12`
5. Heuristic counterexample: ship tiny game with strategically meaningful future bet where checkdown equity and exact continuation value differ; test proves approximation not mislabeled as exact or Fast parity
6. Unsupported Fast fails closed: strict JSON and CLI requests for `fast-ddls` return validation/usage status 2 and stable message explaining trained continuation values not shipped; unknown mode names and booleans also fail
7. Metadata honesty: Classic has `approximation:false`; equity rollout has `approximation:true`; unsupported Fast never emits result object
8. Monotonicity not required: tests must not assert per-iteration monotonic NashConv for vanilla CFR
9. Cross-module preservation: existing Phase 1/2 solve requests (omit `engine_mode`) retain previous schema and behavior
10. Version-3 API strict validation: unknown fields, duplicate JSON keys, bool-as-number, non-finite numbers, duplicate player IDs, duplicate cards/actions, inconsistent stack/contribution values, references to missing named ranges fail with status 2
11. Existing version-1/version-2 APIs unchanged
12. Canonical JSON output sorted and deterministic
13. All new Phase 3 features accessible via version-3 API
14. CLI help updated with version-3 commands
15. Byte-determinism smoke tests pass for version-3 outputs

**Tolerance:** `1e-12` absolute for Classic/checkdown identity; exact byte-identity for deterministic fields

**Oracle references:**

- Existing Phase 1/2 solver outputs for Classic identity
- Hand-solved tiny game for checkdown identity
- Hand-solved tiny game for heuristic counterexample

**API compatibility hazards:**

- Version-3 API must not break version-1/version-2
- Existing Phase 1/2 solve requests must retain previous behavior
- New engine-mode field must be optional for backward compatibility

**Determinism gates:**

- Canonical JSON output
- Byte-identical output for same input/seed
- Deterministic error messages

**Benchmark gates:** Measure and record baseline for version-3 endpoints

**Documentation gates:**

- Engine mode semantics documented
- Classic vs approximation distinction documented
- API versioning documented
- Migration guide from version-2 to version-3

**Mandatory adversarial audit after Batch 7:**

- Dispatch fresh non-author BryantGPT subagents
- Audit scope: run all tests, attack API validation, verify Classic identity, verify approximation labeling, cross-check version-1/version-2 backward compatibility, verify unsupported Fast rejection
- Audit deliverable: `review/phase3/batch7-audit.md`
- Batch 7 is not "done" until audit passes
- No Batch 8 work may start before audit sign-off

---

### Batch 8: Canonical presets and documentation

**Exclusive ownership:**

- `examples/phase3_btn_vs_bb_25bb.json` (new)
- `examples/phase3_river_3way.json` (new)
- `examples/phase3_dynamic_sizing.json` (new)
- `examples/phase3_nodelock_profile.json` (new)
- `examples/phase3_rake_icm.json` (new)
- `tests/test_presets.py` (new)
- `ARCHITECTURE_PHASE3.md` (new)
- `README.md` (update)

**Shared integration points (parent only):**

- None; documentation and examples are leaf artifacts

**Acceptance gates:**

1. All baseline + Batch 1–7 tests remain green
2. Every canonical preset loads without error
3. Every canonical preset validates against version-3 schema
4. Every canonical preset runs to completion with configured iterations
5. Every canonical preset produces deterministic output for same seed
6. Preset library round-trip: load → serialize → load is object-equal
7. ARCHITECTURE_PHASE3.md implemented-vs-boundary matrix complete
8. ARCHITECTURE_PHASE3.md lists every new module with exclusive file ownership
9. ARCHITECTURE_PHASE3.md lists acceptance test for each module
10. ARCHITECTURE_PHASE3.md lists accuracy reference for each module
11. README updated with full GTO Wizard feature list (implemented vs documented-boundary)
12. README updated with Phase 3 CLI examples
13. README updated with version-3 API examples
14. All docstrings complete and accurate
15. All module-level contracts documented
16. All public functions have type hints
17. All acceptance gates from Batches 1–7 documented in ARCHITECTURE_PHASE3.md

**Tolerance:** N/A for documentation; preset outputs use module-specific tolerances

**Oracle references:** N/A for documentation

**API compatibility hazards:** None; documentation only

**Determinism gates:**

- Preset outputs deterministic for same seed
- Canonical JSON serialization

**Benchmark gates:** None required for documentation

**Documentation gates:**

- All documentation complete and accurate
- All examples working and tested
- All implemented-vs-boundary decisions documented

**Mandatory adversarial audit after Batch 8:**

- Dispatch fresh non-author BryantGPT subagents
- Audit scope: run all preset tests, verify documentation accuracy, cross-check implemented-vs-boundary matrix against actual code, verify README examples, verify all acceptance gates documented
- Audit deliverable: `review/phase3/batch8-audit.md`
- Batch 8 is not "done" until audit passes
- Phase 3 is not "done" until Batch 8 audit passes

---

## Cross-cutting integration rules

### Parent-only integration surfaces

The following files may be edited ONLY by the parent orchestrator to integrate batch deliverables:

- `src/poker_solver/api.py`: version-3 endpoint integration
- `src/poker_solver/cli.py`: version-3 command integration
- `src/poker_solver/model.py`: N-player protocol integration
- `src/poker_solver/cfr.py`: nodelock/profile integration
- `src/poker_solver/mccfr.py`: nodelock/profile integration
- `src/poker_solver/best_response.py`: N-player best-response integration
- `pyproject.toml`: dependency updates (none expected)
- `src/poker_solver/__init__.py`: public API exports

No batch worker may edit these files. Parent integration happens AFTER batch audit passes.

### Dependency-safe batch ordering

Batches are ordered to minimize shared-file conflicts:

1. **Batch 1** (sizing, range_editor): no dependencies, leaf modules
2. **Batch 2** (game_structure, nplayer_protocol): depends on Batch 1 complete; parent integrates `model.py`
3. **Batch 3** (preflop, three_way): depends on Batches 1–2 complete; parent integrates composition
4. **Batch 4** (tree_editor, nodelock, profiles): depends on Batches 1–3 complete; parent integrates `cfr.py`/`mccfr.py`
5. **Batch 5** (range_tables, opponent_inference): depends on Batches 1–4 complete; parent integrates composition
6. **Batch 6** (rake, icm, bounty): depends on Batch 2 complete; parent integrates `game_structure.py`
7. **Batch 7** (engine_modes, api_v3): depends on Batches 1–6 complete; parent integrates `api.py`/`cli.py`
8. **Batch 8** (presets, documentation): depends on Batches 1–7 complete; no code integration

### Audit wave composition

Each audit wave uses fresh non-author BryantGPT subagents:

- **Minimum 2 auditors per batch**, maximum 10 (concurrency cap)
- Auditors assigned exclusive audit scope (e.g., one attacks sizing formulas, one attacks Dynamic mode)
- Auditors must RUN the code and tests, not just read them
- Auditors must attempt to find bugs, not just confirm success
- Auditors write `review/phase3/batchN-audit.md` with reproduction for any confirmed bug
- If bugs found, parent dispatches fix wave, then re-runs audit until clean

### Retry policy: 14→12→10 for 502/503 only

When dispatching subagent tasks:

1. Initial attempt with 14-minute timeout
2. If 502/503 observed, retry with 12-minute timeout
3. If 502/503 observed again, retry with 10-minute timeout
4. If 502/503 observed third time, escalate to parent
5. For all other errors (validation, test failure, etc.), do NOT retry; escalate immediately

This policy applies ONLY to observed 502/503 HTTP errors, not to test failures or validation errors.

## API compatibility hazard summary

### Version-1 API (Phase 1)

- `evaluate` command: unchanged
- `equity` command: unchanged
- `solve-kuhn` command: unchanged
- `solve-spot` version-1 schema: unchanged

### Version-2 API (Phase 2)

- `solve-spot` version-2 schema: unchanged
- Multi-street postflop: unchanged
- MCCFR algorithm: unchanged

### Version-3 API (Phase 3)

- New `solve-preflop` command
- New `solve-three-way` command
- New `icm-equity` command
- New `bounty-transition` command
- New `infer-range` command
- Extended `solve-spot` version-3 schema with engine modes, sizing modes, nodelocks, profiles, rake, ICM/bounty

### Shared-file hazards

- `model.py`: adding N-player protocol must not break existing two-player `GameState` semantics
- `cfr.py`/`mccfr.py`: adding nodelock/profile support must not break existing solver behavior when locks/profiles absent
- `best_response.py`: adding N-player best-response must not break existing two-player best-response
- `api.py`/`cli.py`: adding version-3 endpoints must not break version-1/version-2 endpoints

## Determinism gates summary

### Byte-identical output required

- Vanilla CFR with same input/iterations on same interpreter
- Canonical JSON serialization with sorted keys
- Preset library save/load round-trip
- Version-3 API deterministic fields

### Seed-repeatable output required

- Seeded MCCFR on same interpreter/platform
- Seeded Dynamic sizing mode
- Seeded chance enumeration order

### Permutation-invariant output required

- Range editor input order
- Sizing candidate input order
- Inference likelihood-table input order
- ICM seat permutation (output permutes accordingly)

## Benchmark gates summary

No performance claims for large trees. Benchmarks are regression gates only:

- Measure baseline after each batch implementation
- Record median runtime for representative fixtures
- Future changes must not exceed 2x baseline without justification
- Ceilings come from measured local medians, not invented targets

## Documentation gates summary

Every module must have:

- Module-level docstring with contract summary
- Public function docstrings with parameters, returns, raises
- Type hints for all public functions
- Explicit tolerance/rounding policy where applicable
- Explicit oracle/reference where applicable
- Explicit implemented-vs-boundary decision where applicable

ARCHITECTURE_PHASE3.md must document:

- Every new module with exclusive file ownership
- Every acceptance test with oracle/tolerance
- Every accuracy reference
- Every API compatibility hazard
- Every implemented-vs-boundary decision
- Dependency graph for Phase 3 modules

## Definition of done

Phase 3 is complete when:

1. All 8 batches implemented
2. All 8 adversarial audits passed
3. All baseline + Phase 3 tests green (pytest default + slow)
4. ARCHITECTURE_PHASE3.md complete and accurate
5. README updated with Phase 3 features
6. All canonical presets working and tested
7. Version-3 API complete and backward-compatible
8. All documentation gates satisfied
9. PROGRESS.md updated
10. Final cross-batch integration audit passed

## File verification

This plan is written to `/home/genomix-node/poker-solver/research/phase3/design/integration-plan.md`. Read-back verification follows.
