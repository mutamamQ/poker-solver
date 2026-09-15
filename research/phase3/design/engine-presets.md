# Engine modes and canonical presets architecture

## 1. Scope and evidence

This document specifies the Phase 3 engine-mode and preset architecture for the poker-solver repository. It is grounded in:

- PHASE3_MISSION.md Wave B requirements
- research/phase3/engine-modes.md product semantics and correctness contract
- research/phase3/presets-validation.md preset file contract and validation catalogue
- ARCHITECTURE.md Phase 1 and Phase 2 baseline
- Existing solver/CLI/API code (api.py, cli.py, cfr.py, mccfr.py)
- 185 passing baseline tests

No source, test, README, ARCHITECTURE_PHASE3.md, or PROGRESS.md edits are made by this report.

## 2. Engine modes: Classic versus Fast/DDLS

### 2.1 Classic mode

**Definition:** `classic` is an exact full traversal of the declared finite game tree with no depth cutoff and no learned leaf evaluator.

**Behavior:**

1. The complete configured chance and action tree is traversed to every terminal state.
2. All legal actions come from the declared finite action abstraction.
3. Terminal utilities are computed exactly from the game rules.
4. Iteration count is explicit; convergence is measured, not assumed.
5. Heads-up zero-sum outputs report exact-tree expected values and NashConv against an infoset-consistent best response.
6. Deterministic full-tree CFR (vanilla CFR) remains byte-repeatable for the same input and interpreter.
7. Seeded external-sampling MCCFR is a stochastic solver algorithm, not a distinct engine mode.

**Output schema additions:**

```json
{
  "engine_mode": "classic",
  "approximation": false,
  "algorithm": "vanilla-cfr" | "external-sampling-mccfr",
  "iterations": <int>,
  "values": [<float>, <float>],
  "nash_conv": <float>,
  "exploitability_half_nash_conv": <float>
}
```

**Accuracy claim:** Exact traversal and payoff accounting for the configured finite tree. Iterative strategy quality is measured by NashConv, not claimed to be exact Nash.

### 2.2 Fast/DDLS mode

**Status:** Documented boundary. Not implemented in Phase 3.

**Rationale:**

- GTO Wizard Fast/DDLS uses trained neural continuation values and depth-limited re-solving.
- No trained neural model or verified training corpus ships with this dependency-free project.
- A cutoff plus showdown equity ignores future betting, information revelation, and range-dependent responses.
- NeurIPS 2018 depth-limited-solving research (Brown, Sandholm, Amos) cautions that ordinary state-value substitution is insufficient in imperfect-information games.

**API contract:** The API must reject `engine_mode: "fast-ddls"` with a stable documented-boundary error (exit status 2) and a message explaining that trained continuation values are not shipped. Unknown mode names and booleans also fail.

**Example error message:**

```
Unsupported engine_mode 'fast-ddls': trained neural continuation values are not included. Use 'classic' for exact finite-tree solving or 'depth-limited-equity-rollout' for an explicitly bounded approximation.
```

### 2.3 Depth-limited equity rollout (bounded approximation)

**Definition:** `depth-limited-equity-rollout` is an explicitly labeled bounded approximation that truncates the game at a caller-specified public depth boundary and substitutes checkdown equity.

**Behavior:**

1. Traverse the declared game to a caller-specified public depth boundary (e.g., end of flop, end of turn).
2. At each cutoff, enumerate legal remaining board runouts exactly and compute showdown equity for each compatible private deal.
3. Convert equity to terminal utility under an explicit **no-further-betting** continuation assumption.
4. Tag every result with:
   - `engine_mode: "depth-limited-equity-rollout"`
   - `approximation: true`
   - `cutoff_definition: <string>` (e.g., "end-of-flop")
   - `continuation_model: "checkdown-equity"`
   - A warning that there is no unrestricted-game exploitability guarantee.
5. Do not report exact-tree NashConv for the original untruncated game. NashConv may be reported only for the induced truncated game and must be labeled as such.

**Output schema:**

