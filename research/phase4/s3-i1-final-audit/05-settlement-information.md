# FC3I1-5 settlement and information final audit

status=COMPLETE_BLOCKED
provider=openai-codex
auditor=FC3I1-5
blocker_count=1
production_sha256=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812
architecture_sha256=15b378ac224460ee8064e3c54f5925d3721d4ca38e4529cf84b7e82858975a78

Fresh non-author audit of research/phase4/s3-i1-final-audit/CANDIDATE_MANIFEST.md. All commands executed with cwd /home/genomix-node/poker-solver. Candidate files, tests, receipts, manifest, STATE.txt, PROGRESS.md, and git were not edited. Only this report and .hb/FC3I1-5 are durable writes. Two temporary Python probes were created in /tmp and removed in finally blocks. No commit.

## Verdict: one reproducible architecture/projection blocker

B1: the final architecture still requires ledger projection agreement on a valid frozen equal-stack fold fixture, while section 8 requires a different terminal ledger representation. This is a specification conflict, not a demonstrated settlement arithmetic defect.

Exact fixture from tests/test_nplayer_preflop_information.py:110: stacks=(20,20), posts=(1,2), button=0, four uniform disjoint deals, sizing 3 BB/all-in, max_raises=2; DEAL 0, RAISE 6, FOLD. Both decision prefixes have identical actors, ordered actions, and ledgers. Both engines terminate with exact utilities (2,-2). However:

| Terminal field | Legacy | Candidate |
|---|---|---|
| pot | 8 | 4 |
| street commitment | (6,2) | (2,2) |
| total contribution | (6,2) | (2,2) |
| remaining | (14,18) | (18,18) |

The candidate correctly refunds four unmatched chips. Legacy preflop.py:269 leaves the fold ledger unchanged. Architecture line 9 explicitly includes pot, street commitments, total contributions and remaining stacks in the comparison; line 298 requires projected ledgers/terminals for frozen fixtures. Neither specifies terminal refund normalization or limits ledger comparison to decision states. Section 8, line 198, requires refund before every terminal. This equal-stack fold is a valid terminal in both engines and is not the excluded unequal-stack chipless-responder suffix.

The permanent fold projection test checks initial ledgers and terminal returns, but does not compare terminal ledgers. The previous C3I1-5R report explicitly noted this difference while limiting its ledger comparison to nonterminals. The reconciliation receipt resolves the chipless suffix but does not resolve this remaining fold-terminal projection requirement. The independent expanded HU traversal also found 45 terminal ledger differences among 90 leaves, with all terminal utilities matching.

Parent resolution needed: explicitly define terminal-ledger normalization in the projection, or explicitly scope raw ledger comparison to aligned decision states and compare terminal utilities. Preserve section 8 refund behavior and unchanged legacy source. This auditor made no candidate changes.

## Executed passing evidence

Read the full architecture, full production nplayer_preflop.py and legacy preflop.py, full settlement and information suites, reconciliation receipt, and prior C3I1-5R report (including its recorded probes). Overlapping reads recovered truncated tool output.

Required command:
```sh
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py
```
Result: 14 passed in 0.31s, exit 0.

