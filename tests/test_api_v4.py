"""Strict version-4 API contract tests for all-street postflop solve."""

import json
import math

import pytest

from poker_solver.api_v4 import dispatch_v4


def request(operation, payload):
    """Build a version-4 envelope."""
    return {"version": 4, "operation": operation, "payload": payload}


def minimal_allstreet_payload():
    """Minimal valid all-street postflop payload with flat schema."""
    return {
        "version": "allstreet-postflop-v1",
        "starting_board": [0, 1, 2],
        "initial_dead_pot": 100,
        "effective_stack": 500,
        "player0_combos": [{"cards": [3, 4], "weight": 1.0}],
        "player1_combos": [{"cards": [5, 6], "weight": 1.0}],
        "allowed_runouts": [[7, 8], [7, 9]],
        "betting_mode": "no-limit",
        "wager_targets": [100],
        "max_nodes": 100000,
        "max_depth": 512,
        "algorithm": "vanilla-cfr",
        "iterations": 10,
        "seed": None,
    }


def test_canonical_end_to_end_solve():
    """Canonical solve returns valid result with correct metadata."""
    payload = minimal_allstreet_payload()
    result = dispatch_v4(request("solve-allstreet-postflop", payload))
    
    assert result["config_version"] == 4
    assert result["game_version"] == "allstreet-postflop-v1"
    assert result["starting_street"] == "flop"
    assert result["continuation"] == "automatic-natural-terminal"
    assert result["algorithm"] == "vanilla-cfr"
    assert result["iterations"] == 10
    assert result["seed"] is None
    assert "strategy" in result
    assert "exploitability" in result or "nashconv" in result


def test_deterministic_vanilla_cfr_produces_identical_copies():
    """Repeated vanilla CFR runs produce exactly equal results."""
    payload = minimal_allstreet_payload()
    result1 = dispatch_v4(request("solve-allstreet-postflop", payload))
    result2 = dispatch_v4(request("solve-allstreet-postflop", payload))
    
    assert result1 == result2
    # Verify response isolation: mutating one doesn't affect the other
    if "strategy" in result1 and isinstance(result1["strategy"], dict):
        original_keys = set(result1["strategy"].keys())
        result1["strategy"]["__mutated__"] = True
        assert "__mutated__" not in result2["strategy"]
        assert set(result2["strategy"].keys()) == original_keys


def test_deterministic_mccfr_with_same_seed():
    """MCCFR with same seed produces exactly equal results."""
    payload = minimal_allstreet_payload()
    payload["algorithm"] = "external-sampling-mccfr"
    payload["seed"] = 42
    
    result1 = dispatch_v4(request("solve-allstreet-postflop", payload))
    result2 = dispatch_v4(request("solve-allstreet-postflop", payload))
    
    assert result1 == result2
    assert result1["seed"] == 42


def test_unknown_top_level_field_rejected():
    """Unknown fields in the envelope are rejected."""
    bad_request = {
        "version": 4,
        "operation": "solve-allstreet-postflop",
        "payload": minimal_allstreet_payload(),
        "unknown_field": "should_fail",
    }
    with pytest.raises((ValueError, KeyError, TypeError)):
        dispatch_v4(bad_request)