```json
{
  "engine_mode": "depth-limited-equity-rollout",
  "approximation": true,
  "cutoff_definition": "end-of-flop",
  "continuation_model": "checkdown-equity",
  "warning": "No unrestricted-game exploitability guarantee. Approximation ignores future betting.",
  "algorithm": "vanilla-cfr" | "external-sampling-mccfr",
  "iterations": <int>,
  "values": [<float>, <float>],
  "truncated_game_nash_conv": <float>
}
```

**Accuracy claim:** Exact only for the induced checkdown model. No universal numeric error bound is claimed. Observed error is fixture-specific and must be reported by comparison with Classic on instances where Classic is tractable.

**Use case:** Working, testable boundary artifact for Phase 3. Not a claim of Fast/DDLS parity.

### 2.4 Engine mode versus solver algorithm

Engine mode and solver algorithm are orthogonal:

- **Engine mode:** `classic`, `depth-limited-equity-rollout`, or (rejected) `fast-ddls`
- **Solver algorithm:** `vanilla-cfr` or `external-sampling-mccfr`

Valid combinations:

- `classic` + `vanilla-cfr`: deterministic full-tree CFR
- `classic` + `external-sampling-mccfr`: seeded stochastic full-tree MCCFR
- `depth-limited-equity-rollout` + `vanilla-cfr`: deterministic truncated-tree CFR with checkdown equity
- `depth-limited-equity-rollout` + `external-sampling-mccfr`: seeded stochastic truncated-tree MCCFR with checkdown equity

Invalid combinations:

- `fast-ddls` + any algorithm: rejected with documented-boundary error

The API must reject unsupported combinations rather than coercing them.

## 3. Canonical preset library

### 3.1 Preset file contract

Preset files use strict JSON. The Phase 3 API must reject:

- Unknown keys
- Booleans in numeric fields
- Non-finite numbers
- Duplicate player IDs
- Duplicate cards/actions
- Inconsistent stack and contribution values
- References to missing named ranges

Existing version-1 and version-2 APIs remain unchanged.

### 3.2 Phase 3 preset schema

A Phase 3 preset has these top-level fields:

```json
{
  "version": 3,
  "preset_id": "<stable-lowercase-ascii-identifier>",
  "description": "<human-readable-text>",
  "kind": "preflop-heads-up" | "postflop-heads-up" | "postflop-three-way",
  "game": { /* complete game structure in integer chip units */ },
  "ranges": { /* explicit combo weights or references to named ranges */ },
  "tree": { /* sizing mode, candidate sizes, node edits */ },
  "rake": { /* explicit disabled/enabled accounting rule */ },
  "engine": {
    "mode": "classic" | "depth-limited-equity-rollout",
    "algorithm": "vanilla-cfr" | "external-sampling-mccfr",
    "iterations": <int>,
    "seed": <int> | null
  },
  "provenance": {
    "origin": "<string>",
    "accuracy_claim": "<string>",
    "notes": "<string>"
  }
}
```

**Key principles:**

- Amounts use integer chips in the executable game state.
- Human sizing expressions remain strings until converted by the sizing module.
- A preset stores both the expression and the deterministic integer target after conversion so fixtures can detect rounding changes.
- No preset contains a `gto_wizard_url` or claims copied equilibrium ranges unless a separately licensed, machine-readable source is actually bundled and verified.
- Phase 3 canonical examples use `origin: "poker-solver synthetic validation fixture"` and `accuracy_claim: "none; input example only"`.

### 3.3 Required canonical examples

#### 3.3.1 `examples/phase3_btn_vs_bb_25bb.json`

**Kind:** `preflop-heads-up`

**Game structure:**

- Two players: BTN/SB (player 0) and BB (player 1)
- 100-chip big blind, 50-chip small blind, zero ante
- Equal 2,500-chip starting stacks **before forced contributions**
- Root posts 50 and 100, so remaining stacks are 2,450 and 2,400, initial pot is 150
- BTN acts first preflop

**Ranges:** Deliberately tiny explicit combo range per player (e.g., 2-4 combos each) so exhaustive tests remain tractable.

**Tree:** Fixed open/raise-to targets, small maximum raise count.

**Rake:** Disabled.

**Engine:** `classic` + `vanilla-cfr` + explicit iteration count.

**Provenance:**

