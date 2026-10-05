# C4D5-CODEX — fixtures, TDD sequencing, and release audit

Verdict: **PASS** (DESIGN checkpoint only). Blocking findings: **0**.

Independent non-author audit of the frozen architecture. S4 production and permanent tests do not exist yet; their absence is expected. This verdict approves the specification within the assigned scope, not any future implementation or release. No source, tests, architecture, manifest, mission, STATE.txt, PROGRESS.md, or Git objects were edited. Probes imported accepted production with bytecode writes disabled and switched their working directory to /tmp; no probe files were written.

## Authentication and source boundary

Executed from /home/genomix-node/poker-solver:

```sh
git rev-parse HEAD phase3-398-green 'phase3-398-green^{}'
```

Output:
```
149780bf37e3e3a824e03e6d2c1df3cd99b12cd6
feba8222a0b614b0c64eca59402403ce733195ea
5809ecca28ae6d0588ea07709c90beac3072c167
```

`git cat-file -t phase3-398-green` returned `tag`. The frozen requirement is the annotated tag object, not its peeled commit; both were distinguished correctly.

```sh
sha256sum ARCHITECTURE_PHASE4_S4.md PHASE4_MISSION.md research/phase4/s4-design/02-engine-integration-codex.md
sha256sum research/phase4/s4-design-audit/CANDIDATE_MANIFEST.md
```

Output:
```
4285905100a11e3523b241f236233118bb9f4dac67f7c8aa92570fba3048a0e3  ARCHITECTURE_PHASE4_S4.md
5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61  PHASE4_MISSION.md
79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d  research/phase4/s4-design/02-engine-integration-codex.md
db0932118f6370fcaf432fed35e9bd3e170974deb3a379bbe955e42a4b7fd76c  research/phase4/s4-design-audit/CANDIDATE_MANIFEST.md
```

All three literal manifest rows match. The authoritative input's C4D2-CODEX heartbeat also contains its matching report hash. This checks artifact identity; it does not substitute for the parent's transcript authentication.

`git diff --check` and `git diff --exit-code HEAD -- src tests scripts pyproject.toml PHASE4_MISSION.md` exited 0 without output.

`git status --short` before this report:
```
 M PROGRESS.md
 M STATE.txt
?? ARCHITECTURE_PHASE4_S4.md
?? research/phase4/s4-design-audit/
?? research/phase4/s4-design/
```

These preexisting parent/research changes do not alter the accepted production snapshot. No clean-worktree claim is made.

Read the candidate, manifest, mission, pyproject, test inventory, and relevant accepted source: multistreet config/deal/runout/action/settlement, evaluator, WeightedCombo, bounded history traversal, CFR, complete_strategy, NashConv, allstreet translation/preflight, and v4 dispatch. The bounded validator counts history occurrences, including root; it does not count infosets. Allstreet translation enables river betting, matching the fixtures.

## Fixture conclusions

**Small fixture: PASS.** Four compatible equally weighted worlds; full signatures yield P0 bucket size [2], P1 sizes [1,1]. Evaluator outcomes contain both ties and P0 losses, not a constant terminal payoff game. Actual traversal gives 321 nodes, 136 terminals, 57 chance, 128 decisions, depth 12. There are 32 flop, 32 turn, and 64 river decision occurrences, with CHECK/RAISE/FOLD/CALL reachable. Jh has probability 1; after Jh each declared river has probability 1/2. The exact 1,000-iteration solve reproduces the frozen reference receipt exactly and clears the preregistered 0.02 threshold. The future lifted policy's threshold remains an implementation gate.

**Large fixture: PASS.** Each distinct 12-card pool yields C(12,2)=66 holdings. The pools are disjoint from each other and from every public board/runout card. Thus all 66*66=4,356 pairs are compatible and each admits both ordered runouts. Every no-Th P1 holding ties P0; every Th holding wins, verified through evaluate_seven for all labelled cells. There are C(11,2)=55 no-Th hands and 11 Th hands; exact pair masses are 5/6 and 1/6.

