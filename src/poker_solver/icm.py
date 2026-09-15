"""Bounded small-field Independent Chip Model evaluator."""

from __future__ import annotations

from math import isfinite
from typing import Sequence

MAX_ICM_PLAYERS = 10


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{field} must not be bool")
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def calculate_icm_equity(
    stacks: Sequence[int | float], payouts: Sequence[int | float]
) -> tuple[float, ...]:
    """Compute ICM payout equities with an O(n*2**n) subset dynamic program.

    This evaluates a supplied stack and payout state. It does not solve
    tournament strategy or future bounty equity.
    """
    if isinstance(stacks, (str, bytes)) or isinstance(payouts, (str, bytes)):
        raise ValueError("stacks and payouts must be numeric sequences")
    n = len(stacks)
    if n == 0:
        raise ValueError("at least one player is required")
    if n > MAX_ICM_PLAYERS:
        raise ValueError(f"ICM supports at most {MAX_ICM_PLAYERS} players")
    if len(payouts) < n:
        raise ValueError("payout vector must contain at least one payout per player")

    stack_values = tuple(_finite_number(value, f"stack[{i}]") for i, value in enumerate(stacks))
    if any(value <= 0 for value in stack_values):
        raise ValueError("stacks must be positive")
    payout_values = tuple(_finite_number(value, f"payout[{i}]") for i, value in enumerate(payouts[:n]))
    if any(value < 0 for value in payout_values):
        raise ValueError("payouts must be non-negative")
    if any(payout_values[i] < payout_values[i + 1] for i in range(n - 1)):
        raise ValueError("payouts must be non-increasing")

    total_stack = sum(stack_values)
    subset_stack = [0.0] * (1 << n)
    for mask in range(1, 1 << n):
        bit = mask & -mask
        player = bit.bit_length() - 1
        subset_stack[mask] = subset_stack[mask ^ bit] + stack_values[player]

    prefix_probability = [0.0] * (1 << n)
    prefix_probability[0] = 1.0
    equities = [0.0] * n
    full_mask = (1 << n) - 1
    for mask in range(1 << n):
        probability = prefix_probability[mask]
        if probability == 0.0 or mask == full_mask:
            continue
        place = mask.bit_count()
        remaining_stack = total_stack - subset_stack[mask]
        for player, stack in enumerate(stack_values):
            bit = 1 << player
            if mask & bit:
                continue
            branch = probability * stack / remaining_stack
            prefix_probability[mask | bit] += branch
            equities[player] += branch * payout_values[place]

    # Remove only accumulated floating summation drift so the public vector
    # conserves the declared payout pool under ordinary Python summation.
    equities[-1] += sum(payout_values) - sum(equities)
    return tuple(equities)
