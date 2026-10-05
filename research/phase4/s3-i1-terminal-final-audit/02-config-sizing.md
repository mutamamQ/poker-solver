auditor=CTA3A2
provider=openai-codex
role=fresh non-author replacement config/sizing auditor
status=COMPLETE_PASS
blocker_count=0
utc=2026-09-16T07:51:53Z
manifest=/home/genomix-node/poker-solver/research/phase4/s3-i1-terminal-final-audit/CANDIDATE_MANIFEST.md

This report replaces the prior config/sizing evidence in this report path. Evidence below comes from this audit's own raw-byte hashes, requested pytest invocation, and independently authored executable public-production probes. No prior auditor result is used as evidence. Candidate identity is exclusively the 11 literal manifest entries; no git revision is used to substitute for their identity.

Initial command and output:
```sh
pwd; test -f /home/genomix-node/poker-solver/research/phase4/s3-i1-terminal-final-audit/CANDIDATE_MANIFEST.md && cat /home/genomix-node/poker-solver/research/phase4/s3-i1-terminal-final-audit/CANDIDATE_MANIFEST.md
```
The command succeeded (exit 0); pwd returned `/home/genomix-node/poker-solver`, and the literal manifest was read before hashing. Exactly 11 `- <sha256>  <path>` rows were parsed. Each hash below is SHA256(Path(path).read_bytes()), independently computed before and after the tests/probes. Every value equalled the corresponding literal manifest digest.

| Literal path | Before raw SHA-256 | After raw SHA-256 |
|---|---|---|
| ARCHITECTURE_PHASE4_S3.md | 6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db | 6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db |
| src/poker_solver/nplayer_preflop.py | a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812 | a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812 |
| src/poker_solver/sizing.py | 8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240 | 8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240 |
| tests/test_nplayer_preflop_config.py | bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268 | bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268 |
| tests/test_nplayer_preflop_betting.py | 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd | 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd |
| tests/test_nplayer_preflop_settlement.py | e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3 | e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3 |
| tests/test_nplayer_preflop_information.py | 1217cf74f1468252fbc7f941621dc57154c910003eb27fbf8947b7bc5a42e289 | 1217cf74f1468252fbc7f941621dc57154c910003eb27fbf8947b7bc5a42e289 |
| tests/test_sizing.py | 2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1 | 2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1 |
| research/phase4/s3-i1-repair/RED_RECEIPT.md | 61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11 | 61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11 |
| research/phase4/s3-i1-spec-reconciliation/RECEIPT.md | 36a95b38ec1b6016bc46ca80307b2c9f4119c749fceb51cd822bccaf61965164 | 36a95b38ec1b6016bc46ca80307b2c9f4119c749fceb51cd822bccaf61965164 |
| research/phase4/s3-i1-terminal-ledger-reconciliation/RECEIPT.md | b631cc2b933c314c081a70e6b3aaa669ae15054145301d272e1a18967d68a42a | b631cc2b933c314c081a70e6b3aaa669ae15054145301d272e1a18967d68a42a |

Requested test command (exit 0):
```sh
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_config.py tests/test_sizing.py
```
Exact output:
```text
........................................................                 [100%]
56 passed in 0.20s
```

Independent probe results: all 197 labelled checks passed. Positive paths use assertions outside the rejection helper; any positive-path exception aborts execution. Expected ledgers, pending actors, legal actions, bounds and conversions are declared in the source, not obtained from a production oracle.

The complete N=3 showdown mapping covers the sole compatible deal `((0,1),(2,3),(4,5))` with ranks `(1,2,3)`. Uniform ante 1 plus SB 1, BB 2, standard straddle 4 produces root pot 10, street `(4,1,2)`, total contributions `(5,2,3)`, remaining `(25,28,27)` and pending `(1,2,0)`. DEAL, CALL 4, CALL 4, CHECK reaches terminal pot 15, contributions `(5,5,5)` and exact utilities `(-5,-5,10)`. This was an executed success, not a continuation rejection.

Double and Mississippi N=4 roots/deals assert exact ledgers, pending seats, actor, increment and actions. Rejection matrices cover strict scalar types, cards, weights, posts, incomplete/unequal antes, invalid straddle arrangements, malformed continuation objects and config compatibility. Both supplied terminal-table and showdown objects execute successful terminal paths; caller mapping mutation leaves copied content unchanged.

Boundary checks accept N=2 max_raises 508 and reject 509, accept N=3 max_raises 253 and reject 254, accept max_nodes 2 for the one-deal root and reject 1, and accept two candidate deals at max_deals 2 and reject 1. The max_nodes positive result concerns root chance expansion, not a claim that the whole tree fits two nodes. Direct-state checks reject the specific malformed states in the source and accept unchanged copies; this is not an exhaustive reachability proof.

Deep nested config/rule/expression caller detachment preserves hash, information key and exact legal actions. Arbitrary recursively nested expression payloads are outside the strict scalar expression schema and are explicitly rejected. Duplicate rule keys with different expressions are rejected; duplicate rounded sizing targets are reduced to the first expression. Finite Decimal values succeed in pot-percent, previous-bet-multiple and big-blinds expressions. Nonfinite Decimal values fail. Finite Decimal geometric scale is rejected by the existing int/float scale schema; no Decimal geometric support is claimed. Exact ROUND_HALF_UP cases are asserted, including 2.5 -> 3 and 4.5 -> 5.

