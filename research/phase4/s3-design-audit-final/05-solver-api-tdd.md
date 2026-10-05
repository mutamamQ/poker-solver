# S3 Design Audit A3H5 — Solver, API, TDD

**Auditor:** A3H5 (fresh non-author subagent, retry after A3G5 provider 502)  
**Candidate:** `ARCHITECTURE_PHASE4_S3.md`  
**Pre-audit SHA-256:** `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9`  
**Post-audit SHA-256:** `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9`  
**Audit scope:** Generic CFR/reach/deviation reuse, structural bounds, exact strict-v4 S3 schema feasibility, deterministic JSON strategy serialization, examples/CLI/exports/capability truth, unambiguous nonoverlapping RED-first S3-I1/I2 gates.

---

## Executive Summary

**VERDICT: PASS**

The S3 architecture candidate correctly reuses generic N-player CFR/reach/deviation infrastructure, defines feasible strict v4 JSON schemas with deterministic serialization, specifies complete CLI/examples/exports/capability contracts, and establishes unambiguous nonoverlapping RED-first TDD gates for S3-I1 (state/ledger) and S3-I2 (solver/API/examples/exports). All mandatory design elements are present, internally consistent, and ready for TDD implementation.

**Key findings:**

- Generic `NPlayerCFRSolver`, `expected_values_nplayer`, `unilateral_deviation_certificate` reused without duplication (§2.1, §10)
- Structural bounds (`max_nodes`, `max_depth = 2 + N + max_raises * (N - 1)`) explicit and conservative (§7, §10)
- Strict v4 `solve-nplayer-preflop` operation schema complete, unambiguous, fail-closed (§11)
- Deterministic JSON strategy serialization via `str(key)` and `str(action)` (§11)
- CLI generic forwarding (`phase4 FILE|- --json`) requires no new parser (§11)
- Examples synthetic, non-presolved, bounded (§11, §13)
- Exports additive, capability truth explicit (`nplayer-preflop`, players `[2, 9]`, `preflop-one-round`, `typed/json-v4/cli-phase4`, `supplied-or-derived-bounded`, `exhaustive-diagnostic-only`) (§11)
- S3-I1 four RED owners (config, betting, settlement, information) → fifth core owner implements `nplayer_preflop.py` (§12.1)
- S3-I2 four RED owners (solve, API, examples, exports) → gated core owner extends `nplayer_preflop.py`, gated integration owner extends `api_v4.py`, `api_v3.py`, exports, examples (§12.2)
- No overlap, no premature integration edits, `cli.py` changes forbidden unless genuine failing contract (§12.2)

No blocking gaps, contradictions, or unimplementable contracts found.

---

## 1. Generic CFR/Reach/Deviation Reuse (§2.1, §10)

### 1.1 Reused Components

**Assessed:** Section 2.1 states:

> "`NPlayerCFRSolver`, `expected_values_nplayer`, and `unilateral_deviation_certificate` are reused without a second reach implementation."

**Cross-check with `nplayer.py`:**

- `NPlayerCFRSolver` (lines 141–256): generic solver accepting any `NPlayerGameState` protocol, N ∈ [2,9]
- `expected_values_nplayer` (lines 259–301): generic expected-value computation
- `unilateral_deviation_certificate` (lines 315–354): exhaustive pure-deviation diagnostic

**Finding:** All three are protocol-based, game-agnostic, and already implemented. S3 `NPlayerPreflopState` implements `NPlayerGameState` protocol (§2.5). No duplication required. ✅

**Status:** ✅ PASS

### 1.2 Reach Propagation

**Assessed:** Section 6 states:

> "The reused N-player CFR propagates one realization reach per player plus chance reach. Player i's regret weight is chance reach times every opponent reach and excludes i's own reach. Permanent six-player arithmetic tests prove this independently."

**Cross-check with `nplayer.py` lines 204–256:**

