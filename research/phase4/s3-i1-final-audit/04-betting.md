# FC3I1-4 final betting audit

status=COMPLETE_PASS
provider=openai-codex
auditor=FC3I1-4
blocker_count=0
utc=2026-09-16T07:01:50Z
production_sha256=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812
architecture_sha256=15b378ac224460ee8064e3c54f5925d3721d4ca38e4529cf84b7e82858975a78

Fresh non-author replacement audit of betting scope. This report supersedes the rejected report. Architecture, production module, and permanent betting test were read. Inspection is not counted as independent execution. No candidate edits or git writes were performed. This is a bounded betting audit, not a claim that the entire S3 acceptance matrix or full regression ran.

## Required permanent test execution

Command: `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_betting.py`

Exit code: 0. Actual output:

```text
...........                                                              [100%]
11 passed in 0.11s
```

## Independent production-importing execution

Command: `PYTHONDONTWRITEBYTECODE=1 uv run python /tmp/FC3I1-4-probe.py`

Exit code: 0. The temporary probe was created outside the repository, executed successfully twice (the final execution is captured below), and deleted afterward. It imports production types and transitions directly, with no imports from tests and no production private helpers as expected-value oracles. Canonical labels are declared from architecture section 4; production position machinery is unchanged. Hand-calculated expected actions, ledgers and utilities are asserted.

The execution covers every N=2..9 initial actor, complete pending order, complete legal-action tuples and successive folds through terminal/refund. A separate limp/check path for every N selects every canonical label and checks exact sizing declaration order and deduplication. Additional completed HU and multiway paths exercise limps, SB completion, caller count/reset, current-aggressor relation (including CO changing from OOP relative to BTN to IP relative to BB), full reopening of prior caller/raiser entitlement, and open/3/4/5-bet closure. Both mandatory short-all-in policies complete call closures; the enabled policy also executes the reopened raise and reaches terminal.

Every visited state explicitly checks `pot == sum(total_contributed)`, `pot + sum(remaining) == sum(starting_stacks)`, each seat's `total_contributed + remaining == starting_stack`, nonnegative remaining, and `0 <= street_committed <= total_contributed`. These are explicit probe assertions, additional to production validation. Terminal assertions check empty pending/actions and exact zero-sum utilities; individual paths assert independently calculated terminal vectors. The 157 count includes repeated branch visits and is not a unique-state/tree-exhaustion count.

Actual final execution stdout:

