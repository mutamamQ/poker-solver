# Phase 2 API and CLI integration design

## Overview

This document specifies the programmatic JSON API and CLI integration for the poker-solver project. It defines strict schemas, algorithm selection, exploitability commands, JSON input/output shapes, deterministic ordering, backward compatibility, error handling, and acceptance tests.

## Version 2 spot schema

### Strict JSON schema

```json
{
  "version": 2,
  "board": ["2c", "3d", "4h", "9s", "Kc"],
  "pot": 2.0,
  "stack": 100,
  "bet": 50,
  "range0": [
    {"cards": ["As", "5s"], "weight": 1.0},
    {"cards": ["Qs", "Js"], "weight": 0.5}
  ],
  "range1": [
    {"cards": ["Kh", "Qh"], "weight": 1.0},
    {"cards": ["9h", "8h"], "weight": 1.0}
  ],
  "algorithm": "external-sampling-mccfr",
  "seed": 42,
  "iterations": 10000
}
```

### Field specifications

- `version`: JSON integer, must equal 2
- `board`: array of 5 card strings (river), 4 (turn), 3 (flop), or 0 (preflop); each card is rank+suit ("As", "Kc", etc.)
- `pot`: JSON number (float), finite and positive
- `stack`: JSON integer, positive
- `bet`: JSON integer, positive, <= stack
- `range0`, `range1`: nonempty arrays of combo objects
  - `cards`: array of exactly 2 card strings
  - `weight`: JSON number (float), finite, nonnegative
- `algorithm`: optional string, one of `"vanilla-cfr"` or `"external-sampling-mccfr"`; defaults to `"vanilla-cfr"`
- `seed`: optional JSON integer for MCCFR; required when algorithm is `"external-sampling-mccfr"`; ignored for vanilla CFR
- `iterations`: optional JSON integer, positive; defaults to 20000

### Type validation rules

- JSON integers must be `int` type, not `bool`, not `float`
- JSON numbers must be `int` or `float`, not `bool`
- Reject `true`/`false` for numeric fields with error: `"{field} must be a JSON integer"` or `"{field} must be a JSON number"`
- Card strings must parse via existing `parse_card` function
- All cards across board and ranges must be unique (no collisions)

### Backward compatibility: version 1

Version 1 schema (existing `solve-spot` command) remains supported:

```json
{
  "version": 1,
  "board": ["2c", "3d", "4h", "9s", "Kc"],
  "pot": 2,
  "stack": 1,
  "bet": 1,
  "range0": [{"cards": ["As", "5s"], "weight": 1}],
  "range1": [{"cards": ["Kh", "Qh"], "weight": 1}]
}
```

- Version 1 uses vanilla CFR only
- Algorithm and seed fields are not present
- Iterations come from CLI `--iterations` flag
- Version 1 files continue to work with `solve-spot` command

## Algorithm selection

### CLI flags

```bash
# Vanilla CFR (deterministic, default)
poker-solver solve-spot config.json --iterations 10000 --json

# External-sampling MCCFR (requires seed)
poker-solver solve-spot config.json --algorithm external-sampling-mccfr --seed 42 --iterations 10000 --json

# Algorithm in file overrides CLI flag
poker-solver solve-spot config-v2.json --json
```

### Selection priority

1. If config version is 2 and `algorithm` field is present, use that algorithm
2. Else if CLI `--algorithm` flag is present, use that
3. Else default to `"vanilla-cfr"`

### Seed handling

- MCCFR requires a seed: if algorithm is `"external-sampling-mccfr"` and no seed is provided (neither in file nor via `--seed` flag), raise error: `"external-sampling-mccfr requires a seed"`
- Vanilla CFR ignores seed if provided
- Seed must be a JSON integer (not bool, not float)

## Exploitability command

### New command: `exploitability`

```bash
poker-solver exploitability strategy.json spot.json --json
```

### Input: strategy.json

Strategy file contains the output from a previous `solve-spot` or `solve-kuhn` run, or a manually constructed strategy:

