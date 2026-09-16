# CTA3A4 final betting audit

status=COMPLETE_PASS
auditor=CTA3A4
provider=openai-codex
UTC=2026-09-16T07:44:33Z
blocker_count=0
production_sha256=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812
architecture_sha256=6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db

Candidate identity: `/home/genomix-node/poker-solver/research/phase4/s3-i1-terminal-final-audit/CANDIDATE_MANIFEST.md` only; no HEAD-based candidate substitution. Role: user-assigned fresh alternate-provider non-author final auditor replacing the failed BryantGPT betting scope.

The first shell execution began with `pwd`, then `test -f /home/genomix-node/poker-solver/research/phase4/s3-i1-terminal-final-audit/CANDIDATE_MANIFEST.md`. The working directory printed `/home/genomix-node/poker-solver`; the exact manifest existed and was read. Independently hashing raw bytes with Python `hashlib.sha256(Path.read_bytes())` matched all 11 manifest entries before testing and after the final probe. Candidate files and manifest were not edited. No STATE.txt, PROGRESS.md, git metadata or commits were written. The only persistent writes by this audit are this report and `.hb/CTA3A4`; the probe was created under `/tmp`, executed and deleted before this report was written.

## Executed betting suite

Command: `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_betting.py`

Exit code: 0. Raw output:

```text
...........                                                              [100%]
11 passed in 0.16s
```

## Independent production-importing probe

Command: `PYTHONDONTWRITEBYTECODE=1 uv run python /tmp/CTA3A4_probe.py`

Final recorded execution exit code: 0; stderr was empty. The exact source below was executed successfully. It imports public production contracts only, with no test helpers or private sizing, caller, relation or settlement expected-value oracles. Literal fixture orders, position labels, raise targets and action sequences supply expectations. Arithmetic assertions independently apply absolute target minus prior commitment and, at terminal states, a unique-highest unmatched refund. Every transition checks exact street/contribution/remaining vectors, pot and stack conservation.

Executed scope: N=2 through 9 limp/SB-completion caller counts, full ordered legal tuples, pending order and actor checks, sizing declaration order and duplicate removal, full reopening, and independently completed open/3-bet/4-bet/5-bet call closures and fold closures. Additional N=4 fixtures exercise cold callers, caller reset, OOP versus CO and IP versus the new SB aggressor. CO30/BTNcall/SBcall/BB35 executes both short-all-in policies: the no-reopen branch rejects an attempted raise; the reopen branch executes an all-in re-raise and terminal calls. N=5 exercises unacted blind entitlement under both policies, subsequent full reopening and a side-pot call closure. The final probe recorded 352 decision checks, 352 transition arithmetic checks and 54 terminal closures. This is bounded fixture coverage, not exhaustive coverage; the extra cold-caller and short-all-in scenarios are N=4/5, not every player count. The standalone probe uses unstraddled, zero-ante fixtures; the requested existing suite also executed its standard-straddle test.

Exact blockers: none observed in the executed scope. No claim is made about unexecuted configurations or exhaustive game-tree correctness.

### Exact successful probe source

