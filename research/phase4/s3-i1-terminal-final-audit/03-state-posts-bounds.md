# CTA3A3 state/posts/bounds final audit

status=COMPLETE_PASS
provider=openai-codex
blocker_count=0
utc=2026-09-16T07:50:49Z

Fresh non-author replacement audit of only the candidate identified by the literal manifest `/home/genomix-node/poker-solver/research/phase4/s3-i1-terminal-final-audit/CANDIDATE_MANIFEST.md`. Initial operations were `pwd`, `test -f` on that literal path, and reading it. Exactly 11 manifest rows were parsed and independently hashed as raw bytes before and after the work; all matched. No candidate, test, manifest, STATE.txt, PROGRESS.md, git metadata or commit was modified. Repository writes are limited to this report and `.hb/CTA3A3`.

Required command: `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_config.py`. It passed; a second invocation captured the raw output below. Probe command: `PYTHONDONTWRITEBYTECODE=1 uv run python /tmp/CTA3A3-probe.py`; exit status 0. Probe source and raw successful output are embedded verbatim below. Temporary probe/evidence/finalization files were deleted and absence checked before writing these artifacts.

Executed checks cover valid direct reconstruction and malformed CHANCE/dealt/terminal states, per-seat conservation, canonical fold-terminal ledger and hand-expected (-1,+1) utilities; strict malformed config rejection; deterministic blocker pruning with exact masses 3/11, 6/11, 2/11 and public float chance probabilities; no/standard/double/Mississippi straddles with dead antes, hand-declared ledgers and pending/actor orders; and exact posted all-in seat exclusion from pending and raise rights. The source uses public `big-blinds` sizing expressions. No private production helper serves as an expected-value oracle.

Full iterative production-child traversal measured:

| Fixture | Nodes | Terminals | Maximum depth (root=0) | Maximum raises | Infosets | CFR iterations |
|---|---:|---:|---:|---:|---:|---:|
| HU high raise | 1532 | 1020 | 256 | 254 | 511 | 1 |
| N=9 bounded | 382 | 253 | 64 | 62 | 128 | 1 |

Both collectors accepted exact measured node/depth budgets and rejected each budget minus one. Both solver instances trained one iteration. Traversal checked ledger conservation at every visited node, exact zero-sum terminal values, finite float returns, and suppression of raises at the configured cap. N=9 deliberately has seven ante-posted all-in seats and two seats with chips; these measurements establish bounded N=9 protocol traversal, not nine simultaneously active betting seats or realistic full-range performance. The HU 254-raise and N=9 62-raise construction patterns were reviewed in historical accepted `research/phase4/s3-i1-repair-audit/02-state-bounds.md`; all evidence here comes from fresh execution against this manifest.

Boundary checks separately show candidate-product max_deals rejection even after blockers reduce compatible deals, root chance-expansion node limits, and full collector limits. Config acceptance at HU max_raises=508 (structural bound 512) and N=9 max_raises=62 (bound 507), plus rejection at 509/63, are construction checks only. The HU 508-raise tree was not traversed. Root construction checks chance expansion, and is not full-tree traversal; collector/solver limits were explicitly supplied. No convergence or unrestricted scalability claim is made.

## Raw hash verification

