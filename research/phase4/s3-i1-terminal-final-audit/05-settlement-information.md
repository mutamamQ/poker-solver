# CTA3A5 settlement/information final audit

status=COMPLETE_PASS
provider=openai-codex
auditor=CTA3A5
utc=2026-09-16T07:47:39Z
blocker_count=0

Candidate identity is exclusively the literal 11 raw SHA-256 rows in `/home/genomix-node/poker-solver/research/phase4/s3-i1-terminal-final-audit/CANDIDATE_MANIFEST.md`. Production audited: `src/poker_solver/nplayer_preflop.py`. No split settlement/information module was assumed. This is a fresh non-author audit execution; no candidate edits or commits were made.

## Identity and immutability

The first shell execution ran `pwd`, `test -f` on that exact absolute manifest, and `cat` on that manifest. Working directory output was `/home/genomix-node/poker-solver`; manifest existence succeeded. A Python regex read exactly 11 literal rows and independently hashed each file's raw bytes with `hashlib.sha256(Path(name).read_bytes())`, asserting equality. The same raw-byte calculation was repeated after tests and probes. Both passes matched all rows. Manifest/source/tests, STATE.txt, PROGRESS.md and git metadata were not written. No git commands were run. Only this report and the matching heartbeat were written in the repository; temporary probe files were under `/tmp` and removed after embedding.

Before (raw SHA-256 output):
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

After (independent raw SHA-256 output):
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

## Required focused suite

Executed from the repository, exit code 0:
```sh
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py
```
Raw pytest output:
```text
..............                                                           [100%]
14 passed in 0.19s
```

## Independent executed evidence and limits

The probe imports real production classes and roots directly. Its expected settlement oracle reconstructs integer contributions from declared forced posts and actor-labelled history; it never uses production settlement or information helpers as expected-value oracles. It counts contributed chip heights, refunds heights with a single contributor, groups identical contributing-seat sets, and divides each contested pot by independently selected eligible rank winners, applying integer remainder order. It compares exact Fraction utilities and all four normalized ledger fields at every checked terminal.

Hand arithmetic anchors: HU raise 6/fold contributes (6,2), refunds 4, matches (2,2), and produces utilities (2,-2). With uniform ante 1, an immediate HU fold loses 2 for seat 0. Four-player contributions (10,30,50,50) produce pots 40,60,40; ranks (4,3,2,1) award these to seats 0,1,2 respectively, giving utilities (30,30,-10,-50). Three contributions of 3 produce pot 9; two tied winners receive 5 and 4 in the supplied order, producing (2,1,-3) or (1,2,-3). The terminal-table oracle is the independently supplied complete utility vector (5/7,-5/7), which must be returned unchanged.

Ten malformed/missing cases were executed and rejected with ValueError, including absent leaf, wrong actor history lookup, nonzero sum, boolean, nonfinite, wrong utility length, malformed history, overlapping deal cards, absent rank coverage, and malformed ranks. This is not exhaustive malformed-input coverage. Extra unreachable terminal-table entries were not claimed to be rejected: architecture permits leaf-time missing-key validation.

For N=6 and N=9 every owner was checked with all opponent cards changed, then separately with hidden ranks changed, at initial and one-CALL public states. Hidden terminal-table values were changed separately at initial states; those entries were not claimed as complete leaf coverage. There were 75 equality/action comparisons plus owner-card sensitivity checks. This is bounded noninterference evidence, not exhaustive reachable-key equivalence.

The equal-stack HU RAISE6-FOLD comparison independently canonicalized legacy raw pot 8 to pot 4 via refund 4. The unequal-stack HU CALL2-RAISE7-RAISE20 comparison checked aligned decision prefixes, then independently verified generic closure, refund 13, contributions (7,7), remaining (13,0), and utilities (7,-7). Legacy leaves seat 1 actionable with zero chips; its reported FOLD/CALL7 suffix was observed and excluded, not followed or asserted equivalent.

