# C3I1-5 recovery audit — adversarial bounds

**Verdict: FAIL / BLOCKED.** Fresh non-author audit of frozen S3-I1. Runtime defects and mandatory permanent-test omissions prevent PASS. Existing focused tests are green; that does not discharge the architecture requirements.

Scope: typed configuration, immutable inputs, state/chance/betting bounds, protocol compatibility, continuation validation, and permanent I1 coverage. No source, test, existing evidence, or git-state edits; no commit. Only this report and `.hb/C3I1-5` are written. Probe fixtures exist only in interpreter memory. This report does not certify the full regression, I2 facade/API/exports/examples, or solver diagnostics.

## Frozen identity

Verified at entry and again after probes:

```text
a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6  ARCHITECTURE_PHASE4_S3.md
0e55fbce5f6934c8e2e63ee28ce9d01d9268792165d9318bc8c9ed03b5f73422  src/poker_solver/nplayer_preflop.py
5a214b900a7ad1b61aa67cd294d7000e3eef0023f82bb834d1e94035f815a867  tests/test_nplayer_preflop_config.py
d61a86d39f864d494f19a91698478c4af39b76d6ad0372321f18d69706349f69  tests/test_nplayer_preflop_betting.py
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
282112f2b88e57b1b8b25bbdd69d0f6fb90df714e92ccff80945f9724375e69d  tests/test_nplayer_preflop_information.py
```

Read architecture, candidate manifest, production module, all four focused suites, and relevant shared Action/WeightedCombo/ForcedPost/sizing/NPlayerGameState/collector implementations. `rg --files -g AGENTS.md` found no workspace AGENTS.md.

## Blockers

### B1 — sizing expressions are mutable and can violate the hash contract

Production lines 79–99 create a mutable `_data` dictionary and assignable slots, with the hash cached separately in `_items`. Architecture §2.2 requires an immutable, hashable representation; §2.4 requires detached nested inputs.

Executed ordinary assignment `r.expressions[0]._data["value"] = 8`, without object.__setattr__, changed an existing state's raise from 6 to 16 and changed its information key. The original rule hash stayed unchanged. It then compared equal to a reconstructed rule but had a different hash. Assigning the expression's `_data` slot also succeeded. These are accesses to implementation-named attributes, not public mapping assignment; the latter correctly rejects writes. The exposed expression nevertheless contains mutable reachable state and does not satisfy the promised immutable representation.

Caller dictionary detachment and ordinary frozen dataclass assignments pass. Repair the actual backing representation and add permanent tests for stable actions, information identity, equality, and hash behavior after attempted mutation.

### B2 — unsupported forced-post kinds are accepted and transferred as live wagers

Production config lines 260–268 verify ForcedPost instances/amounts/seats but never validate `post.kind`. Shared ForcedPost also does not validate kind. Appending `ForcedPost(0, "garbage", 3)`, `ForcedPost(0, None, 3)`, or `ForcedPost(0, 42, 3)` to valid HU blinds succeeds. Root street commitments become `(4, 2)`.

This violates §2.4 rejection of invalid forced-post types and §3's exact supported ledger. It also corrupts the intended blind/straddle wager without a declared straddle. S3 must validate its own accepted post kinds without relying on the legacy helper. Add permanent rejection fixtures.

### B3 — odd-chip order admits bool/float seat identities, then fails at settlement

Production config's permutation check uses set equality without strict element typing. Both `(False, True)` and `(0.0, 1.0)` construct successfully. A normal DEAL/CALL/CHECK path subsequently raises `ValueError: odd_chip_order must contain unique non-negative seats` in the shared award helper.

Architecture §§2.3–2.4 require seat permutation/strict inputs; invalid configuration must fail at construction. This is an accepted-config runtime failure, not merely cosmetic type permissiveness. Require strict integer non-bool seat elements and permanent boundary tests.

### B4 — public direct construction accepts impossible chance roots

Production state's CHANCE branch (around lines 585–587) checks deal/history/terminal values only. Using dataclasses.replace on a valid root accepts nonzero raise_count, no pending responders despite two funded seats, no raise entitlements, an incorrect last increment, and a zero-post ledger while retaining the original posted config.

Most directly, `replace(root, pending=()).child(Action("DEAL", 0))` settles immediately with empty history and utilities `(-1, 1)`; both seats still had a betting decision. Architecture §§3–4 explicitly state root raise count, wager increment, entitlements, ledger, and responder invariants. This concerns the exported constructor, not factory-produced roots (which passed the probes). Enforce the root invariants or provide an explicit validated construction boundary; add permanent invalid-state tests.

### B5 — nonfinite Decimal sizing is accepted until decision evaluation

A `big-blinds` sizing rule with `Decimal("Infinity")` is accepted by rule/config/root/deal construction, then `legal_actions()` raises `decimal.InvalidOperation`. Decimal NaN rejects by raw InvalidOperation; float NaN/infinity correctly reject with ValueError.

S3 delegates to `validate_size_expression`, but that shared validator's numeric finiteness check only covers floats. Architecture §2.2 requires validated strict expressions, and the bounded typed game cannot accept a rule that crashes when its first legal actions are requested. Validate supported numeric finiteness at the S3 boundary and add a permanent Decimal regression; no shared-file edit was made during this audit.