Before:
```text
6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db  ARCHITECTURE_PHASE4_S3.md  match=True
a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812  src/poker_solver/nplayer_preflop.py  match=True
8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240  src/poker_solver/sizing.py  match=True
bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268  tests/test_nplayer_preflop_config.py  match=True
9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd  tests/test_nplayer_preflop_betting.py  match=True
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py  match=True
1217cf74f1468252fbc7f941621dc57154c910003eb27fbf8947b7bc5a42e289  tests/test_nplayer_preflop_information.py  match=True
2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1  tests/test_sizing.py  match=True
61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11  research/phase4/s3-i1-repair/RED_RECEIPT.md  match=True
36a95b38ec1b6016bc46ca80307b2c9f4119c749fceb51cd822bccaf61965164  research/phase4/s3-i1-spec-reconciliation/RECEIPT.md  match=True
b631cc2b933c314c081a70e6b3aaa669ae15054145301d272e1a18967d68a42a  research/phase4/s3-i1-terminal-ledger-reconciliation/RECEIPT.md  match=True
```
After:
```text
6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db  ARCHITECTURE_PHASE4_S3.md  match=True
a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812  src/poker_solver/nplayer_preflop.py  match=True
8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240  src/poker_solver/sizing.py  match=True
bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268  tests/test_nplayer_preflop_config.py  match=True
9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd  tests/test_nplayer_preflop_betting.py  match=True
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py  match=True
1217cf74f1468252fbc7f941621dc57154c910003eb27fbf8947b7bc5a42e289  tests/test_nplayer_preflop_information.py  match=True
2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1  tests/test_sizing.py  match=True
61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11  research/phase4/s3-i1-repair/RED_RECEIPT.md  match=True
36a95b38ec1b6016bc46ca80307b2c9f4119c749fceb51cd822bccaf61965164  research/phase4/s3-i1-spec-reconciliation/RECEIPT.md  match=True
b631cc2b933c314c081a70e6b3aaa669ae15054145301d272e1a18967d68a42a  research/phase4/s3-i1-terminal-ledger-reconciliation/RECEIPT.md  match=True
```
The independent raw hash operation on both passes was `hashlib.sha256(Path(path).read_bytes()).hexdigest()` for exactly the 11 literal manifest rows, with equality assertions and no path substitution. The before/after output strings also matched exactly.

## Required pytest raw output

```text
...............................                                          [100%]
31 passed in 0.16s
```

## Exact successful production probe source

