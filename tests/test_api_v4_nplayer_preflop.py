"""Strict direct-v4 S3-I2 N-player preflop API contracts."""

from __future__ import annotations

from copy import deepcopy
from math import inf, nan

import pytest

from poker_solver.api_v4 import dispatch_v4


def _request(payload: dict) -> dict:
    return {"version": 4, "operation": "solve-nplayer-preflop", "payload": payload}


def _payload_terminal_table() -> dict:
    """Minimal valid terminal-table continuation payload."""
    deal = [[0, 1], [2, 3]]
    return {
        "version": "nplayer-preflop-v1",
        "num_players": 2,
        "button": 0,
        "starting_stacks": [10, 10],
        "forced_posts": [
            {"seat": 0, "kind": "small-blind", "amount": 1},
            {"seat": 1, "kind": "big-blind", "amount": 2},
        ],
        "straddle_variant": "none",
        "ranges": [
            [{"cards": combo, "weight": 1.0}]
            for combo in deal
        ],
        "sizing_rules": [],
        "max_raises": 1,
        "max_deals": 1,
        "max_nodes": 1000,
        "short_all_in_reopens": False,
        "continuation": {
            "kind": "terminal-table",
            "provenance": "S3-I2 strict API fixture",
            "source": "supplied",
            "entries": [
                {
                    "deal": deal,
                    "history": [
                        {"actor": 0, "kind": "CALL", "amount": 2},
                        {"actor": 1, "kind": "CHECK", "amount": 0},
                    ],
                    "values": [-1, 1],
                },
                {
                    "deal": deal,
                    "history": [
                        {"actor": 0, "kind": "RAISE", "amount": 10},
                        {"actor": 1, "kind": "CALL", "amount": 10},
                    ],
                    "values": [-1, 1],
                },
                {
                    "deal": deal,
                    "history": [
                        {"actor": 0, "kind": "CALL", "amount": 2},
                        {"actor": 1, "kind": "RAISE", "amount": 10},
                        {"actor": 0, "kind": "CALL", "amount": 10},
                    ],
                    "values": [-1, 1],
                },
            ],
        },
        "algorithm": "vanilla-cfr",
        "iterations": 2,
        "seed": None,
        "include_deviation_certificate": False,
        "max_pure_strategies": 100,
    }


def _payload_showdown_ranks() -> dict:
    """Minimal valid showdown-ranks continuation payload."""
    deal = [[0, 1], [2, 3]]
    return {
        "version": "nplayer-preflop-v1",
        "num_players": 2,
        "button": 0,
        "starting_stacks": [10, 10],
        "forced_posts": [
            {"seat": 0, "kind": "small-blind", "amount": 1},
            {"seat": 1, "kind": "big-blind", "amount": 2},
        ],
        "straddle_variant": "none",
        "ranges": [
            [{"cards": combo, "weight": 1.0}]
            for combo in deal
        ],
        "sizing_rules": [],
        "max_raises": 1,
        "max_deals": 1,
        "max_nodes": 1000,
        "short_all_in_reopens": False,
        "continuation": {
            "kind": "showdown-ranks",
            "provenance": "S3-I2 strict API fixture",
            "source": "supplied",
            "entries": [{"deal": deal, "ranks": [2, 1]}],
            "odd_chip_order": [0, 1],
        },
        "algorithm": "vanilla-cfr",
        "iterations": 2,
        "seed": None,
        "include_deviation_certificate": False,
        "max_pure_strategies": 100,
    }


def test_valid_terminal_table_request_has_exact_response_schema() -> None:
    payload = _payload_terminal_table()
    response = dispatch_v4(_request(payload))
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


def test_valid_showdown_ranks_request_has_exact_response_schema() -> None:
    payload = _payload_showdown_ranks()
    response = dispatch_v4(_request(payload))
    assert response["version"] == 4
    assert response["operation"] == "solve-nplayer-preflop"
    assert response["game_version"] == "nplayer-preflop-v1"
    assert response["algorithm"] == "vanilla-cfr"
    assert response["iterations"] == 2
    assert response["seed"] is None
    assert len(response["values"]) == 2
    assert all(isinstance(v, float) for v in response["values"])
    assert isinstance(response["strategy"], dict)
    assert response["metadata"]["converged"] is False
    assert response["approximate"] is False


def test_response_is_deterministic_and_detached() -> None:
    payload = _payload_terminal_table()
    first = dispatch_v4(_request(payload))
    second = dispatch_v4(_request(payload))
    assert first == second
    first["values"].append(999.0)
    first["metadata"]["converged"] = True
    first["strategy"]["mutated"] = {"CHECK": 1.0}
    assert dispatch_v4(_request(payload)) == second


def test_envelope_fields_are_exact() -> None:
    request = _request(_payload_terminal_table())
    request["extra"] = 1
    with pytest.raises(ValueError):
        dispatch_v4(request)


