"""Game structure and rake: immutable accounting contracts.

Provides ForcedPost, SeatLedger, GameStructure, PotLayer, and RakePolicy.
All types are immutable. Integer chip accounting with exact conservation.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ForcedPost:
    """Immutable forced contribution: ante, small-blind, big-blind, or straddle."""

    seat: int
    kind: Literal["ante", "small-blind", "big-blind", "straddle"]
    amount: int

    def __post_init__(self):
        if not isinstance(self.seat, int) or self.seat < 0:
            raise ValueError(f"seat must be non-negative int, got {self.seat}")
        if not isinstance(self.amount, int) or self.amount < 0:
            raise ValueError(f"amount must be non-negative int, got {self.amount}")
        if isinstance(self.seat, bool) or isinstance(self.amount, bool):
            raise TypeError("bool-as-int rejected")


@dataclass(frozen=True)
class SeatLedger:
    """Immutable per-seat accounting snapshot."""

    starting_stack: int
    remaining: int
    street_committed: int
    total_contributed: int
    folded: bool
    all_in: bool

    def __post_init__(self):
        for field_name in ("starting_stack", "remaining", "street_committed", "total_contributed"):
            val = getattr(self, field_name)
            if not isinstance(val, int) or val < 0:
                raise ValueError(f"{field_name} must be non-negative int, got {val}")
            if isinstance(val, bool):
                raise TypeError("bool-as-int rejected")
        if not isinstance(self.folded, bool) or not isinstance(self.all_in, bool):
            raise TypeError("folded and all_in must be bool")


@dataclass(frozen=True)
class GameStructure:
    """Immutable game configuration: button, seats, forced posts, odd-chip order, reopening."""

    button: int
    seats: tuple[int, ...]
    forced_posts: tuple[ForcedPost, ...]
    odd_chip_order: tuple[int, ...]
    short_all_in_reopens: bool

    def __post_init__(self):
        if not isinstance(self.button, int) or self.button < 0:
            raise ValueError(f"button must be non-negative int, got {self.button}")
        if isinstance(self.button, bool):
            raise TypeError("bool-as-int rejected")
        if not isinstance(self.seats, tuple) or not all(isinstance(s, int) and s >= 0 for s in self.seats):
            raise ValueError("seats must be tuple of non-negative ints")
        if any(isinstance(s, bool) for s in self.seats):
            raise TypeError("bool-as-int rejected in seats")
        if self.button not in self.seats:
            raise ValueError(f"button {self.button} not in seats {self.seats}")
        if not isinstance(self.forced_posts, tuple):
            raise ValueError("forced_posts must be tuple")
        for post in self.forced_posts:
            if not isinstance(post, ForcedPost):
                raise TypeError(f"forced_posts entry must be ForcedPost, got {type(post)}")
            if post.seat not in self.seats:
                raise ValueError(f"forced post seat {post.seat} not in seats {self.seats}")
        if not isinstance(self.odd_chip_order, tuple) or not all(isinstance(s, int) and s >= 0 for s in self.odd_chip_order):
            raise ValueError("odd_chip_order must be tuple of non-negative ints")
        if any(isinstance(s, bool) for s in self.odd_chip_order):
            raise TypeError("bool-as-int rejected in odd_chip_order")
        if not isinstance(self.short_all_in_reopens, bool):
            raise TypeError("short_all_in_reopens must be bool")


@dataclass(frozen=True)
class PotLayer:
    """Immutable side-pot layer: amount, contributors, eligible winners."""

    amount: int
    contributors: frozenset[int]
    eligible: frozenset[int]

    def __post_init__(self):
        if not isinstance(self.amount, int) or self.amount < 0:
            raise ValueError(f"amount must be non-negative int, got {self.amount}")
        if isinstance(self.amount, bool):
            raise TypeError("bool-as-int rejected")
        if not isinstance(self.contributors, frozenset):
            raise TypeError("contributors must be frozenset")
        if not isinstance(self.eligible, frozenset):
            raise TypeError("eligible must be frozenset")
        if any(isinstance(seat, bool) or not isinstance(seat, int) or seat < 0 for seat in self.contributors):
            raise ValueError("contributors must contain only non-negative integers")
        if any(isinstance(seat, bool) or not isinstance(seat, int) or seat < 0 for seat in self.eligible):
            raise ValueError("eligible must contain only non-negative integers")
        if not self.eligible:
            raise ValueError("eligible winners must be non-empty")
        if not self.eligible.issubset(self.contributors):
            raise ValueError(f"eligible {self.eligible} must be subset of contributors {self.contributors}")


@dataclass(frozen=True)
class RakePolicy:
    """Immutable rational rake policy with explicit rounding, cap, minimum, NFND, and layer allocation."""

    rate_numerator: int
    rate_denominator: int
    cap: int | None
    minimum_pot: int | None
    no_flop_no_drop: bool
    rounding: Literal["floor", "ceiling", "nearest"]
    layer_order: Literal["top-down", "bottom-up"]

    def __post_init__(self):
        if not isinstance(self.rate_numerator, int) or self.rate_numerator < 0:
            raise ValueError(f"rate_numerator must be non-negative int, got {self.rate_numerator}")
        if not isinstance(self.rate_denominator, int) or self.rate_denominator <= 0:
            raise ValueError(f"rate_denominator must be positive int, got {self.rate_denominator}")
        if isinstance(self.rate_numerator, bool) or isinstance(self.rate_denominator, bool):
            raise TypeError("bool-as-int rejected")
        if self.rate_numerator > self.rate_denominator:
            raise ValueError(f"rate {self.rate_numerator}/{self.rate_denominator} exceeds 1")
        if self.cap is not None:
            if not isinstance(self.cap, int) or self.cap < 0:
                raise ValueError(f"cap must be non-negative int or None, got {self.cap}")
            if isinstance(self.cap, bool):
                raise TypeError("bool-as-int rejected")
        if self.minimum_pot is not None:
            if not isinstance(self.minimum_pot, int) or self.minimum_pot < 0:
                raise ValueError(f"minimum_pot must be non-negative int or None, got {self.minimum_pot}")
            if isinstance(self.minimum_pot, bool):
                raise TypeError("bool-as-int rejected")
        if not isinstance(self.no_flop_no_drop, bool):
            raise TypeError("no_flop_no_drop must be bool")
        if self.rounding not in ("floor", "ceiling", "nearest"):
            raise ValueError(f"rounding must be floor/ceiling/nearest, got {self.rounding}")
        if self.layer_order not in ("top-down", "bottom-up"):
            raise ValueError(f"layer_order must be top-down/bottom-up, got {self.layer_order}")


def _chip(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def apply_forced_posts(
    starting_stacks: tuple[int, ...], posts: tuple[ForcedPost, ...]
) -> tuple[SeatLedger, ...]:
    """Transfer each declared forced post exactly once into seat ledgers."""
    if not starting_stacks:
        raise ValueError("starting_stacks cannot be empty")
    stacks = [_chip(stack, f"starting_stacks[{seat}]") for seat, stack in enumerate(starting_stacks)]
    contributed = [0 for _ in stacks]
    for post in posts:
        if not isinstance(post, ForcedPost) or post.seat >= len(stacks):
            raise ValueError("forced post references an invalid seat")
        payment = min(post.amount, stacks[post.seat])
        stacks[post.seat] -= payment
        contributed[post.seat] += payment
    return tuple(
        SeatLedger(
            starting_stack=starting_stacks[seat],
            remaining=stacks[seat],
            street_committed=contributed[seat],
            total_contributed=contributed[seat],
            folded=False,
            all_in=stacks[seat] == 0,
        )
        for seat in range(len(stacks))
    )


def pairwise_effective_stack(ledgers: tuple[SeatLedger, ...], seat_a: int, seat_b: int) -> int:
    """Return the matched remaining stack between two distinct seats."""
    if (
        isinstance(seat_a, bool)
        or isinstance(seat_b, bool)
        or not isinstance(seat_a, int)
        or not isinstance(seat_b, int)
        or seat_a == seat_b
        or not 0 <= seat_a < len(ledgers)
        or not 0 <= seat_b < len(ledgers)
    ):
        raise ValueError("effective-stack seats must be distinct valid indices")
    return min(ledgers[seat_a].remaining, ledgers[seat_b].remaining)


def refund_uncalled_excess(contributions: tuple[int, ...]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Refund the unique highest contribution above the second-highest amount."""
    if len(contributions) < 2:
        raise ValueError("at least two contribution entries are required")
    values = [_chip(value, f"contributions[{seat}]") for seat, value in enumerate(contributions)]
    refunds = [0 for _ in values]
    highest = max(values)
    leaders = [seat for seat, value in enumerate(values) if value == highest]
    if len(leaders) == 1:
        second = max(value for seat, value in enumerate(values) if seat != leaders[0])
        excess = highest - second
        values[leaders[0]] -= excess
        refunds[leaders[0]] = excess
    return tuple(values), tuple(refunds)


