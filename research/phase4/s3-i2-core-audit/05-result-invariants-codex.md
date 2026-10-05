# C3I2-CODEX-C5 result-invariants audit

owner=C3I2-CODEX-C5
status=COMPLETE
result=PASS
blocker_count=0
manifest_count_before=10/10
manifest_count_after=10/10
utc=2026-09-16T09:26:06Z

Fresh non-author audit of the frozen S3-I2 core candidate. The verdict covers result invariants and the permanent solve facade tests, not the separately gated API/examples/exports or a full regression run. No candidate source, tests, examples, API files, other reports, STATE, PROGRESS, or git were edited; no commit was made. The only audit artifact writes are this report and research/phase4/s3-i2-core-audit/.hb/C3I2-CODEX-C5. The independent program ran from stdin without a temporary repository file. Python bytecode and pytest's cache provider were disabled in the verification commands.

## Findings

PASS: direct construction of NPlayerPreflopSolveResult with an ordinary mutable outer dict keyed by the hashable tuple ('caller-owned-policy', 7), an ordinary inner dict keyed by Action("fold"), and recursively mutable metadata detaches caller-owned standard containers. After construction, changing the original inner dict, clearing the outer dict, modifying nested lists/dicts/sets and a mutable child inside a tuple, and clearing the original metadata did not change the result.

PASS: normal assignment to result fields raises FrozenInstanceError; outer and inner strategy item assignment and metadata dict/tuple item assignment raise TypeError; append/add on frozen metadata containers raises AttributeError. The direct check also rejects mutation of expected_values and a real returned certificate. This establishes the standard container/typed result contract exercised here; it does not claim freezing arbitrary custom mutable objects stored as metadata leaves or validation of arbitrary constructor inputs.

PASS: approximate is exactly False in the directly constructed result and in permanent-fixture solves (weighted 2/6/9-player cases and the six-player certificate case). Every exercised policy is nonempty, finite, bounded in [0,1], and normalized within absolute tolerance 1e-12. Returned values are finite and zero-sum within absolute tolerance 1e-12. Permanent-fixture returned EVs agree with the test module's independent recursive tree evaluator. The direct construction is only a container check and is not represented as a solved game.

PASS: certificate absence agrees with metadata "not-requested" on the weighted permanent fixtures. Certificate presence on the permanent six-player fixture agrees with "exhaustive-diagnostic-only". Values, best-response values, incentives, and total incentive agree with the permanent independent exhaustive pure-deviation oracle. The exact pure-strategy cap is 4, with per-player counts (1, 4, 4, 1, 1, 1); requesting cap 3 fails closed with ValueError: player pure-strategy bound exceeded. The permanent suite additionally checks cap 1 failure.

PASS: returned provenance is exactly "full-tree deterministic vanilla CFR; no convergence guarantee"; certificate provenance is exactly "exhaustive finite pure unilateral deviations; diagnostic only". Metadata declares converged=False, convergence_claim="none", deterministic=True. Thus approximate=False describes full-tree execution on the declared finite fixture; it does not assert equilibrium convergence or real-world accuracy of the fixtures' supplied synthetic showdown ranks. The permanent _config fixtures were reused unchanged; no malformed game fixtures were invented.

Static evidence: src/poker_solver/nplayer_preflop.py:1042 recursively freezes standard metadata containers; :1055 defines the frozen result dataclass; :1072 copies outer and inner strategy maps; :1107 conditionally computes the certificate; :1124-1135 declares diagnostic/convergence metadata, provenance, and approximate=False. Permanent evidence: tests/test_nplayer_preflop_solve.py, including test_solve_deterministic_finite_immutable_result, test_six_player_oracle_runs_independently_before_facade, test_six_player_exhaustive_certificate_and_exact_cap, and test_certificate_cap_fails_closed.

## Initial literal manifest verification

Working directory for every command: /home/genomix-node/poker-solver.
This command ran before candidate source/test evidence was used. It parses every literal raw SHA-256 row, requires exactly ten rows, and independently hashes each file.

```bash
PYTHONDONTWRITEBYTECODE=1 python - <<'PY'
from pathlib import Path
import hashlib,re
p=Path('research/phase4/s3-i2-core-audit/CANDIDATE_MANIFEST.md')
rows=re.findall(r'^([0-9a-f]{64})  (.+)$',p.read_text(),re.M)
assert len(rows)==10,len(rows)
for expected,name in rows:
    actual=hashlib.sha256(Path(name).read_bytes()).hexdigest()
    print(f'{"PASS" if actual==expected else "FAIL"} {actual}  {name}')
    assert actual==expected,name
print('manifest_count=10/10')
print('manifest_sha256='+hashlib.sha256(p.read_bytes()).hexdigest())
PY
```

