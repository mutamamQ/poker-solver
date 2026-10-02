# Phase 4 S4 release/compatibility/implementation-plan design

## 1. Scope and decision

S4 delivers automatic hand abstraction to keep solves tractable. The design wave's consensus is category-based or blocker-aware abstraction chosen via explicit config, with documented abstraction policy and determinism.

This document defines:

- **Compatibility matrix**: which S4 abstraction modes work with which game types (S1 all-street, S2 N-player postflop, S3 N-player preflop);
- **Implementation/audit sequencing**: bounded stdlib-only batches, RED chronology, focused/legacy/full gates;
- **Release boundaries**: candidate manifest scope, fresh non-author post-batch audit scopes, documentation boundaries, failure/fallback rules, commit plan.

## 2. Compatibility matrix

### 2.1 Abstraction modes

S4 introduces three abstraction modes:

| Mode | Description | Determinism | State-count bound |
|------|-------------|-------------|-------------------|
| `none` | No abstraction; full combo enumeration | Exact | Cartesian product |
| `category-based` | Group combos by hand-strength category (e.g., equity buckets, made-hand classes) | Config + seed | Declared category count |
| `blocker-aware` | Merge strategically similar combos preserving blocker structure | Config + seed | Declared blocker-class count |

### 2.2 Game-type compatibility

| Game type | `none` | `category-based` | `blocker-aware` | Notes |
|-----------|--------|------------------|-----------------|-------|
| S1 all-street postflop | ✓ | ✓ | ✓ | All modes supported; abstraction applied per street |
| S2 N-player postflop (3–9p) | ✓ | ✓ | ✓ | All modes; multiway blocker interactions preserved |
| S3 N-player preflop (2–9p) | ✓ | ✓ | ✓ | All modes; per-seat abstraction independent |
| Legacy HU preflop (`preflop.py`) | ✓ | ✗ | ✗ | No abstraction; legacy module unchanged |
| Legacy 3p postflop (`multiway.py`) | ✓ | ✗ | ✗ | No abstraction; legacy module unchanged |

### 2.3 Continuation compatibility

| Continuation type | `none` | `category-based` | `blocker-aware` |
|-------------------|--------|------------------|------------------|
| Automatic natural terminal (S1) | ✓ | ✓ | ✓ |
| Supplied terminal-table | ✓ | ✓ (keys must match abstracted deals) | ✓ (keys must match abstracted deals) |
| Derived showdown-ranks | ✓ | ✓ (ranks per abstract class) | ✓ (ranks per abstract class) |

### 2.4 Solver compatibility

| Algorithm | `none` | `category-based` | `blocker-aware` |
|-----------|--------|------------------|------------------|
| `vanilla-cfr` | ✓ | ✓ | ✓ |
| `external-sampling-mccfr` | ✓ | ✓ | ✓ |

## 3. Implementation batches and RED chronology

### Batch S4-I1 — typed abstraction config and deterministic mapping

Exclusive ownership, at most six BryantGPT authors:

1. **RED**: `tests/test_abstraction_config.py` — immutable `AbstractionConfig` construction, mode validation, seed requirements, defensive copies, malformed inputs.
2. **RED**: `tests/test_abstraction_category.py` — deterministic category-based mapping, equity-bucket assignment, same-seed repeatability, blocker-collision handling.
3. **RED**: `tests/test_abstraction_blocker.py` — deterministic blocker-aware mapping, strategic-equivalence grouping, same-seed repeatability, multiway blocker preservation.
4. **RED**: `tests/test_abstraction_bounds.py` — state-count bounds, max-abstract-combos enforcement, Cartesian-product reduction verification.
5. **GREEN**: `src/poker_solver/abstraction.py` — core abstraction logic only.
6. **GREEN**: Integration — parent runs focused tests, then full 398+ baseline.

**Audit gate**: Fresh six-topic non-author audit attacks config mutation, category determinism, blocker determinism, bound enforcement, multiway correctness, and full regression. No S4-I2 begins until I1 is accepted and committed.

### Batch S4-I2 — S1/S2/S3 integration and oracle comparison

After I1 audit only:

1. **RED**: `tests/test_allstreet_abstraction.py` — S1 all-street with abstraction, per-street application, automatic terminal compatibility.
2. **RED**: `tests/test_nplayer_postflop_abstraction.py` — S2 N-player postflop with abstraction, multiway blocker preservation.
3. **RED**: `tests/test_nplayer_preflop_abstraction.py` — S3 N-player preflop with abstraction, per-seat independent abstraction.
4. **RED**: `tests/test_abstraction_oracle.py` — small exact fixture vs abstracted fixture, derived convergence bounds.
5. **GREEN**: `src/poker_solver/allstreet.py`, `nplayer_postflop.py`, `nplayer_preflop.py` — additive abstraction integration only.
6. **GREEN**: Integration — parent runs focused oracle/API gates and full suite.

**Audit gate**: Fresh non-author audit attacks oracle independence, convergence math, S1/S2/S3 compatibility, abstraction-continuation key matching, and full regression. Any repair requires RED regression, focused/full GREEN, and fresh different-agent repair audit.

