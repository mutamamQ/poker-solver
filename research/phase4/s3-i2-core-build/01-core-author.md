# C3I2-CODEX-G1 core GREEN receipt

status=CORE_GREEN_READY
blocker_count=0
Live UTC from `date -u +%Y-%m-%dT%H:%M:%SZ`: 2026-09-16T08:50:47Z

Implemented frozen/slotted NPlayerPreflopSolveResult and solve_nplayer_preflop in the sole owned source. Result construction and dataclasses.replace detach both strategy map levels and recursively freeze metadata mappings, lists, tuples, sets, and frozensets while preserving keys. The facade validates the typed config and strict solve arguments, uses the prescribed bounded vanilla CFR solver, computes expected values and optional exhaustive diagnostics, and reports truthful metadata with approximate=False and no convergence guarantee.

Initial SHA-256 verified before edits:
`a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812`

Final source SHA-256:
`5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae`

Read PHASE4_MISSION.md, architecture sections 2.5/10/12/13, the full solve test, generic N-player solver, postflop result/facade precedent, and reconciled reports 02–06. No genuine contract contradiction found.

## Exact verification commands and results

First:
```sh
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_solve.py
```
Exit 0: 52 passed in 1.03s.

Then the required core gate:
```sh
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_solve.py tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py
```
Exit 0: 108 passed in 1.20s. Includes deterministic HU/6/9 solves, independent six-player deviation oracle and inclusive cap, strict validation, detached replacement results, structural/node bounds, and accepted state/config/betting/settlement/information controls.

Compileall used the owned heartbeat path temporarily for bytecode to honor exclusive writable paths; the bytecode was removed immediately:
```sh
PYTHONDONTWRITEBYTECODE=1 uv run python - <<'PYCOMPILE'
import compileall
import py_compile
from pathlib import Path
from unittest.mock import patch

source = 'src/poker_solver/nplayer_preflop.py'
owned_output = Path('research/phase4/s3-i2-core-build/.hb/C3I2-CODEX-G1')
original_compile = py_compile.compile

def compile_to_owned_path(file, cfile=None, *args, **kwargs):
    return original_compile(file, str(owned_output), *args, **kwargs)

try:
    with patch.object(py_compile, 'compile', compile_to_owned_path):
        assert compileall.compile_file(source, force=True, quiet=1)
    print('compileall: passed; bytecode restricted to owned heartbeat path')
finally:
    owned_output.unlink(missing_ok=True)
PYCOMPILE
```
Exit 0: compileall passed; no bytecode probe remains.

```sh
git diff --check -- src/poker_solver/nplayer_preflop.py research/phase4/s3-i2-core-build/01-core-author.md research/phase4/s3-i2-core-build/.hb/C3I2-CODEX-G1
```
Exit 0, no output (also rerun after writing this receipt).

```sh
sha256sum src/poker_solver/nplayer_preflop.py
date -u +%Y-%m-%dT%H:%M:%SZ
git diff -- src/poker_solver/nplayer_preflop.py
```
Exit 0; final hash as above. Diff reviewed: imports and appended facade/result/helper only; existing state implementation unchanged.

## Scope confirmation

Worked only in /home/genomix-node/poker-solver. Writes restricted to src/poker_solver/nplayer_preflop.py, this report, and .hb/C3I2-CODEX-G1. No tests, APIs, package exports, examples, other reports, STATE.txt, PROGRESS.md, or git state edited. No commit. No probes remain. Full regression, fresh independent audit, and integration remain parent gates; this receipt claims only the requested core gate.