Exit code: 0. Exact output:

```text
PASS 6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db  ARCHITECTURE_PHASE4_S3.md
PASS 484b95ec85131f3d50212398dc3055dd747a03fb5a5151333a28c6130980b294  src/poker_solver/nplayer.py
PASS 5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae  src/poker_solver/nplayer_preflop.py
PASS 45291a2e7537883acfcf35a3c700e50fe03225c4a00db3a75372ca243326d51c  tests/test_nplayer_preflop_solve.py
PASS bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268  tests/test_nplayer_preflop_config.py
PASS 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd  tests/test_nplayer_preflop_betting.py
PASS e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
PASS 1217cf74f1468252fbc7f941621dc57154c910003eb27fbf8947b7bc5a42e289  tests/test_nplayer_preflop_information.py
PASS 1826b203fe264acd159e5efb35d07a5122ddb12fb75c405078833733a7c3bcec  research/phase4/s3-i2-core-build/01-core-author.md
PASS a51dfcbc692fc434bbe5f485d526f83e411de6e837a4111d06a6c055822e7065  research/phase4/s3-i2-core-build/PARENT_CORE_GATE.md
manifest_count=10/10
manifest_sha256=81ef2c2af67792e6d1c5f5ae0ba2b2d6d433dc8c4bcca8ab662dd93100993d84
```

