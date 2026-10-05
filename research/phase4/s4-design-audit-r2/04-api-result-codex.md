# C4R2A4-CODEX — repaired API/result design audit

Final verdict: **REJECT**. Four MEDIUM design findings remain: incomplete digest preimage definition, undefined bucket mass semantics, an unresolved integer-domain/source-carrier boundary, and unspecified ordering of requested exact-diagnostic preflight relative to training. The original response-shape, mandatory-bound, and ordinary >2**53 ingress defects are substantially repaired. Missing S4 implementation/tests is expected and is not a finding.

Auditor: C4R2A4-CODEX, fresh alternate-provider non-author replacement. No earlier PASS is adopted. No subagents used. Live clock receipt: **2026-09-16 12:50:38 UTC**. This report evaluates the design, not an implemented S4 solver, full regression, or independent proof of the quotient theorem.

## 1. Authentication and scope

Working directory: `/home/genomix-node/poker-solver`. All report-relative paths below are relative to that directory. Commands executed:

```sh
git rev-parse HEAD
git rev-parse refs/tags/phase3-398-green
git rev-parse 'refs/tags/phase3-398-green^{}'
git cat-file -t feba8222a0b614b0c64eca59402403ce733195ea
sha256sum ARCHITECTURE_PHASE4_S4.md research/phase4/s4-design-audit-r2/CANDIDATE_MANIFEST.md PHASE4_MISSION.md research/phase4/s4-design/02-engine-integration-codex.md research/phase4/s4-design-audit/04-api-result-codex.md src/poker_solver/api_v4.py src/poker_solver/allstreet.py src/poker_solver/multistreet.py src/poker_solver/__init__.py src/poker_solver/equity.py src/poker_solver/best_response.py
git diff --name-only -- src tests scripts pyproject.toml
```

Results: HEAD `149780bf37e3e3a824e03e6d2c1df3cd99b12cd6`; tag object `feba8222a0b614b0c64eca59402403ce733195ea`, type `tag`; peeled commit `5809ecca28ae6d0588ea07709c90beac3072c167`. Tracked source/test/script/dependency diff command produced no output. These checks were repeated near report finalization.

| Input | Observed raw SHA-256 |
| --- | --- |
| ARCHITECTURE_PHASE4_S4.md | 37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2 |
| research/phase4/s4-design-audit-r2/CANDIDATE_MANIFEST.md | f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed |
| PHASE4_MISSION.md | 5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61 |
| research/phase4/s4-design/02-engine-integration-codex.md | 79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d |
| research/phase4/s4-design-audit/04-api-result-codex.md | 4b74b1a27da50c6598a0cae4cfcd5846befcea560f6ba821d6e2ff49179c1ee4 |
| src/poker_solver/api_v4.py | 70d378d6a52ae544615a5aa4dda6bd9e987f8161f08119914a0762ed0727a1a3 |
| src/poker_solver/allstreet.py | 30d94c226a82375afa2a10f4e3c3b785e37009257023b65da296742bf7cbd1ea |
| src/poker_solver/multistreet.py | bdacc32688361f0cec48205b722aca8843c24dca4f58dd11479d5aa85fdfa490 |
| src/poker_solver/__init__.py | 0c2a03813d375d362c582b3df0744d80802c5f008e2b42825f4afeaed5326159 |
| src/poker_solver/equity.py | fd419d547dff9209f76bcf32a0b4e72233f3b875ef97857700938daad87ec537 |
| src/poker_solver/best_response.py | 6b4c007e479b446b4297178367e17b575b6b239a87e11817711c9a2c5c85524f |

All four supplied immutable hashes match. Read the architecture, manifest, mission, authoritative integration design, R1 report, and requested source modules. Inspected related model/bounded-tree/API imports and relevant tests, including v4 schema/seed/bound/isolation tests, allstreet deep-freeze tests, multistreet hidden-DEAL information-key tests, equity input/range tests, and best-response hidden-information/oracle tests. Existing unrelated working-tree changes in PROGRESS.md, STATE.txt and research artifacts were observed and left untouched. The user's exclusive ownership instruction overrides mission instructions to write parent state/progress files.

