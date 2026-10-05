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
from .models import KUHN_CARDS, PREFLOP_BLINDS, PracticeSpot, SolveParams

__all__ = [
    "FAMILIES",
    "FAMILY_DEFAULT_SOLVE",
    "PREFLOP_HU_STACKS",
    "PREFLOP_HU_OPEN_SIZES",
    "PREFLOP_3MAX_STACK",
    "PREFLOP_3MAX_OPEN_SIZES",
    "POSTFLOP_BET_PCTS",
    "POSTFLOP_POT",
    "POSTFLOP_SPR",
    "RIVER_BET_PCTS",
    "RIVER_POTS",
    "RIVER_SPR",
    "RIVER_COMBOS_PER_SIDE",
    "RANGE_SHAPES",
    "generate_catalog",
    "find_spot",
    "river_ranges",
]

FAMILIES = (
    "kuhn-intro",
    "river-oop-bet-or-check",
    "river-ip-facing-bet",
    "preflop-hu-open",
    "preflop-3max-open",
    "flop-cbet",
    "turn-barrel",
)
#: Per-family default solve settings (used when ``generate_catalog(solve=None)``).
#: Sized so a cold solve stays within the 20 s budget on the reference host; see
#: research/practice-mode/w4/task-A.md for measured times.
FAMILY_DEFAULT_SOLVE = {
    "kuhn-intro": SolveParams(),
    "river-oop-bet-or-check": SolveParams(),
    "river-ip-facing-bet": SolveParams(),
    "preflop-hu-open": SolveParams(iterations=300),
    "preflop-3max-open": SolveParams(iterations=100),
    "flop-cbet": SolveParams(iterations=200),
    "turn-barrel": SolveParams(iterations=200),
}
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

# -- preflop families (chips; blinds come from models.PREFLOP_BLINDS = 1/2) -------
PREFLOP_HU_STACKS = (30, 50)
#: Open sizes as raise-to chips (2, 2.5 and 3 big blinds).
PREFLOP_HU_OPEN_SIZES = (4, 5, 6)
PREFLOP_HU_COMBOS = 5
PREFLOP_3MAX_STACK = 40
PREFLOP_3MAX_OPEN_SIZES = (5, 6)
PREFLOP_3MAX_COMBOS = 3
#: (shape name, one range text per seat in seat order). Only which hands are dealt
#: is chosen here; how they are played is solved.
PREFLOP_HU_SHAPES = (
    ("wide-vs-wide", ("AA,KK,QQ,JJ,TT,AKs,AQs,KQs,JTs,76s,A5s,AKo,KJo,QJo", "AA,KK,QQ,JJ,99,77,AKs,AJs,KQs,T9s,65s,AQo,KQo,JTo")),
    ("strong-vs-capped", ("AA,KK,QQ,AKs,AQs,AKo,KQs,A5s,54s", "JJ,TT,99,88,AJs,KJs,QJs,AJo,KQo")),
)
PREFLOP_3MAX_SHAPES = (
    ("btn-wide", ("AA,KK,QQ,JJ,AKs,AQs,KQs,JTs,76s,A5s,AKo,KJo", "AA,KK,QQ,TT,AKs,AJs,KQs,98s,AQo", "AA,KK,JJ,99,AKs,AQs,QJs,65s,AJo")),
    ("btn-tight", ("AA,KK,QQ,AKs,AKo,AQs", "QQ,JJ,TT,AQs,KQs,AJo", "JJ,TT,99,AJs,KQs,KJo")),
)
PREFLOP_EQUITY_SAMPLES = 256
PREFLOP_MAX_RAISES = 2
PREFLOP_MAX_NODES = 200_000
#: 3-max hero situations: (label, hero seat, public line before hero acts).
PREFLOP_3MAX_SITUATIONS = (("btn-first-in", 0, ()), ("sb-after-btn-fold", 1, (Action("FOLD"),)))

