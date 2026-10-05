"""Solver adapter: turn a :class:`PracticeSpot` into a runtime solve and a :class:`SolvedSpot`.

Every probability and action value returned here is computed by the real solver
(``cfr.CFRSolver`` / the ``allstreet.solve_allstreet_postflop`` pipeline /
``nplayer.NPlayerCFRSolver`` over ``nplayer_preflop`` / ``cfr.CFRSolver`` over a
``multistreet`` turn root) when the spot is solved, or read back from a cache keyed
by the spot's full ``params_hash``.  Nothing is hardcoded and nothing is post-edited.

Preflop leaves that reach a showdown are valued by a runtime equity table: for each
compatible private deal, ``equity_samples`` boards are drawn with a seed derived
(sha256) from the deal itself and evaluated with ``evaluator.evaluate_seven``; the
table is then supplied to the solver as a ``terminal-table`` continuation.
"""

from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from collections import Counter
from dataclasses import dataclass, fields, is_dataclass
from fractions import Fraction
from importlib import metadata
from types import MappingProxyType
from typing import Any, Callable, Hashable, Mapping, MutableMapping

from ..allstreet import AllStreetPostflopConfig, create_allstreet_root
from ..api import complete_strategy
from ..mccfr import MCCFRSolver
from ..best_response import nash_conv
from ..bounded_tree import validate_bounded_tree
from ..cfr import CFRSolver
from ..evaluator import evaluate_seven
from ..game_structure import ForcedPost, award_pot_layers, build_pot_layers
from ..kuhn import kuhn_root
from ..model import CHANCE, TERMINAL, Action, GameState, Strategy
from ..multistreet import MultiStreetConfig, create_root as create_multistreet_root
from ..nplayer_preflop import (
    NPlayerPreflopConfig,
    NPlayerPreflopContinuation,
    NPlayerPreflopSizingRule,
    create_nplayer_preflop_root,
    enumerate_nplayer_preflop_deals,
)
from ..preflop import WeightedCombo as PreflopCombo
from ..river import RiverConfig, river_root
from .evaluate import action_values
from .nplayer_metrics import FlatNPlayerCFR, FlatTree, nash_conv_nplayer
from .models import PREFLOP_BLINDS, PREFLOP_POSITIONS, PracticeSpot, SolvedSpot, SolveProvenance, format_hand

__all__ = [
    "SolverAdapter",
    "solve_spot",
    "solver_version",
    "locate_decision",
    "HeroDecision",
    "ENTRYPOINTS",
    "CachedState",
    "portable_key",
    "preflop_config",
    "pseudo_raise_aliases",
    "merge_pseudo_raises",
    "optimal_action",
]

ENTRYPOINTS = MappingProxyType(
    {
        "kuhn": "poker_solver.kuhn.kuhn_root+cfr.CFRSolver.train",
        "river": "poker_solver.river.river_root+cfr.CFRSolver.train",
        "allstreet": (
            "poker_solver.allstreet.create_allstreet_root+cfr.CFRSolver.train"
            " (solve_allstreet_postflop pipeline: validate_bounded_tree, complete_strategy, nash_conv)"
        ),
        "nplayer-preflop": (
            "poker_solver.nplayer_preflop.create_nplayer_preflop_root"
            "+practice.nplayer_metrics.FlatNPlayerCFR.train (bit-identical to nplayer.NPlayerCFRSolver;"
            " terminal-table: evaluator.evaluate_seven sampled equity; NashConv: nplayer_metrics.nash_conv_nplayer)"
        ),
        "multistreet": "poker_solver.multistreet.create_root(turn)+cfr.CFRSolver.train",
    }
)
_TRAIN_CHUNK = 25
_PREFLOP_VERSION = "nplayer-preflop-v1"
_PREFLOP_PROVENANCE = "practice runtime sampled showdown equity (evaluator.evaluate_seven)"
_MAX_DEPTH = 512


# --------------------------------------------------------------------------- memoized state


