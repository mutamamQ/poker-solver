# S3 solver/API/TDD design audit — repaired candidate

**Auditor:** A3Y5 (fresh non-author, design-only)  
**Candidate:** `ARCHITECTURE_PHASE4_S3.md`  
**SHA-256 verified:** `f0777689eac5df76ab7630dd3725e40f7409e4369ba9de312ac8992a4a4bb83f` (before and after)  
**Scope:** Solver reuse/reach/deviation/bounds, strict-v4 S3 schema feasibility/serialization, examples/exports/capability truth, nonoverlapping RED-first S3-I1/I2 ownership.  
**Baseline:** S2 complete; S3 production/tests absent as expected.

---

## 1. Solver reuse and reach propagation

### 1.1 Generic N-player CFR reuse

**Architecture claim (§10, §2.5):**  
S3 reuses `NPlayerCFRSolver`, `expected_values_nplayer`, and `unilateral_deviation_certificate` without a second reach implementation. `NPlayerPreflopState` implements `NPlayerGameState`.

**Evidence:**  
- `nplayer.py` (lines 13–21) defines the `NPlayerGameState` protocol with `current_player()`, `num_players()`, `legal_actions()`, `chance_outcomes()`, `child(action)`, `information_state_key(player)`, and `returns()`.  
- `NPlayerCFRSolver.__init__` (lines 144–161) accepts any `NPlayerGameState` root and calls `collect_nplayer_infosets(root, max_nodes, max_depth)` to validate and collect information sets.  
- `solve_nplayer_preflop` (§10) is specified to forward `config.max_nodes` and structural `max_depth` to `NPlayerCFRSolver`.  
- `expected_values_nplayer` (lines 259–301) and `unilateral_deviation_certificate` (lines 315–354) both accept `NPlayerGameState` roots and validate via `collect_nplayer_infosets`.

**Assessment:** **PASS**  
The generic solver, expected-value, and deviation helpers are protocol-driven and accept any conforming state. S3 only needs to implement the seven protocol methods; no reach-propagation duplication is required.

---

### 1.2 Reach propagation and regret weighting

**Architecture claim (§6):**  
The reused N-player CFR propagates one realization reach per player plus chance reach. Player i's regret weight is chance reach times every opponent reach and excludes i's own reach. Permanent six-player arithmetic tests prove this independently.

**Evidence:**  
- `NPlayerCFRSolver._walk` (lines 204–256) maintains `reaches: list[float]` (one per player) and `chance_reach: float`.  
- At TERMINAL (line 217), the method returns `float(state.returns()[updating])`.  
- At CHANCE (lines 218–231), it multiplies `chance_reach * probability` and recurses.  
- At decision nodes (lines 232–256), it copies `reaches`, multiplies `child_reaches[player] *= policy[action]`, and recurses.  
- Regret weight (lines 249–255): `counterfactual = chance_reach`; then `for opponent, reach in enumerate(reaches): if opponent != player: counterfactual *= reach`; finally `deltas[key][action] += counterfactual * (action_values[action] - value)`.

**Assessment:** **PASS**  
The counterfactual weight excludes the updating player's reach and includes chance reach and all opponent reaches. The architecture correctly describes the existing implementation. Six-player independent arithmetic tests (§10, §13 acceptance matrix line 294) are a TDD obligation, not a design flaw.

---

### 1.3 Deviation diagnostic bounds

**Architecture claim (§10, §2.5):**  
The unilateral-deviation certificate is exhaustive below its cap or fails closed; it is never sampled and never called exploitability or a Nash certificate. A permanent six-player tiny oracle independently enumerates pure deviations. Nine-player acceptance uses a deliberately tiny tree and makes no throughput claim.

