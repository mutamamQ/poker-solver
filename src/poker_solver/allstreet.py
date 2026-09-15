"""S1-I1 bounded all-street postflop facade with automatic natural terminals."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Any, Literal, Mapping

from .bounded_tree import validate_bounded_tree
from .cards import parse_card
from .cfr import CFRSolver
from .equity import WeightedCombo
from .mccfr import MCCFRSolver
from .multistreet import MultiStreetConfig, create_root
from .best_response import nash_conv
from .api import complete_strategy


def _deep_freeze(value: Any) -> Any:
    """Recursively detach and freeze standard mutable containers."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_deep_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class AllStreetPostflopConfig:
    """Immutable configuration for automatic all-street postflop solve."""
    version: str
    starting_board: tuple[int, int, int]
    initial_dead_pot: int
    effective_stack: int
    player0_combos: tuple[WeightedCombo, ...]
    player1_combos: tuple[WeightedCombo, ...]
    allowed_runouts: tuple[tuple[int, int], ...]
    betting_mode: Literal["no-limit", "pot-limit"]
    wager_targets: tuple[int, ...]
    max_nodes: int = 100_000
    max_depth: int = 512

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "starting_board", tuple(self.starting_board))
            object.__setattr__(self, "player0_combos", tuple(self.player0_combos))
            object.__setattr__(self, "player1_combos", tuple(self.player1_combos))
            object.__setattr__(
                self,
                "allowed_runouts",
                tuple(tuple(runout) for runout in self.allowed_runouts),
            )
            object.__setattr__(self, "wager_targets", tuple(self.wager_targets))
        except TypeError as exc:
            raise ValueError("all sequence fields must be iterable") from exc

        # Version validation
        if self.version != "allstreet-postflop-v1":
            raise ValueError(f"version must be exactly 'allstreet-postflop-v1', got {self.version!r}")
        
        # Starting board validation
        if not isinstance(self.starting_board, tuple) or len(self.starting_board) != 3:
            raise ValueError("starting_board must contain exactly 3 cards")
        board_set = set(self.starting_board)
        if len(board_set) != 3:
            raise ValueError("starting_board cards must be unique")
        for card in self.starting_board:
            if not isinstance(card, int) or isinstance(card, bool) or not 0 <= card < 52:
                raise ValueError(f"invalid card in starting_board: {card}")
        
        # Pot and stack validation
        if isinstance(self.initial_dead_pot, bool) or not isinstance(self.initial_dead_pot, int):
            raise ValueError("initial_dead_pot must be an integer")
        if self.initial_dead_pot < 0:
            raise ValueError("initial_dead_pot must be non-negative")
        
        if isinstance(self.effective_stack, bool) or not isinstance(self.effective_stack, int):
            raise ValueError("effective_stack must be an integer")
        if self.effective_stack <= 0:
            raise ValueError("effective_stack must be positive")
        
        # Combo validation
        for i, combo in enumerate(self.player0_combos):
            if not isinstance(combo, WeightedCombo):
                raise ValueError(f"player0_combos[{i}] must be WeightedCombo")
            if not isfinite(combo.weight):
                raise ValueError(f"player0_combos[{i}] weight must be finite")
            if combo.weight < 0:
                raise ValueError(f"player0_combos[{i}] weight must be non-negative")
            if board_set.intersection(combo.cards):
                raise ValueError(f"player0_combos[{i}] cards overlap with starting_board")
        
        for i, combo in enumerate(self.player1_combos):
            if not isinstance(combo, WeightedCombo):
                raise ValueError(f"player1_combos[{i}] must be WeightedCombo")
            if not isfinite(combo.weight):
                raise ValueError(f"player1_combos[{i}] weight must be finite")
            if combo.weight < 0:
                raise ValueError(f"player1_combos[{i}] weight must be non-negative")
            if board_set.intersection(combo.cards):
                raise ValueError(f"player1_combos[{i}] cards overlap with starting_board")
        
        # Total weight validation - must be positive for compatible mass
        total_p0 = sum(c.weight for c in self.player0_combos)
        total_p1 = sum(c.weight for c in self.player1_combos)
        if total_p0 <= 0:
            raise ValueError("player0_combos total weight must be positive")
        if total_p1 <= 0:
            raise ValueError("player1_combos total weight must be positive")
        
        # Runout validation
        runout_set = set()
        for i, runout in enumerate(self.allowed_runouts):
            if not isinstance(runout, tuple) or len(runout) != 2:
                raise ValueError(f"runout {i} must contain exactly 2 cards")
            runout_cards = set(runout)
            if len(runout_cards) != 2:
                raise ValueError(f"runout {i} cards must be unique")
            if board_set.intersection(runout_cards):
                raise ValueError(f"runout {i} cards overlap with starting_board")
            runout_frozen = tuple(sorted(runout))
            if runout_frozen in runout_set:
                raise ValueError(f"runout {i} is not unique")
            runout_set.add(runout_frozen)
        
        # Betting mode validation
        if self.betting_mode not in ("no-limit", "pot-limit"):
            raise ValueError(f"betting_mode must be 'no-limit' or 'pot-limit', got {self.betting_mode!r}")
        
        # Wager targets validation
        for i, target in enumerate(self.wager_targets):
            if isinstance(target, bool) or not isinstance(target, int):
                raise ValueError(f"wager_target[{i}] must be an integer")
            if target < 0:
                raise ValueError(f"wager_target[{i}] must be non-negative")
        
        if tuple(sorted(set(self.wager_targets))) != self.wager_targets:
            raise ValueError("wager_targets must be unique and increasing")


