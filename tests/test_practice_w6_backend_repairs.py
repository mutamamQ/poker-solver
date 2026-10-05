"""W6 re-audit backend repairs: N1 single-flight error propagation, N3 fingerprint coverage."""
import threading
import time

from poker_solver.practice import catalog
from poker_solver.practice.adapter import SolverAdapter
from poker_solver.practice.solve_cache import FINGERPRINT_MODULES


def test_n3_fingerprint_covers_nplayer_metrics():
    assert any(m.endswith("nplayer_metrics.py") for m in FINGERPRINT_MODULES)


def test_n1_waiters_get_leader_error_without_resolving():
    spot = catalog.generate_catalog()[0]
    adapter = SolverAdapter()
    calls = []
    gate = threading.Event()

    def failing(_spot, _key):
        calls.append(1)
        gate.wait(5)
        raise ValueError("boom")

    adapter._solve_cold = failing
    errors = []

    def run():
        try:
            adapter.solve(spot)
        except ValueError as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=run) for _ in range(4)]
    for t in threads:
        t.start()
    time.sleep(0.5)  # let all four join the same flight
    gate.set()
    for t in threads:
        t.join(10)
    assert errors == ["boom"] * 4
    assert len(calls) == 1
    # the failed flight is discarded: a later request solves again
    gate.set()
    try:
        adapter.solve(spot)
    except ValueError:
        pass
    assert len(calls) == 2