**Evidence:**  
- `unilateral_deviation_certificate` (lines 315–354) enumerates the Cartesian product of all owned information-set actions per player (line 338: `product(*(actions for _, actions in owned))`).  
- Line 335: `if count > max_pure_strategies: raise ValueError("player pure-strategy bound exceeded")` — fails closed when the product exceeds the cap.  
- `UnilateralDeviationCertificate.provenance` (line 353): `"exhaustive finite pure unilateral deviations; diagnostic only"` — never claims Nash or exploitability.  
- Architecture §13 acceptance matrix (line 294): "exact six-plus-player reach and unilateral-deviation oracles match production below declared caps."

**Assessment:** **PASS**  
The diagnostic is exhaustive enumeration, not sampling. It fails closed above the cap and never claims equilibrium quality. The acceptance matrix requires independent oracles for six-player reach and deviation, and nine-player acceptance explicitly uses a tiny tree (§13 line 295, §3 lines 12–14).

---

## 2. Strict v4 API schema feasibility and serialization

### 2.1 Direct v4 operation and envelope

**Architecture claim (§11):**  
Add direct v4 operation `solve-nplayer-preflop`. The envelope remains exactly `{version: 4, operation, payload}` with integer version 4. The response contains operation/version, config/game versions, algorithm/iterations/bounds, detached serialized strategy, N values, optional certificate, metadata, provenance, and `approximate: false`. It does not claim convergence.

**Evidence:**  
- `api_v4.py` line 284: `def dispatch_v4(data: dict[str, Any]) -> dict[str, Any]:` — the existing v4 dispatcher.  
- Lines 321–333: the dispatcher validates `{"version", "operation", "payload"}`, checks `version == 4` (lines 323–325), and routes `operation == "solve-nplayer-postflop"` to `_dispatch_nplayer_postflop` (lines 327–333).  
- Lines 265–281 (S2 postflop response): returns `{"version": 4, "operation", "config_version", "game_version", "algorithm", "iterations", "seed": None, "max_nodes", "max_depth", "strategy", "values", "certificate", "metadata", "provenance", "approximate"}`.  
- Line 280: `"approximate": result.approximate` — the S2 result already carries this field.

**Assessment:** **PASS (schema feasible, implementation gated)**  
The v4 dispatcher already routes two operations (`solve-allstreet-postflop` and `solve-nplayer-postflop`) and returns the required envelope shape. Adding `solve-nplayer-preflop` requires:
1. A new `_dispatch_nplayer_preflop(payload_value)` function parallel to `_dispatch_nplayer_postflop` (lines 76–281).  
2. A new routing branch in `dispatch_v4` after line 333.  
3. The S3 solve result must carry `approximate: bool` and `metadata: Mapping[str, object]` fields (§2.5 specifies these).

No envelope change is needed. The schema is feasible.

---

### 2.2 Payload structure and validation

**Architecture claim (§11):**  
The payload contains config version, N, button, starting stacks; ordered forced-post objects and straddle variant; per-seat weighted ranges; strict sizing-rule objects; max raises/deals/nodes and short-all-in policy; one continuation object (terminal-table entries as JSON lists of `{deal, history, values}`, or showdown entries as `{deal, ranks}` plus odd-chip order); algorithm, iterations, null seed, diagnostic flag, and pure-strategy cap. History JSON entries explicitly contain actor, action kind, and integer amount. Unknown/missing fields, bool numerics, nonfinite values, malformed arrays, duplicate continuation keys/deals, unsupported seeds/algorithms, and bound violations fail closed.

**Evidence:**  
- `api_v4.py` lines 10–73 define strict validation helpers: `_object`, `_object_with_optional`, `_list`, `_int`, `_float`, `_str`.  
- Line 45: `_int` rejects `isinstance(value, bool)` before `isinstance(value, int)` — bool-as-int is rejected.  
- Line 55: `_float` rejects bools, checks `isfinite(result)` when `finite=True`, and checks `result >= 0` when `nonnegative=True`.  
- Lines 82–88 (S2 postflop payload): `_object(payload_value, fields, "payload")` with exact field set — extra/missing fields raise `ValueError`.  
- Lines 100–107 (S2 helper `n_ints`): validates length equals `num_players` and applies `_int` with `positive`/`nonnegative` flags per item.  
- Lines 153–178 (S2 showdown parsing): validates deal/ranks lengths, rejects duplicate deals (line 174), and applies `_int` to ranks.

