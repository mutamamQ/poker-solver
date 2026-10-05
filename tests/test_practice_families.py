"""W4 task A: solver-backed practice families (preflop HU / 3-max, flop c-bet, turn barrel).

Every assertion about strategies / Q-values is made against a runtime solve; the
tests use reduced iteration counts so the module runs in the normal suite.
"""

from __future__ import annotations

import dataclasses
from math import isclose, isfinite

import pytest

from poker_solver.allstreet import AllStreetPostflopConfig, solve_allstreet_postflop
from poker_solver.model import Action
from poker_solver.nplayer import NPlayerCFRSolver
from poker_solver.nplayer_preflop import create_nplayer_preflop_root
from poker_solver.practice import adapter as adapter_module
from poker_solver.practice.adapter import (
    ENTRYPOINTS,
    CachedState,
    SolverAdapter,
    locate_decision,
    portable_key,
    preflop_config,
)
from poker_solver.practice.catalog import FAMILIES, FAMILY_DEFAULT_SOLVE, find_spot, generate_catalog
from poker_solver.practice.evaluate import action_values
from poker_solver.practice.models import PracticeSpot, SolveParams

NEW = ("preflop-hu-open", "preflop-3max-open", "flop-cbet", "turn-barrel")
SHAPE = {
    "preflop-hu-open": ("nplayer-preflop", "heads-up", "preflop", 0),
    "preflop-3max-open": ("nplayer-preflop", "3-max", "preflop", 0),
    "flop-cbet": ("allstreet", "heads-up", "flop", 3),
    "turn-barrel": ("multistreet", "heads-up", "turn", 4),
}
#: Reduced iterations for the end-to-end checks (defaults are measured in task-A.md).
FAST = {"preflop-hu-open": 40, "preflop-3max-open": 15, "flop-cbet": 25, "turn-barrel": 40}
TOL = 1e-6
LEGACY = ("kuhn-intro", "river-oop-bet-or-check", "river-ip-facing-bet")


def _max_diff(a, b) -> float:
    assert set(a) == set(b)
    return max(abs(a[k] - b[k]) for k in a)


@pytest.fixture(scope="module")
def adapter():
    return SolverAdapter(timeout_s=300)


def _spot(family: str, iterations: int | None = None, index: int = 0) -> PracticeSpot:
    spot = generate_catalog(families=(family,))[index]
    return spot if iterations is None else spot.with_solve(SolveParams(iterations=iterations))


# --------------------------------------------------------------------------- catalog


def test_families_registered_and_legacy_unchanged():
    assert FAMILIES[:3] == LEGACY
    assert set(NEW) <= set(FAMILIES)
    assert set(FAMILY_DEFAULT_SOLVE) == set(FAMILIES)
    legacy = generate_catalog(families=LEGACY)
    assert len(legacy) == 36
    # Legacy families keep the global default solve (and therefore their params_hash).
    assert all(s.solve == SolveParams() for s in legacy)


@pytest.mark.parametrize("family", NEW)
def test_family_generates_valid_unique_stable_spots(family):
    backend, game_type, street, board_len = SHAPE[family]
    spots = generate_catalog(families=(family,), seed=0)
    assert 8 <= len(spots) <= 12
    ids = [s.spot_id for s in spots]
    assert len(set(ids)) == len(ids) and all(i.startswith(family + "/") for i in ids)
    assert len({s.params_hash() for s in spots}) == len(spots)
    again = generate_catalog(families=(family,), seed=0)
    assert [s.canonical() for s in again] == [s.canonical() for s in spots]
    together = [s for s in generate_catalog(seed=0) if s.family == family]
    assert [s.spot_id for s in together] == ids
    other = generate_catalog(families=(family,), seed=1)
    assert [s.spot_id for s in other] != ids
    # spot_id does not depend on solve settings; params_hash does.
    alt = generate_catalog(families=(family,), solve=SolveParams(iterations=7))
    assert [s.spot_id for s in alt] == ids
    assert all(a.params_hash() != b.params_hash() for a, b in zip(spots, alt))
    for spot in spots:
        assert spot.solve == FAMILY_DEFAULT_SOLVE[family]
        assert (spot.backend, spot.game_type, spot.street, len(spot.board)) == (backend, game_type, street, board_len)
        n = 3 if game_type == "3-max" else 2
        assert len(spot.stacks) == n and len(spot.ranges) == n and len(spot.villain_seats) == n - 1
        assert spot.hero_hand in {c.cards for c in spot.ranges[spot.hero_seat]}
        data = spot.to_json()
        for key in ("family", "backend", "game_type", "street", "board", "hero_seat", "villain_seats", "ranges",
                    "pot", "stacks", "action_history", "bet_sizes", "hero_hand", "solve", "spot_id",
                    "params_hash", "board_str", "hero_hand_str", "label"):
            assert key in data
        assert find_spot(spot.spot_id) == spot