## 2. R1 reproduction and adjudication

| R1 finding | R2 verdict | Evidence |
| --- | --- | --- |
| F1 HIGH: response/nested wire schemas not frozen | **PASS for exact field shapes; FAIL for remaining canonical provenance/mass semantics** | R1 explicitly reproduced the ambiguous `include`/prose field list and omitted-vs-null alternatives. R2 lines 336–450 now enumerate the response and nested records exhaustively. The old alternative top-level names and omission of lifted_strategy are prohibited. Deterministic record ordering is now explicit. Findings A/B below identify the remaining semantic/encoding gaps; the old HIGH shape finding is not simply repeated. |
| F2 MEDIUM: inherited optional versus required base limits | **PASS, repaired** | Lines 308–314 explicitly make both base bounds newly mandatory only for the new operation, reject omission before equality checks, and require both equalities. Actual old parser lines 545–563 and 640–646 keeps optional defaults 100000/512. Executable capture below reproduces those defaults. Both omitted, either omitted, equal, and unequal cases are explicitly future RED cases at line 507. |
| F3 MEDIUM: integer ingress rounded through inherited `_float` | **PASS for original witness and explicit local repair; FAIL for wider source-domain feasibility** | Old parser `_float(9007199254740993)` still returns 9007199254740992.0. R2 line 332 explicitly forbids that helper for new weights, preserves non-bool integers, and pins direct-Python/decoded-JSON parity. The original ambiguity is resolved. Finding C is a different, larger integer boundary exposed by the requested source audit. |

## 3. Contract inventory and per-requirement decisions

PASS here means a sufficient design obligation or demonstrated current-source feasibility, not implemented S4 behavior.

