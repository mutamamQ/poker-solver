"""Solver adapter + evaluator tests. Expected values come from fresh runtime solves only."""

from __future__ import annotations

import dataclasses
import json
import threading
from math import isclose

import pytest

from poker_solver.best_response import nash_conv
from poker_solver.cards import parse_cards
from poker_solver.cfr import CFRSolver, collect_infosets, expected_values
from poker_solver.equity import WeightedCombo
from poker_solver.kuhn import kuhn_root
from poker_solver.model import Action
from poker_solver.practice import adapter as adapter_module
from poker_solver.practice.adapter import SolverAdapter, solve_spot, solver_version
from poker_solver.practice.catalog import generate_catalog
from poker_solver.practice.evaluate import action_values, subtree_value
from poker_solver.practice.models import PracticeSpot, SolvedSpot, SolveParams

FAST = SolveParams(iterations=30)


def first(family, solve=FAST):
    return generate_catalog(families=(family,), solve=solve, limit=1)[0]


def allstreet_spot(iterations=15):
    board = parse_cards(["Td", "8h", "2c"])
    r0 = (WeightedCombo(parse_cards(["As", "Ah"]), 1.0), WeightedCombo(parse_cards(["5s", "4s"]), 1.0))
    r1 = (WeightedCombo(parse_cards(["Qs", "Qh"]), 1.0), WeightedCombo(parse_cards(["Jd", "Jc"]), 1.0))
    return PracticeSpot(
        family="flop-check-small-tree", backend="allstreet", game_type="heads-up", street="flop",
        board=board, hero_seat=1, villain_seats=(0,), ranges=(r0, r1), pot=100, stacks=(100, 100),
        action_history=(Action("CHECK"),), bet_sizes=(33,), hero_hand=parse_cards(["Qs", "Qh"]),
        solve=SolveParams(iterations=iterations),
        backend_extra={"allowed_runouts": [list(parse_cards(["3d", "7c"]))], "betting_mode": "no-limit",
                       "max_nodes": 4000, "max_depth": 40},
    )


def check_solved(solved: SolvedSpot):
    spot = solved.spot
    assert abs(sum(solved.strategy.values()) - 1.0) < 1e-9
    assert tuple(solved.strategy) == solved.legal_actions == tuple(solved.action_values)
    for policy in solved.range_strategy.values():
        assert abs(sum(policy.values()) - 1.0) < 1e-9
    prov = solved.provenance
    assert prov.backend == spot.backend and prov.params_hash == spot.params_hash()
    assert prov.iterations == spot.solve.iterations and prov.algorithm == spot.solve.algorithm
    assert prov.nash_conv is not None and prov.nash_conv >= 0 and prov.wall_time_s > 0
    assert prov.solver_version == solver_version() and prov.entrypoint.startswith("poker_solver.")
    assert dict(prov.params)["pot"] == spot.canonical()["pot"]
    # W5 F4: optimal_action = highest-Q action within the solved strategy's support.
    support = [a for a in solved.legal_actions if solved.strategy[a] > 0]
    assert solved.strategy[solved.optimal_action] > 0
    assert solved.action_values[solved.optimal_action] == max(solved.action_values[a] for a in support)
    data = solved.to_json()
    json.dumps(data, allow_nan=False)
    assert set(data) == {"spot", "provenance", "legal_actions", "pot_at_decision", "strategy", "action_values",
                         "range_strategy", "optimal_action", "optimal_size"}
    assert [e["action"] for e in data["strategy"]] == data["legal_actions"]
    assert [e["action"] for e in data["action_values"]] == data["legal_actions"]


def test_kuhn_spots_all_solve_and_match_raw_solver():
    adapter = SolverAdapter()
    spots = generate_catalog(families=("kuhn-intro",), solve=FAST)
    root = kuhn_root()
    profile = CFRSolver(root).train(FAST.iterations)
    for spot in spots:
        solved = adapter.solve(spot)
        check_solved(solved)
        assert solved.info_key == ("kuhn-v1", spot.hero_seat, spot.backend_extra["kuhn_card"], spot.action_history)
        assert dict(solved.strategy) == profile[solved.info_key]
        assert set(solved.range_strategy) == {"J", "Q", "K"}
        assert solved.optimal_size is None
        expected_pot = 2.0 + sum(a.kind == "bet" for a in spot.action_history)
        assert solved.pot_at_decision == expected_pot
    assert adapter.solve_count == len(spots)


def test_river_oop_and_ip_solve():
    adapter = SolverAdapter()
    for family in ("river-oop-bet-or-check", "river-ip-facing-bet"):
        spot = first(family)
        solved = adapter.solve(spot)
        check_solved(solved)
        assert solved.info_key[0] == "river-v1" and solved.info_key[1] == spot.hero_seat
        assert solved.info_key[2] == spot.hero_hand
        assert set(solved.range_strategy) <= {"".join(__import__("poker_solver.cards", fromlist=["x"]).format_card(c)
                                                      for c in combo.cards) for combo in spot.ranges[spot.hero_seat]}
        if family == "river-ip-facing-bet":
            assert {a.kind for a in solved.legal_actions} == {"fold", "call"}
            assert solved.pot_at_decision == spot.pot + spot.bet_sizes[0]
        else:
            assert {a.kind for a in solved.legal_actions} == {"check", "bet"}
            assert solved.pot_at_decision == spot.pot
            if solved.optimal_action.kind == "bet":
                assert solved.optimal_size == spot.bet_sizes[0]