```json
{
  "origin": "poker-solver synthetic validation fixture",
  "accuracy_claim": "none; input example only",
  "notes": "Demonstrates positions, blind accounting, range loading, and finite raise tree. Not a 25bb equilibrium chart."
}
```

#### 3.3.2 `examples/phase3_sb_vs_bb_15bb.json`

**Kind:** `preflop-heads-up`

**Game structure:**

- Two players: SB (player 0) and BB (player 1)
- 100-chip BB, 50-chip SB, 10-chip per-player ante
- Equal 1,500-chip starting stacks before forced contributions
- Both players post ante; SB posts additional blind and acts first
- Tiny synthetic range
- Include limp, raise, fold, call, and all-in paths within a bounded raise tree

**Rake:** Disabled (chip-EV only).

**Engine:** `classic` + `vanilla-cfr`.

**Provenance:** Same as 3.3.1.

**Note:** Must not smuggle a three-player payout vector into a heads-up game or claim ICM.

#### 3.3.3 `examples/phase3_three_way_river.json`

**Kind:** `postflop-three-way`

**Game structure:**

- Three players
- Fixed five-card board
- One exact noncolliding combo per player
- Unequal remaining stacks
- Declared pot/contribution ledger
- Fixed legal wager targets
- Rake disabled

**Coverage:** Must exercise one fold followed by a two-player showdown and one three-way showdown.

**Optional sibling:** `examples/phase3_three_way_river_raked.json` with percentage-plus-cap rake rule.

**Purpose:** Primary side-pot/payoff-conservation example, not a broad multiway parity claim.

**Engine:** `classic` + `vanilla-cfr`.

**Provenance:** Same as 3.3.1.

#### 3.3.4 `examples/phase3_ranges.json`

**Kind:** Named range library (not a game preset).

**Content:** At least two synthetic named ranges with explicit two-card combos and weights in `[0,1]`.

**Contract:** Import, export, save, and reload must be lossless under canonical ordering. Names are identifiers, not paths.

**Example:**

```json
{
  "version": 3,
  "ranges": {
    "tight_open": [
      {"cards": ["As", "Ah"], "weight": 1.0},
      {"cards": ["Ks", "Kh"], "weight": 1.0}
    ],
    "wide_defend": [
      {"cards": ["As", "Ah"], "weight": 1.0},
      {"cards": ["Ks", "Kh"], "weight": 1.0},
      {"cards": ["Qs", "Qh"], "weight": 0.5}
    ]
  }
}
```

#### 3.3.5 `examples/phase3_exploitative.json`

**Kind:** `postflop-heads-up` with nodelock and profile.

**Content:**

- References one canonical node ID
- Provides a complete locked action distribution
- Includes one explicit profile constraint set

**Note:** Labels such as `calling-station` are display names only; the executable payload contains numerical action constraints/incentives.

**Engine:** `classic` + `vanilla-cfr`.

**Provenance:** Same as 3.3.1.

### 3.4 Preset versioning and synthetic content

All Phase 3 presets use `version: 3` to distinguish them from version-1 (river-only) and version-2 (multi-street) formats.

**Synthetic content policy:**

- Ranges, boards, runout subsets, sizes, and profiles are declared test fixtures.
- No preset claims to reproduce GTO Wizard equilibrium strategies unless a separately licensed, machine-readable source is bundled and verified.
- Position labels (BTN, BB, SB) and stack depths (25bb, 15bb) make examples recognizable, but numeric ranges are synthetic.

**Preset versioning:**

- `version: 1` → Phase 1 river-only format (ARCHITECTURE.md §6)
- `version: 2` → Phase 2 multi-street format (ARCHITECTURE.md §13)
- `version: 3` → Phase 3 extended format with engine mode, rake, nodelock, profiles, and provenance

## 4. API and CLI extensions

### 4.1 Programmatic API (api.py)

**New functions:**

