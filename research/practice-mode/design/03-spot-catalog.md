### Design report 03 — immutable spots and solver-driven catalogs

Authority: `PRACTICE_MODE_DESIGN.md` sections 0, 3 and 6, read in full. This is a proposed implementation contract, not implemented practice code. Every answer, strategy, Q value and score must originate in a solve or its content-addressed cache.

### 1. Frozen dataclass specification

All three classes use `@dataclass(frozen=True, slots=True)`, public docstrings and fail-closed `ValueError`. Copy sequences to tuples; recursively detach mappings into `MappingProxyType`. Validate raw values before coercion. Never use `bool` as an integer or number; never catch bare `Exception` in new code.

#### SolveParams

| Field | Type | Validation |
|---|---|---|
| algorithm | `Literal["vanilla-cfr", "external-sampling-mccfr"]` | Exact enum. |
| iterations | `int` | Strict integer, positive. |
| seed | `int | None` | Strict integer when present; vanilla requires None, MCCFR requires integer. |

Catalog sampling seed is independent of `solve.seed`. River, initial Kuhn catalog and nplayer-preflop use vanilla; reject MCCFR for those routes. Allstreet supports both algorithms under the above seed rules.

#### PracticeSpot

Retain section 3's field names; `spot_id` is `field(init=False)` and computed only after validation.

| Field | Type |
|---|---|
| spot_id | `str`, derived |
| family | `str` |
| backend | `Literal["kuhn", "river", "allstreet", "nplayer-preflop"]` |
| game_type | `Literal["heads-up", "3-max"]` |
| street | `Literal["preflop", "flop", "turn", "river"]` |
| board | `tuple[int, ...]` |
| hero_seat | `int` |
| villain_seats | `tuple[int, ...]` |
| ranges | `tuple[tuple[equity.WeightedCombo, ...], ...]` |
| pot | `int | float` |
| stacks | `tuple[int, ...]` |
| action_history | `tuple[Action, ...]` |
| bet_sizes | `tuple[int, ...]` |
| hero_hand | `tuple[int, int] | None` |
| solve | `SolveParams` |
| backend_extra | `Mapping[str, Any]`, recursively frozen JSON-safe values |

Validation and normalization:
- Family must match `[a-z0-9]+(?:-[a-z0-9]+)*`; reject unknown catalog families in the generator. Backend/game/street enums and their compatibility are checked before construction completes.
- Hold'em board lengths: preflop 0, flop 3, turn 4, river 5. Every card is a strict integer in 0..51, with no duplicates within the board or a hand. Preserve board order, including chronological turn/river order; sort each two-card hand.
- Heads-up has two seats; 3-max has three. `hero_seat` is valid; `villain_seats` is exactly the increasing tuple of other seats. Ranges and stacks have one entry per seat.
- Pot is finite, strictly positive, not bool; normalize to float. Stacks are positive strict integers. River/allstreet require equal effective stacks in this initial contract; do not silently take min for unequal user-supplied stacks.
- Validate every range entry as `equity.WeightedCombo`, revalidate its cards and numeric weight at the practice boundary, then reconstruct defensively. Weight is finite and in [0,1], not bool. Reject duplicate combos per seat, even if reversed in the raw input.
- Remove board-blocked and zero-weight combos, sort remaining combos by cards, normalize weights to float, and require each resulting range to have positive mass. Do not require disjointness between alternative combos or across entire ranges: only simultaneously dealt hands must be disjoint.
- Require at least one compatible positive-weight joint deal. A concrete hero hand must be in the sanitized hero range and participate in at least one compatible joint deal; reject overlap with board. Hold'em catalog drills always have a concrete hand; None is reserved for explicitly supported range-level use.
- Bet sizes are positive strict integers, unique/increasing, within effective stack. River has exactly one. Allstreet has one or two wager targets. Preflop targets must agree with its resolved sizing rules; validate by the backend tree, not generic pot-percentage assumptions.
- History entries are `Action`; preserve their real `amount: int = 0` convention, not optional amounts. For river use lowercase check/bet/fold/call; preflop uses uppercase FOLD/CHECK/CALL/RAISE. Never admit chance-deal actions as public history.
- Tree-walk history after each compatible private deal, require legal transitions and a nonterminal hero-acting node. Do not parse stringified InfoKeys. Construction may delegate this semantic preflight to the adapter, but an unvalidated spot must not reach solve/cache/scoring.
- Reject unknown backend-extra keys, unsupported objects, sets, non-string mapping keys and nonfinite numeric values. Validate algorithm/backend compatibility, runout uniqueness/cards, node/depth limits and continuation coverage. JSON parsers reject duplicate keys before creating these objects.