```json
{
  "version": 1,
  "strategy": {
    "('river-v1', 0, (0, 1), (2, 3, 4, 5, 6), (), 2, 1, 1)": {
      "check": 0.6,
      "bet:1": 0.4
    }
  }
}
```

- `version`: must be 1
- `strategy`: dict mapping information-set-key repr strings to action-policy dicts
- Action keys are `"check"`, `"fold"`, `"call"`, or `"bet:N"` / `"raise:N"` where N is the amount

### Input: spot.json

Spot file is a version 1 or 2 spot config (same as `solve-spot` input).

### Output

```json
{
  "values": [0.123, -0.123],
  "best_response_values": [0.456, 0.234],
  "incentives": [0.333, 0.357],
  "nash_conv": 0.690,
  "exploitability_half_nash_conv": 0.345
}
```

- `values`: 2-element array of player 0 and player 1 expected values under the given strategy
- `best_response_values`: 2-element array of best-response values for each player
- `incentives`: 2-element array of `BR_i - u_i(sigma)` for each player
- `nash_conv`: sum of incentives (nonnegative)
- `exploitability_half_nash_conv`: `nash_conv / 2`

### Error cases

- Strategy file missing or malformed: `"error: invalid strategy file"`
- Spot file missing or malformed: `"error: invalid spot config"`
- Strategy does not cover all information sets in spot: `"error: missing policy for information set ..."`
- Strategy probabilities do not sum to 1.0 (tolerance 1e-10): `"error: probabilities do not sum to one at ..."`
- Negative NashConv (indicates bug): `"error: negative NashConv indicates a best-response bug"`

## JSON input modes

### File input (existing)

```bash
poker-solver solve-spot config.json --json
```

### Stdin input (new)

```bash
echo '{"version": 1, ...}' | poker-solver solve-spot --stdin --json
cat config.json | poker-solver solve-spot --stdin --json
```

- `--stdin` flag reads JSON from stdin instead of a file path
- Applies to `solve-spot` and `exploitability` commands
- For `exploitability`, use `--stdin-strategy` and `--stdin-spot` to read both from stdin as a combined object:

```bash
echo '{"strategy": {...}, "spot": {...}}' | poker-solver exploitability --stdin --json
```

Or provide one via stdin and one via file:

```bash
cat strategy.json | poker-solver exploitability --stdin-strategy spot.json --json
```

## JSON output shapes

### evaluate command

```json
{
  "cards": ["As", "Ks", "Qs", "Js", "Ts"],
  "category": "straight-flush",
  "rank": [8, 14, 13, 12, 11, 10]
}
```

### equity command

```json
{
  "equity": 0.8181818181818182,
  "losses": 0,
  "ties": 0,
  "total": 1,
  "wins": 1
}
```

### solve-kuhn command

```json
{
  "algorithm": "vanilla-cfr",
  "exploitability_half_nash_conv": 0.0012,
  "iterations": 1000,
  "known_value_p0": -0.05555555555555555,
  "nash_conv": 0.0024,
  "strategy": {
    "('J', 0)": {"bet:1": 0.4, "check": 0.6},
    "('K', 0)": {"bet:1": 1.0, "check": 0.0}
  },
  "values": [-0.054, 0.054]
}
```

### solve-spot command (version 1)

```json
{
  "algorithm": "vanilla-cfr",
  "exploitability_half_nash_conv": 0.0234,
  "iterations": 1000,
  "nash_conv": 0.0468,
  "strategy": {
    "('river-v1', 0, (0, 1), (2, 3, 4, 5, 6), (), 2, 1, 1)": {
      "bet:1": 0.35,
      "check": 0.65
    }
  },
  "values": [0.0001, -0.0001]
}
```

### solve-spot command (version 2 with MCCFR)

```json
{
  "algorithm": "external-sampling-mccfr",
  "exploitability_half_nash_conv": 0.0456,
  "iterations": 10000,
  "nash_conv": 0.0912,
  "seed": 42,
  "strategy": {
    "('river-v1', 0, (0, 1), (2, 3, 4, 5, 6), (), 2, 1, 1)": {
      "bet:1": 0.38,
      "check": 0.62
    }
  },
  "values": [0.0023, -0.0023]
}
```

### exploitability command

