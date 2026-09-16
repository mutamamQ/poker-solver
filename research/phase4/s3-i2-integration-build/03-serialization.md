# S3-I2 deterministic detached v4 response serialization requirements

**Analyst:** C3I2-IG3R (read-only serialization analyst)
**Scope:** Define exact deterministic detached JSON response contract for `solve-nplayer-preflop` v4 operation
**Sources:** `tests/test_api_v4_nplayer_preflop.py`, `tests/test_phase4_s3_examples.py`, `src/poker_solver/api_v4.py`, `src/poker_solver/nplayer_preflop.py`, S2 precedent
**Status:** Complete, parent-reconciled
**UTC:** 2026-09-16T09:45:42Z

---

## 1. Response envelope structure

### 1.1 Top-level required fields

Evidence: `tests/test_api_v4_nplayer_preflop.py` lines 116–132, 135–148

```python
response = dispatch_v4(request)
assert response["version"] == 4
assert response["operation"] == "solve-nplayer-preflop"
assert response["game_version"] == "nplayer-preflop-v1"
assert response["algorithm"] == "vanilla-cfr"
assert response["iterations"] == 2
assert response["seed"] is None
assert response["max_nodes"] == 1000
assert len(response["values"]) == 2
assert all(isinstance(v, float) for v in response["values"])
assert isinstance(response["strategy"], dict)
assert response["metadata"]["converged"] is False
assert response["metadata"]["convergence_claim"] == "none"
assert isinstance(response["provenance"], str)
assert response["approximate"] is False
```

**Required top-level fields:**
- `version`: integer 4
- `operation`: string "solve-nplayer-preflop"
- `config_version`: integer (test line 201: `assert result["config_version"] == 4`)
- `game_version`: string "nplayer-preflop-v1"
- `algorithm`: string (echoed from request)
- `iterations`: positive integer (echoed from request)
- `seed`: null (vanilla-cfr only)
- `max_nodes`: positive integer (echoed from request)
- `values`: list of N floats (zero-sum, finite)
- `strategy`: dict with string keys and dict values
- `metadata`: dict with at least `{"converged": false, "convergence_claim": "none"}`
- `provenance`: non-empty string
- `approximate`: boolean false

### 1.2 Nullable top-level field

Evidence: `tests/test_api_v4_nplayer_preflop.py` lines 74, 112 (certificate not tested in minimal fixtures)

- `certificate` is always present and is null or a deviation certificate object (when `include_deviation_certificate: true`).

---

## 2. Strategy serialization contract

### 2.1 Collision-free stable string keys

Evidence: `src/poker_solver/api_v4.py` lines 252–255 (S2 precedent):

```python
strategy = {
    str(key): {str(action): float(probability) for action, probability in policy.items()}
    for key, policy in result.strategy.items()
}
```

Evidence: `research/phase4/s3-design-audit-repair/05-solver-api-tdd.md` line 124:

> "The S2 dispatcher stringifies keys and actions. S3 information keys are tuples/frozen structures containing integers, tuples, and immutable sizing-rule/continuation identities (§9). Python's `str()` on these produces deterministic reprs. The S3 dispatcher must apply the same `str(key)` and `str(action)` pattern."

**Requirements:**
1. Information-set keys: apply `str(key)` where `key` is the hashable tuple returned by `NPlayerPreflopState.information_state_key(player)`
2. Action keys: apply `str(action)` where `action` is an `Action` instance
3. Python `str()` on tuples/frozen dataclasses produces deterministic repr strings
4. Within the declared S3 information-key/action domain, the architecture adopts the S2 `str()` encoding; arbitrary external objects are outside this collision claim.
5. Stability: identical requests produce identical string keys

### 2.2 Policy values

Evidence: `tests/test_api_v4_nplayer_preflop.py` lines 284–289:

```python
for policy in response["strategy"].values():
    assert sum(policy.values()) == pytest.approx(1.0, abs=1e-12)
assert sum(response["values"]) == pytest.approx(0.0, abs=1e-9)
```

**Requirements:**
1. Each policy is a dict mapping action strings to floats
2. Probabilities are non-negative floats
3. Probabilities sum to 1.0 per information set (within 1e-12 tolerance)
4. All probabilities are finite (no inf/nan)