Kuhn exception: section 3 types `hero_hand` as a Hold'em pair, but section 4 calls it J/Q/K. Preserve the stated type by using `hero_hand=None`, empty board/ranges, `backend_extra={"kuhn_card": "J"|"Q"|"K"}`; map that symbol through the real Kuhn tree. Require heads-up/preflop, pot 2, stacks (1,1), bet_sizes (1,), and one of its four nonterminal public histories. Empty ranges are permitted only here because `kuhn_root()` owns its six deals. This explicit representation needs parent reconciliation; do not encode J/Q/K as arbitrary Hold'em card pairs.

#### HeroDecision — proposed resolved-node record

Section 3 names `DecisionPoint` but does not define `HeroDecision`; propose one record, with `DecisionPoint` an alias if consumers require that name. It is solver-resolved, never a catalog answer table.

| Field | Type | Validation |
|---|---|---|
| hero_seat | `int` | Strict valid seat; equals spot hero. |
| hero_hand | `tuple[int, int] | None` | Equals spot hand; None only for the Kuhn representation above or supported range drill. |
| action_history | `tuple[Action, ...]` | Equals the walked public line. |
| info_key | `Hashable` | Actual `state.information_state_key(hero_seat)`, not parsed text. |
| legal_actions | `tuple[Action, ...]` | Exact nonempty, unique backend action tuple. |
| pot_at_decision | `float` | Finite positive pot including contributions along history. |
| kuhn_card | `Literal["J", "Q", "K"] | None` | Required only for Kuhn; equals spot extra. |

Copy tuples, validate against the walked node, and exclude strategy/EV/probability fields. InfoKey is an internal object, not a generic JSON identifier; expose structured decision metadata without pretending a string round-trip reconstructs it.

### 2. Canonical JSON and identities

`canonical() -> dict[str, Any]` returns a fresh mutable JSON tree, not internal mappings. Its exact top-level keys are `format`, `family`, `backend`, `game_type`, `street`, `board`, `hero_seat`, `villain_seats`, `ranges`, `pot`, `stacks`, `action_history`, `bet_sizes`, `hero_hand`, `solve`, `backend_extra`; `format="practice-spot-v1"`. Exclude derived spot_id/hash, display labels, solved outputs, runtime timing and HeroDecision.

Encoding rules: tuples become arrays; combos become `{"cards":[c0,c1],"weight":w}`; actions become `{"kind":kind,"amount":amount}`; solve contains exactly algorithm/iterations/seed. Hero hand is an array or null. Preserve semantic sequence order; range combos and villain seats are canonical-sorted. Normalize declared float fields before serialization so pot 150 and 150.0 have identical identities. Within backend-extra normalize numbers according to its typed schema, including sizing-expression values; reject values without a schema. Freeze recursively on input and thaw recursively on canonical output.

`params_hash()` is `hashlib.sha256(json.dumps(canonical(), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")).hexdigest()`.
`spot_id = family + "/" + params_hash()[:12]`. This full-spot identity includes the hero hand/history as well as solve inputs; therefore different drills over one game do not alias. A future game-only cache key would be a separate schema, not a silent change here. Store/check full hash with every shortened ID; fail on a prefix collision. Solver package version belongs in provenance/cache compatibility checks, not a guessed constant.

