"""Permanent S2-I2 typed solve, bounds, reach, and diagnostic contracts."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Hashable, Mapping

import pytest

from poker_solver.model import Action, CHANCE, TERMINAL
from poker_solver.nplayer import NPlayerCFRSolver
from poker_solver.nplayer_postflop import NPlayerPostflopConfig, create_nplayer_postflop_root
from poker_solver.preflop import WeightedCombo


def _config(n: int, *, folded: tuple[bool, ...] | None = None) -> NPlayerPostflopConfig:
    deal = tuple((3 + 2 * seat, 4 + 2 * seat) for seat in range(n))
    return NPlayerPostflopConfig(
        version="nplayer-postflop-v1",
        num_players=n,
        button=0,
        starting_stacks=(20,) * n,
        contributions=(2,) * n,
        folded=folded or (False,) * n,
        board=(0, 1, 2),
        ranges=tuple(((WeightedCombo(cards, Fraction(1)),)) for cards in deal),
        wager_targets=(4,),
        max_raises=1,
        max_deals=1,
        max_nodes=2_000,
        odd_chip_order=tuple(range(n)),
        showdown_ranks={deal: tuple(range(n, 0, -1))},
    )


def _solve(config: NPlayerPostflopConfig, **kwargs):
    from poker_solver.nplayer_postflop import solve_nplayer_postflop

    return solve_nplayer_postflop(config=config, algorithm="vanilla-cfr", **kwargs)


def _assert_normalized(strategy: Mapping[Hashable, Mapping[Action, float]]) -> None:
    for policy in strategy.values():
        assert policy
        assert set(policy)
        assert all(probability >= 0.0 for probability in policy.values())
        assert sum(policy.values()) == pytest.approx(1.0, abs=1e-12)


def test_solve_result_contract_exists_in_defining_module() -> None:
    from poker_solver.nplayer_postflop import NPlayerPostflopSolveResult

    assert NPlayerPostflopSolveResult.__module__ == "poker_solver.nplayer_postflop"


def test_four_player_solve_is_deterministic_normalized_and_detached() -> None:
    config = _config(4)
    first = _solve(config, iterations=3)
    second = _solve(config, iterations=3)
    assert first.algorithm == "vanilla-cfr"
    assert first.iterations == 3
    assert first.expected_values == second.expected_values
    assert len(first.expected_values) == 4
    assert first.strategy == second.strategy
    assert isinstance(first.strategy, dict)
    _assert_normalized(first.strategy)
    if first.strategy:
        key = next(iter(first.strategy))
        first.strategy[key].clear()
        assert second.strategy[key]
        assert _solve(config, iterations=3).strategy == second.strategy


def test_five_player_solve_returns_five_values() -> None:
    config = _config(5, folded=(False, False, True, True, True))
    result = _solve(config, iterations=2)
    assert len(result.expected_values) == 5
    assert all(isinstance(value, float) for value in result.expected_values)
    _assert_normalized(result.strategy)


def test_nine_player_tiny_solve_is_bounded() -> None:
    config = _config(9, folded=(False, False, True, True, True, True, True, True, True))
    result = _solve(config, iterations=2)
    assert len(result.expected_values) == 9
    _assert_normalized(result.strategy)


def test_solver_constructor_forwards_node_bound() -> None:
    root = create_nplayer_postflop_root(_config(2))
    with pytest.raises(ValueError, match="node bound"):
        NPlayerCFRSolver(root, max_nodes=1, max_depth=100)


def test_solver_constructor_forwards_depth_bound() -> None:
    root = create_nplayer_postflop_root(_config(2))
    with pytest.raises(ValueError, match="depth bound"):
        NPlayerCFRSolver(root, max_nodes=1_000, max_depth=1)


CONTINUE = Action("CONTINUE")
STOP = Action("STOP")
WIN = Action("WIN")
LOSE = Action("LOSE")


@dataclass(frozen=True)
class FivePlayerReachGame:
    """Only four successive half-probability continues reach player four."""

    stage: int = 0
    terminal_values: tuple[float, ...] | None = None

    def num_players(self) -> int:
        return 5

    def current_player(self) -> int:
        if self.terminal_values is not None:
            return TERMINAL
        return self.stage

    def legal_actions(self) -> tuple[Action, ...]:
        return (WIN, LOSE) if self.stage == 4 else (CONTINUE, STOP)

    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]:
        return ()

    def child(self, action: Action) -> "FivePlayerReachGame":
        if self.stage < 4:
            if action == STOP:
                return FivePlayerReachGame(terminal_values=(0.0,) * 5)
            if action == CONTINUE:
                return FivePlayerReachGame(stage=self.stage + 1)
        elif action == WIN:
            return FivePlayerReachGame(terminal_values=(0.0, 0.0, 0.0, 0.0, 16.0))
        elif action == LOSE:
            return FivePlayerReachGame(terminal_values=(0.0, 0.0, 0.0, 0.0, -16.0))
        raise ValueError("illegal action")

    def information_state_key(self, player: int) -> Hashable:
        return ("reach", player)

    def returns(self) -> tuple[float, ...]:
        if self.terminal_values is None:
            raise ValueError("non-terminal")
        return self.terminal_values


def test_exact_five_player_counterfactual_reach_scaling() -> None:
    solver = NPlayerCFRSolver(FivePlayerReachGame(), max_nodes=100, max_depth=10)
    solver.train(1)
    data = solver.infosets[("reach", 4)]
    # Opponent reach is (1/2)^4. Action values are +16/-16 and node value 0.
    assert data.regrets[WIN] == pytest.approx(1.0, abs=1e-12)
    assert data.regrets[LOSE] == pytest.approx(-1.0, abs=1e-12)


def _infosets(root) -> dict[Hashable, tuple[int, tuple[Action, ...]]]:
    result: dict[Hashable, tuple[int, tuple[Action, ...]]] = {}

    def walk(state) -> None:
        player = state.current_player()
        if player == TERMINAL:
            return
        if player == CHANCE:
            for action, _ in state.chance_outcomes():
                walk(state.child(action))
            return
        key = state.information_state_key(player)
        result[key] = (player, state.legal_actions())
        for action in state.legal_actions():
            walk(state.child(action))

    walk(root)
    return result


def _values(root, strategy: Mapping[Hashable, Mapping[Action, float]]) -> tuple[float, ...]:
    n = root.num_players()

    def walk(state) -> tuple[float, ...]:
        player = state.current_player()
        if player == TERMINAL:
            return tuple(float(value) for value in state.returns())
        if player == CHANCE:
            total = [0.0] * n
            for action, probability in state.chance_outcomes():
                child = walk(state.child(action))
                for seat in range(n):
                    total[seat] += probability * child[seat]
            return tuple(total)
        key = state.information_state_key(player)
        total = [0.0] * n
        for action in state.legal_actions():
            child = walk(state.child(action))
            for seat in range(n):
                total[seat] += strategy[key][action] * child[seat]
        return tuple(total)

    return walk(root)


def _manual_deviation(root, strategy):
    infosets = _infosets(root)
    baseline = _values(root, strategy)
    best: list[float] = []
    for player in range(root.num_players()):
        owned = [(key, actions) for key, (owner, actions) in infosets.items() if owner == player]
        player_best = baseline[player]
        for choices in product(*(actions for _, actions in owned)):
            deviated = {key: dict(policy) for key, policy in strategy.items()}
            for (key, actions), choice in zip(owned, choices, strict=True):
                deviated[key] = {action: float(action == choice) for action in actions}
            player_best = max(player_best, _values(root, deviated)[player])
        best.append(player_best)
    incentives = tuple(max(0.0, value - baseline[i]) for i, value in enumerate(best))
    return baseline, tuple(best), incentives


def test_five_player_exact_unilateral_deviation_certificate() -> None:
    config = _config(5, folded=(False, False, True, True, True))
    root = create_nplayer_postflop_root(config)
    result = _solve(
        config,
        iterations=2,
        include_deviation_certificate=True,
        max_pure_strategies=100,
    )
    baseline, best, incentives = _manual_deviation(root, result.strategy)
    certificate = result.certificate
    assert certificate is not None
    assert certificate.values == pytest.approx(baseline)
    assert certificate.best_response_values == pytest.approx(best)
    assert certificate.incentives == pytest.approx(incentives)
    assert certificate.total_incentive == pytest.approx(sum(incentives))
    assert certificate.provenance == "exhaustive finite pure unilateral deviations; diagnostic only"


def test_deviation_cap_fails_closed() -> None:
    config = _config(5, folded=(False, False, True, True, True))
    with pytest.raises(ValueError, match="pure-strategy bound exceeded"):
        _solve(
            config,
            iterations=1,
            include_deviation_certificate=True,
            max_pure_strategies=1,
        )
