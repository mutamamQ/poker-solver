"""Deterministic, seeded practice-spot catalog generator.

Each family is a parameter grid (not a puzzle list).  The generator only builds
*inputs* (boards, ranges, pots, bet sizes, hero hands, public lines); it never
solves and contains no strategy, probability or EV values.  Answers come from
:mod:`poker_solver.practice.adapter` at runtime.
"""

from __future__ import annotations

import hashlib
import json
import random
from itertools import product
from typing import Iterable

from ..equity import WeightedCombo
from ..model import Action
from ..ranges import import_range_text
from .models import KUHN_CARDS, PracticeSpot, SolveParams

__all__ = [
    "FAMILIES",
    "RIVER_BET_PCTS",
    "RIVER_POTS",
    "RIVER_SPR",
    "RIVER_COMBOS_PER_SIDE",
    "RANGE_SHAPES",
    "generate_catalog",
    "find_spot",
    "river_ranges",
]

FAMILIES = ("kuhn-intro", "river-oop-bet-or-check", "river-ip-facing-bet")
#: Bet size as a percentage of the pot.
RIVER_BET_PCTS = (33, 75, 125)
RIVER_POTS = (100, 200)
#: Stack-to-pot ratio; stack = pot * SPR keeps every bet size within the stack.
RIVER_SPR = 2
#: Combos kept per side; 4x4 keeps each 200-iteration river solve near 1 s.
RIVER_COMBOS_PER_SIDE = 4
#: Range shapes by hand category: (OOP/bettor range text, IP/defender range text).
#: Only *which hands* are dealt is chosen here; how they are played is solved.
RANGE_SHAPES = (
    ("polar-vs-catchers", "AA,KK,AKs,76s,65s,54s", "QQ,JJ,TT,99"),
    ("merged-vs-condensed", "AA,KK,QQ,AKs,AQs,KQs", "QQ,JJ,TT,AQs,KQs"),
)
_MAX_BOARD_ATTEMPTS = 64
_KUHN_NODES = (
    ((), 0),
    ((Action("check"),), 1),
    ((Action("bet"),), 1),
    ((Action("check"), Action("bet")), 0),
)


def _cell_rng(seed: int, family: str, axes: Iterable[object]) -> tuple[int, random.Random]:
    """Per-cell RNG derived from sha256 (never Python ``hash()``)."""
    text = json.dumps([seed, family, list(axes)], separators=(",", ":"))
    cell_seed = int(hashlib.sha256(text.encode("ascii")).hexdigest()[:12], 16)
    return cell_seed, random.Random(cell_seed)


def river_ranges(
    board: tuple[int, ...], shape: str, rng: random.Random, combos_per_side: int = RIVER_COMBOS_PER_SIDE
) -> tuple[tuple[WeightedCombo, ...], tuple[WeightedCombo, ...]]:
    """Seeded small ranges for ``shape`` with board-blocked combos removed.

    Hands come from ``ranges.import_range_text`` class expressions; weights are the
    helper's own (full) weights.  Raises ``ValueError`` if a side has too few combos.
    """
    texts = {name: (oop, ip) for name, oop, ip in RANGE_SHAPES}
    if shape not in texts:
        raise ValueError(f"unknown range shape {shape!r}")
    out = []
    for text in texts[shape]:
        editor = import_range_text(text).blocked(list(board))
        combos = sorted((cards, weight) for cards, weight in editor.combos().items() if weight > 0)
        if len(combos) < combos_per_side:
            raise ValueError(f"range {text!r} has too few combos on this board")
        picked = sorted(rng.sample(combos, combos_per_side))
        out.append(tuple(WeightedCombo(cards, weight) for cards, weight in picked))
    return out[0], out[1]


def _kuhn_spots(solve: SolveParams) -> list[PracticeSpot]:
    spots = []
    for (history, hero), card in product(_KUHN_NODES, KUHN_CARDS):
        spots.append(
            PracticeSpot(
                family="kuhn-intro",
                backend="kuhn",
                game_type="heads-up",
                street="preflop",
                board=(),
                hero_seat=hero,
                villain_seats=(1 - hero,),
                ranges=((), ()),
                pot=2,
                stacks=(1, 1),
                action_history=history,
                bet_sizes=(1,),
                hero_hand=None,
                solve=solve,
                backend_extra={"kuhn_card": card},
            )
        )
    return spots


