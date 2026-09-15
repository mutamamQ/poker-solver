# Canonical single-street equilibrium values

## Finding

There is no safe, widely published table of river-only Hold'em equilibrium EVs that can be transplanted into a test suite. An EV depends on the exact board, combo-weighted ranges, initial pot, remaining stacks, acting order, legal bet/raise tree, rake, and utility baseline. Solver screenshots without all of these inputs are not fixtures.

The portable known-answer benchmark is Kuhn poker. With a three-card deck J<Q<K, one private card each, one-chip ante each, a one-chip bet, and the standard check/bet/fold/call tree, the first player's Nash value is exactly -1/18 chip per deal. Kuhn validates the same imperfect-information/CFR machinery, but it is not Texas Hold'em.

For Hold'em, this project will create a fully specified river spot and validate it two independent ways: (1) tabular CFR average-strategy exploitability and (2) exhaustive normal-form or sequence-form solution on the same finite tree. The generated oracle value—not an undocumented commercial-solver number—is the known answer.

## Required fixture specification

Every stored spot must include: ordered board cards; explicit two-card combos and nonnegative weights for both players; removal of colliding combos; initial pot and each player's remaining stack/contribution; player to act; exact legal raise-to amounts at every history; terminal utility relative to the start of the spot; no rake; chance semantics; and value/exploitability normalization.

Acceptance tolerances should separate an exact oracle (1e-10 for enumerated payoffs, 1e-8 for LP value) from iterative CFR (a measured NashConv threshold, initially 1e-3 chip on toy games). CFR iteration count alone is not proof.

## Sources

- Kuhn, “Simplified Two-Person Poker” (1950): https://www.rand.org/content/dam/rand/pubs/reports/2006/R1654.pdf
- Zinkevich et al., original CFR paper and poker experiments: https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- Bowling et al., “Heads-up Limit Hold'em Poker is Solved”: https://www.science.org/doi/10.1126/science.1259433
- Koller, Megiddo & von Stengel, sequence-form equilibrium computation: https://doi.org/10.1006/game.1996.0051
- OpenSpiel reference games and algorithms: https://github.com/google-deepmind/open_spiel

## Warning

The Bowling/Cepheus value bound applies to its complete heads-up limit game and conventions. It is evidence that CFR-family methods are standard, not an EV fixture for this solver's river tree.