Single-world traversal, checked for both P1 signature classes, gives 81 nodes (including the deal root), 34 terminals, 15 chance, 32 decisions, depth 12. Removing the repeated root gives 80 histories per world/pair:
- exact: 1+4,356*80=348,481;
- quotient: 1+2*80=161;
- quotient terminals/chance/decisions: 68/29/64;
- charged signature slots: 2*66*66*2=17,424;
- belief member entries: 4,356*4=17,424 for prefixes (), (Jh,), (Jh,9h), (Jh,8h), shared across betting histories.

348,481 and 161 are analytic counts here, not claimed executions of a full large exact tree or nonexistent reduced implementation. The current exact bounded validator was executed at cap 10,000 and failed with its node-cap error. Source allstreet solve places this preflight before CFR construction. Large private payoff classes, reachable betting on all streets, and actual cap failure make the acceptance comparison nonvacuous, while shallow stacks and restricted runouts remain explicit limitations.

**Blocker companions: feasible and nonvacuous.** Concrete independent witnesses establish the required tests can be written against accepted semantics. Opponent blocker: P0 {2c3c,2d3d}, P1 {2c4s,2s4d}, same public game, yields three compatible worlds, all legal showdowns tied, and both players' labelled signatures separate. Runout blocker: P0 {9h3c,2d3d}, P1 {Th4s}; both P0 hands have zero legal-showdown equity, but codes are [-2,-1] versus [-1,-1]. Both worlds retain a legal runout; none requires conditioning away a positive deal. The initial additional runout witness against 2s3s was also source-traversed (138 nodes), but is not the equal-equity witness.

## RED-first and dependency review

Architecture sections 10–11 impose a global requirement on every permanent test: import and invoke production; no placeholder/pass/caught-import trick; parent static inspection before GREEN; baseline controls separately during RED; final test bytes proven RED against the exact prior production snapshot. This applies to all six proposed permanent suites, not merely one positive smoke test.

| Batch / suites | Required production behavior and dependency | Finding |
|---|---|---|
| I1: test_abstraction_signatures.py | Strict AbstractionConfig, canonicalization, build_buckets, immutable signatures, exact labelled membership and blocker/cap controls; no compiler/solver stubs | PASS |
| I2: test_abstraction_reduced_game.py | Accepted I1 plus compile_reduced_game/ReducedState, source transitions, posterior/settlement/recall checks, physical 160-fail/161-pass boundary and traversal instrumentation | PASS |
| I3: test_abstraction_solve.py and test-only rational helpers | Accepted I2 plus real solver/lift/diagnostics; arbitrary nonuniform profile equality, independent exact incentives, tiny exhaustive response cross-check, small quality and large complete solve | PASS |
| I4: test_api_v4_abstraction.py | Accepted I3 through dispatch_v4; valid positive missing-operation RED, specific nested malformed-input validation after GREEN | PASS |
| I4: test_phase4_s4_examples.py | Executable examples and real CLI file/stdin/error paths; examples accepted only after their commands succeed | PASS |
| I4: test_phase4_s4_exports.py | Public production exports and invocation, under the global permanent-test rule; compatibility retained | PASS |

No future test body can be authenticated at a design checkpoint. The specification sufficiently requires genuine behavioral RED and prohibits accepting import-catch/placeholder false coverage. An uncaught missing-production import may initially prevent collection, but cannot replace parent inspection of the eventual test bodies or final-byte RED replay. Test-only rational helpers are independent oracles supporting production calls, not production substitutes.

The current dispatcher rejects an unknown operation before nested payload validation. That is precisely why I4 declares malformed cases controls until GREEN and requires a valid positive request as its missing-feature RED. The executed positive base request succeeds; the corresponding future S4 request fails only at the absent operation gate. No malformed unsupported-operation failure was counted as S4 validation evidence.

Batches are dependency-safe: signature policy -> physical state/compiler -> solve/lift/certificates -> API/exports/examples/docs. I1 expressly forbids future stubs; I2 forbids solve/API edits; I3 limits changes to solver and necessary lift/projection; I4 is additive and preserves prior operations. The I3 large solve precedes I4 strict serialization, and completion requires both.

## Post-batch gates and release sufficiency

