# S3-I2 RED Authenticity & Coverage Plan

**Owner:** R3I2-5
**Scope:** Adversarial executable checklist for parent validation of S3-I2 RED suites
**Context:** S3-I1 accepted at commit `7285335`, four S3-I1 RED suites green (56 tests), production `nplayer_preflop.py` exists
**Deliverable:** Validation plan only — no test edits, no production edits, no commit

---

## 1. Mission

Provide the parent orchestrator with an **adversarial executable checklist** to distinguish authentic RED behavioral failures from:
- Import-only placeholders (tests that import but never exercise production)
- Caught-absence stubs (tests that pass because production raises `NotImplementedError` and the test catches it)
- False-positive traps (tests with inverted assertions, wrong expected values, or no assertions)
- Detached oracles (independent calculations that never compare against production output)

This plan enumerates **required behavioral coverage** for the four S3-I2 RED suites and suggests **focused validation commands** the parent can execute to confirm authenticity before accepting the implementation wave.

---

## 2. S3-I2 RED Suite Responsibilities (from ARCHITECTURE §12)

Four exclusive RED owners must create:

1. **`tests/test_nplayer_preflop_solve.py`** (R3I2-1)
   Typed solve facade, determinism, normalization, detachment, reach arithmetic, exhaustive deviation diagnostic

2. **`tests/test_api_v4_nplayer_preflop.py`** (R3I2-2)
   Strict v4 envelope, payload validation, serialization round-trip, error fail-closed, operation routing

3. **`tests/test_phase4_s3_examples.py`** (R3I2-3)
   Canonical 2/6/9-player JSON examples parse, solve via generic CLI, produce deterministic output

4. **`tests/test_phase4_s3_exports.py`** (R3I2-4)
   Package capability advertisement: `nplayer-preflop`, players `[2,9]`, interfaces, continuations, deviation claim

---

## 3. Required Behavioral Failures (Authentic RED Criteria)

### 3.1 `test_nplayer_preflop_solve.py` — Solve Facade

**Must fail because production does not yet expose:**
- `solve_nplayer_preflop(config, algorithm, iterations, ...)` function
- `NPlayerPreflopSolveResult` dataclass with fields: `strategy`, `expected_values`, `certificate`, `metadata`, `provenance`
- Strategy normalization: `sum(policy.values()) ≈ 1.0` for every infoset
- Determinism: identical config/iterations → identical strategy/values
- Detachment: mutating returned strategy does not affect subsequent calls
- N-player reach propagation: chance × all-opponent reach per player (analogous to S2 postflop)
- Exhaustive deviation diagnostic below `max_pure_strategies` cap, fail-closed above
- 2-player, 6-player, 9-player solve acceptance (tiny synthetic ranges)

**Authentic RED evidence:**
```bash
pytest tests/test_nplayer_preflop_solve.py -v
# Expected: ImportError or AttributeError on solve_nplayer_preflop
# OR: NameError on NPlayerPreflopSolveResult
# NOT: all tests pass (would indicate placeholder/stub)
```

**False-positive traps to check:**
- Test imports `solve_nplayer_preflop` but never calls it → parent must grep for actual invocation
- Test catches `NotImplementedError` and passes → parent must verify no blanket `except` without re-raise
- Test asserts `result is not None` but never checks normalization/determinism → parent must verify sum/equality checks exist
- Independent oracle computes values but never compares `assert oracle_values == result.expected_values` → parent must verify comparison line

**Focused parent validation:**
```bash
# 1. Confirm solve function is actually called
grep -n 'solve_nplayer_preflop(' tests/test_nplayer_preflop_solve.py | head -5

# 2. Confirm normalization check exists
grep -n 'sum.*policy.*approx.*1\.0' tests/test_nplayer_preflop_solve.py

# 3. Confirm determinism check exists
grep -n 'first.*==.*second' tests/test_nplayer_preflop_solve.py

# 4. Confirm 6-player and 9-player cases exist
grep -n 'num_players.*[69]' tests/test_nplayer_preflop_solve.py

# 5. Run and expect import/attribute failure
pytest tests/test_nplayer_preflop_solve.py::test_six_player_solve_returns_six_values -xvs 2>&1 | grep -E 'ImportError|AttributeError|NameError'
```

---

### 3.2 `test_api_v4_nplayer_preflop.py` — Strict v4 API

