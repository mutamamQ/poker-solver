"""Bounded exact two-to-nine-player one-round preflop state."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from fractions import Fraction
from math import isfinite, prod
from types import MappingProxyType
from typing import TypeAlias

from .game_structure import (
    ForcedPost,
    award_pot_layers,
    build_pot_layers,
    refund_uncalled_excess,
    verify_terminal_conservation,
)
from .model import Action, CHANCE, TERMINAL
from .preflop import WeightedCombo
from .sizing import fixed_sizes, validate_size_expression

DealN: TypeAlias = tuple[tuple[int, int], ...]
ContinuationKeyN: TypeAlias = tuple[DealN, tuple["NPlayerPreflopPublicAction", ...]]

# The reused N-player collector and CFR traversals are recursive and default to
# this depth. Reject configurations whose declared structural bound exceeds it
# instead of accepting a finite game that can fail with RecursionError.
_MAX_STRUCTURAL_DEPTH = 512


def _nonnegative(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _positive(value: object, name: str) -> int:
    result = _nonnegative(value, name)
    if result == 0:
        raise ValueError(f"{name} must be positive")
    return result


def _seat_tuple(value: object, n: int, name: str) -> tuple[object, ...]:
    if not isinstance(value, tuple) or len(value) != n:
        raise ValueError(f"{name} length must equal num_players")
    return value


def _valid_cards(cards: object) -> bool:
    return (
        isinstance(cards, tuple)
        and len(cards) == 2
        and all(
            isinstance(card, int)
            and not isinstance(card, bool)
            and 0 <= card <= 51
            for card in cards
        )
        and cards[0] != cards[1]
    )


def _valid_deal_shape(deal: object, n: int) -> bool:
    return (
        isinstance(deal, tuple)
        and len(deal) == n
        and all(_valid_cards(combo) for combo in deal)
        and len({card for combo in deal for card in combo}) == 2 * n
    )


def _combo_mass(combo: WeightedCombo) -> Fraction:
    try:
        value = Fraction(str(combo.weight))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError("range weight must be finite and positive") from exc
    if value <= 0 or not isfinite(float(value)):
        raise ValueError("range weight must be finite and positive")
    return value


@dataclass(frozen=True, slots=True)
class _FrozenExpression(Mapping[str, object]):
    """Small immutable, hashable mapping used by frozen sizing rules."""

    _items: tuple[tuple[str, object], ...]

    def __post_init__(self) -> None:
        hash(self._items)

    def __getitem__(self, key: str) -> object:
        for candidate, value in self._items:
            if candidate == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _value in self._items)

    def __len__(self) -> int:
        return len(self._items)


def _freeze_expression(expression: Mapping[str, object]) -> Mapping[str, object]:
    copied = dict(expression)
    validate_size_expression(copied)
    return _FrozenExpression(tuple(sorted(copied.items())))


def _expression_identity(expression: Mapping[str, object]) -> tuple[tuple[str, object], ...]:
    return tuple(sorted(dict(expression).items()))


@dataclass(frozen=True, slots=True)
class NPlayerPreflopSizingRule:
    position: str
    raise_count: int
    cold_callers: int
    relation: str
    expressions: tuple[Mapping[str, object], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.position, str) or not self.position:
            raise ValueError("position must be a non-empty string")
        _nonnegative(self.raise_count, "raise_count")
        _nonnegative(self.cold_callers, "cold_callers")
        if self.relation not in ("NA", "IP", "OOP"):
            raise ValueError("relation must be NA, IP, or OOP")
        if not isinstance(self.expressions, tuple) or not self.expressions:
            raise ValueError("expressions must be a non-empty tuple")
        try:
            expressions = tuple(_freeze_expression(expression) for expression in self.expressions)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid sizing expression") from exc
        object.__setattr__(self, "expressions", expressions)


@dataclass(frozen=True, slots=True)
class NPlayerPreflopPublicAction:
    actor: int
    action: Action

    def __post_init__(self) -> None:
        if isinstance(self.actor, bool) or not isinstance(self.actor, int) or self.actor < 0:
            raise ValueError("history actor must be a non-negative integer")
        if not isinstance(self.action, Action):
            raise ValueError("history action must be Action")


@dataclass(frozen=True, slots=True)
class NPlayerPreflopContinuation:
    kind: str
    provenance: str
    source: str
    payoff_table: Mapping[ContinuationKeyN, tuple[Fraction, ...]]
    showdown_ranks: Mapping[DealN, tuple[int, ...]]
    odd_chip_order: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.kind not in ("terminal-table", "showdown-ranks"):
            raise ValueError("continuation kind must be terminal-table or showdown-ranks")
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError("continuation provenance must be non-empty")
        if self.source not in ("supplied", "derived"):
            raise ValueError("continuation source must be supplied or derived")
        if not isinstance(self.payoff_table, Mapping) or not isinstance(self.showdown_ranks, Mapping):
            raise ValueError("continuation tables must be mappings")
        if not isinstance(self.odd_chip_order, tuple):
            raise ValueError("odd_chip_order must be a tuple")
        if (
            any(
                isinstance(seat, bool) or not isinstance(seat, int) or seat < 0
                for seat in self.odd_chip_order
            )
            or len(set(self.odd_chip_order)) != len(self.odd_chip_order)
        ):
            raise ValueError("odd_chip_order must contain unique non-negative integer seats")

        payoff: dict[ContinuationKeyN, tuple[Fraction, ...]] = {}
        for key, values in self.payoff_table.items():
            if (
                not isinstance(key, tuple)
                or len(key) != 2
                or not isinstance(key[0], tuple)
                or not isinstance(key[1], tuple)
                or any(not isinstance(item, NPlayerPreflopPublicAction) for item in key[1])
                or not isinstance(values, tuple)
                or any(isinstance(value, bool) for value in values)
            ):
                raise ValueError("invalid terminal-table entry")
            try:
                exact = tuple(Fraction(value) for value in values)
            except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
                raise ValueError("terminal values must be finite exact numbers") from exc
            if any(not isfinite(float(value)) for value in exact) or sum(exact) != 0:
                raise ValueError("terminal values must be finite and zero-sum")
            payoff[key] = exact

        ranks_copy: dict[DealN, tuple[int, ...]] = {}
        for deal, ranks in self.showdown_ranks.items():
            if not isinstance(deal, tuple) or not isinstance(ranks, tuple) or any(
                isinstance(rank, bool) or not isinstance(rank, int) for rank in ranks
            ):
                raise ValueError("invalid showdown-ranks entry")
            ranks_copy[deal] = tuple(ranks)

        if self.kind == "terminal-table":
            if ranks_copy or self.odd_chip_order:
                raise ValueError("terminal-table continuation cannot contain ranks or odd-chip order")
        else:
            if payoff:
                raise ValueError("showdown-ranks continuation cannot contain payoff values")

        object.__setattr__(self, "payoff_table", MappingProxyType(payoff))
        object.__setattr__(self, "showdown_ranks", MappingProxyType(ranks_copy))
        object.__setattr__(self, "odd_chip_order", tuple(self.odd_chip_order))


_POSITION_LABELS: dict[int, tuple[str, ...]] = {
    2: ("BTN/SB", "BB"),
    3: ("BTN", "SB", "BB"),
    4: ("CO", "BTN", "SB", "BB"),
    5: ("HJ", "CO", "BTN", "SB", "BB"),
    6: ("UTG", "HJ", "CO", "BTN", "SB", "BB"),
    7: ("UTG", "MP", "HJ", "CO", "BTN", "SB", "BB"),
    8: ("UTG", "UTG+1", "MP", "HJ", "CO", "BTN", "SB", "BB"),
    9: ("UTG", "UTG+1", "MP", "LJ", "HJ", "CO", "BTN", "SB", "BB"),
}


@dataclass(frozen=True, slots=True)
class NPlayerPreflopConfig:
    version: str
    num_players: int
    button: int
    starting_stacks: tuple[int, ...]
    forced_posts: tuple[ForcedPost, ...]
    straddle_variant: str
    ranges: tuple[tuple[WeightedCombo, ...], ...]
    sizing_rules: tuple[NPlayerPreflopSizingRule, ...]
    max_raises: int
    max_deals: int
    max_nodes: int
    short_all_in_reopens: bool
    continuation: NPlayerPreflopContinuation

    def __post_init__(self) -> None:
        if self.version != "nplayer-preflop-v1":
            raise ValueError("version must be nplayer-preflop-v1")
        if (
            isinstance(self.num_players, bool)
            or not isinstance(self.num_players, int)
            or not 2 <= self.num_players <= 9
        ):
            raise ValueError("num_players must be an integer from 2 to 9")
        n = self.num_players
        if (
            isinstance(self.button, bool)
            or not isinstance(self.button, int)
            or not 0 <= self.button < n
        ):
            raise ValueError("button must be a valid integer seat")
        stacks = tuple(
            _positive(value, "starting stack")
            for value in _seat_tuple(self.starting_stacks, n, "starting_stacks")
        )

        if not isinstance(self.forced_posts, tuple):
            raise ValueError("forced_posts must be a tuple")
        posts = tuple(self.forced_posts)
        if any(not isinstance(post, ForcedPost) for post in posts):
            raise ValueError("forced_posts must contain ForcedPost values")
        if any(
            not isinstance(post.kind, str)
            or post.kind not in {"ante", "small-blind", "big-blind", "straddle"}
            for post in posts
        ):
            raise ValueError("unsupported forced post kind")
        cumulative = [0] * n
        for post in posts:
            if post.seat >= n:
                raise ValueError("forced post references an invalid seat")
            _positive(post.amount, "forced post amount")
            cumulative[post.seat] += post.amount
        if any(cumulative[seat] > stacks[seat] for seat in range(n)):
            raise ValueError("cumulative forced posts exceed a starting stack")
        if sum(cumulative[seat] < stacks[seat] for seat in range(n)) < 2:
            raise ValueError("at least two seats must have chips after forced posts")

        sb_seat = self.button if n == 2 else (self.button + 1) % n
        bb_seat = (self.button + 1) % n if n == 2 else (self.button + 2) % n
        small_blinds = tuple(post for post in posts if post.kind == "small-blind")
        big_blinds = tuple(post for post in posts if post.kind == "big-blind")
        if len(small_blinds) != 1 or small_blinds[0].seat != sb_seat:
            raise ValueError("exactly one small blind is required on the derived SB seat")
        if len(big_blinds) != 1 or big_blinds[0].seat != bb_seat:
            raise ValueError("exactly one big blind is required on the derived BB seat")
        if small_blinds[0].amount > big_blinds[0].amount:
            raise ValueError("small blind cannot exceed big blind")

        antes = tuple(post for post in posts if post.kind == "ante")
        if antes:
            if (
                len(antes) != n
                or {post.seat for post in antes} != set(range(n))
                or len({post.amount for post in antes}) != 1
            ):
                raise ValueError("antes must be one identical positive ante for every seat")

        if self.straddle_variant not in ("none", "standard", "double", "mississippi"):
            raise ValueError("invalid straddle_variant")
        straddles = tuple(post for post in posts if post.kind == "straddle")
        operational_utg = (bb_seat + 1) % n
        operational_utg1 = (operational_utg + 1) % n
        if self.straddle_variant == "none":
            if straddles:
                raise ValueError("straddle_variant none cannot declare a straddle")
        elif self.straddle_variant == "standard":
            if n < 3 or len(straddles) != 1 or straddles[0].seat != operational_utg:
                raise ValueError("standard straddle requires operational UTG and N>=3")
        elif self.straddle_variant == "double":
            if (
                n < 4
                or len(straddles) != 2
                or tuple(post.seat for post in straddles) != (operational_utg, operational_utg1)
            ):
                raise ValueError("double straddle requires ordered UTG/UTG+1 and N>=4")
        else:
            if n < 3 or len(straddles) != 1 or straddles[0].seat in (sb_seat, bb_seat):
                raise ValueError("mississippi straddle requires one non-blind seat and N>=3")
        previous_wager = big_blinds[0].amount
        for post in straddles:
            if post.amount <= previous_wager:
                raise ValueError("straddle amounts must strictly increase")
            previous_wager = post.amount

        ranges_raw = _seat_tuple(self.ranges, n, "ranges")
        ranges: list[tuple[WeightedCombo, ...]] = []
        for player_range in ranges_raw:
            if not isinstance(player_range, tuple) or not player_range:
                raise ValueError("each range must be a non-empty tuple")
            if any(not isinstance(combo, WeightedCombo) for combo in player_range):
                raise ValueError("ranges must contain WeightedCombo values")
            if any(not _valid_cards(combo.cards) for combo in player_range):
                raise ValueError("range combos must contain valid cards in 0..51")
            if len({combo.cards for combo in player_range}) != len(player_range):
                raise ValueError("range combos must be unique within a seat")
            for combo in player_range:
                _combo_mass(combo)
            ranges.append(tuple(player_range))

        if not isinstance(self.sizing_rules, tuple):
            raise ValueError("sizing_rules must be a tuple")
        rules = tuple(self.sizing_rules)
        valid_positions = set(_POSITION_LABELS[n])
        if any(
            not isinstance(rule, NPlayerPreflopSizingRule) or rule.position not in valid_positions
            for rule in rules
        ):
            raise ValueError("sizing rules must use canonical positions")
        sizing_keys = tuple(
            (rule.position, rule.raise_count, rule.cold_callers, rule.relation)
            for rule in rules
        )
        if len(set(sizing_keys)) != len(sizing_keys):
            raise ValueError("duplicate sizing rule key")

        max_raises = _positive(self.max_raises, "max_raises")
        _positive(self.max_deals, "max_deals")
        _positive(self.max_nodes, "max_nodes")
        if 2 + n + max_raises * (n - 1) > _MAX_STRUCTURAL_DEPTH:
            raise ValueError("max_raises exceeds the supported structural depth bound")
        if prod(len(player_range) for player_range in ranges) > self.max_deals:
            raise ValueError("candidate product exceeds max_deals")
        if not isinstance(self.short_all_in_reopens, bool):
            raise ValueError("short_all_in_reopens must be boolean")
        if not isinstance(self.continuation, NPlayerPreflopContinuation):
            raise ValueError("continuation must be NPlayerPreflopContinuation")

        continuation = self.continuation
        if continuation.kind == "terminal-table":
            for (deal, history), values in continuation.payoff_table.items():
                if not _valid_deal_shape(deal, n):
                    raise ValueError("terminal-table deals must contain N disjoint combos")
                if any(not 0 <= item.actor < n for item in history):
                    raise ValueError("terminal history actor is outside the table")
                if len(values) != n:
                    raise ValueError("terminal values must contain N utilities")
        else:
            if (
                len(continuation.odd_chip_order) != n
                or set(continuation.odd_chip_order) != set(range(n))
            ):
                raise ValueError("odd_chip_order must be a permutation of all seats")
            for deal, ranks in continuation.showdown_ranks.items():
                if not _valid_deal_shape(deal, n) or len(ranks) != n:
                    raise ValueError("showdown-ranks entries must contain one rank per seat")

        object.__setattr__(self, "starting_stacks", stacks)
        object.__setattr__(self, "forced_posts", posts)
        object.__setattr__(self, "ranges", tuple(ranges))
        object.__setattr__(self, "sizing_rules", rules)

        compatible = {
            deal for deal, _mass in enumerate_nplayer_preflop_deals(self)
        }
        if continuation.kind == "showdown-ranks":
            if set(continuation.showdown_ranks) != compatible:
                raise ValueError("showdown ranks must cover exactly every compatible deal")
        elif any(
            deal not in compatible
            for deal, _history in continuation.payoff_table
        ):
            raise ValueError("terminal-table contains an incompatible deal")


def enumerate_nplayer_preflop_deals(
    config: NPlayerPreflopConfig,
) -> tuple[tuple[DealN, Fraction], ...]:
    """Enumerate compatible private deals in range order with normalized exact mass."""
    if not isinstance(config, NPlayerPreflopConfig):
        raise ValueError("config must be NPlayerPreflopConfig")
    if prod(len(player_range) for player_range in config.ranges) > config.max_deals:
        raise ValueError("candidate product exceeds max_deals")
    results: list[tuple[DealN, Fraction]] = []

    def walk(
        seat: int,
        used: frozenset[int],
        deal: DealN,
        mass: Fraction,
    ) -> None:
        if seat == config.num_players:
            results.append((deal, mass))
            return
        for combo in config.ranges[seat]:
            if used.isdisjoint(combo.cards):
                walk(
                    seat + 1,
                    used | frozenset(combo.cards),
                    deal + (combo.cards,),
                    mass * _combo_mass(combo),
                )

    walk(0, frozenset(), (), Fraction(1))
    if not results:
        raise ValueError("ranges produce no compatible deals")
    total = sum((mass for _, mass in results), Fraction(0))
    if total <= 0:
        raise ValueError("compatible deals have zero total mass")
    return tuple((deal, mass / total) for deal, mass in results)


def _ordered_after(seat: int, candidates: tuple[int, ...], n: int) -> tuple[int, ...]:
    candidate_set = set(candidates)
    return tuple(
        candidate
        for step in range(1, n + 1)
        if (candidate := (seat + step) % n) in candidate_set
    )


def _blind_seats(config: NPlayerPreflopConfig) -> tuple[int, int]:
    n = config.num_players
    if n == 2:
        return config.button, (config.button + 1) % n
    return (config.button + 1) % n, (config.button + 2) % n


def _position_map(config: NPlayerPreflopConfig) -> dict[int, str]:
    n = config.num_players
    _, bb = _blind_seats(config)
    order = _ordered_after(bb, tuple(range(n)), n)
    return dict(zip(order, _POSITION_LABELS[n], strict=True))


def _active(folded: tuple[bool, ...], remaining: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(
        seat
        for seat in range(len(folded))
        if not folded[seat] and remaining[seat] > 0
    )


def _initial_pending(
    config: NPlayerPreflopConfig,
    remaining: tuple[int, ...],
) -> tuple[int, ...]:
    _, bb = _blind_seats(config)
    straddles = tuple(post for post in config.forced_posts if post.kind == "straddle")
    anchor = straddles[-1].seat if straddles else bb
    return _ordered_after(anchor, tuple(seat for seat in range(config.num_players) if remaining[seat] > 0), config.num_players)


def _root_components(
    config: NPlayerPreflopConfig,
) -> tuple[
    int,
    tuple[int, ...],
    tuple[int, ...],
    tuple[int, ...],
    tuple[int, ...],
    tuple[bool, ...],
    int,
]:
    n = config.num_players
    contributed = [0] * n
    street = [0] * n
    remaining = list(config.starting_stacks)
    for post in config.forced_posts:
        remaining[post.seat] -= post.amount
        contributed[post.seat] += post.amount
        if post.kind != "ante":
            street[post.seat] += post.amount
    remaining_tuple = tuple(remaining)
    pending = _initial_pending(config, remaining_tuple)
    return (
        sum(contributed),
        tuple(street),
        tuple(contributed),
        remaining_tuple,
        pending,
        tuple(value > 0 for value in remaining_tuple),
        max(street),
    )


def _last_aggressor(history: tuple[NPlayerPreflopPublicAction, ...]) -> int | None:
    for item in reversed(history):
        if item.action.kind == "RAISE":
            return item.actor
    return None


def _relation(config: NPlayerPreflopConfig, actor: int, aggressor: int | None) -> str:
    if aggressor is None:
        return "NA"
    n = config.num_players
    postflop_order = tuple((config.button + step) % n for step in range(1, n + 1))
    positions = {seat: index for index, seat in enumerate(postflop_order)}
    return "IP" if positions[actor] > positions[aggressor] else "OOP"


def _cold_callers(state: "NPlayerPreflopState", actor: int) -> int:
    start = 0
    for index, item in enumerate(state.history):
        if item.action.kind == "RAISE":
            start = index + 1
    latest: dict[int, str] = {}
    for item in state.history[start:]:
        latest[item.actor] = item.action.kind
    return sum(
        kind == "CALL" and seat != actor and not state.folded[seat]
        for seat, kind in latest.items()
    )


@dataclass(frozen=True, slots=True)
class NPlayerPreflopState:
    config: NPlayerPreflopConfig
    private_deal: DealN | None
    acting_player: int
    pot: int
    street_committed: tuple[int, ...]
    total_contributed: tuple[int, ...]
    remaining: tuple[int, ...]
    folded: tuple[bool, ...]
    pending: tuple[int, ...]
    can_raise: tuple[bool, ...]
    last_raise_increment: int
    raise_count: int
    history: tuple[NPlayerPreflopPublicAction, ...]
    terminal_values: tuple[Fraction, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.config, NPlayerPreflopConfig):
            raise ValueError("config must be NPlayerPreflopConfig")
        n = self.config.num_players
        if (
            isinstance(self.acting_player, bool)
            or not isinstance(self.acting_player, int)
            or self.acting_player not in (CHANCE, TERMINAL, *range(n))
        ):
            raise ValueError("invalid acting player")
        integer_fields: dict[str, tuple[int, ...]] = {}
        for name in ("street_committed", "total_contributed", "remaining"):
            integer_fields[name] = tuple(
                _nonnegative(value, name)
                for value in _seat_tuple(getattr(self, name), n, name)
            )
        street = integer_fields["street_committed"]
        contributed = integer_fields["total_contributed"]
        remaining = integer_fields["remaining"]
        _nonnegative(self.pot, "pot")
        if self.pot != sum(contributed):
            raise ValueError("pot must equal sum(total_contributed)")
        if any(
            remaining[seat] + contributed[seat] != self.config.starting_stacks[seat]
            for seat in range(n)
        ):
            raise ValueError("remaining plus contribution must equal starting stack")
        if any(street[seat] > contributed[seat] for seat in range(n)):
            raise ValueError("street commitment cannot exceed total contribution")

        folded = _seat_tuple(self.folded, n, "folded")
        if any(not isinstance(value, bool) for value in folded):
            raise ValueError("folded must contain booleans")
        if not isinstance(self.pending, tuple) or len(set(self.pending)) != len(self.pending):
            raise ValueError("pending must contain unique seats")
        if any(
            isinstance(seat, bool)
            or not isinstance(seat, int)
            or not 0 <= seat < n
            or folded[seat]
            or remaining[seat] == 0
            for seat in self.pending
        ):
            raise ValueError("pending contains an invalid responder")
        can_raise = _seat_tuple(self.can_raise, n, "can_raise")
        if any(not isinstance(value, bool) for value in can_raise):
            raise ValueError("can_raise must contain booleans")
        if any(
            can_raise[seat] and (folded[seat] or remaining[seat] == 0)
            for seat in range(n)
        ):
            raise ValueError("folded or all-in seats cannot raise")
        _positive(self.last_raise_increment, "last_raise_increment")
        _nonnegative(self.raise_count, "raise_count")
        if self.raise_count > self.config.max_raises:
            raise ValueError("raise_count exceeds max_raises")
        if not isinstance(self.history, tuple) or any(
            not isinstance(item, NPlayerPreflopPublicAction) or not 0 <= item.actor < n
            for item in self.history
        ):
            raise ValueError("history must contain actor-labelled actions")

        if self.acting_player == CHANCE:
            if self.private_deal is not None or self.history or self.terminal_values is not None:
                raise ValueError("invalid chance root")
            (
                root_pot,
                root_street,
                root_contributed,
                root_remaining,
                root_pending,
                root_can_raise,
                root_increment,
            ) = _root_components(self.config)
            if (
                self.pot != root_pot
                or street != root_street
                or contributed != root_contributed
                or remaining != root_remaining
                or tuple(folded) != (False,) * n
                or self.pending != root_pending
                or tuple(can_raise) != root_can_raise
                or self.last_raise_increment != root_increment
                or self.raise_count != 0
            ):
                raise ValueError("chance root violates root invariants")
        else:
            if self.private_deal is None:
                raise ValueError("dealt state requires a private deal")
            valid_deals = {deal for deal, _ in enumerate_nplayer_preflop_deals(self.config)}
            if self.private_deal not in valid_deals:
                raise ValueError("dealt state uses an incompatible private deal")
        if self.acting_player == TERMINAL:
            if self.pending:
                raise ValueError("terminal state must have empty pending")
            if not isinstance(self.terminal_values, tuple) or len(self.terminal_values) != n:
                raise ValueError("terminal state requires N utilities")
            if any(isinstance(value, bool) for value in self.terminal_values):
                raise ValueError("terminal utilities must be exact numbers")
            exact = tuple(Fraction(value) for value in self.terminal_values)
            if any(not isfinite(float(value)) for value in exact) or sum(exact) != 0:
                raise ValueError("terminal utilities must be finite and zero-sum")
            object.__setattr__(self, "terminal_values", exact)
        elif self.terminal_values is not None:
            raise ValueError("nonterminal state cannot contain utilities")
        elif self.acting_player != CHANCE and (
            not self.pending or self.acting_player != self.pending[0]
        ):
            raise ValueError("acting player must be first pending responder")

        object.__setattr__(self, "street_committed", street)
        object.__setattr__(self, "total_contributed", contributed)
        object.__setattr__(self, "remaining", remaining)
        object.__setattr__(self, "folded", tuple(folded))
        object.__setattr__(self, "can_raise", tuple(can_raise))

    def num_players(self) -> int:
        return self.config.num_players

    def current_player(self) -> int:
        return self.acting_player

    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]:
        if self.acting_player != CHANCE:
            return ()
        return tuple(
            (Action("DEAL", index), float(probability))
            for index, (_, probability) in enumerate(enumerate_nplayer_preflop_deals(self.config))
        )

    def legal_actions(self) -> tuple[Action, ...]:
        if self.acting_player in (CHANCE, TERMINAL):
            return ()
        actor = self.acting_player
        live = tuple(seat for seat in range(self.config.num_players) if not self.folded[seat])
        highest = max(self.street_committed[seat] for seat in live)
        own = self.street_committed[actor]
        to_call = highest - own
        if to_call > 0:
            actions: list[Action] = [
                Action("FOLD"),
                Action("CALL", min(highest, own + self.remaining[actor])),
            ]
        else:
            actions = [Action("CHECK")]

        if (
            self.can_raise[actor]
            and self.remaining[actor] > to_call
            and self.raise_count < self.config.max_raises
        ):
            position = _position_map(self.config)[actor]
            cold_callers = _cold_callers(self, actor)
            relation = _relation(self.config, actor, _last_aggressor(self.history))
            rule = next(
                (
                    candidate
                    for candidate in self.config.sizing_rules
                    if (
                        candidate.position,
                        candidate.raise_count,
                        candidate.cold_callers,
                        candidate.relation,
                    )
                    == (position, self.raise_count, cold_callers, relation)
                ),
                None,
            )
            context = {
                "pot": self.pot,
                "own_commitment": own,
                "highest_commitment": highest,
                "remaining_stack": self.remaining[actor],
                "big_blind": next(
                    post.amount for post in self.config.forced_posts if post.kind == "big-blind"
                ),
                "minimum_raise_to": highest + self.last_raise_increment,
                "pot_limit_max_raise_to": None,
                "short_all_in_allowed": True,
            }
            seen: set[int] = set()
            if rule is not None:
                expressions = tuple(dict(expression) for expression in rule.expressions)
                for choice in fixed_sizes(expressions, context):
                    if choice.target not in seen:
                        seen.add(choice.target)
                        actions.append(Action("RAISE", choice.target))
            all_in = own + self.remaining[actor]
            if highest < all_in and all_in not in seen:
                actions.append(Action("RAISE", all_in))
        return tuple(actions)

    def child(self, action: Action) -> "NPlayerPreflopState":
        if not isinstance(action, Action):
            raise ValueError("action must be Action")
        if self.acting_player == CHANCE:
            outcomes = self.chance_outcomes()
            if action not in {candidate for candidate, _ in outcomes}:
                raise ValueError("action is not legal")
            deal = enumerate_nplayer_preflop_deals(self.config)[action.amount][0]
            if not self.pending:
                return self._settle(private_deal=deal)
            return self._replace(private_deal=deal, acting_player=self.pending[0])
        if action not in self.legal_actions():
            raise ValueError("action is not legal")

        n = self.config.num_players
        actor = self.acting_player
        old_pending = self.pending
        old_can_raise = self.can_raise
        committed = list(self.street_committed)
        contributed = list(self.total_contributed)
        remaining = list(self.remaining)
        folded = list(self.folded)
        pending = [seat for seat in self.pending if seat != actor]
        can_raise = list(self.can_raise)
        pot = self.pot
        increment = self.last_raise_increment
        raise_count = self.raise_count
        history = self.history + (NPlayerPreflopPublicAction(actor, action),)

        if action.kind == "FOLD":
            folded[actor] = True
            can_raise[actor] = False
        elif action.kind == "CHECK":
            can_raise[actor] = False
        elif action.kind == "CALL":
            payment = action.amount - committed[actor]
            committed[actor] += payment
            contributed[actor] += payment
            remaining[actor] -= payment
            pot += payment
            can_raise[actor] = False
        elif action.kind == "RAISE":
            old_highest = max(
                committed[seat] for seat in range(n) if not folded[seat]
            )
            payment = action.amount - committed[actor]
            committed[actor] += payment
            contributed[actor] += payment
            remaining[actor] -= payment
            pot += payment
            active_others = tuple(
                seat
                for seat in range(n)
                if seat != actor and not folded[seat] and remaining[seat] > 0
            )
            pending = list(_ordered_after(actor, active_others, n))
            raise_size = action.amount - old_highest
            if raise_size >= increment:
                increment = raise_size
                can_raise = [
                    seat != actor and not folded[seat] and remaining[seat] > 0
                    for seat in range(n)
                ]
            elif self.config.short_all_in_reopens:
                can_raise = [
                    seat != actor and not folded[seat] and remaining[seat] > 0
                    for seat in range(n)
                ]
            else:
                can_raise = [
                    (
                        seat != actor
                        and seat in old_pending
                        and old_can_raise[seat]
                        and not folded[seat]
                        and remaining[seat] > 0
                    )
                    for seat in range(n)
                ]
            raise_count += 1
        else:
            raise ValueError("unsupported action")

        active_pending = tuple(
            seat for seat in pending if not folded[seat] and remaining[seat] > 0
        )
        live = tuple(seat for seat in range(n) if not folded[seat])
        changes = dict(
            pot=pot,
            street_committed=tuple(committed),
            total_contributed=tuple(contributed),
            remaining=tuple(remaining),
            folded=tuple(folded),
            pending=active_pending,
            can_raise=tuple(can_raise),
            last_raise_increment=increment,
            raise_count=raise_count,
            history=history,
        )
        if len(live) == 1 or not active_pending:
            return self._settle(**changes)
        return self._replace(acting_player=active_pending[0], **changes)

    def _settle(self, **changes: object) -> "NPlayerPreflopState":
        values = {field: getattr(self, field) for field in self.__dataclass_fields__}
        values.update(changes)
        deal = values["private_deal"]
        if not isinstance(deal, tuple):
            raise ValueError("settlement requires a private deal")
        n = self.config.num_players
        contributed = values["total_contributed"]
        current_remaining = values["remaining"]
        current_street = values["street_committed"]
        current_folded = values["folded"]
        history = values["history"]
        assert isinstance(contributed, tuple)
        assert isinstance(current_remaining, tuple)
        assert isinstance(current_street, tuple)
        assert isinstance(current_folded, tuple)
        assert isinstance(history, tuple)

        matched, refunds = refund_uncalled_excess(contributed)
        remaining = tuple(current_remaining[seat] + refunds[seat] for seat in range(n))
        street = tuple(current_street[seat] - refunds[seat] for seat in range(n))
        if any(value < 0 for value in street):
            raise ValueError("uncalled refund exceeds street commitment")
        live = tuple(seat for seat in range(n) if not current_folded[seat])

        if len(live) > 1 and self.config.continuation.kind == "terminal-table":
            key = (deal, history)
            if key not in self.config.continuation.payoff_table:
                raise ValueError("missing continuation value for closed preflop leaf")
            utilities = self.config.continuation.payoff_table[key]
        else:
            folded_set = frozenset(
                seat for seat, is_folded in enumerate(current_folded) if is_folded
            )
            layers = build_pot_layers(matched, folded=folded_set)
            if len(live) == 1:
                winners = tuple(frozenset(live) for _ in layers)
                odd_chip_order = tuple(range(n))
            else:
                ranks = self.config.continuation.showdown_ranks.get(deal)
                if ranks is None:
                    raise ValueError("missing showdown rank coverage for deal")
                winners_list: list[frozenset[int]] = []
                for layer in layers:
                    best = max(ranks[seat] for seat in layer.eligible)
                    winners_list.append(
                        frozenset(seat for seat in layer.eligible if ranks[seat] == best)
                    )
                winners = tuple(winners_list)
                odd_chip_order = self.config.continuation.odd_chip_order
            raw_awards = award_pot_layers(
                layers,
                winners_by_layer=winners,
                odd_chip_order=odd_chip_order,
            )
            awards = raw_awards + (0,) * (n - len(raw_awards))
            final = tuple(remaining[seat] + awards[seat] for seat in range(n))
            verify_terminal_conservation(self.config.starting_stacks, final, house_rake=0)
            utilities = tuple(
                Fraction(final[seat] - self.config.starting_stacks[seat])
                for seat in range(n)
            )

        values.update(
            acting_player=TERMINAL,
            pot=sum(matched),
            street_committed=street,
            total_contributed=matched,
            remaining=remaining,
            pending=(),
            terminal_values=tuple(Fraction(value) for value in utilities),
        )
        return NPlayerPreflopState(**values)  # type: ignore[arg-type]

    def information_state_key(self, player: int):
        n = self.config.num_players
        if (
            isinstance(player, bool)
            or not isinstance(player, int)
            or not 0 <= player < n
            or self.private_deal is None
        ):
            raise ValueError("information key requires a dealt state and valid player")
        sizing_identity = tuple(
            (
                rule.position,
                rule.raise_count,
                rule.cold_callers,
                rule.relation,
                tuple(_expression_identity(expression) for expression in rule.expressions),
            )
            for rule in self.config.sizing_rules
        )
        continuation = self.config.continuation
        return (
            self.config.version,
            n,
            player,
            self.private_deal[player],
            self.config.button,
            self.config.starting_stacks,
            self.config.forced_posts,
            self.config.straddle_variant,
            sizing_identity,
            self.pot,
            self.street_committed,
            self.total_contributed,
            self.remaining,
            self.folded,
            self.pending,
            self.can_raise,
            self.last_raise_increment,
            self.raise_count,
            self.acting_player,
            self.history,
            continuation.kind,
            continuation.source,
            continuation.provenance,
        )

    def returns(self) -> tuple[float, ...]:
        if self.acting_player != TERMINAL or self.terminal_values is None:
            raise ValueError("returns only exist at terminal states")
        return tuple(float(value) for value in self.terminal_values)

    def _replace(self, **changes: object) -> "NPlayerPreflopState":
        values = {field: getattr(self, field) for field in self.__dataclass_fields__}
        values.update(changes)
        return NPlayerPreflopState(**values)  # type: ignore[arg-type]


def create_nplayer_preflop_root(config: NPlayerPreflopConfig) -> NPlayerPreflopState:
    if not isinstance(config, NPlayerPreflopConfig):
        raise ValueError("config must be NPlayerPreflopConfig")
    deals = enumerate_nplayer_preflop_deals(config)
    if 1 + len(deals) > config.max_nodes:
        raise ValueError("node bound too small for chance expansion")
    n = config.num_players
    (
        pot,
        street,
        contributed,
        remaining,
        pending,
        can_raise,
        outer_wager,
    ) = _root_components(config)
    return NPlayerPreflopState(
        config=config,
        private_deal=None,
        acting_player=CHANCE,
        pot=pot,
        street_committed=street,
        total_contributed=contributed,
        remaining=remaining,
        folded=(False,) * n,
        pending=pending,
        can_raise=can_raise,
        last_raise_increment=outer_wager,
        raise_count=0,
        history=(),
    )