Independent probe command (exit 0):
```sh
PYTHONDONTWRITEBYTECODE=1 uv run python /tmp/CTA3A2-probes.py > /tmp/CTA3A2-probes.out 2>&1
```
Exact successful source:
```python
from dataclasses import replace, FrozenInstanceError
from decimal import Decimal
from fractions import Fraction as F
from poker_solver.game_structure import ForcedPost as P
from poker_solver.preflop import WeightedCombo as W
from poker_solver.model import Action as A, CHANCE, TERMINAL
from poker_solver.nplayer_preflop import (NPlayerPreflopConfig as C, NPlayerPreflopContinuation as K,
    NPlayerPreflopSizingRule as R, NPlayerPreflopPublicAction as H,
    create_nplayer_preflop_root as root, enumerate_nplayer_preflop_deals as deals)
from poker_solver.sizing import validate_size_expression as validate, convert_size_to_chips as convert, fixed_sizes

passed = 0
def reject(label, fn, types=(ValueError, TypeError)):
    global passed
    try:
        fn()
    except types as e:
        passed += 1
        print('REJECT', label, type(e).__name__, str(e))
    else:
        raise AssertionError('accepted: ' + label)
def ok(label):
    global passed
    passed += 1
    print('PASS', label)
def continuation(n):
    d=tuple((2*i,2*i+1) for i in range(n))
    return K('showdown-ranks','CTA3A2 hand-declared synthetic ranks','supplied',{}, {d:tuple(range(1,n+1))},tuple(range(n)))
def config(n=2, **changes):
    v=dict(version='nplayer-preflop-v1',num_players=n,button=0 if n==2 else n-1,
        starting_stacks=(30,)*n,forced_posts=(P(0,'small-blind',1),P(1,'big-blind',2)),
        straddle_variant='none',ranges=tuple((W((2*i,2*i+1),F(1)),) for i in range(n)),
        sizing_rules=(),max_raises=2,max_deals=1,max_nodes=1000,short_all_in_reopens=False,
        continuation=continuation(n))
    v.update(changes)
    return C(**v)
b=config()
assert deals(b)==((((0,1),(2,3)),F(1)),)
assert root(b).child(A('DEAL',0)).pending==(0,1)
ok('base valid config and exact single deal')
for field, values in {
    'num_players':(True,2.0,1,10), 'button':(True,0.0,-1,2),
    'max_deals':(True,1.0,0,-1), 'max_nodes':(True,2.0,0,-1),
    'max_raises':(True,1.0,0,-1), 'short_all_in_reopens':(0,1,None),
    'starting_stacks':((30,), (30,False), (30,0), (30,1.5)),
    'continuation':(None,), 'version':('bad',), 'straddle_variant':('bad',)
}.items():
    for v in values:
        reject(f'config {field}={v!r}',lambda f=field,v=v:replace(b,**{f:v}))
for cards in ((True,1),(0.0,1),(-1,1),(1,1),(0,52),(0,),[0,1]):
    reject(f'cards {cards!r}',lambda cards=cards:replace(b,ranges=((W(cards,F(1)),),b.ranges[1])))
for weight in (True,False,0,-1,float('nan'),float('inf'),Decimal('NaN'),Decimal('Infinity')):
    reject(f'weight {weight!r}',lambda weight=weight:replace(b,ranges=((W((0,1),weight),),b.ranges[1])))
weighted=config(ranges=((W((0,1),F(1,3)),W((4,5),F(2,3))),(W((2,3),F(1)),)),max_deals=2,
    continuation=K('showdown-ranks','exact weights','supplied',{}, {((0,1),(2,3)):(1,2),((4,5),(2,3)):(2,1)},(0,1)))
assert deals(weighted)==((((0,1),(2,3)),F(1,3)),(((4,5),(2,3)),F(2,3)))
ok('positive rational weights normalize exactly')
reject('duplicate canonical cards',lambda:replace(b,ranges=((W((0,1),1),W((1,0),1)),b.ranges[1]),max_deals=2))
for seat,amount in ((True,1),(0,True),(-1,1),(0,-1),(0,1.0),(0.0,1),(2,1),(0,0)):
    reject(f'post seat={seat!r} amount={amount!r}',lambda seat=seat,amount=amount:replace(b,forced_posts=(P(seat,'small-blind',amount),P(1,'big-blind',2))))
for extra in ((P(0,'bad',1),),(P(0,'small-blind',1),),(P(0,'ante',1),),
    (P(0,'ante',1),P(1,'ante',2)),(P(0,'ante',30),P(1,'ante',30)),
    (P(0,'ante',1),P(0,'ante',1))):
    reject(f'invalid post arrangement {extra!r}',lambda extra=extra:replace(b,forced_posts=b.forced_posts+extra))
reject('missing blind',lambda:replace(b,forced_posts=b.forced_posts[:1]))
reject('non-post object',lambda:replace(b,forced_posts=(object(),)))
# COMPLETE ranks: exactly the sole compatible three-player deal.
three=config(3,button=0,straddle_variant='standard',forced_posts=(P(0,'ante',1),P(1,'ante',1),P(2,'ante',1),P(1,'small-blind',1),P(2,'big-blind',2),P(0,'straddle',4)))
s=root(three)
assert s.current_player()==CHANCE
assert (s.pot,s.street_committed,s.total_contributed,s.remaining,s.pending,s.last_raise_increment)==(10,(4,1,2),(5,2,3),(25,28,27),(1,2,0),4)
assert s.chance_outcomes()==((A('DEAL',0),1.0),)
s=s.child(A('DEAL',0)); assert s.current_player()==1 and s.pending==(1,2,0)
s=s.child(A('CALL',4)); assert s.current_player()==2 and s.pending==(2,0)
s=s.child(A('CALL',4)); assert s.current_player()==0 and s.pending==(0,)
s=s.child(A('CHECK'))
assert s.current_player()==TERMINAL and s.pending==()
assert (s.pot,s.street_committed,s.total_contributed,s.remaining)==(15,(4,4,4),(5,5,5),(25,25,25))
assert s.terminal_values==(F(-5),F(-5),F(10)) and s.returns()==(-5.0,-5.0,10.0)
ok('N3 uniform ante + standard root/deal/call/call/check terminal: pot 15, utilities (-5,-5,10)')
for variant,posts,pot,street,remaining,pending,increment in (
    ('double',(P(0,'small-blind',1),P(1,'big-blind',2),P(2,'straddle',4),P(3,'straddle',8)),15,(1,2,4,8),(29,28,26,22),(0,1,2,3),8),
    ('mississippi',(P(0,'small-blind',1),P(1,'big-blind',2),P(3,'straddle',5)),8,(1,2,0,5),(29,28,30,25),(0,1,2,3),5)):
    c=config(4,straddle_variant=variant,forced_posts=posts); r=root(c)
    assert (r.pot,r.street_committed,r.total_contributed,r.remaining,r.pending,r.last_raise_increment)==(pot,street,street,remaining,pending,increment)
    d=r.child(A('DEAL',0));assert d.pending==pending and d.current_player()==0
    assert d.legal_actions()==(A('FOLD'),A('CALL',increment),A('RAISE',30))
    ok(variant+' exact root/deal ledgers and actors')
for variant,posts in (
    ('none',(P(2,'straddle',4),)),('standard',(P(3,'straddle',4),)),
    ('standard',(P(2,'straddle',2),)),('double',(P(3,'straddle',8),P(2,'straddle',4))),
    ('double',(P(2,'straddle',4),)),('double',(P(2,'straddle',4),P(3,'straddle',4))),
    ('mississippi',(P(0,'straddle',4),)),('mississippi',(P(2,'straddle',4),P(3,'straddle',8)))):
    reject('invalid '+variant+' '+repr(posts),lambda variant=variant,posts=posts:config(4,straddle_variant=variant,forced_posts=(P(0,'small-blind',1),P(1,'big-blind',2))+posts))
for variant in ('standard','double','mississippi'):
    reject('HU '+variant,lambda variant=variant:replace(b,straddle_variant=variant,forced_posts=b.forced_posts+(P(0,'straddle',4),)))
reject('N3 double',lambda:replace(three,straddle_variant='double'))
# Malformed continuation construction and config compatibility are separate boundaries.
d=((0,1),(2,3)); k=continuation(2)
for changes in ({'kind':'bad'},{'payoff_table':[]},{'showdown_ranks':[]},{'provenance':' '},{'source':'bad'},
    {'showdown_ranks':{d:(True,2)}},{'showdown_ranks':{d:(1.0,2)}},
    {'odd_chip_order':(False,1)},{'odd_chip_order':(0.0,1)},{'odd_chip_order':(0,0)},
    {'odd_chip_order':[0,1]},{'payoff_table':{(d,()):(F(-1),F(1))}}):
    reject('continuation object '+repr(changes),lambda changes=changes:replace(k,**changes))
for changes in ({'showdown_ranks':{}},{'showdown_ranks':{d:(1,)}},{'odd_chip_order':(0,)},
    {'odd_chip_order':(0,2)},{'showdown_ranks':{((0,1),(1,2)):(1,2)}},
    {'showdown_ranks':{d:(1,2),((4,5),(2,3)):(1,2)}}):
    reject('continuation compatibility '+repr(changes),lambda changes=changes:replace(b,continuation=replace(k,**changes)))
empty=K('terminal-table','explicit supplied utilities','supplied',{}, {},())
for table in ({'bad':(0,0)},{(d,()):(1,1)},{(d,()):(True,-1)},{(d,()):(float('nan'),0)},
    {(d,()):[0,0]},{(d,('bad',)):(0,0)}):
    reject('malformed terminal table '+repr(table),lambda table=table:replace(empty,payoff_table=table))
for table in ({(d,()):(0,0,0)},{(((0,1),(1,2)),()):(0,0)},{(d,(H(2,A('CHECK')),)):(0,0)}):
    reject('terminal table config shape '+repr(table),lambda table=table:replace(b,continuation=replace(empty,payoff_table=table)))
h=(H(0,A('CALL',2)),H(1,A('CHECK')))
caller_table={(d,h):(F(-2),F(2))}
table=replace(empty,payoff_table=caller_table)
caller_table.clear()
t=root(replace(b,continuation=table)).child(A('DEAL',0)).child(A('CALL',2)).child(A('CHECK'))
assert t.current_player()==TERMINAL and t.terminal_values==(F(-2),F(2))
assert t.total_contributed==(2,2) and t.pot==4
reject('payoff read-only',lambda:table.payoff_table.clear(),(AttributeError,TypeError))
caller_ranks={d:(1,2)}; detached=replace(k,showdown_ranks=caller_ranks);caller_ranks[d]=(9,0)
assert detached.showdown_ranks[d]==(1,2)
assert root(replace(b,continuation=detached)).child(A('DEAL',0)).child(A('CALL',2)).child(A('CHECK')).terminal_values==(F(-2),F(2))
ok('valid detached terminal-table and showdown objects execute terminal success')
# Strict exact bounds with successful adjacent values.
assert replace(b,max_raises=508).max_raises==508
reject('N2 max_raises 509 exceeds depth 512',lambda:replace(b,max_raises=509))
assert replace(three,max_raises=253).max_raises==253
reject('N3 max_raises 254 exceeds depth 512',lambda:replace(three,max_raises=254))
assert root(replace(b,max_nodes=2)).pot==3
reject('max_nodes 1 chance expansion',lambda:root(replace(b,max_nodes=1)))
assert len(deals(weighted))==2
reject('max_deals candidate product 2 > 1',lambda:replace(weighted,max_deals=1))
ok('positive adjacent max_raises/max_nodes/max_deals boundaries')
r=root(b); dealt=r.child(A('DEAL',0))
for changes in ({'pot':True},{'pot':4},{'remaining':(29,29)},{'pending':(True,0)},
    {'pending':()},{'can_raise':(1,1)},{'folded':(0,0)},{'acting_player':True},
    {'raise_count':True},{'raise_count':3},{'raise_count':1},{'last_raise_increment':0},
    {'last_raise_increment':3},{'can_raise':(False,False)}, {'private_deal':d},
    {'terminal_values':(F(0),F(0))}):
    reject('direct root '+repr(changes),lambda changes=changes:replace(r,**changes))
for changes in ({'private_deal':((4,5),(2,3))},{'acting_player':1},{'pending':()},
    {'acting_player':TERMINAL,'pending':(),'terminal_values':(1,1)},
    {'acting_player':TERMINAL,'pending':(),'terminal_values':(True,-1)}):
    reject('direct dealt '+repr(changes),lambda changes=changes:replace(dealt,**changes))
assert replace(r)==r and replace(dealt)==dealt
ok('valid direct-state copies')
# The schema accepts scalar expressions, not recursive arbitrary payloads.
# Probe deep caller nesting config -> rule tuple -> expression tuple -> mapping.
caller={'unit':'big-blinds','value':Decimal('2.25')}
rule=R('BTN/SB',0,0,'NA',(caller,)); c=replace(b,sizing_rules=(rule,))
x=root(c).child(A('DEAL',0)); before_hash=hash(rule); before_key=x.information_state_key(0)
assert x.legal_actions()==(A('FOLD'),A('CALL',2),A('RAISE',5),A('RAISE',30))
caller['value']=Decimal('9');caller['unit']='pot-percent';caller['extra']={'nested':[1,2]}
assert dict(c.sizing_rules[0].expressions[0])=={'unit':'big-blinds','value':Decimal('2.25')}
assert hash(rule)==before_hash and hash(replace(rule))==before_hash and x.information_state_key(0)==before_key
assert x.legal_actions()==(A('FOLD'),A('CALL',2),A('RAISE',5),A('RAISE',30))
reject('expression mutation',lambda:rule.expressions[0].__setitem__('value',8),(AttributeError,TypeError))
reject('expression backing reassignment',lambda:setattr(rule.expressions[0],'_items',()),(FrozenInstanceError,AttributeError,TypeError))
for expr in ({'unit':'big-blinds','value':{'nested':[{'v':2}]}},{'unit':'all-in','extra':{'nested':[1]}}):
    reject('unsupported recursive expression '+repr(expr),lambda expr=expr:R('BTN/SB',0,0,'NA',(expr,)))
reject('duplicate sizing key with different expressions',lambda:replace(b,sizing_rules=(rule,replace(rule,expressions=({'unit':'all-in'},)))))
ok('deep caller detachment, hash/key/actions stability and strict recursive schema')
ctx=dict(pot=5,own_commitment=0,highest_commitment=0,remaining_stack=20,big_blind=2)
for expr,context,expected in (
    ({'unit':'pot-percent','value':Decimal('50')},ctx,3),
    ({'unit':'big-blinds','value':Decimal('2.25')},ctx,5),
    ({'unit':'big-blinds','value':Decimal('2.249')},ctx,4),
    ({'unit':'previous-bet-multiple','value':Decimal('1.25')},dict(ctx,highest_commitment=2),3),
    ({'unit':'pot-percent','value':Decimal('50')},dict(ctx,pot=4,own_commitment=1,highest_commitment=2),5),
    ({'unit':'geometric','streets':1,'scale':0.125},ctx,3),
    ({'unit':'all-in'},dict(ctx,own_commitment=2,highest_commitment=2),22)):
    assert validate(expr) is None and convert(expr,context)==expected
    ok('exact ROUND_HALF_UP '+repr(expr)+' -> '+str(expected))
for unit in ('pot-percent','big-blinds','previous-bet-multiple'):
    for value in (True,Decimal('NaN'),Decimal('sNaN'),Decimal('Infinity'),Decimal('-Infinity'),float('nan'),float('inf'),Decimal('0'),Decimal('-1')):
        reject(f'sizing {unit} {value!r}',lambda unit=unit,value=value:convert({'unit':unit,'value':value},ctx))
reject('finite Decimal geometric scale unsupported strict schema',lambda:validate({'unit':'geometric','streets':1,'scale':Decimal('1')}))
for field in ctx:
    for value in (True,1.5,Decimal('2'),-1):
        reject(f'context {field} {value!r}',lambda field=field,value=value:convert({'unit':'all-in'},dict(ctx,**{field:value})))
legal=dict(ctx,highest_commitment=2,minimum_raise_to=4,pot_limit_max_raise_to=None,short_all_in_allowed=True)
choices=fixed_sizes(({'unit':'big-blinds','value':Decimal('2.25')},{'unit':'big-blinds','value':Decimal('2.5')}),legal)
assert len(choices)==1 and choices[0].target==5
ok('rounded duplicate sizing targets preserve first expression')
print('ALL PASS; checks =',passed)
```

