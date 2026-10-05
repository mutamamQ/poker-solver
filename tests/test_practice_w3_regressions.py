"""Regression tests for reproduced W3 audit findings (practice mode)."""
from __future__ import annotations

import dataclasses
import json
import socket
import threading
import time
from http.client import HTTPConnection

import pytest

from poker_solver.api_v4 import dispatch_v4
from poker_solver.practice import server as practice_server
from poker_solver.practice.adapter import SolverAdapter
from poker_solver.practice.catalog import generate_catalog
from poker_solver.practice.models import SolveParams
from poker_solver.practice.server import make_server

TOL = 1e-9


def _max_diff(a, b):
    keys = set(a) | set(b)
    return max(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys)


@pytest.fixture()
def live(monkeypatch):
    monkeypatch.setattr(practice_server.PracticeHandler, "timeout", 0.5)
    srv = make_server(port=0)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv.server_address[1]
    srv.shutdown()
    srv.server_close()


def _raw(port, data: bytes, read_timeout=5.0) -> bytes:
    s = socket.create_connection(("127.0.0.1", port), timeout=read_timeout)
    try:
        s.sendall(data)
        chunks = []
        while True:
            try:
                c = s.recv(65536)
            except socket.timeout:
                break
            if not c:
                break
            chunks.append(c)
        return b"".join(chunks)
    finally:
        s.close()


# --- audit-2 F1: huge integer probability -> ValueError (HTTP 400), not 500
def test_huge_integer_probability_is_value_error():
    spot = dispatch_v4({"version": 4, "operation": "practice-list-spots", "payload": {}})
    spot_id = spot["result"]["spots"][0]["spot_id"]
    solved = dispatch_v4({"version": 4, "operation": "practice-solve-spot",
                          "payload": {"spot_id": spot_id, "solve": {"iterations": 20}}})
    acts = solved["result"]["legal_actions"]
    mix = [{"action": {"kind": a["kind"], "amount": a["amount"]}, "probability": 10 ** 400} for a in acts]
    with pytest.raises(ValueError, match="finite"):
        dispatch_v4({"version": 4, "operation": "practice-submit-play",
                     "payload": {"spot_id": spot_id, "solve": {"iterations": 20}, "play": {"mix": mix}}})


# --- audit-2 F2: deeply nested JSON -> 400 JSON error
def test_deeply_nested_json_is_400(live):
    body = b"[" * 5000 + b"]" * 5000
    conn = HTTPConnection("127.0.0.1", live, timeout=10)
    conn.request("POST", "/api/v4", body=body, headers={"Content-Type": "application/json"})
    r = conn.getresponse()
    assert r.status == 400
    assert "error" in json.loads(r.read())


# --- audit-2 F3: TRACE / unknown methods -> 405 JSON with security headers
@pytest.mark.parametrize("method", ["TRACE", "FOO"])
def test_unknown_methods_are_405_json(live, method):
    conn = HTTPConnection("127.0.0.1", live, timeout=10)
    conn.request(method, "/")
    r = conn.getresponse()
    assert r.status == 405
    assert r.getheader("Content-Type", "").startswith("application/json")
    assert r.getheader("X-Content-Type-Options") == "nosniff"
    assert r.getheader("Content-Security-Policy")
    assert "error" in json.loads(r.read())


# --- audit-2 F4: short body must not pin a handler thread forever
def test_handler_has_default_socket_timeout():
    t = practice_server.PracticeHandler.timeout
    assert t is not None and 0 < t <= 120


def test_short_body_times_out(live):
    t0 = time.monotonic()
    _raw(live, b"POST /api/v4 HTTP/1.1\r\nHost: x\r\nContent-Length: 100\r\n"
               b"Content-Type: application/json\r\n\r\n{\"a\":", read_timeout=5.0)
    assert time.monotonic() - t0 < 4.0  # server closed on its socket timeout


# --- audit-1 F1: dedicated R1 check also covers Q-values and range strategy
@pytest.mark.parametrize("family", ["kuhn-intro", "river-oop-bet-or-check", "river-ip-facing-bet"])
def test_iterations_change_action_values(family):
    spot = generate_catalog(families=(family,), limit=1)[0]
    ad = SolverAdapter()
    lo = ad.solve(spot.with_solve(SolveParams(iterations=5)))
    hi = ad.solve(spot.with_solve(SolveParams(iterations=300)))
    assert _max_diff(lo.action_values, hi.action_values) > TOL


