"""External-sampling Monte Carlo CFR with lazy infoset discovery."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

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
    """Convert cumulative regrets to a strategy via regret matching."""
    positive = {action: max(0.0, regrets[action]) for action in actions}
    total = sum(positive.values())
    if total > 0:
        return {action: positive[action] / total for action in actions}
    probability = 1.0 / len(actions)
    return {action: probability for action in actions}


def expected_values(root: GameState, profile: Strategy) -> tuple[float, float]:
    """Evaluate both players' expected values under a fixed strategy profile."""
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


class MCCFRSolver:
    """External-sampling MCCFR with lazy infoset discovery and deterministic seeded RNG.

    External sampling enumerates all actions at the updating player's nodes and samples
    one outcome at opponent and chance nodes. Regret updates use the unbiased external-sampling
    estimator from Lanctot et al. (2009). Because opponent and chance are
    sampled from their target distributions, their reach factors cancel the
    sampling-reach denominator, leaving the sampled update:

        R(I,a) += v_i(I,a) - v_i(I)

    In this two-player implementation, simple averaging is accumulated at
    opponent nodes during the other player's regret pass, matching the
    standard external-sampling algorithm. Infosets are discovered lazily.
    """

    def __init__(self, root: GameState, seed: int = 0):
        """Initialize solver with a game root and a random seed.

        Args:
            root: The root game state.
            seed: Random seed for deterministic sampling.
        """
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        self.root = root
        self.seed = seed
        self.rng = random.Random(seed)
        self.infosets: dict[InfoKey, InfoData] = {}
        self.iterations = 0

    def _ensure_infoset(self, key: InfoKey, player: int, actions: tuple[Action, ...]) -> InfoData:
        """Lazily create or retrieve an infoset."""
        if key not in self.infosets:
            self.infosets[key] = InfoData(player, actions)
        else:
            data = self.infosets[key]
            if data.player != player or data.actions != actions:
                raise ValueError(f"inconsistent information set {key!r}")
        return self.infosets[key]

    def current_strategy(self) -> dict[InfoKey, dict[Action, float]]:
        """Return the current instantaneous strategy from regret matching."""
        return {
            key: regret_matching(data.regrets, data.actions)
            for key, data in self.infosets.items()
        }

    def average_strategy(self) -> dict[InfoKey, dict[Action, float]]:
        """Return the normalized average strategy."""
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
        """Run external-sampling MCCFR for the specified number of iterations."""
        if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations <= 0:
            raise ValueError("iterations must be a positive integer")
        for _ in range(iterations):
            self._walk(self.root, 0)
            self._walk(self.root, 1)
            self.iterations += 1
        return self.average_strategy()

    def _walk(self, state: GameState, updating: int) -> float:
        """Run one external-sampling regret traversal for ``updating``."""
        player = state.current_player()
        if player == TERMINAL:
            return state.returns()[updating]
        if player == CHANCE:
            outcomes = state.chance_outcomes()
            action, _ = self.rng.choices(
                population=outcomes,
                weights=[probability for _, probability in outcomes],
                k=1,
            )[0]
            return self._walk(state.child(action), updating)

        actions = state.legal_actions()
        key = state.information_state_key(player)
        data = self._ensure_infoset(key, player, actions)
        policy = regret_matching(data.regrets, actions)
        if player == updating:
            action_values = {
                action: self._walk(state.child(action), updating)
                for action in actions
            }
            node_value = sum(policy[action] * action_values[action] for action in actions)
            for action in actions:
                data.regrets[action] += action_values[action] - node_value
            return node_value

        # Standard two-player simple averaging updates the opponent's policy
        # during the other player's regret pass.
        for action in actions:
            data.strategy_sum[action] += policy[action]
        sampled = self.rng.choices(
            population=actions,
            weights=[policy[action] for action in actions],
            k=1,
        )[0]
        return self._walk(state.child(sampled), updating)

    def values(self) -> tuple[float, float]:
        """Return expected values under the average strategy."""
        return expected_values(self.root, self.average_strategy())