```python
def load_phase3_preset(data: dict[str, Any]) -> Phase3PresetConfig:
    """Load and validate a version-3 preset configuration.
    
    Strict validation:
    - Rejects unknown fields
    - Rejects bool-as-int
    - Rejects non-finite numbers
    - Validates card uniqueness and overlaps
    - Enforces size limits
    - Rejects empty combo lists
    - Rejects zero-total weights
    - Rejects unsupported engine modes
    """
    ...

def solve_phase3_preset(
    config: Phase3PresetConfig
) -> SolveResult:
    """Solve a Phase 3 preset with the configured engine mode and algorithm.
    
    Raises:
        ValueError: If engine_mode is 'fast-ddls' (documented boundary).
        ValueError: If engine_mode is unknown.
    """
    ...
```

**Engine mode validation:**

```python
def _validate_engine_mode(mode: str) -> None:
    if mode == "fast-ddls":
        raise ValueError(
            "Unsupported engine_mode 'fast-ddls': trained neural continuation "
            "values are not included. Use 'classic' for exact finite-tree solving "
            "or 'depth-limited-equity-rollout' for an explicitly bounded approximation."
        )
    if mode not in ("classic", "depth-limited-equity-rollout"):
        raise ValueError(f"Unknown engine_mode {mode!r}")
```

### 4.2 CLI extensions (cli.py)

**New subcommand:**

```
poker-solver solve-preset CONFIG.json [--json]
```

**Behavior:**

1. Load `CONFIG.json` as a version-3 preset.
2. Validate all fields strictly.
3. Solve with the configured engine mode and algorithm.
4. Emit JSON output with `engine_mode`, `approximation`, `algorithm`, `iterations`, `seed`, `values`, `nash_conv`, `exploitability_half_nash_conv`, and `strategy`.
5. If `engine_mode` is `fast-ddls`, exit with status 2 and documented-boundary error message.

**Example invocation:**

```bash
poker-solver solve-preset examples/phase3_btn_vs_bb_25bb.json --json
```

**Example output (Classic):**

```json
{
  "algorithm": "vanilla-cfr",
  "approximation": false,
  "engine_mode": "classic",
  "exploitability_half_nash_conv": 0.0012,
  "iterations": 10000,
  "nash_conv": 0.0024,
  "seed": null,
  "strategy": { /* ... */ },
  "values": [0.15, -0.15]
}
```

**Example output (Depth-limited equity rollout):**

```json
{
  "algorithm": "vanilla-cfr",
  "approximation": true,
  "continuation_model": "checkdown-equity",
  "cutoff_definition": "end-of-flop",
  "engine_mode": "depth-limited-equity-rollout",
  "iterations": 10000,
  "seed": null,
  "strategy": { /* ... */ },
  "truncated_game_nash_conv": 0.0035,
  "values": [0.18, -0.18],
  "warning": "No unrestricted-game exploitability guarantee. Approximation ignores future betting."
}
```

**Example error (Fast/DDLS):**

```bash
$ poker-solver solve-preset examples/phase3_fast.json --json
Error: Unsupported engine_mode 'fast-ddls': trained neural continuation values are not included. Use 'classic' for exact finite-tree solving or 'depth-limited-equity-rollout' for an explicitly bounded approximation.
$ echo $?
2
```

### 4.3 Backward compatibility

Existing version-1 and version-2 APIs remain unchanged:

- `solve-spot CONFIG.json` (version 1, river-only)
- `solve-multistreet CONFIG.json --algorithm ... --iterations ...` (version 2)

These commands do not gain `engine_mode` fields silently. A new Phase 3 endpoint may default explicitly to Classic, but old endpoints retain their previous schema and behavior.

## 5. Examples and tests

### 5.1 Example files

All example files live in `examples/`:

- `examples/phase3_btn_vs_bb_25bb.json`
- `examples/phase3_sb_vs_bb_15bb.json`
- `examples/phase3_three_way_river.json`
- `examples/phase3_three_way_river_raked.json` (optional)
- `examples/phase3_ranges.json`
- `examples/phase3_exploitative.json`

Each file is a complete, loadable, executable fixture.

### 5.2 Test coverage

All tests live in `tests/test_phase3_presets.py` and `tests/test_phase3_engine_modes.py`.

#### 5.2.1 Engine mode tests

1. **Classic equals legacy exact tree.** On Kuhn and existing tiny river/multistreet fixtures, `classic` must produce the same strategy serialization, values, and NashConv as direct `CFRSolver` for the same iterations. Deterministic fields must be byte-identical.

