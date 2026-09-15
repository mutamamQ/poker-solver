# Phase 2 feature inventory

## Verified categories

Equity engines and equilibrium solvers are different products. PokerStove describes itself as poker evaluation/enumeration software and exposes an evaluation library/tool; it does not claim to solve betting strategies. PH Evaluator is another independent evaluator candidate. Neither is an exploitability oracle for a betting strategy.

OpenSpiel is a general game framework. Its published algorithm inventory includes sequence-form LP, CFR, best response/exploitability, and external- and outcome-sampling MCCFR. Its implementations are useful independent references for tiny games, but that does not provide a production Hold'em abstraction or weighted-range spot API automatically.

Commercial pages provide product evidence, not reproducible numerical fixtures. GTOBase advertises precomputed viewers/trainers and Hold'em libraries. GTO+'s public home page confirms the product exists but did not expose enough machine-readable detail in this research pass to substantiate claims about algorithms, player counts, JSON export, or exact accuracy. “GTD” could not be identified as a distinct industry solver and is treated as unresolved rather than silently mapped to GTOBase.

Open projects such as PyPokerEngine are gameplay/simulation frameworks unless they ship equilibrium and best-response algorithms. Repository names such as pycfr/OpenCFR must be evaluated at a pinned revision before becoming references; popularity is not correctness evidence.

## Concrete target inventory for this project

- immutable finite heads-up flop/turn/river spot trees;
- discrete check/bet/call/fold actions, configured pot fractions and all-in, with pot-limit caps;
- exact combo-weighted ranges and blocker conditioning;
- deterministic vanilla CFR reference and seeded external-sampling MCCFR fast path;
- exact expected values and infoset-consistent best response/NashConv on bounded games;
- stable strategy/EV/exploitability JSON API and CLI;
- deterministic output and measured benchmark gates;
- explicit heads-up scope: no multiway, side pots, rake, ICM, or continuous action space.

## Performance techniques and status

Sampling lowers work per iteration but adds variance. Reach values should be passed incrementally. Hand ranks and immutable transitions may be cached. Suit isomorphism and card/action abstraction are later performance techniques, not correctness-preserving defaults unless equivalence is proved. Full unrestricted Hold'em remains out of scope because published game-size work shows the tree is enormous.

## Sources

- PokerStove repository: https://github.com/andrewprock/pokerstove
- PH Evaluator: https://github.com/HenryRLee/PokerHandEvaluator
- OpenSpiel algorithms: https://openspiel.readthedocs.io/en/latest/algorithms.html
- OpenSpiel repository: https://github.com/google-deepmind/open_spiel
- GTO+ official site: https://www.gtoplus.com/
- GTOBase official site: https://gtobase.com/
- PyPokerEngine: https://github.com/ishikota/PyPokerEngine
- No-limit game-size study: https://arxiv.org/abs/1302.7008

## Parent disposition

Claims not directly supported by the pages above were removed. Commercial outputs are comparison aids only when a complete input tree, utility convention, export, and tolerance are available.