### B6 — declared structural bound can exceed the reused collector's recursion capacity

Executed a real HU configuration with 1,050 per-raise sizing keys, stacks 10,000, max_raises=1,050 and max_nodes=100,000. Repeated minimum full raises increase the target by two. Iterative calls to the production state complete 1,050 raises and a final call (history length 1,051), under the conservative decision bound 1,052, with exact zero-sum utilities.

The unmodified `collect_nplayer_infosets(root, max_nodes=100000, max_depth=1054)` raises `RecursionError: maximum recursion depth exceeded in comparison` at the normal Python recursion limit 1,000. No lowered recursion limit, monkeypatch, artificial state wrapper, or recursive probe traversal was used. A configured finite bound is not sufficient protection for the reused recursive traversal. Architecture §§7/10 promise structural bounds and reuse of that solver path.

The I1 state transition itself handles this path; the failure is in the mandated reused traversal. Treat this as a bounds-integration blocker to resolve before advertising that all accepted bounds are supported. A controlled documented validation bound or an iterative traversal needs a permanent regression. The absent I2 solve facade is not itself counted as an I1 defect.

### B7 — mandatory permanent I1 tests are missing even where runtime probes pass

Only the four listed files import this module (`rg -l` verification). They contain 26 passing pytest cases, but do not provide all I1 contracts promised by architecture §§5, 12–13, and 15.

Specific omissions:

- No accepted double or Mississippi straddle fixture, no permanent four-variant six-seat ledger/actor/legal-action repeatability comparison. The only Mississippi case rejects HU; runtime audit fixtures for all four variants passed.
- No exact-all-in forced-post option fixture. The audit's standard/double all-in straddler probes correctly exclude that seat.
- No permanent rejection tests for partial/single-seat/unequal antes, cumulative overposts, non-increasing straddles, unknown post kinds, or comprehensive bool/type/card/continuation/bound inputs. Audit rejection probes passed for the validly enforced cases.
- No permanent small-blind-completion-as-caller sizing assertion. The audit's HU SB CALL2 followed by BB rule cold_callers=1 exposes RAISE6 correctly.
- No completed 5-bet+ sizing trace: the existing full-reopen test exposes a 4-bet candidate and stops without executing it. Cold-caller reset and exact full ordered action tuples also need stronger coverage than selected `any(...)` assertions.
- No permanent mutation/detachment/hashability or direct-state validation coverage; these omissions allowed B1/B4 through.
- The chance arithmetic test converts masses to floats and uses pytest.approx; it does not independently assert exact Fraction values. Audit exact masses 3/11, 6/11, 2/11 passed.
- Hidden-rank noninterference is tested only at N=2. Opponent-card noninterference covers 6/9, but hidden continuation-content noninterference for those N, hidden payoff-table values, and owner/public-field sensitivity are absent.
- HU projection covers root deals/partitions, initial ledger/actions and one raise/fold path, not the full projected decision/terminal partition compatibility promised by the architecture.

Permanent tests must be added and independently rerun. Passing temporary auditor probes cannot replace explicit permanent-fixture requirements. Solver reach/deviation oracles and strict v4/CLI/example/export suites belong to I2 and are not included in this I1 coverage blocker.

## Other observations and passing checks

- Bool rejection passes for count/button/stacks/bounds, sizing counts/value, range weights/cards, history-independent direct state numeric fields, and forced-post seats/amounts.
- Malformed/duplicate/out-of-range cards, canonical reversed duplicates, nonpositive/nonfinite weights, non-zero-sum/nonfinite/bool payoffs, wrong payoff lengths, and non-integer ranks reject.
- Empty compatible deal sets and candidate products over max_deals reject before unbounded enumeration. Exact deterministic chance order/masses pass.
- max_nodes=1 fails initial chance expansion; the generic collector correctly rejects max_nodes=2. Root creation with max_nodes=2 does not assert full-tree coverage, and is not reported as a bug. A low max_depth rejects predictably. max_raises suppresses further raises.
- Runtime `GameState` and `NPlayerGameState` conformance both pass; a complete tiny HU tree collects four information sets. N=2 through 9 call/check paths conserve the ledger and produce exact zero-sum terminal_values.
- Caller rank/payoff dictionaries are detached and exposed through mappingproxy. Sizing caller dictionaries are detached before the B1 backing mutation.
- Duplicate sizing keys reject. Ordinary dicts cannot represent duplicate continuation keys. A custom Mapping with repeated `.items()` entries is accepted with last-write-wins for both payoff and rank maps. This is recorded as typed-boundary hardening, not a separate I1 blocker: §11 explicitly requires JSON duplicate rejection, whose facade is I2. Tests should preserve that future boundary; do not claim ordinary-dict duplicates were tested.
- Exact Fraction and parseable rational-string payoffs are retained exactly; finite float input is converted to its exact binary rational. No rejection requirement for all finite floats is invented here.
- A finite rational of magnitude 10**400 fails with raw OverflowError in the float-finiteness check. This limits the otherwise exact domain and should receive an explicit supported-range/error contract, but is not needed for the blocking verdict.
- Read-only `git rev-parse phase3-398-green` returned `feba8222a0b614b0c64eca59402403ce733195ea`.
- Full regression was not run by this narrow auditor; the manifest's pending regression receipt is not promoted to a pass. No environment/execution blocker prevented the requested narrow probes.

