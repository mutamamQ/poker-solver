# Phase 3 CLI and examples surface design

## Mission

This document specifies the unified Phase 3 command-line interface, canonical example ownership, input/output conventions, deterministic JSON contracts, failure modes, backward compatibility, and smoke tests. It is the authoritative CLI design for every Phase 3 feature: preflop heads-up, three-way postflop, range editing, bet sizing modes, nodelocking, profiles, rake, ICM, engine modes, and preset library.

## Design principles

1. **Strict versioning:** Phase 3 uses `version: 3` in all new preset/config files. Versions 1 and 2 remain supported without modification.
2. **Deterministic JSON:** All successful outputs use `json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False)`. Same input produces byte-identical output for deterministic algorithms.
3. **Exit codes:** 0 = success, 2 = validation/input error, 1 = internal runtime failure, 130 = interrupt.
4. **No silent fallbacks:** Unknown fields, booleans in numeric slots, NaN/infinity, unsupported modes, and missing references fail with clear error messages to stderr.
5. **Stdin support:** Every config-file command accepts `-` to read JSON from stdin.
6. **Backward compatibility:** Existing `evaluate`, `equity`, `solve-kuhn`, `solve-spot`, `solve-multistreet`, and `exploitability` commands remain unchanged in behavior and output format.

## Subcommand matrix

### Existing commands (unchanged)

| Command | Input | Output | Phase |
|---------|-------|--------|-------|
| `evaluate CARD...` | 5 or 7 strict cards | Hand category and rank tuple | 1 |
| `equity --hero C,C --villain C,C [--board C,...]` | Exact combos | Integer wins/ties/losses/total, equity | 1 |
| `solve-kuhn --iterations N` | None | Kuhn strategy, values, NashConv | 1 |
| `solve-spot CONFIG.json --iterations N` | Version 1 river config | Strategy, values, NashConv | 1 |
| `solve-multistreet CONFIG.json --algorithm ALG --iterations N [--seed S]` | Version 2 multistreet config | Strategy, values, NashConv, seed | 2 |
| `exploitability CONFIG.json STRATEGY.json` | Version 2 config + strategy | BR values, incentives, NashConv | 2 |

### New Phase 3 commands

| Command | Input | Output | Feature |
|---------|-------|--------|----------|
| `solve-preset PRESET.json [--output OUT.json]` | Version 3 preset | Solved strategy + metadata | Unified preset solver |
| `validate-preset PRESET.json` | Version 3 preset | Validation report or errors | Preset structural validation |
| `range-edit OPERATION ARGS...` | Range library + operation | Modified range library | Range editor CLI |
| `range-table CONFIG.json STRATEGY.json NODE --player P` | Config + strategy + node ID | Per-combo action/EV table | Strategy display |
| `convert-sizing EXPR --pot P --stack S [--bb BB]` | Size expression + context | Integer raise-to target | Sizing unit converter |
| `list-presets [--kind KIND]` | None | Shipped preset inventory | Preset discovery |

## Version 3 preset schema

### Top-level structure

```json
{
  "version": 3,
  "preset_id": "btn_vs_bb_25bb",
  "description": "BTN vs BB 25bb effective preflop",
  "kind": "preflop-heads-up",
  "game": { ... },
  "ranges": { ... },
  "tree": { ... },
  "rake": { ... },
  "engine": { ... },
  "provenance": { ... }
}
```

### Field specifications

- **`version`**: JSON integer, must equal `3`
- **`preset_id`**: stable lowercase ASCII identifier matching `[a-z0-9][a-z0-9_-]{0,63}`
- **`description`**: human-readable string, never parsed as rules
- **`kind`**: one of `"preflop-heads-up"`, `"postflop-heads-up"`, `"postflop-three-way"`
- **`game`**: complete game structure (see Game structure section)
- **`ranges`**: explicit combos or named range references (see Range specification)
- **`tree`**: sizing mode and node edits (see Tree configuration)
- **`rake`**: explicit rake rule (see Rake specification)
- **`engine`**: solver algorithm and mode (see Engine configuration)
- **`provenance`**: origin, accuracy claim, notes

### Game structure

#### Preflop heads-up

```json
"game": {
  "players": [
    {"id": 0, "position": "BTN", "starting_stack": 2500},
    {"id": 1, "position": "BB", "starting_stack": 2500}
  ],
  "blinds": {"small": 50, "big": 100},
  "antes": {"mode": "per-player", "amount": 0},
  "first_to_act_preflop": 0
}
```

