"""W5 repair-D: regression tests for the 7 UI audit findings
(research/practice-mode/w5-audit/audit-ui.md, fixes in research/practice-mode/w5/repair-ui.md).

Static checks read ``web/``. Live checks start a REAL ``make_server`` on an ephemeral
port (real ``dispatch_v4``, isolated progress store) and drive headless Chrome over the
DevTools protocol with a tiny stdlib WebSocket client (no third-party deps). Browser
tests skip only when no Chrome/Chromium binary is installed.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from poker_solver.practice import api as practice_api
from poker_solver.practice.progress import ProgressStore
from poker_solver.practice.server import make_server

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
APP_JS = WEB_DIR / "app.js"
STYLE_CSS = WEB_DIR / "style.css"
INDEX = WEB_DIR / "index.html"

NEW_FAMILIES = ("preflop-hu-open", "preflop-3max-open", "flop-cbet", "turn-barrel")


def _src() -> str:
    return APP_JS.read_text(encoding="utf-8")


def _css() -> str:
    return STYLE_CSS.read_text(encoding="utf-8")


def _fn(src: str, name: str) -> str:
    m = re.search(rf"function {name}\(.*?\n  }}\n", src, re.S)
    assert m, f"function {name} not found"
    return m.group(0)


# ------------------------------------------------------------- static checks ---


def test_1_kinds_compared_case_insensitively():
    src = _src()
    assert "function normKind" in src and "toLowerCase()" in _fn(src, "normKind")
    # no raw case-sensitive lookups left
    assert not re.search(r"SIZED_KINDS\[\s*a\.kind\s*\]", src)
    assert not re.search(r"SIZED_KINDS\[\s*sel\.kind\s*\]", src)
    assert not re.search(r"acts\[i\]\.kind\s*===", src)
    assert "normKind(a.kind)" in _fn(src, "indexesByKinds")
    # play sent to the API keeps the original kind string
    assert re.search(r"return \{ kind: a\.kind, amount: amount \}", _fn(src, "currentPlay"))


def test_2_best_badge_not_coloured_by_last_grade():
    body = _fn(_src(), "bestBadge")
    assert "last_grade" not in body.replace("(only last_grade)", "")
    assert "grade-" not in body
    css = _css()
    tail = css[css.index("W5 UI repairs"):]
    assert ".best-badge {" in tail


def test_3_user_change_rerenders_and_reloads_leaderboard():
    body = _fn(_src(), "applyUser")
    assert "rerenderLeaderboard()" in body and "loadLeaderboard()" in body


def test_4_stats_tables_fit_panel_css():
    css = _css()
    tail = css[css.index("W5 UI repairs"):]
    assert "container-type: inline-size" in tail
    assert "@container (max-width: 640px)" in tail
    assert "attr(data-label)" in tail
    assert "cell.dataset.label" in _src()


def test_6_focus_restored_after_submit_static():
    body = _fn(_src(), "submitPlay")
    assert 'focusEl(ok ? $("next-spot") : $("submit-play"))' in body


def test_7_labels_humanized_display_only():
    src = _src()
    assert "kindLabel(a.kind)" in _fn(src, "actionLabel")
    assert '"Raise"' in src and '"Fold"' in src


def test_hint_lists_shortcuts_and_csp_rules_hold():
    html = INDEX.read_text(encoding="utf-8")
    assert "B bet/raise" in html
    assert not re.search(r"\son[a-z]+=", html) and "<style" not in html and " style=" not in html
    src = _src()
    assert not re.search(r"\.innerHTML\b|insertAdjacentHTML|\beval\s*\(", src)


# ---------------------------------------------------------- live server + CDP ---


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    store = ProgressStore(tmp_path_factory.mktemp("w5ui") / "progress.sqlite3")
    practice_api.set_progress_store(store)
    srv = make_server("127.0.0.1", 0)
    t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        t.join(5)
        srv.server_close()
        practice_api.set_progress_store(None)


def _post(base: str, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps({"version": 4, "operation": operation, "payload": payload}).encode()
    req = urllib.request.Request(base + "/api/v4", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())["result"]


@pytest.fixture(scope="module")
def first_spots(base_url) -> dict[str, str]:
    out: dict[str, str] = {}
    for s in _post(base_url, "practice-list-spots", {})["spots"]:
        out.setdefault(s["family"], s["spot_id"])
    return out


@pytest.mark.parametrize("family", NEW_FAMILIES)
def test_live_api_new_families_have_sized_uppercase_actions(base_url, first_spots, family):
    """The UI must work with these: uppercase kinds and RAISE amounts > 0."""
    acts = _post(base_url, "practice-solve-spot", {"spot_id": first_spots[family]})["legal_actions"]
    kinds = {a["kind"].lower() for a in acts}
    assert kinds & {"bet", "raise"}, acts
    assert any(a["kind"].lower() in ("bet", "raise") and a["amount"] > 0 for a in acts)


class _WS:
    """Minimal RFC 6455 client (text frames, client masking) for CDP."""

    def __init__(self, url: str):
        m = re.match(r"ws://([^:/]+):(\d+)(/.*)", url)
        assert m, url
        self.sock = socket.create_connection((m.group(1), int(m.group(2))), timeout=120)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET {m.group(3)} HTTP/1.1\r\nHost: {m.group(1)}:{m.group(2)}\r\n"
                           f"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                           "Sec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(4096)
        assert b" 101 " in buf.split(b"\r\n", 1)[0], buf
        self._rest = buf.split(b"\r\n\r\n", 1)[1]
        self._id = 0

    def _recv_exact(self, n: int) -> bytes:
        while len(self._rest) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("websocket closed")
            self._rest += chunk
        out, self._rest = self._rest[:n], self._rest[n:]
        return out

    def send(self, text: str) -> None:
        data = text.encode()
        head = bytearray([0x81])
        n = len(data)
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head.append(0x80 | 126)
            head += struct.pack(">H", n)
        else:
            head.append(0x80 | 127)
            head += struct.pack(">Q", n)
        mask = os.urandom(4)
        self.sock.sendall(bytes(head) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self) -> str:
        parts = b""
        while True:
            b0, b1 = self._recv_exact(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._recv_exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._recv_exact(8))[0]
            payload = self._recv_exact(n)
            op = b0 & 0x0F
            if op in (0x1, 0x0):
                parts += payload
                if b0 & 0x80:
                    return parts.decode()
            elif op == 0x8:
                raise ConnectionError("websocket closed")

    def call(self, method: str, **params: Any) -> dict[str, Any]:
        self._id += 1
        mid = self._id
        self.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


def _chrome_binary() -> str | None:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    return None


class _Page:
    def __init__(self, ws: _WS):
        self.ws = ws

    def js(self, expr: str) -> Any:
        res = self.ws.call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in res:
            raise AssertionError(f"JS error in {expr[:80]!r}: {res['exceptionDetails']}")
        return res["result"].get("value")

    def wait(self, expr: str, timeout: float = 150.0) -> Any:
        end = time.time() + timeout
        while time.time() < end:
            v = self.js(expr)
            if v:
                return v
            time.sleep(0.2)
        raise AssertionError(f"timeout waiting for {expr}")

    def key(self, key: str) -> None:
        text = "\r" if key == "Enter" else key
        code = 13 if key == "Enter" else ord(key.upper())
        self.ws.call("Input.dispatchKeyEvent", type="keyDown", key=key, text=text,
                     windowsVirtualKeyCode=code)
        self.ws.call("Input.dispatchKeyEvent", type="keyUp", key=key, windowsVirtualKeyCode=code)

    def width(self, w: int) -> None:
        self.ws.call("Emulation.setDeviceMetricsOverride", width=w, height=900,
                     deviceScaleFactor=1, mobile=False)
        time.sleep(0.4)

    def open(self, url: str) -> None:
        self.ws.call("Page.navigate", url=url)
        self.wait("document.readyState === 'complete' && document.querySelectorAll('.spot-item').length > 0")

    def pick(self, spot_id: str) -> None:
        self.js(f"document.querySelector('[data-spot-id=\"{spot_id}\"]').click()")
        self.wait("document.querySelectorAll('#action-controls .action-btn').length > 0 "
                  "&& !document.getElementById('practice-app').hasAttribute('aria-busy')")


@pytest.fixture(scope="module")
def page(base_url):
    chrome = _chrome_binary()
    if not chrome:
        pytest.skip("no Chrome/Chromium binary for live browser checks")
    profile = tempfile.mkdtemp(prefix="w5ui-chrome-")
    proc = subprocess.Popen(
        [chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-first-run",
         "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws = None
    try:
        port_file = Path(profile) / "DevToolsActivePort"
        end = time.time() + 30
        while not (port_file.exists() and port_file.read_text().strip()):
            if time.time() > end or proc.poll() is not None:
                pytest.skip("Chrome did not start a DevTools endpoint")
            time.sleep(0.1)
        port = int(port_file.read_text().split()[0])
        targets = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=10).read())
        target = next(t for t in targets if t.get("type") == "page")
        ws = _WS(target["webSocketDebuggerUrl"])
        ws.call("Page.enable")
        ws.call("Runtime.enable")
        p = _Page(ws)
        p.width(1400)
        p.open(base_url + "/")
        yield p
    finally:
        if ws:
            ws.close()
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


STATE_JS = """(() => ({
  sel: [...document.querySelectorAll('.action-btn.selected')].map(b => b.textContent),
  submitDisabled: document.getElementById('submit-play').disabled,
  sizeVisible: !document.getElementById('size-row').classList.contains('hidden'),
  presets: [...document.querySelectorAll('#size-presets .size-preset')].map(b => b.textContent),
  size: document.getElementById('action-size').value,
  active: document.activeElement ? (document.activeElement.id || document.activeElement.tagName) : null,
  buttons: [...document.querySelectorAll('#action-controls .action-btn')].map(b => b.textContent),
}))()"""


def _label(a: dict[str, Any]) -> str:
    k = a["kind"].lower()
    names = {"fold": "Fold", "check": "Check", "call": "Call", "bet": "Bet", "raise": "Raise"}
    lab: str = names[k] if k in names else k.capitalize()
    amt = a.get("amount") or 0
    if amt > 0:
        lab += " " + (str(int(amt)) if float(amt).is_integer() else str(round(amt, 2)))
    return lab


@pytest.mark.parametrize("family", NEW_FAMILIES)
def test_live_1_7_shortcuts_size_and_labels_on_new_families(page, base_url, first_spots, family):
    spot = first_spots[family]
    acts = _post(base_url, "practice-solve-spot", {"spot_id": spot})["legal_actions"]
    page.pick(spot)
    st = page.js(STATE_JS)
    # 7: humanized labels in API order
    assert st["buttons"] == [_label(a) for a in acts]
    assert not any(b.isupper() and len(b) > 1 for b in " ".join(st["buttons"]).split())
    # 1: size row shows the API's sized amounts
    sized = sorted({a["amount"] for a in acts if a["kind"].lower() in ("bet", "raise") and a["amount"] > 0})
    assert st["sizeVisible"] and st["presets"] == [_label({"kind": "x", "amount": s}).split(" ")[1] for s in sized]
    kinds = [a["kind"].lower() for a in acts]
    for key, wanted in (("f", ("fold",)), ("c", ("check", "call")), ("b", ("bet", "raise"))):
        idx = next((i for w in wanted for i, k in enumerate(kinds) if k == w), None)
        page.js("document.activeElement && document.activeElement.blur()")
        page.key(key)
        st = page.js(STATE_JS)
        if idx is None:
            continue
        assert st["sel"] == [_label(acts[idx])], (key, st)
        assert st["submitDisabled"] is False
        assert st["active"] != "BODY"


def test_live_1_custom_size_submits_original_kind(page, base_url, first_spots):
    spot = first_spots["preflop-3max-open"]
    page.pick(spot)
    page.js("""(() => { window.__plays = []; const of = window.fetch;
      window.fetch = function (u, o) { try { const b = JSON.parse(o.body);
        if (b.operation === 'practice-submit-play') window.__plays.push(b.payload.play); } catch (e) {}
        return of.apply(this, arguments); }; })()""")
    page.js("document.activeElement && document.activeElement.blur()")
    page.key("b")
    assert page.js("document.activeElement.id") == "action-size"
    page.js("(() => { const i = document.getElementById('action-size'); i.value = '12';"
            " i.dispatchEvent(new Event('input', {bubbles: true})); })()")
    page.key("Enter")
    page.wait("!document.getElementById('result-panel').classList.contains('hidden')")
    plays = page.js("window.__plays")
    assert plays and plays[-1]["amount"] == 12
    legal_raise = [a["kind"] for a in _post(base_url, "practice-solve-spot", {"spot_id": spot})["legal_actions"]
                   if a["kind"].lower() == "raise"]
    assert plays[-1]["kind"] == legal_raise[0]  # uppercase value sent unchanged
    # 6: focus lands on Next spot, not <body>
    page.wait("!document.getElementById('practice-app').hasAttribute('aria-busy')")
    assert page.js("document.activeElement.id") == "next-spot"


def test_live_6_next_spot_keeps_keyboard_focus(page):
    page.js("document.getElementById('next-spot').focus()")
    page.key("Enter")
    page.wait("document.querySelectorAll('#action-controls .action-btn').length > 0 "
              "&& !document.getElementById('practice-app').hasAttribute('aria-busy')")
    page.wait("document.activeElement && document.activeElement.classList.contains('action-btn')", 10)


def test_live_2_best_badge_neutral_after_worse_retry(page, base_url, first_spots):
    spot = first_spots["preflop-3max-open"]
    page.js("(() => { const u = document.getElementById('user-input'); u.value = 'w5_badge';"
            " u.dispatchEvent(new Event('change')); })()")
    page.pick(spot)
    # two attempts with different actions: the badge must not take either grade colour
    for btn in (2, 0):
        page.pick(spot)
        page.js(f"document.querySelectorAll('#action-controls .action-btn')[{btn}].click()")
        page.js("document.getElementById('submit-play').click()")
        page.wait("!document.getElementById('result-panel').classList.contains('hidden') "
                  "&& !document.getElementById('practice-app').hasAttribute('aria-busy')")
    entry = next(e for e in _post(base_url, "practice-progress", {"user": "w5_badge"})["spots"]
                 if e["spot_id"] == spot)
    badge = page.wait(f"""(() => {{ const b = document.querySelector('[data-spot-id="{spot}"] .best-badge');
      return b && b.textContent.indexOf('{entry["best_score"]:.1f}') >= 0 ?
        {{cls: b.className, color: getComputedStyle(b).color}} : null; }})()""", 20)
    assert badge["cls"] == "best-badge", badge
    assert not re.search(r"grade-", badge["cls"])


def test_live_3_leaderboard_me_row_follows_user(page, base_url, first_spots):
    for user in ("w5_lb_a", "w5_lb_b"):
        spot = first_spots["kuhn-intro"]
        acts = _post(base_url, "practice-solve-spot", {"spot_id": spot})["legal_actions"]
        _post(base_url, "practice-submit-play", {"spot_id": spot, "play": acts[0], "user": user})
    me_js = ("[...document.querySelectorAll('#leaderboard-table tbody tr.me .cell-user')]"
             ".map(c => c.textContent)")
    page.js("(() => { const u = document.getElementById('user-input'); u.value = 'w5_lb_a';"
            " u.dispatchEvent(new Event('change')); })()")
    page.js("document.getElementById('leaderboard-refresh').click()")
    page.wait(f"JSON.stringify({me_js}) === '[\"w5_lb_a\"]'", 20)
    page.js("(() => { const u = document.getElementById('user-input'); u.value = 'w5_lb_b';"
            " u.dispatchEvent(new Event('change')); })()")
    # no manual refresh: highlight must move on its own
    page.wait(f"JSON.stringify({me_js}) === '[\"w5_lb_b\"]'", 20)


LAYOUT_JS = """(() => {
  const box = id => { const e = document.getElementById(id); if (!e) return null;
    const b = e.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
  const inter = (a, b) => Math.max(0, Math.min(a[2], b[2]) - Math.max(a[0], b[0])) *
                          Math.max(0, Math.min(a[3], b[3]) - Math.max(a[1], b[1]));
  const clipped = (wrapId, panelId) => { const p = document.getElementById(panelId).getBoundingClientRect();
    return [...document.querySelectorAll('#' + wrapId + ' th, #' + wrapId + ' td')]
      .map(c => c.getBoundingClientRect()).filter(r => r.width > 0 &&
        (r.right > p.right + 0.5 || r.left < p.left - 0.5)).length; };
  const ps = document.getElementById('progress-spots'), lb = document.getElementById('leaderboard-table');
  const head = [...document.querySelectorAll('.spot-header > *')]
    .filter(e => e.getClientRects().length).map(e => { const b = e.getBoundingClientRect();
      return [b.left, b.top, b.right, b.bottom]; });
  const seats = ['seat-villain', 'seat-villain-2'].map(box).filter(Boolean);
  let overlap = 0; seats.forEach(s => head.forEach(h => { overlap += inter(s, h); }));
  return { pageOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    progScroll: ps.scrollWidth - ps.clientWidth, lbScroll: lb.scrollWidth - lb.clientWidth,
    progClipped: clipped('progress-spots', 'progress-panel'),
    lbClipped: clipped('leaderboard-table', 'leaderboard-panel'),
    progRows: ps.querySelectorAll('tbody tr').length, seatHeaderOverlap: overlap };
})()"""


@pytest.mark.parametrize("family", ["turn-barrel", "preflop-3max-open"])
def test_live_4_5_layout_at_widths(page, first_spots, family):
    page.width(1400)
    page.pick(first_spots[family])
    page.wait("document.querySelectorAll('#progress-spots tbody tr').length > 0", 30)
    try:
        for w in (360, 900, 1400, 1600):
            page.width(w)
            page.js("window.scrollTo(0, 0)")
            m = page.js(LAYOUT_JS)
            assert m["progRows"] > 0
            assert m["pageOverflow"] <= 0, (w, m)
            assert m["progScroll"] <= 1 and m["progClipped"] == 0, (w, m)   # 4
            assert m["lbScroll"] <= 1 and m["lbClipped"] == 0, (w, m)
            assert m["seatHeaderOverlap"] == 0, (w, m)                       # 5
    finally:
        page.width(1400)
