import pytest

from poker_solver.cards import parse_cards
from poker_solver.equity import EquityResult, WeightedCombo, exact_equity, range_equity


def hand(text):
    cards = parse_cards(text.split())
    return (cards[0], cards[1])


def board(text):
    return parse_cards(text.split()) if text else ()


@pytest.mark.parametrize(("hero","villain","public","expected"), [
    ("As Ks", "9h 9d", "Kc 7s 2s", (946, 0, 44)),
    ("5h 5d", "Ac Ah", "5s 9c 2d", (886, 0, 104)),
    ("Jh Ts", "Kd Qc", "Qh 9s 2d", (284, 0, 706)),
    ("Ah 9h", "Kd Kc", "Kh 7h 3h 3d", (0, 0, 44)),
    ("Jc Td", "Ah Ks", "Kd Jh 9s 2c", (9, 0, 35)),
    ("Ah Jh", "Kd Kc", "Th 9h 2c 3d", (12, 0, 32)),
    ("7c 7d", "Ah Kh", "7h 2h 9h 2c", (44, 0, 0)),
    ("As Kh", "Qd Jc", "Ah Kd Qc Js 2h", (1, 0, 0)),
    ("Ac 7d", "Ad 6s", "Ah Kh Qh Jh Th", (0, 1, 0)),
    ("Ac Qd", "Ah Jc", "As Ks 7h 4d 2c", (1, 0, 0)),
    ("2c 3d", "4c 5d", "As Ks Qs Js Ts", (0, 1, 0)),
    ("6h 5h", "As Ad", "7h 8h 9c Tc 2d", (1, 0, 0)),
    ("Ks Kd", "Qs Qd", "Kc Qc 2h 2d 3s", (1, 0, 0)),
    ("As 2s", "Kh Kd", "3s 4s 5d 9c Tc", (1, 0, 0)),
])
def test_exact_postflop_fixtures(hero, villain, public, expected):
    result = exact_equity(hand(hero), hand(villain), board(public))
    assert (result.wins, result.ties, result.losses) == expected


@pytest.mark.slow
@pytest.mark.parametrize(("hero","villain","expected"), [
    ("As Ah", "Ks Kh", (1_410_336, 9_308, 292_660)),
    ("9h 9d", "Ac Kd", (943_067, 6_697, 762_540)),
])
def test_exact_preflop_fixtures(hero, villain, expected):
    result = exact_equity(hand(hero), hand(villain))
    assert (result.wins, result.ties, result.losses) == expected


def test_result_and_range_weighting_and_errors():
    result = EquityResult(1, 1, 0)
    assert result.total == 2 and result.equity == 0.75
    h1, h2, v = hand("As Ah"), hand("Ks Kh"), hand("Qs Qh")
    river = board("2c 3d 4h 8s 9c")
    eq = range_equity((WeightedCombo(h1, 3.0), WeightedCombo(h2, 1.0)), (WeightedCombo(v),), river)
    assert 0 <= eq <= 1
    with pytest.raises(ValueError):
        exact_equity(h1, (h1[0], v[0]), ())
    with pytest.raises(ValueError):
        range_equity((WeightedCombo(h1),), (WeightedCombo((h1[0], v[0])),), river)