## Exact executed commands and results

All commands ran from `/home/genomix-node/poker-solver`. Pytest cache writing and bytecode generation were disabled for the test/probe runs. No probe scripts were written to disk.

Identity command, exit 0 (hash output above):

```bash
sha256sum ARCHITECTURE_PHASE4_S3.md src/poker_solver/nplayer_preflop.py tests/test_nplayer_preflop_*.py
git rev-parse phase3-398-green
```

Focused permanent suite, exit 0:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py
```

```text
..........................                                               [100%]
26 passed in 0.17s
```

Coverage inspection commands, exit 0 (read alongside full test files):

```bash
rg -n 'def test|class NPlayerGameState|def __post_init__|max_depth|recurs' tests/test_nplayer_preflop* src/poker_solver/nplayer.py src/poker_solver/model.py src/poker_solver/preflop.py
rg -n 'double|mississippi|single.seat|unequal|increasing|nplayer_preflop' tests --glob '*.py'
rg -n 'NPlayerPreflop|nplayer_preflop' tests --glob '*.py' -l
```

The last command returns only the four frozen focused files; test-by-test gaps are stated above.

### Probe batch 1 — exact command, exit 0

The probe wrapper records acceptance and exception types without stopping on expected adversarial failures. An exit code of zero means the batch executed, **not** that every input conformed.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python - <<'PY'
from dataclasses import replace, FrozenInstanceError
from fractions import Fraction
from collections.abc import Mapping
from math import isfinite
from poker_solver.nplayer_preflop import *
from poker_solver.preflop import WeightedCombo
from poker_solver.game_structure import ForcedPost
from poker_solver.model import Action, CHANCE, TERMINAL, GameState
from poker_solver.nplayer import NPlayerGameState, collect_nplayer_infosets

def table(values=None):
    return NPlayerPreflopContinuation("terminal-table","C3I1-5","supplied",
        {} if values is None else {(deal, ()):values}, {}, ())
deal=((0,1),(2,3))
def cfg(n=2, **kw):
    d=tuple((2*i,2*i+1) for i in range(n))
    args=dict(version="nplayer-preflop-v1",num_players=n,button=0 if n==2 else n-1,
        starting_stacks=(100,)*n,forced_posts=(ForcedPost(0,"small-blind",1),ForcedPost(1,"big-blind",2)),
        straddle_variant="none",ranges=tuple((WeightedCombo(c,1),) for c in d),sizing_rules=(),
        max_raises=3,max_deals=1,max_nodes=10000,short_all_in_reopens=False,
        continuation=NPlayerPreflopContinuation("showdown-ranks","C3I1-5","supplied",{}, {d:tuple(range(n))},tuple(range(n))))
    args.update(kw)
    return NPlayerPreflopConfig(**args)
def probe(name, fn):
    try:
        value=fn()
        print(name, "=> ACCEPT", repr(value))
        return value
    except Exception as e:
        print(name, "=>", type(e).__name__, str(e))
def reject(name,fn):
    try: fn()
    except (ValueError,TypeError,OverflowError) as e:
        print(name, "=> REJECT", type(e).__name__, str(e)); return
    print(name, "=> UNEXPECTED ACCEPT")

base=cfg()
for field in ("num_players","button","max_raises","max_deals","max_nodes"):
    reject("bool "+field,lambda field=field:replace(base,**{field:True}))
for field in ("max_raises","max_deals","max_nodes"):
    for v in (0,-1,1.5):
        reject(f"bound {field}={v}",lambda field=field,v=v:replace(base,**{field:v}))
reject("bool stack",lambda:replace(base,starting_stacks=(True,100)))
reject("nonbool reopen",lambda:replace(base,short_all_in_reopens=1))
for cards in ((True,1),(0,0),(-1,2),(0,52),(0,),[0,1],("0",1)):
    reject("cards "+repr(cards),lambda cards=cards:cfg(ranges=((WeightedCombo(cards,1),),(WeightedCombo((2,3),1),))))
for weight in (True,0,-1,float("nan"),float("inf"),"junk"):
    reject("weight "+repr(weight),lambda weight=weight:cfg(ranges=((WeightedCombo((0,1),weight),),(WeightedCombo((2,3),1),))))
reject("duplicate normalized combo",lambda:cfg(max_deals=2,ranges=((WeightedCombo((0,1),1),WeightedCombo((1,0),2)),(WeightedCombo((2,3),1),))))
reject("empty compatible deals",lambda:cfg(continuation=table(),ranges=((WeightedCombo((0,1),1),),(WeightedCombo((0,2),1),))))
reject("product checked before collision",lambda:cfg(continuation=table(),ranges=((WeightedCombo((0,1),1),WeightedCombo((0,2),1)),(WeightedCombo((0,3),1),))))
for values in ((True,-1),(float("nan"),0),(float("inf"),-float("inf")),("junk",0),(1,1),(0,)):
    reject("payoff "+repr(values),lambda values=values:cfg(continuation=table(values)))
for ranks in ((True,1),(1.5,1),(float("nan"),1)):
    reject("ranks "+repr(ranks),lambda ranks=ranks:cfg(continuation=replace(base.continuation,showdown_ranks={deal:ranks})))
for order in ((False,True),(0.0,1.0),(0,0),(0,2)):
    probe("odd-chip "+repr(order),lambda order=order:replace(base,continuation=replace(base.continuation,odd_chip_order=order)).continuation.odd_chip_order)
for values in ((Fraction(1,3),-Fraction(1,3)),(0.1,-0.1),("1/3","-1/3"),(10**400,-10**400)):
    probe("exact payoff "+str(values)[:60],lambda values=values:table(values).payoff_table)
rule=NPlayerPreflopSizingRule("BTN/SB",0,0,"NA",({"unit":"big-blinds","value":3},))
reject("duplicate sizing key",lambda:cfg(sizing_rules=(rule,rule)))
for key in ("raise_count","cold_callers"):
    reject("sizing bool "+key,lambda key=key:replace(rule,**{key:True}))
reject("sizing bool value",lambda:replace(rule,expressions=({"unit":"big-blinds","value":True},)))
probe("rule hash/equality",lambda:(hash(rule)==hash(replace(rule)),rule==replace(rule),len({rule,replace(rule)})))
source={"unit":"big-blinds","value":3}
r=NPlayerPreflopSizingRule("BTN/SB",0,0,"NA",(source,))
state=create_nplayer_preflop_root(cfg(sizing_rules=(r,))).child(Action("DEAL",0))
original=state.legal_actions()
source["value"]=8
assert state.legal_actions()==original
print("caller sizing dict detached => PASS")
for name,fn in (
    ("rule assignment",lambda:setattr(r,"raise_count",2)),
    ("expression public item",lambda:r.expressions[0].__setitem__("value",8)),
    ("config assignment",lambda:setattr(base,"max_nodes",2)),
    ("continuation mapping assignment",lambda:base.continuation.showdown_ranks.__setitem__(deal,(9,8))),
):
    probe(name,fn)
before_key=state.information_state_key(0)
old_hash=hash(r)
r.expressions[0]._data["value"]=8
print("backing dict mutation =>",original,"->",state.legal_actions(),
      "key_changed",before_key!=state.information_state_key(0),"hash_unchanged",old_hash==hash(r),
      "equal_new_rule",r==replace(r),"equal_hash",hash(r)==hash(replace(r)))
probe("expression slot reassignment",lambda:setattr(r.expressions[0],"_data",{"unit":"big-blinds","value":9}))

rank_source={deal:(1,2)}
continuation=NPlayerPreflopContinuation("showdown-ranks","detach","supplied",{},rank_source,(0,1))
c=cfg(continuation=continuation)
rank_source[deal]=(2,1)
assert c.continuation.showdown_ranks[deal]==(1,2)
pay_source={(deal,()):(Fraction(1),Fraction(-1))}
p=NPlayerPreflopContinuation("terminal-table","detach","supplied",pay_source,{},())
pay_source.clear()
assert len(p.payoff_table)==1
print("caller rank/payoff dictionaries detached => PASS")

class RepeatedItems(Mapping):
    def __init__(self,key,first,second): self.key,self.first,self.second=key,first,second
    def __len__(self): return 2
    def __iter__(self): return iter((self.key,self.key))
    def __getitem__(self,key): return self.second
    def items(self): return ((self.key,self.first),(self.key,self.second))
probe("duplicate terminal mapping items",lambda:NPlayerPreflopContinuation("terminal-table","dup","supplied",RepeatedItems((deal,()),(1,-1),(2,-2)),{},()).payoff_table)
probe("duplicate rank mapping items",lambda:cfg(continuation=replace(base.continuation,showdown_ranks=RepeatedItems(deal,(1,2),(2,1)))).continuation.showdown_ranks)

root=create_nplayer_preflop_root(base)
s=root.child(Action("DEAL",0))
for name,changes in (
    ("bool pot",dict(pot=True)),
    ("bad ledger",dict(pot=4)),
    ("duplicate pending",dict(pending=(0,0))),
    ("bool pending",dict(pending=(False,1))),
    ("actor mismatch",dict(acting_player=1)),
    ("too many raises",dict(raise_count=4)),
    ("malformed deal",dict(private_deal=((0,0),(2,3)))),
    ("bool folded",dict(folded=(0,False))),
):
    reject("direct "+name,lambda changes=changes:replace(s,**changes))
for name,changes in (
    ("chance raise_count",dict(raise_count=1)),
    ("chance empty pending",dict(pending=())),
    ("chance missing entitlement",dict(can_raise=(False,False))),
    ("chance wrong increment",dict(last_raise_increment=99)),
    ("chance zero post ledger",dict(pot=0,street_committed=(0,0),total_contributed=(0,0),remaining=(100,100))),
):
    probe("direct "+name,lambda changes=changes:replace(root,**changes).current_player())
bad=replace(root,pending=()).child(Action("DEAL",0))
print("direct empty pending consequence => terminal",bad.current_player()==TERMINAL,"history",bad.history,"values",bad.terminal_values)
reject("max_nodes chance 1",lambda:create_nplayer_preflop_root(replace(base,max_nodes=1)))
small=create_nplayer_preflop_root(replace(base,max_nodes=2))
reject("max_nodes generic tree 2",lambda:collect_nplayer_infosets(small,max_nodes=2,max_depth=7))
probe("full-tree GameState/NPlayerGameState",lambda:(isinstance(root,GameState),isinstance(root,NPlayerGameState),len(collect_nplayer_infosets(root,max_nodes=10000,max_depth=7))))
reject("depth 1",lambda:collect_nplayer_infosets(root,max_nodes=10000,max_depth=1))
capped=create_nplayer_preflop_root(cfg(max_raises=1)).child(Action("DEAL",0)).child(Action("RAISE",100))
assert not any(a.kind=="RAISE" for a in capped.legal_actions())
print("max_raises suppresses next raise => PASS")

ranges=((WeightedCombo((0,1),1),WeightedCombo((2,3),2)),(WeightedCombo((4,5),3),WeightedCombo((0,6),1)))
masscfg=cfg(ranges=ranges,max_deals=4,continuation=table())
expected=((((0,1),(4,5)),Fraction(3,11)),(((2,3),(4,5)),Fraction(6,11)),(((2,3),(0,6)),Fraction(2,11)))
assert enumerate_nplayer_preflop_deals(masscfg)==expected
a=create_nplayer_preflop_root(masscfg).chance_outcomes()
assert a==create_nplayer_preflop_root(masscfg).chance_outcomes()
assert abs(sum(p for _,p in a)-1)<1e-12 and all(isfinite(p) and p>=0 for _,p in a)
print("deterministic exact blocker mass => PASS",expected)
for n in range(2,10):
    cur=create_nplayer_preflop_root(cfg(n))
    assert isinstance(cur,NPlayerGameState)
    cur=cur.child(Action("DEAL",0))
    steps=0
    while cur.current_player()!=TERMINAL:
        action=next(a for a in cur.legal_actions() if a.kind in ("CALL","CHECK"))
        cur=cur.child(action); steps+=1
        assert cur.pot==sum(cur.total_contributed)
        assert all(cur.remaining[i]+cur.total_contributed[i]==100 for i in range(n))
    assert sum(cur.terminal_values)==0 and steps<=n
    print("N",n,"call/check steps",steps,"exact",cur.terminal_values)

PY
```

