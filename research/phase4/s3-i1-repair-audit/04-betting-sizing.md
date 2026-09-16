# C3I1-4R replacement betting and sizing audit

status=COMPLETE_PASS
provider=openai-codex
auditor=C3I1-4R
role=fresh non-author replacement auditor
production_sha256=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812
blocker_count=0
utc=2026-09-16T06:38:28Z

This report replaces the invalid Bryant betting report. Its earlier claimed N=2..9 result is not used as evidence. This run executed and passed every N in 2,3,4,5,6,7,8,9. Scope is the requested betting/sizing audit, not full S3 acceptance.

All nine manifest entries and the separately specified production digest were verified before reading the architecture/source/tests and before executing tests. They were verified again after the independent probe. Read: ARCHITECTURE_PHASE4_S3.md, src/poker_solver/nplayer_preflop.py, and tests/test_nplayer_preflop_betting.py. Candidate source, tests, manifest, STATE, PROGRESS and git were not edited; no commit was made.

## Executed findings

- N=2 through N=9: exact initial actor and pending order; entire ordered FOLD/CALL/RAISE tuple, including declaration-order preservation, duplicate-target removal, and all-in; actor-valid folds through terminal; exact BB refund and terminal utilities.
- Four-player limps: one and two callers; SB completion increments to three callers. Separate HU SB completion selects callers=1. Competing caller-count rules make exact selection observable.
- A BB isolation raise resets caller count to zero and fully reopens the former limpers; a former limper executes a full reraise. Pending, entitlement, and increment are checked.
- SB is OOP to CO after CO opens and BTN calls. After SB raises, BB is IP to the new SB aggressor (BB was OOP to the earlier CO), and callers reset despite the earlier BTN call. Competing relation/count rules are excluded by full action-tuple equality.
- Independent HU open/3/4/5-bet targets 8/24/60/108 all executed, followed by CALL to terminal. Every preceding ordered action tuple is checked, with multiple distinct targets and duplicates, competing caller/relation rules, and exact max-raise closure.
- Mandatory CO30-BTNcall-SBcall-BB35 executed under both policies. Both produce pending=(2,3,0), increment=20, raise_count=2, pot=125. Entitlement is all false under no-reopen and (True,False,True,True) under reopen. Every responder's complete action tuple is checked and every responder calls to terminal. A separate reopen branch executes CO90 and checks pending=(3,0), increment=55.
- 93 state snapshots satisfy independent pot/contribution/stack conservation checks. Nonterminal voluntary transfers are checked seat-by-seat against absolute-target-minus-old-commitment arithmetic. Terminal utilities are checked against hand-calculated values for the executed fold, HU chain, and mandatory trace leaves.

The probe imports production public constructors and Action; the only private helper used is _position_map to obtain actual canonical labels. It does not import production sizing-key, caller-count, relation, transfer, or settlement helpers as expected-value oracles, and does not import the permanent tests. Expected actors, amounts, action order, entitlement, pending and utilities are declared independently. Synthetic ranks are supplied to close the specific executed leaves. No claim is made about unexecuted configurations or exhaustive tree coverage.

## Raw manifest output (post-probe repeat of initial nine-row verification)

```text
PASS a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6 ARCHITECTURE_PHASE4_S3.md
PASS a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812 src/poker_solver/nplayer_preflop.py
PASS 8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240 src/poker_solver/sizing.py
PASS bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268 tests/test_nplayer_preflop_config.py
PASS 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd tests/test_nplayer_preflop_betting.py
PASS e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3 tests/test_nplayer_preflop_settlement.py
PASS 0d800d2f8fe797f29d8a347e1ab216bbc079fee0ede792ab253db23097819445 tests/test_nplayer_preflop_information.py
PASS 2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1 tests/test_sizing.py
PASS 61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11 research/phase4/s3-i1-repair/RED_RECEIPT.md
MANIFEST 9/9 PASS; production expected SHA PASS (post-probe recheck)
```

## Raw focused test output

Command: `uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_betting.py`
Exit code: 0

```text
...........                                                              [100%]
11 passed in 0.16s
```

