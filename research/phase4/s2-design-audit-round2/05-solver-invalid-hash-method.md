# F205 S2 design-only solver audit

**Frozen hash**: 770a25ab (verified: 43e33aff — HASH MISMATCH)
**Auditor**: F205
**UTC**: 2026-09-15T21:16:30Z
**Verdict**: FAIL

## Critical findings

### 1. Hash mismatch (blocking)
Manifest declares `770a25ab` but actual ARCHITECTURE_PHASE4_S2.md hash is `43e33aff`. Audit cannot proceed against unfrozen specification.

### 2. CFR reach reuse (conditional PASS if hash corrected)
Section 8 correctly states "reuse `NPlayerCFRSolver`" and "S2 adds no duplicate reach tracker." Existing `nplayer.py` lines 178–246 implement counterfactual reach (chance × opponents, excluding own reach). Specification correctly delegates to proven implementation.

### 3. S2-I2 bound plumbing (PASS)
Section 8 mandates keyword-only `max_nodes`/`max_depth` parameters forwarded to `collect_nplayer_infosets`. Existing `nplayer.py` lines 52–63 already accept these parameters with strict validation. S2-I2 constructor change is minimal and well-defined.

### 4. Detached truthful results (PASS)
Section 8 specifies `NPlayerPostflopSolveResult` with "detached strategy" and "truthful metadata." Section 9 requires "detached typed mapping" for showdown ranks. Specification correctly mandates defensive copies preventing caller mutation.

### 5. Exhaustive diagnostic capping (PASS)
Section 8: "optional positive `max_pure_strategies`... runs or fails closed on its cap. It is never sampled and is never described as Nash convergence." Existing `unilateral_deviation_certificate` (lines 305–344) enforces strict cap and returns provenance "diagnostic only." Specification correctly prohibits convergence claims.

### 6. Tiny acceptance fixtures (PASS)
Section 11 mandates 4-, 5-, 9-player executable acceptance with exact hand-derived oracles. Section 10 requires independent settlement oracles that "do not use the settlement functions to calculate expected results." Specification makes tiny bounded trees feasible through `max_deals`, `max_nodes`, strict caps, and independent verification.

## Non-findings (expected absences)
- No S2 implementation in `src/poker_solver/nplayer_postflop.py` (expected per manifest line 9)
- No S2-I1/S2-I2 test modules (expected; design-only audit)

## Recommendation
Cannot accept. Correct hash mismatch before re-audit. If hash corrected to match actual content, conditional PASS on items 2–6.