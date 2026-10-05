"""Solver adapter: turn a :class:`PracticeSpot` into a runtime solve and a :class:`SolvedSpot`.

Every probability and action value returned here is computed by the real solver
(``cfr.CFRSolver`` / ``allstreet.solve_allstreet_postflop``) when the spot is
solved, or read back from an in-memory cache keyed by the spot's full
``params_hash``.  Nothing is hardcoded and nothing is post-edited.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from importlib import metadata
from types import MappingProxyType
from typing import Any, Callable, Hashable, MutableMapping

from ..allstreet import AllStreetPostflopConfig, create_allstreet_root, solve_allstreet_postflop
from ..best_response import nash_conv
from ..cfr import CFRSolver
from ..kuhn import kuhn_root
from ..model import CHANCE, TERMINAL, Action, GameState, Strategy
from ..river import RiverConfig, river_root
from .evaluate import action_values
from .models import PracticeSpot, SolvedSpot, SolveProvenance, format_hand

__all__ = ["SolverAdapter", "solve_spot", "solver_version", "locate_decision", "HeroDecision", "ENTRYPOINTS"]

ENTRYPOINTS = MappingProxyType(
    {
        "kuhn": "poker_solver.kuhn.kuhn_root+cfr.CFRSolver.train",
        "river": "poker_solver.river.river_root+cfr.CFRSolver.train",
        "allstreet": "poker_solver.allstreet.solve_allstreet_postflop",
    }
)
_TRAIN_CHUNK = 25


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
        router: dict[str, Callable[[PracticeSpot], SolvedSpot]] = {
            "kuhn": self._solve_kuhn,
            "river": self._solve_river,
            "allstreet": self._solve_allstreet,
        }
        handler = router.get(spot.backend)
        if handler is None:
            raise ValueError(f"backend {spot.backend!r} is not routed by the practice adapter (PARTIAL)")
        solved = handler(spot)
        with self._lock:
            self._cache.setdefault(key, solved)
            self.solve_count += 1
            return self._cache[key]

    # -- backends --------------------------------------------------------------------

    def _train_cfr(self, root: GameState, spot: PracticeSpot, start: float) -> Strategy:
        if spot.solve.algorithm != "vanilla-cfr":
            raise ValueError(f"backend {spot.backend} supports only vanilla-cfr")
        solver = CFRSolver(root)
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
        result = solve_allstreet_postflop(
            config, algorithm=spot.solve.algorithm, iterations=spot.solve.iterations, seed=spot.solve.seed
        )
        if time.perf_counter() - start > self.timeout_s:
            raise ValueError(f"allstreet solve exceeded the {self.timeout_s:g}s budget")
        root = create_allstreet_root(config)
        hands = tuple(c.cards for c in spot.ranges[spot.hero_seat])
        return self._finish(spot, root, result.strategy, result.nash_conv, start, spot.hero_hand, hands, format_hand)

    # -- evaluation ------------------------------------------------------------------

    def _finish(
        self,
        spot: PracticeSpot,
        root: GameState,
        profile: Strategy,
        conv: float,
        start: float,
        hero_hand: Any,
        range_hands: tuple,
        label: Callable[[Any], str],
    ) -> SolvedSpot:
        decision = locate_decision(root, spot, hero_hand, spot.backend)
        if decision is None:
            raise ValueError("hero hand has no compatible deal reaching the decision")
        strategy = self._policy_at(profile, decision)
        q, _mass = action_values(root, profile, spot.hero_seat, decision.info_key)
        range_strategy: dict[str, Any] = {}
        for hand in range_hands:
            node = locate_decision(root, spot, hand, spot.backend)
            if node is not None:  # hands blocked by every villain combo never reach the node
                range_strategy[label(hand)] = self._policy_at(profile, node)
        actions = decision.legal_actions
        best_p = max(strategy[a] for a in actions)
        optimal = next(a for a in actions if strategy[a] == best_p)
        size = optimal.amount if optimal.kind.lower() in ("bet", "raise") and optimal.amount > 0 else None
        provenance = SolveProvenance(
            backend=spot.backend,
            entrypoint=ENTRYPOINTS[spot.backend],
            params=spot.canonical(),
            params_hash=spot.params_hash(),
            algorithm=spot.solve.algorithm,
            iterations=spot.solve.iterations,
            seed=spot.solve.seed,
            nash_conv=float(conv),
            wall_time_s=time.perf_counter() - start,
            solver_version=solver_version(),
        )
        return SolvedSpot(
            spot=spot,
            provenance=provenance,
            legal_actions=actions,
            pot_at_decision=decision.pot_at_decision,
            info_key=decision.info_key,
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
