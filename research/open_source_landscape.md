# Open-source reference landscape

| Project | URL | License (verify in exact checkout) | Relevant use | Risk |
|---|---|---|---|---|
| OpenSpiel | https://github.com/google-deepmind/open_spiel | Apache-2.0 | Game API, Kuhn/Leduc, CFR and exploitability | Large compiled dependency; use as external reference |
| PokerStove | https://github.com/andrewprock/pokerstove | repo license must be checked | Exhaustive equity/evaluation | Old C++ build and maintenance state |
| PH Evaluator | https://github.com/HenryRLee/PokerHandEvaluator | Apache-2.0 in current repo | Independent fast evaluator and tests | Native tables/build |
| Deuces | https://github.com/worldveil/deuces | MIT in current repo | Auditable Python 5/6/7 evaluation | Old; 7-card is 21 five-card evaluations |
| Treys | https://github.com/ihendley/treys | MIT in current repo | Python 3 fixture generation | Port of Deuces, not independent from it |
| PokerKit | https://github.com/uoftcprg/pokerkit | verify current LICENSE | Python poker state/evaluation | Scope is broad; API/version drift |
| TexasSolver | https://github.com/bupticybee/TexasSolver | GPL-3.0 | Practical postflop tree concepts | Do not copy/link into a permissive project without accepting GPL obligations |
| PokerRL | https://github.com/TinkeringCode/PokerRL | verify current LICENSE | Leduc/Hold'em RL environments | Heavy neural/distributed stack, not a simple oracle |
| PyPokerEngine | https://github.com/ishikota/PyPokerEngine | MIT (verify) | Hold'em transition examples | Gameplay engine, not equilibrium proof |
| ACPC server | https://github.com/ethansbrown/acpc | verify exact files | Standard game definitions/protocol | C code and competition conventions |

Pluribus is a published system, not an open-source solver repository, so it is deliberately excluded from the project table. Commercial solver outputs are not test oracles without complete input files and licensing permission.

## Cross-check plan

- Algorithm/game value: project CFR versus OpenSpiel's Kuhn implementation/results. Installing OpenSpiel is optional because the exact -1/18 value and a separately coded normal-form/best-response oracle are checked in tests.
- Hand evaluation: project evaluator versus PH Evaluator where available. Treys can generate fixtures but is not independent of Deuces.
- Equity: exact integer win/tie/loss counts, not rounded GUI percentages.
- Rules: project limited river tree versus explicit ACPC-style state definitions; no code is copied from GPL projects.

Correctness evidence is strongest when two implementations with different algorithms/data representations agree exhaustively. Stars, benchmark speed, or community anecdotes are not correctness evidence.

## Verified observations

The OpenSpiel repository identifies an Apache-2.0 license and includes game algorithms; the PH Evaluator repository exposes build/tests and a perfect-hash evaluator; Deuces states it evaluates 5/6/7 cards and runs pytest; Treys states it is a Python 3 port of Deuces; PokerStove exposes `peval` and `ps-eval`. These repository pages were fetched during Wave 0. License details must still be read from the pinned commit before incorporating code. This project uses independent original code and external expected values only.