### 3. Generator and actual helper boundaries

Proposed signature: `generate_catalog(families: tuple[str,...]=ALL_FAMILIES, seed: int=0, solve: SolveParams=SolveParams("vanilla-cfr",200,None)) -> tuple[PracticeSpot,...]`.

Validate families/seed/solve, reject duplicate family requests, iterate known families in fixed order and grid axes in declared order. Derive a per-cell RNG seed from SHA256 of canonical `[seed,family,axis-values]`, never Python `hash()`. Instantiate `random.Random(cell_seed)`. This keeps one family's output stable when other families are requested. Record `catalog_seed` and `cell_seed` as typed integer backend-extra generation metadata included in canonical form, but strip them when routing solve payloads.

Read helpers and limitations:
- `ranges.import_range_text(text)` expands explicit combos and 169-class tokens; supports comma-separated tokens with optional `:weight`, not assumed `AA+`/dash syntax. `RangeEditor.add`, `include_or_replace`, `blocked(list(board))`, `combos()` are real methods. Convert sorted positive entries with `equity.WeightedCombo(cards, weight)`.
- `presets.list_presets()` / `get_preset(name)` offer only `btn-vs-bb-25bb` and `threeway-flop-demo` in the inspected source. Neither contains a range or solved strategy. First provides stacks/posts/sizing expressions; second is three-player and requires supplied ranks. Do not invent range-preset names or treat either as GTO.
- `range_table.build_range_table(root, strategy, *, seat, provenance)` consumes an already complete solved profile; it does not build starting ranges. It expects chance children exposing `private_deal`; river uses `deal`, so it is not a drop-in river view. It is root-public-node only, not an IP-facing-bet conditional table. Use adapter/evaluate's walked conditional aggregation for those cases; no fabricated range-table helper.

Board sampling: `tuple(rng.sample(range(52), street_length))`, without texture-biased answers. Range schemas below are input abstractions, not claims of optimal opening/continuation frequencies. Reject cells without compatible deals; a deterministic maximum of 64 resampling attempts ends in ValueError, never a fallback puzzle.

For each range, block board and filter zeros first, then seeded-sample a bounded subset from sorted combos, retaining source weights. Choose hero via `rng.choices` over compatible sanitized hero combos weighted by source weight, then verify its tree node exists. Kuhn instead enumerates the card axis. Flop samples runouts from cards excluding the board and the union of retained private cards, ensuring every retained deal can use each sampled runout.

#### Parameter grids (proposed defaults, not benchmark-certified)

| Family | Grid axes | Ranges / history / hero |
|---|---|---|
| kuhn-intro | hero {0,1} × card {J,Q,K} × compatible public node | P0: () or (check,bet); P1: (check,) or (bet,). Use kuhn_root's deals, not RangeEditor; four actor/node pairs yield 12 drills. |
| river-oop-bet-or-check | board draw {0,1} × range-shape {polar-ish/condensed,merged/condensed} × pot {100,200} × SPR {2,4} × bet-percent {33,75,125} | Hero 0; history (); two bounded ranges. |
| river-ip-facing-bet | Same river axes | Hero 1; history (Action("bet",bet),). It is fold/call, not a new bet-size choice; bet size varies between cells. |
| flop-cbet-small-tree | board draw {0,1} × pot {100,200} × SPR {1,2} × runout-count {1,2} × sizing {small,small-and-large} | Hero 1 after P0 check; range inputs AA,AKs,AQs versus QQ,JJ,TT; confirm actual actor through tree. |
| preflop-3max-open | button {0,1,2} × stack-bb {10,25} × open-size-bb {2,2.5} × target position {BTN,SB,BB} | Three bounded expression ranges AA,AKs,A5s / QQ,AQs,KQs / JJ,TT,AJs; map positions relative to button; see legal-node caveat below. |

