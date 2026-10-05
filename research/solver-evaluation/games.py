"""Benchmark-owned reference games and independent oracles.

Nothing here imports solver *results*; the oracles are re-implemented from first
principles so they can check the repo's solver, best-response and practice-scoring
code instead of echoing it.

* :class:`ThreePlayerKuhn` - standard three-player Kuhn poker (Abou Risk & Szafron
  2010: four cards, ante 1, one bet of 1). Known analytic equilibrium family
  (Szafron, Gibson & Sturtevant, AAMAS 2013): player 2 (seat 1) always earns
  -1/48 per hand; seat 0 earns -(1+2b)/48 and seat 2 earns (1+b)/24, b in [0, 1].
* :func:`best_response_value` - infoset-consistent best response for any number of
  players (aggregate opponent+chance reach over every history in an infoset, then
  pick one action per infoset), independent of ``poker_solver.best_response``.
* :func:`nash_conv_n` - sum over players of BR value minus profile value.
* :func:`independent_action_values` - Q(a) at one infoset, re-derived from scratch.
* :func:`malmuth_harville` - ICM by explicit finishing-order enumeration.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from math import fsum
from typing import Any, Hashable, Mapping, Sequence

from poker_solver.model import CHANCE, TERMINAL, Action

Profile = Mapping[Hashable, Mapping[Action, float]]

# --------------------------------------------------------------------------- 3-player Kuhn

K3_CARDS = "JQKA"
K3_DEALS = tuple(permutations(range(4), 3))
K3_CHECK = Action("check")
K3_BET = Action("bet")
K3_FOLD = Action("fold")
K3_CALL = Action("call")
#: Analytic reference values (Szafron, Gibson & Sturtevant 2013).
K3_SEAT1_VALUE = -1.0 / 48.0
K3_SEAT0_RANGE = (-3.0 / 48.0, -1.0 / 48.0)
K3_SEAT2_RANGE = (1.0 / 24.0, 2.0 / 24.0)


@dataclass(frozen=True, slots=True)
class ThreePlayerKuhn:
    """Immutable three-player Kuhn poker state (seat order 0, 1, 2; ante 1, bet 1)."""

    deal: tuple[int, int, int] | None = None
    history: tuple[Action, ...] = ()

    def num_players(self) -> int:
        return 3

    def _bet_index(self) -> int | None:
        for index, action in enumerate(self.history):
            if action == K3_BET:
                return index
        return None

    def current_player(self) -> int:
        if self.deal is None:
            return CHANCE
        bet = self._bet_index()
        if bet is None:
            return TERMINAL if len(self.history) == 3 else len(self.history)
        responses = len(self.history) - bet - 1
        if responses == 2:
            return TERMINAL
        return (bet + 1 + responses) % 3

    def legal_actions(self) -> tuple[Action, ...]:
        player = self.current_player()
        if player == CHANCE:
            return tuple(Action("deal", i) for i in range(len(K3_DEALS)))
        if player == TERMINAL:
            return ()
        return (K3_CHECK, K3_BET) if self._bet_index() is None else (K3_FOLD, K3_CALL)

    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]:
        if self.current_player() != CHANCE:
            return ()
        p = 1.0 / len(K3_DEALS)
        return tuple((Action("deal", i), p) for i in range(len(K3_DEALS)))

    def child(self, action: Action) -> "ThreePlayerKuhn":
        if action not in self.legal_actions():
            raise ValueError(f"illegal action {action!r}")
        if self.deal is None:
            return ThreePlayerKuhn(K3_DEALS[action.amount], ())
        return ThreePlayerKuhn(self.deal, self.history + (action,))

    def information_state_key(self, player: int) -> tuple[object, ...]:
        if self.current_player() != player or self.deal is None:
            raise ValueError("information key requested for non-acting player")
        return ("kuhn3-bench", player, K3_CARDS[self.deal[player]], self.history)

    def returns(self) -> tuple[float, float, float]:
        if self.current_player() != TERMINAL or self.deal is None:
            raise ValueError("returns requested at non-terminal")
        contributed = [1.0, 1.0, 1.0]
        live = [True, True, True]
        bet = self._bet_index()
        if bet is not None:
            contributed[bet] += 1.0
            for offset, action in enumerate(self.history[bet + 1:]):
                seat = (bet + 1 + offset) % 3
                if action == K3_CALL:
                    contributed[seat] += 1.0
                else:
                    live[seat] = False
        pot = sum(contributed)
        deal = self.deal
        winner = max((s for s in range(3) if live[s]), key=lambda s: deal[s])
        return tuple((pot if s == winner else 0.0) - contributed[s] for s in range(3))  # type: ignore[return-value]


# --------------------------------------------------------------------------- oracles


def profile_value(root: Any, profile: Profile, player: int) -> float:
    """Expected payoff for ``player`` when everyone follows ``profile`` (own walker)."""

    def walk(state: Any) -> float:
        actor = state.current_player()
        if actor == TERMINAL:
            return float(state.returns()[player])
        if actor == CHANCE:
            return fsum(p * walk(state.child(a)) for a, p in state.chance_outcomes())
        policy = profile[state.information_state_key(actor)]
        return fsum(policy[a] * walk(state.child(a)) for a in state.legal_actions() if policy[a] > 0)

    return walk(root)


def best_response_value(root: Any, profile: Profile, responder: int) -> float:
    """Exact infoset-consistent best-response value of ``responder`` against ``profile``."""
    nodes: dict[Hashable, list[tuple[Any, float]]] = {}

    def discover(state: Any, weight: float) -> None:
        actor = state.current_player()
        if actor == TERMINAL:
            return
        if actor == CHANCE:
            for action, p in state.chance_outcomes():
                if p > 0:
                    discover(state.child(action), weight * p)
            return
        if actor == responder:
            nodes.setdefault(state.information_state_key(actor), []).append((state, weight))
            for action in state.legal_actions():
                discover(state.child(action), weight)
            return
        policy = profile[state.information_state_key(actor)]
        for action in state.legal_actions():
            if policy[action] > 0:
                discover(state.child(action), weight * policy[action])

    discover(root, 1.0)
    chosen: dict[Hashable, Action] = {}
    deciding: set[Hashable] = set()

    def decide(key: Hashable) -> Action:
        if key in chosen:
            return chosen[key]
        if key in deciding:
            raise ValueError("cyclic responder infoset dependency (imperfect recall?)")
        deciding.add(key)
        members = nodes[key]
        actions = members[0][0].legal_actions()
        totals = [fsum(w * continuation(s.child(a)) for s, w in members) for a in actions]
        best = max(range(len(actions)), key=totals.__getitem__)
        chosen[key] = actions[best]
        deciding.discard(key)
        return chosen[key]

    def continuation(state: Any) -> float:
        actor = state.current_player()
        if actor == TERMINAL:
            return float(state.returns()[responder])
        if actor == CHANCE:
            return fsum(p * continuation(state.child(a)) for a, p in state.chance_outcomes() if p > 0)
        key = state.information_state_key(actor)
        if actor == responder:
            return continuation(state.child(decide(key)))
        policy = profile[key]
        return fsum(policy[a] * continuation(state.child(a)) for a in state.legal_actions() if policy[a] > 0)

    return continuation(root)


def nash_conv_n(root: Any, profile: Profile, players: int) -> dict[str, Any]:
    """Independent NashConv = sum_i (BR_i - u_i) for an n-player profile."""
    values = [profile_value(root, profile, p) for p in range(players)]
    brs = [best_response_value(root, profile, p) for p in range(players)]
    incentives = [b - v for b, v in zip(brs, values)]
    return {"values": values, "best_response_values": brs, "incentives": incentives,
            "nash_conv": fsum(incentives)}


def independent_action_values(root: Any, profile: Profile, hero: int, key: Hashable) -> tuple[dict[Action, float], float]:
    """Q(a) at infoset ``key``: chance x opponent reach weighted, everyone follows ``profile`` after."""
    numer: dict[Action, list[float]] = {}
    mass: list[float] = []

    def walk(state: Any, weight: float) -> None:
        actor = state.current_player()
        if actor == TERMINAL or weight == 0.0:
            return
        if actor == CHANCE:
            for action, p in state.chance_outcomes():
                walk(state.child(action), weight * p)
            return
        state_key = state.information_state_key(actor)
        if actor == hero and state_key == key:
            mass.append(weight)
            for action in state.legal_actions():
                numer.setdefault(action, []).append(weight * profile_value(state.child(action), profile, hero))
            return
        if actor == hero:
            for action in state.legal_actions():
                walk(state.child(action), weight)
            return
        policy = profile[state_key]
        for action in state.legal_actions():
            walk(state.child(action), weight * policy[action])

    walk(root, 1.0)
    total = fsum(mass)
    if total <= 0:
        raise ValueError("infoset unreachable under the profile")
    return {a: fsum(v) / total for a, v in numer.items()}, total


def malmuth_harville(stacks: Sequence[float], payouts: Sequence[float]) -> tuple[float, ...]:
    """ICM equities by enumerating every finishing order (n! orders, n <= 7 here)."""
    n = len(stacks)
    equities = [0.0] * n
    for order in permutations(range(n)):
        probability = 1.0
        remaining = float(sum(stacks))
        for seat in order:
            probability *= stacks[seat] / remaining
            remaining -= stacks[seat]
        for place, seat in enumerate(order):
            if place < len(payouts):
                equities[seat] += probability * payouts[place]
    return tuple(equities)


# --------------------------------------------------------------------------- memoizing proxy


class Memo:
    """Benchmark-owned memoizing proxy over an immutable solver ``GameState``.

    Solver states are frozen dataclasses with pure methods, so caching children /
    actions / chance outcomes / keys / returns changes no value; it only stops the
    benchmark from re-validating identical states every CFR iteration.  (The practice
    adapter has its own equivalent; this copy keeps the benchmark independent of it.)
    """

    __slots__ = ("state", "_player", "_children", "_actions", "_outcomes", "_keys", "_returns")

    def __init__(self, state: Any):
        self.state = state
        self._player = state.current_player()
        self._children: dict[Action, Memo] = {}
        self._actions: tuple[Action, ...] | None = None
        self._outcomes: tuple[tuple[Action, float], ...] | None = None
        self._keys: dict[int, Hashable] = {}
        self._returns: tuple[float, ...] | None = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self.state, name)

    def current_player(self) -> int:
        return self._player

    def num_players(self) -> int:
        counter = getattr(self.state, "num_players", None)
        return 2 if counter is None else counter()

    def legal_actions(self) -> tuple[Action, ...]:
        if self._actions is None:
            self._actions = self.state.legal_actions()
        return self._actions

    def chance_outcomes(self) -> tuple[tuple[Action, float], ...]:
        if self._outcomes is None:
            self._outcomes = self.state.chance_outcomes()
        return self._outcomes

    def child(self, action: Action) -> "Memo":
        node = self._children.get(action)
        if node is None:
            node = Memo(self.state.child(action))
            self._children[action] = node
        return node

    def information_state_key(self, player: int) -> Hashable:
        key = self._keys.get(player)
        if key is None:
            key = self.state.information_state_key(player)
            self._keys[player] = key
        return key

    def returns(self) -> tuple[float, ...]:
        if self._returns is None:
            self._returns = tuple(self.state.returns())
        return self._returns