## Raw independent probe output

The source below was written to a unique /tmp/C3I1-4R-*.py file and executed from /home/genomix-node/poker-solver using `uv run python -B <temporary-path>`, with PYTHONDONTWRITEBYTECODE=1. A finally block deleted that file and printed the deletion result. PROBE_EXIT is the subprocess exit status.

```text
TEMP_PROBE /tmp/C3I1-4R-7ciyudpc.py
PASS N=2 initial canonical=BTN/SB actor= 0 actions= (('FOLD', 0), ('CALL', 2), ('RAISE', 8), ('RAISE', 6), ('RAISE', 200))
PASS N=2 fold actors=[0] terminal=(Fraction(-1, 1), Fraction(1, 1)) refunded_BB=1
PASS N=3 initial canonical=BTN actor= 2 actions= (('FOLD', 0), ('CALL', 2), ('RAISE', 8), ('RAISE', 6), ('RAISE', 200))
PASS N=3 fold actors=[2, 0] terminal=(Fraction(-1, 1), Fraction(1, 1), Fraction(0, 1)) refunded_BB=1
PASS N=4 initial canonical=CO actor= 2 actions= (('FOLD', 0), ('CALL', 2), ('RAISE', 8), ('RAISE', 6), ('RAISE', 200))
PASS N=4 fold actors=[2, 3, 0] terminal=(Fraction(-1, 1), Fraction(1, 1), Fraction(0, 1), Fraction(0, 1)) refunded_BB=1
PASS N=5 initial canonical=HJ actor= 2 actions= (('FOLD', 0), ('CALL', 2), ('RAISE', 8), ('RAISE', 6), ('RAISE', 200))
PASS N=5 fold actors=[2, 3, 4, 0] terminal=(Fraction(-1, 1), Fraction(1, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1)) refunded_BB=1
PASS N=6 initial canonical=UTG actor= 2 actions= (('FOLD', 0), ('CALL', 2), ('RAISE', 8), ('RAISE', 6), ('RAISE', 200))
PASS N=6 fold actors=[2, 3, 4, 5, 0] terminal=(Fraction(-1, 1), Fraction(1, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1)) refunded_BB=1
PASS N=7 initial canonical=UTG actor= 2 actions= (('FOLD', 0), ('CALL', 2), ('RAISE', 8), ('RAISE', 6), ('RAISE', 200))
PASS N=7 fold actors=[2, 3, 4, 5, 6, 0] terminal=(Fraction(-1, 1), Fraction(1, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1)) refunded_BB=1
PASS N=8 initial canonical=UTG actor= 2 actions= (('FOLD', 0), ('CALL', 2), ('RAISE', 8), ('RAISE', 6), ('RAISE', 200))
PASS N=8 fold actors=[2, 3, 4, 5, 6, 7, 0] terminal=(Fraction(-1, 1), Fraction(1, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1)) refunded_BB=1
PASS N=9 initial canonical=UTG actor= 2 actions= (('FOLD', 0), ('CALL', 2), ('RAISE', 8), ('RAISE', 6), ('RAISE', 200))
PASS N=9 fold actors=[2, 3, 4, 5, 6, 7, 8, 0] terminal=(Fraction(-1, 1), Fraction(1, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1), Fraction(0, 1)) refunded_BB=1
PASS one limp callers=1 actor= 3 actions= (('FOLD', 0), ('CALL', 2), ('RAISE', 10), ('RAISE', 200))
PASS two limps callers=2 actor= 0 actions= (('FOLD', 0), ('CALL', 2), ('RAISE', 14), ('RAISE', 200))
PASS SB completion adds third caller actor= 1 actions= (('CHECK', 0), ('RAISE', 18), ('RAISE', 200))
PASS raise resets callers=0; CO IP to BB; full reopening actor= 2 actions= (('FOLD', 0), ('CALL', 18), ('RAISE', 40), ('RAISE', 200))
PASS former limper executes full reraise
PASS HU SB completion callers=1 actor= 1 actions= (('CHECK', 0), ('RAISE', 8), ('RAISE', 200))
PASS SB OOP to CO with one cold caller actor= 0 actions= (('FOLD', 0), ('CALL', 8), ('RAISE', 24), ('RAISE', 200))
PASS BB IP to NEW SB aggressor; reset=0 despite BTN prior call actor= 1 actions= (('FOLD', 0), ('CALL', 24), ('RAISE', 50), ('RAISE', 200))
PASS completed chain raise_count=0 relation=NA actor= 0 actions= (('FOLD', 0), ('CALL', 2), ('RAISE', 10), ('RAISE', 8), ('RAISE', 200))
PASS completed chain raise_count=1 relation=OOP actor= 1 actions= (('FOLD', 0), ('CALL', 8), ('RAISE', 28), ('RAISE', 24), ('RAISE', 200))
PASS completed chain raise_count=2 relation=IP actor= 0 actions= (('FOLD', 0), ('CALL', 24), ('RAISE', 64), ('RAISE', 60), ('RAISE', 200))
PASS completed chain raise_count=3 relation=OOP actor= 1 actions= (('FOLD', 0), ('CALL', 60), ('RAISE', 112), ('RAISE', 108), ('RAISE', 200))
PASS after completed fifth bet max_raises=4 actor= 0 actions= (('FOLD', 0), ('CALL', 108))
PASS open/3/4/5-bet completed to CALL terminal; utilities= (Fraction(-108, 1), Fraction(108, 1))
PASS mandatory reopen=False pending=(2, 3, 0) entitlement=(False, False, False, False) pot=125 increment=20
PASS mandatory reopen=False responder=2 actor= 2 actions= (('FOLD', 0), ('CALL', 35))
PASS mandatory reopen=False responder=3 actor= 3 actions= (('FOLD', 0), ('CALL', 35))
PASS mandatory reopen=False responder=0 actor= 0 actions= (('FOLD', 0), ('CALL', 35))
PASS mandatory reopen=False all responders CALL; terminal=(Fraction(-35, 1), Fraction(-35, 1), Fraction(-35, 1), Fraction(105, 1))
PASS mandatory reopen=True pending=(2, 3, 0) entitlement=(True, False, True, True) pot=125 increment=20
PASS mandatory reopen=True responder=2 actor= 2 actions= (('FOLD', 0), ('CALL', 35), ('RAISE', 90), ('RAISE', 500))
PASS mandatory reopen=True responder=3 actor= 3 actions= (('FOLD', 0), ('CALL', 35), ('RAISE', 500))
PASS mandatory reopen=True responder=0 actor= 0 actions= (('FOLD', 0), ('CALL', 35), ('RAISE', 500))
PASS mandatory reopen=True all responders CALL; terminal=(Fraction(-35, 1), Fraction(-35, 1), Fraction(-35, 1), Fraction(105, 1))
PASS mandatory reopen=True CO executes 90; pending=(3, 0); increment=55
ALL INDEPENDENT CASES PASS; ledger snapshots=93; N executed=2,3,4,5,6,7,8,9
PROBE_EXIT 0
TEMP_PROBE_DELETED True
```

