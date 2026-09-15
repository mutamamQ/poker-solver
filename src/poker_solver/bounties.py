"""Immediate one-hand bounty accounting.

Supports KO, PKO (caller-supplied rational cash/progressive split),
TKO (explicit transfer policy), and Mystery (finite prize distribution
enumeration/expectation).

Accepts ICM values as inputs; does not edit icm.py.
Tracks cash and bounty pools separately; enforces exact conservation
where rational inputs permit.

Rejects booleans, nonfinite/negative values, invalid fractions/distributions,
and unsupported simultaneous-elimination policy.

Does NOT claim future-bounty strategy support.
"""

from fractions import Fraction
from math import isfinite
from typing import Mapping


Amount = int | float | Fraction


def _amount(value: Amount, field: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise ValueError(f"{field} must be numeric")
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{field} must be finite")
        result = Fraction(str(value))
    else:
        result = Fraction(value)
    if result < 0:
        raise ValueError(f"{field} cannot be negative")
    return result


def _shares(recipient_shares: Mapping[int, Fraction]) -> dict[int, Fraction]:
    if not recipient_shares:
        raise ValueError("recipient_shares cannot be empty")
    result: dict[int, Fraction] = {}
    for seat, share in recipient_shares.items():
        if isinstance(seat, bool) or not isinstance(seat, int) or seat < 0:
            raise ValueError("recipient seats must be non-negative integers")
        if not isinstance(share, Fraction) or share < 0:
            raise ValueError(f"share for seat {seat} must be a non-negative Fraction")
        result[seat] = share
    if sum(result.values(), Fraction()) != 1:
        raise ValueError("recipient_shares must sum to 1")
    return result


def compute_ko_bounty(
    eliminated_bounty: Amount,
    recipient_shares: Mapping[int, Fraction],
) -> dict[str, object]:
    """Compute standard KO bounty distribution.
    
    Args:
        eliminated_bounty: Total bounty value of eliminated player
        recipient_shares: Map from recipient seat to share (must sum to 1)
    
    Returns:
        Dictionary with:
        - immediate_cash: Map from recipient seat to cash amount
        - eliminated_bounty_after: Remaining bounty on eliminated head (0 for KO)
    """
    bounty = _amount(eliminated_bounty, "eliminated_bounty")
    shares = _shares(recipient_shares)
    return {
        "immediate_cash": {seat: bounty * share for seat, share in shares.items()},
        "eliminated_bounty_after": Fraction(),
    }


def compute_pko_bounty(
    eliminated_bounty: Amount,
    recipient_shares: Mapping[int, Fraction],
    immediate_fraction: Fraction,
) -> dict[str, object]:
    """Split an eliminated PKO head between cash and recipient bounties."""
    bounty = _amount(eliminated_bounty, "eliminated_bounty")
    shares = _shares(recipient_shares)
    if not isinstance(immediate_fraction, Fraction) or not 0 <= immediate_fraction <= 1:
        raise ValueError("immediate_fraction must be a Fraction in [0, 1]")
    cash = bounty * immediate_fraction
    progressive = bounty - cash
    return {
        "immediate_cash": {seat: cash * share for seat, share in shares.items()},
        "bounty_increases": {seat: progressive * share for seat, share in shares.items()},
        "eliminated_bounty_after": Fraction(),
    }


def compute_mystery_bounty(
    prizes: tuple[tuple[Amount, Fraction], ...],
    recipient_shares: Mapping[int, Fraction],
) -> dict[str, object]:
    """Enumerate a supplied Mystery prize distribution and its expectation."""
    shares = _shares(recipient_shares)
    if not prizes:
        raise ValueError("prizes cannot be empty")
    parsed: list[tuple[Fraction, Fraction]] = []
    for index, (prize, probability) in enumerate(prizes):
        amount = _amount(prize, f"prize {index}")
        if not isinstance(probability, Fraction) or probability < 0:
            raise ValueError("prize probabilities must be non-negative Fractions")
        parsed.append((amount, probability))
    if sum((probability for _, probability in parsed), Fraction()) != 1:
        raise ValueError("prize probabilities must sum to 1")
    expected = sum((amount * probability for amount, probability in parsed), Fraction())
    return {
        "expected_prize": expected,
        "expected_cash": {seat: expected * share for seat, share in shares.items()},
        "outcomes": tuple(
            {
                "prize": amount,
                "probability": probability,
                "cash": {seat: amount * share for seat, share in shares.items()},
            }
            for amount, probability in parsed
        ),
    }


def compute_tko_bounty(
    eliminated_bounty: Amount,
    recipient_shares: Mapping[int, Fraction],
    immediate_fraction: Fraction,
    bounty_transfer_fraction: Fraction,
) -> dict[str, object]:
    """Apply an explicit TKO cash/recipient-bounty transfer policy."""
    bounty = _amount(eliminated_bounty, "eliminated_bounty")
    shares = _shares(recipient_shares)
    if (
        not isinstance(immediate_fraction, Fraction)
        or not isinstance(bounty_transfer_fraction, Fraction)
        or immediate_fraction < 0
        or bounty_transfer_fraction < 0
        or immediate_fraction + bounty_transfer_fraction != 1
    ):
        raise ValueError("TKO transfer fractions must be non-negative Fractions that sum to 1")
    cash = bounty * immediate_fraction
    transfer = bounty * bounty_transfer_fraction
    return {
        "immediate_cash": {seat: cash * share for seat, share in shares.items()},
        "bounty_increases": {seat: transfer * share for seat, share in shares.items()},
        "eliminated_bounty_after": Fraction(),
    }


def one_hand_tournament_utility(
    pre_icm: tuple[Amount, ...],
    post_icm: tuple[Amount, ...],
    immediate_cash: Mapping[int, Amount],
    *,
    elimination_count: int,
) -> tuple[Fraction, ...]:
    """Return post-ICM minus pre-ICM plus immediate bounty cash."""
    if isinstance(elimination_count, bool) or elimination_count != 1:
        raise ValueError("simultaneous eliminations are unsupported")
    if len(pre_icm) != len(post_icm) or not pre_icm:
        raise ValueError("pre_icm and post_icm must have the same non-zero length")
    pre = tuple(_amount(value, f"pre_icm[{i}]") for i, value in enumerate(pre_icm))
    post = tuple(_amount(value, f"post_icm[{i}]") for i, value in enumerate(post_icm))
    cash = [Fraction() for _ in pre]
    for seat, value in immediate_cash.items():
        if isinstance(seat, bool) or not isinstance(seat, int) or not 0 <= seat < len(cash):
            raise ValueError("immediate_cash contains an invalid seat")
        cash[seat] = _amount(value, f"immediate_cash[{seat}]")
    return tuple(post[i] - pre[i] + cash[i] for i in range(len(pre)))
