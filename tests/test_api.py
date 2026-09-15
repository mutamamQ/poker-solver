"""Tests for the strict version-2 API."""

import json
import pytest
from poker_solver.api import (
    ExploitabilityResult,
    SolveResult,
    compute_exploitability,
    deserialize_strategy,
    load_json_input,
    load_multistreet_config,
    serialize_strategy,
    solve_multistreet,
)
from poker_solver.equity import WeightedCombo
from poker_solver.multistreet import MultiStreetConfig, create_root


def minimal_river_config():
    """Minimal valid river configuration."""
    return {
        "version": 2,
        "starting_street": "river",
        "starting_board": ["2c", "3d", "4h", "9s", "Kc"],
        "initial_dead_pot": 10,
        "effective_stack": 50,
        "player0_combos": [
            {"cards": ["As", "5s"], "weight": 1.0},
            {"cards": ["Qs", "Js"], "weight": 1.0},
        ],
        "player1_combos": [
            {"cards": ["Kh", "Qh"], "weight": 1.0},
            {"cards": ["9h", "8h"], "weight": 1.0},
        ],
        "allowed_runouts": [],
        "betting_mode": "no-limit",
        "wager_targets": [10, 20, 50],
    }


def test_load_multistreet_config_valid():
    """Test loading a valid configuration."""
    data = minimal_river_config()
    config = load_multistreet_config(data)
    assert config.version == "multistreet-v1"
    assert config.starting_street == "river"
    assert len(config.starting_board) == 5
    assert config.initial_dead_pot == 10
    assert config.effective_stack == 50
    assert len(config.player0_combos) == 2
    assert len(config.player1_combos) == 2
    assert config.betting_mode == "no-limit"
    assert config.wager_targets == (10, 20, 50)


def test_load_multistreet_config_rejects_unknown_fields():
    """Test that unknown fields are rejected."""
    data = minimal_river_config()
    data["extra_field"] = "invalid"
    with pytest.raises(ValueError, match="unknown fields"):
        load_multistreet_config(data)


def test_load_multistreet_config_rejects_missing_fields():
    """Test that missing required fields are rejected."""
    data = minimal_river_config()
    del data["effective_stack"]
    with pytest.raises(ValueError, match="missing required fields"):
        load_multistreet_config(data)


def test_load_multistreet_config_rejects_bool_as_int():
    """Test that booleans are rejected where integers are expected."""
    data = minimal_river_config()
    data["effective_stack"] = True
    with pytest.raises(ValueError, match="effective_stack must be a JSON integer"):
        load_multistreet_config(data)


def test_load_multistreet_config_rejects_bool_as_weight():
    """Test that booleans are rejected for combo weights."""
    data = minimal_river_config()
    data["player0_combos"][0]["weight"] = False
    with pytest.raises(ValueError, match="combo 0 weight must not be a boolean"):
        load_multistreet_config(data)


def test_load_multistreet_config_rejects_negative_weight():
    """Test that negative weights are rejected."""
    data = minimal_river_config()
    data["player0_combos"][0]["weight"] = -1.0
    with pytest.raises(ValueError, match="combo 0 weight must be non-negative"):
        load_multistreet_config(data)


def test_load_multistreet_config_rejects_non_finite_weight():
    """Test that non-finite weights are rejected."""
    data = minimal_river_config()
    data["player0_combos"][0]["weight"] = float("inf")
    with pytest.raises(ValueError, match="combo 0 weight must be finite"):
        load_multistreet_config(data)


def test_load_multistreet_config_rejects_invalid_cards():
    """Test that invalid card strings are rejected."""
    data = minimal_river_config()
    data["starting_board"][0] = "XX"
    with pytest.raises(ValueError):
        load_multistreet_config(data)


def test_load_multistreet_config_rejects_overlapping_cards():
    """Test that overlapping cards are rejected."""
    data = minimal_river_config()
    data["player0_combos"][0]["cards"] = ["2c", "3d"]  # Overlap with board
    with pytest.raises(ValueError, match="combo cards overlap with board"):
        load_multistreet_config(data)


def test_load_multistreet_config_enforces_size_limits():
    """Test that size limits are enforced."""
    data = minimal_river_config()
    data["player0_combos"] = [{"cards": ["As", "Ah"], "weight": 1.0}] * 1001
    with pytest.raises(ValueError, match="player0_combos exceeds limit"):
        load_multistreet_config(data)