**Must fail because production does not yet:**
- Route `{"version": 4, "operation": "solve-nplayer-preflop", "payload": {...}}` in `api_v4.dispatch_v4()`
- Validate strict integer version `4` (reject bool, float, string "4")
- Validate payload fields: `version`, `num_players`, `button`, `starting_stacks`, `forced_posts`, `straddle_variant`, `ranges`, `sizing_rules`, `max_raises/deals/nodes`, `short_all_in_reopens`, `continuation`, `algorithm`, `iterations`, `seed`, `include_deviation_certificate`, `max_pure_strategies`
- Serialize `NPlayerPreflopPublicAction` history as `{"actor": int, "action": str, "amount": int}` in strategy keys
- Fail closed on: unknown operation, malformed arrays, bool-as-int, nonfinite values, duplicate continuation keys, unsupported algorithm/seed
- Return envelope: `{"version": 4, "operation": "solve-nplayer-preflop", "config_version": "nplayer-preflop-v1", "game_version": "nplayer-preflop-v1", "algorithm": ..., "iterations": ..., "strategy": {...}, "values": [...], "certificate": ..., "metadata": {...}, "provenance": ..., "approximate": false}`

**Authentic RED evidence:**
```bash
pytest tests/test_api_v4_nplayer_preflop.py -v
# Expected: KeyError on unknown operation, or dispatch returns error dict
# NOT: all tests pass
```

**False-positive traps:**
- Test constructs payload but never calls `dispatch_v4()` → parent must verify call exists
- Test asserts `"error" in result` but production returns `{"error": None}` and test passes → parent must verify error is truthy or specific
- Test checks `result["version"] == 4` but never checks `result["operation"]` or `result["values"]` → parent must verify substantive field checks
- Serialization test constructs history but never verifies JSON round-trip → parent must verify `json.dumps(result)` succeeds and re-parse matches

**Focused parent validation:**
```bash
# 1. Confirm dispatch_v4 is called with solve-nplayer-preflop
grep -n 'dispatch_v4.*solve-nplayer-preflop' tests/test_api_v4_nplayer_preflop.py | head -3

# 2. Confirm strict type rejection tests exist
grep -n 'version.*True\|version.*"4"' tests/test_api_v4_nplayer_preflop.py

# 3. Confirm response envelope checks exist
grep -n 'result\["values"\]' tests/test_api_v4_nplayer_preflop.py | head -3

# 4. Run and expect KeyError or operation-unknown error
pytest tests/test_api_v4_nplayer_preflop.py::test_valid_request_returns_envelope -xvs 2>&1 | grep -E 'KeyError|operation.*unknown|not.*implemented'
```

---

### 3.3 `test_phase4_s3_examples.py` — Canonical JSON Examples

**Must fail because:**
- `examples/phase4/nplayer_2p_preflop.json` does not exist yet
- `examples/phase4/nplayer_6p_preflop.json` does not exist yet
- `examples/phase4/nplayer_9p_preflop.json` does not exist yet
- Generic CLI `python -m poker_solver.cli phase4 FILE --json` does not route `solve-nplayer-preflop` operation

**Authentic RED evidence:**
```bash
pytest tests/test_phase4_s3_examples.py -v
# Expected: FileNotFoundError on missing examples, or operation routing failure
# NOT: all tests pass
```

**False-positive traps:**
- Test uses `pytest.importorskip` or `@pytest.mark.skip` → parent must verify no skip decorators
- Test checks `Path(example).exists()` and passes if missing → parent must verify test actually parses and solves
- Test loads JSON but never invokes CLI or `dispatch_v4()` → parent must verify execution
- Test asserts `result is not None` but never checks determinism or value count → parent must verify substantive checks

**Focused parent validation:**
```bash
# 1. Confirm examples are referenced
grep -n 'nplayer_[269]p_preflop\.json' tests/test_phase4_s3_examples.py

# 2. Confirm CLI invocation or dispatch exists
grep -n 'cli.*phase4\|dispatch_v4' tests/test_phase4_s3_examples.py

# 3. Confirm determinism check exists
grep -n 'first.*==.*second' tests/test_phase4_s3_examples.py

# 4. Verify examples do not exist yet
ls examples/phase4/nplayer_*p_preflop.json 2>&1
# Expected: No such file or directory

# 5. Run and expect FileNotFoundError
pytest tests/test_phase4_s3_examples.py::test_nplayer_2p_example_deterministic -xvs 2>&1 | grep -E 'FileNotFoundError|No such file'
```

