# C3I1-1 independent recovery audit — config and forced-post ledger

Status: **FAIL — architecture blockers remain.**
Completed UTC: 2026-09-16 05:48:01 UTC
Scope: frozen S3-I1 typed config, positions, deals, forced posts, sizing representation and local bounds. This is not full S3/S3-I2 solver/API acceptance.

## Frozen identity

Independently read ARCHITECTURE_PHASE4_S3.md, CANDIDATE_MANIFEST.md, the production module, all four permanent preflop suites, and relevant ForcedPost/WeightedCombo/sizing helpers. Parent narrative and prior audit conclusions were not used as proof.

Command (run at entry and again after probes; exit 0):
```sh
sha256sum ARCHITECTURE_PHASE4_S3.md src/poker_solver/nplayer_preflop.py
```
Result:
```text
a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6  ARCHITECTURE_PHASE4_S3.md
0e55fbce5f6934c8e2e63ee28ce9d01d9268792165d9318bc8c9ed03b5f73422  src/poker_solver/nplayer_preflop.py
```

All four test hashes independently matched the manifest:
```sh
sha256sum tests/test_nplayer_preflop_*.py
```
```text
d61a86d39f864d494f19a91698478c4af39b76d6ad0372321f18d69706349f69  tests/test_nplayer_preflop_betting.py
5a214b900a7ad1b61aa67cd294d7000e3eef0023f82bb834d1e94035f815a867  tests/test_nplayer_preflop_config.py
282112f2b88e57b1b8b25bbdd69d0f6fb90df714e92ccff80945f9724375e69d  tests/test_nplayer_preflop_information.py
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
```

The manifest specifies a production hash and a design hash, not its own self-hash. No manifest-file-to-production-hash comparison was made.

## Blockers

| ID | Severity | Independent observation | Architecture requirement |
| --- | --- | --- | --- |
| C3I1-1-B1 | P1 / high / acceptance blocker | Config accepts additional ForcedPost(2, "not-a-post", 7), also None, integer 123 and "bogus" kinds. With no straddle, ordinary 1/2 blinds, the root becomes pot 10 and street (1,2,7,0,0,0). Invalid post kinds silently become live wagers. | Sections 2.4 and 3 require strict forced-post types, exactly supported post kinds and validated straddle arrangements. |
| C3I1-1-B2 | P1 / high / acceptance blocker | Sizing expressions expose writable backing storage. Mutating rule.expressions[0]._data["value"] from 3 to 4 changes an existing state's legal raise from 6 to 8 and changes its information key. The mutated rule equals a fresh value-4 rule but their hashes differ. | Section 2.2 requires an immutable, hashable representation; sections 1 and 2.4 require immutable config. |
| C3I1-1-B3 | P2 / medium / acceptance blocker | showdown-ranks odd_chip_order accepts (False,True,2,3,4,5) and (0.0,1.0,2.0,3.0,4.0,5.0). | Sections 2.3–2.4 specify tuple[int,...], a seat permutation and bool-as-int rejection. |

B1 source: nplayer_preflop.py:260–268 validates the ForcedPost class and amount but not kind; game_structure.ForcedPost does not enforce its Literal annotation. Root lines 939–943 treat every non-ante as live. This reproducer uses ordinary constructors, no forged or mutated post objects.

B2 source: nplayer_preflop.py:79–99 stores a plain dict plus a separately cached tuple for hashing. Ordinary item assignment through the Mapping interface is rejected and the original input dict is detached; those limited properties pass. The explicit adversarial reproduction accesses the single-underscore backing attribute, with no object.__setattr__, reflection or frozen-dataclass bypass. The container itself also permits normal reassignment of its slots. The stale cached hash violates equality/hash consistency after the legal-action-changing mutation.

B3 source: nplayer_preflop.py:372–376 checks only length/set equality, which treats False/0/0.0 and True/1/1.0 as equal. This is a strict validation defect, independent of whether a downstream settlement helper later rejects an order.

## Passing checks and limits