Independent probe 1, exit 0:
- A chip-by-chip contributor-set oracle independently computes refunds, pot bands, eligible winners, ties, odd chips and exact Fraction utilities; it imports no production settlement helper.
- Named fold: refund (38,0,0), matched (2,1,2), awards (5,0,0), utilities (3,-1,-2).
- Three distinct side-pot winners: layers/awards 40/60/40, matched (10,30,50,50), utilities (30,30,-10,-50).
- Tie odd-chip order (0,1,2) gives (2,1,-3); order (1,0,2) gives (1,2,-3).
- Short call: refund (0,13), matched (7,7), utilities (7,-7).
- Complete selected tiny trees: N=3 has 11 decision nodes / 13 terminal checks; N=6 has 297 / 315; N=9 has 6,309 / 6,487. Total 6,815 terminal oracles. All checked states conserve pot and starting stacks, and all checked terminal utilities are exact zero-sum rationals.
- Exact terminal-table values (7/3,-7/3) returned once; missing keys, actor-mismatched keys and nonzero-sum values rejected.
- N=6 and N=9 information checks reach every acting seat on limp/check paths; 30 and 72 individual opponent-card mutations preserve keys and ordered actions. Hidden ranks and hidden table-value mutations also preserve both. Owner-card mutation changes the key; public raise-entitlement mutation changes key and actions.
- Weighted HU blocker ranges normalize exactly to (3/13,4/13,6/13), matching legacy exact masses and candidate float projection. Complete selected equal-stack HU tree: 48 aligned decisions, 90 equal terminal utility vectors, 4,608 pairwise information-partition comparisons. Actors, ordered actions, deals, action-projected histories and decision ledgers agree. Terminal ledger exceptions are B1 above.
- Named CALL2-CHECK, RAISE6-CALL6 and RAISE6-RAISE18-CALL18 have matching terminal ledgers and exact supplied (5/7,-5/7). RAISE6-FOLD has matching (2,-2) utilities and the reproducible terminal ledger difference.
- Unequal stacks=(20,7), CALL2-RAISE7-RAISE20: every preceding actor/action/ledger aligns. Legacy ends actionable at seat 1 with remaining=(0,0), legal (FOLD,CALL7). Candidate closes, pending=(), refunds 13, pot=14, street=total=(7,7), remaining=(13,0), utility=(7,-7). Checked separately with showdown-ranks and exact terminal-table continuations.

Independent probe 2 reproduced B1 using the exact existing four-deal frozen fold fixture, without importing test helpers:
```text
EXACT FROZEN FIXTURE: RAISE6 FOLD
legacy: -2 8 (6, 2) (6, 2) (14, 18) (Fraction(2, 1), Fraction(-2, 1))
candidate: -2 4 (2, 2) (2, 2) (18, 18) (Fraction(2, 1), Fraction(-2, 1))
B1 reproduced: both valid terminals; raw terminal ledger projection differs.
TEMP_DELETED True
```

The prior unequal-stack blocker is resolved by the explicit domain exclusion in architecture sections 1 and 13 and the permanent regression at information.py:304. Candidate closure/refund obeys sections 7–8. Legacy source is byte-identical to both HEAD and the Phase-3 baseline. The remaining B1 concerns a valid equal-stack fixture, not that resolved exclusion.

No full regression, solve/API/CFR audit, or universal configuration coverage is claimed.

## Before/after integrity

All 10 manifest rows were SHA-256 checked before source/test audit and again after both independent probes. All matched on both passes. Manifest itself retained SHA-256 9e7e12f1cdfdbc66bc39ca051229486486255da61b8ea3f56f8290f2f0e9e9da. Final verification output:
```text
PASS 15b378ac224460ee8064e3c54f5925d3721d4ca38e4529cf84b7e82858975a78 ARCHITECTURE_PHASE4_S3.md
PASS a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812 src/poker_solver/nplayer_preflop.py
PASS 8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240 src/poker_solver/sizing.py
PASS bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268 tests/test_nplayer_preflop_config.py
PASS 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd tests/test_nplayer_preflop_betting.py
PASS e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3 tests/test_nplayer_preflop_settlement.py
PASS 49cf12eb1bd514a4bcaad4bae896f4a143407ceff71928cdaf5e8f05395e2e84 tests/test_nplayer_preflop_information.py
PASS 2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1 tests/test_sizing.py
PASS 61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11 research/phase4/s3-i1-repair/RED_RECEIPT.md
PASS 36a95b38ec1b6016bc46ca80307b2c9f4119c749fceb51cd822bccaf61965164 research/phase4/s3-i1-spec-reconciliation/RECEIPT.md
MANIFEST UNCHANGED 9e7e12f1cdfdbc66bc39ca051229486486255da61b8ea3f56f8290f2f0e9e9da
legacy equals HEAD 89dd56b291b138064e744f73e54af3aef38f5c36a439a6767d8f61fff755e8d2
legacy equals feba8222a0b614b0c64eca59402403ce733195ea 89dd56b291b138064e744f73e54af3aef38f5c36a439a6767d8f61fff755e8d2
HEAD 65d411793d1d7767d86500d0adffe9f40b379108
phase3-398-green feba8222a0b614b0c64eca59402403ce733195ea
TEMP FILES REMAIN: []
```

## Reproducible temporary probes