**PASS.** Section 11 applies to each of the four batches, requiring final-byte RED proof, literal test/source/report hashes, focused tests without skipped/xfail placeholder coverage, relevant S1/API compatibility, compileall, full pytest with no exclusions, diff-check, root-resolved frozen manifest, exactly six wholly fresh BryantGPT non-authors with exclusive reports and completed flat heartbeats, and parent authentication of transcripts/hashes/probes/candidate pre/post identities/test receipts/HEAD/tag. Reproduced findings require new behavioral RED and a wholly fresh audit of changed bytes. An accepted commit is mandatory before the next batch begins. Mission additionally requires auditor execution, parent reruns, additive baseline preservation, and commits; these obligations are not waived by the design.

Current frozen design manifest identifies the architecture, accepted source HEAD, mission, authoritative design input and tag object. Implementation manifests/hashes and accepted commits are future per-batch requirements, not falsely supplied by this design manifest.

Section 12 closes release against the mission's S4 requirements: explicit deterministic policy, complete large bounded solve, real physical reduction, exact small comparison with derived incentive bound, immutable full lift coverage and equal twin values, blocker safety, independent diagnostic bounds, truthful finite-iteration/reduced versus exact metadata, all prior plus additive tests, fresh audits/commits, and unchanged historical tag. S5 design cannot begin until this is verified. Package exports, strict serialization, executable examples and S4 documentation are owned by I4. Full Phase 4 deliverables and phase4-complete tag remain mission-wide S1–S7 gates; this S4 checkpoint cannot authorize them.

Bounds are preregistered, not selected after observing reduced results. Node equality is accepted at 161, large exact failure uses the same public game and cap, and latent signature/belief/world limits are distinct from physical node counts. The source-backed finite-game scope excludes multiplayer integration, unrestricted deck claims, warm starts, generic wrappers, future S5 work, and universal error/runtime claims. No scope or release blocker found.

## Executed verification receipts

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest --collect-only -q -p no:cacheprovider
```
Final output: `817 tests collected in 0.39s` (exit 0). The collection listing is omitted.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_bounded_tree.py tests/test_allstreet_state.py tests/test_evaluator.py tests/test_multistreet.py
```
Final output: `99 passed in 39.70s` (exit 0).

No full 817-test regression was executed by this auditor. The manifest's 817-passed receipt remains a parent receipt, not an independently reproduced full-suite result. No S4 production solve, RED suite, serialization or lifted-policy test was claimed executed.

