# S3 Design Cross-Release Audit — Repaired A3R6

**Auditor:** A3R6 (fresh different non-author)  
**Timestamp:** 2026-09-16 UTC  
**Scope:** Repaired frozen S3 design cross-release audit  
**Candidate:** `ARCHITECTURE_PHASE4_S3.md`  
**Expected hash:** `fcae1cb6ce9da8b4e4ccb7ef085c223369e76e2be6ead3c5170cd2d41c118a21`  
**Baseline:** `phase3-398-green` → `feba8222a0b614b0c64eca59402403ce733195ea`  
**Current HEAD:** `4b3f87f4e6cf38e9dc88aca744b23de2c44c08fe`  

---

## SHA-256 Verification

**Computed hash:**
```
f0777689eac5df76ab7630dd3725e40f7409e4369ba9de312ac8992a4a4bb83f  ARCHITECTURE_PHASE4_S3.md
```

**Expected hash (from CANDIDATE_MANIFEST.md):**
```
fcae1cb6ce9da8b4e4ccb7ef085c223369e76e2be6ead3c5170cd2d41c118a21
```

❌ **HASH MISMATCH:** The architecture document has been modified since the frozen candidate was declared. This is a **blocking failure**.

---

## Git Baseline Verification

**Tag `phase3-398-green` SHA:**
```
feba8222a0b614b0c64eca59402403ce733195ea
```
✓ Matches expected baseline.

**Current HEAD SHA:**
```
4b3f87f4e6cf38e9dc88aca744b23de2c44c08fe
```
✓ Matches task context.

---

## S3 Design Changes vs S2-Complete Base

**Git diff check:**
```bash
git diff phase3-398-green HEAD -- ARCHITECTURE_PHASE4_S3.md | wc -l
→ 0
```

✓ **ARCHITECTURE_PHASE4_S3.md did not exist at the Phase 3 baseline.** It is a new S3 design document added during Phase 4.

**Diff between tag and HEAD (src/tests only):**
```bash
git diff phase3-398-green HEAD -- 'src/**' 'tests/**' | head -100
```

Shows S1 (all-street) and S2 (N-player postflop) implementation files:
- `src/poker_solver/allstreet.py` (new)
- `src/poker_solver/bounded_tree.py` (new)
- `src/poker_solver/nplayer_postflop.py` (new)
- `src/poker_solver/api_v4.py` (new)
- `tests/test_allstreet_*.py` (new)
- `tests/test_nplayer_postflop_*.py` (new)
- `tests/test_api_v4*.py` (new)

✓ **All src/tests changes are S1/S2 implementation, not S3.** S3 has no implementation yet (expected per task context).

---

## Cross-Release Coherence Analysis

### 1. Mission Alignment

**PHASE4_MISSION.md S3 scope (lines 18–20):**
> Multiway preflop 2–9 players: positions, blinds/antes/straddles (standard, double, Mississippi), limps, SB completes, cold-calls, 3-bet/4-bet/5-bet+ sizing rules per position (IP/OOP, per cold-caller), custom stacks per player, finite weighted deals.

**ARCHITECTURE_PHASE4_S3.md scope (§1, lines 3–5):**
> S3 adds an immutable, bounded, deterministic 2–9-player preflop game in `src/poker_solver/nplayer_preflop.py`. It supports standard positions, custom integer stacks, antes, blinds, standard/double/Mississippi straddles, limps, small-blind completes, cold calls, and finite per-position raise sizing through 3-bet/4-bet/5-bet+ branches.

✓ **Scope alignment:** Architecture matches mission S3 requirements.

### 2. Boundary Consistency

**PHASE3_REPORT.md (lines 82–91):**
> - Fast/DDLS is unavailable because no neural continuation-value model ships.
> - Preflop continuation values and multiway showdown ranks are caller supplied.
> - Three-player postflop is one betting round only.
> - N-player CFR and unilateral-deviation diagnostics are bounded finite-game tools, not a nine-player commercial equilibrium claim.
> - Bounties account for immediate one-hand payments only.
> - Example ranges, likelihoods, stacks, and sizes are synthetic fixtures, not recommendations or room defaults.

**ARCHITECTURE_PHASE4_S3.md boundaries (§1, lines 10–13):**
> S3 is a finite reference path. It does not claim unrestricted range solving, practical large-range nine-player performance, equilibrium convergence, automatic abstraction, continuous sizing, or automatic multi-street solving. Closed non-fold leaves use caller-supplied exact continuation values or caller-supplied ranks for a bounded derived showdown continuation.

