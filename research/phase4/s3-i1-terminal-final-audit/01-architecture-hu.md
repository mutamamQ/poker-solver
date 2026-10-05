# CTA3A1 architecture / HU final audit

auditor=CTA3A1
provider=openai-codex
status=COMPLETE_PASS
blocker_count=0
production_sha256=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812
architecture_sha256=6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db

Fresh alternate-provider non-author audit. Candidate identity is exclusively the 11 literal raw-SHA256 rows in /home/genomix-node/poker-solver/research/phase4/s3-i1-terminal-final-audit/CANDIDATE_MANIFEST.md. Began with pwd, test -f of that literal manifest, and reading it. Cwd was /home/genomix-node/poker-solver. Independently hashed exactly those 11 paths before source review and after test/probe execution; every row matched on both passes.

## Verdict and scope

PASS for this architecture/HU scope; no blockers found. Read PHASE4_MISSION.md, full ARCHITECTURE_PHASE4_S3.md, both spec and terminal-ledger reconciliation receipts, prior FC3I1-5 report at research/phase4/s3-i1-final-audit/05-settlement-information.md, full legacy preflop.py, full production nplayer_preflop.py, and full information suite. Overlapping reads recovered truncated output.

Sections 1 and 13 consistently require raw ledger equality at aligned decisions and independently canonical refunded ledger equality plus exact utility equality at aligned terminals. Section 7 still closes when no actionable pending responder remains; section 8 still mandates refunds before every terminal. Section 3 explicitly keeps live blind/straddle differences at the root. Sections 2.3 and 8 both define table values as complete-hand utilities and rank settlement after refund. The reconciliation does not waive or weaken refund, erase terminal ledger checks, or grant universal custom-stack equivalence. The invalid legacy chipless suffix is explicitly excluded while correct N-player closure/refund remains mandatory. Section 15's uniform-ante restriction maintains refund boundedness. The former FC3I1-5 equal-stack projection blocker is resolved by the current wording and executable normalization.

The N-player _settle implementation refunds before branching to either a continuation table or pot awards. The permanent regressions pin both named boundaries. Legacy source SHA256 89dd56b291b138064e744f73e54af3aef38f5c36a439a6767d8f61fff755e8d2 equals the bytes independently read with git show from Phase-3 commit feba8222a0b614b0c64eca59402403ce733195ea.

No full regression, API/solver acceptance, or universal HU equivalence is claimed. The complete tree probe explicitly extends sizing-rule coverage to all HU public contexts and supplies complete rational continuation values; it uses exactly the four uniform deals of the permanent fold fixture and the expressions/max_raises of the permanent call/raise/reraise fixture. The original single-rule fold fixture is used unchanged for its named trace. This distinction is explicit in the embedded source.

## Executed tests

Command:
```sh
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_information.py
```

Exact output (exit 0):
```text
........                                                                 [100%]
8 passed in 0.17s
```

## Independent probe findings

- Equal stacks (20,20), RAISE6-FOLD: both decisions compare actors, ordered actions, raw ledgers, deals and projected histories. Exact utilities (2,-2). Legacy raw terminal ledger is (8,(6,2),(6,2),(14,18)); hand normalization refunds (4,0), yielding N-player stored (4,(2,2),(2,2),(18,18)).
- Unequal stacks (20,7), CALL2-RAISE7-RAISE20: all decision prefixes align. Legacy leaves actor 1 with zero chips and FOLD/CALL7 actions; raw ledger (27,(20,7),(20,7),(0,0)). Hand normalization refunds (13,0), yielding closed N-player ledger (14,(7,7),(7,7),(13,0)), pending empty, exact (7,-7). Executed separately with fixture terminal-table values and supplied ranks (2,1); the independent rank oracle is (13+14-20,0-7).
- Complete expanded equal-stack tree over all four fixture deals: exact masses 1/4 from four unit products, 64 aligned decisions, 120 exact terminal utility/canonical ledger comparisons, 60 raw terminal ledger differences resolved by refund, 60 supplied continuation keys, 8192 pairwise information-partition equivalence checks for both players. Fold status is reconstructed from legacy action history. All N-player stored terminal ledgers are already canonical.
- HU normalization uses cap=min(contributions), refund_i=contribution_i-cap, pot minus total refunds, street minus refund, remaining plus refund. It imports no production settlement helper. Fold utilities are independently +/-cap; non-fold tree values are supplied exact (5/7,-5/7), not inferred from settlement.
- Probe was created only as a NamedTemporaryFile under /tmp, actually executed by uv run python with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=/home/genomix-node/poker-solver/src, and unlinked in finally. Exact output includes exit 0 and deletion confirmation.

## Before and after raw SHA256

