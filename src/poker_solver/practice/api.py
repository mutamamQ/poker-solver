"""Strict JSON handlers for the practice v4 operations plus a CLI smoke entry point.

Operations (see research/practice-mode/w1/task-2.md for the exact response shapes):

* ``practice-list-spots``  {families?: [str], seed?: int, limit?: int}
* ``practice-solve-spot``  {spot_id: str, families?: [str], seed?: int, solve?: SolveParams}
* ``practice-submit-play`` {spot_id: str, play: Play, families?, seed?, solve?, user?: str}
* ``practice-progress``    {user?: str, spot_id?: str}            (provenance null)
* ``practice-leaderboard`` {limit?: int 1..100 = 20, family?: str} (provenance null)

``practice-submit-play`` records the attempt in the persisted :class:`ProgressStore`
and returns the updated per-spot entry as ``result.progress``. ``result.progress`` is
``null`` (result keys never change) when the attempt was *not* recorded:

* the store is unavailable or the write failed (recording never fails a submit);
* the submit used a non-canonical solve (W5 F1): progress / leaderboard only count
  attempts scored against the spot's family-default solve (``catalog.FAMILY_DEFAULT_SOLVE``).
  A ``solve`` override is still solved and scored, but it is a practice-only "what if"
  -- otherwise ``solve: {iterations: 1}`` would let a client grade any action Perfect.
  An override equal to the family default (same ``params_hash``) still counts. The
  stored row carries ``params_hash`` of the solve that produced the score;
* the HTTP request already timed out (504): the server's :class:`RequestToken` skips
  the write so a client told "failed" never gets a hidden attempt (W5 F2).

A failed store open is retried after :data:`STORE_RETRY_S` seconds instead of being
latched for the life of the process (W5 F3).

Every response is ``{"version": 4, "operation": op, "result": ..., "provenance": ...}``.
Validation is fail-closed: unknown/missing keys and wrong types (bool is not int) raise
``ValueError``. ``api_v4.dispatch_v4`` is wired to :func:`handle_practice` by the parent.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
import time
from typing import Any, Mapping, Sequence

from .adapter import SolverAdapter
from .catalog import FAMILIES, find_spot, generate_catalog
from .models import SolveParams
from .progress import (DEFAULT_USER, SKIPPED, ProgressStore, current_request_token,
                       validate_user)
from .scoring import score_play

__all__ = [
    "PRACTICE_OPERATIONS",
    "MAX_ITERATIONS",
    "ALGORITHMS",
    "handle_practice",
    "set_progress_store",
    "STORE_RETRY_S",
    "main",
]

PRACTICE_OPERATIONS = frozenset(
    {"practice-list-spots", "practice-solve-spot", "practice-submit-play",
     "practice-progress", "practice-leaderboard"}
)
MAX_ITERATIONS = 20000
ALGORITHMS = frozenset({"vanilla-cfr", "external-sampling-mccfr"})
LEADERBOARD_MAX = 100
LEADERBOARD_DEFAULT = 20

_LOG = logging.getLogger(__name__)


def _build_cache() -> Any:
    """Persistent DiskSolveCache keyed by full params_hash; dict fallback (fail-soft)."""
    try:
        from .solve_cache import DiskSolveCache
    except ImportError as exc:
        _LOG.info("practice: solve_cache module unavailable, using in-memory dict: %s", exc)
        return {}
    try:
        return DiskSolveCache.from_env()
    except Exception as exc:  # noqa: BLE001 - missing module / unwritable dir
        _LOG.warning("practice: disk solve cache unavailable, using in-memory dict: %s", exc)
        return {}


# Module-level adapter: its cache is keyed by the spot's params_hash, so repeated
# solve/submit calls for identical solve parameters reuse one solve (across
# processes too when the disk cache is available).
_ADAPTER = SolverAdapter(cache=_build_cache())

# Progress store is opened lazily on first use so importing this module never
# touches the filesystem. A failed open is retried no more often than every
# STORE_RETRY_S seconds (F3: no permanent latch -> recovers once the dir is fixed).
STORE_RETRY_S = 30.0
_STORE: ProgressStore | None = None
_STORE_RETRY_AT = 0.0  # time.monotonic() before which no reopen is attempted
_STORE_LOCK = threading.Lock()


def _progress_store(*, required: bool) -> ProgressStore | None:
    """Return the shared store. ``required`` -> raise ValueError when unavailable."""
    global _STORE, _STORE_RETRY_AT
    with _STORE_LOCK:
        if _STORE is None and time.monotonic() >= _STORE_RETRY_AT:
            try:
                _STORE = ProgressStore.from_env()
            except Exception as exc:  # noqa: BLE001 - fail-soft
                _LOG.warning("practice: progress store unavailable (retry in %.0f s): %s",
                             STORE_RETRY_S, exc)
                _STORE_RETRY_AT = time.monotonic() + STORE_RETRY_S
        store = _STORE
    if store is None and required:
        raise ValueError("progress store unavailable")
    return store


def set_progress_store(store: ProgressStore | None) -> None:
    """Replace the shared store (tests / embedding). ``None`` re-enables lazy open now."""
    global _STORE, _STORE_RETRY_AT
    with _STORE_LOCK:
        _STORE = store
        _STORE_RETRY_AT = 0.0


# --------------------------------------------------------------------------- validation


def _int(value: Any, label: str, *, minimum: int | None = None,
         maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{label} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{label} must be <= {maximum}")
    return value


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    try:
        value.encode("utf-8")
    except UnicodeError:  # lone surrogates; never echo codec text (F5)
        raise ValueError(f"{label}: invalid string encoding") from None
    return value


def _payload(payload: Any, required: set[str], optional: set[str], label: str) -> dict:
    if not isinstance(payload, Mapping):
        raise ValueError(f"{label} payload must be an object")
    keys = set(payload)
    for key in keys:
        if not isinstance(key, str):
            raise ValueError(f"{label} payload keys must be strings")
    missing = required - keys
    if missing:
        raise ValueError(f"{label} payload missing fields: {sorted(missing)}")
    unknown = keys - required - optional
    if unknown:
        raise ValueError(f"{label} payload has unknown fields: {sorted(unknown)}")
    return dict(payload)


def _families(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("families must be a non-empty list of strings")
    out = tuple(_str(item, "families[]") for item in value)
    if len(set(out)) != len(out):
        raise ValueError("families must not contain duplicates")
    known = set(FAMILIES)
    unknown = [f for f in out if f not in known]
    if unknown:
        raise ValueError(f"unknown families: {unknown}; known: {sorted(known)}")
    return out


def _solve_params(value: Any) -> SolveParams:
    # Omitted fields take the SolveParams defaults; SolveParams enforces the
    # algorithm/seed pairing (vanilla -> seed null, MCCFR -> int seed).
    defaults = SolveParams()
    obj = _payload(value, set(), {"algorithm", "iterations", "seed"}, "solve")
    algorithm = _str(obj.get("algorithm", defaults.algorithm), "solve.algorithm")
    if algorithm not in ALGORITHMS:
        raise ValueError(f"solve.algorithm must be one of {sorted(ALGORITHMS)}")
    iterations = _int(obj.get("iterations", defaults.iterations), "solve.iterations",
                      minimum=1, maximum=MAX_ITERATIONS)
    seed = obj.get("seed", defaults.seed)
    if seed is not None:
        seed = _int(seed, "solve.seed")
    return SolveParams(algorithm=algorithm, iterations=iterations, seed=seed)


def _catalog_args(obj: Mapping[str, Any]) -> tuple[tuple[str, ...] | None, int]:
    families = _families(obj["families"]) if "families" in obj else None
    seed = _int(obj["seed"], "seed") if "seed" in obj else 0
    return families, seed


def _resolve_spot_canonical(obj: Mapping[str, Any]) -> tuple[Any, bool]:
    """``(spot, canonical)``: ``canonical`` iff the effective solve is the family default.

    ``find_spot`` without ``solve`` returns the spot with its family-default solve; an
    override counts as canonical only when it yields the identical ``params_hash``.
    """
    spot_id = _str(obj["spot_id"], "spot_id")
    families, seed = _catalog_args(obj)
    base = find_spot(spot_id, families=families, seed=seed)
    if base is None:
        raise ValueError(f"unknown spot_id {spot_id!r}")
    if "solve" not in obj:
        return base, True
    spot = base.with_solve(_solve_params(obj["solve"]))
    return spot, spot.params_hash() == base.params_hash()


def _resolve_spot(obj: Mapping[str, Any]) -> Any:
    return _resolve_spot_canonical(obj)[0]


def _check_json(response: dict[str, Any]) -> dict[str, Any]:
    """Fail closed if the response is not strict JSON (NaN/inf, non-str keys...)."""
    try:
        json.dumps(response, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"practice response is not JSON-safe: {exc}") from exc
    return response


# --------------------------------------------------------------------------- handlers


def _list_spots(payload: Any) -> tuple[Any, Any]:
    obj = _payload(payload, set(), {"families", "seed", "limit"}, "practice-list-spots")
    families, seed = _catalog_args(obj)
    limit = _int(obj["limit"], "limit", minimum=1) if "limit" in obj else None
    spots = generate_catalog(families=families, seed=seed, limit=limit)
    result = {
        "spots": [spot.to_json() for spot in spots],
        "families": list(families) if families is not None else list(FAMILIES),
    }
    return result, None


def _solve_spot(payload: Any) -> tuple[Any, Any]:
    obj = _payload(payload, {"spot_id"}, {"families", "seed", "solve"},
                   "practice-solve-spot")
    solved = _ADAPTER.solve(_resolve_spot(obj))
    return solved.to_json(), solved.provenance.to_json()


def _submit_play(payload: Any) -> tuple[Any, Any]:
    obj = _payload(payload, {"spot_id", "play"}, {"families", "seed", "solve", "user"},
                   "practice-submit-play")
    user = validate_user(obj["user"]) if "user" in obj else DEFAULT_USER
    spot, canonical = _resolve_spot_canonical(obj)
    solved = _ADAPTER.solve(spot)
    score = score_play(solved, obj["play"])
    # F1: only family-default solves feed progress/leaderboard; overrides -> null.
    progress = _record(user, spot, score) if canonical else None
    result = {"user": user, "score": score.to_json(), "solved": solved.to_json(),
              "progress": progress}
    return result, solved.provenance.to_json()


def _record(user: str, spot: Any, score: Any) -> dict[str, Any] | None:
    """Persist one scored attempt; any store failure -> None (never fails the submit).

    Inside an HTTP request the write goes through the request's ``RequestToken``
    (F2): if the server already answered 504 or the deadline passed, nothing is written.
    """
    token = current_request_token()
    if token is not None and (token.cancelled or token.expired()):
        return None
    try:
        store = _progress_store(required=False)
        if store is None:
            return None

        def write() -> dict[str, Any]:
            return store.record(
                user=user, spot_id=spot.spot_id, family=spot.family, street=spot.street,
                game_type=spot.game_type, score=score.score, grade=score.grade,
                ev_loss_pct=score.ev_loss_pct_pot, params_hash=spot.params_hash())

        out = write() if token is None else token.run_side_effect(write)
        return None if out is SKIPPED else out
    except Exception as exc:  # noqa: BLE001 - fail-soft by contract
        _LOG.warning("practice: failed to record progress: %s", exc)
        return None


def _progress(payload: Any) -> tuple[Any, Any]:
    obj = _payload(payload, set(), {"user", "spot_id"}, "practice-progress")
    user = validate_user(obj["user"]) if "user" in obj else DEFAULT_USER
    spot_id = _str(obj["spot_id"], "spot_id") if "spot_id" in obj else None
    store = _progress_store(required=True)
    try:
        return store.progress(user, spot_id), None
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 - never echo driver/codec text (F5)
        _LOG.warning("practice: progress store error: %s", exc)
        raise ValueError("progress store error") from exc


def _leaderboard(payload: Any) -> tuple[Any, Any]:
    obj = _payload(payload, set(), {"limit", "family"}, "practice-leaderboard")
    limit = (_int(obj["limit"], "limit", minimum=1, maximum=LEADERBOARD_MAX)
             if "limit" in obj else LEADERBOARD_DEFAULT)
    family = _str(obj["family"], "family") if "family" in obj else None
    store = _progress_store(required=True)
    try:
        return {"entries": store.leaderboard(limit=limit, family=family)}, None
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 - never echo driver/codec text (F5)
        _LOG.warning("practice: progress store error: %s", exc)
        raise ValueError("progress store error") from exc


_HANDLERS = {
    "practice-list-spots": _list_spots,
    "practice-solve-spot": _solve_spot,
    "practice-submit-play": _submit_play,
    "practice-progress": _progress,
    "practice-leaderboard": _leaderboard,
}


def handle_practice(operation: str, payload: Any) -> dict[str, Any]:
    """Route one practice operation; returns the strict v4 response envelope."""
    if not isinstance(operation, str) or operation not in PRACTICE_OPERATIONS:
        raise ValueError(f"operation must be one of {sorted(PRACTICE_OPERATIONS)}")
    result, provenance = _HANDLERS[operation](payload)
    return _check_json({"version": 4, "operation": operation, "result": result,
                        "provenance": provenance})


# --------------------------------------------------------------------------- CLI smoke


def _solve_override(iterations: int | None) -> dict[str, Any]:
    if iterations is None:
        return {}
    return {"solve": {"algorithm": "vanilla-cfr", "iterations": iterations, "seed": None}}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m poker_solver.practice.api",
                                     description="Practice-mode API smoke CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    p_list = sub.add_parser("list", help="list catalog spots")
    p_list.add_argument("--family", action="append", dest="families")
    p_list.add_argument("--seed", type=int)
    p_list.add_argument("--limit", type=int)
    p_solve = sub.add_parser("solve", help="solve one spot")
    p_solve.add_argument("spot_id")
    p_solve.add_argument("--iterations", type=int)
    p_submit = sub.add_parser("submit", help="score a pure action")
    p_submit.add_argument("spot_id")
    p_submit.add_argument("kind")
    p_submit.add_argument("amount", nargs="?", type=int)
    p_submit.add_argument("--iterations", type=int)
    p_submit.add_argument("--user")
    p_progress = sub.add_parser("progress", help="show persisted progress for a user")
    p_progress.add_argument("--user")
    p_progress.add_argument("--spot-id", dest="spot_id")
    p_board = sub.add_parser("leaderboard", help="show the persisted leaderboard")
    p_board.add_argument("--limit", type=int)
    p_board.add_argument("--family")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI smoke entry point. Prints one JSON response; exit 2 on ValueError."""
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "list":
            payload: dict[str, Any] = {}
            if args.families:
                payload["families"] = list(args.families)
            if args.seed is not None:
                payload["seed"] = args.seed
            if args.limit is not None:
                payload["limit"] = args.limit
            response = handle_practice("practice-list-spots", payload)
        elif args.command == "solve":
            payload = {"spot_id": args.spot_id, **_solve_override(args.iterations)}
            response = handle_practice("practice-solve-spot", payload)
        elif args.command == "progress":
            payload = {}
            if args.user is not None:
                payload["user"] = args.user
            if args.spot_id is not None:
                payload["spot_id"] = args.spot_id
            response = handle_practice("practice-progress", payload)
        elif args.command == "leaderboard":
            payload = {}
            if args.limit is not None:
                payload["limit"] = args.limit
            if args.family is not None:
                payload["family"] = args.family
            response = handle_practice("practice-leaderboard", payload)
        else:
            play: dict[str, Any] = {"kind": args.kind}
            if args.amount is not None:
                play["amount"] = args.amount
            payload = {"spot_id": args.spot_id, "play": play,
                       **_solve_override(args.iterations)}
            if args.user is not None:
                payload["user"] = args.user
            response = handle_practice("practice-submit-play", payload)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(response, allow_nan=False, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