@dataclass(frozen=True, slots=True)
class AllStreetSolveResult:
    """Immutable result from all-street postflop solve."""
    algorithm: str
    seed: int | None
    iterations: int
    values: tuple[float, float]
    nash_conv: float
    half_nash_conv: float
    strategy: Mapping[Any, Mapping[Any, float]]
    config_version: int
    game_version: str
    starting_street: str
    continuation: str
    max_nodes: int
    max_depth: int
    node_count: int
    max_depth_reached: int
    approximate: bool
    provenance: str
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        frozen_strategy = MappingProxyType(
            {
                info_key: MappingProxyType(dict(policy))
                for info_key, policy in self.strategy.items()
            }
        )
        object.__setattr__(self, "strategy", frozen_strategy)
        object.__setattr__(self, "metadata", _deep_freeze(self.metadata))


def create_allstreet_root(config: AllStreetPostflopConfig):
    """Create the root composite state for an all-street postflop game."""
    # Translate to MultiStreetConfig
    ms_config = MultiStreetConfig(
        version="multistreet-v1",
        starting_street="flop",
        starting_board=config.starting_board,
        initial_dead_pot=config.initial_dead_pot,
        effective_stack=config.effective_stack,
        player0_combos=config.player0_combos,
        player1_combos=config.player1_combos,
        allowed_runouts=config.allowed_runouts,
        betting_mode=config.betting_mode,
        wager_targets=config.wager_targets,
        river_betting=True,
    )
    return create_root(ms_config)


def solve_allstreet_postflop(
    config: AllStreetPostflopConfig,
    *,
    algorithm: Literal["vanilla-cfr", "external-sampling-mccfr"],
    iterations: int,
    seed: int | None = None,
) -> AllStreetSolveResult:
    """Solve an all-street postflop game with bounded-tree validation.
    
    Args:
        config: Validated all-street postflop configuration
        algorithm: Either 'vanilla-cfr' or 'external-sampling-mccfr'
        iterations: Number of iterations (must be positive)
        seed: Random seed for MCCFR (required for MCCFR, must be None for vanilla)
    
    Returns:
        AllStreetSolveResult with complete metadata and strategy
    """
    # Algorithm validation
    if algorithm not in ("vanilla-cfr", "external-sampling-mccfr"):
        raise ValueError(f"algorithm must be 'vanilla-cfr' or 'external-sampling-mccfr', got {algorithm!r}")
    
    # Iterations validation
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations <= 0:
        raise ValueError("iterations must be a positive integer")
    
    # Seed validation
    if algorithm == "vanilla-cfr":
        if seed is not None:
            raise ValueError("vanilla-cfr does not accept a seed parameter")
    else:  # external-sampling-mccfr
        if seed is None:
            raise ValueError("external-sampling-mccfr requires a seed parameter")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
    
    # Create root and validate bounded tree
    root = create_allstreet_root(config)
    stats = validate_bounded_tree(
        root,
        max_nodes=config.max_nodes,
        max_depth=config.max_depth,
    )
    
    # Train with appropriate algorithm
    if algorithm == "vanilla-cfr":
        solver = CFRSolver(root)
        strategy = solver.train(iterations)
    else:  # external-sampling-mccfr
        solver = MCCFRSolver(root, seed)
        strategy = solver.train(iterations)
    
    # Complete strategy and compute exploitability
    strategy = complete_strategy(root, strategy)
    metric = nash_conv(root, strategy)
    
    return AllStreetSolveResult(
        algorithm=algorithm,
        seed=seed,
        iterations=iterations,
        values=(metric.values[0], metric.values[1]),
        nash_conv=metric.nash_conv,
        half_nash_conv=metric.exploitability,
        strategy=strategy,
        config_version=4,
        game_version="allstreet-postflop-v1",
        starting_street="flop",
        continuation="automatic-natural-terminal",
        max_nodes=config.max_nodes,
        max_depth=config.max_depth,
        node_count=stats.node_count,
        max_depth_reached=stats.max_depth_reached,
        approximate=False,
        provenance="complete configured flop-to-river finite-tree traversal",
        metadata={
            "terminal_count": stats.terminal_count,
            "chance_count": stats.chance_count,
            "decision_count": stats.decision_count,
        },
    )