```text
N=2 labels=('BTN/SB', 'BB') initial_actor=0 pending=(0, 1); initial=(FOLD0,CALL2,RAISE200); fold terminal=(-1, 1); every-label ordered sizing=(8,6,200), limp/check closure PASS
N=3 labels=('BTN', 'SB', 'BB') initial_actor=2 pending=(2, 0, 1); initial=(FOLD0,CALL2,RAISE200); fold terminal=(-1, 1, 0); every-label ordered sizing=(8,6,200), limp/check closure PASS
N=4 labels=('CO', 'BTN', 'SB', 'BB') initial_actor=2 pending=(2, 3, 0, 1); initial=(FOLD0,CALL2,RAISE200); fold terminal=(-1, 1, 0, 0); every-label ordered sizing=(8,6,200), limp/check closure PASS
N=5 labels=('HJ', 'CO', 'BTN', 'SB', 'BB') initial_actor=2 pending=(2, 3, 4, 0, 1); initial=(FOLD0,CALL2,RAISE200); fold terminal=(-1, 1, 0, 0, 0); every-label ordered sizing=(8,6,200), limp/check closure PASS
N=6 labels=('UTG', 'HJ', 'CO', 'BTN', 'SB', 'BB') initial_actor=2 pending=(2, 3, 4, 5, 0, 1); initial=(FOLD0,CALL2,RAISE200); fold terminal=(-1, 1, 0, 0, 0, 0); every-label ordered sizing=(8,6,200), limp/check closure PASS
N=7 labels=('UTG', 'MP', 'HJ', 'CO', 'BTN', 'SB', 'BB') initial_actor=2 pending=(2, 3, 4, 5, 6, 0, 1); initial=(FOLD0,CALL2,RAISE200); fold terminal=(-1, 1, 0, 0, 0, 0, 0); every-label ordered sizing=(8,6,200), limp/check closure PASS
N=8 labels=('UTG', 'UTG+1', 'MP', 'HJ', 'CO', 'BTN', 'SB', 'BB') initial_actor=2 pending=(2, 3, 4, 5, 6, 7, 0, 1); initial=(FOLD0,CALL2,RAISE200); fold terminal=(-1, 1, 0, 0, 0, 0, 0, 0); every-label ordered sizing=(8,6,200), limp/check closure PASS
N=9 labels=('UTG', 'UTG+1', 'MP', 'LJ', 'HJ', 'CO', 'BTN', 'SB', 'BB') initial_actor=2 pending=(2, 3, 4, 5, 6, 7, 8, 0, 1); initial=(FOLD0,CALL2,RAISE200); fold terminal=(-1, 1, 0, 0, 0, 0, 0, 0, 0); every-label ordered sizing=(8,6,200), limp/check closure PASS
HU SB completion -> BB10 -> BTN/SB30 -> BB call: caller reset and IP current aggressor, terminal=(-30,30) PASS
4p CO limp -> BTN10 -> SBcall10 -> BB36 -> CO100 -> BTN180 -> SB/BB/COcall180: full ordered tuples, caller reset, CO IP vs current BB (OOP vs prior BTN), reopening and completed open/3/4/5-bet; terminal=(-180,-180,-180,540) PASS
HU completed open8/3bet24/4bet60/5bet120/call120: ordered actions, alternating IP/OOP, full reopening, raise cap; terminal=(-120,120) PASS
CO30-BTNcall-SBcall-BB35 policy=False pending=(2, 3, 0) can_raise=(False, False, False, False) actions=(Action(kind='FOLD', amount=0), Action(kind='CALL', amount=35)) pot=125 total=(30, 35, 30, 30) remaining=(470, 0, 470, 470) increment=20 PASS
policy=False call closure terminal=(-35,-35,-35,105) PASS
CO30-BTNcall-SBcall-BB35 policy=True pending=(2, 3, 0) can_raise=(True, False, True, True) actions=(Action(kind='FOLD', amount=0), Action(kind='CALL', amount=35), Action(kind='RAISE', amount=90), Action(kind='RAISE', amount=500)) pot=125 total=(30, 35, 30, 30) remaining=(470, 0, 470, 470) increment=20 PASS
policy=True call closure terminal=(-35,-35,-35,105); actual CO90 reopening/call/call terminal=(-90,-35,-90,215) PASS
INDEPENDENT_PROBE PASS; conservation explicitly asserted on 157 visited states (chance, decisions, terminal included)
```

Actual stderr: ''.
Temporary probe deletion verified: `/tmp/FC3I1-4-probe.py` does not exist.

## Raw artifact integrity

All 10 manifest rows were independently SHA-256 hashed from raw file bytes before testing and again after execution/deletion. The manifest itself was read only. Matching text in the manifest was not used as a substitute for hashing file contents.

| File | Computed SHA-256 (both checks) | Before | After |
| --- | --- | --- | --- |
| `ARCHITECTURE_PHASE4_S3.md` | `15b378ac224460ee8064e3c54f5925d3721d4ca38e4529cf84b7e82858975a78` | PASS | PASS |
| `src/poker_solver/nplayer_preflop.py` | `a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812` | PASS | PASS |
| `src/poker_solver/sizing.py` | `8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240` | PASS | PASS |
| `tests/test_nplayer_preflop_config.py` | `bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268` | PASS | PASS |
| `tests/test_nplayer_preflop_betting.py` | `9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd` | PASS | PASS |
| `tests/test_nplayer_preflop_settlement.py` | `e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3` | PASS | PASS |
| `tests/test_nplayer_preflop_information.py` | `49cf12eb1bd514a4bcaad4bae896f4a143407ceff71928cdaf5e8f05395e2e84` | PASS | PASS |
| `tests/test_sizing.py` | `2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1` | PASS | PASS |
| `research/phase4/s3-i1-repair/RED_RECEIPT.md` | `61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11` | PASS | PASS |
| `research/phase4/s3-i1-spec-reconciliation/RECEIPT.md` | `36a95b38ec1b6016bc46ca80307b2c9f4119c749fceb51cd822bccaf61965164` | PASS | PASS |

## Executed probe source

Retained here for review/reproduction after deleting the temporary executable:

