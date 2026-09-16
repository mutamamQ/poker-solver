# A303 examples and generic CLI audit — parent-recovered artifact

Fresh non-author A303 executed a read-only audit of the frozen S2-I2 candidate. The worker omitted its owned report and heartbeat, so the parent recovered this artifact from canonical transcript `deleg_04dfd111/task-2.log` after ownership ended.

Evidence executed by A303:

- Verified frozen hashes for `nplayer.py`, `nplayer_postflop.py`, `api_v4.py`, and all three example JSON files.
- Inspected the 4-, 5-, and 9-player requests: exact v4 operation, complete one-combo ranges and showdown deal/ranks, `max_deals=1`, `max_nodes=2000`, `iterations=2`.
- Executed each through the unchanged generic command `uv run python -m poker_solver.cli phase4 <file> --json`; all exited zero with N-length values, six normalized infosets, deterministic/no-convergence metadata, and structural depths 9/11/19.
- Executed `tests/test_phase4_s2_examples.py`: `7 passed`.
- Executed stdin/file/error paths. Missing payload, wrong version/incomplete envelope, malformed JSON, missing file, and incomplete payload all exited 2 with deterministic errors.
- Confirmed the legacy `solve-spot` command rejects v4 requests rather than silently routing them.

Parent reconciliation at 2026-09-16T00:05Z verified the complete manifest `12/12` post-hash and preserved `phase3-398-green`.

Verdict: PASS.