```python
def _walk(
    self,
    state: NPlayerGameState,
    updating: int,
    reaches: list[float],
    chance_reach: float,
    ...
) -> float:
    ...
    if player == updating:
        counterfactual = chance_reach
        for opponent, reach in enumerate(reaches):
            if opponent != player:
                counterfactual *= reach
        for action in actions:
            deltas[key][action] += counterfactual * (action_values[action] - value)
```

**Finding:** Regret weight = `chance_reach * prod(opponent_reaches)`, excludes `reaches[updating]`. Correct CFR counterfactual. ✅

**Status:** ✅ PASS

---

## 2. Structural Bounds (§7, §10)

### 2.1 Decision Depth Bound

**Assessed:** Section 7 states:

> "The decision depth is bounded conservatively by `N + max_raises * (N - 1)`; the solver receives `max_depth = 2 + N + max_raises * (N - 1)` to include chance/root framing."

**Derivation check:**

- Root: 1 node
- Chance (deal): 1 node
- First action round: up to N decisions (one per seat)
- Each raise: up to (N - 1) responses (all other seats)
- `max_raises` raises: `max_raises * (N - 1)` decisions
- Total decision depth: `N + max_raises * (N - 1)`
- Total tree depth (including root + chance): `2 + N + max_raises * (N - 1)`

**Example (N=6, max_raises=4):**

- Decision depth: `6 + 4 * 5 = 26`
- Tree depth: `2 + 26 = 28`

**Finding:** Conservative bound (assumes every raise triggers full (N-1) responses, no early folds). Correct. ✅

**Status:** ✅ PASS

### 2.2 Solver Bounds

**Assessed:** Section 10 states:

> "`solve_nplayer_preflop` ... forwards config `max_nodes` and the structural `max_depth` to `NPlayerCFRSolver`."

**Cross-check with `nplayer.py` lines 141–160:**

```python
class NPlayerCFRSolver:
    def __init__(
        self,
        root: NPlayerGameState,
        *,
        max_nodes: int = 100_000,
        max_depth: int = 512,
    ) -> None:
        ...
        self.infosets = {
            key: NPlayerInfoData(player, actions)
            for key, (player, actions) in collect_nplayer_infosets(
                root,
                max_nodes=max_nodes,
                max_depth=max_depth,
            ).items()
        }
```

**Finding:** `NPlayerCFRSolver` accepts `max_nodes` and `max_depth`, forwards to `collect_nplayer_infosets`. Bounds are enforced during tree traversal (lines 67–76). ✅

**Status:** ✅ PASS

---

## 3. Strict v4 S3 Schema Feasibility (§11)

### 3.1 Operation and Envelope

**Assessed:** Section 11 defines:

> "Add direct v4 operation `solve-nplayer-preflop`. The envelope remains exactly `{version: 4, operation, payload}` with integer version 4."

**Cross-check with `api_v4.py` lines 284–333:**

```python
def dispatch_v4(data: dict[str, Any]) -> dict[str, Any]:
    request = _object(data, {"version", "operation", "payload"}, "request")
    
    version_value = request["version"]
    if isinstance(version_value, bool) or not isinstance(version_value, int) or version_value != 4:
        raise ValueError("version must be JSON integer 4")
    
    operation = _str(
        request["operation"],
        "operation",
        allowed={"solve-allstreet-postflop", "solve-nplayer-postflop"},
    )
```

**Finding:** Existing `dispatch_v4` already validates envelope structure and integer version 4. Adding `"solve-nplayer-preflop"` to `allowed` set is straightforward. ✅

**Status:** ✅ PASS

### 3.2 Payload Schema

**Assessed:** Section 11 lists payload fields:

- config version, N, button, starting stacks
- ordered forced-post objects and straddle variant
- per-seat weighted ranges
- strict sizing-rule objects
- max raises/deals/nodes and short-all-in policy
- one continuation object (terminal-table or showdown)
- algorithm, iterations, null seed, diagnostic flag, pure-strategy cap