def build_pot_layers(
    contributions: tuple[int, ...], *, folded: frozenset[int] = frozenset()
) -> tuple[PotLayer, ...]:
    """Build exact contribution layers after uncalled excess has been refunded."""
    values = tuple(_chip(value, f"contributions[{seat}]") for seat, value in enumerate(contributions))
    if any(isinstance(seat, bool) or not isinstance(seat, int) or not 0 <= seat < len(values) for seat in folded):
        raise ValueError("folded contains an invalid seat")
    levels = sorted({value for value in values if value > 0})
    previous = 0
    layers: list[PotLayer] = []
    for level in levels:
        contributors = frozenset(seat for seat, value in enumerate(values) if value >= level)
        amount = (level - previous) * len(contributors)
        eligible = contributors.difference(folded)
        if not eligible:
            raise ValueError("pot layer has no eligible winner")
        layers.append(PotLayer(amount, contributors, eligible))
        previous = level
    return tuple(layers)


def calculate_rake(policy: RakePolicy, eligible_pot: int, *, flop_seen: bool) -> int:
    """Calculate one hand-level rake using exact integer rational arithmetic."""
    pot = _chip(eligible_pot, "eligible_pot")
    if not isinstance(flop_seen, bool):
        raise ValueError("flop_seen must be boolean")
    if (policy.no_flop_no_drop and not flop_seen) or (
        policy.minimum_pot is not None and pot < policy.minimum_pot
    ):
        return 0
    numerator = pot * policy.rate_numerator
    quotient, remainder = divmod(numerator, policy.rate_denominator)
    if policy.rounding == "floor":
        rake = quotient
    elif policy.rounding == "ceiling":
        rake = quotient + (remainder > 0)
    else:
        rake = quotient + (2 * remainder >= policy.rate_denominator)
    if policy.cap is not None:
        rake = min(rake, policy.cap)
    return min(rake, pot)