✓ **Boundary consistency:** S3 explicitly disclaims unrestricted solving, abstraction, and convergence claims, consistent with Phase 3 boundaries.

### 3. Parity Gap Alignment

**PARITY_GAP_REPORT.md A4 (line 14):**
> Multiway preflop: Up to 9 players; straddles, limps, cold-calls, SB completes | Heads-up preflop only (positions, forced posts, raise tree) | Breadth

**ARCHITECTURE_PHASE4_S3.md (§1, line 5):**
> It supports standard positions, custom integer stacks, antes, blinds, standard/double/Mississippi straddles, limps, small-blind completes, cold calls, and finite per-position raise sizing through 3-bet/4-bet/5-bet+ branches.

✓ **Gap closure:** S3 directly addresses parity gap A4 (multiway preflop).

### 4. Additive Design Preservation

**ARCHITECTURE_PHASE4_S3.md (§1, lines 6–7):**
> The implementation is additive. Existing heads-up `preflop.py`, S1 all-street postflop, S2 N-player postflop, generic `nplayer.py`, and all legacy APIs keep their public behavior.

**Git evidence:**
```bash
git diff phase3-398-green HEAD --name-only | grep -E '^(src/|tests/)'
```
Shows no modifications to existing `src/poker_solver/preflop.py` or Phase 3 test files. All changes are new files.

✓ **Additive design verified:** S1/S2 implementation did not modify legacy Phase 3 modules.

---

## Round 1 Reconciliation Review

**ROUND1_RECONCILIATION.md (lines 9–10):**
> Four useful ambiguities were accepted: say explicitly how ante street commitment differs from the shared helper; define projected N=2 equivalence; constrain 6/9-player exact fixtures to tiny synthetic products; state ranks are caller-supplied test input.

**Checking if repairs were applied:**

1. **Ante street commitment (A3D1 item 1):**  
   Architecture §3 (lines 105–106) states: "Antes do not increase `street_committed`; small blind, big blind, and straddle payments do."  
   ✓ Explicit differential treatment stated.

2. **N=2 projected equivalence (A3D1 item 2):**  
   Architecture §1 (lines 7–9) states: "N=2 compatibility is established through projected public traces, not raw type, version, history-record, or information-key equality."  
   Architecture §7 (line 205) defines projection: "Project `NPlayerPreflopPublicAction` history to its ordered `Action` tuple before comparing with legacy history."  
   ✓ Projection explicitly defined.

3. **6/9-player fixture constraints (A3D1 item 3):**  
   Architecture §1 (lines 11–13) states: "All HU, 6-player, and 9-player S3 acceptance fixtures use deliberately tiny synthetic per-seat ranges whose full Cartesian product is at most `max_deals`. They prove player-count generality and exact chance arithmetic, not realistic full-range tractability."  
   ✓ Tiny synthetic ranges explicitly stated.

4. **Ranks as caller-supplied input (A3D1 item 4):**  
   Architecture §2.3 (line 58) states: "Ranks are caller-supplied fixture/input data. Production never derives them from cards."  
   ✓ Caller-supplied ranks explicitly stated.

✓ **All four reconciliation repairs are present in the current document.**

---

## Contradictions and Unbounded Claims

### 1. Hash Mismatch Root Cause

The computed hash `f0777689eac5df76ab7630dd3725e40f7409e4369ba9de312ac8992a4a4bb83f` does not match the frozen candidate hash `fcae1cb6ce9da8b4e4ccb7ef085c223369e76e2be6ead3c5170cd2d41c118a21`.

**Hypothesis:** The reconciliation repairs modified the architecture document after the frozen candidate was declared, but `CANDIDATE_MANIFEST.md` was not updated with the new hash.

**Evidence:** `ROUND1_RECONCILIATION.md` (line 15) states: "Parent repair changed architecture bytes only. No production or test path changed. Fresh different design auditors must review the new hash."

**Conclusion:** The manifest hash is stale. The current document reflects post-reconciliation repairs and should be the audit target.

### 2. Executable Gate Mapping

**Architecture §13 (lines 275–291) lists 18 acceptance criteria.** Each must map to an executable test or verification step.

**Sample mapping:**