The following identical results were independently obtained on both passes; no path substitutions or alternate manifests were used.
```text
6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db ARCHITECTURE_PHASE4_S3.md MATCH
a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812 src/poker_solver/nplayer_preflop.py MATCH
8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240 src/poker_solver/sizing.py MATCH
bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268 tests/test_nplayer_preflop_config.py MATCH
9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd tests/test_nplayer_preflop_betting.py MATCH
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3 tests/test_nplayer_preflop_settlement.py MATCH
1217cf74f1468252fbc7f941621dc57154c910003eb27fbf8947b7bc5a42e289 tests/test_nplayer_preflop_information.py MATCH
2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1 tests/test_sizing.py MATCH
61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11 research/phase4/s3-i1-repair/RED_RECEIPT.md MATCH
36a95b38ec1b6016bc46ca80307b2c9f4119c749fceb51cd822bccaf61965164 research/phase4/s3-i1-spec-reconciliation/RECEIPT.md MATCH
b631cc2b933c314c081a70e6b3aaa669ae15054145301d272e1a18967d68a42a research/phase4/s3-i1-terminal-ledger-reconciliation/RECEIPT.md MATCH
```

Hash procedure on each pass:
```python
from pathlib import Path
import hashlib, re
p = Path('/home/genomix-node/poker-solver/research/phase4/s3-i1-terminal-final-audit/CANDIDATE_MANIFEST.md')
rows = re.findall(r'^- ([0-9a-f]{64})  (.+)$', p.read_text(), re.M)
assert len(rows) == 11
for expected, name in rows:
    actual = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    assert actual == expected, name
```

## Exact executed temporary probe source

