"""Strict JSON handlers for the practice v4 operations plus a CLI smoke entry point.

Operations (see research/practice-mode/w1/task-2.md for the exact response shapes):

* ``practice-list-spots``  {families?: [str], seed?: int, limit?: int}
* ``practice-solve-spot``  {spot_id: str, families?: [str], seed?: int, solve?: SolveParams}
* ``practice-submit-play`` {spot_id: str, play: Play, families?, seed?, solve?, user?: str}

Every response is ``{"version": 4, "operation": op, "result": ..., "provenance": ...}``.
Validation is fail-closed: unknown/missing keys and wrong types (bool is not int) raise
``ValueError``. ``api_v4.dispatch_v4`` is wired to :func:`handle_practice` by the parent.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Mapping, Sequence

from .adapter import SolverAdapter
from .catalog import FAMILIES, find_spot, generate_catalog
from .models import SolveParams
from .scoring import score_play

__all__ = [
    "PRACTICE_OPERATIONS",
    "MAX_ITERATIONS",
    "ALGORITHMS",
    "handle_practice",
    "main",
]

PRACTICE_OPERATIONS = frozenset(
    {"practice-list-spots", "practice-solve-spot", "practice-submit-play"}
)
MAX_ITERATIONS = 20000
ALGORITHMS = frozenset({"vanilla-cfr", "external-sampling-mccfr"})

# Module-level adapter: its cache is keyed by the spot's params_hash, so repeated
# solve/submit calls for identical solve parameters reuse one solve.
_ADAPTER = SolverAdapter()


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


def _resolve_spot(obj: Mapping[str, Any]) -> Any:
    spot_id = _str(obj["spot_id"], "spot_id")
    families, seed = _catalog_args(obj)
    spot = find_spot(spot_id, families=families, seed=seed)
    if spot is None:
        raise ValueError(f"unknown spot_id {spot_id!r}")
    if "solve" in obj:
        spot = spot.with_solve(_solve_params(obj["solve"]))
    return spot


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
    user = _str(obj["user"], "user") if "user" in obj else "local"
    spot = _resolve_spot(obj)
    solved = _ADAPTER.solve(spot)
    score = score_play(solved, obj["play"])
    result = {"user": user, "score": score.to_json(), "solved": solved.to_json()}
    return result, solved.provenance.to_json()


_HANDLERS = {
    "practice-list-spots": _list_spots,
    "practice-solve-spot": _solve_spot,
    "practice-submit-play": _submit_play,
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
