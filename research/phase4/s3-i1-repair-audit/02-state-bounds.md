# C3I1-2R state and bounds audit

status=COMPLETE_PASS
provider=openai-codex
production_sha256=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812
blocker_count=0
utc=2026-09-16T06:38:00Z

This fresh non-author audit replaces the invalid/nonexistent R3A2 report. Scope: frozen S3-I1 state/config/chance/bounds implementation. No candidate files, tests, manifest, STATE, PROGRESS, or git were edited; no commit was made. The only repository writes for this audit are this report and `.hb/C3I1-2R`. The temporary production-importing probe was created outside the repository at `/tmp/c3i1-2r-19h5nokc/probe.py`, executed with bytecode disabled, and its directory was deleted and absence verified before these artifacts were written.

Read: `ARCHITECTURE_PHASE4_S3.md`, all of `src/poker_solver/nplayer_preflop.py`, `src/poker_solver/nplayer.py`, and `tests/test_nplayer_preflop_config.py`.

## Manifest verification

All nine literal manifest rows were checked before source inspection/testing and rechecked after the probe. Both checks matched. Final executed verification:

```text
PASS a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6  ARCHITECTURE_PHASE4_S3.md
PASS a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812  src/poker_solver/nplayer_preflop.py
PASS 8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240  src/poker_solver/sizing.py
PASS bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268  tests/test_nplayer_preflop_config.py
PASS 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd  tests/test_nplayer_preflop_betting.py
PASS e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
PASS 0d800d2f8fe797f29d8a347e1ab216bbc079fee0ede792ab253db23097819445  tests/test_nplayer_preflop_information.py
PASS 2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1  tests/test_sizing.py
PASS 61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11  research/phase4/s3-i1-repair/RED_RECEIPT.md
MANIFEST: 9/9 PASS
```

## Required test execution

Command (environment disables bytecode writes):

```sh
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_config.py
```

Exit 0; actual output:

```text
...............................                                          [100%]
31 passed in 0.07s
```

## Probe assessment

The probe checks `isinstance(state, NPlayerGameState)` at CHANCE, dealt, terminal, and every manually traversed node. Twenty-five `dataclasses.replace` invalid-state cases were rejected. Exact enumerator masses are Fractions 3/11, 6/11, 2/11 in independently specified blocker-pruned range order. Protocol chance probabilities are floats, explicitly type-checked and compared to float conversions of those exact masses; their sum was 1.0, within the protocol tolerance. Repeated enumeration, repeated chance outcomes, action indices, and action-to-deal mapping matched. The permanent test's numerical comparison against Fraction(1) does not establish a Fraction return type; this audit verifies the actual float contract separately.

Rejections cover candidate-product `max_deals`, root chance-expansion `max_nodes`, full-tree collector node limits, one-less-than-actual node counts, HU max_raises=1050 (structural bound 1054), and N=9 max_raises=63 (bound 515). Production rejects declared structural bounds above 512. Root construction only prechecks chance expansion; complete tree limits are enforced by the collector/solver when explicitly passed the configured bounds.

Accepted fixtures use one disjoint deal with supplied integer ranks 0..N-1 and a complete showdown-ranks continuation, so every non-fold leaf has exact settlement coverage. HU uses stacks (514,514), blinds (1,2), valid BTN/SB and BB sizing labels, and max_raises=254. N=9 uses stacks (131,131,1,1,1,1,1,1,1), equal ante 1 for all seats plus blinds (1,2), button 8, and valid SB/BB sizing labels. Seven seats are all-in after their exact ante, making this a narrow nine-player fixture with two actionable seats. Its max_raises is 62. Per-count rules alternate the two active positions and offer target (count+2) big blinds; the implementation's legal all-in alternative remains present.

