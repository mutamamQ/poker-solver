# C3I2-1 solve RED recovery receipt

Status: COMPLETE_RED; blocker_count=0.
Live UTC start: 2026-09-16T08:22:45.554726+00:00
Live UTC finish: 2026-09-16T08:22:46.681177+00:00

Read PHASE4_MISSION.md, ARCHITECTURE_PHASE4_S3.md (including 2.5, 10, 12, 13), the prior solve test, analogous postflop solve test, and both canonical delegation transcripts (deleg_ae4beec2/task-0.log and deleg_ff1e5e3f/task-0.log).

Rewrote invalid mixed-position sizing fixtures with deliberately empty sizing rules. Uniform one-chip antes, one-chip blinds and stacks of one/three chips leave two actionable blind seats; all N seats still participate in settlement. Complete ranks cover every compatible deal. Each unweighted tree has 10 nodes and observed depth 4. Nine passing parameterized fixture checks cover N=2/6/9, one or two weighted deals, and declared max_raises=1/2. They directly construct configs/roots, traverse all leaves, verify exact rational zero-sum terminal values, enforce bounds, and train the real generic CFR solver before the facade exists. Weighted masses are exactly 1/4 and 3/4.

The independent rational oracle uses public state traversal and exact terminal utilities, with its own expectation recursion and Cartesian enumeration of each player's complete pure information-set choices. It imports neither production expectation nor certificate helpers. A separate test compares its output to the existing production generic certificate, and the future facade certificate is compared too. Six-player pure counts are (1,4,4,1,1,1), baseline (5,1/8,-17/8,-1,-1,-1), incentives (0,3/8,3/8,0,0,0). Exact cap 4 succeeds; cap 3 fails closed in the generic control. The oracle is independent of EV/certificate logic, not a second state/settlement implementation.

Permanent facade contracts cover strict algorithm/iteration/include-certificate/cap inputs, cap validation even when disabled, HU/6/9 deterministic finite normalized policies, exact structural depth, N expected values, immutable nested strategy/metadata and frozen result, caller source mutation detachment via result reconstruction, node bound forwarding, optional/exhaustive diagnostic and fail-closed caps. Float facade EV conservation uses 1e-12 tolerance; terminal and independent rational EV conservation are exact. No skips, xfails, caught missing imports, mocks, or placeholders.

Exact final focused command (cwd /home/genomix-node/poker-solver):

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_nplayer_preflop_solve.py -q --tb=short
```

Exit 1: 41 failed, 11 passed. Failure taxonomy: 1 missing NPlayerPreflopSolveResult import, 40 missing solve_nplayer_preflop imports; zero fixture/config/root/traversal/bound/oracle failures, zero collection errors. Assertions after missing imports remain future GREEN requirements, not claimed as passing today.

Control command:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_nplayer_preflop_config.py tests/test_nplayer_preflop_betting.py tests/test_nplayer_preflop_settlement.py tests/test_nplayer_preflop_information.py tests/test_nplayer_postflop_solve.py -q --tb=short
```

Exit 0: 65 passed in 1.06s. This receipt covers the owned solve suite and adjacent controls, not a repository-wide GREEN claim.

Recovery execution notes: bare python initially lacked pytest, so the exact accepted command uses the repository .venv. An intermediate oracle comparison passed Fraction probabilities to the generic helper, which strictly accepts int/float; changed the uniform profile to exact binary 0.5 floats while retaining Fraction arithmetic inside the independent oracle. Final evidence below supersedes that intermediate run. No temporary probe files were created; in-memory probes left no files to delete. Bytecode and pytest cache writes disabled for all pytest runs. Only the three authorized paths were written; no production, other reports/tests, STATE/PROGRESS, or git edits; no commit.

SHA-256 tests/test_nplayer_preflop_solve.py:
`45291a2e7537883acfcf35a3c700e50fe03225c4a00db3a75372ca243326d51c`

Final captured failure taxonomy:

```text
1 x E   ImportError: cannot import name 'NPlayerPreflopSolveResult' from 'poker_solver.nplayer_preflop' (/home/genomix-node/poker-solver/src/poker_solver/nplayer_preflop.py)
40 x E   ImportError: cannot import name 'solve_nplayer_preflop' from 'poker_solver.nplayer_preflop' (/home/genomix-node/poker-solver/src/poker_solver/nplayer_preflop.py)
41 failed, 11 passed in 0.91s
```
