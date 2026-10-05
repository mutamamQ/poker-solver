"""Production checks for the canonical direct Phase-4 S1 request."""

from __future__ import annotations

import json
from math import isfinite
from pathlib import Path

import pytest

from poker_solver.api_v4 import dispatch_v4


EXAMPLE_PATH = Path(__file__).parent.parent / "examples" / "phase4_s1_flop.json"


@pytest.fixture(scope="module")
def example_request() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def result(example_request: dict) -> dict:
    return dispatch_v4(example_request)


def test_example_is_a_small_direct_strict_v4_request(example_request):
    assert set(example_request) == {"version", "operation", "payload"}
    assert example_request["version"] == 4
    assert example_request["operation"] == "solve-allstreet-postflop"
    payload = example_request["payload"]
    assert payload["version"] == "allstreet-postflop-v1"
    assert len(payload["starting_board"]) == 3
    assert len(payload["player0_combos"]) == 1
    assert len(payload["player1_combos"]) == 1
    assert 1 <= len(payload["allowed_runouts"]) <= 10
    assert payload["algorithm"] == "vanilla-cfr"
    assert payload["seed"] is None
    assert payload["iterations"] <= 100
    assert payload["max_nodes"] <= 10_000
    assert payload["max_depth"] <= 128


def test_example_dispatch_is_truthful_and_zero_sum(example_request, result):
    assert result["version"] == 4
    assert result["operation"] == "solve-allstreet-postflop"
    assert result["config_version"] == 4
    assert result["game_version"] == "allstreet-postflop-v1"
    assert result["starting_street"] == "flop"
    assert result["continuation"] == "automatic-natural-terminal"
    assert result["algorithm"] == example_request["payload"]["algorithm"]
    assert result["iterations"] == example_request["payload"]["iterations"]
    assert result["seed"] is None
    assert result["values"][0] + result["values"][1] == pytest.approx(0.0, abs=1e-12)
    assert all(isfinite(value) for value in result["values"])
    assert result["provenance"] == "complete configured flop-to-river finite-tree traversal"
    forbidden = ("converged", "exact equilibrium", "gto parity", "unrestricted")
    assert not any(term in result["provenance"].lower() for term in forbidden)


def test_example_strategy_is_normalized(result):
    assert result["strategy"]
    for policy in result["strategy"].values():
        assert policy
        assert all(isfinite(probability) and probability >= 0 for probability in policy.values())
        assert sum(policy.values()) == pytest.approx(1.0, abs=1e-12)


def test_example_is_deterministic_and_json_serializable(example_request, result):
    repeated = dispatch_v4(example_request)
    assert repeated == result
    assert json.loads(json.dumps(result, allow_nan=False)) == result