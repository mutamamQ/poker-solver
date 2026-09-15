from dataclasses import dataclass

import pytest

from poker_solver.audit import GameValidationError, audit_game
from poker_solver.kuhn import kuhn_root
from poker_solver.model import Action, CHANCE, TERMINAL


@dataclass(frozen=True)
class BadChance:
    terminal: bool = False
    def current_player(self): return TERMINAL if self.terminal else CHANCE
    def legal_actions(self): return () if self.terminal else (Action("x"), Action("y"))
    def chance_outcomes(self): return () if self.terminal else ((Action("x"), 0.7), (Action("y"), 0.7))
    def child(self, action): return BadChance(True)
    def information_state_key(self, player): raise ValueError
    def returns(self): return (0.0, 0.0)


@dataclass(frozen=True)
class BadTerminal:
    def current_player(self): return TERMINAL
    def legal_actions(self): return ()
    def chance_outcomes(self): return ()
    def child(self, action): raise ValueError
    def information_state_key(self, player): raise ValueError
    def returns(self): return (1.0, 1.0)


def test_valid_kuhn_audit_counts():
    report = audit_game(kuhn_root())
    assert report.nodes == 55
    assert report.terminals == 30
    assert report.infosets == 12
    assert report.max_depth == 4


def test_bad_chance_and_non_zero_sum_are_rejected():
    with pytest.raises(GameValidationError, match="chance"):
        audit_game(BadChance())
    with pytest.raises(GameValidationError, match="zero-sum"):
        audit_game(BadTerminal())


def test_node_limit_is_enforced():
    with pytest.raises(GameValidationError, match="max_nodes"):
        audit_game(kuhn_root(), max_nodes=10)