# -- postflop families -------------------------------------------------------------
POSTFLOP_POT = 100
POSTFLOP_SPR = 2
POSTFLOP_BET_PCTS = (33, 75)
FLOP_COMBOS_PER_SIDE = 3
FLOP_RUNOUTS = 2
TURN_COMBOS_PER_SIDE = 4
TURN_RUNOUTS = 4
#: Hero roles: (label, hero seat, public line before hero acts). Seat 0 acts first.
POSTFLOP_ROLES = (("oop-first", 0, ()), ("ip-after-check", 1, (Action("CHECK"),)))
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


def _sample_range(text: str, dead: Iterable[int], rng: random.Random, count: int) -> tuple[WeightedCombo, ...]:
    editor = import_range_text(text).blocked(sorted(set(dead)))
    combos = sorted((cards, weight) for cards, weight in editor.combos().items() if weight > 0)
    if len(combos) < count:
        raise ValueError(f"range {text!r} has too few combos")
    return tuple(WeightedCombo(cards, weight) for cards, weight in sorted(rng.sample(combos, count)))


def _pick_hero_hand(ranges: tuple, hero: int, rng: random.Random) -> tuple[int, int] | None:
    """Seeded hero hand that leaves every villain at least one unblocked combo."""
    candidates = [
        c
        for c in ranges[hero]
        if all(
            any(not set(c.cards).intersection(v.cards) for v in ranges[seat])
            for seat in range(len(ranges))
            if seat != hero
        )
    ]
    if not candidates:
        return None
    return rng.choices(candidates, weights=[c.weight for c in candidates])[0].cards


def _preflop_spot(
    family: str, seed: int, solve: SolveParams, shape: tuple, stack: int, size: int, situation: tuple
) -> PracticeSpot:
    shape_name, texts = shape
    label, hero, history = situation
    n = len(texts)
    count = PREFLOP_HU_COMBOS if n == 2 else PREFLOP_3MAX_COMBOS
    cell_seed, rng = _cell_rng(seed, family, (shape_name, stack, size, label))
    for _attempt in range(_MAX_BOARD_ATTEMPTS):
        used: set[int] = set()
        ranges = []
        for text in texts:
            # Seats draw sequentially from the unused deck, so every deal is compatible.
            seat_range = _sample_range(text, used, rng, count)
            used.update(card for combo in seat_range for card in combo.cards)
            ranges.append(seat_range)
        hero_hand = _pick_hero_hand(tuple(ranges), hero, rng)
        if hero_hand is None:
            continue
        return PracticeSpot(
            family=family,
            backend="nplayer-preflop",
            game_type="heads-up" if n == 2 else "3-max",
            street="preflop",
            board=(),
            hero_seat=hero,
            villain_seats=tuple(s for s in range(n) if s != hero),
            ranges=tuple(ranges),
            pot=sum(PREFLOP_BLINDS),
            stacks=(stack,) * n,
            action_history=history,
            bet_sizes=(size,),
            hero_hand=hero_hand,
            solve=solve,
            backend_extra={
                "max_raises": PREFLOP_MAX_RAISES,
                "max_nodes": PREFLOP_MAX_NODES,
                "equity_samples": PREFLOP_EQUITY_SAMPLES,
                "range_shape": shape_name,
                "cell_seed": cell_seed,
            },
        )
    raise ValueError(f"no valid deal for {family} cell {(shape_name, stack, size, label)}")


