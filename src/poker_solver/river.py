"""Exact compact heads-up river Hold'em extensive-form game."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .cards import format_card, validate_unique
from .equity import WeightedCombo
from .evaluator import evaluate_seven
from .model import Action, CHANCE, TERMINAL

CHECK = Action("check")
FOLD = Action("fold")
CALL = Action("call")


@dataclass(frozen=True, slots=True)
class RiverConfig:
    board: tuple[int, int, int, int, int]
    pot: float
    stack: int
    bet: int
    range0: tuple[WeightedCombo, ...]
    range1: tuple[WeightedCombo, ...]

    def __post_init__(self) -> None:
        board = validate_unique(self.board)
        if len(board) != 5:
            raise ValueError("river board requires five cards")
        if not isfinite(self.pot) or self.pot <= 0:
            raise ValueError("pot must be finite and positive")
        if not isinstance(self.stack, int) or self.stack <= 0:
            raise ValueError("stack must be a positive integer")
        if not isinstance(self.bet, int) or not 0 < self.bet <= self.stack:
            raise ValueError("bet must be a positive integer no larger than stack")
        if not self.range0 or not self.range1:
            raise ValueError("both ranges must be nonempty")
        object.__setattr__(self, "board", board)

    @property
    def bet_action(self) -> Action:
        return Action("bet", self.bet)


@dataclass(frozen=True, slots=True)
class RiverState:
    config: RiverConfig
    deal: tuple[tuple[int, int], tuple[int, int]] | None = None
    history: tuple[Action, ...] = ()

    def _outcomes(self) -> tuple[tuple[Action, float], ...]:
        board = set(self.config.board)
        raw: list[tuple[Action, float]] = []
        index = 0
        for hand0 in self.config.range0:
            if hand0.weight == 0 or board.intersection(hand0.cards):
                continue
            for hand1 in self.config.range1:
                if hand1.weight == 0 or board.intersection(hand1.cards):
                    continue
                if set(hand0.cards).intersection(hand1.cards):
                    continue
                raw.append((Action("deal", index), hand0.weight * hand1.weight))
                index += 1
        total = sum(weight for _, weight in raw)
        if total <= 0:
            raise ValueError("ranges have no compatible positive-weight deals")
        return tuple((action, weight / total) for action, weight in raw)

    def _deals(self) -> tuple[tuple[tuple[int, int], tuple[int, int]], ...]:
        board = set(self.config.board)
        result = []
        for hand0 in self.config.range0:
            if hand0.weight == 0 or board.intersection(hand0.cards):
                continue
            for hand1 in self.config.range1:
                if hand1.weight == 0 or board.intersection(hand1.cards):
                    continue
                if not set(hand0.cards).intersection(hand1.cards):
                    result.append((hand0.cards, hand1.cards))
        return tuple(result)

    def current_player(self) -> int:
        if self.deal is None:
            return CHANCE
        b = self.config.bet_action
        terminals = ((CHECK, CHECK), (b, FOLD), (b, CALL), (CHECK, b, FOLD), (CHECK, b, CALL))
        if self.history in terminals:
            return TERMINAL
        if self.history in ((), (CHECK, b)):
            return 0
        if self.history in ((CHECK,), (b,)):
            return 1
        raise ValueError(f"invalid river history: {self.history!r}")

    def legal_actions(self) -> tuple[Action, ...]:
        player = self.current_player()
        if player == CHANCE:
            return tuple(action for action, _ in self._outcomes())
        if player == TERMINAL:
            return ()
        if self.history in ((), (CHECK,)):
            return (CHECK, self.config.bet_action)
        return (FOLD, CALL)

    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]:
        return self._outcomes() if self.current_player() == CHANCE else ()

    def child(self, action: Action) -> RiverState:
        if action not in self.legal_actions():
            raise ValueError(f"illegal action {action!r}")
        if self.current_player() == CHANCE:
            return RiverState(self.config, self._deals()[action.amount], ())
        return RiverState(self.config, self.deal, self.history + (action,))

    def information_state_key(self, player: int) -> tuple[object, ...]:
        if self.current_player() != player:
            raise ValueError("information key requested for non-acting player")
        assert self.deal is not None
        own = self.deal[player]
        return (
            "river-v1", player, own, self.config.board, self.history,
            self.config.pot, self.config.stack, self.config.bet,
        )

    def returns(self) -> tuple[float, float]:
        if self.current_player() != TERMINAL:
            raise ValueError("returns requested at non-terminal")
        assert self.deal is not None
        b = self.config.bet_action
        if self.history == (b, FOLD):
            value = self.config.pot / 2.0
        elif self.history == (CHECK, b, FOLD):
            value = -self.config.pot / 2.0
        else:
            rank0 = evaluate_seven(self.deal[0] + self.config.board)
            rank1 = evaluate_seven(self.deal[1] + self.config.board)
            stake = self.config.pot / 2.0
            if self.history in ((b, CALL), (CHECK, b, CALL)):
                stake += self.config.bet
            value = stake if rank0 > rank1 else -stake if rank1 > rank0 else 0.0
        return (value, -value)

    def deal_text(self) -> str:
        if self.deal is None:
            return "undealt"
        return "/".join("".join(format_card(c) for c in hand) for hand in self.deal)


def river_root(config: RiverConfig) -> RiverState:
    root = RiverState(config)
    root.chance_outcomes()
    return root