---

### 3.4 `test_phase4_s3_exports.py` — Package Capability Truth

**Must fail because:**
- `poker_solver.__init__` or `api_v3.get_capabilities()` does not yet advertise:
  - `"nplayer-preflop"` game type
  - `"players": [2, 9]` range
  - `"street": "preflop-one-round"`
  - `"interfaces": ["typed", "json-v4", "cli-phase4"]`
  - `"continuations": "supplied-or-derived-bounded"`
  - `"deviation": "exhaustive-diagnostic-only"`

**Authentic RED evidence:**
```bash
pytest tests/test_phase4_s3_exports.py -v
# Expected: KeyError or assertion failure on missing capability
# NOT: all tests pass
```

**False-positive traps:**
- Test imports `get_capabilities()` but never calls it → parent must verify call exists
- Test asserts `"nplayer-preflop" in caps` but `caps` is an empty dict and test passes → parent must verify caps is populated
- Test checks one field but ignores others → parent must verify all six fields above are checked

**Focused parent validation:**
```bash
# 1. Confirm get_capabilities is called
grep -n 'get_capabilities()' tests/test_phase4_s3_exports.py

# 2. Confirm nplayer-preflop is checked
grep -n 'nplayer-preflop' tests/test_phase4_s3_exports.py

# 3. Confirm player range [2,9] is checked
grep -n 'players.*2.*9' tests/test_phase4_s3_exports.py

# 4. Run and expect KeyError or assertion failure
pytest tests/test_phase4_s3_exports.py::test_nplayer_preflop_capability_advertised -xvs 2>&1 | grep -E 'KeyError|AssertionError|not.*found'
```

---

## 4. Cross-Suite Invariants (Parent Must Verify)

### 4.1 Zero-Sum Terminal Utilities
Every solve result must satisfy `sum(expected_values) ≈ 0.0` within `1e-9`.

**Check:**
```bash
grep -rn 'sum.*expected_values.*approx.*0' tests/test_nplayer_preflop_solve.py tests/test_api_v4_nplayer_preflop.py
```

### 4.2 Policy Normalization
Every infoset policy must satisfy `sum(policy.values()) ≈ 1.0` within `1e-12`.

**Check:**
```bash
grep -rn 'sum.*policy.*approx.*1' tests/test_nplayer_preflop_solve.py tests/test_api_v4_nplayer_preflop.py
```

### 4.3 Determinism
Identical config + iterations → identical strategy + values.

**Check:**
```bash
grep -rn 'first.*==.*second\|result.*==.*expected' tests/test_nplayer_preflop_solve.py tests/test_api_v4_nplayer_preflop.py tests/test_phase4_s3_examples.py
```

### 4.4 Detachment
Mutating returned strategy/values does not affect subsequent calls.

**Check:**
```bash
grep -rn 'strategy.*clear\|values.*append' tests/test_nplayer_preflop_solve.py tests/test_api_v4_nplayer_preflop.py
```

### 4.5 2/6/9 Player Coverage
At least one test per suite exercises N=2, N=6, N=9.

**Check:**
```bash
for suite in solve api_v4 examples; do
  echo "=== test_*_$suite.py =="
  grep -n 'num_players.*[269]\|_[269]p_' tests/test_*${suite}*.py | head -5
done
```

### 4.6 Independent Six-Player Pure-Deviation Oracle
`test_nplayer_preflop_solve.py` must contain a six-player fixture with an independent pure-strategy enumerator that matches production's exhaustive certificate below cap.

**Check:**
```bash
grep -n 'pure.*deviation\|enumerate.*pure\|six.*player.*oracle' tests/test_nplayer_preflop_solve.py
```

---

## 5. Unchanged Generic CLI Contract

The existing generic Phase 4 CLI `python -m poker_solver.cli phase4 FILE|- --json` must:
- Accept `solve-nplayer-preflop` operation without new parser shape
- Forward v4 envelope to `dispatch_v4()`
- Return JSON response to stdout
- Preserve existing `solve-allstreet-postflop` and `solve-nplayer-postflop` behavior

