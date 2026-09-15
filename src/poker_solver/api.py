"""Strict version-2 programmatic JSON API for multi-street solver."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any, Literal

from .best_response import nash_conv
from .cards import parse_card
from .cfr import CFRSolver, collect_infosets
from .equity import WeightedCombo
from .mccfr import MCCFRSolver
from .multistreet import BettingMode, MultiStreetConfig, Street, create_root
from .model import Action, GameState, Strategy


@dataclass(frozen=True, slots=True)
class SolveResult:
    """Result of a multi-street solve operation."""
    algorithm: str
    seed: int | None
    iterations: int
    values: tuple[float, float]
    nash_conv: float
    half_nash_conv: float
    strategy: dict[Any, dict[Any, float]]
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ExploitabilityResult:
    """Result of an exploitability computation."""
    nash_conv: float
    half_nash_conv: float
    values: tuple[float, float]
    best_response_values: tuple[float, float]
    incentives: tuple[float, float]


def _reject_bool(value: Any, field: str) -> None:
    """Reject boolean values masquerading as numbers."""
    if isinstance(value, bool):
        raise ValueError(f"{field} must not be a boolean")


def _strict_int(value: Any, field: str) -> int:
    """Parse a strict JSON integer, rejecting booleans and floats."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be a JSON integer")
    return value


def _strict_number(value: Any, field: str) -> float:
    """Parse a strict JSON number, rejecting booleans."""
    _reject_bool(value, field)
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a JSON number")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _strict_positive_int(value: Any, field: str) -> int:
    """Parse a strict positive integer."""
    result = _strict_int(value, field)
    if result <= 0:
        raise ValueError(f"{field} must be positive")
    return result


def _strict_nonnegative_int(value: Any, field: str) -> int:
    """Parse a strict non-negative integer."""
    result = _strict_int(value, field)
    if result < 0:
        raise ValueError(f"{field} must be non-negative")
    return result


def _strict_nonnegative_number(value: Any, field: str) -> float:
    """Parse a strict non-negative number."""
    result = _strict_number(value, field)
    if result < 0:
        raise ValueError(f"{field} must be non-negative")
    return result


def _parse_combo(item: Any, index: int) -> WeightedCombo:
    """Parse a single combo with strict validation."""
    if not isinstance(item, dict):
        raise ValueError(f"combo {index} must be an object")
    if set(item.keys()) != {"cards", "weight"}:
        raise ValueError(f"combo {index} must have exactly 'cards' and 'weight' fields")
    cards_value = item["cards"]
    if not isinstance(cards_value, list) or len(cards_value) != 2:
        raise ValueError(f"combo {index} cards must be a two-element list")
    if not all(isinstance(c, str) for c in cards_value):
        raise ValueError(f"combo {index} cards must be strings")
    card0 = parse_card(cards_value[0])
    card1 = parse_card(cards_value[1])
    weight = _strict_nonnegative_number(item["weight"], f"combo {index} weight")
    return WeightedCombo((card0, card1), weight)


def _parse_board(cards: Any, field: str) -> tuple[int, ...]:
    """Parse a board card list with strict validation."""
    if not isinstance(cards, list):
        raise ValueError(f"{field} must be a list")
    if not all(isinstance(c, str) for c in cards):
        raise ValueError(f"{field} must contain only strings")
    return tuple(parse_card(c) for c in cards)


def _parse_runout(runout: Any, index: int) -> tuple[int, ...]:
    """Parse a single runout with strict validation."""
    if not isinstance(runout, list):
        raise ValueError(f"runout {index} must be a list")
    if not all(isinstance(c, str) for c in runout):
        raise ValueError(f"runout {index} must contain only strings")
    return tuple(parse_card(c) for c in runout)


