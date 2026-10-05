"""W5 regression tests for disk solve cache audit findings F1, F2, F8, F9, F10.

Each test reproduces the corresponding repro from
``research/practice-mode/w5-audit/audit-backend.md``. Every cached value comes from a real runtime solve.
"""

from __future__ import annotations

import json
import logging
import shutil

import pytest

from poker_solver.practice import solve_cache as sc
from poker_solver.practice.adapter import SolverAdapter
from poker_solver.practice.catalog import generate_catalog
from poker_solver.practice.models import SolveParams
from poker_solver.practice.solve_cache import DiskSolveCache, solved_from_record, solved_to_record

FAST = SolveParams(iterations=20)


@pytest.fixture(scope="module")
def spot():
    return generate_catalog(families=("kuhn-intro",), solve=FAST, limit=1)[0]


@pytest.fixture(scope="module")
def solved(spot):
    return SolverAdapter().solve(spot)


def _written(tmp_path, solved):
    key = solved.spot.params_hash()
    DiskSolveCache(tmp_path)[key] = solved
    path = tmp_path / f"{key}.json"
    assert path.is_file()
    return key, path


def _rewrite(path, fn):
    rec = json.loads(path.read_text())
    fn(rec)
    path.write_text(json.dumps(rec))


# --------------------------------------------------------------------------- F1


def _set_info_key(value):
    def fn(rec):
        rec["info_key"] = value
    return fn


F1_CORRUPTIONS = {
    "invalid-utf8": lambda p: p.write_bytes(b"\xff\xfe\x00garbage"),
    "deep-nesting": lambda p: p.write_text("[" * 100000 + "]" * 100000),
    "fraction-zero-den": lambda p: _rewrite(p, _set_info_key({"$": "fraction", "n": 1, "d": 0})),
    "fraction-bad-type": lambda p: _rewrite(p, _set_info_key({"$": "fraction", "n": "x", "d": [1]})),
    "info-key-missing-tag-field": lambda p: _rewrite(p, _set_info_key({"$": "tuple"})),
    "map-not-pairs": lambda p: _rewrite(p, _set_info_key({"$": "map", "v": [1, 2]})),
    "unhashable-frozenset-item": lambda p: _rewrite(
        p, _set_info_key({"$": "frozenset", "v": [{"$": "list", "v": [1]}]})),
    "record-is-list": lambda p: p.write_text("[1, 2, 3]"),
    "solved-spot-is-string": lambda p: _rewrite(p, lambda r: r["solved"].__setitem__("spot", "nope")),
    "strategy-entries-not-objects": lambda p: _rewrite(p, lambda r: r["solved"].__setitem__("strategy", [1, 2])),
    "provenance-missing": lambda p: _rewrite(p, lambda r: r["solved"].pop("provenance")),
    "legal-actions-null": lambda p: _rewrite(p, lambda r: r["solved"].__setitem__("legal_actions", None)),
    "huge-int-float-overflow": lambda p: _rewrite(
        p, lambda r: r["solved"]["strategy"][0].__setitem__("probability", 10 ** 400)),
}


@pytest.mark.parametrize("name", sorted(F1_CORRUPTIONS))
def test_f1_any_undecodable_record_is_a_miss_and_removed(tmp_path, solved, name, caplog):
    key, path = _written(tmp_path, solved)
    F1_CORRUPTIONS[name](path)
    for attempt in (1, 2):  # never raises, and stays a miss after removal
        fresh = DiskSolveCache(tmp_path)
        with caplog.at_level(logging.WARNING, logger=sc.__name__):
            assert fresh.get(key) is None
            assert key not in fresh
        assert not path.exists()
    # re-solve through the adapter re-persists a valid file
    adapter = SolverAdapter(cache=DiskSolveCache(tmp_path))
    assert adapter.solve(solved.spot).strategy == solved.strategy
    assert adapter.solve_count == 1 and path.exists()
    assert DiskSolveCache(tmp_path)[key] == adapter.solve(solved.spot)


def test_f1_corruption_through_adapter_is_resolved_not_raised(tmp_path, solved):
    """Audit repro: memory layer cleared (restart) + corrupt file -> solve succeeds, file replaced."""
    key, path = _written(tmp_path, solved)
    good = path.read_text()
    cache = DiskSolveCache(tmp_path)
    adapter = SolverAdapter(cache=cache)
    for corrupt in (F1_CORRUPTIONS["invalid-utf8"], F1_CORRUPTIONS["deep-nesting"],
                    F1_CORRUPTIONS["fraction-zero-den"]):
        corrupt(path)
        for _ in (1, 2):
            cache._memory.clear()
            result = adapter.solve(solved.spot)
            assert result.strategy == solved.strategy
            assert json.loads(path.read_text())["key"] == key  # re-persisted valid record
        path.write_text(good)


