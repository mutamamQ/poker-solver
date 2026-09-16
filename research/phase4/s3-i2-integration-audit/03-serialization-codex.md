# C3I2-CODEX-I3 serialization audit

status=PASS
blockers=none
auditor=C3I2-CODEX-I3 (fresh assigned non-author auditor)
working_directory=/home/genomix-node/poker-solver
before_utc=2026-09-16T10:26:44.841254+00:00
after_utc=2026-09-16T10:30:18.581422+00:00

The frozen candidate passes this serialization/detachment scope. No candidate edits, repository probe files, git commands, or commits were made. Bytecode writes and pytest cache were disabled. Probe scripts/logs were confined to /tmp and removed after embedding below. Only this report and `.hb/C3I2-CODEX-I3` are repository outputs. Provider identity beyond the assigned auditor role is not independently attested here.

## Manifest and API integrity

Parsed all 20 literal SHA-256/path rows (not a sampled or reconstructed file list), asserted count and unique paths, hashed file bytes before execution and after all tests/probes, and required equality for every row. Manifest SHA-256 before and after: `363b8a21f6c45053957b905282a9392e0b01a9da37d67136a1ef53a4a29df07c`.

Required API SHA-256 before and after: `70d378d6a52ae544615a5aa4dda6bd9e987f8161f08119914a0762ed0727a1a3` — PASS.

Every row below was independently verified at both UTC timestamps above; each listed actual digest equals its literal expected digest:

```text
6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db  ARCHITECTURE_PHASE4_S3.md  PASS
5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae  src/poker_solver/nplayer_preflop.py  PASS
70d378d6a52ae544615a5aa4dda6bd9e987f8161f08119914a0762ed0727a1a3  src/poker_solver/api_v4.py  PASS
01ad9f614a01a4b623a36d42b611d75050fbe3ebdead650fbd4272852e593a4a  src/poker_solver/api_v3.py  PASS
0c2a03813d375d362c582b3df0744d80802c5f008e2b42825f4afeaed5326159  src/poker_solver/__init__.py  PASS
3f4df8452f427757d11c7bcee8b44b783efe65290b2f18050cdeba67d94ada13  src/poker_solver/cli.py  PASS
45291a2e7537883acfcf35a3c700e50fe03225c4a00db3a75372ca243326d51c  tests/test_nplayer_preflop_solve.py  PASS
38b36491172a3152157ff369f680ba0a5bab25c5a551db3552ed7074f52ff50d  tests/test_api_v4_nplayer_preflop.py  PASS
8c3a416b298aa4bad0c902817500ccf7450f73636330cebc396fac8828f27061  tests/test_phase4_s3_examples.py  PASS
40df575dd72fd5b39a9bbd7c5f3b1358a2a344f92be0d5b587bdb1b4bc232c60  tests/test_phase4_s3_exports.py  PASS
884bd673589224885feeafe8633fc9a4cdae69b18135e9ebf4cd1eae3d7fa8e5  examples/phase4/nplayer_2p_preflop.json  PASS
3d46183d39b0bb905a3679a38776683c47db9657825c92e55bc239176dcc7365  examples/phase4/nplayer_6p_preflop.json  PASS
1f7b26a0e3fee5912b9695a59a2a181dbd13f3b5df386a9fe15f07e690dcdfb9  examples/phase4/nplayer_9p_preflop.json  PASS
14b8dd501d1a36d2ad3aac98d360c097504a17c175058668f248e67a3e3f31ff  research/phase4/s3-i2-integration-build/01-integration-author-codex.md  PASS
c1722069adc923e054cee5773e9d337a384e7749907757e2e2563ccc5d452add  research/phase4/s3-i2-integration-build/02-parser-contract-parent.md  PASS
adf2d65d46d032820ff7f2930f6dd00ac04433262f5335f42d46891703334f5b  research/phase4/s3-i2-integration-build/03-serialization.md  PASS
680b37a0f199fbb2ac9f51f407a3c3d168217eba190d67f3fabedb8d5f555710  research/phase4/s3-i2-integration-build/04-capability-exports.md  PASS
a15a2528a2c093d1ef91b2fc91b7e73e91de2abdc1d92770d0a23c38c61aa0c8  research/phase4/s3-i2-integration-build/05-examples-cli.md  PASS
2b5b61269322cb848c61f047e8e358507aa87cf62d8266775117ca865d8c04f3  research/phase4/s3-i2-integration-build/06-tdd-release.md  PASS
114945024fbf7d2f4356c5f1195fed4770557fb25058ebd23612d75684d9c39f  research/phase4/s3-i2-integration-audit/PARENT_FULL_REGRESSION.md  PASS
```