def test_allstreet_flop_route():
    solved = SolverAdapter().solve(allstreet_spot())
    check_solved(solved)
    # W4: same solve_allstreet_postflop pipeline over a memoized root (equality checked in test_practice_families)
    assert solved.provenance.entrypoint.startswith("poker_solver.allstreet.create_allstreet_root+cfr.CFRSolver.train")
    assert solved.pot_at_decision == 100.0


def test_cache_hit_and_thread_safety():
    adapter = SolverAdapter()
    spot = first("kuhn-intro")
    results = []
    threads = [threading.Thread(target=lambda: results.append(adapter.solve(spot))) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(r is results[0] for r in results)
    assert adapter.cached(spot) is results[0]
    assert adapter.solve(spot) is results[0]
    other = adapter.solve(spot.with_solve(SolveParams(iterations=31)))
    assert other is not results[0]
    assert solve_spot(spot) is solve_spot(spot)
    shared = {}
    SolverAdapter(cache=shared).solve(spot)
    assert spot.params_hash() in shared


def test_fail_closed():
    adapter = SolverAdapter()
    with pytest.raises(ValueError):
        adapter.solve("not a spot")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        SolverAdapter(timeout_s=True)
    river = first("river-oop-bet-or-check")
    with pytest.raises(ValueError, match="vanilla"):
        adapter.solve(river.with_solve(SolveParams("external-sampling-mccfr", 5, 1)))
    with pytest.raises(ValueError, match="budget"):
        SolverAdapter(timeout_s=1e-9).solve(river.with_solve(SolveParams(iterations=60)))


def test_evaluator_identity_and_bruteforce():
    root = kuhn_root()
    profile = CFRSolver(root).train(300)
    base = expected_values(root, profile)
    total = 0.0
    for key, (player, actions) in collect_infosets(root).items():
        q, mass = action_values(root, profile, player, key)
        mix = sum(profile[key][a] * q[a] for a in actions)
        if player == 0 and key[3] == ():
            assert isclose(mass, 1 / 3, abs_tol=1e-12)
            total += mass * mix
        # brute-force deviation: hero reach x mass x (Q(a) - mix)
        hero_reach = 1.0 if key[3] in ((), (Action("check"),), (Action("bet"),)) else profile[(
            "kuhn-v1", 0, key[2], ())][Action("check")]
        for action in actions:
            deviated = dict(profile)
            deviated[key] = {a: float(a == action) for a in actions}
            delta = expected_values(root, deviated)[player] - base[player]
            assert isclose(delta, hero_reach * mass * (q[action] - mix), abs_tol=1e-12)
    assert isclose(total, base[0], abs_tol=1e-12)
    assert isclose(subtree_value(root, profile, 0), base[0], abs_tol=1e-12)


def test_evaluator_fail_closed():
    root = kuhn_root()
    profile = CFRSolver(root).train(10)
    key = ("kuhn-v1", 0, "K", (Action("check"), Action("bet")))
    never_bets = dict(profile)
    for card in "JQK":
        never_bets[("kuhn-v1", 1, card, (Action("check"),))] = {Action("check"): 1.0, Action("bet"): 0.0}
    with pytest.raises(ValueError, match="zero"):
        action_values(root, never_bets, 0, key)
    broken = dict(profile)
    del broken[("kuhn-v1", 1, "J", (Action("check"),))]
    with pytest.raises(ValueError):
        action_values(root, broken, 0, key)
    with pytest.raises(ValueError):
        action_values(root, profile, True, key)
    with pytest.raises(ValueError):
        action_values(root, profile, 0, ("missing",))


def test_kuhn_solver_self_loss():
    """At ~2000 iterations solver noise is small and bounded by the solver's own NashConv."""
    root = kuhn_root()
    solver = CFRSolver(root)
    early = solver.train(200)
    early_loss = {}
    for key, (player, actions) in collect_infosets(root).items():
        q, _ = action_values(root, early, player, key)
        early_loss[key] = max(q.values()) - sum(early[key][a] * q[a] for a in actions)
    profile = solver.train(1800)
    result = nash_conv(root, profile)
    losses = {}
    weighted = {0: 0.0, 1: 0.0}
    for key, (player, actions) in collect_infosets(root).items():
        q, mass = action_values(root, profile, player, key)
        loss = max(q.values()) - sum(profile[key][a] * q[a] for a in actions)
        assert loss >= -1e-12
        losses[key] = loss
        weighted[player] += mass * loss
    for player in (0, 1):
        assert weighted[player] <= result.incentives[player] + 1e-3
    # Non-mixing infosets converge to zero noise; mixed ones shrink with iterations.
    assert min(losses.values()) < 1e-3
    assert sum(losses.values()) < sum(early_loss.values())
    assert sum(1 for v in losses.values() if v < 1e-3) >= 6


def test_solved_spot_validation():
    solved = SolverAdapter().solve(first("kuhn-intro"))
    with pytest.raises(ValueError):
        dataclasses.replace(solved, optimal_size=1)
    with pytest.raises(ValueError):
        dataclasses.replace(solved, strategy={a: 0.0 for a in solved.legal_actions})
    with pytest.raises(ValueError):
        dataclasses.replace(solved, spot=solved.spot.with_solve(SolveParams(iterations=3)))
    with pytest.raises(TypeError):
        solved.strategy[solved.legal_actions[0]] = 1.0  # type: ignore[index]


def test_module_entrypoints_declared():
    # W4: + nplayer-preflop (heads-up / 3-max) and multistreet (turn)
    assert set(adapter_module.ENTRYPOINTS) == {"kuhn", "river", "allstreet", "nplayer-preflop", "multistreet"}