2. **No-cutoff identity.** A depth-limited evaluator whose boundary is at or below every terminal must equal Classic exactly. This checks traversal plumbing without relying on a heuristic.

3. **Checkdown identity.** On a game where all future nodes have only `CHECK`/chance actions, `depth-limited-equity-rollout` at the start of the remaining streets must equal exact Classic value within `1e-12`.

4. **Heuristic counterexample.** Ship a tiny game with a strategically meaningful future bet where checkdown equity and exact continuation value differ. The test proves that the approximation is not mislabeled as exact or Fast parity.

5. **Unsupported Fast fails closed.** Strict JSON and CLI requests for `fast-ddls` return validation/usage status 2 and a stable message explaining that trained continuation values are not shipped. Unknown mode names and booleans also fail.

6. **Metadata honesty.** Classic has `approximation: false`; equity rollout has `approximation: true`; unsupported Fast never emits a result object.

7. **Monotonicity is not required.** Tests must not assert per-iteration monotonic NashConv for vanilla CFR; regret guarantees concern averages/rates, not monotonic improvement at every finite iteration.

8. **Cross-module preservation.** Existing Phase 1 and 2 solve requests, which omit `engine_mode`, retain their previous schema and behavior.

#### 5.2.2 Preset tests

1. **Strict loader.** Every shipped example loads, canonicalizes deterministically, audits, and reaches all intended action kinds.

2. **Provenance disclaims solved output.** Every synthetic fixture has `accuracy_claim: "none; input example only"`.

3. **Stack/pot arithmetic.** Independently verify blind/ante conservation, stack + committed + awarded chips conserved, and action order.

4. **Range round trip.** Import, export, save, and reload must be lossless under canonical ordering.

5. **Nodelock/profile.** Locked policy is preserved exactly; unlocked opponent best response and value equal brute-force enumeration.

6. **Rake.** For each terminal pot, independently compute `min(floor_or_round(rule.percent * eligible_pot), cap)` using the declared rounding and eligibility rule. Operator rake plus player awards equals pot exactly; disabled rake reproduces chip-EV byte-for-byte.

7. **Multiway.** Exhaustive tiny three-player terminal allocation including folds, ties, unequal contributions, side pots, and odd-chip policy. Sum of returns plus rake is zero under the declared baseline.

### 5.3 Acceptance gates

All comparisons use `abs(actual - expected) <= 1e-12` unless a test explicitly documents a looser iterative convergence tolerance.

**Phase 3 preset/engine acceptance:**

- All 185 Phase 1+2 tests remain green.
- All Phase 3 engine mode tests pass (8 tests).
- All Phase 3 preset tests pass (7 tests).
- Every shipped example loads without error.
- Classic mode produces byte-identical output to legacy CFR on Kuhn and river fixtures.
- Fast/DDLS rejection is stable and documented.
- Depth-limited equity rollout is labeled `approximation: true` and includes warning.

## 6. Deterministic accuracy labels and acceptance gates

### 6.1 Accuracy labels

Every solve result must include an explicit accuracy label:

**Classic mode:**

```json
{
  "engine_mode": "classic",
  "approximation": false,
  "accuracy_claim": "Exact traversal and payoff accounting for the configured finite tree. Iterative strategy quality measured by NashConv."
}
```

**Depth-limited equity rollout:**

```json
{
  "engine_mode": "depth-limited-equity-rollout",
  "approximation": true,
  "accuracy_claim": "Exact only for the induced checkdown model. No universal numeric error bound. Observed error is fixture-specific.",
  "warning": "No unrestricted-game exploitability guarantee. Approximation ignores future betting."
}
```

**Fast/DDLS (rejected):**

No result object is emitted. Error message is the accuracy label.

### 6.2 Acceptance gates

All acceptance gates use deterministic arithmetic and probability comparisons with absolute tolerance `1e-12` unless a test explicitly documents a looser iterative convergence tolerance.

**Engine mode gates:**

