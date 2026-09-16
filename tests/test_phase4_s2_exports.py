"""Permanent S2-I2 package-export and capability contracts."""

from __future__ import annotations

import poker_solver
from poker_solver import nplayer_postflop
from poker_solver.api_v3 import dispatch_v3


def _capabilities() -> dict:
    return dispatch_v3({"version": 3, "operation": "capabilities", "payload": {}})


def test_package_exports_nplayer_postflop_state_contracts() -> None:
    names = (
        "NPlayerPostflopConfig",
        "DealN",
        "NPlayerPublicAction",
        "NPlayerPostflopState",
        "enumerate_deals",
        "create_nplayer_postflop_root",
    )
    for name in names:
        defining_symbol = getattr(nplayer_postflop, name)
        assert getattr(poker_solver, name, None) is defining_symbol


def test_package_exports_nplayer_postflop_solve_contracts() -> None:
    for name in ("NPlayerPostflopSolveResult", "solve_nplayer_postflop"):
        defining_symbol = getattr(nplayer_postflop, name, None)
        assert defining_symbol is not None, f"poker_solver.nplayer_postflop.{name} is required"
        assert getattr(poker_solver, name, None) is defining_symbol


def test_capability_manifest_describes_bounded_nplayer_postflop_exactly() -> None:
    expected = {
        "status": "implemented-bounded",
        "players": [2, 9],
        "streets": "one-betting-round",
        "interfaces": ["typed", "json-v4", "cli-phase4"],
        "deviation": "exhaustive-diagnostic-only",
    }
    result = _capabilities()
    assert result["features"]["nplayer-postflop"] == expected


def test_nplayer_capability_response_is_deterministic_and_detached() -> None:
    expected = {
        "status": "implemented-bounded",
        "players": [2, 9],
        "streets": "one-betting-round",
        "interfaces": ["typed", "json-v4", "cli-phase4"],
        "deviation": "exhaustive-diagnostic-only",
    }
    first = _capabilities()
    assert first == _capabilities()
    first["features"]["nplayer-postflop"]["players"].append(10)
    first["features"]["nplayer-postflop"]["interfaces"].append("mutated")
    assert _capabilities()["features"]["nplayer-postflop"] == expected


def test_existing_s1_package_exports_remain_identical() -> None:
    from poker_solver.allstreet import (
        AllStreetPostflopConfig,
        AllStreetSolveResult,
        create_allstreet_root,
        solve_allstreet_postflop,
    )
    from poker_solver.api_v4 import dispatch_v4

    assert poker_solver.AllStreetPostflopConfig is AllStreetPostflopConfig
    assert poker_solver.AllStreetSolveResult is AllStreetSolveResult
    assert poker_solver.create_allstreet_root is create_allstreet_root
    assert poker_solver.solve_allstreet_postflop is solve_allstreet_postflop
    assert poker_solver.dispatch_v4 is dispatch_v4


def test_existing_v3_capabilities_remain_available() -> None:
    features = _capabilities()["features"]
    assert features["multiway-postflop"]["players"] == 3
    assert features["n-player-cfr"]["deviation_certificate"] == "exhaustive-diagnostic-only"
    assert features["allstreet-postflop"] == {
        "status": "implemented-bounded",
        "starting_street": "flop",
        "continuation": "automatic-natural-terminal",
        "interfaces": ["typed", "json-v4", "cli-phase4"],
    }
