# A3I1-6R Release/TDD/Evidence Audit — BLOCKED

**Auditor:** A3I1-6R (retry-once recovery for A3I1-6)
**Candidate:** S3-I1 frozen at `research/phase4/s3-i1-audit/CANDIDATE_MANIFEST.md`
**Architecture:** `ARCHITECTURE_PHASE4_S3.md` hash `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`
**Baseline:** `phase3-398-green` at `feba8222a0b614b0c64eca59402403ce733195ea`
**Started:** 2026-09-16T05:35:00Z (approx)
**Completed:** 2026-09-16T05:40:00Z (approx)

---

## Disposition: BLOCKED

Parent-verified coverage gap confirmed through independent adversarial review. Frozen permanent test suites omit architecture-mandatory fixtures.

---

## Hash Verification

### Candidate files (all match manifest exactly)

```text
0e55fbce5f6934c8e2e63ee28ce9d01d9268792165d9318bc8c9ed03b5f73422  src/poker_solver/nplayer_preflop.py
5a214b900a7ad1b61aa67cd294d7000e3eef0023f82bb834d1e94035f815a867  tests/test_nplayer_preflop_config.py
d61a86d39f864d494f19a91698478c4af39b76d6ad0372321f18d69706349f69  tests/test_nplayer_preflop_betting.py
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
282112f2b88e57b1b8b25bbdd69d0f6fb90df714e92ccff80945f9724375e69d  tests/test_nplayer_preflop_information.py
```

### Architecture and baseline

```bash
$ sha256sum ARCHITECTURE_PHASE4_S3.md
a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6  ARCHITECTURE_PHASE4_S3.md

$ git rev-parse phase3-398-green
feba8222a0b614b0c64eca59402403ce733195ea

$ git diff --check
(clean, exit 0)
```

---

## Test Execution

### Focused S3-I1 tests

```bash
$ uv run pytest -q tests/test_nplayer_preflop_*.py
26 passed in 0.18s
```

### Legacy regression (selected suites)

```bash
$ uv run pytest tests/test_preflop.py tests/test_nplayer.py tests/test_nplayer_postflop_*.py -q
94 passed in 2.00s

$ uv run pytest tests/test_allstreet_*.py -q
70 passed in 10.37s

$ uv run pytest tests/test_api.py tests/test_api_v3.py tests/test_api_v4.py tests/test_api_v4_nplayer.py -q
95 passed in 8.08s
```

### Full legacy suite (excluding nplayer_preflop)

```bash
$ uv run pytest tests/ -k 'not (nplayer_preflop or slow)' -q --tb=no
649 passed, 30 deselected in 146.92s (0:02:26)
```

---

## RED Authenticity Verification

### Direct production imports (all four suites)

```bash
$ grep -n 'from poker_solver.nplayer_preflop import' tests/test_nplayer_preflop_*.py
tests/test_nplayer_preflop_config.py:12:from poker_solver.nplayer_preflop import (
tests/test_nplayer_preflop_betting.py:18:from poker_solver.nplayer_preflop import (
tests/test_nplayer_preflop_settlement.py:18:from poker_solver.nplayer_preflop import (
tests/test_nplayer_preflop_information.py:11:from poker_solver.nplayer_preflop import (
```

### No escape hatches

```bash
$ grep -E '(pytest\.skip|pytest\.xfail|@pytest\.mark\.skip|@pytest\.mark\.xfail|importorskip)' tests/test_nplayer_preflop_*.py
tests/test_nplayer_preflop_settlement.py:Direct module-scope production imports only; no catch/importorskip/skip/xfail/fakes/placeholders.
```

(Single match is a comment, not actual usage.)

---

## Coverage Gap Analysis

### Parent blocker claim

C3I1-2 reported: "frozen permanent suites omit architecture-required double/Mississippi positive fixtures, exact limp/SB-completion caller-key coverage, and a completed 3/4/5-bet sizing trace (ARCHITECTURE lines 158, 265-266, 287-290)."

### Independent verification

#### 1. Double and Mississippi straddle fixtures

**Architecture requirements:**
- §5 lines 149–157: Four straddle variants (none, standard, double, Mississippi) with distinct ledgers, first actors, and trees
- §13 line 289: "no/standard/double/Mississippi straddles produce distinct verified ledgers, first actionable actors, and trees"

**Betting suite coverage:**