**Assessment:** **PASS (validation pattern established, S3 payload gated)**  
The existing v4 dispatcher uses strict validation with exact field sets, bool-as-int rejection, finite checks, and duplicate-key rejection. The S3 payload structure in §11 is more complex than S2 (forced posts, straddle variant, sizing rules, two continuation kinds, history with actor labels), but the validation primitives and patterns are already present. The S3 dispatcher must:
1. Define the exact required field set for the S3 payload.  
2. Parse forced-post objects (seat, type, amount) and validate cumulative posts ≤ stack (§2.4 line 84).  
3. Parse sizing-rule objects (position, raise_count, cold_callers, relation, expressions) and validate unique four-field keys (§2.2 lines 35–43).  
4. Parse continuation kind and route to terminal-table or showdown-ranks validation (§2.3).  
5. For terminal-table, parse `{deal, history, values}` entries; validate history as `[{actor, action: {kind, amount}}, ...]`; reject duplicate `(deal, history)` keys.  
6. For showdown-ranks, parse `{deal, ranks}` entries and odd-chip order; reject duplicate deals.  
7. Validate `algorithm == "vanilla-cfr"` and `seed is None` (§10 line 222).

All validation primitives exist. The S3 payload is feasible but implementation-gated (S3-I2 batch, §12 lines 269–278).

---

### 2.3 Strategy serialization

**Architecture claim (§11):**  
The response contains detached serialized strategy. (Implicit: keys and actions must be JSON-serializable.)

**Evidence:**  
- `api_v4.py` lines 252–255 (S2 postflop): `strategy = {str(key): {str(action): float(probability) for action, probability in policy.items()} for key, policy in result.strategy.items()}` — keys and actions are stringified.  
- `nplayer.py` line 116: `key = state.information_state_key(player)` — the key is `Hashable` (line 20 protocol), not necessarily a string.  
- Architecture §2.4 line 90: `NPlayerPreflopPublicAction` is a frozen `(actor: int, action: Action)` record.  
- Architecture §9 lines 206–218: the information key includes version/rule identity, N, owner seat, owner's private combo, button, stacks, posts, variant, sizing-rule identity, pot, commitments, pending, history, and continuation kind/source/provenance.

**Assessment:** **PASS (serialization pattern established, S3 key structure complex)**  
The S2 dispatcher stringifies keys and actions. S3 information keys are tuples/frozen structures containing integers, tuples, and immutable sizing-rule/continuation identities (§9). Python's `str()` on these produces deterministic reprs. The S3 dispatcher must apply the same `str(key)` and `str(action)` pattern. The architecture does not require human-readable keys, only deterministic JSON-safe serialization. **No blocker.**

---

## 3. Examples, exports, and capability truth

### 3.1 Canonical examples

**Architecture claim (§11):**  
Add canonical synthetic bounded examples: `examples/phase4/nplayer_2p_preflop.json`, `examples/phase4/nplayer_6p_preflop.json`, `examples/phase4/nplayer_9p_preflop.json`. At least the 6-player examples distinguish no, standard, double, and Mississippi straddle trees through permanent typed fixtures; canonical JSON may use one representative variant each. Examples are synthetic and non-presolved.

**Evidence:**  
- `cli.py` lines 144–146: `phase4_parser = sub.add_parser("phase4", help="run a strict bounded version-4 JSON operation"); phase4_parser.add_argument("request", help="JSON request file path or '-' for stdin"); phase4_parser.add_argument("--json", action="store_true")`.  
- Lines 216–218: `if args.command == "phase4": _emit(dispatch_v4(load_json_input(args.request)), args.json); return 0`.  
- The CLI already accepts file paths and stdin for phase4 requests. No parser change is needed for S3 examples.

