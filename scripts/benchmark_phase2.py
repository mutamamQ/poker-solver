#!/usr/bin/env python3
"""Phase 2 standalone benchmark: Kuhn vanilla/MCCFR throughput and peak RSS.

Measures median iterations/second and peak memory without making correctness claims.
Emits stable-schema JSON to stdout.
"""

import argparse
import json
import resource
import statistics
import sys
import time
from pathlib import Path

# Add src to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from poker_solver.cfr import CFRSolver
from poker_solver.kuhn import kuhn_root
from poker_solver.mccfr import MCCFRSolver


def measure_throughput(solver_factory, iterations: int, trials: int = 5) -> dict:
    """Measure median throughput over multiple trials.
    
    Args:
        solver_factory: Callable that returns a fresh solver instance
        iterations: Number of iterations per trial
        trials: Number of measurement trials
    
    Returns:
        dict with median_iterations_per_sec, min/max, and trial data
    """
    rates = []
    for _ in range(trials):
        solver = solver_factory()
        start = time.perf_counter()
        solver.train(iterations)
        elapsed = time.perf_counter() - start
        rate = iterations / elapsed if elapsed > 0 else 0.0
        rates.append(rate)
    
    return {
        "median_iterations_per_sec": statistics.median(rates),
        "min_iterations_per_sec": min(rates),
        "max_iterations_per_sec": max(rates),
        "trials": trials,
        "iterations_per_trial": iterations,
        "all_rates": rates
    }


def measure_peak_rss_kb() -> int:
    """Get peak RSS in kilobytes."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # ru_maxrss is in KB on Linux, bytes on macOS
    if sys.platform == 'darwin':
        return usage.ru_maxrss // 1024
    return usage.ru_maxrss


def benchmark_vanilla_cfr(iterations: int, trials: int) -> dict:
    """Benchmark vanilla CFR on Kuhn poker."""
    def factory():
        return CFRSolver(kuhn_root())
    
    rss_before = measure_peak_rss_kb()
    throughput = measure_throughput(factory, iterations, trials)
    rss_after = measure_peak_rss_kb()
    
    return {
        "algorithm": "vanilla-cfr",
        "game": "kuhn",
        "throughput": throughput,
        "peak_rss_kb": rss_after,
        "rss_delta_kb": rss_after - rss_before
    }


def benchmark_mccfr(iterations: int, trials: int, seed: int = 0) -> dict:
    """Benchmark MCCFR on Kuhn poker."""
    def factory():
        return MCCFRSolver(kuhn_root(), seed=seed)
    
    rss_before = measure_peak_rss_kb()
    throughput = measure_throughput(factory, iterations, trials)
    rss_after = measure_peak_rss_kb()
    
    return {
        "algorithm": "mccfr",
        "game": "kuhn",
        "seed": seed,
        "throughput": throughput,
        "peak_rss_kb": rss_after,
        "rss_delta_kb": rss_after - rss_before
    }


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Phase 2 CFR algorithms",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help="Iterations per trial (default: 1000)"
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=5,
        help="Number of measurement trials (default: 5)"
    )
    parser.add_argument(
        "--algorithm",
        choices=["vanilla", "mccfr", "both"],
        default="both",
        help="Algorithm to benchmark (default: both)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="MCCFR seed (default: 0)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON to file instead of stdout"
    )
    
    args = parser.parse_args()
    
    results = {
        "schema_version": 1,
        "benchmarks": []
    }
    
    if args.algorithm in ("vanilla", "both"):
        print("Benchmarking vanilla CFR...", file=sys.stderr)
        results["benchmarks"].append(
            benchmark_vanilla_cfr(args.iterations, args.trials)
        )
    
    if args.algorithm in ("mccfr", "both"):
        print("Benchmarking MCCFR...", file=sys.stderr)
        results["benchmarks"].append(
            benchmark_mccfr(args.iterations, args.trials, args.seed)
        )
    
    output_json = json.dumps(results, indent=2, sort_keys=True)
    
    if args.output:
        args.output.write_text(output_json)
        print(f"Results written to {args.output}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