Exact fixture probe command:
```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'
import os,sys
sys.path.insert(0,os.path.abspath("src"))
os.chdir("/tmp")
from itertools import combinations
from collections import Counter
from dataclasses import replace,asdict
from fractions import Fraction
from poker_solver.cards import parse_cards
from poker_solver.equity import WeightedCombo
from poker_solver.evaluator import evaluate_seven
from poker_solver.multistreet import MultiStreetConfig,create_root
from poker_solver.bounded_tree import validate_bounded_tree
from poker_solver.model import CHANCE,TERMINAL
from poker_solver.cfr import CFRSolver
from poker_solver.api import complete_strategy
from poker_solver.best_response import nash_conv
pc=lambda s:parse_cards(s.split())
comb=lambda s:WeightedCombo(pc(s))
board=pc("Ah Kh Qh")
runs=(pc("Jh 9h"),pc("Jh 8h"))
cfg=MultiStreetConfig("multistreet-v1","flop",board,2,1,(comb("2c 3c"),comb("2d 3d")),(comb("2s 3s"),comb("Th 4s")),runs,"no-limit",(1,),True)
def signatures(c):
    hs=[c.player0_combos,c.player1_combos]
    rows=[]
    codes=Counter()
    for p in (0,1):
        out=[]
        for h in hs[p]:
            row=[]
            for g in hs[1-p]:
                if set(h.cards)&set(g.cards):
                    row.append((0,()))
                    continue
                cells=[]
                for r in c.allowed_runouts:
                    if (set(h.cards)|set(g.cards))&set(r): cells.append(-2)
                    else:
                        a=evaluate_seven(c.starting_board+r+h.cards)
                        b=evaluate_seven(c.starting_board+r+g.cards)
                        cells.append((a>b)-(a<b))
                row.append((1,tuple(cells)))
                if p==0: codes.update(cells)
            out.append(tuple(row))
        rows.append(out)
    sizes=[sorted(Counter(rs).values()) for rs in rows]
    return rows,sizes,codes
root=create_root(cfg)
print("cwd",os.getcwd())
print("small_stats",asdict(validate_bounded_tree(root,max_nodes=321,max_depth=12)))
rows,sizes,codes=signatures(cfg)
print("small_buckets",sizes,"p0_runout_codes",dict(codes))
print("small_deal_mass",[p for a,p in root.chance_outcomes()])
streets=Counter(); actions=set(); terminal_values=set(); prefixes=set()
def visit(s):
    if s.current_player()==TERMINAL:
        terminal_values.add(s.returns());return
    if s.current_player()!=CHANCE:
        streets[s.street]+=1
        actions.update(a.kind for a in s.legal_actions())
    elif s.private_deal is not None:
        prefixes.add((s.board[3:],tuple(p for a,p in s.chance_outcomes())))
    for a in s.legal_actions(): visit(s.child(a))
visit(root)
print("small_decisions_by_street",dict(streets),"actions",sorted(actions),"terminal_values",sorted(terminal_values))
print("public_chance",sorted(prefixes))
a=tuple(WeightedCombo(h) for h in combinations(pc("2c 3c 4c 5c 6c 7c 2d 3d 4d 5d 6d 7d"),2))
b=tuple(WeightedCombo(h) for h in combinations(pc("2s 3s 4s 5s 6s 7s 2h 3h 4h 5h 6h Th"),2))
large=replace(cfg,player0_combos=a,player1_combos=b)
lr,ls,lc=signatures(large)
worlds=sum(not(set(h.cards)&set(g.cards)) for h in a for g in b)
assert all(not(set(h.cards)&set(board+r)) for hs in (a,b) for h in hs for r in runs)
print("large_hands_worlds",len(a),len(b),worlds,"buckets",ls,"p0_runout_codes",dict(lc))
single=replace(cfg,player0_combos=(a[0],),player1_combos=(b[0],))
ss=validate_bounded_tree(create_root(single),max_nodes=81,max_depth=12)
print("single_world_stats",asdict(ss))
# Every class combination has same branch shape, including Th winning class.
for sig in sorted(set(lr[1])):
    h=b[lr[1].index(sig)]
    st=validate_bounded_tree(create_root(replace(single,player1_combos=(h,))),max_nodes=81,max_depth=12)
    assert st==ss
print("analytic_exact_reduced",1+worlds*(ss.node_count-1),1+2*(ss.node_count-1))
print("reduced_terminal_chance_decisions",2*ss.terminal_count,1+2*(ss.chance_count-1),2*ss.decision_count)
print("signature_slots",2*len(a)*len(b)*len(runs),"belief_entries",worlds*len({(),(runs[0][0],),*runs}))
print("pair_masses",sorted(str(Fraction(n,66)) for n in ls[1]))
try: validate_bounded_tree(create_root(large),max_nodes=10000,max_depth=32)
except ValueError as e: print("large_bounded_preflight",type(e).__name__,str(e))
else: raise AssertionError("expected cap failure")
# Concrete design companion witnesses, tested against source.
opp=replace(cfg,player0_combos=(comb("2c 3c"),comb("2d 3d")),player1_combos=(comb("2c 4s"),comb("2s 4d")))
run=replace(cfg,player0_combos=(comb("9h 3c"),comb("2d 3d")),player1_combos=(comb("2s 3s"),))
for name,c in (("opponent_blocker",opp),("runout_blocker",run)):
    rs,sz,co=signatures(c)
    rt=create_root(c)
    print(name,"deals",len(rt.chance_outcomes()),"buckets",sz,"codes",dict(co),"nodes",validate_bounded_tree(rt,max_nodes=321,max_depth=12).node_count)
print("starting_exact_1000",flush=True)
profile=complete_strategy(root,CFRSolver(root).train(1000))
print("small_exact_1000",nash_conv(root,profile))
PY
```