Both fixtures were exhaustively traversed with a separate iterative walk checking ledger conservation, runtime protocol conformance, declared node/depth bounds, exact zero-sum terminal utilities, and finite float returns. The walk actually reached the configured raise caps. Both also passed the production recursive collector and one full production NPlayerCFRSolver training iteration under their explicit node/depth bounds. These are bounded synthetic fixtures, not a claim of arbitrary large-tree tractability or full S3 facade/API completion.

Actual probe command:

```sh
PYTHONDONTWRITEBYTECODE=1 uv run python -B /tmp/c3i1-2r-19h5nokc/probe.py
```

Exit 0; actual output:

```text
production /home/genomix-node/poker-solver/src/poker_solver/nplayer_preflop.py a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812
PROTOCOL CHANCE PASS
PROTOCOL dealt PASS
PROTOCOL terminal PASS
REJECT chance raise_count : chance root violates root invariants
REJECT chance pending : chance root violates root invariants
REJECT chance entitlement : chance root violates root invariants
REJECT chance increment : chance root violates root invariants
REJECT chance deal : invalid chance root
REJECT chance history : invalid chance root
REJECT chance ledger : chance root violates root invariants
REJECT dealt missing deal : dealt state requires a private deal
REJECT dealt incompatible deal : dealt state uses an incompatible private deal
REJECT dealt wrong actor : acting player must be first pending responder
REJECT dealt duplicate pending : pending must contain unique seats
REJECT dealt invalid responder : pending contains an invalid responder
REJECT dealt utilities : nonterminal state cannot contain utilities
REJECT dealt pot : pot must equal sum(total_contributed)
REJECT dealt conservation : remaining plus contribution must equal starting stack
REJECT dealt street exceeds total : street commitment cannot exceed total contribution
REJECT dealt raise bound : raise_count exceeds max_raises
REJECT dealt bool actor : invalid acting player
REJECT dealt bool folded : folded must contain booleans
REJECT terminal pending : terminal state must have empty pending
REJECT terminal missing values : terminal state requires N utilities
REJECT terminal dimension : terminal state requires N utilities
REJECT terminal nonzero sum : terminal utilities must be finite and zero-sum
REJECT terminal bool utilities : terminal utilities must be exact numbers
REJECT terminal missing deal : dealt state requires a private deal
CHANCE exact ((((0, 1), (4, 5)), Fraction(3, 11)), (((2, 3), (4, 5)), Fraction(6, 11)), (((2, 3), (0, 6)), Fraction(2, 11))) protocol floats ((Action(kind='DEAL', amount=0), 0.2727272727272727), (Action(kind='DEAL', amount=1), 0.5454545454545454), (Action(kind='DEAL', amount=2), 0.18181818181818182)) sum 1.0
REJECT candidate product 4 > max_deals 3 : candidate product exceeds max_deals
REJECT chance expansion > max_nodes 1 : node bound too small for chance expansion
REJECT full traversal > max_nodes 2 : game exceeds finite node bound
REJECT HU max_raises 1050 : max_raises exceeds the supported structural depth bound
REJECT N9 max_raises 63 : max_raises exceeds the supported structural depth bound
TRAVERSAL N=2 max_raises=254 structural_depth=258 nodes=1532 terminals=1020 observed_depth=256 observed_raises=254 infosets=511 CFR_iterations=1 PASS
REJECT N2 exact node budget minus one : game exceeds finite node bound
TRAVERSAL N=9 max_raises=62 structural_depth=507 nodes=382 terminals=253 observed_depth=64 observed_raises=62 infosets=128 CFR_iterations=1 PASS
REJECT N9 exact node budget minus one : game exceeds finite node bound
PROBE COMPLETE_PASS
```

## Reproducibility: executed temporary probe source

