"""Persistent practice solve cache tests. Every cached value comes from a real runtime solve."""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import threading
from fractions import Fraction

import pytest

from poker_solver.cards import parse_cards
from poker_solver.equity import WeightedCombo
from poker_solver.model import Action
from poker_solver.practice import solve_cache as sc
from poker_solver.practice.adapter import SolverAdapter
from poker_solver.practice.catalog import generate_catalog
from poker_solver.practice.models import PracticeSpot, SolvedSpot, SolveParams
from poker_solver.practice.solve_cache import DiskSolveCache, solved_from_record, solved_to_record

FAST = SolveParams(iterations=30)


def first(family, solve=FAST):
    return generate_catalog(families=(family,), solve=solve, limit=1)[0]


def allstreet_spot(iterations=10):
    board = parse_cards(["Td", "8h", "2c"])
    r0 = (WeightedCombo(parse_cards(["As", "Ah"]), 1.0), WeightedCombo(parse_cards(["5s", "4s"]), 1.0))
    r1 = (WeightedCombo(parse_cards(["Qs", "Qh"]), 1.0), WeightedCombo(parse_cards(["Jd", "Jc"]), 1.0))
    return PracticeSpot(
        family="flop-check-small-tree", backend="allstreet", game_type="heads-up", street="flop",
        board=board, hero_seat=1, villain_seats=(0,), ranges=(r0, r1), pot=100, stacks=(100, 100),
        action_history=(Action("CHECK"),), bet_sizes=(33,), hero_hand=parse_cards(["Qs", "Qh"]),
        solve=SolveParams(iterations=iterations),
        backend_extra={"allowed_runouts": [list(parse_cards(["3d", "7c"]))], "betting_mode": "no-limit",
                       "max_nodes": 5000, "max_depth": 40},
    )


def assert_fields_equal(a: SolvedSpot, b: SolvedSpot) -> None:
    for f in dataclasses.fields(SolvedSpot):
        va, vb = getattr(a, f.name), getattr(b, f.name)
        assert va == vb, f.name
    for f in dataclasses.fields(PracticeSpot):
        assert getattr(a.spot, f.name) == getattr(b.spot, f.name), f.name
    assert a.spot.params_hash() == b.spot.params_hash()
    assert a.spot.spot_id == b.spot.spot_id
    # floats exact (not approximately equal)
    for action in a.legal_actions:
        assert a.strategy[action].hex() == b.strategy[action].hex()
        assert a.action_values[action].hex() == b.action_values[action].hex()
    assert a.provenance.to_json() == b.provenance.to_json()
    assert a.to_json() == b.to_json()
    assert a == b


@pytest.fixture(scope="module")
def solved_kuhn():
    return SolverAdapter().solve(first("kuhn-intro"))


@pytest.fixture(scope="module")
def solved_river():
    return SolverAdapter().solve(first("river-oop-bet-or-check"))


@pytest.mark.parametrize("which", ["solved_kuhn", "solved_river"])
def test_record_round_trip_is_exact(which, request):
    solved = request.getfixturevalue(which)
    text = json.dumps(solved_to_record(solved))
    back = solved_from_record(json.loads(text), key=solved.spot.params_hash())
    assert_fields_equal(solved, back)


def test_allstreet_round_trip_is_exact():
    solved = SolverAdapter().solve(allstreet_spot())
    back = solved_from_record(json.loads(json.dumps(solved_to_record(solved))), key=solved.spot.params_hash())
    assert_fields_equal(solved, back)


def test_info_key_codec_handles_generic_components():
    key = ("v", 3, None, True, 1.5, Fraction(7, 3), (Action("RAISE", 6), (1, 2)), frozenset({1, 2}), "x")
    assert sc._decode_key(json.loads(json.dumps(sc._encode_key(key)))) == key
    with pytest.raises(ValueError):
        sc._encode_key((object(),))


@pytest.mark.parametrize("which", ["solved_kuhn", "solved_river"])
def test_disk_round_trip_through_fresh_instance(tmp_path, which, request):
    solved = request.getfixturevalue(which)
    key = solved.spot.params_hash()
    DiskSolveCache(tmp_path)[key] = solved
    path = tmp_path / f"{key}.json"
    assert path.is_file()
    record = json.loads(path.read_text())
    assert record["schema"] == sc.SCHEMA and record["key"] == key
    assert record["solver_version"] == solved.provenance.solver_version
    fresh = DiskSolveCache(tmp_path)
    assert key in fresh and len(fresh) == 1 and list(fresh) == [key]
    assert_fields_equal(solved, fresh[key])


def test_second_adapter_hits_disk_without_solving(tmp_path):
    spot = first("river-ip-facing-bet")
    a1 = SolverAdapter(cache=DiskSolveCache(tmp_path))
    r1 = a1.solve(spot)
    assert a1.solve_count == 1
    a2 = SolverAdapter(cache=DiskSolveCache(tmp_path))
    assert a2.cached(spot) is not None
    r2 = a2.solve(spot)
    assert a2.solve_count == 0
    assert_fields_equal(r1, r2)