River inputs: polar-ish `AA,AKs,A5s` versus condensed `QQ,JJ,TT`; merged `AA,KK,QQ,AKs,AQs` versus `QQ,JJ,TT,AQs`. These names describe input composition only: a random board can change actual hand-strength polarity. Use `import_range_text`, block board, retain at most two combos per seat. Bet is `max(1,(pot*percent+50)//100)` and stack is pot*SPR; fixed grid ensures bet<=stack. Do not offer multiple bets in a single `RiverConfig`.

Flop retains at most two combos per seat. Wager targets are cumulative backend chip targets `(pot//3,)` or `(pot//3,3*pot//4)`, not claimed persistent street-relative pot percentages. Extra keys: version `allstreet-postflop-v1`, allowed_runouts, betting_mode `no-limit`, max_nodes 1500, max_depth 32. Include automatic stack-sized actions when counting the real tree; target count alone is not a branching bound. Reject cells exceeding the bound; never truncate a legal tree and still call it complete.

Preflop uses `get_preset("btn-vs-bb-25bb")` only as a template for BB=100/SB=50 and existing sizing-expression shape, extends posts to the derived three seats, and sets three starting stacks from the grid. Board is empty. Retain at most two combos per seat, enumerate disjoint joint deals (<=8), and sample a five-card continuation board excluding the union of retained private cards. Compute all three ranks per compatible deal with real `evaluator.evaluate_seven`; never type payoff/rank answers. This is a bounded sampled-showdown continuation, not full-deck preflop GTO.

Route through `api_v4.dispatch_v4` with exact envelope integer version 4, operation `solve-nplayer-preflop`, flat payload. Payload fields read from `_dispatch_nplayer_preflop`: version `nplayer-preflop-v1`, num_players 3, button, starting_stacks, forced_posts, straddle_variant `none`, ranges, sizing_rules, max_raises 1, max_deals 8, max_nodes 1500, short_all_in_reopens false, continuation, algorithm, iterations, seed null, include_deviation_certificate false, max_pure_strategies 1000. Sizing rules contain position/raise_count/cold_callers/relation/expressions, with initial contexts raise_count=0, cold_callers=0, relation=NA and generated big-blinds expressions. Continuation contains kind `showdown-ranks`, provenance describing sampled board, source `derived`, entries of deal/ranks and odd_chip_order as a seat permutation. Include continuation board/ranks and generation seeds in spot canonical extras; only permitted payload fields go to dispatch.

Convert practice equity.WeightedCombo to the separate `preflop.WeightedCombo(cards, Fraction(str(weight)))` on typed tree construction; the dispatcher itself constructs that different class. Do not pass equity.WeightedCombo directly to NPlayerPreflopConfig.

Preflop legal-node caveat: BTN opens at root; SB opens after BTN fold. After BTN and SB fold, BB has won and there is no decision. After BTN fold and SB CALL, BB has CHECK/RAISE, not open/fold. Therefore BB is a labeled check-or-raise drill (history found by legal tree walk), or excluded from an open/fold-only catalog. Do not fabricate a BB fold button. Parent must reconcile the family description before promising three positional open/fold drills.

#### Runtime budgets

Initial default is 200 iterations. Kuhn has six deals and a fixed tiny tree. River has <=4 compatible deals, four decisions plus five terminal histories per deal, hence <=37 tree nodes including chance root. The measured example below meets the target, including root/solver construction. Flop and preflop caps above are conservative proposed admission limits, not evidence of <10-second solves: only river was timed here. Preflop also disables potentially exponential deviation certificates.

A node cap cannot guarantee wall time for arbitrary iteration counts/hardware. Benchmark complete solves, including preflight and required diagnostics, before admitting a default cell; enforce a roughly 10-second process deadline in the service for interactive solves and report failure without a solved artifact. Never reduce requested iterations or substitute an answer. Higher iteration settings are explicit noninteractive work or fail the interactive budget. No solver result is hardcoded into catalog.py.

