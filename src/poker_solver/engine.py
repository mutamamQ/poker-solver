"""Truthful bounded Phase-3 engine-mode dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Hashable, Mapping

from .cfr import CFRSolver, expected_values
from .model import Action, CHANCE, TERMINAL
from .nplayer import NPlayerCFRSolver, collect_nplayer_infosets, expected_values_nplayer


@dataclass(frozen=True, slots=True)
class EngineConfig:
    mode: str
    iterations: int = 100
    max_nodes: int = 100_000
    max_depth: int = 512

    def __post_init__(self) -> None:
        if self.mode not in ("classic", "checkdown-equity", "fast-ddls"):
            raise ValueError("mode must be classic, checkdown-equity, or fast-ddls")
        for name in ("iterations", "max_nodes", "max_depth"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class EngineResult:
    mode: str
    values: tuple[float, ...]
    strategy: Mapping[Hashable, Mapping[Action, float]]
    approximate: bool
    provenance: str


def _freeze_strategy(strategy) -> Mapping[Hashable, Mapping[Action, float]]:
    return MappingProxyType({
        key: MappingProxyType(dict(policy))
        for key, policy in strategy.items()
    })


def solve_engine(root, config: EngineConfig) -> EngineResult:
    if not isinstance(config, EngineConfig):
        raise ValueError("config must be EngineConfig")
    if config.mode == "fast-ddls":
        raise ValueError("fast-ddls unavailable: no shipped neural continuation model")
    if config.mode == "checkdown-equity":
        values = _checkdown_values(root, config)
        return EngineResult(
            mode=config.mode,
            values=values,
            strategy=MappingProxyType({}),
            approximate=True,
            provenance="check-only rollout; ignores future betting",
        )
    if hasattr(root, "num_players"):
        collect_nplayer_infosets(root, max_nodes=config.max_nodes, max_depth=config.max_depth)
        solver = NPlayerCFRSolver(root)
        strategy = solver.train(config.iterations)
        values = expected_values_nplayer(root, strategy)
    else:
        # Existing two-player GameState APIs remain unchanged.
        solver = CFRSolver(root)
        strategy = solver.train(config.iterations)
        values = expected_values(root, strategy)
    return EngineResult(
        mode=config.mode,
        values=tuple(float(value) for value in values),
        strategy=_freeze_strategy(strategy),
        approximate=False,
        provenance="complete configured finite-tree CFR",
    )


def _checkdown_values(root, config: EngineConfig) -> tuple[float, ...]:
    players = root.num_players() if hasattr(root, "num_players") else 2
    if isinstance(players, bool) or not isinstance(players, int) or not 2 <= players <= 9:
        raise ValueError("game must declare two through nine players")
    seen = 0
    visiting: set[int] = set()

    def walk(state, depth: int) -> tuple[float, ...]:
        nonlocal seen
        if depth > config.max_depth:
            raise ValueError("game exceeds finite depth bound")
        seen += 1
        if seen > config.max_nodes:
            raise ValueError("game exceeds finite node bound")
        identity = id(state)
        if identity in visiting:
            raise ValueError("cycle detected in game tree")
        visiting.add(identity)
        try:
            actor = state.current_player()
            if actor == TERMINAL:
                values = tuple(state.returns())
                if len(values) != players or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not isfinite(float(value))
                    for value in values
                ):
                    raise ValueError("invalid terminal utility vector")
                return tuple(float(value) for value in values)
            if actor == CHANCE:
                outcomes = tuple(state.chance_outcomes())
                if not outcomes or len({action for action, _ in outcomes}) != len(outcomes):
                    raise ValueError("chance actions must be non-empty and unique")
                result = [0.0] * players
                total = 0.0
                for action, probability in outcomes:
                    if (
                        isinstance(probability, bool)
                        or not isinstance(probability, (int, float))
                        or not isfinite(float(probability))
                        or probability < 0
                    ):
                        raise ValueError("invalid chance probability")
                    total += float(probability)
                    child = walk(state.child(action), depth + 1)
                    for seat, value in enumerate(child):
                        result[seat] += float(probability) * value
                if abs(total - 1.0) > 1e-12:
                    raise ValueError("chance probabilities must sum to one")
                return tuple(result)
            actions = tuple(state.legal_actions())
            check = Action("CHECK")
            if check not in actions:
                raise ValueError("checkdown-equity requires CHECK at every decision")
            return walk(state.child(check), depth + 1)
        finally:
            visiting.remove(identity)

    return walk(root, 0)
