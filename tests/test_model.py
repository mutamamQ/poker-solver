import pytest

from poker_solver.model import Action, CHANCE, TERMINAL, GameState, other_player


def test_action_is_hashable_ordered_and_validated():
    assert sorted((Action("bet", 2), Action("bet", 1), Action("check"))) == [
        Action("bet", 1), Action("bet", 2), Action("check")
    ]
    assert {Action("fold"): 1}[Action("fold")] == 1
    with pytest.raises(ValueError):
        Action("")
    with pytest.raises(ValueError):
        Action("bet", True)


def test_constants_and_player_helper():
    assert (CHANCE, TERMINAL) == (-1, -2)
    assert other_player(0) == 1 and other_player(1) == 0
    with pytest.raises(ValueError):
        other_player(CHANCE)


def test_protocol_is_runtime_checkable():
    class State:
        def current_player(self): return TERMINAL
        def legal_actions(self): return ()
        def chance_outcomes(self): return ()
        def child(self, action): raise ValueError
        def information_state_key(self, player): raise ValueError
        def returns(self): return (0.0, 0.0)
    assert isinstance(State(), GameState)
