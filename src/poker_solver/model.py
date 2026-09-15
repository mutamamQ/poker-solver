"""Generic protocol and immutable action type for finite games."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Mapping, Protocol, runtime_checkable

CHANCE = -1
TERMINAL = -2


@dataclass(frozen=True, order=True, slots=True)
class Action:
    kind: str
    amount: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind:
            raise ValueError("action kind must be a non-empty string")
        if not isinstance(self.amount, int) or isinstance(self.amount, bool):
            raise ValueError("action amount must be an integer")


InfoKey = Hashable
ActionPolicy = Mapping[Action, float]
Strategy = Mapping[InfoKey, ActionPolicy]


@runtime_checkable
class GameState(Protocol):
    def current_player(self) -> int: ...
    def legal_actions(self) -> tuple[Action, ...]: ...
    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]: ...
    def child(self, action: Action) -> GameState: ...
    def information_state_key(self, player: int) -> InfoKey: ...
    def returns(self) -> tuple[float, float]: ...


def other_player(player: int) -> int:
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    return 1 - player