Complete action traversals used singleton deals, stacks 3, no antes/straddles/sizing rules, max_raises 1, and ranks i%3. Every reachable terminal was checked: N=2: 6 leaves/10 dealt-subtree nodes; N=3: 22/40; N=6: 696/1360; N=9: 19426/38596. Total: 20150 terminal leaves. Node counts exclude each CHANCE root; its sole DEAL edge was executed. These are complete tiny trees only; no claim of exhaustive configurations, arbitrary range sizes, full HU equivalence, solver/CFR correctness, API coverage, full regression, or large-game performance is made. Runtime dependencies such as legacy preflop and shared game_structure were imported from this workspace; they are not additional manifest identity rows and were not separately frozen by this audit.

No reproducible blocker was observed within this settlement/information scope. COMPLETE_PASS is scoped to the exact candidate and executed evidence here, not acceptance of unexecuted architectural stages.

## Exact successful temporary probe source

Executed command (Python and enclosing shell completed with exit code 0):
```sh
PYTHONDONTWRITEBYTECODE=1 uv run python /tmp/CTA3A5_probe.py > /tmp/CTA3A5_probe.out 2>&1
cat /tmp/CTA3A5_probe.out
```

```python
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from poker_solver.nplayer_preflop import NPlayerPreflopConfig as Config, NPlayerPreflopContinuation as Cont, NPlayerPreflopPublicAction as Public, NPlayerPreflopSizingRule as Rule, create_nplayer_preflop_root as root
from poker_solver.preflop import WeightedCombo, PreflopConfig, Continuation, create_preflop_root
from poker_solver.game_structure import ForcedPost
from poker_solver.model import Action as A, TERMINAL


def config(stacks, ranks=None, button=None, ante=0, rules=(), deal=None, cont=None, raises=4):
    n=len(stacks); button=(0 if n==2 else n-1) if button is None else button
    sb=button if n==2 else (button+1)%n; bb=(sb+1)%n
    deal=deal or tuple((2*i,2*i+1) for i in range(n))
    posts=tuple(ForcedPost(i,'ante',ante) for i in range(n)) if ante else ()
    posts+=(ForcedPost(sb,'small-blind',1),ForcedPost(bb,'big-blind',2))
    cont=cont or Cont('showdown-ranks','CTA3A5','supplied',{}, {deal: ranks or tuple(range(n))},tuple(range(n)))
    return Config('nplayer-preflop-v1',n,button,tuple(stacks),posts,'none',tuple((WeightedCombo(c,F(1)),) for c in deal),rules,raises,1,1000000,False,cont)


def play(c, actions):
    s=root(c).child(A('DEAL',0))
    for a in actions: s=s.child(a)
    return s


def oracle(s):
    # Reconstruct payments from input posts and public actions, never terminal ledgers.
    n=s.config.num_players; paid=[0]*n; street=[0]*n; folded=set()
    for p in s.config.forced_posts:
        paid[p.seat]+=p.amount
        if p.kind!='ante': street[p.seat]+=p.amount
    for h in s.history:
        i=h.actor; a=h.action
        if a.kind=='FOLD': folded.add(i)
        elif a.kind in ('CALL','RAISE'):
            paid[i]+=a.amount-street[i]; street[i]=a.amount
    # Each contributed chip height forms its own pot. A solitary contributor
    # receives that chip back; contested chips go only to eligible rank winners.
    matched=paid.copy(); refund=[0]*n; awards=[0]*n
    ranks=s.config.continuation.showdown_ranks[s.private_deal]
    order=s.config.continuation.odd_chip_order
    # Combine adjacent identical contributor sets before odd-chip division.
    buckets={}
    for height in range(1,max(paid)+1):
        contributors=tuple(i for i in range(n) if paid[i]>=height)
        if len(contributors)==1:
            i=contributors[0]; refund[i]+=1; matched[i]-=1
        else: buckets[contributors]=buckets.get(contributors,0)+len(contributors)
    for contributors,amount in buckets.items():
        eligible=[i for i in contributors if i not in folded]
        best=max(ranks[i] for i in eligible)
        winners=[i for i in order if i in eligible and ranks[i]==best]
        q,r=divmod(amount,len(winners))
        for j,i in enumerate(winners): awards[i]+=q+(j<r)
    utilities=tuple(F(awards[i]+refund[i]-paid[i]) for i in range(n))
    ledger=(sum(matched),tuple(street[i]-refund[i] for i in range(n)),tuple(matched),tuple(s.config.starting_stacks[i]-paid[i]+refund[i] for i in range(n)))
    return utilities,ledger


def check(s, expected=None):
    assert s.current_player()==TERMINAL
    u,ledger=oracle(s)
    assert s.terminal_values==u,(s.history,s.terminal_values,u)
    assert all(type(x) is F for x in s.terminal_values)
    assert sum(u)==0
    assert (s.pot,s.street_committed,s.total_contributed,s.remaining)==ledger
    assert s.pending==() and s.legal_actions()==()
    if expected is not None: assert u==expected
    return u

r6=Rule('BTN/SB',0,0,'NA',({'unit':'big-blinds','value':3},))
s=play(config((20,20),rules=(r6,)),[A('RAISE',6),A('FOLD')])
print('equal-stack fold/refund:',check(s,(F(2),F(-2))),s.total_contributed,s.remaining)
s=play(config((20,20),ante=1),[A('FOLD')])
print('ante fold:',check(s,(F(-2),F(2))))
c=config((10,30,50,100),ranks=(4,3,2,1),button=1)
s=play(c,[A('RAISE',10),A('RAISE',30),A('RAISE',50),A('CALL',50)])
# Pots 40 to seat0, 60 to seat1, 40 to seat2: awards=(40,60,40,0).
print('multiple side pots distinct winners:',check(s,(F(30),F(30),F(-10),F(-50))))
c=config((20,20,20),ranks=(10,10,1),button=0,ante=1)
for order,expected in [((0,1,2),(2,1,-3)),((1,0,2),(1,2,-3))]:
    cc=replace(c,continuation=replace(c.continuation,odd_chip_order=order))
    s=play(cc,[A('CALL',2),A('CALL',2),A('CHECK')])
    print('tie odd-chip',order,check(s,tuple(map(F,expected))))

# Arbitrary supplied total utilities must remain exact and must not have
# contributions subtracted a second time.
c=config((20,20)); deal=tuple(r[0].cards for r in c.ranges)
h=(Public(0,A('CALL',2)),Public(1,A('CHECK')))
v=(F(5,7),F(-5,7))
def table(t): return Cont('terminal-table','CTA3A5','supplied',t,{},())
tc=replace(c,continuation=table({(deal,h):v}))
s=play(tc,[A('CALL',2),A('CHECK')]); assert s.terminal_values==v
assert s.total_contributed==(2,2) and s.remaining==(18,18)
print('terminal-table exact:',s.terminal_values)
rejections=0
def reject(name,fn):
    global rejections
    try: fn()
    except ValueError as e:
        rejections+=1; print('rejected',name,type(e).__name__,str(e)); return
    raise AssertionError('accepted '+name)
reject('missing leaf',lambda:play(replace(c,continuation=table({})),[A('CALL',2),A('CHECK')]))
reject('wrong actor key missing',lambda:play(replace(c,continuation=table({(deal,(Public(1,A('CALL',2)),Public(0,A('CHECK')))):v})),[A('CALL',2),A('CHECK')]))
for name,values in [('nonzero sum',(F(1),F(0))),('bool',(True,-1)),('nonfinite',(float('inf'),float('-inf'))),('wrong length',(F(0),))]:
    reject(name,lambda values=values:replace(c,continuation=table({(deal,h):values})))
reject('malformed history',lambda:table({(deal,(A('CHECK'),)):v}))
reject('overlapping cards',lambda:replace(c,continuation=table({(((0,1),(1,2)),h):v})))
reject('missing ranks',lambda:replace(c,continuation=replace(c.continuation,showdown_ranks={})))
reject('malformed ranks',lambda:replace(c,continuation=replace(c.continuation,showdown_ranks={deal:(True,2)})))
print('malformed/missing rejection count:',rejections)

# For every owner, change all opponent cards while fixing own cards; separately
# change hidden ranks and hidden terminal values. Compare initial and one-action
# public states, including keys for nonacting owners.
comparisons=0
for n in (6,9):
    base=tuple((2*i,2*i+1) for i in range(n))
    for owner in range(n):
        changed=tuple(base[i] if i==owner else (20+2*i,21+2*i) for i in range(n))
        c=config((5,)*n,deal=base)
        variants=[config((5,)*n,deal=changed),replace(c,continuation=replace(c.continuation,showdown_ranks={base:tuple(reversed(range(n)))}))]
        for other in variants:
            a=play(c,[]); b=play(other,[])
            for step in range(2):
                assert a.information_state_key(owner)==b.information_state_key(owner)
                assert a.legal_actions()==b.legal_actions(); comparisons+=1
                if step==0:
                    action=next(x for x in a.legal_actions() if x.kind=='CALL')
                    a=a.child(action); b=b.child(action)
        history=(Public(2,A('CALL',2)),)
        v1=(F(1,3),F(-1,3))+(F(0),)*(n-2)
        v2=tuple(-x for x in v1)
        a=play(replace(c,continuation=table({(base,history):v1})),[])
        b=play(replace(c,continuation=table({(base,history):v2})),[])
        assert a.information_state_key(owner)==b.information_state_key(owner)
        assert a.legal_actions()==b.legal_actions(); comparisons+=1
        own=list(base); own[owner]=(48,49)
        b=play(config((5,)*n,deal=tuple(own)),[])
        assert play(c,[]).information_state_key(owner)!=b.information_state_key(owner)
    print('hidden cards/ranks/table noninterference N=',n,'all owners; owner-card sensitivity passed')
print('noninterference comparisons:',comparisons)

# Legacy is comparison subject only; expected normalization is literal arithmetic.
def legacy(c,expressions):
    return create_preflop_root(PreflopConfig(c.starting_stacks,(1,2),c.ranges,expressions,c.max_raises,1,1000000,False,Continuation('terminal-table',{},'CTA3A5'))).child(A('DEAL',0))
c=config((20,20),rules=(r6,)); old=legacy(c,({'unit':'big-blinds','value':3},{'unit':'all-in'})); new=play(c,[])
for action in [A('RAISE',6),A('FOLD')]:
    assert (old.pot,old.committed,old.total_contributed,old.remaining)==(new.pot,new.street_committed,new.total_contributed,new.remaining)
    assert old.legal_actions()==new.legal_actions()
    old=old.child(action); new=new.child(action)
assert old.pot==8 and old.remaining==(14,18)
assert old.returns()==new.returns()==(2.,-2.)
assert (old.pot-4,(old.committed[0]-4,old.committed[1]),(old.total_contributed[0]-4,old.total_contributed[1]),(old.remaining[0]+4,old.remaining[1]))==(new.pot,new.street_committed,new.total_contributed,new.remaining)
print('HU RAISE6-FOLD legacy raw pot 8 -> canonical 4; refund 4; utilities (2,-2)')
c=config((20,7),ranks=(2,1)); old=legacy(c,({'unit':'all-in'},)); new=play(c,[])
for action in [A('CALL',2),A('RAISE',7),A('RAISE',20)]:
    assert old.current_player()==new.current_player()
    assert old.legal_actions()==new.legal_actions()
    assert (old.pot,old.committed,old.total_contributed,old.remaining)==(new.pot,new.street_committed,new.total_contributed,new.remaining)
    old=old.child(action); new=new.child(action)
assert old.current_player()==1 and old.remaining[1]==0
assert new.current_player()==TERMINAL and new.remaining==(13,0) and new.total_contributed==(7,7)
check(new,(F(7),F(-7)))
print('HU CALL2-RAISE7-RAISE20: generic terminal refund 13 utilities (7,-7); legacy chipless actor',old.current_player(),'actions',old.legal_actions(),'; suffix excluded, not followed')

# Traverse every action edge for each tiny singleton-deal configuration.
for n in (2,3,6,9):
    c=config((3,)*n,ranks=tuple(i%3 for i in range(n)),raises=1)
    nodes=leaves=0
    def visit(s):
        global nodes,leaves
        nodes+=1
        if s.current_player()==TERMINAL:
            check(s); leaves+=1; return
        actions=s.legal_actions()
        assert actions
        for action in actions: visit(s.child(action))
    visit(play(c,[]))
    print('complete tiny tree N=',n,'stacks=3 max_raises=1 singleton deal ranks=i%3 decision+terminal nodes=',nodes,'leaves=',leaves)
print('ALL INDEPENDENT PROBES PASSED')
```

