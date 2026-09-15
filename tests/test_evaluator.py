from itertools import combinations

import pytest

from poker_solver.cards import FULL_DECK, parse_cards
from poker_solver.evaluator import (
    FLUSH, FOUR_OF_A_KIND, FULL_HOUSE, HIGH_CARD, ONE_PAIR, STRAIGHT,
    STRAIGHT_FLUSH, THREE_OF_A_KIND, TWO_PAIR, evaluate_five, evaluate_seven,
)


def c(text):
    return parse_cards(text.split())


@pytest.mark.parametrize(("cards", "category"), [
    ("As Kd Qh Jc 9s", HIGH_CARD),
    ("As Ah Kd Qh Jc", ONE_PAIR),
    ("As Ah Kd Kh Qc", TWO_PAIR),
    ("As Ah Ad Kd Qc", THREE_OF_A_KIND),
    ("9s 8d 7h 6c 5s", STRAIGHT),
    ("As Js 9s 7s 3s", FLUSH),
    ("As Ah Ad Kd Kc", FULL_HOUSE),
    ("As Ah Ad Ac Kc", FOUR_OF_A_KIND),
    ("9s 8s 7s 6s 5s", STRAIGHT_FLUSH),
])
def test_every_category(cards, category):
    assert evaluate_five(c(cards))[0] == category


def test_wheel_and_tiebreaks():
    assert evaluate_five(c("5c 4d 3h 2s Ac")) == (STRAIGHT, 3)
    assert evaluate_five(c("6c 5d 4h 3s 2c")) > evaluate_five(c("5c 4d 3h 2s Ac"))
    assert evaluate_five(c("Ac Ad Kc Kd Qh")) > evaluate_five(c("Ac Ah Qc Qd Kh"))
    assert evaluate_five(c("Ac Ad Kh Qc Jd")) > evaluate_five(c("As Ah Kc Qd Tc"))


def test_seven_selects_best_and_board_can_play():
    assert evaluate_seven(c("Jc Jd Jh Js Ac Kd Qh")) == (FOUR_OF_A_KIND, 9, 12)
    assert evaluate_seven(c("2c 3d As Ks Qs Js Ts")) == (STRAIGHT_FLUSH, 12)
    with pytest.raises(ValueError):
        evaluate_seven(c("As As Ks Qs Js Ts 9s"))


@pytest.mark.parametrize(("cards", "expected"), [
    ("As 2h 3d 4c 5s Kh Qd", (STRAIGHT, 3)),
    ("As 2h 3d 4c 5s 6h 7d", (STRAIGHT, 5)),
    ("9s 8s 7s 6s 5s 3s 2s", (STRAIGHT_FLUSH, 7)),
    ("Ah 2h 3h 4h 5h Kd Qc", (STRAIGHT_FLUSH, 3)),
    ("As Ah Kd Kc Qs Qh Jd", (TWO_PAIR, 12, 11, 10)),
    ("As Ah Ad Kc Ks Kh Qd", (FULL_HOUSE, 12, 11)),
    ("7s 7h 7d 7c 3s 3h 3d", (FOUR_OF_A_KIND, 5, 1)),
    ("As Ks Qs Js 9s 7s 2d", (FLUSH, 12, 11, 10, 9, 7)),
    ("9s 8h 7d 6c 5s 5h 5d", (STRAIGHT, 7)),
])
def test_adversarial_seven_card_edges(cards, expected):
    assert evaluate_seven(c(cards)) == expected


@pytest.mark.slow
def test_exhaustive_five_card_category_counts():
    counts = [0] * 9
    for hand in combinations(FULL_DECK, 5):
        counts[evaluate_five(hand)[0]] += 1
    assert counts == [1_302_540, 1_098_240, 123_552, 54_912, 10_200, 5_108, 3_744, 624, 40]
    assert sum(counts) == 2_598_960