```python
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from poker_solver.model import Action as A, TERMINAL
from poker_solver.game_structure import ForcedPost
from poker_solver.preflop import WeightedCombo, PreflopConfig, Continuation, create_preflop_root
from poker_solver.nplayer_preflop import (NPlayerPreflopConfig, NPlayerPreflopContinuation,
    NPlayerPreflopSizingRule, NPlayerPreflopPublicAction, create_nplayer_preflop_root,
    enumerate_nplayer_preflop_deals)

# Public constructor shapes copied from permanent information fixtures.
ranges = ((WeightedCombo((0,1),F(1)),WeightedCombo((2,3),F(1))),
          (WeightedCombo((4,5),F(1)),WeightedCombo((6,7),F(1))))
expressions = ({"unit":"big-blinds","value":3},{"unit":"all-in"})
def configs(stacks=(20,20), rs=ranges, expr=expressions, raises=2, rules=None, table=None):
    table = {} if table is None else table
    old = PreflopConfig(starting_stacks=stacks, forced_posts=(1,2), ranges=rs,
        sizing_expressions=expr, max_raises=raises, max_deals=4, max_nodes=1000,
        short_all_in_reopens=False,
        continuation=Continuation(kind="terminal-table",payoff_table=table,provenance="hu-projection"))
    new = NPlayerPreflopConfig(version="nplayer-preflop-v1",num_players=2,button=0,
        starting_stacks=stacks,
        forced_posts=(ForcedPost(seat=0,kind="small-blind",amount=1),
                      ForcedPost(seat=1,kind="big-blind",amount=2)),
        straddle_variant="none",ranges=rs,
        sizing_rules=rules if rules is not None else (
            NPlayerPreflopSizingRule(position="BTN/SB",raise_count=0,cold_callers=0,
                relation="NA",expressions=expr),),
        max_raises=raises,max_deals=4,max_nodes=1000,short_all_in_reopens=False,
        continuation=NPlayerPreflopContinuation(kind="terminal-table",provenance="hu-projection",
            source="supplied",payoff_table={
                (d,tuple(NPlayerPreflopPublicAction(actor=i%2,action=a) for i,a in enumerate(h))):v
                for (d,h),v in table.items()},showdown_ranks={},odd_chip_order=()))
    return old,new

def ledger(s):
    street = s.committed if hasattr(s,"committed") else s.street_committed
    return s.pot,street,s.total_contributed,s.remaining
def canonical(raw):
    pot,street,total,remaining=raw
    cap=min(total) # HU: unmatched chips are precisely the amount above the other contribution.
    refund=tuple(c-cap for c in total)
    return (pot-sum(refund),tuple(c-r for c,r in zip(street,refund)),
            (cap,cap),tuple(c+r for c,r in zip(remaining,refund)))
def aligned(l,n,verbose=False):
    assert l.current_player()==n.current_player()
    assert l.private_deal==n.private_deal
    assert l.legal_actions()==n.legal_actions()
    assert ledger(l)==ledger(n)
    assert l.history==tuple(x.action for x in n.history)
    assert n.folded==(False,False)
    if verbose: print("decision",l.history,"actor",l.current_player(),"actions",l.legal_actions(),"raw",ledger(l))
def start(cs):
    return (create_preflop_root(cs[0]).child(A("DEAL",0)),
            create_nplayer_preflop_root(cs[1]).child(A("DEAL",0)))

l,n=start(configs())
for a in (A("RAISE",6),A("FOLD")):
    aligned(l,n,True); l,n=l.child(a),n.child(a)
assert l.current_player()==n.current_player()==TERMINAL
assert l.terminal_values==n.terminal_values==(F(2),F(-2))
assert ledger(l)==(8,(6,2),(6,2),(14,18))
assert canonical(ledger(l))==ledger(n)==(4,(2,2),(2,2),(18,18))
assert canonical(ledger(n))==ledger(n) and n.folded==(False,True)
print("EQUAL PASS legacy raw",ledger(l),"refund",(4,0),"canonical/stored",ledger(n),"exact",n.terminal_values)

deal=((0,1),(2,3))
rs=((WeightedCombo(deal[0],F(1)),),(WeightedCombo(deal[1],F(1)),))
path=(A("CALL",2),A("RAISE",7),A("RAISE",20))
expr=({"unit":"all-in"},)
rules=(NPlayerPreflopSizingRule("BTN/SB",0,0,"NA",expr),
       NPlayerPreflopSizingRule("BB",1,0,"OOP",expr),
       NPlayerPreflopSizingRule("BTN/SB",2,0,"IP",expr))
cs=configs((20,7),rs,expr,3,rules,{(deal,path):(F(7),F(-7))})
# Run both the fixture table and an independently ranked showdown.
for kind in ("terminal-table","showdown-ranks"):
    nc=cs[1] if kind=="terminal-table" else replace(cs[1],continuation=NPlayerPreflopContinuation(
        kind="showdown-ranks",provenance="independent HU winner",source="supplied",
        payoff_table={},showdown_ranks={deal:(2,1)},odd_chip_order=(0,1)))
    l,n=start((cs[0],nc))
    for a in path:
        aligned(l,n,True);l,n=l.child(a),n.child(a)
    assert l.current_player()==1 and l.remaining==(0,0)
    assert l.legal_actions()==(A("FOLD"),A("CALL",7))
    assert ledger(l)==(27,(20,7),(20,7),(0,0))
    assert n.current_player()==TERMINAL and n.pending==()
    assert canonical(ledger(l))==ledger(n)==(14,(7,7),(7,7),(13,0))
    # Winner 0 receives matched pot 14: (13+14-20,0-7)=(7,-7).
    assert n.terminal_values==(F(13+14-20),F(0-7))
    print("UNEQUAL PASS",kind,"legacy actor/actions/raw",l.current_player(),l.legal_actions(),ledger(l),
          "refund",(13,0),"closed",ledger(n),"exact",n.terminal_values)

# Expand fixture sizing to all public contexts to obtain a complete aligned HU tree.
# The permanent fold fixture intentionally supplies only one sizing rule, for its named trace.
# Deals remain exactly its four uniform disjoint deals; expressions also include the
# permanent call/raise/reraise fixture's 9 BB target, max_raises=3.
expr=({"unit":"big-blinds","value":3},{"unit":"big-blinds","value":9},{"unit":"all-in"})
rules=tuple(NPlayerPreflopSizingRule(p,r,c,rel,expr)
    for p,r,c,rel in product(("BTN/SB","BB"),range(3),range(2),("NA","IP","OOP")))
oc,nc=configs(expr=expr,raises=3,rules=rules)
# Discover continuation keys only, using legacy missing-key errors. No payoff oracle
# is obtained from either engine: non-fold values are independently supplied 5/7,-5/7.
table={}
def discover(s):
    if s.current_player()==TERMINAL: return
    for a in s.legal_actions():
        try: child=s.child(a)
        except ValueError as e:
            assert str(e)=="missing continuation value for closed preflop leaf"
            table[(s.private_deal,s.history+(a,))]=(F(5,7),F(-5,7))
        else: discover(child)
root=create_preflop_root(oc)
for a,_ in root.chance_outcomes(): discover(root.child(a))
oc,nc=configs(expr=expr,raises=3,rules=rules,table=table)
lr,nr=create_preflop_root(oc),create_nplayer_preflop_root(nc)
deals=tuple((x.cards,y.cards) for x in ranges[0] for y in ranges[1])
# Each unnormalized mass is 1*1; denominator is 4, exactly.
assert lr.chance_outcomes()==tuple((A("DEAL",i),F(1,4)) for i in range(4))
assert enumerate_nplayer_preflop_deals(nc)==tuple((d,F(1,4)) for d in deals)
assert nr.chance_outcomes()==tuple((A("DEAL",i),0.25) for i in range(4))
pairs=[]; counts=[0,0,0]
def walk(l,n):
    assert l.private_deal==n.private_deal
    assert l.history==tuple(x.action for x in n.history)
    assert l.current_player()==n.current_player()
    if l.current_player()==TERMINAL:
        counts[1]+=1
        assert l.legal_actions()==n.legal_actions()==()
        folded=[False,False]
        for i,a in enumerate(l.history):
            if a.kind=="FOLD": folded[i%2]=True
        assert tuple(folded)==n.folded
        assert canonical(ledger(l))==canonical(ledger(n))==ledger(n)
        if ledger(l)!=ledger(n): counts[2]+=1
        if any(folded):
            cap=min(l.total_contributed)
            expected=tuple(F(-cap if f else cap) for f in folded)
        else: expected=(F(5,7),F(-5,7))
        assert l.terminal_values==n.terminal_values==expected
        assert all(type(v) is F for v in n.terminal_values) and sum(expected)==0
        return
    aligned(l,n); pairs.append((l,n));counts[0]+=1
    for a in l.legal_actions(): walk(l.child(a),n.child(a))
for a,_ in lr.chance_outcomes(): walk(lr.child(a),nr.child(a))
for p in (0,1):
    keys=[(l.information_state_key(p),n.information_state_key(p)) for l,n in pairs]
    for a,b in keys:
        for c,d in keys: assert (a==c)==(b==d)
assert sum(counts[:2])+1<=1000
print("TREE PASS deals",deals,"masses",(F(1,4),)*4,"decisions/terminals/raw terminal differences",counts,
      "continuation keys",len(table),"partition pair comparisons",2*len(pairs)**2)
print("ALL PROBES PASS")
```