(See "Exploitability command" section above.)

## Deterministic ordering and hashes

### JSON serialization

- Use `json.dumps(data, sort_keys=True, separators=(',', ':'), allow_nan=False)`
- Sorted keys ensure deterministic field order
- Compact separators remove whitespace
- `allow_nan=False` rejects NaN/Infinity

### Strategy dict ordering

- Information set keys: sort by `repr(key)`
- Actions within a policy: sort by `Action` natural order (dataclass with `order=True`)
- Existing `_strategy_json` function already implements this

### Determinism guarantees

- Vanilla CFR with same input produces byte-identical JSON output
- MCCFR with same seed/input/iterations produces byte-identical JSON output locally (same Python interpreter)
- Cross-platform byte identity is not guaranteed due to floating-point differences
- Numerical agreement uses explicit tolerances (not byte comparison)

### Hash verification

```bash
poker-solver solve-kuhn --iterations 100 --json | sha256sum
poker-solver solve-kuhn --iterations 100 --json | sha256sum
# Both hashes must match
```

## Backward compatibility

### Existing commands unchanged

- `evaluate`: no changes
- `equity`: no changes
- `solve-kuhn`: no changes (always vanilla CFR)
- `solve-spot` with version 1 config: no changes

### Version 1 spot files

- Continue to work with `solve-spot` command
- Use vanilla CFR
- Iterations from `--iterations` flag
- Output format unchanged

### Version 2 spot files

- Require `"version": 2` field
- Support `algorithm` and `seed` fields
- Backward-compatible: version 2 files with `"algorithm": "vanilla-cfr"` produce same results as version 1 (modulo the version field in output)

### Migration path

1. Version 1 files remain valid indefinitely
2. New features (MCCFR, multi-street) require version 2
3. Tools can detect version and handle both
4. Version 2 is a superset: all version 1 configs can be expressed in version 2

## Error handling and limits

### Validation errors (exit code 2)

- `"error: {field} must be a JSON integer"` - type mismatch
- `"error: {field} must be a JSON number"` - type mismatch
- `"error: spot config requires exactly {fields} and version {N}"` - missing/extra fields
- `"error: spot board must contain five card strings"` - wrong board size for river
- `"error: each combo must be an object"` - range item not a dict
- `"error: each combo requires exactly cards and weight fields"` - wrong combo fields
- `"error: combo cards must be a two-item list"` - wrong cards array size
- `"error: combo weight must be finite and nonnegative"` - invalid weight
- `"error: iterations must be positive"` - non-positive iterations
- `"error: external-sampling-mccfr requires a seed"` - missing seed for MCCFR
- `"error: unknown algorithm: {name}"` - invalid algorithm name
- `"error: seed must be a JSON integer"` - seed type mismatch

### Runtime errors (exit code 2)

- `"error: ranges have no compatible positive-weight deals"` - all combos blocked
- `"error: invalid river history: {history}"` - internal game-tree bug
- `"error: negative NashConv indicates a best-response bug"` - internal BR bug

### File errors (exit code 2)

- `"error: [Errno 2] No such file or directory: '{path}'"` - file not found
- `"error: Expecting value: line 1 column 1 (char 0)"` - JSON parse error

### Limits

- Maximum iterations: no hard limit, but vanilla CFR on large games will be slow
- Maximum range size: no hard limit, but memory/time grow with range product
- Maximum board size: 5 cards (river)
- Minimum board size: 0 cards (preflop, future)
- Players: exactly 2 (heads-up)
- Seed range: any valid JSON integer (Python `int`)

### Exit codes

- `0`: success
- `2`: validation or runtime error (printed to stderr)

## Acceptance test cases

### Test 1: Version 2 vanilla CFR spot

```python
def test_solve_spot_v2_vanilla(tmp_path, capsys):
    config = {
        "version": 2,
        "board": ["2c", "3d", "4h", "9s", "Kc"],
        "pot": 2.0,
        "stack": 1,
        "bet": 1,
        "range0": [{"cards": ["As", "5s"], "weight": 1.0}],
        "range1": [{"cards": ["Kh", "Qh"], "weight": 1.0}],
        "algorithm": "vanilla-cfr",
        "iterations": 100
    }
    path = tmp_path / "spot_v2.json"
    path.write_text(json.dumps(config))
    assert main(["solve-spot", str(path), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["algorithm"] == "vanilla-cfr"
    assert data["iterations"] == 100
    assert "seed" not in data
    assert data["nash_conv"] >= 0
```