---

## 3. Values serialization contract

### 3.1 Zero-sum finite float list

Evidence: `tests/test_api_v4_nplayer_preflop.py` lines 126–127, 144–145, 289:

```python
assert len(response["values"]) == 2
assert all(isinstance(v, float) for v in response["values"])
assert sum(response["values"]) == pytest.approx(0.0, abs=1e-9)
```

Evidence: `tests/test_phase4_s3_examples.py` lines 100–101, 122, 142, 206:

```python
assert len(data["values"]) == 2
assert abs(data["values"][0] + data["values"][1]) < 1e-9
assert abs(sum(data["values"])) < 1e-9
```

**Requirements:**
1. `values` is a list of exactly N floats (N = num_players)
2. All values are finite (no inf/nan)
3. Values sum to zero (within 1e-9 tolerance)
4. Conversion: `list(result.expected_values)` where `expected_values` is a tuple of floats

### 3.2 Finite enforcement

Evidence: `src/poker_solver/api_v4.py` lines 469–474 (S2 precedent):

```python
def serialize_values(values: tuple[float, float]) -> list[float]:
    """Convert the zero-sum value vector to a JSON-safe list."""
    v0, v1 = values
    if not isfinite(v0) or not isfinite(v1):
        raise ValueError(f"non-finite value vector: ({v0}, {v1})")
    return [float(v0), float(v1)]
```

**Requirement:** S3 dispatcher must validate finite values before serialization

---

## 4. Certificate serialization contract (optional)

Evidence: `src/poker_solver/api_v4.py` lines 256–264 (S2 precedent):

```python
certificate = None
if result.certificate is not None:
    certificate = {
        "values": list(result.certificate.values),
        "best_response_values": list(result.certificate.best_response_values),
        "incentives": list(result.certificate.incentives),
        "total_incentive": float(result.certificate.total_incentive),
        "provenance": result.certificate.provenance,
    }
```

**Requirements (when present):**
1. `certificate` is null or a dict with exactly these fields:
   - `values`: list of N floats
   - `best_response_values`: list of N floats
   - `incentives`: list of N floats
   - `total_incentive`: float
   - `provenance`: string
2. All numeric values are finite

---

## 5. Metadata contract

Evidence: `tests/test_api_v4_nplayer_preflop.py` lines 129–130:

```python
assert response["metadata"]["converged"] is False
assert response["metadata"]["convergence_claim"] == "none"
```

Evidence: `tests/test_phase4_s3_examples.py` lines 103, 124, 145:

```python
assert data["metadata"]["converged"] is False
```

Evidence: `src/poker_solver/nplayer_preflop.py` lines 1123–1133:

```python
metadata={
    "converged": False,
    "convergence_claim": "none",
    "deterministic": True,
    "deviation_certificate": (
        "exhaustive-diagnostic-only"
        if include_deviation_certificate
        else "not-requested"
    ),
},
```

**Required metadata fields:**
- `converged`: boolean false
- `convergence_claim`: string "none"
- `deterministic`: boolean true
- `deviation_certificate`: string ("exhaustive-diagnostic-only" or "not-requested")

**Requirement:** Metadata must be JSON-serializable dict; nested containers allowed

---

## 6. Provenance contract

Evidence: `tests/test_api_v4_nplayer_preflop.py` line 131:

```python
assert isinstance(response["provenance"], str)
```

Evidence: `src/poker_solver/nplayer_preflop.py` line 1134:

```python
provenance="full-tree deterministic vanilla CFR; no convergence guarantee",
```

**Requirement:** Non-empty string describing solver method and limitations

---

## 7. Approximate flag contract

Evidence: `tests/test_api_v4_nplayer_preflop.py` line 132, 148:

```python
assert response["approximate"] is False
```

Evidence: `tests/test_phase4_s3_examples.py` lines 207, 228, 249:

```python
assert result["approximate"] is False
```

**Requirement:** Boolean false (S3 is exact finite tree)

---

## 8. Determinism and detachment contract

### 8.1 Deterministic repeat calls

Evidence: `tests/test_api_v4_nplayer_preflop.py` lines 151–159:

```python
def test_response_is_deterministic_and_detached() -> None:
    payload = _payload_terminal_table()
    first = dispatch_v4(_request(payload))
    second = dispatch_v4(_request(payload))
    assert first == second
    first["values"].append(999.0)
    first["metadata"]["converged"] = True
    first["strategy"]["mutated"] = {"CHECK": 1.0}
    assert dispatch_v4(_request(payload)) == second
```

**Requirements:**
1. Identical requests produce identical responses (deep equality)
2. Mutating a response does not affect subsequent calls
3. Response containers (lists, dicts) are fresh copies, not shared references

### 8.2 Detachment implementation

Evidence: `src/poker_solver/nplayer_preflop.py` lines 1073–1077:

```python
def __post_init__(self) -> None:
    object.__setattr__(self, "strategy", MappingProxyType({
        key: MappingProxyType(dict(policy))
        for key, policy in self.strategy.items()
    }))
```

Evidence: `src/poker_solver/api_v4.py` lines 252–255, 276:

```python
strategy = {
    str(key): {str(action): float(probability) for action, probability in policy.items()}
    for key, policy in result.strategy.items()
}
return {
    "values": list(result.expected_values),
    "strategy": strategy,
    ...
}
```

**Requirements:**
1. Strategy: deep copy via dict comprehension with `str()` conversion
2. Values: fresh list via `list(tuple)`
3. Metadata: fresh dict via `dict(result.metadata)` (S2 line 278); the declared S3 metadata is flat
4. Certificate: fresh dict with list conversions (S2 lines 258–264)
5. No shared mutable references between result object and response dict

---

## 9. Normalization requirements

### 9.1 Strategy normalization

Evidence: `tests/test_phase4_s3_examples.py` lines 253–266:

```python
def test_example_strategies_normalized():
    """All example strategies are normalized and finite."""
    for player_count in [2, 6, 9]:
        result = dispatch_v4(request)
        assert result["strategy"]
        for policy in result["strategy"].values():
            assert policy
            assert all(isinstance(p, (int, float)) and p >= 0 for p in policy.values())
            assert abs(sum(policy.values()) - 1.0) < 1e-9
```

**Requirements:**
1. Every policy dict is non-empty
2. Every probability is a non-negative number
3. Probabilities sum to 1.0 per information set (within 1e-9)
4. All probabilities are finite

### 9.2 Finite enforcement

Evidence: `tests/test_api_v4_nplayer_preflop.py` lines 202–207:

```python
@pytest.mark.parametrize("value", [inf, nan])
def test_nonfinite_numeric_fields_are_rejected(value: float) -> None:
    payload = _payload_terminal_table()
    payload["continuation"]["entries"][0]["values"][0] = value
    with pytest.raises(ValueError, match="finite"):
        dispatch_v4(_request(payload))
```

**Requirement:** Input validation rejects non-finite values; output must also be finite

---

## 10. Mutation isolation requirement

Evidence: `tests/test_api_v4_nplayer_preflop.py` lines 156–159:

```python
first["values"].append(999.0)
first["metadata"]["converged"] = True
first["strategy"]["mutated"] = {"CHECK": 1.0}
assert dispatch_v4(_request(payload)) == second
```

**Requirements:**
1. Mutating response `values` list does not affect internal state
2. Mutating response `metadata` dict does not affect internal state
3. Mutating response `strategy` dict does not affect internal state
4. Each call returns independent mutable containers

---

## 11. S2 serialization precedent

Evidence: `src/poker_solver/api_v4.py` lines 252–281 (S2 `_dispatch_nplayer_postflop`):

```python
strategy = {
    str(key): {str(action): float(probability) for action, probability in policy.items()}
    for key, policy in result.strategy.items()
}
certificate = None
if result.certificate is not None:
    certificate = {
        "values": list(result.certificate.values),
        "best_response_values": list(result.certificate.best_response_values),
        "incentives": list(result.certificate.incentives),
        "total_incentive": float(result.certificate.total_incentive),
        "provenance": result.certificate.provenance,
    }
return {
    "version": 4,
    "operation": "solve-nplayer-postflop",
    "config_version": result.config_version,
    "game_version": result.game_version,
    "algorithm": result.algorithm,
    "iterations": result.iterations,
    "seed": None,
    "max_nodes": result.max_nodes,
    "max_depth": result.max_depth,
    "strategy": strategy,
    "values": list(result.expected_values),
    "certificate": certificate,
    "metadata": dict(result.metadata),
    "provenance": result.provenance,
    "approximate": result.approximate,
}
```

