"""N-player tree compilation, an exact fast vanilla-CFR trainer and NashConv for practice.

Three pieces, all pure Python and all computed at runtime from the real solver game:

* :class:`FlatTree` -- the solver's game tree (``nplayer_preflop`` states, usually
  behind :class:`~poker_solver.practice.adapter.CachedState`) compiled once into flat
  index arrays.  No value is altered: terminal returns, chance probabilities, legal
  action order and information-set keys are copied verbatim from the states.
* :class:`FlatNPlayerCFR` -- synchronous vanilla CFR that reproduces
  :class:`poker_solver.nplayer.NPlayerCFRSolver` **bit for bit** (same regret
  matching, same per-player counterfactual weights, same floating-point operation
  order) but walks the tree once per iteration for all players at the same time
  instead of once per player, over arrays instead of dicts.  The equivalence is
  asserted by ``tests/test_practice_w5_repairs.py``.
* :func:`nash_conv_nplayer` -- NashConv = sum over players of (best-response value -
  profile value), with an exact infoset-consistent best response (opponent and chance
  reach aggregated over every history in an infoset).  Same definition as the
  solver-evaluation benchmark's independent oracle (``games.nash_conv_n``); it is the
  number reported as ``SolveProvenance.nash_conv`` for 3-max spots.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import fsum, isfinite
from functools import reduce
from operator import add, itemgetter, mul, sub
from typing import Any, Hashable, Mapping

from ..model import CHANCE, TERMINAL, Action

__all__ = ["FlatTree", "FlatNPlayerCFR", "NPlayerNashConv", "nash_conv_nplayer"]

_TERMINAL, _CHANCE, _DECISION = 0, 1, 2


class FlatTree:
    """Game tree compiled into flat arrays (node 0 is the root).

    ``kind[i]`` is terminal / chance / decision; ``children[i]`` follows the state's
    ``legal_actions()`` (decision) or ``chance_outcomes()`` (chance) order;
    ``probs[i]`` holds chance probabilities; ``returns[i]`` the terminal utilities;
    ``infoset[i]`` indexes ``keys`` / ``actions`` / ``owner`` for decision nodes.
    """

    __slots__ = ("players", "kind", "player", "infoset", "children", "probs", "returns",
                 "keys", "actions", "owner", "key_index")

    def __init__(self, root: Any, *, max_nodes: int = 1_000_000, max_depth: int = 512):
        counter = getattr(root, "num_players", None)
        players = 2 if counter is None else counter()
        if isinstance(players, bool) or not isinstance(players, int) or not 2 <= players <= 9:
            raise ValueError("num_players must be an integer from 2 to 9")
        self.players = players
        self.kind: list[int] = []
        self.player: list[int] = []
        self.infoset: list[int] = []
        self.children: list[tuple[int, ...]] = []
        self.probs: list[tuple[float, ...]] = []
        self.returns: list[tuple[float, ...]] = []
        self.keys: list[Hashable] = []
        self.actions: list[tuple[Action, ...]] = []
        self.owner: list[int] = []
        self.key_index: dict[Hashable, int] = {}
        self._compile(root, max_nodes, max_depth)

    def _new(self) -> int:
        self.kind.append(_TERMINAL)
        self.player.append(-1)
        self.infoset.append(-1)
        self.children.append(())
        self.probs.append(())
        self.returns.append(())
        return len(self.kind) - 1

    def _compile(self, root: Any, max_nodes: int, max_depth: int) -> None:
        stack = [(root, self._new(), 0)]
        while stack:
            state, index, depth = stack.pop()
            if depth > max_depth:
                raise ValueError("game exceeds finite depth bound")
            if len(self.kind) > max_nodes:
                raise ValueError("game exceeds finite node bound")
            actor = state.current_player()
            if actor == TERMINAL:
                values = tuple(float(v) for v in state.returns())
                if len(values) != self.players or not all(isfinite(v) for v in values):
                    raise ValueError("terminal returns must be finite with one entry per player")
                self.returns[index] = values
                continue
            if actor == CHANCE:
                outcomes = state.chance_outcomes()
                if not outcomes:
                    raise ValueError("chance node must have outcomes")
                kids = tuple(self._new() for _ in outcomes)
                self.kind[index] = _CHANCE
                self.children[index] = kids
                self.probs[index] = tuple(float(p) for _, p in outcomes)
                for (action, _p), kid in zip(outcomes, kids):
                    stack.append((state.child(action), kid, depth + 1))
                continue
            if isinstance(actor, bool) or not isinstance(actor, int) or not 0 <= actor < self.players:
                raise ValueError("current player is outside player range")
            actions = tuple(state.legal_actions())
            if not actions or len(set(actions)) != len(actions):
                raise ValueError("decision node actions must be non-empty and unique")
            key = state.information_state_key(actor)
            slot = self.key_index.get(key)
            if slot is None:
                slot = self.key_index[key] = len(self.keys)
                self.keys.append(key)
                self.actions.append(actions)
                self.owner.append(actor)
            elif self.actions[slot] != actions or self.owner[slot] != actor:
                raise ValueError("information set owner/action mismatch")
            kids = tuple(self._new() for _ in actions)
            self.kind[index] = _DECISION
            self.player[index] = actor
            self.infoset[index] = slot
            self.children[index] = kids
            for action, kid in zip(actions, kids):
                stack.append((state.child(action), kid, depth + 1))

    def profile_arrays(self, profile: Mapping[Hashable, Mapping[Action, float]]) -> list[list[float]]:
        """Per-infoset probability lists (legal-action order) from a key -> policy profile."""
        out = []
        for key, actions in zip(self.keys, self.actions):
            try:
                policy = profile[key]
            except KeyError:
                raise ValueError(f"profile has no policy for information set {key!r}") from None
            out.append([float(policy[a]) for a in actions])
        return out


class _PublicTree:
    """Root chance over private deals, each deal subtree having the same betting shape.

    Nodes: terminal ``(None, per-seat lists of returns over deals, (), 0, ())``; decision
    ``(player, gather(per-infoset list) -> per-deal tuple, kids, width,
    ((slot, gather(per-deal list) -> that slot's deals in order), ...))``.  ``chance_probs[d]`` is the reference's
    chance reach below the root (``1.0 * p_d``).
    """

    __slots__ = ("players", "root", "chance_probs")

    def __init__(self, players: int, root: Any, chance_probs: list[float]):
        self.players = players
        self.root = root
        self.chance_probs = chance_probs

    @classmethod
    def build(cls, tree: FlatTree) -> "_PublicTree | bool":
        if tree.kind[0] != _CHANCE:
            return False
        deals = tree.children[0]
        n = tree.players
        seen: set[int] = set()

        def merge(nodes: tuple[int, ...]) -> Any:
            first = nodes[0]
            k = tree.kind[first]
            if any(tree.kind[x] != k for x in nodes):
                raise _NotPublic
            if k == _TERMINAL:
                return (None, [[tree.returns[x][i] for x in nodes] for i in range(n)], (), 0, ())

            if k == _CHANCE:
                raise _NotPublic
            player = tree.player[first]
            width = len(tree.children[first])
            if any(tree.player[x] != player or len(tree.children[x]) != width for x in nodes):
                raise _NotPublic
            slots = [tree.infoset[x] for x in nodes]
            for slot in set(slots):
                if slot in seen:
                    raise _NotPublic  # an infoset spanning public nodes would change summation order
                seen.add(slot)
            kids = tuple(merge(tuple(tree.children[x][j] for x in nodes)) for j in range(width))
            order: dict[int, list[int]] = {}
            for deal, slot in enumerate(slots):
                order.setdefault(slot, []).append(deal)
            groups = tuple((slot, _gatherer(deals_of)) for slot, deals_of in order.items())
            return (player, _gatherer(slots), kids, width, groups)

        try:
            root = merge(deals)
        except _NotPublic:
            return False
        if root[0] is None:
            return False
        return cls(n, root, [1.0 * p for p in tree.probs[0]])


class _NotPublic(Exception):
    pass


def _gatherer(indices: list[int]) -> Any:
    """C-level ``lambda seq: tuple(seq[i] for i in indices)`` (always returns a tuple)."""
    if len(indices) == 1:
        only = indices[0]
        return lambda seq: (seq[only],)
    return itemgetter(*indices)


class FlatNPlayerCFR:
    """Vanilla CFR over a :class:`FlatTree`, bit-identical to ``NPlayerCFRSolver``.

    ``NPlayerCFRSolver.train`` walks the tree once per updating player; every node's
    reach vector and every player's value at a node are independent of which player is
    updating, so one walk returning the whole value vector performs the same floating
    point operations, in the same order, for each component.  Strategy sums are
    accumulated where the reference accumulates them (its player-0 walk, i.e. the same
    DFS position) and regrets are applied after the walk, as in the reference.
    """

    def __init__(self, tree: FlatTree):
        self.tree = tree
        self.iterations = 0
        self.regrets = [[0.0] * len(a) for a in tree.actions]
        self.strategy_sum = [[0.0] * len(a) for a in tree.actions]
        self._public: Any = None  # _PublicTree, or False when the deal-vector path does not apply

    def _current(self) -> list[list[float]]:
        out = []
        for regrets in self.regrets:
            positives = [r if r > 0.0 else 0.0 for r in regrets]  # == max(0.0, r)
            total = sum(positives)
            if total > 0:
                out.append([p / total for p in positives])
            else:
                uniform = 1.0 / len(regrets)
                out.append([uniform] * len(regrets))
        return out

    def average_strategy(self) -> dict[Hashable, dict[Action, float]]:
        result: dict[Hashable, dict[Action, float]] = {}
        for key, actions, sums in zip(self.tree.keys, self.tree.actions, self.strategy_sum):
            total = sum(sums)
            if total > 0:
                result[key] = {a: s / total for a, s in zip(actions, sums)}
            else:
                uniform = 1.0 / len(actions)
                result[key] = {a: uniform for a in actions}
        return result

    def _iterate_public(self, public: "_PublicTree") -> None:
        """One iteration over the public tree, every private deal processed as a vector.

        Per deal the arithmetic is the reference's: reach ``r * p``, node values
        ``p_0 v_0 + p_1 v_1 + ...`` left to right, counterfactual ``(cr * r_a) * r_b``
        over opponents in seat order, regret term ``cf * (v_a - v)`` and strategy-sum term
        ``r_own * p``.  An information set lives at exactly one public node (checked when
        the public tree is built) and occurs at most once per deal there, so the reference
        adds its terms consecutively in deal (= DFS) order: ``delta`` from ``0.0``, then
        ``regret += delta`` after the walk; ``strategy_sum += term`` in place.  The same
        sequential additions are done here with ``functools.reduce(operator.add, ...)``
        over the terms gathered per information set in deal order.  Regrets can be
        updated during the walk because this iteration's strategy was fixed beforehand.
        """
        n = public.players
        strategy = self._current()
        strategy_sum = self.strategy_sum
        regrets = self.regrets
        seats = range(n)
        chance_reach = public.chance_probs

        def walk(node: Any, reaches: list[list[float]]) -> list[list[Any]]:
            player, gather_policy, kids, width, groups = node
            own_reach = reaches[player]
            columns = list(zip(*gather_policy(strategy)))  # columns[j][d]: deal d, action j
            children = []
            for j, kid in enumerate(kids):
                column = columns[j]
                terms = list(map(mul, own_reach, column))
                for slot, gather in groups:
                    row = strategy_sum[slot]
                    row[j] = reduce(add, gather(terms), row[j])
                if kid[0] is None:  # terminal: per-seat lists over deals
                    children.append(kid[1])
                    continue
                child_reaches = list(reaches)
                child_reaches[player] = terms
                children.append(walk(kid, child_reaches))
            values: list[list[Any]] = []
            first_column, rest_columns = columns[0], columns[1:]
            first_child, rest_children = children[0], children[1:]
            for i in seats:
                # The reference's ``sum()`` starts at int 0; ``0 + x == x`` for every
                # float x (only -0.0 becomes 0.0, which compares equal), so it is skipped.
                acc: Any = list(map(mul, first_column, first_child[i]))
                for column, child in zip(rest_columns, rest_children):
                    acc = list(map(add, acc, map(mul, column, child[i])))
                values.append(acc)
            counterfactual: Any = chance_reach
            for opponent in seats:
                if opponent != player:
                    counterfactual = list(map(mul, counterfactual, reaches[opponent]))
            own = values[player]
            for j, child in enumerate(children):
                terms = list(map(mul, counterfactual, map(sub, child[player], own)))
                for slot, gather in groups:
                    row = regrets[slot]
                    row[j] = row[j] + reduce(add, gather(terms), 0.0)
            return values

        walk(public.root, [[1.0] * len(chance_reach) for _ in seats])
        self.iterations += 1

    def train(self, iterations: int) -> dict[Hashable, dict[Action, float]]:
        if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations <= 0:
            raise ValueError("iterations must be a positive integer")
        tree = self.tree
        n = tree.players
        kind, player_of, infoset_of = tree.kind, tree.player, tree.infoset
        children, probs, rets = tree.children, tree.probs, tree.returns
        strategy_sum = self.strategy_sum
        seats = range(n)
        if self._public is None:
            self._public = _PublicTree.build(tree)
        if self._public is not False:
            for _ in range(iterations):
                self._iterate_public(self._public)
            return self.average_strategy()
        for _ in range(iterations):
            strategy = self._current()
            deltas = [[0.0] * len(a) for a in tree.actions]

            def walk(node: int, reaches: list[float], chance_reach: float) -> list[Any]:
                k = kind[node]
                if k == _TERMINAL:
                    return list(rets[node])
                if k == _CHANCE:
                    total: list[Any] = [0] * n  # int 0 start, exactly like ``sum()`` in the reference
                    for kid, p in zip(children[node], probs[node]):
                        child = walk(kid, reaches, chance_reach * p)
                        for i in seats:
                            total[i] = total[i] + p * child[i]
                    return total
                player = player_of[node]
                slot = infoset_of[node]
                policy = strategy[slot]
                owner_reach = reaches[player]
                sums = strategy_sum[slot]
                kids = children[node]
                for j in range(len(kids)):
                    sums[j] += owner_reach * policy[j]
                values = []
                for j, kid in enumerate(kids):
                    child_reaches = reaches.copy()
                    child_reaches[player] *= policy[j]
                    values.append(walk(kid, child_reaches, chance_reach))
                node_value: list[Any] = [0] * n
                for i in seats:
                    acc: Any = 0
                    for j in range(len(kids)):
                        acc = acc + policy[j] * values[j][i]
                    node_value[i] = acc
                counterfactual = chance_reach
                for opponent, reach in enumerate(reaches):
                    if opponent != player:
                        counterfactual *= reach
                own = node_value[player]
                delta = deltas[slot]
                for j in range(len(kids)):
                    delta[j] += counterfactual * (values[j][player] - own)
                return node_value

            walk(0, [1.0] * n, 1.0)
            for regrets, delta in zip(self.regrets, deltas):
                for j in range(len(regrets)):
                    regrets[j] += delta[j]
            self.iterations += 1
        return self.average_strategy()


@dataclass(frozen=True, slots=True)
class NPlayerNashConv:
    """Per-player profile values, best-response values and incentives (chips)."""

    values: tuple[float, ...]
    best_response_values: tuple[float, ...]
    incentives: tuple[float, ...]
    nash_conv: float


def _profile_values(tree: FlatTree, policy: list[list[float]]) -> list[float]:
    n = tree.players
    kind, children, probs, rets, infoset_of = tree.kind, tree.children, tree.probs, tree.returns, tree.infoset

    def walk(node: int) -> list[float]:
        k = kind[node]
        if k == _TERMINAL:
            return list(rets[node])
        weights = probs[node] if k == _CHANCE else policy[infoset_of[node]]
        terms: list[list[float]] = [[] for _ in range(n)]
        for kid, w in zip(children[node], weights):
            if w > 0:
                child = walk(kid)
                for i in range(n):
                    terms[i].append(w * child[i])
        return [fsum(t) for t in terms]

    return walk(0)


def _best_response(tree: FlatTree, policy: list[list[float]], responder: int) -> float:
    """Exact infoset-consistent best-response value of ``responder``."""
    kind, children, probs, rets = tree.kind, tree.children, tree.probs, tree.returns
    player_of, infoset_of = tree.player, tree.infoset
    members: dict[int, list[tuple[int, float]]] = {}

    stack = [(0, 1.0)]
    while stack:
        node, weight = stack.pop()
        k = kind[node]
        if k == _TERMINAL:
            continue
        if k == _CHANCE:
            stack.extend((kid, weight * p) for kid, p in zip(children[node], probs[node]) if p > 0)
        elif player_of[node] == responder:
            members.setdefault(infoset_of[node], []).append((node, weight))
            stack.extend((kid, weight) for kid in children[node])
        else:
            stack.extend((kid, weight * p) for kid, p in zip(children[node], policy[infoset_of[node]]) if p > 0)

    chosen: dict[int, int] = {}
    deciding: set[int] = set()
    memo: dict[int, float] = {}

    def decide(slot: int) -> int:
        if slot in chosen:
            return chosen[slot]
        if slot in deciding:
            raise ValueError("cyclic responder infoset dependency (imperfect recall?)")
        deciding.add(slot)
        group = members[slot]
        width = len(tree.actions[slot])
        totals = [fsum(w * continuation(children[node][j]) for node, w in group) for j in range(width)]
        best = max(range(width), key=totals.__getitem__)
        chosen[slot] = best
        deciding.discard(slot)
        return best

    def continuation(node: int) -> float:
        cached = memo.get(node)
        if cached is not None:
            return cached
        k = kind[node]
        if k == _TERMINAL:
            value = rets[node][responder]
        elif k == _CHANCE:
            value = fsum(p * continuation(kid) for kid, p in zip(children[node], probs[node]) if p > 0)
        elif player_of[node] == responder:
            value = continuation(children[node][decide(infoset_of[node])])
        else:
            value = fsum(p * continuation(kid) for kid, p in zip(children[node], policy[infoset_of[node]]) if p > 0)
        memo[node] = value
        return value

    return continuation(0)


def nash_conv_nplayer(tree_or_root: Any, profile: Mapping[Hashable, Mapping[Action, float]]) -> NPlayerNashConv:
    """NashConv = sum_i (BR_i - u_i) of ``profile`` (each incentive is >= 0 up to rounding).

    ``tree_or_root`` is a :class:`FlatTree` or a game root (compiled on the fly).
    """
    tree = tree_or_root if isinstance(tree_or_root, FlatTree) else FlatTree(tree_or_root)
    policy = tree.profile_arrays(profile)
    values = _profile_values(tree, policy)
    brs = [_best_response(tree, policy, p) for p in range(tree.players)]
    incentives = [b - v for b, v in zip(brs, values)]
    total = fsum(incentives)
    if not isfinite(total):
        raise ValueError("non-finite NashConv")
    return NPlayerNashConv(tuple(values), tuple(brs), tuple(incentives), total)
