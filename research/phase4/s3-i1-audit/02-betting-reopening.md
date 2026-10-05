# C3I1-2 recovery audit: betting and reopening

Verdict: **FAIL — one P2 architecture acceptance blocker (permanent test coverage).**
No production betting/reopening defect was reproduced in this scope. The focused tests and all independent probes passed. This is not a runtime-failure finding.

Auditor: C3I1-2, fresh non-author recovery reviewer. Work directory: /home/genomix-node/poker-solver.
Authority: ARCHITECTURE_PHASE4_S3.md and research/phase4/s3-i1-audit/CANDIDATE_MANIFEST.md.
Scope: S3-I1 action order, straddles, callers/sizing, raise targets, reopening, closure, and chip conservation. S3-I2 integration and full-regression acceptance are not certified here.

## Frozen identity

Verified before review and again after tests/probes:

```text
a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6  ARCHITECTURE_PHASE4_S3.md
0e55fbce5f6934c8e2e63ee28ce9d01d9268792165d9318bc8c9ed03b5f73422  src/poker_solver/nplayer_preflop.py
d61a86d39f864d494f19a91698478c4af39b76d6ad0372321f18d69706349f69  tests/test_nplayer_preflop_betting.py
5a214b900a7ad1b61aa67cd294d7000e3eef0023f82bb834d1e94035f815a867  tests/test_nplayer_preflop_config.py
282112f2b88e57b1b8b25bbdd69d0f6fb90df714e92ccff80945f9724375e69d  tests/test_nplayer_preflop_information.py
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
```

All hashes match the frozen manifest. No source, test, existing evidence, or git-state edits were made. No git mutation commands were run. Python bytecode and pytest cache writes were disabled; probes ran through stdin. Only this new report and the assigned heartbeat were written.

## B1 — P2 acceptance blocker: required permanent straddle/betting coverage is incomplete

Architecture line 158 requires: “Permanent no/single/double/Mississippi fixtures must verify those differences and deterministic repeatability.”
Lines 265–266 explicitly allocate all straddle variants, limps, SB completion, and 3/4/5-bet+ coverage to the permanent S3-I1 suites.

The frozen config suite has no accepted double-straddle or Mississippi fixture. Its only Mississippi occurrence is the HU rejection case at tests/test_nplayer_preflop_config.py:128–136. The betting suite adds only the standard variant (line 131 onward). A search of every Python test identifies only the four frozen suites as direct users of the new module. There is no double-straddle declaration in those suites.

The betting suite also does not assert a sizing key that counts pre-raise limps/SB completion, and its named full-raise test stops at availability of the 4-bet (line 262), without taking it and reaching the 5-bet decision. Settlement does exercise a chain of full all-ins; that does not validate the missing per-position 5-bet sizing key.

Impact: the candidate lacks architecture-required permanent regression protection. The independent probes below verify current behavior but do not replace the specifically required permanent production-importing fixtures. This blocker is about acceptance evidence, not a claim that the implemented variants or raises fail.

Required resolution by the authorized test owner: add permanent accepted 6-player no/standard/double/Mississippi fixtures asserting exact ledgers, pending/first actor, legal actions, and repeatability (including all-in option exclusion); add exact pre-raise SB-completion caller-key and full 3/4/5-bet sizing traces. Re-run, re-freeze the test hashes, and obtain the required fresh verification. No repair was attempted under this read-only assignment.

## Behavioral findings