**Assessment:** **PASS (CLI ready, examples gated)**  
The generic phase4 CLI (lines 144–218) already forwards v4 requests from files or stdin to `dispatch_v4`. Adding S3 examples requires:
1. Creating `examples/phase4/nplayer_2p_preflop.json`, `nplayer_6p_preflop.json`, `nplayer_9p_preflop.json` with valid S3 payloads.  
2. Permanent typed fixtures (§12 S3-I1 batch, §13 acceptance matrix lines 285–286) that distinguish no/standard/double/Mississippi straddles.  
3. A test suite `tests/test_phase4_s3_examples.py` (§12 S3-I2 line 274) that loads and validates these examples.

The CLI requires no change. Examples are implementation-gated (S3-I2 batch).

---

### 3.2 Package exports

**Architecture claim (§11):**  
Package exports are additive. After implementation, v3 capabilities truthfully advertise `nplayer-preflop` with players `[2, 9]`, street `preflop-one-round`, interfaces `typed/json-v4/cli-phase4`, continuations `supplied-or-derived-bounded`, and deviation `exhaustive-diagnostic-only`.

**Evidence:**  
- `__init__.py` lines 3–19: the package currently exports S1 allstreet and S2 nplayer-postflop symbols.  
- `api_v3.py` lines 17–47: `_FEATURES` dict defines capability metadata.  
- Lines 27–33 (nplayer-postflop feature): `{"status": "implemented-bounded", "players": [2, 9], "streets": "one-betting-round", "interfaces": ["typed", "json-v4", "cli-phase4"], "deviation": "exhaustive-diagnostic-only"}`.  
- Lines 38–43 (allstreet-postflop feature): `{"status": "implemented-bounded", "starting_street": "flop", "continuation": "automatic-natural-terminal", "interfaces": ["typed", "json-v4", "cli-phase4"]}`.

**Assessment:** **PASS (export pattern established, S3 entry gated)**  
The v3 capabilities dict already advertises S2 nplayer-postflop with the exact metadata shape required for S3. Adding S3 requires:
1. Exporting S3 symbols in `__init__.py`: `NPlayerPreflopConfig`, `NPlayerPreflopContinuation`, `NPlayerPreflopSizingRule`, `NPlayerPreflopPublicAction`, `NPlayerPreflopState`, `NPlayerPreflopSolveResult`, `enumerate_nplayer_preflop_deals`, `create_nplayer_preflop_root`, `solve_nplayer_preflop` (§2.1 lines 19–29).  
2. Adding a `"nplayer-preflop"` entry to `_FEATURES` in `api_v3.py` with `{"status": "implemented-bounded", "players": [2, 9], "street": "preflop-one-round", "interfaces": ["typed", "json-v4", "cli-phase4"], "continuations": "supplied-or-derived-bounded", "deviation": "exhaustive-diagnostic-only"}`.  
3. A test suite `tests/test_phase4_s3_exports.py` (§12 S3-I2 line 275) that validates the capability entry and public exports.

The export mechanism is ready. S3 exports are implementation-gated (S3-I2 batch).

---

### 3.3 Capability truth

**Architecture claim (§11, §1):**  
S3 is a finite reference path. It does not claim unrestricted range solving, practical large-range nine-player performance, equilibrium convergence, automatic abstraction, continuous sizing, or automatic multi-street solving. Closed non-fold leaves use caller-supplied exact continuation values or caller-supplied ranks for a bounded derived showdown continuation. All HU, 6-player, and 9-player S3 acceptance fixtures use deliberately tiny synthetic per-seat ranges whose full Cartesian product is at most `max_deals`. They prove player-count generality and exact chance arithmetic, not realistic full-range tractability. Large-range tractability belongs to S4 abstraction.

