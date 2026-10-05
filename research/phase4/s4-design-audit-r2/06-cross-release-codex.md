# C4R2A6-CODEX — independent cross-release DESIGN audit

Verdict: **ACCEPT** (design checkpoint only). No blocking design finding was reproduced. Missing S4 production and tests is expected; this verdict does not certify an implemented reduced solver.

Auditor: C4R2A6-CODEX, replacement non-author audit. All commands ran with repository cwd /home/genomix-node/poker-solver. No R2A6/R2A6R regression receipt is used as evidence. Only the assigned report and heartbeat are intentionally written. Existing PROGRESS.md and STATE.txt modifications and untracked design/audit directories were present at entry and were left untouched. No source, test, script, dependency, candidate, or Git-history edits were made.

## Identity and release boundary — PASS

Independently executed:
```sh
git rev-parse HEAD
git rev-parse refs/tags/phase3-398-green 'refs/tags/phase3-398-green^{}'
sha256sum ARCHITECTURE_PHASE4_S4.md research/phase4/s4-design-audit-r2/CANDIDATE_MANIFEST.md PHASE4_MISSION.md research/phase4/s4-design/02-engine-integration-codex.md
git diff HEAD --name-only -- src tests scripts pyproject.toml
git ls-files --others --exclude-standard -- src tests scripts pyproject.toml
git diff --check
```

Results (exit 0): HEAD 149780bf37e3e3a824e03e6d2c1df3cd99b12cd6; annotated tag object feba8222a0b614b0c64eca59402403ce733195ea; peeled commit 5809ecca28ae6d0588ea07709c90beac3072c167. The object and commit are intentionally different identities. Both protected-path listings and diff-check were empty.

SHA-256 results:
- Architecture: 37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2.
- R2 manifest: f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed.
- Mission: 5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61.
- Authoritative engine design: 79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d.

In addition to git diff, the byte-for-byte probe below compared every tracked protected file against git show HEAD:path. All 99 matched. Aggregate fingerprint: f7bba6b85b24ad312cc63d82a05779dbfbd88ed08572407ddcc5da05ffb3e6a9. This checks index-staged changes too, not merely worktree-versus-index changes. The current regression target is 817; mission's 398 denotes the historical release baseline.

## Architecture completeness and mathematical scope — PASS

Architecture §§3–7 provide an implementable path from validated canonical configuration to signatures, rectangular bucket pairs, rational world masses, prefix beliefs, immutable physical history nodes, ReducedState, solve, bounded lift, and scoped diagnostics. §§8–12 bind that path to literal fixtures, a strict wire contract, four sequential RED/GREEN batches, independent audits, and completion gates.

Full labelled compatibility/runout/showdown rows and columns provide a conservative equivalence certificate. Equal rows/columns imply a positive pair is a Cartesian rectangle and each configured public runout has constant legality and showdown ordering within it. Product range weights then factorize within the pair: own-card distinctions reveal no further opponent distribution. Card-independent public betting plus retained own bucket and full public/action history allow a perfect-recall quotient. Exact-card randomization can be represented by a realization-plan mixture against a bucket policy; it does not create extra best-response value. This supports zero model error for the rational configured game, not bitwise equality of independently trained float policies.

The posterior formula correctly mixes per-world conditional laws rather than pooling sequence counts. The generalized arithmetic example independently gives chance mass 2/3 and posterior (1/2,1/2). Production signatures intentionally separate worlds with unequal labelled kernels; that arithmetic unit case is not authority to merge them.

Settlement is feasible from source integer awards, contributions, and half the dead pot, including P1's odd tie remainder. Exact conservation and independently checked complementary utility are stronger than averaging rounded equity. The separate rational certificate and float tolerance prevent the zero-error theorem from being mistaken for a float-precision or finite-training guarantee.

## Actual-source feasibility — PASS

Read model.py, multistreet.py, allstreet.py, bounded_tree.py, cfr.py, mccfr.py, best_response.py, api.py, api_v4.py, equity.py and package exports, with relevant existing multistreet/API/bounds/oracle test contracts.

