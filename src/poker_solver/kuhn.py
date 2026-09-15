"""Immutable standard three-card Kuhn poker."""

from __future__ import annotations

from dataclasses import dataclass

from .model import Action, CHANCE, TERMINAL

CHECK = Action("check")
BET = Action("bet")
FOLD = Action("fold")
CALL = Action("call")
KUHN_VALUE_P0 = -1.0 / 18.0
_CARDS = "JQK"
_DEALS = tuple(a + b for a in _CARDS for b in _CARDS if a != b)
_TERMINALS = {
    (CHECK, CHECK),
    (BET, FOLD),
    (BET, CALL),
    (CHECK, BET, FOLD),
    (CHECK, BET, CALL),
}


@dataclass(frozen=True, slots=True)
class KuhnState:
    deal: str | None = None
    history: tuple[Action, ...] = ()

    def current_player(self) -> int:
        if self.deal is None:
            return CHANCE
        if self.history in _TERMINALS:
            return TERMINAL
        if self.history in ((), (CHECK, BET)):
            return 0
        if self.history in ((CHECK,), (BET,)):
            return 1
        raise ValueError(f"invalid Kuhn history: {self.history!r}")

    def legal_actions(self) -> tuple[Action, ...]:
        player = self.current_player()
        if player == CHANCE:
            return tuple(Action("deal", i) for i in range(6))
        if player == TERMINAL:
            return ()
        if self.history in ((), (CHECK,)):
            return (CHECK, BET)
        return (FOLD, CALL)

    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]:
        if self.current_player() != CHANCE:
            return ()
        return tuple((action, 1.0 / 6.0) for action in self.legal_actions())

    def child(self, action: Action) -> KuhnState:
        if action not in self.legal_actions():
            raise ValueError(f"illegal action {action!r}")
        if self.current_player() == CHANCE:
            return KuhnState(_DEALS[action.amount], ())
        return KuhnState(self.deal, self.history + (action,))

    def information_state_key(self, player: int) -> tuple[object, ...]:
        if self.current_player() != player:
            raise ValueError("information key requested for non-acting player")
        assert self.deal is not None
        return ("kuhn-v1", player, self.deal[player], self.history)

    def returns(self) -> tuple[float, float]:
        if self.current_player() != TERMINAL:
            raise ValueError("returns requested at non-terminal")
        assert self.deal is not None
        p0_wins = _CARDS.index(self.deal[0]) > _CARDS.index(self.deal[1])
        if self.history == (BET, FOLD):
            value = 1.0
        elif self.history == (CHECK, BET, FOLD):
            value = -1.0
        elif self.history in ((BET, CALL), (CHECK, BET, CALL)):
            value = 2.0 if p0_wins else -2.0
        elif self.history == (CHECK, CHECK):
            value = 1.0 if p0_wins else -1.0
        else:
            raise ValueError("invalid terminal history")
        return (value, -value)


def kuhn_root() -> KuhnState:
    return KuhnState()
