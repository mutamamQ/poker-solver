"""Bounded exactly-three-player postflop state and settlement.

This additive model uses explicit weighted deals, one finite betting round,
caller-supplied showdown ranks, exact integer side pots, odd-chip order, and an
optional declared rake policy.  It makes no multiplayer convergence claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType
from typing import Mapping

from .game_structure import (
    RakePolicy,
    allocate_rake,
    award_pot_layers,
    build_pot_layers,
    calculate_rake,
    refund_uncalled_excess,
)
from .model import Action, CHANCE, TERMINAL
from .preflop import WeightedCombo


Deal3 = tuple[tuple[int, int], tuple[int, int], tuple[int, int]]


def _nonnegative(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _positive(value: object, name: str) -> int:
    result = _nonnegative(value, name)
    if result == 0:
        raise ValueError(f"{name} must be positive")
    return result


@dataclass(frozen=True, slots=True)
class MultiwayConfig:
    button: int
    starting_stacks: tuple[int, int, int]
    contributions: tuple[int, int, int]
    folded: tuple[bool, bool, bool]
    board: tuple[int, ...]
    ranges: tuple[tuple[WeightedCombo, ...], tuple[WeightedCombo, ...], tuple[WeightedCombo, ...]]
    wager_targets: tuple[int, ...]
    max_raises: int
    max_deals: int
    max_nodes: int
    odd_chip_order: tuple[int, int, int]
    showdown_ranks: Mapping[Deal3, tuple[int, int, int]]
    rake_policy: RakePolicy | None = None
    version: str = "holdem-postflop-3p-v1"

    def __post_init__(self) -> None:
        if isinstance(self.button, bool) or self.button not in (0, 1, 2):
            raise ValueError("button must be one of exactly three seats")
        if not isinstance(self.starting_stacks, tuple) or len(self.starting_stacks) != 3:
            raise ValueError("starting_stacks must contain exactly three players")
        stacks = tuple(_positive(value, "starting stack") for value in self.starting_stacks)
        if not isinstance(self.contributions, tuple) or len(self.contributions) != 3:
            raise ValueError("contributions must contain exactly three players")
        contributions = tuple(_nonnegative(value, "contribution") for value in self.contributions)
        if any(value > stack for value, stack in zip(contributions, stacks)):
            raise ValueError("contribution exceeds starting stack")
        if not isinstance(self.folded, tuple) or len(self.folded) != 3 or any(not isinstance(value, bool) for value in self.folded):
            raise ValueError("folded must contain exactly three booleans")
        if sum(not value for value in self.folded) < 2:
            raise ValueError("at least two players must be live initially")
        if (
            not isinstance(self.board, tuple)
            or len(self.board) not in (3, 4, 5)
            or any(isinstance(card, bool) or not isinstance(card, int) or card < 0 for card in self.board)
            or len(set(self.board)) != len(self.board)
        ):
            raise ValueError("board must contain 3, 4, or 5 unique non-negative cards")
        if not isinstance(self.ranges, tuple) or len(self.ranges) != 3:
            raise ValueError("ranges must contain exactly three player ranges")
        for player_range in self.ranges:
            if not isinstance(player_range, tuple) or not player_range or any(not isinstance(combo, WeightedCombo) for combo in player_range):
                raise ValueError("each range must be a non-empty WeightedCombo tuple")
            if len({combo.cards for combo in player_range}) != len(player_range):
                raise ValueError("range combos must be unique")
        if not isinstance(self.wager_targets, tuple):
            raise ValueError("wager_targets must be a tuple")
        targets = tuple(_positive(value, "wager target") for value in self.wager_targets)
        if len(set(targets)) != len(targets) or tuple(sorted(targets)) != targets:
            raise ValueError("wager_targets must be unique and increasing")
        _positive(self.max_raises, "max_raises")
        _positive(self.max_deals, "max_deals")
        _positive(self.max_nodes, "max_nodes")
        if not isinstance(self.odd_chip_order, tuple) or set(self.odd_chip_order) != {0, 1, 2}:
            raise ValueError("odd_chip_order must be a permutation of three seats")
        if not isinstance(self.showdown_ranks, Mapping):
            raise ValueError("showdown_ranks must be a mapping")
        ranks_copy: dict[Deal3, tuple[int, int, int]] = {}
        for deal, ranks in self.showdown_ranks.items():
            if not _valid_deal_shape(deal) or not isinstance(ranks, tuple) or len(ranks) != 3:
                raise ValueError("showdown table requires deal triples and three ranks")
            if any(isinstance(rank, bool) or not isinstance(rank, int) for rank in ranks):
                raise ValueError("showdown ranks must be integers")
            ranks_copy[deal] = ranks
        object.__setattr__(self, "showdown_ranks", MappingProxyType(ranks_copy))
        if self.rake_policy is not None and not isinstance(self.rake_policy, RakePolicy):
            raise ValueError("rake_policy must be RakePolicy or None")
        if not isinstance(self.version, str) or not self.version:
            raise ValueError("version must be non-empty")


def _valid_deal_shape(deal: object) -> bool:
    return (
        isinstance(deal, tuple)
        and len(deal) == 3
        and all(isinstance(combo, tuple) and len(combo) == 2 for combo in deal)
        and all(isinstance(card, int) and not isinstance(card, bool) and card >= 0 for combo in deal for card in combo)
        and len({card for combo in deal for card in combo}) == 6
    )


@dataclass(frozen=True, slots=True)
class ThreePlayerPostflopState:
    config: MultiwayConfig
    private_deal: Deal3 | None
    acting_player: int
    pot: int
    street_committed: tuple[int, int, int]
    total_contributed: tuple[int, int, int]
    remaining: tuple[int, int, int]
    folded: tuple[bool, bool, bool]
    pending: tuple[int, ...]
    can_raise: tuple[bool, bool, bool]
    last_raise_increment: int
    raise_count: int
    history: tuple[Action, ...]
    terminal_values: tuple[int, int, int] | None = None
    house_rake: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.config, MultiwayConfig):
            raise ValueError("config must be MultiwayConfig")
        if isinstance(self.acting_player, bool) or self.acting_player not in (CHANCE, TERMINAL, 0, 1, 2):
            raise ValueError("invalid acting player")
        for name in ("street_committed", "total_contributed", "remaining"):
            values = getattr(self, name)
            if not isinstance(values, tuple) or len(values) != 3 or any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in values):
                raise ValueError(f"{name} must contain three non-negative integers")
        _nonnegative(self.pot, "pot")
        _positive(self.last_raise_increment, "last_raise_increment")
        _nonnegative(self.house_rake, "house_rake")
        if self.pot != sum(self.total_contributed):
            raise ValueError("pot must equal total contributions")
        if any(r + c != s for r, c, s in zip(self.remaining, self.total_contributed, self.config.starting_stacks)):
            raise ValueError("stack conservation failed")
        if any(street > total for street, total in zip(self.street_committed, self.total_contributed)):
            raise ValueError("street commitment exceeds total contribution")
        if not isinstance(self.folded, tuple) or len(self.folded) != 3 or any(not isinstance(v, bool) for v in self.folded):
            raise ValueError("folded must contain three booleans")
        if not isinstance(self.can_raise, tuple) or len(self.can_raise) != 3 or any(not isinstance(v, bool) for v in self.can_raise):
            raise ValueError("can_raise must contain three booleans")
        if not isinstance(self.pending, tuple) or len(set(self.pending)) != len(self.pending) or any(isinstance(v, bool) or v not in (0, 1, 2) for v in self.pending):
            raise ValueError("pending must contain unique valid seats")
        if isinstance(self.raise_count, bool) or not isinstance(self.raise_count, int) or not 0 <= self.raise_count <= self.config.max_raises:
            raise ValueError("raise_count outside configured bound")
        if not isinstance(self.history, tuple) or any(not isinstance(action, Action) for action in self.history):
            raise ValueError("history must be an Action tuple")
        if self.acting_player == CHANCE:
            if self.private_deal is not None or self.history or self.terminal_values is not None:
                raise ValueError("chance root has invalid phase data")
        elif self.private_deal not in {deal for deal, _ in _deals(self.config)}:
            raise ValueError("state requires a compatible configured deal")
        if self.acting_player == TERMINAL:
            if not isinstance(self.terminal_values, tuple) or len(self.terminal_values) != 3:
                raise ValueError("terminal state requires three utilities")
            if sum(self.terminal_values) != -self.house_rake:
                raise ValueError("terminal utility/rake conservation failed")
        elif self.terminal_values is not None or self.house_rake != 0:
            raise ValueError("non-terminal state cannot contain settlement")

    def num_players(self) -> int:
        return 3

    def current_player(self) -> int:
        return self.acting_player

    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]:
        if self.acting_player != CHANCE:
            return ()
        deals = _deals(self.config)
        total = sum(weight for _, weight in deals)
        return tuple((Action("DEAL", index), float(weight / total)) for index, (_, weight) in enumerate(deals))

    def legal_actions(self) -> tuple[Action, ...]:
        if self.acting_player in (CHANCE, TERMINAL):
            return ()
        player = self.acting_player
        own = self.street_committed[player]
        highest = max(self.street_committed)
        to_call = highest - own
        actions = [Action("FOLD"), Action("CALL", min(highest, own + self.remaining[player]))] if to_call else [Action("CHECK")]
        if self.can_raise[player] and self.remaining[player] > to_call and self.raise_count < self.config.max_raises:
            maximum = own + self.remaining[player]
            minimum = highest + self.last_raise_increment
            targets = list(self.config.wager_targets) + [maximum]
            seen = set()
            for target in targets:
                if target in seen:
                    continue
                seen.add(target)
                if highest < target <= maximum and (target >= minimum or target == maximum):
                    actions.append(Action("RAISE", target))
        return tuple(actions)

    def child(self, action: Action) -> ThreePlayerPostflopState:
        if not isinstance(action, Action):
            raise ValueError("action must be Action")
        if self.acting_player == CHANCE:
            outcomes = self.chance_outcomes()
            if action not in {candidate for candidate, _ in outcomes}:
                raise ValueError("action is not legal")
            deal = _deals(self.config)[action.amount][0]
            active = _actionable(self.folded, self.remaining)
            next_player = _next_after(self.config.button, active) if active else self.config.button
            base = self._replace(private_deal=deal, acting_player=next_player)
            if not active:
                return base._settle()
            return base
        if action not in self.legal_actions():
            raise ValueError("action is not legal")
        player = self.acting_player
        committed = list(self.street_committed)
        contributed = list(self.total_contributed)
        remaining = list(self.remaining)
        folded = list(self.folded)
        pending = [seat for seat in self.pending if seat != player]
        can_raise = list(self.can_raise)
        pot = self.pot
        increment = self.last_raise_increment
        raise_count = self.raise_count
        history = self.history + (action,)

        if action.kind == "FOLD":
            folded[player] = True
        elif action.kind == "CALL":
            payment = action.amount - committed[player]
            committed[player] += payment
            contributed[player] += payment
            remaining[player] -= payment
            pot += payment
        elif action.kind == "RAISE":
            old_highest = max(committed)
            payment = action.amount - committed[player]
            committed[player] += payment
            contributed[player] += payment
            remaining[player] -= payment
            pot += payment
            raise_size = action.amount - old_highest
            active_others = [seat for seat in range(3) if seat != player and not folded[seat] and remaining[seat] > 0]
            pending = active_others
            if raise_size >= increment:
                increment = raise_size
                can_raise = [not folded[seat] and remaining[seat] > 0 for seat in range(3)]
            else:
                for seat in active_others:
                    if seat not in self.pending:
                        can_raise[seat] = False
            raise_count += 1

        live = [seat for seat in range(3) if not folded[seat]]
        updated = self._replace(
            pot=pot,
            street_committed=tuple(committed),
            total_contributed=tuple(contributed),
            remaining=tuple(remaining),
            folded=tuple(folded),
            pending=tuple(pending),
            can_raise=tuple(can_raise),
            last_raise_increment=increment,
            raise_count=raise_count,
            history=history,
        )
        if len(live) == 1 or not pending:
            return updated._settle()
        actionable_pending = [seat for seat in pending if not folded[seat] and remaining[seat] > 0]
        if not actionable_pending:
            return updated._settle()
        return updated._replace(acting_player=_next_after(player, tuple(actionable_pending)))

    def _settle(self) -> ThreePlayerPostflopState:
        assert self.private_deal is not None
        matched, refunds = refund_uncalled_excess(self.total_contributed)
        remaining = tuple(value + refund for value, refund in zip(self.remaining, refunds))
        street_committed = tuple(value - refund for value, refund in zip(self.street_committed, refunds))
        if any(value < 0 for value in street_committed):
            raise ValueError("uncalled refund exceeds street contribution")
        folded_set = frozenset(seat for seat, value in enumerate(self.folded) if value)
        layers = build_pot_layers(matched, folded=folded_set)
        live = [seat for seat in range(3) if not self.folded[seat]]
        if len(live) > 1:
            if self.private_deal not in self.config.showdown_ranks:
                raise ValueError("missing showdown rank coverage for deal")
            ranks = self.config.showdown_ranks[self.private_deal]
            winners = []
            for layer in layers:
                best = max(ranks[seat] for seat in layer.eligible)
                winners.append(frozenset(seat for seat in layer.eligible if ranks[seat] == best))
        else:
            winners = [frozenset(live) for _ in layers]
        rake = 0
        rake_by_layer = None
        if self.config.rake_policy is not None:
            rake = calculate_rake(self.config.rake_policy, sum(layer.amount for layer in layers), flop_seen=True)
            rake_by_layer = allocate_rake(layers, rake, layer_order=self.config.rake_policy.layer_order)
        awards = award_pot_layers(
            layers,
            winners_by_layer=tuple(winners),
            odd_chip_order=self.config.odd_chip_order,
            rake_by_layer=rake_by_layer,
        )
        final = tuple(remaining[seat] + awards[seat] for seat in range(3))
        utilities = tuple(final[seat] - self.config.starting_stacks[seat] for seat in range(3))
        return self._replace(
            acting_player=TERMINAL,
            pot=sum(matched),
            street_committed=street_committed,
            total_contributed=matched,
            remaining=remaining,
            pending=(),
            terminal_values=utilities,
            house_rake=rake,
        )

    def information_state_key(self, player: int):
        if player not in (0, 1, 2) or self.private_deal is None:
            raise ValueError("information key requires dealt state and valid player")
        return (
            self.config.version,
            player,
            self.private_deal[player],
            self.config.board,
            self.config.button,
            self.street_committed,
            self.total_contributed,
            self.remaining,
            self.folded,
            self.history,
            self.config.wager_targets,
        )

    def returns(self) -> tuple[float, ...]:
        if self.acting_player != TERMINAL or self.terminal_values is None:
            raise ValueError("returns only exist at terminal states")
        return tuple(float(value) for value in self.terminal_values)

    def _replace(self, **changes) -> ThreePlayerPostflopState:
        values = {field: getattr(self, field) for field in self.__dataclass_fields__}
        values.update(changes)
        return ThreePlayerPostflopState(**values)


def _deals(config: MultiwayConfig) -> tuple[tuple[Deal3, Fraction], ...]:
    board = set(config.board)
    results = []
    for first in config.ranges[0]:
        for second in config.ranges[1]:
            for third in config.ranges[2]:
                cards = first.cards + second.cards + third.cards
                if len(set(cards)) == 6 and board.isdisjoint(cards):
                    results.append(((first.cards, second.cards, third.cards), first.weight * second.weight * third.weight))
    if not results:
        raise ValueError("ranges produce no compatible three-player deals")
    if len(results) > config.max_deals:
        raise ValueError("deal count exceeds max_deals")
    return tuple(results)


def _actionable(folded: tuple[bool, bool, bool], remaining: tuple[int, int, int]) -> tuple[int, ...]:
    return tuple(seat for seat in range(3) if not folded[seat] and remaining[seat] > 0)


def _next_after(seat: int, candidates: tuple[int, ...]) -> int:
    for step in range(1, 4):
        candidate = (seat + step) % 3
        if candidate in candidates:
            return candidate
    raise ValueError("no actionable player")


def create_three_player_root(config: MultiwayConfig) -> ThreePlayerPostflopState:
    if not isinstance(config, MultiwayConfig):
        raise ValueError("config must be MultiwayConfig")
    deals = _deals(config)
    if 1 + len(deals) > config.max_nodes:
        raise ValueError("node bound too small for chance expansion")
    remaining = tuple(stack - contribution for stack, contribution in zip(config.starting_stacks, config.contributions))
    pending = _actionable(config.folded, remaining)
    first_target = config.wager_targets[0] if config.wager_targets else 1
    return ThreePlayerPostflopState(
        config=config,
        private_deal=None,
        acting_player=CHANCE,
        pot=sum(config.contributions),
        street_committed=(0, 0, 0),
        total_contributed=config.contributions,
        remaining=remaining,
        folded=config.folded,
        pending=pending,
        can_raise=tuple(seat in pending for seat in range(3)),
        last_raise_increment=first_target,
        raise_count=0,
        history=(),
    )