Concrete source anchors:
- model.py exposes six structural GameState methods and hashable InfoKey; Action accepts a new string kind, so ABSTRACT_DEAL requires no shared protocol rewrite.
- multistreet.py:158 enumerates product-weight compatible deals and prefix-conditioned RUNOUTs; :197 constructs public transitions; :439 removes DEAL from exact information history; :458 settles integer awards. The proposed compiler can construct detached member snapshots directly and project these fields without retaining member subtrees.
- bounded_tree.py counts history occurrences, including root/chance/terminals, and fails before exceeding the cap. Its infoset check compares action sets, whereas cfr.py:34 checks ordered tuples. Therefore the architecture correctly requires additional order/recall/noninterference checks instead of attributing those guarantees to preflight.
- CFRSolver construction already traverses the entire supplied root. Preflight and compilation must precede it. A precompiled ReducedState with constant-time child lookup supports existing CFR/MCCFR/completion/BR consumers without rewriting them.
- api.py:312 fills missing policies uniformly. That is useful for reduced solver completion but would conceal broken exact lift coverage, which the new contract explicitly rejects.
- best_response.py:58 uses counterfactual reach and an infoset dependency graph, while :174 supplies an exhaustive tiny-game oracle. Retaining full own/action/public history addresses absent-mindedness and cycles.
- allstreet's translation sets river_betting=True and performs an exact preflight in the old solve path. The new facade must translate without first invoking that old exact solve, as specified.

The fixture probes below reproduce source counts and the small reference solve. They do not implement a surrogate reduced solver or claim execution of future S4 acceptance tests.

## Dependency graph and cycle risk — PASS

Feasible acyclic layering is:
```text
model/cards/evaluator/equity
  -> multistreet + bounded_tree -> abstraction
model -> cfr/mccfr -> best_response
multistreet/cfr/mccfr/best_response -> api.complete_strategy
api + multistreet -> existing allstreet
abstraction + api/cfr/mccfr/best_response + allstreet translation
  -> abstraction_solve -> api_v4 dispatcher/package exports
```
Arrows here mean lower layer is consumed by the layer to its right. Existing allstreet imports api.complete_strategy; api does not import allstreet. api_v4 already imports allstreet locally in dispatch. No new reverse import from api into abstraction_solve is necessary. The authenticated engine design §10 explicitly identifies the potential api -> facade -> allstreet -> api cycle. The architecture's separate state and solve files, additive dispatcher integration, and I1/I2-before-I3-before-I4 ordering permit avoiding it without changing accepted modules' responsibilities. Package exports should be integrated only after lower modules load. This is a design feasibility judgment, not a claim that future imports were executed.

The implementation dependency chain is policy/canonicalization -> compiler/state -> solver/lift/certificates -> API/exports/examples. Each batch names production ownership, behavioral RED tests, and a fresh audit gate; later tests cannot be silently passed by early placeholder stubs.

## Bounded scope, claims, and S1–S3 compatibility — PASS

Physical reduction is mandatory now: one actual history tree per nonempty bucket pair, no hidden exact subtrees or DAG-count substitution. Worlds, signature slots, belief entries, Fraction size, physical nodes and depth have separate caps. The recursion ceiling of 128 is compatible with existing recursive consumers. Node-count reduction does not promise a fixed speedup; preprocessing and repeated best-response work remain real costs.

The large fixture is deliberately shallow and strongly equivalent. It is legitimate finite all-street acceptance, not evidence of unrestricted-deck/full-stack performance. Failure without compression is allowed and explicit. Generic GameState abstraction, S2/S3 multiway integration, general suit automorphisms, lossy buckets and later S5 work are excluded. These boundaries satisfy the mission's S4 acceptance without pretending all remaining features are delivered.

S1 exact operation, optional bounds, natural settlement, result type and approximate=False convention are preserved. New finite-iteration approximate=True has separate lossless-abstraction semantics. S2 postflop and S3 preflop operation names, parsers, exports, ledgers and N-player diagnostics need no modification; no two-player NashConv reinterpretation is proposed for them. Existing compatibility tests are included in the independently run full suite. No dependency is added to the dependency-free runtime pyproject.

## R2 repairs — PASS

1. Architecture §9.1 now enumerates required response keys and nested action, rational, public/exact/abstract key, policy, membership, pair, and metadata shapes. It defines deterministic sorting, null diagnostic relationships, detached serialization, digest encoding and finite-number rules. This closes the earlier unspecified response surface.
2. §9 requires both base bounds only on the new operation, equality with abstraction bounds, and unchanged optional defaults for the old operation. I4 explicitly requires omitted/partially omitted/equal/unequal cases.
3. New range parsing bypasses inherited _float for integers. An independent source probe shows WeightedCombo preserves 9007199254740993 as int, while legacy _float rounds it to 9007199254740992. Fraction(integer) retains 9007199254740993, so the repair is necessary and feasible without altering prior operation semantics. I4 requires JSON/direct-Python parity.

