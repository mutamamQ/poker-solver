"""Permanent S3-I2 examples and generic CLI contracts.

The synthetic 2/6/9-player request files construct real typed roots before the
missing v4 operation is invoked, so RED is attributable to the facade rather
than absent files or malformed fixtures.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from poker_solver.api_v4 import dispatch_v4
from poker_solver.game_structure import ForcedPost
from poker_solver.nplayer_preflop import (
    NPlayerPreflopConfig,
    NPlayerPreflopContinuation,
    create_nplayer_preflop_root,
)
from poker_solver.preflop import WeightedCombo


def _example_request(player_count: int) -> dict:
    path = Path(f"examples/phase4/nplayer_{player_count}p_preflop.json")
    request = json.loads(path.read_text(encoding="utf-8"))
    assert set(request) == {"version", "operation", "payload"}
    assert request["version"] == 4
    assert request["operation"] == "solve-nplayer-preflop"
    return request


def _typed_config(request: dict) -> NPlayerPreflopConfig:
    payload = request["payload"]
    continuation = payload["continuation"]
    showdown_ranks = {
        tuple(tuple(combo) for combo in entry["deal"]): tuple(entry["ranks"])
        for entry in continuation["entries"]
    }
    return NPlayerPreflopConfig(
        version=payload["version"],
        num_players=payload["num_players"],
        button=payload["button"],
        starting_stacks=tuple(payload["starting_stacks"]),
        forced_posts=tuple(ForcedPost(**post) for post in payload["forced_posts"]),
        straddle_variant=payload["straddle_variant"],
        ranges=tuple(
            tuple(WeightedCombo(tuple(combo["cards"]), combo["weight"]) for combo in player_range)
            for player_range in payload["ranges"]
        ),
        sizing_rules=(),
        max_raises=payload["max_raises"],
        max_deals=payload["max_deals"],
        max_nodes=payload["max_nodes"],
        short_all_in_reopens=payload["short_all_in_reopens"],
        continuation=NPlayerPreflopContinuation(
            kind=continuation["kind"],
            provenance=continuation["provenance"],
            source=continuation["source"],
            payoff_table={},
            showdown_ranks=showdown_ranks,
            odd_chip_order=tuple(continuation["odd_chip_order"]),
        ),
    )


@pytest.mark.parametrize("player_count", [2, 6, 9])
def test_example_request_constructs_a_valid_bounded_typed_root(player_count: int) -> None:
    request = _example_request(player_count)
    payload = request["payload"]
    assert not ({"strategy", "values", "metadata", "certificate"} & set(payload))
    config = _typed_config(request)
    root = create_nplayer_preflop_root(config)
    outcomes = root.chance_outcomes()
    assert len(outcomes) == 1
    assert outcomes[0][1] == 1
    dealt = root.child(outcomes[0][0])
    assert dealt.num_players() == player_count
    assert dealt.legal_actions()


def test_phase4_nplayer_2p_preflop_example_file():
    """2-player canonical preflop example executes via file path and returns valid structure."""
    example_path = Path("examples/phase4/nplayer_2p_preflop.json")
    result = subprocess.run(
        [sys.executable, "-m", "poker_solver.cli", "phase4", str(example_path), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["version"] == 4
    assert data["operation"] == "solve-nplayer-preflop"
    assert data["game_version"] == "nplayer-preflop-v1"
    assert "strategy" in data
    assert "values" in data and len(data["values"]) == 2
    assert abs(data["values"][0] + data["values"][1]) < 1e-9
    assert "metadata" in data
    assert data["metadata"]["converged"] is False


def test_phase4_nplayer_6p_preflop_example_file():
    """6-player canonical preflop example executes via file path and returns valid structure."""
    example_path = Path("examples/phase4/nplayer_6p_preflop.json")
    result = subprocess.run(
        [sys.executable, "-m", "poker_solver.cli", "phase4", str(example_path), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["version"] == 4
    assert data["operation"] == "solve-nplayer-preflop"
    assert data["game_version"] == "nplayer-preflop-v1"
    assert "strategy" in data
    assert "values" in data and len(data["values"]) == 6
    assert abs(sum(data["values"])) < 1e-9
    assert "metadata" in data
    assert data["metadata"]["converged"] is False


def test_phase4_nplayer_9p_preflop_example_file():
    """9-player canonical preflop example executes via file path and returns valid structure."""
    example_path = Path("examples/phase4/nplayer_9p_preflop.json")
    result = subprocess.run(
        [sys.executable, "-m", "poker_solver.cli", "phase4", str(example_path), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["version"] == 4
    assert data["operation"] == "solve-nplayer-preflop"
    assert data["game_version"] == "nplayer-preflop-v1"
    assert "strategy" in data
    assert "values" in data and len(data["values"]) == 9
    assert abs(sum(data["values"])) < 1e-9
    assert "metadata" in data
    assert data["metadata"]["converged"] is False


def test_phase4_nplayer_preflop_stdin_execution():
    """Generic stdin path `phase4 - --json` executes 2p preflop example."""
    example_path = Path("examples/phase4/nplayer_2p_preflop.json")
    request_json = example_path.read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "poker_solver.cli", "phase4", "-", "--json"],
        input=request_json,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["operation"] == "solve-nplayer-preflop"
    assert len(data["values"]) == 2


def test_phase4_preflop_missing_file_error():
    """Missing file path returns exit code 2 with error message."""
    result = subprocess.run(
        [sys.executable, "-m", "poker_solver.cli", "phase4", "nonexistent_preflop.json", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "error:" in result.stderr


def test_phase4_preflop_malformed_json_error():
    """Malformed JSON input returns exit code 2 with error message."""
    result = subprocess.run(
        [sys.executable, "-m", "poker_solver.cli", "phase4", "-", "--json"],
        input="{invalid json",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "error:" in result.stderr


def test_2p_example_direct_dispatch():
    """2-player example dispatches through api_v4 and returns exact strict v4 envelope."""
    example_path = Path("examples/phase4/nplayer_2p_preflop.json")
    request = json.loads(example_path.read_text(encoding="utf-8"))
    assert set(request) == {"version", "operation", "payload"}
    assert request["version"] == 4
    assert request["operation"] == "solve-nplayer-preflop"

    result = dispatch_v4(request)
    assert result["version"] == 4
    assert result["operation"] == "solve-nplayer-preflop"
    assert result["config_version"] == 4
    assert result["game_version"] == "nplayer-preflop-v1"
    assert "strategy" in result
    assert len(result["values"]) == 2
    assert all(isinstance(v, (int, float)) for v in result["values"])
    assert abs(sum(result["values"])) < 1e-9
    assert result["approximate"] is False
    assert result["provenance"]


def test_6p_example_direct_dispatch():
    """6-player example dispatches through api_v4 and returns exact strict v4 envelope."""
    example_path = Path("examples/phase4/nplayer_6p_preflop.json")
    request = json.loads(example_path.read_text(encoding="utf-8"))
    assert set(request) == {"version", "operation", "payload"}
    assert request["version"] == 4
    assert request["operation"] == "solve-nplayer-preflop"

    result = dispatch_v4(request)
    assert result["version"] == 4
    assert result["operation"] == "solve-nplayer-preflop"
    assert result["config_version"] == 4
    assert result["game_version"] == "nplayer-preflop-v1"
    assert "strategy" in result
    assert len(result["values"]) == 6
    assert all(isinstance(v, (int, float)) for v in result["values"])
    assert abs(sum(result["values"])) < 1e-9
    assert result["approximate"] is False
    assert result["provenance"]


def test_9p_example_direct_dispatch():
    """9-player example dispatches through api_v4 and returns exact strict v4 envelope."""
    example_path = Path("examples/phase4/nplayer_9p_preflop.json")
    request = json.loads(example_path.read_text(encoding="utf-8"))
    assert set(request) == {"version", "operation", "payload"}
    assert request["version"] == 4
    assert request["operation"] == "solve-nplayer-preflop"

    result = dispatch_v4(request)
    assert result["version"] == 4
    assert result["operation"] == "solve-nplayer-preflop"
    assert result["config_version"] == 4
    assert result["game_version"] == "nplayer-preflop-v1"
    assert "strategy" in result
    assert len(result["values"]) == 9
    assert all(isinstance(v, (int, float)) for v in result["values"])
    assert abs(sum(result["values"])) < 1e-9
    assert result["approximate"] is False
    assert result["provenance"]


def test_example_strategies_normalized():
    """All example strategies are normalized and finite."""
    for player_count in [2, 6, 9]:
        example_path = Path(f"examples/phase4/nplayer_{player_count}p_preflop.json")
        request = json.loads(example_path.read_text(encoding="utf-8"))
        result = dispatch_v4(request)
        assert dispatch_v4(request) == result

        assert result["strategy"]
        for policy in result["strategy"].values():
            assert policy
            assert all(isinstance(p, (int, float)) and p >= 0 for p in policy.values())
            assert abs(sum(policy.values()) - 1.0) < 1e-9