### Batch S4-I3 — v4 API, CLI, examples, exports

After I2 audit only:

1. **RED**: `tests/test_api_v4_abstraction.py` — v4 envelope with abstraction config, strict schema, error handling.
2. **RED**: `tests/test_phase4_s4_cli.py` — CLI abstraction flags, JSON input/output, error messages.
3. **RED**: `tests/test_phase4_s4_examples.py` — canonical abstracted examples (S1/S2/S3), synthetic/non-presolved provenance.
4. **RED**: `tests/test_phase4_s4_exports.py` — capability manifest updates, truthful abstraction advertising.
5. **GREEN**: `src/poker_solver/api_v4.py` — additive abstraction operations.
6. **GREEN**: `examples/phase4/s4_*.json` — canonical examples.
7. **GREEN**: Package exports, capability manifest.

**Audit gate**: Fresh non-author audit attacks API strictness, CLI behavior, example truthfulness/determinism, capability truth, and full regression.

## 4. Focused/legacy/full test gates

### 4.1 Focused gates (per batch)

- **S4-I1**: All `test_abstraction_*.py` (config, category, blocker, bounds) GREEN.
- **S4-I2**: All `test_*_abstraction.py` (allstreet, nplayer_postflop, nplayer_preflop, oracle) GREEN.
- **S4-I3**: All `test_*_s4_*.py` (api_v4, cli, examples, exports) GREEN.

### 4.2 Legacy gates (per batch)

All prior Phase 1+2+3 tests (398 tests) plus S1/S2/S3 tests remain GREEN. No silent breakage of:

- `test_allstreet_*.py` (S1)
- `test_nplayer_postflop_*.py` (S2)
- `test_nplayer_preflop_*.py` (S3)
- All Phase 3 baseline tests

### 4.3 Full regression gate (per batch)

Complete suite (398 + S1 + S2 + S3 + S4 focused) GREEN before audit.

## 5. Candidate manifest scope

Each batch produces a `CANDIDATE_MANIFEST.md` under `research/phase4/s4-i{1,2,3}-audit/` containing:

- Batch ID and exclusive file ownership
- RED receipt hashes (pytest output, test file hashes)
- GREEN receipt hashes (production file hashes, focused test pass, full suite pass)
- Parent verification timestamp and commit SHA
- Audit assignment (six non-author topics for I1/I2, four for I3)

## 6. Fresh non-author post-batch audit scopes

### S4-I1 audit (six topics, six auditors)

1. **Config mutation/construction**: `AbstractionConfig` immutability, defensive copies, validation.
2. **Category determinism**: Same seed → same category mapping; equity-bucket stability.
3. **Blocker determinism**: Same seed → same blocker-class mapping; strategic-equivalence correctness.
4. **Bound enforcement**: State-count reduction verified; max-abstract-combos respected.
5. **Multiway correctness**: N-player blocker interactions preserved.
6. **Full regression**: All 398+ tests GREEN; no silent breakage.

### S4-I2 audit (six topics, six auditors)

1. **Oracle independence**: Exact vs abstracted fixture comparison; convergence bounds derived, not guessed.
2. **S1 compatibility**: All-street abstraction per-street; automatic terminal compatibility.
3. **S2 compatibility**: N-player postflop abstraction; multiway blocker preservation.
4. **S3 compatibility**: N-player preflop abstraction; per-seat independence.
5. **Continuation key matching**: Abstracted deals match supplied terminal-table/showdown-ranks keys.
6. **Full regression**: All S1/S2/S3 + baseline tests GREEN.

### S4-I3 audit (four topics, four auditors)

1. **API strictness**: v4 envelope schema, unknown/missing fields fail closed, error messages.
2. **CLI behavior**: Abstraction flags, JSON input/output, error exit codes.
3. **Example truthfulness**: Canonical examples synthetic/non-presolved, deterministic, documented provenance.
4. **Capability truth**: Manifest advertises abstraction modes accurately; no overclaiming.

## 7. Documentation boundaries

S4 documentation must state:

- **What abstraction does**: Reduces state count by grouping strategically similar combos.
- **What abstraction does NOT do**: Does not claim unrestricted poker, convergence certificate, or automatic optimal abstraction selection.
- **Determinism**: Same config + seed → same abstraction mapping.
- **Accuracy trade-off**: Abstracted solutions are approximate; derived bounds quantify error vs exact on small fixtures.
- **Mode selection**: User chooses mode; no automatic mode selection.
- **Continuation compatibility**: Supplied terminal-table/showdown-ranks keys must match abstracted deals.

Documentation must NOT claim:

- "Commercial GTO Wizard parity" (S4 is one component; full parity requires S1–S7 + neural DDLS).
- "Optimal abstraction" (mode selection is user-driven, not optimized).
- "Exact equilibrium" (abstraction introduces approximation).
- "Automatic convergence" (finite-iteration CFR + abstraction = bounded approximation).

## 8. Failure/fallback rules

### 8.1 Config validation failures