**Parent validation:**
```bash
# 1. Verify cli.py is not modified (or only routing table extended)
git diff 7285335..HEAD -- src/poker_solver/cli.py | grep -E '^\+.*def |^\+.*if.*operation' | head -10

# 2. Verify existing S1/S2 CLI tests remain green
pytest tests/test_phase4_s1_cli.py tests/test_cli.py -v --tb=no -q

# 3. Verify generic phase4 stdin/file/error behavior unchanged
pytest tests/test_api_v4.py -k 'cli' -v --tb=no -q
```

---

## 6. Fail-Closed Type/API/Serialization Cases

Each RED suite must include **at least 3 strict rejection tests**:

### 6.1 Solve Suite
- `num_players` as bool/float/out-of-range → `ValueError`
- `algorithm` as unsupported string → `ValueError`
- `max_pure_strategies` as negative → `ValueError`

### 6.2 API Suite
- `version` as bool `True` or string `"4"` → error response
- `num_players` as float `6.0` → error response
- `forced_posts` with duplicate seat → error response
- `continuation` with non-zero-sum payoff → error response
- Unknown `operation` → error response

### 6.3 Examples Suite
- Malformed JSON → parse error or validation failure
- Missing required field → validation failure
- Invalid straddle variant → validation failure

### 6.4 Exports Suite
- Capability query before implementation → missing key or empty list

**Parent validation:**
```bash
for suite in solve api_v4 examples exports; do
  echo "=== Rejection tests in test_*${suite}*.py =="
  grep -n 'pytest.raises\|with.*raises\|assert.*error\|ValueError\|TypeError' tests/test_*${suite}*.py | wc -l
done
# Expected: at least 3 per suite
```

---

## 7. Suggested Focused Parent Commands

### 7.1 Pre-Implementation RED Verification (Before R3I2-5 Starts)
```bash
cd /home/genomix-node/poker-solver

# 1. Confirm all four RED suites exist and import production
for suite in solve api_v4_nplayer_preflop phase4_s3_examples phase4_s3_exports; do
  echo "=== tests/test_nplayer_preflop_${suite}.py =="
  head -20 tests/test_nplayer_preflop_${suite}.py 2>/dev/null || echo "MISSING"
done

# 2. Run all four suites and expect failures
pytest tests/test_nplayer_preflop_solve.py tests/test_api_v4_nplayer_preflop.py tests/test_phase4_s3_examples.py tests/test_phase4_s3_exports.py -v --tb=short 2>&1 | tee /tmp/s3i2-red-pre.log

# 3. Verify failures are authentic (not all skipped/passed)
grep -E 'FAILED|ERROR' /tmp/s3i2-red-pre.log | wc -l
# Expected: >0

grep -E 'ImportError|AttributeError|NameError|FileNotFoundError|KeyError' /tmp/s3i2-red-pre.log | head -10

# 4. Verify no placeholder passes
grep -E 'PASSED' /tmp/s3i2-red-pre.log
# Expected: 0 or only unrelated legacy tests
```

### 7.2 Post-Implementation GREEN Verification (After R3I2-5 Completes)
```bash
cd /home/genomix-node/poker-solver

# 1. Run all four S3-I2 RED suites
pytest tests/test_nplayer_preflop_solve.py tests/test_api_v4_nplayer_preflop.py tests/test_phase4_s3_examples.py tests/test_phase4_s3_exports.py -v --tb=short 2>&1 | tee /tmp/s3i2-red-post.log

# 2. Verify all tests pass
grep -E 'passed' /tmp/s3i2-red-post.log | tail -1
# Expected: X passed in Y.YYs

# 3. Verify no skips/xfails
grep -E 'skipped|xfail' /tmp/s3i2-red-post.log
# Expected: empty

# 4. Verify 2/6/9 player coverage
grep -rn 'num_players.*(2|6|9)' tests/test_nplayer_preflop_solve.py tests/test_api_v4_nplayer_preflop.py tests/test_phase4_s3_examples.py | wc -l
# Expected: >=6 (at least 2 per player count)

# 5. Verify examples exist
ls -lh examples/phase4/nplayer_{2,6,9}p_preflop.json

# 6. Verify generic CLI unchanged
git diff 7285335..HEAD -- src/poker_solver/cli.py | grep -E '^\+.*def ' | wc -l
# Expected: 0 (no new top-level functions)

# 7. Verify full regression green
pytest tests/ -x --tb=no -q 2>&1 | tail -5
# Expected: XXX passed in Y.YYs
```

