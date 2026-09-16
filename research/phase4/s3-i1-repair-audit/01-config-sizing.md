# C3I1-1R config and sizing release audit

status=COMPLETE_PASS
provider=openai-codex
blocker_count=0
production_sha256=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812
utc=2026-09-16T06:31:41Z

PASS for the assigned S3-I1 config/sizing scope. No reproducible blocker found. This is a fresh non-author audit of the frozen files, not adoption of prior receipts. It does not certify the later S3-I2 solver/API/export work or substitute for full regression and other audit scopes.

## Authority and review

Read ARCHITECTURE_PHASE4_S3.md in full, src/poker_solver/nplayer_preflop.py in full, src/poker_solver/sizing.py in full, tests/test_nplayer_preflop_config.py in full, and tests/test_sizing.py in full. Also inspected the reused ForcedPost and WeightedCombo constructors to distinguish constructor rejection from config rejection. No prior audit report was used as an oracle.

Contracts checked against architecture sections 2.2–2.4, 3–7, 8–9 where relevant to continuation validation and immutable sizing identity, and the S3-I1 assignment in section 12:

- Strict N=2..9, button/stacks/bounds, tuple shapes, cards, weights, duplicates, compatible deals, and Cartesian product precheck. The probe accepts all supported player counts and rejects bool/float aliases and malformed inputs.
- Posts: unsupported kinds including unhashable values, bad seats and amounts, missing/duplicate/misplaced blinds, partial/unequal antes, cumulative overflow, degenerate post stacks, and undeclared straddles. Reused ForcedPost rejects bool seat/amount with TypeError; that is a constructor-level fail-closed result, not an accepted config.
- Continuations: kind/source/provenance, disjoint cards/rank counts/coverage, strict odd-chip permutation including mixed bool/float aliases, finite zero-sum values, read-only detached tables, and failure at a reached missing terminal-table leaf. Root construction does not falsely claim complete terminal-table coverage.
- Sizing: unique four-field config keys even when expressions differ, canonical positions at config validation, strict rule numeric fields, numeric schema, context fields, Decimal NaN/sNaN/positive and negative Infinity normalized to ValueError, finite Decimal half-up conversion, and first-order target deduplication.
- Deep mutation: assignment to expression items, backing field, backing tuple and nonexistent __dict__ is rejected. Caller dictionaries are changed after construction; legal actions, information keys and rule hashes remain stable. Independently constructed rules with reordered expression dictionary keys remain equal with equal hashes and work interchangeably as dictionary keys. Nested mutable numeric values are rejected by the strict expression schema.

The focused permanent tests additionally exercise uniform-ante ledgers, standard/double/Mississippi straddles, all-in option removal, exact mass/pruning, invalid roots, sizing formulas, legality, and dynamic/automatic selection. Frozen/slotted tuple-backed expression contents and read-only continuation mappings agree with the architecture's ordinary Python immutability contract; deliberate object.__setattr__ bypasses were not treated as supported mutation APIs.

## Initial location and required-file verification

First command:

```bash
pwd
```

Raw result (exit 0):

```text
/home/genomix-node/poker-solver
```

Initial required-file command:

```bash
ls -l ARCHITECTURE_PHASE4_S3.md src/poker_solver/nplayer_preflop.py src/poker_solver/sizing.py tests/test_nplayer_preflop_config.py tests/test_sizing.py research/phase4/s3-i1-repair-audit/CANDIDATE_MANIFEST.md; cat research/phase4/s3-i1-repair-audit/CANDIDATE_MANIFEST.md
```

All six paths existed (exit 0). The manifest contained exactly nine SHA-256 rows. The following command then verified every row relative to the verified working directory before source review and execution; reading every path also verifies all nine candidate files exist.

```bash
python - <<'PY'
import pathlib,re,hashlib
root=pathlib.Path.cwd()
rows=re.findall(r'^- ([0-9a-f]{64})  (.+)$',(root/'research/phase4/s3-i1-repair-audit/CANDIDATE_MANIFEST.md').read_text(),re.M)
assert len(rows)==9,len(rows)
for expected,name in rows:
 actual=hashlib.sha256((root/name).read_bytes()).hexdigest()
 print(f'{name}: expected={expected} actual={actual} match={actual==expected}')
 assert actual==expected
print('MANIFEST: 9/9 PASS')
PY
```

Raw result (exit 0):

```text
ARCHITECTURE_PHASE4_S3.md: expected=a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6 actual=a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6 match=True
src/poker_solver/nplayer_preflop.py: expected=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812 actual=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812 match=True
src/poker_solver/sizing.py: expected=8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240 actual=8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240 match=True
tests/test_nplayer_preflop_config.py: expected=bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268 actual=bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268 match=True
tests/test_nplayer_preflop_betting.py: expected=9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd actual=9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd match=True
tests/test_nplayer_preflop_settlement.py: expected=e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3 actual=e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3 match=True
tests/test_nplayer_preflop_information.py: expected=0d800d2f8fe797f29d8a347e1ab216bbc079fee0ede792ab253db23097819445 actual=0d800d2f8fe797f29d8a347e1ab216bbc079fee0ede792ab253db23097819445 match=True
tests/test_sizing.py: expected=2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1 actual=2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1 match=True
research/phase4/s3-i1-repair/RED_RECEIPT.md: expected=61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11 actual=61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11 match=True
MANIFEST: 9/9 PASS
```