The verification command used `python -B - <<'PY'` with the following hash-check logic; the first run also saved its UTC, manifest digest and row output to `/tmp/C3I2-CODEX-I3-before.json`. The finalizer repeated the literal parse/hash checks, asserted equality with that saved before output, and explicitly asserted the required API digest.

```python
from pathlib import Path
import hashlib, re, datetime
p=Path("research/phase4/s3-i2-integration-audit/CANDIDATE_MANIFEST.md")
rows=re.findall(r"^([0-9a-f]{64})  (.+)$",p.read_text(),re.M)
assert len(rows)==20 and len({name for _,name in rows})==20
for expected,name in rows:
    actual=hashlib.sha256(Path(name).read_bytes()).hexdigest()
    assert actual==expected,(name,expected,actual)
    print(actual,name,"PASS")
print(datetime.datetime.now(datetime.timezone.utc).isoformat())
```

## Existing tests: exact commands and results

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B -m pytest -p no:cacheprovider -q tests/test_api_v4_nplayer_preflop.py
```

Exit 1: `/home/genomix-node/.hermes/hermes-agent/venv/bin/python: No module named pytest`. Resolved using the existing project virtual environment; no packages installed.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -B -m pytest -p no:cacheprovider -q tests/test_api_v4_nplayer_preflop.py
```

Exit 0: `30 passed in 0.22s`.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -B -m pytest -p no:cacheprovider -q tests/test_nplayer_preflop_solve.py tests/test_api_v4.py::test_result_is_json_serializable_with_strict_nan_check tests/test_api_v4.py::test_metadata_is_truthful_and_complete tests/test_api_v4.py::test_deep_response_isolation_comprehensive tests/test_api_v4_nplayer.py::test_valid_nplayer_request_has_deterministic_detached_response tests/test_api_v4_nplayer.py::test_valid_request_can_return_exact_diagnostic_certificate
```

Exit 0: `57 passed in 4.81s` (52 typed preflop solve controls plus five adjacent API controls). This includes typed nested metadata/strategy detachment, finite deterministic values, certificate diagnostics/caps, strict JSON, and adjacent response isolation. Total: **87 passed**.

## Independent probes

Dispatched the committed 2/6/9 JSON requests unchanged for certificate-disabled cases. Certificate-enabled cases changed only `include_deviation_certificate` in an in-memory request copy. Each case performed three dispatches: pristine baseline, response to mutate, and subsequent fresh response. Input requests remained equal to their pristine copies.

Verified the exact 15 fields: `version`, `operation`, `config_version`, `game_version`, `algorithm`, `iterations`, `seed`, `max_nodes`, `max_depth`, `strategy`, `values`, `certificate`, `metadata`, `provenance`, `approximate`.

All cases passed strict `json.dumps(..., allow_nan=False)` plus JSON round-trip, exact deterministic response equality, string keys throughout, finite probabilities in [0,1] normalized to 1, finite N-seat values summing to zero, and equality to an independent recursive expectation. Numeric comparison used relative and absolute tolerance 1e-12. Response hashes below use UTF-8 `json.dumps(response, allow_nan=False, sort_keys=True)` with default separators.

Constructed typed roots independently from the committed requests (no API parser/solver monkeypatch, no imported test fixture). Traversed every reachable state, checked exact serialized information/action domain equality and absence of stringification collisions, including continuation kind/source/provenance in information keys. These domain/EV checks rely on candidate state transitions; they are not an independent poker-rules implementation. Enabled certificates were additionally checked against independent exhaustive pure unilateral deviation enumeration without production EV/certificate helpers.

Metadata exactly states `converged=False`, `convergence_claim="none"`, `deterministic=True`, and the correct requested/not-requested certificate status. Provenance is exactly `full-tree deterministic vanilla CFR; no convergence guarantee`. `approximate=False` describes the declared finite full-tree path, not an equilibrium guarantee or unrestricted poker solution. Enabled certificate provenance says `exhaustive finite pure unilateral deviations; diagnostic only`; disabled certificate is null. These claims agree with architecture and the inspected finite-tree implementation.

For each case, mutated one returned response's outer strategy and existing nested policy, existing metadata flag and an inserted nested metadata list, existing value and vector length; enabled cases also mutated all three certificate vectors, total incentive, provenance, and outer certificate mapping. Disabled cases replaced the null certificate. Subsequent dispatch equaled the pristine baseline, including strict serialized bytes. Production response metadata is flat, so the inserted nested list is not evidence of a pre-existing nested metadata alias; the existing typed-result control supplies the nested-input metadata detachment coverage.

Two initial /tmp harness runs failed before dispatch: missing required `payoff_table` (TypeError), then importing the distinct equity `WeightedCombo` instead of preflop `WeightedCombo` (ValueError: ranges must contain WeightedCombo values). Corrected only the temporary probe: added `payoff_table={}` and imported `poker_solver.preflop.WeightedCombo`. No candidate defect was indicated. The final exact probe below completed with exit 0.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -B /tmp/C3I2-CODEX-I3-probe.py > /tmp/C3I2-CODEX-I3-probe.log 2>&1
```

