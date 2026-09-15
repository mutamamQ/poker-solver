"""Independent exhaustive gates for the bounded multi-street fixture."""

from __future__ import annotations

from dataclasses import replace
from math import isclose, isfinite

import pytest

from poker_solver.audit import audit_game
from poker_solver.best_response import best_response, exhaustive_best_response, nash_conv
from poker_solver.cfr import CFRSolver, collect_infosets
from poker_solver.mccfr import MCCFRSolver
from poker_solver.model import CHANCE, TERMINAL, Action
from poker_solver.phase2_fixture import tiny_multistreet_root
from poker_solver.cards import parse_cards
from poker_solver.multistreet import create_root


def _uniform(root):
    return {
        key: {action: 1.0 / len(actions) for action in actions}
        for key, (_, actions) in collect_infosets(root).items()
    }


def _all_terminals(root):
    terminals = []

    def walk(state):
        player = state.current_player()
        if player == TERMINAL:
            terminals.append(state)
            return
        branches = state.chance_outcomes() if player == CHANCE else tuple(
            (action, 1.0) for action in state.legal_actions()
        )
        for action, _ in branches:
            walk(state.child(action))

    walk(root)
    return terminals


def test_fixture_chance_mass_and_conditional_runouts():
    root = tiny_multistreet_root()
    assert sum(probability for _, probability in root.chance_outcomes()) == pytest.approx(1.0)
    dealt = root.child(root.chance_outcomes()[0][0])
    closed = dealt.child(Action("CHECK")).child(Action("CHECK"))
    assert closed.current_player() == CHANCE
    turn = closed.chance_outcomes()
    assert len(turn) == 2
    assert [probability for _, probability in turn] == pytest.approx([0.5, 0.5])
    after_turn = closed.child(turn[0][0])
    assert len(after_turn.board) == 4
    after_turn_closed = after_turn.child(Action("CHECK")).child(Action("CHECK"))
    river = after_turn_closed.chance_outcomes()
    assert len(river) == 1
    assert river[0][1] == pytest.approx(1.0)


def test_fixture_runouts_are_conditioned_on_private_blockers():
    base = tiny_multistreet_root().config
    config = replace(
        base,
        allowed_runouts=(parse_cards(("9s", "Kc")), parse_cards(("As", "Jd"))),
    )
    root = create_root(config)
    dealt = root.child(root.chance_outcomes()[0][0])
    chance = dealt.child(Action("CHECK")).child(Action("CHECK"))
    outcomes = chance.chance_outcomes()
    assert len(outcomes) == 1
    assert outcomes[0][0].amount == parse_cards(("9s",))[0]
    assert outcomes[0][1] == pytest.approx(1.0)


def test_fixture_audit_and_every_terminal_zero_sum():
    report = audit_game(tiny_multistreet_root(), max_nodes=20_000)
    assert report.nodes > 0
    terminals = _all_terminals(tiny_multistreet_root())
    assert terminals
    for state in terminals:
        values = state.returns()
        assert all(isfinite(value) for value in values)
        assert isclose(sum(values), 0.0, abs_tol=1e-12)


@pytest.mark.parametrize("profile_kind", ["uniform", "trained"])
@pytest.mark.parametrize("player", [0, 1])
def test_dynamic_best_response_matches_exhaustive_oracle(profile_kind, player):
    root = tiny_multistreet_root()
    if profile_kind == "uniform":
        profile = _uniform(root)
    else:
        profile = CFRSolver(root).train(100)
    dynamic_value, _ = best_response(root, profile, player)
    exhaustive_value, _ = exhaustive_best_response(root, profile, player)
    assert dynamic_value == pytest.approx(exhaustive_value, abs=1e-12)


def test_vanilla_reference_converges_on_fixture():
    root = tiny_multistreet_root()
    solver = CFRSolver(root)
    profile = solver.train(1_000)
    assert nash_conv(root, profile).nash_conv < 0.005


@pytest.mark.parametrize("seed", [42, 123, 999, 2024, 7777])
def test_mccfr_seed_matrix_value_agrees_with_vanilla(seed):
    root = tiny_multistreet_root()
    reference = CFRSolver(root)
    reference.train(1_000)
    expected = reference.values()[0]
    sampled = MCCFRSolver(tiny_multistreet_root(), seed=seed)
    sampled.train(5_000)
    assert sampled.values()[0] == pytest.approx(expected, abs=0.01)