#### Postflop heads-up

```json
"game": {
  "players": [
    {"id": 0, "position": "BTN"},
    {"id": 1, "position": "BB"}
  ],
  "starting_street": "river",
  "starting_board": ["2c", "3d", "4h", "9s", "Kc"],
  "initial_dead_pot": 100,
  "effective_stack": 50,
  "allowed_runouts": [],
  "first_to_act": 1
}
```

#### Postflop three-way

```json
"game": {
  "players": [
    {"id": 0, "position": "BTN", "stack": 100},
    {"id": 1, "position": "SB", "stack": 80},
    {"id": 2, "position": "BB", "stack": 120}
  ],
  "starting_street": "river",
  "starting_board": ["2c", "3d", "4h", "9s", "Kc"],
  "pot": 50,
  "contributions": [10, 15, 25],
  "allowed_runouts": [],
  "first_to_act": 1
}
```

### Range specification

#### Explicit combos

```json
"ranges": {
  "player0": [
    {"cards": ["As", "5s"], "weight": 1.0},
    {"cards": ["Qs", "Js"], "weight": 0.5}
  ],
  "player1": [
    {"cards": ["Kh", "Qh"], "weight": 1.0}
  ]
}
```

#### Named range reference

```json
"ranges": {
  "player0": {"ref": "btn_25bb_open"},
  "player1": {"ref": "bb_25bb_defend"}
}
```

Named ranges must exist in the same preset file's `range_library` section or in a separately loaded library file.

### Tree configuration

#### Fixed sizing

```json
"tree": {
  "mode": "fixed",
  "default_sizes": [
    {"unit": "pot-percent", "value": 33},
    {"unit": "pot-percent", "value": 75},
    {"unit": "all-in"}
  ],
  "max_raises": 3
}
```

#### Dynamic sizing

```json
"tree": {
  "mode": "dynamic",
  "candidates": [
    {"unit": "pot-percent", "value": 25},
    {"unit": "pot-percent", "value": 50},
    {"unit": "pot-percent", "value": 75},
    {"unit": "pot-percent", "value": 100},
    {"unit": "all-in"}
  ],
  "retained_count": 3,
  "selecting_player": 0,
  "tie_tolerance": 1e-6
}
```

#### Automatic sizing

```json
"tree": {
  "mode": "automatic",
  "max_sizes": 3,
  "ev_tolerance": 0.001,
  "selecting_player": 0
}
```

#### Node edits and nodelocking

```json
"tree": {
  "mode": "fixed",
  "default_sizes": [...],
  "node_edits": [
    {
      "node_id": "root.check.bet:75",
      "player": 1,
      "locked_strategy": {
        "fold": 0.2,
        "call": 0.6,
        "raise:150": 0.2
      }
    }
  ]
}
```

### Rake specification

#### Disabled

```json
"rake": {"enabled": false}
```

#### Percentage with cap

```json
"rake": {
  "enabled": true,
  "percent": 5.0,
  "cap": 3,
  "no_flop_no_drop": true,
  "rounding": "floor"
}
```

### Engine configuration

```json
"engine": {
  "mode": "classic",
  "algorithm": "vanilla-cfr",
  "iterations": 10000,
  "seed": null
}
```

- **`mode`**: `"classic"` (full tree) or `"depth-limited-equity-rollout"` (bounded approximation). `"fast-ddls"` is rejected as unsupported.
- **`algorithm`**: `"vanilla-cfr"` or `"external-sampling-mccfr"`
- **`iterations`**: positive integer
- **`seed`**: JSON integer or `null`; required for MCCFR

### Provenance

```json
"provenance": {
  "origin": "poker-solver synthetic validation fixture",
  "accuracy_claim": "none; input example only",
  "notes": "Tiny bounded range for exhaustive testing"
}
```

## Input/output conventions

### File input

```bash
poker-solver solve-preset examples/phase3_btn_vs_bb_25bb.json --json
```

### Stdin input

```bash
cat preset.json | poker-solver solve-preset - --json
echo '{"version": 3, ...}' | poker-solver solve-preset - --json
```

### Output file

```bash
poker-solver solve-preset preset.json --output solution.json --json
```

Without `--output`, JSON goes to stdout. With `--output`, a success message goes to stdout and the full result is written to the file.