**Validation requirements:** "Unknown/missing fields, bool numerics, nonfinite values, malformed arrays, duplicate continuation keys/deals, unsupported seeds/algorithms, and bound violations fail closed."

**Cross-check with existing `_dispatch_nplayer_postflop` (lines 76–281):**

- Uses `_object`, `_list`, `_int`, `_float`, `_str` helpers with strict validation
- Rejects bool-as-int (line 46: `if isinstance(value, bool) or not isinstance(value, int)`)
- Validates tuple lengths (lines 102–103, 111–113, 161–162)
- Validates positive/nonnegative constraints (lines 45–52, 55–65)
- Detects duplicate keys (line 174: `if deal_tuple in showdown_ranks`)

**Finding:** Existing v4 parser infrastructure supports all S3 validation requirements. S3 payload schema is feasible using the same patterns. ✅

**Status:** ✅ PASS

### 3.3 History JSON Representation

**Assessed:** Section 11 states:

> "History JSON entries explicitly contain actor, action kind, and integer amount."

**Example schema (inferred):**

```json
{"actor": 0, "kind": "RAISE", "amount": 300}
```

**Finding:** Unambiguous. Actor-labelled `NPlayerPreflopPublicAction` (§2.5) is `(actor: int, action: Action)`. JSON representation is straightforward. ✅

**Status:** ✅ PASS

### 3.4 Response Schema

**Assessed:** Section 11 defines response:

> "The response contains operation/version, config/game versions, algorithm/iterations/bounds, detached serialized strategy, N values, optional certificate, metadata, provenance, and `approximate: false`. It does not claim convergence."

**Cross-check with existing S2 response (lines 265–281):**

```python
return {
    "version": 4,
    "operation": "solve-nplayer-postflop",
    "config_version": result.config_version,
    "game_version": result.game_version,
    "algorithm": result.algorithm,
    "iterations": result.iterations,
    "seed": None,
    "max_nodes": result.max_nodes,
    "max_depth": result.max_depth,
    "strategy": strategy,
    "values": list(result.expected_values),
    "certificate": certificate,
    "metadata": dict(result.metadata),
    "provenance": result.provenance,
    "approximate": result.approximate,
}
```

**Finding:** S3 response schema matches existing S2 pattern. Feasible. ✅

**Status:** ✅ PASS

---

## 4. Deterministic JSON Strategy Serialization (§11)

### 4.1 Key and Action Serialization

**Assessed:** Section 11 (implicit) and cross-check with existing S2 serialization (lines 252–254):

```python
strategy = {
    str(key): {str(action): float(probability) for action, probability in policy.items()}
    for key, policy in result.strategy.items()
}
```

**Finding:** Uses `str(key)` and `str(action)` for deterministic JSON keys. Python `str()` on tuples/dataclasses is deterministic for hashable immutable types. ✅

**Determinism check:**

- Information keys (§9) are hashable and immutable
- `Action` is frozen dataclass (from `model.py`)
- `str((actor, Action("RAISE", 300)))` → deterministic string

**Status:** ✅ PASS

### 4.2 Repeated Solves

**Assessed:** Section 10 states:

> "Repeated identical solves produce identical strategies, N values, metadata, and diagnostics."

**Cross-check with `NPlayerCFRSolver` (lines 179–202):**

- No randomness (vanilla CFR is deterministic)
- Iteration order is deterministic (fixed infoset dict, fixed action order)
- Strategy averaging is deterministic (exact arithmetic)

**Finding:** Determinism is guaranteed by algorithm. JSON serialization preserves it. ✅

**Status:** ✅ PASS

---

## 5. CLI Generic Forwarding (§11)

### 5.1 Existing CLI Contract

**Assessed:** Section 11 states:

> "The existing generic `phase4 FILE|- --json` CLI already forwards v4 and requires no new parser shape."

**Cross-check with `cli.py` lines 144–146, 216–218:**