Exact stdout:

```text
bool num_players => REJECT ValueError num_players must be an integer from 2 to 9
bool button => REJECT ValueError button must be a valid integer seat
bool max_raises => REJECT ValueError max_raises must be a non-negative integer
bool max_deals => REJECT ValueError max_deals must be a non-negative integer
bool max_nodes => REJECT ValueError max_nodes must be a non-negative integer
bound max_raises=0 => REJECT ValueError max_raises must be positive
bound max_raises=-1 => REJECT ValueError max_raises must be a non-negative integer
bound max_raises=1.5 => REJECT ValueError max_raises must be a non-negative integer
bound max_deals=0 => REJECT ValueError max_deals must be positive
bound max_deals=-1 => REJECT ValueError max_deals must be a non-negative integer
bound max_deals=1.5 => REJECT ValueError max_deals must be a non-negative integer
bound max_nodes=0 => REJECT ValueError max_nodes must be positive
bound max_nodes=-1 => REJECT ValueError max_nodes must be a non-negative integer
bound max_nodes=1.5 => REJECT ValueError max_nodes must be a non-negative integer
bool stack => REJECT ValueError starting stack must be a non-negative integer
nonbool reopen => REJECT ValueError short_all_in_reopens must be boolean
cards (True, 1) => REJECT ValueError cards must be two distinct non-negative integers
cards (0, 0) => REJECT ValueError cards must be two distinct non-negative integers
cards (-1, 2) => REJECT ValueError cards must be two distinct non-negative integers
cards (0, 52) => REJECT ValueError range combos must contain valid cards in 0..51
cards (0,) => REJECT ValueError cards must be two distinct non-negative integers
cards [0, 1] => REJECT ValueError cards must be two distinct non-negative integers
cards ('0', 1) => REJECT ValueError cards must be two distinct non-negative integers
weight True => REJECT ValueError weight must be an exact positive rational
weight 0 => REJECT ValueError weight must be an exact positive rational
weight -1 => REJECT ValueError weight must be an exact positive rational
weight nan => REJECT ValueError weight must be an exact positive rational
weight inf => REJECT ValueError weight must be an exact positive rational
weight 'junk' => REJECT ValueError weight must be an exact positive rational
duplicate normalized combo => REJECT ValueError range combos must be unique within a seat
empty compatible deals => REJECT ValueError ranges produce no compatible deals
product checked before collision => REJECT ValueError candidate product exceeds max_deals
payoff (True, -1) => REJECT ValueError invalid terminal-table entry
payoff (nan, 0) => REJECT ValueError terminal values must be finite exact numbers
payoff (inf, -inf) => REJECT ValueError terminal values must be finite exact numbers
payoff ('junk', 0) => REJECT ValueError terminal values must be finite exact numbers
payoff (1, 1) => REJECT ValueError terminal values must be finite and zero-sum
payoff (0,) => REJECT ValueError terminal values must contain N utilities
ranks (True, 1) => REJECT ValueError invalid showdown-ranks entry
ranks (1.5, 1) => REJECT ValueError invalid showdown-ranks entry
ranks (nan, 1) => REJECT ValueError invalid showdown-ranks entry
odd-chip (False, True) => ACCEPT (False, True)
odd-chip (0.0, 1.0) => ACCEPT (0.0, 1.0)
odd-chip (0, 0) => ValueError odd_chip_order must be a permutation of all seats
odd-chip (0, 2) => ValueError odd_chip_order must be a permutation of all seats
exact payoff (Fraction(1, 3), Fraction(-1, 3)) => ACCEPT mappingproxy({(((0, 1), (2, 3)), ()): (Fraction(1, 3), Fraction(-1, 3))})
exact payoff (0.1, -0.1) => ACCEPT mappingproxy({(((0, 1), (2, 3)), ()): (Fraction(3602879701896397, 36028797018963968), Fraction(-3602879701896397, 36028797018963968))})
exact payoff ('1/3', '-1/3') => ACCEPT mappingproxy({(((0, 1), (2, 3)), ()): (Fraction(1, 3), Fraction(-1, 3))})
exact payoff (10000000000000000000000000000000000000000000000000000000000 => OverflowError integer division result too large for a float
duplicate sizing key => REJECT ValueError duplicate sizing rule key
sizing bool raise_count => REJECT ValueError raise_count must be a non-negative integer
sizing bool cold_callers => REJECT ValueError cold_callers must be a non-negative integer
sizing bool value => REJECT ValueError invalid sizing expression
rule hash/equality => ACCEPT (True, True, 1)
caller sizing dict detached => PASS
rule assignment => FrozenInstanceError cannot assign to field 'raise_count'
expression public item => AttributeError '_FrozenExpression' object has no attribute '__setitem__'
config assignment => FrozenInstanceError cannot assign to field 'max_nodes'
continuation mapping assignment => AttributeError 'mappingproxy' object has no attribute '__setitem__'
backing dict mutation => (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=2), Action(kind='RAISE', amount=6), Action(kind='RAISE', amount=100)) -> (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=2), Action(kind='RAISE', amount=16), Action(kind='RAISE', amount=100)) key_changed True hash_unchanged True equal_new_rule True equal_hash False
expression slot reassignment => ACCEPT None
caller rank/payoff dictionaries detached => PASS
duplicate terminal mapping items => ACCEPT mappingproxy({(((0, 1), (2, 3)), ()): (Fraction(2, 1), Fraction(-2, 1))})
duplicate rank mapping items => ACCEPT mappingproxy({((0, 1), (2, 3)): (2, 1)})
direct bool pot => REJECT ValueError pot must be a non-negative integer
direct bad ledger => REJECT ValueError pot must equal sum(total_contributed)
direct duplicate pending => REJECT ValueError pending must contain unique seats
direct bool pending => REJECT ValueError pending contains an invalid responder
direct actor mismatch => REJECT ValueError acting player must be first pending responder
direct too many raises => REJECT ValueError raise_count exceeds max_raises
direct malformed deal => REJECT ValueError dealt state uses an incompatible private deal
direct bool folded => REJECT ValueError folded must contain booleans
direct chance raise_count => ACCEPT -1
direct chance empty pending => ACCEPT -1
direct chance missing entitlement => ACCEPT -1
direct chance wrong increment => ACCEPT -1
direct chance zero post ledger => ACCEPT -1
direct empty pending consequence => terminal True history () values (Fraction(-1, 1), Fraction(1, 1))
max_nodes chance 1 => REJECT ValueError node bound too small for chance expansion
max_nodes generic tree 2 => REJECT ValueError game exceeds finite node bound
full-tree GameState/NPlayerGameState => ACCEPT (True, True, 4)
depth 1 => REJECT ValueError game exceeds finite depth bound
max_raises suppresses next raise => PASS
deterministic exact blocker mass => PASS ((((0, 1), (4, 5)), Fraction(3, 11)), (((2, 3), (4, 5)), Fraction(6, 11)), (((2, 3), (0, 6)), Fraction(2, 11)))
N 2 call/check steps 2 exact (Fraction(-2, 1), Fraction(2, 1))
N 3 call/check steps 3 exact (Fraction(-2, 1), Fraction(-2, 1), Fraction(4, 1))
N 4 call/check steps 4 exact (Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(6, 1))
N 5 call/check steps 5 exact (Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(8, 1))
N 6 call/check steps 6 exact (Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(10, 1))
N 7 call/check steps 7 exact (Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(12, 1))
N 8 call/check steps 8 exact (Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(14, 1))
N 9 call/check steps 9 exact (Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(-2, 1), Fraction(16, 1))
```

