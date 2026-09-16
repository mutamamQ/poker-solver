"""Permanent S3-I2 package-export and capability contracts.

R3I2-4 owner: tests/test_phase4_s3_exports.py
Strict TDD RED: require all documented public typed S3 names exported from
poker_solver package root and require dispatch_v3 capabilities to advertise
nplayer-preflop feature with exact status, players, street, interfaces,
continuations, and deviation fields.
"""

from __future__ import annotations

import poker_solver
from poker_solver import nplayer_preflop
from poker_solver.api_v3 import dispatch_v3


def _capabilities() -> dict:
    return dispatch_v3({"version": 3, "operation": "capabilities", "payload": {}})


def test_package_exports_nplayer_preflop_config() -> None:
    """Require NPlayerPreflopConfig exported from package root."""
    defining_symbol = nplayer_preflop.NPlayerPreflopConfig
    assert getattr(poker_solver, "NPlayerPreflopConfig", None) is defining_symbol, (
        "NPlayerPreflopConfig must be exported from poker_solver package root"
    )


def test_package_exports_nplayer_preflop_continuation() -> None:
    """Require NPlayerPreflopContinuation exported from package root."""
    defining_symbol = nplayer_preflop.NPlayerPreflopContinuation
    assert getattr(poker_solver, "NPlayerPreflopContinuation", None) is defining_symbol, (
        "NPlayerPreflopContinuation must be exported from poker_solver package root"
    )


def test_package_exports_nplayer_preflop_sizing_rule() -> None:
    """Require NPlayerPreflopSizingRule exported from package root."""
    defining_symbol = nplayer_preflop.NPlayerPreflopSizingRule
    assert getattr(poker_solver, "NPlayerPreflopSizingRule", None) is defining_symbol, (
        "NPlayerPreflopSizingRule must be exported from poker_solver package root"
    )


def test_package_exports_nplayer_preflop_public_action() -> None:
    """Require NPlayerPreflopPublicAction exported from package root."""
    defining_symbol = nplayer_preflop.NPlayerPreflopPublicAction
    assert getattr(poker_solver, "NPlayerPreflopPublicAction", None) is defining_symbol, (
        "NPlayerPreflopPublicAction must be exported from poker_solver package root"
    )


def test_package_exports_nplayer_preflop_state() -> None:
    """Require NPlayerPreflopState exported from package root."""
    defining_symbol = nplayer_preflop.NPlayerPreflopState
    assert getattr(poker_solver, "NPlayerPreflopState", None) is defining_symbol, (
        "NPlayerPreflopState must be exported from poker_solver package root"
    )


def test_package_exports_nplayer_preflop_solve_result() -> None:
    """Require NPlayerPreflopSolveResult exported from package root."""
    defining_symbol = nplayer_preflop.NPlayerPreflopSolveResult
    assert getattr(poker_solver, "NPlayerPreflopSolveResult", None) is defining_symbol, (
        "NPlayerPreflopSolveResult must be exported from poker_solver package root"
    )


def test_package_exports_enumerate_nplayer_preflop_deals() -> None:
    """Require enumerate_nplayer_preflop_deals exported from package root."""
    defining_symbol = nplayer_preflop.enumerate_nplayer_preflop_deals
    assert getattr(poker_solver, "enumerate_nplayer_preflop_deals", None) is defining_symbol, (
        "enumerate_nplayer_preflop_deals must be exported from poker_solver package root"
    )


def test_package_exports_create_nplayer_preflop_root() -> None:
    """Require create_nplayer_preflop_root exported from package root."""
    defining_symbol = nplayer_preflop.create_nplayer_preflop_root
    assert getattr(poker_solver, "create_nplayer_preflop_root", None) is defining_symbol, (
        "create_nplayer_preflop_root must be exported from poker_solver package root"
    )


def test_package_exports_solve_nplayer_preflop() -> None:
    """Require solve_nplayer_preflop exported from package root."""
    defining_symbol = nplayer_preflop.solve_nplayer_preflop
    assert getattr(poker_solver, "solve_nplayer_preflop", None) is defining_symbol, (
        "solve_nplayer_preflop must be exported from poker_solver package root"
    )


