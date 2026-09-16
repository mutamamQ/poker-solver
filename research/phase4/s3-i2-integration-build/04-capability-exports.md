# S3-I2 Integration Build: Capability Exports and Truth Requirements

Parent reconciliation (2026-09-16T10:05:24Z): this is a pre-implementation contract report. The current candidate now provides the nine exports and exact capability object, and the permanent export/capability suite passes 13/13. Statements below using "currently missing" describe the accepted RED base, not the current candidate.

**Agent:** C3I2-IG4 (read-only capability/export analyst)
**Workspace:** `/home/genomix-node/poker-solver`
**Scope:** Map exact nine S3 package exports and exact `nplayer-preflop` capability object; prove S1/S2 exports/capabilities remain byte-for-byte truth-equivalent/detached/deterministic.

---

## 1. Exact Nine S3 Package Exports

**Source:** `tests/test_phase4_s3_exports.py` lines 21–90
**Target module:** `src/poker_solver/__init__.py` (currently missing S3 exports)

The following nine symbols from `src/poker_solver/nplayer_preflop.py` must be exported from the `poker_solver` package root:

1. **`NPlayerPreflopConfig`** (class, line 240 in nplayer_preflop.py)
2. **`NPlayerPreflopContinuation`** (class, line 159)
3. **`NPlayerPreflopSizingRule`** (class, line 123)
4. **`NPlayerPreflopPublicAction`** (class, line 147)
5. **`NPlayerPreflopState`** (class, line 567)
6. **`NPlayerPreflopSolveResult`** (class, line 1056)
7. **`enumerate_nplayer_preflop_deals`** (function, line 425)
8. **`create_nplayer_preflop_root`** (function, line 1009)
9. **`solve_nplayer_preflop`** (function, line 1080)

**Test contract:** Each export must be the identical object (`is` identity) to the defining symbol in `nplayer_preflop` module.

---

## 2. Exact `nplayer-preflop` Capability Object

**Source:** `tests/test_phase4_s3_exports.py` lines 93–149
**Target:** `src/poker_solver/api_v3.py` `_FEATURES` dict (lines 17–47)

### 2.1 Required Capability Structure

The `dispatch_v3({"version": 3, "operation": "capabilities", "payload": {}})` response must include a `features["nplayer-preflop"]` entry with **exactly** these fields:

```python
{
    "status": "implemented-bounded",
    "players": [2, 9],
    "street": "preflop-one-round",
    "interfaces": ["typed", "json-v4", "cli-phase4"],
    "continuations": "supplied-or-derived-bounded",
    "deviation": "exhaustive-diagnostic-only"
}
```

**Field semantics:**

- `status`: Bounded implementation (not unrestricted)
- `players`: Inclusive range [2, 9] (list literal, not tuple)
- `street`: Single preflop betting round
- `interfaces`: Typed Python API, JSON v4 dispatch, CLI Phase 4
- `continuations`: Caller-supplied terminal table OR caller-supplied showdown ranks (bounded, not automatic equity)
- `deviation`: Exhaustive unilateral deviation certificate available (diagnostic-only, not convergence proof)

### 2.2 Truth Requirements

**Determinism:** Repeated `dispatch_v3(capabilities)` calls must return identical deep-equal results (test lines 132–134).

**Deep-copy isolation:** Caller mutations to the returned `features` dict or nested lists/dicts must NOT affect subsequent calls (test lines 136–149). Implementation must use `deepcopy(_FEATURES)` (current api_v3.py line 95 already does this for existing features).

**No silent drift:** The capability object is a **permanent truth contract**. Fields must match actual implementation capabilities:

- `players: [2, 9]` ← validated by `NPlayerPreflopConfig` (nplayer_preflop.py line 73: `num_players: int` strict 2–9)
- `street: "preflop-one-round"` ← single-round preflop (ARCHITECTURE_PHASE4_S3.md line 5)
- `continuations: "supplied-or-derived-bounded"` ← `NPlayerPreflopContinuation.kind` is `"terminal-table"` or `"showdown-ranks"` (nplayer_preflop.py line 168), never automatic equity
- `deviation: "exhaustive-diagnostic-only"` ← `solve_nplayer_preflop` returns `UnilateralDeviationCertificate` when requested (line 1107–1112), metadata confirms `"exhaustive-diagnostic-only"` (line 1129)

---

## 3. Existing S1/S2 Export Truth Preservation

**Source:** `tests/test_phase4_s3_exports.py` lines 152–188
**Current state:** `src/poker_solver/__init__.py` lines 3–19

### 3.1 S1 Exports (All-Street Postflop)

Must remain **byte-for-byte identical** `is` references:

- `AllStreetPostflopConfig` ← `allstreet.AllStreetPostflopConfig`
- `AllStreetSolveResult` ← `allstreet.AllStreetSolveResult`
- `create_allstreet_root` ← `allstreet.create_allstreet_root`
- `solve_allstreet_postflop` ← `allstreet.solve_allstreet_postflop`
- `dispatch_v4` ← `api_v4.dispatch_v4`

### 3.2 S2 Exports (N-Player Postflop)

Must remain **byte-for-byte identical** `is` references:

