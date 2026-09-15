"""Exact five-card and best-of-seven Hold'em evaluator."""

from collections import Counter
from .cards import rank_index, suit_index, validate_unique

HIGH_CARD = 0
ONE_PAIR = 1
TWO_PAIR = 2
THREE_OF_A_KIND = 3
STRAIGHT = 4
FLUSH = 5
FULL_HOUSE = 6
FOUR_OF_A_KIND = 7
STRAIGHT_FLUSH = 8
CATEGORY_NAMES = (
    "high-card", "one-pair", "two-pair", "three-of-a-kind", "straight",
    "flush", "full-house", "four-of-a-kind", "straight-flush",
)
HandRank = tuple[int, ...]


def _straight_high(ranks: set[int]) -> int | None:
    if {12, 0, 1, 2, 3}.issubset(ranks):
        wheel = 3
    else:
        wheel = None
    for high in range(12, 3, -1):
        if all(rank in ranks for rank in range(high - 4, high + 1)):
            return high
    return wheel


def evaluate_five(cards: tuple[int, ...] | list[int]) -> HandRank:
    cards = validate_unique(cards)
    if len(cards) != 5:
        raise ValueError("evaluate_five requires exactly 5 cards")
    ranks = [rank_index(c) for c in cards]
    counts = Counter(ranks)
    groups = sorted(((count, rank) for rank, count in counts.items()), reverse=True)
    flush = len({suit_index(c) for c in cards}) == 1
    straight_high = _straight_high(set(ranks)) if len(counts) == 5 else None
    if flush and straight_high is not None:
        return (STRAIGHT_FLUSH, straight_high)
    if groups[0][0] == 4:
        return (FOUR_OF_A_KIND, groups[0][1], groups[1][1])
    if [g[0] for g in groups] == [3, 2]:
        return (FULL_HOUSE, groups[0][1], groups[1][1])
    if flush:
        return (FLUSH, *sorted(ranks, reverse=True))
    if straight_high is not None:
        return (STRAIGHT, straight_high)
    if groups[0][0] == 3:
        kickers = sorted((rank for rank, count in counts.items() if count == 1), reverse=True)
        return (THREE_OF_A_KIND, groups[0][1], *kickers)
    pairs = sorted((rank for rank, count in counts.items() if count == 2), reverse=True)
    if len(pairs) == 2:
        kicker = next(rank for rank, count in counts.items() if count == 1)
        return (TWO_PAIR, pairs[0], pairs[1], kicker)
    if len(pairs) == 1:
        kickers = sorted((rank for rank, count in counts.items() if count == 1), reverse=True)
        return (ONE_PAIR, pairs[0], *kickers)
    return (HIGH_CARD, *sorted(ranks, reverse=True))


def evaluate_seven(cards: tuple[int, ...] | list[int]) -> HandRank:
    cards = validate_unique(cards)
    if len(cards) != 7:
        raise ValueError("evaluate_seven requires exactly 7 cards")
    ranks = [rank_index(c) for c in cards]
    counts = Counter(ranks)
    by_suit: dict[int, list[int]] = {suit: [] for suit in range(4)}
    for card in cards:
        by_suit[suit_index(card)].append(rank_index(card))
    for suited_ranks in by_suit.values():
        if len(suited_ranks) >= 5:
            high = _straight_high(set(suited_ranks))
            if high is not None:
                return (STRAIGHT_FLUSH, high)
    quads = sorted((rank for rank, count in counts.items() if count == 4), reverse=True)
    if quads:
        kicker = max(rank for rank in counts if rank != quads[0])
        return (FOUR_OF_A_KIND, quads[0], kicker)
    trips = sorted((rank for rank, count in counts.items() if count >= 3), reverse=True)
    pairs = sorted((rank for rank, count in counts.items() if count >= 2), reverse=True)
    if trips:
        pair_candidates = [rank for rank in pairs if rank != trips[0]]
        if pair_candidates:
            return (FULL_HOUSE, trips[0], pair_candidates[0])
    flushes = [sorted(rs, reverse=True)[:5] for rs in by_suit.values() if len(rs) >= 5]
    if flushes:
        return (FLUSH, *max(flushes))
    straight_high = _straight_high(set(ranks))
    if straight_high is not None:
        return (STRAIGHT, straight_high)
    if trips:
        kickers = sorted((rank for rank in counts if rank != trips[0]), reverse=True)[:2]
        return (THREE_OF_A_KIND, trips[0], *kickers)
    if len(pairs) >= 2:
        high_pair, low_pair = pairs[:2]
        kicker = max(rank for rank in counts if rank not in (high_pair, low_pair))
        return (TWO_PAIR, high_pair, low_pair, kicker)
    if len(pairs) == 1:
        kickers = sorted((rank for rank in counts if rank != pairs[0]), reverse=True)[:3]
        return (ONE_PAIR, pairs[0], *kickers)
    return (HIGH_CARD, *sorted(counts, reverse=True)[:5])


def evaluate(cards: tuple[int, ...] | list[int]) -> HandRank:
    if len(cards) == 5:
        return evaluate_five(cards)
    if len(cards) == 7:
        return evaluate_seven(cards)
    raise ValueError("evaluation requires exactly 5 or 7 cards")