def test_3max_family_has_two_villains_and_both_situations():
    spots = generate_catalog(families=("preflop-3max-open",))
    assert {s.hero_seat for s in spots} == {0, 1}
    for spot in spots:
        assert spot.villain_seats == tuple(x for x in range(3) if x != spot.hero_seat)
        assert len(spot.stacks) == 3
        if spot.hero_seat == 1:
            assert spot.action_history == (Action("FOLD"),)


def test_new_backends_validate():
    hu = _spot("preflop-hu-open")
    # nplayer-preflop now accepts heads-up and 3-max; multistreet only the turn.
    with pytest.raises(ValueError):
        dataclasses.replace(hu, pot=4)  # pot must equal the blinds
    with pytest.raises(ValueError):
        dataclasses.replace(hu, bet_sizes=(2,))  # open size must exceed the big blind
    with pytest.raises(ValueError):
        dataclasses.replace(hu, backend_extra={**hu.backend_extra, "equity_samples": 0})
    with pytest.raises(ValueError):
        dataclasses.replace(hu, action_history=(Action("bet", 4),))
    turn = _spot("turn-barrel")
    with pytest.raises(ValueError):
        dataclasses.replace(turn, street="flop", board=turn.board[:3])
    with pytest.raises(ValueError):
        dataclasses.replace(turn, backend_extra={**turn.backend_extra, "allowed_runouts": [[1, 2]]})
    flop = _spot("flop-cbet")
    with pytest.raises(ValueError, match="turn"):
        dataclasses.replace(flop, street="turn", board=turn.board)


# --------------------------------------------------------------------------- end-to-end solves


def _check_solved(solved, family):
    spot = solved.spot
    actions = solved.legal_actions
    assert isclose(sum(solved.strategy.values()), 1.0, abs_tol=1e-9)
    assert all(solved.strategy[a] >= 0 for a in actions)
    assert set(solved.action_values) == set(actions) and all(isfinite(v) for v in solved.action_values.values())
    assert solved.range_strategy
    for policy in solved.range_strategy.values():
        assert set(policy) == set(actions) and isclose(sum(policy.values()), 1.0, abs_tol=1e-9)
    prov = solved.provenance
    assert prov.backend == spot.backend and prov.entrypoint == ENTRYPOINTS[spot.backend]
    assert prov.params_hash == spot.params_hash() and prov.iterations == spot.solve.iterations
    # Every family reports a finite NashConv; 3-max uses the n-player sum of incentives.
    assert prov.nash_conv is not None and isfinite(prov.nash_conv) and prov.nash_conv >= -1e-12
    # W5 F4: optimal_action = highest-Q action within the solved strategy's support.
    support = [a for a in actions if solved.strategy[a] > 0]
    assert solved.strategy[solved.optimal_action] > 0
    assert solved.action_values[solved.optimal_action] == max(solved.action_values[a] for a in support)
    import json
    json.dumps(solved.to_json(), allow_nan=False)


@pytest.mark.parametrize("family", NEW)
def test_family_solves_end_to_end(adapter, family):
    spot = _spot(family, FAST[family])
    solved = adapter.solve(spot)
    _check_solved(solved, family)
    kinds = {a.kind for a in solved.legal_actions}
    if SHAPE[family][0] == "nplayer-preflop":
        assert {"FOLD", "CALL", "RAISE"} <= kinds
        assert Action("RAISE", spot.bet_sizes[0]) in solved.legal_actions
        assert solved.pot_at_decision == 3.0
    else:
        assert kinds == {"CHECK", "RAISE"}
        assert Action("RAISE", spot.bet_sizes[0]) in solved.legal_actions
        assert solved.pot_at_decision == spot.pot
    assert adapter.solve(spot) is solved  # cache hit by params_hash


def test_3max_sb_spot_q_values_for_hero(adapter):
    """3-player Q-values at the SB infoset after a BTN fold, recomputed independently."""
    spot = next(s for s in generate_catalog(families=("preflop-3max-open",)) if s.hero_seat == 1)
    spot = spot.with_solve(SolveParams(iterations=FAST["preflop-3max-open"]))
    solved = adapter.solve(spot)
    _check_solved(solved, "preflop-3max-open")
    assert solved.spot.villain_seats == (0, 2)
    config = preflop_config(spot)
    root = CachedState(create_nplayer_preflop_root(config))
    profile = NPlayerCFRSolver(root, max_nodes=config.max_nodes).train(spot.solve.iterations)
    decision = locate_decision(root, spot, spot.hero_hand, spot.backend)
    assert portable_key(decision.info_key) == solved.info_key
    q, mass = action_values(root, profile, 1, decision.info_key)
    assert mass > 0 and dict(q) == dict(solved.action_values)
    assert {a: profile[decision.info_key][a] for a in decision.legal_actions} == dict(solved.strategy)


