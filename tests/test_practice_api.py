"""HTTP server + practice API round-trip tests (design report 05)."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from http.client import HTTPConnection
from pathlib import Path
from typing import Any

import pytest

from poker_solver.practice import server as practice_server
from poker_solver.practice.server import make_server

INDEX_HTML = "<!doctype html><html><body><main id=\"app\">practice ✓</main></body></html>"
APP_JS = "console.log('practice');\n"
STYLE_CSS = "body { margin: 0; }\n"


@pytest.fixture()
def web_dir(tmp_path: Path) -> Path:
    d = tmp_path / "web"
    d.mkdir()
    (d / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (d / "app.js").write_text(APP_JS, encoding="utf-8")
    (d / "style.css").write_text(STYLE_CSS, encoding="utf-8")
    # A secret file outside the web dir that traversal must never reach.
    (tmp_path / "secret.txt").write_text("TOP-SECRET", encoding="utf-8")
    return d


def _start(srv):
    t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    t.start()
    return t


def _stop(srv, t):
    try:
        srv.shutdown()
        t.join(5)
    finally:
        srv.server_close()


@pytest.fixture()
def base_url(web_dir: Path):
    srv = make_server("127.0.0.1", 0, web_dir=web_dir)
    t = _start(srv)
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        _stop(srv, t)


def _request(url: str, method: str = "GET", body: bytes | None = None, headers: dict | None = None):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), err.read()


def _raw(base: str, method: str, path: str, body: bytes = b"", headers: dict | None = None):
    """Send a raw request without urllib path normalisation."""
    host, port = base.removeprefix("http://").split(":")
    conn = HTTPConnection(host, int(port), timeout=30)
    try:
        conn.putrequest(method, path, skip_accept_encoding=True)
        for k, v in (headers or {}).items():
            conn.putheader(k, v)
        conn.endheaders()
        if body:
            conn.send(body)
        resp = conn.getresponse()
        return resp.status, dict(resp.getheaders()), resp.read()
    finally:
        conn.close()


def _post_json(base: str, obj: Any) -> tuple[int, dict, Any]:
    body = json.dumps(obj).encode("utf-8")
    status, headers, raw = _request(
        base + "/api/v4", "POST", body, {"Content-Type": "application/json"}
    )
    return status, headers, json.loads(raw)


# ---------------------------------------------------------------- static ---


@pytest.mark.parametrize(
    "path,expected,ctype",
    [
        ("/", INDEX_HTML, "text/html; charset=utf-8"),
        ("/index.html", INDEX_HTML, "text/html; charset=utf-8"),
        ("/app.js", APP_JS, "text/javascript; charset=utf-8"),
        ("/style.css", STYLE_CSS, "text/css; charset=utf-8"),
    ],
)
def test_static_assets(base_url, path, expected, ctype):
    status, headers, body = _request(base_url + path)
    assert status == 200
    assert headers["Content-Type"] == ctype
    assert int(headers["Content-Length"]) == len(body)
    assert body.decode("utf-8") == expected


def test_missing_asset_is_404_json(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    srv = make_server("127.0.0.1", 0, web_dir=empty)
    t = _start(srv)
    try:
        status, headers, body = _request(f"http://127.0.0.1:{srv.server_address[1]}/app.js")
    finally:
        _stop(srv, t)
    assert status == 404
    assert headers["Content-Type"].startswith("application/json")
    assert "error" in json.loads(body)


@pytest.mark.parametrize(
    "path",
    [
        "/../pyproject.toml",
        "/%2e%2e/x",
        "/%2e%2e/secret.txt",
        "/web/../x",
        "/../secret.txt",
        "/..%2fsecret.txt",
        "/secret.txt",
        "/index.html/../../secret.txt",
        "/unknown",
        "/api/v5",
    ],
)
def test_traversal_and_unknown_paths_404(base_url, path):
    status, _, body = _raw(base_url, "GET", path)
    assert status == 404
    assert b"TOP-SECRET" not in body
    assert b"[project]" not in body


def test_health(base_url):
    status, headers, body = _request(base_url + "/api/health")
    assert status == 200
    assert json.loads(body) == {"ok": True}
    assert headers["Cache-Control"] == "no-store"


def test_put_is_405(base_url):
    status, _, body = _raw(base_url, "PUT", "/api/v4", b"{}", {"Content-Length": "2"})
    assert status == 405
    assert "error" in json.loads(body)
    status, _, _ = _raw(base_url, "PUT", "/")
    assert status == 405


def test_get_api_v4_is_405(base_url):
    status, _, _ = _request(base_url + "/api/v4")
    assert status == 405


def test_post_to_static_path_is_405(base_url):
    status, _, _ = _raw(base_url, "POST", "/", b"{}", {"Content-Length": "2"})
    assert status == 405


# ------------------------------------------------------------- api errors ---


def test_malformed_json_400(base_url):
    status, headers, body = _request(base_url + "/api/v4", "POST", b"{not json")
    assert status == 400
    assert headers["Cache-Control"] == "no-store"
    payload = json.loads(body)
    assert "error" in payload and "Traceback" not in payload["error"]


def test_duplicate_keys_400(base_url):
    raw = b'{"version": 4, "version": 4, "operation": "x", "payload": {}}'
    status, _, body = _request(base_url + "/api/v4", "POST", raw)
    assert status == 400
    assert "duplicate" in json.loads(body)["error"]


def test_nan_rejected_400(base_url):
    raw = b'{"version": NaN, "operation": "x", "payload": {}}'
    status, _, _ = _request(base_url + "/api/v4", "POST", raw)
    assert status == 400


def test_non_object_body_400(base_url):
    status, _, _ = _request(base_url + "/api/v4", "POST", b"[1, 2]")
    assert status == 400


def test_oversize_content_length_413(base_url):
    status, _, body = _raw(
        base_url, "POST", "/api/v4", b"", {"Content-Length": str(2 * 1024 * 1024)}
    )
    assert status == 413
    assert "error" in json.loads(body)


def test_missing_and_negative_content_length_400(base_url):
    status, _, _ = _raw(base_url, "POST", "/api/v4")
    assert status == 400
    status, _, _ = _raw(base_url, "POST", "/api/v4", b"", {"Content-Length": "-1"})
    assert status == 400


@pytest.mark.parametrize("version", ["4", 4.0, True])
def test_strict_version_400(base_url, version):
    status, _, payload = _post_json(
        base_url, {"version": version, "operation": "practice-list-spots", "payload": {}}
    )
    assert status == 400
    assert "error" in payload


def test_unknown_operation_400(base_url):
    status, _, payload = _post_json(
        base_url, {"version": 4, "operation": "no-such-op", "payload": {}}
    )
    assert status == 400
    assert "Traceback" not in payload["error"]


def test_dispatch_errors_mapped_to_400(web_dir):
    def bad(data):
        raise KeyError("missing thing")

    srv = make_server("127.0.0.1", 0, web_dir=web_dir, dispatch=bad)
    t = _start(srv)
    try:
        status, _, payload = _post_json(f"http://127.0.0.1:{srv.server_address[1]}", {"a": 1})
    finally:
        _stop(srv, t)
    assert status == 400
    assert payload == {"error": "missing thing"}


def test_injected_dispatch_success(web_dir):
    seen = []

    def echo(data):
        seen.append(data)
        return {"version": 4, "operation": data["operation"], "result": {"ok": 1}}

    srv = make_server("127.0.0.1", 0, web_dir=web_dir, dispatch=echo)
    t = _start(srv)
    try:
        status, headers, payload = _post_json(
            f"http://127.0.0.1:{srv.server_address[1]}",
            {"version": 4, "operation": "x", "payload": {}},
        )
    finally:
        _stop(srv, t)
    assert status == 200
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert headers["Cache-Control"] == "no-store"
    assert payload["result"] == {"ok": 1}
    assert seen == [{"version": 4, "operation": "x", "payload": {}}]


def test_timeout_504(web_dir, monkeypatch):
    monkeypatch.setenv("POKER_PRACTICE_TIMEOUT", "0.2")
    release = threading.Event()

    def slow(data):
        release.wait(5)
        return {"late": True}

    srv = make_server("127.0.0.1", 0, web_dir=web_dir, dispatch=slow)
    t = _start(srv)
    try:
        start = time.monotonic()
        status, _, payload = _post_json(f"http://127.0.0.1:{srv.server_address[1]}", {"a": 1})
        elapsed = time.monotonic() - start
    finally:
        release.set()
        _stop(srv, t)
    assert status == 504
    assert "error" in payload
    assert elapsed < 3


def test_web_dir_env_override(web_dir, monkeypatch):
    monkeypatch.setenv("POKER_PRACTICE_WEB", str(web_dir))
    srv = make_server("127.0.0.1", 0)
    try:
        assert getattr(srv.RequestHandlerClass, "web_dir") == web_dir.resolve()
    finally:
        srv.server_close()


def test_default_web_dir_is_repo_web():
    assert practice_server.DEFAULT_WEB_DIR == Path(__file__).resolve().parents[1] / "web"


# ---------------------------------------------------- practice round trip ---


def _practice_routed() -> bool:
    """True once dispatch_v4 serves 'practice-list-spots' (probe raises ValueError otherwise)."""
    from poker_solver.api_v4 import dispatch_v4

    try:
        dispatch_v4({"version": 4, "operation": "practice-list-spots", "payload": {}})
    except ValueError:
        return False
    return True


practice_routed = pytest.mark.skipif(
    not _practice_routed(), reason="dispatch_v4 does not route 'practice-list-spots' yet"
)


def _spots(base_url):
    status, _, payload = _post_json(
        base_url, {"version": 4, "operation": "practice-list-spots", "payload": {}}
    )
    assert status == 200, payload
    spots = payload["result"]["spots"]
    assert spots
    return spots


def _pick_spot(spots) -> str:
    def family(s):
        return str(s.get("family", "") or s.get("spot_id", "")).lower()

    for key in ("kuhn", "river"):
        for s in spots:
            if key in family(s) or key in str(s.get("spot_id", "")).lower():
                return s["spot_id"]
    return spots[0]["spot_id"]


def _solve(base_url, spot_id, iterations, seed=None):
    body = {
        "version": 4,
        "operation": "practice-solve-spot",
        "payload": {"spot_id": spot_id, "solve": {"iterations": iterations, "seed": seed}},
    }
    status, _, payload = _post_json(base_url, body)
    assert status == 200, payload
    assert payload["version"] == 4
    assert payload["operation"] == "practice-solve-spot"
    return payload["result"]


@practice_routed
def test_http_list_spots(base_url):
    spots = _spots(base_url)
    assert all("spot_id" in s for s in spots)


@practice_routed
def test_http_solve_and_submit(base_url):
    spot_id = _pick_spot(_spots(base_url))
    solved = _solve(base_url, spot_id, 50)
    total = sum(float(item["probability"]) for item in solved["strategy"])
    assert total == pytest.approx(1.0, abs=1e-6)
    assert solved["provenance"]["params_hash"]
    assert solved["provenance"]["iterations"] == 50

    status, _, payload = _post_json(
        base_url,
        {
            "version": 4,
            "operation": "practice-submit-play",
            "payload": {
                "spot_id": spot_id,
                "play": solved["optimal_action"],
                "solve": {"iterations": 50, "seed": None},
            },
        },
    )
    assert status == 200, payload
    score = payload["result"]["score"]
    assert 0 <= score["score"] <= 100
    assert score["grade"]


@practice_routed
def test_http_r1_iterations_change_answer(base_url):
    spot_id = _pick_spot(_spots(base_url))
    low = _solve(base_url, spot_id, 5)
    high = _solve(base_url, spot_id, 300)
    assert low["spot"]["spot_id"] == high["spot"]["spot_id"] == spot_id  # same spot, only solve params differ
    assert low["provenance"]["params_hash"] != high["provenance"]["params_hash"]
    assert (low["strategy"], low.get("range_strategy")) != (
        high["strategy"],
        high.get("range_strategy"),
    )