Exact successful output:
```text
PASS base valid config and exact single deal
REJECT config num_players=True ValueError num_players must be an integer from 2 to 9
REJECT config num_players=2.0 ValueError num_players must be an integer from 2 to 9
REJECT config num_players=1 ValueError num_players must be an integer from 2 to 9
REJECT config num_players=10 ValueError num_players must be an integer from 2 to 9
REJECT config button=True ValueError button must be a valid integer seat
REJECT config button=0.0 ValueError button must be a valid integer seat
REJECT config button=-1 ValueError button must be a valid integer seat
REJECT config button=2 ValueError button must be a valid integer seat
REJECT config max_deals=True ValueError max_deals must be a non-negative integer
REJECT config max_deals=1.0 ValueError max_deals must be a non-negative integer
REJECT config max_deals=0 ValueError max_deals must be positive
REJECT config max_deals=-1 ValueError max_deals must be a non-negative integer
REJECT config max_nodes=True ValueError max_nodes must be a non-negative integer
REJECT config max_nodes=2.0 ValueError max_nodes must be a non-negative integer
REJECT config max_nodes=0 ValueError max_nodes must be positive
REJECT config max_nodes=-1 ValueError max_nodes must be a non-negative integer
REJECT config max_raises=True ValueError max_raises must be a non-negative integer
REJECT config max_raises=1.0 ValueError max_raises must be a non-negative integer
REJECT config max_raises=0 ValueError max_raises must be positive
REJECT config max_raises=-1 ValueError max_raises must be a non-negative integer
REJECT config short_all_in_reopens=0 ValueError short_all_in_reopens must be boolean
REJECT config short_all_in_reopens=1 ValueError short_all_in_reopens must be boolean
REJECT config short_all_in_reopens=None ValueError short_all_in_reopens must be boolean
REJECT config starting_stacks=(30,) ValueError starting_stacks length must equal num_players
REJECT config starting_stacks=(30, False) ValueError starting stack must be a non-negative integer
REJECT config starting_stacks=(30, 0) ValueError starting stack must be positive
REJECT config starting_stacks=(30, 1.5) ValueError starting stack must be a non-negative integer
REJECT config continuation=None ValueError continuation must be NPlayerPreflopContinuation
REJECT config version='bad' ValueError version must be nplayer-preflop-v1
REJECT config straddle_variant='bad' ValueError invalid straddle_variant
REJECT cards (True, 1) ValueError cards must be two distinct non-negative integers
REJECT cards (0.0, 1) ValueError cards must be two distinct non-negative integers
REJECT cards (-1, 1) ValueError cards must be two distinct non-negative integers
REJECT cards (1, 1) ValueError cards must be two distinct non-negative integers
REJECT cards (0, 52) ValueError range combos must contain valid cards in 0..51
REJECT cards (0,) ValueError cards must be two distinct non-negative integers
REJECT cards [0, 1] ValueError cards must be two distinct non-negative integers
REJECT weight True ValueError weight must be an exact positive rational
REJECT weight False ValueError weight must be an exact positive rational
REJECT weight 0 ValueError weight must be an exact positive rational
REJECT weight -1 ValueError weight must be an exact positive rational
REJECT weight nan ValueError weight must be an exact positive rational
REJECT weight inf ValueError weight must be an exact positive rational
REJECT weight Decimal('NaN') ValueError weight must be an exact positive rational
REJECT weight Decimal('Infinity') ValueError weight must be an exact positive rational
PASS positive rational weights normalize exactly
REJECT duplicate canonical cards ValueError range combos must be unique within a seat
REJECT post seat=True amount=1 TypeError bool-as-int rejected
REJECT post seat=0 amount=True TypeError bool-as-int rejected
REJECT post seat=-1 amount=1 ValueError seat must be non-negative int, got -1
REJECT post seat=0 amount=-1 ValueError amount must be non-negative int, got -1
REJECT post seat=0 amount=1.0 ValueError amount must be non-negative int, got 1.0
REJECT post seat=0.0 amount=1 ValueError seat must be non-negative int, got 0.0
REJECT post seat=2 amount=1 ValueError forced post references an invalid seat
REJECT post seat=0 amount=0 ValueError forced post amount must be positive
REJECT invalid post arrangement (ForcedPost(seat=0, kind='bad', amount=1),) ValueError unsupported forced post kind
REJECT invalid post arrangement (ForcedPost(seat=0, kind='small-blind', amount=1),) ValueError exactly one small blind is required on the derived SB seat
REJECT invalid post arrangement (ForcedPost(seat=0, kind='ante', amount=1),) ValueError antes must be one identical positive ante for every seat
REJECT invalid post arrangement (ForcedPost(seat=0, kind='ante', amount=1), ForcedPost(seat=1, kind='ante', amount=2)) ValueError antes must be one identical positive ante for every seat
REJECT invalid post arrangement (ForcedPost(seat=0, kind='ante', amount=30), ForcedPost(seat=1, kind='ante', amount=30)) ValueError cumulative forced posts exceed a starting stack
REJECT invalid post arrangement (ForcedPost(seat=0, kind='ante', amount=1), ForcedPost(seat=0, kind='ante', amount=1)) ValueError antes must be one identical positive ante for every seat
REJECT missing blind ValueError exactly one big blind is required on the derived BB seat
REJECT non-post object ValueError forced_posts must contain ForcedPost values
PASS N3 uniform ante + standard root/deal/call/call/check terminal: pot 15, utilities (-5,-5,10)
PASS double exact root/deal ledgers and actors
PASS mississippi exact root/deal ledgers and actors
REJECT invalid none (ForcedPost(seat=2, kind='straddle', amount=4),) ValueError straddle_variant none cannot declare a straddle
REJECT invalid standard (ForcedPost(seat=3, kind='straddle', amount=4),) ValueError standard straddle requires operational UTG and N>=3
REJECT invalid standard (ForcedPost(seat=2, kind='straddle', amount=2),) ValueError straddle amounts must strictly increase
REJECT invalid double (ForcedPost(seat=3, kind='straddle', amount=8), ForcedPost(seat=2, kind='straddle', amount=4)) ValueError double straddle requires ordered UTG/UTG+1 and N>=4
REJECT invalid double (ForcedPost(seat=2, kind='straddle', amount=4),) ValueError double straddle requires ordered UTG/UTG+1 and N>=4
REJECT invalid double (ForcedPost(seat=2, kind='straddle', amount=4), ForcedPost(seat=3, kind='straddle', amount=4)) ValueError straddle amounts must strictly increase
REJECT invalid mississippi (ForcedPost(seat=0, kind='straddle', amount=4),) ValueError mississippi straddle requires one non-blind seat and N>=3
REJECT invalid mississippi (ForcedPost(seat=2, kind='straddle', amount=4), ForcedPost(seat=3, kind='straddle', amount=8)) ValueError mississippi straddle requires one non-blind seat and N>=3
REJECT HU standard ValueError standard straddle requires operational UTG and N>=3
REJECT HU double ValueError double straddle requires ordered UTG/UTG+1 and N>=4
REJECT HU mississippi ValueError mississippi straddle requires one non-blind seat and N>=3
REJECT N3 double ValueError double straddle requires ordered UTG/UTG+1 and N>=4
REJECT continuation object {'kind': 'bad'} ValueError continuation kind must be terminal-table or showdown-ranks
REJECT continuation object {'payoff_table': []} ValueError continuation tables must be mappings
REJECT continuation object {'showdown_ranks': []} ValueError continuation tables must be mappings
REJECT continuation object {'provenance': ' '} ValueError continuation provenance must be non-empty
REJECT continuation object {'source': 'bad'} ValueError continuation source must be supplied or derived
REJECT continuation object {'showdown_ranks': {((0, 1), (2, 3)): (True, 2)}} ValueError invalid showdown-ranks entry
REJECT continuation object {'showdown_ranks': {((0, 1), (2, 3)): (1.0, 2)}} ValueError invalid showdown-ranks entry
REJECT continuation object {'odd_chip_order': (False, 1)} ValueError odd_chip_order must contain unique non-negative integer seats
REJECT continuation object {'odd_chip_order': (0.0, 1)} ValueError odd_chip_order must contain unique non-negative integer seats
REJECT continuation object {'odd_chip_order': (0, 0)} ValueError odd_chip_order must contain unique non-negative integer seats
REJECT continuation object {'odd_chip_order': [0, 1]} ValueError odd_chip_order must be a tuple
REJECT continuation object {'payoff_table': {(((0, 1), (2, 3)), ()): (Fraction(-1, 1), Fraction(1, 1))}} ValueError showdown-ranks continuation cannot contain payoff values
REJECT continuation compatibility {'showdown_ranks': {}} ValueError showdown ranks must cover exactly every compatible deal
REJECT continuation compatibility {'showdown_ranks': {((0, 1), (2, 3)): (1,)}} ValueError showdown-ranks entries must contain one rank per seat
REJECT continuation compatibility {'odd_chip_order': (0,)} ValueError odd_chip_order must be a permutation of all seats
REJECT continuation compatibility {'odd_chip_order': (0, 2)} ValueError odd_chip_order must be a permutation of all seats
REJECT continuation compatibility {'showdown_ranks': {((0, 1), (1, 2)): (1, 2)}} ValueError showdown-ranks entries must contain one rank per seat
REJECT continuation compatibility {'showdown_ranks': {((0, 1), (2, 3)): (1, 2), ((4, 5), (2, 3)): (1, 2)}} ValueError showdown ranks must cover exactly every compatible deal
REJECT malformed terminal table {'bad': (0, 0)} ValueError invalid terminal-table entry
REJECT malformed terminal table {(((0, 1), (2, 3)), ()): (1, 1)} ValueError terminal values must be finite and zero-sum
REJECT malformed terminal table {(((0, 1), (2, 3)), ()): (True, -1)} ValueError invalid terminal-table entry
REJECT malformed terminal table {(((0, 1), (2, 3)), ()): (nan, 0)} ValueError terminal values must be finite exact numbers
REJECT malformed terminal table {(((0, 1), (2, 3)), ()): [0, 0]} ValueError invalid terminal-table entry
REJECT malformed terminal table {(((0, 1), (2, 3)), ('bad',)): (0, 0)} ValueError invalid terminal-table entry
REJECT terminal table config shape {(((0, 1), (2, 3)), ()): (0, 0, 0)} ValueError terminal values must contain N utilities
REJECT terminal table config shape {(((0, 1), (1, 2)), ()): (0, 0)} ValueError terminal-table deals must contain N disjoint combos
REJECT terminal table config shape {(((0, 1), (2, 3)), (NPlayerPreflopPublicAction(actor=2, action=Action(kind='CHECK', amount=0)),)): (0, 0)} ValueError terminal history actor is outside the table
REJECT payoff read-only AttributeError 'mappingproxy' object has no attribute 'clear'
PASS valid detached terminal-table and showdown objects execute terminal success
REJECT N2 max_raises 509 exceeds depth 512 ValueError max_raises exceeds the supported structural depth bound
REJECT N3 max_raises 254 exceeds depth 512 ValueError max_raises exceeds the supported structural depth bound
REJECT max_nodes 1 chance expansion ValueError node bound too small for chance expansion
REJECT max_deals candidate product 2 > 1 ValueError candidate product exceeds max_deals
PASS positive adjacent max_raises/max_nodes/max_deals boundaries
REJECT direct root {'pot': True} ValueError pot must be a non-negative integer
REJECT direct root {'pot': 4} ValueError pot must equal sum(total_contributed)
REJECT direct root {'remaining': (29, 29)} ValueError remaining plus contribution must equal starting stack
REJECT direct root {'pending': (True, 0)} ValueError pending contains an invalid responder
REJECT direct root {'pending': ()} ValueError chance root violates root invariants
REJECT direct root {'can_raise': (1, 1)} ValueError can_raise must contain booleans
REJECT direct root {'folded': (0, 0)} ValueError folded must contain booleans
REJECT direct root {'acting_player': True} ValueError invalid acting player
REJECT direct root {'raise_count': True} ValueError raise_count must be a non-negative integer
REJECT direct root {'raise_count': 3} ValueError raise_count exceeds max_raises
REJECT direct root {'raise_count': 1} ValueError chance root violates root invariants
REJECT direct root {'last_raise_increment': 0} ValueError last_raise_increment must be positive
REJECT direct root {'last_raise_increment': 3} ValueError chance root violates root invariants
REJECT direct root {'can_raise': (False, False)} ValueError chance root violates root invariants
REJECT direct root {'private_deal': ((0, 1), (2, 3))} ValueError invalid chance root
REJECT direct root {'terminal_values': (Fraction(0, 1), Fraction(0, 1))} ValueError invalid chance root
REJECT direct dealt {'private_deal': ((4, 5), (2, 3))} ValueError dealt state uses an incompatible private deal
REJECT direct dealt {'acting_player': 1} ValueError acting player must be first pending responder
REJECT direct dealt {'pending': ()} ValueError acting player must be first pending responder
REJECT direct dealt {'acting_player': -2, 'pending': (), 'terminal_values': (1, 1)} ValueError terminal utilities must be finite and zero-sum
REJECT direct dealt {'acting_player': -2, 'pending': (), 'terminal_values': (True, -1)} ValueError terminal utilities must be exact numbers
PASS valid direct-state copies
REJECT expression mutation AttributeError '_FrozenExpression' object has no attribute '__setitem__'
REJECT expression backing reassignment FrozenInstanceError cannot assign to field '_items'
REJECT unsupported recursive expression {'unit': 'big-blinds', 'value': {'nested': [{'v': 2}]}} ValueError invalid sizing expression
REJECT unsupported recursive expression {'unit': 'all-in', 'extra': {'nested': [1]}} ValueError invalid sizing expression
REJECT duplicate sizing key with different expressions ValueError duplicate sizing rule key
PASS deep caller detachment, hash/key/actions stability and strict recursive schema
PASS exact ROUND_HALF_UP {'unit': 'pot-percent', 'value': Decimal('50')} -> 3
PASS exact ROUND_HALF_UP {'unit': 'big-blinds', 'value': Decimal('2.25')} -> 5
PASS exact ROUND_HALF_UP {'unit': 'big-blinds', 'value': Decimal('2.249')} -> 4
PASS exact ROUND_HALF_UP {'unit': 'previous-bet-multiple', 'value': Decimal('1.25')} -> 3
PASS exact ROUND_HALF_UP {'unit': 'pot-percent', 'value': Decimal('50')} -> 5
PASS exact ROUND_HALF_UP {'unit': 'geometric', 'streets': 1, 'scale': 0.125} -> 3
PASS exact ROUND_HALF_UP {'unit': 'all-in'} -> 22
REJECT sizing pot-percent True ValueError pot-percent value must not be a boolean
REJECT sizing pot-percent Decimal('NaN') ValueError pot-percent value must be finite
REJECT sizing pot-percent Decimal('sNaN') ValueError pot-percent value must be finite
REJECT sizing pot-percent Decimal('Infinity') ValueError pot-percent value must be finite
REJECT sizing pot-percent Decimal('-Infinity') ValueError pot-percent value must be finite
REJECT sizing pot-percent nan ValueError pot-percent value must be finite
REJECT sizing pot-percent inf ValueError pot-percent value must be finite
REJECT sizing pot-percent Decimal('0') ValueError pot-percent value must be positive
REJECT sizing pot-percent Decimal('-1') ValueError pot-percent value must be positive
REJECT sizing big-blinds True ValueError big-blinds value must not be a boolean
REJECT sizing big-blinds Decimal('NaN') ValueError big-blinds value must be finite
REJECT sizing big-blinds Decimal('sNaN') ValueError big-blinds value must be finite
REJECT sizing big-blinds Decimal('Infinity') ValueError big-blinds value must be finite
REJECT sizing big-blinds Decimal('-Infinity') ValueError big-blinds value must be finite
REJECT sizing big-blinds nan ValueError big-blinds value must be finite
REJECT sizing big-blinds inf ValueError big-blinds value must be finite
REJECT sizing big-blinds Decimal('0') ValueError big-blinds value must be positive
REJECT sizing big-blinds Decimal('-1') ValueError big-blinds value must be positive
REJECT sizing previous-bet-multiple True ValueError previous-bet-multiple value must not be a boolean
REJECT sizing previous-bet-multiple Decimal('NaN') ValueError previous-bet-multiple value must be finite
REJECT sizing previous-bet-multiple Decimal('sNaN') ValueError previous-bet-multiple value must be finite
REJECT sizing previous-bet-multiple Decimal('Infinity') ValueError previous-bet-multiple value must be finite
REJECT sizing previous-bet-multiple Decimal('-Infinity') ValueError previous-bet-multiple value must be finite
REJECT sizing previous-bet-multiple nan ValueError previous-bet-multiple value must be finite
REJECT sizing previous-bet-multiple inf ValueError previous-bet-multiple value must be finite
REJECT sizing previous-bet-multiple Decimal('0') ValueError previous-bet-multiple value must be positive
REJECT sizing previous-bet-multiple Decimal('-1') ValueError previous-bet-multiple value must be positive
REJECT finite Decimal geometric scale unsupported strict schema ValueError geometric scale must be positive
REJECT context pot True ValueError pot must be a non-negative integer
REJECT context pot 1.5 ValueError pot must be a non-negative integer
REJECT context pot Decimal('2') ValueError pot must be a non-negative integer
REJECT context pot -1 ValueError pot must be a non-negative integer
REJECT context own_commitment True ValueError own_commitment must be a non-negative integer
REJECT context own_commitment 1.5 ValueError own_commitment must be a non-negative integer
REJECT context own_commitment Decimal('2') ValueError own_commitment must be a non-negative integer
REJECT context own_commitment -1 ValueError own_commitment must be a non-negative integer
REJECT context highest_commitment True ValueError highest_commitment must be a non-negative integer
REJECT context highest_commitment 1.5 ValueError highest_commitment must be a non-negative integer
REJECT context highest_commitment Decimal('2') ValueError highest_commitment must be a non-negative integer
REJECT context highest_commitment -1 ValueError highest_commitment must be a non-negative integer
REJECT context remaining_stack True ValueError remaining_stack must be a non-negative integer
REJECT context remaining_stack 1.5 ValueError remaining_stack must be a non-negative integer
REJECT context remaining_stack Decimal('2') ValueError remaining_stack must be a non-negative integer
REJECT context remaining_stack -1 ValueError remaining_stack must be a non-negative integer
REJECT context big_blind True ValueError big_blind must be a non-negative integer
REJECT context big_blind 1.5 ValueError big_blind must be a non-negative integer
REJECT context big_blind Decimal('2') ValueError big_blind must be a non-negative integer
REJECT context big_blind -1 ValueError big_blind must be a non-negative integer
PASS rounded duplicate sizing targets preserve first expression
ALL PASS; checks = 197
```

No candidate, test, manifest, STATE.txt, PROGRESS.md, git metadata or commit was edited. Repository writes were limited to this report and `.hb/CTA3A2`. Temporary probe/evidence files were created only in `/tmp`, embedded here, read back for equality, and deleted. Verdict applies to this config/sizing audit scope and the concrete checks above; it does not assert a full-suite or whole-candidate final verdict.