### Probe batch 2 — exact command, exit 0

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python - <<'PY'
from dataclasses import replace, FrozenInstanceError
from fractions import Fraction
from collections.abc import Mapping
from math import isfinite
from poker_solver.nplayer_preflop import *
from poker_solver.preflop import WeightedCombo
from poker_solver.game_structure import ForcedPost
from poker_solver.model import Action, CHANCE, TERMINAL, GameState
from poker_solver.nplayer import NPlayerGameState, collect_nplayer_infosets

def table(values=None):
    return NPlayerPreflopContinuation("terminal-table","C3I1-5","supplied",
        {} if values is None else {(deal, ()):values}, {}, ())
deal=((0,1),(2,3))
def cfg(n=2, **kw):
    d=tuple((2*i,2*i+1) for i in range(n))
    args=dict(version="nplayer-preflop-v1",num_players=n,button=0 if n==2 else n-1,
        starting_stacks=(100,)*n,forced_posts=(ForcedPost(0,"small-blind",1),ForcedPost(1,"big-blind",2)),
        straddle_variant="none",ranges=tuple((WeightedCombo(c,1),) for c in d),sizing_rules=(),
        max_raises=3,max_deals=1,max_nodes=10000,short_all_in_reopens=False,
        continuation=NPlayerPreflopContinuation("showdown-ranks","C3I1-5","supplied",{}, {d:tuple(range(n))},tuple(range(n))))
    args.update(kw)
    return NPlayerPreflopConfig(**args)
