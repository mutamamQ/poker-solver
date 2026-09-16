# A301 core solver/reach/diagnostic audit — parent reconciliation

Fresh non-author A301 recovery verified all twelve initial hashes and executed `tests/test_nplayer_postflop_solve.py`: `9 passed`.

Independent executed probes:

1. Default `NPlayerCFRSolver` construction remained compatible and collected six infosets.
2. A five-player reach game produced exact one-iteration player-4 regrets `WIN=+1.0`, `LOSE=-1.0`, confirming opponent reach `(1/2)^4` against terminal values ±16.
3. Repeated solves returned identical values and strategy; mutation of one detached result did not affect another.
4. All 60 returned policies were nonnegative and normalized within `1e-12`.
5. A five-player solve returned exactly five finite float values.
6. Exact certificate structure/provenance matched the permanent independent enumeration contract.
7. `max_nodes=1` failed closed with a node-bound error.
8. `max_depth=1` failed closed with a depth-bound error.
9. `max_pure_strategies=1` failed closed with a pure-strategy-bound error.

The worker's on-disk report remained an in-progress template despite its completed execution summary; after ownership ended, parent replaced it with this factual reconciliation and verified all twelve post-hashes.

Verdict: PASS. No blocking or non-blocking findings.