Probe source SHA-256: `c0d8369b51e15a650b2d8a0b096d1257c106bccd291044223a5a1503e025dfde`.

```python
import json, math, hashlib, datetime
from pathlib import Path
from copy import deepcopy
from itertools import product
from poker_solver.api_v4 import dispatch_v4
from poker_solver.nplayer_preflop import NPlayerPreflopConfig, NPlayerPreflopContinuation, create_nplayer_preflop_root
from poker_solver.game_structure import ForcedPost
from poker_solver.preflop import WeightedCombo
from poker_solver.model import CHANCE, TERMINAL
FIELDS=set('version operation config_version game_version algorithm iterations seed max_nodes max_depth strategy values certificate metadata provenance approximate'.split())
def close(a,b):
    assert math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12),(a,b)
def keys(x):
    if isinstance(x,dict):
        assert all(isinstance(k,str) for k in x)
        for v in x.values(): keys(v)
    elif isinstance(x,list):
        for v in x: keys(v)
for n in (2,6,9):
    request=json.loads(Path(f'examples/phase4/nplayer_{n}p_preflop.json').read_text())
    p=request['payload']; c=p['continuation']
    assert p['sizing_rules']==[] and c['kind']=='showdown-ranks'
    config=NPlayerPreflopConfig(version=p['version'],num_players=n,button=p['button'],starting_stacks=tuple(p['starting_stacks']),forced_posts=tuple(ForcedPost(**x) for x in p['forced_posts']),straddle_variant=p['straddle_variant'],ranges=tuple(tuple(WeightedCombo(tuple(x['cards']),x['weight']) for x in r) for r in p['ranges']),sizing_rules=(),max_raises=p['max_raises'],max_deals=p['max_deals'],max_nodes=p['max_nodes'],short_all_in_reopens=p['short_all_in_reopens'],continuation=NPlayerPreflopContinuation(payoff_table={},kind=c['kind'],source=c['source'],provenance=c['provenance'],showdown_ranks={tuple(tuple(h) for h in e['deal']):tuple(e['ranks']) for e in c['entries']},odd_chip_order=tuple(c['odd_chip_order'])))
    root=create_nplayer_preflop_root(config); domain={}; typed={}; nodes=[0]
    def visit(s):
        nodes[0]+=1
        actor=s.current_player()
        if actor==TERMINAL:
            close(sum(s.returns()),0); return
        if actor==CHANCE: edges=[a for a,_ in s.chance_outcomes()]
        else:
            k=s.information_state_key(actor); sk=str(k); edges=s.legal_actions()
            assert sk not in typed or typed[sk]==k
            typed[sk]=k
            record=(actor,tuple(str(a) for a in edges))
            assert len(set(record[1]))==len(edges)
            assert domain.setdefault(sk,record)==record
            assert k[0]==p['version'] and k[1]==n and k[2]==actor
            assert k[-3:]==(c['kind'],c['source'],c['provenance'])
        for a in edges: visit(s.child(a))
    visit(root); assert nodes[0]<=p['max_nodes']
    def ev(s, strategy, deviation=None):
        actor=s.current_player()
        if actor==TERMINAL: return s.returns()
        if actor==CHANCE: edges=s.chance_outcomes()
        else:
            k=str(s.information_state_key(actor))
            edges=[(a,float(str(a)==deviation[k]) if deviation and k in deviation else strategy[k][str(a)]) for a in s.legal_actions()]
        total=[0.0]*n
        for a,prob in edges:
            for i,v in enumerate(ev(s.child(a),strategy,deviation)): total[i]+=prob*v
        return total
    for enabled in (False,True):
        q=deepcopy(request); q['payload']['include_deviation_certificate']=enabled; saved=deepcopy(q)
        baseline=dispatch_v4(q); mutant=dispatch_v4(q)
        assert q==saved and baseline==mutant
        assert set(baseline)==FIELDS and len(baseline)==15
        encoded=json.dumps(baseline,allow_nan=False,sort_keys=True); assert json.loads(encoded)==baseline; keys(baseline)
        assert baseline['version']==baseline['config_version']==4
        for field in ('algorithm','iterations','seed','max_nodes'): assert baseline[field]==p[field]
        assert baseline['operation']==request['operation'] and baseline['game_version']==p['version']
        assert baseline['max_depth']==2+n+p['max_raises']*(n-1)
        assert baseline['metadata']=={'converged':False,'convergence_claim':'none','deterministic':True,'deviation_certificate':'exhaustive-diagnostic-only' if enabled else 'not-requested'}
        assert baseline['provenance']=='full-tree deterministic vanilla CFR; no convergence guarantee'
        assert baseline['approximate'] is False
        strategy=baseline['strategy']; assert set(strategy)==set(domain)
        for k,pol in strategy.items():
            assert set(pol)==set(domain[k][1])
            assert all(isinstance(v,float) and math.isfinite(v) and 0<=v<=1 for v in pol.values()); close(sum(pol.values()),1)
        values=baseline['values']; assert len(values)==n and all(isinstance(v,float) and math.isfinite(v) for v in values); close(sum(values),0)
        for a,b in zip(values,ev(root,strategy)): close(a,b)
        cert=baseline['certificate']
        if enabled:
            assert set(cert)=={'values','best_response_values','incentives','total_incentive','provenance'}
            assert cert['provenance']=='exhaustive finite pure unilateral deviations; diagnostic only'
            assert cert['values']==values
            counts=[]
            for seat in range(n):
                owned=[(k,actions) for k,(owner,actions) in domain.items() if owner==seat]
                count=math.prod(len(actions) for _,actions in owned); counts.append(count); assert count<=p['max_pure_strategies']
                best=max([values[seat]]+[ev(root,strategy,dict(zip([k for k,_ in owned],choice)))[seat] for choice in product(*(actions for _,actions in owned))])
                close(cert['best_response_values'][seat],best); close(cert['incentives'][seat],max(0,best-values[seat]))
            close(cert['total_incentive'],sum(cert['incentives']))
        else: assert cert is None
        k=next(iter(mutant['strategy'])); a=next(iter(mutant['strategy'][k]))
        mutant['strategy'][k][a]=-999.0; mutant['strategy'][k]['injected-action']=1.0
        mutant['strategy']['injected-info']={'injected-action':1.0}
        mutant['metadata']['converged']=True; mutant['metadata']['injected']={'nested':[999]}
        mutant['metadata']['injected']['nested'].append(-999)
        mutant['values'][0]=999.0; mutant['values'].append(-999.0)
        if enabled:
            for field in ('values','best_response_values','incentives'):
                mutant['certificate'][field][0]=999.0; mutant['certificate'][field].append(-999.0)
            mutant['certificate']['total_incentive']=-999; mutant['certificate']['provenance']='mutated'; mutant['certificate']['injected']={}
        else: mutant['certificate']={'injected':[999]}
        fresh=dispatch_v4(q)
        assert mutant!=baseline and fresh==baseline and q==saved
        assert json.dumps(fresh,allow_nan=False,sort_keys=True)==encoded
        print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'players':n,'certificate':enabled,'nodes':nodes[0],'infosets':len(domain),'action_entries':sum(len(x) for x in strategy.values()),'values':values,'pure_strategy_counts':counts if enabled else None,'response_sha256':hashlib.sha256(encoded.encode()).hexdigest(),'checks':'PASS: exact envelope; strict JSON; deterministic; declared domain; normalized finite policies; finite zero-sum independent EV; truthful metadata; independent certificate oracle; full response mutation isolation'}),flush=True)
```