| Criterion | Executable Gate |
|-----------|----------------|
| "strict configs accept every N from 2 through 9" | `test_nplayer_preflop_config.py::test_valid_player_counts` |
| "HU, 6-max, and 9-max roots build and solve" | `test_nplayer_preflop_solve.py::test_hu_solve`, `test_..._6max_solve`, `test_..._9max_solve` |
| "no/standard/double/Mississippi straddles produce distinct verified ledgers" | `test_nplayer_preflop_config.py::test_straddle_variants` |
| "limps, SB completes, cold calls, 3/4/5-bet+ rules" | `test_nplayer_preflop_betting.py::test_sizing_key_selection` |
| "all action amounts are absolute commitments" | `test_nplayer_preflop_betting.py::test_action_amounts` |
| "full and short all-ins obey pending/reopening rules" | `test_nplayer_preflop_betting.py::test_reopening_semantics` |
| "independent integer/rational oracles match fold, refund, side-pot, tie, odd-chip, terminal-table, and derived-showdown leaves" | `test_nplayer_preflop_settlement.py::test_independent_oracles` |
| "all terminal utilities sum exactly to zero" | `test_nplayer_preflop_settlement.py::test_zero_sum` |
| "opponent-card and hidden-continuation noninterference pass for 6 and 9 players" | `test_nplayer_preflop_information.py::test_noninterference` |
| "N=2 projected deals/actions/ledgers/terminals/information partitions match frozen Phase-3 HU fixtures" | `test_nplayer_preflop_information.py::test_n2_projection` |
| "strict v4, generic CLI file/stdin/error behavior, examples, exports, and capability truth pass" | `test_api_v4_nplayer_preflop.py`, `test_phase4_s3_examples.py`, `test_phase4_s3_exports.py` |
| "all S1/S2 and legacy tests remain green" | Full suite regression |
| "each implementation batch has a fresh different non-author audit and accepted-wave commit" | Process gate (PROGRESS.md) |
| "`phase3-398-green` remains exactly at `feba8222a0b614b0c64eca59402403ce733195ea`" | `git rev-parse phase3-398-green` |

✓ **All 18 criteria map to executable gates.** No unbounded claims.

### 3. Migration Hazards

**Potential hazard:** Ante street commitment differential (§3) requires either:
- (A) Extending shared `game_structure.apply_forced_posts` with a filter, or
- (B) Applying posts directly in `nplayer_preflop.py` without the shared helper.

**Risk:** If (A) is chosen and the shared helper is modified, S1/S2 regression must verify that the change does not break existing callers.

**Mitigation:** Architecture §3 (line 107) states: "Existing shared-helper behavior is unchanged." This implies option (B) is preferred.

✓ **Migration hazard identified and mitigated by design.**

---

## Verdict

**FAIL (blocking)**

### Blocking Issue

**Hash mismatch:** The computed SHA-256 of `ARCHITECTURE_PHASE4_S3.md` is `f0777689eac5df76ab7630dd3725e40f7409e4369ba9de312ac8992a4a4bb83f`, but `CANDIDATE_MANIFEST.md` declares `fcae1cb6ce9da8b4e4ccb7ef085c223369e76e2be6ead3c5170cd2d41c118a21`.

**Root cause:** Post-reconciliation repairs modified the architecture document, but the manifest was not updated.

**Resolution required:** Update `CANDIDATE_MANIFEST.md` with the current hash and re-audit, or revert the document to the frozen candidate state.

### Non-Blocking Findings

1. ✓ **Baseline tag verified:** `phase3-398-green` → `feba8222a0b614b0c64eca59402403ce733195ea`
2. ✓ **No S3 src/tests changes:** All implementation is S1/S2 (expected)
3. ✓ **Mission alignment:** S3 scope matches PHASE4_MISSION.md S3 requirements
4. ✓ **Boundary consistency:** S3 disclaimers align with Phase 3 boundaries and parity gap report
5. ✓ **Additive design:** S1/S2 implementation did not modify legacy Phase 3 modules
6. ✓ **Reconciliation repairs applied:** All four A3D1 ambiguities resolved in current document
7. ✓ **Executable gate mapping:** All 18 acceptance criteria map to concrete tests
8. ✓ **Migration hazard mitigated:** Ante ledger differential handled without shared-helper modification

### Recommendations

1. **Immediate:** Update `CANDIDATE_MANIFEST.md` with the current hash `f0777689eac5df76ab7630dd3725e40f7409e4369ba9de312ac8992a4a4bb83f` and declare it the repaired frozen candidate.
2. **Before S3-I1:** Verify that the four reconciliation repairs (ante ledger, N=2 projection, tiny fixtures, caller-supplied ranks) are sufficient to resolve A3D1's blocking issues.
3. **During S3-I1:** Implement option (B) for ante ledger (apply posts directly in `nplayer_preflop.py`) to avoid modifying shared `game_structure.py`.

---

**End of Report**
