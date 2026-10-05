"""Minimal stdlib HTTP server for practice mode.

Serves the static practice UI from ``web/`` (strict allow-list) and forwards
``POST /api/v4`` JSON envelopes to :func:`poker_solver.api_v4.dispatch_v4`.

Run with ``python -m poker_solver.practice.server --port 7777``.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

__all__ = [
    "DEFAULT_WEB_DIR",
    "DEFAULT_TIMEOUT_S",
    "MAX_BODY_BYTES",
    "make_server",
    "serve",
    "main",
]

logger = logging.getLogger(__name__)

DEFAULT_WEB_DIR = Path(__file__).resolve().parents[3] / "web"
DEFAULT_TIMEOUT_S = 90.0
MAX_BODY_BYTES = 1024 * 1024  # 1 MiB

# URL path -> (file name inside web dir, content type). Never derived from the URL.
STATIC_ROUTES: dict[str, tuple[str, str]] = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
API_PATH = "/api/v4"
HEALTH_PATH = "/api/health"
KNOWN_PATHS = frozenset(STATIC_ROUTES) | {API_PATH, HEALTH_PATH}

DispatchFn = Callable[[dict[str, Any]], Any]


def _resolve_web_dir(web_dir: str | os.PathLike[str] | None) -> Path:
    if web_dir is not None:
        return Path(web_dir).resolve()
    env = os.environ.get("POKER_PRACTICE_WEB")
    if env:
        return Path(env).resolve()
    return DEFAULT_WEB_DIR


def _timeout_seconds() -> float:
    raw = os.environ.get("POKER_PRACTICE_TIMEOUT")
    if raw:
        try:
            value = float(raw)
            if value > 0:
                return value
        except ValueError:
            pass
    return DEFAULT_TIMEOUT_S


def _default_dispatch(data: dict[str, Any]) -> Any:
    from poker_solver.api_v4 import dispatch_v4

    return dispatch_v4(data)


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key!r}")
        out[key] = value
    return out


def _reject_constant(name: str) -> Any:
    raise ValueError(f"non-finite JSON constant not allowed: {name}")


def parse_json_strict(raw: bytes) -> Any:
    """Parse UTF-8 JSON rejecting duplicate keys and NaN/Infinity."""
    text = raw.decode("utf-8")
    return json.loads(text, object_pairs_hook=_reject_duplicates, parse_constant=_reject_constant)


class _Timeout(Exception):
    pass


def _run_with_timeout(fn: DispatchFn, data: dict[str, Any], timeout: float) -> Any:
    box: dict[str, Any] = {}

    def target() -> None:
        try:
            box["result"] = fn(data)
        except BaseException as exc:  # re-raised in the request thread
            box["error"] = exc

    worker = threading.Thread(target=target, name="practice-dispatch", daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise _Timeout()
    if "error" in box:
        raise box["error"]
    return box.get("result")


class PracticeHandler(BaseHTTPRequestHandler):
    server_version = "PokerPractice/1"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    # Set per-server via a subclass in make_server.
    web_dir: Path = DEFAULT_WEB_DIR
    dispatch: DispatchFn = staticmethod(_default_dispatch)

    # -- helpers ---------------------------------------------------------
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        logger.debug("%s - %s", self.address_string(), format % args)

    def _path(self) -> str:
        return urlsplit(self.path).path

    def _send(self, status: int, body: bytes, content_type: str, *, no_store: bool) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        if no_store:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, status: int, obj: Any, extra_headers: dict[str, str] | None = None) -> None:
        try:
            body = json.dumps(obj, allow_nan=False, separators=(",", ":")).encode("utf-8")
        except (ValueError, TypeError):
            status = 500
            body = b'{"error":"response not JSON-serializable"}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _error(self, status: int, message: str, extra_headers: dict[str, str] | None = None) -> None:
        self._send_json(status, {"error": message}, extra_headers)

    def _method_not_allowed(self) -> None:
        path = self._path()
        if path in KNOWN_PATHS:
            allow = "POST" if path == API_PATH else "GET, HEAD"
            self.close_connection = True
            self._error(405, "method not allowed", {"Allow": allow})
        else:
            self.close_connection = True
            self._error(404, "not found")

    # -- methods ---------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        path = self._path()
        if path == HEALTH_PATH:
            self._send_json(200, {"ok": True})
            return
        route = STATIC_ROUTES.get(path)
        if route is None:
            if path == API_PATH:
                self._error(405, "method not allowed", {"Allow": "POST"})
            else:
                self._error(404, "not found")
            return
        name, content_type = route
        file_path = self.web_dir / name  # name comes from the allow-list only
        try:
            body = file_path.read_bytes()
        except OSError:
            self._error(404, "not found")
            return
        self._send(200, body, content_type, no_store=False)

    do_HEAD = do_GET

    def do_POST(self) -> None:  # noqa: N802
        path = self._path()
        if path != API_PATH:
            self._method_not_allowed()
            return
        raw_len = self.headers.get("Content-Length")
        if raw_len is None:
            self.close_connection = True
            self._error(400, "Content-Length required")
            return
        try:
            length = int(raw_len.strip())
        except ValueError:
            self.close_connection = True
            self._error(400, "invalid Content-Length")
            return
        if length < 0:
            self.close_connection = True
            self._error(400, "invalid Content-Length")
            return
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            self._error(413, f"request body exceeds {MAX_BODY_BYTES} bytes")
            return
        raw = self.rfile.read(length) if length else b""
        if len(raw) != length:
            self.close_connection = True
            self._error(400, "incomplete request body")
            return
        try:
            data = parse_json_strict(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            self._error(400, f"malformed JSON: {exc}")
            return
        if not isinstance(data, dict):
            self._error(400, "request must be a JSON object")
            return
        try:
            result = _run_with_timeout(type(self).dispatch, data, _timeout_seconds())
        except _Timeout:
            self._error(504, "solve timed out")
            return
        except (ValueError, TypeError, KeyError) as exc:
            message = exc.args[0] if isinstance(exc, KeyError) and exc.args else exc
            self._error(400, str(message))
            return
        except Exception:  # pragma: no cover - defensive
            logger.exception("unhandled error in /api/v4 dispatch")
            self._error(500, "internal server error")
            return
        self._send_json(200, result)

    def do_PUT(self) -> None:  # noqa: N802
        self._method_not_allowed()

    do_DELETE = do_PUT
    do_PATCH = do_PUT
    do_OPTIONS = do_PUT


def make_server(
    host: str = "127.0.0.1",
    port: int = 7777,
    web_dir: str | os.PathLike[str] | None = None,
    dispatch: DispatchFn | None = None,
) -> ThreadingHTTPServer:
    """Create (but do not start) the practice server. ``port=0`` picks a free port."""
    attrs: dict[str, Any] = {"web_dir": _resolve_web_dir(web_dir)}
    if dispatch is not None:
        attrs["dispatch"] = staticmethod(dispatch)
    handler = type("BoundPracticeHandler", (PracticeHandler,), attrs)
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def serve(
    host: str = "127.0.0.1",
    port: int = 7777,
    web_dir: str | os.PathLike[str] | None = None,
) -> None:
    server = make_server(host, port, web_dir)
    try:
        bound_host, bound_port = server.server_address[:2]
        print(f"Practice server on http://{bound_host}:{bound_port}/", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="poker_solver.practice.server", description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--web-dir", default=None)
    args = parser.parse_args(argv)
    serve(args.host, args.port, args.web_dir)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