- 44 N/button rotations cover every N=2..9 against hand-declared canonical label sequences.
- 2,608 ledger cases cover every rotation, no/standard/double and every non-blind Mississippi straddler, uniform antes interleaved with reversed blind declarations, and every exact all-in seat at N>=3. Expected contributions, live commitments, remaining stacks, pot, increment, entitlement, first actor and full pending order are calculated independently.
- Source inspection confirms the root iterates forced_posts directly in declared order, with no clamp or initial refund. Final totals alone cannot distinguish reordered additive transfers; ordered straddle validation is independently tested.
- The explicit recovery check sets starting_stacks[0]=3 with seat 0 ante 2 + SB 1. Remaining is (0,96,98,98,98,98), pending is (2,3,4,5,1), and seat 0 cannot raise. The earlier claimed seat-0 ledger blocker is not reproduced.
- Strict numeric fields, tuple lengths, invalid cards/weights, duplicate canonical combos, nonuniform/partial/single-seat antes, invalid straddle seats/orders/amounts, overposted and degenerate stacks, duplicate sizing keys and malformed sizing expressions reject.
- Exact blocked product oracle returns masses 3/11, 6/11, 2/11 in declared range order; no compatible deals rejects. max_deals applies before pruning. Public chance floats normalize.
- max_nodes rejects insufficient initial chance expansion and accepts the exact expansion boundary. max_raises=1 suppresses further raises after a short all-in. Full solver-wide node enforcement is S3-I2 scope, not claimed here.
- Immutable input copying and public mapping assignment rejection pass, but do not cure B2.
- The permanent suites do not catch these blockers; green tests alone are insufficient.

## Focused test commands and exact results

All commands executed from /home/genomix-node/poker-solver. Bytecode and pytest cache writes were disabled.

```sh
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py
```
Exit 0: `26 passed in 0.17s`.

```sh
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider -q tests/test_game_structure.py tests/test_sizing.py tests/test_preflop.py
```
Exit 0: `49 passed in 0.10s`.

## Independent matrix: exact reproducible command

This command intentionally prints reproduced blockers after asserting the passing cases; exit 0 is successful execution of the audit probe, not candidate acceptance.

