# C3I1-5R settlement, information, and HU audit

status=COMPLETE_BLOCKED
provider=openai-codex
auditor=C3I1-5R
production_sha256=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812
blocker_count=1

Fresh non-author replacement audit. All work ran from /home/genomix-node/poker-solver. No source, tests, manifest, STATE.txt, PROGRESS.md, existing evidence, or git edits were made; no git commands or commits were used. Two independent temporary Python probes were created outside the repository and deleted in finally blocks. Only this report and .hb/C3I1-5R are durable audit writes.

## Verdict and blocker B1

The requested permanent suites pass, and independent exact settlement and information checks pass. The required named equal-stack HU traces and complete selected equal-stack HU tree also pass. Unqualified HU compatibility is blocked by a reproducible architecture/legacy closure conflict on a valid unequal-stack configuration.

B1: N=2, button=0, stacks=(20,7), SB=1, BB=2, one disjoint deal ((0,1),(2,3)), all-in sizing in both engines, max_raises=3, short_all_in_reopens=False. Play CALL 2, RAISE 7, RAISE 20. Both engines have identical acting seats, ordered legal-action tuples and ledgers at every preceding decision. After the last action:

- Candidate is TERMINAL (-2), refunds 13 to seat 0, has pot=14, street=total=(7,7), remaining=(13,0), and exact supplied utilities=(7,-7).
- Legacy has actor=1 despite remaining=(0,0), pot=27, street=total=(20,7), and legal actions FOLD / CALL 7, with no terminal utility.

This is not a guessed utility mismatch or a missing-key artifact: the same exact public history has an explicit terminal-table entry in both configurations. The candidate looks up that entry; legacy never closes at that history. The exact command and raw output appear below.

Architecture line 9 requires projected acting-seat/action/ledger/terminal agreement. Architecture line 194 requires closure when no actionable pending responder remains, and line 198 requires terminal refund. Candidate lines 819–823 exclude opponents with no remaining chips from rebuilt pending; line 868 closes, and line 890 refunds. Legacy lines 312–324 close on equal commitments or a short-stack CALL, then line 326 unconditionally passes action to the other seat. Thus the candidate follows the explicit pending/settlement architecture, while the broader legacy projection conflicts. Do not silently modify legacy or the frozen candidate to force agreement. Parent must resolve/document the HU compatibility domain or reconcile these contracts. This is one compatibility/specification blocker, not a demonstrated settlement arithmetic defect. Architecture line 298's narrower frozen-fixture acceptance wording does not establish equivalence for this additional valid unequal-stack trace.

## Verified coverage and limits

- All nine manifest rows verified before source/test audit and again after probes; required files exist.
- Requested pytest: 13 passed in 0.14s, exit 0.
- Independent integer layer/refund oracle, without production settlement helpers: five named cases plus 6,815 terminal checks across complete selected N=3/6/9 tiny trees. Every visited state conserves pot and stacks; every checked terminal has exact zero-sum Fraction utilities and conserved final chips.
- Three-level side pots have amounts 40/60/40 awarded to three different winners, yielding (30,30,-10,-50); this tests eligibility rather than merely awarding all layers to one strongest seat.
- Tie/odd-chip order reversal yields (2,1,-3) versus (1,2,-3). Fold excess 38 is refunded; a short call refunds 13 and yields matched (7,7).
- Terminal tables return exact (7/3,-7/3) once, without subtracting contributions again. Empty and actor-mismatched keys reject on the reached leaf; nonzero-sum input rejects.
- N=6 and N=9: reached every acting seat on the limp/check path; 30 and 72 individual opponent-card mutations respectively; independently changed all hidden ranks and hidden terminal-table values; exact information-key and ordered-action equality holds. Owner-card mutation changes the key. Raise-entitlement mutation changes both key and actions. These are bounded adversarial checks, not proof over all configurations.
- HU weighted ranges with a blocker yield exact normalized masses (3/13,4/13,6/13); deterministic private deals and chance float projection match legacy. Complete selected equal-stack tree: 48 aligned decisions, 90 matching terminal utilities, 4,608 pairwise information-partition comparisons, zero conflicts. At every aligned nonterminal: ordered actions, actor, public history, pot, street, total, remaining and no-fold status agree. Named call/check, raise/call, reraise/call and raise/fold traces pass with exact rational utilities.
- Terminal fold ledgers are intentionally refunded by candidate; legacy retains unmatched amounts. Named raise/fold utilities still match (2,-2). This audit compares nonterminal aligned ledgers and terminal utilities as requested; it does not disguise terminal ledger representation differences.
- No full regression, solver/CFR/API audit, or global HU equivalence claim is made in this assigned scope.