- `NPlayerPostflopConfig` ← `nplayer_postflop.NPlayerPostflopConfig`
- `DealN` ← `nplayer_postflop.DealN`
- `NPlayerPublicAction` ← `nplayer_postflop.NPlayerPublicAction`
- `NPlayerPostflopState` ← `nplayer_postflop.NPlayerPostflopState`
- `enumerate_deals` ← `nplayer_postflop.enumerate_deals`
- `create_nplayer_postflop_root` ← `nplayer_postflop.create_nplayer_postflop_root`
- `NPlayerPostflopSolveResult` ← `nplayer_postflop.NPlayerPostflopSolveResult`
- `solve_nplayer_postflop` ← `nplayer_postflop.solve_nplayer_postflop`

**Constraint:** S3 integration must NOT modify `__init__.py` import statements for S1/S2 symbols. Only additive S3 imports are permitted.

---

## 4. Existing v3 Capability Truth Preservation

**Source:** `tests/test_phase4_s3_exports.py` lines 190–214
**Current state:** `src/poker_solver/api_v3.py` `_FEATURES` lines 17–47

### 4.1 Legacy Features (Must Remain Unchanged)

Verified via live `dispatch_v3` call:

```json
{
  "preflop": {"status": "implemented-bounded", "continuation": "terminal-table-only"},
  "n-player-cfr": {"status": "implemented-bounded", "players": [2, 9], "deviation_certificate": "exhaustive-diagnostic-only"},
  "multiway-postflop": {"status": "implemented-bounded", "players": 3, "streets": "one-betting-round"}
}
```

### 4.2 S1 Feature (Must Remain Unchanged)

```json
{
  "allstreet-postflop": {
    "status": "implemented-bounded",
    "starting_street": "flop",
    "continuation": "automatic-natural-terminal",
    "interfaces": ["typed", "json-v4", "cli-phase4"]
  }
}
```

### 4.3 S2 Feature (Must Remain Unchanged)

```json
{
  "nplayer-postflop": {
    "status": "implemented-bounded",
    "players": [2, 9],
    "streets": "one-betting-round",
    "interfaces": ["typed", "json-v4", "cli-phase4"],
    "deviation": "exhaustive-diagnostic-only"
  }
}
```

**Constraint:** S3 integration must add `"nplayer-preflop"` key to `_FEATURES` dict without modifying any existing keys or values. The `deepcopy(_FEATURES)` return pattern (line 95) already ensures detachment; no change to that mechanism is permitted.

---

## 5. Integration Proof Obligations

### 5.1 Package Export Proof

The integration build (S3-I2 implementation agent) must:

1. Add nine import statements to `src/poker_solver/__init__.py`
2. Verify `tests/test_phase4_s3_exports.py::test_package_exports_*` (9 tests, lines 21–90) pass
3. Verify `tests/test_phase4_s3_exports.py::test_existing_s1_and_s2_package_exports_remain_identical` (line 152) passes

### 5.2 Capability Truth Proof

The integration build must:

1. Add `"nplayer-preflop": {...}` entry to `api_v3.py` `_FEATURES` dict
2. Verify `tests/test_phase4_s3_exports.py::test_capability_manifest_describes_bounded_nplayer_preflop_exactly` (line 93) passes
3. Verify `tests/test_phase4_s3_exports.py::test_nplayer_preflop_capability_response_is_deterministic_and_detached` (line 122) passes
4. Verify `tests/test_phase4_s3_exports.py::test_existing_v3_capabilities_remain_available` (line 190) passes

### 5.3 No Production/Test Edits

This analysis phase must NOT:

- Modify `src/poker_solver/__init__.py`
- Modify `src/poker_solver/api_v3.py`
- Modify `tests/test_phase4_s3_exports.py`
- Modify any S1/S2 production modules
- Commit any changes

All edits are deferred to the implementation agent (next iteration).

---

## 6. Architectural Alignment

**Source:** `ARCHITECTURE_PHASE4_S3.md` lines 1–30

The nine exports and capability object align with the frozen S3 architecture:

- **Additive contract:** S3 adds new symbols without modifying S1/S2 (architecture line 6)
- **Bounded scope:** `players: [2, 9]`, `street: "preflop-one-round"`, `continuations: "supplied-or-derived-bounded"` match architecture lines 5, 11 (finite reference path, no unrestricted range solving)
- **Deterministic:** `deviation: "exhaustive-diagnostic-only"` matches architecture line 13 (tiny synthetic ranges, exact chance arithmetic)
- **Public typed contracts:** Nine symbols match architecture lines 19–29 (exact public API surface)

---

## 7. Summary

**Nine S3 exports identified:**
6 classes + 3 functions from `nplayer_preflop.py` → `poker_solver` package root

**Exact capability object specified:**
6 fields, deterministic, deep-copy isolated, truth-aligned with implementation

**S1/S2 preservation verified:**
13 existing package exports + 3 existing v3 capability features must remain byte-for-byte identical

**Integration contract:**
Additive-only changes to `__init__.py` and `api_v3.py`; no S1/S2 modifications; all truth requirements enforced by permanent test suite.

**Next agent (implementation):** Apply exact changes, run test suite, verify GREEN, write heartbeat.