def test_different_iterations_is_a_different_key(tmp_path):
    spot = first("kuhn-intro")
    a1 = SolverAdapter(cache=DiskSolveCache(tmp_path))
    a1.solve(spot)
    other = spot.with_solve(SolveParams(iterations=31))
    assert other.params_hash() != spot.params_hash()
    a2 = SolverAdapter(cache=DiskSolveCache(tmp_path))
    assert a2.cached(other) is None
    a2.solve(other)
    assert a2.solve_count == 1
    assert len(DiskSolveCache(tmp_path)) == 2


@pytest.mark.parametrize(
    "mutate",
    [
        lambda text, rec: "{not json",
        lambda text, rec: text[: len(text) // 2],
        lambda text, rec: json.dumps({**rec, "schema": "practice-solve-cache-v0"}),
        lambda text, rec: json.dumps({**rec, "solver_version": "0.0.0-other"}),
        lambda text, rec: json.dumps({**rec, "key": "0" * 64}),
        lambda text, rec: json.dumps({**rec, "solved": {**rec["solved"], "strategy": []}}),
        lambda text, rec: json.dumps(
            {**rec, "solved": {**rec["solved"], "spot": {**rec["solved"]["spot"], "pot": 3.0}}}
        ),
    ],
    ids=["garbage", "truncated", "schema", "solver-version", "key", "bad-strategy", "hash-mismatch"],
)
def test_corrupt_or_mismatched_file_is_a_miss_and_removed(tmp_path, solved_kuhn, mutate, caplog):
    key = solved_kuhn.spot.params_hash()
    DiskSolveCache(tmp_path)[key] = solved_kuhn
    path = tmp_path / f"{key}.json"
    text = path.read_text()
    path.write_text(mutate(text, json.loads(text)))
    fresh = DiskSolveCache(tmp_path)
    with caplog.at_level(logging.WARNING, logger=sc.__name__):
        assert fresh.get(key) is None
    assert not path.exists()
    assert fresh.discarded == 1
    # a fresh adapter then re-solves and re-persists
    adapter = SolverAdapter(cache=fresh)
    resolved = adapter.solve(solved_kuhn.spot)
    assert resolved.strategy == solved_kuhn.strategy  # deterministic vanilla CFR
    assert adapter.solve_count == 1 and path.exists()


def test_file_under_wrong_name_is_rejected(tmp_path, solved_kuhn, solved_river):
    cache = DiskSolveCache(tmp_path)
    cache[solved_kuhn.spot.params_hash()] = solved_kuhn
    wrong = solved_river.spot.params_hash()
    os.replace(tmp_path / f"{solved_kuhn.spot.params_hash()}.json", tmp_path / f"{wrong}.json")
    assert DiskSolveCache(tmp_path).get(wrong) is None
    assert not (tmp_path / f"{wrong}.json").exists()


@pytest.mark.parametrize(
    "key",
    ["../" + "a" * 61, "a" * 63, "A" * 64, "a" * 64 + "/x", "/etc/passwd", "", "g" * 64, 123, None, "a" * 65],
)
def test_traversal_or_malformed_keys_rejected(tmp_path, solved_kuhn, key):
    cache = DiskSolveCache(tmp_path)
    with pytest.raises(ValueError):
        cache[key]
    with pytest.raises(ValueError):
        cache[key] = solved_kuhn
    with pytest.raises(ValueError):
        del cache[key]
    assert list(tmp_path.iterdir()) == []


def test_value_must_match_key(tmp_path, solved_kuhn, solved_river):
    cache = DiskSolveCache(tmp_path)
    with pytest.raises(ValueError):
        cache[solved_river.spot.params_hash()] = solved_kuhn
    with pytest.raises(ValueError):
        cache[solved_kuhn.spot.params_hash()] = {"not": "solved"}  # type: ignore[assignment]


def test_writes_are_atomic_and_leave_no_temp_files(tmp_path, solved_kuhn, monkeypatch):
    key = solved_kuhn.spot.params_hash()
    cache = DiskSolveCache(tmp_path)
    calls = []
    real_replace = os.replace

    def spy(src, dst):
        calls.append((os.path.dirname(src), os.path.basename(dst)))
        return real_replace(src, dst)

    monkeypatch.setattr(sc.os, "replace", spy)
    cache[key] = solved_kuhn
    assert calls == [(str(tmp_path), f"{key}.json")]
    assert sorted(p.name for p in tmp_path.iterdir()) == [f"{key}.json"]

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(sc.os, "replace", boom)
    other = solved_kuhn.spot.with_solve(SolveParams(iterations=7))
    solved_other = SolverAdapter().solve(other)
    cache[other.params_hash()] = solved_other  # fail-soft: kept in memory
    assert cache[other.params_hash()] == solved_other
    assert sorted(p.name for p in tmp_path.iterdir()) == [f"{key}.json"]


def test_unwritable_dir_degrades_to_memory(tmp_path, solved_kuhn, caplog):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    with caplog.at_level(logging.WARNING, logger=sc.__name__):
        cache = DiskSolveCache(blocker / "sub", memory_items=1)
    assert not cache.disk_ok
    assert any("memory-only" in r.message for r in caplog.records)
    adapter = SolverAdapter(cache=cache)
    adapter.solve(solved_kuhn.spot)
    adapter.solve(solved_kuhn.spot.with_solve(SolveParams(iterations=5)))
    adapter.solve(solved_kuhn.spot)
    assert adapter.solve_count == 2  # memory-only mode never evicts
    assert cache.stats()["count"] == 0 and len(cache) == 2


def test_memory_lru_is_bounded_but_disk_keeps_everything(tmp_path):
    cache = DiskSolveCache(tmp_path, memory_items=2)
    adapter = SolverAdapter(cache=cache)
    spots = generate_catalog(families=("kuhn-intro",), solve=SolveParams(iterations=5), limit=4)
    for spot in spots:
        adapter.solve(spot)
    assert len(cache._memory) == 2
    assert len(cache) == 4
    for spot in spots:
        assert adapter.solve(spot).spot == spot
    assert adapter.solve_count == 4


def test_from_env_uses_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv(sc.ENV_VAR, str(tmp_path / "envcache"))
    cache = DiskSolveCache.from_env()
    assert cache.directory == tmp_path / "envcache" and cache.disk_ok
    monkeypatch.delenv(sc.ENV_VAR)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert sc.default_cache_dir() == tmp_path / "home" / ".cache" / "poker-solver" / "practice"


def test_delete_clear_and_stats(tmp_path, solved_kuhn, solved_river):
    cache = DiskSolveCache(tmp_path)
    for solved in (solved_kuhn, solved_river):
        cache[solved.spot.params_hash()] = solved
    (tmp_path / ".tmp-stale.json.tmp").write_text("x")
    (tmp_path / "unrelated.txt").write_text("keep")
    stats = cache.stats()
    assert stats["count"] == 2 and stats["bytes"] > 0 and stats["dir"] == str(tmp_path)
    del cache[solved_kuhn.spot.params_hash()]
    with pytest.raises(KeyError):
        del cache[solved_kuhn.spot.params_hash()]
    assert len(cache) == 1
    assert cache.clear() == 1
    assert len(cache) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["unrelated.txt"]


def test_concurrency_smoke(tmp_path):
    spots = generate_catalog(families=("kuhn-intro",), solve=SolveParams(iterations=10), limit=6)
    cache = DiskSolveCache(tmp_path, memory_items=3)
    errors: list[BaseException] = []
    results: dict[int, list] = {}

    def worker(i: int) -> None:
        try:
            adapter = SolverAdapter(cache=cache if i % 2 else DiskSolveCache(tmp_path, memory_items=2))
            results[i] = [adapter.solve(s) for s in spots[i % 3:] + spots[: i % 3]]
        except BaseException as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    by_key = {}
    for solved_list in results.values():
        for solved in solved_list:
            key = solved.spot.params_hash()
            # same deterministic solve regardless of thread / hit / miss (wall time aside)
            norm = solved.to_json()
            norm["provenance"].pop("wall_time_s")
            by_key.setdefault(key, norm)
            assert by_key[key] == norm
    assert len(by_key) == 6
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(f"{k}.json" for k in by_key)
    fresh = DiskSolveCache(tmp_path)
    for key in by_key:
        assert fresh[key].spot.params_hash() == key


def test_cli_warm_stats_clear(tmp_path, capsys):
    d = str(tmp_path / "cli")
    assert sc.main(["--dir", d, "warm", "--families", "kuhn-intro", "--limit", "2", "--iterations", "5"]) == 0
    out = capsys.readouterr().out
    assert sum(line.startswith("miss ") for line in out.splitlines()) == 2 and "0 hit, 2 miss" in out
    assert sc.main(["--dir", d, "warm", "--families", "kuhn-intro", "--limit", "2", "--iterations", "5"]) == 0
    out = capsys.readouterr().out
    assert "2 hit, 0 miss" in out and out.splitlines()[0].startswith("hit")
    assert sc.main(["--dir", d, "stats"]) == 0
    out = capsys.readouterr().out
    assert "count: 2" in out and f"dir: {d}" in out
    assert sc.main(["--dir", d, "clear"]) == 0
    assert "removed 2" in capsys.readouterr().out
    assert sc.main(["--dir", d, "stats"]) == 0
    assert "count: 0" in capsys.readouterr().out
    assert sc.main(["--dir", d, "warm", "--families", "no-such-family"]) == 2


def test_cli_uses_env_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv(sc.ENV_VAR, str(tmp_path / "envcli"))
    assert sc.main(["stats"]) == 0
    assert f"dir: {tmp_path / 'envcli'}" in capsys.readouterr().out


def test_no_presolved_cache_files_in_repo():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    offenders = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", ".venv", "node_modules", "__pycache__")]
        for name in filenames:
            if name.endswith(".json") and sc._KEY_RE.match(name[:-5]):
                offenders.append(os.path.join(dirpath, name))
    assert offenders == []
