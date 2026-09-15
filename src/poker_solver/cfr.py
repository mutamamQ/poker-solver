"""Deterministic synchronous full-tree vanilla CFR."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose

from .model import Action, CHANCE, GameState, InfoKey, Strategy, TERMINAL


@dataclass(slots=True)
class InfoData:
    player: int
    actions: tuple[Action, ...]
    regrets: dict[Action, float] = field(default_factory=dict)
    strategy_sum: dict[Action, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.regrets:
            self.regrets = {action: 0.0 for action in self.actions}
        if not self.strategy_sum:
            self.strategy_sum = {action: 0.0 for action in self.actions}


def regret_matching(regrets: dict[Action, float], actions: tuple[Action, ...]) -> dict[Action, float]:
    positive = {action: max(0.0, regrets[action]) for action in actions}
    total = sum(positive.values())
    if total > 0:
        return {action: positive[action] / total for action in actions}
    probability = 1.0 / len(actions)
    return {action: probability for action in actions}


def collect_infosets(root: GameState) -> dict[InfoKey, tuple[int, tuple[Action, ...]]]:
    result: dict[InfoKey, tuple[int, tuple[Action, ...]]] = {}

    def walk(state: GameState) -> None:
        player = state.current_player()
        if player == TERMINAL:
            return
        if player == CHANCE:
            branches = state.chance_outcomes()
        else:
            actions = state.legal_actions()
            key = state.information_state_key(player)
            signature = (player, actions)
            if key in result and result[key] != signature:
                raise ValueError(f"inconsistent information set {key!r}")
            result[key] = signature
            branches = tuple((action, 0.0) for action in actions)
        for action, _ in branches:
            walk(state.child(action))

    walk(root)
    return result


def expected_values(root: GameState, profile: Strategy) -> tuple[float, float]:
    def walk(state: GameState) -> tuple[float, float]:
        player = state.current_player()
        if player == TERMINAL:
            return state.returns()
        if player == CHANCE:
            branches = state.chance_outcomes()
        else:
            actions = state.legal_actions()
            policy = profile[state.information_state_key(player)]
            branches = tuple((action, policy[action]) for action in actions)
        value0 = value1 = 0.0
        for action, probability in branches:
            child0, child1 = walk(state.child(action))
            value0 += probability * child0
            value1 += probability * child1
        return value0, value1

    return walk(root)


class CFRSolver:
    def __init__(self, root: GameState):
        self.root = root
        self.infosets = {
            key: InfoData(player, actions)
            for key, (player, actions) in collect_infosets(root).items()
        }
        self.iterations = 0

    def current_strategy(self) -> dict[InfoKey, dict[Action, float]]:
        return {
            key: regret_matching(data.regrets, data.actions)
            for key, data in self.infosets.items()
        }

    def average_strategy(self) -> dict[InfoKey, dict[Action, float]]:
        result = {}
        for key, data in self.infosets.items():
            total = sum(data.strategy_sum.values())
            if total > 0:
                result[key] = {a: data.strategy_sum[a] / total for a in data.actions}
            else:
                p = 1.0 / len(data.actions)
                result[key] = {a: p for a in data.actions}
        return result

    def train(self, iterations: int) -> dict[InfoKey, dict[Action, float]]:
        if not isinstance(iterations, int) or iterations <= 0:
            raise ValueError("iterations must be a positive integer")
        for _ in range(iterations):
            snapshot = self.current_strategy()
            deltas = {key: {a: 0.0 for a in data.actions} for key, data in self.infosets.items()}
            owner_reaches: dict[InfoKey, float] = {}
            self._walk(self.root, 0, 1.0, 1.0, 1.0, snapshot, deltas, owner_reaches)
            self._walk(self.root, 1, 1.0, 1.0, 1.0, snapshot, deltas, None)
            for key, data in self.infosets.items():
                for action in data.actions:
                    data.regrets[action] += deltas[key][action]
                    data.strategy_sum[action] += owner_reaches[key] * snapshot[key][action]
            self.iterations += 1
        return self.average_strategy()

    def _walk(
        self,
        state: GameState,
        updating: int,
        p0: float,
        p1: float,
        pc: float,
        profile: Strategy,
        deltas: dict[InfoKey, dict[Action, float]],
        owner_reaches: dict[InfoKey, float] | None,
    ) -> float:
        player = state.current_player()
        if player == TERMINAL:
            return state.returns()[updating]
        if player == CHANCE:
            return sum(
                probability * self._walk(state.child(action), updating, p0, p1, pc * probability, profile, deltas, owner_reaches)
                for action, probability in state.chance_outcomes()
            )
        actions = state.legal_actions()
        key = state.information_state_key(player)
        policy = profile[key]
        own_reach = p0 if player == 0 else p1
        if owner_reaches is not None:
            if key in owner_reaches and not isclose(owner_reaches[key], own_reach, abs_tol=1e-12):
                raise ValueError(f"imperfect-recall owner reach at {key!r}")
            owner_reaches[key] = own_reach
        action_values: dict[Action, float] = {}
        for action in actions:
            if player == 0:
                action_values[action] = self._walk(state.child(action), updating, p0 * policy[action], p1, pc, profile, deltas, owner_reaches)
            else:
                action_values[action] = self._walk(state.child(action), updating, p0, p1 * policy[action], pc, profile, deltas, owner_reaches)
        node_value = sum(policy[a] * action_values[a] for a in actions)
        if player == updating:
            counterfactual_reach = (p1 if player == 0 else p0) * pc
            for action in actions:
                deltas[key][action] += counterfactual_reach * (action_values[action] - node_value)
        return node_value

    def values(self) -> tuple[float, float]:
        return expected_values(self.root, self.average_strategy())