def test_f1_transient_read_error_keeps_file(tmp_path, solved, monkeypatch):
    key, path = _written(tmp_path, solved)
    fresh = DiskSolveCache(tmp_path)

    def boom(self):
        raise PermissionError("denied")

    monkeypatch.setattr(sc.Path, "read_bytes", boom)
    assert fresh.get(key) is None
    monkeypatch.undo()
    assert path.exists() and fresh.discarded == 0
    assert DiskSolveCache(tmp_path)[key] == solved


# --------------------------------------------------------------------------- F2


def test_f2_record_carries_code_fingerprint(tmp_path, solved):
    _, path = _written(tmp_path, solved)
    rec = json.loads(path.read_text())
    assert rec["schema"] == sc.SCHEMA == "practice-solve-cache-v2"
    assert rec["code_fingerprint"] == sc.code_fingerprint()
    assert len(sc.code_fingerprint()) == 64
    assert DiskSolveCache(tmp_path).stats()["code_fingerprint"] == sc.code_fingerprint()


def test_f2_fingerprint_covers_required_modules():
    required = {
        "cfr.py", "kuhn.py", "river.py", "allstreet.py", "multistreet.py", "nplayer_preflop.py",
        "nplayer.py", "best_response.py", "evaluator.py", "practice/adapter.py", "practice/evaluate.py",
        "practice/models.py", "practice/scoring.py", "practice/catalog.py",
    }
    assert required <= set(sc.FINGERPRINT_MODULES)
    root = sc.Path(sc.__file__).resolve().parent.parent
    missing = [m for m in sc.FINGERPRINT_MODULES if not (root / m).is_file()]
    assert missing == []


def test_f2_fingerprint_is_cached_and_deterministic():
    assert sc.code_fingerprint() is sc.code_fingerprint()
    assert sc.compute_code_fingerprint() == sc.code_fingerprint()


@pytest.mark.parametrize("module", ["cfr.py", "kuhn.py", "practice/adapter.py", "practice/evaluate.py"])
def test_f2_editing_solver_source_changes_fingerprint(tmp_path, module):
    pkg = sc.Path(sc.__file__).resolve().parent.parent
    copy = tmp_path / "poker_solver"
    for rel in sc.FINGERPRINT_MODULES:
        (copy / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pkg / rel, copy / rel)
    assert sc.compute_code_fingerprint(copy) == sc.code_fingerprint()
    with open(copy / module, "a", encoding="utf-8") as handle:
        handle.write("\n# behaviour change\n")
    assert sc.compute_code_fingerprint(copy) != sc.code_fingerprint()
    (copy / module).unlink()
    assert sc.compute_code_fingerprint(copy) != sc.code_fingerprint()


def test_f2_stale_code_record_is_rejected_even_with_same_version(tmp_path, solved, spot):
    """Audit repro: 'mutant' code writes the cache (same package version), real code reads it."""
    key = spot.params_hash()
    mutant = DiskSolveCache(tmp_path, fingerprint="0" * 64)  # same solver_version, different code
    mutant[key] = solved
    path = tmp_path / f"{key}.json"
    rec = json.loads(path.read_text())
    assert rec["solver_version"] == solved.provenance.solver_version and rec["code_fingerprint"] == "0" * 64
    real = DiskSolveCache(tmp_path)
    assert real.get(key) is None and not path.exists() and real.discarded == 1
    adapter = SolverAdapter(cache=real)
    adapter.solve(spot)
    assert adapter.solve_count == 1
    assert json.loads(path.read_text())["code_fingerprint"] == sc.code_fingerprint()


def test_f2_record_without_fingerprint_is_rejected(tmp_path, solved):
    key, path = _written(tmp_path, solved)
    _rewrite(path, lambda r: r.pop("code_fingerprint"))
    assert DiskSolveCache(tmp_path).get(key) is None and not path.exists()


def test_f2_v1_schema_records_are_rejected(tmp_path, solved):
    key, path = _written(tmp_path, solved)
    _rewrite(path, lambda r: r.__setitem__("schema", "practice-solve-cache-v1"))
    assert DiskSolveCache(tmp_path).get(key) is None and not path.exists()


def test_f2_solved_from_record_checks_fingerprint(solved):
    rec = json.loads(json.dumps(solved_to_record(solved)))
    key = solved.spot.params_hash()
    assert solved_from_record(rec, key=key, fingerprint=sc.code_fingerprint()) == solved
    with pytest.raises(ValueError, match="code_fingerprint"):
        solved_from_record(rec, key=key, fingerprint="f" * 64)


# --------------------------------------------------------------------------- F8


def _prov(field, value):
    def fn(rec):
        rec["solved"]["provenance"][field] = value
    return fn


def _prov_param(field, value):
    def fn(rec):
        rec["solved"]["provenance"]["params"][field] = value
    return fn