### Deterministic JSON

All JSON output uses:

```python
json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False)
```

- Sorted keys ensure field order
- Compact separators remove whitespace
- `allow_nan=False` rejects NaN/Infinity
- Floating-point numbers use Python's default shortest representation
- Deterministic algorithms produce byte-identical output for identical input

### Strategy serialization

Information set keys use `repr()` of the canonical key tuple. Actions use `kind` for zero-amount actions and `kind:amount` for sized actions:

```json
"strategy": {
  "('river-v1', 0, (0, 1), (2, 3, 4, 5, 6), (), 2, 1, 1)": {
    "check": 0.65,
    "bet:1": 0.35
  }
}
```

## Deterministic output fields

### solve-preset output

```json
{
  "preset_id": "btn_vs_bb_25bb",
  "version": 3,
  "engine": {
    "mode": "classic",
    "algorithm": "vanilla-cfr",
    "iterations": 10000,
    "seed": null,
    "approximation": false
  },
  "metadata": {
    "config_version": 3,
    "kind": "preflop-heads-up",
    "tree_mode": "fixed",
    "rake_enabled": false
  },
  "values": [0.123, -0.123],
  "nash_conv": 0.0045,
  "exploitability_half_nash_conv": 0.00225,
  "strategy": { ... }
}
```

### validate-preset output

```json
{
  "valid": true,
  "preset_id": "btn_vs_bb_25bb",
  "checks": {
    "schema": "pass",
    "cards": "pass",
    "stacks": "pass",
    "ranges": "pass",
    "tree": "pass",
    "rake": "pass"
  },
  "warnings": []
}
```

### range-table output

```json
{
  "node": "root.check.bet:75",
  "player": 1,
  "acts_here": true,
  "total_compatible_mass": 12.5,
  "combos": [
    {
      "cards": ["As", "Ah"],
      "source_weight": 1.0,
      "reach": 0.85,
      "normalized_prob": 0.068,
      "actions": {
        "fold": {"prob": 0.1, "ev": -0.5},
        "call": {"prob": 0.7, "ev": 0.3},
        "raise:150": {"prob": 0.2, "ev": 0.8}
      },
      "mixed_ev": 0.37
    }
  ],
  "aggregate": {
    "fold": 0.15,
    "call": 0.65,
    "raise:150": 0.20,
    "ev": 0.25
  }
}
```

### convert-sizing output

```json
{
  "expression": {"unit": "pot-percent", "value": 75},
  "context": {"pot": 100, "stack": 200, "to_call": 0},
  "unrounded": 75.0,
  "target": 75,
  "rounding": "half-up",
  "legal": true
}
```

## Error handling and failures

### Validation errors (exit 2)

| Error | Message |
|-------|----------|
| Unknown version | `error: version must be 1, 2, or 3` |
| Boolean in numeric field | `error: {field} must be a JSON integer` |
| Non-finite number | `error: {field} must be finite` |
| Duplicate cards | `error: duplicate card {card}` |
| Unknown preset kind | `error: kind must be preflop-heads-up, postflop-heads-up, or postflop-three-way` |
| Missing range reference | `error: range reference '{name}' not found` |
| Invalid sizing mode | `error: tree mode must be fixed, dynamic, or automatic` |
| Unsupported engine mode | `error: engine mode 'fast-ddls' is not supported; trained continuation values are not shipped` |
| MCCFR without seed | `error: external-sampling-mccfr requires a seed` |
| Invalid node ID | `error: node_id '{id}' does not exist in tree` |
| Locked strategy incomplete | `error: locked strategy probabilities sum to {sum}, expected 1.0` |
| Rake percentage out of range | `error: rake percent must be in [0, 100]` |
| Zero compatible mass | `error: ranges have no compatible positive-weight deals` |

### Runtime errors (exit 1)

| Error | Message |
|-------|----------|
| Internal solver failure | `error: solver failed: {details}` |
| Negative NashConv | `error: negative NashConv indicates a best-response bug` |
| Strategy validation failure | `error: strategy probabilities do not sum to one at {key}` |

### File errors (exit 2)

| Error | Message |
|-------|----------|
| File not found | `error: [Errno 2] No such file or directory: '{path}'` |
| JSON parse error | `error: Expecting value: line {N} column {M}` |
| Permission denied | `error: [Errno 13] Permission denied: '{path}'` |