## Raw successful probe output

```text
equal-stack fold/refund: (Fraction(2, 1), Fraction(-2, 1)) (2, 2) (18, 18)
ante fold: (Fraction(-2, 1), Fraction(2, 1))
multiple side pots distinct winners: (Fraction(30, 1), Fraction(30, 1), Fraction(-10, 1), Fraction(-50, 1))
tie odd-chip (0, 1, 2) (Fraction(2, 1), Fraction(1, 1), Fraction(-3, 1))
tie odd-chip (1, 0, 2) (Fraction(1, 1), Fraction(2, 1), Fraction(-3, 1))
terminal-table exact: (Fraction(5, 7), Fraction(-5, 7))
rejected missing leaf ValueError missing continuation value for closed preflop leaf
rejected wrong actor key missing ValueError missing continuation value for closed preflop leaf
rejected nonzero sum ValueError terminal values must be finite and zero-sum
rejected bool ValueError invalid terminal-table entry
rejected nonfinite ValueError terminal values must be finite exact numbers
rejected wrong length ValueError terminal values must contain N utilities
rejected malformed history ValueError invalid terminal-table entry
rejected overlapping cards ValueError terminal-table deals must contain N disjoint combos
rejected missing ranks ValueError showdown ranks must cover exactly every compatible deal
rejected malformed ranks ValueError invalid showdown-ranks entry
malformed/missing rejection count: 10
hidden cards/ranks/table noninterference N= 6 all owners; owner-card sensitivity passed
hidden cards/ranks/table noninterference N= 9 all owners; owner-card sensitivity passed
noninterference comparisons: 75
HU RAISE6-FOLD legacy raw pot 8 -> canonical 4; refund 4; utilities (2,-2)
HU CALL2-RAISE7-RAISE20: generic terminal refund 13 utilities (7,-7); legacy chipless actor 1 actions (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=7)) ; suffix excluded, not followed
complete tiny tree N= 2 stacks=3 max_raises=1 singleton deal ranks=i%3 decision+terminal nodes= 10 leaves= 6
complete tiny tree N= 3 stacks=3 max_raises=1 singleton deal ranks=i%3 decision+terminal nodes= 40 leaves= 22
complete tiny tree N= 6 stacks=3 max_raises=1 singleton deal ranks=i%3 decision+terminal nodes= 1360 leaves= 696
complete tiny tree N= 9 stacks=3 max_raises=1 singleton deal ranks=i%3 decision+terminal nodes= 38596 leaves= 19426
ALL INDEPENDENT PROBES PASSED
```