```python
from fractions import Fraction
from poker_solver.nplayer_preflop import (NPlayerPreflopConfig, NPlayerPreflopContinuation,
    NPlayerPreflopSizingRule, create_nplayer_preflop_root)
from poker_solver.game_structure import ForcedPost
from poker_solver.preflop import WeightedCombo
from poker_solver.model import Action, TERMINAL

# Literal fixtures: button is last seat except HU; SB=0, BB=1.
ORDERS = {2:(0,1), 3:(2,0,1), 4:(2,3,0,1), 5:(2,3,4,0,1),
          6:(2,3,4,5,0,1), 7:(2,3,4,5,6,0,1),
          8:(2,3,4,5,6,7,0,1), 9:(2,3,4,5,6,7,8,0,1)}
LABELS = {2:('BTN/SB','BB'), 3:('SB','BB','BTN'), 4:('SB','BB','CO','BTN'),
          5:('SB','BB','HJ','CO','BTN'), 6:('SB','BB','UTG','HJ','CO','BTN'),
          7:('SB','BB','UTG','MP','HJ','CO','BTN'),
          8:('SB','BB','UTG','UTG+1','MP','HJ','CO','BTN'),
          9:('SB','BB','UTG','UTG+1','MP','LJ','HJ','CO','BTN')}
F=Action('FOLD'); C=Action('CHECK')
def call(x): return Action('CALL',x)
def raise_to(x): return Action('RAISE',x)
def menu(h,*targets): return (F,call(h))+tuple(raise_to(x) for x in targets)
def rule(pos,rc,cc,rel,*targets):
    return NPlayerPreflopSizingRule(pos,rc,cc,rel,
        tuple({'unit':'big-blinds','value':x/2} for x in targets))
def start(n,rules=(),stacks=None,reopen=False):
    deal=tuple((2*i,2*i+1) for i in range(n))
    cfg=NPlayerPreflopConfig('nplayer-preflop-v1',n,0 if n==2 else n-1,
        stacks or (200,)*n,(ForcedPost(0,'small-blind',1),ForcedPost(1,'big-blind',2)),
        'none',tuple((WeightedCombo(c,Fraction(1)),) for c in deal),tuple(rules),4,1,10000,reopen,
        NPlayerPreflopContinuation('showdown-ranks','CTA3A4 literal ranks','derived',{},
            {deal:tuple(range(n))},tuple(range(n))))
    root=create_nplayer_preflop_root(cfg)
    assert root.chance_outcomes()==((Action('DEAL',0),1.0),)
    s=root.child(Action('DEAL',0))
    assert s.street_committed==(1,2)+(0,)*(n-2)
    assert s.pot==3
    conservation(s)
    return s
checks=0
transfers=0
terminals=0
def conservation(s):
    assert s.pot==sum(s.total_contributed)
    assert tuple(a+b for a,b in zip(s.remaining,s.total_contributed))==s.config.starting_stacks
    assert all(0<=a<=b for a,b in zip(s.street_committed,s.total_contributed))
    assert s.pot+sum(s.remaining)==sum(s.config.starting_stacks)
    if s.current_player()==TERMINAL:
        assert sum(s.terminal_values)==0
        assert s.pending==() and s.legal_actions()==()
def expect(s,pending,actions):
    global checks
    assert s.pending==pending,(s.pending,pending)
    assert s.current_player()==pending[0]
    assert s.legal_actions()==actions,(s.history,s.legal_actions(),actions)
    conservation(s); checks+=1

def move(s,a):
    global transfers,terminals
    p=s.current_player()
    street=list(s.street_committed); total=list(s.total_contributed); rem=list(s.remaining)
    paid=a.amount-street[p] if a.kind in ('CALL','RAISE') else 0
    street[p]+=paid; total[p]+=paid; rem[p]-=paid
    t=s.child(a)
    assert t.history[-1].actor==p and t.history[-1].action==a
    if t.current_player()==TERMINAL:
        # Independent canonical unmatched refund; no settlement helper imports.
        top=sorted(total,reverse=True)
        excess=top[0]-top[1]
        if excess:
            seat=total.index(top[0]); total[seat]-=excess; street[seat]-=excess; rem[seat]+=excess
        terminals+=1
    assert t.street_committed==tuple(street)
    assert t.total_contributed==tuple(total)
    assert t.remaining==tuple(rem)
    assert t.pot==sum(total)
    conservation(t); transfers+=1
    return t

for n,order in ORDERS.items():
    # Every limp and the SB completion must count: only exact BB caller key matches.
    s=start(n,[rule('BB',0,n-1,'NA',8,6,8,200)])
    for index,p in enumerate(order[:-1]):
        expect(s,order[index:],menu(2,200)); s=move(s,call(2))
    expect(s,(1,),(C,raise_to(8),raise_to(6),raise_to(200)))
    s=move(s,C)
    assert s.current_player()==TERMINAL and s.total_contributed==(2,)*n
    assert s.terminal_values==(-2,)*(n-1)+(2*(n-1),)
    # Completed open, 3-bet, 4-bet and 5-bet leaves, each independently restarted.
    # HU postflop order is BB then BTN; otherwise seat order ends at button.
    postflop=(1,0) if n==2 else tuple(range(n))
    rules=[]
    for k,target in enumerate((6,14,30,62)):
        actor=order[k%n]
        rel='NA' if k==0 else ('IP' if postflop.index(actor)>postflop.index(order[(k-1)%n]) else 'OOP')
        rules.append(rule(LABELS[n][actor],k,0,rel,target))
    for depth in (1,2,3,4):
        s=start(n,rules); pending=order; high=2
        for k,target in enumerate((6,14,30,62)[:depth]):
            expect(s,pending,menu(high,target,200))
            actor=pending[0]; s=move(s,raise_to(target))
            idx=order.index(actor)
            pending=order[idx+1:]+order[:idx]
            assert s.pending==pending
            assert s.can_raise==tuple(i!=actor for i in range(n))
            assert s.last_raise_increment==target-high
            high=target
        for index,p in enumerate(pending):
            # Only the first responder can match the next literal rule; after
            # its CALL the caller key changes and all rules above have cc=0.
            targets=() if depth==4 else ((6,14,30,62)[depth],200) if index==0 else (200,)
            expect(s,pending[index:],menu(high,*targets))
            s=move(s,call(high))
        assert s.current_player()==TERMINAL
        assert s.total_contributed==(high,)*n
        assert s.terminal_values==(-high,)*(n-1)+(high*(n-1),)
    # Fold closure with unmatched raise refunded to the largest opposing post.
    s=start(n,[rule(LABELS[n][order[0]],0,0,'NA',6)])
    expect(s,order,menu(2,6,200)); s=move(s,raise_to(6))
    actor=order[0]; pending=order[1:]
    for index,p in enumerate(pending):
        expect(s,pending[index:],menu(6,200)); s=move(s,F)
    assert s.current_player()==TERMINAL and s.folded==tuple(i!=actor for i in range(n))
    print(f'N={n} PASS limps/SB-count/order/dedup; completed open/3bet/4bet/5bet; full reopen; call/fold closures')

# Cold caller, current aggressor relation, reset after raise, ordered sizing.
rules=(rule('CO',0,0,'NA',6),rule('SB',1,1,'OOP',20,18,20),
       rule('BB',2,0,'IP',40),rule('CO',2,1,'IP',44),
       rule('BTN',3,0,'IP',90))
s=start(4,rules)
for pending,actions,a in [
 ((2,3,0,1),menu(2,6,200),raise_to(6)),
 ((3,0,1),menu(6,200),call(6)),
 ((0,1),menu(6,20,18,200),raise_to(20)),
 ((1,2,3),menu(20,40,200),call(20)),
 ((2,3),menu(20,44,200),raise_to(44)),
 ((3,0,1),menu(44,90,200),raise_to(90)),
 ((0,1,2),menu(90),call(90)),((1,2),menu(90),call(90)),((2,),menu(90),call(90))]:
    expect(s,pending,actions); s=move(s,a)
assert s.current_player()==TERMINAL and s.total_contributed==(90,)*4
print('N=4 PASS cold callers, caller reset, OOP to CO then IP to SB, ordered duplicate sizes, completed 5bet')

# Literal mandatory CO30 / BTNcall / SBcall / BB35 under both policies.
for reopen in (False,True):
    s=start(4,[rule('CO',0,0,'NA',30)],(200,35,200,200),reopen)
    for pending,actions,a in [
        ((2,3,0,1),menu(2,30,200),raise_to(30)),
        ((3,0,1),menu(30,200),call(30)),
        ((0,1),menu(30,200),call(30)),
        ((1,),menu(30,35),raise_to(35))]:
        expect(s,pending,actions); s=move(s,a)
    assert s.last_raise_increment==28 and s.raise_count==2
    assert s.can_raise==(reopen,False,reopen,reopen)
    if reopen:
        expect(s,(2,3,0),menu(35,200))
        branch=move(s,raise_to(200))
        for queue in ((3,0),(0,)):
            expect(branch,queue,menu(200)); branch=move(branch,call(200))
        assert branch.current_player()==TERMINAL
        assert branch.total_contributed==(200,35,200,200)
        assert branch.terminal_values==(-200,-35,-200,435)
    else:
        try:
            s.child(raise_to(200))
        except ValueError as exc:
            assert str(exc)=='action is not legal'
        else:
            raise AssertionError('consumed actor illegally re-raised after short all-in')
    for pending in ((2,3,0),(3,0),(0,)):
        expect(s,pending,menu(35,*((200,) if reopen else ())))
        s=move(s,call(35))
    assert s.current_player()==TERMINAL and s.total_contributed==(35,)*4
    print(f'N=4 PASS short all-in reopens={reopen}; prior actors entitlement; terminal calls')

# Unacted blinds retain entitlement; already-acted HJ and CO depend on policy.
for reopen in (False,True):
    s=start(5,[rule('HJ',0,0,'NA',30),rule('SB',2,0,'OOP',70)],
            (200,200,200,200,35),reopen)
    for pending,actions,a in [
        ((2,3,4,0,1),menu(2,30,200),raise_to(30)),
        ((3,4,0,1),menu(30,200),call(30)),
        ((4,0,1),menu(30,35),raise_to(35))]:
        expect(s,pending,actions); s=move(s,a)
    assert s.can_raise==(True,True,reopen,reopen,False)
    expect(s,(0,1,2,3),menu(35,70,200)); s=move(s,raise_to(70))
    assert s.can_raise==(False,True,True,True,False) and s.last_raise_increment==35
    for pending in ((1,2,3),(2,3),(3,)):
        expect(s,pending,menu(70,200)); s=move(s,call(70))
    assert s.current_player()==TERMINAL and s.total_contributed==(70,70,70,70,35)
    assert s.terminal_values==(-70,-70,-70,70,140)
    print(f'N=5 PASS short policy={reopen}; unacted entitlement; subsequent full reopening; side-pot call closure')
print(f'PASS decision_checks={checks} transition_arithmetic_checks={transfers} terminal_closures={terminals}')
print('Bounded declared fixtures only; no exhaustive coverage claim.')
```