def probe(name, fn):
    try:
        value=fn()
        print(name, "=> ACCEPT", repr(value))
        return value
    except Exception as e:
        print(name, "=>", type(e).__name__, str(e))
def reject(name,fn):
    try: fn()
    except (ValueError,TypeError,OverflowError) as e:
        print(name, "=> REJECT", type(e).__name__, str(e)); return
    print(name, "=> UNEXPECTED ACCEPT")


from decimal import Decimal
import sys
base=cfg()
for kind in ("garbage",None,42):
    probe("unknown forced-post kind "+repr(kind),lambda kind=kind:
        create_nplayer_preflop_root(cfg(forced_posts=base.forced_posts+(ForcedPost(0,kind,3),))).street_committed)
for args in ((True,"ante",1),(0,"ante",True),(-1,"ante",1),(2,"ante",1)):
    reject("forced post "+repr(args),lambda args=args:cfg(forced_posts=base.forced_posts+(ForcedPost(*args),)))
for amount in (0,100):
    reject("forced extra ante "+str(amount),lambda amount=amount:cfg(forced_posts=base.forced_posts+(ForcedPost(0,"ante",amount),)))
for order in ((False,True),(0.0,1.0)):
    def leaf(order=order):
        c=cfg(continuation=replace(base.continuation,odd_chip_order=order))
        s=create_nplayer_preflop_root(c).child(Action("DEAL",0))
        return s.child(Action("CALL",2)).child(Action("CHECK")).terminal_values
    probe("odd-chip accepted config reaches leaf "+repr(order),leaf)