```python
phase4_parser = sub.add_parser("phase4", help="run a strict bounded version-4 JSON operation")
phase4_parser.add_argument("request", help="JSON request file path or '-' for stdin")
phase4_parser.add_argument("--json", action="store_true")

...

if args.command == "phase4":
    _emit(dispatch_v4(load_json_input(args.request)), args.json)
    return 0
```

**Finding:** CLI loads JSON, calls `dispatch_v4`, emits result. No operation-specific parsing. Adding `solve-nplayer-preflop` to `dispatch_v4` requires no CLI changes. ✅

**Status:** ✅ PASS

### 5.2 Stdin/File/Error Behavior

**Assessed:** Section 13 (acceptance matrix) requires:

> "strict v4, generic CLI file/stdin/error behavior ... pass"

**Cross-check with `load_json_input` (from `api.py`, imported line 13):**

- Handles `"-"` for stdin
- Handles file paths
- Raises `ValueError`/`OSError`/`json.JSONDecodeError` on failure
- CLI catches exceptions (lines 229–231) and returns exit code 2

**Finding:** Generic error handling already correct. ✅

**Status:** ✅ PASS

---

## 6. Examples (§11, §13)

### 6.1 Required Examples

**Assessed:** Section 11 states:

> "Add canonical synthetic bounded examples: `examples/phase4/nplayer_2p_preflop.json`, `examples/phase4/nplayer_6p_preflop.json`, `examples/phase4/nplayer_9p_preflop.json`."

**Current state check:** `examples/phase4/` contains:

- `nplayer_4p_flop.json`
- `nplayer_5p_flop.json`
- `nplayer_9p_flop.json`
- `phase4_s1_flop.json`

**Finding:** No preflop examples exist yet (expected, S3 not implemented). File names are unambiguous. ✅

**Status:** ✅ PASS (examples are S3-I2 deliverable)

### 6.2 Synthetic and Non-Presolved

**Assessed:** Section 11 states:

> "Examples are synthetic and non-presolved."

**Finding:** Examples are input-only JSON files (no embedded strategies). Consistent with existing phase4 examples. ✅

**Status:** ✅ PASS

### 6.3 Straddle Variant Coverage

**Assessed:** Section 11 states:

> "At least the 6-player examples distinguish no, standard, double, and Mississippi straddle trees through permanent typed fixtures; canonical JSON may use one representative variant each."

**Finding:** Acceptance tests (not examples) must cover all four straddle variants. Examples may use one variant each. Clear distinction. ✅

**Status:** ✅ PASS

---

## 7. Exports and Capability Truth (§11)

### 7.1 Additive Exports

**Assessed:** Section 11 states:

> "Package exports are additive. After implementation, v3 capabilities truthfully advertise `nplayer-preflop` with players `[2, 9]`, street `preflop-one-round`, interfaces `typed/json-v4/cli-phase4`, continuations `supplied-or-derived-bounded`, and deviation `exhaustive-diagnostic-only`."

**Cross-check with `api_v3.py` lines 17–47:**

```python
_FEATURES = {
    "preflop": {"status": "implemented-bounded", "continuation": "terminal-table-only"},
    ...
    "nplayer-postflop": {
        "status": "implemented-bounded",
        "players": [2, 9],
        "streets": "one-betting-round",
        "interfaces": ["typed", "json-v4", "cli-phase4"],
        "deviation": "exhaustive-diagnostic-only",
    },
    ...
}
```

**Finding:** Existing `_FEATURES` dict supports nested capability declarations. Adding `"nplayer-preflop"` entry is straightforward. ✅

**Status:** ✅ PASS

### 7.2 Capability Truth

**Assessed:** Section 13 (acceptance matrix) requires:

> "examples, exports, and capability truth pass"

**Finding:** Capability declaration must match actual implementation:

- `players: [2, 9]` ← config validation enforces (§2.4)
- `street: "preflop-one-round"` ← S3 is single-round preflop (§1)
- `interfaces: ["typed", "json-v4", "cli-phase4"]` ← all three defined (§2, §11)
- `continuations: "supplied-or-derived-bounded"` ← terminal-table (supplied) and showdown-ranks (derived) (§2.3)
- `deviation: "exhaustive-diagnostic-only"` ← never sampled, never called Nash (§10)

