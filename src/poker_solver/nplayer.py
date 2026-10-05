"""Deterministic full-tree CFR for finite games with two to nine players."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from math import isfinite, prod
from typing import Hashable, Mapping, Protocol, runtime_checkable

from .model import Action, CHANCE, TERMINAL


@runtime_checkable
class NPlayerGameState(Protocol):
    def current_player(self) -> int: ...
    def num_players(self) -> int: ...
    def legal_actions(self) -> tuple[Action, ...]: ...
    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]: ...
    def child(self, action: Action) -> "NPlayerGameState": ...
    def information_state_key(self, player: int) -> Hashable: ...
    def returns(self) -> tuple[float, ...]: ...


@dataclass(slots=True)
class NPlayerInfoData:
    player: int
    actions: tuple[Action, ...]
    regrets: dict[Action, float] = field(init=False)
    strategy_sum: dict[Action, float] = field(init=False)

    def __post_init__(self) -> None:
        self.regrets = {action: 0.0 for action in self.actions}
        self.strategy_sum = {action: 0.0 for action in self.actions}


def _player_count(root: NPlayerGameState) -> int:
    count = root.num_players()
    if isinstance(count, bool) or not isinstance(count, int) or not 2 <= count <= 9:
        raise ValueError("num_players must be an integer from 2 to 9 players")
    return count


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def collect_nplayer_infosets(
    root: NPlayerGameState,
    *,
    max_nodes: int = 100_000,
    max_depth: int = 512,
) -> dict[Hashable, tuple[int, tuple[Action, ...]]]:
    """Validate a finite game and return its consistent information sets."""
    players = _player_count(root)
    if isinstance(max_nodes, bool) or not isinstance(max_nodes, int) or max_nodes <= 0:
        raise ValueError("max_nodes must be a positive integer")
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth <= 0:
        raise ValueError("max_depth must be a positive integer")
    infosets: dict[Hashable, tuple[int, tuple[Action, ...]]] = {}
    visited = 0

    def walk(state: NPlayerGameState, ancestors: frozenset[int], depth: int) -> None:
        nonlocal visited
        if depth > max_depth:
            raise ValueError("game exceeds finite depth bound")
        visited += 1
        if visited > max_nodes:
            raise ValueError("game exceeds finite node bound")
        identity = id(state)
        if identity in ancestors:
            raise ValueError("cycle detected in game tree")
        next_ancestors = ancestors | {identity}
        player = state.current_player()
        if isinstance(player, bool) or not isinstance(player, int):
            raise ValueError("current player must be an integer")
        if player == TERMINAL:
            values = state.returns()
            if not isinstance(values, tuple) or len(values) != players:
                raise ValueError("terminal return dimension must equal num_players")
            for value in values:
                _finite_number(value, "terminal return")
            return
        if player == CHANCE:
            outcomes = state.chance_outcomes()
            if not isinstance(outcomes, tuple) or not outcomes:
                raise ValueError("chance node must have outcomes")
            actions: set[Action] = set()
            total = 0.0
            for action, probability in outcomes:
                if not isinstance(action, Action) or action in actions:
                    raise ValueError("chance actions must be unique Action values")
                actions.add(action)
                probability = _finite_number(probability, "finite chance probability")
                if probability < 0:
                    raise ValueError("chance probability must be non-negative")
                total += probability
                walk(state.child(action), next_ancestors, depth + 1)
            if abs(total - 1.0) > 1e-12:
                raise ValueError("chance probabilities must sum to 1")
            return
        if not 0 <= player < players:
            raise ValueError("current player is outside player range")
        actions = state.legal_actions()
        if (
            not isinstance(actions, tuple)
            or not actions
            or any(not isinstance(action, Action) for action in actions)
            or len(set(actions)) != len(actions)
        ):
            raise ValueError("decision node actions must be non-empty unique Action values")
        key = state.information_state_key(player)
        try:
            hash(key)
        except TypeError as exc:
            raise ValueError("information-state key must be hashable") from exc
        observed = (player, actions)
        if key in infosets and infosets[key] != observed:
            raise ValueError("information set owner/action mismatch")
        infosets[key] = observed
        for action in actions:
            walk(state.child(action), next_ancestors, depth + 1)

    walk(root, frozenset(), 0)
    return infosets


def _regret_matching(data: NPlayerInfoData) -> dict[Action, float]:
    positives = {action: max(0.0, data.regrets[action]) for action in data.actions}
    total = sum(positives.values())
    if total > 0:
        return {action: positives[action] / total for action in data.actions}
    uniform = 1.0 / len(data.actions)
    return {action: uniform for action in data.actions}


class NPlayerCFRSolver:
    """Synchronous vanilla CFR over a validated finite N-player tree."""

    def __init__(
        self,
        root: NPlayerGameState,
        *,
        max_nodes: int = 100_000,
        max_depth: int = 512,
    ) -> None:
        self.root = root
        self.num_players = _player_count(root)
        self.infosets = {
            key: NPlayerInfoData(player, actions)
            for key, (player, actions) in collect_nplayer_infosets(
                root,
                max_nodes=max_nodes,
                max_depth=max_depth,
            ).items()
        }
        self.iterations = 0

    def current_strategy(self) -> dict[Hashable, dict[Action, float]]:
        return {key: _regret_matching(data) for key, data in self.infosets.items()}

    def average_strategy(self) -> dict[Hashable, dict[Action, float]]:
        result: dict[Hashable, dict[Action, float]] = {}
        for key, data in self.infosets.items():
            total = sum(data.strategy_sum.values())
            if total > 0:
                result[key] = {
                    action: data.strategy_sum[action] / total for action in data.actions
                }
            else:
                uniform = 1.0 / len(data.actions)
                result[key] = {action: uniform for action in data.actions}
        return result

    def train(self, iterations: int) -> dict[Hashable, dict[Action, float]]:
        if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations <= 0:
            raise ValueError("iterations must be a positive integer")
        for _ in range(iterations):
            strategy = self.current_strategy()
            deltas = [
                {key: {action: 0.0 for action in data.actions} for key, data in self.infosets.items()}
                for _ in range(self.num_players)
            ]
            for updating in range(self.num_players):
                self._walk(
                    self.root,
                    updating,
                    [1.0] * self.num_players,
                    1.0,
                    strategy,
                    deltas[updating],
                    accumulate=(updating == 0),
                )
            for key, data in self.infosets.items():
                for action in data.actions:
                    data.regrets[action] += deltas[data.player][key][action]
            self.iterations += 1
        return self.average_strategy()

    def _walk(
        self,
        state: NPlayerGameState,
        updating: int,
        reaches: list[float],
        chance_reach: float,
        strategy: Mapping[Hashable, Mapping[Action, float]],
        deltas: dict[Hashable, dict[Action, float]],
        *,
        accumulate: bool,
    ) -> float:
        player = state.current_player()
        if player == TERMINAL:
            return float(state.returns()[updating])
        if player == CHANCE:
            return sum(
                probability
                * self._walk(
                    state.child(action),
                    updating,
                    reaches,
                    chance_reach * probability,
                    strategy,
                    deltas,
                    accumulate=accumulate,
                )
                for action, probability in state.chance_outcomes()
            )
        actions = state.legal_actions()
        key = state.information_state_key(player)
        policy = strategy[key]
        if accumulate:
            owner_reach = reaches[player]
            data = self.infosets[key]
            for action in actions:
                data.strategy_sum[action] += owner_reach * policy[action]
        action_values: dict[Action, float] = {}
        for action in actions:
            child_reaches = reaches.copy()
            child_reaches[player] *= policy[action]
            action_values[action] = self._walk(
                state.child(action), updating, child_reaches, chance_reach,
                strategy, deltas, accumulate=accumulate,
            )
        value = sum(policy[action] * action_values[action] for action in actions)
        if player == updating:
            counterfactual = chance_reach
            for opponent, reach in enumerate(reaches):
                if opponent != player:
                    counterfactual *= reach
            for action in actions:
                deltas[key][action] += counterfactual * (action_values[action] - value)
        return value


def expected_values_nplayer(
    root: NPlayerGameState,
    strategy: Mapping[Hashable, Mapping[Action, float]],
) -> tuple[float, ...]:
    """Return expected utilities for a complete strategy profile."""
    players = _player_count(root)
    infosets = collect_nplayer_infosets(root)
    if set(strategy) != set(infosets):
        raise ValueError("strategy keys must exactly match game information sets")
    for key, (_, actions) in infosets.items():
        policy = strategy[key]
        if set(policy) != set(actions):
            raise ValueError("strategy actions must exactly match legal actions")
        total = 0.0
        for probability in policy.values():
            probability = _finite_number(probability, "strategy probability")
            if probability < 0:
                raise ValueError("strategy probability must be non-negative")
            total += probability
        if abs(total - 1.0) > 1e-12:
            raise ValueError("strategy probabilities must sum to 1")

    def walk(state: NPlayerGameState) -> tuple[float, ...]:
        player = state.current_player()
        if player == TERMINAL:
            return tuple(float(value) for value in state.returns())
        if player == CHANCE:
            result = [0.0] * players
            for action, probability in state.chance_outcomes():
                child_values = walk(state.child(action))
                for index in range(players):
                    result[index] += probability * child_values[index]
            return tuple(result)
        key = state.information_state_key(player)
        result = [0.0] * players
        for action in state.legal_actions():
            child_values = walk(state.child(action))
            probability = strategy[key][action]
            for index in range(players):
                result[index] += probability * child_values[index]
        return tuple(result)

    return walk(root)


@dataclass(frozen=True, slots=True)
class UnilateralDeviationCertificate:
    """Finite exhaustive unilateral-deviation diagnostic, not a Nash guarantee."""

    values: tuple[float, ...]
    best_response_values: tuple[float, ...]
    incentives: tuple[float, ...]
    total_incentive: float
    provenance: str


def unilateral_deviation_certificate(
    root: NPlayerGameState,
    strategy: Mapping[Hashable, Mapping[Action, float]],
    *,
    max_pure_strategies: int = 100_000,
) -> UnilateralDeviationCertificate:
    """Exhaustively evaluate each player's pure information-set deviations."""
    if (
        isinstance(max_pure_strategies, bool)
        or not isinstance(max_pure_strategies, int)
        or max_pure_strategies <= 0
    ):
        raise ValueError("max_pure_strategies must be a positive integer")
    infosets = collect_nplayer_infosets(root)
    values = expected_values_nplayer(root, strategy)
    players = _player_count(root)
    best_values: list[float] = []
    for player in range(players):
        owned = [(key, actions) for key, (owner, actions) in infosets.items() if owner == player]
        count = prod(len(actions) for _, actions in owned)
        if count > max_pure_strategies:
            raise ValueError("player pure-strategy bound exceeded")
        best = values[player]
        for choices in product(*(actions for _, actions in owned)):
            deviated = {key: dict(policy) for key, policy in strategy.items()}
            for (key, actions), chosen in zip(owned, choices, strict=True):
                deviated[key] = {action: float(action == chosen) for action in actions}
            best = max(best, expected_values_nplayer(root, deviated)[player])
        best_values.append(best)
    incentives = tuple(
        max(0.0, best - value)
        for best, value in zip(best_values, values, strict=True)
    )
    return UnilateralDeviationCertificate(
        values=values,
        best_response_values=tuple(best_values),
        incentives=incentives,
        total_incentive=sum(incentives),
        provenance="exhaustive finite pure unilateral deviations; diagnostic only",
    )