### Test 2: Version 2 MCCFR with seed

```python
def test_solve_spot_v2_mccfr(tmp_path, capsys):
    config = {
        "version": 2,
        "board": ["2c", "3d", "4h", "9s", "Kc"],
        "pot": 2.0,
        "stack": 1,
        "bet": 1,
        "range0": [{"cards": ["As", "5s"], "weight": 1.0}],
        "range1": [{"cards": ["Kh", "Qh"], "weight": 1.0}],
        "algorithm": "external-sampling-mccfr",
        "seed": 42,
        "iterations": 100
    }
    path = tmp_path / "spot_v2_mccfr.json"
    path.write_text(json.dumps(config))
    assert main(["solve-spot", str(path), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["algorithm"] == "external-sampling-mccfr"
    assert data["seed"] == 42
    assert data["iterations"] == 100
    assert data["nash_conv"] >= 0
```

### Test 3: MCCFR determinism

```python
def test_mccfr_determinism(tmp_path, capsys):
    config = {
        "version": 2,
        "board": ["2c", "3d", "4h", "9s", "Kc"],
        "pot": 2.0,
        "stack": 1,
        "bet": 1,
        "range0": [{"cards": ["As", "5s"], "weight": 1.0}],
        "range1": [{"cards": ["Kh", "Qh"], "weight": 1.0}],
        "algorithm": "external-sampling-mccfr",
        "seed": 123,
        "iterations": 50
    }
    path = tmp_path / "spot_mccfr.json"
    path.write_text(json.dumps(config))
    assert main(["solve-spot", str(path), "--json"]) == 0
    first = capsys.readouterr().out
    assert main(["solve-spot", str(path), "--json"]) == 0
    second = capsys.readouterr().out
    assert first == second
```

### Test 4: MCCFR missing seed error

```python
def test_mccfr_missing_seed_error(tmp_path, capsys):
    config = {
        "version": 2,
        "board": ["2c", "3d", "4h", "9s", "Kc"],
        "pot": 2.0,
        "stack": 1,
        "bet": 1,
        "range0": [{"cards": ["As", "5s"], "weight": 1.0}],
        "range1": [{"cards": ["Kh", "Qh"], "weight": 1.0}],
        "algorithm": "external-sampling-mccfr",
        "iterations": 50
    }
    path = tmp_path / "spot_no_seed.json"
    path.write_text(json.dumps(config))
    assert main(["solve-spot", str(path), "--json"]) == 2
    assert "external-sampling-mccfr requires a seed" in capsys.readouterr().err
```

### Test 5: Version 2 strict numeric validation

```python
def test_v2_strict_numeric_types(tmp_path, capsys):
    # Boolean rejected for integer field
    config = {
        "version": 2,
        "board": ["2c", "3d", "4h", "9s", "Kc"],
        "pot": 2.0,
        "stack": True,
        "bet": 1,
        "range0": [{"cards": ["As", "5s"], "weight": 1.0}],
        "range1": [{"cards": ["Kh", "Qh"], "weight": 1.0}]
    }
    path = tmp_path / "bad_stack.json"
    path.write_text(json.dumps(config))
    assert main(["solve-spot", str(path), "--json"]) == 2
    assert "stack must be a JSON integer" in capsys.readouterr().err

    # String rejected for number field
    config["stack"] = 1
    config["range0"][0]["weight"] = "1.0"
    path.write_text(json.dumps(config))
    assert main(["solve-spot", str(path), "--json"]) == 2
    assert "combo weight must be a JSON number" in capsys.readouterr().err
```

### Test 6: Backward compatibility version 1