## Exact independent probe source

```python
from dataclasses import replace
from fractions import Fraction
from poker_solver.nplayer_preflop import NPlayerPreflopConfig as Config, NPlayerPreflopContinuation as Cont, NPlayerPreflopSizingRule as Rule, create_nplayer_preflop_root, _position_map
from poker_solver.preflop import WeightedCombo
from poker_solver.game_structure import ForcedPost
from poker_solver.model import Action, TERMINAL

checks = 0
def ledger(s):
    global checks
    assert s.pot == sum(s.total_contributed)
    assert all(r+c == initial for r,c,initial in zip(s.remaining,s.total_contributed,s.config.starting_stacks))
    assert all(0 <= c <= t for c,t in zip(s.street_committed,s.total_contributed))
    if s.current_player() == TERMINAL:
        assert sum(s.terminal_values) == 0
    checks += 1

def config(n, stacks=None, bb=2, reopen=False):
    deal = tuple((2*i,2*i+1) for i in range(n))
    return Config("nplayer-preflop-v1",n,0 if n==2 else n-1,stacks or (200,)*n,
        (ForcedPost(0,"small-blind",bb//2),ForcedPost(1,"big-blind",bb)),
        "none",tuple((WeightedCombo(c,Fraction(1)),) for c in deal),(),4,1,10000,reopen,
        Cont("showdown-ranks","C3I1-4R independent synthetic ranks","derived",{}, {deal:tuple(range(n))},tuple(range(n))))

def rule(c,seat,count,callers,relation,*targets):
    # Only label lookup comes from production; expected seats/actions/amounts are hand-declared.
    bb=next(p.amount for p in c.forced_posts if p.kind=="big-blind")
    return Rule(_position_map(c)[seat],count,callers,relation,tuple({"unit":"big-blinds","value":t/bb} for t in targets))

def start(c,rules=()):
    r=create_nplayer_preflop_root(replace(c,sizing_rules=tuple(rules)))
    ledger(r)
    s=r.child(Action("DEAL",0)); ledger(s)
    return s

def actions(s,actor,expected,label):
    assert s.current_player()==actor, (label,s.current_player(),actor)
    actual=tuple((a.kind,a.amount) for a in s.legal_actions())
    assert actual==expected, (label,actual,expected)
    print("PASS",label,"actor=",actor,"actions=",actual)

def step(s,actor,kind,amount=0):
    assert s.current_player()==actor and s.pending[0]==actor
    a=Action(kind,amount); assert a in s.legal_actions()
    t=s.child(a)
    assert t.history[-1].actor==actor and t.history[-1].action==a
    ledger(t)
    if t.current_player()!=TERMINAL:
        pay=amount-s.street_committed[actor] if kind in ("CALL","RAISE") else 0
        assert t.pot==s.pot+pay
        assert t.total_contributed==tuple(v+(pay if i==actor else 0) for i,v in enumerate(s.total_contributed))
        assert t.remaining==tuple(v-(pay if i==actor else 0) for i,v in enumerate(s.remaining))
    return t

def facing(call,*raises):
    return (("FOLD",0),("CALL",call))+tuple(("RAISE",r) for r in raises)

for n in range(2,10):
    c=config(n); actor=0 if n==2 else 2
    s=start(c,[rule(c,actor,0,0,"NA",8,6,8)])
    order=(0,1) if n==2 else tuple(range(2,n))+(0,1)
    assert s.pending==order
    actions(s,actor,facing(2,8,6,200),f"N={n} initial canonical={_position_map(c)[actor]}")
    path=[]
    for p in order[:-1]:
        path.append(p)
        s=step(s,p,"FOLD")
    assert s.current_player()==TERMINAL and s.pending==()
    assert s.terminal_values==tuple(Fraction(-1 if i==0 else 1 if i==1 else 0) for i in range(n))
    assert s.total_contributed==(1,1)+(0,)*(n-2) and s.pot==2
    print(f"PASS N={n} fold actors={path} terminal={s.terminal_values} refunded_BB=1")

c=config(4)
rules=[rule(c,3,0,1,"NA",10),rule(c,3,0,0,"NA",12),
       rule(c,0,0,2,"NA",14),rule(c,0,0,1,"NA",16),
       rule(c,1,0,3,"NA",18),rule(c,1,0,2,"NA",20),
       rule(c,2,1,0,"IP",40),rule(c,2,1,3,"IP",42),rule(c,2,1,0,"OOP",44)]
s=start(c,rules)
s=step(s,2,"CALL",2); actions(s,3,facing(2,10,200),"one limp callers=1")
s=step(s,3,"CALL",2); actions(s,0,facing(2,14,200),"two limps callers=2")
s=step(s,0,"CALL",2); actions(s,1,(("CHECK",0),("RAISE",18),("RAISE",200)),"SB completion adds third caller")
s=step(s,1,"RAISE",18)
assert s.pending==(2,3,0) and s.can_raise==(True,False,True,True) and s.last_raise_increment==16
actions(s,2,facing(18,40,200),"raise resets callers=0; CO IP to BB; full reopening")
s=step(s,2,"RAISE",40)
assert s.pending==(3,0,1) and s.can_raise==(True,True,False,True) and s.last_raise_increment==22
print("PASS former limper executes full reraise")

c=config(2)
s=start(c,[rule(c,1,0,1,"NA",8),rule(c,1,0,0,"NA",10)])
s=step(s,0,"CALL",2)
actions(s,1,(("CHECK",0),("RAISE",8),("RAISE",200)),"HU SB completion callers=1")

c=config(4)
rules=[rule(c,2,0,0,"NA",8),
       rule(c,0,1,1,"OOP",24),rule(c,0,1,0,"OOP",26),rule(c,0,1,1,"IP",28),
       rule(c,1,2,0,"IP",50),rule(c,1,2,1,"IP",52),rule(c,1,2,0,"OOP",54)]
s=start(c,rules); s=step(s,2,"RAISE",8); s=step(s,3,"CALL",8)
actions(s,0,facing(8,24,200),"SB OOP to CO with one cold caller")
s=step(s,0,"RAISE",24)
actions(s,1,facing(24,50,200),"BB IP to NEW SB aggressor; reset=0 despite BTN prior call")

c=config(2)
specs=[(0,0,"NA",8,10),(1,1,"OOP",24,28),(0,2,"IP",60,64),(1,3,"OOP",108,112)]
rules=[]
for seat,count,rel,a,b in specs:
    rules += [rule(c,seat,count,0,rel,b,a,b),rule(c,seat,count,1,rel,a+6)]
    if rel!="NA": rules.append(rule(c,seat,count,0,"IP" if rel=="OOP" else "OOP",a+8))
s=start(c,rules)
call=2
for seat,count,rel,a,b in specs:
    actions(s,seat,facing(call,b,a,200),f"completed chain raise_count={count} relation={rel}")
    s=step(s,seat,"RAISE",a)
    assert s.raise_count==count+1
    call=a
actions(s,0,facing(108),"after completed fifth bet max_raises=4")
s=step(s,0,"CALL",108)
assert s.current_player()==TERMINAL and s.terminal_values==(Fraction(-108),Fraction(108))
assert tuple(h.action.amount for h in s.history)==(8,24,60,108,108)
print("PASS open/3/4/5-bet completed to CALL terminal; utilities=",s.terminal_values)

for reopen in (False,True):
    c=config(4,(500,35,500,500),10,reopen)
    rules=[rule(c,2,0,0,"NA",30),rule(c,2,2,0,"IP",90)]
    s=start(c,rules)
    for seat,kind,target in [(2,"RAISE",30),(3,"CALL",30),(0,"CALL",30),(1,"RAISE",35)]:
        s=step(s,seat,kind,target)
    assert s.pending==(2,3,0) and s.last_raise_increment==20 and s.raise_count==2
    assert s.can_raise==((True,False,True,True) if reopen else (False,)*4)
    assert s.total_contributed==(30,35,30,30) and s.remaining==(470,0,470,470) and s.pot==125
    print(f"PASS mandatory reopen={reopen} pending={s.pending} entitlement={s.can_raise} pot={s.pot} increment={s.last_raise_increment}")
    branch=s
    for seat in (2,3,0):
        raises=(90,500) if seat==2 else (500,)
        actions(s,seat,facing(35,*(raises if reopen else ())),f"mandatory reopen={reopen} responder={seat}")
        s=step(s,seat,"CALL",35)
    assert s.current_player()==TERMINAL and s.terminal_values==(Fraction(-35),Fraction(-35),Fraction(-35),Fraction(105))
    print(f"PASS mandatory reopen={reopen} all responders CALL; terminal={s.terminal_values}")
    if reopen:
        branch=step(branch,2,"RAISE",90)
        assert branch.pending==(3,0) and branch.can_raise==(True,False,False,True) and branch.last_raise_increment==55
        print("PASS mandatory reopen=True CO executes 90; pending=(3, 0); increment=55")
print(f"ALL INDEPENDENT CASES PASS; ledger snapshots={checks}; N executed=2,3,4,5,6,7,8,9")
```