```python
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from math import isfinite
import hashlib
import poker_solver.nplayer_preflop as production
from poker_solver.nplayer_preflop import NPlayerPreflopConfig as Config, NPlayerPreflopContinuation as Cont, NPlayerPreflopSizingRule as Rule, create_nplayer_preflop_root as root, enumerate_nplayer_preflop_deals as deals
from poker_solver.preflop import WeightedCombo as Combo
from poker_solver.game_structure import ForcedPost as Post
from poker_solver.model import Action, CHANCE, TERMINAL
from poker_solver.nplayer import NPlayerGameState, collect_nplayer_infosets, NPlayerCFRSolver
assert Path(production.__file__).resolve()==Path('/home/genomix-node/poker-solver/src/poker_solver/nplayer_preflop.py')
print('IMPORT',production.__file__,hashlib.sha256(Path(production.__file__).read_bytes()).hexdigest(),flush=True)
def cfg(n=2,k=3):
    deal=tuple((2*i,2*i+1) for i in range(n))
    return Config('nplayer-preflop-v1',n,0 if n==2 else n-1,(100,)*n,(Post(0,'small-blind',1),Post(1,'big-blind',2)),'none',tuple((Combo(c,F(1)),) for c in deal),(),k,1,10000,False,Cont('showdown-ranks','CTA3A3 hand supplied ranks','supplied',{}, {deal:tuple(range(n))},tuple(range(n))))
def reject(label,fn):
    try: fn()
    except ValueError as e: print('REJECT',label,':',e,flush=True)
    else: raise AssertionError('accepted '+label)
def ledger(s):
    assert s.pot==sum(s.total_contributed)
    assert tuple(a+b for a,b in zip(s.remaining,s.total_contributed))==s.config.starting_stacks
    assert all(a<=b for a,b in zip(s.street_committed,s.total_contributed))
c=cfg();r=root(c);d=r.child(Action('DEAL',0));t=d.child(Action('FOLD'))
assert r.current_player()==CHANCE and r.private_deal is None and r.legal_actions()==()
assert d.current_player()==0 and d.pending==(0,1) and d.chance_outcomes()==()
assert t.current_player()==TERMINAL and t.pending==() and t.legal_actions()==() and t.chance_outcomes()==()
assert t.terminal_values==(F(-1),F(1)) and t.returns()==(-1.0,1.0)
for label,s in [('CHANCE',r),('dealt',d),('terminal',t)]:
    assert replace(s)==s and isinstance(s,NPlayerGameState) and s.num_players()==2
    ledger(s)
    print('DIRECT valid',label,'pot',s.pot,'contributions',s.total_contributed,'remaining',s.remaining,'pending',s.pending,'utilities',s.terminal_values)
for label,s,kw in [
 ('chance count',r,dict(raise_count=1)),('chance order',r,dict(pending=(1,0))),
 ('chance rights',r,dict(can_raise=(False,False))),('chance increment',r,dict(last_raise_increment=3)),
 ('chance deal',r,dict(private_deal=d.private_deal)),('chance history',r,dict(history=t.history)),
 ('chance ledger',r,dict(pot=0,street_committed=(0,0),total_contributed=(0,0),remaining=(100,100))),
 ('missing deal',d,dict(private_deal=None)),('incompatible deal',d,dict(private_deal=((4,5),(6,7)))),
 ('wrong actor',d,dict(acting_player=1)),('duplicate pending',d,dict(pending=(0,0))),
 ('bad responder',d,dict(pending=(0,2))),('nonterminal values',d,dict(terminal_values=(F(0),F(0)))),
 ('pot',d,dict(pot=4)),('conservation',d,dict(remaining=(98,98))),
 ('street exceeds total',d,dict(street_committed=(2,2))),('raise bound',d,dict(raise_count=4)),
 ('bool actor',d,dict(acting_player=True)),('nonbool folded',d,dict(folded=(0,False))),
 ('terminal pending',t,dict(pending=(1,))),('terminal missing values',t,dict(terminal_values=None)),
 ('terminal dimension',t,dict(terminal_values=(F(0),))),('terminal sum',t,dict(terminal_values=(F(1),F(1)))),
 ('terminal bool',t,dict(terminal_values=(False,False))),('terminal missing deal',t,dict(private_deal=None))]:
    reject(label,lambda s=s,kw=kw:replace(s,**kw))
for key,values in {'num_players':(True,1,10),'button':(True,-1,2),'max_raises':(True,0,1.5),'max_deals':(False,0,1.5),'max_nodes':(True,0,1.5),'starting_stacks':((0,100),(True,100),(1,100)),'short_all_in_reopens':(1,),'forced_posts':((),),'ranges':(((),c.ranges[1]),),'straddle_variant':('invalid',)}.items():
    for v in values: reject('config '+key+'='+repr(v),lambda key=key,v=v:replace(c,**{key:v}))
# Hand declared order and ledgers: button 4, SB 0, BB 1, antes dead.
base=cfg(5)
ante=tuple(Post(i,'ante',1) for i in range(5))
for variant,extra,street,total,remaining,pending in [
 ('none',(),(1,2,0,0,0),(2,3,1,1,1),(98,97,99,99,99),(2,3,4,0,1)),
 ('standard',(Post(2,'straddle',4),),(1,2,4,0,0),(2,3,5,1,1),(98,97,95,99,99),(3,4,0,1,2)),
 ('double',(Post(2,'straddle',4),Post(3,'straddle',8)),(1,2,4,8,0),(2,3,5,9,1),(98,97,95,91,99),(4,0,1,2,3)),
 ('mississippi',(Post(4,'straddle',4),),(1,2,0,0,4),(2,3,1,1,5),(98,97,99,99,95),(0,1,2,3,4))]:
    pc=replace(base,forced_posts=ante+base.forced_posts+extra,straddle_variant=variant)
    pr=root(pc);pd=pr.child(Action('DEAL',0))
    for s in (pr,pd):
        assert (s.street_committed,s.total_contributed,s.remaining,s.pending)==(street,total,remaining,pending)
        ledger(s)
    assert pd.current_player()==pending[0]
    print('POSTS',variant,'street',street,'total',total,'remaining',remaining,'pot',sum(total),'pending',pending,'actor',pd.current_player())
    if variant=='double':
        ac=replace(pc,starting_stacks=(100,100,5,9,100)); ar=root(ac);ad=ar.child(Action('DEAL',0))
        assert ar.remaining==(98,97,0,0,99) and ar.pending==(4,0,1) and ar.can_raise==(True,True,False,False,True)
        assert ad.current_player()==4 and ad.pending==(4,0,1)
        ledger(ad)
        reject('all-in pending',lambda:replace(ad,pending=(4,0,1,2)))
        reject('all-in raise rights',lambda:replace(ad,can_raise=(True,True,True,False,True)))
        print('EXACT POSTED ALL-IN seats 2,3 excluded; remaining',ar.remaining,'pending',ar.pending,'rights',ar.can_raise)
# Four candidate pairs; the (0,1)/(0,6) pair is blocked. Raw masses 3,6,2.
expected=(((0,1),(4,5)),((2,3),(4,5)),((2,3),(0,6)))
w=replace(c,ranges=((Combo((0,1),F(1)),Combo((2,3),F(2))),(Combo((4,5),F(3)),Combo((0,6),F(1)))),max_deals=4,continuation=Cont('showdown-ranks','CTA3A3 weighted','supplied',{},dict.fromkeys(expected,(1,2)),(0,1)))
e=deals(w);o=root(w).chance_outcomes()
assert e==tuple(zip(expected,(F(3,11),F(6,11),F(2,11)))) and e==deals(w)
assert all(type(p) is F for _,p in e) and sum(p for _,p in e)==1
assert o==tuple((Action('DEAL',i),float(p)) for i,(_,p) in enumerate(e)) and o==root(w).chance_outcomes()
assert all(type(p) is float for _,p in o) and abs(sum(p for _,p in o)-1)<1e-12
assert tuple(root(w).child(a).private_deal for a,_ in o)==expected
print('CHANCE exact',e,'float protocol',o)
reject('product 4 max_deals 3 despite only 3 compatible',lambda:replace(w,max_deals=3))
reject('chance max_nodes 3 for 3 deals',lambda:root(replace(w,max_nodes=3)))
assert len(root(replace(w,max_nodes=4)).chance_outcomes())==3
reject('chance max_nodes 1',lambda:root(replace(c,max_nodes=1)))
assert len(root(replace(c,max_nodes=2)).chance_outcomes())==1
reject('full collector max_nodes 2',lambda:collect_nplayer_infosets(root(replace(c,max_nodes=2)),max_nodes=2))
for n,accepted,rejected in ((2,508,509),(9,62,63)):
    assert cfg(n,accepted).max_raises==accepted
    print('STRUCTURAL config acceptance only N',n,'max_raises',accepted,'bound',2+n+accepted*(n-1))
    reject('structural N'+str(n)+' max_raises '+str(rejected),lambda n=n,rejected=rejected:cfg(n,rejected))
# Known valid construction pattern reviewed in accepted C3I1-2R; fresh execution.
for n,k in ((2,254),(9,62)):
    tc=cfg(n,k)
    labels=('BTN/SB','BB') if n==2 else ('SB','BB')
    rules=tuple(Rule(labels[j%2],j,0,'NA' if j==0 else (('IP' if j%2==0 else 'OOP') if n==2 else ('OOP' if j%2==0 else 'IP')),({'unit':'big-blinds','value':j+2},)) for j in range(k))
    tc=replace(tc,sizing_rules=rules,starting_stacks=(2*k+6,)*2 if n==2 else (2*k+7,)*2+(1,)*7,forced_posts=tc.forced_posts if n==2 else tuple(Post(i,'ante',1) for i in range(n))+tc.forced_posts)
    tr=root(tc); stack=[(tr,0)]; count=leaves=depthmax=raisesmax=0
    while stack:
        s,depth=stack.pop();count+=1;depthmax=max(depthmax,depth);raisesmax=max(raisesmax,s.raise_count)
        ledger(s);assert isinstance(s,NPlayerGameState)
        assert count<=tc.max_nodes and depth<=2+n+k*(n-1)
        if s.current_player()==TERMINAL:
            leaves+=1
            assert sum(s.terminal_values)==0 and all(type(v) is F for v in s.terminal_values)
            assert all(type(v) is float and isfinite(v) for v in s.returns())
        else:
            actions=tuple(a for a,_ in s.chance_outcomes()) if s.current_player()==CHANCE else s.legal_actions()
            if s.raise_count==k: assert all(a.kind!='RAISE' for a in actions)
            stack.extend((s.child(a),depth+1) for a in actions)
    assert raisesmax==k
    infos=collect_nplayer_infosets(tr,max_nodes=count,max_depth=depthmax)
    reject('N'+str(n)+' max_nodes actual minus one',lambda:collect_nplayer_infosets(tr,max_nodes=count-1,max_depth=depthmax))
    reject('N'+str(n)+' max_depth actual minus one',lambda:collect_nplayer_infosets(tr,max_nodes=count,max_depth=depthmax-1))
    solver=NPlayerCFRSolver(tr,max_nodes=count,max_depth=depthmax);solver.train(1);assert solver.iterations==1
    print('TRAVERSED N',n,'nodes',count,'terminals',leaves,'depth',depthmax,'raises',raisesmax,'infosets',len(infos),'CFR_iterations',solver.iterations,flush=True)
print('COMPLETE_PASS blockers=0',flush=True)
```

