"""Exhaustive exact-card and blocker-aware range equity."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import isfinite

from .cards import FULL_DECK, validate_unique
from .evaluator import evaluate_seven


@dataclass(frozen=True, slots=True)
class EquityResult:
    wins: int
    ties: int
    losses: int

    @property
    def total(self) -> int:
        return self.wins + self.ties + self.losses

    @property
    def equity(self) -> float:
        if self.total == 0:
            raise ValueError("equity has no outcomes")
        return (self.wins + self.ties / 2.0) / self.total


@dataclass(frozen=True, slots=True)
class WeightedCombo:
    cards: tuple[int, int]
    weight: float = 1.0

    def __post_init__(self) -> None:
        cards = validate_unique(self.cards)
        if len(cards) != 2:
            raise ValueError("a combo requires exactly two cards")
        if not isfinite(self.weight) or self.weight < 0:
            raise ValueError("combo weight must be finite and nonnegative")
        object.__setattr__(self, "cards", tuple(sorted(cards)))


def exact_equity(
    hero: tuple[int, int], villain: tuple[int, int], board: tuple[int, ...] = ()
) -> EquityResult:
    hero = tuple(validate_unique(hero))  # type: ignore[assignment]
    villain = tuple(validate_unique(villain))  # type: ignore[assignment]
    board = validate_unique(board)
    if len(hero) != 2 or len(villain) != 2:
        raise ValueError("hero and villain require exactly two cards")
    if len(board) not in (0, 3, 4, 5):
        raise ValueError("board must contain 0, 3, 4, or 5 cards")
    dead = validate_unique(hero + villain + board)
    remaining = tuple(card for card in FULL_DECK if card not in set(dead))
    wins = ties = losses = 0
    for runout in combinations(remaining, 5 - len(board)):
        final_board = board + runout
        h = evaluate_seven(hero + final_board)
        v = evaluate_seven(villain + final_board)
        if h > v:
            wins += 1
        elif h == v:
            ties += 1
        else:
            losses += 1
    return EquityResult(wins, ties, losses)


def range_equity(
    hero_range: tuple[WeightedCombo, ...],
    villain_range: tuple[WeightedCombo, ...],
    board: tuple[int, ...],
) -> float:
    board = validate_unique(board)
    if len(board) not in (0, 3, 4, 5):
        raise ValueError("board must contain 0, 3, 4, or 5 cards")
    board_set = set(board)
    weighted_share = total_weight = 0.0
    for hero in hero_range:
        if hero.weight == 0 or board_set.intersection(hero.cards):
            continue
        for villain in villain_range:
            if villain.weight == 0 or board_set.intersection(villain.cards):
                continue
            if set(hero.cards).intersection(villain.cards):
                continue
            weight = hero.weight * villain.weight
            result = exact_equity(hero.cards, villain.cards, board)
            weighted_share += weight * result.equity
            total_weight += weight
    if total_weight <= 0:
        raise ValueError("ranges have no compatible positive-weight hand pairs")
    return weighted_share / total_weight