Implementation attention, nonblocking: §6 mentions lossy_merges=0 while the exhaustive wire metadata key set in §9.1 omits that key. Use §9.1 as the exact wire schema and retain the zero-loss invariant; do not add an undeclared wire field. Similarly, compiler recall checks and import direction must be exercised during implementation, not inferred from this design acceptance. Neither observation prevents the specified quotient or its release-safe integration.

## Acceptance metrics — PASS

The small exact count 321 and quotient target 161 compare the same configured game. Both independently trained reference and lifted profiles must meet exact-tree NashConv <=0.02 after exactly 1,000 vanilla iterations. From L(x)<=v*<=U(x), subtracting endpoints yields
|v(a)-v(r)| <= max(e1(a)+e0(r),e0(a)+e1(r)) <= C(a)+C(r).
Thus the 0.04 loose gate is derived, not guessed. Rational replay/BR certification and 1e-10 float comparison serve different purposes. Small exact-lift evaluation is compulsory; large exact diagnostics are optional with separate caps and cannot silently disappear if requested.

The large gate requires the complete reduced path including training, completion, reduced BR, frozen result and serialization under 10,000 nodes/depth32. It pins 161 nodes, 68 terminals, 29 chance nodes, 64 decisions, depth12; exact source preflight must reject the same game at 10,000. Membership, blocker companions, cap boundary 160/161, repeat determinism, same-seed MCCFR, bit-identical twin lift, and solve-time no-member-construction instrumentation guard against superficial success.

## Independent commands and receipts

### Protected-file byte comparison
```sh
PYTHONDONTWRITEBYTECODE=1 python - <<'PY'
import hashlib, pathlib, subprocess
paths=subprocess.check_output(['git','ls-files','-z','--','src','tests','scripts','pyproject.toml']).decode().split('\0')
paths=[p for p in paths if p]
for p in paths:
    assert pathlib.Path(p).read_bytes()==subprocess.check_output(['git','show','HEAD:'+p]),p
print('tracked protected files equal HEAD:',len(paths))
print('protected aggregate SHA-256:',hashlib.sha256(b''.join(p.encode()+b'\0'+hashlib.sha256(pathlib.Path(p).read_bytes()).digest() for p in paths)).hexdigest())
PY
```
Output: tracked protected files equal HEAD: 99; protected aggregate SHA-256 as above. Exit 0.

### Compileall — PASS
The write restriction forbids creating bytecode files. This invokes actual compileall with force=True and intercepts only its atomic bytecode write; parsing/compilation failures still fail the assertion.
```sh
PYTHONDONTWRITEBYTECODE=1 UV_NO_CACHE=1 uv run --no-sync python - <<'PY'
import compileall
import importlib._bootstrap_external as bootstrap
# Exercise compileall compilation while suppressing bytecode filesystem writes.
writes=[]
bootstrap._write_atomic=lambda path,data,mode=0o666: writes.append(path)
results={p:compileall.compile_dir(p,quiet=1,force=True) for p in ('src','tests','scripts')}
print('compileall:',results,'bytecode writes suppressed:',len(writes))
assert all(results.values())
PY
```
Exact output:
```text
compileall: {'src': True, 'tests': True, 'scripts': True} bytecode writes suppressed: 97
```
Exit 0.