| Requirement | Verdict | Evidence/limits |
| --- | --- | --- |
| Strict envelope and request field membership | **PASS** | Lines 306–330: exact envelope; 15 mandatory payload fields including both base bounds and abstraction; only optional field exact_evaluation. Inherited combo record is exactly cards/weight (api_v4.py:589), integer-card arrays retain existing meanings. Seven required abstraction keys, exact two-key diagnostic object. Missing/unknown fields explicitly fail at every nested level. |
| Exact successful top-level schema | **PASS** | Lines 339–359 require all 21 keys: version, operation, game_version, abstraction_version, algorithm, iterations, seed, values, reduced_nashconv, reduced_exploitability, exact_nashconv, exact_exploitability, exact_evaluation_status, metric_scope, strategy_scope, strategy, lifted_strategy, abstraction_lossless, approximate, metadata, provenance. No additional keys or optional top-level keys. |
| Exact nested record membership | **PASS for shapes** | Lines 364–403 define ActionRecord(kind/amount), RationalRecord(numerator/denominator), PublicFrameRecord's ten fields, AbstractKeyRecord's five fields, ExactKeyRecord's nine fields, PolicyItem(action/probability), both policy entries(key/policy), BucketRecord(player/bucket_id/members/exact_mass), and BucketPairRecord(player0_bucket/player1_bucket/world_count/exact_mass). Lines 407–448 exhaustively enumerate metadata. Bucket mass meaning remains B. |
| Required-null relationships | **PASS** | Lines 362/450: not-requested requires null exact metrics, lifted_strategy, and diagnostic bounds; completed requires finite metrics, complete non-null lift, and the requested bounds. Null/absent diagnostic request selects not-requested. Cap failure cannot masquerade as a successful not-requested response. |
| Ordering and structural identity | **PASS**, except digest preimage A | Line 405 sorts policy entries by encoded structured keys, preserves source action order, sorts buckets/pairs numerically and members by card pair. Lines 44–48 preserve turn/river order while sorting whole runouts and assign IDs by full signatures. ExactKeyRecord matches all nine components of multistreet.py:446–456; public history excludes DEAL but retains RUNOUT. No `str(key)` overwrite/collision path is prescribed. Cryptographic hashes do not replace signature equality (line 63). |
| Deterministic canonical digest | **FAIL — MEDIUM, A** | JSON formatting is specified, but its exact input object schema is not. |
| Bucket probability meaning | **FAIL — MEDIUM, B** | `BucketRecord.exact_mass` has a type but no selected normalization/marginal definition. |
| Missing/unknown, bool, seed and nonfinite rejection | **PASS as design** | Lines 52,105,226,330,332,405,454 reject unsupported numerics, bool integer/weight values, invalid seeds, NaN/infinity and nonfinite serialization. Existing helpers support strict field rejection. WeightedCombo alone accepts bool/Fraction, so the new boundary must perform its own checks. |
| Exact float/Fraction arithmetic and caps | **PASS in stated arithmetic; FAIL source-domain coverage C** | 0.1 means its exact binary float, not 1/10. Convert before multiplying; preserve integer Fraction values; enforce numerator/denominator cap, all intermediate Fraction bounds, positive non-bool resource bounds, depth <=128 and pot+2*stack <=2**40. Zero weights are omitted/countable (line 50); “positivity” at line 332 is read with that explicit zero rule, not as a new zero-input rejection. |
| Requested diagnostic bounds and fail-before-training | **PASS for bounded failure/status; FAIL timing — MEDIUM, D** | Independent bounds are explicit. Reduced preflight is before solver construction (173), but requested exact preflight is not placed before training (228/362). |
| Provenance, scope and finite-profile claims | **PASS** | Exact provenance sentence is pinned at 362; reduced-game and abstract-bucket-public-history are literals; diagnostic absence is not represented as measured exact exploitability. approximate=true is finite float training, abstraction_lossless=true is the quotient certificate. Zero rational terminal diameter/model error, arithmetic label, analytic/executed count status and resource counts/caps are wire fields. §7 finite-profile incentives and rational replay are acceptance-test certificates, not a promise to return an extra runtime certificate object. |
| `lossy_merges=0` versus wire omission | **PASS, no genuine wire contradiction** | Detailed adjudication below. |
| Deep immutability/result isolation | **PASS as design** | Lines 84,230,454 require defensive detachment and recursive freezing, plus fresh JSON containers; frozen dataclasses alone are insufficient. Existing _deep_freeze and nested result tests demonstrate a feasible pattern. New record whitelist must prevent arbitrary opaque mutable metadata escape. |
| Existing operation compatibility | **PASS, scoped evidence** | Lines 304,311,332,509 preserve prior schemas/defaults/coercion. Source diff is empty; 48 existing focused tests pass. No full 817-test regression was run or adopted from another auditor. |
| Dependency/import-cycle feasibility | **PASS, with numeric carrier issue C separate** | stdlib Fraction/hashlib/json suffice; pyproject.toml has no runtime dependencies. allstreet imports api.complete_strategy, api imports multistreet/CFR/BR but no eager allstreet import; api_v4 imports allstreet locally. New abstraction may depend downward on model/multistreet/equity/bounded_tree; solve facade can import complete_strategy and locally translate allstreet; __init__ can export after existing imports. No reverse eager api->facade->allstreet->api edge is required. |

## 4. Remaining findings

### A — FAIL / MEDIUM — canonical digest formatting does not freeze the preimage schema

Architecture line 452 says: “SHA-256 over UTF-8 canonical JSON for the normalized semantic source config plus abstraction config.” It specifies a digest_schema field, key sorting, separators, ASCII escaping, integer encoding and RationalRecord. It does not specify the exact outer object field names or nesting of those two configs. Both `{digest_schema, source_config, abstraction_config}` and `{digest_schema, config, abstraction}` meet the literal instructions and hash differently. This is not a SHA-256 collision claim; it is two encoders assigning different IDs to the same semantic input.

The arithmetic probe below demonstrates different hashes with illustrative config fragments; those fragments are deliberately not claimed to be valid solve requests. Substituting complete configs preserves the ambiguity. Line 405 also relies on canonical encoding for key sorting, so a frozen common encoder specification should explicitly apply to those records as well.

Repair: freeze the exact digest-input object and all included source/abstraction fields, specify normalization of zero support and weights, canonical reduced fraction spelling (including zero), and pin at least one complete input/preimage/digest vector. This is the residual canonical provenance portion of R1 F1, not an absence-of-implementation complaint.

