# C4R2A2-CODEX physical-engine DESIGN audit

Final decision: **ACCEPT**. All assigned design scopes PASS. No blocking finding reproduced. This accepts specification correctness and feasibility, not an implemented reduced engine or a completed S4 release.

Auditor: C4R2A2-CODEX, fresh alternate-provider non-author replacement. Repository: /home/genomix-node/poker-solver. Only this report and the assigned flat heartbeat are written. Missing reduced implementation is expected at this DESIGN checkpoint. No production, test, architecture, manifest, progress, state, or Git-history edits were made.

## Authentication and source authority — PASS

Executed from repository root:

```sh
sha256sum ARCHITECTURE_PHASE4_S4.md research/phase4/s4-design-audit-r2/CANDIDATE_MANIFEST.md
```
```text
37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2  ARCHITECTURE_PHASE4_S4.md
f98a7b9c3bc8b33f8761716e0c23a318aeb2b5c738546845f560875cbc004bed  research/phase4/s4-design-audit-r2/CANDIDATE_MANIFEST.md
```

Both match the supplied immutable inputs. Additional manifest hashes were reproduced:
PHASE4_MISSION.md = 5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61;
research/phase4/s4-design/02-engine-integration-codex.md = 79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d.

Executed:
```sh
git rev-parse HEAD phase3-398-green 'phase3-398-green^{}'
```
```text
149780bf37e3e3a824e03e6d2c1df3cd99b12cd6
feba8222a0b614b0c64eca59402403ce733195ea
5809ecca28ae6d0588ea07709c90beac3072c167
```

Source hashes from `sha256sum src/poker_solver/{multistreet,bounded_tree,evaluator,equity}.py`:
```text
bdacc32688361f0cec48205b722aca8843c24dca4f58dd11479d5aa85fdfa490  src/poker_solver/multistreet.py
c221d77dffed3866b497acdef2ea039e93cd5b10e9ce387f1b6f0537df9b91f9  src/poker_solver/bounded_tree.py
4f51235f92f22ad180989ede683a63fc31270be4a717249cf517e8ae25b5111e  src/poker_solver/evaluator.py
fd419d547dff9209f76bcf32a0b4e72233f3b875ef97857700938daad87ec537  src/poker_solver/equity.py
```

`git diff -- src/poker_solver/multistreet.py src/poker_solver/bounded_tree.py src/poker_solver/evaluator.py src/poker_solver/equity.py` returned empty output. Existing unrelated workspace changes were observed and left untouched.

Actual inspected symbols: MultiStreetConfig, MultiStreetState.legal_actions, chance_outcomes, child, information_state_key, returns, and **create_root** (multistreet.py:485); validate_bounded_tree (bounded_tree.py:20); evaluate_seven (evaluator.py:65); WeightedCombo (equity.py:31). There is no invented create_multistreet_root call in this audit. allstreet.py:177 create_allstreet_root translates to MultiStreetConfig with starting_street="flop" and river_betting=True, then calls create_root.

## Physical quotient and no hidden exact subtree — PASS

Architecture §§3–5 specify complete labelled signatures, one public history tree per nonempty bucket pair, and literal history occurrence counting. Equal rows identify compatibility, blocked runouts, and each terminal comparison against every labelled opponent hand; equal columns give the converse. For a nonempty bucket-pair cell, changing either member preserves the cell, hence all cross-pairs are compatible and have the same complete runout code vector. Legal betting transitions depend on the public ledger, not private cards. This establishes the required rectangular behavioural-twin cells; scalar equity alone would not.

A one-world exact root includes a single DEAL root and an 80-node continuation. Replacing the four small exact deals by two abstract deals therefore yields 1+2*80=161, not 162. The same reasoning applies to the large fixture because every member has the same runout support and public action topology. Worlds remain bounded latent data; they are not physical tree branches.

The required ReducedPlan.nodes is a tree, not a DAG whose unique-node count disguises history multiplicity. ReducedState.child must do O(1) validated lookup; bounded member source-state checks are permitted only during preprocessing, with no retained exact subtrees and zero exact-world GameState construction during CFR/completion/reduced best response. Optional lift/exact diagnostics have explicit separate traversal bounds. §§10 I2/I3 require instrumentation. These are concrete, feasible implementation obligations, not claims tested against nonexistent reduced code.

