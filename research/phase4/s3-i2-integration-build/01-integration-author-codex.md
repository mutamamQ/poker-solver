# C3I2-CODEX-IG1 author receipt

UTC: 2026-09-16T10:03:13.447693+00:00
HEAD: 68e0ad2e9983928e666c3aabfa5d32161f7baca8
Status: author GREEN
blocker_count: 0

Implemented strict solve-nplayer-preflop JSON parsing using existing helpers and typed config, sizing, continuation and history classes; calls the real solve_nplayer_preflop. Exact nested fields, strict numerics, finite values, duplicate keys, malformed arrays/history/sizing, unsupported seeds/algorithms/straddles and invalid bounds fail closed. Fresh JSON containers preserve real solver metadata/provenance, config_version=4, max_nodes/max_depth, seed=None and approximate=False. Certificates are nullable and serialize as finite floats.

Diff scope: api_v4.py has 212 insertions and 1 deletion. Only other authored files are this report and .hb/C3I2-CODEX-IG1. No commit or git writes. All baseline files outside these three authorized paths have matching SHA-256 hashes. Removing the new helper and reverting the operation registration/routing exactly reproduces baseline api_v4.py, proving existing operation source preservation.

Pre-existing changes in PROGRESS.md, STATE.txt, __init__.py, api_v3.py and the untracked integration research directory were preserved. Exports/capability were not edited.

## Commands and results

All commands ran in /home/genomix-node/poker-solver. Test commands exited 0. uv ran with no sync/cache, Python bytecode disabled and pytest cacheprovider disabled.

```sh
PYTHONDONTWRITEBYTECODE=1 UV_NO_CACHE=1 uv run --no-sync pytest -q -p no:cacheprovider tests/test_api_v4_nplayer_preflop.py
```
Result: 30 passed in 0.21s.

```sh
PYTHONDONTWRITEBYTECODE=1 UV_NO_CACHE=1 uv run --no-sync pytest -q -p no:cacheprovider tests/test_phase4_s3_examples.py
```
Result: 13 passed in 2.76s.

```sh
PYTHONDONTWRITEBYTECODE=1 UV_NO_CACHE=1 uv run --no-sync pytest -q -p no:cacheprovider tests/test_api_v4_nplayer_preflop.py tests/test_phase4_s3_examples.py tests/test_phase4_s3_exports.py
```
Result: 56 passed in 3.21s.

```sh
PYTHONDONTWRITEBYTECODE=1 UV_NO_CACHE=1 uv run --no-sync pytest -q -p no:cacheprovider tests/test_nplayer_preflop_solve.py
```
Result: 52 passed in 3.36s.

```sh
PYTHONDONTWRITEBYTECODE=1 UV_NO_CACHE=1 uv run --no-sync pytest -q -p no:cacheprovider tests/test_api_v4.py tests/test_api_v4_nplayer.py tests/test_api_v3.py tests/test_phase4_s1_cli.py tests/test_cli.py tests/test_cli_phase2.py
```
Result: 95 passed in 10.67s.

```sh
PYTHONDONTWRITEBYTECODE=1 UV_NO_CACHE=1 uv run --no-sync python - <<'PY'
import compileall
from unittest.mock import patch
# compileall ignores PYTHONDONTWRITEBYTECODE; suppress its bytecode writer.
with patch('importlib._bootstrap_external._write_atomic'):
    assert compileall.compile_dir('src/poker_solver', quiet=1, force=True)
print('compileall: PASS (bytecode writes suppressed)')
PY
```
Result: compileall: PASS (bytecode writes suppressed), exit 0.

```sh
git diff --check
```
Result: exit 0, no output.

```sh
PYTHONDONTWRITEBYTECODE=1 UV_NO_CACHE=1 uv run --no-sync python - <<'PY'
import json
from copy import deepcopy
from pathlib import Path
from poker_solver.api_v4 import dispatch_v4
request=json.loads(Path('examples/phase4/nplayer_2p_preflop.json').read_text())
request['payload']['include_deviation_certificate']=True
request['payload']['max_pure_strategies']=100000
result=dispatch_v4(request)
assert result['certificate'] is not None
assert result == dispatch_v4(deepcopy(request))
json.dumps(result, allow_nan=False)
for expression in ({'unit': []}, {'unit': 'all-in', 'value': 1}, {'unit': 'big-blinds', 'value': True}, {'unit': 'geometric', 'streets': 1, 'scale': float('inf')}):
    bad=deepcopy(request)
    bad['payload']['sizing_rules']=[{'position': 'BTN/SB', 'raise_count': 0, 'cold_callers': 0, 'relation': 'NA', 'expressions': [expression]}]
    try:
        dispatch_v4(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(expression)
print('certificate/determinism/finite JSON and malformed sizing probes: PASS')
PY
```
Result: certificate/determinism/finite JSON and malformed sizing probes: PASS, exit 0.

```sh
git diff --stat -- src/poker_solver/api_v4.py
```
Result: 1 file changed, 212 insertions(+), 1 deletion(-).

Receipt-generation note: the first report-writing heredoc command failed with exit 2 because a nested PY delimiter terminated it early (unterminated triple-quoted string). It made no writes. Corrected using RECEIPT_SCRIPT delimiter. This was a reporting command error, not a product/test failure.

This is author verification only, not a claim of independent audit, full repository regression, parent acceptance or accepted-wave commit.

## SHA-256

```text
e70584d5ead154011a70b13572eaa55cdfee2f76c408e5f5e7866b2ae672069a  api_v4.py (baseline)
70d378d6a52ae544615a5aa4dda6bd9e987f8161f08119914a0762ed0727a1a3  src/poker_solver/api_v4.py
01ad9f614a01a4b623a36d42b611d75050fbe3ebdead650fbd4272852e593a4a  src/poker_solver/api_v3.py
0c2a03813d375d362c582b3df0744d80802c5f008e2b42825f4afeaed5326159  src/poker_solver/__init__.py
5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae  src/poker_solver/nplayer_preflop.py
3f4df8452f427757d11c7bcee8b44b783efe65290b2f18050cdeba67d94ada13  src/poker_solver/cli.py
6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db  ARCHITECTURE_PHASE4_S3.md
38b36491172a3152157ff369f680ba0a5bab25c5a551db3552ed7074f52ff50d  tests/test_api_v4_nplayer_preflop.py
8c3a416b298aa4bad0c902817500ccf7450f73636330cebc396fac8828f27061  tests/test_phase4_s3_examples.py
40df575dd72fd5b39a9bbd7c5f3b1358a2a344f92be0d5b587bdb1b4bc232c60  tests/test_phase4_s3_exports.py
45291a2e7537883acfcf35a3c700e50fe03225c4a00db3a75372ca243326d51c  tests/test_nplayer_preflop_solve.py
```