### B — FAIL / MEDIUM — BucketRecord.exact_mass has two materially different plausible meanings

Line 396 defines a bucket exact_mass but never defines its probability space. Lines 129–143 define compatible-world, bucket-pair, and conditional member mass, not the standalone per-player bucket mass. Summing normalized own input weights differs from marginalizing the globally normalized compatible-deal distribution when blockers are present.

Concrete design-relevant witness: two equally weighted P0 hands; one is compatible with one equally weighted opponent hand, the other with two. Their prior own-range masses are 1/2,1/2, but their root compatible-deal marginals are 1/3,2/3. This is precisely the structure of the mandated opponent-blocker companion. Both interpretations produce RationalRecord values and neither is selected by the wire definition. Clients cannot know whether bucket masses must equal marginals of bucket_pairs.

Repair: define BucketRecord.exact_mass explicitly, preferably as the sum of root bucket-pair masses incident to that player's bucket if a root-deal marginal is intended; otherwise explicitly label and define the own-range prior. Pin the blocker witness. Pair masses themselves are adequately defined by line 129.

### C — FAIL / MEDIUM — advertised integer arithmetic outgrows the unchanged typed source carrier

Lines 52/105/332 prescribe exact integer ingress and a default max_fraction_bits=4096 without a float-representability ceiling. A positive integer `2**1024` has 1025 bits and survives JSON decoding exactly. With one compatible world and opponent weight 1, its raw weight/product/normalizer and normalized mass fit that cap; the pot/stack/depth constraints can all be tiny.

Nevertheless normal construction of required `WeightedCombo((0,1), 2**1024)` raises `OverflowError: int too large to convert to float` at equity.py:39 (`math.isfinite`). allstreet.py:89/99 and multistreet.py:64 repeat the same conversion. Merely specializing `_float` does not fix this path. The typed facade requires existing AllStreetPostflopConfig/MultiStreetConfig with WeightedCombo members, so this is a concrete source boundary the design must resolve. It is not evidence of a future parser defect, and does not invalidate the successfully repaired `2**53+1` case.

Repair: explicitly choose the accepted integer domain and error behavior, or specify a safe S4 carrier/construction path preserving raw exact weights and direct-Python/JSON parity without silently weakening old-operation validation. If shared constructor changes are intended, reconcile that with the implementation batches' current owned-file lists and compatibility gates. Do not rely on bypassing frozen constructors or rescaling away requested input bits without defining those semantics.

Additional source warning, not a separate defect: finite float weights 1e308 are accepted by existing config constructors, but legacy exact-root multiplication yields inf/inf -> NaN. The reduced design already requires Fraction conversion before multiplication and thus avoids it. Exact diagnostics need a deliberate safe boundary/failure path; reusing the old root is not evidence that all new rational-domain inputs are diagnosable. The probe below records this limitation without claiming reduced S4 executes that code.

### D — FAIL / MEDIUM — exact-diagnostic cap rejection is not explicitly before training

Line 173 explicitly places the **reduced** preflight “before solver construction.” Line 228 says “Reduced compilation happens before any exact-tree preflight” and that requested diagnostics exceeding independent bounds fail. Line 362 forbids returning success/not-requested on such failure. None orders the exact preflight before reduced solver construction/training. Both `compile -> reduced preflight -> train -> exact preflight -> error` and `compile -> reduced preflight -> exact preflight -> train` fit those statements.

The requested audit includes fail-before-training. The current old facade demonstrates the desired behavior (allstreet.py:232–243 and executable instrumentation below), but that old-operation behavior does not silently impose an ordering on the new optional diagnostics. Lines 300/541 require the separate exact same-game cap control to fail before training; they do not fill this new-facade diagnostic ordering gap.

Repair: explicitly place requested exact node/depth preflight after reduced compilation/preflight and before either solver construction or training; add a mock/counter assertion for a fitting reduced tree paired with an insufficient exact diagnostic bound. Actual lift/evaluation can remain after training. No exact preflight should run when diagnostics are not requested.

## 5. Explicit adjudication: lossy_merges