```python
from dataclasses import replace
from fractions import Fraction as F
from math import isfinite
import hashlib
import poker_solver.nplayer_preflop as production
from poker_solver.nplayer_preflop import NPlayerPreflopConfig as Config, NPlayerPreflopContinuation as Continuation, NPlayerPreflopSizingRule as Rule, create_nplayer_preflop_root as root, enumerate_nplayer_preflop_deals as deals
from poker_solver.preflop import WeightedCombo as Combo
from poker_solver.game_structure import ForcedPost as Post
from poker_solver.model import Action, CHANCE, TERMINAL
from poker_solver.nplayer import NPlayerGameState, collect_nplayer_infosets, NPlayerCFRSolver
assert production.__file__ == '/home/genomix-node/poker-solver/src/poker_solver/nplayer_preflop.py'
print('production', production.__file__, hashlib.sha256(open(production.__file__,'rb').read()).hexdigest(), flush=True)
def config(n=2, raises=3):
    deal=tuple((2*i,2*i+1) for i in range(n))
    return Config('nplayer-preflop-v1',n,0 if n==2 else n-1,(100,)*n,(Post(0,'small-blind',1),Post(1,'big-blind',2)),'none',tuple((Combo(c,F(1)),) for c in deal),(),raises,1,10000,False,Continuation('showdown-ranks','C3I1-2R independent ranks','supplied',{}, {deal:tuple(range(n))},tuple(range(n))))
def reject(label, fn, match=None):
    try: fn()
    except ValueError as e:
        if match: assert match in str(e), (label,str(e))
        print('REJECT',label,':',str(e),flush=True)
    else: raise AssertionError('accepted '+label)
c=config(); r=root(c); d=r.child(Action('DEAL',0)); t=d.child(Action('FOLD'))
for label,s in [('CHANCE',r),('dealt',d),('terminal',t)]:
    assert isinstance(s,NPlayerGameState)
    assert s.num_players()==2
    print('PROTOCOL',label,'PASS')
for label,s,changes in [
 ('chance raise_count',r,dict(raise_count=1)),('chance pending',r,dict(pending=())),
 ('chance entitlement',r,dict(can_raise=(False,False))),('chance increment',r,dict(last_raise_increment=99)),
 ('chance deal',r,dict(private_deal=d.private_deal)),('chance history',r,dict(history=t.history)),
 ('chance ledger',r,dict(pot=0,street_committed=(0,0),total_contributed=(0,0),remaining=(100,100))),
 ('dealt missing deal',d,dict(private_deal=None)),('dealt incompatible deal',d,dict(private_deal=((4,5),(6,7)))),
 ('dealt wrong actor',d,dict(acting_player=1)),('dealt duplicate pending',d,dict(pending=(0,0))),
 ('dealt invalid responder',d,dict(pending=(0,2))),('dealt utilities',d,dict(terminal_values=(F(0),F(0)))),
 ('dealt pot',d,dict(pot=4)),('dealt conservation',d,dict(remaining=(98,98))),
 ('dealt street exceeds total',d,dict(street_committed=(2,2))),('dealt raise bound',d,dict(raise_count=4)),
 ('dealt bool actor',d,dict(acting_player=True)),('dealt bool folded',d,dict(folded=(0,False))),
 ('terminal pending',t,dict(pending=(1,))),('terminal missing values',t,dict(terminal_values=None)),
 ('terminal dimension',t,dict(terminal_values=(F(0),))),('terminal nonzero sum',t,dict(terminal_values=(F(1),F(1)))),
 ('terminal bool utilities',t,dict(terminal_values=(False,False))),('terminal missing deal',t,dict(private_deal=None))]:
    reject(label,lambda s=s,changes=changes:replace(s,**changes))
ranges=((Combo((0,1),F(1)),Combo((2,3),F(2))),(Combo((4,5),F(3)),Combo((0,6),F(1))))
expected=(((0,1),(4,5)),((2,3),(4,5)),((2,3),(0,6)))
cont=Continuation('showdown-ranks','C3I1-2R weighted ranks','supplied',{},dict.fromkeys(expected,(1,2)),(0,1))
w=replace(c,ranges=ranges,max_deals=4,continuation=cont)
e=deals(w); o=root(w).chance_outcomes()
assert tuple(x for x,p in e)==expected
assert tuple(p for x,p in e)==(F(3,11),F(6,11),F(2,11))
assert all(type(p) is F for x,p in e) and sum(p for x,p in e)==1
assert tuple(a for a,p in o)==tuple(Action('DEAL',i) for i in range(3))
assert all(type(p) is float and isfinite(p) and p>=0 for a,p in o)
assert tuple(p for a,p in o)==tuple(float(p) for x,p in e)
assert abs(sum(p for a,p in o)-1)<1e-12
assert e==deals(w) and o==root(w).chance_outcomes()
assert tuple(root(w).child(a).private_deal for a,p in o)==expected
print('CHANCE exact',repr(e),'protocol floats',repr(o),'sum',sum(p for a,p in o),flush=True)
reject('candidate product 4 > max_deals 3',lambda:replace(w,max_deals=3),'candidate product')
reject('chance expansion > max_nodes 1',lambda:root(replace(c,max_nodes=1)),'chance expansion')
reject('full traversal > max_nodes 2',lambda:collect_nplayer_infosets(root(replace(c,max_nodes=2)),max_nodes=2),'node bound')
reject('HU max_raises 1050',lambda:replace(c,max_raises=1050),'structural depth')
reject('N9 max_raises 63',lambda:config(9,63),'structural depth')
for n,k in [(2,254),(9,62)]:
    c=config(n,k)
    labels=('BTN/SB','BB') if n==2 else ('SB','BB')
    rules=tuple(Rule(labels[j%2],j,0,'NA' if j==0 else (('IP' if j%2==0 else 'OOP') if n==2 else ('OOP' if j%2==0 else 'IP')),({'unit':'big-blinds','value':j+2},)) for j in range(k))
    stacks=(2*k+6,)*2 if n==2 else (2*k+7,)*2+(1,)*7
    posts=c.forced_posts if n==2 else tuple(Post(i,'ante',1) for i in range(n))+c.forced_posts
    c=replace(c,starting_stacks=stacks,forced_posts=posts,sizing_rules=rules)
    r=root(c); depthbound=2+n+k*(n-1)
    count=leaves=maxdepth=maxraise=0
    stack=[(r,0)]
    while stack:
        s,depth=stack.pop(); count+=1; maxdepth=max(maxdepth,depth); maxraise=max(maxraise,s.raise_count)
        assert count<=c.max_nodes and depth<=depthbound and isinstance(s,NPlayerGameState)
        assert s.pot==sum(s.total_contributed)
        assert all(a+b==v for a,b,v in zip(s.remaining,s.total_contributed,c.starting_stacks))
        if s.current_player()==TERMINAL:
            leaves+=1
            assert all(type(v) is F for v in s.terminal_values) and sum(s.terminal_values)==0
            assert all(type(v) is float and isfinite(v) for v in s.returns())
        else:
            actions=tuple(a for a,p in s.chance_outcomes()) if s.current_player()==CHANCE else s.legal_actions()
            stack.extend((s.child(a),depth+1) for a in actions)
    assert maxraise==k
    infos=collect_nplayer_infosets(r,max_nodes=c.max_nodes,max_depth=depthbound)
    solver=NPlayerCFRSolver(r,max_nodes=c.max_nodes,max_depth=depthbound)
    solver.train(1)
    print(f'TRAVERSAL N={n} max_raises={k} structural_depth={depthbound} nodes={count} terminals={leaves} observed_depth={maxdepth} observed_raises={maxraise} infosets={len(infos)} CFR_iterations={solver.iterations} PASS',flush=True)
    reject(f'N{n} exact node budget minus one',lambda:collect_nplayer_infosets(r,max_nodes=count-1,max_depth=depthbound),'node bound')
print('PROBE COMPLETE_PASS',flush=True)
```
