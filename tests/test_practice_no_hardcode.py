"""R1 definition-of-done: answers come from runtime solves, never from literals.

(a) iterations 5 vs 300 on the same spot (same spot_id) changes the solved
    strategy/range strategy AND params_hash.
(b) a different range width or pot changes the strategy/action values AND
    params_hash.
(c) catalog.py and adapter.py contain no dict literals with float values.
"""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest

import poker_solver.practice.adapter as adapter_module
import poker_solver.practice.catalog as catalog_module
from poker_solver.practice.adapter import SolverAdapter
from poker_solver.practice.catalog import generate_catalog
from poker_solver.practice.models import SolveParams

TOL = 1e-6


def _max_diff(a, b):
    assert tuple(a) == tuple(b)
    return max(abs(a[k] - b[k]) for k in a)


def _range_diff(a, b):
    common = set(a.range_strategy) & set(b.range_strategy)
    assert common
    return max(_max_diff(a.range_strategy[h], b.range_strategy[h]) for h in common)


@pytest.fixture(scope="module")
def adapter():
    return SolverAdapter()


@pytest.fixture(scope="module")
def river_spot():
    return generate_catalog(families=("river-oop-bet-or-check",), solve=SolveParams(iterations=60), limit=1)[0]


@pytest.mark.parametrize("family", ["kuhn-intro", "river-oop-bet-or-check", "river-ip-facing-bet"])
def test_a_iterations_change_strategy_and_hash(adapter, family):
    spot = generate_catalog(families=(family,), limit=1)[0]
    low = spot.with_solve(SolveParams(iterations=5))
    high = spot.with_solve(SolveParams(iterations=300))
    assert low.spot_id == high.spot_id == spot.spot_id
    assert low.params_hash() != high.params_hash()
    s_low, s_high = adapter.solve(low), adapter.solve(high)
    assert s_low.provenance.params_hash != s_high.provenance.params_hash
    assert s_low.provenance.iterations == 5 and s_high.provenance.iterations == 300
    assert _max_diff(s_low.strategy, s_high.strategy) > TOL or _range_diff(s_low, s_high) > TOL
    assert s_high.provenance.nash_conv < s_low.provenance.nash_conv


def test_b_pot_changes_answers_and_hash(adapter, river_spot):
    bigger = dataclasses.replace(river_spot, pot=river_spot.pot * 3)
    assert bigger.params_hash() != river_spot.params_hash()
    a, b = adapter.solve(river_spot), adapter.solve(bigger)
    assert _max_diff(a.strategy, b.strategy) > TOL or _max_diff(a.action_values, b.action_values) > TOL
    assert _range_diff(a, b) > TOL


def test_b_range_width_changes_answers_and_hash(adapter, river_spot):
    hero = river_spot.hero_seat
    villain = 1 - hero
    ranges = list(river_spot.ranges)
    # Narrow the villain range by one combo that does not conflict with hero's hand.
    keep = [c for c in ranges[villain]]
    drop = next(c for c in keep if not set(c.cards) & set(river_spot.hero_hand))
    keep.remove(drop)
    if not any(not set(c.cards) & set(river_spot.hero_hand) for c in keep):
        pytest.skip("narrowing would leave hero without opponents")
    ranges[villain] = tuple(keep)
    narrower = dataclasses.replace(river_spot, ranges=tuple(ranges))
    assert narrower.params_hash() != river_spot.params_hash()
    a, b = adapter.solve(river_spot), adapter.solve(narrower)
    assert _max_diff(a.strategy, b.strategy) > TOL or _max_diff(a.action_values, b.action_values) > TOL
    # Hero range width too.
    hero_keep = tuple(c for c in river_spot.ranges[hero] if c.cards == river_spot.hero_hand)
    ranges = list(river_spot.ranges)
    ranges[hero] = hero_keep
    hero_narrow = dataclasses.replace(river_spot, ranges=tuple(ranges))
    assert hero_narrow.params_hash() != river_spot.params_hash()
    c = adapter.solve(hero_narrow)
    assert _max_diff(a.strategy, c.strategy) > TOL or _max_diff(a.action_values, c.action_values) > TOL


def _float_dict_literals(path: Path) -> list[int]:
    tree = ast.parse(path.read_text())
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for value in node.values:
                target = value.operand if isinstance(value, ast.UnaryOp) else value
                if isinstance(target, ast.Constant) and isinstance(target.value, float):
                    bad.append(node.lineno)
        if isinstance(node, ast.DictComp):
            target = node.value.operand if isinstance(node.value, ast.UnaryOp) else node.value
            if isinstance(target, ast.Constant) and isinstance(target.value, float):
                bad.append(node.lineno)
    return sorted(set(bad))


@pytest.mark.parametrize("module", [catalog_module, adapter_module])
def test_c_no_float_probability_dict_literals(module):
    path = Path(module.__file__)
    assert _float_dict_literals(path) == [], f"float dict literal in {path.name}"


def test_c_detector_catches_a_literal(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text("STRATEGY = {'check': 0.5, 'bet': -0.5}\nX = {a: 0.25 for a in 'ab'}\n")
    assert len(_float_dict_literals(sample)) == 2
