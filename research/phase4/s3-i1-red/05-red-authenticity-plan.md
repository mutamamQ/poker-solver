# S3-I1 RED Authenticity Checklist

## Purpose

This checklist provides strict, adversarial verification criteria for accepting the four RED test suites in S3-I1 (bounded N-player preflop). Each suite must demonstrate genuine production-importing behavioral contracts that fail due to absent production implementation, not test infrastructure errors.

## Architecture Context

- **Design commit**: `65d411793d1d7767d86500d0adffe9f40b379108`
- **Architecture hash**: `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`
- **Architecture file**: `ARCHITECTURE_PHASE4_S3.md` (325 lines)
- **Production module**: `src/poker_solver/nplayer_preflop.py` (MUST NOT EXIST)
- **Four RED suites**:
  1. `tests/test_nplayer_preflop_config.py`
  2. `tests/test_nplayer_preflop_betting.py`
  3. `tests/test_nplayer_preflop_settlement.py`
  4. `tests/test_nplayer_preflop_information.py`

## Mandatory Checklist (All Items MUST Pass)

### 1. Direct Production Import

- [ ] Each test file contains `from poker_solver.nplayer_preflop import ...` with at least one production symbol
- [ ] Imported symbols match architecture §2.1 public contract:
  - `NPlayerPreflopConfig`
  - `NPlayerPreflopContinuation`
  - `NPlayerPreflopSizingRule`
  - `NPlayerPreflopPublicAction`
  - `NPlayerPreflopState`
  - `NPlayerPreflopSolveResult`
  - `enumerate_nplayer_preflop_deals`
  - `create_nplayer_preflop_root`
  - `solve_nplayer_preflop`
- [ ] No conditional imports (no `try/except ImportError`)
- [ ] No `pytest.importorskip("poker_solver.nplayer_preflop")`

### 2. No Test Infrastructure Escape Hatches

- [ ] Zero occurrences of `pytest.skip`
- [ ] Zero occurrences of `pytest.xfail`
- [ ] Zero occurrences of `@pytest.mark.skip`
- [ ] Zero occurrences of `@pytest.mark.xfail`
- [ ] Zero placeholder/stub test bodies (no `pass`, no `...` as sole statement)
- [ ] No `importorskip` anywhere in test files

### 3. Behavioral Assertions Spanning Architecture Scope

#### Suite 1: `test_nplayer_preflop_config.py`

- [ ] Config validation: version string, num_players [2,9], bool-as-int rejection
- [ ] Forced posts: SB/BB/antes/straddles, exact transfer, all-in posts
- [ ] Straddle variants: none/standard/double/mississippi (§5)
- [ ] Deterministic bounded deals with exact Fraction mass (§6)
- [ ] Blocker filtering and max_deals fail-closed
- [ ] Canonical positions for N=2,3,4,5,6,7,8,9 (§4)

#### Suite 2: `test_nplayer_preflop_betting.py`

- [ ] HU/6/9 action order, pending queue, clockwise traversal (§4)
- [ ] Limps, SB complete, cold_callers counting (§7)
- [ ] Sizing-key selection: position/raise_count/cold_callers/relation (§2.2)
- [ ] Raise targets: full/short all-in, last_raise_increment (§7)
- [ ] 3-bet/4-bet/5-bet+ branches, max_raises bound
- [ ] short_all_in_reopens: true/false, pending/entitlement intersection (§7)
- [ ] Action closure: one live seat or no pending responders

#### Suite 3: `test_nplayer_preflop_settlement.py`

- [ ] Fold-out: exact side-pot layers, eligible winners (§8)
- [ ] Refund uncalled excess: bounded by street_committed (§8)
- [ ] Terminal-table continuation: exact zero-sum N-tuples (§2.3, §8)
- [ ] Showdown-ranks continuation: derived side-pots, odd_chip_order (§2.3, §8)
- [ ] Independent ledger oracles (no production settlement helper imports)
- [ ] All terminal utilities sum exactly to Fraction(0)

#### Suite 4: `test_nplayer_preflop_information.py`

- [ ] Information key includes only §9 permitted fields
- [ ] Information key excludes opponent cards, deal index, hidden payoffs/ranks
- [ ] Opponent-card noninterference: varying opponent combos preserves key when owner/public fixed
- [ ] Hidden-continuation noninterference: varying payoff/rank values preserves key
- [ ] N=2 projected equivalence: deals/actions/ledgers/terminals/infosets match Phase-3 HU (§1, §13)

### 4. Isolated Failing Command

- [ ] `uv run pytest tests/test_nplayer_preflop_config.py -v` exits nonzero
- [ ] `uv run pytest tests/test_nplayer_preflop_betting.py -v` exits nonzero
- [ ] `uv run pytest tests/test_nplayer_preflop_settlement.py -v` exits nonzero
- [ ] `uv run pytest tests/test_nplayer_preflop_information.py -v` exits nonzero
- [ ] Each failure is attributable to `ModuleNotFoundError` or `ImportError` for `poker_solver.nplayer_preflop`
- [ ] No failures from syntax errors, fixture errors, or unrelated imports

### 5. Production Path Absence

- [ ] `src/poker_solver/nplayer_preflop.py` does NOT exist
- [ ] No `nplayer_preflop` module in `src/poker_solver/__init__.py` exports
- [ ] `git ls-files src/poker_solver/nplayer_preflop.py` returns empty

### 6. Ownership Disjointness

- [ ] Test files do NOT modify:
  - `src/poker_solver/preflop.py` (legacy HU)
  - `src/poker_solver/nplayer_postflop.py` (S2)
  - `src/poker_solver/allstreet.py` (S1)
  - `src/poker_solver/api_v4.py`
  - `src/poker_solver/api_v3.py`
  - `STATE.txt`, `PROGRESS.md`, `.git/`
