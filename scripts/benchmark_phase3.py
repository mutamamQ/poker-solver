"""Run the packaged Phase-3 benchmark harness."""

import json

from poker_solver.benchmark_phase3 import run_benchmarks


if __name__ == "__main__":
    print(json.dumps(run_benchmarks(), sort_keys=True, separators=(",", ":")))
