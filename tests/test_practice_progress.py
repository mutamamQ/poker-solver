"""Persisted progress tracker: store math, v4 ops, fail-soft submit, CLI, HTTP smoke.

Every recorded score comes from a real Kuhn solve via ``dispatch_v4`` (scoring.score_play);
store-only tests that need controlled numbers write directly via ``ProgressStore.record``.
"""

from __future__ import annotations

import io
import json
import threading
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection

import pytest

from poker_solver.api_v4 import dispatch_v4
from poker_solver.practice import api as practice_api
from poker_solver.practice.progress import SCHEMA_VERSION, ProgressStore, default_path
from poker_solver.practice.server import make_server

# Equal to the kuhn-intro family default: only canonical solves are recorded (W5 F1).
SOLVE = {"algorithm": "vanilla-cfr", "iterations": 200, "seed": None}


@pytest.fixture()
def store(tmp_path):
    st = ProgressStore(tmp_path / "progress.sqlite3")
    practice_api.set_progress_store(st)
    yield st
    practice_api.set_progress_store(None)
    st.close()


@pytest.fixture(scope="module")
def kuhn_ids():
    listing = dispatch_v4({"version": 4, "operation": "practice-list-spots",
                           "payload": {"families": ["kuhn-intro"]}})
    ids = [s["spot_id"] for s in listing["result"]["spots"]]
    assert len(ids) >= 2
    return ids


def _v4(op, payload):
    return dispatch_v4({"version": 4, "operation": op, "payload": payload})


def _solved(spot_id):
    return _v4("practice-solve-spot", {"spot_id": spot_id, "solve": SOLVE})["result"]


_UNSET = object()


def _submit(spot_id, play, user=_UNSET):
    payload = {"spot_id": spot_id, "play": play, "solve": SOLVE}
    if user is not _UNSET:
        payload["user"] = user
    return _v4("practice-submit-play", payload)


def _best_and_other(spot_id):
    solved = _solved(spot_id)
    best = solved["optimal_action"]
    others = [a for a in solved["legal_actions"] if a != best]
    return best, (others[0] if others else best)


def _rec(st, user, spot, score, *, family="fam-a", ts=None, grade="Good"):
    return st.record(user=user, spot_id=spot, family=family, street="river",
                     game_type="heads-up", score=score, grade=grade, ev_loss_pct=1.0,
                     params_hash="h" * 64, ts=ts)


# --------------------------------------------------------------------------- real submit


def test_submit_records_real_score(store, kuhn_ids):
    sid = kuhn_ids[0]
    best, other = _best_and_other(sid)
    r1 = _submit(sid, other, user="alice")
    assert set(r1) == {"version", "operation", "result", "provenance"}
    assert set(r1["result"]) == {"user", "score", "solved", "progress"}
    s1 = r1["result"]["score"]["score"]
    prog = r1["result"]["progress"]
    assert prog["spot_id"] == sid and prog["attempts"] == 1
    assert prog["family"] == "kuhn-intro" and prog["street"] and prog["game_type"] == "heads-up"
    assert prog["best_score"] == prog["last_score"] == s1
    assert prog["last_grade"] == r1["result"]["score"]["grade"]
    assert prog["first_at"] == prog["last_at"] and prog["last_at"].endswith("Z")

    r2 = _submit(sid, best, user="alice")
    s2 = r2["result"]["score"]["score"]
    prog2 = r2["result"]["progress"]
    assert prog2["attempts"] == 2
    assert prog2["best_score"] == max(s1, s2)
    assert prog2["last_score"] == s2
    assert prog2["first_at"] == prog["first_at"] and prog2["last_at"] >= prog["last_at"]

    view = _v4("practice-progress", {"user": "alice"})
    assert view["provenance"] is None and view["operation"] == "practice-progress"
    assert view["result"]["user"] == "alice"
    assert view["result"]["spots"] == [prog2]
    assert view["result"]["totals"] == {"attempts": 2, "spots_attempted": 1,
                                        "avg_best_score": max(s1, s2), "avg_last_score": s2}
    json.dumps(view, allow_nan=False)


def test_default_user_is_local(store, kuhn_ids):
    r = _submit(kuhn_ids[0], _solved(kuhn_ids[0])["optimal_action"])
    assert r["result"]["user"] == "local"
    assert _v4("practice-progress", {})["result"]["totals"]["attempts"] == 1


@pytest.mark.parametrize("bad", ["", "a" * 33, "bob smith", "x/y", "é", "bob\n", 7, None, True])
def test_invalid_user_rejected(store, kuhn_ids, bad):
    with pytest.raises(ValueError):
        _submit(kuhn_ids[0], {"kind": "check"}, user=bad)
    with pytest.raises(ValueError):
        _v4("practice-progress", {"user": bad})
    assert store.progress("local")["totals"]["attempts"] == 0