Each source below was run from the repository cwd using uv run python with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=/home/genomix-node/poker-solver/src. To reproduce without repository writes, put the source into a tempfile.NamedTemporaryFile in /tmp, run it with subprocess.run, and unlink in a finally block. First actual temporary path: /tmp/FC3I1-5-1zc0ytkv.py. Both wrappers confirmed deletion; final glob found no FC3I1-5-*.py files. Probe 1 exits 0 after asserting the listed checks and recording B1; it does not treat recorded ledger mismatches as arithmetic assertion failures.

### Probe 1 source
```python
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from poker_solver.nplayer_preflop import *
from poker_solver.preflop import PreflopConfig, Continuation, WeightedCombo, create_preflop_root
from poker_solver.game_structure import ForcedPost
from poker_solver.model import Action as A, TERMINAL

def config(n, stacks=None, ranks=None, ante=0, button=None):
    b=(0 if n==2 else n-1) if button is None else button
    sb=b if n==2 else (b+1)%n
    bb=(b+1)%n if n==2 else (b+2)%n
    d=tuple((2*i,2*i+1) for i in range(n))
    return NPlayerPreflopConfig('nplayer-preflop-v1',n,b,stacks or (40,)*n,
        tuple(ForcedPost(i,'ante',ante) for i in range(n) if ante)+
        (ForcedPost(sb,'small-blind',1),ForcedPost(bb,'big-blind',2)),
        'none',tuple((WeightedCombo(c,F(1)),) for c in d),(),3,16,100000,False,
        NPlayerPreflopContinuation('showdown-ranks','FC3I1-5','supplied',{},
        {d:ranks or tuple(range(n))},tuple(range(n))))
def start(c): return create_nplayer_preflop_root(c).child(A('DEAL',0))
def ledger(s):
    assert s.pot==sum(s.total_contributed)
    assert tuple(x+y for x,y in zip(s.remaining,s.total_contributed))==s.config.starting_stacks
    assert all(0<=x<=y for x,y in zip(s.street_committed,s.total_contributed))
def settle_oracle(s,a,t):
    raw=list(s.total_contributed); street=list(s.street_committed); folded=list(s.folded)
    p=s.current_player()
    if a.kind in ('CALL','RAISE'):
        raw[p]+=a.amount-street[p];street[p]=a.amount
    if a.kind=='FOLD':folded[p]=True
    # One chip per contributor per height; combine equal contributor sets for odd-chip allocation.
    cap=sorted(raw)[-2]
    matched=tuple(min(x,cap) for x in raw)
    refunds=tuple(x-y for x,y in zip(raw,matched))
    bands={}
    for height in range(1,cap+1):
        seats=tuple(i for i,c in enumerate(matched) if c>=height)
        bands[seats]=bands.get(seats,0)+len(seats)
    awards=[0]*len(raw)
    ranks=s.config.continuation.showdown_ranks[s.private_deal]
    for seats,amount in bands.items():
        eligible=[i for i in seats if not folded[i]]
        best=max(ranks[i] for i in eligible)
        winners=[i for i in s.config.continuation.odd_chip_order if i in eligible and ranks[i]==best]
        q,r=divmod(amount,len(winners))
        for j,i in enumerate(winners):awards[i]+=q+(j<r)
    expected=tuple(F(a-c) for a,c in zip(awards,matched))
    assert t.total_contributed==matched
    assert t.street_committed==tuple(x-r for x,r in zip(street,refunds))
    assert t.terminal_values==expected
    assert sum(expected)==0 and all(isinstance(v,F) for v in t.terminal_values)
    assert sum(x+v for x,v in zip(t.config.starting_stacks,expected))==sum(t.config.starting_stacks)
    ledger(t)
    return refunds,awards
def trace(c,actions,label):
    s=start(c)
    for a in actions:
        ledger(s);t=s.child(a)
        if t.current_player()==TERMINAL:details=settle_oracle(s,a,t)
        s=t
    assert s.current_player()==TERMINAL
    print(label,'refund/awards',details,'matched',s.total_contributed,'utilities',s.terminal_values)
trace(config(3,button=0),[A('RAISE',40),A('FOLD'),A('FOLD')],'fold refund')
trace(config(4,(10,30,50,100),(9,7,5,1),button=1),
      [A('RAISE',10),A('RAISE',30),A('RAISE',50),A('CALL',50)],'three distinct side-pot winners')
for order in ((0,1,2),(1,0,2)):
    c=config(3,ranks=(9,9,1),ante=1,button=0)
    c=replace(c,continuation=replace(c.continuation,odd_chip_order=order))
    trace(c,[A('CALL',2),A('CALL',2),A('CHECK')],'tie '+str(order))
trace(config(2,(7,20),(9,1)),[A('CALL',2),A('RAISE',20),A('CALL',7)],'short call')
for n in (3,6,9):
    counts=[0,0]
    def walk(s):
        ledger(s);counts[0]+=1
        for a in s.legal_actions():
            t=s.child(a)
            if t.current_player()==TERMINAL:settle_oracle(s,a,t);counts[1]+=1
            else:walk(t)
    walk(start(config(n,tuple(3+i%3 for i in range(n)),tuple(i%3 for i in range(n)),ante=1)))
    print('exhaustive N',n,'decisions/terminals',counts)

for n in (6,9):
    c=config(n);s=start(c);owners=[];mutations=0
    while s.current_player()!=TERMINAL:
        p=s.current_player();owners.append(p);key=s.information_state_key(p);actions=s.legal_actions()
        for q in range(n):
            if q==p:continue
            d=list(s.private_deal);d[q]=(48,49);d=tuple(d)
            cc=replace(c,ranges=tuple((WeightedCombo(x,F(1)),) for x in d),
                continuation=replace(c.continuation,showdown_ranks={d:tuple(reversed(range(n)))}))
            changed=replace(s,config=cc,private_deal=d)
            assert changed.information_state_key(p)==key and changed.legal_actions()==actions
            mutations+=1
        hidden=replace(s,config=replace(c,continuation=replace(c.continuation,
            showdown_ranks={s.private_deal:(77,)*n})))
        assert hidden.information_state_key(p)==key and hidden.legal_actions()==actions
        d=list(s.private_deal);d[p]=(46,47);d=tuple(d)
        cc=replace(c,ranges=tuple((WeightedCombo(x,F(1)),) for x in d),
            continuation=replace(c.continuation,showdown_ranks={d:tuple(range(n))}))
        assert replace(s,config=cc,private_deal=d).information_state_key(p)!=key
        rights=replace(s,can_raise=tuple(False if i==p else v for i,v in enumerate(s.can_raise)))
        assert rights.information_state_key(p)!=key and rights.legal_actions()!=actions
        values=(F(2,7),F(-2,7))+(F(0),)*(n-2);tk=(s.private_deal,s.history)
        cont=NPlayerPreflopContinuation('terminal-table','same','supplied',{tk:values},{},())
        one=replace(s,config=replace(c,continuation=cont))
        two=replace(one,config=replace(c,continuation=replace(cont,payoff_table={tk:tuple(-x for x in values)})))
        assert one.information_state_key(p)==two.information_state_key(p)
        assert one.legal_actions()==two.legal_actions()==actions
        s=s.child(next(a for a in actions if a.kind in ('CALL','CHECK')))
    assert set(owners)==set(range(n))
    print('information N',n,'owners',owners,'opponent mutations',mutations,'ranks/table/owner/public PASS')

c=config(2);d=start(c).private_deal
h=(NPlayerPreflopPublicAction(0,A('CALL',2)),NPlayerPreflopPublicAction(1,A('CHECK')))
v=(F(7,3),F(-7,3))
cont=NPlayerPreflopContinuation('terminal-table','rational','supplied',{(d,h):v},{},())
t=start(replace(c,continuation=cont)).child(A('CALL',2)).child(A('CHECK'))
assert t.terminal_values==v;ledger(t)
for table in ({},{(d,tuple(NPlayerPreflopPublicAction(1-x.actor,x.action) for x in h)):v}):
    try:start(replace(c,continuation=replace(cont,payoff_table=table))).child(A('CALL',2)).child(A('CHECK'))
    except ValueError:pass
    else:raise AssertionError('missing/wrong actor key accepted')
try:replace(cont,payoff_table={(d,h):(F(1),F(1))})
except ValueError:pass
else:raise AssertionError('nonzero table accepted')
print('exact table',v,'missing/actor/nonzero rejection PASS')

# Complete equal-stack tree with independently assigned complete-hand rational values.
expr=({'unit':'big-blinds','value':3},{'unit':'big-blinds','value':9},{'unit':'all-in'})
rules=tuple(NPlayerPreflopSizingRule(p,r,k,rel,expr)
    for p,r,k,rel in product(('BTN/SB','BB'),range(3),range(2),('NA','IP','OOP')))
ranges=((WeightedCombo((0,1),F(1,3)),WeightedCombo((2,3),F(2,3))),
        (WeightedCombo((0,4),F(2,5)),WeightedCombo((6,7),F(3,5))))
nc=replace(config(2),starting_stacks=(20,20),ranges=ranges,sizing_rules=rules,
    continuation=NPlayerPreflopContinuation('terminal-table','HU','supplied',{}, {},()))
deals=enumerate_nplayer_preflop_deals(nc)
assert tuple(m for _,m in deals)==(F(3,13),F(4,13),F(6,13))
rc=replace(nc,continuation=NPlayerPreflopContinuation('showdown-ranks','HU','supplied',{},
    {d:(1,2) for d,_ in deals},(0,1)))
table={}
def collect(s):
    if s.current_player()==TERMINAL:
        if not any(s.folded):table[(s.private_deal,s.history)]=(F(5,7),F(-5,7))
        return
    for a in s.legal_actions():collect(s.child(a))
for a,_ in create_nplayer_preflop_root(rc).chance_outcomes():collect(create_nplayer_preflop_root(rc).child(a))
nc=replace(nc,continuation=replace(nc.continuation,payoff_table=table))
lc=PreflopConfig((20,20),(1,2),ranges,expr,3,16,100000,False,
    Continuation('terminal-table',{(d,tuple(x.action for x in h)):v for (d,h),v in table.items()},'HU'))
lr=create_preflop_root(lc);nr=create_nplayer_preflop_root(nc)
assert tuple(m for _,m in lr.chance_outcomes())==tuple(m for _,m in deals)
assert nr.chance_outcomes()==tuple((a,float(m)) for a,m in lr.chance_outcomes())
pairs=[];terminal_count=0;fold_differences=[]
def projected_ledger(l,r):
    return (l.pot,l.committed,l.total_contributed,l.remaining)==(r.pot,r.street_committed,r.total_contributed,r.remaining)
def compare(l,r):
    global terminal_count
    assert l.current_player()==r.current_player()
    assert l.private_deal==r.private_deal
    assert l.history==tuple(x.action for x in r.history)
    assert l.legal_actions()==r.legal_actions()
    if l.current_player()==TERMINAL:
        assert l.terminal_values==r.terminal_values;terminal_count+=1
        if not projected_ledger(l,r):fold_differences.append(l.history)
        else:assert not any(r.folded)
        return
    assert projected_ledger(l,r) and not any(r.folded)
    pairs.append((l,r))
    for a in l.legal_actions():compare(l.child(a),r.child(a))
for a,_ in lr.chance_outcomes():compare(lr.child(a),nr.child(a))
for p in (0,1):
    left=[l.information_state_key(p) for l,r in pairs]
    right=[r.information_state_key(p) for l,r in pairs]
    assert all((a==b)==(c==d) for a,c in zip(left,right) for b,d in zip(left,right))
print('HU decisions',len(pairs),'terminal utilities',terminal_count,'partition comparisons',2*len(pairs)**2,
      'terminal ledger differences',len(fold_differences))
for path in ((A('CALL',2),A('CHECK')),(A('RAISE',6),A('CALL',6)),
             (A('RAISE',6),A('RAISE',18),A('CALL',18)),(A('RAISE',6),A('FOLD'))):
    l=lr.child(A('DEAL',0));r=nr.child(A('DEAL',0))
    for a in path:
        assert projected_ledger(l,r) and l.legal_actions()==r.legal_actions()
        l=l.child(a);r=r.child(a)
    assert l.current_player()==r.current_player()==TERMINAL
    assert l.terminal_values==r.terminal_values
    print('named HU',path,'values',r.terminal_values,'legacy ledger',
        (l.pot,l.committed,l.total_contributed,l.remaining),'new ledger',
        (r.pot,r.street_committed,r.total_contributed,r.remaining))
# Known reconciled exception, both continuations exercised independently.
path=(A('CALL',2),A('RAISE',7),A('RAISE',20))
c=replace(config(2,(20,7),(9,1)),sizing_rules=rules)
d=start(c).private_deal;h=tuple(NPlayerPreflopPublicAction(i%2,a) for i,a in enumerate(path))
lc=PreflopConfig((20,7),(1,2),c.ranges,expr,3,16,100000,False,
    Continuation('terminal-table',{(d,path):(F(7),F(-7))},'edge'))
for continuation in (c.continuation,NPlayerPreflopContinuation('terminal-table','edge','supplied',
        {(d,h):(F(7),F(-7))},{},())):
    l=create_preflop_root(lc).child(A('DEAL',0));r=start(replace(c,continuation=continuation))
    for a in path:
        assert l.current_player()==r.current_player()
        assert l.legal_actions()==r.legal_actions() and projected_ledger(l,r)
        l=l.child(a);r=r.child(a)
    assert l.current_player()==1 and l.remaining==(0,0)
    assert l.legal_actions()==(A('FOLD'),A('CALL',7))
    assert r.current_player()==TERMINAL and r.pending==()
    assert (r.pot,r.street_committed,r.total_contributed,r.remaining)==(14,(7,7),(7,7),(13,0))
    assert r.terminal_values==(F(7),F(-7))
    print('unequal regression',continuation.kind,'PASS legacy actor',l.current_player(),
        'new terminal/refund13/utilities',r.terminal_values)
print('PROBE COMPLETE; reproducible specification issue: valid equal-stack fold terminal ledger projection')
```