```sh
PYTHONDONTWRITEBYTECODE=1 uv run python - <<'PY'
from dataclasses import replace, FrozenInstanceError
from fractions import Fraction
from itertools import product
from math import isfinite
from poker_solver.game_structure import ForcedPost as P
from poker_solver.preflop import WeightedCombo as W
from poker_solver.model import Action
from poker_solver.nplayer_preflop import (
 NPlayerPreflopConfig as C, NPlayerPreflopContinuation as K,
 NPlayerPreflopSizingRule as R, create_nplayer_preflop_root as root,
 enumerate_nplayer_preflop_deals as deals, _position_map)
counts = {}
def ok(group):
 counts[group] = counts.get(group, 0) + 1
def reject(group, fn):
 try: fn()
 except (ValueError, TypeError, OverflowError): ok(group)
 else: raise AssertionError("unexpected acceptance: " + group)
def cfg(n=6, button=None, **kw):
 b = (0 if n == 2 else n-1) if button is None else button
 sb = b if n == 2 else (b+1)%n
 bb = (b+1)%n if n == 2 else (b+2)%n
 v = dict(version="nplayer-preflop-v1", num_players=n, button=b,
 starting_stacks=(100,)*n, forced_posts=(P(sb,"small-blind",1),P(bb,"big-blind",2)),
 straddle_variant="none", ranges=tuple((W((2*i,2*i+1),1),) for i in range(n)),
 sizing_rules=(),max_raises=3,max_deals=1,max_nodes=1000,short_all_in_reopens=False,
 continuation=K("terminal-table","independent-C3I1-1","supplied",{}, {}, ()))
 v.update(kw)
 return C(**v)
labels = {
2:("BTN/SB","BB"),3:("BTN","SB","BB"),4:("CO","BTN","SB","BB"),
5:("HJ","CO","BTN","SB","BB"),6:("UTG","HJ","CO","BTN","SB","BB"),
7:("UTG","MP","HJ","CO","BTN","SB","BB"),
8:("UTG","UTG+1","MP","HJ","CO","BTN","SB","BB"),
9:("UTG","UTG+1","MP","LJ","HJ","CO","BTN","SB","BB")}
for n in range(2,10):
 for b in range(n):
  c=cfg(n,b); sb=b if n==2 else (b+1)%n; bb=(sb+1)%n
  order=tuple((bb+i)%n for i in range(1,n+1))
  assert tuple(_position_map(c)[s] for s in order)==labels[n]
  ok("canonical-position-rotation")
  variants=[("none",())]
  if n>=3:
   variants += [("standard",(P((bb+1)%n,"straddle",4),))]
   variants += [("mississippi",(P(s,"straddle",5),)) for s in range(n) if s not in (sb,bb)]
  if n>=4: variants += [("double",(P((bb+1)%n,"straddle",4),P((bb+2)%n,"straddle",8)))]
  for variant, extra in variants:
   # Interleave uniform antes with reversed blind declaration order.
   posts=(c.forced_posts[1],P(0,"ante",2),c.forced_posts[0])+tuple(P(s,"ante",2) for s in range(1,n))+extra
   cc=replace(c,forced_posts=posts,straddle_variant=variant)
   total=[0]*n; street=[0]*n; rem=list(cc.starting_stacks)
   for post in posts:
    total[post.seat]+=post.amount; rem[post.seat]-=post.amount
    if post.kind!="ante": street[post.seat]+=post.amount
   anchor=extra[-1].seat if extra else bb
   for short in [None]+(list(range(n)) if n>=3 else []):
    stacks=list(cc.starting_stacks)
    if short is not None: stacks[short]=total[short]
    case=replace(cc,starting_stacks=tuple(stacks))
    rr=root(case); dd=rr.child(Action("DEAL",0))
    expect_rem=tuple(stacks[s]-total[s] for s in range(n))
    expect_pending=tuple((anchor+i)%n for i in range(1,n+1) if expect_rem[(anchor+i)%n]>0)
    assert rr.total_contributed==tuple(total) and rr.street_committed==tuple(street)
    assert rr.remaining==expect_rem and rr.pot==sum(total)
    assert rr.last_raise_increment==(extra[-1].amount if extra else 2)
    assert rr.can_raise==tuple(x>0 for x in expect_rem)
    assert dd.pending==expect_pending and dd.current_player()==expect_pending[0]
    assert rr.history==() and rr.raise_count==0 and rr.private_deal is None
    assert dd.legal_actions()[:2]==(Action("FOLD"),Action("CALL",min(max(street),street[dd.current_player()]+expect_rem[dd.current_player()]))) if street[dd.current_player()]<max(street) else dd.legal_actions()[0]==Action("CHECK")
    assert root(case)==rr
    ok("ledger-variant-ante-exact-all-in")
base=cfg()
for name in ("num_players","button","max_raises","max_deals","max_nodes"):
 for value in (True,False,-1,1.5,"2",None):
  reject("strict-numerics",lambda name=name,value=value:replace(base,**{name:value}))
for name in ("max_raises","max_deals","max_nodes"):
 reject("strict-bounds",lambda name=name:replace(base,**{name:0}))
for kw in (dict(num_players=1),dict(num_players=10),dict(button=6),
 dict(starting_stacks=(100,)*5),dict(starting_stacks=[100]*6),dict(starting_stacks=(True,)*6),
 dict(starting_stacks=(0,)*6),dict(ranges=base.ranges[:5]),dict(ranges=((),)+base.ranges[1:]),
 dict(short_all_in_reopens=1),dict(version="bad"),dict(continuation=None),
 dict(forced_posts=list(base.forced_posts)),dict(forced_posts=()),
 dict(forced_posts=base.forced_posts*2),dict(forced_posts=(P(2,"small-blind",1),P(1,"big-blind",2))),
 dict(forced_posts=base.forced_posts+(P(6,"ante",1),)),dict(starting_stacks=(1,1,100,100,100,100)),
 dict(forced_posts=(P(0,"small-blind",3),P(1,"big-blind",2))),
 dict(forced_posts=(P(0,"small-blind",0),P(1,"big-blind",2)))):
 reject("strict-config",lambda kw=kw:replace(base,**kw))
for antes in ((P(1,"ante",1),),tuple(P(s,"ante",1+(s==3)) for s in range(6)),
 tuple(P(s,"ante",1) for s in range(5)),tuple(P(0,"ante",1) for s in range(6))):
 reject("invalid-antes",lambda antes=antes:replace(base,forced_posts=base.forced_posts+antes))
for variant, extra in (("bad",()),("none",(P(2,"straddle",4),)),("standard",()),
 ("standard",(P(3,"straddle",4),)),("standard",(P(2,"straddle",2),)),
 ("double",(P(3,"straddle",4),P(2,"straddle",8))),("double",(P(2,"straddle",4),P(3,"straddle",4))),
 ("mississippi",(P(0,"straddle",4),)),("mississippi",(P(1,"straddle",4),))):
 reject("invalid-straddles",lambda variant=variant,extra=extra:replace(base,straddle_variant=variant,forced_posts=base.forced_posts+extra))
reject("HU-standard",lambda:cfg(2,straddle_variant="standard",forced_posts=(P(0,"small-blind",1),P(1,"big-blind",2),P(0,"straddle",4))))
reject("three-seat-double",lambda:cfg(3,straddle_variant="double"))
reject("degenerate-posts",lambda:cfg(2,starting_stacks=(1,100)))
for cards in ((0,52),(False,2),(1,1),(-1,2)):
 reject("invalid-cards",lambda cards=cards:replace(base,ranges=((W(cards,1),),)+base.ranges[1:]))
for weight in (True,0,-1,float("inf"),float("nan")):
 reject("invalid-weight",lambda weight=weight:W((0,1),weight))
reject("duplicate-combos",lambda:replace(base,ranges=((W((0,1),1),W((1,0),2)),)+base.ranges[1:],max_deals=2))
rr=((W((0,1),Fraction(1,10)),W((2,3),Fraction(2,10))),
 (W((4,5),Fraction(3,10)),W((0,6),Fraction(1,10))))
c=cfg(2,ranges=rr,max_deals=4)
expected=((((0,1),(4,5)),Fraction(3,11)),(((2,3),(4,5)),Fraction(6,11)),(((2,3),(0,6)),Fraction(2,11)))
assert deals(c)==expected and deals(c)==deals(c)
assert all(isfinite(p) and p>=0 for _,p in root(c).chance_outcomes())
assert abs(sum(p for _,p in root(c).chance_outcomes())-1)<1e-12
ok("exact-mass")
reject("product-bound-before-pruning",lambda:replace(c,max_deals=3))
reject("all-blocked",lambda:cfg(2,ranges=((W((0,1),1),),(W((0,2),1),))))
reject("chance-node-bound",lambda:root(replace(c,max_nodes=3)))
assert len(root(replace(c,max_nodes=4)).chance_outcomes())==3
ok("chance-node-bound-equality")
for expr in ({},{"unit":"big-blinds","value":True},{"unit":"big-blinds","value":float("nan")},
 {"unit":"all-in","extra":1},{"unit":"big-blinds","value":3,"extra":1}):
 reject("strict-sizing",lambda expr=expr:R("UTG",0,0,"NA",(expr,)))
r=R("UTG",0,0,"NA",({"unit":"big-blinds","value":3},))
reject("duplicate-sizing-key",lambda:replace(base,sizing_rules=(r,r)))
reject("noncanonical-sizing-position",lambda:replace(base,sizing_rules=(replace(r,position="BAD"),)))
source={"unit":"big-blinds","value":3}
r=R("UTG",0,0,"NA",(source,)); h=hash(r); source["value"]=9
assert r.expressions[0]["value"]==3 and hash(r)==h
def assign_expression():
 r.expressions[0]["value"]=9
reject("mapping-assignment",assign_expression)
print("PASS COUNTS",counts)
print("TOTAL PASS CASES",sum(counts.values()))
# Independently reproduce accepted malformed inputs and mutable sizing.
bad=replace(base,forced_posts=base.forced_posts+(P(2,"not-a-post",7),))
br=root(bad)
print("BLOCKER unknown forced-post kind accepted:",br.pot,br.street_committed)
deal=tuple((2*i,2*i+1) for i in range(6))
cont=K("showdown-ranks","bool-order","supplied",{}, {deal:(1,2,3,4,5,6)},(False,True,2,3,4,5))
bad=replace(base,continuation=cont)
print("BLOCKER bool odd-chip seats accepted:",bad.continuation.odd_chip_order)
state=root(replace(base,sizing_rules=(r,))).child(Action("DEAL",0))
before=state.legal_actions(); key_before=state.information_state_key(2)
r.expressions[0]._data["value"]=4
after=state.legal_actions(); key_after=state.information_state_key(2)
equal=R("UTG",0,0,"NA",({"unit":"big-blinds","value":4},))
assert before!=after and key_before!=key_after and r==equal
print("BLOCKER mutable sizing:",before,"=>",after)
print("BLOCKER hash contract: equal rules =",r==equal,"equal hashes =",hash(r)==hash(equal))

PY
```