## Commands and receipts

Initial commands:
```sh
pwd; rg --files -g AGENTS.md -g '*CANDIDATE_MANIFEST*' -g 'ARCHITECTURE_PHASE4_S3.md' -g '*preflop*' -g 'STATE.txt' -g 'PROGRESS.md'
cat research/phase4/s3-i1-repair-audit/CANDIDATE_MANIFEST.md
```
pwd returned /home/genomix-node/poker-solver. All requested paths were found. No AGENTS.md was returned by rg; the initial Python verification additionally checked the workspace, parent, and grandparent AGENTS.md paths and found none.

Initial hash/existence command:
```sh
python - <<'PY'
from pathlib import Path
import re,hashlib
root=Path.cwd(); assert str(root)=='/home/genomix-node/poker-solver'
for p in [root/'AGENTS.md',root.parent/'AGENTS.md',root.parent.parent/'AGENTS.md']:
 if p.exists(): print(str(p)+'\\n'+p.read_text())
m=Path('research/phase4/s3-i1-repair-audit/CANDIDATE_MANIFEST.md').read_text(); rows=re.findall(r'^- ([0-9a-f]{64})  (.+)$',m,re.M);assert len(rows)==9
for expected,name in rows:
 p=Path(name);actual=hashlib.sha256(p.read_bytes()).hexdigest(); print(('OK' if actual==expected else 'FAIL'),actual,name);assert actual==expected
for name in ['src/poker_solver/preflop.py','STATE.txt','PROGRESS.md']:
 assert Path(name).is_file();print('REQUIRED EXISTS',name)
PY
```
Raw output (exit 0):
```text
OK a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6 ARCHITECTURE_PHASE4_S3.md
OK a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812 src/poker_solver/nplayer_preflop.py
OK 8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240 src/poker_solver/sizing.py
OK bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268 tests/test_nplayer_preflop_config.py
OK 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd tests/test_nplayer_preflop_betting.py
OK e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3 tests/test_nplayer_preflop_settlement.py
OK 0d800d2f8fe797f29d8a347e1ab216bbc079fee0ede792ab253db23097819445 tests/test_nplayer_preflop_information.py
OK 2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1 tests/test_sizing.py
OK 61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11 research/phase4/s3-i1-repair/RED_RECEIPT.md
REQUIRED EXISTS src/poker_solver/preflop.py
REQUIRED EXISTS STATE.txt
REQUIRED EXISTS PROGRESS.md
```

Source reads (cat output was large; overlapping sed reads recovered truncated portions):
```sh
cat ARCHITECTURE_PHASE4_S3.md src/poker_solver/nplayer_preflop.py
cat tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py src/poker_solver/preflop.py
cat tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py
sed -n '1,260p' src/poker_solver/nplayer_preflop.py
sed -n '260,560p' src/poker_solver/nplayer_preflop.py
sed -n '560,1000p' src/poker_solver/nplayer_preflop.py
sed -n '210,420p' ARCHITECTURE_PHASE4_S3.md
sed -n '700,760p' src/poker_solver/nplayer_preflop.py
sed -n '1000,1200p' src/poker_solver/nplayer_preflop.py
sed -n '190,212p' ARCHITECTURE_PHASE4_S3.md
sed -n '680,708p' src/poker_solver/nplayer_preflop.py
sed -n '200,335p' src/poker_solver/game_structure.py
cat src/poker_solver/preflop.py
```

Requested command:
```sh
uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py
```
Raw output, exit 0:
```text
.............                                                            [100%]
13 passed in 0.14s
```

