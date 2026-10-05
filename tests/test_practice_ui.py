"""Live end-to-end tests for the practice UI (design report 05, W2 UI contract).

A REAL server (``make_server`` on port 0) serves the REAL repo ``web/`` dir and
the real ``dispatch_v4``. Static-asset tests skip only while ``web/index.html``
(or the asset under test) does not exist yet; the HTTP/API flow never skips.
"""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from poker_solver.practice import server as practice_server
from poker_solver.practice.server import make_server

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
INDEX = WEB_DIR / "index.html"
APP_JS = WEB_DIR / "app.js"
STYLE_CSS = WEB_DIR / "style.css"

REQUIRED_IDS = (
    "practice-app spot-list spot-status spot-details board-cards pot-value stacks-list "
    "action-history hero-hand action-controls action-size submit-play result-panel "
    "score-value grade-value ev-loss-value optimal-mix range-strategy provenance error-message"
).split()
EXTRA_IDS = "iterations-input resolve-btn feedback-text action-values spot-filter".split()
GRADES = {"Perfect", "Good", "Inaccuracy", "Mistake", "Blunder"}
EXPECTED_CSP = (
    "default-src 'self'; style-src 'self'; script-src 'self'; "
    "img-src 'self' data:; connect-src 'self'"
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")

needs_index = pytest.mark.skipif(not INDEX.exists(), reason="web/index.html not written yet")


def _needs(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"{path.relative_to(REPO_ROOT)} not written yet")


# ------------------------------------------------------------- server/http ---


@pytest.fixture(scope="module")
def base_url():
    srv = make_server("127.0.0.1", 0)  # default web dir == repo web/
    assert getattr(srv.RequestHandlerClass, "web_dir") == WEB_DIR.resolve()
    t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        t.join(5)
        srv.server_close()


def _get(url: str):
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.headers, err.read()


def _api(base: str, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps({"version": 4, "operation": operation, "payload": payload}).encode()
    req = urllib.request.Request(
        base + "/api/v4", data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as err:
        status, raw = err.code, err.read()
    data = json.loads(raw)
    assert status == 200, data
    assert data["version"] == 4 and data["operation"] == operation
    return data["result"]


# ------------------------------------------------------------ server tests ---


def test_default_web_dir_is_repo_root_web():
    assert practice_server.DEFAULT_WEB_DIR == WEB_DIR


def test_favicon_204(base_url):
    status, headers, body = _get(base_url + "/favicon.ico")
    assert status == 204
    assert body == b""
    assert headers["X-Content-Type-Options"] == "nosniff"


def test_module_main_prints_banner():
    """`python -m poker_solver.practice.server` announces its URL on stdout (flushed)."""
    import socket
    import subprocess
    import sys

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        [sys.executable, "-m", "poker_solver.practice.server", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        assert proc.stdout is not None
        line = proc.stdout.readline()
        assert line.strip() == f"Practice server on http://127.0.0.1:{port}/"
    finally:
        proc.terminate()
        proc.wait(10)


def test_health(base_url):
    status, _, body = _get(base_url + "/api/health")
    assert status == 200 and json.loads(body) == {"ok": True}


def test_security_headers_on_static(tmp_path):
    """Headers asserted against a throwaway web dir so this never skips."""
    (tmp_path / "index.html").write_text("<!doctype html><title>x</title>", encoding="utf-8")
    (tmp_path / "app.js").write_text("void 0;\n", encoding="utf-8")
    (tmp_path / "style.css").write_text("body{}\n", encoding="utf-8")
    srv = make_server("127.0.0.1", 0, web_dir=tmp_path)
    t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    t.start()
    try:
        for path in ("/", "/index.html", "/app.js", "/style.css"):
            status, headers, _ = _get(f"http://127.0.0.1:{srv.server_address[1]}{path}")
            assert status == 200, path
            assert headers["X-Content-Type-Options"] == "nosniff"
            assert headers["Content-Security-Policy"] == EXPECTED_CSP
    finally:
        srv.shutdown()
        t.join(5)
        srv.server_close()


@needs_index
def test_security_headers_on_real_index(base_url):
    status, headers, _ = _get(base_url + "/")
    assert status == 200
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Content-Security-Policy"] == EXPECTED_CSP


# ------------------------------------------------------------ static tests ---


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.scripts: list[dict[str, str | None]] = []
        self.links: list[dict[str, str | None]] = []
        self.metas: list[dict[str, str | None]] = []
        self.inline_style_attrs: list[str] = []
        self.inline_handlers: list[str] = []
        self.inline_script_bodies: list[str] = []
        self.style_blocks = 0
        self._in_script_without_src = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(str(a["id"]))
        for name, _ in attrs:
            if name == "style":
                self.inline_style_attrs.append(tag)
            if name.startswith("on"):
                self.inline_handlers.append(f"{tag}[{name}]")
        if tag == "script":
            self.scripts.append(a)
            self._in_script_without_src = not a.get("src")
        elif tag == "link":
            self.links.append(a)
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "style":
            self.style_blocks += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._in_script_without_src = False

    def handle_data(self, data: str) -> None:
        if self._in_script_without_src and data.strip():
            self.inline_script_bodies.append(data.strip()[:60])


def _parse_index(base_url: str) -> _Collector:
    status, _, body = _get(base_url + "/index.html")
    assert status == 200
    parser = _Collector()
    parser.feed(body.decode("utf-8"))
    return parser


@needs_index
def test_index_has_required_dom_ids(base_url):
    doc = _parse_index(base_url)
    ids = set(doc.ids)
    missing = [i for i in REQUIRED_IDS + EXTRA_IDS if i not in ids]
    assert not missing, f"index.html missing contract IDs: {missing}"
    dupes = sorted({i for i in doc.ids if doc.ids.count(i) > 1})
    assert not dupes, f"duplicate ids: {dupes}"


@needs_index
def test_index_links_assets_and_viewport(base_url):
    doc = _parse_index(base_url)
    srcs = [str(s.get("src") or "") for s in doc.scripts]
    assert any(re.fullmatch(r"(\./|/)?app\.js(\?.*)?", s) for s in srcs), srcs
    css = [
        str(link.get("href") or "")
        for link in doc.links
        if "stylesheet" in str(link.get("rel") or "").lower().split()
    ]
    assert any(re.fullmatch(r"(\./|/)?style\.css(\?.*)?", h) for h in css), css
    viewport = [m for m in doc.metas if str(m.get("name") or "").lower() == "viewport"]
    assert viewport and "width=device-width" in str(viewport[0].get("content") or "")


@needs_index
def test_index_is_csp_compatible(base_url):
    """CSP forbids inline script/style: the UI would silently break otherwise."""
    doc = _parse_index(base_url)
    assert not doc.inline_script_bodies, f"inline <script> bodies: {doc.inline_script_bodies}"
    assert not doc.inline_handlers, f"inline event handlers: {doc.inline_handlers}"
    assert not doc.inline_style_attrs, f"style= attributes on: {doc.inline_style_attrs}"
    assert doc.style_blocks == 0, "<style> blocks are blocked by style-src 'self'"


def test_app_js_references_operations():
    _needs(APP_JS)
    src = APP_JS.read_text(encoding="utf-8")
    for op in ("practice-list-spots", "practice-solve-spot", "practice-submit-play"):
        assert op in src, op
    assert "/api/v4" in src


def test_app_js_avoids_csp_blocked_inline_styles():
    """Under style-src 'self', markup ``style="..."`` and setAttribute('style') are
    blocked; CSSOM (el.style.width = ..., style.setProperty) is fine."""
    _needs(APP_JS)
    src = APP_JS.read_text(encoding="utf-8")
    assert not re.search(r"""setAttribute\(\s*['"]style['"]""", src)
    assert not re.search(r"""<[a-zA-Z][^<>]*\sstyle\s*=""", src), "inline style= in HTML string"
    assert not re.search(r"\beval\s*\(|new\s+Function\s*\(", src)


R1_PATTERNS = [
    (re.compile(r"probability\s*:\s*0?\.\d"), "probability literal"),
    (re.compile(r"probability\s*:\s*[01](\.\d+)?\s*[,}]"), "probability literal"),
    (re.compile(r"\b(ev|ev_loss\w*|chosen_q|best_q|worst_q)\s*:\s*-?\d+(\.\d+)?\s*[,}]"), "EV/score literal"),
    (re.compile(r"""grade\s*[:=]\s*['"`](Perfect|Good|Inaccuracy|Mistake|Blunder)"""), "grade literal"),
    (re.compile(r"""['"`]kuhn-intro/"""), "hardcoded kuhn spot_id"),
    (re.compile(r"""['"`]river-[a-z-]+/"""), "hardcoded river spot_id"),
    (re.compile(r"\b(kuhn-intro|river-[a-z-]+)/[0-9a-f]{8,}"), "hardcoded spot_id"),
    (re.compile(r"\b[0-9a-f]{64}\b"), "hardcoded params_hash"),
]


@pytest.mark.parametrize("asset", [APP_JS, STYLE_CSS], ids=["app.js", "style.css"])
def test_r1_no_hardcoded_answers(asset):
    _needs(asset)
    src = asset.read_text(encoding="utf-8")
    hits = []
    for pattern, label in R1_PATTERNS:
        for m in pattern.finditer(src):
            line = src.count("\n", 0, m.start()) + 1
            hits.append(f"{asset.name}:{line}: {label}: {m.group(0)!r}")
    assert not hits, "R1 violations:\n" + "\n".join(hits)


# ----------------------------------------------------------- live e2e flow ---


@pytest.fixture(scope="module")
def spots(base_url):
    result = _api(base_url, "practice-list-spots", {})
    assert result["spots"]
    return result["spots"]


def _pick(spots, family_prefix: str) -> dict[str, Any]:
    for s in spots:
        if str(s["family"]).startswith(family_prefix):
            return s
    pytest.fail(f"no {family_prefix} spot in list")


def _canon_hand(hand: str | list[str]) -> frozenset[str]:
    if isinstance(hand, list):
        hand = "".join(hand)
    return frozenset(hand[i : i + 2] for i in range(0, len(hand), 2)) if len(hand) > 1 else frozenset([hand])


def _check_solved(solved: dict[str, Any], spot: dict[str, Any], iterations: int) -> None:
    assert solved["spot"]["spot_id"] == spot["spot_id"]
    total = sum(float(x["probability"]) for x in solved["strategy"])
    assert total == pytest.approx(1.0, abs=1e-6)
    assert all(0.0 <= float(x["probability"]) <= 1.0 for x in solved["strategy"])
    rs = solved["range_strategy"]
    assert rs, "range_strategy empty"
    for row in rs:
        assert sum(float(x["probability"]) for x in row["strategy"]) == pytest.approx(1.0, abs=1e-6)
    hero = _canon_hand(spot["hero_hand_str"])
    assert any(_canon_hand(row["hand"]) == hero for row in rs), (hero, [r["hand"] for r in rs])
    prov = solved["provenance"]
    assert HEX64.match(prov["params_hash"]), prov["params_hash"]
    assert prov["iterations"] == iterations
    legal = solved["legal_actions"]
    assert solved["optimal_action"] in legal


@pytest.mark.parametrize("family", ["kuhn", "river"])
def test_e2e_solve_and_submit(base_url, spots, family):
    spot = _pick(spots, family)
    solve = {"iterations": 40}
    solved = _api(base_url, "practice-solve-spot", {"spot_id": spot["spot_id"], "solve": solve})
    _check_solved(solved, spot, 40)

    optimal = solved["optimal_action"]
    other = next(a for a in solved["legal_actions"] if a != optimal)
    results = {}
    for label, play in (("optimal", optimal), ("other", other)):
        res = _api(
            base_url,
            "practice-submit-play",
            {"spot_id": spot["spot_id"], "play": play, "solve": solve},
        )
        score = res["score"]
        assert 0.0 <= float(score["score"]) <= 100.0
        assert score["grade"] in GRADES
        assert float(score["ev_loss_chips"]) >= -1e-9
        _check_solved(res["solved"], spot, 40)
        # Submit re-solves with the same params -> same, deterministic answer.
        assert res["solved"]["provenance"]["params_hash"] == solved["provenance"]["params_hash"]
        assert res["solved"]["strategy"] == solved["strategy"]
        results[label] = score
    assert results["optimal"]["ev_loss_chips"] == pytest.approx(0.0, abs=1e-6)
    assert float(results["other"]["ev_loss_chips"]) >= float(results["optimal"]["ev_loss_chips"]) - 1e-9


@pytest.mark.parametrize("family", ["kuhn", "river"])
def test_e2e_r1_iterations_change_answer(base_url, spots, family):
    spot = _pick(spots, family)
    low = _api(base_url, "practice-solve-spot", {"spot_id": spot["spot_id"], "solve": {"iterations": 5}})
    high = _api(base_url, "practice-solve-spot", {"spot_id": spot["spot_id"], "solve": {"iterations": 300}})
    assert low["spot"]["spot_id"] == high["spot"]["spot_id"] == spot["spot_id"]
    assert low["provenance"]["iterations"] == 5 and high["provenance"]["iterations"] == 300
    assert low["provenance"]["params_hash"] != high["provenance"]["params_hash"]
    assert low["strategy"] != high["strategy"]
    assert low["range_strategy"] != high["range_strategy"]