### Independent source fixture probe — PASS
```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
from itertools import combinations
from poker_solver.cards import parse_cards
from poker_solver.equity import WeightedCombo
from poker_solver.multistreet import MultiStreetConfig, create_root
from poker_solver.bounded_tree import validate_bounded_tree
from poker_solver.evaluator import evaluate_seven
from poker_solver.cfr import CFRSolver
from poker_solver.api import complete_strategy
from poker_solver.best_response import nash_conv
cards=lambda s: parse_cards(s.split())
board=cards('Ah Kh Qh'); runs=tuple(cards(s) for s in ('Jh 9h','Jh 8h'))
a=tuple(WeightedCombo(c) for c in combinations(cards('2c 3c 4c 5c 6c 7c 2d 3d 4d 5d 6d 7d'),2))
b=tuple(WeightedCombo(c) for c in combinations(cards('2s 3s 4s 5s 6s 7s 2h 3h 4h 5h 6h Th'),2))
def cfg(x,y): return MultiStreetConfig('multistreet-v1','flop',board,2,1,x,y,runs,'no-limit',(1,),True)
# Memoized showdown comparisons; these literal pools have no blockers.
ranks={(c.cards,r):evaluate_seven(c.cards+board+r) for c in a+b for r in runs}
sizes=[]
for own,opp in ((a,b),(b,a)):
    groups={}
    for c in own:
        sig=tuple(tuple((ranks[c.cards,r]>ranks[d.cards,r])-(ranks[c.cards,r]<ranks[d.cards,r]) for r in runs) for d in opp)
        groups.setdefault(sig,[]).append(c)
    sizes.append(sorted(map(len,groups.values())))
print('large hands/worlds/buckets:',len(a),len(b),len(a)*len(b),sizes)
s=validate_bounded_tree(create_root(cfg(a[:1],b[:1])),max_nodes=10000,max_depth=32)
print('single-world:',s)
print('derived exact/reduced nodes:',1+4356*(s.node_count-1),1+2*(s.node_count-1))
try: validate_bounded_tree(create_root(cfg(a,b)),max_nodes=10000,max_depth=32)
except ValueError as e: print('large exact cap:',str(e))
else: raise AssertionError('expected cap rejection')
small=create_root(cfg(tuple(WeightedCombo(cards(s)) for s in ('2c 3c','2d 3d')),tuple(WeightedCombo(cards(s)) for s in ('2s 3s','Th 4s'))))
print('small:',validate_bounded_tree(small,max_nodes=10000,max_depth=32))
solver=CFRSolver(small); solver.train(1000)
profile=complete_strategy(small,solver.average_strategy())
print('small exact 1000:',nash_conv(small,profile))
PY
```
Exact combined output:
```text
large hands/worlds/buckets: 66 66 4356 [[66], [11, 55]]
single-world: BoundedTreeStats(node_count=81, max_depth_reached=12, terminal_count=34, chance_count=15, decision_count=32)
derived exact/reduced nodes: 348481 161
large exact cap: max_nodes 10000 exceeded
small: BoundedTreeStats(node_count=321, max_depth_reached=12, terminal_count=136, chance_count=57, decision_count=128)
small exact 1000: NashConvResult(values=(-0.9993335546875001, 0.9993335546875001), best_response_values=(-0.9993333333333333, 1.0000625), incentives=(2.2135416677393494e-07, 0.0007289453125000067), nash_conv=0.0007291666666667806)
```
Exit 0. Large exact full count and reduced count are derived; only single-world/small exact traversals and the capped large traversal were executed.

### R2 numeric and posterior probe — PASS
```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
from fractions import Fraction
from poker_solver.equity import WeightedCombo
from poker_solver.api_v4 import _float
n=2**53+1
c=WeightedCombo((0,1),n)
assert isinstance(c.weight,int) and c.weight==n
print('WeightedCombo preserved integer:',c.weight)
print('legacy _float:',int(_float(n,'weight')))
print('new specified Fraction:',Fraction(c.weight))
q=(Fraction(1,3),Fraction(2,3)); p=(Fraction(1),Fraction(1,2))
mass=sum(a*b for a,b in zip(q,p))
print('generalized chance/posterior:',mass,tuple(a*b/mass for a,b in zip(q,p)))
PY
```
Exact output:
```text
WeightedCombo preserved integer: 9007199254740993
legacy _float: 9007199254740992
new specified Fraction: 9007199254740993
generalized chance/posterior: 2/3 (Fraction(1, 2), Fraction(1, 2))
```
Exit 0.

### Full independent regression — PASS
Executed the required command with bytecode/cache output disabled to respect exclusive file ownership. No test selection, exclusions, skips, xfails, or prior-agent receipts were substituted:
```sh
export PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider'
UV_NO_CACHE=1 uv run --no-sync pytest -q
```
Exact concatenated stdout/stderr from this audit's process:
```text
........................................................................ [  8%]
........................................................................ [ 17%]
........................................................................ [ 26%]
........................................................................ [ 35%]
........................................................................ [ 44%]
........................................................................ [ 52%]
........................................................................ [ 61%]
........................................................................ [ 70%]
........................................................................ [ 79%]
........................................................................ [ 88%]
........................................................................ [ 96%]
.........................                                                [100%]
817 passed in 246.50s (0:04:06)
```
Exit 0.

## Final disposition

PASS: identities/release immutability; architecture completeness; actual-source feasibility; dependency/cycle feasibility; bounded scope and claim discipline; S1–S3 compatibility; R2 repair coverage; acceptance metrics; compileall; diff-check; full independent regression.

Final pre-heartbeat checks reassert the four immutable hashes, required HEAD, annotated object and peeled commit, all 99 protected file contents against HEAD, absence of untracked protected files, and git diff --check. No implementation acceptance is inferred from this design verdict. No blocking finding, blocked=false. **Final verdict: ACCEPT.**

The heartbeat is written only after this report is final. Its live UTC timestamp is obtained from the system clock, and report_sha256 is the SHA-256 of these final bytes. The finalizer rereads both files and asserts equality after the heartbeat write; it makes no subsequent filesystem writes.