- [ ] Each suite is self-contained in its single test file
- [ ] No cross-suite imports or shared test fixtures outside pytest/stdlib

### 7. Hash Binding

- [ ] Architecture file `ARCHITECTURE_PHASE4_S3.md` exists at design commit
- [ ] `sha256sum ARCHITECTURE_PHASE4_S3.md` matches `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`
- [ ] Design commit `65d411793d1d7767d86500d0adffe9f40b379108` is reachable in git history
- [ ] No uncommitted changes to architecture file

### 8. No False Positives from Infrastructure

- [ ] All four test files parse without SyntaxError: `python3 -m py_compile tests/test_nplayer_preflop_*.py`
- [ ] Pre-production pytest collection fails with exit 2 due to missing module: `uv run pytest --collect-only tests/test_nplayer_preflop_*.py` exits 2 with `ModuleNotFoundError: No module named 'poker_solver.nplayer_preflop'`
- [ ] Isolated runs fail exclusively with `ModuleNotFoundError: No module named 'poker_solver.nplayer_preflop'` (not collection/syntax/fixture errors)
- [ ] After production implementation, collection succeeds: `uv run pytest --collect-only tests/test_nplayer_preflop_*.py` exits 0 and the collected count exactly matches the tests found by the parent AST scan
- [ ] Existing production tests remain green: `uv run pytest tests/test_nplayer_postflop_config.py tests/test_nplayer_postflop_betting.py -v` exits 0
- [ ] No pytest version/plugin incompatibilities

### 9. Permanent Test Quality (Adversarial)

- [ ] Each suite contains the distinct substantive tests needed for its required behavior map; no arbitrary minimum count substitutes for coverage
- [ ] Test names are descriptive and map to architecture sections
- [ ] Assertions use exact equality (`==`, `assert x in y`) not approximate/fuzzy checks
- [ ] No `# TODO`, `# FIXME`, `# PLACEHOLDER` comments in test bodies
- [ ] Docstrings reference architecture sections (e.g., "§2.2", "§7")

### 10. RED Receipt Evidence

- [ ] Each suite owner provides:
  - Isolated pytest output showing `ModuleNotFoundError: No module named 'poker_solver.nplayer_preflop'`
  - Line count and assertion count per suite
  - Explicit architecture section coverage map
- [ ] Parent verifier independently reproduces nonzero exit on all four suites
- [ ] Parent verifier confirms production module absence

## Verdict Criteria

### PASS

All 10 checklist sections (50+ individual items) verified. Four RED suites are:

- Authentic production-importing behavioral contracts
- Failing exclusively due to absent `nplayer_preflop.py`
- Spanning full S3 architecture scope (config/betting/settlement/information)
- Free of escape hatches, placeholders, and infrastructure errors
- Disjoint from in-progress owner paths and legacy production

**Action**: Accept RED receipts. Gate S3-I1 core implementation owner.

### BLOCKED

Any checklist item fails. Common blocking patterns:

- **Import escape**: `importorskip`, `try/except ImportError`, conditional imports
- **Test escape**: `@pytest.mark.skip`, `pytest.xfail`, placeholder bodies
- **Scope gaps**: Missing N=2/6/9 coverage, missing straddle variants, missing continuation kinds
- **False positive**: Syntax errors, fixture errors, unrelated import failures
- **Ownership violation**: Edits to `STATE.txt`, `api_v4.py`, legacy production, or git state
- **Production leak**: `nplayer_preflop.py` exists, partial stubs, commented-out implementation

**Action**: Reject RED receipts. Return to suite owners with specific gap evidence. Do not gate core owner.

## Verification Procedure

1. **Clone/checkout**: Verify working tree at design commit `65d41179`
2. **Hash check**: `sha256sum ARCHITECTURE_PHASE4_S3.md`
3. **Absence check**: `ls src/poker_solver/nplayer_preflop.py` (must fail)
4. **Syntax check**: `python3 -m py_compile tests/test_nplayer_preflop_*.py`
5. **Pre-production collection check**: `uv run pytest --collect-only tests/test_nplayer_preflop_*.py` (must exit 2 with `ModuleNotFoundError`)
6. **Isolated run**: `uv run pytest tests/test_nplayer_preflop_config.py -v` (repeat for all 4, each must exit 2 with `ModuleNotFoundError`)
7. **Import inspection**: `grep -n 'from poker_solver.nplayer_preflop import' tests/test_nplayer_preflop_*.py`
8. **Escape-hatch scan**: `grep -n 'skip\|xfail\|importorskip' tests/test_nplayer_preflop_*.py` (must be empty)
9. **Scope audit**: Manual review of test function names and assertions against architecture §2-9, §13
10. **Regression check**: `uv run pytest tests/test_nplayer_postflop_config.py tests/test_nplayer_postflop_betting.py -v` (must pass)
11. **Post-production collection check**: After implementing `nplayer_preflop.py`, `uv run pytest --collect-only tests/test_nplayer_preflop_*.py` must exit 0 and its count must equal the parent AST count

## Notes

- This checklist is **adversarial by design**: it assumes suite owners may inadvertently (or deliberately) submit false-positive RED tests that pass without real production.
- **No partial credit**: A suite with 90% coverage but one `pytest.skip` is BLOCKED.
- **Independence**: Checklist derivation used only committed architecture and existing S2 postflop test patterns. No communication with suite owners or core implementer.
- **Immutability**: Once accepted, RED suites are frozen. Post-acceptance edits require a new RED wave.

---

**Checklist version**: 1.0
**Author role**: R3I1-5 (independent RED authenticity adversary)
**Date**: 2026-09-16
**Bound to**: S3-I1 exact-six RED wave, design commit `65d41179`, architecture hash `a4dd4f9...`