| Area | Independent result |
| --- | --- |
| HU/6/9 order | PASS; all button rotations, with additional N=3/4 operational-alias boundaries. |
| Straddles | PASS; 324 configurations spanning no/standard/double/Mississippi, every valid non-blind Mississippi seat, uniform antes, and exact all-in option seats. Both double-option seats all-in also tested. |
| Limp/SB completion | PASS; five pre-raise callers including SB select BB key (BB,0,5,NA); HU SB completion counts; a live all-in limper counts. |
| Exact sizing | PASS; near matches in each key dimension are excluded, absent exact key leaves only all-in raising, duplicate targets preserve declaration order. |
| IP/OOP | PASS; relation follows the last voluntary aggressor, including CO/BTN re-raises and SB squeeze followed by CO IP response. |
| Targets/context | PASS; absolute targets subtract own commitment once; ante money enters pot but not live wager/all-in street target; 50% pot rounding and previous-wager multiple agree; below-minimum non-all-in and oversized candidates are filtered without clamping. |
| 3/4/5-bets | PASS; CO6–BTN18–SBfold–BBfold–CO40–BTN80, followed by cap enforcement and closure. |
| Reopening | PASS; full raises restore entitlement. Consecutive short raises preserve only old pending AND old entitlement with reopens=false. Both policies checked. CHECK consumes entitlement. Full all-in after a short raise restores entitlement. |
| Closure/conservation | PASS; independent transfer/refund/pot-layer/tie/odd-chip oracle, exact terminal utility equality and zero sum, empty terminal pending/legal actions, bounded path depth. |

Important consecutive-short trace (six players, button 5, SB0=1, BB1=2): UTG2 raises to 6, HJ3 calls 6, CO4 all-in 7, BTN5 all-in 8. After CO7, pending=(5,0,1,2,3). After BTN8, pending=(0,1,2,3), increment remains 4 and raise_count=3. With reopens=false, entitlement is (True,True,False,False,False,False): seats 2/3 were pending before the second short raise but were already not entitled. With reopens=true, seats 0/1/2/3 are entitled. This distinguishes intersection from an implementation that incorrectly re-entitles every pending seat.

Code review: _initial_pending, _position_map, _relation, _cold_callers, legal_actions, child, and _settle were checked against architecture sections 3–8. legal_actions/child use the live-seat high-water mark rather than literally max(all commitments); no reachable discrepancy was found because a seat cannot fold while checking, and a folding seat must be below a surviving live wager. Terminal refunds were compared independently, not computed by importing production settlement helpers.

## Exact verification commands and results

All commands were executed in /home/genomix-node/poker-solver.

```bash
sha256sum ARCHITECTURE_PHASE4_S3.md src/poker_solver/nplayer_preflop.py
sha256sum ARCHITECTURE_PHASE4_S3.md src/poker_solver/nplayer_preflop.py tests/test_nplayer_preflop_*.py
```