class CachedState:
    """Transparent memoizing proxy over an immutable solver ``GameState``.

    The wrapped game states are frozen dataclasses whose methods are pure, so caching
    children, legal actions, chance outcomes, infoset keys and returns changes no
    value -- it only avoids re-deriving (and re-validating) the same immutable states
    on every CFR iteration.  Any other attribute is delegated to the wrapped state.
    """

    __slots__ = ("state", "_player", "_children", "_actions", "_outcomes", "_keys", "_returns")

    def __init__(self, state: Any):
        self.state = state
        self._player = state.current_player()
        self._children: dict[Action, CachedState] = {}
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

    def child(self, action: Action) -> "CachedState":
        node = self._children.get(action)
        if node is None:
            node = self._children[action] = CachedState(self.state.child(action))
        return node

    def information_state_key(self, player: int) -> Hashable:
        key = self._keys.get(player)
        if key is None:
            key = self._keys[player] = self.state.information_state_key(player)
        return key

    def returns(self) -> tuple[float, ...]:
        if self._returns is None:
            self._returns = tuple(self.state.returns())
        return self._returns


# --------------------------------------------------------------------------- preflop game build


def _deal_seed(deal: tuple, samples: int) -> int:
    text = json.dumps([[list(cards) for cards in deal], samples], separators=(",", ":"))
    return int(hashlib.sha256(text.encode("ascii")).hexdigest()[:16], 16)


def _rank_patterns(deal: tuple, samples: int) -> Counter:
    """Counter of per-seat hand-rank tuples over ``samples`` seeded random boards."""
    dead = {card for cards in deal for card in cards}
    deck = [card for card in range(52) if card not in dead]
    rng = random.Random(_deal_seed(deal, samples))
    patterns: Counter = Counter()
    for _ in range(samples):
        board = tuple(rng.sample(deck, 5))
        ranks = tuple(evaluate_seven(tuple(cards) + board) for cards in deal)
        order = sorted(set(ranks))
        patterns[tuple(order.index(rank) for rank in ranks)] += 1
    return patterns


def _showdown_utilities(state: Any, patterns: Counter, samples: int, stacks: tuple[int, ...]) -> tuple[Fraction, ...]:
    """Exact expected chip utilities of a closed multi-way leaf under sampled boards."""
    n = len(stacks)
    folded = frozenset(seat for seat, is_folded in enumerate(state.folded) if is_folded)
    layers = build_pot_layers(state.total_contributed, folded=folded)
    totals = [0] * n
    for ranks, count in patterns.items():
        winners = tuple(
            frozenset(s for s in layer.eligible if ranks[s] == max(ranks[e] for e in layer.eligible))
            for layer in layers
        )
        awards = award_pot_layers(layers, winners_by_layer=winners, odd_chip_order=tuple(range(n)))
        awards = tuple(awards) + (0,) * (n - len(awards))
        for seat in range(n):
            totals[seat] += count * awards[seat]
    values = tuple(Fraction(totals[s], samples) + state.remaining[s] - stacks[s] for s in range(n))
    if sum(values) != 0:
        raise ValueError("preflop showdown utilities are not zero-sum")
    return values


