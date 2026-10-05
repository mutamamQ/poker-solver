"""Permanent checks for the solver-evaluation benchmark (research/solver-evaluation).

Runs the benchmark in ``quick`` mode (< 2 min budget, real solver runs, no copied
numbers) into a temp dir and asserts: it runs, the results JSON schema, the worst-case
verdict rule, and that the Kuhn analytic criterion (value -1/18) is PASS.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "research" / "solver-evaluation" / "benchmark.py"
VERDICTS = {"PASS", "PARTIAL", "FAIL"}


def _load():
    spec = importlib.util.spec_from_file_location("solver_eval_benchmark", BENCH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def quick(tmp_path_factory):
    bench = _load()
    out = tmp_path_factory.mktemp("solver_eval")
    results = bench.run(mode="quick", out_dir=out)
    return bench, results, out


def test_quick_mode_writes_parseable_results(quick):
    _bench, results, out = quick
    path = out / "results.json"
    assert path.is_file()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["mode"] == "quick"
    assert on_disk == json.loads(json.dumps(results, allow_nan=False))
    assert (out / "results.md").is_file()


def test_results_schema(quick):
    bench, results, _out = quick
    assert results["schema_version"] == bench.SCHEMA_VERSION
    for key in ("mode", "started_at", "finished_at", "wall_time_s", "host", "git", "thresholds",
                "criteria", "capabilities", "overall", "verdict_rule"):
        assert key in results, key
    host = results["host"]
    for key in ("platform", "python", "machine", "cpu_count"):
        assert key in host
    assert set(results["git"]) >= {"commit", "branch", "dirty"}
    assert results["wall_time_s"] < 120.0
    ids = [c["id"] for c in results["criteria"]]
    assert len(ids) == len(set(ids))
    assert set(bench.CRITERIA_IDS) <= set(ids)
    for crit in results["criteria"]:
        assert crit["verdict"] in VERDICTS
        assert isinstance(crit["thresholds"], dict) and crit["thresholds"]
        assert isinstance(crit["evidence"], dict) and crit["evidence"]
        assert crit["wall_time_s"] >= 0
    caps = {c["capability"]: c for c in results["capabilities"]}
    assert set(caps) == set(bench.CAPABILITIES)
    for cap in caps.values():
        assert cap["verdict"] in VERDICTS and cap["evidence"] and "gaps" in cap


def test_overall_is_worst_case(quick):
    bench, results, _out = quick
    order = {"PASS": 0, "PARTIAL": 1, "FAIL": 2}
    every = [c["verdict"] for c in results["criteria"]] + [c["verdict"] for c in results["capabilities"]]
    assert results["overall"] == max(every, key=order.__getitem__)
    assert bench.worst(["PASS", "PARTIAL"]) == "PARTIAL"
    assert bench.worst(["PASS", "FAIL", "PARTIAL"]) == "FAIL"
    assert bench.worst(["PASS"]) == "PASS"


def test_kuhn_criterion_passes_against_analytic_value(quick):
    _bench, results, _out = quick
    kuhn = next(c for c in results["criteria"] if c["id"] == "C1-kuhn-analytic")
    assert kuhn["verdict"] == "PASS", kuhn
    final = kuhn["evidence"]["checkpoints"][-1]
    assert abs(final["ev0"] - (-1.0 / 18.0)) <= kuhn["thresholds"]["pass_value_error"]
    nash = [row["nash_conv"] for row in kuhn["evidence"]["checkpoints"]]
    assert nash[-1] < nash[0]


def test_grading_helper_is_threshold_driven():
    bench = _load()
    assert bench.grade_upper(0.5, pass_max=1.0, partial_max=2.0) == "PASS"
    assert bench.grade_upper(1.5, pass_max=1.0, partial_max=2.0) == "PARTIAL"
    assert bench.grade_upper(2.5, pass_max=1.0, partial_max=2.0) == "FAIL"
    assert bench.grade_upper(float("nan"), pass_max=1.0, partial_max=2.0) == "FAIL"