The source validator increments for each occurrence and removes the identity from its active path at bounded_tree.py:238. It does not provide a unique-state-node compression metric. Root and public chance nodes are counted. Its infoset action comparison uses a frozenset (line 220), so the architecture correctly requires additional ordered-action and recall checks; calling the existing validator alone would be insufficient.

## Root/chance mass and Bayesian posteriors — PASS

Architecture §4.2 correctly normalizes compatible active world products once: r_w=f_h*f_g, Z=sum r_w, then sums normalized mass by bucket pair and conditions within the pair. No runout-count weighting is inserted at root. Source chance_outcomes (multistreet.py:158) likewise forms compatible product-weight deals, then counts legal full runout suffixes for the current revealed prefix. Architecture adds exact Fraction conversion before multiplication and rejects positive deals with no legal runout instead of silently dropping them.

At a prefix, the correct denominator is each world's own number of surviving full runouts. P(c)=sum q(w)p_w(c|s) and q'(w)=q(w)p_w(c|s)/P(c) conserve mass and perform Bayes conditioning. The probe checks a nonuniform two-world example with unequal denominators: q=(1/3,2/3), p=(1/2,1/4), yielding P=1/3 and posterior=(1/2,1/2). Pooling raw counts would give the wrong observable probability.

For certified cells the kernels agree, so observation leaves within-pair member proportions unchanged. Bucket strategies likewise apply identical likelihood to twin members at a betting action, justifying belief sharing by (pair,prefix) across betting histories. Public turn reveal occurs before turn betting; river is chosen only at its later public chance node. The source probe confirms deterministic Jh, then a decision actor, then equiprobable 8h/9h after betting.

Small exact DEAL probabilities are four quarters; abstract pair masses are two halves. Large rational pair masses are 5/6 and 1/6. These rational aggregates are audit calculations, not outputs of a reduced compiler.

## Terminal settlement, refunds, ties — PASS