```bash
$ grep -E '(double|mississippi)' tests/test_nplayer_preflop_betting.py
(zero matches)

$ uv run pytest tests/test_nplayer_preflop_betting.py -v --tb=short 2>&1 | grep -E '^tests/'
tests/test_nplayer_preflop_betting.py::TestInitialActionOrder::test_hu_initial_pending PASSED
tests/test_nplayer_preflop_betting.py::TestInitialActionOrder::test_6p_no_straddle_first_actor_utg PASSED
tests/test_nplayer_preflop_betting.py::TestInitialActionOrder::test_9p_no_straddle_first_actor_utg PASSED
tests/test_nplayer_preflop_betting.py::TestStraddleBoundary::test_6p_standard_straddle_first_actor_after_utg PASSED
tests/test_nplayer_preflop_betting.py::TestExactSizingCaller::test_cold_callers_after_raise PASSED
tests/test_nplayer_preflop_betting.py::TestFullRaiseReopening::test_full_raise_restores_entitlement PASSED
tests/test_nplayer_preflop_betting.py::TestMandatoryShortAllInTrace::test_short_all_in_no_reopen PASSED
tests/test_nplayer_preflop_betting.py::TestMandatoryShortAllInTrace::test_short_all_in_with_reopen PASSED
```

**Config suite coverage:**

```bash
$ grep -n -E '(double|mississippi)' tests/test_nplayer_preflop_config.py
109:def test_standard_straddle_boundary_and_hu_mississippi_rejection() -> None:
128:    with pytest.raises(ValueError, match="mississippi|straddle"):
136:            straddle_variant="mississippi",
```

Config suite has:
- Standard straddle boundary test (lines 110–126)
- HU Mississippi rejection test (lines 128–137)

**Gap confirmed:**
- Betting suite: only standard straddle; zero double/Mississippi
- Config suite: standard boundary + HU Mississippi rejection (negative test)
- **Missing:** positive double straddle fixture (N≥4, two ordered straddles)
- **Missing:** positive Mississippi straddle fixture (N≥3, caller-selected non-blind straddler)

#### 2. Limp and SB-completion caller-key coverage

**Architecture requirements:**
- §7 line 184: "every pre-raise CALL, including a small-blind completion, counts for an opening/isolation decision"
- §15 line 323: "a small-blind completion counts as a pre-raise CALL for `cold_callers`"
- §13 line 290: "limps, SB completes, cold calls, 3/4/5-bet+ rules, IP/OOP-aggressor relation, and per-cold-caller keys select exactly the declared sizes"

**Betting suite coverage:**

```bash
$ grep -n -E '(limp|complete|cold_caller)' tests/test_nplayer_preflop_betting.py | head -15
157:    """Exact sizing-key selection with cold_callers."""
159:    def test_cold_callers_after_raise(self):
160:        """After CO raises, BTN calls, SB has cold_callers=1."""
176:                    cold_callers=0,
183:                    cold_callers=1,
200:        # SB should have raise to 20 with cold_callers=1
```

Betting suite has:
- `test_cold_callers_after_raise`: CO raises, BTN calls, SB sees `cold_callers=1`

**Gap confirmed:**
- **Missing:** explicit limp fixture (CHECK action in unopened pot)
- **Missing:** explicit SB-completion fixture (SB completes to BB, counted as pre-raise caller)

#### 3. 3/4/5-bet sizing trace

**Architecture requirements:**
- §2.2 line 38: "`raise_count: int`: raises already made before this decision (`0` means open/limp pot, `1` means a 3-bet decision, and so on)"
- §13 line 290: "limps, SB completes, cold calls, 3/4/5-bet+ rules, IP/OOP-aggressor relation, and per-cold-caller keys select exactly the declared sizes"

**Betting suite coverage:**

```bash
$ grep -n -E '(def test_.*3bet|def test_.*4bet|def test_.*5bet)' tests/test_nplayer_preflop_betting.py
(zero matches)

$ uv run pytest tests/test_nplayer_preflop_betting.py -v --tb=short 2>&1 | grep -E '^tests/' | wc -l
8
```

Betting suite has 8 tests total; none explicitly named for 3/4/5-bet traces.

**Gap confirmed:**
- **Missing:** explicit 3-bet trace (raise_count=1)
- **Missing:** explicit 4-bet trace (raise_count=2)
- **Missing:** explicit 5-bet trace (raise_count=3)

---

## Blocker Summary

Frozen permanent test suites lack architecture-mandatory coverage:

1. **Double straddle positive fixture** (§5, §13 line 289)
2. **Mississippi straddle positive fixture** (§5, §13 line 289)
3. **Limp fixture** (§7 line 184, §13 line 290)
4. **SB-completion fixture** (§7 line 184, §15 line 323, §13 line 290)
5. **3/4/5-bet sizing trace** (§2.2 line 38, §13 line 290)

Candidate code quality, existing test correctness, hash integrity, baseline preservation, and legacy regression are not disputed. The blocker is incomplete architecture coverage in the frozen test suites themselves.

---

## Recommendation

**BLOCKED**: S3-I1 release cannot proceed until frozen permanent test suites are extended to cover architecture-mandatory fixtures. Parent should coordinate test-suite amendment or reject candidate.

---

**Heartbeat:** `.hb/A3I1-6R`
**Report:** `research/phase4/s3-i1-audit/06-release-tdd.md`
**Auditor:** A3I1-6R
**Completed:** 2026-09-16T05:40:00Z (approx)