## Exact probe output

```text
decision () actor 0 actions (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=2), Action(kind='RAISE', amount=6), Action(kind='RAISE', amount=20)) raw (3, (1, 2), (1, 2), (19, 18))
decision (Action(kind='RAISE', amount=6),) actor 1 actions (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=6), Action(kind='RAISE', amount=20)) raw (8, (6, 2), (6, 2), (14, 18))
EQUAL PASS legacy raw (8, (6, 2), (6, 2), (14, 18)) refund (4, 0) canonical/stored (4, (2, 2), (2, 2), (18, 18)) exact (Fraction(2, 1), Fraction(-2, 1))
decision () actor 0 actions (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=2), Action(kind='RAISE', amount=20)) raw (3, (1, 2), (1, 2), (19, 5))
decision (Action(kind='CALL', amount=2),) actor 1 actions (Action(kind='CHECK', amount=0), Action(kind='RAISE', amount=7)) raw (4, (2, 2), (2, 2), (18, 5))
decision (Action(kind='CALL', amount=2), Action(kind='RAISE', amount=7)) actor 0 actions (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=7), Action(kind='RAISE', amount=20)) raw (9, (2, 7), (2, 7), (18, 0))
UNEQUAL PASS terminal-table legacy actor/actions/raw 1 (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=7)) (27, (20, 7), (20, 7), (0, 0)) refund (13, 0) closed (14, (7, 7), (7, 7), (13, 0)) exact (Fraction(7, 1), Fraction(-7, 1))
decision () actor 0 actions (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=2), Action(kind='RAISE', amount=20)) raw (3, (1, 2), (1, 2), (19, 5))
decision (Action(kind='CALL', amount=2),) actor 1 actions (Action(kind='CHECK', amount=0), Action(kind='RAISE', amount=7)) raw (4, (2, 2), (2, 2), (18, 5))
decision (Action(kind='CALL', amount=2), Action(kind='RAISE', amount=7)) actor 0 actions (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=7), Action(kind='RAISE', amount=20)) raw (9, (2, 7), (2, 7), (18, 0))
UNEQUAL PASS showdown-ranks legacy actor/actions/raw 1 (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=7)) (27, (20, 7), (20, 7), (0, 0)) refund (13, 0) closed (14, (7, 7), (7, 7), (13, 0)) exact (Fraction(7, 1), Fraction(-7, 1))
TREE PASS deals (((0, 1), (4, 5)), ((0, 1), (6, 7)), ((2, 3), (4, 5)), ((2, 3), (6, 7))) masses (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)) decisions/terminals/raw terminal differences [64, 120, 60] continuation keys 60 partition pair comparisons 8192
ALL PROBES PASS
PROBE_EXIT 0
TEMP_DELETED True
```

Candidate files/tests/manifest, STATE.txt, PROGRESS.md and git/commits were read-only throughout. Only this report and matching .hb/CTA3A1 are durable writes. No commit. Mission-level state/commit/wave instructions were subordinate to the user's explicit exclusive auditor scope.

completed_utc=2026-09-16T07:52:15Z