**PASS — omission is an internal/result invariant versus wire-projection distinction, not a genuine schema contradiction requiring an added wire key.**

Exact text at §6 line 234: “Set `abstraction_lossless=True`, `model_error_bound=0`, `lossy_merges=0`, and label reduced versus exact metrics explicitly.” This paragraph does not say “serialize these as top-level keys” or “include these three keys in AbstractionMetadata.” The Python result declaration at lines 187–203 itself has no lossy_merges or model_error_bound field; it has a plan and a general metadata mapping.

In contrast, §9.1 line 336 explicitly says the successful response has “exactly these required top-level keys; no key is optional,” line 364 says nested records have “no additional keys,” and line 407 says AbstractionMetadata “has exactly these keys and value types.” Thus a serializer must not add lossy_merges to either wire object. An implementation can preserve zero lossy merges as a checked compiler/plan invariant or Python-side metadata and emit the exact enumerated projection. Zero model error is separately and explicitly projected as a RationalRecord at lines 440/450.

This reading satisfies both sections without silently relaxing the exact schema. §3 lines 63/67 already prohibit mismatched-signature merges, making zero lossy merges a substantive invariant independently of a redundant JSON key. A clarifying sentence could help a future author, but the text does not require exposing every internal result fact in JSON; internal plan arrays are explicitly omitted at line 450. I do not manufacture a fifth finding from the omission.

Likewise §5's mention of infosets/runtime accounting does not license adding unspecified wire metadata fields. The tests' rational finite-profile certificate is not falsely described as a measured unrestricted-poker solution. Source allstreet's old approximate=False and new approximate=True retain separately defined meanings and are not a contradiction.

## 6. Read-only executable evidence

All Python probes used `PYTHONDONTWRITEBYTECODE=1`; no future S4 implementation, source test, cache, or probe file was created. In-memory mock replacement was confined to its context manager. Below are the exact two substantive probe commands and their observed output.

### Probe 1: parser/types, exact arithmetic, structural encoding

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
import json, math, hashlib
from fractions import Fraction
from poker_solver.api_v4 import _float, _int, _object, _object_with_optional, dispatch_v4
from poker_solver.equity import WeightedCombo
from poker_solver.allstreet import _deep_freeze, AllStreetPostflopConfig
from poker_solver.multistreet import MultiStreetConfig, create_root

def probe(label, fn):
    try: print(label, '=>', repr(fn()))
    except Exception as e: print(label, '=>', type(e).__name__ + ':', str(e))
n=2**53+1
print('integer ingress', n, _float(n,'weight'), Fraction(n), Fraction.from_float(_float(n,'weight')))
print('JSON parity',type(json.loads(json.dumps(n))).__name__, json.loads(json.dumps(n))==n)
for label,v in [('bool',True),('nan',float('nan')),('inf',float('inf')),('negative',-1),('Fraction',Fraction(1,3))]:
    probe('_float '+label,lambda v=v:_float(v,'weight',nonnegative=True))
    probe('WeightedCombo '+label,lambda v=v:WeightedCombo((0,1),v).weight)
probe('_int bool',lambda:_int(True,'bound',positive=True))
probe('missing',lambda:_object({}, {'x'},'probe'))
probe('unknown',lambda:_object({'x':1,'extra':2},{'x'},'probe'))
probe('optional omitted',lambda:_object_with_optional({'x':1},{'x'},{'max_nodes','max_depth'},'probe'))
large=2**1024
print('large integer bits',large.bit_length(),'Fraction bits',Fraction(large).numerator.bit_length(),'JSON preserved',json.loads(json.dumps(large))==large)
probe('WeightedCombo 2**1024',lambda:WeightedCombo((0,1),large))
for v in [0.1, 5e-324, 1e308]:
    f=Fraction.from_float(v)
    print('float rational',repr(v),str(f) if v==0.1 else 'large', 'bits',f.numerator.bit_length(),f.denominator.bit_length())