```python
def test_v1_backward_compat(tmp_path, capsys):
    config = {
        "version": 1,
        "board": ["2c", "3d", "4h", "9s", "Kc"],
        "pot": 2,
        "stack": 1,
        "bet": 1,
        "range0": [{"cards": ["As", "5s"], "weight": 1}],
        "range1": [{"cards": ["Kh", "Qh"], "weight": 1}]
    }
    path = tmp_path / "spot_v1.json"
    path.write_text(json.dumps(config))
    assert main(["solve-spot", str(path), "--iterations", "100", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["algorithm"] == "vanilla-cfr"
    assert data["iterations"] == 100
    assert "seed" not in data
```

### Test 7: Exploitability command (stub)

```python
def test_exploitability_command(tmp_path, capsys):
    # Solve a spot first
    spot_config = {
        "version": 1,
        "board": ["2c", "3d", "4h", "9s", "Kc"],
        "pot": 2,
        "stack": 1,
        "bet": 1,
        "range0": [{"cards": ["As", "5s"], "weight": 1}],
        "range1": [{"cards": ["Kh", "Qh"], "weight": 1}]
    }
    spot_path = tmp_path / "spot.json"
    spot_path.write_text(json.dumps(spot_config))
    assert main(["solve-spot", str(spot_path), "--iterations", "100", "--json"]) == 0
    solve_output = json.loads(capsys.readouterr().out)
    
    # Extract strategy and save to file
    strategy_config = {
        "version": 1,
        "strategy": solve_output["strategy"]
    }
    strategy_path = tmp_path / "strategy.json"
    strategy_path.write_text(json.dumps(strategy_config))
    
    # Run exploitability command
    assert main(["exploitability", str(strategy_path), str(spot_path), "--json"]) == 0
    exploit_data = json.loads(capsys.readouterr().out)
    assert "nash_conv" in exploit_data
    assert "exploitability_half_nash_conv" in exploit_data
    assert exploit_data["nash_conv"] >= 0
    assert abs(exploit_data["exploitability_half_nash_conv"] - exploit_data["nash_conv"] / 2.0) < 1e-9
```

### Test 8: Unknown algorithm error

```python
def test_unknown_algorithm_error(tmp_path, capsys):
    config = {
        "version": 2,
        "board": ["2c", "3d", "4h", "9s", "Kc"],
        "pot": 2.0,
        "stack": 1,
        "bet": 1,
        "range0": [{"cards": ["As", "5s"], "weight": 1.0}],
        "range1": [{"cards": ["Kh", "Qh"], "weight": 1.0}],
        "algorithm": "cfr-plus",
        "iterations": 50
    }
    path = tmp_path / "bad_algo.json"
    path.write_text(json.dumps(config))
    assert main(["solve-spot", str(path), "--json"]) == 2
    assert "unknown algorithm" in capsys.readouterr().err.lower()
```

## Implementation notes

### CLI changes required

1. Add `--algorithm` and `--seed` flags to `solve-spot` parser
2. Add `--stdin` flag to `solve-spot` parser
3. Add new `exploitability` subcommand with strategy and spot file arguments
4. Extend `_load_spot` to handle version 2 schema
5. Add algorithm selection logic in `run` function
6. Add seed validation for MCCFR
7. Update output to include `seed` field when MCCFR is used

### New modules/functions

- `MCCFRSolver` class in `cfr.py` or new `mccfr.py` module
- External-sampling MCCFR implementation following OpenSpiel reference
- Strategy file loader/validator for `exploitability` command
- Stdin JSON reader utility

### Testing strategy

- Add all acceptance tests to `tests/test_cli.py`
- Run tests with `pytest tests/test_cli.py -v`
- Verify determinism with hash checks
- Cross-validate MCCFR against vanilla CFR on small games
- Measure performance on fixed fixtures

## References

- Existing CLI implementation: `src/poker_solver/cli.py`
- Existing tests: `tests/test_cli.py`
- CFR implementation: `src/poker_solver/cfr.py`
- Best response: `src/poker_solver/best_response.py`
- River game model: `src/poker_solver/river.py`
- Phase 2 research: `research/phase2/*.md`
- MCCFR paper: https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html
- OpenSpiel MCCFR: https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/python/algorithms/external_sampling_mccfr.py