def test_payload_fields_are_exact() -> None:
    payload = _payload_terminal_table()
    payload["extra"] = 1
    with pytest.raises(ValueError, match="unknown payload fields"):
        dispatch_v4(_request(payload))
    payload = _payload_terminal_table()
    del payload["num_players"]
    with pytest.raises(ValueError, match="missing payload fields"):
        dispatch_v4(_request(payload))


def test_unknown_nested_continuation_field_is_rejected() -> None:
    payload = _payload_terminal_table()
    payload["continuation"]["unknown"] = 1
    with pytest.raises(ValueError, match="unknown continuation fields"):
        dispatch_v4(_request(payload))


def test_missing_nested_continuation_field_is_rejected() -> None:
    payload = _payload_terminal_table()
    del payload["continuation"]["entries"]
    with pytest.raises(ValueError, match="missing continuation fields"):
        dispatch_v4(_request(payload))


@pytest.mark.parametrize("field", ["num_players", "button", "max_raises", "max_deals", "max_nodes", "iterations", "max_pure_strategies"])
def test_bool_numeric_fields_are_rejected(field: str) -> None:
    payload = _payload_terminal_table()
    payload[field] = True
    with pytest.raises(ValueError, match=field):
        dispatch_v4(_request(payload))


@pytest.mark.parametrize("value", [inf, nan])
def test_nonfinite_numeric_fields_are_rejected(value: float) -> None:
    payload = _payload_terminal_table()
    payload["continuation"]["entries"][0]["values"][0] = value
    with pytest.raises(ValueError, match="finite"):
        dispatch_v4(_request(payload))


def test_malformed_deal_array_is_rejected() -> None:
    payload = _payload_terminal_table()
    payload["continuation"]["entries"][0]["deal"] = [[0, 1]]
    with pytest.raises(ValueError, match="deal"):
        dispatch_v4(_request(payload))


def test_malformed_history_is_rejected() -> None:
    payload = _payload_terminal_table()
    payload["continuation"]["entries"][0]["history"] = [{"actor": 0}]
    with pytest.raises(ValueError, match="history"):
        dispatch_v4(_request(payload))


def test_duplicate_terminal_table_keys_are_rejected() -> None:
    payload = _payload_terminal_table()
    entry = deepcopy(payload["continuation"]["entries"][0])
    payload["continuation"]["entries"].append(entry)
    with pytest.raises(ValueError, match="duplicate"):
        dispatch_v4(_request(payload))


def test_duplicate_showdown_deals_are_rejected() -> None:
    payload = _payload_showdown_ranks()
    entry = deepcopy(payload["continuation"]["entries"][0])
    payload["continuation"]["entries"].append(entry)
    with pytest.raises(ValueError, match="duplicate"):
        dispatch_v4(_request(payload))


@pytest.mark.parametrize(
    ("algorithm", "seed"),
    [("external-sampling-mccfr", 1), ("cfr-plus", None), ("vanilla-cfr", 1)],
)
def test_only_seedless_vanilla_cfr_is_supported(algorithm: str, seed: int | None) -> None:
    payload = _payload_terminal_table()
    payload["algorithm"] = algorithm
    payload["seed"] = seed
    expected = "seed" if algorithm == "vanilla-cfr" else "algorithm"
    with pytest.raises(ValueError, match=expected):
        dispatch_v4(_request(payload))


@pytest.mark.parametrize("field", ["max_deals", "max_nodes", "iterations", "max_pure_strategies"])
def test_positive_bounds_are_required(field: str) -> None:
    payload = _payload_terminal_table()
    payload[field] = 0
    with pytest.raises(ValueError, match=field):
        dispatch_v4(_request(payload))


def test_unsupported_straddle_variant_is_rejected() -> None:
    payload = _payload_terminal_table()
    payload["straddle_variant"] = "unsupported"
    with pytest.raises(ValueError, match="straddle_variant"):
        dispatch_v4(_request(payload))


def test_malformed_sizing_rule_is_rejected() -> None:
    payload = _payload_terminal_table()
    payload["sizing_rules"] = [
        {
            "position": "BTN/SB",
            "raise_count": 0,
            "cold_callers": 0,
            "relation": "NA",
            "expressions": [{"unit": "all-in"}],
            "extra": 1,
        }
    ]
    with pytest.raises(ValueError, match="sizing rule"):
        dispatch_v4(_request(payload))


def test_response_has_exact_strategy_values_and_metadata() -> None:
    payload = _payload_terminal_table()
    response = dispatch_v4(_request(payload))
    for policy in response["strategy"].values():
        assert sum(policy.values()) == pytest.approx(1.0, abs=1e-12)
    assert sum(response["values"]) == pytest.approx(0.0, abs=1e-9)