1. Classic equals legacy exact tree (byte-identical on Kuhn and river).
2. No-cutoff identity (depth-limited evaluator at terminal equals Classic).
3. Checkdown identity (checkdown-only game equals Classic within `1e-12`).
4. Heuristic counterexample (checkdown equity differs from strategic continuation).
5. Unsupported Fast fails closed (exit status 2, stable message).
6. Metadata honesty (Classic `approximation: false`, rollout `approximation: true`).
7. Cross-module preservation (old endpoints unchanged).

**Preset gates:**

1. Strict loader (all examples load and audit).
2. Provenance disclaims solved output (all synthetic fixtures).
3. Stack/pot arithmetic (independent verification).
4. Range round trip (lossless).
5. Nodelock/profile (locked policy preserved, opponent BR exact).
6. Rake (operator rake + player awards = pot exactly).
7. Multiway (sum of returns + rake = zero).

**Baseline preservation:**

- All 185 Phase 1+2 tests remain green.

## 7. Implementation guidance

### 7.1 Module ownership

No new modules are created by this report. Extensions are made to existing modules:

- `api.py`: Add `load_phase3_preset`, `solve_phase3_preset`, `_validate_engine_mode`.
- `cli.py`: Add `solve-preset` subcommand.
- `tests/test_phase3_presets.py`: New test file for preset tests.
- `tests/test_phase3_engine_modes.py`: New test file for engine mode tests.
- `examples/`: Add six new JSON files.

### 7.2 Separation of concerns

Engine mode is separate from solver algorithm:

- **Engine mode:** Defines the game tree (full traversal, depth-limited, or rejected).
- **Solver algorithm:** Defines the iterative regret-minimization method (vanilla CFR or MCCFR).

A suitable strict schema has two orthogonal fields:

```json
{
  "engine_mode": "classic" | "depth-limited-equity-rollout",
  "algorithm": "vanilla-cfr" | "external-sampling-mccfr"
}
```

This prevents the common but incorrect mapping "MCCFR = Fast."

### 7.3 Error handling

All validation errors raise `ValueError` with a descriptive message and exit with status 2 (invalid input).

Internal runtime failures exit with status 1.

Successful execution exits with status 0.

### 7.4 JSON schema strictness

All Phase 3 preset loaders must:

- Reject unknown fields.
- Reject booleans in numeric fields.
- Reject non-finite numbers.
- Validate card uniqueness and overlaps.
- Enforce size limits.
- Reject empty combo lists.
- Reject zero-total weights.
- Reject unsupported engine modes.

### 7.5 Backward compatibility

Existing version-1 and version-2 APIs remain unchanged. No silent schema changes.

## 8. Product parity matrix

| Item | Status |
|------|--------|
| Classic mode (exact finite-tree traversal) | Implement |
| Fast/DDLS mode (neural continuation values) | Documented boundary; reject explicitly |
| Depth-limited equity rollout (bounded approximation) | Implement with explicit labels |
| BTN vs BB 25bb preset | Implement as synthetic fixture |
| SB vs BB 15bb preset | Implement as synthetic fixture |
| Three-way river preset | Implement as synthetic fixture |
| Named range library | Implement |
| Nodelock/profile preset | Implement |
| Embedded equilibrium charts | Not included |
| Authenticated GTO Wizard API | Not included |
| Full presolved spot library | Tier 3 documented boundary |
| Numeric parity with GTO Wizard | Not claimed |

## 9. Definition of done

**Deliverable:** This report (`research/phase3/design/engine-presets.md`).

**Verification:** Read back the report to confirm completeness.

**Acceptance criteria:**

- Exact Classic behavior specified (§2.1).
- Explicitly labeled bounded checkdown rollout/Fast approximation specified (§2.3).
- Neural-value boundary documented (§2.2).
- Preset versioning specified (§3.4).
- Synthetic config content without invented strategy data specified (§3.4).
- APIs/CLI/examples/tests specified (§4, §5).
- Deterministic accuracy labels specified (§6.1).
- Acceptance gates specified (§6.2).
- No source, test, README, ARCHITECTURE_PHASE3.md, or PROGRESS.md edits made.

**Baseline preservation:** 185 tests remain green (not verified by this report; verified by implementation).

---

**Report complete.**