**S3 must follow identical pattern:**
1. Stringify keys and actions via `str()`
2. Convert values tuple to list via `list()`
3. Copy the declared flat metadata into a fresh dict via `dict()`
4. Conditionally serialize certificate with list conversions
5. Return fresh dict with no shared mutable references

---

## 12. Implementation checklist for S3-I2 integration owner

### 12.1 Response construction

```python
def _dispatch_nplayer_preflop(payload_value: Any) -> dict[str, Any]:
    # ... payload parsing and validation ...

    result = solve_nplayer_preflop(
        config,
        algorithm=algorithm,
        iterations=iterations,
        include_deviation_certificate=include_certificate,
        max_pure_strategies=max_pure_strategies,
    )

    # Serialize strategy with string keys
    strategy = {
        str(key): {str(action): float(probability) for action, probability in policy.items()}
        for key, policy in result.strategy.items()
    }

    # Serialize optional certificate
    certificate = None
    if result.certificate is not None:
        certificate = {
            "values": list(result.certificate.values),
            "best_response_values": list(result.certificate.best_response_values),
            "incentives": list(result.certificate.incentives),
            "total_incentive": float(result.certificate.total_incentive),
            "provenance": result.certificate.provenance,
        }

    # Return detached response
    return {
        "version": 4,
        "operation": "solve-nplayer-preflop",
        "config_version": result.config_version,
        "game_version": result.game_version,
        "algorithm": result.algorithm,
        "iterations": result.iterations,
        "seed": None,
        "max_nodes": result.max_nodes,
        "max_depth": result.max_depth,
        "strategy": strategy,
        "values": list(result.expected_values),
        "certificate": certificate,
        "metadata": dict(result.metadata),
        "provenance": result.provenance,
        "approximate": result.approximate,
    }
```

### 12.2 Routing in dispatch_v4

Add after line 333 in `src/poker_solver/api_v4.py`:

```python
if operation == "solve-nplayer-preflop":
    return _dispatch_nplayer_preflop(request["payload"])
```

### 12.3 Validation requirements

1. Validate `result.expected_values` are all finite before serialization
2. Validate `result.strategy` policies sum to 1.0 (within tolerance)
3. Validate `result.metadata` is JSON-serializable
4. Validate `result.approximate` is boolean false
5. Validate `result.provenance` is non-empty string

---

## 13. Summary

**Deterministic detached v4 response contract for `solve-nplayer-preflop`:**

1. **Envelope:** 15 required top-level fields (version, operation, config_version, game_version, algorithm, iterations, seed, max_nodes, max_depth, strategy, values, certificate, metadata, provenance, approximate)

2. **Strategy:** String keys via `str(information_state_key)`, string action keys via `str(action)`, normalized finite float probabilities summing to 1.0 per infoset

3. **Values:** List of N finite floats summing to zero (within 1e-9)

4. **Certificate:** Null or dict with 5 fields (values, best_response_values, incentives, total_incentive, provenance), all finite

5. **Metadata:** Dict with at least {converged: false, convergence_claim: "none", deterministic: true, deviation_certificate: string}

6. **Provenance:** Non-empty string describing solver method

7. **Approximate:** Boolean false

8. **Determinism:** Identical requests produce identical responses (deep equality)

9. **Detachment:** Response containers are fresh copies; mutations do not affect internal state or subsequent calls

10. **Normalization:** All probabilities finite, non-negative, sum to 1.0; all values finite and zero-sum

11. **S2 precedent:** Follow identical serialization pattern (stringify keys/actions, list conversions, dict copy, conditional certificate)

**No blockers.** All requirements resolved from literal test evidence and S2 precedent.

---

**Analyst:** C3I2-IG3R
**Status:** Complete, parent-reconciled
**UTC:** 2026-09-16T09:45:42Z
