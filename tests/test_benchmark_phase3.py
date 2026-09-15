"""Phase-3 benchmark harness semantic regression tests."""

from poker_solver.benchmark_phase3 import run_benchmarks


def test_phase3_benchmarks_execute_bounded_representative_workloads():
    result = run_benchmarks()
    assert tuple(result) == ("icm_10", "inference_64", "deviation_3p", "checkdown")
    for item in result.values():
        assert item["elapsed_seconds"] >= 0
        assert item["semantic_check"] is True
        assert item["scope"] == "synthetic bounded regression benchmark"


def test_phase3_benchmark_semantic_results_repeat():
    first = run_benchmarks()
    second = run_benchmarks()
    assert {
        key: value["result_fingerprint"] for key, value in first.items()
    } == {
        key: value["result_fingerprint"] for key, value in second.items()
    }
