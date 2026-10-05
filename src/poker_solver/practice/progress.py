"""Persisted practice progress tracker (SQLite).

One row per scored attempt; every per-spot / per-user aggregate (attempts, best,
last, timestamps, leaderboard) is computed from those rows at query time. Scores
are only ever written by ``practice.api`` from ``scoring.score_play`` of a real
solve -- this module never invents a score.

* ``ProgressStore(path)``: thread-safe (one connection, ``check_same_thread=False``
  guarded by a lock), WAL journal, versioned schema (``schema_migrations`` table).
* ``ProgressStore.from_env()``: ``$POKER_PRACTICE_DATA_DIR/progress.sqlite3`` or
  ``~/.local/share/poker-solver/practice/progress.sqlite3``.
* All SQL is parameterized.
* Per-spot ``last_*`` fields (score, grade, ``last_at``) all come from the newest row
  (MAX(id)) and ``first_at`` from the oldest row (MIN(id)), so they always describe real,
  consistent attempts even if wall-clock timestamps go backwards (W5 F6).
* Before every operation the DB file's (st_dev, st_ino) is compared with the one the
  connection opened; if the file was deleted or replaced the connection is reopened
  (fresh schema) instead of writing into an unlinked inode (W5 F7).
* :class:`RequestToken` / :func:`request_scope` let the HTTP server cancel the
  progress write of a request that already answered 504 (W5 F2). Stdlib only, so the
  server can import it cheaply.
"""

from __future__ import annotations

import math
import os
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "ProgressStore",
    "USER_RE",
    "DEFAULT_USER",
    "SCHEMA_VERSION",
    "validate_user",
    "default_path",
    "RequestToken",
    "request_scope",
    "current_request_token",
    "SKIPPED",
]

USER_RE = re.compile(r"[A-Za-z0-9_.-]{1,32}")
DEFAULT_USER = "local"
SCHEMA_VERSION = 1
_DB_NAME = "progress.sqlite3"