for value in (Decimal("NaN"),Decimal("Infinity"),float("nan"),float("inf")):
    def decimal_rule(value=value):
        r=NPlayerPreflopSizingRule("BTN/SB",0,0,"NA",({"unit":"big-blinds","value":value},))
        print("  rule constructed",repr(value))
        s=create_nplayer_preflop_root(cfg(sizing_rules=(r,))).child(Action("DEAL",0))
        return s.legal_actions()
    probe("nonfinite sizing "+repr(value),decimal_rule)

for variant,extra,expected in (
    ("none",(),(3,2,(2,3,4,5,0,1))),
    ("standard",(ForcedPost(2,"straddle",4),),(7,3,(3,4,5,0,1,2))),
    ("double",(ForcedPost(2,"straddle",4),ForcedPost(3,"straddle",8)),(15,4,(4,5,0,1,2,3))),
    ("mississippi",(ForcedPost(5,"straddle",4),),(7,0,(0,1,2,3,4,5))),
):
    c=cfg(6,straddle_variant=variant,forced_posts=base.forced_posts+extra)
    s=create_nplayer_preflop_root(c).child(Action("DEAL",0))
    assert (s.pot,s.current_player(),s.pending)==expected
    assert s==create_nplayer_preflop_root(c).child(Action("DEAL",0))
    print("six-seat straddle",variant,expected,s.legal_actions())
for stacks in ((100,100,4,100,100,100),(100,100,100,8,100,100)):
    variant="standard" if stacks[2]==4 else "double"
    extra=(ForcedPost(2,"straddle",4),) if variant=="standard" else (ForcedPost(2,"straddle",4),ForcedPost(3,"straddle",8))
    s=create_nplayer_preflop_root(cfg(6,starting_stacks=stacks,straddle_variant=variant,forced_posts=base.forced_posts+extra))
    seat=2 if variant=="standard" else 3
    assert seat not in s.pending and not s.can_raise[seat]
    print("all-in posted option excluded",variant,s.pending)
for posts in (
    base.forced_posts+(ForcedPost(0,"ante",1),),
    base.forced_posts+(ForcedPost(0,"ante",1),ForcedPost(1,"ante",2)),
    base.forced_posts+(ForcedPost(0,"ante",100),ForcedPost(1,"ante",100)),
):
    reject("invalid ante arrangement "+repr(posts),lambda posts=posts:cfg(forced_posts=posts))
reject("nonincreasing double",lambda:cfg(6,straddle_variant="double",forced_posts=base.forced_posts+(ForcedPost(2,"straddle",4),ForcedPost(3,"straddle",4))))

# HU SB completion must select BB rule with one cold caller.
r=NPlayerPreflopSizingRule("BB",0,1,"NA",({"unit":"big-blinds","value":3},))
s=create_nplayer_preflop_root(cfg(sizing_rules=(r,))).child(Action("DEAL",0)).child(Action("CALL",2))
assert Action("RAISE",6) in s.legal_actions()
print("SB-completion caller sizing => PASS",s.legal_actions())