def load_multistreet_config(data: dict[str, Any]) -> MultiStreetConfig:
    """Load and validate a version-2 multi-street configuration.
    
    Strict validation:
    - Rejects unknown fields
    - Rejects bool-as-int
    - Rejects non-finite or negative weights
    - Validates card uniqueness and overlaps
    - Enforces size limits
    - Rejects empty combo lists
    - Rejects zero-total weights
    """
    if not isinstance(data, dict):
        raise ValueError("configuration must be a JSON object")
    
    required = {
        "version", "starting_street", "starting_board", "initial_dead_pot",
        "effective_stack", "player0_combos", "player1_combos",
        "allowed_runouts", "betting_mode", "wager_targets"
    }
    if set(data.keys()) != required:
        extra = set(data.keys()) - required
        missing = required - set(data.keys())
        if extra:
            raise ValueError(f"unknown fields: {sorted(extra)}")
        if missing:
            raise ValueError(f"missing required fields: {sorted(missing)}")
    
    version = _strict_int(data["version"], "version")
    if version != 2:
        raise ValueError(f"unsupported version {version!r}, expected 2")
    
    starting_street = data["starting_street"]
    if starting_street not in ("flop", "turn", "river"):
        raise ValueError(f"starting_street must be 'flop', 'turn', or 'river'")
    
    starting_board = _parse_board(data["starting_board"], "starting_board")
    initial_dead_pot = _strict_nonnegative_int(data["initial_dead_pot"], "initial_dead_pot")
    effective_stack = _strict_positive_int(data["effective_stack"], "effective_stack")
    
    if not isinstance(data["player0_combos"], list):
        raise ValueError("player0_combos must be a list")
    if not isinstance(data["player1_combos"], list):
        raise ValueError("player1_combos must be a list")
    
    # Reject empty combo lists
    if len(data["player0_combos"]) == 0:
        raise ValueError("player0_combos must not be empty")
    if len(data["player1_combos"]) == 0:
        raise ValueError("player1_combos must not be empty")
    
    player0_combos = tuple(_parse_combo(item, i) for i, item in enumerate(data["player0_combos"]))
    player1_combos = tuple(_parse_combo(item, i) for i, item in enumerate(data["player1_combos"]))
    
    # Reject zero-total weights
    total_weight_p0 = sum(c.weight for c in player0_combos)
    total_weight_p1 = sum(c.weight for c in player1_combos)
    if total_weight_p0 <= 0:
        raise ValueError("player0_combos total weight must be positive")
    if total_weight_p1 <= 0:
        raise ValueError("player1_combos total weight must be positive")
    
    if not isinstance(data["allowed_runouts"], list):
        raise ValueError("allowed_runouts must be a list")
    allowed_runouts = tuple(_parse_runout(r, i) for i, r in enumerate(data["allowed_runouts"]))
    
    betting_mode = data["betting_mode"]
    if betting_mode not in ("no-limit", "pot-limit"):
        raise ValueError(f"betting_mode must be 'no-limit' or 'pot-limit'")
    
    if not isinstance(data["wager_targets"], list):
        raise ValueError("wager_targets must be a list")
    wager_targets = tuple(_strict_nonnegative_int(t, f"wager_target[{i}]") for i, t in enumerate(data["wager_targets"]))
    
    # Size limits
    MAX_COMBOS = 1000
    MAX_RUNOUTS = 1000
    MAX_WAGERS = 100
    
    if len(player0_combos) > MAX_COMBOS:
        raise ValueError(f"player0_combos exceeds limit of {MAX_COMBOS}")
    if len(player1_combos) > MAX_COMBOS:
        raise ValueError(f"player1_combos exceeds limit of {MAX_COMBOS}")
    if len(allowed_runouts) > MAX_RUNOUTS:
        raise ValueError(f"allowed_runouts exceeds limit of {MAX_RUNOUTS}")
    if len(wager_targets) > MAX_WAGERS:
        raise ValueError(f"wager_targets exceeds limit of {MAX_WAGERS}")
    
    return MultiStreetConfig(
        version="multistreet-v1",
        starting_street=starting_street,  # type: ignore
        starting_board=starting_board,
        initial_dead_pot=initial_dead_pot,
        effective_stack=effective_stack,
        player0_combos=player0_combos,
        player1_combos=player1_combos,
        allowed_runouts=allowed_runouts,
        betting_mode=betting_mode,  # type: ignore
        wager_targets=wager_targets,
    )


def solve_multistreet(
    config: MultiStreetConfig,
    algorithm: Literal["vanilla-cfr", "external-sampling-mccfr"],
    iterations: int,
    seed: int | None = None,
) -> SolveResult:
    """Solve a multi-street game with the specified algorithm.
    
    Args:
        config: Validated multi-street configuration
        algorithm: Either 'vanilla-cfr' or 'external-sampling-mccfr'
        iterations: Number of iterations (must be positive)
        seed: Random seed for MCCFR (required for MCCFR, must be None for vanilla)
    
    Returns:
        SolveResult with values, exploitability, and strategy
    """
    if algorithm not in ("vanilla-cfr", "external-sampling-mccfr"):
        raise ValueError(f"algorithm must be 'vanilla-cfr' or 'external-sampling-mccfr'")
    
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations <= 0:
        raise ValueError("iterations must be a positive integer")
    
    root = create_root(config)
    exact_chance_leaves = (
        len(config.player0_combos)
        * len(config.player1_combos)
        * max(1, len(config.allowed_runouts))
    )
    if algorithm == "vanilla-cfr" and exact_chance_leaves > 10_000:
        raise ValueError("vanilla-cfr input exceeds the exact chance-tree limit of 10000")
    
    if algorithm == "vanilla-cfr":
        if seed is not None:
            raise ValueError("vanilla-cfr does not accept a seed parameter")
        solver = CFRSolver(root)
        strategy = solver.train(iterations)
    else:  # external-sampling-mccfr
        if seed is None:
            raise ValueError("external-sampling-mccfr requires a seed parameter")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        solver = MCCFRSolver(root, seed)
        strategy = solver.train(iterations)

    strategy = complete_strategy(root, strategy)
    metric = nash_conv(root, strategy)
    
    return SolveResult(
        algorithm=algorithm,
        seed=seed,
        iterations=iterations,
        values=metric.values,
        nash_conv=metric.nash_conv,
        half_nash_conv=metric.exploitability,
        strategy=strategy,
        metadata={
            "config_version": 2,
            "starting_street": config.starting_street,
        },
    )


