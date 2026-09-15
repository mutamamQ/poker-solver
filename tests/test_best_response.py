from dataclasses import dataclass

import pytest

from poker_solver.best_response import best_response, nash_conv
from poker_solver.cfr import CFRSolver
from poker_solver.kuhn import kuhn_root
from poker_solver.model import Action, CHANCE, TERMINAL

D0 = Action("deal", 0)
D1 = Action("deal", 1)
G0 = Action("guess", 0)
G1 = Action("guess", 1)


@dataclass(frozen=True)
class HiddenBitState:
    bit: int | None = None
    guess: int | None = None

    def current_player(self):
        return CHANCE if self.bit is None else 1 if self.guess is None else TERMINAL
    def legal_actions(self):
        return (D0, D1) if self.bit is None else (G0, G1) if self.guess is None else ()
    def chance_outcomes(self):
        return ((D0, 0.5), (D1, 0.5)) if self.bit is None else ()
    def child(self, action):
        if action not in self.legal_actions(): raise ValueError
        return HiddenBitState(action.amount, None) if self.bit is None else HiddenBitState(self.bit, action.amount)
    def information_state_key(self, player):
        if self.current_player() != player: raise ValueError
        return ("hidden-guess", player)
    def returns(self):
        if self.current_player() != TERMINAL: raise ValueError
        p1 = 1.0 if self.bit == self.guess else -1.0
        return (-p1, p1)


def test_best_response_is_infoset_consistent_hidden_bit():
    root = HiddenBitState()
    profile = {("hidden-guess", 1): {G0: 0.5, G1: 0.5}}
    value, response = best_response(root, profile, 1)
    assert value == pytest.approx(0.0)
    assert len(response) == 1
    result = nash_conv(root, profile)
    assert result.nash_conv == pytest.approx(0.0)


def test_kuhn_nashconv_nonnegative_and_decreases_to_small_value():
    root = kuhn_root()
    early_solver = CFRSolver(root)
    early = nash_conv(root, early_solver.train(20)).nash_conv
    late_solver = CFRSolver(root)
    late = nash_conv(root, late_solver.train(5_000)).nash_conv
    assert late >= 0
    assert late < early
    assert late < 0.03


def test_invalid_profile_rejected():
    root = HiddenBitState()
    with pytest.raises(ValueError):
        nash_conv(root, {("hidden-guess", 1): {G0: 0.2, G1: 0.2}})