### Raw successful probe output

```text
N=2 PASS limps/SB-count/order/dedup; completed open/3bet/4bet/5bet; full reopen; call/fold closures
N=3 PASS limps/SB-count/order/dedup; completed open/3bet/4bet/5bet; full reopen; call/fold closures
N=4 PASS limps/SB-count/order/dedup; completed open/3bet/4bet/5bet; full reopen; call/fold closures
N=5 PASS limps/SB-count/order/dedup; completed open/3bet/4bet/5bet; full reopen; call/fold closures
N=6 PASS limps/SB-count/order/dedup; completed open/3bet/4bet/5bet; full reopen; call/fold closures
N=7 PASS limps/SB-count/order/dedup; completed open/3bet/4bet/5bet; full reopen; call/fold closures
N=8 PASS limps/SB-count/order/dedup; completed open/3bet/4bet/5bet; full reopen; call/fold closures
N=9 PASS limps/SB-count/order/dedup; completed open/3bet/4bet/5bet; full reopen; call/fold closures
N=4 PASS cold callers, caller reset, OOP to CO then IP to SB, ordered duplicate sizes, completed 5bet
N=4 PASS short all-in reopens=False; prior actors entitlement; terminal calls
N=4 PASS short all-in reopens=True; prior actors entitlement; terminal calls
N=5 PASS short policy=False; unacted entitlement; subsequent full reopening; side-pot call closure
N=5 PASS short policy=True; unacted entitlement; subsequent full reopening; side-pot call closure
PASS decision_checks=352 transition_arithmetic_checks=352 terminal_closures=54
Bounded declared fixtures only; no exhaustive coverage claim.
```