Exit 0, exact output:
```text
PASS COUNTS {'canonical-position-rotation': 44, 'ledger-variant-ante-exact-all-in': 2608, 'strict-numerics': 30, 'strict-bounds': 3, 'strict-config': 20, 'invalid-antes': 4, 'invalid-straddles': 9, 'HU-standard': 1, 'three-seat-double': 1, 'degenerate-posts': 1, 'invalid-cards': 4, 'invalid-weight': 5, 'duplicate-combos': 1, 'exact-mass': 1, 'product-bound-before-pruning': 1, 'all-blocked': 1, 'chance-node-bound': 1, 'chance-node-bound-equality': 1, 'strict-sizing': 5, 'duplicate-sizing-key': 1, 'noncanonical-sizing-position': 1, 'mapping-assignment': 1}
TOTAL PASS CASES 2744
BLOCKER unknown forced-post kind accepted: 10 (1, 2, 7, 0, 0, 0)
BLOCKER bool odd-chip seats accepted: (False, True, 2, 3, 4, 5)
BLOCKER mutable sizing: (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=2), Action(kind='RAISE', amount=6), Action(kind='RAISE', amount=100)) => (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=2), Action(kind='RAISE', amount=8), Action(kind='RAISE', amount=100))
BLOCKER hash contract: equal rules = True equal hashes = False
```

