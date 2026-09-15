"""Bounded exact heads-up preflop game state.

The model covers explicit weighted private deals, forced posts, finite raise-to
sizes, short all-ins, and caller-supplied terminal continuation values.  It is
not an unrestricted poker or learned continuation model.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import isfinite
from types import MappingProxyType
from typing import Mapping

from .model import Action, CHANCE, TERMINAL
from .sizing import fixed_sizes, validate_size_expression


Deal = tuple[tuple[int, int], tuple[int, int]]
ContinuationKey = tuple[Deal, tuple[Action, ...]]


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _chips(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class WeightedCombo:
    cards: tuple[int, int]
    weight: Fraction

    def __post_init__(self) -> None:
        if (
            not isinstance(self.cards, tuple)
            or len(self.cards) != 2
            or any(isinstance(card, bool) or not isinstance(card, int) or card < 0 for card in self.cards)
            or self.cards[0] == self.cards[1]
        ):
            raise ValueError("cards must be two distinct non-negative integers")
        canonical = tuple(sorted(self.cards))
        object.__setattr__(self, "cards", canonical)
        try:
            weight = Fraction(self.weight)
        except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
            raise ValueError("weight must be an exact positive rational") from exc
        if isinstance(self.weight, bool) or weight <= 0:
            raise ValueError("weight must be an exact positive rational")
        object.__setattr__(self, "weight", weight)


@dataclass(frozen=True, slots=True)
class Continuation:
    kind: str
    payoff_table: Mapping[ContinuationKey, tuple[Fraction, Fraction]]
    provenance: str

    def __post_init__(self) -> None:
        if self.kind != "terminal-table":
            raise ValueError("only bounded terminal-table continuation is implemented")
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise ValueError("continuation provenance must be non-empty")
        if not isinstance(self.payoff_table, Mapping):
            raise ValueError("payoff_table must be a mapping")
        copied: dict[ContinuationKey, tuple[Fraction, Fraction]] = {}
        for key, values in self.payoff_table.items():
            if not isinstance(key, tuple) or len(key) != 2 or not isinstance(key[1], tuple):
                raise ValueError("invalid continuation key")
            if not isinstance(values, tuple) or len(values) != 2:
                raise ValueError("continuation values must be a two-player tuple")
            if any(isinstance(value, bool) for value in values):
                raise ValueError("continuation values must be finite numbers")
            try:
                exact = tuple(Fraction(value) for value in values)
            except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
                raise ValueError("continuation values must be finite numbers") from exc
            if any(not isfinite(float(value)) for value in exact) or sum(exact) != 0:
                raise ValueError("continuation values must be finite and zero-sum")
            copied[key] = exact  # type: ignore[assignment]
        object.__setattr__(self, "payoff_table", MappingProxyType(copied))


@dataclass(frozen=True, slots=True)
class PreflopConfig:
    starting_stacks: tuple[int, int]
    forced_posts: tuple[int, int]
    ranges: tuple[tuple[WeightedCombo, ...], tuple[WeightedCombo, ...]]
    sizing_expressions: tuple[Mapping[str, object], ...]
    max_raises: int
    max_deals: int
    max_nodes: int
    short_all_in_reopens: bool
    continuation: Continuation
    version: str = "holdem-preflop-hu-v1"

    def __post_init__(self) -> None:
        if not isinstance(self.starting_stacks, tuple) or len(self.starting_stacks) != 2:
            raise ValueError("starting_stacks must contain two seats")
        stacks = tuple(_positive_int(v, "starting stack") for v in self.starting_stacks)
        if not isinstance(self.forced_posts, tuple) or len(self.forced_posts) != 2:
            raise ValueError("forced_posts must contain two amounts")
        posts = tuple(_chips(v, "forced post") for v in self.forced_posts)
        if posts[0] > posts[1]:
            raise ValueError("heads-up button post cannot exceed big-blind post")
        if posts[1] <= 0 or any(post > stack for post, stack in zip(posts, stacks)):
            raise ValueError("forced posts must fit stacks and include a positive big blind")
        if not isinstance(self.ranges, tuple) or len(self.ranges) != 2:
            raise ValueError("ranges must contain two immutable ranges")
        for player_range in self.ranges:
            if not isinstance(player_range, tuple) or not player_range:
                raise ValueError("each range must be a non-empty tuple")
            if any(not isinstance(combo, WeightedCombo) for combo in player_range):
                raise ValueError("ranges must contain WeightedCombo values")
            if len({combo.cards for combo in player_range}) != len(player_range):
                raise ValueError("range combos must be unique")
        if not isinstance(self.sizing_expressions, tuple) or not self.sizing_expressions:
            raise ValueError("sizing_expressions must be a non-empty tuple")
        # Copy nested expressions so caller mutation cannot affect the game.
        expressions_list = []
        for expression in self.sizing_expressions:
            copied = dict(expression)
            validate_size_expression(copied)
            expressions_list.append(MappingProxyType(copied))
        expressions = tuple(expressions_list)
        object.__setattr__(self, "sizing_expressions", expressions)
        _positive_int(self.max_raises, "max_raises")
        _positive_int(self.max_deals, "max_deals")
        _positive_int(self.max_nodes, "max_nodes")
        if not isinstance(self.short_all_in_reopens, bool):
            raise ValueError("short_all_in_reopens must be boolean")
        if not isinstance(self.continuation, Continuation):
            raise ValueError("continuation must be Continuation")
        if not isinstance(self.version, str) or not self.version:
            raise ValueError("version must be non-empty")


@dataclass(frozen=True, slots=True)
class PreflopState:
    config: PreflopConfig
    private_deal: Deal | None
    acting_player: int
    pot: int
    committed: tuple[int, int]
    total_contributed: tuple[int, int]
    remaining: tuple[int, int]
    last_raise_increment: int
    acted: tuple[bool, bool]
    can_raise: tuple[bool, bool]
    raise_count: int
    history: tuple[Action, ...]
    terminal_values: tuple[Fraction, Fraction] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.config, PreflopConfig):
            raise ValueError("config must be PreflopConfig")
        if isinstance(self.acting_player, bool) or self.acting_player not in (CHANCE, TERMINAL, 0, 1):
            raise ValueError("acting_player must be CHANCE, TERMINAL, 0, or 1")
        for name in ("committed", "total_contributed", "remaining"):
            values = getattr(self, name)
            if (
                not isinstance(values, tuple)
                or len(values) != 2
                or any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values)
            ):
                raise ValueError(f"{name} must be two non-negative integers")
        _chips(self.pot, "pot")
        _positive_int(self.last_raise_increment, "last_raise_increment")
        if isinstance(self.raise_count, bool) or not isinstance(self.raise_count, int) or not 0 <= self.raise_count <= self.config.max_raises:
            raise ValueError("raise_count is outside the configured bound")
        for name in ("acted", "can_raise"):
            values = getattr(self, name)
            if not isinstance(values, tuple) or len(values) != 2 or any(not isinstance(value, bool) for value in values):
                raise ValueError(f"{name} must be two booleans")
        if not isinstance(self.history, tuple) or any(not isinstance(action, Action) for action in self.history):
            raise ValueError("history must be a tuple of Action values")
        if self.pot != sum(self.total_contributed):
            raise ValueError("pot must equal total contributions")
        if any(committed > total for committed, total in zip(self.committed, self.total_contributed)):
            raise ValueError("street commitment cannot exceed total contribution")
        if any(
            remaining + total != stack
            for remaining, total, stack in zip(self.remaining, self.total_contributed, self.config.starting_stacks)
        ):
            raise ValueError("remaining stack and contribution must conserve starting stack")
        if self.acting_player == CHANCE:
            if self.private_deal is not None or self.history or self.terminal_values is not None:
                raise ValueError("chance root cannot contain a deal, history, or returns")
        else:
            valid_deals = {deal for deal, _ in _deals(self.config)}
            if self.private_deal not in valid_deals:
                raise ValueError("dealt state requires a compatible configured private deal")
        if self.acting_player == TERMINAL:
            if not isinstance(self.terminal_values, tuple) or len(self.terminal_values) != 2:
                raise ValueError("terminal state requires two returns")
            if any(isinstance(value, bool) for value in self.terminal_values):
                raise ValueError("terminal returns must be finite exact numbers")
            try:
                exact = tuple(Fraction(value) for value in self.terminal_values)
            except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
                raise ValueError("terminal returns must be finite exact numbers") from exc
            if any(not isfinite(float(value)) for value in exact) or sum(exact) != 0:
                raise ValueError("terminal returns must be finite and zero-sum")
            object.__setattr__(self, "terminal_values", exact)
        elif self.terminal_values is not None:
            raise ValueError("non-terminal state cannot contain returns")

    def current_player(self) -> int:
        return self.acting_player

    def chance_outcomes(self) -> tuple[tuple[Action, Fraction], ...]:
        if self.acting_player != CHANCE:
            return ()
        deals = _deals(self.config)
        total = sum(weight for _, weight in deals)
        return tuple((Action("DEAL", index), weight / total) for index, (_, weight) in enumerate(deals))

    def legal_actions(self) -> tuple[Action, ...]:
        if self.acting_player in (CHANCE, TERMINAL):
            return ()
        player = self.acting_player
        other = 1 - player
        own = self.committed[player]
        highest = max(self.committed)
        to_call = highest - own
        actions: list[Action] = []
        if to_call:
            actions.append(Action("FOLD"))
            actions.append(Action("CALL", min(highest, own + self.remaining[player])))
        else:
            actions.append(Action("CHECK"))
        if self.can_raise[player] and self.remaining[player] > to_call and self.raise_count < self.config.max_raises:
            minimum = highest + self.last_raise_increment
            context = {
                "pot": self.pot,
                "own_commitment": own,
                "highest_commitment": highest,
                "remaining_stack": self.remaining[player],
                "big_blind": self.config.forced_posts[1],
                "minimum_raise_to": minimum,
                "pot_limit_max_raise_to": None,
                "short_all_in_allowed": True,
            }
            expressions = tuple(dict(expression) for expression in self.config.sizing_expressions)
            actions.extend(Action("RAISE", choice.target) for choice in fixed_sizes(expressions, context))
        return tuple(actions)

    def child(self, action: Action) -> PreflopState:
        if not isinstance(action, Action):
            raise ValueError("action must be Action")
        if self.acting_player == CHANCE:
            outcomes = self.chance_outcomes()
            if action not in {candidate for candidate, _ in outcomes}:
                raise ValueError("action is not legal")
            deal_value = _deals(self.config)[action.amount][0]
            return self._replace(private_deal=deal_value, acting_player=0)
        if action not in self.legal_actions():
            raise ValueError("action is not legal")
        player = self.acting_player
        other = 1 - player
        history = self.history + (action,)
        if action.kind == "FOLD":
            values = [Fraction(-self.total_contributed[0]), Fraction(-self.total_contributed[1])]
            values[other] += self.pot
            return self._replace(acting_player=TERMINAL, history=history, terminal_values=tuple(values))

        committed = list(self.committed)
        contributed = list(self.total_contributed)
        remaining = list(self.remaining)
        acted = list(self.acted)
        can_raise = list(self.can_raise)
        pot = self.pot
        raise_count = self.raise_count
        increment = self.last_raise_increment

        if action.kind == "CHECK":
            acted[player] = True
        elif action.kind == "CALL":
            payment = action.amount - committed[player]
            committed[player] += payment
            contributed[player] += payment
            remaining[player] -= payment
            pot += payment
            acted[player] = True
        else:
            old_highest = max(committed)
            payment = action.amount - committed[player]
            committed[player] += payment
            contributed[player] += payment
            remaining[player] -= payment
            pot += payment
            raise_size = action.amount - old_highest
            full_raise = raise_size >= increment
            if full_raise:
                increment = raise_size
                acted = [False, False]
                acted[player] = True
                can_raise = [True, True]
            else:
                acted[player] = True
                if not self.config.short_all_in_reopens:
                    can_raise[other] = False
            raise_count += 1

        if committed[0] == committed[1] and all(acted):
            return self._continuation(history, tuple(committed), tuple(contributed), tuple(remaining), pot, increment, tuple(acted), tuple(can_raise), raise_count)
        if (remaining[0] == 0 or remaining[1] == 0) and committed[0] == committed[1]:
            return self._continuation(history, tuple(committed), tuple(contributed), tuple(remaining), pot, increment, tuple(acted), tuple(can_raise), raise_count)
        # A call by a short stack can leave unmatched excess; refund before closing.
        if action.kind == "CALL" and remaining[player] == 0 and committed[0] != committed[1]:
            rich = 0 if committed[0] > committed[1] else 1
            excess = abs(committed[0] - committed[1])
            committed[rich] -= excess
            contributed[rich] -= excess
            remaining[rich] += excess
            pot -= excess
            return self._continuation(history, tuple(committed), tuple(contributed), tuple(remaining), pot, increment, tuple(acted), tuple(can_raise), raise_count)
        return self._replace(
            acting_player=other,
            pot=pot,
            committed=tuple(committed),
            total_contributed=tuple(contributed),
            remaining=tuple(remaining),
            last_raise_increment=increment,
            acted=tuple(acted),
            can_raise=tuple(can_raise),
            raise_count=raise_count,
            history=history,
        )

    def _continuation(self, history, committed, contributed, remaining, pot, increment, acted, can_raise, raise_count):
        assert self.private_deal is not None
        key = (self.private_deal, history)
        if key not in self.config.continuation.payoff_table:
            raise ValueError("missing continuation value for closed preflop leaf")
        return self._replace(
            acting_player=TERMINAL,
            pot=pot,
            committed=committed,
            total_contributed=contributed,
            remaining=remaining,
            last_raise_increment=increment,
            acted=acted,
            can_raise=can_raise,
            raise_count=raise_count,
            history=history,
            terminal_values=self.config.continuation.payoff_table[key],
        )

    def information_state_key(self, player: int):
        if player not in (0, 1) or self.private_deal is None:
            raise ValueError("information key requires dealt state and player 0 or 1")
        return (
            self.config.version,
            player,
            self.private_deal[player],
            self.config.starting_stacks,
            self.config.forced_posts,
            self.pot,
            self.committed,
            self.remaining,
            self.last_raise_increment,
            self.history,
            tuple(tuple(sorted(expression.items())) for expression in self.config.sizing_expressions),
            self.config.continuation.kind,
            self.config.continuation.provenance,
        )

    def returns(self) -> tuple[float, float]:
        if self.acting_player != TERMINAL or self.terminal_values is None:
            raise ValueError("returns only exist at terminal states")
        return tuple(float(value) for value in self.terminal_values)  # type: ignore[return-value]

    def _replace(self, **changes) -> PreflopState:
        values = {field: getattr(self, field) for field in self.__dataclass_fields__}
        values.update(changes)
        return PreflopState(**values)


def _deals(config: PreflopConfig) -> tuple[tuple[Deal, Fraction], ...]:
    deals = []
    for first in config.ranges[0]:
        for second in config.ranges[1]:
            if set(first.cards).isdisjoint(second.cards):
                deals.append(((first.cards, second.cards), first.weight * second.weight))
    if not deals:
        raise ValueError("ranges produce no compatible private deals")
    if len(deals) > config.max_deals:
        raise ValueError("deal count exceeds max_deals")
    return tuple(deals)


def create_preflop_root(config: PreflopConfig) -> PreflopState:
    if not isinstance(config, PreflopConfig):
        raise ValueError("config must be PreflopConfig")
    deals = _deals(config)
    if 1 + len(deals) > config.max_nodes:
        raise ValueError("node bound too small for root chance expansion")
    posts = config.forced_posts
    remaining = tuple(stack - post for stack, post in zip(config.starting_stacks, posts))
    return PreflopState(
        config=config,
        private_deal=None,
        acting_player=CHANCE,
        pot=sum(posts),
        committed=posts,
        total_contributed=posts,
        remaining=remaining,
        last_raise_increment=config.forced_posts[1],
        acted=(False, False),
        can_raise=(True, True),
        raise_count=0,
        history=(),
    )