### 4. Executed river probe — command and output verbatim

Working directory: `/home/genomix-node/poker-solver`; `.venv` Python 3.11.16, branch `feat/practice-mode`. Initial git status was clean. The command uses a disposable /tmp directory and disables bytecode writes. It builds full blocked ranges then solves seeded two-combo subsets; full blocked counts are not the solve-tree counts.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -c 'import random,time,tempfile,os; from poker_solver.ranges import import_range_text; from poker_solver.presets import get_preset; from poker_solver.equity import WeightedCombo; from poker_solver.cards import format_card; from poker_solver.river import RiverConfig,river_root; from poker_solver.cfr import CFRSolver; probe=tempfile.TemporaryDirectory(prefix="practice03-",dir="/tmp"); rng=random.Random(17); board=tuple(rng.sample(range(52),5)); preset=get_preset("btn-vs-bb-25bb"); editors=tuple(import_range_text(expr).blocked(list(board)) for expr in ("AA,AKs,A5s","QQ,JJ,TT")); full=tuple(tuple(WeightedCombo(cards,weight) for cards,weight in sorted(editor.combos().items()) if weight>0) for editor in editors); small=tuple(tuple(sorted(rng.sample(list(r),min(2,len(r))),key=lambda c:c.cards)) for r in full); pot=sum(preset["forced_posts"]); stack=min(preset["starting_stacks"]); bet=round(pot*0.75); print("seed=17"); print("board_ids="+repr(board)); print("board_text="+" ".join(format_card(c) for c in board)); print("expressions=AA,AKs,A5s | QQ,JJ,TT"); print("after_board_removal="+repr(tuple(len(r) for r in full))); print("solve_range_counts="+repr(tuple(len(r) for r in small))); print("solve_combos="+repr(tuple(tuple(c.cards for c in r) for r in small))); print("pot="+str(pot)+" stack="+str(stack)+" bet="+str(bet)); start=time.perf_counter(); root=river_root(RiverConfig(board,pot,stack,bet,*small)); solver=CFRSolver(root); strategy=solver.train(200); elapsed=time.perf_counter()-start; print("compatible_deals="+str(len(root.chance_outcomes()))); print("infosets="+str(len(strategy))); print("iterations="+str(solver.iterations)); print("solve_wall_time_s="+format(elapsed,".6f")); print("max_policy_sum_error="+repr(max(abs(sum(p.values())-1) for p in strategy.values()))); path=probe.name; probe.cleanup(); print("tmp_probe_removed="+str(not os.path.exists(path)))'
```

```text
seed=17
board_ids=(33, 26, 51, 19, 23)
board_text=Td 8h As 6s 7s
expressions=AA,AKs,A5s | QQ,JJ,TT
after_board_removal=(9, 15)
solve_range_counts=(2, 2)
solve_combos=(((14, 50), (45, 49)), ((40, 43), (41, 42)))
pot=150 stack=2500 bet=112
compatible_deals=4
infosets=8
iterations=200
solve_wall_time_s=0.332025
max_policy_sum_error=1.1102230246251565e-16
tmp_probe_removed=True
```

Probe `round(150*0.75)` uses Python ties-to-even, giving 112; the proposed integer half-up generator rule gives 113 for that non-grid pot. Report the executed value unchanged. No strategy/score assertion is inferred from this timing probe.

### 5. Permanent test list (future implementation, no tests written here)

#### tests/test_practice_spot.py
- Parameterize invalid enums and every integer/card field with bool, strings, negatives and boundary values; require ValueError, not incidental TypeError/IndexError. Reject NaN/infinity and boolean pot/weights.
- Validate street lengths including turn=4; duplicate/out-of-range cards, duplicate/reversed combos, board blocking, zero-mass ranges and incompatible joint deals. Test hero membership, hero-board collision and hero with no compatible opponents.
- Test backend/game/street mismatches, unequal unsupported stacks, malformed histories, non-hero/terminal nodes, unknown extras and invalid runouts/continuation coverage. Require exact actor and action tuple from real tree.
- Check frozen assignment, nested defensive copies, canonical result detachment and copied source range lists/maps. Mutating an input after construction cannot affect the spot or hash.
- Canonical JSON round-trip, sorted mapping/range order, integer/float pot equivalence, explicit null seed/hand and Action amount=0. Reject duplicate JSON keys, unknown schemas and unsupported extra values.
- Independently recompute SHA256; require full 64 hexadecimal digits and exact family/hash-prefix ID. Detect shortened-ID collision using controlled hashing, without inserting strategy fixtures.
- Every solve-sensitive field mutation changes canonical bytes/hash: iterations, algorithm/seed, range weight/cards, board, pot, stack, size, history, hero, and continuation/runouts. Runtime timing does not enter identity.
- Kuhn representation tests keep None hand plus J/Q/K symbol explicit; reject Hold'em exemptions on other backends. HeroDecision matches the real walked InfoKey and carries no answer fields.

#### tests/test_practice_catalog.py
- Same seed/grid/solve gives identical canonical spots, order and IDs; different seeds change sampled content. Requesting a family alone versus with others preserves that family's output. Unknown/duplicate families and bool seeds fail closed.
- Assert unique full hashes/IDs after parameter-grid generation; compare counts to explicit axis products minus documented legal-node exclusions, never silently drop invalid cells. Require exactly 12 Kuhn drills.
- All generated Hold'em hands/ranges survive board removal and have compatible joint deals. Verify every history terminates at the intended hero decision; IP-facing-bet is fold/call; BB never gets a terminal open/fold drill.
- Assert real helper-derived range composition, seeded subset weights, preset template fields, <=2 runouts, per-seat combo caps, exact river one-bet abstraction, actual node/depth bounds, deterministic retry exhaustion and no fallback puzzle.
- Import production catalog and adapter, solve tiny generated spots and assert legal normalized policies/provenance. Generate expected answers from fresh independent solves in the test, never literal probability fixtures.
- For preflop assert integer envelope version 4, exact payload schema, converted combo types, generated evaluator ranks covering all compatible deals, and visible sampled-continuation limitation. No hand-authored payoff or optimal-action table.
- AST gate: `ast.parse` production catalog.py; walk every `ast.Dict` and reject any value that is a float `ast.Constant` (also unary +/- float constants). Keep float sizing/input weights in typed tuples or helper results, not dict literals. A broader second gate rejects action-keyed literal strategy mappings even when probabilities are integers; no AST Dict exemption for nested structures.
- Verify no strategy, EV, score or optimal-action literals embedded in catalog records; no cache fixture can bypass solving/provenance. AST checks are structural defenses, not proof by themselves.
- Required cross-module sensitivity test (owned by tests/test_practice_no_hardcode.py): choose a small generated game where separate iterations/range/pot/stack changes alter strategy or score AND hash. Solve both variants for each change; merely asserting changed hashes is insufficient. Do not assert that every arbitrary parameter perturbation must change equilibrium.
- Keep fast permanent tests within the shared <60-second added suite budget. Record full-solve runtime admission measurements separately; do not add flaky universal <10-second assertions based solely on this one river measurement.

### 6. Findings requiring parent reconciliation

Kuhn's symbolic hand disagrees with the stated pair type; BB cannot be an unopened fold/open decision; range_table is not a range generator or a river conditional-table adapter; bundled presets supply no ranges/solutions; preflop has a sampled continuation, not unrestricted preflop GTO. Only the river probe is performance-verified. These limits must remain visible instead of being replaced by hardcoded puzzles or invented solver answers.