def preflop_config(spot: PracticeSpot) -> NPlayerPreflopConfig:
    """Build the solver config for a ``nplayer-preflop`` spot (equity table computed now)."""
    n = len(spot.stacks)
    small, big = PREFLOP_BLINDS
    sb, bb = (0, 1) if n == 2 else (1, 2)
    posts = (ForcedPost(sb, "small-blind", small), ForcedPost(bb, "big-blind", big))
    ranges = tuple(
        tuple(PreflopCombo(c.cards, Fraction(str(c.weight))) for c in seat_range) for seat_range in spot.ranges
    )
    expressions = tuple({"unit": "big-blinds", "value": size / big} for size in spot.bet_sizes)
    rules = tuple(
        NPlayerPreflopSizingRule(position, 0, callers, "NA", expressions)
        for position in PREFLOP_POSITIONS[spot.game_type]
        for callers in range(n)
    )
    extra = spot.backend_extra
    max_deals = 1
    for seat_range in ranges:
        max_deals *= len(seat_range)

    def build(continuation: NPlayerPreflopContinuation) -> NPlayerPreflopConfig:
        return NPlayerPreflopConfig(
            version=_PREFLOP_VERSION,
            num_players=n,
            button=0,
            starting_stacks=spot.stacks,
            forced_posts=posts,
            straddle_variant="none",
            ranges=ranges,
            sizing_rules=rules,
            max_raises=extra["max_raises"],
            max_deals=max_deals,
            max_nodes=extra["max_nodes"],
            short_all_in_reopens=False,
            continuation=continuation,
        )

    # Pass 1: the betting tree does not depend on the private cards, so walking it
    # under one representative deal yields every closed multi-way leaf (history plus
    # settled chips).  A structural placeholder continuation is used only for this
    # walk; settlement chip amounts do not depend on it.
    bare = build(NPlayerPreflopContinuation("terminal-table", "structure-only", "derived", {}, {}, ()))
    deals = tuple(deal for deal, _ in enumerate_nplayer_preflop_deals(bare))
    placeholder = NPlayerPreflopContinuation(
        "showdown-ranks", "structure-only", "derived", {}, {deal: (0,) * n for deal in deals}, tuple(range(n))
    )
    probe_root = create_nplayer_preflop_root(build(placeholder))
    leaves: list = []
    visited = 0

    def walk(state: Any) -> None:
        nonlocal visited
        visited += 1
        if visited > extra["max_nodes"]:
            raise ValueError("preflop tree exceeds max_nodes")
        player = state.current_player()
        if player == TERMINAL:
            if sum(not f for f in state.folded) > 1:
                leaves.append(state)
            return
        for action in state.legal_actions():
            walk(state.child(action))

    walk(probe_root.child(probe_root.chance_outcomes()[0][0]))
    samples = extra["equity_samples"]
    table: dict = {}
    for deal in deals:
        patterns = _rank_patterns(deal, samples)
        for leaf in leaves:
            table[(deal, leaf.history)] = _showdown_utilities(leaf, patterns, samples, spot.stacks)
    return build(NPlayerPreflopContinuation("terminal-table", _PREFLOP_PROVENANCE, "derived", table, {}, ()))


def solver_version() -> str:
    """Installed ``poker-solver`` package version, or ``'unknown'``."""
    try:
        return metadata.version("poker-solver")
    except metadata.PackageNotFoundError:
        return "unknown"


@dataclass(frozen=True, slots=True)
class HeroDecision:
    """Hero's decision node, resolved by walking the real solver tree."""

    info_key: Hashable
    legal_actions: tuple[Action, ...]
    pot_at_decision: float


# --------------------------------------------------------------------------- portable keys


def portable_key(value: Any) -> Any:
    """Solver infoset key re-expressed with tuples / primitives / ``Action`` only.

    ``SolvedSpot.info_key`` is descriptive (lookups use the raw solver key); some
    backends embed config dataclasses (``ForcedPost``, seat-labelled actions) in their
    keys, which are mapped here to ``(type name, *fields)`` tuples so the solved spot
    stays JSON-encodable for the persistent cache.
    """
    if value is None or isinstance(value, (bool, int, float, str, Fraction, Action)):
        return value
    if isinstance(value, (tuple, list)):
        return tuple(portable_key(item) for item in value)
    if isinstance(value, Mapping):
        return tuple((portable_key(k), portable_key(v)) for k, v in value.items())
    if is_dataclass(value):
        return (type(value).__name__,) + tuple(portable_key(getattr(value, f.name)) for f in fields(value))
    raise ValueError(f"unsupported infoset key component {type(value).__name__}")


# --------------------------------------------------------------------------- tree walk


def _private_hand(state: Any, seat: int) -> Any:
    """Hero private holding at a dealt state (Kuhn symbol or sorted card pair)."""
    deal = getattr(state, "private_deal", None)
    if deal is None:
        deal = getattr(state, "deal", None)
    if deal is None:
        raise ValueError("dealt state exposes no private deal")
    own = deal[seat]
    return own if isinstance(own, str) else tuple(sorted(own))