## Exact successful production probe raw output

```text
IMPORT /home/genomix-node/poker-solver/src/poker_solver/nplayer_preflop.py a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812
DIRECT valid CHANCE pot 3 contributions (1, 2) remaining (99, 98) pending (0, 1) utilities None
DIRECT valid dealt pot 3 contributions (1, 2) remaining (99, 98) pending (0, 1) utilities None
DIRECT valid terminal pot 2 contributions (1, 1) remaining (99, 99) pending () utilities (Fraction(-1, 1), Fraction(1, 1))
REJECT chance count : chance root violates root invariants
REJECT chance order : chance root violates root invariants
REJECT chance rights : chance root violates root invariants
REJECT chance increment : chance root violates root invariants
REJECT chance deal : invalid chance root
REJECT chance history : invalid chance root
REJECT chance ledger : chance root violates root invariants
REJECT missing deal : dealt state requires a private deal
REJECT incompatible deal : dealt state uses an incompatible private deal
REJECT wrong actor : acting player must be first pending responder
REJECT duplicate pending : pending must contain unique seats
REJECT bad responder : pending contains an invalid responder
REJECT nonterminal values : nonterminal state cannot contain utilities
REJECT pot : pot must equal sum(total_contributed)
REJECT conservation : remaining plus contribution must equal starting stack
REJECT street exceeds total : street commitment cannot exceed total contribution
REJECT raise bound : raise_count exceeds max_raises
REJECT bool actor : invalid acting player
REJECT nonbool folded : folded must contain booleans
REJECT terminal pending : terminal state must have empty pending
REJECT terminal missing values : terminal state requires N utilities
REJECT terminal dimension : terminal state requires N utilities
REJECT terminal sum : terminal utilities must be finite and zero-sum
REJECT terminal bool : terminal utilities must be exact numbers
REJECT terminal missing deal : dealt state requires a private deal
REJECT config num_players=True : num_players must be an integer from 2 to 9
REJECT config num_players=1 : num_players must be an integer from 2 to 9
REJECT config num_players=10 : num_players must be an integer from 2 to 9
REJECT config button=True : button must be a valid integer seat
REJECT config button=-1 : button must be a valid integer seat
REJECT config button=2 : button must be a valid integer seat
REJECT config max_raises=True : max_raises must be a non-negative integer
REJECT config max_raises=0 : max_raises must be positive
REJECT config max_raises=1.5 : max_raises must be a non-negative integer
REJECT config max_deals=False : max_deals must be a non-negative integer
REJECT config max_deals=0 : max_deals must be positive
REJECT config max_deals=1.5 : max_deals must be a non-negative integer
REJECT config max_nodes=True : max_nodes must be a non-negative integer
REJECT config max_nodes=0 : max_nodes must be positive
REJECT config max_nodes=1.5 : max_nodes must be a non-negative integer
REJECT config starting_stacks=(0, 100) : starting stack must be positive
REJECT config starting_stacks=(True, 100) : starting stack must be a non-negative integer
REJECT config starting_stacks=(1, 100) : at least two seats must have chips after forced posts
REJECT config short_all_in_reopens=1 : short_all_in_reopens must be boolean
REJECT config forced_posts=() : exactly one small blind is required on the derived SB seat
REJECT config ranges=((), (WeightedCombo(cards=(2, 3), weight=Fraction(1, 1)),)) : each range must be a non-empty tuple
REJECT config straddle_variant='invalid' : invalid straddle_variant
POSTS none street (1, 2, 0, 0, 0) total (2, 3, 1, 1, 1) remaining (98, 97, 99, 99, 99) pot 8 pending (2, 3, 4, 0, 1) actor 2
POSTS standard street (1, 2, 4, 0, 0) total (2, 3, 5, 1, 1) remaining (98, 97, 95, 99, 99) pot 12 pending (3, 4, 0, 1, 2) actor 3
POSTS double street (1, 2, 4, 8, 0) total (2, 3, 5, 9, 1) remaining (98, 97, 95, 91, 99) pot 20 pending (4, 0, 1, 2, 3) actor 4
REJECT all-in pending : pending contains an invalid responder
REJECT all-in raise rights : folded or all-in seats cannot raise
EXACT POSTED ALL-IN seats 2,3 excluded; remaining (98, 97, 0, 0, 99) pending (4, 0, 1) rights (True, True, False, False, True)
POSTS mississippi street (1, 2, 0, 0, 4) total (2, 3, 1, 1, 5) remaining (98, 97, 99, 99, 95) pot 12 pending (0, 1, 2, 3, 4) actor 0
CHANCE exact ((((0, 1), (4, 5)), Fraction(3, 11)), (((2, 3), (4, 5)), Fraction(6, 11)), (((2, 3), (0, 6)), Fraction(2, 11))) float protocol ((Action(kind='DEAL', amount=0), 0.2727272727272727), (Action(kind='DEAL', amount=1), 0.5454545454545454), (Action(kind='DEAL', amount=2), 0.18181818181818182))
REJECT product 4 max_deals 3 despite only 3 compatible : candidate product exceeds max_deals
REJECT chance max_nodes 3 for 3 deals : node bound too small for chance expansion
REJECT chance max_nodes 1 : node bound too small for chance expansion
REJECT full collector max_nodes 2 : game exceeds finite node bound
STRUCTURAL config acceptance only N 2 max_raises 508 bound 512
REJECT structural N2 max_raises 509 : max_raises exceeds the supported structural depth bound
STRUCTURAL config acceptance only N 9 max_raises 62 bound 507
REJECT structural N9 max_raises 63 : max_raises exceeds the supported structural depth bound
REJECT N2 max_nodes actual minus one : game exceeds finite node bound
REJECT N2 max_depth actual minus one : game exceeds finite depth bound
TRAVERSED N 2 nodes 1532 terminals 1020 depth 256 raises 254 infosets 511 CFR_iterations 1
REJECT N9 max_nodes actual minus one : game exceeds finite node bound
REJECT N9 max_depth actual minus one : game exceeds finite depth bound
TRAVERSED N 9 nodes 382 terminals 253 depth 64 raises 62 infosets 128 CFR_iterations 1
COMPLETE_PASS blockers=0
```
