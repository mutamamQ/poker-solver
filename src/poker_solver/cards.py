"""Strict integer card representation."""

from collections.abc import Iterable

RANKS = "23456789TJQKA"
SUITS = "cdhs"
_RANK = {r: i for i, r in enumerate(RANKS)}
_SUIT = {s: i for i, s in enumerate(SUITS)}
FULL_DECK = tuple(range(52))


def parse_card(text: str) -> int:
    if not isinstance(text, str) or len(text) != 2:
        raise ValueError(f"invalid card {text!r}: expected two characters")
    if text[0] not in _RANK or text[1] not in _SUIT:
        raise ValueError(f"invalid card {text!r}: use ranks {RANKS} and suits {SUITS}")
    return _RANK[text[0]] * 4 + _SUIT[text[1]]


def format_card(card: int) -> str:
    if not isinstance(card, int) or isinstance(card, bool) or not 0 <= card < 52:
        raise ValueError(f"invalid card integer {card!r}")
    return RANKS[card // 4] + SUITS[card % 4]


def validate_unique(cards: Iterable[int]) -> tuple[int, ...]:
    result = tuple(cards)
    for card in result:
        if not isinstance(card, int) or isinstance(card, bool) or not 0 <= card < 52:
            raise ValueError(f"invalid card integer {card!r}")
    if len(set(result)) != len(result):
        raise ValueError("duplicate cards")
    return result


def parse_cards(values: Iterable[str]) -> tuple[int, ...]:
    return validate_unique(parse_card(value) for value in values)


def rank_index(card: int) -> int:
    format_card(card)
    return card // 4


def suit_index(card: int) -> int:
    format_card(card)
    return card % 4
