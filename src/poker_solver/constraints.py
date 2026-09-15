"""Nodelocking and player-profile constraints for CFR solvers."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import TYPE_CHECKING, Hashable, Mapping

if TYPE_CHECKING:
    from .model import Action, GameState, InfoKey


def validate_locks(
    root: "GameState",
    locks: dict["InfoKey", dict["Action", float]],
    tolerance: float = 1e-10,
) -> None:
    """Validate lock configuration against game tree.
    
    Args:
        root: Game root state
        locks: Map from InfoKey to complete probability distribution
        tolerance: Numerical tolerance for unit-sum validation
    
    Raises:
        ValueError: If any lock is invalid (missing/extra actions, bad probabilities, etc.)
    """
    from .cfr import collect_infosets
    
    infosets = collect_infosets(root)
    
    for key, distribution in locks.items():
        # Check key existence
        if key not in infosets:
            raise ValueError(f"Lock key {key!r} not found in game tree")
        
        player, legal_actions = infosets[key]
        lock_actions = set(distribution.keys())
        legal_set = set(legal_actions)
        
        # Check action completeness
        if lock_actions != legal_set:
            missing = legal_set - lock_actions
            extra = lock_actions - legal_set
            if missing:
                raise ValueError(
                    f"Lock at {key!r} missing actions: {missing}"
                )
            if extra:
                raise ValueError(
                    f"Lock at {key!r} has extra actions: {extra}"
                )
        
        # Check finite non-negative probabilities and unit sum
        total = 0.0
        for action, prob in distribution.items():
            if isinstance(prob, bool):
                raise ValueError(
                    f"Lock at {key!r} action {action} probability must not be boolean"
                )
            if not isinstance(prob, (int, float)):
                raise TypeError(f"Lock at {key!r} probability must be numeric")
            if not isfinite(prob):
                raise ValueError(
                    f"Lock at {key!r} action {action} has non-finite probability {prob}"
                )
            if prob < 0:
                raise ValueError(
                    f"Lock at {key!r} action {action} has negative probability {prob}"
                )
            total += prob
        
        if abs(total - 1.0) > tolerance:
            raise ValueError(
                f"Lock at {key!r} probabilities sum to {total}, not 1.0 (tolerance {tolerance})"
            )


class ConstrainedCFRSolver:
    """CFR solver with exact nodelocks.
    
    Locked information sets use fixed probability distributions.
    Regret updates are skipped for locked keys.
    Strategy sums accumulate the locked distribution.
    """
    
    def __init__(self, root: "GameState", locks: dict["InfoKey", dict["Action", float]]) -> None:
        from .cfr import collect_infosets, InfoData
        
        validate_locks(root, locks)
        
        self.root = root
        self.locks = MappingProxyType({
            key: MappingProxyType(dict(distribution))
            for key, distribution in locks.items()
        })
        self.infosets = {
            key: InfoData(player, actions)
            for key, (player, actions) in collect_infosets(root).items()
        }
        self.iterations = 0
    
    def current_strategy(self) -> dict["InfoKey", dict["Action", float]]:
        from .cfr import regret_matching
        
        result = {}
        for key, data in self.infosets.items():
            if key in self.locks:
                result[key] = self.locks[key]
            else:
                result[key] = regret_matching(data.regrets, data.actions)
        return result
    
    def average_strategy(self) -> dict["InfoKey", dict["Action", float]]:
        result = {}
        for key, data in self.infosets.items():
            total = sum(data.strategy_sum.values())
            if total > 0:
                result[key] = {a: data.strategy_sum[a] / total for a in data.actions}
            else:
                p = 1.0 / len(data.actions)
                result[key] = {a: p for a in data.actions}
        return result
    
    def train(self, iterations: int) -> dict["InfoKey", dict["Action", float]]:
        from .model import Strategy
        
        if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations <= 0:
            raise ValueError("iterations must be a positive integer")
        
        for _ in range(iterations):
            snapshot = self.current_strategy()
            deltas = {key: {a: 0.0 for a in data.actions} for key, data in self.infosets.items()}
            owner_reaches: dict["InfoKey", float] = {}
            self._walk(self.root, 0, 1.0, 1.0, 1.0, snapshot, deltas, owner_reaches)
            self._walk(self.root, 1, 1.0, 1.0, 1.0, snapshot, deltas, None)
            
            for key, data in self.infosets.items():
                for action in data.actions:
                    # Skip regret update for locked keys
                    if key not in self.locks:
                        data.regrets[action] += deltas[key][action]
                    # Always accumulate strategy sum (locked or not)
                    data.strategy_sum[action] += owner_reaches[key] * snapshot[key][action]
            
            self.iterations += 1
        
        return self.average_strategy()
    
    def _walk(
        self,
        state: "GameState",
        updating: int,
        p0: float,
        p1: float,
        pc: float,
        profile: "Strategy",
        deltas: dict["InfoKey", dict["Action", float]],
        owner_reaches: dict["InfoKey", float] | None,
    ) -> float:
        from .model import TERMINAL, CHANCE
        from math import isclose
        
        player = state.current_player()
        if player == TERMINAL:
            return state.returns()[updating]
        if player == CHANCE:
            return sum(
                probability * self._walk(state.child(action), updating, p0, p1, pc * probability, profile, deltas, owner_reaches)
                for action, probability in state.chance_outcomes()
            )
        
        actions = state.legal_actions()
        key = state.information_state_key(player)
        policy = profile[key]
        own_reach = p0 if player == 0 else p1
        
        if owner_reaches is not None:
            if key in owner_reaches and not isclose(owner_reaches[key], own_reach, abs_tol=1e-12):
                raise ValueError(f"imperfect-recall owner reach at {key!r}")
            owner_reaches[key] = own_reach
        
        action_values: dict["Action", float] = {}
        for action in actions:
            if player == 0:
                action_values[action] = self._walk(state.child(action), updating, p0 * policy[action], p1, pc, profile, deltas, owner_reaches)
            else:
                action_values[action] = self._walk(state.child(action), updating, p0, p1 * policy[action], pc, profile, deltas, owner_reaches)
        
        node_value = sum(policy[a] * action_values[a] for a in actions)
        
        if player == updating:
            counterfactual_reach = (p1 if player == 0 else p0) * pc
            for action in actions:
                deltas[key][action] += counterfactual_reach * (action_values[action] - node_value)
        
        return node_value
    
    def values(self) -> tuple[float, float]:
        from .cfr import expected_values
        return expected_values(self.root, self.average_strategy())


_PROFILE_CATEGORIES = frozenset({"fold", "check", "call", "aggressive"})
_PUBLIC_CONDITIONING_FIELDS = frozenset({
    "street", "board", "public_history", "acting_seat", "pot", "stacks"
})


def _immutable_nested_policy(
    policy: Mapping[Hashable, Mapping["Action", float]],
) -> Mapping[Hashable, Mapping["Action", float]]:
    return MappingProxyType({
        key: MappingProxyType(dict(distribution))
        for key, distribution in policy.items()
    })


@dataclass(frozen=True, slots=True)
class BehaviorProfile:
    """Explicit action-category multipliers over a supplied baseline policy."""

    target_seat: int
    baseline: Mapping[Hashable, Mapping["Action", float]]
    multipliers: Mapping[str, float]
    baseline_provenance: str
    conditioning_fields: tuple[str, ...] = ("public_history",)

    def __post_init__(self) -> None:
        if (
            isinstance(self.target_seat, bool)
            or not isinstance(self.target_seat, int)
            or self.target_seat < 0
        ):
            raise ValueError("target_seat must be a non-negative integer")
        if not isinstance(self.baseline_provenance, str) or not self.baseline_provenance:
            raise ValueError("baseline_provenance must be non-empty text")
        if not isinstance(self.conditioning_fields, tuple) or any(
            field not in _PUBLIC_CONDITIONING_FIELDS for field in self.conditioning_fields
        ):
            raise ValueError("conditioning fields must be public-observable")
        if set(self.multipliers) != _PROFILE_CATEGORIES:
            raise ValueError("multipliers must define fold, check, call, and aggressive")
        copied_multipliers: dict[str, float] = {}
        for category, multiplier in self.multipliers.items():
            if (
                isinstance(multiplier, bool)
                or not isinstance(multiplier, (int, float))
                or not isfinite(multiplier)
                or multiplier < 0
            ):
                raise ValueError("profile multipliers must be finite non-negative numbers")
            copied_multipliers[category] = float(multiplier)
        object.__setattr__(self, "baseline", _immutable_nested_policy(self.baseline))
        object.__setattr__(self, "multipliers", MappingProxyType(copied_multipliers))


@dataclass(frozen=True, slots=True)
class ResolvedBehaviorProfile:
    target_seat: int
    provenance: str
    multipliers: Mapping[str, float]
    locks: Mapping[Hashable, Mapping["Action", float]]


def _action_category(action: "Action") -> str:
    kind = action.kind.upper()
    if kind == "FOLD":
        return "fold"
    if kind == "CHECK":
        return "check"
    if kind == "CALL":
        return "call"
    if kind in {"BET", "RAISE", "ALL_IN", "ALL-IN"}:
        return "aggressive"
    raise ValueError(f"unsupported profile action kind {action.kind!r}")


def resolve_profile_locks(
    root: "GameState",
    profile: BehaviorProfile,
) -> ResolvedBehaviorProfile:
    """Resolve baseline×multiplier policies into exact target-seat locks."""
    from .cfr import collect_infosets

    infosets = collect_infosets(root)
    target = {
        key: actions for key, (owner, actions) in infosets.items()
        if owner == profile.target_seat
    }
    if not target:
        raise ValueError("target_seat has no information sets")
    if set(profile.baseline) != set(target):
        raise ValueError("baseline must cover exactly the target seat information sets")
    resolved: dict[Hashable, Mapping["Action", float]] = {}
    for key, actions in target.items():
        baseline = profile.baseline[key]
        if set(baseline) != set(actions):
            raise ValueError("baseline action set must exactly match legal actions")
        weighted: dict["Action", float] = {}
        for action in actions:
            probability = baseline[action]
            if (
                isinstance(probability, bool)
                or not isinstance(probability, (int, float))
                or not isfinite(probability)
                or probability < 0
            ):
                raise ValueError("baseline probabilities must be finite non-negative numbers")
            weighted[action] = float(probability) * profile.multipliers[_action_category(action)]
        baseline_total = sum(float(value) for value in baseline.values())
        if abs(baseline_total - 1.0) > 1e-10:
            raise ValueError("baseline probabilities must sum to 1")
        denominator = sum(weighted.values())
        if denominator <= 0:
            raise ValueError("profile normalization has zero denominator")
        resolved[key] = MappingProxyType({
            action: weighted[action] / denominator for action in actions
        })
    locks = MappingProxyType(resolved)
    validate_locks(root, {key: dict(value) for key, value in locks.items()})
    return ResolvedBehaviorProfile(
        target_seat=profile.target_seat,
        provenance=profile.baseline_provenance,
        multipliers=profile.multipliers,
        locks=locks,
    )