- Invalid mode → fail closed, exit 2, clear error message.
- Missing seed for `category-based`/`blocker-aware` → fail closed.
- `max_abstract_combos` exceeded → fail closed before solve, clear error message.
- Malformed abstraction config → fail closed, no silent fallback to `none`.

### 8.2 Runtime failures

- Abstraction mapping collision (should not occur with correct seed) → fail closed, log seed/config.
- Continuation key mismatch (supplied table uses non-abstracted deals) → fail closed, clear error message.
- State-count bound exceeded during solve → fail closed, suggest higher `max_abstract_combos` or coarser abstraction.

### 8.3 Fallback policy

No silent fallback. Every failure is explicit, logged, and exits with non-zero code. User must fix config or input.

## 9. Expected residual failures between batches

### After S4-I1 (before I2)

- S1/S2/S3 integration tests do not exist yet → expected.
- Oracle comparison tests do not exist yet → expected.
- API/CLI/examples do not exist yet → expected.

### After S4-I2 (before I3)

- v4 API abstraction operations do not exist yet → expected.
- CLI abstraction flags do not exist yet → expected.
- Canonical examples do not exist yet → expected.
- Capability manifest does not advertise abstraction yet → expected.

### After S4-I3 (S4 complete)

No expected residual failures. Full S4 scope complete.

## 10. Commit plan

### S4-I1 commit

- Message: `Phase 4 S4-I1: typed abstraction config and deterministic mapping`
- Files: `src/poker_solver/abstraction.py`, `tests/test_abstraction_{config,category,blocker,bounds}.py`
- Tag: `phase4-s4-i1-green`
- Parent verification: Focused + full suite GREEN, fresh audit PASS.

### S4-I2 commit

- Message: `Phase 4 S4-I2: S1/S2/S3 abstraction integration and oracle comparison`
- Files: `src/poker_solver/{allstreet,nplayer_postflop,nplayer_preflop}.py` (additive only), `tests/test_{allstreet,nplayer_postflop,nplayer_preflop,abstraction}_abstraction.py`
- Tag: `phase4-s4-i2-green`
- Parent verification: Focused + full suite GREEN, fresh audit PASS.

### S4-I3 commit

- Message: `Phase 4 S4-I3: v4 API, CLI, examples, exports for abstraction`
- Files: `src/poker_solver/api_v4.py` (additive), `examples/phase4/s4_*.json`, package exports, `tests/test_{api_v4,phase4_s4_{cli,examples,exports}}_*.py`
- Tag: `phase4-s4-complete`
- Parent verification: Focused + full suite GREEN, fresh audit PASS.

## 11. Risks and mitigations

### 11.1 Overclaiming commercial abstraction

**Risk**: Claiming S4 delivers "GTO Wizard automatic abstraction" when it is user-configured, not learned/optimized.

**Mitigation**: Documentation explicitly states mode selection is user-driven; no automatic optimization. Provenance metadata includes `abstraction_mode` and `user_configured=true`.

### 11.2 Convergence overclaiming

**Risk**: Claiming abstracted solutions are "exact" or "converged" when abstraction introduces approximation.

**Mitigation**: Result metadata includes `approximate=true` when abstraction mode is not `none`. Documentation states derived bounds quantify error vs exact on small fixtures; no convergence certificate.

### 11.3 State-count undercounting

**Risk**: Abstraction reduces state count but not as much as expected; large spots still intractable.

**Mitigation**: Acceptance tests verify state-count reduction on measured fixtures. Documentation states S4 is a tractability tool, not a performance guarantee. S5 continuous sizing and S1 neural DDLS are separate tractability layers.

### 11.4 Error-bound underestimation

**Risk**: Derived bounds on abstracted vs exact error are too loose or too tight.

**Mitigation**: Oracle comparison uses measured NashConv on both exact and abstracted fixtures. Bounds are derived from measured convergence, not guessed. Permanent regression freezes measured bounds.

## 12. S4 definition of done

S4 is accepted only when:

- All three implementation batches (I1, I2, I3) have passed focused + legacy + full gates.
- Each batch has a fresh non-author executable audit with PASS verdict.
- Compatibility matrix verified: all S1/S2/S3 game types work with all abstraction modes.
- Oracle comparison satisfies derived bounds on measured fixtures.
- API/CLI/examples/exports truthfully advertise abstraction capabilities.
- Documentation states boundaries (user-configured, approximate, no convergence certificate).
- All prior 398+ baseline tests plus S1/S2/S3 tests remain GREEN.
- Three accepted-wave commits with tags `phase4-s4-i{1,2,3}-green` and final `phase4-s4-complete`.
- `phase3-398-green` tag remains exactly at `feba8222a0b614b0c64eca59402403ce733195ea`.

This does NOT complete S5–S7 or Phase 4.

## 13. Heartbeat and status

**Heartbeat path**: `/home/genomix-node/poker-solver/research/phase4/s4-design/.hb/S4D6`

**Final status**: `COMPLETE_DESIGN`

**Report hash**: SHA-256 of this file after write.
