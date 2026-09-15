"""Deterministic external cross-check against Treys.

Run with: uv run --with treys python scripts/crosscheck_treys.py
"""

import random

from treys import Card, Evaluator

from poker_solver.cards import format_card
from poker_solver.evaluator import evaluate_seven


def sign(value: int) -> int:
    return (value > 0) - (value < 0)


def main() -> None:
    rng = random.Random(0xC0FFEE)
    evaluator = Evaluator()
    deck = list(range(52))
    category_cases = 100_000
    comparison_cases = 50_000

    for index in range(category_cases):
        seven = rng.sample(deck, 7)
        treys_cards = [Card.new(format_card(card)) for card in seven]
        rank_class = max(1, evaluator.get_rank_class(evaluator.evaluate(treys_cards[:2], treys_cards[2:])))
        external = 9 - rank_class
        internal = evaluate_seven(seven)[0]
        if internal != external:
            raise AssertionError(("category", index, [format_card(c) for c in seven], internal, external))

    for index in range(comparison_cases):
        nine = rng.sample(deck, 9)
        board, hero, villain = nine[:5], nine[5:7], nine[7:]
        treys_board = [Card.new(format_card(card)) for card in board]
        external_delta = evaluator.evaluate([Card.new(format_card(c)) for c in villain], treys_board) - evaluator.evaluate([Card.new(format_card(c)) for c in hero], treys_board)
        internal_delta = (evaluate_seven(hero + board) > evaluate_seven(villain + board)) - (evaluate_seven(hero + board) < evaluate_seven(villain + board))
        if internal_delta != sign(external_delta):
            raise AssertionError(("comparison", index, [format_card(c) for c in nine], internal_delta, sign(external_delta)))

    print(f"treys cross-check passed: categories={category_cases} comparisons={comparison_cases} seed=0xC0FFEE")


if __name__ == "__main__":
    main()
