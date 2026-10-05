"""Persistent on-disk cache of practice solves, keyed by ``PracticeSpot.params_hash()``.

Every value stored here was produced by a real runtime solve through
:class:`poker_solver.practice.adapter.SolverAdapter`; this module only persists
and reloads those results so repeat requests are instant.  Nothing is ever
pre-solved into the repository (R1): the cache lives in
``$POKER_PRACTICE_CACHE_DIR`` (default ``~/.cache/poker-solver/practice``).

File layout: one ``<params_hash>.json`` file per solve containing
``{"schema", "solver_version", "key", "created_at", "solved", "info_key"}`` where
``solved`` is :meth:`SolvedSpot.to_json` and ``info_key`` is a tagged encoding of
the (arbitrary hashable) solver infoset key.  Files are written atomically
(temp file in the same directory + :func:`os.replace`).  On load the spot is
rebuilt from its canonical parameters (never re-solved) and the result is
rejected -- and the file removed -- if the schema or solver version differs, the
JSON is corrupt, or the rebuilt spot's ``params_hash`` does not match the key.

Before a value is persisted it is round-tripped in memory; if the decoded value
is not exactly equal (field by field, floats exact) the solve is kept in memory
only.  This keeps deserialization generic over backends / game types added later.

CLI::

    python -m poker_solver.practice.solve_cache warm [--families a,b] [--limit N] [--iterations N]
    python -m poker_solver.practice.solve_cache stats
    python -m poker_solver.practice.solve_cache clear
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import re
import sys
import tempfile
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterator, Mapping, MutableMapping

from ..equity import WeightedCombo
from ..model import Action
from .models import (
    SPOT_FORMAT,
    PracticeSpot,
    SolvedSpot,
    SolveParams,
    SolveProvenance,
    action_from_json,
)

__all__ = [
    "SCHEMA",
    "ENV_VAR",
    "DEFAULT_DIR",
    "DiskSolveCache",
    "default_cache_dir",
    "solved_to_record",
    "solved_from_record",
    "main",
]

logger = logging.getLogger(__name__)

SCHEMA = "practice-solve-cache-v1"
ENV_VAR = "POKER_PRACTICE_CACHE_DIR"
DEFAULT_DIR = Path("~/.cache/poker-solver/practice")
_KEY_RE = re.compile(r"^[0-9a-f]{64}$")
_SUFFIX = ".json"
_TMP_PREFIX = ".tmp-"
#: Files larger than this are treated as corrupt (a single solve is a few KB-MB).
MAX_FILE_BYTES = 64 * 1024 * 1024
DEFAULT_MEMORY_ITEMS = 256


def _current_solver_version() -> str:
    # Imported lazily so ``stats``/``clear`` do not pull in every solver backend.
    from .adapter import solver_version

    return solver_version()


def default_cache_dir() -> Path:
    """``$POKER_PRACTICE_CACHE_DIR`` if set and non-empty, else ``~/.cache/poker-solver/practice``."""
    raw = os.environ.get(ENV_VAR, "").strip()
    return Path(raw).expanduser() if raw else DEFAULT_DIR.expanduser()


def _validate_key(key: Any) -> str:
    """Only full lowercase sha256 hex digests are keys (prevents path traversal)."""
    if not isinstance(key, str) or not _KEY_RE.match(key):
        raise ValueError(f"cache key must be a 64-char lowercase sha256 hex digest, got {key!r}")
    return key


# --------------------------------------------------------------------------- info_key codec

# Tagged JSON encoding for arbitrary solver infoset keys.  JSON primitives are
# stored as-is (Python's json round-trips floats exactly and keeps int/float
# distinct); containers and non-JSON scalars are tagged objects.


def _encode_key(value: Any) -> Any:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non-finite float in info_key")
        return value
    if isinstance(value, Action):
        return {"$": "action", "kind": value.kind, "amount": value.amount}
    if isinstance(value, Fraction):
        return {"$": "fraction", "n": value.numerator, "d": value.denominator}
    if isinstance(value, tuple):
        return {"$": "tuple", "v": [_encode_key(item) for item in value]}
    if isinstance(value, list):
        return {"$": "list", "v": [_encode_key(item) for item in value]}
    if isinstance(value, frozenset):
        items = [_encode_key(item) for item in value]
        items.sort(key=lambda item: json.dumps(item, sort_keys=True))
        return {"$": "frozenset", "v": items}
    if isinstance(value, Mapping):
        return {"$": "map", "v": [[_encode_key(k), _encode_key(v)] for k, v in value.items()]}
    raise ValueError(f"unsupported info_key component of type {type(value).__name__}")


def _decode_key(value: Any) -> Any:
    if value is None or isinstance(value, (bool, str, int, float)):
        return value
    if not isinstance(value, dict) or "$" not in value:
        raise ValueError("malformed info_key encoding")
    tag = value["$"]
    if tag == "action":
        return Action(value["kind"], value["amount"])
    if tag == "fraction":
        return Fraction(value["n"], value["d"])
    if tag == "tuple":
        return tuple(_decode_key(item) for item in value["v"])
    if tag == "list":
        return [_decode_key(item) for item in value["v"]]
    if tag == "frozenset":
        return frozenset(_decode_key(item) for item in value["v"])
    if tag == "map":
        return MappingProxyType({_decode_key(k): _decode_key(v) for k, v in value["v"]})
    raise ValueError(f"unknown info_key tag {tag!r}")


# --------------------------------------------------------------------------- SolvedSpot codec


def _spot_from_json(data: Mapping[str, Any]) -> PracticeSpot:
    """Rebuild a :class:`PracticeSpot` from its canonical parameters (no solving).

    Generic over backend/game type: every ``init`` field of ``PracticeSpot`` is read
    from the canonical dict; only fields with structured types get converters, all
    others are passed through and validated by ``PracticeSpot`` itself.
    """
    if not isinstance(data, Mapping):
        raise ValueError("spot must be an object")
    if data.get("format") != SPOT_FORMAT:
        raise ValueError(f"unsupported spot format {data.get('format')!r}")
    converters = {
        "board": lambda v: tuple(v),
        "villain_seats": lambda v: tuple(v),
        "stacks": lambda v: tuple(v),
        "bet_sizes": lambda v: tuple(v),
        "ranges": lambda v: tuple(
            tuple(WeightedCombo(tuple(c["cards"]), c["weight"]) for c in seat) for seat in v
        ),
        "action_history": lambda v: tuple(action_from_json(a) for a in v),
        "hero_hand": lambda v: None if v is None else tuple(v),
        "solve": SolveParams.from_json,
    }
    kwargs: dict[str, Any] = {}
    for f in dataclasses.fields(PracticeSpot):
        if not f.init:
            continue
        if f.name not in data:
            if f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING:
                continue
            raise ValueError(f"spot is missing field {f.name!r}")
        raw = data[f.name]
        kwargs[f.name] = converters[f.name](raw) if f.name in converters else raw
    spot = PracticeSpot(**kwargs)
    if "params_hash" in data and data["params_hash"] != spot.params_hash():
        raise ValueError("rebuilt spot params_hash does not match the stored spot")
    if "spot_id" in data and data["spot_id"] != spot.spot_id:
        raise ValueError("rebuilt spot_id does not match the stored spot")
    return spot


def _provenance_from_json(data: Mapping[str, Any]) -> SolveProvenance:
    if not isinstance(data, Mapping):
        raise ValueError("provenance must be an object")
    names = [f.name for f in dataclasses.fields(SolveProvenance) if f.init]
    missing = [n for n in names if n not in data]
    if missing:
        raise ValueError(f"provenance missing {missing}")
    return SolveProvenance(**{n: data[n] for n in names})


def _policy(entries: Any, value_key: str) -> dict[Action, float]:
    return {action_from_json(e["action"]): e[value_key] for e in entries}


def solved_to_record(solved: SolvedSpot, solver_version: str | None = None) -> dict[str, Any]:
    """JSON-safe on-disk record for ``solved`` (raises ``ValueError`` if not encodable)."""
    if not isinstance(solved, SolvedSpot):
        raise ValueError("value must be a SolvedSpot")
    return {
        "schema": SCHEMA,
        "solver_version": solver_version or solved.provenance.solver_version,
        "key": solved.spot.params_hash(),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "solved": solved.to_json(),
        "info_key": _encode_key(solved.info_key),
    }


def solved_from_record(record: Any, *, key: str | None = None, solver_version: str | None = None) -> SolvedSpot:
    """Decode a record written by :func:`solved_to_record` (fail closed with ``ValueError``)."""
    if not isinstance(record, Mapping):
        raise ValueError("record must be an object")
    if record.get("schema") != SCHEMA:
        raise ValueError(f"schema mismatch: {record.get('schema')!r} != {SCHEMA!r}")
    if solver_version is not None and record.get("solver_version") != solver_version:
        raise ValueError(f"solver_version mismatch: {record.get('solver_version')!r} != {solver_version!r}")
    if key is not None and record.get("key") != key:
        raise ValueError("record key does not match the file key")
    data = record.get("solved")
    if not isinstance(data, Mapping):
        raise ValueError("record has no solved object")
    spot = _spot_from_json(data["spot"])
    if key is not None and spot.params_hash() != key:
        raise ValueError("rebuilt spot params_hash does not match the cache key")
    provenance = _provenance_from_json(data["provenance"])
    if solver_version is not None and provenance.solver_version != solver_version:
        raise ValueError("provenance solver_version mismatch")
    optimal_size = data["optimal_size"]
    return SolvedSpot(
        spot=spot,
        provenance=provenance,
        legal_actions=tuple(action_from_json(a) for a in data["legal_actions"]),
        pot_at_decision=data["pot_at_decision"],
        info_key=_decode_key(record["info_key"]),
        strategy=_policy(data["strategy"], "probability"),
        action_values=_policy(data["action_values"], "q"),
        range_strategy={e["hand"]: _policy(e["strategy"], "probability") for e in data["range_strategy"]},
        optimal_action=action_from_json(data["optimal_action"]),
        optimal_size=optimal_size,
    )


# --------------------------------------------------------------------------- cache


class DiskSolveCache(MutableMapping[str, SolvedSpot]):
    """Thread-safe ``MutableMapping[params_hash, SolvedSpot]`` backed by one JSON file per key.

    A small LRU dict sits in front of the disk.  If the directory cannot be created
    or written, a warning is logged and the cache degrades to memory-only (the
    LRU becomes unbounded for that instance so no solves are lost).
    """

    def __init__(self, directory: str | os.PathLike[str], *, memory_items: int = DEFAULT_MEMORY_ITEMS):
        if isinstance(memory_items, bool) or not isinstance(memory_items, int) or memory_items < 0:
            raise ValueError("memory_items must be a non-negative integer")
        self.directory = Path(directory).expanduser()
        self.memory_items = memory_items
        self._memory: OrderedDict[str, SolvedSpot] = OrderedDict()
        self._lock = threading.RLock()
        self._solver_version = _current_solver_version()
        self.disk_ok = self._init_dir()
        self.hits = 0
        self.misses = 0
        self.discarded = 0

    @classmethod
    def from_env(cls, **kwargs: Any) -> "DiskSolveCache":
        """Cache in ``$POKER_PRACTICE_CACHE_DIR`` or ``~/.cache/poker-solver/practice``."""
        return cls(default_cache_dir(), **kwargs)

    def __repr__(self) -> str:
        mode = "disk" if self.disk_ok else "memory-only"
        return f"DiskSolveCache({str(self.directory)!r}, {mode})"

    # -- setup / paths -------------------------------------------------------------

    def _init_dir(self) -> bool:
        try:
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            fd, probe = tempfile.mkstemp(prefix=_TMP_PREFIX, suffix=".probe", dir=self.directory)
            os.close(fd)
            os.unlink(probe)
            return True
        except OSError as exc:
            logger.warning("practice solve cache dir %s unusable (%s); using memory-only cache", self.directory, exc)
            return False

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}{_SUFFIX}"

    def _discard_file(self, path: Path, reason: str) -> None:
        self.discarded += 1
        logger.warning("discarding practice cache file %s: %s", path.name, reason)
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.warning("could not remove %s: %s", path, exc)

    # -- memory LRU ----------------------------------------------------------------

    def _remember(self, key: str, value: SolvedSpot) -> None:
        self._memory[key] = value
        self._memory.move_to_end(key)
        if self.disk_ok:  # memory-only mode must keep everything
            while len(self._memory) > self.memory_items:
                self._memory.popitem(last=False)

    # -- disk IO -------------------------------------------------------------------

    def _load(self, key: str) -> SolvedSpot | None:
        path = self._path(key)
        try:
            if path.is_symlink() or not path.is_file():
                return None
            if path.stat().st_size > MAX_FILE_BYTES:
                self._discard_file(path, "file too large")
                return None
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            logger.warning("cannot read practice cache file %s: %s", path, exc)
            return None
        try:
            record = json.loads(text)
            return solved_from_record(record, key=key, solver_version=self._solver_version)
        except (ValueError, KeyError, TypeError, AttributeError, IndexError) as exc:
            self._discard_file(path, str(exc) or type(exc).__name__)
            return None

    def _store(self, key: str, value: SolvedSpot) -> bool:
        try:
            record = solved_to_record(value, self._solver_version)
            text = json.dumps(record, sort_keys=True, allow_nan=False, separators=(",", ":"))
            # Persist only if the record decodes back to an exactly equal value.
            if solved_from_record(json.loads(text), key=key, solver_version=self._solver_version) != value:
                raise ValueError("record does not round-trip exactly")
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning("practice solve %s kept in memory only (not serializable: %s)", key[:12], exc)
            return False
        tmp = None
        try:
            fd, tmp = tempfile.mkstemp(prefix=_TMP_PREFIX, suffix=_SUFFIX + ".tmp", dir=self.directory)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self._path(key))
            tmp = None
            return True
        except OSError as exc:
            logger.warning("cannot write practice cache file for %s (%s); kept in memory", key[:12], exc)
            return False
        finally:
            if tmp is not None:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    def _disk_keys(self) -> list[str]:
        if not self.disk_ok:
            return []
        try:
            names = os.listdir(self.directory)
        except OSError:
            return []
        keys = []
        for name in names:
            if name.endswith(_SUFFIX) and _KEY_RE.match(name[: -len(_SUFFIX)]):
                keys.append(name[: -len(_SUFFIX)])
        return sorted(keys)

    # -- MutableMapping ------------------------------------------------------------

    def __getitem__(self, key: str) -> SolvedSpot:
        _validate_key(key)
        with self._lock:
            hit = self._memory.get(key)
            if hit is not None:
                self._memory.move_to_end(key)
                self.hits += 1
                return hit
            value = self._load(key) if self.disk_ok else None
            if value is None:
                self.misses += 1
                raise KeyError(key)
            self._remember(key, value)
            self.hits += 1
            return value

    def __setitem__(self, key: str, value: SolvedSpot) -> None:
        _validate_key(key)
        if not isinstance(value, SolvedSpot):
            raise ValueError("DiskSolveCache values must be SolvedSpot")
        if value.spot.params_hash() != key or value.provenance.params_hash != key:
            raise ValueError("SolvedSpot params_hash does not match the cache key")
        with self._lock:
            self._remember(key, value)
            if self.disk_ok:
                self._store(key, value)

    def __delitem__(self, key: str) -> None:
        _validate_key(key)
        with self._lock:
            found = self._memory.pop(key, None) is not None
            if self.disk_ok:
                try:
                    self._path(key).unlink()
                    found = True
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    logger.warning("cannot remove practice cache file for %s: %s", key[:12], exc)
            if not found:
                raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        try:
            self[key]  # type: ignore[index]
        except KeyError:
            return False
        return True

    def __iter__(self) -> Iterator[str]:
        with self._lock:
            keys = dict.fromkeys(self._disk_keys())
            keys.update(dict.fromkeys(self._memory))
        return iter(list(keys))

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def clear(self) -> int:  # type: ignore[override]
        """Remove every cache file (and stale temp files) and the memory layer; return files removed."""
        removed = 0
        with self._lock:
            self._memory.clear()
            if not self.disk_ok:
                return 0
            try:
                names = os.listdir(self.directory)
            except OSError:
                return 0
            for name in names:
                is_entry = name.endswith(_SUFFIX) and _KEY_RE.match(name[: -len(_SUFFIX)])
                if is_entry or name.startswith(_TMP_PREFIX):
                    try:
                        (self.directory / name).unlink()
                        removed += 1 if is_entry else 0
                    except OSError as exc:
                        logger.warning("cannot remove %s: %s", name, exc)
        return removed

    def stats(self) -> dict[str, Any]:
        """``{dir, disk_ok, count, bytes, memory_items, schema, solver_version}`` (files not validated)."""
        total = 0
        keys = self._disk_keys()
        for key in keys:
            try:
                total += self._path(key).stat().st_size
            except OSError:
                pass
        return {
            "dir": str(self.directory),
            "disk_ok": self.disk_ok,
            "count": len(keys),
            "bytes": total,
            "memory_items": len(self._memory),
            "schema": SCHEMA,
            "solver_version": self._solver_version,
        }


# --------------------------------------------------------------------------- CLI


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m poker_solver.practice.solve_cache",
        description="Persistent practice solve cache (values are always produced by real runtime solves).",
    )
    parser.add_argument("--dir", help=f"cache directory (default ${ENV_VAR} or {DEFAULT_DIR})")
    sub = parser.add_subparsers(dest="command", required=True)
    warm = sub.add_parser("warm", help="pre-solve catalog spots through the real SolverAdapter")
    warm.add_argument("--families", help="comma-separated family names (default: all)")
    warm.add_argument("--limit", type=int, help="max number of spots")
    warm.add_argument("--iterations", type=int, help="override solve iterations (default: family default)")
    warm.add_argument("--seed", type=int, default=0, help="catalog seed (default 0)")
    warm.add_argument("--timeout", type=float, default=600.0, help="per-spot solve budget in seconds")
    sub.add_parser("stats", help="print entry count, bytes and directory")
    sub.add_parser("clear", help="delete every cache file")
    return parser


def _cmd_warm(cache: DiskSolveCache, args: argparse.Namespace) -> int:
    from .adapter import SolverAdapter
    from .catalog import generate_catalog

    families = None
    if args.families:
        families = tuple(f.strip() for f in args.families.split(",") if f.strip())
    solve = None if args.iterations is None else SolveParams(iterations=args.iterations)
    spots = generate_catalog(families, seed=args.seed, solve=solve, limit=args.limit)
    adapter = SolverAdapter(cache=cache, timeout_s=args.timeout)
    hits = misses = errors = 0
    began = time.perf_counter()
    for spot in spots:
        key = spot.params_hash()
        hit = key in cache
        start = time.perf_counter()
        try:
            adapter.solve(spot)
        except ValueError as exc:
            errors += 1
            print(f"error {time.perf_counter() - start:8.3f}s {spot.spot_id} {key[:12]} {exc}", flush=True)
            continue
        hits += hit
        misses += not hit
        status = "hit " if hit else "miss"
        print(f"{status}  {time.perf_counter() - start:8.3f}s {spot.spot_id} {key[:12]}", flush=True)
    print(
        f"warmed {len(spots)} spots: {hits} hit, {misses} miss, {errors} error, "
        f"{time.perf_counter() - began:.2f}s total; dir {cache.directory}"
        + ("" if cache.disk_ok else " (memory-only: directory unusable)")
    )
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    args = _build_parser().parse_args(argv)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    cache = DiskSolveCache(args.dir) if args.dir else DiskSolveCache.from_env()
    try:
        if args.command == "warm":
            return _cmd_warm(cache, args)
        if args.command == "stats":
            stats = cache.stats()
            print(f"dir: {stats['dir']}")
            print(f"count: {stats['count']}")
            print(f"bytes: {stats['bytes']}")
            print(f"disk_ok: {stats['disk_ok']}")
            print(f"schema: {stats['schema']}  solver_version: {stats['solver_version']}")
            return 0
        removed = cache.clear()
        print(f"removed {removed} cache files from {cache.directory}")
        return 0
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