Source returns (multistreet.py:458–482) awards the whole contested amount on a fold or outright win, and splits a tie as (C//2, C-C//2). Thus P1 receives the odd chip. Subtracting each player's total_contributed and half the initial dead pot reproduces source utility. Architecture §4.4 preserves integer awards before rational aggregation; it does not replace an odd tie with half-pot equity or average rounded utility.

The ledger condition C=initial_dead_pot+sum(total_contributed) proves zero sum when both awards sum to C. Independent exact P1 calculation catches settlement errors before returning the complementary float. The specified chip/Fraction limits and finite checks bound conversion.

Source child short CALL handling (lines 317–328) refunds excess by reducing the larger commitment and its total contribution and restoring remaining chips. The probe directly exercises that branch with a synthetic ledger-consistent unequal-stack snapshot, obtaining commitments (1,1), remaining (2,0), contributions (1,1). This is a branch probe, not a claim that the synthetic state is reachable from the equal-effective-stack fixture. An executed odd-dead-pot checkdown returns (-0.5,0.5). Differential traversals also cover reachable folds and all-in chance continuations.

## Transition compatibility — PASS

Architecture §4.3 delegates projected public transitions to actual MultiStreetState.child and requires agreement in actor, ordered actions, ledger, history, and chance support, failing on disagreement. PublicFrame carries the required fields, including total contributions and raise increment. Own fixed bucket plus complete public observation history preserves recall; excluding DEAL/ABSTRACT_DEAL, opponent bucket and world identity prevents hidden information leakage. The source exact information key already excludes DEAL actions (line 446); abstract history projection must similarly omit root abstract-deal identity as explicitly required by §3.3.

Executed twin differential checks compare both P0 hands against each small-fixture P1 hand, in no-limit and pot-limit modes and with river betting enabled/disabled. They compare full public fields, ordered actions, chance probabilities, ledger conservation, terminal utilities and zero sum at 528 source-state occurrences. This supports the source projection premise, while broad reduced differential and noninterference tests remain future I2 obligations. allstreet translation is explicitly pinned to the existing facade.

## Separate resource caps — PASS

§§4.1/5 specify distinct positive non-bool integer limits, inclusive node allocation boundaries, and post-freeze validator reconciliation:

| Resource | Required accounting / limit |
|---|---|
| Physical nodes | Reserve before allocation; max_abstract_nodes, default 10,000 |
| Latent worlds | Compatible active pairs; max_worlds, default 5,000 |
| Signature scalar slots | 2*H0*H1*max(1,runouts), including blocked slots; max_signature_cells, default 20,000 |
| Belief members | Sum of stored MemberWeight entries across retained beliefs; max_belief_entries, default 20,000 |
| Fraction growth | Numerator/denominator bit cap, default 4,096 |
| Depth | Caller cap, default 32; reject configured cap above 128 |

The large fixture fits each independent default. Belief sharing prevents copying member arrays into every betting node but does not reduce four stored per-world prefix memberships to one. The signature limit is an explicitly defined scalar charge, not a promise of Python object-byte accounting. Physical count alone makes no runtime or memory-ratio claim. Equality at 161 nodes is legal; 160 must fail. These reduced allocation boundaries and Fraction failures are specified future tests, not executed implementation results here.

## Fixture validity and evidence classification — PASS

Executed exact-source full validations: small (321 nodes,136 terminal,57 chance,128 decision,depth12); one world (81,34,15,32,depth12).

Executed finite input/signature enumeration: 66 hands each, 4,356 compatible worlds; complete P0 row signatures form one 66-hand class; P1 column signatures form 55 no-Th and 11 Th. For every opposing P0 hand, evaluator outcomes on BOTH runouts are (0,0) for no-Th and (+1,+1) for Th, from P1's perspective. This is evaluator-backed identity checking, not just counting combinations containing Th.

Analytic full large exact nodes: 1+4,356*80=348,481. Analytic nonexistent reduced nodes: 1+2*80=161, with terminal/chance/decision counts 68/29/64 and depth12. Neither number is presented as an executed full large/reduced traversal.

Signature scalar charge: 2*66*66*2=17,424. Belief member entries: each compatible world occurs in the four retained revealed-prefix beliefs (), (Jh,), (Jh,9h), (Jh,8h), giving 4*4,356=17,424. The probe enumerates legal prefix membership explicitly. It does not report 4,356 as the belief-entry total or count duplicate betting-history references as distinct stored beliefs.

Executed large exact preflight: ValueError: max_nodes 10000 exceeded. No training was invoked. The failed bounded traversal is not a completed 348,481-node traversal.

## Exact read-only probe command and output receipt

Command executed in /home/genomix-node/poker-solver, stdin-only, with bytecode and UV cache disabled; no probe script persisted:

```sh
PYTHONDONTWRITEBYTECODE=1 UV_NO_CACHE=1 uv run --no-sync python -B - <<'PY'
from collections import Counter
from dataclasses import replace
from fractions import Fraction as F
from itertools import combinations
from poker_solver.cards import parse_cards, parse_card
from poker_solver.equity import WeightedCombo
from poker_solver.evaluator import evaluate_seven
from poker_solver.multistreet import MultiStreetConfig, create_root
from poker_solver.bounded_tree import validate_bounded_tree
from poker_solver.model import CHANCE, TERMINAL, Action

def combos(text):
    return tuple(WeightedCombo(parse_cards(h.split())) for h in text)
def config(p0, p1):
    return MultiStreetConfig("multistreet-v1", "flop", parse_cards("Ah Kh Qh".split()),
        2, 1, p0, p1, (parse_cards("Jh 9h".split()), parse_cards("Jh 8h".split())),
        "no-limit", (1,), True)
small = config(combos(["2c 3c", "2d 3d"]), combos(["2s 3s", "Th 4s"]))
def stats(c):
    s = validate_bounded_tree(create_root(c), max_nodes=10000, max_depth=32)
    return (s.node_count, s.terminal_count, s.chance_count, s.decision_count, s.max_depth_reached)
print("small exact executed nodes/terminal/chance/decision/depth:", stats(small))
assert stats(small) == (321,136,57,128,12)
one = replace(small, player0_combos=small.player0_combos[:1], player1_combos=small.player1_combos[:1])
one_stats = stats(one)
print("one-world exact executed nodes/terminal/chance/decision/depth:", one_stats)
assert one_stats == (81,34,15,32,12)
p0 = tuple(WeightedCombo(h) for h in combinations(parse_cards("2c 3c 4c 5c 6c 7c 2d 3d 4d 5d 6d 7d".split()),2))
p1 = tuple(WeightedCombo(h) for h in combinations(parse_cards("2s 3s 4s 5s 6s 7s 2h 3h 4h 5h 6h Th".split()),2))
large = config(p0,p1)
worlds = [(h.cards,g.cards) for h in p0 for g in p1 if not set(h.cards)&set(g.cards)]
assert len(worlds)==4356
print("enumerated P0 hands/P1 hands/compatible worlds:", len(p0),len(p1),len(worlds))
def cell(h,g):
    if set(h)&set(g): return (0,())
    codes=[]
    for r in large.allowed_runouts:
        if set(r)&set(h+g): codes.append(-2)
        else:
            a=evaluate_seven(h+large.starting_board+r)
            b=evaluate_seven(g+large.starting_board+r)
            codes.append((a>b)-(a<b))
    return (1,tuple(codes))
rows=Counter(tuple(cell(h.cards,g.cards) for g in p1) for h in p0)
cols=Counter(tuple(cell(g.cards,h.cards) for h in p0) for g in p1)
print("evaluator-backed complete signature bucket sizes P0/P1:", sorted(rows.values()), sorted(cols.values()))
assert sorted(rows.values())==[66] and sorted(cols.values())==[11,55]
th=parse_card("Th")
for label, present in [("no-Th",False),("Th",True)]:
    members=[g for g in p1 if (th in g.cards)==present]
    outcomes={cell(g.cards,h.cards)[1] for g in members for h in p0}
    print("P1",label,"members/outcomes over (Jh,9h),(Jh,8h):",len(members),sorted(outcomes))
    assert outcomes==({(1,1)} if present else {(0,0)})
prefixes=((),parse_cards(["Jh"]),parse_cards(["Jh","9h"]),parse_cards(["Jh","8h"]))
entries=sum(1 for h,g in worlds for s in prefixes
    if any(r[:len(s)]==s and not set(r)&set(h+g) for r in large.allowed_runouts))
slots=2*len(p0)*len(p1)*len(large.allowed_runouts)
print("analytic physical exact/quotient:",1+len(worlds)*(one_stats[0]-1),1+2*(one_stats[0]-1))
print("analytic quotient terminal/chance/decision/depth:",2*34,1+2*(15-1),2*32,12)
print("charged signature scalar slots:",slots)
print("enumerated retained-prefix belief member entries (four per world):",entries)
assert slots==entries==17424
print("exact rational large bucket-pair masses no-Th/Th:",F(66*55,len(worlds)),F(66*11,len(worlds)))
root=create_root(small)
print("small source root chance masses:",[p for _,p in root.chance_outcomes()])
s=root.child(root.legal_actions()[0])
s=s.child(Action("CHECK")).child(Action("CHECK"))
print("source turn law:",s.chance_outcomes())
s=s.child(Action("RUNOUT",parse_card("Jh")))
assert s.current_player()==0
s=s.child(Action("CHECK")).child(Action("CHECK"))
print("source river law after Jh betting:",s.chance_outcomes())
q=(F(1,3),F(2,3)); pc=(F(1,2),F(1,4))
mass=sum(a*b for a,b in zip(q,pc))
posterior=tuple(a*b/mass for a,b in zip(q,pc))
print("generalized Bayesian arithmetic q=(1/3,2/3), kernels=(1/2,1/4):",mass,posterior)
assert mass==F(1,3) and posterior==(F(1,2),F(1,2))
def public(s):
    return (s.board,s.street,s.acting_player,s.pot,s.committed,s.total_contributed,
        s.remaining,s.last_raise_increment,tuple(a for a in s.history if a.kind!="DEAL"),s.terminal_reason)
def compare(a,b):
    assert public(a)==public(b) and a.legal_actions()==b.legal_actions()
    assert a.chance_outcomes()==b.chance_outcomes()
    assert a.pot+sum(a.committed)==a.config.initial_dead_pot+sum(a.total_contributed)
    if a.current_player()==TERMINAL:
        assert a.returns()==b.returns() and sum(a.returns())==0
        return 1
    return 1+sum(compare(a.child(x),b.child(x)) for x in a.legal_actions())
checked=0
for mode in ("no-limit","pot-limit"):
    for river in (False,True):
        c=replace(small,betting_mode=mode,river_betting=river)
        rt=create_root(c)
        for i in (0,1):
            checked+=compare(rt.child(Action("DEAL",i)),rt.child(Action("DEAL",i+2)))
print("executed twin source transition/terminal comparisons (two betting modes, both river flags):",checked)
odd=replace(one,initial_dead_pot=3)
s=create_root(odd).child(Action("DEAL",0))
while s.current_player()!=TERMINAL:
    s=s.child(s.legal_actions()[0])
print("source odd-pot checkdown tie returns:",s.returns())
assert s.returns()==(-0.5,0.5)
# Synthetic valid-ledger snapshot exercises source short-call refund branch.
s=create_root(one).child(Action("DEAL",0))
s=replace(s,acting_player=1,pot=2,committed=(3,0),total_contributed=(3,0),remaining=(0,1))
s=s.child(Action("CALL",1))
print("source short-call refund committed/remaining/contributed:",s.committed,s.remaining,s.total_contributed)
assert (s.committed,s.remaining,s.total_contributed)==((1,1),(2,0),(1,1))
try:
    validate_bounded_tree(create_root(large),max_nodes=10000,max_depth=32)
except ValueError as e:
    print("large exact executed preflight failure:",type(e).__name__+": "+str(e))
    assert str(e)=="max_nodes 10000 exceeded"
else:
    raise AssertionError("large exact preflight unexpectedly passed")
print("ALL PROBE ASSERTIONS PASSED")
PY
```

Combined stdout in emission order (initial execution plus session completion); process exit code 0:
```text
small exact executed nodes/terminal/chance/decision/depth: (321, 136, 57, 128, 12)
one-world exact executed nodes/terminal/chance/decision/depth: (81, 34, 15, 32, 12)
enumerated P0 hands/P1 hands/compatible worlds: 66 66 4356
evaluator-backed complete signature bucket sizes P0/P1: [66] [11, 55]
P1 no-Th members/outcomes over (Jh,9h),(Jh,8h): 55 [(0, 0)]
P1 Th members/outcomes over (Jh,9h),(Jh,8h): 11 [(1, 1)]
analytic physical exact/quotient: 348481 161
analytic quotient terminal/chance/decision/depth: 68 29 64 12
charged signature scalar slots: 17424
enumerated retained-prefix belief member entries (four per world): 17424
exact rational large bucket-pair masses no-Th/Th: 5/6 1/6
small source root chance masses: [0.25, 0.25, 0.25, 0.25]
source turn law: ((Action(kind='RUNOUT', amount=38), 1.0),)
source river law after Jh betting: ((Action(kind='RUNOUT', amount=26), 0.5), (Action(kind='RUNOUT', amount=30), 0.5))
generalized Bayesian arithmetic q=(1/3,2/3), kernels=(1/2,1/4): 1/3 (Fraction(1, 2), Fraction(1, 2))
executed twin source transition/terminal comparisons (two betting modes, both river flags): 528
source odd-pot checkdown tie returns: (-0.5, 0.5)
source short-call refund committed/remaining/contributed: (1, 1) (2, 0) (1, 1)
large exact executed preflight failure: ValueError: max_nodes 10000 exceeded
ALL PROBE ASSERTIONS PASSED
```

## Findings and disposition

No blocking specification defect found in the assigned physical-engine scope. The report's generalized Bayesian calculation and analytic reduction arithmetic are audit checks; only the stated exact-source probes execute production behavior. No reduced compiler, solver, serialization, runtime guarantee, or future regression gate is claimed to have passed. Existing full-regression figures in the manifest were not independently rerun for this design audit.

Final: **ACCEPT / COMPLETE_PASS**, blocked=false. Preserve I2/I3 instrumentation, ordered-action checks, settlement differentials, and independent resource-cap tests as written; missing future S4 implementation is not a rejection reason.