print('pre-multiply exact vs float', Fraction.from_float(1e308)**2 > 0, 1e308*1e308)
a=WeightedCombo((0,1),1e308); b=WeightedCombo((2,3),1e308)
cfg=MultiStreetConfig('multistreet-v1','river',(4,5,6,7,8),2,1,(a,),(b,),(),'no-limit',(1,),True)
probe('source exact root overflowing products',lambda:create_root(cfg).chance_outcomes())
raw={'x':[{'y':1}]}; frozen=_deep_freeze(raw); raw['x'][0]['y']=2
print('deep freeze detached',frozen['x'][0]['y'])
probe('deep freeze nested mutation',lambda:frozen['x'][0].__setitem__('y',3))
def enc(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
print('structured collision check',enc({'kind':'A:1','amount':2}) != enc({'kind':'A','amount':12}))
print('rational alternatives',enc({'numerator':'1','denominator':'2'}),enc({'numerator':'2','denominator':'4'}))
source={'version':'multistreet-v1'}; abstraction={'version':'exact-signature-belief-v1'}
for obj in [{'digest_schema':'s4-semantic-config-v1','source_config':source,'abstraction_config':abstraction},{'digest_schema':'s4-semantic-config-v1','config':source,'abstraction':abstraction}]:
    s=enc(obj);print('digest wrapper witness',s,hashlib.sha256(s.encode()).hexdigest())
PY
```

Exit 0, output:

```text
integer ingress 9007199254740993 9007199254740992.0 9007199254740993 9007199254740992
JSON parity int True
_float bool => ValueError: weight must be a number
WeightedCombo bool => True
_float nan => ValueError: weight must be finite
WeightedCombo nan => ValueError: combo weight must be finite and nonnegative
_float inf => ValueError: weight must be finite
WeightedCombo inf => ValueError: combo weight must be finite and nonnegative
_float negative => ValueError: weight must be non-negative
WeightedCombo negative => ValueError: combo weight must be finite and nonnegative
_float Fraction => ValueError: weight must be a number
WeightedCombo Fraction => Fraction(1, 3)
_int bool => ValueError: bound must be a JSON integer
missing => ValueError: missing probe fields: ['x']
unknown => ValueError: unknown probe fields: ['extra']
optional omitted => {'x': 1}
large integer bits 1025 Fraction bits 1025 JSON preserved True
WeightedCombo 2**1024 => OverflowError: int too large to convert to float
float rational 0.1 3602879701896397/36028797018963968 bits 52 56
float rational 5e-324 large bits 1 1075
float rational 1e+308 large bits 1024 1
pre-multiply exact vs float True inf
source exact root overflowing products => ((Action(kind='DEAL', amount=0), nan),)
deep freeze detached 1
deep freeze nested mutation => AttributeError: 'mappingproxy' object has no attribute '__setitem__'
structured collision check True
rational alternatives {"denominator":"2","numerator":"1"} {"denominator":"4","numerator":"2"}
digest wrapper witness {"abstraction_config":{"version":"exact-signature-belief-v1"},"digest_schema":"s4-semantic-config-v1","source_config":{"version":"multistreet-v1"}} 40e1d56bfda62555f5fa206ee9f6d330db55c1a018762df71dd00c13fcef0bb3
digest wrapper witness {"abstraction":{"version":"exact-signature-belief-v1"},"config":{"version":"multistreet-v1"},"digest_schema":"s4-semantic-config-v1"} 5ae5026130f5ce8a54dc86614f7c7eb4d5ba4cc21495a829db765f9f2e36ff0b
```

### Probe 2: old defaults, exact fixture, early cap rejection, mass arithmetic

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python - <<'PY'
from unittest.mock import patch
from fractions import Fraction
from poker_solver.api_v4 import dispatch_v4
from poker_solver.allstreet import AllStreetPostflopConfig, solve_allstreet_postflop
from poker_solver.equity import WeightedCombo
from poker_solver.cards import parse_cards
from poker_solver.bounded_tree import validate_bounded_tree
from poker_solver.allstreet import create_allstreet_root
class StopProbe(Exception): pass
p=dict(version='allstreet-postflop-v1', starting_board=[0,1,2], initial_dead_pot=2, effective_stack=1, player0_combos=[dict(cards=[3,4],weight=2**53+1)], player1_combos=[dict(cards=[5,6],weight=1)], allowed_runouts=[[7,8]], betting_mode='no-limit',wager_targets=[1], algorithm='vanilla-cfr',iterations=1,seed=None)
def capture(config,**kw):
    print('old omitted bounds and parsed weight',config.max_nodes,config.max_depth,config.player0_combos[0].weight)
    raise StopProbe
with patch('poker_solver.allstreet.solve_allstreet_postflop',capture):
    try: dispatch_v4(dict(version=4,operation='solve-allstreet-postflop',payload=p))
    except StopProbe: pass
cards=lambda s:parse_cards(s.split())
cfg=AllStreetPostflopConfig('allstreet-postflop-v1',cards('Ah Kh Qh'),2,1,tuple(WeightedCombo(cards(s)) for s in ['2c 3c','2d 3d']),tuple(WeightedCombo(cards(s)) for s in ['2s 3s','Th 4s']),tuple(cards(s) for s in ['Jh 9h','Jh 8h']),'no-limit',(1,),10000,32)
print('small exact stats',validate_bounded_tree(create_allstreet_root(cfg),max_nodes=10000,max_depth=32))
from dataclasses import replace
with patch('poker_solver.allstreet.CFRSolver') as solver:
    try:solve_allstreet_postflop(replace(cfg,max_nodes=1),algorithm='vanilla-cfr',iterations=1)
    except ValueError as e: print('old cap failure',str(e),'solver constructed',solver.called)
weights=[Fraction(1),Fraction(1)]; compatible_counts=[1,2]
print('bucket prior masses',[str(w/sum(weights)) for w in weights])
print('bucket compatible-deal marginals',[str(Fraction(n,sum(compatible_counts))) for n in compatible_counts])
q=(Fraction(1,3),Fraction(2,3)); kernel=(Fraction(1),Fraction(1,2)); total=sum(x*y for x,y in zip(q,kernel))
print('belief arithmetic',str(total),tuple(str(x*y/total) for x,y in zip(q,kernel)))
PY
```

Exit 0, output:

```text
old omitted bounds and parsed weight 100000 512 9007199254740992.0
small exact stats BoundedTreeStats(node_count=321, max_depth_reached=12, terminal_count=136, chance_count=57, decision_count=128)
old cap failure max_nodes 1 exceeded solver constructed False
bucket prior masses ['1/2', '1/2']
bucket compatible-deal marginals ['1/3', '2/3']
belief arithmetic 2/3 ('1/2', '1/2')
```

### Focused existing tests

First attempted:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p no:cacheprovider tests/test_api_v4.py tests/test_phase4_s1_exports.py tests/test_allstreet_config.py::TestAllStreetResultDeepImmutability
```

Exit 1: `/home/genomix-node/.hermes/hermes-agent/venv/bin/python: No module named pytest`. No installation attempted. Used the existing workspace interpreter:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_api_v4.py tests/test_phase4_s1_exports.py tests/test_allstreet_config.py::TestAllStreetResultDeepImmutability
```

Exit 0: **48 passed in 1.80s**. These validate old operation schemas, malformed requests, seed determinism, resource errors, JSON safety, exports and deep result isolation. They do not validate the proposed S4 schema or repair the findings above.

## 7. Final decision and evidence boundary

**REJECT** the frozen design contract pending A–D. No HIGH implementation bug is alleged; all four remaining findings are MEDIUM design ambiguities/boundary omissions with concrete text or executable source witnesses. R1 F2 and the literal R1 F3 rounding defect are repaired. R1 F1 exact field layouts are repaired, but canonical provenance remains incomplete. The zero-loss invariant is compatible with the exhaustive wire projection.

Only this report and `.hb/C4R2A4-CODEX` are owned outputs. No source, tests, architecture, manifest, mission, dependency, progress/state, or Git history was written. No future S4 code was implemented. No full suite, reduced solve, 1,000-iteration acceptance, runtime speedup, or independent exact-quotient proof is claimed. Audit completion is not operationally blocked: findings warrant COMPLETE_FAIL with blocked=false. The final raw report hash is computed after the last report write and recorded in the heartbeat, which is written last and then reread with this report for equality verification.
