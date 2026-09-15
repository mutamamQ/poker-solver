"""Exhaustive structural audit for finite game trees."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite
from typing import Hashable

from .model import CHANCE, GameState, InfoKey, TERMINAL


class GameValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AuditReport:
    nodes: int
    terminals: int
    chance_nodes: int
    decision_nodes: int
    infosets: int
    max_depth: int


def audit_game(root: GameState, max_nodes: int = 1_000_000) -> AuditReport:
    if max_nodes <= 0:
        raise ValueError("max_nodes must be positive")
    path: set[Hashable] = set()
    signatures: dict[InfoKey, tuple[int, tuple[object, ...]]] = {}
    counts = {"nodes": 0, "terminals": 0, "chance": 0, "decision": 0, "depth": 0}

    def state_id(state: GameState) -> Hashable:
        try:
            hash(state)
        except TypeError:
            return id(state)
        return state  # type: ignore[return-value]

    def walk(state: GameState, depth: int) -> None:
        counts["nodes"] += 1
        counts["depth"] = max(counts["depth"], depth)
        if counts["nodes"] > max_nodes:
            raise GameValidationError(f"tree exceeds max_nodes={max_nodes}")
        identity = state_id(state)
        if identity in path:
            raise GameValidationError("cycle detected")
        path.add(identity)
        try:
            player = state.current_player()
            actions1 = state.legal_actions()
            actions2 = state.legal_actions()
            if actions1 != actions2 or len(set(actions1)) != len(actions1):
                raise GameValidationError("legal actions are nondeterministic or duplicated")
            if player == TERMINAL:
                counts["terminals"] += 1
                if actions1 or state.chance_outcomes():
                    raise GameValidationError("terminal node exposes actions")
                returns = state.returns()
                if len(returns) != 2 or any(not isfinite(v) for v in returns) or not isclose(sum(returns), 0.0, abs_tol=1e-10):
                    raise GameValidationError("terminal returns are not finite zero-sum values")
                return
            if player == CHANCE:
                counts["chance"] += 1
                outcomes = state.chance_outcomes()
                if tuple(a for a, _ in outcomes) != actions1 or not outcomes:
                    raise GameValidationError("chance actions/outcomes disagree")
                probabilities = tuple(p for _, p in outcomes)
                if any(not isfinite(p) or p < 0 for p in probabilities) or not isclose(sum(probabilities), 1.0, abs_tol=1e-10):
                    raise GameValidationError("invalid chance probability mass")
                branches = outcomes
            elif player in (0, 1):
                counts["decision"] += 1
                if not actions1 or state.chance_outcomes():
                    raise GameValidationError("invalid decision-node action contract")
                key = state.information_state_key(player)
                signature = (player, actions1)
                if key in signatures and signatures[key] != signature:
                    raise GameValidationError("information set has inconsistent owner/actions")
                signatures[key] = signature
                branches = tuple((action, 1.0) for action in actions1)
            else:
                raise GameValidationError(f"invalid current player {player}")
            for action, _ in branches:
                child = state.child(action)
                walk(child, depth + 1)
        finally:
            path.remove(identity)

    walk(root, 0)
    return AuditReport(
        counts["nodes"], counts["terminals"], counts["chance"],
        counts["decision"], len(signatures), counts["depth"],
    )