def test_solve_multistreet_vanilla_cfr():
    """Test solving with vanilla CFR."""
    data = minimal_river_config()
    config = load_multistreet_config(data)
    result = solve_multistreet(config, "vanilla-cfr", 100, seed=None)
    assert result.algorithm == "vanilla-cfr"
    assert result.seed is None
    assert result.iterations == 100
    assert result.nash_conv >= 0
    assert result.half_nash_conv == result.nash_conv / 2
    assert abs(sum(result.values)) < 1e-9  # Zero-sum
    assert len(result.strategy) > 0


def test_solve_multistreet_mccfr_requires_seed():
    """Test that MCCFR requires a seed."""
    data = minimal_river_config()
    config = load_multistreet_config(data)
    with pytest.raises(ValueError, match="external-sampling-mccfr requires a seed"):
        solve_multistreet(config, "external-sampling-mccfr", 100, seed=None)


def test_solve_multistreet_mccfr_with_seed():
    """Test solving with MCCFR and a seed."""
    data = minimal_river_config()
    config = load_multistreet_config(data)
    result = solve_multistreet(config, "external-sampling-mccfr", 100, seed=42)
    assert result.algorithm == "external-sampling-mccfr"
    assert result.seed == 42
    assert result.iterations == 100
    assert result.nash_conv >= 0


def test_solve_multistreet_vanilla_rejects_seed():
    """Test that vanilla CFR rejects a seed parameter."""
    data = minimal_river_config()
    config = load_multistreet_config(data)
    with pytest.raises(ValueError, match="vanilla-cfr does not accept a seed"):
        solve_multistreet(config, "vanilla-cfr", 100, seed=42)


def test_solve_multistreet_rejects_invalid_algorithm():
    """Test that invalid algorithms are rejected."""
    data = minimal_river_config()
    config = load_multistreet_config(data)
    with pytest.raises(ValueError, match="algorithm must be"):
        solve_multistreet(config, "invalid-algo", 100, seed=None)


def test_solve_multistreet_rejects_non_positive_iterations():
    """Test that non-positive iterations are rejected."""
    data = minimal_river_config()
    config = load_multistreet_config(data)
    with pytest.raises(ValueError, match="iterations must be a positive integer"):
        solve_multistreet(config, "vanilla-cfr", 0, seed=None)


def test_solve_multistreet_rejects_bool_iterations():
    """Test that boolean iterations are rejected."""
    data = minimal_river_config()
    config = load_multistreet_config(data)
    with pytest.raises(ValueError, match="iterations must be a positive integer"):
        solve_multistreet(config, "vanilla-cfr", True, seed=None)


def test_solve_multistreet_deterministic_same_seed():
    """Test that same seed produces identical output for MCCFR."""
    data = minimal_river_config()
    config = load_multistreet_config(data)
    result1 = solve_multistreet(config, "external-sampling-mccfr", 50, seed=123)
    result2 = solve_multistreet(config, "external-sampling-mccfr", 50, seed=123)
    assert result1.values == result2.values
    assert result1.nash_conv == result2.nash_conv
    # Strategy keys should match
    assert set(result1.strategy.keys()) == set(result2.strategy.keys())


def test_compute_exploitability():
    """Test computing exploitability."""
    data = minimal_river_config()
    config = load_multistreet_config(data)
    result = solve_multistreet(config, "vanilla-cfr", 100, seed=None)
    root = create_root(config)
    exploit = compute_exploitability(root, result.strategy)
    assert exploit.nash_conv >= 0
    assert exploit.half_nash_conv == exploit.nash_conv / 2
    assert len(exploit.values) == 2
    assert len(exploit.best_response_values) == 2
    assert len(exploit.incentives) == 2


def test_strategy_json_roundtrip_and_wrapper():
    config = load_multistreet_config(minimal_river_config())
    solved = solve_multistreet(config, "vanilla-cfr", 20)
    root = create_root(config)
    encoded = serialize_strategy(solved.strategy)
    assert deserialize_strategy(root, encoded) == solved.strategy
    assert deserialize_strategy(root, {"strategy": encoded, "metadata": {}}) == solved.strategy


def test_strategy_json_rejects_missing_policy():
    config = load_multistreet_config(minimal_river_config())
    solved = solve_multistreet(config, "vanilla-cfr", 5)
    encoded = serialize_strategy(solved.strategy)
    encoded["policies"].pop()
    with pytest.raises(ValueError, match="missing information states"):
        deserialize_strategy(create_root(config), encoded)


def test_load_json_input_from_file(tmp_path):
    """Test loading JSON from a file."""
    data = minimal_river_config()
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data))
    loaded = load_json_input(str(path))
    assert loaded == data
