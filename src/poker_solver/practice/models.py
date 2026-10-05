"""Immutable practice-mode data model.

Every class here is a frozen dataclass that validates fail-closed with
``ValueError`` (``bool`` is never accepted as an integer or a number).  No
strategy, probability or EV values are ever produced here: ``SolvedSpot`` only
*carries* numbers computed at runtime by the solver adapter.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from math import isclose, isfinite
from types import MappingProxyType
from typing import Any, Hashable, Mapping

from ..cards import format_card
from ..equity import WeightedCombo
from ..model import Action

__all__ = [
    "ALGORITHMS",
    "BACKENDS",
    "GAME_TYPES",
    "STREETS",
    "KUHN_CARDS",
    "PREFLOP_BLINDS",
    "PREFLOP_POSITIONS",
    "SPOT_FORMAT",
    "SolveParams",
    "PracticeSpot",
    "SolveProvenance",
    "SolvedSpot",
    "action_to_json",
    "action_from_json",
    "format_hand",
]

SPOT_FORMAT = "practice-spot-v1"
ALGORITHMS = ("vanilla-cfr", "external-sampling-mccfr")
BACKENDS = ("kuhn", "river", "allstreet", "nplayer-preflop", "multistreet")
GAME_TYPES = ("heads-up", "3-max")
STREETS = ("preflop", "flop", "turn", "river")
KUHN_CARDS = ("J", "Q", "K")
_BOARD_LEN = MappingProxyType({"preflop": 0, "flop": 3, "turn": 4, "river": 5})
_SEATS = MappingProxyType({"heads-up": 2, "3-max": 3})
#: backend -> (allowed game types, allowed streets)
_BACKEND_SHAPE = MappingProxyType(
    {
        "kuhn": (("heads-up",), ("preflop",)),
        "river": (("heads-up",), ("river",)),
        "allstreet": (("heads-up",), ("flop",)),
        "nplayer-preflop": (("heads-up", "3-max"), ("preflop",)),
        "multistreet": (("heads-up",), ("turn",)),
    }
)
#: Blinds used by every ``nplayer-preflop`` spot (button = seat 0, chips).
PREFLOP_BLINDS = (1, 2)
#: Seat labels for button = seat 0 (matches ``nplayer_preflop`` position order).
PREFLOP_POSITIONS = MappingProxyType({"heads-up": ("BTN/SB", "BB"), "3-max": ("BTN", "SB", "BB")})
#: Action kinds used by the nplayer-preflop and multistreet/allstreet game states.
_UPPER_KINDS = frozenset({"FOLD", "CHECK", "CALL", "RAISE"})
_MAX_EQUITY_SAMPLES = 5000
_MAX_PREFLOP_RAISES = 4
_FAMILY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
#: Allowed ``backend_extra`` keys: solver inputs plus descriptive generation metadata.
EXTRA_KEYS = frozenset(
    {
        "kuhn_card",
        "allowed_runouts",
        "betting_mode",
        "max_nodes",
        "max_depth",
        "bet_pct",
        "spr",
        "range_shape",
        "cell_seed",
        "max_raises",
        "equity_samples",
    }
)
_KUHN_HISTORIES = MappingProxyType(
    {
        (): 0,
        (Action("check"),): 1,
        (Action("bet"),): 1,
        (Action("check"), Action("bet")): 0,
    }
)


# --------------------------------------------------------------------------- helpers


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_int(value: Any, name: str, *, minimum: int | None = None) -> int:
    if not _is_int(value):
        raise ValueError(f"{name} must be an integer (bool not allowed), got {value!r}")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value!r}")
    return value


def _require_str(value: Any, name: str, allowed: tuple[str, ...]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{name} must be one of {allowed}, got {value!r}")
    return value


def _require_tuple(value: Any, name: str) -> tuple:
    if isinstance(value, (str, bytes)) or not isinstance(value, (tuple, list)):
        raise ValueError(f"{name} must be a tuple or list, got {type(value).__name__}")
    return tuple(value)


def _card(value: Any, name: str) -> int:
    if not _is_int(value) or not 0 <= value < 52:
        raise ValueError(f"{name} must be a card integer in 0..51, got {value!r}")
    return value


def _freeze_json(value: Any, path: str) -> Any:
    """Validate a JSON-safe value and return a recursively frozen copy."""
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{path} must be finite")
        return value
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, f"{path}[]") for item in value)
    if isinstance(value, Mapping):
        out = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} keys must be strings")
            out[key] = _freeze_json(item, f"{path}.{key}")
        return MappingProxyType(out)
    raise ValueError(f"{path} has unsupported value type {type(value).__name__}")


def _thaw_json(value: Any) -> Any:
    """Inverse of :func:`_freeze_json`: fresh mutable JSON tree."""
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _sha256_json(data: Any) -> str:
    text = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def action_to_json(action: Action) -> dict[str, Any]:
    """Serialize an :class:`Action` as ``{"kind", "amount"}``."""
    if not isinstance(action, Action):
        raise ValueError(f"expected Action, got {type(action).__name__}")
    return {"kind": action.kind, "amount": action.amount}


def action_from_json(data: Any) -> Action:
    """Parse ``{"kind": str, "amount": int?}`` into an :class:`Action` (fail closed)."""
    if not isinstance(data, Mapping):
        raise ValueError("action must be an object with 'kind' and optional 'amount'")
    unknown = set(data) - {"kind", "amount"}
    if unknown:
        raise ValueError(f"unknown action keys: {sorted(unknown)}")
    kind = data.get("kind")
    amount = data.get("amount", 0)
    if not isinstance(kind, str) or not kind:
        raise ValueError("action kind must be a non-empty string")
    if not _is_int(amount) or amount < 0:
        raise ValueError("action amount must be a non-negative integer")
    return Action(kind, amount)


def format_hand(cards: tuple[int, ...]) -> str:
    """Format card integers as a compact string, e.g. ``'AsKd'``."""
    return "".join(format_card(card) for card in cards)


# --------------------------------------------------------------------------- SolveParams


@dataclass(frozen=True, slots=True)
class SolveParams:
    """Solver settings. Vanilla CFR requires ``seed=None``; MCCFR requires an int seed."""

    algorithm: str = "vanilla-cfr"
    iterations: int = 200
    seed: int | None = None

    def __post_init__(self) -> None:
        _require_str(self.algorithm, "algorithm", ALGORITHMS)
        _require_int(self.iterations, "iterations", minimum=1)
        if self.algorithm == "vanilla-cfr":
            if self.seed is not None:
                raise ValueError("vanilla-cfr requires seed=None")
        elif not _is_int(self.seed):
            raise ValueError("external-sampling-mccfr requires an integer seed")

    def canonical(self) -> dict[str, Any]:
        """JSON-safe dict."""
        return {"algorithm": self.algorithm, "iterations": self.iterations, "seed": self.seed}

    @classmethod
    def from_json(cls, data: Any) -> "SolveParams":
        """Parse a canonical dict (unknown keys rejected)."""
        if not isinstance(data, Mapping):
            raise ValueError("solve params must be an object")
        unknown = set(data) - {"algorithm", "iterations", "seed"}
        if unknown:
            raise ValueError(f"unknown solve keys: {sorted(unknown)}")
        return cls(
            data.get("algorithm", "vanilla-cfr"),
            data.get("iterations", 200),
            data.get("seed"),
        )


# --------------------------------------------------------------------------- PracticeSpot


def _sanitize_range(raw: Any, board: frozenset[int], seat: int) -> tuple[WeightedCombo, ...]:
    entries = _require_tuple(raw, f"ranges[{seat}]")
    seen: set[tuple[int, int]] = set()
    out: list[WeightedCombo] = []
    for entry in entries:
        if not isinstance(entry, WeightedCombo):
            raise ValueError(f"ranges[{seat}] entries must be WeightedCombo")
        cards = _require_tuple(entry.cards, f"ranges[{seat}] cards")
        if len(cards) != 2:
            raise ValueError(f"ranges[{seat}] combo must have two cards")
        c0, c1 = (_card(c, f"ranges[{seat}] card") for c in cards)
        if c0 == c1:
            raise ValueError(f"ranges[{seat}] combo has duplicate cards")
        weight = entry.weight
        if not _is_number(weight) or not isfinite(weight) or not 0 <= weight <= 1:
            raise ValueError(f"ranges[{seat}] weight must be a finite number in [0, 1]")
        key = (min(c0, c1), max(c0, c1))
        if key in seen:
            raise ValueError(f"ranges[{seat}] has duplicate combo {format_hand(key)}")
        seen.add(key)
        if weight == 0 or board.intersection(key):
            continue
        out.append(WeightedCombo(key, float(weight)))
    out.sort(key=lambda combo: combo.cards)
    if not out:
        raise ValueError(f"ranges[{seat}] has no positive-weight combos off the board")
    return tuple(out)


@dataclass(frozen=True, slots=True)
class PracticeSpot:
    """One drill: a public game position plus the hero's dealt hand and solve settings.

    ``spot_id`` (= ``family/sha256(canonical without solve)[:12]``) is derived and
    stable across solve-parameter changes; ``params_hash()`` covers everything.
    """

    family: str
    backend: str
    game_type: str
    street: str
    board: tuple[int, ...]
    hero_seat: int
    villain_seats: tuple[int, ...]
    ranges: tuple[tuple[WeightedCombo, ...], ...]
    pot: float
    stacks: tuple[int, ...]
    action_history: tuple[Action, ...]
    bet_sizes: tuple[int, ...]
    hero_hand: tuple[int, int] | None
    solve: SolveParams = field(default_factory=SolveParams)
    backend_extra: Mapping[str, Any] = field(default_factory=dict)
    spot_id: str = field(init=False, compare=False, repr=False)
    _params_hash: str = field(init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        setter = object.__setattr__
        if not isinstance(self.family, str) or not _FAMILY_RE.match(self.family):
            raise ValueError(f"family must be lowercase-hyphenated, got {self.family!r}")
        _require_str(self.backend, "backend", BACKENDS)
        _require_str(self.game_type, "game_type", GAME_TYPES)
        _require_str(self.street, "street", STREETS)
        want_games, want_streets = _BACKEND_SHAPE[self.backend]
        if self.game_type not in want_games:
            raise ValueError(f"backend {self.backend} requires game_type in {want_games}")
        if self.street not in want_streets:
            if self.backend == "allstreet" and self.street == "turn":
                raise ValueError("turn start unsupported by the allstreet facade; use backend multistreet")
            raise ValueError(f"backend {self.backend} requires street in {want_streets}")
        n_seats = _SEATS[self.game_type]

        board = tuple(_card(c, "board card") for c in _require_tuple(self.board, "board"))
        if len(set(board)) != len(board):
            raise ValueError("board has duplicate cards")
        if self.backend != "kuhn" and len(board) != _BOARD_LEN[self.street]:
            raise ValueError(f"{self.street} board requires {_BOARD_LEN[self.street]} cards")
        if self.backend == "kuhn" and board:
            raise ValueError("kuhn spots have no board")
        setter(self, "board", board)

        _require_int(self.hero_seat, "hero_seat", minimum=0)
        if self.hero_seat >= n_seats:
            raise ValueError(f"hero_seat must be < {n_seats}")
        villains = tuple(_require_int(v, "villain seat", minimum=0) for v in _require_tuple(self.villain_seats, "villain_seats"))
        expected = tuple(s for s in range(n_seats) if s != self.hero_seat)
        if villains != expected:
            raise ValueError(f"villain_seats must be {expected}")
        setter(self, "villain_seats", villains)

        if not _is_number(self.pot) or not isfinite(self.pot) or self.pot <= 0:
            raise ValueError("pot must be a finite positive number (bool not allowed)")
        setter(self, "pot", float(self.pot))
        stacks = tuple(_require_int(s, "stack", minimum=1) for s in _require_tuple(self.stacks, "stacks"))
        if len(stacks) != n_seats:
            raise ValueError(f"stacks must have {n_seats} entries")
        if self.game_type == "heads-up" and len(set(stacks)) != 1:
            raise ValueError("heads-up spots require equal effective stacks")
        setter(self, "stacks", stacks)

        sizes = tuple(_require_int(b, "bet size", minimum=1) for b in _require_tuple(self.bet_sizes, "bet_sizes"))
        if not sizes or list(sizes) != sorted(set(sizes)):
            raise ValueError("bet_sizes must be non-empty, unique and increasing")
        if sizes[-1] > min(stacks):
            raise ValueError("bet sizes must not exceed the effective stack")
        setter(self, "bet_sizes", sizes)

        history = _require_tuple(self.action_history, "action_history")
        for action in history:
            if not isinstance(action, Action):
                raise ValueError("action_history entries must be Action")
            if action.kind.lower() in ("deal", "runout") or action.amount < 0:
                raise ValueError(f"illegal public action {action!r}")
        setter(self, "action_history", history)

        if not isinstance(self.solve, SolveParams):
            raise ValueError("solve must be SolveParams")
        if not isinstance(self.backend_extra, Mapping):
            raise ValueError("backend_extra must be a mapping")
        unknown = set(self.backend_extra) - EXTRA_KEYS
        if unknown:
            raise ValueError(f"unknown backend_extra keys: {sorted(unknown)}")
        setter(self, "backend_extra", _freeze_json(self.backend_extra, "backend_extra"))

        raw_ranges = _require_tuple(self.ranges, "ranges")
        if self.backend == "kuhn":
            self._validate_kuhn(raw_ranges, stacks, sizes)
            setter(self, "ranges", tuple(() for _ in range(n_seats)))
        else:
            if "kuhn_card" in self.backend_extra:
                raise ValueError("kuhn_card is only valid for the kuhn backend")
            if len(raw_ranges) != n_seats:
                raise ValueError(f"ranges must have {n_seats} entries")
            board_set = frozenset(board)
            ranges = tuple(_sanitize_range(r, board_set, i) for i, r in enumerate(raw_ranges))
            setter(self, "ranges", ranges)
            self._validate_hero_hand(ranges, board_set)
            if self.backend == "river":
                self._validate_river(sizes)
            if self.backend == "allstreet":
                self._validate_runout_extra(board_set, 2)
            if self.backend == "multistreet":
                self._validate_runout_extra(board_set, 1)
            if self.backend == "nplayer-preflop":
                self._validate_preflop(stacks, sizes)
            if self.backend in ("allstreet", "multistreet"):
                for action in history:
                    if action.kind not in _UPPER_KINDS:
                        raise ValueError(f"{self.backend} actions must be one of {sorted(_UPPER_KINDS)}")

        canonical = self.canonical()
        setter(self, "_params_hash", _sha256_json(canonical))
        canonical.pop("solve")
        setter(self, "spot_id", f"{self.family}/{_sha256_json(canonical)[:12]}")

    # -- backend-specific validation -------------------------------------------------

    def _validate_kuhn(self, raw_ranges: tuple, stacks: tuple, sizes: tuple) -> None:
        if any(_require_tuple(r, "ranges entry") for r in raw_ranges) or len(raw_ranges) not in (0, 2):
            raise ValueError("kuhn spots take empty ranges (the game owns its deals)")
        if self.hero_hand is not None:
            raise ValueError("kuhn spots use hero_hand=None and backend_extra.kuhn_card")
        card = self.backend_extra.get("kuhn_card")
        if card not in KUHN_CARDS:
            raise ValueError("kuhn spots require backend_extra.kuhn_card in J/Q/K")
        if self.pot != 2.0 or stacks != (1, 1) or sizes != (1,):
            raise ValueError("kuhn spots require pot=2, stacks=(1,1), bet_sizes=(1,)")
        actor = _KUHN_HISTORIES.get(self.action_history)
        if actor is None:
            raise ValueError("kuhn action_history must be a nonterminal public node")
        if actor != self.hero_seat:
            raise ValueError("hero is not the acting player after this kuhn history")

    def _validate_hero_hand(self, ranges: tuple, board: frozenset[int]) -> None:
        if self.hero_hand is None:
            raise ValueError("hold'em spots require a concrete hero_hand")
        cards = _require_tuple(self.hero_hand, "hero_hand")
        if len(cards) != 2:
            raise ValueError("hero_hand must have two cards")
        c0, c1 = (_card(c, "hero_hand card") for c in cards)
        if c0 == c1:
            raise ValueError("hero_hand has duplicate cards")
        hand = (min(c0, c1), max(c0, c1))
        if board.intersection(hand):
            raise ValueError("hero_hand collides with the board")
        if hand not in {combo.cards for combo in ranges[self.hero_seat]}:
            raise ValueError("hero_hand is not in the (positive-weight) hero range")
        for seat in self.villain_seats:
            if not any(not set(hand).intersection(c.cards) for c in ranges[seat]):
                raise ValueError(f"hero_hand blocks every combo of seat {seat}")
        object.__setattr__(self, "hero_hand", hand)

    def _validate_river(self, sizes: tuple) -> None:
        if len(sizes) != 1:
            raise ValueError("river spots take exactly one bet size")
        bet = Action("bet", sizes[0])
        check = Action("check")
        actors = {(): 0, (check,): 1, (bet,): 1, (check, bet): 0}
        actor = actors.get(self.action_history)
        if actor is None:
            raise ValueError("river action_history must be a nonterminal node of the one-bet tree")
        if actor != self.hero_seat:
            raise ValueError("hero is not the acting player after this river history")

    def _validate_preflop(self, stacks: tuple, sizes: tuple) -> None:
        extra = self.backend_extra
        missing = {"max_nodes", "max_raises", "equity_samples"} - set(extra)
        if missing:
            raise ValueError(f"nplayer-preflop backend_extra missing {sorted(missing)}")
        _require_int(extra["max_nodes"], "max_nodes", minimum=1)
        raises = _require_int(extra["max_raises"], "max_raises", minimum=1)
        if raises > _MAX_PREFLOP_RAISES:
            raise ValueError(f"max_raises must be <= {_MAX_PREFLOP_RAISES}")
        samples = _require_int(extra["equity_samples"], "equity_samples", minimum=1)
        if samples > _MAX_EQUITY_SAMPLES:
            raise ValueError(f"equity_samples must be <= {_MAX_EQUITY_SAMPLES}")
        for key in ("allowed_runouts", "betting_mode", "max_depth"):
            if key in extra:
                raise ValueError(f"{key} is not a nplayer-preflop input")
        small, big = PREFLOP_BLINDS
        if self.pot != float(small + big):
            raise ValueError(f"nplayer-preflop spots require pot = blinds = {small + big}")
        if min(stacks) <= big:
            raise ValueError("preflop stacks must exceed the big blind")
        if sizes[0] <= big:
            raise ValueError("preflop open sizes (raise-to chips) must exceed the big blind")
        for action in self.action_history:
            if action.kind not in _UPPER_KINDS:
                raise ValueError(f"preflop actions must be one of {sorted(_UPPER_KINDS)}")

    def _validate_runout_extra(self, board: frozenset[int], runout_len: int) -> None:
        extra = self.backend_extra
        missing = {"allowed_runouts", "betting_mode", "max_nodes", "max_depth"} - set(extra)
        if missing:
            raise ValueError(f"{self.backend} backend_extra missing {sorted(missing)}")
        if extra["betting_mode"] not in ("no-limit", "pot-limit"):
            raise ValueError("betting_mode must be 'no-limit' or 'pot-limit'")
        for key in ("max_nodes", "max_depth"):
            _require_int(extra[key], key, minimum=1)
        runouts = extra["allowed_runouts"]
        if not isinstance(runouts, tuple) or not runouts:
            raise ValueError("allowed_runouts must be a non-empty list")
        for runout in runouts:
            if not isinstance(runout, tuple) or len(runout) != runout_len:
                raise ValueError(
                    "each runout must have two cards (turn, river)" if runout_len == 2
                    else "each runout must have one card (river)"
                )
            cards = tuple(_card(c, "runout card") for c in runout)
            if len(set(cards)) != len(cards) or board.intersection(cards):
                raise ValueError("runout cards must be distinct and off the board")
        if len(set(runouts)) != len(runouts):
            raise ValueError("allowed_runouts must be unique")
        if float(self.pot) != int(self.pot):
            raise ValueError(f"{self.backend} requires an integer-valued pot")

    # -- identity --------------------------------------------------------------------

    def canonical(self) -> dict[str, Any]:
        """Fresh JSON-safe dict of every solve-relevant field (no derived ids)."""
        return {
            "format": SPOT_FORMAT,
            "family": self.family,
            "backend": self.backend,
            "game_type": self.game_type,
            "street": self.street,
            "board": list(self.board),
            "hero_seat": self.hero_seat,
            "villain_seats": list(self.villain_seats),
            "ranges": [
                [{"cards": list(c.cards), "weight": float(c.weight)} for c in seat_range]
                for seat_range in self.ranges
            ],
            "pot": float(self.pot),
            "stacks": list(self.stacks),
            "action_history": [action_to_json(a) for a in self.action_history],
            "bet_sizes": list(self.bet_sizes),
            "hero_hand": None if self.hero_hand is None else list(self.hero_hand),
            "solve": self.solve.canonical(),
            "backend_extra": _thaw_json(self.backend_extra),
        }

    def params_hash(self) -> str:
        """sha256 hex digest of the canonical JSON (includes ``solve``)."""
        return self._params_hash

    def with_solve(self, solve: SolveParams) -> "PracticeSpot":
        """Same spot (same ``spot_id``) with different solve settings."""
        if not isinstance(solve, SolveParams):
            raise ValueError("solve must be SolveParams")
        return replace(self, solve=solve)

    @property
    def hero_hand_str(self) -> list[str]:
        """Hero hand as card strings, or ``[kuhn_card]`` for Kuhn."""
        if self.backend == "kuhn":
            return [str(self.backend_extra["kuhn_card"])]
        assert self.hero_hand is not None
        return [format_card(c) for c in self.hero_hand]

    @property
    def label(self) -> str:
        """Human description generated from the fields only."""
        hero = "".join(self.hero_hand_str)
        line = " ".join(a.kind + (f" {a.amount}" if a.amount else "") for a in self.action_history) or "first to act"
        if self.backend == "kuhn":
            return f"Kuhn poker: P{self.hero_seat} holding {hero}, line: {line}"
        if self.backend == "nplayer-preflop":
            seat = PREFLOP_POSITIONS[self.game_type][self.hero_seat]
            sizes = "/".join(str(b) for b in self.bet_sizes)
            small, big = PREFLOP_BLINDS
            return (
                f"Preflop {self.game_type} {seat} with {hero}; blinds {small}/{big}, "
                f"stack {self.stacks[0]}, open to {sizes}; line: {line}"
            )
        board = " ".join(format_card(c) for c in self.board)
        position = "OOP" if self.hero_seat == 0 else "IP"
        sizes = "/".join(str(b) for b in self.bet_sizes)
        return (
            f"{self.street.capitalize()} {position} with {hero} on {board}; pot {self.pot:g}, "
            f"stack {self.stacks[0]}, bet {sizes}; line: {line}"
        )

    def to_json(self) -> dict[str, Any]:
        """Canonical dict plus derived ids and display helpers."""
        data = self.canonical()
        data.update(
            spot_id=self.spot_id,
            params_hash=self.params_hash(),
            board_str=[format_card(c) for c in self.board],
            hero_hand_str=self.hero_hand_str,
            label=self.label,
        )
        return data


# --------------------------------------------------------------------------- provenance


@dataclass(frozen=True, slots=True)
class SolveProvenance:
    """Where a solved artifact came from (displayed by UI/CLI)."""

    backend: str
    entrypoint: str
    params: Mapping[str, Any]
    params_hash: str
    algorithm: str
    iterations: int
    seed: int | None
    nash_conv: float | None
    wall_time_s: float
    solver_version: str

    def __post_init__(self) -> None:
        _require_str(self.backend, "backend", BACKENDS)
        if not isinstance(self.entrypoint, str) or not self.entrypoint:
            raise ValueError("entrypoint must be a non-empty string")
        if not isinstance(self.params, Mapping):
            raise ValueError("params must be a mapping")
        object.__setattr__(self, "params", _freeze_json(self.params, "params"))
        if not isinstance(self.params_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", self.params_hash):
            raise ValueError("params_hash must be a 64-char sha256 hex digest")
        _require_str(self.algorithm, "algorithm", ALGORITHMS)
        _require_int(self.iterations, "iterations", minimum=1)
        if self.seed is not None and not _is_int(self.seed):
            raise ValueError("seed must be an integer or None")
        if self.nash_conv is not None and (not _is_number(self.nash_conv) or not isfinite(self.nash_conv)):
            raise ValueError("nash_conv must be finite or None")
        if not _is_number(self.wall_time_s) or not isfinite(self.wall_time_s) or self.wall_time_s < 0:
            raise ValueError("wall_time_s must be a finite non-negative number")
        if not isinstance(self.solver_version, str) or not self.solver_version:
            raise ValueError("solver_version must be a non-empty string")

    def to_json(self) -> dict[str, Any]:
        """JSON-safe dict."""
        return {
            "backend": self.backend,
            "entrypoint": self.entrypoint,
            "params": _thaw_json(self.params),
            "params_hash": self.params_hash,
            "algorithm": self.algorithm,
            "iterations": self.iterations,
            "seed": self.seed,
            "nash_conv": self.nash_conv,
            "wall_time_s": self.wall_time_s,
            "solver_version": self.solver_version,
        }


# --------------------------------------------------------------------------- SolvedSpot


def _check_policy(policy: Any, actions: tuple[Action, ...], name: str) -> Mapping[Action, float]:
    if not isinstance(policy, Mapping) or set(policy) != set(actions):
        raise ValueError(f"{name} must cover exactly the legal actions")
    values = {}
    for action in actions:
        p = policy[action]
        if not _is_number(p) or not isfinite(p) or p < 0:
            raise ValueError(f"{name} has invalid probability for {action!r}")
        values[action] = float(p)
    if not isclose(sum(values.values()), 1.0, abs_tol=1e-9):
        raise ValueError(f"{name} probabilities must sum to 1")
    return MappingProxyType(values)


@dataclass(frozen=True, slots=True)
class SolvedSpot:
    """Solver output for one spot. All numbers come from a runtime solve (or its cache)."""

    spot: PracticeSpot
    provenance: SolveProvenance
    legal_actions: tuple[Action, ...]
    pot_at_decision: float
    info_key: Hashable
    strategy: Mapping[Action, float]
    action_values: Mapping[Action, float]
    range_strategy: Mapping[str, Mapping[Action, float]]
    optimal_action: Action
    optimal_size: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.spot, PracticeSpot):
            raise ValueError("spot must be PracticeSpot")
        if not isinstance(self.provenance, SolveProvenance):
            raise ValueError("provenance must be SolveProvenance")
        if self.provenance.params_hash != self.spot.params_hash():
            raise ValueError("provenance params_hash does not match the spot")
        actions = _require_tuple(self.legal_actions, "legal_actions")
        if not actions or any(not isinstance(a, Action) for a in actions) or len(set(actions)) != len(actions):
            raise ValueError("legal_actions must be unique Actions")
        object.__setattr__(self, "legal_actions", actions)
        if not _is_number(self.pot_at_decision) or not isfinite(self.pot_at_decision) or self.pot_at_decision <= 0:
            raise ValueError("pot_at_decision must be finite and positive")
        object.__setattr__(self, "pot_at_decision", float(self.pot_at_decision))
        object.__setattr__(self, "strategy", _check_policy(self.strategy, actions, "strategy"))
        if not isinstance(self.action_values, Mapping) or set(self.action_values) != set(actions):
            raise ValueError("action_values must cover exactly the legal actions")
        q = {}
        for action in actions:
            value = self.action_values[action]
            if not _is_number(value) or not isfinite(value):
                raise ValueError("action values must be finite numbers")
            q[action] = float(value)
        object.__setattr__(self, "action_values", MappingProxyType(q))
        if not isinstance(self.range_strategy, Mapping):
            raise ValueError("range_strategy must be a mapping")
        object.__setattr__(
            self,
            "range_strategy",
            MappingProxyType(
                {str(h): _check_policy(p, actions, f"range_strategy[{h}]") for h, p in self.range_strategy.items()}
            ),
        )
        if self.optimal_action not in actions:
            raise ValueError("optimal_action must be legal")
        sized = self.optimal_action.kind.lower() in ("bet", "raise") and self.optimal_action.amount > 0
        expected_size = self.optimal_action.amount if sized else None
        if self.optimal_size != expected_size:
            raise ValueError(
                "optimal_size must be the amount of a sized bet/raise optimal action, else None"
            )

    def to_json(self) -> dict[str, Any]:
        """JSON-safe dict; every list follows legal-action order."""
        return {
            "spot": self.spot.to_json(),
            "provenance": self.provenance.to_json(),
            "legal_actions": [action_to_json(a) for a in self.legal_actions],
            "pot_at_decision": self.pot_at_decision,
            "strategy": [
                {"action": action_to_json(a), "probability": self.strategy[a]} for a in self.legal_actions
            ],
            "action_values": [{"action": action_to_json(a), "q": self.action_values[a]} for a in self.legal_actions],
            "range_strategy": [
                {
                    "hand": hand,
                    "strategy": [{"action": action_to_json(a), "probability": policy[a]} for a in self.legal_actions],
                }
                for hand, policy in self.range_strategy.items()
            ],
            "optimal_action": action_to_json(self.optimal_action),
            "optimal_size": self.optimal_size,
        }
