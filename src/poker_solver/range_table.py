"""Reach-weighted per-combo strategy and action-EV tables.

Tables are exact with respect to a caller-supplied complete strategy and the
configured finite chance tree.  They do not claim population or GTO provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Hashable, Mapping

from .model import Action, CHANCE, TERMINAL
from .nplayer import collect_nplayer_infosets


@dataclass(frozen=True, slots=True)
class RangeTableRow:
    combo: tuple[int, int]
    source_weight: object
    conditional_reach: float
    range_probability: float
    info_key: Hashable
    actions: tuple[Action, ...]
    action_probabilities: Mapping[Action, float]
    action_evs: Mapping[Action, float]
    mixed_ev: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_probabilities", MappingProxyType(dict(self.action_probabilities)))
        object.__setattr__(self, "action_evs", MappingProxyType(dict(self.action_evs)))


@dataclass(frozen=True, slots=True)
class RangeTable:
    seat: int
    rows: tuple[RangeTableRow, ...]
    action_frequencies: Mapping[Action, float]
    mixed_ev: float
    provenance: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_frequencies", MappingProxyType(dict(self.action_frequencies)))


def _validate_strategy(root, strategy: Mapping[Hashable, Mapping[Action, float]]):
    if not isinstance(strategy, Mapping):
        raise ValueError("strategy must be a mapping")
    max_nodes = getattr(getattr(root, "config", None), "max_nodes", 100_000)
    infosets = collect_nplayer_infosets(root, max_nodes=max(100_000, max_nodes))
    if set(strategy) != set(infosets):
        raise ValueError("strategy keys must exactly match reachable information sets")
    copied = {}
    for key, (_, actions) in infosets.items():
        policy = strategy[key]
        if not isinstance(policy, Mapping) or set(policy) != set(actions):
            raise ValueError("strategy actions must exactly match legal actions")
        values = {}
        for action in actions:
            probability = policy[action]
            if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not isfinite(float(probability)) or probability < 0:
                raise ValueError("strategy probabilities must be finite non-negative numbers")
            values[action] = float(probability)
        if abs(sum(values.values()) - 1.0) > 1e-12:
            raise ValueError("strategy probabilities must sum to one")
        copied[key] = MappingProxyType(values)
    return MappingProxyType(copied)


def _value(state, strategy, seat: int) -> float:
    player = state.current_player()
    if player == TERMINAL:
        returns = state.returns()
        if seat >= len(returns):
            raise ValueError("terminal utility vector omits requested seat")
        value = returns[seat]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
            raise ValueError("terminal utilities must be finite numbers")
        return float(value)
    if player == CHANCE:
        outcomes = state.chance_outcomes()
        if not outcomes:
            raise ValueError("chance node must have outcomes")
        return sum(float(probability) * _value(state.child(action), strategy, seat) for action, probability in outcomes)
    actions = state.legal_actions()
    key = state.information_state_key(player)
    policy = strategy[key]
    return sum(policy[action] * _value(state.child(action), strategy, seat) for action in actions)


def _source_weight(root, seat: int, combo: tuple[int, int]):
    config = getattr(root, "config", None)
    ranges = getattr(config, "ranges", None)
    if ranges is None or seat >= len(ranges):
        return None
    for weighted in ranges[seat]:
        if getattr(weighted, "cards", None) == combo:
            return getattr(weighted, "weight", None)
    return None


def build_range_table(
    root,
    strategy: Mapping[Hashable, Mapping[Action, float]],
    *,
    seat: int,
    provenance: str = "caller-supplied finite strategy",
) -> RangeTable:
    """Build a root-public-node table grouped by the requested private combo."""
    if isinstance(seat, bool) or not isinstance(seat, int):
        raise ValueError("seat must be an integer")
    player_count = root.num_players() if hasattr(root, "num_players") else 2
    if not 0 <= seat < player_count:
        raise ValueError("seat outside player range")
    if root.current_player() != CHANCE:
        raise ValueError("range table root must be a chance node")
    if not isinstance(provenance, str) or not provenance.strip():
        raise ValueError("provenance must be non-empty")
    immutable_strategy = _validate_strategy(root, strategy)
    outcomes = root.chance_outcomes()
    if not outcomes:
        raise ValueError("chance root has zero reach")

    grouped: dict[tuple[int, int], list[tuple[float, object, Hashable, tuple[Action, ...], Mapping[Action, float], dict[Action, float], float]]] = {}
    total_reach = 0.0
    for action, probability_raw in outcomes:
        if isinstance(probability_raw, bool) or not isinstance(probability_raw, (int, float)) or not isfinite(float(probability_raw)) or probability_raw < 0:
            raise ValueError("chance probabilities must be finite and non-negative")
        probability = float(probability_raw)
        if probability == 0:
            continue
        state = root.child(action)
        deal = getattr(state, "private_deal", None)
        if not isinstance(deal, tuple) or seat >= len(deal):
            raise ValueError("chance child does not expose requested private combo")
        combo = deal[seat]
        if not isinstance(combo, tuple) or len(combo) != 2:
            raise ValueError("private combo must contain two cards")
        info_key = state.information_state_key(seat)
        if state.current_player() == seat:
            actions = state.legal_actions()
            policy = immutable_strategy[info_key]
            action_evs = {candidate: _value(state.child(candidate), immutable_strategy, seat) for candidate in actions}
            mixed_ev = sum(policy[candidate] * action_evs[candidate] for candidate in actions)
        else:
            actions = ()
            policy = MappingProxyType({})
            action_evs = {}
            mixed_ev = _value(state, immutable_strategy, seat)
        grouped.setdefault(combo, []).append(
            (probability, _source_weight(root, seat, combo), info_key, actions, policy, action_evs, mixed_ev)
        )
        total_reach += probability
    if total_reach <= 0:
        raise ValueError("requested range has zero reach")

    rows = []
    for combo, realizations in grouped.items():
        reach = sum(item[0] for item in realizations)
        _, source_weight, info_key, actions, policy, _, _ = realizations[0]
        if any(item[2] != info_key or item[3] != actions or dict(item[4]) != dict(policy) for item in realizations):
            raise ValueError("same private combo has inconsistent information policy")
        action_evs = {
            candidate: sum(item[0] * item[5][candidate] for item in realizations) / reach
            for candidate in actions
        }
        mixed_ev = sum(item[0] * item[6] for item in realizations) / reach
        rows.append(
            RangeTableRow(
                combo=combo,
                source_weight=source_weight,
                conditional_reach=reach / total_reach,
                range_probability=reach / total_reach,
                info_key=info_key,
                actions=actions,
                action_probabilities=policy,
                action_evs=action_evs,
                mixed_ev=mixed_ev,
            )
        )
    row_tuple = tuple(rows)
    common_actions = row_tuple[0].actions if row_tuple and all(row.actions == row_tuple[0].actions for row in row_tuple) else ()
    frequencies = {
        action: sum(row.range_probability * row.action_probabilities[action] for row in row_tuple)
        for action in common_actions
    }
    mixed_ev = sum(row.range_probability * row.mixed_ev for row in row_tuple)
    return RangeTable(seat, row_tuple, frequencies, mixed_ev, provenance)