# Ordered migrations; index i migrates schema version i -> i + 1.
_MIGRATIONS: tuple[tuple[str, ...], ...] = (
    (
        """
        CREATE TABLE IF NOT EXISTS attempts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user        TEXT    NOT NULL,
            spot_id     TEXT    NOT NULL,
            family      TEXT    NOT NULL,
            street      TEXT    NOT NULL,
            game_type   TEXT    NOT NULL,
            score       REAL    NOT NULL,
            grade       TEXT    NOT NULL,
            ev_loss_pct REAL    NOT NULL,
            params_hash TEXT    NOT NULL,
            ts          TEXT    NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_attempts_user_spot ON attempts(user, spot_id, id)",
        "CREATE INDEX IF NOT EXISTS idx_attempts_family ON attempts(family)",
    ),
)


# --------------------------------------------------------------------------- request token


class _Skipped:
    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return "SKIPPED"


#: Sentinel returned by :meth:`RequestToken.run_side_effect` when the write was skipped.
SKIPPED: Any = _Skipped()


class RequestToken:
    """Deadline + cancellation for one server request (W5 F2).

    The server creates one per ``/api/v4`` request; ``practice.api`` performs the
    progress write through :meth:`run_side_effect`. Once the server gave up on the
    request (:meth:`cancel`) or the monotonic ``deadline`` has passed, the write is
    skipped. The write runs under the token lock, so :meth:`cancel` either happens
    strictly before it (write skipped, ``True``) or strictly after it (``False``: the
    attempt was recorded and the caller should deliver the imminent result instead of
    a 504).
    """

    def __init__(self, deadline: float | None = None):
        self.deadline = deadline
        self._lock = threading.Lock()
        self._cancelled = False
        self._committed = False

    @property
    def cancelled(self) -> bool:
        with self._lock:
            return self._cancelled

    def expired(self) -> bool:
        return self.deadline is not None and time.monotonic() >= self.deadline

    def cancel(self) -> bool:
        """Cancel; ``True`` if no side effect was committed (safe to report failure)."""
        with self._lock:
            self._cancelled = True
            return not self._committed

    def run_side_effect(self, fn: Any) -> Any:
        """Run ``fn()`` unless cancelled/expired (-> :data:`SKIPPED`)."""
        with self._lock:
            if self._cancelled or self.expired():
                self._cancelled = True
                return SKIPPED
            self._committed = True
            return fn()


_REQUEST_LOCAL = threading.local()


@contextmanager
def request_scope(token: RequestToken | None):
    """Bind ``token`` to the current thread for the duration of the block."""
    previous = getattr(_REQUEST_LOCAL, "token", None)
    _REQUEST_LOCAL.token = token
    try:
        yield token
    finally:
        _REQUEST_LOCAL.token = previous


def current_request_token() -> RequestToken | None:
    """The token bound by :func:`request_scope` on this thread (``None`` outside a request)."""
    return getattr(_REQUEST_LOCAL, "token", None)


# --------------------------------------------------------------------------- helpers


def validate_user(value: Any) -> str:
    """Return ``value`` if it is a valid user id, else raise ``ValueError``."""
    if not isinstance(value, str) or USER_RE.fullmatch(value) is None:
        raise ValueError("user must match ^[A-Za-z0-9_.-]{1,32}$")
    return value


def default_path() -> Path:
    data_dir = os.environ.get("POKER_PRACTICE_DATA_DIR")
    if data_dir:
        return Path(data_dir) / _DB_NAME
    return Path.home() / ".local" / "share" / "poker-solver" / "practice" / _DB_NAME


def _iso(ts: datetime) -> str:
    # Fixed-width UTC ISO-8601 so lexical order == chronological order.
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{label} must be finite")
    return out


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    _encodable(value, label)
    return value


def _encodable(value: str, label: str) -> str:
    """Reject strings sqlite cannot store (lone surrogates) without leaking codec text (F5)."""
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ValueError(f"{label}: invalid string encoding") from None
    return value


# first_* / last_* come from the MIN(id) / MAX(id) rows, never from MIN/MAX(ts), so
# every field of an entry describes a real attempt (F6). ``{spot_filter}`` is a
# constant fragment, never user data.
_SPOT_SQL = """
WITH g AS (
    SELECT spot_id, COUNT(*) AS attempts, MAX(score) AS best_score,
           MIN(id) AS first_id, MAX(id) AS last_id
    FROM attempts
    WHERE user = ? {spot_filter}
    GROUP BY spot_id
)
SELECT g.spot_id, l.family, l.street, l.game_type, g.attempts, g.best_score,
       l.score AS last_score, l.grade AS last_grade, f.ts AS first_at, l.ts AS last_at
FROM g
JOIN attempts l ON l.id = g.last_id
JOIN attempts f ON f.id = g.first_id
ORDER BY g.spot_id
"""

_SPOT_KEYS = ("spot_id", "family", "street", "game_type", "attempts", "best_score",
              "last_score", "last_grade", "first_at", "last_at")

_LEADERBOARD_SQL = """
WITH per_spot AS (
    SELECT user, spot_id, COUNT(*) AS attempts, MAX(score) AS best
    FROM attempts
    WHERE (? IS NULL OR family = ?)
    GROUP BY user, spot_id
)
SELECT user,
       COUNT(*)      AS spots_attempted,
       SUM(attempts) AS attempts,
       AVG(best)     AS avg_best_score,
       SUM(best)     AS total_best_score
FROM per_spot
GROUP BY user
ORDER BY total_best_score DESC, avg_best_score DESC, user ASC
LIMIT ?
"""


class ProgressStore:
    """SQLite-backed attempt log with per-spot and leaderboard aggregates."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._memory = str(self.path) == ":memory:"
        self._file_id: tuple[int, int] | None = None
        self.reopen_count = 0
        with self._lock:
            self._conn = self._open_locked()

    def _stat_id(self) -> tuple[int, int] | None:
        try:
            st = os.stat(self.path)
        except FileNotFoundError:
            return None
        return (st.st_dev, st.st_ino)

    def _open_locked(self) -> sqlite3.Connection:
        if not self._memory:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path), check_same_thread=False, timeout=10.0,
                               isolation_level=None)
        try:
            conn.execute("PRAGMA busy_timeout = 10000")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            self._conn = conn
            self._migrate()
        except Exception:
            conn.close()
            raise
        if not self._memory:
            self._file_id = self._stat_id()
        return conn

    def _ensure_file_locked(self) -> None:
        """Reopen if the DB file was deleted or replaced since it was opened (F7)."""
        if self._memory:
            return
        current = self._stat_id()
        if current is not None and current == self._file_id:
            return
        try:
            self._conn.close()  # checkpoints into the old (possibly unlinked) inode
        except Exception:  # noqa: BLE001 - old handle is unusable anyway
            pass
        if current is None:
            # The main file is gone: leftover -wal/-shm belong to the deleted DB and
            # must not be replayed onto the fresh one.
            for suffix in ("-wal", "-shm"):
                try:
                    os.unlink(f"{self.path}{suffix}")
                except FileNotFoundError:
                    pass
        self._open_locked()
        self.reopen_count += 1

    @classmethod
    def from_env(cls) -> "ProgressStore":
        return cls(default_path())

    # -- schema ----------------------------------------------------------------------

    def _migrate(self) -> None:
        conn = self._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
            row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
            current = int(row[0])
            if current > SCHEMA_VERSION:
                raise RuntimeError(
                    f"progress db schema v{current} is newer than supported v{SCHEMA_VERSION}")
            for version in range(current, SCHEMA_VERSION):
                for statement in _MIGRATIONS[version]:
                    conn.execute(statement)
                conn.execute("INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                             (version + 1, _iso(datetime.now(timezone.utc))))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def schema_version(self) -> int:
        with self._lock:
            self._ensure_file_locked()
            row = self._conn.execute(
                "SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
        return int(row[0])

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- writes ----------------------------------------------------------------------

    def record(self, *, user: str, spot_id: str, family: str, street: str, game_type: str,
               score: float, grade: str, ev_loss_pct: float, params_hash: str,
               ts: datetime | None = None) -> dict[str, Any]:
        """Insert one attempt; return the user's spot entry after the update."""
        user = validate_user(user)
        row = (
            user,
            _text(spot_id, "spot_id"),
            _text(family, "family"),
            _text(street, "street"),
            _text(game_type, "game_type"),
            _finite(score, "score"),
            _text(grade, "grade"),
            _finite(ev_loss_pct, "ev_loss_pct"),
            _text(params_hash, "params_hash"),
            _iso(ts if ts is not None else datetime.now(timezone.utc)),
        )
        with self._lock:
            self._ensure_file_locked()
            self._conn.execute(
                "INSERT INTO attempts(user, spot_id, family, street, game_type, score, grade,"
                " ev_loss_pct, params_hash, ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", row)
            spots = self._spots_locked(user, spot_id)
        if len(spots) != 1:  # pragma: no cover - defensive
            raise RuntimeError("progress entry missing after insert")
        return spots[0]

    # -- reads -----------------------------------------------------------------------

    def _spots_locked(self, user: str, spot_id: str | None) -> list[dict[str, Any]]:
        if spot_id is None:
            sql, params = _SPOT_SQL.format(spot_filter=""), (user,)
        else:
            sql, params = _SPOT_SQL.format(spot_filter="AND spot_id = ?"), (user, spot_id)
        out = []
        for row in self._conn.execute(sql, params).fetchall():
            entry = dict(zip(_SPOT_KEYS, row))
            entry["attempts"] = int(entry["attempts"])
            entry["best_score"] = float(entry["best_score"])
            entry["last_score"] = float(entry["last_score"])
            out.append(entry)
        return out

    def spots(self, user: str, spot_id: str | None = None) -> list[dict[str, Any]]:
        user = validate_user(user)
        if spot_id is not None:
            spot_id = _text(spot_id, "spot_id")
        with self._lock:
            self._ensure_file_locked()
            return self._spots_locked(user, spot_id)

    def progress(self, user: str, spot_id: str | None = None) -> dict[str, Any]:
        """``{user, totals, spots}`` for ``user`` (optionally one spot)."""
        spots = self.spots(user, spot_id)
        n = len(spots)
        totals = {
            "attempts": sum(s["attempts"] for s in spots),
            "spots_attempted": n,
            "avg_best_score": (sum(s["best_score"] for s in spots) / n) if n else None,
            "avg_last_score": (sum(s["last_score"] for s in spots) / n) if n else None,
        }
        return {"user": user, "totals": totals, "spots": spots}

    def leaderboard(self, limit: int = 20, family: str | None = None) -> list[dict[str, Any]]:
        """Ranked users: total_best_score desc, avg_best_score desc, user asc."""
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        if family is not None:
            family = _text(family, "family")
        with self._lock:
            self._ensure_file_locked()
            rows = self._conn.execute(_LEADERBOARD_SQL, (family, family, limit)).fetchall()
        return [
            {
                "rank": i,
                "user": user,
                "spots_attempted": int(spots),
                "attempts": int(attempts),
                "avg_best_score": float(avg_best),
                "total_best_score": float(total_best),
            }
            for i, (user, spots, attempts, avg_best, total_best) in enumerate(rows, start=1)
        ]