def test_allstreet_memoized_route_matches_facade(adapter):
    spot = _spot("flop-cbet", 8)
    ex = spot.backend_extra
    config = AllStreetPostflopConfig(
        "allstreet-postflop-v1", spot.board, int(spot.pot), spot.stacks[0], spot.ranges[0], spot.ranges[1],
        ex["allowed_runouts"], ex["betting_mode"], spot.bet_sizes, ex["max_nodes"], ex["max_depth"],
    )
    facade = solve_allstreet_postflop(config, algorithm="vanilla-cfr", iterations=8)
    solved = adapter.solve(spot)
    assert solved.provenance.nash_conv == facade.nash_conv
    decision_policy = {a: facade.strategy[_raw_key(spot)][a] for a in solved.legal_actions}
    assert decision_policy == dict(solved.strategy)


def _raw_key(spot):
    from poker_solver.allstreet import create_allstreet_root
    ex = spot.backend_extra
    config = AllStreetPostflopConfig(
        "allstreet-postflop-v1", spot.board, int(spot.pot), spot.stacks[0], spot.ranges[0], spot.ranges[1],
        ex["allowed_runouts"], ex["betting_mode"], spot.bet_sizes, ex["max_nodes"], ex["max_depth"],
    )
    return locate_decision(create_allstreet_root(config), spot, spot.hero_hand, spot.backend).info_key


def test_preflop_equity_table_is_runtime_and_zero_sum():
    spot = _spot("preflop-hu-open")
    config = preflop_config(spot)
    table = config.continuation.payoff_table
    assert table and config.continuation.kind == "terminal-table"
    assert all(sum(values) == 0 for values in table.values())
    fewer = dataclasses.replace(spot, backend_extra={**spot.backend_extra, "equity_samples": 16})
    other = preflop_config(fewer).continuation.payoff_table
    assert set(other) == set(table) and other != table


# --------------------------------------------------------------------------- R1 sensitivity


@pytest.mark.parametrize("family", NEW)
def test_r1_iterations_change_answer_for_same_spot_id(adapter, family):
    base = _spot(family)
    low = base.with_solve(SolveParams(iterations=3))
    high = base.with_solve(SolveParams(iterations=FAST[family]))
    assert low.spot_id == high.spot_id == base.spot_id and low.params_hash() != high.params_hash()
    a, b = adapter.solve(low), adapter.solve(high)
    assert _max_diff(a.strategy, b.strategy) > TOL or _max_diff(a.action_values, b.action_values) > TOL
    hands = set(a.range_strategy) & set(b.range_strategy)
    assert max(_max_diff(a.range_strategy[h], b.range_strategy[h]) for h in hands) > TOL


def _range_variants(spot):
    """Narrower villain ranges (one combo dropped), then hero range = dealt hand only."""
    villain = spot.villain_seats[0]
    for drop in spot.ranges[villain]:
        keep = tuple(c for c in spot.ranges[villain] if c != drop)
        if any(not set(c.cards) & set(spot.hero_hand) for c in keep):
            ranges = list(spot.ranges)
            ranges[villain] = keep
            yield dataclasses.replace(spot, ranges=tuple(ranges))
    ranges = list(spot.ranges)
    ranges[spot.hero_seat] = tuple(c for c in spot.ranges[spot.hero_seat] if c.cards == spot.hero_hand)
    yield dataclasses.replace(spot, ranges=tuple(ranges))


@pytest.mark.parametrize("family", NEW)
def test_r1_range_width_changes_answer(adapter, family):
    # Some catalog cells are strategically degenerate for a range tweak (e.g. a villain
    # range that loses on every allowed runout), so the first spots of the family are
    # scanned and at least one range-width change must move the solved answer.
    for index in range(3):
        spot = _spot(family, FAST[family], index)
        a = adapter.solve(spot)
        for variant in _range_variants(spot):
            assert variant.spot_id != spot.spot_id and variant.params_hash() != spot.params_hash()
            b = adapter.solve(variant)
            if _max_diff(a.strategy, b.strategy) > TOL or _max_diff(a.action_values, b.action_values) > TOL:
                return
    pytest.fail(f"no range-width change moved the solved answer for {family}")


def test_entrypoints_cover_every_backend():
    from poker_solver.practice.models import BACKENDS
    assert set(adapter_module.ENTRYPOINTS) == set(BACKENDS)
    assert all(v.startswith("poker_solver.") for v in ENTRYPOINTS.values())


def test_new_family_solve_round_trips_disk_cache(tmp_path):
    from poker_solver.practice.solve_cache import DiskSolveCache
    cache = DiskSolveCache(tmp_path)
    ad = SolverAdapter(cache=cache)
    for family in ("preflop-3max-open", "turn-barrel"):
        spot = _spot(family, 3)
        solved = ad.solve(spot)
        assert DiskSolveCache(tmp_path).get(spot.params_hash()) == solved