Exact successful output (certificate oracle applies to enabled cases; disabled cases assert null):

```jsonl
{"utc": "2026-09-16T10:28:44.727293+00:00", "players": 2, "certificate": false, "nodes": 6, "infosets": 2, "action_entries": 4, "values": [1.75, -1.75], "pure_strategy_counts": null, "response_sha256": "2318a4d6615b0c4bcb967e18e0506c5e522c7db5cf33b43971cf05f2b8a96908", "checks": "PASS: exact envelope; strict JSON; deterministic; declared domain; normalized finite policies; finite zero-sum independent EV; truthful metadata; independent certificate oracle; full response mutation isolation"}
{"utc": "2026-09-16T10:28:44.777585+00:00", "players": 2, "certificate": true, "nodes": 6, "infosets": 2, "action_entries": 4, "values": [1.75, -1.75], "pure_strategy_counts": [2, 2], "response_sha256": "1065e59e26a687881da33d52a647ed80a5f6257a8348aa30ea4aa181b22a1d1d", "checks": "PASS: exact envelope; strict JSON; deterministic; declared domain; normalized finite policies; finite zero-sum independent EV; truthful metadata; independent certificate oracle; full response mutation isolation"}
{"utc": "2026-09-16T10:28:44.942337+00:00", "players": 6, "certificate": false, "nodes": 13, "infosets": 5, "action_entries": 11, "values": [5.0, 0.5226449275362319, -2.522644927536232, -1.0, -1.0, -1.0], "pure_strategy_counts": null, "response_sha256": "ae2a0c0012c832f112050cceaec3e6caa5435e97d91253ec49d0a9ed082c7355", "checks": "PASS: exact envelope; strict JSON; deterministic; declared domain; normalized finite policies; finite zero-sum independent EV; truthful metadata; independent certificate oracle; full response mutation isolation"}
{"utc": "2026-09-16T10:28:45.579223+00:00", "players": 6, "certificate": true, "nodes": 13, "infosets": 5, "action_entries": 11, "values": [5.0, 0.5226449275362319, -2.522644927536232, -1.0, -1.0, -1.0], "pure_strategy_counts": [1, 6, 8, 1, 1, 1], "response_sha256": "975956a1a2a8dada31912fc98db5a33547b3956e8455a41e5d6c83b74bad6c83", "checks": "PASS: exact envelope; strict JSON; deterministic; declared domain; normalized finite policies; finite zero-sum independent EV; truthful metadata; independent certificate oracle; full response mutation isolation"}
{"utc": "2026-09-16T10:28:45.949103+00:00", "players": 9, "certificate": false, "nodes": 13, "infosets": 5, "action_entries": 11, "values": [8.0, 0.5226449275362319, -2.522644927536232, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0], "pure_strategy_counts": null, "response_sha256": "e4212d8133addffb17c189c773eaf1f890b9283ff90391582d7acb813c8972bf", "checks": "PASS: exact envelope; strict JSON; deterministic; declared domain; normalized finite policies; finite zero-sum independent EV; truthful metadata; independent certificate oracle; full response mutation isolation"}
{"utc": "2026-09-16T10:28:46.793225+00:00", "players": 9, "certificate": true, "nodes": 13, "infosets": 5, "action_entries": 11, "values": [8.0, 0.5226449275362319, -2.522644927536232, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0], "pure_strategy_counts": [1, 6, 8, 1, 1, 1, 1, 1, 1], "response_sha256": "2e431c13b0950552a22bd45f10c4447ca5859835e9a6f298e6aacdaaa6c2c1b8", "checks": "PASS: exact envelope; strict JSON; deterministic; declared domain; normalized finite policies; finite zero-sum independent EV; truthful metadata; independent certificate oracle; full response mutation isolation"}
```

## Completion

Final literal manifest verification: 20/20 PASS, no drift. API digest: PASS. Existing tests: 87 PASS. Independent cases: 6/6 PASS. No unresolved blockers. The flat heartbeat includes this report's SHA-256; the report does not self-hash.