**Evidence:**  
- Architecture §1 lines 11–14: "S3 is a finite reference path. It does not claim unrestricted range solving, practical large-range nine-player performance, equilibrium convergence, automatic abstraction, continuous sizing, or automatic multi-street solving. ... All HU, 6-player, and 9-player S3 acceptance fixtures use deliberately tiny synthetic per-seat ranges whose full Cartesian product is at most `max_deals`. They prove player-count generality and exact chance arithmetic, not realistic full-range tractability. Large-range tractability belongs to S4 abstraction."  
- §2.5 line 106: `metadata` states `converged=False` and `convergence_claim="none"`.  
- §2.3 lines 61–64: "For `showdown-ranks`, every compatible deal has one strict integer rank per seat, larger wins. ... This is a synthetic bounded continuation, not automatic board rollout or equity evaluation. No rake is applied by S3; a caller that wants rake-adjusted future value supplies a zero-sum terminal table whose provenance describes its convention. Ranks are caller-supplied fixture/input data. Production never derives them from cards."  
- §13 acceptance matrix line 295: "N=2 projected deals/actions/ledgers/terminals/information partitions match frozen Phase-3 HU fixtures."

**Assessment:** **PASS**  
The architecture explicitly bounds S3 scope to finite synthetic fixtures, caller-supplied continuations, and no convergence claim. The metadata and continuation provenance fields (§2.3 line 50, §2.5 line 106) carry these disclaimers into the API response. The acceptance matrix (§13) requires N=2 projection compatibility with frozen Phase-3 HU fixtures, not full-range performance. The v3 capability entry (§3.2 assessment) must state `"continuations": "supplied-or-derived-bounded"` and `"deviation": "exhaustive-diagnostic-only"` to preserve truth. **No blocker.**

---

## 4. Nonoverlapping RED-first S3-I1/I2 TDD ownership

### 4.1 S3-I1 batch structure

**Architecture claim (§12 lines 257–267):**  
Four exclusive RED owners create permanent production-importing suites:
1. `tests/test_nplayer_preflop_config.py`: immutable config, positions, forced posts, all straddle variants, deterministic bounded deals;  
2. `tests/test_nplayer_preflop_betting.py`: HU/6/9 action order, limps, SB complete, cold calls, exact sizing-key selection, raise-to targets, 3/4/5-bet+, full/short all-ins and closure;  
3. `tests/test_nplayer_preflop_settlement.py`: independent fold/refund/side-pot/showdown continuation ledgers and zero-sum terminal-table leaves;  
4. `tests/test_nplayer_preflop_information.py`: information noninterference and projected N=2 legacy equivalence.  
A fifth owner may implement `src/poker_solver/nplayer_preflop.py` only after all four parent-verified RED receipts exist. No child owns shared legacy files. Focused tests, legacy controls, full regression, frozen hashes, a fresh different non-author audit, parent verification, and an accepted-wave commit are mandatory.

**Assessment:** **PASS (clear exclusive ownership, RED-first enforced)**  
The four test suites are nonoverlapping by domain:
- Config/deals (suite 1) vs. betting (suite 2) vs. settlement (suite 3) vs. information (suite 4).  
- Each suite imports production (`nplayer_preflop.py`) but does not own it.  
- The fifth core owner may only implement `nplayer_preflop.py` after all four RED receipts exist (line 265).  
- "No child owns shared legacy files" (line 266) prevents conflicts with `nplayer.py`, `api_v4.py`, `api_v3.py`, `cli.py`, `__init__.py`.  
- The gate requires focused tests, legacy controls (full regression), frozen hashes, fresh non-author audit, parent verification, and accepted-wave commit (lines 266–267).

**No overlap, RED-first enforced, legacy isolation clear.**

---

### 4.2 S3-I2 batch structure

