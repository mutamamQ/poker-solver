# S3 solver/API/TDD feasibility and release integration audit

**Auditor:** A3J5  
**Candidate:** `/home/genomix-node/poker-solver/ARCHITECTURE_PHASE4_S3.md`  
**Pre-audit SHA-256:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`  
**Post-audit SHA-256:** `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`  
**Verdict:** **PASS** — zero blockers

---

## 1. Generic CFR/reach/deviation reuse

**Claim (§2.2, §10):** S3 reuses `NPlayerCFRSolver`, `expected_values_nplayer`, and `unilateral_deviation_certificate` without a second reach implementation.

**Evidence:**
- `nplayer.py` (lines 141–256) implements one N-player CFR with `reaches: list[float]` (one per player) plus `chance_reach: float`.
- Regret weight at line 250–253: `counterfactual = chance_reach * prod(reaches[opponent] for opponent != player)`, matching the S3 spec.
- `solve_nplayer_preflop` (§10) accepts only `algorithm="vanilla-cfr"` and forwards to the shared solver.
- No second CFR or reach implementation is declared.

**Attack:** Could S3 silently require a preflop-specific reach formula?
- The architecture explicitly states "Player i's regret weight is chance reach times every opponent reach and excludes i's own reach" (§6, end).
- `nplayer.py` line 250–253 implements exactly that formula.
- S3-I1 batch 4 (§12) must create `test_nplayer_preflop_information.py` with independent six-player reach oracles; this is an executable acceptance gate, not assumed.

**Conclusion:** Generic reuse is feasible and testable. **PASS.**

---

## 2. Max-depth/max-node/max-deal bounds

**Claim (§2.4, §7, §10):** Config validation rejects `max_deals`, `max_raises`, `max_nodes` violations; `max_depth` is derived and forwarded.

**Evidence:**
- §2.4: "The Cartesian product `prod(len(range_i))` must not exceed `max_deals`; this precheck bounds work even if blockers eliminate every candidate."
- §7: "The decision depth is bounded conservatively by `N + max_raises * (N - 1)`; the solver receives `max_depth = 2 + N + max_raises * (N - 1)` to include chance/root framing."
- `nplayer.py` lines 60–63, 69–73: `collect_nplayer_infosets` enforces `max_nodes` and `max_depth` with `ValueError` on violation.
- §6: "No compatible deals, zero exact mass, or candidate product above `max_deals` fails closed."

**Attack:** Could a valid config still exceed bounds at runtime?
- The Cartesian precheck (§2.4) occurs before any deal enumeration.
- The depth formula (§7) is deterministic and independent of actual action sequences.
- `collect_nplayer_infosets` (lines 67–76) tracks `visited` nodes and `depth` with hard failure.

**Conclusion:** Bounds are pre-validated and enforced. **PASS.**

---

## 3. Strict v4 `solve-nplayer-preflop` request/response feasibility

**Claim (§11):** Direct v4 operation with strict envelope `{version: 4, operation, payload}`, integer version 4, explicit actor/action/amount history, unknown/bool/nonfinite rejection, and detached response.

**Evidence:**
- `api_v4.py` lines 284–333: `dispatch_v4` validates `version` as JSON integer 4 (line 324), operation in allowed set (line 327–332), and dispatches `solve-nplayer-postflop` via `_dispatch_nplayer_postflop`.
- Lines 45–52 (`_int`), 55–65 (`_float`): reject bool-as-int (line 46, 56), enforce positive/nonnegative, and enforce finite (line 61–62).
- S2 postflop dispatcher (lines 76–281) shows the pattern: strict field validation, nested object/list parsing, detached typed construction, and serialized response.
- §11 specifies history JSON entries "explicitly contain actor, action kind, and integer amount" and "unknown/missing fields, bool numerics, nonfinite values … fail closed."

**Attack:** Is the S3 operation actually implemented in `api_v4.py`?
- Line 330: `allowed={"solve-allstreet-postflop", "solve-nplayer-postflop"}` — S2 postflop is present.
- §11 states "Add direct v4 operation `solve-nplayer-preflop`" — this is a design-only document; implementation is S3-I2 batch 2 (§12).
- The S2 dispatcher (lines 76–281) is a complete executable template for the S3 dispatcher.

**Conclusion:** The v4 contract is feasible and follows the established S2 pattern. Implementation is gated to S3-I2. **PASS.**

---

## 4. Bool/nonfinite/unknown rejection

**Claim (§11):** "Unknown/missing fields, bool numerics, nonfinite values, malformed arrays, duplicate continuation keys/deals, unsupported seeds/algorithms, and bound violations fail closed."

**Evidence:**
- `api_v4.py` lines 10–73: `_object`, `_list`, `_int`, `_float`, `_str` helpers enforce strict types.
- Line 46: `if isinstance(value, bool) or not isinstance(value, int)` — bool-as-int rejected.
- Line 56: `if isinstance(value, bool)` — bool-as-float rejected.
- Line 61–62: `if finite and not isfinite(result): raise ValueError` — nonfinite rejected.
- Lines 12–18: `_object` raises on extra or missing fields.
- S2 dispatcher line 174: `if deal_tuple in showdown_ranks: raise ValueError("duplicate showdown deal")` — duplicate keys rejected.
- Line 218: `if payload["seed"] is not None: raise ValueError("vanilla-cfr requires seed null")` — unsupported seed rejected.

**Attack:** Could S3 silently accept bool `True` as integer `1`?
- Python `isinstance(True, int)` is `True`, but the guard `isinstance(value, bool)` is checked first (line 46, 56).
- This pattern is already deployed in S1/S2 v4 dispatchers.

**Conclusion:** Bool/nonfinite/unknown rejection is implemented and reusable. **PASS.**

---

## 5. Deterministic key/action JSON serialization

**Claim (§11):** "Conversion creates detached typed values" and response contains "detached serialized strategy."

**Evidence:**
- `api_v4.py` lines 252–255 (S2 postflop): `strategy = {str(key): {str(action): float(probability) ...} ...}` — keys and actions stringified.
- `cli.py` lines 49–53: `_strategy_json` uses `sorted(strategy.items(), key=lambda item: repr(item[0]))` and `sorted(policy)` — deterministic order.
- Line 58: `json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)` — sorted keys, no NaN.
- §11: "History JSON entries explicitly contain actor, action kind, and integer amount" — structured, not opaque.

**Attack:** Could two identical strategies serialize differently?
- `str(key)` and `str(action)` are deterministic for immutable frozen types.
- `sort_keys=True` enforces lexicographic order.
- S3-I2 batch 2 (§12) must create `test_api_v4_nplayer_preflop.py` with deterministic serialization tests.

**Conclusion:** Serialization is deterministic and testable. **PASS.**

---

## 6. Generic CLI

**Claim (§11):** "The existing generic `phase4 FILE|- --json` CLI already forwards v4 and requires no new parser shape."

**Evidence:**
- `cli.py` lines 144–146: `phase4_parser = sub.add_parser("phase4", help="run a strict bounded version-4 JSON operation"); phase4_parser.add_argument("request", help="JSON request file path or '-' for stdin"); phase4_parser.add_argument("--json", action="store_true")`.
- Lines 216–218: `if args.command == "phase4": _emit(dispatch_v4(load_json_input(args.request)), args.json); return 0`.
- `dispatch_v4` (line 284) is the single entry point; it dispatches by `operation` field.
- §11: "CLI changes are forbidden unless a genuine failing generic-CLI contract proves they are necessary" (§12, S3-I2).

**Attack:** Does the CLI need S3-specific argument parsing?
- No. The `phase4` subcommand accepts arbitrary JSON and delegates to `dispatch_v4`.
- S3 adds a new `operation` value, not a new CLI shape.

**Conclusion:** Generic CLI is sufficient. **PASS.**

---

## 7. Synthetic examples

**Claim (§11):** "Add canonical synthetic bounded examples: `examples/phase4/nplayer_2p_preflop.json`, `nplayer_6p_preflop.json`, `nplayer_9p_preflop.json`. … Examples are synthetic and non-presolved."

**Evidence:**
- §1: "All HU, 6-player, and 9-player S3 acceptance fixtures use deliberately tiny synthetic per-seat ranges whose full Cartesian product is at most `max_deals`. They prove player-count generality and exact chance arithmetic, not realistic full-range tractability."
- §11: "At least the 6-player examples distinguish no, standard, double, and Mississippi straddle trees through permanent typed fixtures; canonical JSON may use one representative variant each."
- S3-I2 batch 3 (§12): `test_phase4_s3_examples.py` — executable validation.

**Attack:** Could examples be too large to execute?
- §2.4: "The Cartesian product … must not exceed `max_deals`" — config validation enforces this.
- Tiny synthetic ranges (e.g., 2–4 combos per seat) keep the product small.

**Conclusion:** Synthetic examples are feasible and bounded. **PASS.**

---

## 8. Additive exports

**Claim (§11):** "Package exports are additive. After implementation, v3 capabilities truthfully advertise `nplayer-preflop` with players `[2, 9]`, street `preflop-one-round`, interfaces `typed/json-v4/cli-phase4`, continuations `supplied-or-derived-bounded`, and deviation `exhaustive-diagnostic-only`."

**Evidence:**
- `api_v3.py` lines 17–47: `_FEATURES` dict with existing entries.
- Line 27–33: `"nplayer-postflop": {"status": "implemented-bounded", "players": [2, 9], "streets": "one-betting-round", "interfaces": ["typed", "json-v4", "cli-phase4"], "deviation": "exhaustive-diagnostic-only"}`.
- §11 specifies a parallel `nplayer-preflop` entry with the same structure.
- S3-I2 batch 4 (§12): `test_phase4_s3_exports.py` — executable validation.

**Attack:** Could S3 exports conflict with existing entries?
- `nplayer-preflop` is a new key, not a modification of an existing one.
- The structure matches the S2 postflop pattern.

**Conclusion:** Additive exports are feasible. **PASS.**

---

## 9. Truthful capability data

**Claim (§11):** Capabilities advertise `supplied-or-derived-bounded` continuations and `exhaustive-diagnostic-only` deviation.

**Evidence:**
- §2.3: `NPlayerPreflopContinuation` has `kind: Literal["terminal-table", "showdown-ranks"]` and `source: Literal["supplied", "derived"]`.
- §2.3: "For `showdown-ranks`, … production … derives exact zero-sum chip utilities. This is a synthetic bounded continuation, not automatic board rollout or equity evaluation."
- §10: "The unilateral-deviation certificate is exhaustive below its cap or fails closed; it is never sampled and never called exploitability or a Nash certificate."
- `nplayer.py` lines 315–354: `unilateral_deviation_certificate` enumerates pure deviations with `prod(len(actions) for _, actions in owned)` and raises on `max_pure_strategies` violation (line 336).

**Attack:** Could the capability claim "automatic" continuation?
- §1: "S3 is a finite reference path. It does not claim … automatic abstraction, continuous sizing, or automatic multi-street solving."
- The capability string `supplied-or-derived-bounded` explicitly excludes automatic.

**Conclusion:** Capability data is truthful. **PASS.**

---

## 10. Unambiguous nonoverlapping RED-first S3-I1/I2 ownership gates

**Claim (§12):** S3-I1 has four exclusive RED owners (config, betting, settlement, information); a fifth core owner implements only after all four parent-verified RED receipts. S3-I2 has four exclusive RED owners (solve, API, examples, exports); gated core and integration owners extend only after RED and core receipts.

**Evidence:**
- §12, S3-I1: "Four exclusive RED owners create permanent production-importing suites: 1. `test_nplayer_preflop_config.py` … 2. `test_nplayer_preflop_betting.py` … 3. `test_nplayer_preflop_settlement.py` … 4. `test_nplayer_preflop_information.py`. A fifth owner may implement `src/poker_solver/nplayer_preflop.py` only after all four parent-verified RED receipts exist."
- §12, S3-I2: "Four exclusive RED owners create: 1. `test_nplayer_preflop_solve.py`; 2. `test_api_v4_nplayer_preflop.py`; 3. `test_phase4_s3_examples.py`; 4. `test_phase4_s3_exports.py`. A gated core owner may extend only `nplayer_preflop.py`; a core-gated integration owner may extend `api_v4.py`, `api_v3.py`, package exports, and examples after the RED and core receipts."
- "No child owns shared legacy files."
- "Focused tests, legacy controls, full regression, frozen hashes, a fresh different non-author audit, parent verification, and an accepted-wave commit are mandatory."

**Attack:** Could two RED owners collide on the same test file?
- Each test file is named uniquely and assigned to exactly one owner.
- The core implementation file `nplayer_preflop.py` is owned by a single gated owner in I1.
- Integration files (`api_v4.py`, `api_v3.py`, exports, examples) are owned by a single gated owner in I2.

**Attack:** Could a RED owner start implementation before tests exist?
- "A fifth owner may implement … only after all four parent-verified RED receipts exist."
- "A gated core owner may extend … after the RED and core receipts."
- These are explicit blocking gates.

**Conclusion:** Ownership is unambiguous and nonoverlapping. **PASS.**

---

## 11. Executable acceptance criteria without unstated evaluator behavior

**Claim (§13):** "S3 is complete only when executable evidence proves" 15 acceptance criteria.

**Evidence (sample):**
- §13, criterion 1: "strict configs accept every N from 2 through 9 and reject malformed types, lengths, posts, variants, sizing keys, continuations, and bounds" — executable via `test_nplayer_preflop_config.py`.
- §13, criterion 6: "independent integer/rational oracles match fold, refund, side-pot, tie, odd-chip, terminal-table, and derived-showdown leaves" — §2.3 states "Permanent tests hand-declare tiny rank vectors and independently compute winners, layers, splits, and odd-chip recipients; no production evaluator is used as the expected-value oracle."
- §13, criterion 10: "exact six-plus-player reach and unilateral-deviation oracles match production below declared caps" — independent oracle, not production self-check.
- §13, criterion 11: "N=2 projected deals/actions/ledgers/terminals/information partitions match frozen Phase-3 HU fixtures" — §1 defines projection: "Align states by deterministic chance outcome and public action path, then compare: normalized private deals and exact masses; acting seat; ordered legal `Action` tuples; pot, street commitments, total contributions, remaining stacks, and fold status; and exact terminal utilities."

**Attack:** Could "independent oracle" secretly call production helpers?
- §8: "Independent permanent ledger fixtures must calculate expected refunds, layers, awards, final stacks, and utilities without importing production settlement helpers."
- §2.3: "no production evaluator is used as the expected-value oracle."
- These are explicit prohibitions.

**Attack:** Could acceptance criteria require unstated behavior?
- Every criterion references a specific architecture section with explicit contracts.
- Oracles are defined as "independent" or "hand-declared."

**Conclusion:** Acceptance criteria are executable and do not rely on unstated evaluator behavior. **PASS.**

---

## 12. Cross-release integration

**Claim (§1, §13):** "Existing heads-up `preflop.py`, S1 all-street postflop, S2 N-player postflop, generic `nplayer.py`, and all legacy APIs keep their public behavior. … N=2 compatibility is established through projected public traces, not raw type, version, history-record, or information-key equality."

**Evidence:**
- §1: "The implementation is additive. … The N=2 projection is explicit."
- §13, criterion 11: "N=2 projected deals/actions/ledgers/terminals/information partitions match frozen Phase-3 HU fixtures."
- §13, criterion 9: "all S1/S2 and legacy tests remain green."
- §13, criterion 10: "each implementation batch has a fresh different non-author audit and accepted-wave commit."
- §13, criterion 11: "`phase3-398-green` remains exactly at `feba8222a0b614b0c64eca59402403ce733195ea`."
- PHASE4_MISSION.md line 55: "Preserve the 398-test baseline: every batch ends with the prior suite green (new tests additive)."

**Attack:** Could S3 break legacy tests?
- The architecture explicitly forbids modification of legacy files (§12: "No child owns shared legacy files").
- The 398-test baseline is frozen at a specific commit SHA.
- S3-I1 and S3-I2 gates require "all S1/S2 and legacy tests remain green."

**Conclusion:** Cross-release integration is contractually protected. **PASS.**

---

## Summary

All 12 audit dimensions pass:

1. **Generic CFR/reach/deviation reuse:** `nplayer.py` implements the exact reach formula; no second implementation needed.
2. **Max-depth/max-node/max-deal bounds:** Pre-validated and enforced by `collect_nplayer_infosets`.
3. **Strict v4 request/response:** Follows established S2 pattern; implementation gated to S3-I2.
4. **Bool/nonfinite/unknown rejection:** Implemented in `api_v4.py` helpers and reusable.
5. **Deterministic serialization:** `str(key)`, `str(action)`, `sort_keys=True` enforce determinism.
6. **Generic CLI:** `phase4` subcommand forwards arbitrary v4 JSON; no S3-specific parser needed.
7. **Synthetic examples:** Tiny ranges keep Cartesian product below `max_deals`.
8. **Additive exports:** New `nplayer-preflop` key does not conflict with existing entries.
9. **Truthful capability data:** `supplied-or-derived-bounded` and `exhaustive-diagnostic-only` match implementation.
10. **Unambiguous ownership gates:** Four exclusive RED owners per batch; gated core/integration owners; no overlap.
11. **Executable acceptance criteria:** 15 criteria reference explicit contracts; independent oracles prohibited from calling production.
12. **Cross-release integration:** Additive implementation; N=2 projection; frozen 398-test baseline; legacy tests green.

**Zero blockers.** The refrozen S3 design is executable under strict TDD with the declared ownership gates and acceptance matrix.
