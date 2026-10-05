"""Correctness-first finite-game poker solver."""

from .allstreet import (
    AllStreetPostflopConfig,
    AllStreetSolveResult,
    create_allstreet_root,
    solve_allstreet_postflop,
)
from .api_v4 import dispatch_v4
from .nplayer_postflop import (
    DealN,
    NPlayerPostflopConfig,
    NPlayerPostflopSolveResult,
    NPlayerPostflopState,
    NPlayerPublicAction,
    create_nplayer_postflop_root,
    enumerate_deals,
    solve_nplayer_postflop,
)
from .nplayer_preflop import (
    NPlayerPreflopConfig,
    NPlayerPreflopContinuation,
    NPlayerPreflopSizingRule,
    NPlayerPreflopPublicAction,
    NPlayerPreflopState,
    NPlayerPreflopSolveResult,
    enumerate_nplayer_preflop_deals,
    create_nplayer_preflop_root,
    solve_nplayer_preflop,
)

__version__ = "0.1.0"