Output (exit 0):
```
cwd /tmp
small_stats {'node_count': 321, 'max_depth_reached': 12, 'terminal_count': 136, 'chance_count': 57, 'decision_count': 128}
small_buckets [[2], [1, 1]] p0_runout_codes {0: 4, -1: 4}
small_deal_mass [0.25, 0.25, 0.25, 0.25]
small_decisions_by_street {'flop': 32, 'turn': 32, 'river': 64} actions ['CALL', 'CHECK', 'FOLD', 'RAISE'] terminal_values [(-2.0, 2.0), (-1.0, 1.0), (0.0, 0.0), (1.0, -1.0)]
public_chance [((), (1.0,)), ((38,), (0.5, 0.5))]
large_hands_worlds 66 66 4356 buckets [[66], [11, 55]] p0_runout_codes {0: 7260, -1: 1452}
single_world_stats {'node_count': 81, 'max_depth_reached': 12, 'terminal_count': 34, 'chance_count': 15, 'decision_count': 32}
analytic_exact_reduced 348481 161
reduced_terminal_chance_decisions 68 29 64
signature_slots 17424 belief_entries 17424
pair_masses ['1/6', '5/6']
large_bounded_preflight ValueError max_nodes 10000 exceeded
opponent_blocker deals 3 buckets [[1, 1], [1, 1]] codes {0: 6} nodes 241
runout_blocker deals 2 buckets [[1, 1], [1]] codes {-2: 1, 1: 1, 0: 2} nodes 138
starting_exact_1000
small_exact_1000 NashConvResult(values=(-0.9993335546875001, 0.9993335546875001), best_response_values=(-0.9993333333333333, 1.0000625), incentives=(2.2135416677393494e-07, 0.0007289453125000067), nash_conv=0.0007291666666667806)
```

Exact API/control and equal-equity blocker probe command:
```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'
import os,sys
sys.path.insert(0,os.path.abspath("src"));os.chdir("/tmp")
from poker_solver.cards import parse_cards
from poker_solver.api_v4 import dispatch_v4
from poker_solver.evaluator import evaluate_seven
pc=lambda s:list(parse_cards(s.split()))
payload=dict(version="allstreet-postflop-v1",starting_board=pc("Ah Kh Qh"),initial_dead_pot=2,effective_stack=1,player0_combos=[dict(cards=pc(s),weight=1.0) for s in ("2c 3c","2d 3d")],player1_combos=[dict(cards=pc(s),weight=1.0) for s in ("2s 3s","Th 4s")],allowed_runouts=[pc("Jh 9h"),pc("Jh 8h")],betting_mode="no-limit",wager_targets=[1],algorithm="vanilla-cfr",iterations=1,seed=None,max_nodes=10000,max_depth=32)
r=dispatch_v4(dict(version=4,operation="solve-allstreet-postflop",payload=payload))
print("base_positive_operation",r["operation"])
payload["abstraction"]=dict(version="exact-signature-belief-v1",max_abstract_nodes=10000,max_depth=32,max_worlds=5000,max_signature_cells=20000,max_belief_entries=20000,max_fraction_bits=4096)
try: dispatch_v4(dict(version=4,operation="solve-allstreet-abstracted",payload=payload))
except ValueError as e: print("valid_future_operation",type(e).__name__,str(e))
else: raise AssertionError("S4 unexpectedly present")
for hs in ("9h 3c","2d 3d"):
    codes=[]
    for rs in ("Jh 9h","Jh 8h"):
        h=pc(hs);g=pc("Th 4s");run=pc(rs)
        if set(h+g)&set(run):codes.append(-2)
        else:
            x=evaluate_seven(pc("Ah Kh Qh")+run+h)
            y=evaluate_seven(pc("Ah Kh Qh")+run+g)
            codes.append((x>y)-(x<y))
    print("equal_equity_runout_blocker",hs,codes,"legal_equity",0.0)
PY
```

Output (exit 0):
```
base_positive_operation solve-allstreet-postflop
valid_future_operation ValueError operation must be one of ['solve-allstreet-postflop', 'solve-nplayer-postflop', 'solve-nplayer-preflop']
equal_equity_runout_blocker 9h 3c [-2, -1] legal_equity 0.0
equal_equity_runout_blocker 2d 3d [-1, -1] legal_equity 0.0
```

Finalization contract: after this final report write, compute its SHA-256, obtain live UTC, revalidate the literal manifest rows and candidate hash, accepted HEAD, annotated tag identity, protected-source diff and Git status, then write the C4D5-CODEX heartbeat last. No writes follow that heartbeat.