F8_TAMPERS = {
    "iterations": _prov("iterations", 99999),
    "algorithm-seed": lambda r: (_prov("algorithm", "external-sampling-mccfr")(r), _prov("seed", 7)(r)),
    "seed-only": _prov("seed", 3),
    "params-pot": _prov_param("pot", 999.0),
    "params-extra-field": _prov_param("bogus", 1),
    "params-missing-field": lambda r: r["solved"]["provenance"]["params"].pop("pot"),
    "params-int-vs-float": _prov_param("pot", 2),  # canonical pot is float 2.0 -> types must match
    "params-hash-other": _prov("params_hash", "a" * 64),
    "audit-combined": lambda r: (_prov_param("pot", 999.0)(r), _prov("iterations", 99999)(r)),
}


@pytest.mark.parametrize("name", sorted(F8_TAMPERS))
def test_f8_provenance_inconsistent_with_spot_is_rejected(tmp_path, solved, name):
    key, path = _written(tmp_path, solved)
    rec = json.loads(path.read_text())
    if name == "params-int-vs-float":
        assert rec["solved"]["provenance"]["params"]["pot"] == 2.0
    _rewrite(path, F8_TAMPERS[name])
    fresh = DiskSolveCache(tmp_path)
    assert fresh.get(key) is None
    assert not path.exists() and fresh.discarded == 1


def test_f8_consistent_record_still_loads(tmp_path, solved):
    key, _ = _written(tmp_path, solved)
    loaded = DiskSolveCache(tmp_path)[key]
    assert loaded == solved
    assert loaded.provenance.params_hash == key == loaded.spot.params_hash()
    assert dict(loaded.provenance.params) is not None


def test_f8_solved_from_record_without_key_still_checks_consistency(solved):
    rec = json.loads(json.dumps(solved_to_record(solved)))
    rec["solved"]["provenance"]["iterations"] = 12345
    with pytest.raises(ValueError, match="iterations"):
        solved_from_record(rec)


# --------------------------------------------------------------------------- F9


def test_f9_memory_items_zero_and_write_failure_returns_solve(tmp_path, spot, monkeypatch):
    cache = DiskSolveCache(tmp_path, memory_items=0)

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(sc.os, "replace", boom)
    adapter = SolverAdapter(cache=cache)
    other = spot.with_solve(SolveParams(iterations=21))
    result = adapter.solve(other)  # audit: KeyError here
    assert result.provenance.iterations == 21
    assert cache[other.params_hash()] == result  # kept in memory since not persisted
    assert adapter.solve(other) is result and adapter.solve_count == 1
    assert [p.name for p in tmp_path.iterdir()] == []


def test_f9_unpersisted_entries_survive_lru_but_persisted_are_evicted(tmp_path, monkeypatch):
    spots = generate_catalog(families=("kuhn-intro",), solve=SolveParams(iterations=5), limit=3)
    cache = DiskSolveCache(tmp_path, memory_items=2)  # the unpersisted entry uses one slot
    adapter = SolverAdapter(cache=cache)
    real_replace = sc.os.replace

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(sc.os, "replace", boom)
    volatile = adapter.solve(spots[0])
    monkeypatch.setattr(sc.os, "replace", real_replace)
    adapter.solve(spots[1])
    adapter.solve(spots[2])
    keys = [s.params_hash() for s in spots]
    assert keys[0] in cache._memory  # unpersisted: never evicted
    assert keys[1] not in cache._memory and keys[2] in cache._memory  # LRU bound for persisted
    assert cache[keys[0]] is volatile
    # once it is persisted it becomes evictable again
    cache[keys[0]] = volatile
    assert (tmp_path / f"{keys[0]}.json").exists()
    adapter.solve(spots[1])  # disk hit -> evicts spots[2]
    adapter.solve(spots[2])  # disk hit -> evicts the now-persisted spots[0]
    assert keys[0] not in cache._memory and adapter.solve_count == 3


def test_f9_memory_items_zero_happy_path_reads_back_from_disk(tmp_path, spot):
    cache = DiskSolveCache(tmp_path, memory_items=0)
    adapter = SolverAdapter(cache=cache)
    result = adapter.solve(spot)
    assert len(cache._memory) == 0 and cache[spot.params_hash()] == result


# --------------------------------------------------------------------------- F10


@pytest.mark.parametrize(
    "key", [123, "nothex", None, "A" * 64, "../" + "a" * 61, "a" * 63, ("a" * 64,), b"a" * 64, 1.5],
)
def test_f10_contains_is_false_for_malformed_keys(tmp_path, key):
    cache = DiskSolveCache(tmp_path)
    assert (key in cache) is False
    assert list(tmp_path.iterdir()) == []


def test_f10_contains_still_true_for_present_key(tmp_path, solved):
    key, _ = _written(tmp_path, solved)
    assert key in DiskSolveCache(tmp_path)
    assert "b" * 64 not in DiskSolveCache(tmp_path)
