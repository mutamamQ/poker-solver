"""Infoset-consistent best response and NashConv for finite games."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import isclose, isfinite

from .cfr import collect_infosets, expected_values
from .model import Action, CHANCE, GameState, InfoKey, Strategy, TERMINAL


@dataclass(frozen=True, slots=True)
class NashConvResult:
    values: tuple[float, float]
    best_response_values: tuple[float, float]
    incentives: tuple[float, float]
    nash_conv: float

    @property
    def exploitability(self) -> float:
        return self.nash_conv / 2.0


def validate_strategy(root: GameState, profile: Strategy, tolerance: float = 1e-10) -> None:
    infosets = collect_infosets(root)
    for key, (_, actions) in infosets.items():
        if key not in profile:
            raise ValueError(f"missing policy for information set {key!r}")
        policy = profile[key]
        if set(policy) != set(actions):
            raise ValueError(f"wrong actions for information set {key!r}")
        probabilities = tuple(policy[action] for action in actions)
        if any(not isfinite(p) or p < 0 for p in probabilities):
            raise ValueError(f"invalid probability at {key!r}")
        if not isclose(sum(probabilities), 1.0, abs_tol=tolerance):
            raise ValueError(f"probabilities do not sum to one at {key!r}")


def _value_against(
    state: GameState,
    responding: int,
    response: dict[InfoKey, Action],
    opponent: Strategy,
) -> float:
    player = state.current_player()
    if player == TERMINAL:
        return state.returns()[responding]
    if player == CHANCE:
        return sum(p * _value_against(state.child(a), responding, response, opponent) for a, p in state.chance_outcomes())
    key = state.information_state_key(player)
    if player == responding:
        return _value_against(state.child(response[key]), responding, response, opponent)
    policy = opponent[key]
    return sum(policy[a] * _value_against(state.child(a), responding, response, opponent) for a in state.legal_actions())


def _scalable_best_response(
    root: GameState,
    opponent_profile: Strategy,
    player: int,
) -> tuple[float, dict[InfoKey, Action]]:
    """Infoset-consistent best response via opponent+chance counterfactual reach.
    
    Supports finite perfect-recall trees where every history in an infoset has
    identical ordered legal actions. Fails closed on cycles, absent-minded dependencies,
    or action inconsistencies.
    """
    infosets = collect_infosets(root)
    owned = {key: actions for key, (owner, actions) in infosets.items() if owner == player}
    nodes: dict[InfoKey, list[tuple[GameState, float]]] = {key: [] for key in owned}
    dependencies: dict[InfoKey, set[InfoKey]] = {key: set() for key in owned}
    recursion_stack: set[int] = set()

    def validate_policy(key: InfoKey, actions: tuple[Action, ...]) -> dict[Action, float]:
        if key not in opponent_profile:
            raise ValueError(f"missing opponent policy for information set {key!r}")
        policy = opponent_profile[key]
        if set(policy) != set(actions):
            raise ValueError(f"wrong opponent actions for information set {key!r}")
        probabilities = tuple(policy[action] for action in actions)
        if any(not isfinite(p) or p < 0 for p in probabilities):
            raise ValueError(f"invalid opponent probability at {key!r}")
        if not isclose(sum(probabilities), 1.0, abs_tol=1e-10):
            raise ValueError(f"opponent probabilities do not sum to one at {key!r}")
        return policy

    def discover(state: GameState, counterfactual_reach: float, previous_owned: InfoKey | None) -> None:
        identity = id(state)
        if identity in recursion_stack:
            raise ValueError("cyclic game tree is not supported")
        recursion_stack.add(identity)
        try:
            current = state.current_player()
            if current == TERMINAL:
                return
            if current == CHANCE:
                outcomes = state.chance_outcomes()
                if any(not isfinite(probability) or probability < 0 for _, probability in outcomes):
                    raise ValueError("invalid chance probability")
                if not isclose(sum(probability for _, probability in outcomes), 1.0, abs_tol=1e-10):
                    raise ValueError("chance probabilities do not sum to one")
                for action, probability in outcomes:
                    discover(state.child(action), counterfactual_reach * probability, previous_owned)
                return

            actions = state.legal_actions()
            key = state.information_state_key(current)
            if current == player:
                nodes[key].append((state, counterfactual_reach))
                if previous_owned is not None:
                    if previous_owned == key:
                        raise ValueError("absent-minded information set is not supported")
                    dependencies[previous_owned].add(key)
                for action in actions:
                    discover(state.child(action), counterfactual_reach, key)
            else:
                policy = validate_policy(key, actions)
                for action in actions:
                    discover(state.child(action), counterfactual_reach * policy[action], previous_owned)
        finally:
            recursion_stack.remove(identity)

    discover(root, 1.0, None)

    # A postorder of the responder-infoset dependency graph puts descendants first.
    order: list[InfoKey] = []
    visiting: set[InfoKey] = set()
    visited: set[InfoKey] = set()

    def visit(key: InfoKey) -> None:
        if key in visiting:
            raise ValueError("cyclic responder information-set dependency")
        if key in visited:
            return
        visiting.add(key)
        for descendant in sorted(dependencies[key], key=repr):
            visit(descendant)
        visiting.remove(key)
        visited.add(key)
        order.append(key)

    for key in sorted(owned, key=repr):
        visit(key)

    best_actions: dict[InfoKey, Action] = {}

    def continuation(state: GameState) -> float:
        current = state.current_player()
        if current == TERMINAL:
            return state.returns()[player]
        if current == CHANCE:
            return sum(probability * continuation(state.child(action)) for action, probability in state.chance_outcomes())
        key = state.information_state_key(current)
        if current == player:
            if key not in best_actions:
                raise ValueError("unsupported responder infoset dependency")
            return continuation(state.child(best_actions[key]))
        actions = state.legal_actions()
        policy = validate_policy(key, actions)
        return sum(policy[action] * continuation(state.child(action)) for action in actions)

    for key in order:
        actions = owned[key]
        totals = []
        for action in actions:
            total = sum(reach * continuation(state.child(action)) for state, reach in nodes[key])
            totals.append(total)
        best_actions[key] = actions[max(range(len(actions)), key=totals.__getitem__)]

    return _value_against(root, player, best_actions, opponent_profile), best_actions


def exhaustive_best_response(root: GameState, opponent_profile: Strategy, player: int) -> tuple[float, dict[InfoKey, Action]]:
    """Compute a best response by enumerating pure strategies (tiny-game oracle)."""
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    
    infosets = collect_infosets(root)
    owned = sorted(
        ((key, actions) for key, (owner, actions) in infosets.items() if owner == player),
        key=lambda item: repr(item[0]),
    )
    keys = tuple(key for key, _ in owned)
    action_sets = tuple(actions for _, actions in owned)
    best_value = float("-inf")
    best_choice: dict[InfoKey, Action] = {}
    for choices in product(*action_sets):
        response = dict(zip(keys, choices, strict=True))
        value = _value_against(root, player, response, opponent_profile)
        if value > best_value:
            best_value = value
            best_choice = response
    if best_value == float("-inf"):
        best_value = _value_against(root, player, {}, opponent_profile)
    return best_value, best_choice


def best_response(root: GameState, opponent_profile: Strategy, player: int) -> tuple[float, dict[InfoKey, Action]]:
    """Compute an infoset-consistent best response on a supported finite tree."""
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    return _scalable_best_response(root, opponent_profile, player)


def nash_conv(root: GameState, profile: Strategy) -> NashConvResult:
    validate_strategy(root, profile)
    values = expected_values(root, profile)
    br0, _ = best_response(root, profile, 0)
    br1, _ = best_response(root, profile, 1)
    incentives = (br0 - values[0], br1 - values[1])
    total = sum(incentives)
    if total < -1e-9:
        raise ArithmeticError("negative NashConv indicates a best-response bug")
    return NashConvResult(values, (br0, br1), incentives, max(0.0, total))