def test_pot_change_changes_action_values():
    spot = generate_catalog(families=("river-oop-bet-or-check",), solve=SolveParams(iterations=60), limit=1)[0]
    ad = SolverAdapter()
    a = ad.solve(spot)
    b = ad.solve(dataclasses.replace(spot, pot=spot.pot * 3))
    assert _max_diff(a.action_values, b.action_values) > TOL


# --- audit-1 F2 / reaudit F1: stack ALONE changes the answer (allstreet route; bet size fixed)
def test_stack_change_changes_answer():
    from poker_solver.cards import parse_cards
    from poker_solver.practice.models import Action, PracticeSpot, WeightedCombo
    board = parse_cards(["Td", "8h", "2c"])
    r0 = (WeightedCombo(parse_cards(["As", "Ah"]), 1.0), WeightedCombo(parse_cards(["5s", "4s"]), 1.0))
    r1 = (WeightedCombo(parse_cards(["Qs", "Qh"]), 1.0), WeightedCombo(parse_cards(["Jd", "Jc"]), 1.0))
    base = PracticeSpot(
        family="flop-check-small-tree", backend="allstreet", game_type="heads-up", street="flop",
        board=board, hero_seat=1, villain_seats=(0,), ranges=(r0, r1), pot=100, stacks=(100, 100),
        action_history=(Action("CHECK"),), bet_sizes=(33,), hero_hand=parse_cards(["Qs", "Qh"]),
        solve=SolveParams(iterations=15),
        backend_extra={"allowed_runouts": [list(parse_cards(["3d", "7c"]))], "betting_mode": "no-limit",
                       "max_nodes": 4000, "max_depth": 40},
    )
    ad = SolverAdapter()
    short = dataclasses.replace(base, stacks=(40, 40))
    deep = dataclasses.replace(base, stacks=(400, 400))
    assert short.bet_sizes == deep.bet_sizes == base.bet_sizes
    assert short.params_hash() != deep.params_hash()
    a, b = ad.solve(short), ad.solve(deep)
    assert _max_diff(a.strategy, b.strategy) > 1e-3 or _max_diff(a.action_values, b.action_values) > 1e-3


# --- reaudit-2 F1: legacy v4 _float overflow -> ValueError
def test_api_v4_float_overflow_is_value_error():
    from poker_solver.api_v4 import _float
    with pytest.raises(ValueError, match="finite"):
        _float(10 ** 400, "weight")


# --- reaudit-2 F2: error responses that close the connection say so
def test_error_close_sends_connection_close(live):
    conn = HTTPConnection("127.0.0.1", live, timeout=10)
    conn.request("PUT", "/api/v4", body=b"{}")
    r = conn.getresponse(); r.read()
    assert r.status == 405
    assert (r.getheader("Connection") or "").lower() == "close"


# --- reaudit-2 F3: trickled body bounded by a whole-request deadline
def test_trickled_body_hits_total_deadline(live):
    s = socket.create_connection(("127.0.0.1", live), timeout=10)
    try:
        s.sendall(b"POST /api/v4 HTTP/1.1\r\nHost: x\r\nContent-Length: 50\r\n\r\n")
        t0 = time.monotonic()
        closed = False
        for _ in range(12):
            time.sleep(0.3)
            try:
                s.sendall(b" ")
            except OSError:
                closed = True
                break
        s.settimeout(3)
        data = b""
        try:
            data = s.recv(4096)
        except OSError:
            pass
        assert closed or data.startswith(b"HTTP/1.1 400") or data == b""
        assert time.monotonic() - t0 < 6.0
    finally:
        s.close()


# --- reaudit-2 F4a: non-alpha unknown methods are 405 JSON too
def test_nonalpha_method_is_405(live):
    conn = HTTPConnection("127.0.0.1", live, timeout=10)
    conn.request("M-SEARCH", "/")
    r = conn.getresponse()
    assert r.status == 405 and r.getheader("Allow") == "GET, HEAD"
    assert "error" in json.loads(r.read())


# --- reaudit-3 N1: protocol errors before version parse still get status line + headers
@pytest.mark.parametrize("line", [b"hello\r\n\r\n", b"GET / HTTP/2.0\r\n\r\n"])
def test_garbage_request_line_has_status_and_headers(live, line):
    data = _raw(live, line, read_timeout=3.0)
    assert data.startswith(b"HTTP/1.1 ")
    head = data.split(b"\r\n\r\n", 1)[0].lower()
    assert b"x-content-type-options: nosniff" in head
    assert b"content-security-policy" in head


# --- reaudit-3 N4: leading blank line before the request line is ignored
def test_leading_blank_line_is_ignored(live):
    data = _raw(live, b"\r\nGET /api/health HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n", read_timeout=3.0)
    assert data.startswith(b"HTTP/1.1 200")
