"""Smoke tests for practice.api: handle_practice for all 3 operations + in-process CLI.

Uses real Kuhn solves via the production catalog/adapter (small trees, few iterations).
"""

from __future__ import annotations

import json

import pytest

from poker_solver.practice.api import PRACTICE_OPERATIONS, handle_practice, main


def _strict(obj) -> str:
    return json.dumps(obj, allow_nan=False, sort_keys=True)


@pytest.fixture(scope="module")
def listing():
    return handle_practice("practice-list-spots", {})


@pytest.fixture(scope="module")
def kuhn_spot(listing):
    from poker_solver.practice.catalog import find_spot
    for spot in listing["result"]["spots"]:
        s = find_spot(spot["spot_id"])
        if s is not None and s.backend == "kuhn":
            return spot
    pytest.fail("no kuhn spot in the default catalog")


def _solve(iterations):
    return {"algorithm": "vanilla-cfr", "iterations": iterations, "seed": None}


def test_operations_set():
    assert PRACTICE_OPERATIONS == frozenset(
        {"practice-list-spots", "practice-solve-spot", "practice-submit-play",
         "practice-progress", "practice-leaderboard"})  # W4 contract additions


def test_list_envelope_json_safe(listing):
    assert set(listing) == {"version", "operation", "result", "provenance"}
    assert listing["version"] == 4 and listing["operation"] == "practice-list-spots"
    assert listing["provenance"] is None
    assert set(listing["result"]) == {"spots", "families"}
    assert listing["result"]["spots"]
    _strict(listing)
    limited = handle_practice("practice-list-spots", {"limit": 1, "seed": 0})
    assert len(limited["result"]["spots"]) == 1


def test_solve_and_submit_json_safe(kuhn_spot):
    sid = kuhn_spot["spot_id"]
    solved = handle_practice("practice-solve-spot",
                             {"spot_id": sid, "solve": _solve(50)})
    _strict(solved)
    assert solved["operation"] == "practice-solve-spot"
    assert isinstance(solved["provenance"], dict)
    assert solved["result"]["spot"]["spot_id"] == sid
    action = solved["result"]["optimal_action"]
    sub = handle_practice("practice-submit-play",
                          {"spot_id": sid, "play": action, "solve": _solve(50),
                           "user": "tester"})
    _strict(sub)
    assert set(sub["result"]) == {"user", "score", "solved", "progress"}  # W4: + progress
    assert sub["result"]["user"] == "tester"
    assert sub["provenance"] == solved["provenance"]
    assert sub["result"]["score"]["provenance"] == sub["provenance"]


def test_r1_iterations_change_score_and_hash(kuhn_spot):
    """Same play, iterations 5 vs 500: params_hash changes and best_q/mix_q/score move."""
    sid = kuhn_spot["spot_id"]
    lo_solve = handle_practice("practice-solve-spot", {"spot_id": sid, "solve": _solve(5)})
    legal = lo_solve["result"]["legal_actions"]
    play = legal[0]
    lo = handle_practice("practice-submit-play",
                         {"spot_id": sid, "play": play, "solve": _solve(5)})
    hi = handle_practice("practice-submit-play",
                         {"spot_id": sid, "play": play, "solve": _solve(500)})
    assert lo["provenance"]["params_hash"] != hi["provenance"]["params_hash"]
    assert lo["result"]["solved"]["spot"]["spot_id"] == sid
    assert hi["result"]["solved"]["spot"]["spot_id"] == sid
    assert lo["provenance"]["iterations"] == 5 and hi["provenance"]["iterations"] == 500
    keys = ("best_q", "solver_mix_q", "score")
    assert tuple(lo["result"]["score"][k] for k in keys) != \
        tuple(hi["result"]["score"][k] for k in keys)


@pytest.mark.parametrize("op,payload", [
    ("practice-list-spots", {"bogus": 1}),
    ("practice-list-spots", {"limit": True}),
    ("practice-list-spots", {"limit": 0}),
    ("practice-list-spots", {"seed": 1.0}),
    ("practice-list-spots", {"families": []}),
    ("practice-list-spots", {"families": ["no-such-family"]}),
    ("practice-list-spots", []),
    ("practice-solve-spot", {}),
    ("practice-solve-spot", {"spot_id": "does/not-exist"}),
    ("practice-solve-spot", {"spot_id": 3}),
    ("practice-submit-play", {"spot_id": "x"}),
    ("practice-unknown", {}),
])
def test_validation_errors(op, payload):
    with pytest.raises(ValueError):
        handle_practice(op, payload)


@pytest.mark.parametrize("solve", [
    {"algorithm": "vanilla-cfr", "iterations": 0, "seed": None},
    {"algorithm": "vanilla-cfr", "iterations": 20001, "seed": None},
    {"algorithm": "vanilla-cfr", "iterations": True, "seed": None},
    {"algorithm": "vanilla-cfr", "iterations": 10, "seed": True},
    {"algorithm": "nope", "iterations": 10, "seed": None},
    {"algorithm": "vanilla-cfr", "iterations": 10, "seed": 7},  # vanilla needs null
    {"algorithm": "vanilla-cfr", "iterations": 10.0},
    [],
    {"algorithm": "vanilla-cfr", "iterations": 10, "seed": None, "x": 1},
])
def test_solve_override_validation(kuhn_spot, solve):
    with pytest.raises(ValueError):
        handle_practice("practice-solve-spot", {"spot_id": kuhn_spot["spot_id"],
                                                "solve": solve})


def test_submit_rejects_bad_play_and_user(kuhn_spot):
    sid = kuhn_spot["spot_id"]
    for payload in ({"spot_id": sid, "play": {"kind": "jam"}, "solve": _solve(5)},
                    {"spot_id": sid, "play": {"kind": "check"}, "user": "",
                     "solve": _solve(5)},
                    {"spot_id": sid, "play": {"kind": "check"}, "score": 100}):
        with pytest.raises(ValueError):
            handle_practice("practice-submit-play", payload)


# --------------------------------------------------------------------------- CLI


def test_cli_list_solve_submit(kuhn_spot, capsys):
    assert main(["list", "--limit", "2"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["operation"] == "practice-list-spots" and len(out["result"]["spots"]) == 2

    sid = kuhn_spot["spot_id"]
    assert main(["solve", sid, "--iterations", "20"]) == 0
    solved = json.loads(capsys.readouterr().out)
    assert solved["provenance"]["iterations"] == 20
    action = solved["result"]["legal_actions"][0]

    argv = ["submit", sid, action["kind"]]
    if action["amount"]:
        argv.append(str(action["amount"]))
    assert main(argv + ["--iterations", "20"]) == 0
    sub = json.loads(capsys.readouterr().out)
    assert sub["operation"] == "practice-submit-play"
    assert sub["result"]["score"]["grade"] in {
        "Perfect", "Good", "Inaccuracy", "Mistake", "Blunder"}


def test_cli_errors_exit_nonzero(kuhn_spot, capsys):
    assert main(["solve", "nope/000000000000"]) != 0
    assert "error:" in capsys.readouterr().err
    assert main(["submit", kuhn_spot["spot_id"], "jam", "--iterations", "5"]) != 0
    assert main(["solve", kuhn_spot["spot_id"], "--iterations", "0"]) != 0