def _pot_at(state: Any, backend: str) -> float:
    if backend == "kuhn":
        return 2.0 + sum(1.0 for a in state.history if a.kind in ("bet", "call"))
    if backend == "river":
        return float(state.config.pot) + sum(float(a.amount) for a in state.history if a.kind == "bet")
    if backend == "nplayer-preflop":
        return float(state.pot)  # pot already includes current-street commitments
    return float(state.pot + sum(state.committed))


def locate_decision(root: GameState, spot: PracticeSpot, hand: Any, backend: str) -> HeroDecision | None:
    """Walk root deals matching ``hand`` and replay ``spot.action_history``.

    Returns ``None`` when no compatible deal reaches the node (hand blocked by every
    villain combo).  Raises ``ValueError`` for illegal histories, a wrong actor or
    inconsistent infosets.  Never parses ``str(InfoKey)``.
    """
    if root.current_player() != CHANCE:
        raise ValueError("solver root must be a chance (deal) node")
    hero = spot.hero_seat
    found: list[HeroDecision] = []
    for deal_action, probability in root.chance_outcomes():
        if probability <= 0:
            continue
        state = root.child(deal_action)
        if _private_hand(state, hero) != hand:
            continue
        for action in spot.action_history:
            actor = state.current_player()
            if actor in (CHANCE, TERMINAL):
                raise ValueError(f"action_history leaves the decision tree before {action!r}")
            if action not in state.legal_actions():
                raise ValueError(f"illegal action {action!r} in action_history")
            state = state.child(action)
        if state.current_player() != hero:
            raise ValueError("hero is not the acting player at the end of action_history")
        decision = HeroDecision(state.information_state_key(hero), state.legal_actions(), _pot_at(state, backend))
        if found and decision != found[0]:
            raise ValueError("compatible deals disagree on the hero infoset")
        if not found:
            found.append(decision)
    return found[0] if found else None


# --------------------------------------------------------------------------- user-facing actions


def pseudo_raise_aliases(actions: tuple[Action, ...]) -> dict[Action, Action]:
    """``{RAISE(t): CALL(t)}`` for raises whose target equals the call target.

    ``multistreet`` (and ``allstreet``, which builds on it) lists a wager target equal
    to the opponent's all-in as ``RAISE`` even when it only matches the bet; such an
    action is a call, not a raise, and must never be offered to a user as a raise.
    """
    calls = [a for a in actions if a.kind == "CALL"]
    if not calls:
        return {}
    call = calls[0]
    return {a: call for a in actions if a.kind == "RAISE" and a.amount == call.amount}


def optimal_action(
    actions: tuple[Action, ...], strategy: Mapping[Action, float], q: Mapping[Action, float]
) -> Action:
    """Displayed "optimal" action, consistent with Q-based grading.

    The highest-Q action among those the solved strategy actually plays (probability
    > 0); ties go to the higher probability, then legal-action order.  At an exact
    equilibrium every supported action has the same Q, so this is a strategy action;
    before convergence it is the supported action that grading scores best, never an
    action the solver does not play.
    """
    support = [a for a in actions if strategy[a] > 0.0] or list(actions)
    return max(support, key=lambda a: (q[a], strategy[a], -actions.index(a)))


def merge_pseudo_raises(policy: dict[Action, float], aliases: Mapping[Action, Action]) -> dict[Action, float]:
    """Fold the probability of each pseudo-raise into the CALL it duplicates."""
    if not aliases:
        return policy
    merged = {a: p for a, p in policy.items() if a not in aliases}
    for alias, call in aliases.items():
        merged[call] += policy[alias]
    return merged


# --------------------------------------------------------------------------- adapter