Probe correction disclosure: the initial run was identical except that the three lines defining/calling assign_expression were instead:
```python
reject("mapping-assignment",lambda:r.expressions[0].__setitem__("value",9))
```
That run exited 1 at stdin line 126 with:
```text
AttributeError: '_FrozenExpression' object has no attribute '__setitem__'. Did you mean: '__getitem__'?
```
This was an auditor exception-handling mistake, not a production defect. It was corrected to ordinary assignment and the entire matrix rerun successfully.

## Explicit seat-0 recovery and supplementary probes

```sh
PYTHONDONTWRITEBYTECODE=1 uv run python - <<'PY'
from dataclasses import replace
from poker_solver.nplayer_preflop import NPlayerPreflopConfig as C, NPlayerPreflopContinuation as K, create_nplayer_preflop_root as root
from poker_solver.game_structure import ForcedPost as P
from poker_solver.preflop import WeightedCombo as W
from poker_solver.model import Action
c=C('nplayer-preflop-v1',6,5,(3,100,100,100,100,100),tuple(P(s,'ante',2) for s in range(6))+(P(0,'small-blind',1),P(1,'big-blind',2)),'none',tuple((W((2*s,2*s+1),1),) for s in range(6)),(),3,1,1000,False,K('terminal-table','C3I1-1-explicit-seat-0','supplied',{}, {}, ()))
r=root(c); d=r.child(Action('DEAL',0))
assert r.remaining==(0,96,98,98,98,98) and d.pending==(2,3,4,5,1)
assert not r.can_raise[0]
print('PASS explicit seat 0:',c.starting_stacks,r.total_contributed,r.remaining,d.pending)
for kind in (None,123,'bogus'):
 x=replace(c,forced_posts=c.forced_posts+(P(2,kind,7),))
 print('ACCEPTED invalid post kind',repr(kind),'root street',root(x).street_committed)
deal=tuple((2*s,2*s+1) for s in range(6))
for order in ((False,True,2,3,4,5),(0.0,1.0,2.0,3.0,4.0,5.0)):
 x=replace(c,continuation=K('showdown-ranks','strict-order','supplied',{}, {deal:(1,2,3,4,5,6)},order))
 print('ACCEPTED non-strict odd-chip order',x.continuation.odd_chip_order)
# A short all-in increments and exhausts max_raises=1.
bounded=replace(c,starting_stacks=(100,100,5,100,100,100),max_raises=1)
s=root(bounded).child(Action('DEAL',0))
s=s.child(Action('RAISE',3))
assert s.raise_count==1 and s.last_raise_increment==2
assert all(a.kind!='RAISE' for a in s.legal_actions())
print('PASS short-all-in max_raises bound:',s.raise_count,s.legal_actions())

PY
```

Exit 0, exact output:
```text
PASS explicit seat 0: (3, 100, 100, 100, 100, 100) (3, 4, 2, 2, 2, 2) (0, 96, 98, 98, 98, 98) (2, 3, 4, 5, 1)
ACCEPTED invalid post kind None root street (1, 2, 7, 0, 0, 0)
ACCEPTED invalid post kind 123 root street (1, 2, 7, 0, 0, 0)
ACCEPTED invalid post kind 'bogus' root street (1, 2, 7, 0, 0, 0)
ACCEPTED non-strict odd-chip order (False, True, 2, 3, 4, 5)
ACCEPTED non-strict odd-chip order (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)
PASS short-all-in max_raises bound: 1 (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=3))
```

The same supplementary command without its final max_raises block was also run first and produced the same first six output lines, exit 0.

## Audit hygiene and verdict

No src/, tests/, manifest, pre-existing evidence other than the two expressly assigned output paths, or git state was edited. No commit or git mutation command was run. Probes mutated only process-local Python objects. Final design, production and test hashes remained frozen.

Process deviation disclosed: initial instruction-file discovery accidentally used `find .. -name AGENTS.md -print` from the repository, so read-only filename enumeration extended outside the requested work directory. No outside file contents were read and no outside paths were written. A subsequent `rg --files --hidden -g AGENTS.md -g '!\\.git' .` stayed within the repository and found no AGENTS.md. This does not affect the frozen-code findings.

**FAIL.** B1, B2 and B3 are independently reproduced architecture blockers. The obsolete seat-index assertion and nonexistent manifest self-hash check are not blockers.