def test_capability_manifest_describes_bounded_nplayer_preflop_exactly() -> None:
    """Require v3 capability response to include nplayer-preflop feature.

    The existing v3 capability response must add a truthful deterministic
    deep-copy-isolated feature key 'nplayer-preflop' with exact fields:
    - status: 'implemented-bounded'
    - players: [2, 9]
    - street: 'preflop-one-round'
    - interfaces: ['typed', 'json-v4', 'cli-phase4']
    - continuations: 'supplied-or-derived-bounded'
    - deviation: 'exhaustive-diagnostic-only'

    All existing capability entries must be retained.
    """
    expected = {
        "status": "implemented-bounded",
        "players": [2, 9],
        "street": "preflop-one-round",
        "interfaces": ["typed", "json-v4", "cli-phase4"],
        "continuations": "supplied-or-derived-bounded",
        "deviation": "exhaustive-diagnostic-only",
    }
    result = _capabilities()
    assert result["features"]["nplayer-preflop"] == expected, (
        f"nplayer-preflop capability must match exact specification, "
        f"got {result['features'].get('nplayer-preflop')!r}"
    )


def test_nplayer_preflop_capability_response_is_deterministic_and_detached() -> None:
    """Require nplayer-preflop capability to be deterministic and deep-copy isolated."""
    expected = {
        "status": "implemented-bounded",
        "players": [2, 9],
        "street": "preflop-one-round",
        "interfaces": ["typed", "json-v4", "cli-phase4"],
        "continuations": "supplied-or-derived-bounded",
        "deviation": "exhaustive-diagnostic-only",
    }
    first = _capabilities()
    second = _capabilities()
    assert first == second, "Repeated capability calls must return identical results"

    # Mutate first response
    first["features"]["nplayer-preflop"]["players"].append(10)
    first["features"]["nplayer-preflop"]["interfaces"].append("mutated")
    first["features"]["nplayer-preflop"]["status"] = "mutated"
    first["features"]["new-feature"] = {"status": "mutated"}

    # Fresh call must return original unmutated values
    fresh = _capabilities()
    assert fresh["features"]["nplayer-preflop"] == expected, (
        "Capability response must be deep-copy isolated from caller mutations"
    )
    assert "new-feature" not in fresh["features"], (
        "Capability response must not retain caller-added keys"
    )


def test_existing_s1_and_s2_package_exports_remain_identical() -> None:
    """Require all S1 and S2 package exports to remain unchanged."""
    from poker_solver.allstreet import (
        AllStreetPostflopConfig,
        AllStreetSolveResult,
        create_allstreet_root,
        solve_allstreet_postflop,
    )
    from poker_solver.nplayer_postflop import (
        DealN,
        NPlayerPostflopConfig,
        NPlayerPostflopSolveResult,
        NPlayerPostflopState,
        NPlayerPublicAction,
        create_nplayer_postflop_root,
        enumerate_deals,
        solve_nplayer_postflop,
    )
    from poker_solver.api_v4 import dispatch_v4

    # S1 exports
    assert poker_solver.AllStreetPostflopConfig is AllStreetPostflopConfig
    assert poker_solver.AllStreetSolveResult is AllStreetSolveResult
    assert poker_solver.create_allstreet_root is create_allstreet_root
    assert poker_solver.solve_allstreet_postflop is solve_allstreet_postflop
    assert poker_solver.dispatch_v4 is dispatch_v4

    # S2 exports
    assert poker_solver.NPlayerPostflopConfig is NPlayerPostflopConfig
    assert poker_solver.DealN is DealN
    assert poker_solver.NPlayerPublicAction is NPlayerPublicAction
    assert poker_solver.NPlayerPostflopState is NPlayerPostflopState
    assert poker_solver.enumerate_deals is enumerate_deals
    assert poker_solver.create_nplayer_postflop_root is create_nplayer_postflop_root
    assert poker_solver.NPlayerPostflopSolveResult is NPlayerPostflopSolveResult
    assert poker_solver.solve_nplayer_postflop is solve_nplayer_postflop


def test_existing_v3_capabilities_remain_available() -> None:
    """Require all existing v3 capability features to remain unchanged."""
    features = _capabilities()["features"]

    # Legacy features
    assert features["preflop"]["status"] == "implemented-bounded"
    assert features["multiway-postflop"]["players"] == 3
    assert features["n-player-cfr"]["deviation_certificate"] == "exhaustive-diagnostic-only"

    # S1 feature
    assert features["allstreet-postflop"] == {
        "status": "implemented-bounded",
        "starting_street": "flop",
        "continuation": "automatic-natural-terminal",
        "interfaces": ["typed", "json-v4", "cli-phase4"],
    }

    # S2 feature
    assert features["nplayer-postflop"] == {
        "status": "implemented-bounded",
        "players": [2, 9],
        "streets": "one-betting-round",
        "interfaces": ["typed", "json-v4", "cli-phase4"],
        "deviation": "exhaustive-diagnostic-only",
    }
