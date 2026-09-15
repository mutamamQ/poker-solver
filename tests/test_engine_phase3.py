"""Phase-3 engine dispatch and truthful mode tests."""

from dataclasses import dataclass

import pytest

from poker_solver.engine import EngineConfig, solve_engine
from poker_solver.model import Action, CHANCE, TERMINAL


@dataclass(frozen=True)
class CheckdownGame:
    history: tuple[Action, ...] = ()

    def num_players(self):
        return 2

    def current_player(self):
        if not self.history:
            return CHANCE
        if len(self.history) == 1:
            return 0
        if len(self.history) == 2:
            return 1
        return TERMINAL

    def chance_outcomes(self):
        if not self.history:
            return ((Action("GOOD"), 0.25), (Action("BAD"), 0.75))
        return ()

    def legal_actions(self):
        if len(self.history) in (1, 2):
            return (Action("CHECK"), Action("BET", 1))
        return ()

    def child(self, action):
        if self.current_player() == CHANCE or action in self.legal_actions():
            return CheckdownGame(self.history + (action,))
        raise ValueError("illegal action")

    def information_state_key(self, player):
        return (player, tuple(action.kind for action in self.history))

    def returns(self):
        if self.current_player() != TERMINAL:
            raise ValueError("non-terminal")
        value = 2.0 if self.history[0].kind == "GOOD" else -1.0
        if any(action.kind == "BET" for action in self.history[1:]):
            value *= 10
        return (value, -value)


@dataclass(frozen=True)
class ThreePlayerGame:
    history: tuple[Action, ...] = ()

    def num_players(self):
        return 3

    def current_player(self):
        return len(self.history) if len(self.history) < 3 else TERMINAL

    def chance_outcomes(self):
        return ()

    def legal_actions(self):
        return (Action("A"), Action("B")) if len(self.history) < 3 else ()

    def child(self, action):
        if action not in self.legal_actions():
            raise ValueError("illegal action")
        return ThreePlayerGame(self.history + (action,))

    def information_state_key(self, player):
        return (player, self.history)

    def returns(self):
        score = sum(action.kind == "A" for action in self.history)
        return (float(score), float(3 - score), 0.0)


def test_checkdown_rollout_follows_only_checks_and_is_labeled_approximate():
    result = solve_engine(CheckdownGame(), EngineConfig("checkdown-equity"))
    assert result.values == pytest.approx((-0.25, 0.25))
    assert result.strategy == {}
    assert result.approximate is True
    assert result.provenance == "check-only rollout; ignores future betting"


def test_checkdown_fails_if_a_decision_has_no_check():
    @dataclass(frozen=True)
    class NoCheck(CheckdownGame):
        def legal_actions(self):
            return (Action("BET", 1),) if self.current_player() in (0, 1) else ()

        def child(self, action):
            return NoCheck(self.history + (action,))

    with pytest.raises(ValueError, match="CHECK"):
        solve_engine(NoCheck(), EngineConfig("checkdown-equity"))


def test_classic_dispatch_matches_nplayer_solver_on_finite_game():
    from poker_solver.nplayer import NPlayerCFRSolver, expected_values_nplayer

    root = ThreePlayerGame()
    direct = NPlayerCFRSolver(root)
    strategy = direct.train(5)
    expected = expected_values_nplayer(root, strategy)
    result = solve_engine(root, EngineConfig("classic", iterations=5))
    assert result.strategy == strategy
    assert result.values == pytest.approx(expected)
    assert result.approximate is False
    assert result.provenance == "complete configured finite-tree CFR"


def test_fast_ddls_fails_closed_without_neural_model():
    with pytest.raises(ValueError, match="neural continuation"):
        solve_engine(CheckdownGame(), EngineConfig("fast-ddls"))


@pytest.mark.parametrize("mode", ["", "CLASSIC", "unknown", 1, True])
def test_engine_mode_and_limits_are_strict(mode):
    with pytest.raises(ValueError):
        EngineConfig(mode)
    with pytest.raises(ValueError):
        EngineConfig("classic", iterations=True)
    with pytest.raises(ValueError):
        EngineConfig("classic", max_nodes=0)
    with pytest.raises(ValueError):
        EngineConfig("classic", max_depth=float("inf"))


def test_checkdown_node_and_depth_bounds_fail_closed():
    with pytest.raises(ValueError, match="node bound"):
        solve_engine(CheckdownGame(), EngineConfig("checkdown-equity", max_nodes=1))
    with pytest.raises(ValueError, match="depth bound"):
        solve_engine(CheckdownGame(), EngineConfig("checkdown-equity", max_depth=1))
