"""Strict direct-v4 S2-I2 N-player postflop API contracts."""

from __future__ import annotations

from copy import deepcopy
from math import inf, nan

import pytest

from poker_solver.api_v4 import dispatch_v4


def _request(payload: dict) -> dict:
    return {"version": 4, "operation": "solve-nplayer-postflop", "payload": payload}


def _payload() -> dict:
    deal = [[3, 4], [5, 6], [7, 8], [9, 10]]
    return {
        "version": "nplayer-postflop-v1",
        "num_players": 4,
        "button": 0,
        "starting_stacks": [20, 20, 20, 20],
        "contributions": [2, 2, 2, 2],
        "folded": [False, False, False, False],
        "board": [0, 1, 2],
        "ranges": [
            [{"cards": combo, "weight": 1.0}]
            for combo in deal
        ],
        "wager_targets": [4],
        "max_raises": 1,
        "max_deals": 1,
        "max_nodes": 2000,
        "odd_chip_order": [0, 1, 2, 3],
        "showdowns": [{"deal": deal, "ranks": [4, 3, 2, 1]}],
        "rake_policy": None,
        "algorithm": "vanilla-cfr",
        "iterations": 2,
        "seed": None,
        "include_deviation_certificate": False,
        "max_pure_strategies": 100,
    }


def test_legacy_v4_allstreet_control_is_green() -> None:
    payload = {
        "version": "allstreet-postflop-v1",
        "starting_board": [0, 1, 2],
        "initial_dead_pot": 10,
        "effective_stack": 20,
        "player0_combos": [{"cards": [3, 4], "weight": 1.0}],
        "player1_combos": [{"cards": [5, 6], "weight": 1.0}],
        "allowed_runouts": [[7, 8]],
        "betting_mode": "no-limit",
        "wager_targets": [5],
        "algorithm": "vanilla-cfr",
        "iterations": 1,
        "seed": None,
        "max_nodes": 10_000,
        "max_depth": 100,
    }
    result = dispatch_v4({"version": 4, "operation": "solve-allstreet-postflop", "payload": payload})
    assert result["operation"] == "solve-allstreet-postflop"
    assert len(result["values"]) == 2


def test_valid_nplayer_request_has_deterministic_detached_response() -> None:
    payload = _payload()
    first = dispatch_v4(_request(payload))
    second = dispatch_v4(_request(payload))
    assert first == second
    assert first["version"] == 4
    assert first["operation"] == "solve-nplayer-postflop"
    assert first["game_version"] == "nplayer-postflop-v1"
    assert first["algorithm"] == "vanilla-cfr"
    assert first["iterations"] == 2
    assert first["seed"] is None
    assert first["max_nodes"] == 2000
    assert len(first["values"]) == 4
    assert all(isinstance(value, float) for value in first["values"])
    for policy in first["strategy"].values():
        assert sum(policy.values()) == pytest.approx(1.0, abs=1e-12)
    assert first["metadata"]["converged"] is False
    assert first["metadata"]["convergence_claim"] == "none"
    assert first["provenance"]
    first["values"].append(999.0)
    first["metadata"]["converged"] = True
    first["strategy"]["mutated"] = {"CHECK": 1.0}
    assert dispatch_v4(_request(payload)) == second


def test_valid_request_can_return_exact_diagnostic_certificate() -> None:
    payload = _payload()
    payload["folded"] = [False, False, True, True]
    payload["include_deviation_certificate"] = True
    payload["max_pure_strategies"] = 100_000
    response = dispatch_v4(_request(payload))
    certificate = response["certificate"]
    assert len(certificate["values"]) == 4
    assert len(certificate["best_response_values"]) == 4
    assert len(certificate["incentives"]) == 4
    assert certificate["total_incentive"] == pytest.approx(sum(certificate["incentives"]))
    assert certificate["provenance"] == "exhaustive finite pure unilateral deviations; diagnostic only"


def test_envelope_and_payload_fields_are_exact() -> None:
    request = _request(_payload())
    request["extra"] = 1
    with pytest.raises(ValueError):
        dispatch_v4(request)
    payload = _payload()
    payload["extra"] = 1
    with pytest.raises(ValueError):
        dispatch_v4(_request(payload))
    payload = _payload()
    del payload["num_players"]
    with pytest.raises(ValueError):
        dispatch_v4(_request(payload))


@pytest.mark.parametrize("field", ["starting_stacks", "contributions", "folded", "ranges", "odd_chip_order"])
def test_all_player_arrays_must_have_n_entries(field: str) -> None:
    payload = _payload()
    payload[field] = payload[field][:-1]
    with pytest.raises(ValueError):
        dispatch_v4(_request(payload))


@pytest.mark.parametrize("field", ["num_players", "button", "max_raises", "max_deals", "max_nodes", "iterations", "max_pure_strategies"])
def test_bool_numeric_fields_are_rejected(field: str) -> None:
    payload = _payload()
    payload[field] = True
    with pytest.raises(ValueError):
        dispatch_v4(_request(payload))


@pytest.mark.parametrize("weight", [0.0, -1.0, inf, nan])
def test_invalid_range_weights_are_rejected(weight: float) -> None:
    payload = _payload()
    payload["ranges"][0][0]["weight"] = weight
    with pytest.raises(ValueError):
        dispatch_v4(_request(payload))


def test_showdown_list_is_converted_and_duplicates_fail_closed() -> None:
    payload = _payload()
    payload["showdowns"].append(deepcopy(payload["showdowns"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        dispatch_v4(_request(payload))
    payload = _payload()
    payload["showdowns"][0]["deal"] = payload["showdowns"][0]["deal"][:-1]
    with pytest.raises(ValueError):
        dispatch_v4(_request(payload))
    payload = _payload()
    payload["showdowns"][0]["ranks"] = [1, 2, 3]
    with pytest.raises(ValueError):
        dispatch_v4(_request(payload))


def test_malformed_rake_policy_is_rejected() -> None:
    payload = _payload()
    payload["rake_policy"] = {"rate_numerator": 1}
    with pytest.raises(ValueError):
        dispatch_v4(_request(payload))


@pytest.mark.parametrize(
    ("algorithm", "seed"),
    [("external-sampling-mccfr", 1), ("cfr-plus", None), ("vanilla-cfr", 1)],
)
def test_only_seedless_vanilla_cfr_is_supported(algorithm: str, seed: int | None) -> None:
    payload = _payload()
    payload["algorithm"] = algorithm
    payload["seed"] = seed
    with pytest.raises(ValueError):
        dispatch_v4(_request(payload))


@pytest.mark.parametrize("field", ["max_deals", "max_nodes", "iterations", "max_pure_strategies"])
def test_positive_bounds_are_required(field: str) -> None:
    payload = _payload()
    payload[field] = 0
    with pytest.raises(ValueError):
        dispatch_v4(_request(payload))