def test_store_failure_keeps_submit(store, kuhn_ids, monkeypatch):
    def boom(**_kw):
        raise RuntimeError("disk full")
    monkeypatch.setattr(store, "record", boom)
    r = _submit(kuhn_ids[0], _solved(kuhn_ids[0])["optimal_action"], user="bob")
    assert r["result"]["progress"] is None
    assert 0 <= r["result"]["score"]["score"] <= 100


def test_store_unavailable_keeps_submit(kuhn_ids, monkeypatch, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("POKER_PRACTICE_DATA_DIR", str(blocker / "sub"))  # cannot mkdir under a file
    practice_api.set_progress_store(None)
    try:
        r = _submit(kuhn_ids[0], _solved(kuhn_ids[0])["optimal_action"])
        assert r["result"]["progress"] is None
        with pytest.raises(ValueError, match="unavailable"):
            _v4("practice-progress", {})
    finally:
        practice_api.set_progress_store(None)


# --------------------------------------------------------------------------- validation


@pytest.mark.parametrize("op,payload", [
    ("practice-progress", {"x": 1}),
    ("practice-progress", {"spot_id": ""}),
    ("practice-progress", []),
    ("practice-leaderboard", {"limit": 0}),
    ("practice-leaderboard", {"limit": 101}),
    ("practice-leaderboard", {"limit": True}),
    ("practice-leaderboard", {"limit": "5"}),
    ("practice-leaderboard", {"family": ""}),
    ("practice-leaderboard", {"user": "a"}),
])
def test_payload_validation(store, op, payload):
    with pytest.raises(ValueError):
        _v4(op, payload)


def test_submit_rejects_client_progress(store, kuhn_ids):
    with pytest.raises(ValueError):
        _v4("practice-submit-play", {"spot_id": kuhn_ids[0], "play": {"kind": "check"},
                                     "progress": {"best_score": 100}})


# --------------------------------------------------------------------------- store math


def test_totals_best_last_math(store):
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    _rec(store, "u", "s1", 40.0, ts=t0)
    _rec(store, "u", "s1", 90.0, ts=t0 + timedelta(seconds=1))
    _rec(store, "u", "s1", 10.0, ts=t0 + timedelta(seconds=2), grade="Blunder")
    _rec(store, "u", "s2", 60.0, ts=t0 + timedelta(seconds=3))
    p = store.progress("u")
    s1, s2 = p["spots"]
    assert (s1["spot_id"], s1["attempts"], s1["best_score"], s1["last_score"], s1["last_grade"]) == \
        ("s1", 3, 90.0, 10.0, "Blunder")
    assert s1["first_at"] == "2026-01-01T00:00:00.000000Z"
    assert s1["last_at"] == "2026-01-01T00:00:02.000000Z"
    assert p["totals"] == {"attempts": 4, "spots_attempted": 2,
                           "avg_best_score": 75.0, "avg_last_score": 35.0}
    assert store.progress("u", "s2")["spots"] == [s2]
    empty = store.progress("nobody")
    assert empty["spots"] == [] and empty["totals"]["attempts"] == 0
    assert empty["totals"]["avg_best_score"] is None


def test_leaderboard_ordering_ties_and_family(store):
    _rec(store, "carol", "s1", 100.0)                      # total 100, avg 100
    _rec(store, "alice", "s1", 50.0)
    _rec(store, "alice", "s2", 50.0)                       # total 100, avg 50
    _rec(store, "bob", "s1", 70.0, family="fam-b")
    _rec(store, "bob", "s1", 80.0, family="fam-b")         # total 80
    _rec(store, "dave", "s1", 100.0)                       # ties carol fully -> user asc
    entries = _v4("practice-leaderboard", {})["result"]["entries"]
    assert [e["user"] for e in entries] == ["carol", "dave", "alice", "bob"]
    assert [e["rank"] for e in entries] == [1, 2, 3, 4]
    alice = entries[2]
    assert alice == {"rank": 3, "user": "alice", "spots_attempted": 2, "attempts": 2,
                     "avg_best_score": 50.0, "total_best_score": 100.0}
    assert entries[3]["attempts"] == 2 and entries[3]["total_best_score"] == 80.0
    top = _v4("practice-leaderboard", {"limit": 2})
    assert top["provenance"] is None and len(top["result"]["entries"]) == 2
    fam_b = _v4("practice-leaderboard", {"family": "fam-b"})["result"]["entries"]
    assert [e["user"] for e in fam_b] == ["bob"]
    assert _v4("practice-leaderboard", {"family": "nope"})["result"]["entries"] == []


def test_leaderboard_from_real_submits(store, kuhn_ids):
    best = _solved(kuhn_ids[0])["optimal_action"]
    r = _submit(kuhn_ids[0], best, user="real")
    entries = _v4("practice-leaderboard", {"family": "kuhn-intro"})["result"]["entries"]
    assert entries[0]["user"] == "real"
    assert entries[0]["total_best_score"] == r["result"]["score"]["score"]


def test_persistence_and_schema(tmp_path):
    path = tmp_path / "p.sqlite3"
    a = ProgressStore(path)
    _rec(a, "u", "s1", 42.0)
    a.close()
    b = ProgressStore(path)
    assert b.schema_version() == SCHEMA_VERSION
    assert b.progress("u")["spots"][0]["best_score"] == 42.0
    _rec(b, "u", "s1", 43.0)
    assert b.progress("u")["spots"][0]["attempts"] == 2
    b.close()


def test_sql_injection_safe(store):
    _rec(store, "u", "s'; DROP TABLE attempts; --", 1.0, family="f' OR '1'='1")
    assert store.leaderboard(family="f' OR '1'='1")[0]["user"] == "u"
    assert store.leaderboard(family="x' OR '1'='1") == []
    assert store.progress("u")["totals"]["attempts"] == 1


def test_from_env_path(monkeypatch, tmp_path):
    monkeypatch.setenv("POKER_PRACTICE_DATA_DIR", str(tmp_path / "d"))
    assert default_path() == tmp_path / "d" / "progress.sqlite3"
    st = ProgressStore.from_env()
    assert st.path.exists()
    st.close()
    monkeypatch.delenv("POKER_PRACTICE_DATA_DIR")
    assert str(default_path()).endswith(".local/share/poker-solver/practice/progress.sqlite3")


def test_concurrency_smoke(tmp_path):
    path = tmp_path / "c.sqlite3"
    st = ProgressStore(path)
    other = ProgressStore(path)  # second connection to the same WAL db
    errors = []

    def work(i):
        try:
            target = st if i % 2 else other
            for j in range(25):
                _rec(target, f"u{i % 4}", f"s{j % 5}", float(j))
                target.leaderboard()
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert sum(e["attempts"] for e in st.leaderboard(limit=100)) == 200
    st.close()
    other.close()


# --------------------------------------------------------------------------- CLI + HTTP


def _cli(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = practice_api.main(argv)
    return code, buf.getvalue()


def test_cli_progress_and_leaderboard(store):
    _rec(store, "cli", "s1", 77.0, family="fam-c")
    code, out = _cli(["progress", "--user", "cli"])
    assert code == 0
    assert json.loads(out)["result"]["totals"]["avg_best_score"] == 77.0
    code, out = _cli(["leaderboard", "--limit", "5", "--family", "fam-c"])
    assert code == 0
    assert json.loads(out)["result"]["entries"][0]["user"] == "cli"
    assert _cli(["leaderboard", "--limit", "0"])[0] == 2
    assert _cli(["progress", "--user", "bad user"])[0] == 2


def _post(port, body):
    conn = HTTPConnection("127.0.0.1", port, timeout=60)
    conn.request("POST", "/api/v4", body=json.dumps(body).encode(),
                 headers={"Content-Type": "application/json"})
    r = conn.getresponse()
    return r.status, json.loads(r.read())


def test_http_smoke(store, kuhn_ids):
    srv = make_server(port=0)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        port = srv.server_address[1]
        best = _solved(kuhn_ids[1])["optimal_action"]
        status, sub = _post(port, {"version": 4, "operation": "practice-submit-play",
                                   "payload": {"spot_id": kuhn_ids[1], "play": best,
                                               "solve": SOLVE, "user": "web"}})
        assert status == 200, sub
        assert sub["result"]["progress"]["attempts"] == 1
        status, prog = _post(port, {"version": 4, "operation": "practice-progress",
                                    "payload": {"user": "web"}})
        assert status == 200 and prog["result"]["spots"] == [sub["result"]["progress"]]
        status, board = _post(port, {"version": 4, "operation": "practice-leaderboard",
                                     "payload": {"limit": 3}})
        assert status == 200 and board["result"]["entries"][0]["user"] == "web"
        status, err = _post(port, {"version": 4, "operation": "practice-submit-play",
                                   "payload": {"spot_id": kuhn_ids[1], "play": best,
                                               "user": "no spaces allowed"}})
        assert status == 400 and "error" in err
    finally:
        srv.shutdown()
        srv.server_close()