## Required permanent test command

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_solve.py
```

Exit code: 0. Exact combined output (the tool split the progress dots across two reads):

```text
....................................................                     [100%]
52 passed in 1.03s
```

## Independent in-memory direct construction and permanent-fixture checks

Exact command:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python - <<'PY'
from dataclasses import FrozenInstanceError
from math import isfinite, isclose, prod
from operator import setitem
import runpy
from poker_solver.model import Action
from poker_solver.nplayer_preflop import NPlayerPreflopSolveResult

def rejected(label, action, error):
    try:
        action()
    except error as exc:
        print(f'PASS rejected {label}: {type(exc).__name__}')
    else:
        raise AssertionError(f'mutation accepted: {label}')

key = ('caller-owned-policy', 7)
fold = Action("fold")
inner = {fold: 1.0}
outer = {key: inner}
flags = [False, {'depth': [1]}]
tags = {'original'}
tuple_child = [{'items': [2]}]
metadata = {'nested': {'flags': flags, 'tags': tags, 'tuple': tuple(tuple_child)}}
result = NPlayerPreflopSolveResult(
    config_version=4, game_version='nplayer-preflop-v1',
    algorithm='vanilla-cfr', iterations=1, max_nodes=100, max_depth=5,
    strategy=outer, expected_values=(0.0, 0.0), certificate=None,
    metadata=metadata, provenance='direct container audit; no solver execution claimed',
    approximate=False,
)
inner[fold] = -99.0
inner[Action("check")] = 100.0
outer.clear()
flags.append(True)
flags[1]['depth'].append(99)
tags.add('changed')
tuple_child[0]['items'].append(99)
metadata['nested']['added'] = True
metadata.clear()
assert dict(result.strategy[key]) == {fold: 1.0}
assert tuple(result.strategy) == (key,)
nested = result.metadata['nested']
assert nested['flags'][0] is False and len(nested['flags']) == 2
assert nested['flags'][1]['depth'] == (1,)
assert nested['tags'] == frozenset({'original'})
assert nested['tuple'][0]['items'] == (2,)
assert set(nested) == {'flags', 'tags', 'tuple'}
print('PASS caller mutation detached: outer/inner dict; nested dict/list/set/tuple-child')
rejected('result field', lambda: setattr(result, 'iterations', 99), FrozenInstanceError)
rejected('result strategy field', lambda: setattr(result, 'strategy', {}), FrozenInstanceError)
rejected('outer strategy', lambda: setitem(result.strategy, key, {}), TypeError)
rejected('inner strategy', lambda: setitem(result.strategy[key], fold, 0), TypeError)
rejected('metadata root', lambda: setitem(result.metadata, 'new', True), TypeError)
rejected('metadata nested dict', lambda: setitem(nested, 'new', True), TypeError)
rejected('metadata frozen list', lambda: setitem(nested['flags'], 0, True), TypeError)
rejected('metadata list append', lambda: nested['flags'].append(True), AttributeError)
rejected('metadata dict inside list', lambda: setitem(nested['flags'][1], 'depth', []), TypeError)
rejected('metadata recursive list', lambda: setitem(nested['flags'][1]['depth'], 0, 9), TypeError)
rejected('metadata set', lambda: nested['tags'].add('new'), AttributeError)
rejected('metadata tuple child', lambda: setitem(nested['tuple'][0]['items'], 0, 9), TypeError)
rejected('expected values tuple', lambda: setitem(result.expected_values, 0, 1), TypeError)

def invariants(r):
    assert r.approximate is False
    assert all(isfinite(v) for v in r.expected_values)
    assert isclose(sum(r.expected_values), 0, abs_tol=1e-12)
    for policy in r.strategy.values():
        assert policy
        assert all(isfinite(p) and 0 <= p <= 1 for p in policy.values())
        assert isclose(sum(policy.values()), 1, rel_tol=0, abs_tol=1e-12)

invariants(result)
assert result.certificate is None
print('PASS direct result: approximate=False; finite normalized probabilities; finite zero-sum values')

fixtures = runpy.run_path('tests/test_nplayer_preflop_solve.py')
for n in (2, 6, 9):
    config = fixtures['_config'](n, weighted=True)
    root, _, infosets = fixtures['_tree'](config)
    solved = fixtures['_solve'](config, iterations=3)
    invariants(solved)
    assert len(solved.expected_values) == n
    assert set(solved.strategy) == set(infosets)
    for k, policy in solved.strategy.items():
        assert set(policy) == set(infosets[k][1])
    oracle_values = fixtures['_values'](root, solved.strategy)
    assert all(isclose(a, float(b), rel_tol=0, abs_tol=1e-12)
               for a, b in zip(solved.expected_values, oracle_values, strict=True))
    assert solved.certificate is None
    assert dict(solved.metadata) == {
        'converged': False, 'convergence_claim': 'none',
        'deterministic': True, 'deviation_certificate': 'not-requested'}
    assert solved.provenance == 'full-tree deterministic vanilla CFR; no convergence guarantee'
    print(f'PASS permanent weighted n={n}: approximate=False; normalized finite policies; zero-sum EV={solved.expected_values!r}; independent tree EV match; certificate absent and not-requested; no convergence claim')

config = fixtures['_config'](6)
root, _, infosets = fixtures['_tree'](config)
cap = max(prod(len(actions) for owner, actions in infosets.values() if owner == seat)
          for seat in range(6))
assert cap == 4
solved = fixtures['_solve'](config, iterations=3, include_deviation_certificate=True,
                            max_pure_strategies=cap)
invariants(solved)
cert = solved.certificate
assert cert is not None
baseline, best, incentives, counts = fixtures['_oracle'](root, infosets, solved.strategy)
for actual, expected in ((solved.expected_values, baseline), (cert.values, baseline),
                         (cert.best_response_values, best), (cert.incentives, incentives)):
    assert len(actual) == 6
    assert all(isfinite(a) and isclose(a, float(b), rel_tol=0, abs_tol=1e-12)
               for a, b in zip(actual, expected, strict=True))
assert isclose(cert.total_incentive, float(sum(incentives)), rel_tol=0, abs_tol=1e-12)
assert cert.provenance == 'exhaustive finite pure unilateral deviations; diagnostic only'
assert dict(solved.metadata) == {
    'converged': False, 'convergence_claim': 'none',
    'deterministic': True, 'deviation_certificate': 'exhaustive-diagnostic-only'}
assert solved.provenance == 'full-tree deterministic vanilla CFR; no convergence guarantee'
print(f'PASS permanent six-player certificate: cap={cap}; counts={counts!r}; values/best-responses/incentives/total match independent exhaustive oracle; diagnostic provenance and no convergence claim')
rejected('certificate field', lambda: setattr(cert, 'total_incentive', 99), FrozenInstanceError)
try:
    fixtures['_solve'](config, iterations=1, include_deviation_certificate=True,
                       max_pure_strategies=cap-1)
except ValueError as exc:
    assert 'pure-strategy bound exceeded' in str(exc)
    print(f'PASS certificate cap fails closed: {type(exc).__name__}: {exc}')
else:
    raise AssertionError('certificate cap accepted')
print('independent_check=PASS blocker_count=0')
PY
```

