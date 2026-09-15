"""Test bounties.py: immediate one-hand bounty accounting.

Vertical TDD: write failing test before each behavior.
Owned file: tests/test_bounties.py only.
"""

import pytest
from fractions import Fraction


def test_ko_single_recipient_exact():
    """KO: bounty 100, one recipient → immediate cash 100, eliminated head 0."""
    # RED: module does not exist yet
    from poker_solver.bounties import compute_ko_bounty
    
    result = compute_ko_bounty(
        eliminated_bounty=100,
        recipient_shares={0: Fraction(1, 1)}
    )
    
    assert result["immediate_cash"] == {0: 100}
    assert result["eliminated_bounty_after"] == 0


def test_pko_splits_cash_and_progressive_pool_exactly():
    from poker_solver.bounties import compute_pko_bounty

    result = compute_pko_bounty(
        eliminated_bounty=Fraction(100),
        recipient_shares={0: Fraction(1, 4), 2: Fraction(3, 4)},
        immediate_fraction=Fraction(2, 5),
    )

    assert result["immediate_cash"] == {0: Fraction(10), 2: Fraction(30)}
    assert result["bounty_increases"] == {0: Fraction(15), 2: Fraction(45)}
    assert sum(result["immediate_cash"].values()) + sum(result["bounty_increases"].values()) == 100
    assert result["eliminated_bounty_after"] == 0


def test_mystery_bounty_returns_exact_outcomes_and_expectation():
    from poker_solver.bounties import compute_mystery_bounty

    result = compute_mystery_bounty(
        prizes=((Fraction(20), Fraction(3, 4)), (Fraction(100), Fraction(1, 4))),
        recipient_shares={1: Fraction(1, 2), 2: Fraction(1, 2)},
    )

    assert result["expected_prize"] == 40
    assert result["expected_cash"] == {1: Fraction(20), 2: Fraction(20)}
    assert result["outcomes"][1]["cash"] == {1: Fraction(50), 2: Fraction(50)}


def test_tko_requires_explicit_conserving_transfer_policy():
    from poker_solver.bounties import compute_tko_bounty

    result = compute_tko_bounty(
        eliminated_bounty=Fraction(90),
        recipient_shares={0: Fraction(1)},
        immediate_fraction=Fraction(1, 3),
        bounty_transfer_fraction=Fraction(2, 3),
    )

    assert result["immediate_cash"] == {0: Fraction(30)}
    assert result["bounty_increases"] == {0: Fraction(60)}
    with pytest.raises(ValueError, match="sum to 1"):
        compute_tko_bounty(90, {0: Fraction(1)}, Fraction(1, 3), Fraction(1, 3))


def test_one_hand_utility_combines_icm_delta_and_immediate_cash():
    from poker_solver.bounties import one_hand_tournament_utility

    result = one_hand_tournament_utility(
        pre_icm=(Fraction(50), Fraction(30), Fraction(20)),
        post_icm=(Fraction(70), Fraction(30), Fraction(0)),
        immediate_cash={0: Fraction(25)},
        elimination_count=1,
    )

    assert result == (Fraction(45), Fraction(0), Fraction(-20))
    with pytest.raises(ValueError, match="simultaneous"):
        one_hand_tournament_utility((1, 1), (2, 0), {0: 5}, elimination_count=2)