class SolverAdapter:
    """Routes spots to solver backends and caches results by ``params_hash`` (thread-safe)."""

    def __init__(self, cache: MutableMapping[str, SolvedSpot] | None = None, timeout_s: float = 60.0):
        if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)) or not timeout_s > 0:
            raise ValueError("timeout_s must be a positive number")
        self._cache: MutableMapping[str, SolvedSpot] = {} if cache is None else cache
        self._lock = threading.Lock()
        self.timeout_s = float(timeout_s)
        self.solve_count = 0
        self._inflight: dict[str, list] = {}

    def cached(self, spot: PracticeSpot) -> SolvedSpot | None:
        """Cached result for this exact ``params_hash``, if any."""
        with self._lock:
            return self._cache.get(spot.params_hash())

    def solve(self, spot: PracticeSpot) -> SolvedSpot:
        """Solve ``spot`` (or return the cached solve) and evaluate the hero decision."""
        if not isinstance(spot, PracticeSpot):
            raise ValueError("solve() requires a PracticeSpot")
        key = spot.params_hash()
        with self._lock:
            hit = self._cache.get(key)
            if hit is not None:
                return hit
            flight = self._inflight.get(key)
            if flight is None:
                flight = self._inflight[key] = [threading.Lock(), 0, None]
            flight[1] += 1
        # Single flight: concurrent cold requests for one params_hash serialize on a
        # per-key lock; followers find the leader's result in the cache instead of
        # solving again (if the leader failed, the next one solves itself).
        try:
            with flight[0]:
                with self._lock:
                    hit = self._cache.get(key)
                if hit is None:
                    hit = flight[2]  # leader's result even if the cache did not keep it
                if hit is not None:
                    return hit
                flight[2] = self._solve_cold(spot, key)
                return flight[2]
        finally:
            with self._lock:
                flight[1] -= 1
                if flight[1] == 0 and self._inflight.get(key) is flight:
                    del self._inflight[key]

    def _solve_cold(self, spot: PracticeSpot, key: str) -> SolvedSpot:
        router: dict[str, Callable[[PracticeSpot], SolvedSpot]] = {
            "kuhn": self._solve_kuhn,
            "river": self._solve_river,
            "allstreet": self._solve_allstreet,
            "nplayer-preflop": self._solve_preflop,
            "multistreet": self._solve_multistreet,
        }
        handler = router.get(spot.backend)
        if handler is None:
            raise ValueError(f"backend {spot.backend!r} is not routed by the practice adapter (PARTIAL)")
        solved = handler(spot)
        with self._lock:
            self._cache.setdefault(key, solved)
            self.solve_count += 1
            # A bounded / write-failing cache may not retain the entry: return the solve.
            return self._cache.get(key) or solved

    # -- backends --------------------------------------------------------------------

    def _train_cfr(self, root: GameState, spot: PracticeSpot, start: float, solver: Any = None) -> Strategy:
        if spot.solve.algorithm != "vanilla-cfr":
            raise ValueError(f"backend {spot.backend} supports only vanilla-cfr")
        if solver is None:
            solver = CFRSolver(root)
        return self._train_chunked(solver, spot, start)

    def _train_chunked(self, solver: Any, spot: PracticeSpot, start: float) -> Strategy:
        remaining = spot.solve.iterations
        profile: Strategy = {}
        while remaining > 0:
            step = min(_TRAIN_CHUNK, remaining)
            profile = solver.train(step)
            remaining -= step
            if remaining and time.perf_counter() - start > self.timeout_s:
                raise ValueError(
                    f"solve exceeded the {self.timeout_s:g}s budget after {solver.iterations} "
                    f"of {spot.solve.iterations} iterations; no partial result is returned"
                )
        return profile

    def _solve_kuhn(self, spot: PracticeSpot) -> SolvedSpot:
        start = time.perf_counter()
        root = kuhn_root()
        profile = self._train_cfr(root, spot, start)
        conv = nash_conv(root, profile).nash_conv
        hands = tuple(dict.fromkeys(_private_hand(root.child(a), spot.hero_seat) for a, _ in root.chance_outcomes()))
        return self._finish(spot, root, profile, conv, start, spot.backend_extra["kuhn_card"], hands, str)

    def _solve_river(self, spot: PracticeSpot) -> SolvedSpot:
        start = time.perf_counter()
        config = RiverConfig(
            board=spot.board,  # type: ignore[arg-type]
            pot=spot.pot,
            stack=spot.stacks[0],
            bet=spot.bet_sizes[0],
            range0=spot.ranges[0],
            range1=spot.ranges[1],
        )
        root = river_root(config)
        profile = self._train_cfr(root, spot, start)
        conv = nash_conv(root, profile).nash_conv
        hands = tuple(c.cards for c in spot.ranges[spot.hero_seat])
        return self._finish(spot, root, profile, conv, start, spot.hero_hand, hands, format_hand)

    def _solve_allstreet(self, spot: PracticeSpot) -> SolvedSpot:
        start = time.perf_counter()
        extra = spot.backend_extra
        config = AllStreetPostflopConfig(
            version="allstreet-postflop-v1",
            starting_board=spot.board,  # type: ignore[arg-type]
            initial_dead_pot=int(spot.pot),
            effective_stack=spot.stacks[0],
            player0_combos=spot.ranges[0],
            player1_combos=spot.ranges[1],
            allowed_runouts=extra["allowed_runouts"],
            betting_mode=extra["betting_mode"],
            wager_targets=spot.bet_sizes,
            max_nodes=extra["max_nodes"],
            max_depth=extra["max_depth"],
        )
        # Same steps as ``allstreet.solve_allstreet_postflop`` (bounded-tree validation,
        # CFRSolver / MCCFRSolver training, ``api.complete_strategy``, NashConv) run over
        # a memoized root, which yields an identical profile in a fraction of the time.
        root = CachedState(create_allstreet_root(config))
        validate_bounded_tree(root, max_nodes=config.max_nodes, max_depth=config.max_depth)
        if spot.solve.algorithm == "vanilla-cfr":
            profile = self._train_cfr(root, spot, start)
        else:
            # Chunked so the budget is enforced during training; MCCFRSolver keeps its RNG
            # and regrets across train() calls, so chunking does not change the result.
            profile = self._train_chunked(MCCFRSolver(root, spot.solve.seed), spot, start)
        profile = complete_strategy(root, profile)
        conv = nash_conv(root, profile).nash_conv
        hands = tuple(c.cards for c in spot.ranges[spot.hero_seat])
        return self._finish(spot, root, profile, conv, start, spot.hero_hand, hands, format_hand)

    def _solve_preflop(self, spot: PracticeSpot) -> SolvedSpot:
        start = time.perf_counter()
        config = preflop_config(spot)
        root = CachedState(create_nplayer_preflop_root(config))
        max_depth = 2 + config.num_players + config.max_raises * (config.num_players - 1)
        # The tree is compiled once into flat arrays; FlatNPlayerCFR performs exactly the
        # floating-point operations of nplayer.NPlayerCFRSolver (one walk for all players
        # instead of one per player), so the profile is bit-identical, only faster.
        tree = FlatTree(root, max_nodes=config.max_nodes, max_depth=max_depth)
        profile = self._train_cfr(root, spot, start, FlatNPlayerCFR(tree))
        if config.num_players == 2:
            conv = nash_conv(root, profile).nash_conv
        else:
            # n-player NashConv: sum over seats of (exact best response - profile value).
            conv = nash_conv_nplayer(tree, profile).nash_conv
        decision = locate_decision(root, spot, spot.hero_hand, spot.backend)
        if decision is not None:
            sizes = {a.amount for a in decision.legal_actions if a.kind == "RAISE"}
            unopened = not any(a.kind == "RAISE" for a in spot.action_history)
            if unopened and not set(spot.bet_sizes) <= sizes:
                raise ValueError("solver tree does not offer the declared open size")
        hands = tuple(c.cards for c in spot.ranges[spot.hero_seat])
        return self._finish(spot, root, profile, conv, start, spot.hero_hand, hands, format_hand)

    def _solve_multistreet(self, spot: PracticeSpot) -> SolvedSpot:
        start = time.perf_counter()
        extra = spot.backend_extra
        config = MultiStreetConfig(
            version="multistreet-v1",
            starting_street="turn",
            starting_board=spot.board,
            initial_dead_pot=int(spot.pot),
            effective_stack=spot.stacks[0],
            player0_combos=spot.ranges[0],
            player1_combos=spot.ranges[1],
            allowed_runouts=extra["allowed_runouts"],
            betting_mode=extra["betting_mode"],
            wager_targets=spot.bet_sizes,
            river_betting=True,
        )
        root = CachedState(create_multistreet_root(config))
        validate_bounded_tree(root, max_nodes=extra["max_nodes"], max_depth=extra["max_depth"])
        profile = self._train_cfr(root, spot, start)
        conv = nash_conv(root, profile).nash_conv
        hands = tuple(c.cards for c in spot.ranges[spot.hero_seat])
        return self._finish(spot, root, profile, conv, start, spot.hero_hand, hands, format_hand)

    # -- evaluation ------------------------------------------------------------------

    def _finish(
        self,
        spot: PracticeSpot,
        root: GameState,
        profile: Strategy,
        conv: float | None,
        start: float,
        hero_hand: Any,
        range_hands: tuple,
        label: Callable[[Any], str],
    ) -> SolvedSpot:
        decision = locate_decision(root, spot, hero_hand, spot.backend)
        if decision is None:
            raise ValueError("hero hand has no compatible deal reaching the decision")
        raw_q, _mass = action_values(root, profile, spot.hero_seat, decision.info_key)
        aliases = pseudo_raise_aliases(decision.legal_actions)
        actions = tuple(a for a in decision.legal_actions if a not in aliases)
        for alias, call in aliases.items():
            # Facing an all-in, the game tree offers RAISE(target == call target): it moves
            # exactly the chips a CALL moves, so its solved value must equal CALL's.  It is
            # shown to the user as the CALL it really is (probability merged); the solver,
            # the profile and NashConv are untouched.  Fail closed if the values differ.
            if abs(raw_q[alias] - raw_q[call]) > 1e-9 * max(1.0, abs(raw_q[call])):
                raise ValueError(f"{alias!r} is not value-equivalent to {call!r}; refusing to merge")
        strategy = merge_pseudo_raises(self._policy_at(profile, decision), aliases)
        q = {a: raw_q[a] for a in actions}
        range_strategy: dict[str, Any] = {}
        for hand in range_hands:
            node = locate_decision(root, spot, hand, spot.backend)
            if node is not None:  # hands blocked by every villain combo never reach the node
                range_strategy[label(hand)] = merge_pseudo_raises(
                    self._policy_at(profile, node), pseudo_raise_aliases(node.legal_actions)
                )
        optimal = optimal_action(actions, strategy, q)
        size = optimal.amount if optimal.kind.lower() in ("bet", "raise") and optimal.amount > 0 else None
        provenance = SolveProvenance(
            backend=spot.backend,
            entrypoint=ENTRYPOINTS[spot.backend],
            params=spot.canonical(),
            params_hash=spot.params_hash(),
            algorithm=spot.solve.algorithm,
            iterations=spot.solve.iterations,
            seed=spot.solve.seed,
            nash_conv=None if conv is None else float(conv),
            wall_time_s=time.perf_counter() - start,
            solver_version=solver_version(),
        )
        return SolvedSpot(
            spot=spot,
            provenance=provenance,
            legal_actions=actions,
            pot_at_decision=decision.pot_at_decision,
            info_key=portable_key(decision.info_key),
            strategy=strategy,
            action_values=q,
            range_strategy=range_strategy,
            optimal_action=optimal,
            optimal_size=size,
        )

    @staticmethod
    def _policy_at(profile: Strategy, decision: HeroDecision) -> dict[Action, float]:
        try:
            policy = profile[decision.info_key]
        except KeyError:
            raise ValueError("solved profile has no policy at the hero infoset") from None
        if set(policy) != set(decision.legal_actions):
            raise ValueError("solved policy does not match the legal actions")
        return {a: float(policy[a]) for a in decision.legal_actions}


_DEFAULT_ADAPTER = SolverAdapter()


def solve_spot(spot: PracticeSpot) -> SolvedSpot:
    """Solve with the module-level default adapter (shared in-memory cache)."""
    return _DEFAULT_ADAPTER.solve(spot)