Exit code: 0. Exact output:

```text
PASS caller mutation detached: outer/inner dict; nested dict/list/set/tuple-child
PASS rejected result field: FrozenInstanceError
PASS rejected result strategy field: FrozenInstanceError
PASS rejected outer strategy: TypeError
PASS rejected inner strategy: TypeError
PASS rejected metadata root: TypeError
PASS rejected metadata nested dict: TypeError
PASS rejected metadata frozen list: TypeError
PASS rejected metadata list append: AttributeError
PASS rejected metadata dict inside list: TypeError
PASS rejected metadata recursive list: TypeError
PASS rejected metadata set: AttributeError
PASS rejected metadata tuple child: TypeError
PASS rejected expected values tuple: TypeError
PASS direct result: approximate=False; finite normalized probabilities; finite zero-sum values
PASS permanent weighted n=2: approximate=False; normalized finite policies; zero-sum EV=(-1.0295138888888888, 1.0295138888888888); independent tree EV match; certificate absent and not-requested; no convergence claim
PASS permanent weighted n=6: approximate=False; normalized finite policies; zero-sum EV=(0.5, -1.7083333333333335, -0.29166666666666663, -1.0, -1.0, 3.5); independent tree EV match; certificate absent and not-requested; no convergence claim
PASS permanent weighted n=9: approximate=False; normalized finite policies; zero-sum EV=(1.25, -1.7083333333333335, -0.29166666666666663, -1.0, -1.0, -1.0, -1.0, -1.0, 5.75); independent tree EV match; certificate absent and not-requested; no convergence claim
PASS permanent six-player certificate: cap=4; counts=(1, 4, 4, 1, 1, 1); values/best-responses/incentives/total match independent exhaustive oracle; diagnostic provenance and no convergence claim
PASS rejected certificate field: FrozenInstanceError
PASS certificate cap fails closed: ValueError: player pure-strategy bound exceeded
independent_check=PASS blocker_count=0
```

## Final literal manifest verification

After all tests/checks, the initial literal manifest verification command above was run again unchanged.

Exit code: 0. Exact output:

```text
PASS 6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db  ARCHITECTURE_PHASE4_S3.md
PASS 484b95ec85131f3d50212398dc3055dd747a03fb5a5151333a28c6130980b294  src/poker_solver/nplayer.py
PASS 5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae  src/poker_solver/nplayer_preflop.py
PASS 45291a2e7537883acfcf35a3c700e50fe03225c4a00db3a75372ca243326d51c  tests/test_nplayer_preflop_solve.py
PASS bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268  tests/test_nplayer_preflop_config.py
PASS 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd  tests/test_nplayer_preflop_betting.py
PASS e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
PASS 1217cf74f1468252fbc7f941621dc57154c910003eb27fbf8947b7bc5a42e289  tests/test_nplayer_preflop_information.py
PASS 1826b203fe264acd159e5efb35d07a5122ddb12fb75c405078833733a7c3bcec  research/phase4/s3-i2-core-build/01-core-author.md
PASS a51dfcbc692fc434bbe5f485d526f83e411de6e837a4111d06a6c055822e7065  research/phase4/s3-i2-core-build/PARENT_CORE_GATE.md
manifest_count=10/10
manifest_sha256=81ef2c2af67792e6d1c5f5ae0ba2b2d6d433dc8c4bcca8ab662dd93100993d84
```

## Live completion clock

```bash
date -u '+%Y-%m-%dT%H:%M:%SZ'
```

Exit code: 0. Exact output:

```text
2026-09-16T09:26:06Z
```

## Report hash inputs

Algorithm: SHA-256. The report hash input is every byte of the final UTF-8 file research/phase4/s3-i2-core-audit/05-result-invariants-codex.md, including its final newline, with no exclusions or normalization. Its digest is recorded as report_sha256 in the flat final heartbeat and returned at artifact verification, avoiding a self-referential embedded digest. Candidate evidence inputs are the ten literal file/hash pairs printed above, the manifest itself (SHA-256 81ef2c2af67792e6d1c5f5ae0ba2b2d6d433dc8c4bcca8ab662dd93100993d84), and the exact commands/results recorded in this report.

Verification command:

```bash
sha256sum research/phase4/s3-i2-core-audit/05-result-invariants-codex.md
```

Final disposition: PASS. blocker_count=0. Both manifest checks are 10/10.