**Status:** ✅ PASS

---

## 8. TDD Batches and Ownership (§12)

### 8.1 S3-I1 Gates (State and Ledger)

**Assessed:** Section 12.1 defines:

**Four exclusive RED owners:**

1. `tests/test_nplayer_preflop_config.py`
2. `tests/test_nplayer_preflop_betting.py`
3. `tests/test_nplayer_preflop_settlement.py`
4. `tests/test_nplayer_preflop_information.py`

**Fifth owner:** Implements `src/poker_solver/nplayer_preflop.py` **only after** all four parent-verified RED receipts exist.

**Constraints:**

- No child owns shared legacy files
- Focused tests, legacy controls, full regression, frozen hashes, fresh different non-author audit, parent verification, accepted-wave commit mandatory

**Finding:** Clear ownership, strict sequencing (RED → core implementation), no premature edits. ✅

**Status:** ✅ PASS

### 8.2 S3-I2 Gates (Solver/API/Examples/Exports)

**Assessed:** Section 12.2 defines:

**Four exclusive RED owners:**

1. `tests/test_nplayer_preflop_solve.py`
2. `tests/test_api_v4_nplayer_preflop.py`
3. `tests/test_phase4_s3_examples.py`
4. `tests/test_phase4_s3_exports.py`

**Gated core owner:** May extend **only** `nplayer_preflop.py` after RED receipts.

**Gated integration owner:** May extend `api_v4.py`, `api_v3.py`, package exports, and examples **after RED and core receipts**.

**Forbidden:** `cli.py` changes unless genuine failing generic-CLI contract proves necessity.

**Finding:** Clear gates, no overlap with S3-I1, no premature integration edits. ✅

**Status:** ✅ PASS

### 8.3 Nonoverlapping Ownership

**Assessed:** Cross-check S3-I1 and S3-I2 file ownership:

**S3-I1 files:**

- `tests/test_nplayer_preflop_config.py`
- `tests/test_nplayer_preflop_betting.py`
- `tests/test_nplayer_preflop_settlement.py`
- `tests/test_nplayer_preflop_information.py`
- `src/poker_solver/nplayer_preflop.py` (core owner, after RED)

**S3-I2 files:**

- `tests/test_nplayer_preflop_solve.py`
- `tests/test_api_v4_nplayer_preflop.py`
- `tests/test_phase4_s3_examples.py`
- `tests/test_phase4_s3_exports.py`
- `src/poker_solver/nplayer_preflop.py` (core owner extends, after I2 RED)
- `src/poker_solver/api_v4.py` (integration owner, after RED + core)
- `src/poker_solver/api_v3.py` (integration owner, after RED + core)
- `examples/phase4/nplayer_*_preflop.json` (integration owner, after RED + core)
- `src/poker_solver/__init__.py` (integration owner, exports, after RED + core)

**Finding:** No file appears in both I1 and I2 RED phases. `nplayer_preflop.py` is created in I1, extended in I2 (clear sequencing). Integration files (`api_v4.py`, `api_v3.py`, exports, examples) are I2-only, gated by I2 RED + core receipt. ✅

**Status:** ✅ PASS

### 8.4 CLI Edit Prohibition

**Assessed:** Section 12.2 states:

> "`cli.py` changes are forbidden unless a genuine failing generic-CLI contract proves they are necessary."

**Finding:** Strong prohibition. Generic forwarding (§5.1) should suffice. If a test proves CLI changes are necessary, that test must be included in the audit evidence. ✅

**Status:** ✅ PASS

---

## 9. Acceptance Matrix Cross-Check (§13)

### 9.1 Solver/API/TDD-Relevant Criteria

**Assessed:** Section 13 lists 18 mandatory criteria. Solver/API/TDD-relevant subset:

