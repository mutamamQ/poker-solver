"""Behavioral RED contracts for the bounded N-player betting round."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from poker_solver.model import Action, TERMINAL
from poker_solver.preflop import WeightedCombo
from poker_solver.nplayer_postflop import (
    NPlayerPostflopConfig,
    NPlayerPublicAction,
    create_nplayer_postflop_root,
)


def _config(
    n: int = 4,
    *,
    button: int = 0,
    starting_stacks: tuple[int, ...] | None = None,
    max_raises: int = 2,
) -> NPlayerPostflopConfig:
    deal = tuple((3 + 2 * seat, 4 + 2 * seat) for seat in range(n))
    ranges = tuple((WeightedCombo(cards, Fraction(1)),) for cards in deal)
    return NPlayerPostflopConfig(
        version="nplayer-postflop-v1",
        num_players=n,
        button=button,
        starting_stacks=starting_stacks or tuple(20 for _ in range(n)),
        contributions=tuple(2 for _ in range(n)),
        folded=tuple(False for _ in range(n)),
        board=(0, 1, 2),
        ranges=ranges,
        wager_targets=(4, 8),
        max_raises=max_raises,
        max_deals=1,
        max_nodes=20_000,
        odd_chip_order=tuple(range(n)),
        showdown_ranks={deal: tuple(range(n, 0, -1))},
        rake_policy=None,
    )


def _dealt(config: NPlayerPostflopConfig | None = None):
    root = create_nplayer_postflop_root(config or _config())
    outcomes = root.chance_outcomes()
    assert len(outcomes) == 1
    return root, root.child(outcomes[0][0])


def test_root_and_dealt_state_use_clockwise_pending_order() -> None:
    root, state = _dealt(_config(button=0))
    assert root.pending == (1, 2, 3, 0)
    assert root.street_committed == (0, 0, 0, 0)
    assert root.pot == sum(root.total_contributed) == 8
    assert state.pending == (1, 2, 3, 0)
    assert state.current_player() == state.pending[0] == 1


def test_check_transition_is_actor_labelled_and_fold_is_not_legal() -> None:
    _, state = _dealt()
    actions = state.legal_actions()
    assert Action("CHECK") in actions
    assert Action("FOLD") not in actions
    checked = state.child(Action("CHECK"))
    assert checked.pending == (2, 3, 0)
    assert checked.current_player() == 2
    assert checked.history[-1] == NPlayerPublicAction(actor=1, action=Action("CHECK"))


def test_full_raise_reopens_and_call_transfers_absolute_delta() -> None:
    _, state = _dealt()
    assert Action("RAISE", 4) in state.legal_actions()
    raised = state.child(Action("RAISE", 4))
    assert raised.street_committed == (0, 4, 0, 0)
    assert raised.total_contributed == (2, 6, 2, 2)
    assert raised.pot == 12
    assert raised.pending == (2, 3, 0)
    assert raised.last_raise_increment == 4
    assert raised.raise_count == 1
    assert raised.can_raise == (True, True, True, True)

    legal = raised.legal_actions()
    assert Action("FOLD") in legal
    assert Action("CALL", 4) in legal
    assert Action("CHECK") not in legal
    called = raised.child(Action("CALL", 4))
    assert called.street_committed == (0, 4, 4, 0)
    assert called.total_contributed == (2, 6, 6, 2)
    assert called.remaining[2] == 14
    assert called.pot == 16
    assert called.pending == (3, 0)


def test_short_all_in_does_not_reopen_for_players_who_already_acted() -> None:
    config = _config(starting_stacks=(20, 8, 20, 20))
    _, state = _dealt(config)
    state = state.child(Action("CHECK"))        # seat 1
    state = state.child(Action("RAISE", 4))     # seat 2, full raise
    state = state.child(Action("CALL", 4))      # seat 3
    state = state.child(Action("CALL", 4))      # seat 0
    assert state.current_player() == 1
    assert Action("RAISE", 6) in state.legal_actions()

    short = state.child(Action("RAISE", 6))
    assert short.remaining[1] == 0
    assert short.street_committed[1] == 6
    assert short.last_raise_increment == 4
    assert short.pending == (2, 3, 0)
    assert short.can_raise == (False, False, False, False)
    assert all(action.kind != "RAISE" for action in short.legal_actions())


def test_round_closes_on_last_fold_or_empty_pending() -> None:
    _, heads_up = _dealt(_config(n=2, button=0))
    heads_up = heads_up.child(Action("CHECK"))
    heads_up = heads_up.child(Action("RAISE", 4))
    terminal = heads_up.child(Action("FOLD"))
    assert terminal.current_player() == TERMINAL
    assert terminal.pending == ()
    assert len(terminal.returns()) == 2

    _, state = _dealt()
    for _ in range(4):
        state = state.child(Action("CHECK"))
    assert state.current_player() == TERMINAL
    assert state.pending == ()
    assert len(state.returns()) == 4
    assert sum(state.returns()) == 0.0


def test_direct_state_invariants_reject_corrupt_ledgers_and_pending() -> None:
    _, state = _dealt()
    with pytest.raises(ValueError, match="pot"):
        replace(state, pot=state.pot + 1)
    with pytest.raises(ValueError, match="pending"):
        replace(state, pending=(state.pending[0], state.pending[0]))
    with pytest.raises(ValueError, match="starting|contribution|remaining"):
        replace(state, remaining=(999,) + state.remaining[1:])


def test_every_branch_respects_structural_decision_depth_bound() -> None:
    config = _config(n=4, max_raises=2)
    _, initial = _dealt(config)
    maximum = 0
    stack = [(initial, 0)]
    while stack:
        state, depth = stack.pop()
        maximum = max(maximum, depth)
        if state.current_player() == TERMINAL:
            continue
        stack.extend((state.child(action), depth + 1) for action in state.legal_actions())
    assert maximum <= config.num_players + config.max_raises * (config.num_players - 1)