First probe: exact shell command, including embedded source and cleanup. Source is recorded here so the deleted temporary file is reproducible. The wrapper sets PYTHONDONTWRITEBYTECODE and PYTHONPATH to the workspace src directory; cwd remains the workspace.
```sh
python - <<'PY'
import tempfile, subprocess, os
from pathlib import Path
source="from dataclasses import replace\nfrom fractions import Fraction as F\nfrom itertools import product\nfrom poker_solver.nplayer_preflop import *\nfrom poker_solver.preflop import PreflopConfig, Continuation, WeightedCombo, create_preflop_root\nfrom poker_solver.game_structure import ForcedPost\nfrom poker_solver.model import Action as A, TERMINAL\n\ndef cfg(n, stacks=None, ranks=None, ante=0, button=None):\n    deal=tuple((2*i,2*i+1) for i in range(n))\n    b=(0 if n==2 else n-1) if button is None else button\n    sb=b if n==2 else (b+1)%n\n    bb=(b+1)%n if n==2 else (b+2)%n\n    posts=tuple(ForcedPost(i,'ante',ante) for i in range(n)) if ante else ()\n    return NPlayerPreflopConfig('nplayer-preflop-v1',n,b,stacks or (40,)*n,\n        posts+(ForcedPost(sb,'small-blind',1),ForcedPost(bb,'big-blind',2)),\n        'none',tuple((WeightedCombo(c,F(1)),) for c in deal),(),3,16,100000,False,\n        NPlayerPreflopContinuation('showdown-ranks','C3I1-5R','supplied',{},\n            {deal:ranks or tuple(range(n))},tuple(range(n))))\ndef dealt(c):\n    return create_nplayer_preflop_root(c).child(A('DEAL',0))\ndef ledger(s):\n    assert s.pot==sum(s.total_contributed)\n    assert tuple(x+y for x,y in zip(s.remaining,s.total_contributed))==s.config.starting_stacks\n    assert all(0<=x<=y for x,y in zip(s.street_committed,s.total_contributed))\ndef oracle(before,action,after):\n    # Independent transfer and chip-by-chip level oracle: no production settlement helper.\n    c=list(before.total_contributed); st=list(before.street_committed)\n    folded=list(before.folded); p=before.current_player()\n    if action.kind in ('CALL','RAISE'):\n        c[p]+=action.amount-st[p]; st[p]=action.amount\n    elif action.kind=='FOLD': folded[p]=True\n    cap=sorted(c)[-2]\n    matched=tuple(min(x,cap) for x in c)\n    refund=tuple(x-y for x,y in zip(c,matched))\n    assert after.total_contributed==matched\n    assert after.street_committed==tuple(x-y for x,y in zip(st,refund))\n    awards=[0]*len(c)\n    ranks=before.config.continuation.showdown_ranks[before.private_deal]\n    # Group consecutive equal contributor sets, then distribute whole layer odd chips.\n    prev=0\n    for high in sorted(set(matched)-{0}):\n        contributors=[i for i,x in enumerate(matched) if x>=high]\n        amount=(high-prev)*len(contributors); prev=high\n        eligible=[i for i in contributors if not folded[i]]\n        best=max(ranks[i] for i in eligible)\n        winners=[i for i in before.config.continuation.odd_chip_order if i in eligible and ranks[i]==best]\n        each,odd=divmod(amount,len(winners))\n        for j,i in enumerate(winners): awards[i]+=each+(j<odd)\n    expected=tuple(F(x-y) for x,y in zip(awards,matched))\n    assert after.terminal_values==expected,(before.history,action,expected,after.terminal_values)\n    assert sum(expected)==0\n    assert sum(x+y for x,y in zip(after.config.starting_stacks,expected))==sum(after.config.starting_stacks)\n    ledger(after)\n    return refund,awards\n\ndef trace(c,actions,label):\n    s=dealt(c)\n    for a in actions:\n        ledger(s); t=s.child(a)\n        if t.current_player()==TERMINAL: refund,awards=oracle(s,a,t)\n        s=t\n    assert s.current_player()==TERMINAL\n    print(label,'contributions=',s.total_contributed,'refund=',refund,'awards=',awards,'utilities=',s.terminal_values)\n    return s\ntrace(cfg(3,button=0),[A('RAISE',40),A('FOLD'),A('FOLD')],'refund-fold')\ntrace(cfg(4,(10,30,50,100),(9,7,5,1),button=1),\n      [A('RAISE',10),A('RAISE',30),A('RAISE',50),A('CALL',50)],'side-pots-different-winners')\ntrace(cfg(3,ranks=(10,10,1),ante=1,button=0),\n      [A('CALL',2),A('CALL',2),A('CHECK')],'odd-chip-seat0')\nc=cfg(3,ranks=(10,10,1),ante=1,button=0)\ntrace(replace(c,continuation=replace(c.continuation,odd_chip_order=(1,0,2))),\n      [A('CALL',2),A('CALL',2),A('CHECK')],'odd-chip-seat1')\ntrace(cfg(2,(7,20),(9,1)),[A('CALL',2),A('RAISE',20),A('CALL',7)],'short-call-refund')\n\n# Walk small multiseat trees to independently check every terminal.\nfor n in (3,6,9):\n    c=cfg(n,tuple(3+i%3 for i in range(n)),tuple(i%3 for i in range(n)),ante=1)\n    count=[0,0]\n    def walk(s):\n        ledger(s); count[0]+=1\n        for a in s.legal_actions():\n            t=s.child(a)\n            if t.current_player()==TERMINAL:\n                oracle(s,a,t); count[1]+=1\n            else: walk(t)\n    walk(dealt(c))\n    print('exhaustive settlement',n,'decision_nodes',count[0],'terminal_oracles',count[1])\n\n# All acting seats, reached via limps/checks; hidden changes preserve exact action tuples.\nfor n in (6,9):\n    base=cfg(n); s=dealt(base); count=0\n    while s.current_player()!=TERMINAL:\n        p=s.current_player(); key=s.information_state_key(p); legal=s.legal_actions()\n        d=list(s.private_deal)\n        for other in range(n):\n            if other==p: continue\n            d2=list(d);d2[other]=(48,49);d2=tuple(d2)\n            ranges=tuple((WeightedCombo(x,F(1)),) for x in d2)\n            cc=replace(base,ranges=ranges,continuation=replace(base.continuation,showdown_ranks={d2:tuple(reversed(range(n)))}))\n            ss=replace(s,config=cc,private_deal=d2)\n            assert ss.information_state_key(p)==key and ss.legal_actions()==legal\n            count+=1\n        changed=replace(s,config=replace(base,continuation=replace(base.continuation,showdown_ranks={s.private_deal:(999,)*n})))\n        assert changed.information_state_key(p)==key and changed.legal_actions()==legal\n        d[p]=(46,47);d=tuple(d)\n        owner=replace(base,ranges=tuple((WeightedCombo(x,F(1)),) for x in d),\n          continuation=replace(base.continuation,showdown_ranks={d:tuple(range(n))}))\n        assert replace(s,config=owner,private_deal=d).information_state_key(p)!=key\n        public=replace(s,can_raise=tuple(False if i==p else x for i,x in enumerate(s.can_raise)))\n        assert public.information_state_key(p)!=key and public.legal_actions()!=legal\n        # Isolate hidden terminal table contents under identical metadata.\n        tabkey=(s.private_deal,s.history)\n        vals=(F(1,3),F(-1,3))+(F(0),)*(n-2)\n        tc=NPlayerPreflopContinuation('terminal-table','same','supplied',{tabkey:vals},{},())\n        one=replace(s,config=replace(base,continuation=tc))\n        two=replace(s,config=replace(base,continuation=replace(tc,payoff_table={tabkey:tuple(-x for x in vals)})))\n        assert one.information_state_key(p)==two.information_state_key(p)\n        assert one.legal_actions()==two.legal_actions()==legal\n        a=next(a for a in legal if a.kind in ('CALL','CHECK'));s=s.child(a)\n    print('information N=',n,'all acting seats=',n,'opponent mutations=',count,'ranks/table/owner/public/actions PASS')\n\n# Exact table values used once; history actor and missing keys fail closed.\nc=cfg(2); d=dealt(c).private_deal\nh=(NPlayerPreflopPublicAction(0,A('CALL',2)),NPlayerPreflopPublicAction(1,A('CHECK')))\nv=(F(7,3),F(-7,3))\ntc=NPlayerPreflopContinuation('terminal-table','table','supplied',{(d,h):v},{},())\ns=dealt(replace(c,continuation=tc)).child(A('CALL',2)).child(A('CHECK'))\nassert s.terminal_values==v;ledger(s)\nfor bad in ({}, {(d,tuple(NPlayerPreflopPublicAction(1-x.actor,x.action) for x in h)):v}):\n    try: dealt(replace(c,continuation=replace(tc,payoff_table=bad))).child(A('CALL',2)).child(A('CHECK'))\n    except ValueError as e: print('missing/exact actor table rejection:',str(e))\n    else: raise AssertionError('accepted wrong table key')\nfor kwargs in (dict(payoff_table={(d,h):(F(1),F(1))}),):\n    try: replace(tc,**kwargs)\n    except ValueError as e: print('nonzero table rejection:',str(e))\n    else: raise AssertionError('nonzero table')\nprint('terminal table exact fractions PASS',s.terminal_values)\n\n# Full sizing coverage in both games. Weighted ranges include one blocker pair.\nranges=((WeightedCombo((0,1),F(1,3)),WeightedCombo((2,3),F(2,3))),\n        (WeightedCombo((0,4),F(2,5)),WeightedCombo((6,7),F(3,5))))\nexpr=({'unit':'big-blinds','value':3},{'unit':'big-blinds','value':9},{'unit':'all-in'})\nrules=tuple(NPlayerPreflopSizingRule(pos,r,k,rel,expr) for pos,r,k,rel in product(('BTN/SB','BB'),range(3),range(2),('NA','IP','OOP')))\nbase=cfg(2)\nnc=replace(base,ranges=ranges,sizing_rules=rules,starting_stacks=(20,20),\n    continuation=NPlayerPreflopContinuation('terminal-table','HU','supplied',{}, {},()))\nold=PreflopConfig((20,20),(1,2),ranges,expr,3,16,100000,False,Continuation('terminal-table',{},'HU'))\nnr=create_nplayer_preflop_root(nc);lr=create_preflop_root(old)\nmasses=tuple(m for _,m in enumerate_nplayer_preflop_deals(nc))\nassert masses==(F(3,13),F(4,13),F(6,13))\nassert masses==tuple(m for _,m in lr.chance_outcomes())\nassert nr.chance_outcomes()==tuple((a,float(m)) for a,m in lr.chance_outcomes())\nprint('HU exact normalized masses',masses)\n# Traverse candidate with ranks to enumerate all closed keys, then supply arbitrary rational\n# complete hand utilities identically to both implementations.\ndeals=tuple(d for d,_ in enumerate_nplayer_preflop_deals(nc))\nrc=replace(nc,continuation=NPlayerPreflopContinuation('showdown-ranks','HU','supplied',{}, {d:(1,2) for d in deals},(0,1)))\ntable={}\ndef collect(s):\n    if s.current_player()==TERMINAL:\n        if not any(s.folded): table[(s.private_deal,s.history)]=(F(5,7),F(-5,7))\n        return\n    for a in s.legal_actions(): collect(s.child(a))\nfor a,_ in nr.chance_outcomes(): collect(create_nplayer_preflop_root(rc).child(a))\nnc=replace(nc,continuation=replace(nc.continuation,payoff_table=table))\nold=replace(old,continuation=Continuation('terminal-table',{(d,tuple(x.action for x in h)):v for (d,h),v in table.items()},'HU'))\npairs=[];terminals=0; conflicts=[]\ndef compare(l,r,path):\n    global terminals\n    if l.current_player()!=r.current_player():\n        conflicts.append((path,'actor/closure',l.current_player(),r.current_player()));return\n    if l.current_player()==TERMINAL:\n        assert l.terminal_values==r.terminal_values; terminals+=1;return\n    assert l.private_deal==r.private_deal\n    assert (l.pot,l.committed,l.total_contributed,l.remaining)==(r.pot,r.street_committed,r.total_contributed,r.remaining)\n    assert not any(r.folded)\n    assert l.history==tuple(x.action for x in r.history)\n    if l.legal_actions()!=r.legal_actions():\n        conflicts.append((path,'actions',l.legal_actions(),r.legal_actions()));return\n    pairs.append((l,r))\n    for a in l.legal_actions():\n        try: ll=l.child(a);rr=r.child(a)\n        except ValueError as e: conflicts.append((path+(a,),'child error',str(e)));continue\n        compare(ll,rr,path+(a,))\nfor a,_ in create_preflop_root(old).chance_outcomes():\n    compare(create_preflop_root(old).child(a),create_nplayer_preflop_root(nc).child(a),())\nfor p in (0,1):\n    lk=[l.information_state_key(p) for l,r in pairs];rk=[r.information_state_key(p) for l,r in pairs]\n    assert all((lk[i]==lk[j])==(rk[i]==rk[j]) for i in range(len(pairs)) for j in range(len(pairs)))\nprint('HU full tree aligned decisions',len(pairs),'terminal utilities',terminals,'partition comparisons',2*len(pairs)**2)\nprint('HU conflicts',len(conflicts))\nfor conflict in conflicts[:12]: print('CONFLICT',conflict)\n# Required named traces, with rational table values and fold utility.\nfor path in ((A('CALL',2),A('CHECK')),(A('RAISE',6),A('CALL',6)),(A('RAISE',6),A('RAISE',18),A('CALL',18)),(A('RAISE',6),A('FOLD'))):\n    l=create_preflop_root(old).child(A('DEAL',0));r=create_nplayer_preflop_root(nc).child(A('DEAL',0))\n    for a in path:\n        assert l.legal_actions()==r.legal_actions()\n        assert (l.pot,l.committed,l.total_contributed,l.remaining)==(r.pot,r.street_committed,r.total_contributed,r.remaining)\n        l=l.child(a);r=r.child(a)\n    assert l.current_player()==r.current_player()==TERMINAL and l.terminal_values==r.terminal_values\n    print('HU named',path,'utilities',r.terminal_values)\nprint('PROBE_COMPLETED blocker_groups=',int(bool(conflicts)))\n"
p=None
try:
 f=tempfile.NamedTemporaryFile(mode='w',prefix='C3I1-5R-',suffix='.py',dir='/tmp',delete=False);p=f.name;f.write(source);f.close()
 print('TEMP_PROBE',p,flush=True)
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(Path.cwd()/'src'))
 result=subprocess.run(['uv','run','python',p],env=env,text=True,capture_output=True)
 print(result.stdout,end='');print(result.stderr,end='');print('PROBE_EXIT',result.returncode)
finally:
 if p: os.unlink(p);print('TEMP_DELETED',p,not Path(p).exists())

PY
```
Raw output (wrapper exit 0; probe exit 0):
```text
TEMP_PROBE /tmp/C3I1-5R-z9osj7xe.py
refund-fold contributions= (2, 1, 2) refund= (38, 0, 0) awards= [5, 0, 0] utilities= (Fraction(3, 1), Fraction(-1, 1), Fraction(-2, 1))
side-pots-different-winners contributions= (10, 30, 50, 50) refund= (0, 0, 0, 0) awards= [40, 60, 40, 0] utilities= (Fraction(30, 1), Fraction(30, 1), Fraction(-10, 1), Fraction(-50, 1))
odd-chip-seat0 contributions= (3, 3, 3) refund= (0, 0, 0) awards= [5, 4, 0] utilities= (Fraction(2, 1), Fraction(1, 1), Fraction(-3, 1))
odd-chip-seat1 contributions= (3, 3, 3) refund= (0, 0, 0) awards= [4, 5, 0] utilities= (Fraction(1, 1), Fraction(2, 1), Fraction(-3, 1))
short-call-refund contributions= (7, 7) refund= (0, 13) awards= [14, 0] utilities= (Fraction(7, 1), Fraction(-7, 1))
exhaustive settlement 3 decision_nodes 11 terminal_oracles 13
exhaustive settlement 6 decision_nodes 297 terminal_oracles 315
exhaustive settlement 9 decision_nodes 6309 terminal_oracles 6487
information N= 6 all acting seats= 6 opponent mutations= 30 ranks/table/owner/public/actions PASS
information N= 9 all acting seats= 9 opponent mutations= 72 ranks/table/owner/public/actions PASS
missing/exact actor table rejection: missing continuation value for closed preflop leaf
missing/exact actor table rejection: missing continuation value for closed preflop leaf
nonzero table rejection: terminal values must be finite and zero-sum
terminal table exact fractions PASS (Fraction(7, 3), Fraction(-7, 3))
HU exact normalized masses (Fraction(3, 13), Fraction(4, 13), Fraction(6, 13))
HU full tree aligned decisions 48 terminal utilities 90 partition comparisons 4608
HU conflicts 0
HU named (Action(kind='CALL', amount=2), Action(kind='CHECK', amount=0)) utilities (Fraction(5, 7), Fraction(-5, 7))
HU named (Action(kind='RAISE', amount=6), Action(kind='CALL', amount=6)) utilities (Fraction(5, 7), Fraction(-5, 7))
HU named (Action(kind='RAISE', amount=6), Action(kind='RAISE', amount=18), Action(kind='CALL', amount=18)) utilities (Fraction(5, 7), Fraction(-5, 7))
HU named (Action(kind='RAISE', amount=6), Action(kind='FOLD', amount=0)) utilities (Fraction(2, 1), Fraction(-2, 1))
PROBE_COMPLETED blocker_groups= 0
PROBE_EXIT 0
TEMP_DELETED /tmp/C3I1-5R-z9osj7xe.py True
```