def test_unknown_payload_field_rejected():
    """Unknown fields in the payload are rejected."""
    payload = minimal_allstreet_payload()
    payload["unknown_payload_field"] = "should_fail"
    with pytest.raises((ValueError, KeyError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_missing_required_envelope_field():
    """Missing required envelope fields are rejected."""
    with pytest.raises((ValueError, KeyError, TypeError)):
        dispatch_v4({"version": 4, "payload": minimal_allstreet_payload()})
    
    with pytest.raises((ValueError, KeyError, TypeError)):
        dispatch_v4({"operation": "solve-allstreet-postflop", "payload": minimal_allstreet_payload()})


def test_missing_required_payload_field():
    """Missing required payload fields are rejected."""
    payload = minimal_allstreet_payload()
    del payload["algorithm"]
    with pytest.raises((ValueError, KeyError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))
    
    payload = minimal_allstreet_payload()
    del payload["iterations"]
    with pytest.raises((ValueError, KeyError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_missing_required_config_field():
    """Missing required config fields are rejected."""
    payload = minimal_allstreet_payload()
    del payload["starting_board"]
    with pytest.raises((ValueError, KeyError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))
    
    payload = minimal_allstreet_payload()
    del payload["player0_combos"]
    with pytest.raises((ValueError, KeyError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_bool_as_int_rejected_for_numeric_fields():
    """Boolean values are rejected for numeric fields."""
    payload = minimal_allstreet_payload()
    payload["iterations"] = True
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))
    
    payload = minimal_allstreet_payload()
    payload["effective_stack"] = False
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_nonfinite_weight_rejected():
    """Non-finite weights (inf, -inf, nan) are rejected."""
    payload = minimal_allstreet_payload()
    payload["player0_combos"] = [{"cards": [3, 4], "weight": float('inf')}]
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))
    
    payload = minimal_allstreet_payload()
    payload["player1_combos"] = [{"cards": [5, 6], "weight": float('nan')}]
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))
    
    payload = minimal_allstreet_payload()
    payload["player0_combos"] = [{"cards": [3, 4], "weight": float('-inf')}]
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_negative_weight_rejected():
    """Negative weights are rejected."""
    payload = minimal_allstreet_payload()
    payload["player0_combos"] = [{"cards": [3, 4], "weight": -1.0}]
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_zero_total_weight_rejected():
    """Zero total weight (no positive compatible mass) is rejected."""
    payload = minimal_allstreet_payload()
    payload["player0_combos"] = [{"cards": [3, 4], "weight": 0.0}]
    payload["player1_combos"] = [{"cards": [5, 6], "weight": 0.0}]
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_invalid_algorithm_rejected():
    """Invalid algorithm names are rejected."""
    payload = minimal_allstreet_payload()
    payload["algorithm"] = "unknown-algorithm"
    with pytest.raises((ValueError, KeyError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))
    
    payload = minimal_allstreet_payload()
    payload["algorithm"] = "cfr-plus"  # Not in the S1 contract
    with pytest.raises((ValueError, KeyError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_vanilla_cfr_with_seed_rejected():
    """Vanilla CFR with a seed is rejected."""
    payload = minimal_allstreet_payload()
    payload["algorithm"] = "vanilla-cfr"
    payload["seed"] = 42
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_mccfr_without_seed_rejected():
    """MCCFR without a seed is rejected."""
    payload = minimal_allstreet_payload()
    payload["algorithm"] = "external-sampling-mccfr"
    payload["seed"] = None
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_mccfr_with_non_integer_seed_rejected():
    """MCCFR with non-integer seed is rejected."""
    payload = minimal_allstreet_payload()
    payload["algorithm"] = "external-sampling-mccfr"
    payload["seed"] = 42.5
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_explicit_continuation_field_rejected():
    """Explicit continuation field in payload is rejected."""
    payload = minimal_allstreet_payload()
    payload["continuation"] = "automatic"
    with pytest.raises((ValueError, KeyError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_explicit_payoff_table_rejected():
    """Explicit payoff table in payload is rejected."""
    payload = minimal_allstreet_payload()
    payload["payoff_table"] = {}
    with pytest.raises((ValueError, KeyError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_non_positive_iterations_rejected():
    """Non-positive iteration counts are rejected."""
    payload = minimal_allstreet_payload()
    payload["iterations"] = 0
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))
    
    payload = minimal_allstreet_payload()
    payload["iterations"] = -10
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_non_positive_max_nodes_rejected():
    """Non-positive max_nodes are rejected."""
    payload = minimal_allstreet_payload()
    payload["max_nodes"] = 0
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))
    
    payload = minimal_allstreet_payload()
    payload["max_nodes"] = -1000
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_non_positive_max_depth_rejected():
    """Non-positive max_depth are rejected."""
    payload = minimal_allstreet_payload()
    payload["max_depth"] = 0
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_duplicate_cards_in_board_rejected():
    """Duplicate cards in starting board are rejected."""
    payload = minimal_allstreet_payload()
    payload["starting_board"] = [0, 0, 2]
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_duplicate_cards_in_combo_rejected():
    """Duplicate cards in a combo are rejected."""
    payload = minimal_allstreet_payload()
    payload["player0_combos"] = [{"cards": [3, 3], "weight": 1.0}]
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_blocker_conflict_board_and_combo_rejected():
    """Blocker conflicts between board and combos are rejected."""
    payload = minimal_allstreet_payload()
    payload["starting_board"] = [0, 1, 2]
    payload["player0_combos"] = [{"cards": [0, 4], "weight": 1.0}]
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_blocker_conflict_in_runout_rejected():
    """Blocker conflicts in runouts are rejected."""
    payload = minimal_allstreet_payload()
    payload["starting_board"] = [0, 1, 2]
    payload["allowed_runouts"] = [[0, 8], [7, 9]]  # 0 already on board
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_duplicate_cards_in_runout_rejected():
    """Duplicate cards within a runout are rejected."""
    payload = minimal_allstreet_payload()
    payload["allowed_runouts"] = [[7, 7], [8, 9]]
    with pytest.raises((ValueError, TypeError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_resource_bound_node_limit_error():
    """Exceeding max_nodes raises documented error with no partial result."""
    payload = minimal_allstreet_payload()
    payload["max_nodes"] = 5  # Unrealistically low
    payload["wager_targets"] = [100, 200, 300, 400, 500]  # Large tree
    
    with pytest.raises(ValueError) as exc_info:
        dispatch_v4(request("solve-allstreet-postflop", payload))
    
    # Verify error message mentions node limit
    assert "node" in str(exc_info.value).lower() or "limit" in str(exc_info.value).lower()


def test_resource_bound_depth_limit_error():
    """Exceeding max_depth raises documented error with no partial result."""
    payload = minimal_allstreet_payload()
    payload["max_depth"] = 3  # Unrealistically low
    payload["wager_targets"] = [100, 200, 300]
    
    with pytest.raises(ValueError) as exc_info:
        dispatch_v4(request("solve-allstreet-postflop", payload))
    
    # Verify error message mentions depth limit
    assert "depth" in str(exc_info.value).lower() or "limit" in str(exc_info.value).lower()


def test_result_is_json_serializable_with_strict_nan_check():
    """Result is JSON serializable with allow_nan=False."""
    payload = minimal_allstreet_payload()
    result = dispatch_v4(request("solve-allstreet-postflop", payload))
    
    # This will raise ValueError if result contains NaN, Infinity, or -Infinity
    json_str = json.dumps(result, allow_nan=False)
    
    # Verify round-trip
    reconstructed = json.loads(json_str)
    assert reconstructed["config_version"] == 4


def test_metadata_is_truthful_and_complete():
    """Result metadata contains all required truthful fields."""
    payload = minimal_allstreet_payload()
    payload["algorithm"] = "external-sampling-mccfr"
    payload["seed"] = 123
    payload["iterations"] = 50
    
    result = dispatch_v4(request("solve-allstreet-postflop", payload))
    
    # Required metadata fields
    assert result["config_version"] == 4
    assert result["game_version"] == "allstreet-postflop-v1"
    assert result["starting_street"] == "flop"
    assert result["continuation"] == "automatic-natural-terminal"
    assert result["algorithm"] == "external-sampling-mccfr"
    assert result["iterations"] == 50
    assert result["seed"] == 123
    
    # Verify no false claims
    result_str = json.dumps(result).lower()
    assert "converged" not in result_str
    assert "exact equilibrium" not in result_str
    assert "gto parity" not in result_str
    assert "unrestricted" not in result_str


def test_wrong_version_number_rejected():
    """Wrong version number in envelope is rejected."""
    payload = minimal_allstreet_payload()
    bad_request = {"version": 3, "operation": "solve-allstreet-postflop", "payload": payload}
    with pytest.raises((ValueError, KeyError, TypeError)):
        dispatch_v4(bad_request)
    
    bad_request = {"version": 5, "operation": "solve-allstreet-postflop", "payload": payload}
    with pytest.raises((ValueError, KeyError, TypeError)):
        dispatch_v4(bad_request)


def test_float_envelope_version_rejected():
    """Float envelope version 4.0 is rejected; version must be JSON integer 4."""
    payload = minimal_allstreet_payload()
    bad_request = {"version": 4.0, "operation": "solve-allstreet-postflop", "payload": payload}
    with pytest.raises(ValueError, match=r"version must be JSON integer 4"):
        dispatch_v4(bad_request)


def test_wrong_operation_name_rejected():
    """Wrong operation name is rejected."""
    payload = minimal_allstreet_payload()
    with pytest.raises((ValueError, KeyError)):
        dispatch_v4(request("solve-postflop", payload))
    
    with pytest.raises((ValueError, KeyError)):
        dispatch_v4(request("solve-allstreet", payload))


def test_invalid_betting_mode_rejected():
    """Invalid betting mode is rejected."""
    payload = minimal_allstreet_payload()
    payload["betting_mode"] = "fixed-limit"
    with pytest.raises((ValueError, KeyError)):
        dispatch_v4(request("solve-allstreet-postflop", payload))


def test_pot_limit_betting_mode_accepted():
    """Pot-limit betting mode is accepted."""
    payload = minimal_allstreet_payload()
    payload["betting_mode"] = "pot-limit"
    result = dispatch_v4(request("solve-allstreet-postflop", payload))
    assert result["config_version"] == 4


def test_deep_response_isolation_comprehensive():
    """Deep response isolation: mutate strategy, nested policy, metadata, values; fresh response equals pristine baseline."""
    payload = minimal_allstreet_payload()
    
    # Get pristine baseline
    baseline = dispatch_v4(request("solve-allstreet-postflop", payload))
    
    # Get response to mutate
    response_to_mutate = dispatch_v4(request("solve-allstreet-postflop", payload))
    
    # Verify they start equal
    assert response_to_mutate == baseline
    
    # Mutate top-level strategy
    if "strategy" in response_to_mutate and isinstance(response_to_mutate["strategy"], dict):
        response_to_mutate["strategy"]["__top_level_mutation__"] = "injected"
        # Mutate nested policy if present
        for key, value in response_to_mutate["strategy"].items():
            if isinstance(value, dict):
                value["__nested_policy_mutation__"] = True
                # Mutate values within nested structures
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, (int, float)):
                        value[nested_key] = nested_value * 999
                    elif isinstance(nested_value, list):
                        nested_value.append("__list_mutation__")
                break
    
    # Mutate metadata fields
    if "algorithm" in response_to_mutate:
        response_to_mutate["algorithm"] = "mutated-algorithm"
    if "iterations" in response_to_mutate:
        response_to_mutate["iterations"] = 999999
    if "config_version" in response_to_mutate:
        response_to_mutate["config_version"] = 999
    
    # Mutate exploitability/nashconv if present
    if "exploitability" in response_to_mutate:
        response_to_mutate["exploitability"] = -999.999
    if "nashconv" in response_to_mutate:
        response_to_mutate["nashconv"] = -999.999
    
    # Get fresh response after mutations
    fresh_response = dispatch_v4(request("solve-allstreet-postflop", payload))
    
    # Fresh response must equal pristine baseline exactly
    assert fresh_response == baseline
    
    # Verify mutations didn't leak to fresh response
    if "strategy" in fresh_response and isinstance(fresh_response["strategy"], dict):
        assert "__top_level_mutation__" not in fresh_response["strategy"]
        for key, value in fresh_response["strategy"].items():
            if isinstance(value, dict):
                assert "__nested_policy_mutation__" not in value
                assert "__list_mutation__" not in str(value)
    
    assert fresh_response.get("algorithm") != "mutated-algorithm"
    assert fresh_response.get("iterations") != 999999
    assert fresh_response.get("config_version") == 4
    if "exploitability" in fresh_response:
        assert fresh_response["exploitability"] != -999.999
    if "nashconv" in fresh_response:
        assert fresh_response["nashconv"] != -999.999