def _postflop_spot(family: str, seed: int, solve: SolveParams, shape: str, pct: int, role: tuple) -> PracticeSpot:
    label, hero, history = role
    street = "flop" if family == "flop-cbet" else "turn"
    n_board = 3 if street == "flop" else 4
    combos = FLOP_COMBOS_PER_SIDE if street == "flop" else TURN_COMBOS_PER_SIDE
    cell_seed, rng = _cell_rng(seed, family, (shape, pct, label))
    pot = POSTFLOP_POT
    stack = pot * POSTFLOP_SPR
    bet = max(1, (pot * pct + 50) // 100)
    for _attempt in range(_MAX_BOARD_ATTEMPTS):
        board = tuple(rng.sample(range(52), n_board))
        try:
            ranges = river_ranges(board, shape, rng, combos)
        except ValueError:
            continue
        hero_hand = _pick_hero_hand(ranges, hero, rng)
        if hero_hand is None:
            continue
        # Runout cards avoid every range card, so each compatible deal has live runouts.
        dead = set(board) | {card for side in ranges for combo in side for card in combo.cards}
        deck = [card for card in range(52) if card not in dead]
        if street == "flop":
            runouts: list = []
            while len(runouts) < FLOP_RUNOUTS:
                pair = sorted(rng.sample(deck, 2))
                if pair not in runouts:
                    runouts.append(pair)
            runouts.sort()
            extra = {"allowed_runouts": runouts, "max_nodes": 200_000, "max_depth": 64}
            backend = "allstreet"
        else:
            extra = {"allowed_runouts": [[card] for card in sorted(rng.sample(deck, TURN_RUNOUTS))],
                     "max_nodes": 200_000, "max_depth": 64}
            backend = "multistreet"
        extra.update(betting_mode="no-limit", bet_pct=pct, spr=POSTFLOP_SPR, range_shape=shape, cell_seed=cell_seed)
        return PracticeSpot(
            family=family,
            backend=backend,
            game_type="heads-up",
            street=street,
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
            backend_extra=extra,
        )
    raise ValueError(f"no valid board for {family} cell {(shape, pct, label)} after {_MAX_BOARD_ATTEMPTS} attempts")


def _family_spots(family: str, seed: int, solve: SolveParams) -> list[PracticeSpot]:
    if family == "kuhn-intro":
        return _kuhn_spots(solve)
    if family in ("river-oop-bet-or-check", "river-ip-facing-bet"):
        return [
            _river_spot(family, seed, solve, shape, pot, pct)
            for (shape, _o, _i), pot, pct in product(RANGE_SHAPES, RIVER_POTS, RIVER_BET_PCTS)
        ]
    if family == "preflop-hu-open":
        opener = ("btn-first-in", 0, ())
        return [
            _preflop_spot(family, seed, solve, shape, stack, size, opener)
            for shape, stack, size in product(PREFLOP_HU_SHAPES, PREFLOP_HU_STACKS, PREFLOP_HU_OPEN_SIZES)
        ]
    if family == "preflop-3max-open":
        return [
            _preflop_spot(family, seed, solve, shape, PREFLOP_3MAX_STACK, size, situation)
            for situation, shape, size in product(PREFLOP_3MAX_SITUATIONS, PREFLOP_3MAX_SHAPES, PREFLOP_3MAX_OPEN_SIZES)
        ]
    if family in ("flop-cbet", "turn-barrel"):
        return [
            _postflop_spot(family, seed, solve, shape, pct, role)
            for role, (shape, _o, _i), pct in product(POSTFLOP_ROLES, RANGE_SHAPES, POSTFLOP_BET_PCTS)
        ]
    raise ValueError(f"unknown family {family!r}")


def _validate_args(families, seed, solve, limit) -> tuple[tuple[str, ...], SolveParams | None]:
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
    if solve is not None and not isinstance(solve, SolveParams):
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
    family's spots do not depend on which other families are requested.  With
    ``solve=None`` each family uses its :data:`FAMILY_DEFAULT_SOLVE` entry; an
    explicit ``solve`` applies to every family (``spot_id`` never depends on it).
    """
    wanted, solve = _validate_args(families, seed, solve, limit)
    spots: list[PracticeSpot] = []
    for family in FAMILIES:
        if family not in wanted:
            continue
        spots.extend(_family_spots(family, seed, FAMILY_DEFAULT_SOLVE[family] if solve is None else solve))
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