Adaptive unequal-stack probe: exact shell command and embedded source:
```sh
python - <<'PY'
import tempfile, subprocess, os
from pathlib import Path
source="from dataclasses import replace\nfrom fractions import Fraction as F\nfrom itertools import product\nfrom poker_solver.nplayer_preflop import *\nfrom poker_solver.preflop import PreflopConfig, Continuation, WeightedCombo, create_preflop_root\nfrom poker_solver.game_structure import ForcedPost\nfrom poker_solver.model import Action as A, TERMINAL\n\ndef cfg(n, stacks=None, ranks=None, ante=0, button=None):\n    deal=tuple((2*i,2*i+1) for i in range(n))\n    b=(0 if n==2 else n-1) if button is None else button\n    sb=b if n==2 else (b+1)%n\n    bb=(b+1)%n if n==2 else (b+2)%n\n    posts=tuple(ForcedPost(i,'ante',ante) for i in range(n)) if ante else ()\n    return NPlayerPreflopConfig('nplayer-preflop-v1',n,b,stacks or (40,)*n,\n        posts+(ForcedPost(sb,'small-blind',1),ForcedPost(bb,'big-blind',2)),\n        'none',tuple((WeightedCombo(c,F(1)),) for c in deal),(),3,16,100000,False,\n        NPlayerPreflopContinuation('showdown-ranks','C3I1-5R','supplied',{},\n            {deal:ranks or tuple(range(n))},tuple(range(n))))\ndef dealt(c):\n    return create_nplayer_preflop_root(c).child(A('DEAL',0))\ndef ledger(s):\n    assert s.pot==sum(s.total_contributed)\n    assert tuple(x+y for x,y in zip(s.remaining,s.total_contributed))==s.config.starting_stacks\n    assert all(0<=x<=y for x,y in zip(s.street_committed,s.total_contributed))\ndef oracle(before,action,after):\n    # Independent transfer and chip-by-chip level oracle: no production settlement helper.\n    c=list(before.total_contributed); st=list(before.street_committed)\n    folded=list(before.folded); p=before.current_player()\n    if action.kind in ('CALL','RAISE'):\n        c[p]+=action.amount-st[p]; st[p]=action.amount\n    elif action.kind=='FOLD': folded[p]=True\n    cap=sorted(c)[-2]\n    matched=tuple(min(x,cap) for x in c)\n    refund=tuple(x-y for x,y in zip(c,matched))\n    assert after.total_contributed==matched\n    assert after.street_committed==tuple(x-y for x,y in zip(st,refund))\n    awards=[0]*len(c)\n    ranks=before.config.continuation.showdown_ranks[before.private_deal]\n    # Group consecutive equal contributor sets, then distribute whole layer odd chips.\n    prev=0\n    for high in sorted(set(matched)-{0}):\n        contributors=[i for i,x in enumerate(matched) if x>=high]\n        amount=(high-prev)*len(contributors); prev=high\n        eligible=[i for i in contributors if not folded[i]]\n        best=max(ranks[i] for i in eligible)\n        winners=[i for i in before.config.continuation.odd_chip_order if i in eligible and ranks[i]==best]\n        each,odd=divmod(amount,len(winners))\n        for j,i in enumerate(winners): awards[i]+=each+(j<odd)\n    expected=tuple(F(x-y) for x,y in zip(awards,matched))\n    assert after.terminal_values==expected,(before.history,action,expected,after.terminal_values)\n    assert sum(expected)==0\n    assert sum(x+y for x,y in zip(after.config.starting_stacks,expected))==sum(after.config.starting_stacks)\n    ledger(after)\n    return refund,awards\n\ndef trace(c,actions,label):\n    s=dealt(c)\n    for a in actions:\n        ledger(s); t=s.child(a)\n        if t.current_player()==TERMINAL: refund,awards=oracle(s,a,t)\n        s=t\n    assert s.current_player()==TERMINAL\n    print(label,'contributions=',s.total_contributed,'refund=',refund,'awards=',awards,'utilities=',s.terminal_values)\n    return s\n\nexpressions=({'unit':'all-in'},)\nrules=tuple(NPlayerPreflopSizingRule(pos,r,k,rel,expressions)\n    for pos,r,k,rel in product(('BTN/SB','BB'),range(3),range(2),('NA','IP','OOP')))\nc=replace(cfg(2,(20,7)),sizing_rules=rules)\nd=dealt(c).private_deal\npath=(A('CALL',2),A('RAISE',7),A('RAISE',20))\nhist=tuple(NPlayerPreflopPublicAction(i%2,a) for i,a in enumerate(path))\nv=(F(7),F(-7))\nc=replace(c,continuation=NPlayerPreflopContinuation('terminal-table','conflict','supplied',{(d,hist):v},{},()))\nlc=PreflopConfig((20,7),(1,2),c.ranges,expressions,3,16,100000,False,\n    Continuation('terminal-table',{(d,path):v},'conflict'))\nl=create_preflop_root(lc).child(A('DEAL',0));r=dealt(c)\nfor a in path:\n    assert l.current_player()==r.current_player()\n    assert l.legal_actions()==r.legal_actions()\n    assert (l.pot,l.committed,l.total_contributed,l.remaining)==(r.pot,r.street_committed,r.total_contributed,r.remaining)\n    print('BEFORE',a,'actor',l.current_player(),'actions',l.legal_actions(),'pot/street/total/remaining',(l.pot,l.committed,l.total_contributed,l.remaining))\n    l=l.child(a);r=r.child(a)\nprint('AFTER legacy actor',l.current_player(),'actions',l.legal_actions(),'ledger',(l.pot,l.committed,l.total_contributed,l.remaining),'utility',l.terminal_values)\nprint('AFTER candidate actor',r.current_player(),'actions',r.legal_actions(),'ledger',(r.pot,r.street_committed,r.total_contributed,r.remaining),'utility',r.terminal_values)\nassert l.current_player()==1 and r.current_player()==TERMINAL\nassert l.remaining[1]==0 and A('FOLD') in l.legal_actions()\nprint('REPRODUCED architecture/legacy closure conflict; blocker_count=1')\n"
f=tempfile.NamedTemporaryFile(mode='w',prefix='C3I1-5R-edge-',suffix='.py',dir='/tmp',delete=False)
p=f.name
try:
 f.write(source);f.close();print('TEMP_PROBE',p,flush=True)
 result=subprocess.run(['uv','run','python',p],env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(Path.cwd()/'src')),text=True,capture_output=True)
 print(result.stdout,end='');print(result.stderr,end='');print('PROBE_EXIT',result.returncode)
finally:
 os.unlink(p);print('TEMP_DELETED',p,not Path(p).exists())

PY
```
Raw output (wrapper exit 0; probe exit 0 means the conflict assertion reproduced successfully):
```text
TEMP_PROBE /tmp/C3I1-5R-edge-e2quwpsw.py
BEFORE Action(kind='CALL', amount=2) actor 0 actions (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=2), Action(kind='RAISE', amount=20)) pot/street/total/remaining (3, (1, 2), (1, 2), (19, 5))
BEFORE Action(kind='RAISE', amount=7) actor 1 actions (Action(kind='CHECK', amount=0), Action(kind='RAISE', amount=7)) pot/street/total/remaining (4, (2, 2), (2, 2), (18, 5))
BEFORE Action(kind='RAISE', amount=20) actor 0 actions (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=7), Action(kind='RAISE', amount=20)) pot/street/total/remaining (9, (2, 7), (2, 7), (18, 0))
AFTER legacy actor 1 actions (Action(kind='FOLD', amount=0), Action(kind='CALL', amount=7)) ledger (27, (20, 7), (20, 7), (0, 0)) utility None
AFTER candidate actor -2 actions () ledger (14, (7, 7), (7, 7), (13, 0)) utility (Fraction(7, 1), Fraction(-7, 1))
REPRODUCED architecture/legacy closure conflict; blocker_count=1
PROBE_EXIT 0
TEMP_DELETED /tmp/C3I1-5R-edge-e2quwpsw.py True
```