### Probe 2 source
```python
from fractions import Fraction as F
from poker_solver.model import Action as A, TERMINAL
from poker_solver.game_structure import ForcedPost
from poker_solver.preflop import WeightedCombo, PreflopConfig, Continuation, create_preflop_root
from poker_solver.nplayer_preflop import NPlayerPreflopConfig, NPlayerPreflopContinuation, NPlayerPreflopSizingRule, create_nplayer_preflop_root
ranges=tuple(tuple(WeightedCombo(c,F(1)) for c in seat) for seat in (((0,1),(2,3)),((4,5),(6,7))))
expr=({'unit':'big-blinds','value':3},{'unit':'all-in'})
old=PreflopConfig((20,20),(1,2),ranges,expr,2,4,1000,False,Continuation('terminal-table',{},'hu-projection'))
new=NPlayerPreflopConfig('nplayer-preflop-v1',2,0,(20,20),
    (ForcedPost(0,'small-blind',1),ForcedPost(1,'big-blind',2)),
    'none',ranges,(NPlayerPreflopSizingRule('BTN/SB',0,0,'NA',expr),),
    2,4,1000,False,NPlayerPreflopContinuation('terminal-table','hu-projection','supplied',{}, {},()))
l=create_preflop_root(old).child(A('DEAL',0));r=create_nplayer_preflop_root(new).child(A('DEAL',0))
for a in (A('RAISE',6),A('FOLD')):
    assert l.current_player()==r.current_player()
    assert l.legal_actions()==r.legal_actions()
    assert (l.pot,l.committed,l.total_contributed,l.remaining)==(r.pot,r.street_committed,r.total_contributed,r.remaining)
    l=l.child(a);r=r.child(a)
assert l.current_player()==r.current_player()==TERMINAL
assert l.terminal_values==r.terminal_values==(F(2),F(-2))
assert (l.pot,l.committed,l.total_contributed,l.remaining)==(8,(6,2),(6,2),(14,18))
assert (r.pot,r.street_committed,r.total_contributed,r.remaining)==(4,(2,2),(2,2),(18,18))
print('EXACT FROZEN FIXTURE: RAISE6 FOLD')
print('legacy:',l.current_player(),l.pot,l.committed,l.total_contributed,l.remaining,l.terminal_values)
print('candidate:',r.current_player(),r.pot,r.street_committed,r.total_contributed,r.remaining,r.terminal_values)
print('B1 reproduced: both valid terminals; raw terminal ledger projection differs.')
```

completed_utc=2026-09-16T07:00:17Z