def allocate_rake(
    layers: tuple[PotLayer, ...], total_rake: int, *, layer_order: str
) -> tuple[int, ...]:
    """Allocate an exact hand-level rake across layers in declared order."""
    remaining = _chip(total_rake, "total_rake")
    if remaining > sum(layer.amount for layer in layers):
        raise ValueError("total_rake exceeds pot")
    if layer_order not in ("top-down", "bottom-up"):
        raise ValueError("layer_order must be top-down or bottom-up")
    allocated = [0 for _ in layers]
    indices = range(len(layers) - 1, -1, -1) if layer_order == "top-down" else range(len(layers))
    for index in indices:
        take = min(remaining, layers[index].amount)
        allocated[index] = take
        remaining -= take
    return tuple(allocated)


def award_pot_layers(
    layers: tuple[PotLayer, ...],
    *,
    winners_by_layer: tuple[frozenset[int], ...],
    odd_chip_order: tuple[int, ...],
    rake_by_layer: tuple[int, ...] | None = None,
) -> tuple[int, ...]:
    """Award every post-rake layer, assigning remainders by explicit order."""
    if len(winners_by_layer) != len(layers):
        raise ValueError("one winner set is required per layer")
    if len(set(odd_chip_order)) != len(odd_chip_order) or any(
        isinstance(seat, bool) or not isinstance(seat, int) or seat < 0 for seat in odd_chip_order
    ):
        raise ValueError("odd_chip_order must contain unique non-negative seats")
    if rake_by_layer is None:
        rake_by_layer = tuple(0 for _ in layers)
    if len(rake_by_layer) != len(layers):
        raise ValueError("one rake amount is required per layer")
    seat_count = 1 + max((seat for layer in layers for seat in layer.contributors), default=-1)
    awards = [0 for _ in range(seat_count)]
    for layer, winners, rake in zip(layers, winners_by_layer, rake_by_layer, strict=True):
        rake = _chip(rake, "layer rake")
        if rake > layer.amount:
            raise ValueError("layer rake exceeds layer amount")
        if not winners or not winners.issubset(layer.eligible):
            raise ValueError("winners must be a non-empty subset of eligible seats")
        ordered = [seat for seat in odd_chip_order if seat in winners]
        if len(ordered) != len(winners):
            raise ValueError("odd_chip_order must include every winner")
        quotient, remainder = divmod(layer.amount - rake, len(winners))
        for seat in winners:
            awards[seat] += quotient
        for seat in ordered[:remainder]:
            awards[seat] += 1
    return tuple(awards)


def verify_terminal_conservation(
    initial_stacks: tuple[int, ...], final_stacks: tuple[int, ...], *, house_rake: int
) -> None:
    """Raise unless final player chips plus house rake equal initial chips."""
    if len(initial_stacks) != len(final_stacks) or not initial_stacks:
        raise ValueError("initial and final stacks must have equal non-zero length")
    initial = sum(_chip(value, f"initial_stacks[{i}]") for i, value in enumerate(initial_stacks))
    final = sum(_chip(value, f"final_stacks[{i}]") for i, value in enumerate(final_stacks))
    rake = _chip(house_rake, "house_rake")
    if final + rake != initial:
        raise ValueError("terminal chip conservation failed")