```python
from fractions import Fraction
from poker_solver.nplayer_preflop import NPlayerPreflopConfig as Config, NPlayerPreflopContinuation as Continuation, NPlayerPreflopSizingRule as Rule, create_nplayer_preflop_root
from poker_solver.game_structure import ForcedPost
from poker_solver.preflop import WeightedCombo
from poker_solver.model import Action, TERMINAL

states=0
labels={2:('BTN/SB','BB'),3:('BTN','SB','BB'),4:('CO','BTN','SB','BB'),5:('HJ','CO','BTN','SB','BB'),6:('UTG','HJ','CO','BTN','SB','BB'),7:('UTG','MP','HJ','CO','BTN','SB','BB'),8:('UTG','UTG+1','MP','HJ','CO','BTN','SB','BB'),9:('UTG','UTG+1','MP','LJ','HJ','CO','BTN','SB','BB')}
def rule(pos,rc,cc,rel,*values):
 return Rule(pos,rc,cc,rel,tuple({'unit':'big-blinds','value':v} for v in values))
def config(n,rules=(),stacks=None,bb=2,reopens=False):
 deal=tuple((2*i,2*i+1) for i in range(n))
 return Config(version='nplayer-preflop-v1',num_players=n,button=0 if n==2 else n-1,starting_stacks=stacks or (200,)*n,forced_posts=(ForcedPost(0,'small-blind',bb//2),ForcedPost(1,'big-blind',bb)),straddle_variant='none',ranges=tuple((WeightedCombo(c,Fraction(1)),) for c in deal),sizing_rules=rules,max_raises=4,max_deals=1,max_nodes=10000,short_all_in_reopens=reopens,continuation=Continuation('showdown-ranks','FC3I1-4 independent fixture','derived',{}, {deal:tuple(range(n))},tuple(range(n))))
def check(s):
 global states
 assert s.pot==sum(s.total_contributed)
 assert s.pot+sum(s.remaining)==sum(s.config.starting_stacks)
 for i in range(s.num_players()):
  assert s.total_contributed[i]+s.remaining[i]==s.config.starting_stacks[i]
  assert 0<=s.street_committed[i]<=s.total_contributed[i]
  assert s.remaining[i]>=0
 if s.current_player()==TERMINAL:
  assert s.pending==() and s.legal_actions()==() and sum(s.terminal_values)==0
 states+=1
 return s
def start(c):
 return step(check(create_nplayer_preflop_root(c)),'DEAL',0)
def step(s,k,a=0):
 return check(s.child(Action(k,a)))
def legal(s,*expected):
 assert s.legal_actions()==tuple(Action(*a) for a in expected),(s.legal_actions(),expected)
def facing(s,call,*raises):
 legal(s,('FOLD',0),('CALL',call),*(('RAISE',r) for r in raises))
def terminal(s,values):
 assert s.current_player()==TERMINAL and s.terminal_values==tuple(map(Fraction,values))

for n in range(2,10):
 order=(0,1) if n==2 else tuple(range(2,n))+(0,1)
 s=start(config(n))
 assert s.current_player()==order[0] and s.pending==order
 facing(s,2,200)
 for i,actor in enumerate(order[:-1]):
  assert s.current_player()==actor and s.pending==order[i:]
  facing(s,2,200)
  s=step(s,'FOLD')
 terminal(s,(-1,1)+(0,)*(n-2))
 assert s.pot==2 and s.total_contributed==(1,1)+(0,)*(n-2)
 # Select every canonical label via actual decisions; exact caller keys, declared unsorted duplicate sizes.
 rules=tuple(rule(label,0,i,'NA',4,3,4) for i,label in enumerate(labels[n]))
 s=start(config(n,rules))
 for i,actor in enumerate(order):
  assert s.current_player()==actor and s.pending==order[i:]
  if actor==1: legal(s,('CHECK',0),('RAISE',8),('RAISE',6),('RAISE',200))
  else: facing(s,2,8,6,200)
  s=step(s,'CHECK' if actor==1 else 'CALL',0 if actor==1 else 2)
 terminal(s,tuple(2*n-2 if i==n-1 else -2 for i in range(n)))
 print(f'N={n} labels={labels[n]} initial_actor={order[0]} pending={order}; initial=(FOLD0,CALL2,RAISE200); fold terminal={tuple(sv for sv in ((-1,1)+(0,)*(n-2)))}; every-label ordered sizing=(8,6,200), limp/check closure PASS')

# HU SB complete counted, reset to zero on BB raise, current aggressor relation IP.
s=start(config(2,(rule('BB',0,1,'NA',5),rule('BTN/SB',1,0,'IP',15),rule('BTN/SB',1,1,'IP',20))))
s=step(s,'CALL',2); legal(s,('CHECK',0),('RAISE',10),('RAISE',200))
s=step(s,'RAISE',10); facing(s,10,30,200)
s=step(s,'RAISE',30); s=step(s,'CALL',30); terminal(s,(-30,30))
print('HU SB completion -> BB10 -> BTN/SB30 -> BB call: caller reset and IP current aggressor, terminal=(-30,30) PASS')

# CO changes OOP vs BTN to IP vs BB; decoy wrong-relation and stale-caller keys must not appear.
rules=(rule('BTN',0,1,'NA',5),rule('SB',1,0,'OOP',15),rule('BB',1,1,'OOP',18),rule('CO',2,0,'IP',50),rule('CO',2,0,'OOP',60),rule('CO',2,1,'IP',70),rule('BTN',3,0,'IP',90))
s=start(config(4,rules))
s=step(s,'CALL',2); facing(s,2,10,200)
s=step(s,'RAISE',10); facing(s,10,30,200)
s=step(s,'CALL',10); facing(s,10,36,200)
s=step(s,'RAISE',36); facing(s,36,100,200)
assert s.can_raise==(True,False,True,True) and s.pending==(2,3,0)
s=step(s,'RAISE',100); facing(s,100,180,200)
s=step(s,'RAISE',180)
assert s.raise_count==4
for actor in (0,1,2):
 assert s.current_player()==actor
 facing(s,180)
 s=step(s,'CALL',180)
terminal(s,(-180,-180,-180,540))
print('4p CO limp -> BTN10 -> SBcall10 -> BB36 -> CO100 -> BTN180 -> SB/BB/COcall180: full ordered tuples, caller reset, CO IP vs current BB (OOP vs prior BTN), reopening and completed open/3/4/5-bet; terminal=(-180,-180,-180,540) PASS')

# Full reopening of consumed caller entitlement and consumed raiser entitlement above; HU sequence independent targets.
rules=(rule('BTN/SB',0,0,'NA',4),rule('BB',1,0,'OOP',12),rule('BTN/SB',2,0,'IP',30),rule('BB',3,0,'OOP',60))
s=start(config(2,rules))
for rc,(call,target) in enumerate(((2,8),(8,24),(24,60),(60,120))):
 assert s.raise_count==rc
 facing(s,call,target,200)
 s=step(s,'RAISE',target)
 assert s.can_raise[s.current_player()]
facing(s,120); s=step(s,'CALL',120); terminal(s,(-120,120))
print('HU completed open8/3bet24/4bet60/5bet120/call120: ordered actions, alternating IP/OOP, full reopening, raise cap; terminal=(-120,120) PASS')

for reopen in (False,True):
 rules=(rule('CO',0,0,'NA',3),rule('CO',2,0,'IP',9))
 s=start(config(4,rules,(500,35,500,500),10,reopen))
 facing(s,10,30,500)
 for k,a in (('RAISE',30),('CALL',30),('CALL',30)):
  s=step(s,k,a)
 facing(s,30,35); s=step(s,'RAISE',35)
 assert s.pending==(2,3,0) and s.last_raise_increment==20 and s.raise_count==2
 assert s.can_raise==((True,False,True,True) if reopen else (False,)*4)
 assert s.pot==125 and s.total_contributed==(30,35,30,30) and s.remaining==(470,0,470,470)
 facing(s,35,*((90,500) if reopen else ()))
 print(f'CO30-BTNcall-SBcall-BB35 policy={reopen} pending={s.pending} can_raise={s.can_raise} actions={s.legal_actions()} pot={s.pot} total={s.total_contributed} remaining={s.remaining} increment={s.last_raise_increment} PASS')
 # Complete call branch under both policies.
 calls=s
 for actor in (2,3,0):
  assert calls.current_player()==actor
  facing(calls,35,*((90,500) if reopen and actor==2 else (500,) if reopen else ()))
  calls=step(calls,'CALL',35)
 terminal(calls,(-35,-35,-35,105))
 if reopen:
  s=step(s,'RAISE',90)
  assert s.pending==(3,0) and s.last_raise_increment==55 and s.can_raise==(True,False,False,True)
  s=step(s,'CALL',90); s=step(s,'CALL',90)
  terminal(s,(-90,-35,-90,215))
 print(f'policy={reopen} call closure terminal=(-35,-35,-35,105)'+('; actual CO90 reopening/call/call terminal=(-90,-35,-90,215)' if reopen else '')+' PASS')
print(f'INDEPENDENT_PROBE PASS; conservation explicitly asserted on {states} visited states (chance, decisions, terminal included)')
```

## Verdict

COMPLETE_PASS for the requested betting scope; blocker_count=0. No discrepancy was observed in the executed cases. Only this report and `.hb/FC3I1-4` are authorized repository writes.
