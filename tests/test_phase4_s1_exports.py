"""RED suite for S1-I2 package exports and capability manifest.

I204 owner: tests/test_phase4_s1_exports.py
Strict TDD RED: require package-root exports and capability feature.
"""

from poker_solver.api_v3 import dispatch_v3


def test_package_exports_allstreet_config():
    """Require AllStreetPostflopConfig exported from package root."""
    import poker_solver
    from poker_solver.allstreet import AllStreetPostflopConfig as DefiningClass
    
    assert hasattr(poker_solver, "AllStreetPostflopConfig"), (
        "AllStreetPostflopConfig must be exported from poker_solver package root"
    )
    
    ExportedClass = poker_solver.AllStreetPostflopConfig
    assert ExportedClass is DefiningClass, (
        f"Exported AllStreetPostflopConfig must be identical to defining-module symbol, "
        f"got {ExportedClass!r} vs {DefiningClass!r}"
    )


def test_package_exports_allstreet_result():
    """Require AllStreetSolveResult exported from package root."""
    import poker_solver
    from poker_solver.allstreet import AllStreetSolveResult as DefiningClass
    
    assert hasattr(poker_solver, "AllStreetSolveResult"), (
        "AllStreetSolveResult must be exported from poker_solver package root"
    )
    
    ExportedClass = poker_solver.AllStreetSolveResult
    assert ExportedClass is DefiningClass, (
        f"Exported AllStreetSolveResult must be identical to defining-module symbol, "
        f"got {ExportedClass!r} vs {DefiningClass!r}"
    )


def test_package_exports_create_allstreet_root():
    """Require create_allstreet_root exported from package root."""
    import poker_solver
    from poker_solver.allstreet import create_allstreet_root as defining_func
    
    assert hasattr(poker_solver, "create_allstreet_root"), (
        "create_allstreet_root must be exported from poker_solver package root"
    )
    
    exported_func = poker_solver.create_allstreet_root
    assert exported_func is defining_func, (
        f"Exported create_allstreet_root must be identical to defining-module symbol, "
        f"got {exported_func!r} vs {defining_func!r}"
    )


def test_package_exports_solve_allstreet_postflop():
    """Require solve_allstreet_postflop exported from package root."""
    import poker_solver
    from poker_solver.allstreet import solve_allstreet_postflop as defining_func
    
    assert hasattr(poker_solver, "solve_allstreet_postflop"), (
        "solve_allstreet_postflop must be exported from poker_solver package root"
    )
    
    exported_func = poker_solver.solve_allstreet_postflop
    assert exported_func is defining_func, (
        f"Exported solve_allstreet_postflop must be identical to defining-module symbol, "
        f"got {exported_func!r} vs {defining_func!r}"
    )


def test_package_exports_dispatch_v4():
    """Require dispatch_v4 exported from package root."""
    import poker_solver
    from poker_solver.api_v4 import dispatch_v4 as defining_func
    
    assert hasattr(poker_solver, "dispatch_v4"), (
        "dispatch_v4 must be exported from poker_solver package root"
    )
    
    exported_func = poker_solver.dispatch_v4
    assert exported_func is defining_func, (
        f"Exported dispatch_v4 must be identical to defining-module symbol, "
        f"got {exported_func!r} vs {defining_func!r}"
    )


def test_capability_allstreet_postflop_feature():
    """Require v3 capability response to include allstreet-postflop feature.
    
    The existing v3 capability response must add a truthful deterministic
    deep-copy-isolated feature key 'allstreet-postflop' with exact fields:
    - status: 'implemented-bounded'
    - starting_street: 'flop'
    - continuation: 'automatic-natural-terminal'
    - interfaces: ['typed', 'json-v4', 'cli-phase4']
    
    All existing capability entries must be retained.
    """
    request = {"version": 3, "operation": "capabilities", "payload": {}}
    first = dispatch_v3(request)
    second = dispatch_v3(request)

    assert first == second
    assert "fast-ddls" in first["features"]
    assert "preflop" in first["features"]

    expected = {
        "status": "implemented-bounded",
        "starting_street": "flop",
        "continuation": "automatic-natural-terminal",
        "interfaces": ["typed", "json-v4", "cli-phase4"],
    }
    assert first["features"]["allstreet-postflop"] == expected

    first["features"]["allstreet-postflop"]["interfaces"].append("mutated")
    first["features"]["allstreet-postflop"]["status"] = "mutated"
    first["features"]["new"] = {"status": "mutated"}
    fresh = dispatch_v3(request)
    assert fresh["features"]["allstreet-postflop"] == expected
    assert "new" not in fresh["features"]
