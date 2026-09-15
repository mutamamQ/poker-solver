import pytest

from poker_solver.cards import FULL_DECK, format_card, parse_card, parse_cards, validate_unique


def test_all_cards_round_trip_and_deck_unique():
    assert len(FULL_DECK) == len(set(FULL_DECK)) == 52
    for card in FULL_DECK:
        assert parse_card(format_card(card)) == card
    assert format_card(0) == "2c"
    assert format_card(51) == "As"


@pytest.mark.parametrize("bad", ["as", "AS", "10s", "A", "Ax", "", None])
def test_strict_invalid_cards(bad):
    with pytest.raises(ValueError):
        parse_card(bad)


def test_parse_and_duplicate_validation():
    assert parse_cards(("As", "Kh")) == (51, 46)
    with pytest.raises(ValueError, match="duplicate"):
        parse_cards(("As", "As"))
    with pytest.raises(ValueError):
        validate_unique((0, 52))
    with pytest.raises(ValueError):
        format_card(-1)