## Before raw SHA-256

These are the initial independent raw-byte measurements, all matched before the pytest/probe runs.

```text
6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db  ARCHITECTURE_PHASE4_S3.md  MATCH
a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812  src/poker_solver/nplayer_preflop.py  MATCH
8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240  src/poker_solver/sizing.py  MATCH
bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268  tests/test_nplayer_preflop_config.py  MATCH
9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd  tests/test_nplayer_preflop_betting.py  MATCH
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py  MATCH
1217cf74f1468252fbc7f941621dc57154c910003eb27fbf8947b7bc5a42e289  tests/test_nplayer_preflop_information.py  MATCH
2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1  tests/test_sizing.py  MATCH
61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11  research/phase4/s3-i1-repair/RED_RECEIPT.md  MATCH
36a95b38ec1b6016bc46ca80307b2c9f4119c749fceb51cd822bccaf61965164  research/phase4/s3-i1-spec-reconciliation/RECEIPT.md  MATCH
b631cc2b933c314c081a70e6b3aaa669ae15054145301d272e1a18967d68a42a  research/phase4/s3-i1-terminal-ledger-reconciliation/RECEIPT.md  MATCH
```

## After raw SHA-256

These were independently recomputed after the final successful probe execution.

```text
6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db  ARCHITECTURE_PHASE4_S3.md  MATCH
a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812  src/poker_solver/nplayer_preflop.py  MATCH
8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240  src/poker_solver/sizing.py  MATCH
bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268  tests/test_nplayer_preflop_config.py  MATCH
9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd  tests/test_nplayer_preflop_betting.py  MATCH
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py  MATCH
1217cf74f1468252fbc7f941621dc57154c910003eb27fbf8947b7bc5a42e289  tests/test_nplayer_preflop_information.py  MATCH
2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1  tests/test_sizing.py  MATCH
61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11  research/phase4/s3-i1-repair/RED_RECEIPT.md  MATCH
36a95b38ec1b6016bc46ca80307b2c9f4119c749fceb51cd822bccaf61965164  research/phase4/s3-i1-spec-reconciliation/RECEIPT.md  MATCH
b631cc2b933c314c081a70e6b3aaa669ae15054145301d272e1a18967d68a42a  research/phase4/s3-i1-terminal-ledger-reconciliation/RECEIPT.md  MATCH
```

Temporary probe deletion was checked with `assert not probe.exists()` after unlinking `/tmp/CTA3A4_probe.py`. UTC was obtained live using `date -u +%Y-%m-%dT%H:%M:%SZ`.
