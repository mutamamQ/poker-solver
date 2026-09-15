"""Correctness-first finite-game poker solver."""

from .allstreet import (
    AllStreetPostflopConfig,
    AllStreetSolveResult,
    create_allstreet_root,
    solve_allstreet_postflop,
)
from .api_v4 import dispatch_v4

__version__ = "0.1.0"
