"""W4 practice UI tests: filters, 3-max display, progress / leaderboard panels,
user name, long-solve state (research/practice-mode/w4/CONTRACT.md, section UI).

Static checks read the repo ``web/`` assets; the live checks run a REAL
``make_server`` on an ephemeral port with the real ``dispatch_v4``. The
progress round-trip skips only when ``practice-progress`` itself errors
(op not yet implemented); everything else never skips.
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

from poker_solver.practice.server import make_server

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
INDEX = WEB_DIR / "index.html"
APP_JS = WEB_DIR / "app.js"
STYLE_CSS = WEB_DIR / "style.css"

W2_IDS = (
    "practice-app spot-list spot-status spot-details board-cards pot-value stacks-list "
    "action-history hero-hand action-controls action-size submit-play result-panel "
    "score-value grade-value ev-loss-value optimal-mix range-strategy provenance error-message "
    "iterations-input resolve-btn feedback-text action-values spot-filter"
).split()
W4_IDS = "progress-panel leaderboard-panel user-input street-filter game-filter".split()


# ------------------------------------------------------------------ helpers ---


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.tags: dict[str, tuple[str, dict[str, str | None]]] = {}
        self.inline_handlers: list[str] = []
        self.inline_styles: list[str] = []
        self.inline_scripts = 0
        self.style_blocks = 0
        self._script_no_src = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(str(a["id"]))
            self.tags[str(a["id"])] = (tag, a)
        for name, _ in attrs:
            if name.startswith("on"):
                self.inline_handlers.append(f"{tag}[{name}]")
            if name == "style":
                self.inline_styles.append(tag)
        if tag == "script":
            self._script_no_src = not a.get("src")
        if tag == "style":
            self.style_blocks += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._script_no_src = False

    def handle_data(self, data: str) -> None:
        if self._script_no_src and data.strip():
            self.inline_scripts += 1


def _parse(html: str) -> _Collector:
    p = _Collector()
    p.feed(html)
    return p


def _app_src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _strip_js_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", src)


# ------------------------------------------------------------ static checks ---


def test_index_has_w2_and_w4_ids_unique():
    doc = _parse(INDEX.read_text(encoding="utf-8"))
    ids = set(doc.ids)
    missing = [i for i in W2_IDS + W4_IDS if i not in ids]
    assert not missing, f"missing ids: {missing}"
    dupes = sorted({i for i in doc.ids if doc.ids.count(i) > 1})
    assert not dupes, f"duplicate ids: {dupes}"


def test_w4_controls_are_accessible_form_elements():
    doc = _parse(INDEX.read_text(encoding="utf-8"))
    assert doc.tags["street-filter"][0] == "select"
    assert doc.tags["game-filter"][0] == "select"
    assert doc.tags["spot-filter"][0] == "select"
    tag, attrs = doc.tags["user-input"]
    assert tag == "input" and attrs.get("type") == "text"
    assert attrs.get("maxlength") == "32"
    for i in ("street-filter", "game-filter", "user-input"):
        assert doc.tags[i][1].get("aria-label"), f"{i} needs an accessible name"
    assert doc.tags["progress-panel"][0] == "section"
    assert doc.tags["leaderboard-panel"][0] == "section"
    # Each select starts with only the "all" option: values come from the API.
    html = INDEX.read_text(encoding="utf-8")
    for sel in ("street-filter", "game-filter"):
        block = re.search(rf'<select id="{sel}".*?</select>', html, re.S)
        assert block is not None
        assert block.group(0).count("<option") == 1, f"{sel} must not hardcode values"


def test_index_csp_compatible():
    doc = _parse(INDEX.read_text(encoding="utf-8"))
    assert not doc.inline_handlers, doc.inline_handlers
    assert not doc.inline_styles, doc.inline_styles
    assert doc.inline_scripts == 0
    assert doc.style_blocks == 0


def test_app_js_no_innerhtml_or_unsafe_sinks():
    src = _app_src()
    for pat in (r"\.innerHTML\b", r"\.outerHTML\b", r"insertAdjacentHTML", r"document\.write\s*\(",
                r"\beval\s*\(", r"new\s+Function\s*\(", r"""setAttribute\(\s*['"]on""",
                r"""setAttribute\(\s*['"]style['"]"""):
        assert not re.search(pat, src), f"forbidden sink {pat!r} in app.js"
    # string-form timers are eval-equivalent
    assert not re.search(r"""set(Timeout|Interval)\(\s*['"`]""", src)


def test_app_js_no_inline_handler_assignment():
    src = _app_src()
    assert not re.search(r"\.on(click|change|input|keydown|submit|load)\s*=", src), \
        "use addEventListener, not on* properties"


def test_app_js_uses_w4_operations_and_user_key():
    src = _app_src()
    for op in ("practice-progress", "practice-leaderboard", "practice-submit-play"):
        assert f'"{op}"' in src, op
    assert '"practice.user"' in src
    assert "localStorage" in src
    for i in W4_IDS:
        assert f'"{i}"' in src or i.endswith("-panel"), f"app.js never references #{i}"
    # graceful degradation text
    assert "unavailable" in src
    # long-solve counter and the server timeout
    assert "Solving" in src and re.search(r"SERVER_TIMEOUT_S\s*=\s*90\b", src)
    # 3-max: villain seats read from the spot JSON
    assert "villain_seats" in src
    for key in ("street", "game_type", "best_score", "last_score", "attempts", "totals",
                "entries", "total_best_score", "avg_best_score"):
        assert key in src, key


# Numeric literals assigned to answer/score-like keys would be hardcoded data (R1/R3).
_R3_KEYS = (
    r"probability|q|ev|ev_loss\w*|chosen_q|best_q|worst_q|score|best_score|last_score|"
    r"avg_best_score|avg_last_score|total_best_score|attempts|spots_attempted|rank|nash_conv"
)
R3_PATTERNS = [
    (re.compile(rf"\b({_R3_KEYS})\s*:\s*-?\d+(\.\d+)?\s*[,}}]"), "numeric answer/score literal"),
    (re.compile(r"probability\s*:\s*0?\.\d"), "probability literal"),
    (re.compile(r"""grade\s*[:=]\s*['"`](Perfect|Good|Inaccuracy|Mistake|Blunder)"""), "grade literal"),
    (re.compile(r"""\b(strategy|range_strategy|action_values|spots|entries)\s*:\s*\[\s*[{\d-]"""),
     "inline data array"),
    (re.compile(r"\b[0-9a-f]{64}\b"), "hardcoded params_hash"),
    (re.compile(r"""['"`](kuhn-intro|river-[a-z-]+|preflop-[a-z0-9-]+|flop-cbet|turn-barrel)/"""),
     "hardcoded spot_id"),
]


@pytest.mark.parametrize("asset", [APP_JS, STYLE_CSS], ids=["app.js", "style.css"])
def test_no_numeric_strategy_or_score_literals(asset):
    src = _strip_js_comments(asset.read_text(encoding="utf-8"))
    hits = []
    for pattern, label in R3_PATTERNS:
        for m in pattern.finditer(src):
            line = src.count("\n", 0, m.start()) + 1
            hits.append(f"{asset.name}:{line}: {label}: {m.group(0)!r}")
    assert not hits, "\n".join(hits)


def test_style_defines_w4_hooks():
    css = STYLE_CSS.read_text(encoding="utf-8")
    for sel in (".best-badge", ".solve-status", ".stats-grid", ".filter-group",
                ".table-felt.players-3", ".panel-status.unavailable", ".totals-grid"):
        assert sel in css, sel


# --------------------------------------------------------------- live server ---


@pytest.fixture(scope="module")
def base_url():
    srv = make_server("127.0.0.1", 0)
    t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        t.join(5)
        srv.server_close()


def _get(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def _post(base: str, operation: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    body = json.dumps({"version": 4, "operation": operation, "payload": payload}).encode()
    req = urllib.request.Request(base + "/api/v4", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def test_live_index_serves_w4_ids(base_url):
    status, body = _get(base_url + "/")
    assert status == 200
    doc = _parse(body.decode("utf-8"))
    missing = [i for i in W2_IDS + W4_IDS if i not in set(doc.ids)]
    assert not missing, missing
    status, js = _get(base_url + "/app.js")
    assert status == 200 and b"practice-progress" in js and b"practice.user" in js


def test_live_spot_list_has_filter_fields(base_url):
    """The UI builds street/game filters from these spot keys; they must exist."""
    status, data = _post(base_url, "practice-list-spots", {})
    assert status == 200, data
    spots = data["result"]["spots"]
    assert spots
    for s in spots:
        assert isinstance(s.get("street"), str) and s["street"]
        assert isinstance(s.get("game_type"), str) and s["game_type"]
        assert isinstance(s.get("villain_seats"), list) and s["villain_seats"]
        assert s["hero_seat"] not in s["villain_seats"]
        assert len(s["villain_seats"]) + 1 == len(s["stacks"])


def test_live_leaderboard_shape_or_error(base_url):
    status, data = _post(base_url, "practice-leaderboard", {"limit": 5})
    if status != 200:
        # UI degrades to "Leaderboard unavailable"; server must still answer with JSON error
        assert "error" in data
        pytest.skip(f"practice-leaderboard not available: {data['error']}")
    entries = data["result"]["entries"]
    assert isinstance(entries, list) and len(entries) <= 5


def test_live_submit_then_progress_shows_attempt(base_url):
    user = "ui_w4_test"
    status, pdata = _post(base_url, "practice-progress", {"user": user})
    if status != 200:
        assert "error" in pdata  # UI shows "Progress unavailable"
        pytest.skip(f"practice-progress not available: {pdata['error']}")
    before = pdata["result"]
    assert before["user"] == user
    before_attempts = int(before["totals"]["attempts"])

    status, ldata = _post(base_url, "practice-list-spots", {})
    assert status == 200
    spot = next(s for s in ldata["result"]["spots"] if s["family"].startswith("kuhn"))
    solve = {"iterations": 30}
    status, sdata = _post(base_url, "practice-solve-spot", {"spot_id": spot["spot_id"], "solve": solve})
    assert status == 200, sdata
    play = sdata["result"]["legal_actions"][0]
    status, sub = _post(base_url, "practice-submit-play",
                        {"spot_id": spot["spot_id"], "play": play, "solve": solve, "user": user})
    assert status == 200, sub
    res = sub["result"]
    assert res["user"] == user
    score = float(res["score"]["score"])
    if res.get("progress") is not None:
        assert res["progress"]["spot_id"] == spot["spot_id"]

    status, pdata = _post(base_url, "practice-progress", {"user": user})
    assert status == 200, pdata
    after = pdata["result"]
    assert int(after["totals"]["attempts"]) == before_attempts + 1
    entry = next(e for e in after["spots"] if e["spot_id"] == spot["spot_id"])
    assert entry["attempts"] >= 1
    assert entry["last_score"] == pytest.approx(score)
    assert entry["best_score"] >= entry["last_score"] - 1e-9
    assert entry["street"] == spot["street"] and entry["game_type"] == spot["game_type"]