def _river_spot(family: str, seed: int, solve: SolveParams, shape: str, pot: int, pct: int) -> PracticeSpot:
    hero = 0 if family == "river-oop-bet-or-check" else 1
    cell_seed, rng = _cell_rng(seed, family, (shape, pot, pct))
    bet = max(1, (pot * pct + 50) // 100)
    stack = pot * RIVER_SPR
    history = () if hero == 0 else (Action("bet", bet),)
    for _attempt in range(_MAX_BOARD_ATTEMPTS):
        board = tuple(rng.sample(range(52), 5))
        try:
            ranges = river_ranges(board, shape, rng)
        except ValueError:
            continue
        hero_range, villain_range = ranges[hero], ranges[1 - hero]
        candidates = [
            c for c in hero_range if any(not set(c.cards).intersection(v.cards) for v in villain_range)
        ]
        if not candidates:
            continue
        hero_hand = rng.choices(candidates, weights=[c.weight for c in candidates])[0].cards
        return PracticeSpot(
            family=family,
            backend="river",
            game_type="heads-up",
            street="river",
            board=board,
            hero_seat=hero,
            villain_seats=(1 - hero,),
            ranges=ranges,
            pot=pot,
            stacks=(stack, stack),
            action_history=history,
            bet_sizes=(bet,),
            hero_hand=hero_hand,
            solve=solve,
            backend_extra={"bet_pct": pct, "spr": RIVER_SPR, "range_shape": shape, "cell_seed": cell_seed},
        )
    raise ValueError(f"no valid board for {family} cell {(shape, pot, pct)} after {_MAX_BOARD_ATTEMPTS} attempts")


def _validate_args(families, seed, solve, limit) -> tuple[tuple[str, ...], SolveParams]:
    if families is None:
        families = FAMILIES
    if isinstance(families, str):
        families = (families,)
    families = tuple(families)
    for family in families:
        if family not in FAMILIES:
            raise ValueError(f"unknown family {family!r}; known: {FAMILIES}")
    if len(set(families)) != len(families):
        raise ValueError("duplicate families requested")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer (bool not allowed)")
    if solve is None:
        solve = SolveParams()
    if not isinstance(solve, SolveParams):
        raise ValueError("solve must be SolveParams or None")
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0):
        raise ValueError("limit must be a non-negative integer or None")
    return families, solve


def generate_catalog(
    families: Iterable[str] | None = None,
    seed: int = 0,
    solve: SolveParams | None = None,
    limit: int | None = None,
) -> tuple[PracticeSpot, ...]:
    """Generate the spot catalog (no solving; deterministic for ``seed``).

    Families are emitted in :data:`FAMILIES` order regardless of request order, so a
    family's spots do not depend on which other families are requested.
    """
    wanted, solve = _validate_args(families, seed, solve, limit)
    spots: list[PracticeSpot] = []
    for family in FAMILIES:
        if family not in wanted:
            continue
        if family == "kuhn-intro":
            spots.extend(_kuhn_spots(solve))
        else:
            for (shape, _o, _i), pot, pct in product(RANGE_SHAPES, RIVER_POTS, RIVER_BET_PCTS):
                spots.append(_river_spot(family, seed, solve, shape, pot, pct))
    ids = [s.spot_id for s in spots]
    if len(set(ids)) != len(ids):
        raise ValueError("catalog produced duplicate spot ids")
    if limit is not None:
        spots = spots[:limit]
    return tuple(spots)


def find_spot(
    spot_id: str,
    families: Iterable[str] | None = None,
    seed: int = 0,
    solve: SolveParams | None = None,
) -> PracticeSpot:
    """Look up a generated spot by ``spot_id``; ``ValueError`` if unknown."""
    if not isinstance(spot_id, str):
        raise ValueError("spot_id must be a string")
    for spot in generate_catalog(families, seed, solve):
        if spot.spot_id == spot_id:
            return spot
    raise ValueError(f"unknown spot_id {spot_id!r} for seed {seed}")
