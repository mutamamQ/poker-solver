"""Bounded typed two-to-nine-player one-round postflop state.

This module is additive to the frozen three-player implementation. It provides
strict immutable configuration, deterministic exact deal enumeration, a finite
betting round, exact integer settlement, and information-safe state keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import isfinite, prod
from types import MappingProxyType
from typing import Mapping, TypeAlias

from .equity import WeightedCombo as EquityWeightedCombo
from .game_structure import (
    RakePolicy,
    allocate_rake,
    award_pot_layers,
    build_pot_layers,
    calculate_rake,
    refund_uncalled_excess,
    verify_terminal_conservation,
)
from .model import Action, CHANCE, TERMINAL
from .preflop import WeightedCombo as ExactWeightedCombo

DealN: TypeAlias = tuple[tuple[int, int], ...]
_Combo = EquityWeightedCombo | ExactWeightedCombo


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


def _combo_mass(combo: _Combo) -> Fraction:
    try:
        value = Fraction(str(combo.weight))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError("range weight must be finite and positive") from exc
    if value <= 0 or not isfinite(float(value)):
        raise ValueError("range weight must be finite and positive")
    return value


@dataclass(frozen=True, slots=True)
class NPlayerPostflopConfig:
    version: str
    num_players: int
    button: int
    starting_stacks: tuple[int, ...]
    contributions: tuple[int, ...]
    folded: tuple[bool, ...]
    board: tuple[int, ...]
    ranges: tuple[tuple[_Combo, ...], ...]
    wager_targets: tuple[int, ...]
    max_raises: int
    max_deals: int
    max_nodes: int
    odd_chip_order: tuple[int, ...]
    showdown_ranks: Mapping[DealN, tuple[int, ...]]
    rake_policy: RakePolicy | None = None

    def __post_init__(self) -> None:
        if self.version != "nplayer-postflop-v1":
            raise ValueError("version must be nplayer-postflop-v1")
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

        stacks_raw = _seat_tuple(self.starting_stacks, n, "starting_stacks")
        stacks = tuple(_positive(value, "starting stack") for value in stacks_raw)
        contributions_raw = _seat_tuple(self.contributions, n, "contributions")
        contributions = tuple(
            _nonnegative(value, "contribution") for value in contributions_raw
        )
        if any(value > stack for value, stack in zip(contributions, stacks)):
            raise ValueError("contribution exceeds starting stack")
        if sum(contributions) <= 0:
            raise ValueError("initial pot from contributions must be positive")

        folded_raw = _seat_tuple(self.folded, n, "folded")
        if any(not isinstance(value, bool) for value in folded_raw):
            raise ValueError("folded must contain booleans")
        if sum(not value for value in folded_raw) < 2:
            raise ValueError("at least two players must be live initially")

        if (
            not isinstance(self.board, tuple)
            or len(self.board) not in (3, 4, 5)
            or any(
                isinstance(card, bool)
                or not isinstance(card, int)
                or not 0 <= card <= 51
                for card in self.board
            )
            or len(set(self.board)) != len(self.board)
        ):
            raise ValueError("board must contain 3, 4, or 5 unique cards in 0..51")

        ranges_raw = _seat_tuple(self.ranges, n, "ranges")
        normalized_ranges: list[tuple[_Combo, ...]] = []
        combo_types = (EquityWeightedCombo, ExactWeightedCombo)
        for player_range in ranges_raw:
            if not isinstance(player_range, tuple) or not player_range:
                raise ValueError("each range must be a non-empty tuple")
            if any(not isinstance(combo, combo_types) for combo in player_range):
                raise ValueError("each range entry must be a WeightedCombo")
            if any(not _valid_cards(combo.cards) for combo in player_range):
                raise ValueError("range combos must contain valid cards in 0..51")
            if len({combo.cards for combo in player_range}) != len(player_range):
                raise ValueError("range combos must be unique")
            for combo in player_range:
                _combo_mass(combo)
            normalized_ranges.append(tuple(player_range))

        if not isinstance(self.wager_targets, tuple):
            raise ValueError("wager_targets must be a tuple")
        targets = tuple(_positive(value, "wager target") for value in self.wager_targets)
        if len(set(targets)) != len(targets) or targets != tuple(sorted(targets)):
            raise ValueError("wager targets must be unique and increasing")
        _positive(self.max_raises, "max_raises")
        _positive(self.max_deals, "max_deals")
        _positive(self.max_nodes, "max_nodes")
        if prod(len(player_range) for player_range in normalized_ranges) > self.max_deals:
            raise ValueError("candidate product exceeds max_deals")

        if (
            not isinstance(self.odd_chip_order, tuple)
            or len(self.odd_chip_order) != n
            or set(self.odd_chip_order) != set(range(n))
        ):
            raise ValueError("odd_chip_order must be a permutation of all seats")

        matched, refunds = refund_uncalled_excess(contributions)
        if matched != contributions or any(refunds):
            raise ValueError("initial contributions contain unmatched excess refund")

        if not isinstance(self.showdown_ranks, Mapping):
            raise ValueError("showdown_ranks must be a mapping")
        copied: dict[DealN, tuple[int, ...]] = {}
        for deal, ranks in self.showdown_ranks.items():
            if not _valid_deal_shape(deal, n):
                raise ValueError("showdown deals must contain N disjoint two-card combos")
            if any(card in self.board for combo in deal for card in combo):
                raise ValueError("showdown deal collides with board")
            if (
                not isinstance(ranks, tuple)
                or len(ranks) != n
                or any(isinstance(rank, bool) or not isinstance(rank, int) for rank in ranks)
            ):
                raise ValueError("showdown ranks must contain N integers")
            if deal in copied:
                raise ValueError("duplicate showdown deal")
            copied[deal] = ranks
        if self.rake_policy is not None and not isinstance(self.rake_policy, RakePolicy):
            raise ValueError("rake_policy must be RakePolicy or None")

        object.__setattr__(self, "starting_stacks", stacks)
        object.__setattr__(self, "contributions", contributions)
        object.__setattr__(self, "folded", tuple(folded_raw))
        object.__setattr__(self, "ranges", tuple(normalized_ranges))
        object.__setattr__(self, "wager_targets", targets)
        object.__setattr__(self, "showdown_ranks", MappingProxyType(copied))


@dataclass(frozen=True, slots=True)
class NPlayerPublicAction:
    actor: int
    action: Action

    def __post_init__(self) -> None:
        if isinstance(self.actor, bool) or not isinstance(self.actor, int) or self.actor < 0:
            raise ValueError("history actor must be a non-negative integer")
        if not isinstance(self.action, Action):
            raise ValueError("history action must be Action")


def enumerate_deals(
    config: NPlayerPostflopConfig,
) -> tuple[tuple[DealN, Fraction], ...]:
    """Enumerate compatible deals deterministically with exact raw masses."""
    if not isinstance(config, NPlayerPostflopConfig):
        raise ValueError("config must be NPlayerPostflopConfig")
    candidate_count = prod(len(player_range) for player_range in config.ranges)
    if candidate_count > config.max_deals:
        raise ValueError("candidate product exceeds max_deals")

    results: list[tuple[DealN, Fraction]] = []
    board = frozenset(config.board)

    def walk(seat: int, used: frozenset[int], deal: tuple[tuple[int, int], ...], mass: Fraction) -> None:
        if seat == config.num_players:
            results.append((deal, mass))
            return
        for combo in config.ranges[seat]:
            cards = combo.cards
            if used.isdisjoint(cards):
                walk(
                    seat + 1,
                    used | frozenset(cards),
                    deal + (cards,),
                    mass * _combo_mass(combo),
                )

    walk(0, board, (), Fraction(1))
    if not results:
        raise ValueError("ranges produce no compatible deals")
    total = sum((mass for _, mass in results), Fraction(0))
    if total <= 0:
        raise ValueError("compatible deals have zero total mass")
    return tuple(results)


def _active(folded: tuple[bool, ...], remaining: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(
        seat
        for seat in range(len(folded))
        if not folded[seat] and remaining[seat] > 0
    )


def _ordered_after(
    seat: int,
    candidates: tuple[int, ...],
    num_players: int,
) -> tuple[int, ...]:
    candidate_set = set(candidates)
    return tuple(
        candidate
        for step in range(1, num_players + 1)
        if (candidate := (seat + step) % num_players) in candidate_set
    )


@dataclass(frozen=True, slots=True)
class NPlayerPostflopState:
    config: NPlayerPostflopConfig
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
    history: tuple[NPlayerPublicAction, ...]
    terminal_values: tuple[int, ...] | None = None
    house_rake: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.config, NPlayerPostflopConfig):
            raise ValueError("config must be NPlayerPostflopConfig")
        n = self.config.num_players
        if (
            isinstance(self.acting_player, bool)
            or not isinstance(self.acting_player, int)
            or self.acting_player not in (CHANCE, TERMINAL, *range(n))
        ):
            raise ValueError("invalid acting player")

        values_by_name: dict[str, tuple[int, ...]] = {}
        for name in ("street_committed", "total_contributed", "remaining"):
            raw = _seat_tuple(getattr(self, name), n, name)
            values_by_name[name] = tuple(_nonnegative(value, name) for value in raw)
        street = values_by_name["street_committed"]
        contributed = values_by_name["total_contributed"]
        remaining = values_by_name["remaining"]
        _nonnegative(self.pot, "pot")
        if self.pot != sum(contributed):
            raise ValueError("pot must equal sum(total_contributed)")
        if any(
            remaining[seat] + contributed[seat] != self.config.starting_stacks[seat]
            for seat in range(n)
        ):
            raise ValueError("remaining plus contribution must equal starting stack")
        if any(street[seat] > contributed[seat] for seat in range(n)):
            raise ValueError("street_committed must not exceed total contribution")

        folded_raw = _seat_tuple(self.folded, n, "folded")
        if any(not isinstance(value, bool) for value in folded_raw):
            raise ValueError("folded must contain booleans")
        if not isinstance(self.pending, tuple):
            raise ValueError("pending must be a tuple")
        if (
            len(set(self.pending)) != len(self.pending)
            or any(
                isinstance(seat, bool)
                or not isinstance(seat, int)
                or not 0 <= seat < n
                or folded_raw[seat]
                or remaining[seat] == 0
                for seat in self.pending
            )
        ):
            raise ValueError("pending seats must be unique active valid seats")

        can_raise_raw = _seat_tuple(self.can_raise, n, "can_raise")
        if any(not isinstance(value, bool) for value in can_raise_raw):
            raise ValueError("can_raise must contain booleans")
        if any(
            can_raise_raw[seat] and (folded_raw[seat] or remaining[seat] == 0)
            for seat in range(n)
        ):
            raise ValueError("folded or all-in seats cannot raise")
        _positive(self.last_raise_increment, "last_raise_increment")
        _nonnegative(self.raise_count, "raise_count")
        if self.raise_count > self.config.max_raises:
            raise ValueError("raise_count exceeds max_raises")

        if not isinstance(self.history, tuple) or any(
            not isinstance(item, NPlayerPublicAction)
            or not 0 <= item.actor < n
            for item in self.history
        ):
            raise ValueError("history must contain valid public actions")
        _nonnegative(self.house_rake, "house_rake")

        if self.acting_player == CHANCE:
            if (
                self.private_deal is not None
                or self.history
                or self.terminal_values is not None
                or self.house_rake != 0
                or self.pot != sum(self.config.contributions)
                or street != (0,) * n
                or contributed != self.config.contributions
            ):
                raise ValueError("invalid chance root baseline")
        else:
            if self.private_deal is None:
                raise ValueError("dealt state requires a private deal")
            valid_deals = {deal for deal, _ in enumerate_deals(self.config)}
            if self.private_deal not in valid_deals:
                raise ValueError("dealt state uses an incompatible deal")

        if self.acting_player == TERMINAL:
            if self.pending:
                raise ValueError("terminal state must have empty pending")
            if (
                not isinstance(self.terminal_values, tuple)
                or len(self.terminal_values) != n
                or any(
                    isinstance(value, bool) or not isinstance(value, int)
                    for value in self.terminal_values
                )
            ):
                raise ValueError("terminal state requires N integer utilities")
            if sum(self.terminal_values) + self.house_rake != 0:
                raise ValueError("terminal utility and rake conservation failed")
        else:
            if self.terminal_values is not None or self.house_rake != 0:
                raise ValueError("nonterminal state cannot contain settlement")
            if self.acting_player != CHANCE:
                if not self.pending or self.acting_player != self.pending[0]:
                    raise ValueError("dealt nonterminal acting player must be first pending")

    def num_players(self) -> int:
        return self.config.num_players

    def current_player(self) -> int:
        return self.acting_player

    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]:
        if self.acting_player != CHANCE:
            return ()
        deals = enumerate_deals(self.config)
        total = sum((mass for _, mass in deals), Fraction(0))
        return tuple(
            (Action("DEAL", index), float(mass / total))
            for index, (_, mass) in enumerate(deals)
        )

    def legal_actions(self) -> tuple[Action, ...]:
        if self.acting_player in (CHANCE, TERMINAL):
            return ()
        player = self.acting_player
        live = tuple(seat for seat in range(self.config.num_players) if not self.folded[seat])
        highest = max(self.street_committed[seat] for seat in live)
        own = self.street_committed[player]
        to_call = highest - own
        if to_call == 0:
            actions: list[Action] = [Action("CHECK")]
        else:
            actions = [
                Action("FOLD"),
                Action("CALL", own + min(to_call, self.remaining[player])),
            ]

        if (
            self.can_raise[player]
            and self.remaining[player] > to_call
            and self.raise_count < self.config.max_raises
        ):
            maximum = own + self.remaining[player]
            minimum = highest + self.last_raise_increment
            seen: set[int] = set()
            for target in (*self.config.wager_targets, maximum):
                if target in seen:
                    continue
                seen.add(target)
                if highest < target <= maximum and (
                    target >= minimum or target == maximum
                ):
                    actions.append(Action("RAISE", target))
        return tuple(actions)

    def child(self, action: Action) -> NPlayerPostflopState:
        if not isinstance(action, Action):
            raise ValueError("action must be Action")
        if self.acting_player == CHANCE:
            outcomes = self.chance_outcomes()
            if action not in {candidate for candidate, _ in outcomes}:
                raise ValueError("action is not legal")
            deal = enumerate_deals(self.config)[action.amount][0]
            if not self.pending:
                return self._settle(private_deal=deal)
            return self._replace(
                private_deal=deal,
                acting_player=self.pending[0],
            )
        if action not in self.legal_actions():
            raise ValueError("action is not legal")

        n = self.config.num_players
        player = self.acting_player
        old_pending = self.pending
        old_can_raise = self.can_raise
        committed = list(self.street_committed)
        contributed = list(self.total_contributed)
        remaining = list(self.remaining)
        folded = list(self.folded)
        pending = [seat for seat in self.pending if seat != player]
        can_raise = list(self.can_raise)
        pot = self.pot
        increment = self.last_raise_increment
        raise_count = self.raise_count
        history = self.history + (NPlayerPublicAction(player, action),)

        if action.kind == "FOLD":
            folded[player] = True
            can_raise[player] = False
        elif action.kind == "CHECK":
            pass
        elif action.kind == "CALL":
            payment = action.amount - committed[player]
            committed[player] += payment
            contributed[player] += payment
            remaining[player] -= payment
            pot += payment
            if remaining[player] == 0:
                can_raise[player] = False
        elif action.kind == "RAISE":
            live_before = tuple(seat for seat in range(n) if not folded[seat])
            old_highest = max(committed[seat] for seat in live_before)
            payment = action.amount - committed[player]
            committed[player] += payment
            contributed[player] += payment
            remaining[player] -= payment
            pot += payment
            active_others = tuple(
                seat
                for seat in range(n)
                if seat != player and not folded[seat] and remaining[seat] > 0
            )
            pending = list(_ordered_after(player, active_others, n))
            raise_size = action.amount - old_highest
            if raise_size >= increment:
                increment = raise_size
                can_raise = [
                    not folded[seat] and remaining[seat] > 0
                    for seat in range(n)
                ]
            else:
                can_raise = [
                    (
                        seat != player
                        and seat in old_pending
                        and old_can_raise[seat]
                        and not folded[seat]
                        and remaining[seat] > 0
                    )
                    for seat in range(n)
                ]
            if remaining[player] == 0:
                can_raise[player] = False
            raise_count += 1
        else:  # guarded by membership in legal_actions
            raise ValueError("unsupported action")

        active_pending = tuple(
            seat
            for seat in pending
            if not folded[seat] and remaining[seat] > 0
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

    def _settle(self, **pre_settlement: object) -> NPlayerPostflopState:
        values = {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }
        values.update(pre_settlement)
        private_deal = values["private_deal"]
        if private_deal is None:
            raise ValueError("settlement requires a private deal")
        n = self.config.num_players
        total_contributed = values["total_contributed"]
        current_remaining = values["remaining"]
        current_street = values["street_committed"]
        current_folded = values["folded"]
        assert isinstance(total_contributed, tuple)
        assert isinstance(current_remaining, tuple)
        assert isinstance(current_street, tuple)
        assert isinstance(current_folded, tuple)
        matched, refunds = refund_uncalled_excess(total_contributed)
        remaining = tuple(
            current_remaining[seat] + refunds[seat] for seat in range(n)
        )
        street_committed = tuple(
            current_street[seat] - refunds[seat] for seat in range(n)
        )
        if any(value < 0 for value in street_committed):
            raise ValueError("uncalled refund exceeds street contribution")
        folded_set = frozenset(
            seat for seat, value in enumerate(current_folded) if value
        )
        layers = build_pot_layers(matched, folded=folded_set)
        live = tuple(seat for seat in range(n) if not current_folded[seat])
        if len(live) > 1:
            if private_deal not in self.config.showdown_ranks:
                raise ValueError("missing showdown rank coverage for deal")
            ranks = self.config.showdown_ranks[private_deal]
            winners = []
            for layer in layers:
                best = max(ranks[seat] for seat in layer.eligible)
                winners.append(
                    frozenset(
                        seat for seat in layer.eligible if ranks[seat] == best
                    )
                )
        else:
            winners = [frozenset(live) for _ in layers]

        rake = 0
        rake_by_layer = None
        if self.config.rake_policy is not None:
            rake = calculate_rake(
                self.config.rake_policy,
                sum(layer.amount for layer in layers),
                flop_seen=True,
            )
            rake_by_layer = allocate_rake(
                layers,
                rake,
                layer_order=self.config.rake_policy.layer_order,
            )
        raw_awards = award_pot_layers(
            layers,
            winners_by_layer=tuple(winners),
            odd_chip_order=self.config.odd_chip_order,
            rake_by_layer=rake_by_layer,
        )
        awards = raw_awards + (0,) * (n - len(raw_awards))
        final = tuple(remaining[seat] + awards[seat] for seat in range(n))
        verify_terminal_conservation(
            self.config.starting_stacks,
            final,
            house_rake=rake,
        )
        utilities = tuple(
            final[seat] - self.config.starting_stacks[seat]
            for seat in range(n)
        )
        values.update(
            acting_player=TERMINAL,
            pot=sum(matched),
            street_committed=street_committed,
            total_contributed=matched,
            remaining=remaining,
            pending=(),
            terminal_values=utilities,
            house_rake=rake,
        )
        return NPlayerPostflopState(**values)  # type: ignore[arg-type]

    def information_state_key(self, player: int):
        n = self.config.num_players
        if (
            isinstance(player, bool)
            or not isinstance(player, int)
            or not 0 <= player < n
            or self.private_deal is None
        ):
            raise ValueError("information key requires dealt state and valid player")
        return (
            self.config.version,
            n,
            player,
            self.private_deal[player],
            self.config.board,
            self.config.button,
            self.street_committed,
            self.total_contributed,
            self.remaining,
            self.folded,
            self.pending,
            self.can_raise,
            self.last_raise_increment,
            self.raise_count,
            self.acting_player,
            self.config.wager_targets,
            self.history,
        )

    def information_state_string(self, player: int) -> str:
        key = self.information_state_key(player)
        history = ",".join(
            f"{item.actor}:{item.action.kind}:{item.action.amount}"
            for item in self.history
        )
        return (
            f"{key[:-1]!r}|history={history}"
        )

    def returns(self) -> tuple[float, ...]:
        if self.acting_player != TERMINAL or self.terminal_values is None:
            raise ValueError("returns only exist at terminal states")
        return tuple(float(value) for value in self.terminal_values)

    def _replace(self, **changes: object) -> NPlayerPostflopState:
        values = {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }
        values.update(changes)
        return NPlayerPostflopState(**values)  # type: ignore[arg-type]


def create_nplayer_postflop_root(
    config: NPlayerPostflopConfig,
) -> NPlayerPostflopState:
    if not isinstance(config, NPlayerPostflopConfig):
        raise ValueError("config must be NPlayerPostflopConfig")
    deals = enumerate_deals(config)
    compatible = {deal for deal, _ in deals}
    supplied = set(config.showdown_ranks)
    if supplied != compatible:
        missing = compatible - supplied
        extra = supplied - compatible
        raise ValueError(
            f"showdown coverage must exactly match compatible deals "
            f"(missing={len(missing)}, extra={len(extra)})"
        )
    if 1 + len(deals) > config.max_nodes:
        raise ValueError("node bound too small for chance expansion")
    n = config.num_players
    remaining = tuple(
        stack - contribution
        for stack, contribution in zip(
            config.starting_stacks,
            config.contributions,
        )
    )
    active = _active(config.folded, remaining)
    pending = _ordered_after(config.button, active, n)
    first_target = config.wager_targets[0] if config.wager_targets else 1
    return NPlayerPostflopState(
        config=config,
        private_deal=None,
        acting_player=CHANCE,
        pot=sum(config.contributions),
        street_committed=(0,) * n,
        total_contributed=config.contributions,
        remaining=remaining,
        folded=config.folded,
        pending=pending,
        can_raise=tuple(seat in pending for seat in range(n)),
        last_raise_increment=first_target,
        raise_count=0,
        history=(),
    )