## Focused tests

Bytecode writing was disabled to preserve the read-only candidate. The requested pytest invocation otherwise ran unchanged; cacheprovider was disabled as requested.

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/test_nplayer_preflop_config.py tests/test_sizing.py
```

Raw result (exit 0):

```text
........................................................                 [100%]
56 passed in 0.24s
```

## Independent temporary production-importing probe

The following exact command creates the probe outside the repo under /tmp, imports the actual production module (asserting its resolved path), runs all attacks without importing test helpers, and deletes the temporary file in a finally block. The command embeds the complete independent probe source for reproduction.

```bash
python - <<'PY'
import os, pathlib, subprocess, tempfile
source = "from dataclasses import replace\nfrom decimal import Decimal\nfrom fractions import Fraction\nfrom pathlib import Path\nimport operator\nimport poker_solver.nplayer_preflop as production\nfrom poker_solver.nplayer_preflop import NPlayerPreflopConfig as Config, NPlayerPreflopContinuation as Cont, NPlayerPreflopSizingRule as Rule, create_nplayer_preflop_root as root, enumerate_nplayer_preflop_deals as deals\nfrom poker_solver.preflop import WeightedCombo as Combo\nfrom poker_solver.game_structure import ForcedPost as Post\nfrom poker_solver.model import Action\nfrom poker_solver.sizing import validate_size_expression as validate, convert_size_to_chips as convert, fixed_sizes\nassert Path(production.__file__).resolve() == Path('/home/genomix-node/poker-solver/src/poker_solver/nplayer_preflop.py')\nprint('PRODUCTION_IMPORT', production.__file__)\npassed=0\nfailures=[]\ndef reject(label, fn, types=(ValueError,)):\n    global passed\n    try: fn()\n    except types as e:\n        passed+=1\n        print('PASS',label,type(e).__name__,str(e))\n    except Exception as e:\n        failures.append(label)\n        print('FAIL',label,'unexpected',type(e).__name__,str(e))\n    else:\n        failures.append(label)\n        print('FAIL',label,'accepted')\ndef check(label, fn):\n    global passed\n    try:\n        assert fn()\n        passed+=1\n        print('PASS',label)\n    except Exception as e:\n        failures.append(label)\n        print('FAIL',label,type(e).__name__,str(e))\nempty=Cont('terminal-table','C3I1-1R independent','supplied',{}, {}, ())\ndef config(n=2, **kw):\n    args=dict(version='nplayer-preflop-v1',num_players=n,button=0 if n==2 else n-1,\n        starting_stacks=(40,)*n,forced_posts=(Post(0,'small-blind',1),Post(1,'big-blind',2)),\n        straddle_variant='none',ranges=tuple((Combo((2*i,2*i+1),Fraction(1)),) for i in range(n)),\n        sizing_rules=(),max_raises=2,max_deals=1,max_nodes=1000,short_all_in_reopens=False,continuation=empty)\n    args.update(kw)\n    return Config(**args)\nbase=config()\nfor n in range(2,10):\n    check('valid-N-'+str(n),lambda n=n: root(config(n)).pot==3 and deals(config(n))[0][1]==1)\nfor field, bads in {\n    'num_players':(True,False,2.0,'2',1,10),\n    'button':(True,0.0,-1,2),\n    'max_raises':(True,1.0,0,-1,1000),\n    'max_deals':(False,1.0,0,-1),\n    'max_nodes':(True,2.0,0,-1),\n    'short_all_in_reopens':(0,1,None),\n    'starting_stacks':([40,40],(40,),(True,40),(40.0,40),(0,40)),\n    'ranges':([],(),((),base.ranges[1]),([base.ranges[0][0]],base.ranges[1]),((object(),),base.ranges[1])),\n    'forced_posts':([],(),(object(),)),\n    'sizing_rules':([], (object(),)),\n    'continuation':(None,object()),\n    'version':('bad',True),\n    'straddle_variant':('bad',True)\n}.items():\n    for i,bad in enumerate(bads):\n        reject(f'config-{field}-{i}',lambda field=field,bad=bad: replace(base,**{field:bad}))\nfor cards in ((False,2),(0.0,2),(-1,2),(0,52),(1,1),(0,),[0,1]):\n    reject('cards-'+repr(cards),lambda cards=cards: config(ranges=((Combo(cards,1),),base.ranges[1])))\nfor w in (True,0,-1,float('nan'),float('inf'),Decimal('NaN'),Decimal('Infinity')):\n    reject('weight-'+repr(w),lambda w=w: config(ranges=((Combo((0,1),w),),base.ranges[1])))\nreject('reversed-duplicate-combo',lambda: config(ranges=((Combo((0,1),1),Combo((1,0),2)),base.ranges[1]),max_deals=2))\nreject('no-compatible-deal',lambda: config(ranges=(base.ranges[0],base.ranges[0])))\nreject('product-bound-before-blockers',lambda: config(ranges=((Combo((0,1),1),Combo((0,2),1)),(Combo((0,3),1),Combo((0,4),1))),max_deals=3))\nreject('chance-node-bound',lambda: root(config(max_nodes=1)))\nfor kind in ('dead-blind','bring-in','garbage',None,42,True,[],{}):\n    reject('post-kind-'+repr(kind),lambda kind=kind: config(forced_posts=base.forced_posts+(Post(0,kind,1),)))\nfor seat in (True,0.0,-1,2):\n    reject('post-seat-'+repr(seat),lambda seat=seat: config(forced_posts=base.forced_posts+(Post(seat,'ante',1),)),(ValueError,TypeError))\nfor amount in (True,1.0,0,-1,41):\n    reject('post-amount-'+repr(amount),lambda amount=amount: config(forced_posts=(Post(0,'small-blind',amount),Post(1,'big-blind',2))),(ValueError,TypeError))\nfor label,posts in (\n    ('duplicate-blind',base.forced_posts+(Post(0,'small-blind',1),)),\n    ('wrong-blind-seats',(Post(1,'small-blind',1),Post(0,'big-blind',2))),\n    ('partial-ante',base.forced_posts+(Post(0,'ante',1),)),\n    ('unequal-ante',base.forced_posts+(Post(0,'ante',1),Post(1,'ante',2))),\n    ('cumulative-overstack',base.forced_posts+(Post(0,'ante',39),Post(1,'ante',39))),\n    ('undeclared-straddle',base.forced_posts+(Post(0,'straddle',4),))):\n    reject(label,lambda posts=posts: config(forced_posts=posts))\nreject('degenerate-posts',lambda: config(starting_stacks=(1,40)))\nd=((0,1),(2,3))\nranks=Cont('showdown-ranks','probe','supplied',{}, {d:(3,2)},(0,1))\nfor order in ((False,True),(0.0,1.0),(0,True),(0,1.0),(0,0),(-1,0),[0,1],(0,), (0,2)):\n    reject('odd-order-'+repr(order),lambda order=order: config(continuation=replace(ranks,odd_chip_order=order)))\nfor field,bads in {\n    'kind':('bad',),'provenance':('', '  ',None),'source':('bad',),\n    'showdown_ranks':({d:(True,2)},{d:(1.0,2)},{d:(1,)},{},{((0,1),(0,2)):(1,2)}),\n    'payoff_table':({(d,()):(Fraction(0),Fraction(0))},)\n}.items():\n    for i,bad in enumerate(bads):\n        reject(f'continuation-{field}-{i}',lambda field=field,bad=bad: config(continuation=replace(ranks,**{field:bad})))\nfor values in ((True,-1),(1,1),(1,), (Decimal('NaN'),0),(Decimal('Infinity'),0)):\n    reject('payoff-'+repr(values),lambda values=values: config(continuation=replace(empty,payoff_table={(d,()):values})))\nreject('missing-table-leaf',lambda: root(base).child(Action('DEAL',0)).child(Action('CALL',2)).child(Action('CHECK')))\nrule=Rule('BTN/SB',0,0,'NA',({'unit':'big-blinds','value':3},))\nreject('duplicate-sizing-key-different-expression',lambda: config(sizing_rules=(rule,replace(rule,expressions=({'unit':'all-in'},)))))\nfor field,bad in (('position','UTG'),('raise_count',True),('raise_count',0.0),('cold_callers',False),('relation','bad'),('expressions',())):\n    reject('rule-'+field+'-'+repr(bad),lambda field=field,bad=bad: config(sizing_rules=(replace(rule,**{field:bad}),)))\nctx=dict(pot=3,own_commitment=1,highest_commitment=2,remaining_stack=39,big_blind=2,\n    minimum_raise_to=4,pot_limit_max_raise_to=None,short_all_in_allowed=True)\nfor unit,field in (('big-blinds','value'),('pot-percent','value'),('previous-bet-multiple','value'),('geometric','scale'),('geometric','streets')):\n    for bad in (True,Decimal('NaN'),Decimal('sNaN'),Decimal('Infinity'),Decimal('-Infinity'),{'nested':[3]},[3]):\n        expr={'unit':unit,field:bad}\n        if unit=='geometric': expr={'unit':unit,'streets':2,'scale':1,field:bad}\n        reject('sizing-'+unit+'-'+field+'-'+repr(bad),lambda expr=expr: validate(expr))\n        reject('rule-normalization-'+unit+'-'+field+'-'+repr(bad),lambda expr=expr: replace(rule,expressions=(expr,)))\nfor field in ('pot','own_commitment','highest_commitment','remaining_stack','big_blind','minimum_raise_to','pot_limit_max_raise_to'):\n    for bad in (True,1.5):\n        reject('context-'+field+'-'+repr(bad),lambda field=field,bad=bad: fixed_sizes(({'unit':'all-in'},),{**ctx,field:bad}))\na={'unit':'big-blinds','value':Decimal('3')}\nb={'unit':'geometric','streets':2,'scale':1}\nfrozen=replace(rule,expressions=(a,b))\nequivalent=replace(rule,expressions=({'value':Decimal('3'),'unit':'big-blinds'},dict(b)))\nstate=root(config(sizing_rules=(frozen,))).child(Action('DEAL',0))\nsnapshot=(hash(frozen),state.legal_actions(),state.information_state_key(0))\nlookup={frozen:'present'}\na['value']=19\nb['scale']=50\nfor i,e in enumerate(frozen.expressions):\n    reject('mutation-item-'+str(i),lambda e=e: operator.setitem(e,'unit','all-in'),(TypeError,AttributeError))\n    reject('mutation-backing-'+str(i),lambda e=e: setattr(e,'_items',()),(TypeError,AttributeError))\n    reject('mutation-backing-tuple-'+str(i),lambda e=e: operator.setitem(e._items,0,('unit','all-in')),(TypeError,AttributeError))\n    reject('mutation-dict-'+str(i),lambda e=e: e.__dict__.update({'_items':()}),(TypeError,AttributeError))\ncheck('detachment-actions-key-hash',lambda: snapshot==(hash(frozen),state.legal_actions(),state.information_state_key(0)))\ncheck('equality-order-hash-lookup',lambda: frozen==equivalent and hash(frozen)==hash(equivalent) and lookup[equivalent]=='present')\ntable={(d,()):(Fraction(1),Fraction(-1))}\ndetached=replace(empty,payoff_table=table)\ntable.clear()\ncheck('payoff-caller-detachment',lambda: detached.payoff_table[(d,())]==(1,-1))\nreject('payoff-readonly',lambda: operator.setitem(detached.payoff_table,(d,()),(0,0)),(TypeError,))\nrankdict={d:(3,2)}\ndetached_ranks=replace(ranks,showdown_ranks=rankdict)\nrankdict.clear()\ncheck('rank-caller-detachment',lambda: detached_ranks.showdown_ranks[d]==(3,2))\nreject('ranks-readonly',lambda: operator.setitem(detached_ranks.showdown_ranks,d,(2,3)),(TypeError,))\ncheck('decimal-finite-half-up',lambda: convert({'unit':'big-blinds','value':Decimal('2.25')},ctx)==5)\ncheck('target-dedup-first-order',lambda: tuple(x.target for x in fixed_sizes(({'unit':'big-blinds','value':3},{'unit':'previous-bet-multiple','value':3},{'unit':'all-in'}),ctx))==(6,40))\nprint('SUMMARY passed='+str(passed)+' blockers='+str(len(failures)))\nraise SystemExit(bool(failures))\n"
fd, name = tempfile.mkstemp(prefix='C3I1-1R-', suffix='.py', dir='/tmp')
os.close(fd)
p = pathlib.Path(name)
try:
 p.write_text(source)
 print('TEMP_PROBE='+name, flush=True)
 result=subprocess.run(['uv','run','python','-B',name],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 print('PROBE_EXIT='+str(result.returncode),flush=True)
finally:
 p.unlink()
 print('TEMP_PROBE_DELETED='+str(not p.exists()),flush=True)
raise SystemExit(result.returncode)
PY
```

Raw result (exit 0):

```text
TEMP_PROBE=/tmp/C3I1-1R-mc7x1kwr.py
PRODUCTION_IMPORT /home/genomix-node/poker-solver/src/poker_solver/nplayer_preflop.py
PASS valid-N-2
PASS valid-N-3
PASS valid-N-4
PASS valid-N-5
PASS valid-N-6
PASS valid-N-7
PASS valid-N-8
PASS valid-N-9
PASS config-num_players-0 ValueError num_players must be an integer from 2 to 9
PASS config-num_players-1 ValueError num_players must be an integer from 2 to 9
PASS config-num_players-2 ValueError num_players must be an integer from 2 to 9
PASS config-num_players-3 ValueError num_players must be an integer from 2 to 9
PASS config-num_players-4 ValueError num_players must be an integer from 2 to 9
PASS config-num_players-5 ValueError num_players must be an integer from 2 to 9
PASS config-button-0 ValueError button must be a valid integer seat
PASS config-button-1 ValueError button must be a valid integer seat
PASS config-button-2 ValueError button must be a valid integer seat
PASS config-button-3 ValueError button must be a valid integer seat
PASS config-max_raises-0 ValueError max_raises must be a non-negative integer
PASS config-max_raises-1 ValueError max_raises must be a non-negative integer
PASS config-max_raises-2 ValueError max_raises must be positive
PASS config-max_raises-3 ValueError max_raises must be a non-negative integer
PASS config-max_raises-4 ValueError max_raises exceeds the supported structural depth bound
PASS config-max_deals-0 ValueError max_deals must be a non-negative integer
PASS config-max_deals-1 ValueError max_deals must be a non-negative integer
PASS config-max_deals-2 ValueError max_deals must be positive
PASS config-max_deals-3 ValueError max_deals must be a non-negative integer
PASS config-max_nodes-0 ValueError max_nodes must be a non-negative integer
PASS config-max_nodes-1 ValueError max_nodes must be a non-negative integer
PASS config-max_nodes-2 ValueError max_nodes must be positive
PASS config-max_nodes-3 ValueError max_nodes must be a non-negative integer
PASS config-short_all_in_reopens-0 ValueError short_all_in_reopens must be boolean
PASS config-short_all_in_reopens-1 ValueError short_all_in_reopens must be boolean
PASS config-short_all_in_reopens-2 ValueError short_all_in_reopens must be boolean
PASS config-starting_stacks-0 ValueError starting_stacks length must equal num_players
PASS config-starting_stacks-1 ValueError starting_stacks length must equal num_players
PASS config-starting_stacks-2 ValueError starting stack must be a non-negative integer
PASS config-starting_stacks-3 ValueError starting stack must be a non-negative integer
PASS config-starting_stacks-4 ValueError starting stack must be positive
PASS config-ranges-0 ValueError ranges length must equal num_players
PASS config-ranges-1 ValueError ranges length must equal num_players
PASS config-ranges-2 ValueError each range must be a non-empty tuple
PASS config-ranges-3 ValueError each range must be a non-empty tuple
PASS config-ranges-4 ValueError ranges must contain WeightedCombo values
PASS config-forced_posts-0 ValueError forced_posts must be a tuple
PASS config-forced_posts-1 ValueError exactly one small blind is required on the derived SB seat
PASS config-forced_posts-2 ValueError forced_posts must contain ForcedPost values
PASS config-sizing_rules-0 ValueError sizing_rules must be a tuple
PASS config-sizing_rules-1 ValueError sizing rules must use canonical positions
PASS config-continuation-0 ValueError continuation must be NPlayerPreflopContinuation
PASS config-continuation-1 ValueError continuation must be NPlayerPreflopContinuation
PASS config-version-0 ValueError version must be nplayer-preflop-v1
PASS config-version-1 ValueError version must be nplayer-preflop-v1
PASS config-straddle_variant-0 ValueError invalid straddle_variant
PASS config-straddle_variant-1 ValueError invalid straddle_variant
PASS cards-(False, 2) ValueError cards must be two distinct non-negative integers
PASS cards-(0.0, 2) ValueError cards must be two distinct non-negative integers
PASS cards-(-1, 2) ValueError cards must be two distinct non-negative integers
PASS cards-(0, 52) ValueError range combos must contain valid cards in 0..51
PASS cards-(1, 1) ValueError cards must be two distinct non-negative integers
PASS cards-(0,) ValueError cards must be two distinct non-negative integers
PASS cards-[0, 1] ValueError cards must be two distinct non-negative integers
PASS weight-True ValueError weight must be an exact positive rational
PASS weight-0 ValueError weight must be an exact positive rational
PASS weight--1 ValueError weight must be an exact positive rational
PASS weight-nan ValueError weight must be an exact positive rational
PASS weight-inf ValueError weight must be an exact positive rational
PASS weight-Decimal('NaN') ValueError weight must be an exact positive rational
PASS weight-Decimal('Infinity') ValueError weight must be an exact positive rational
PASS reversed-duplicate-combo ValueError range combos must be unique within a seat
PASS no-compatible-deal ValueError ranges produce no compatible deals
PASS product-bound-before-blockers ValueError candidate product exceeds max_deals
PASS chance-node-bound ValueError node bound too small for chance expansion
PASS post-kind-'dead-blind' ValueError unsupported forced post kind
PASS post-kind-'bring-in' ValueError unsupported forced post kind
PASS post-kind-'garbage' ValueError unsupported forced post kind
PASS post-kind-None ValueError unsupported forced post kind
PASS post-kind-42 ValueError unsupported forced post kind
PASS post-kind-True ValueError unsupported forced post kind
PASS post-kind-[] ValueError unsupported forced post kind
PASS post-kind-{} ValueError unsupported forced post kind
PASS post-seat-True TypeError bool-as-int rejected
PASS post-seat-0.0 ValueError seat must be non-negative int, got 0.0
PASS post-seat--1 ValueError seat must be non-negative int, got -1
PASS post-seat-2 ValueError forced post references an invalid seat
PASS post-amount-True TypeError bool-as-int rejected
PASS post-amount-1.0 ValueError amount must be non-negative int, got 1.0
PASS post-amount-0 ValueError forced post amount must be positive
PASS post-amount--1 ValueError amount must be non-negative int, got -1
PASS post-amount-41 ValueError cumulative forced posts exceed a starting stack
PASS duplicate-blind ValueError exactly one small blind is required on the derived SB seat
PASS wrong-blind-seats ValueError exactly one small blind is required on the derived SB seat
PASS partial-ante ValueError antes must be one identical positive ante for every seat
PASS unequal-ante ValueError antes must be one identical positive ante for every seat
PASS cumulative-overstack ValueError cumulative forced posts exceed a starting stack
PASS undeclared-straddle ValueError straddle_variant none cannot declare a straddle
PASS degenerate-posts ValueError at least two seats must have chips after forced posts
PASS odd-order-(False, True) ValueError odd_chip_order must contain unique non-negative integer seats
PASS odd-order-(0.0, 1.0) ValueError odd_chip_order must contain unique non-negative integer seats
PASS odd-order-(0, True) ValueError odd_chip_order must contain unique non-negative integer seats
PASS odd-order-(0, 1.0) ValueError odd_chip_order must contain unique non-negative integer seats
PASS odd-order-(0, 0) ValueError odd_chip_order must contain unique non-negative integer seats
PASS odd-order-(-1, 0) ValueError odd_chip_order must contain unique non-negative integer seats
PASS odd-order-[0, 1] ValueError odd_chip_order must be a tuple
PASS odd-order-(0,) ValueError odd_chip_order must be a permutation of all seats
PASS odd-order-(0, 2) ValueError odd_chip_order must be a permutation of all seats
PASS continuation-kind-0 ValueError continuation kind must be terminal-table or showdown-ranks
PASS continuation-provenance-0 ValueError continuation provenance must be non-empty
PASS continuation-provenance-1 ValueError continuation provenance must be non-empty
PASS continuation-provenance-2 ValueError continuation provenance must be non-empty
PASS continuation-source-0 ValueError continuation source must be supplied or derived
PASS continuation-showdown_ranks-0 ValueError invalid showdown-ranks entry
PASS continuation-showdown_ranks-1 ValueError invalid showdown-ranks entry
PASS continuation-showdown_ranks-2 ValueError showdown-ranks entries must contain one rank per seat
PASS continuation-showdown_ranks-3 ValueError showdown ranks must cover exactly every compatible deal
PASS continuation-showdown_ranks-4 ValueError showdown-ranks entries must contain one rank per seat
PASS continuation-payoff_table-0 ValueError showdown-ranks continuation cannot contain payoff values
PASS payoff-(True, -1) ValueError invalid terminal-table entry
PASS payoff-(1, 1) ValueError terminal values must be finite and zero-sum
PASS payoff-(1,) ValueError terminal values must be finite and zero-sum
PASS payoff-(Decimal('NaN'), 0) ValueError terminal values must be finite exact numbers
PASS payoff-(Decimal('Infinity'), 0) ValueError terminal values must be finite exact numbers
PASS missing-table-leaf ValueError missing continuation value for closed preflop leaf
PASS duplicate-sizing-key-different-expression ValueError duplicate sizing rule key
PASS rule-position-'UTG' ValueError sizing rules must use canonical positions
PASS rule-raise_count-True ValueError raise_count must be a non-negative integer
PASS rule-raise_count-0.0 ValueError raise_count must be a non-negative integer
PASS rule-cold_callers-False ValueError cold_callers must be a non-negative integer
PASS rule-relation-'bad' ValueError relation must be NA, IP, or OOP
PASS rule-expressions-() ValueError expressions must be a non-empty tuple
PASS sizing-big-blinds-value-True ValueError big-blinds value must not be a boolean
PASS rule-normalization-big-blinds-value-True ValueError invalid sizing expression
PASS sizing-big-blinds-value-Decimal('NaN') ValueError big-blinds value must be finite
PASS rule-normalization-big-blinds-value-Decimal('NaN') ValueError invalid sizing expression
PASS sizing-big-blinds-value-Decimal('sNaN') ValueError big-blinds value must be finite
PASS rule-normalization-big-blinds-value-Decimal('sNaN') ValueError invalid sizing expression
PASS sizing-big-blinds-value-Decimal('Infinity') ValueError big-blinds value must be finite
PASS rule-normalization-big-blinds-value-Decimal('Infinity') ValueError invalid sizing expression
PASS sizing-big-blinds-value-Decimal('-Infinity') ValueError big-blinds value must be finite
PASS rule-normalization-big-blinds-value-Decimal('-Infinity') ValueError invalid sizing expression
PASS sizing-big-blinds-value-{'nested': [3]} ValueError big-blinds value must be numeric
PASS rule-normalization-big-blinds-value-{'nested': [3]} ValueError invalid sizing expression
PASS sizing-big-blinds-value-[3] ValueError big-blinds value must be numeric
PASS rule-normalization-big-blinds-value-[3] ValueError invalid sizing expression
PASS sizing-pot-percent-value-True ValueError pot-percent value must not be a boolean
PASS rule-normalization-pot-percent-value-True ValueError invalid sizing expression
PASS sizing-pot-percent-value-Decimal('NaN') ValueError pot-percent value must be finite
PASS rule-normalization-pot-percent-value-Decimal('NaN') ValueError invalid sizing expression
PASS sizing-pot-percent-value-Decimal('sNaN') ValueError pot-percent value must be finite
PASS rule-normalization-pot-percent-value-Decimal('sNaN') ValueError invalid sizing expression
PASS sizing-pot-percent-value-Decimal('Infinity') ValueError pot-percent value must be finite
PASS rule-normalization-pot-percent-value-Decimal('Infinity') ValueError invalid sizing expression
PASS sizing-pot-percent-value-Decimal('-Infinity') ValueError pot-percent value must be finite
PASS rule-normalization-pot-percent-value-Decimal('-Infinity') ValueError invalid sizing expression
PASS sizing-pot-percent-value-{'nested': [3]} ValueError pot-percent value must be numeric
PASS rule-normalization-pot-percent-value-{'nested': [3]} ValueError invalid sizing expression
PASS sizing-pot-percent-value-[3] ValueError pot-percent value must be numeric
PASS rule-normalization-pot-percent-value-[3] ValueError invalid sizing expression
PASS sizing-previous-bet-multiple-value-True ValueError previous-bet-multiple value must not be a boolean
PASS rule-normalization-previous-bet-multiple-value-True ValueError invalid sizing expression
PASS sizing-previous-bet-multiple-value-Decimal('NaN') ValueError previous-bet-multiple value must be finite
PASS rule-normalization-previous-bet-multiple-value-Decimal('NaN') ValueError invalid sizing expression
PASS sizing-previous-bet-multiple-value-Decimal('sNaN') ValueError previous-bet-multiple value must be finite
PASS rule-normalization-previous-bet-multiple-value-Decimal('sNaN') ValueError invalid sizing expression
PASS sizing-previous-bet-multiple-value-Decimal('Infinity') ValueError previous-bet-multiple value must be finite
PASS rule-normalization-previous-bet-multiple-value-Decimal('Infinity') ValueError invalid sizing expression
PASS sizing-previous-bet-multiple-value-Decimal('-Infinity') ValueError previous-bet-multiple value must be finite
PASS rule-normalization-previous-bet-multiple-value-Decimal('-Infinity') ValueError invalid sizing expression
PASS sizing-previous-bet-multiple-value-{'nested': [3]} ValueError previous-bet-multiple value must be numeric
PASS rule-normalization-previous-bet-multiple-value-{'nested': [3]} ValueError invalid sizing expression
PASS sizing-previous-bet-multiple-value-[3] ValueError previous-bet-multiple value must be numeric
PASS rule-normalization-previous-bet-multiple-value-[3] ValueError invalid sizing expression
PASS sizing-geometric-scale-True ValueError geometric scale must not be a boolean
PASS rule-normalization-geometric-scale-True ValueError invalid sizing expression
PASS sizing-geometric-scale-Decimal('NaN') ValueError geometric scale must be finite
PASS rule-normalization-geometric-scale-Decimal('NaN') ValueError invalid sizing expression
PASS sizing-geometric-scale-Decimal('sNaN') ValueError geometric scale must be finite
PASS rule-normalization-geometric-scale-Decimal('sNaN') ValueError invalid sizing expression
PASS sizing-geometric-scale-Decimal('Infinity') ValueError geometric scale must be finite
PASS rule-normalization-geometric-scale-Decimal('Infinity') ValueError invalid sizing expression
PASS sizing-geometric-scale-Decimal('-Infinity') ValueError geometric scale must be finite
PASS rule-normalization-geometric-scale-Decimal('-Infinity') ValueError invalid sizing expression
PASS sizing-geometric-scale-{'nested': [3]} ValueError geometric scale must be numeric
PASS rule-normalization-geometric-scale-{'nested': [3]} ValueError invalid sizing expression
PASS sizing-geometric-scale-[3] ValueError geometric scale must be numeric
PASS rule-normalization-geometric-scale-[3] ValueError invalid sizing expression
PASS sizing-geometric-streets-True ValueError geometric streets must not be a boolean
PASS rule-normalization-geometric-streets-True ValueError invalid sizing expression
PASS sizing-geometric-streets-Decimal('NaN') ValueError geometric streets must be finite
PASS rule-normalization-geometric-streets-Decimal('NaN') ValueError invalid sizing expression
PASS sizing-geometric-streets-Decimal('sNaN') ValueError geometric streets must be finite
PASS rule-normalization-geometric-streets-Decimal('sNaN') ValueError invalid sizing expression
PASS sizing-geometric-streets-Decimal('Infinity') ValueError geometric streets must be finite
PASS rule-normalization-geometric-streets-Decimal('Infinity') ValueError invalid sizing expression
PASS sizing-geometric-streets-Decimal('-Infinity') ValueError geometric streets must be finite
PASS rule-normalization-geometric-streets-Decimal('-Infinity') ValueError invalid sizing expression
PASS sizing-geometric-streets-{'nested': [3]} ValueError geometric streets must be numeric
PASS rule-normalization-geometric-streets-{'nested': [3]} ValueError invalid sizing expression
PASS sizing-geometric-streets-[3] ValueError geometric streets must be numeric
PASS rule-normalization-geometric-streets-[3] ValueError invalid sizing expression
PASS context-pot-True ValueError pot must be a non-negative integer
PASS context-pot-1.5 ValueError pot must be a non-negative integer
PASS context-own_commitment-True ValueError own_commitment must be a non-negative integer
PASS context-own_commitment-1.5 ValueError own_commitment must be a non-negative integer
PASS context-highest_commitment-True ValueError highest_commitment must be a non-negative integer
PASS context-highest_commitment-1.5 ValueError highest_commitment must be a non-negative integer
PASS context-remaining_stack-True ValueError remaining_stack must be a non-negative integer
PASS context-remaining_stack-1.5 ValueError remaining_stack must be a non-negative integer
PASS context-big_blind-True ValueError big_blind must be a non-negative integer
PASS context-big_blind-1.5 ValueError big_blind must be a non-negative integer
PASS context-minimum_raise_to-True ValueError minimum_raise_to must be a non-negative integer
PASS context-minimum_raise_to-1.5 ValueError minimum_raise_to must be a non-negative integer
PASS context-pot_limit_max_raise_to-True ValueError pot_limit_max_raise_to must be a non-negative integer or None
PASS context-pot_limit_max_raise_to-1.5 ValueError pot_limit_max_raise_to must be a non-negative integer or None
PASS mutation-item-0 TypeError '_FrozenExpression' object does not support item assignment
PASS mutation-backing-0 FrozenInstanceError cannot assign to field '_items'
PASS mutation-backing-tuple-0 TypeError 'tuple' object does not support item assignment
PASS mutation-dict-0 AttributeError '_FrozenExpression' object has no attribute '__dict__'
PASS mutation-item-1 TypeError '_FrozenExpression' object does not support item assignment
PASS mutation-backing-1 FrozenInstanceError cannot assign to field '_items'
PASS mutation-backing-tuple-1 TypeError 'tuple' object does not support item assignment
PASS mutation-dict-1 AttributeError '_FrozenExpression' object has no attribute '__dict__'
PASS detachment-actions-key-hash
PASS equality-order-hash-lookup
PASS payoff-caller-detachment
PASS payoff-readonly TypeError 'mappingproxy' object does not support item assignment
PASS rank-caller-detachment
PASS ranks-readonly TypeError 'mappingproxy' object does not support item assignment
PASS decimal-finite-half-up
PASS target-dedup-first-order
SUMMARY passed=230 blockers=0
PROBE_EXIT=0
TEMP_PROBE_DELETED=True
```

## Post-execution frozen-candidate verification

Repeated the identical nine-row verifier after tests/probe. Raw result (exit 0):

```text
ARCHITECTURE_PHASE4_S3.md: expected=a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6 actual=a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6 match=True
src/poker_solver/nplayer_preflop.py: expected=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812 actual=a960108af02dc56fc63c5dd4f6cc1d1ea83e782991c1370303f9cc3cc6f5f812 match=True
src/poker_solver/sizing.py: expected=8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240 actual=8483502edd38a7071fb43e109af657f1730efc9c924f3298e646258e515e3240 match=True
tests/test_nplayer_preflop_config.py: expected=bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268 actual=bc928536872f9bd239b6fa4e50d5bf4a3ffd777af6875e6b456881f4e7034268 match=True
tests/test_nplayer_preflop_betting.py: expected=9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd actual=9429dfff65586f0dc915c58e44b221e78748c6dbdfdc19cbf9b012b55f0cb6dd match=True
tests/test_nplayer_preflop_settlement.py: expected=e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3 actual=e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3 match=True
tests/test_nplayer_preflop_information.py: expected=0d800d2f8fe797f29d8a347e1ab216bbc079fee0ede792ab253db23097819445 actual=0d800d2f8fe797f29d8a347e1ab216bbc079fee0ede792ab253db23097819445 match=True
tests/test_sizing.py: expected=2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1 actual=2ee84a8b244b39c050301678df0be653045dfc390085b9b8e54dcf42319b95a1 match=True
research/phase4/s3-i1-repair/RED_RECEIPT.md: expected=61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11 actual=61cd31f21bd75c371f6c93e30200431b7c63cbc673ceffaecb12e8cf76a63a11 match=True
MANIFEST: 9/9 PASS
```

## Completion timestamp and write scope

```bash
date -u '+%Y-%m-%dT%H:%M:%SZ'
```

Raw result (exit 0):

```text
2026-09-16T06:31:41Z
```

Only the assigned report and .hb/C3I1-1R are persistent audit outputs. The temporary probe was removed. No source, tests, manifest, STATE.txt, PROGRESS.md, other evidence, git index, or commits were edited by this audit. Both assigned outputs are read back before exit using:

```bash
cat research/phase4/s3-i1-repair-audit/01-config-sizing.md research/phase4/s3-i1-repair-audit/.hb/C3I1-1R
```
