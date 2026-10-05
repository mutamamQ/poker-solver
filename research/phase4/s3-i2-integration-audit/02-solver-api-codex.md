# C3I2-CODEX-I2 solver/API integration audit

status=PASS
blocker_count=0
auditor=C3I2-CODEX-I2
role=fresh alternate-provider non-author solver/API auditor
workspace=/home/genomix-node/poker-solver
initial_manifest_utc=2026-09-16T10:22:26.121106+00:00
final_manifest_utc=2026-09-16T10:24:29.126846+00:00

PASS: all requested checks completed; no candidate defect identified. Candidate source, tests, examples, and other manifest entries were not edited. No git commands or commits were used. Only this report and the named heartbeat were written intentionally. Probes ran entirely through stdin/in-memory; no repository or /tmp probe files were created, so probe cleanup required no deletions. Test subprocesses inherited PYTHONDONTWRITEBYTECODE=1; pytest cache was disabled. uv used --no-sync and UV_NO_CACHE=1.

The independently rerun gates were 52 passed in 1.68s and 56 passed in 1.33s, both exit 0. The parent's 817-test regression was not rerun or claimed as independent evidence.

## Frozen candidate verification

Before executing audit tests/probes, parsed exactly 20 literal lowercase 64-hex SHA-256 rows, required 20 distinct paths, read each file as bytes, and compared its digest. Repeated after tests/probes. Both exit 0. The explicit required core and API digest assertions also passed.

Initial exact command:
```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import hashlib,re,datetime
from pathlib import Path
p=Path('research/phase4/s3-i2-integration-audit/CANDIDATE_MANIFEST.md')
rows=re.findall(r'^([0-9a-f]{64})  (.+)$',p.read_text(),re.M)
assert len(rows)==20 and len({p for _,p in rows})==20
for expected,path in rows:
 actual=hashlib.sha256(Path(path).read_bytes()).hexdigest()
 assert actual==expected,(path,expected,actual)
 print(actual+'  '+path+'  PASS')
assert dict((p,h) for h,p in rows)['src/poker_solver/nplayer_preflop.py']=='5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae'
assert dict((p,h) for h,p in rows)['src/poker_solver/api_v4.py']=='70d378d6a52ae544615a5aa4dda6bd9e987f8161f08119914a0762ed0727a1a3'
print('INITIAL_MANIFEST_PASS rows=20 UTC='+datetime.datetime.now(datetime.timezone.utc).isoformat())
PY
```

Initial output was the 20 PASS rows below followed by:
```text
INITIAL_MANIFEST_PASS rows=20 UTC=2026-09-16T10:22:26.121106+00:00
```

Final exact command:
```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import hashlib,re,datetime
from pathlib import Path
p=Path('research/phase4/s3-i2-integration-audit/CANDIDATE_MANIFEST.md')
rows=re.findall(r'^([0-9a-f]{64})  (.+)$',p.read_text(),re.M)
assert len(rows)==20 and len({p for _,p in rows})==20
for expected,path in rows:
 actual=hashlib.sha256(Path(path).read_bytes()).hexdigest()
 assert actual==expected,(path,expected,actual)
 print(actual+'  '+path+'  PASS')
assert dict((p,h) for h,p in rows)['src/poker_solver/nplayer_preflop.py']=='5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae'
assert dict((p,h) for h,p in rows)['src/poker_solver/api_v4.py']=='70d378d6a52ae544615a5aa4dda6bd9e987f8161f08119914a0762ed0727a1a3'
print('FINAL_MANIFEST_PASS rows=20 UTC='+datetime.datetime.now(datetime.timezone.utc).isoformat())
PY
```