### 7.3 Authenticity Spot-Checks
```bash
# 1. Solve determinism
pytest tests/test_nplayer_preflop_solve.py -k deterministic -xvs 2>&1 | grep -A5 'assert first'

# 2. Policy normalization
pytest tests/test_nplayer_preflop_solve.py -k normalized -xvs 2>&1 | grep -A3 'sum.*policy'

# 3. Six-player pure-deviation oracle
pytest tests/test_nplayer_preflop_solve.py -k 'six.*deviation' -xvs 2>&1 | grep -A10 'independent'

# 4. API strict type rejection
pytest tests/test_api_v4_nplayer_preflop.py -k 'bool\|float\|string' -xvs 2>&1 | grep -A3 'error'

# 5. Examples deterministic
pytest tests/test_phase4_s3_examples.py -k deterministic -xvs 2>&1 | grep -A3 'first.*==.*second'

# 6. Exports capability truth
pytest tests/test_phase4_s3_exports.py -k capability -xvs 2>&1 | grep -A5 'nplayer-preflop'
```

---

## 8. Acceptance Criteria Summary

**S3-I2 RED suites are AUTHENTIC if and only if:**

1. ✅ All four suites exist and directly import production modules (no `importorskip`)
2. ✅ Pre-implementation: all suites FAIL with `ImportError`/`AttributeError`/`FileNotFoundError`/`KeyError`
3. ✅ Post-implementation: all suites PASS with no skips/xfails
4. ✅ Each suite exercises N=2, N=6, N=9 (at least one test per N)
5. ✅ Solve suite: determinism, normalization, detachment, six-player pure-deviation oracle
6. ✅ API suite: strict v4 envelope, type rejection, serialization round-trip, fail-closed
7. ✅ Examples suite: 2/6/9p JSON files exist, parse, solve via generic CLI, deterministic
8. ✅ Exports suite: `nplayer-preflop` capability with players `[2,9]`, interfaces, continuations, deviation
9. ✅ Generic CLI unchanged (no new parser shape, existing S1/S2 tests green)
10. ✅ Full regression green (all S1/S2/S3-I1 tests pass)
11. ✅ Zero-sum, normalization, determinism, detachment checks present in code (grep-verified)
12. ✅ At least 3 strict rejection tests per suite (type/API/serialization fail-closed)

---

## 8.1 Parent adjudication

The checklist is advisory; the architecture and executable behavior remain authoritative. Parent validation narrows four statements above:

- authentic RED must be behavioral and need not be a collection-time `ImportError`; importing the existing production module and failing when the missing public facade is invoked is preferred;
- already-implemented shared envelope/CLI error characterization may pass before S3-I2, provided every claimed S3 path has specific failing evidence (the repaired API suite currently has 29 genuine failures and one shared-envelope pass);
- 2/6/9 coverage belongs across the solve/API/example acceptance matrix, not literally in every rejection/export suite;
- capability truth is queried through `dispatch_v3({"version": 3, "operation": "capabilities", "payload": {}})`, not a nonexistent `get_capabilities()` helper.

Implementation ownership remains gated until the parent authenticates all four final RED suites; planner role names do not identify implementation owners.

---

## 9. Heartbeat

**Task:** S3-I2 RED planner 5 — adversarial authenticity and coverage plan
**Status:** COMPLETE_PLAN
**UTC:** 2026-09-16T08:14:52Z (parent-normalized from the canonical write receipt)
**Deliverable:** `/home/genomix-node/poker-solver/research/phase4/s3-i2-red/05-red-authenticity-plan.md`
**Next:** Parent authenticates the four recovered RED suites, then gates exclusive core and integration GREEN owners.

---

## 10. References

- `PHASE4_MISSION.md` §3 (adversarial cross-check mandate)
- `ARCHITECTURE_PHASE4_S3.md` §10-13 (S3-I2 contracts, TDD batches, acceptance matrix)
- Accepted S3-I1 commit `7285335` (56 green S3-I1 RED tests)
- Analogous S2 postflop: `tests/test_nplayer_postflop_solve.py`, `tests/test_api_v4_nplayer.py`
- Generic CLI: `src/poker_solver/cli.py` phase4 operation forwarding
- Package exports: `src/poker_solver/api_v3.py` `get_capabilities()`