**Architecture claim (§12 lines 269–278):**  
Four exclusive RED owners create:
1. `tests/test_nplayer_preflop_solve.py`;  
2. `tests/test_api_v4_nplayer_preflop.py`;  
3. `tests/test_phase4_s3_examples.py`;  
4. `tests/test_phase4_s3_exports.py`.  
A gated core owner may extend only `nplayer_preflop.py`; a core-gated integration owner may extend `api_v4.py`, `api_v3.py`, package exports, and examples after the RED and core receipts. `cli.py` changes are forbidden unless a genuine failing generic-CLI contract proves they are necessary. The same focused/full/freeze/fresh-audit/parent/commit gate applies.

**Assessment:** **PASS (clear exclusive ownership, integration gated, CLI protected)**  
The four test suites are nonoverlapping by domain:
- Solve (suite 1) vs. API (suite 2) vs. examples (suite 3) vs. exports (suite 4).  
- The core owner (gated by S3-I1 completion) may only extend `nplayer_preflop.py` (line 271).  
- The integration owner (gated by S3-I2 RED + core receipts) may extend `api_v4.py`, `api_v3.py`, exports, and examples (lines 271–272).  
- `cli.py` changes are forbidden unless a failing generic-CLI contract proves necessity (lines 272–273). The CLI audit (§3.1) found no change needed.  
- The same gate (focused/full/freeze/fresh-audit/parent/commit) applies (line 273).

**No overlap, integration gated, CLI protected.**

---

### 4.3 Ownership vs. existing S2 code

**Architecture claim (§12 line 266, line 272):**  
No child owns shared legacy files. `cli.py` changes are forbidden unless a genuine failing generic-CLI contract proves they are necessary.

**Evidence:**  
- `nplayer.py` (354 lines): generic N-player CFR solver, used by S2 and S3.  
- `api_v4.py` (497 lines): v4 dispatcher, currently routes S1 allstreet and S2 postflop.  
- `api_v3.py` (162 lines): v3 capabilities and utilities.  
- `cli.py` (235 lines): generic phase4 CLI, already forwards v4 requests.  
- `__init__.py` (21 lines): package exports, currently S1 and S2.

**Assessment:** **PASS (no S3 child owns legacy files, CLI change forbidden)**  
The S3-I1 test owners (config, betting, settlement, information) import `nplayer_preflop.py` but do not own `nplayer.py`, `api_v4.py`, `api_v3.py`, `cli.py`, or `__init__.py`. The S3-I1 core owner implements only `nplayer_preflop.py`. The S3-I2 integration owner (gated by S3-I1 + S3-I2 RED) may extend `api_v4.py`, `api_v3.py`, and `__init__.py` but not `nplayer.py` or `cli.py`. The CLI audit (§3.1) confirmed no change is needed. **No ownership conflict.**

---

## 5. Summary and verdict

### 5.1 Findings

| Domain | Assessment | Blocker? |
|--------|------------|----------|
| **1. Solver reuse** | Generic `NPlayerCFRSolver`, `expected_values_nplayer`, `unilateral_deviation_certificate` accept any `NPlayerGameState`. S3 only needs to implement the protocol. | **No** |
| **2. Reach propagation** | Existing CFR correctly propagates N player reaches + chance reach; regret weight excludes updating player. Architecture description matches implementation. | **No** |
| **3. Deviation bounds** | Exhaustive enumeration below cap, fails closed above, never claims Nash. Independent oracles required by acceptance matrix. | **No** |
| **4. V4 envelope** | Existing dispatcher routes two operations, returns required shape. S3 needs parallel `_dispatch_nplayer_preflop` and routing branch. | **No** |
| **5. V4 payload** | Strict validation primitives exist. S3 payload is more complex (forced posts, straddles, sizing rules, two continuation kinds, actor-labelled history) but feasible. | **No** |
| **6. Strategy serialization** | S2 stringifies keys/actions. S3 keys are complex tuples but `str()` produces deterministic reprs. | **No** |
| **7. CLI** | Generic phase4 CLI already forwards v4 file/stdin requests. No change needed. | **No** |
| **8. Examples** | CLI ready. Examples are synthetic bounded fixtures, implementation-gated (S3-I2). | **No** |
| **9. Exports** | Export pattern established (S2). S3 needs additive `__init__.py` symbols and v3 capability entry. | **No** |
| **10. Capability truth** | Architecture explicitly bounds scope, disclaims convergence, requires caller-supplied continuations, uses tiny synthetic fixtures. Metadata/provenance carry disclaimers. | **No** |
| **11. S3-I1 ownership** | Four exclusive RED test owners (config, betting, settlement, information) + one core owner (production). No overlap, RED-first enforced, legacy isolation clear. | **No** |
| **12. S3-I2 ownership** | Four exclusive RED test owners (solve, API, examples, exports) + gated core/integration owners. CLI protected. No overlap. | **No** |

