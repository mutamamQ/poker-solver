"""Independent automatic-versus-explicit S1 continuation oracles."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite

import pytest

from poker_solver.allstreet import (
    AllStreetPostflopConfig,
    create_allstreet_root,
    solve_allstreet_postflop,
)
from poker_solver.best_response import nash_conv
from poker_solver.cards import parse_card
from poker_solver.cfr import CFRSolver
from poker_solver.equity import WeightedCombo
from poker_solver.evaluator import evaluate_seven
from poker_solver.model import Action, CHANCE, TERMINAL


_DEAL = Action("DEAL", 0)
_CHECK = Action("CHECK")
_RAISE = Action("RAISE", 1)
_FOLD = Action("FOLD")
_CALL = Action("CALL", 1)


def _cards2(first: str, second: str) -> tuple[int, int]:
    return (parse_card(first), parse_card(second))


def _cards3(first: str, second: str, third: str) -> tuple[int, int, int]:
    return (parse_card(first), parse_card(second), parse_card(third))


def _config(*, strategic: bool) -> AllStreetPostflopConfig:
    runouts = ((_cards2("9s", "Kc")),) if strategic else (
        _cards2("9s", "Kc"),
        _cards2("Tc", "Jd"),
    )
    return AllStreetPostflopConfig(
        version="allstreet-postflop-v1",
        starting_board=_cards3("2c", "3d", "4h"),
        initial_dead_pot=2,
        effective_stack=1,
        player0_combos=(WeightedCombo(_cards2("As", "5s"), 1.0),),
        player1_combos=(WeightedCombo(_cards2("Kh", "Qh"), 1.0),),
        allowed_runouts=runouts,
        betting_mode="pot-limit",
        wager_targets=(1,) if strategic else (0,),
        max_nodes=10_000,
        max_depth=64,
    )


def _manual_showdown_ev(config: AllStreetPostflopConfig) -> float:
    """Enumerate terminal cards without invoking either solve representation."""
    hand0 = config.player0_combos[0].cards
    hand1 = config.player1_combos[0].cards
    utilities: list[float] = []
    for runout in config.allowed_runouts:
        board = config.starting_board + runout
        rank0 = evaluate_seven(hand0 + board)
        rank1 = evaluate_seven(hand1 + board)
        award0 = 2 if rank0 > rank1 else 0 if rank1 > rank0 else 1
        utilities.append(award0 - 1)
    return sum(utilities) / len(utilities)


def _manual_strategic_value() -> float:
    """Backward-induct the singleton, one-chip continuation independently.

    Player 0 wins every showdown. At any street, betting gives player 0
    min(+1 on a fold, +2 on a call) = +1. Checking gives player 1 the
    choice between continuing at +1 for player 0 and betting into a call
    for +2, hence also +1. Backward induction from river to flop is +1.
    """
    showdown_after_call = 2.0
    fold_to_player0_bet = 1.0
    fold_to_player1_bet = -1.0
    value = 1.0  # river check/check showdown
    for _street in ("river", "turn", "flop"):
        p0_facing_bet = max(fold_to_player1_bet, showdown_after_call)
        after_p0_check = min(value, p0_facing_bet)
        after_p0_bet = min(fold_to_player0_bet, showdown_after_call)
        value = max(after_p0_check, after_p0_bet)
    return value


@dataclass(frozen=True, slots=True)
class _ExplicitContinuationState:
    """Separate test-only flop representation backed by manual leaves."""

    game: str
    node: str = "deal"
    utility0: float = 0.0

    def current_player(self) -> int:
        return {
            "deal": CHANCE,
            "p0": 0,
            "p1_forced": 1,
            "p1_after_check": 1,
            "p1_facing_bet": 1,
            "p0_facing_bet": 0,
            "terminal": TERMINAL,
        }[self.node]

    def legal_actions(self) -> tuple[Action, ...]:
        return {
            "deal": (_DEAL,),
            "p0": (_CHECK,) if self.game == "structural" else (_CHECK, _RAISE),
            "p1_forced": (_CHECK,),
            "p1_after_check": (_CHECK, _RAISE),
            "p1_facing_bet": (_FOLD, _CALL),
            "p0_facing_bet": (_FOLD, _CALL),
            "terminal": (),
        }[self.node]

    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]:
        return ((_DEAL, 1.0),) if self.node == "deal" else ()

    def child(self, action: Action) -> "_ExplicitContinuationState":
        if action not in self.legal_actions():
            raise ValueError(f"illegal explicit action {action!r} at {self.node}")
        if self.node == "deal":
            return _ExplicitContinuationState(self.game, "p0")
        if self.game == "structural":
            if self.node == "p0":
                return _ExplicitContinuationState(self.game, "p1_forced")
            return _ExplicitContinuationState(self.game, "terminal", 1.0)
        if self.node == "p0":
            next_node = "p1_after_check" if action == _CHECK else "p1_facing_bet"
            return _ExplicitContinuationState(self.game, next_node)
        if self.node == "p1_after_check":
            if action == _CHECK:
                return _ExplicitContinuationState(self.game, "terminal", _manual_strategic_value())
            return _ExplicitContinuationState(self.game, "p0_facing_bet")
        if self.node == "p1_facing_bet":
            utility = 1.0 if action == _FOLD else 2.0
            return _ExplicitContinuationState(self.game, "terminal", utility)
        if self.node == "p0_facing_bet":
            utility = -1.0 if action == _FOLD else 2.0
            return _ExplicitContinuationState(self.game, "terminal", utility)
        raise ValueError(f"terminal explicit node has no child: {self.node}")

    def information_state_key(self, player: int):
        if player != self.current_player() or player not in (0, 1):
            raise ValueError("information key requires the acting decision player")
        return ("explicit-continuation-v1", self.game, self.node, player)

    def returns(self) -> tuple[float, float]:
        if self.node != "terminal":
            raise ValueError("returns require an explicit terminal")
        return (self.utility0, -self.utility0)


def _explicit_metric(game: str, iterations: int):
    root = _ExplicitContinuationState(game)
    strategy = CFRSolver(root).train(iterations)
    return strategy, nash_conv(root, strategy)


def _assert_normalized(strategy) -> None:
    assert strategy
    for policy in strategy.values():
        assert policy
        assert all(isfinite(probability) and probability >= 0 for probability in policy.values())
        assert isclose(sum(policy.values()), 1.0, abs_tol=1e-12)


def _terminals(state):
    player = state.current_player()
    if player == TERMINAL:
        yield state
        return
    branches = state.chance_outcomes() if player == CHANCE else (
        (action, 1.0) for action in state.legal_actions()
    )
    for action, _probability in branches:
        yield from _terminals(state.child(action))


def test_structural_oracle_is_exact_and_non_circular():
    config = _config(strategic=False)
    manual = _manual_showdown_ev(config)
    assert manual == 1.0

    automatic = solve_allstreet_postflop(config, algorithm="vanilla-cfr", iterations=20)
    explicit_strategy, explicit = _explicit_metric("structural", 20)

    assert automatic.values[0] == pytest.approx(manual, abs=1e-12)
    assert explicit.values[0] == pytest.approx(manual, abs=1e-12)
    assert automatic.nash_conv == pytest.approx(0.0, abs=1e-12)
    assert explicit.nash_conv == pytest.approx(0.0, abs=1e-12)
    _assert_normalized(automatic.strategy)
    _assert_normalized(explicit_strategy)


def test_strategic_oracle_uses_independent_backward_induction_bound():
    config = _config(strategic=True)
    equilibrium = _manual_strategic_value()
    assert _manual_showdown_ev(config) == 1.0
    assert equilibrium == 1.0

    automatic = solve_allstreet_postflop(config, algorithm="vanilla-cfr", iterations=1_000)
    explicit_strategy, explicit = _explicit_metric("strategic", 1_000)
    delta_num = 1e-12
    bound = automatic.nash_conv + explicit.nash_conv + delta_num

    assert abs(automatic.values[0] - explicit.values[0]) <= bound
    assert abs(automatic.values[0] - equilibrium) <= automatic.nash_conv + delta_num
    assert abs(explicit.values[0] - equilibrium) <= explicit.nash_conv + delta_num
    _assert_normalized(automatic.strategy)
    _assert_normalized(explicit_strategy)


def test_strategic_convergence_sweep_confirms_trend():
    config = _config(strategic=True)
    totals: list[float] = []
    gaps: list[float] = []
    for iterations in (20, 100, 500):
        automatic = solve_allstreet_postflop(
            config, algorithm="vanilla-cfr", iterations=iterations
        )
        _strategy, explicit = _explicit_metric("strategic", iterations)
        totals.append(automatic.nash_conv + explicit.nash_conv)
        gaps.append(abs(automatic.values[0] - explicit.values[0]))
        assert gaps[-1] <= totals[-1] + 1e-12
    assert totals[-1] < totals[0]
    assert gaps[-1] < gaps[0]


def test_oracle_terminals_are_finite_and_zero_sum():
    for strategic in (False, True):
        terminals = tuple(_terminals(create_allstreet_root(_config(strategic=strategic))))
        assert terminals
        for terminal in terminals:
            values = terminal.returns()
            assert all(isfinite(value) for value in values)
            assert sum(values) == pytest.approx(0.0, abs=1e-12)


def test_oracle_vanilla_runs_are_deterministic():
    config = _config(strategic=True)
    first = solve_allstreet_postflop(config, algorithm="vanilla-cfr", iterations=100)
    second = solve_allstreet_postflop(config, algorithm="vanilla-cfr", iterations=100)
    assert first.values == second.values
    assert first.nash_conv == second.nash_conv
    assert first.strategy == second.strategy