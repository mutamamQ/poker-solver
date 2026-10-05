"""Exact action values (Q) at a hero infoset under a solved profile.

Implements design report 01 section 3: counterfactual weighting (chance reach
times opponent reach; the hero's own reach is excluded), every player follows the
profile after the forced action, fail closed on missing/invalid policies or zero
reach.
"""

from __future__ import annotations

from math import fsum, isclose, isfinite
from types import MappingProxyType
from typing import Mapping

from ..model import CHANCE, TERMINAL, Action, GameState, InfoKey, Strategy

__all__ = ["action_values", "subtree_value", "checked_policy"]


def checked_policy(state: GameState, profile: Strategy, player: int) -> Mapping[Action, float]:
    """Return the validated profile policy at ``state`` (ValueError, never KeyError)."""
    key = state.information_state_key(player)
    try:
        policy = profile[key]
    except KeyError:
        raise ValueError(f"profile has no policy for information set {key!r}") from None
    actions = state.legal_actions()
    if not isinstance(policy, Mapping) or set(policy) != set(actions):
        raise ValueError(f"policy actions do not match legal actions at {key!r}")
    probabilities = [policy[a] for a in actions]
    for p in probabilities:
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not isfinite(p) or p < 0:
            raise ValueError(f"invalid probability {p!r} at {key!r}")
    if not isclose(fsum(probabilities), 1.0, abs_tol=1e-9):
        raise ValueError(f"policy does not sum to 1 at {key!r}")
    return policy


def _check_hero(hero: object) -> int:
    if isinstance(hero, bool) or not isinstance(hero, int) or hero < 0:
        raise ValueError("hero must be a non-negative integer seat (bool not allowed)")
    return hero


def subtree_value(state: GameState, profile: Strategy, hero: int) -> float:
    """Hero's expected payoff of ``state`` when every player follows ``profile``."""
    _check_hero(hero)
    player = state.current_player()
    if player == TERMINAL:
        value = state.returns()[hero]
        if not isfinite(value):
            raise ValueError("non-finite terminal return")
        return float(value)
    if player == CHANCE:
        return fsum(p * subtree_value(state.child(a), profile, hero) for a, p in state.chance_outcomes())
    policy = checked_policy(state, profile, player)
    return fsum(
        policy[a] * subtree_value(state.child(a), profile, hero)
        for a in state.legal_actions()
        if policy[a] > 0
    )


def action_values(
    root: GameState, profile: Strategy, hero: int, target_key: InfoKey
) -> tuple[MappingProxyType, float]:
    """Return ``(Q, mass)`` for hero's infoset ``target_key``.

    ``Q[a] = sum_h w(h) v(child(h, a)) / M`` with ``w(h)`` = chance reach x opponent
    reach and ``M = sum_h w(h)``.  Raises ``ValueError`` when the infoset is
    unreachable (zero counterfactual mass) or its histories disagree on actions.
    """
    _check_hero(hero)
    numerators: dict[Action, list[float]] = {}
    mass_terms: list[float] = []
    found: list[tuple[Action, ...]] = []

    def walk(state: GameState, weight: float) -> None:
        if weight == 0.0:
            return
        player = state.current_player()
        if player == TERMINAL:
            return
        if player == CHANCE:
            for action, probability in state.chance_outcomes():
                walk(state.child(action), weight * probability)
            return
        actions = state.legal_actions()
        key = state.information_state_key(player)
        if player == hero and key == target_key:
            if found and actions != found[0]:
                raise ValueError("inconsistent legal actions within the hero infoset")
            if not found:
                found.append(actions)
            mass_terms.append(weight)
            for action in actions:
                numerators.setdefault(action, []).append(
                    weight * subtree_value(state.child(action), profile, hero)
                )
            return  # perfect recall: the infoset is not revisited below
        if player == hero:
            for action in actions:
                walk(state.child(action), weight)
            return
        policy = checked_policy(state, profile, player)
        for action in actions:
            walk(state.child(action), weight * policy[action])

    walk(root, 1.0)
    mass = fsum(mass_terms)
    if not found or not isfinite(mass) or mass <= 0.0:
        raise ValueError("hero infoset has zero counterfactual reach")
    q = {action: fsum(numerators[action]) / mass for action in found[0]}
    if not all(isfinite(v) for v in q.values()):
        raise ValueError("non-finite action value")
    return MappingProxyType(q), mass