# Legal minimum full raises with constant increment 2; no recursive state transition.
count=1050
rules=tuple(NPlayerPreflopSizingRule("BTN/SB" if k%2==0 else "BB",k,0,
    "NA" if k==0 else ("IP" if k%2==0 else "OOP"),({"unit":"big-blinds","value":k+2},))
    for k in range(count))
deepcfg=cfg(starting_stacks=(10000,10000),max_raises=count,max_nodes=100000,sizing_rules=rules)
root=create_nplayer_preflop_root(deepcfg)
s=root.child(Action("DEAL",0))
for k in range(count):
    action=Action("RAISE",2*(k+2))
    assert action in s.legal_actions(), (k,s.legal_actions())
    s=s.child(action)
assert s.raise_count==count and not any(a.kind=="RAISE" for a in s.legal_actions())
terminal=s.child(next(a for a in s.legal_actions() if a.kind=="CALL"))
assert terminal.current_player()==TERMINAL and sum(terminal.terminal_values)==0
print("iterative legal depth",len(terminal.history),"structural decision bound",2+count,
      "python recursion limit",sys.getrecursionlimit())
# Generic collector traverses real full tree in declared action order; no monkeypatch.
probe("deep generic collector structural max_depth",lambda:len(collect_nplayer_infosets(
    root,max_nodes=deepcfg.max_nodes,max_depth=2+2+count)))

PY
```

Exact stdout (initial tool chunk followed by completion chunk):

```text
unknown forced-post kind 'garbage' => ACCEPT (4, 2)
unknown forced-post kind None => ACCEPT (4, 2)
unknown forced-post kind 42 => ACCEPT (4, 2)
forced post (True, 'ante', 1) => REJECT TypeError bool-as-int rejected
forced post (0, 'ante', True) => REJECT TypeError bool-as-int rejected
forced post (-1, 'ante', 1) => REJECT ValueError seat must be non-negative int, got -1
forced post (2, 'ante', 1) => REJECT ValueError forced post references an invalid seat
forced extra ante 0 => REJECT ValueError forced post amount must be positive
forced extra ante 100 => REJECT ValueError cumulative forced posts exceed a starting stack
odd-chip accepted config reaches leaf (False, True) => ValueError odd_chip_order must contain unique non-negative seats
odd-chip accepted config reaches leaf (0.0, 1.0) => ValueError odd_chip_order must contain unique non-negative seats
nonfinite sizing Decimal('NaN') => InvalidOperation [<class 'decimal.InvalidOperation'>]
  rule constructed Decimal('Infinity')
nonfinite sizing Decimal('Infinity') => InvalidOperation [<class 'decimal.InvalidOperation'>]
nonfinite sizing nan => ValueError invalid sizing expression
nonfinite sizing inf => ValueError invalid sizing expression
six-seat straddle none (3, 2, (2, 3, 4, 5, 0, 1)) (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=2), Action(kind='RAISE', amount=100))
six-seat straddle standard (7, 3, (3, 4, 5, 0, 1, 2)) (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=4), Action(kind='RAISE', amount=100))
six-seat straddle double (15, 4, (4, 5, 0, 1, 2, 3)) (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=8), Action(kind='RAISE', amount=100))
six-seat straddle mississippi (7, 0, (0, 1, 2, 3, 4, 5)) (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=4), Action(kind='RAISE', amount=100))
all-in posted option excluded standard (3, 4, 5, 0, 1)
all-in posted option excluded double (4, 5, 0, 1, 2)
invalid ante arrangement (ForcedPost(seat=0, kind='small-blind', amount=1), ForcedPost(seat=1, kind='big-blind', amount=2), ForcedPost(seat=0, kind='ante', amount=1)) => REJECT ValueError antes must be one identical positive ante for every seat
invalid ante arrangement (ForcedPost(seat=0, kind='small-blind', amount=1), ForcedPost(seat=1, kind='big-blind', amount=2), ForcedPost(seat=0, kind='ante', amount=1), ForcedPost(seat=1, kind='ante', amount=2)) => REJECT ValueError antes must be one identical positive ante for every seat
invalid ante arrangement (ForcedPost(seat=0, kind='small-blind', amount=1), ForcedPost(seat=1, kind='big-blind', amount=2), ForcedPost(seat=0, kind='ante', amount=100), ForcedPost(seat=1, kind='ante', amount=100)) => REJECT ValueError cumulative forced posts exceed a starting stack
nonincreasing double => REJECT ValueError straddle amounts must strictly increase
SB-completion caller sizing => PASS (Action(kind='CHECK', amount=0), Action(kind='RAISE', amount=6), Action(kind='RAISE', amount=100))
iterative legal depth 1051 structural decision bound 1052 python recursion limit 1000
deep generic collector structural max_depth => RecursionError maximum recursion depth exceeded in comparison
```

## Completion

Audit work complete at 2026-09-16T05:51:56Z UTC. Candidate remains BLOCKED on B1–B7. Frozen architecture, production, and four test hashes still match after execution. Report and heartbeat are the only intended writes; no fixes or git mutations performed.