## Canonical preset examples

### 1. `examples/phase3_btn_vs_bb_25bb.json`

**Owner:** Preflop heads-up feature  
**Purpose:** BTN vs BB 25bb effective with tiny synthetic range  
**Key features:**
- Two-player preflop
- Blind accounting (50 SB, 100 BB)
- Zero ante
- Starting stacks 2,500 before blinds
- Tiny explicit combo ranges (tractable exhaustive tests)
- Fixed sizing with bounded raises
- Classic engine, vanilla CFR

**Acceptance test:** Loads, validates, solves in <10s, produces finite zero-sum values, NashConv >= 0

### 2. `examples/phase3_sb_vs_bb_15bb.json`

**Owner:** Preflop heads-up feature  
**Purpose:** SB vs BB 15bb with per-player antes  
**Key features:**
- Two-player preflop
- 50 SB, 100 BB, 10 ante per player
- Starting stacks 1,500 before forced bets
- Limp, raise, fold, call, all-in paths
- Bounded raise tree
- Chip-EV only (no ICM)

**Acceptance test:** Ante accounting exact, limp path exists, all-in legal, zero-sum

### 3. `examples/phase3_three_way_river.json`

**Owner:** Three-way postflop feature  
**Purpose:** Bounded three-player river with side pots  
**Key features:**
- Three players, unequal stacks
- Fixed five-card board
- One exact combo per player (no collisions)
- Declared pot/contribution ledger
- Fixed wager targets
- Rake disabled
- Exercises fold → two-player showdown and three-way showdown

**Acceptance test:** Side-pot arithmetic exact, payoff conservation, zero-sum after rake

### 4. `examples/phase3_three_way_river_rake.json`

**Owner:** Rake feature  
**Purpose:** Same as #3 with percentage+cap rake enabled  
**Key features:**
- 5% rake, 3-chip cap
- No-flop-no-drop disabled (river start)
- Floor rounding

**Acceptance test:** Rake deduction exact, player awards + rake = pot

### 5. `examples/phase3_ranges.json`

**Owner:** Range editor feature  
**Purpose:** Named range library with explicit combos  
**Key features:**
- At least two named ranges
- Explicit two-card combos with weights in [0,1]
- Lossless save/load round trip

**Acceptance test:** Import, export, reload byte-identical under canonical ordering

### 6. `examples/phase3_exploitative.json`

**Owner:** Nodelocking and profiles feature  
**Purpose:** Node lock and profile constraint example  
**Key features:**
- One canonical node ID
- Complete locked action distribution
- One explicit profile constraint set

**Acceptance test:** Locked policy preserved exactly, unlocked opponent BR matches brute-force

### 7. `examples/phase3_dynamic_sizing.json`

**Owner:** Bet sizing feature  
**Purpose:** Dynamic sizing with candidate subset selection  
**Key features:**
- 5 candidates, retain 3
- Exhaustive subset evaluation
- Deterministic tie-break

**Acceptance test:** Selected subset EV equals brute-force best subset

### 8. `examples/phase3_automatic_sizing.json`

**Owner:** Bet sizing feature  
**Purpose:** Automatic sizing with EV tolerance  
**Key features:**
- Generated candidate grid
- EV tolerance 0.001
- Smallest qualifying subset

**Acceptance test:** Selected subset within tolerance of full-tree EV

## Backward compatibility

### Version 1 (Phase 1)

- `solve-spot` with version 1 config: **unchanged**
- Uses vanilla CFR only
- Iterations from `--iterations` flag
- Output format preserved
- All existing tests pass

### Version 2 (Phase 2)

- `solve-multistreet` with version 2 config: **unchanged**
- Algorithm selection via `--algorithm` flag
- Seed via `--seed` flag
- Output format preserved
- All existing tests pass

### Version 3 (Phase 3)

- New `solve-preset` command for version 3 configs
- Version 1 and 2 configs **not accepted** by `solve-preset`
- Version 3 configs **not accepted** by `solve-spot` or `solve-multistreet`
- Clear error message directs user to correct command

### Migration path

No automatic migration tool is provided. Users must:

1. Keep version 1/2 configs for existing workflows
2. Manually author version 3 presets for new features
3. Use `validate-preset` to check version 3 syntax

## Smoke tests

All smoke tests must pass before Phase 3 acceptance.

### 1. Help and version