### 5.2 Verdict

**PASS**

The repaired S3 architecture is feasible for implementation under the stated TDD ownership and acceptance gates. Specific findings:

1. **Solver reuse:** The generic N-player CFR, expected-value, and deviation helpers are protocol-driven. S3 only needs to implement `NPlayerGameState` (seven methods). No reach-propagation duplication is required.

2. **Strict v4 schema:** The existing v4 dispatcher provides strict validation primitives (bool-as-int rejection, finite checks, exact field sets, duplicate-key rejection) and a routing pattern. The S3 payload is more complex than S2 (forced posts, straddle variant, sizing rules, two continuation kinds, actor-labelled history) but all validation building blocks exist. Adding `solve-nplayer-preflop` requires a parallel `_dispatch_nplayer_preflop` function and a routing branch; no envelope change is needed.

3. **Examples/exports/capability truth:** The generic phase4 CLI already forwards v4 file/stdin requests to `dispatch_v4`; no CLI change is needed. Package exports follow the established S2 pattern (additive `__init__.py` symbols + v3 capability entry). The architecture explicitly bounds S3 scope to finite synthetic fixtures, caller-supplied continuations, and no convergence claim; metadata and provenance fields carry these disclaimers into the API response.

4. **TDD ownership:** S3-I1 has four exclusive RED test owners (config, betting, settlement, information) and one core owner (production `nplayer_preflop.py`), gated by all four RED receipts. S3-I2 has four exclusive RED test owners (solve, API, examples, exports), a core owner (gated by S3-I1), and an integration owner (gated by S3-I2 RED + core) who may extend `api_v4.py`, `api_v3.py`, exports, and examples. No S3 child owns `nplayer.py`, `cli.py`, or other legacy files. `cli.py` changes are forbidden unless a failing contract proves necessity; the audit found none. Ownership is nonoverlapping and RED-first.

### 5.3 Implementation gates

The architecture is design-complete and feasible. Implementation is gated by:

- **S3-I1:** Four RED test suites (config, betting, settlement, information) must exist and be parent-verified before the core owner implements `nplayer_preflop.py`.  
- **S3-I2:** Four RED test suites (solve, API, examples, exports) must exist; the core owner (gated by S3-I1) extends `nplayer_preflop.py`; the integration owner (gated by S3-I2 RED + core) extends `api_v4.py`, `api_v3.py`, `__init__.py`, and examples.  
- **Acceptance matrix (§13):** 299 lines of executable evidence requirements, including independent oracles for ledgers/reach/deviation, N=2 projection compatibility with frozen Phase-3 HU fixtures, straddle variant distinction, and full S1/S2 regression.

**No design blocker exists.** The candidate is accepted for implementation under the stated gates.

---

**Candidate SHA-256 after audit:** `f0777689eac5df76ab7630dd3725e40f7409e4369ba9de312ac8992a4a4bb83f` ✓  
**Audit complete:** 2026-09-16  
**Auditor:** A3Y5 (fresh non-author, design-only)
