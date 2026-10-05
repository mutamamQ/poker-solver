"""Catalog generator tests: determinism, uniqueness, validity, no literal strategies."""

from __future__ import annotations

import ast
import time
from pathlib import Path

import pytest

import poker_solver.practice.catalog as catalog_module
from poker_solver.model import Action
from poker_solver.practice.adapter import SolverAdapter
from poker_solver.practice.catalog import (
    FAMILIES,
    RIVER_BET_PCTS,
    RIVER_COMBOS_PER_SIDE,
    find_spot,
    generate_catalog,
)
from poker_solver.practice.models import SolveParams


def test_families_and_size():
    assert set(("kuhn-intro", "river-oop-bet-or-check", "river-ip-facing-bet")) <= set(FAMILIES)
    spots = generate_catalog()
    assert 20 <= len(spots) <= 100  # W4: four solver-backed families added (36 -> 72)
    assert {s.family for s in spots} == set(FAMILIES)
    assert sum(s.family == "kuhn-intro" for s in spots) == 12


def test_generation_is_fast_and_deterministic():
    start = time.perf_counter()
    first = generate_catalog(seed=3)
    assert time.perf_counter() - start < 1.0
    second = generate_catalog(seed=3)
    assert [s.canonical() for s in first] == [s.canonical() for s in second]
    assert [s.spot_id for s in first] == [s.spot_id for s in second]
    other = generate_catalog(seed=4)
    river_a = [s.board for s in first if s.backend == "river"]
    river_b = [s.board for s in other if s.backend == "river"]
    assert river_a != river_b


def test_unique_ids_and_hashes():
    spots = generate_catalog()
    assert len({s.spot_id for s in spots}) == len(spots)
    assert len({s.params_hash() for s in spots}) == len(spots)


def test_family_output_independent_of_other_requests():
    alone = generate_catalog(families=("river-ip-facing-bet",), seed=1)
    together = [s for s in generate_catalog(seed=1) if s.family == "river-ip-facing-bet"]
    assert [s.spot_id for s in alone] == [s.spot_id for s in together]


def test_solve_params_propagate_and_ids_stable():
    base = generate_catalog()
    alt = generate_catalog(solve=SolveParams(iterations=17))
    assert all(s.solve.iterations == 17 for s in alt)
    assert [s.spot_id for s in base] == [s.spot_id for s in alt]
    assert all(a.params_hash() != b.params_hash() for a, b in zip(base, alt))


def test_river_spot_shape():
    for spot in generate_catalog():
        if spot.backend != "river":
            continue
        assert len(spot.board) == 5
        assert all(1 <= len(r) <= RIVER_COMBOS_PER_SIDE for r in spot.ranges)
        assert spot.hero_hand in {c.cards for c in spot.ranges[spot.hero_seat]}
        assert not set(spot.hero_hand) & set(spot.board)
        assert spot.backend_extra["bet_pct"] in RIVER_BET_PCTS
        assert spot.bet_sizes[0] == max(1, (int(spot.pot) * spot.backend_extra["bet_pct"] + 50) // 100)
        if spot.family == "river-ip-facing-bet":
            assert spot.hero_seat == 1 and spot.action_history == (Action("bet", spot.bet_sizes[0]),)
        else:
            assert spot.hero_seat == 0 and spot.action_history == ()


def test_limit_and_argument_validation():
    assert len(generate_catalog(limit=5)) == 5
    for kwargs in (dict(families=("nope",)), dict(families=("kuhn-intro", "kuhn-intro")),
                   dict(seed=True), dict(seed="0"), dict(solve={"iterations": 3}), dict(limit=-1)):
        with pytest.raises(ValueError):
            generate_catalog(**kwargs)


def test_find_spot():
    spots = generate_catalog(seed=2)
    target = spots[-1]
    assert find_spot(target.spot_id, seed=2) == target
    with pytest.raises(ValueError):
        find_spot("kuhn-intro/000000000000", seed=2)
    with pytest.raises(ValueError):
        find_spot(target.spot_id, seed=99)


def test_every_family_solves_at_runtime():
    adapter = SolverAdapter()
    solve = SolveParams(iterations=20)
    for family in FAMILIES:
        spot = generate_catalog(families=(family,), solve=solve, limit=1)[0]
        solved = adapter.solve(spot)
        assert abs(sum(solved.strategy.values()) - 1.0) < 1e-9
        assert solved.provenance.iterations == 20


def test_catalog_has_no_strategy_literals():
    tree = ast.parse(Path(catalog_module.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for value in node.values:
                target = value.operand if isinstance(value, ast.UnaryOp) else value
                assert not (isinstance(target, ast.Constant) and isinstance(target.value, float)), (
                    f"float literal in dict at line {node.lineno}"
                )
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            pytest.fail(f"float literal {node.value!r} at line {node.lineno} in catalog.py")