```bash
poker-solver --help
poker-solver solve-preset --help
poker-solver validate-preset --help
poker-solver range-edit --help
poker-solver range-table --help
poker-solver convert-sizing --help
poker-solver list-presets --help
```

**Expected:** Exit 0, usage text to stdout

### 2. Canonical preset loading

```bash
for preset in examples/phase3_*.json; do
  poker-solver validate-preset "$preset" --json || exit 1
done
```

**Expected:** All presets valid, exit 0

### 3. Determinism

```bash
poker-solver solve-preset examples/phase3_btn_vs_bb_25bb.json --json > out1.json
poker-solver solve-preset examples/phase3_btn_vs_bb_25bb.json --json > out2.json
diff out1.json out2.json
```

**Expected:** No diff, byte-identical output

### 4. Stdin input

```bash
cat examples/phase3_btn_vs_bb_25bb.json | poker-solver solve-preset - --json
```

**Expected:** Same output as file input

### 5. Invalid input rejection

```bash
echo '{"version": 3, "preset_id": "test", "kind": "invalid"}' | \
  poker-solver solve-preset - --json
```

**Expected:** Exit 2, error message to stderr

### 6. Unsupported engine mode

```bash
echo '{"version": 3, ..., "engine": {"mode": "fast-ddls", ...}}' | \
  poker-solver solve-preset - --json
```

**Expected:** Exit 2, message: `error: engine mode 'fast-ddls' is not supported`

### 7. Range round trip

```bash
poker-solver range-edit export examples/phase3_ranges.json --json > exported.json
poker-solver range-edit import exported.json --json > reimported.json
diff exported.json reimported.json
```

**Expected:** Byte-identical

### 8. Sizing conversion

```bash
poker-solver convert-sizing '{"unit":"pot-percent","value":75}' \
  --pot 100 --stack 200 --json
```

**Expected:** `{"target": 75, "legal": true, ...}`

### 9. Backward compatibility

```bash
poker-solver solve-kuhn --iterations 100 --json > kuhn_v1.json
poker-solver solve-spot examples/river_spot.json --iterations 100 --json > spot_v1.json
poker-solver solve-multistreet examples/multistreet_spot.json \
  --algorithm vanilla-cfr --iterations 100 --json > multi_v2.json
```

**Expected:** All exit 0, output format unchanged from Phase 1/2

### 10. Three-way zero-sum

```bash
poker-solver solve-preset examples/phase3_three_way_river.json --json | \
  jq '.values | add'
```

**Expected:** Sum within 1e-10 of zero

## CLI implementation checklist

- [ ] Add `solve-preset` subcommand parser
- [ ] Add `validate-preset` subcommand parser
- [ ] Add `range-edit` subcommand parser
- [ ] Add `range-table` subcommand parser
- [ ] Add `convert-sizing` subcommand parser
- [ ] Add `list-presets` subcommand parser
- [ ] Implement version 3 preset loader with strict validation
- [ ] Implement stdin `-` support for all config commands
- [ ] Implement `--output` file writing with atomic replace
- [ ] Add engine mode validation (reject `fast-ddls`)
- [ ] Add sizing mode validation and conversion
- [ ] Add range reference resolution
- [ ] Add node lock validation
- [ ] Add rake calculation
- [ ] Wire `solve-preset` to appropriate solver backend
- [ ] Wire `range-table` to strategy display module
- [ ] Wire `convert-sizing` to sizing conversion module
- [ ] Add all error messages from error table
- [ ] Preserve exit code semantics (0/1/2/130)
- [ ] Write CLI integration tests for all new commands
- [ ] Write smoke test suite
- [ ] Write backward compatibility regression tests
- [ ] Document all commands in `--help` text
- [ ] Update README.md CLI section (separate task, not this report)

## Review and acceptance

This design document must be reviewed by a non-author before any CLI implementation begins. The reviewer must:

1. Verify subcommand matrix completeness for all Phase 3 features
2. Check stdin/file/output conventions are consistent
3. Verify deterministic JSON contract matches existing Phase 1/2 conventions
4. Check error messages are actionable and exit codes are correct
5. Verify canonical preset example ownership is clear
6. Check backward compatibility claims against existing tests
7. Verify smoke tests cover critical paths
8. Sign off under `review/phase3/design/cli-examples-review.md`

No source, test, README, or PROGRESS.md edits are made by this design document. Implementation follows after review sign-off.
