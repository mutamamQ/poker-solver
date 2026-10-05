"""W5 repair-C regressions for the progress/API/server audit (audit-progress-api.md F1..F7).

Each test reproduces the audit repro and asserts the repaired behaviour.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection

import pytest

from poker_solver.api_v4 import dispatch_v4
from poker_solver.practice import api as practice_api
from poker_solver.practice import server as practice_server
from poker_solver.practice.catalog import FAMILY_DEFAULT_SOLVE
from poker_solver.practice.progress import (SKIPPED, ProgressStore, RequestToken,
                                            request_scope)
from poker_solver.practice.server import REQUEST_QUEUE_SIZE, make_server


def _v4(op, payload):
    return dispatch_v4({"version": 4, "operation": op, "payload": payload})


@pytest.fixture()
def store(tmp_path):
    st = ProgressStore(tmp_path / "progress.sqlite3")
    practice_api.set_progress_store(st)
    yield st
    practice_api.set_progress_store(None)
    st.close()


@pytest.fixture(scope="module")
def kuhn_spot():
    spots = _v4("practice-list-spots", {"families": ["kuhn-intro"]})["result"]["spots"]
    return spots[0]


def _rec(st, user, spot, score, *, ts=None, grade="Good"):
    return st.record(user=user, spot_id=spot, family="fam", street="river",
                     game_type="heads-up", score=score, grade=grade, ev_loss_pct=1.0,
                     params_hash="h" * 64, ts=ts)


@pytest.fixture()
def http_server():
    srv = make_server(port=0)
    t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    t.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        t.join(5)
        srv.server_close()


def _post_raw(port, body: bytes, timeout=60):
    conn = HTTPConnection("127.0.0.1", port, timeout=timeout)
    conn.request("POST", "/api/v4", body=body, headers={"Content-Type": "application/json"})
    r = conn.getresponse()
    data = json.loads(r.read())
    conn.close()
    return r.status, data


def _post(port, op, payload, timeout=60):
    body = json.dumps({"version": 4, "operation": op, "payload": payload}).encode()
    return _post_raw(port, body, timeout)


# ------------------------------------------------------------------- F1 score forging


def test_f1_degenerate_solve_override_is_not_recorded(store, kuhn_spot):
    """Audit repro: iterations=1 grades the equilibrium-rejected action 'Perfect'."""
    sid = kuhn_spot["spot_id"]
    play = {"kind": "bet", "amount": 0}
    honest = _v4("practice-submit-play", {"spot_id": sid, "play": play, "user": "honest"})
    gamer = _v4("practice-submit-play", {"spot_id": sid, "play": play, "user": "gamer",
                                         "solve": {"iterations": 1}})
    # Envelope / result keys are stable either way.
    for r in (honest, gamer):
        assert set(r) == {"version", "operation", "result", "provenance"}
        assert set(r["result"]) == {"user", "score", "solved", "progress"}
    assert honest["result"]["progress"] is not None
    assert honest["result"]["progress"]["attempts"] == 1
    # The override is still scored (practice "what if") but never recorded/ranked.
    assert 0 <= gamer["result"]["score"]["score"] <= 100
    assert gamer["result"]["progress"] is None
    assert store.progress("gamer")["totals"]["attempts"] == 0
    users = [e["user"] for e in store.leaderboard(limit=100)]
    assert "gamer" not in users and "honest" in users


def test_f1_override_equal_to_family_default_counts(store, kuhn_spot):
    default = FAMILY_DEFAULT_SOLVE["kuhn-intro"].canonical()
    r = _v4("practice-submit-play", {"spot_id": kuhn_spot["spot_id"], "user": "explicit",
                                     "play": {"kind": "check"}, "solve": default})
    assert r["result"]["progress"]["attempts"] == 1
    # Omitted fields default to SolveParams(): {} is also the family default for kuhn.
    r = _v4("practice-submit-play", {"spot_id": kuhn_spot["spot_id"], "user": "explicit",
                                     "play": {"kind": "check"}, "solve": {}})
    assert r["result"]["progress"]["attempts"] == 2


def test_f1_stored_row_has_canonical_params_hash(store, kuhn_spot):
    sid = kuhn_spot["spot_id"]
    _v4("practice-submit-play", {"spot_id": sid, "play": {"kind": "check"}, "user": "h"})
    _v4("practice-submit-play", {"spot_id": sid, "play": {"kind": "check"}, "user": "h",
                                 "solve": {"iterations": 7}})
    rows = store._conn.execute("SELECT params_hash FROM attempts WHERE user='h'").fetchall()
    assert rows == [(kuhn_spot["params_hash"],)]


def test_f1_http_forging_blocked(store, kuhn_spot, http_server):
    port = http_server.server_address[1]
    status, r = _post(port, "practice-submit-play",
                      {"spot_id": kuhn_spot["spot_id"], "play": {"kind": "bet", "amount": 0},
                       "user": "gamer2", "solve": {"iterations": 1}})
    assert status == 200 and r["result"]["progress"] is None
    status, b = _post(port, "practice-leaderboard", {})
    assert status == 200 and all(e["user"] != "gamer2" for e in b["result"]["entries"])


# ------------------------------------------------------------------- F2 late writes after 504


def test_f2_request_token_semantics():
    tok = RequestToken(deadline=time.monotonic() + 60)
    assert tok.run_side_effect(lambda: 1) == 1
    assert tok.cancel() is False  # already committed -> caller must not report failure
    tok2 = RequestToken(deadline=time.monotonic() + 60)
    assert tok2.cancel() is True
    assert tok2.run_side_effect(lambda: pytest.fail("must not run")) is SKIPPED
    tok3 = RequestToken(deadline=time.monotonic() - 1)  # expired
    assert tok3.run_side_effect(lambda: pytest.fail("must not run")) is SKIPPED


def test_f2_cancelled_token_skips_record(store, kuhn_spot):
    tok = RequestToken()
    tok.cancel()
    with request_scope(tok):
        r = _v4("practice-submit-play", {"spot_id": kuhn_spot["spot_id"],
                                         "play": {"kind": "check"}, "user": "late"})
    assert r["result"]["progress"] is None
    assert store.progress("late")["totals"]["attempts"] == 0


def test_f2_timed_out_submit_never_records(store, kuhn_spot, monkeypatch):
    """Audit repro: 504 then the abandoned solve wrote an attempt ~40 s later."""
    real_solve = practice_api._ADAPTER.solve
    release = threading.Event()
    finished = threading.Event()

    def slow_solve(spot):
        release.wait(30)
        try:
            return real_solve(spot)
        finally:
            finished.set()

    monkeypatch.setattr(practice_api._ADAPTER, "solve", slow_solve)
    monkeypatch.setenv("POKER_PRACTICE_TIMEOUT", "0.3")
    srv = make_server(port=0)
    t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    t.start()
    try:
        status, body = _post(srv.server_address[1], "practice-submit-play",
                             {"spot_id": kuhn_spot["spot_id"], "play": {"kind": "check"},
                              "user": "t2"})
        assert status == 504 and body == {"error": "solve timed out"}
        release.set()  # let the orphaned dispatch finish scoring
        assert finished.wait(30)
        time.sleep(0.5)  # record step would run right after the solve
        assert store.progress("t2")["totals"]["attempts"] == 0
    finally:
        release.set()
        srv.shutdown()
        t.join(5)
        srv.server_close()


def test_f2_within_deadline_still_records(store, kuhn_spot, http_server):
    status, r = _post(http_server.server_address[1], "practice-submit-play",
                      {"spot_id": kuhn_spot["spot_id"], "play": {"kind": "check"},
                       "user": "ontime"})
    assert status == 200 and r["result"]["progress"]["attempts"] == 1
    assert store.progress("ontime")["totals"]["attempts"] == 1


# ------------------------------------------------------------------- F3 latched failure


def test_f3_store_open_failure_is_retried(tmp_path, monkeypatch, kuhn_spot):
    """Audit repro: dir unwritable at first use stayed disabled after it was fixed."""
    blocker = tmp_path / "blocker"
    blocker.write_text("x")  # data dir path is a file -> open fails
    monkeypatch.setenv("POKER_PRACTICE_DATA_DIR", str(blocker))
    clock = [1000.0]
    monkeypatch.setattr(practice_api.time, "monotonic", lambda: clock[0])
    practice_api.set_progress_store(None)
    try:
        assert practice_api._progress_store(required=False) is None
        with pytest.raises(ValueError, match="unavailable"):
            _v4("practice-progress", {})
        # Fix the directory.
        blocker.unlink()
        blocker.mkdir()
        # Still inside the backoff window: no reopen storm.
        clock[0] += practice_api.STORE_RETRY_S / 2
        assert practice_api._progress_store(required=False) is None
        # After the backoff the store opens and works.
        clock[0] += practice_api.STORE_RETRY_S
        r = _v4("practice-submit-play", {"spot_id": kuhn_spot["spot_id"],
                                         "play": {"kind": "check"}, "user": "sticky"})
        assert r["result"]["progress"]["attempts"] == 1
        assert _v4("practice-progress", {"user": "sticky"})["result"]["totals"]["attempts"] == 1
        assert (blocker / "progress.sqlite3").exists()
    finally:
        st = practice_api._STORE
        practice_api.set_progress_store(None)
        if st is not None:
            st.close()


# ------------------------------------------------------------------- F4 backlog


def test_f4_request_queue_size(http_server):
    assert REQUEST_QUEUE_SIZE == 64
    assert type(http_server).request_queue_size == 64
    assert http_server.daemon_threads is True


def test_f4_concurrent_clients_not_reset(store, http_server):
    port = http_server.server_address[1]
    results: list = []
    lock = threading.Lock()
    barrier = threading.Barrier(64)

    def work():
        barrier.wait()
        try:
            out = _post(port, "practice-progress", {}, timeout=60)[0]
        except Exception as exc:  # noqa: BLE001
            out = type(exc).__name__
        with lock:
            results.append(out)

    threads = [threading.Thread(target=work) for _ in range(64)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(90)
    assert results.count(200) == 64, results


# ------------------------------------------------------------------- F5 codec leak


@pytest.mark.parametrize("op,payload", [
    ("practice-leaderboard", {"family": "\ud800"}),
    ("practice-progress", {"spot_id": "\ud800"}),
    ("practice-submit-play", {"spot_id": "\ud800", "play": {"kind": "check"}}),
    ("practice-solve-spot", {"spot_id": "\udfff"}),
])
def test_f5_lone_surrogate_generic_400(store, http_server, op, payload):
    port = http_server.server_address[1]
    # json.dumps escapes the surrogate as \\ud800 -> valid UTF-8 body, surrogate after parse.
    status, body = _post(port, op, payload)
    assert status == 400 and set(body) == {"error"}
    assert "codec" not in body["error"] and "surrogate" not in body["error"]
    assert "invalid string encoding" in body["error"]


def test_f5_invalid_utf8_body_generic(http_server):
    status, body = _post_raw(http_server.server_address[1], b'{"version": 4, "x": "\xff"}')
    assert status == 400 and set(body) == {"error"}
    assert "codec" not in body["error"] and "0xff" not in body["error"]


def test_f5_store_level_validation(store):
    with pytest.raises(ValueError, match="invalid string encoding"):
        store.leaderboard(family="\ud800")
    with pytest.raises(ValueError, match="invalid string encoding"):
        store.progress("local", "\ud800")


# ------------------------------------------------------------------- F6 last_* consistency


def test_f6_last_fields_describe_same_attempt(store):
    """Audit repro: record(100, now); record(0, now-1s) -> last_at of the 100 attempt."""
    now = datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)
    _rec(store, "u", "s", 100.0, ts=now, grade="Perfect")
    _rec(store, "u", "s", 0.0, ts=now - timedelta(seconds=1), grade="Blunder")
    (entry,) = store.progress("u")["spots"]
    assert entry["last_score"] == 0.0 and entry["last_grade"] == "Blunder"
    assert entry["last_at"] == "2026-10-05T11:59:59.000000Z"   # the Blunder row
    assert entry["first_at"] == "2026-10-05T12:00:00.000000Z"  # the first (Perfect) row
    assert entry["best_score"] == 100.0 and entry["attempts"] == 2


# ------------------------------------------------------------------- F7 deleted DB


def test_f7_deleted_db_is_recreated(tmp_path):
    """Audit repro: after rm the attempts went to an unlinked inode and were lost."""
    path = tmp_path / "p.sqlite3"
    st = ProgressStore(path)
    try:
        assert _rec(st, "u", "s", 10.0)["attempts"] == 1
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(f"{path}{suffix}"):
                os.unlink(f"{path}{suffix}")
        assert _rec(st, "u", "s", 20.0)["attempts"] == 1  # fresh DB, not the ghost inode
        assert _rec(st, "u", "s", 30.0)["attempts"] == 2
        assert path.exists() and st.reopen_count == 1
    finally:
        st.close()
    other = ProgressStore(path)  # what a restart would see
    try:
        assert other.progress("u")["totals"]["attempts"] == 2
    finally:
        other.close()


def test_f7_replaced_db_is_reopened(tmp_path):
    path = tmp_path / "p.sqlite3"
    st = ProgressStore(path)
    try:
        _rec(st, "u", "s", 10.0)
        replacement = tmp_path / "new.sqlite3"
        fresh = ProgressStore(replacement)
        _rec(fresh, "v", "s", 50.0)
        fresh.close()
        for suffix in ("-wal", "-shm"):
            if os.path.exists(f"{path}{suffix}"):
                os.unlink(f"{path}{suffix}")
        os.replace(replacement, path)
        board = [e["user"] for e in st.leaderboard()]
        assert board == ["v"] and st.reopen_count == 1
    finally:
        st.close()


def test_f7_unchanged_file_does_not_reopen(tmp_path):
    st = ProgressStore(tmp_path / "p.sqlite3")
    try:
        for i in range(5):
            _rec(st, "u", "s", float(i))
        st.progress("u")
        st.leaderboard()
        assert st.reopen_count == 0
    finally:
        st.close()


def test_memory_store_still_works():
    st = ProgressStore(":memory:")
    try:
        assert _rec(st, "u", "s", 1.0)["attempts"] == 1
        assert st.reopen_count == 0
    finally:
        st.close()


def test_server_module_exports():
    assert "REQUEST_QUEUE_SIZE" in practice_server.__all__