Final exact output (the same 20 digest/path checks passed initially):
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
FINAL_MANIFEST_PASS rows=20 UTC=2026-09-16T10:24:29.126846+00:00
```

## Test commands and results

Executed from the workspace, with independent test groups launched concurrently:
```bash
PYTHONDONTWRITEBYTECODE=1 UV_NO_CACHE=1 uv run --no-sync python -B -m pytest -p no:cacheprovider tests/test_nplayer_preflop_solve.py -q
```
Result: exit 0; 52 passed in 1.68s.

```bash
PYTHONDONTWRITEBYTECODE=1 UV_NO_CACHE=1 uv run --no-sync python -B -m pytest -p no:cacheprovider tests/test_api_v4_nplayer_preflop.py tests/test_phase4_s3_examples.py tests/test_phase4_s3_exports.py -q
```
Result: exit 0; 56 passed in 1.33s.

## Independent public-dispatch probe

Only the manifest-pinned 2/6/9-player JSON requests supplied game inputs. Each original request was dispatched twice, then a deep copy enabled the certificate and was dispatched twice. Exact response equality, unchanged original request, unchanged policy/value output with certificate enabled, finite normalized nonnegative policies, finite zero-sum value vectors, strict finite JSON serialization, max_nodes equal to the request, and max_depth equal to 2 + n + max_raises * (n - 1) all passed. Disabled certificates were None and enabled certificates had exhaustive diagnostic provenance; convergence claims remained absent.

The sole poker-solver import in the independent probe was public dispatch_v4. The oracle parsed serialized information-set histories/actions, built a history-indexed tree, maintained its own contribution ledger from the committed forced posts and action amounts, and settled each terminal contribution tier using the committed unique showdown ranks. It enumerated every pure action assignment at every information set for each seat (including unreachable choices), evaluated each unilateral deviation against the reported fixed opponents, and compared baseline values, best-response values, incentives, and total incentive to the certificate with absolute/relative tolerance 1e-12. It did not call production tree constructors, expected-value functions, settlement helpers, or certificate helpers. Tree topology/action support came from the public strategy response; this is an independent settlement/expectation/deviation calculation for these bounded fixtures, not a separate general legality implementation or convergence proof.

The six-player per-seat pure-strategy counts were [1, 6, 8, 1, 1, 1], independently computed as the product of action counts per information set; the largest count is 8. A request with cap 8 returned exactly the same response as cap 100000. Cap 7 raised ValueError with "player pure-strategy bound exceeded", with no response returned.

Probe correction: the first run exited 1 solely because the audit script expected the invented substring "pure-strategy cap exceeded". The API had already correctly raised ValueError("player pure-strategy bound exceeded") at cap 7. Corrected only the in-memory assertion to the actual message and reran the complete probe successfully; no candidate change. The first run passed the 2/6-player numeric oracles before that assertion and had not yet reached 9 players.

Initial probe exact command is the final command below with this single line replacement:
```python
# initial line:
assert "pure-strategy cap exceeded" in str(exc), str(exc)
# corrected line:
assert str(exc) == "player pure-strategy bound exceeded", str(exc)
```

Initial exact output:
```text
{"players": 2, "status": "PASS", "max_nodes": 100, "max_depth": 5, "information_sets": 2, "terminal_histories": 3, "pure_strategy_counts": [2, 2], "values": [1.75, -1.75], "best_response_values": [3.0, -1.75], "total_incentive": 1.25}
{"players": 6, "status": "PASS", "max_nodes": 100, "max_depth": 13, "information_sets": 5, "terminal_histories": 7, "pure_strategy_counts": [1, 6, 8, 1, 1, 1], "values": [5.0, 0.5226449275362319, -2.522644927536232, -1.0, -1.0, -1.0], "best_response_values": [5.0, 1.75, -2.3369565217391304, -1.0, -1.0, -1.0], "total_incentive": 1.4130434782608696}
Traceback (most recent call last):
  File "<stdin>", line 147, in <module>
  File "/home/genomix-node/poker-solver/src/poker_solver/api_v4.py", line 542, in dispatch_v4
    return _dispatch_nplayer_preflop(request["payload"])
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/genomix-node/poker-solver/src/poker_solver/api_v4.py", line 452, in _dispatch_nplayer_preflop
    result = solve_nplayer_preflop(
             ^^^^^^^^^^^^^^^^^^^^^^
  File "/home/genomix-node/poker-solver/src/poker_solver/nplayer_preflop.py", line 1108, in solve_nplayer_preflop
    unilateral_deviation_certificate(
  File "/home/genomix-node/poker-solver/src/poker_solver/nplayer.py", line 336, in unilateral_deviation_certificate
    raise ValueError("player pure-strategy bound exceeded")
ValueError: player pure-strategy bound exceeded

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "<stdin>", line 149, in <module>
AssertionError: player pure-strategy bound exceeded
```

Final exact probe command:
```bash
PYTHONDONTWRITEBYTECODE=1 UV_NO_CACHE=1 uv run --no-sync python -B - <<'PY'
import copy, datetime, itertools, json, math, re
from pathlib import Path
from poker_solver.api_v4 import dispatch_v4

def close(a, b):
    assert math.isfinite(a) and math.isfinite(b)
    assert math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12), (a, b)

def action(s):
    m = re.fullmatch(r"Action\(kind='([A-Z]+)', amount=(\d+)\)", s)
    assert m, s
    return m.group(1), int(m.group(2))

def independent_oracle(request, response):
    p = request["payload"]
    n = p["num_players"]
    assert len(p["continuation"]["entries"]) == 1
    assert all(len(r) == 1 and r[0]["weight"] == 1 for r in p["ranges"])
    assert p["sizing_rules"] == [] and p["continuation"]["kind"] == "showdown-ranks"
    ranks = p["continuation"]["entries"][0]["ranks"]
    states = {}
    by_seat = [[] for _ in range(n)]
    for key, policy in response["strategy"].items():
        m = re.match(r"\('nplayer-preflop-v1', (\d+), (\d+),", key)
        assert m and int(m[1]) == n
        actor = int(m[2])
        history = tuple((int(a), k, int(v)) for a, k, v in re.findall(
            r"NPlayerPreflopPublicAction\(actor=(\d+), action=Action\(kind='([A-Z]+)', amount=(\d+)\)\)", key))
        assert history not in states
        states[history] = actor, {action(a): prob for a, prob in policy.items()}
        by_seat[actor].append(history)
    assert () in states

    # Independent chip ledger: antes are dead money; action amounts are street totals.
    # Terminal payoff is contribution-tier settlement using supplied ranks.
    def terminal(history):
        contributions = [0] * n
        street = [0] * n
        folded = set()
        for post in p["forced_posts"]:
            contributions[post["seat"]] += post["amount"]
            if post["kind"] != "ante":
                street[post["seat"]] += post["amount"]
        for actor, kind, amount in history:
            if kind == "FOLD":
                folded.add(actor)
            elif kind in ("CALL", "RAISE"):
                assert amount >= street[actor]
                contributions[actor] += amount - street[actor]
                street[actor] = amount
            else:
                assert kind == "CHECK" and amount == 0
        assert all(0 <= c <= s for c, s in zip(contributions, p["starting_stacks"]))
        payouts = [0.0] * n
        previous = 0
        for level in sorted(set(contributions) - {0}):
            contributors = [s for s in range(n) if contributions[s] >= level]
            pot = (level - previous) * len(contributors)
            eligible = [s for s in contributors if s not in folded]
            assert eligible
            best = max(ranks[s] for s in eligible)
            winners = [s for s in eligible if ranks[s] == best]
            # These committed examples have unique ranks, hence no odd-chip ambiguity.
            assert len(winners) == 1
            payouts[winners[0]] += pot
            previous = level
        values = [a - b for a, b in zip(payouts, contributions)]
        close(sum(values), 0)
        return values

    leaves = set()
    def evaluate(history=(), override=None):
        if history not in states:
            leaves.add(history)
            return terminal(history)
        actor, policy = states[history]
        values = [0.0] * n
        for (kind, amount), prob in policy.items():
            if override is not None and history in override:
                prob = float(override[history] == (kind, amount))
            child = evaluate(history + ((actor, kind, amount),), override)
            for s in range(n):
                values[s] += prob * child[s]
        return values

    baseline = evaluate()
    counts, best_values = [], []
    for seat, histories in enumerate(by_seat):
        choices = [list(states[h][1]) for h in histories]
        counts.append(math.prod(map(len, choices)))
        best_values.append(max(evaluate(override=dict(zip(histories, pure)))[seat]
                               for pure in itertools.product(*choices)))
    for a, b in zip(baseline, response["values"]):
        close(a, b)
    c = response["certificate"]
    for field, expected in (
        ("values", baseline),
        ("best_response_values", best_values),
        ("incentives", [max(0.0, b-v) for b,v in zip(best_values, baseline)]),
    ):
        assert len(c[field]) == n
        for a, b in zip(c[field], expected):
            close(a, b)
    close(c["total_incentive"], sum(c["incentives"]))
    return counts, len(states), len(leaves), baseline, best_values

for n in (2, 6, 9):
    request = json.loads(Path(f"examples/phase4/nplayer_{n}p_preflop.json").read_text())
    original = copy.deepcopy(request)
    first = dispatch_v4(request)
    assert first == dispatch_v4(copy.deepcopy(request))
    assert request == original
    assert first["certificate"] is None
    assert first["metadata"]["deviation_certificate"] == "not-requested"
    enabled = copy.deepcopy(request)
    enabled["payload"]["include_deviation_certificate"] = True
    response = dispatch_v4(enabled)
    assert response == dispatch_v4(copy.deepcopy(enabled))
    assert response["strategy"] == first["strategy"] and response["values"] == first["values"]
    for r in (first, response):
        assert r["max_nodes"] == request["payload"]["max_nodes"]
        assert r["max_depth"] == 2 + n + request["payload"]["max_raises"] * (n - 1)
        assert len(r["values"]) == n and all(math.isfinite(v) for v in r["values"])
        close(math.fsum(r["values"]), 0)
        assert r["strategy"]
        for policy in r["strategy"].values():
            assert policy and all(math.isfinite(v) and 0 <= v <= 1 for v in policy.values())
            close(math.fsum(policy.values()), 1)
        assert r["metadata"]["converged"] is False
        assert r["metadata"]["convergence_claim"] == "none"
        json.dumps(r, allow_nan=False)
    assert response["certificate"]["provenance"] == "exhaustive finite pure unilateral deviations; diagnostic only"
    assert response["metadata"]["deviation_certificate"] == "exhaustive-diagnostic-only"
    counts, states, leaves, values, best = independent_oracle(enabled, response)
    print(json.dumps(dict(players=n, status="PASS", max_nodes=response["max_nodes"],
        max_depth=response["max_depth"], information_sets=states, terminal_histories=leaves,
        pure_strategy_counts=counts, values=values, best_response_values=best,
        total_incentive=response["certificate"]["total_incentive"])))
    if n == 6:
        cap = max(counts)
        assert counts == [1, 6, 8, 1, 1, 1] and cap == 8
        boundary = copy.deepcopy(enabled)
        boundary["payload"]["max_pure_strategies"] = cap
        assert dispatch_v4(boundary) == response
        boundary["payload"]["max_pure_strategies"] = cap - 1
        try:
            dispatch_v4(boundary)
        except ValueError as exc:
            assert str(exc) == "player pure-strategy bound exceeded", str(exc)
            print(f"SIX_PLAYER_CAP_PASS cap={cap} cap_minus_one={cap-1} exception={type(exc).__name__}: {exc}")
        else:
            raise AssertionError("cap-1 returned a result instead of failing closed")
print("PUBLIC_DISPATCH_INDEPENDENT_ORACLE_PASS UTC=" + datetime.datetime.now(datetime.timezone.utc).isoformat())
PY
```

Final exact output:
```text
{"players": 2, "status": "PASS", "max_nodes": 100, "max_depth": 5, "information_sets": 2, "terminal_histories": 3, "pure_strategy_counts": [2, 2], "values": [1.75, -1.75], "best_response_values": [3.0, -1.75], "total_incentive": 1.25}
{"players": 6, "status": "PASS", "max_nodes": 100, "max_depth": 13, "information_sets": 5, "terminal_histories": 7, "pure_strategy_counts": [1, 6, 8, 1, 1, 1], "values": [5.0, 0.5226449275362319, -2.522644927536232, -1.0, -1.0, -1.0], "best_response_values": [5.0, 1.75, -2.3369565217391304, -1.0, -1.0, -1.0], "total_incentive": 1.4130434782608696}
SIX_PLAYER_CAP_PASS cap=8 cap_minus_one=7 exception=ValueError: player pure-strategy bound exceeded
{"players": 9, "status": "PASS", "max_nodes": 100, "max_depth": 19, "information_sets": 5, "terminal_histories": 7, "pure_strategy_counts": [1, 6, 8, 1, 1, 1, 1, 1, 1], "values": [8.0, 0.5226449275362319, -2.522644927536232, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0], "best_response_values": [8.0, 1.75, -2.3369565217391304, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0], "total_incentive": 1.4130434782608696}
PUBLIC_DISPATCH_INDEPENDENT_ORACLE_PASS UTC=2026-09-16T10:24:12.051590+00:00
```

## Disposition

PASS; blockers: none. Requested solver/API tests and independent bounded dispatch checks passed, and all 20 frozen candidate SHA-256 rows matched both before and after execution. Required core hash: 5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae. Required API hash: 70d378d6a52ae544615a5aa4dda6bd9e987f8161f08119914a0762ed0727a1a3.