Exit 0; hashes are listed above.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py
```

Exit 0: `26 passed in 0.30s`.

```bash
rg -n 'double|mississippi|complet|limp|5.bet|cold_callers|short_all_in|pending|can_raise' tests/test_nplayer_preflop_*.py
rg -n 'nplayer_preflop|nplayer-preflop' tests --glob '*.py'
rg -n 'Permanent no|S3-I1|limps, SB completes|At least the 6-player' ARCHITECTURE_PHASE4_S3.md
```

Each exited 0. Results establish B1: no double fixture; Mississippi only in HU rejection; direct new-module test users are the four frozen suites. The architecture matches include lines 158, 255, 261, and 290. Full suite contents, not only these searches, were read.

The base independent probe was run once, then re-run with supplemental cases for CHECK entitlement, two all-in straddle options, absent exact key, and immediate unmatched refund. The exact final command follows. The initial command was the same heredoc ending immediately before the comment “Reuse only auditor-defined helpers” below; it exited 0 with 6,369 edges and 876 terminals. The repeated prefix is not counted twice in coverage totals.

Final command: exit 0. Output:

```text
PASS rotated HU/3/4/6/9 roots, four variants, every non-blind Mississippi seat, all-in options: 324
PASS limp/SB completion/all-in caller counts, exact keys, IP/OOP, dedup order, absolute targets, 3/4/5-bets, cap
PASS sizing context, ante separation, minimum/full/short all-in boundaries, no clamping
PASS consecutive short all-ins: old pending AND old entitlement; full all-in restores entitlement
PASS deterministic 540 random legal paths, independent transition/refund/layer/award oracles
TOTAL {'roots': 324, 'edges': 6369, 'terminals': 876}
PASS CHECK entitlement, two forced-all-in straddles, absent exact key, immediate closure/refund
FINAL TOTAL {'roots': 324, 'edges': 6381, 'terminals': 880}
```

The 540 generated paths use a fixed seed and tiny single-deal inputs; they are bounded adversarial sampling, not exhaustive tree verification. Fixed hand-authored assertions supplement the transition oracle. No production private helpers or production settlement helpers are used as expected-value oracles.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from dataclasses import replace
from fractions import Fraction
import random
from poker_solver.game_structure import ForcedPost
from poker_solver.model import Action, TERMINAL
from poker_solver.preflop import WeightedCombo
from poker_solver.nplayer_preflop import (
    NPlayerPreflopConfig as Config, NPlayerPreflopContinuation as Continuation,
    NPlayerPreflopSizingRule as Rule, create_nplayer_preflop_root as root,
)
checks = {"roots": 0, "edges": 0, "terminals": 0}
def cfg(n, button=None, variant="none", straddler=None, stacks=None,
        rules=(), reopen=False, ante=0, cap=4):
    button = (0 if n == 2 else n-1) if button is None else button
    sb = button if n == 2 else (button+1)%n
    bb = (button+1)%n if n == 2 else (button+2)%n
    posts = tuple(ForcedPost(i, "ante", ante) for i in range(n)) if ante else ()
    posts += (ForcedPost(sb,"small-blind",1), ForcedPost(bb,"big-blind",2))
    if variant == "standard": posts += (ForcedPost((bb+1)%n,"straddle",4),)
    if variant == "double":
        posts += (ForcedPost((bb+1)%n,"straddle",4), ForcedPost((bb+2)%n,"straddle",8))
    if variant == "mississippi":
        posts += (ForcedPost(button if straddler is None else straddler,"straddle",4),)
    deal = tuple((2*i,2*i+1) for i in range(n))
    return Config("nplayer-preflop-v1",n,button,stacks or (100,)*n,posts,variant,
        tuple((WeightedCombo(c,Fraction(1)),) for c in deal),rules,cap,1,100000,
        reopen,Continuation("showdown-ranks","C3I1-2 independent probe","supplied",
        {},{deal:tuple(i%3 for i in range(n))},tuple(reversed(range(n)))))
def rule(p,r,c,rel,*targets):
    return Rule(p,r,c,rel,tuple({"unit":"big-blinds","value":x/2} for x in targets))
def dealt(c): return root(c).child(Action("DEAL",0))
def raises(s): return tuple(a.amount for a in s.legal_actions() if a.kind=="RAISE")
def invariant(s):
    n=s.config.num_players
    assert s.pot==sum(s.total_contributed)
    assert all(s.remaining[i]+s.total_contributed[i]==s.config.starting_stacks[i] for i in range(n))
    assert all(0<=s.street_committed[i]<=s.total_contributed[i] for i in range(n))
    assert len(s.pending)==len(set(s.pending))
    assert all(not s.folded[i] and s.remaining[i]>0 for i in s.pending)
    if s.current_player()!=TERMINAL: assert s.current_player()==s.pending[0]
def edge(s,a):
    invariant(s)
    n=s.config.num_players; p=s.current_player()
    H=max(s.street_committed); own=s.street_committed[p]
    pay=a.amount-own if a.kind in ("CALL","RAISE") else 0
    rem=list(s.remaining); rem[p]-=pay
    contrib=list(s.total_contributed); contrib[p]+=pay
    street=list(s.street_committed); street[p]+=pay
    folded=list(s.folded); folded[p] |= a.kind=="FOLD"
    entitled=list(s.can_raise); entitled[p]=False
    pending=list(s.pending[1:]); increment=s.last_raise_increment
    count=s.raise_count
    if a.kind=="RAISE":
        assert a.amount>H and (a.amount>=H+increment or rem[p]==0)
        pending=[(p+d)%n for d in range(1,n) if not folded[(p+d)%n] and rem[(p+d)%n]>0]
        full=a.amount-H>=increment
        if full: increment=a.amount-H
        entitled=[i in pending and (full or s.config.short_all_in_reopens or
            (i in s.pending and s.can_raise[i])) for i in range(n)]
        count+=1
    t=s.child(a); checks["edges"]+=1
    assert t.raise_count==count and t.last_raise_increment==increment
    assert t.folded==tuple(folded) and t.can_raise==tuple(entitled)
    assert t.history[-1].actor==p and t.history[-1].action==a
    closing=sum(not x for x in folded)==1 or not pending
    assert (t.current_player()==TERMINAL)==closing
    if closing:
        checks["terminals"]+=1
        # Independent refund and integer-layer award oracle, no production helpers.
        top=sorted(contrib,reverse=True)
        refund=top[0]-top[1]
        if refund:
            leader=contrib.index(top[0]); contrib[leader]-=refund
            rem[leader]+=refund; street[leader]-=refund
        awards=[0]*n; previous=0
        ranks=s.config.continuation.showdown_ranks[s.private_deal]
        for level in sorted(set(contrib)-{0}):
            involved=[i for i in range(n) if contrib[i]>=level]
            eligible=[i for i in involved if not folded[i]]
            assert eligible
            winners=[i for i in eligible if ranks[i]==max(ranks[j] for j in eligible)]
            amount=(level-previous)*len(involved)
            q,r=divmod(amount,len(winners))
            for i in winners: awards[i]+=q
            ordered=[i for i in s.config.continuation.odd_chip_order if i in winners]
            for i in ordered[:r]: awards[i]+=1
            previous=level
        expected=tuple(Fraction(rem[i]+awards[i]-s.config.starting_stacks[i]) for i in range(n))
        assert t.terminal_values==expected and sum(expected)==0
        assert t.pending==() and t.legal_actions()==()
    else:
        assert t.pending==tuple(pending)
    assert t.remaining==tuple(rem) and t.total_contributed==tuple(contrib)
    assert t.street_committed==tuple(street)
    invariant(t)
    return t
def play(s,kind,amount=0): return edge(s,Action(kind,amount))
def finish(s):
    while s.current_player()!=TERMINAL:
        a=next(a for a in s.legal_actions() if a.kind in ("CALL","CHECK"))
        s=edge(s,a)
    return s

# Every button rotation; every legal Mississippi seat; options with/without chips.
for n in (2,3,4,6,9):
    for button in range(n):
        sb=button if n==2 else (button+1)%n
        bb=(button+1)%n if n==2 else (button+2)%n
        variants=[("none",None)]
        if n>=3:
            variants += [("standard",None)]
            variants += [("mississippi",i) for i in range(n) if i not in (sb,bb)]
        if n>=4: variants += [("double",None)]
        for variant,straddler in variants:
            c=cfg(n,button,variant,straddler,ante=1)
            anchor=next((p.seat for p in reversed(c.forced_posts) if p.kind=="straddle"),bb)
            for allin in (False,True):
                if allin and n==2: continue
                cc=c
                if allin:
                    stacks=list(c.starting_stacks)
                    stacks[anchor]=sum(p.amount for p in c.forced_posts if p.seat==anchor)
                    cc=replace(c,starting_stacks=tuple(stacks))
                s=dealt(cc); checks["roots"]+=1
                expected=tuple((anchor+d)%n for d in range(1,n+1) if s.remaining[(anchor+d)%n]>0)
                assert s.pending==expected and s.can_raise==tuple(x>0 for x in s.remaining)
                assert s.last_raise_increment==max(s.street_committed)
                assert s==dealt(cc)
                finish(s)
print("PASS rotated HU/3/4/6/9 roots, four variants, every non-blind Mississippi seat, all-in options:",checks["roots"])

# Limps including SB completion; exact match excludes each wrong key dimension.
rules=(rule("BB",0,5,"NA",14,12,14),rule("BB",0,4,"NA",16),
       rule("BB",1,5,"NA",18),rule("BB",0,5,"IP",20),rule("SB",0,5,"NA",22))
s=dealt(cfg(6,rules=rules))
for i in (2,3,4,5,0):
    assert s.current_player()==i
    s=play(s,"CALL",2)
assert raises(s)==(14,12,100),raises(s)
s=play(s,"RAISE",14)
assert s.street_committed[1]==14 and s.remaining[1]==86
finish(s)
# HU SB completion counts; BB is NA before voluntary raise.
s=play(dealt(cfg(2,rules=(rule("BB",0,1,"NA",6),))),"CALL",2)
assert raises(s)==(6,100)
finish(s)
# All-in limper is live and counts, even though not actionable.
s=play(dealt(cfg(6,stacks=(100,100,2,100,100,100),
    rules=(rule("HJ",0,1,"NA",8),))),"CALL",2)
assert raises(s)==(8,100)
# 3/4/5-bet chain, relation flips relative to last aggressor; exact raise cap.
rules=(rule("CO",0,0,"NA",6),rule("BTN",1,0,"IP",18),
       rule("CO",2,0,"OOP",40),rule("BTN",3,0,"IP",80))
s=dealt(cfg(4,rules=rules))
for kind,amount in (("RAISE",6),("RAISE",18),("FOLD",0),("FOLD",0),
                    ("RAISE",40),("RAISE",80)):
    s=play(s,kind,amount)
assert s.raise_count==4 and not raises(s)
finish(s)
# Squeeze resets caller count, consumes SB's own commitment only once.
rules=(rule("CO",0,0,"NA",6),rule("SB",1,1,"OOP",20),
       rule("CO",2,0,"IP",40),rule("CO",2,1,"IP",42))
s=dealt(cfg(4,rules=rules))
for k,v in (("RAISE",6),("CALL",6),("RAISE",20),("FOLD",0)):
    s=play(s,k,v)
assert raises(s)==(40,100)
finish(s)
print("PASS limp/SB completion/all-in caller counts, exact keys, IP/OOP, dedup order, absolute targets, 3/4/5-bets, cap")

# Pot context includes antes; 50% pot: H=2, P=9, call=2 => round(2+5.5)=8.
s=dealt(cfg(6,ante=1,rules=(Rule("UTG",0,0,"NA",
    ({"unit":"pot-percent","value":50},{"unit":"previous-bet-multiple","value":4},
     {"unit":"big-blinds","value":1.5},{"unit":"big-blinds","value":101},
     {"unit":"all-in"})),)))
assert raises(s)==(8,99), raises(s)
finish(play(s,"RAISE",8))
# Short all-in only below-minimum raise, with exact minimum accepted too.
for stack,expected in ((3,(3,)),(4,(4,)),(5,(4,5))):
    s=dealt(cfg(2,stacks=(stack,100),rules=(rule("BTN/SB",0,0,"NA",3,4,101),)))
    assert raises(s)==expected,(stack,raises(s))
    finish(play(s,"RAISE",expected[0]))
print("PASS sizing context, ante separation, minimum/full/short all-in boundaries, no clamping")

# Two consecutive short raises exercise pending-but-not-entitled callers.
for reopen in (False,True):
    rules=(rule("UTG",0,0,"NA",6),)
    s=dealt(cfg(6,stacks=(100,100,100,100,7,8),rules=rules,reopen=reopen))
    for k,v in (("RAISE",6),("CALL",6),("RAISE",7)):
        s=play(s,k,v)
    assert s.pending==(5,0,1,2,3)
    assert s.can_raise==((True,True,True,True,False,True) if reopen else
                         (True,True,False,False,False,True))
    s=play(s,"RAISE",8)
    assert s.pending==(0,1,2,3)
    assert s.can_raise==((True,True,True,True,False,False) if reopen else
                         (True,True,False,False,False,False))
    assert s.last_raise_increment==4 and s.raise_count==3
    finish(s)
    # A full all-in after a short raise restores everyone's entitlement.
    s=dealt(cfg(6,stacks=(100,100,100,100,7,12),rules=rules,reopen=reopen))
    for k,v in (("RAISE",6),("CALL",6),("RAISE",7),("RAISE",12)):
        s=play(s,k,v)
    assert s.can_raise==(True,True,True,True,False,False)
    assert s.last_raise_increment==5
    finish(s)
print("PASS consecutive short all-ins: old pending AND old entitlement; full all-in restores entitlement")

# Bounded independent transition/settlement sweeps, fixed seed.
rng=random.Random(32012)
for n in (2,6,9):
    variants=("none",) if n==2 else ("none","standard","double","mississippi")
    for variant in variants:
        for reopen in (False,True):
            for trial in range(30):
                base=cfg(n,variant=variant,ante=trial%2,reopen=reopen)
                paid=[sum(p.amount for p in base.forced_posts if p.seat==i) for i in range(n)]
                stacks=tuple(max(paid[i]+1,rng.randrange(3,23)) for i in range(n))
                s=dealt(replace(base,starting_stacks=stacks))
                while s.current_player()!=TERMINAL:
                    s=edge(s,rng.choice(s.legal_actions()))
                    assert len(s.history)<=n+base.max_raises*(n-1)
print("PASS deterministic 540 random legal paths, independent transition/refund/layer/award oracles")
print("TOTAL",checks)
# Reuse only auditor-defined helpers from the preceding probe.
s=dealt(cfg(2,stacks=(100,3)))
c=replace(s.config,forced_posts=(ForcedPost(0,"small-blind",2),ForcedPost(1,"big-blind",2)))
for reopen in (False,True):
    s=dealt(replace(c,short_all_in_reopens=reopen))
    assert s.legal_actions()[0]==Action("CHECK")
    s=play(s,"CHECK")
    assert not s.can_raise[0]
    s=play(s,"RAISE",3)
    assert s.can_raise==(reopen,False)
    assert raises(s)==((100,) if reopen else ())
    finish(s)
# Both double-straddle option seats forced all-in, skip both and keep live BB option.
c=cfg(6,variant="double",stacks=(100,100,4,8,100,100))
s=dealt(c)
assert s.pending==(4,5,0,1)
finish(s)
# An absent exact key must not use any near match.
s=dealt(cfg(6,rules=(rule("UTG",0,1,"NA",6),
    rule("UTG",1,0,"NA",8),rule("UTG",0,0,"IP",10),rule("HJ",0,0,"NA",12))))
assert raises(s)==(100,)
# Full all-in caller (not a raise) consumes entitlement; absolute short call target.
s=dealt(cfg(2,stacks=(3,100)))
s=play(s,"RAISE",3)
s=play(s,"RAISE",100)
# Seat 0 is already all-in; no pending responder, excess 97 refunded immediately.
assert s.current_player()==TERMINAL and s.total_contributed==(3,3)
print("PASS CHECK entitlement, two forced-all-in straddles, absent exact key, immediate closure/refund")
print("FINAL TOTAL",checks)
PY
```

## Completion

Architecture acceptance remains blocked by B1 (P2). Production behavior within the exercised betting/reopening scope passed; no P0/P1 runtime blocker was found. No claim is made that the full regression, complete S3, or S3-I2 passed.

UTC completion: 2026-09-16T05:43:14Z