Two attempted JavaScript orchestration calls before the adaptive probe returned exactly:
```text
Script error:
SyntaxError: Unexpected token ')'
```
They failed before any shell execution or file creation. The corrected call above ran successfully; this is not an environment blocker.

Final frozen-file and temporary-file verification:
```sh
python - <<'PY'
from pathlib import Path
import re,hashlib
assert str(Path.cwd())=='/home/genomix-node/poker-solver'
print('pwd:',Path.cwd())
rows=re.findall(r'^- ([0-9a-f]{64})  (.+)$',Path('research/phase4/s3-i1-repair-audit/CANDIDATE_MANIFEST.md').read_text(),re.M)
assert len(rows)==9
for expected,name in rows:
 actual=hashlib.sha256(Path(name).read_bytes()).hexdigest()
 assert actual==expected
 print('OK',actual,name)
for name in ['src/poker_solver/preflop.py','STATE.txt','PROGRESS.md']:
 assert Path(name).is_file();print('REQUIRED EXISTS',name)
print('TEMP FILES REMAIN:',list(Path('/tmp').glob('C3I1-5R-*.py')))
assert not list(Path('/tmp').glob('C3I1-5R-*.py'))
PY
```
Raw output, exit 0:
```text
pwd: /home/genomix-node/poker-solver
OK a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6 ARCHITECTURE_PHASE4_S3.md
OK a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812 src/poker_solver/nplayer_preflop.py
OK 8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240 src/poker_solver/sizing.py
OK bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268 tests/test_nplayer_preflop_config.py
OK 9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd tests/test_nplayer_preflop_betting.py
OK e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3 tests/test_nplayer_preflop_settlement.py
OK 0d800d2f8fe797f29d8a347e1ab216bbc079fee0ede792ab253db23097819445 tests/test_nplayer_preflop_information.py
OK 2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1 tests/test_sizing.py
OK 61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11 research/phase4/s3-i1-repair/RED_RECEIPT.md
REQUIRED EXISTS src/poker_solver/preflop.py
REQUIRED EXISTS STATE.txt
REQUIRED EXISTS PROGRESS.md
TEMP FILES REMAIN: []
```

Heartbeat UTC is obtained live with date -u +%Y-%m-%dT%H:%M:%SZ at finalization. Both assigned files are read back after writing. No commit.

completed_utc=2026-09-16T06:35:38Z