def compute_exploitability(root: Any, strategy: dict[Any, dict[Any, float]]) -> ExploitabilityResult:
    """Compute exploitability metrics for a given strategy.
    
    Args:
        root: Game root state
        strategy: Strategy profile
    
    Returns:
        ExploitabilityResult with NashConv and related metrics
    """
    metric = nash_conv(root, strategy)
    return ExploitabilityResult(
        nash_conv=metric.nash_conv,
        half_nash_conv=metric.exploitability,
        values=metric.values,
        best_response_values=metric.best_response_values,
        incentives=metric.incentives,
    )


def complete_strategy(root: GameState, strategy: Strategy) -> Strategy:
    """Fill lazily unvisited infosets with explicit uniform policies."""
    complete = {key: dict(policy) for key, policy in strategy.items()}
    for key, (_, actions) in collect_infosets(root).items():
        if key not in complete:
            probability = 1.0 / len(actions)
            complete[key] = {action: probability for action in actions}
    return complete


def serialize_strategy(strategy: Strategy) -> dict[str, Any]:
    """Return a deterministic, round-trippable JSON strategy object."""
    return {
        "format": "poker-solver-strategy-v1",
        "policies": [
            {
                "information_state": repr(key),
                "actions": [
                    {"kind": action.kind, "amount": action.amount, "probability": policy[action]}
                    for action in sorted(policy)
                ],
            }
            for key, policy in sorted(strategy.items(), key=lambda item: repr(item[0]))
        ],
    }


def deserialize_strategy(root: GameState, data: Any) -> Strategy:
    """Decode JSON by matching canonical labels to this exact game tree."""
    if isinstance(data, dict) and "strategy" in data:
        data = data["strategy"]
    if not isinstance(data, dict) or set(data) != {"format", "policies"}:
        raise ValueError("strategy must contain exactly format and policies")
    if data["format"] != "poker-solver-strategy-v1" or not isinstance(data["policies"], list):
        raise ValueError("unsupported strategy format")
    infosets = collect_infosets(root)
    labels = {repr(key): (key, actions) for key, (_, actions) in infosets.items()}
    if len(labels) != len(infosets):
        raise ValueError("information-state labels are not unique")
    result: Strategy = {}
    for index, entry in enumerate(data["policies"]):
        if not isinstance(entry, dict) or set(entry) != {"information_state", "actions"}:
            raise ValueError(f"invalid policy entry {index}")
        label = entry["information_state"]
        if label not in labels or not isinstance(entry["actions"], list):
            raise ValueError(f"unknown information state {label!r}")
        key, expected_actions = labels[label]
        if key in result:
            raise ValueError(f"duplicate information state {label!r}")
        decoded: dict[Action, float] = {}
        for action_entry in entry["actions"]:
            if not isinstance(action_entry, dict) or set(action_entry) != {"kind", "amount", "probability"}:
                raise ValueError(f"invalid action entry for {label!r}")
            if not isinstance(action_entry["kind"], str):
                raise ValueError("action kind must be a string")
            action = Action(action_entry["kind"], _strict_int(action_entry["amount"], "action amount"))
            probability = _strict_nonnegative_number(action_entry["probability"], "action probability")
            if action in decoded:
                raise ValueError(f"duplicate action at {label!r}")
            decoded[action] = probability
        if set(decoded) != set(expected_actions):
            raise ValueError(f"wrong actions for information state {label!r}")
        result[key] = decoded
    if set(result) != set(infosets):
        raise ValueError("strategy is missing information states")
    return result


def load_json_input(source: str | Path) -> dict[str, Any]:
    """Load JSON from file path or stdin ('-').
    
    Args:
        source: File path or '-' for stdin
    
    Returns:
        Parsed JSON object
    """
    if source == "-":
        content = sys.stdin.read()
    else:
        content = Path(source).read_text(encoding="utf-8")
    return json.loads(content)