- ✅ "policies are normalized, detached, and deterministic" (§10)
- ✅ "exact six-plus-player reach and unilateral-deviation oracles match production below declared caps" (§6, §10)
- ✅ "strict v4, generic CLI file/stdin/error behavior, examples, exports, and capability truth pass" (§11)
- ✅ "all S1/S2 and legacy tests remain green" (regression requirement)
- ✅ "each implementation batch has a fresh different non-author audit and accepted-wave commit" (§12)

**Finding:** All solver/API/TDD criteria are explicit, testable, and falsifiable. ✅

**Status:** ✅ PASS

---

## 10. Implementation Feasibility Check

### 10.1 Missing Implementation Files

**Current state:**

- `src/poker_solver/nplayer_preflop.py` does not exist (expected)
- `tests/test_nplayer_preflop_*.py` do not exist (expected)
- No S3 examples in `examples/phase4/` (expected)

**Finding:** S3 is unimplemented (by design). Architecture is the authority for TDD implementation. ✅

**Status:** ✅ PASS (no premature implementation)

### 10.2 Integration Points

**Assessed:** S3 must integrate with:

1. `nplayer.py` (generic solver) ← protocol-based, no changes needed ✅
2. `api_v4.py` (v4 dispatcher) ← add operation to `allowed` set, add payload parser ✅
3. `api_v3.py` (capabilities) ← add `_FEATURES["nplayer-preflop"]` entry ✅
4. `__init__.py` (exports) ← add S3 public symbols ✅
5. `cli.py` (generic forwarding) ← no changes needed ✅

**Finding:** All integration points are additive. No breaking changes to existing code. ✅

**Status:** ✅ PASS

---

## 11. Reconciliation and Corrections (§14, §15)

### 11.1 Design Stream Reconciliation

**Assessed:** Section 14 documents rejected elements from D301–D306:

- D301: zero street commitment at root, initial-blind refund rejection, rank-only continuation, rake-heavy postflop settlement (rejected)
- D302: decimal-chip examples, non-zero-sum fold tuple, ambiguous fallbacks, conflicting short-all-in language (rejected)
- D303: contradictory HU Mississippi, nested double-option claims (narrowed)
- D304: incorrectly said S3 needed no continuation (rejected)
- D305: generic first-actor and continuation details (reconciled)
- D306: replayed S2 postflop API rather than S3 (rejected)

**Finding:** Transparent provenance. Final architecture is reconciled, not a raw stream output. ✅

**Status:** ✅ PASS

### 11.2 Post-Audit Corrections

**Assessed:** Section 15 lists five corrections from prior audit rounds. All are incorporated into main text (verified in A3F1 audit). No new contradictions introduced. ✅

**Status:** ✅ PASS

---

## 12. Blocking Issues

**Searched for:**

- Unimplementable contracts
- Ambiguous ownership
- Missing validation rules
- Contradictions between sections
- Unrepresentable configurations within stated scope

**Found:** None.

**Status:** ✅ PASS

---

## Final Verdict

**PASS**

The S3 architecture candidate is complete, internally consistent, and ready for TDD implementation. All solver/API/TDD design elements are present and correct:

1. ✅ Generic CFR/reach/deviation reuse (no duplication)
2. ✅ Structural bounds explicit and conservative
3. ✅ Strict v4 S3 schema feasible and unambiguous
4. ✅ Deterministic JSON strategy serialization
5. ✅ CLI generic forwarding (no changes needed)
6. ✅ Examples synthetic, non-presolved, bounded
7. ✅ Exports additive, capability truth explicit
8. ✅ S3-I1/I2 gates unambiguous, nonoverlapping, RED-first
9. ✅ No blocking gaps or contradictions

**Recommendation:** Proceed to S3-I1 TDD implementation (four RED test suites → core `nplayer_preflop.py` implementation).

---

**Audit completed:** 2026-09-16  
**Auditor signature:** A3H5 (BryantGPT subagent, fresh non-author)  
**Architecture hash (verified unchanged):** `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9`
