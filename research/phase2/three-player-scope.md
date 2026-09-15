# Three-player scope decision

## Decision

Phase 2 remains explicitly heads-up. Three-player support is not required for the backend's Phase 2 correctness claim. This is a game-theoretic boundary, not merely a scheduling choice.

## What changes

Chip-conserving three-player cash poker can still be represented as constant-sum (and shifted to zero-sum across all players): one player's net gain is the others' total net loss. It is nevertheless not a two-player zero-sum game. The minimax equivalence, unique game value, two-player exploitability normalization, and theorem that average no-regret self-play approaches a Nash equilibrium do not transfer.

A finite multiplayer game still has a mixed Nash equilibrium. `NashConv = sum_i(max_{sigma'_i} u_i(sigma'_i, sigma_-i) - u_i(sigma))` remains zero exactly when no player has a profitable unilateral deviation (a Nash equilibrium), but `NashConv/2` is no longer the heads-up exploitability convention and low regret does not generally imply that the average joint profile approaches Nash.

Research reports practical multiplayer CFR agents but explicitly states that the two-player theoretical guarantees are lost. That is evidence CFR may be useful empirically, not proof of equilibrium accuracy.

## Engineering impact

The current protocol hard-codes two returns, `other_player`, two reaches, and zero-sum pair checks. Multiway Hold'em also needs:

- arbitrary player count and turn order, folds that leave changing active sets;
- per-player stacks and cumulative commitments;
- main/side-pot construction and eligibility at showdown;
- multiple opponents' private ranges and blocker conditioning;
- N-component utilities and best responses against a joint opponent profile;
- a multiplayer metric/API whose normalization is not labeled heads-up exploitability;
- independent toy-game/normal-form oracles before any poker accuracy claim.

## Future migration path

A future protocol version should expose `num_players`, `returns() -> tuple[float, ...]`, vector reaches, active/all-in masks, and a pot-layer ledger. Keep the current 2-player protocol and solvers stable rather than weakening their invariants. First implement a tiny three-player extensive-form game with a separately enumerated normal-form oracle; then test side-pot conservation exhaustively; only then evaluate multiplayer regret algorithms without promising Nash convergence.

## Sources

- Nash equilibrium existence: https://www.pnas.org/doi/10.1073/pnas.36.1.48
- Original two-player-zero-sum CFR guarantee: https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- MCCFR: https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html
- Multiplayer CFR empirical/theoretical limits: https://arxiv.org/abs/1305.0034
- AAMAS 2010 three-player poker agents: https://ifaamas.csc.liv.ac.uk/Proceedings/aamas2010/pdf/01%20Full%20Papers/03_01_FP_0089.pdf
- OpenSpiel multi-agent algorithm inventory: https://openspiel.readthedocs.io/en/latest/algorithms.html

## Parent corrections

The subagent draft incorrectly called chip-conserving three-player poker general-sum in the utility-sum sense, claimed zero NashConv could occur at a non-Nash profile, asserted monotonic exploitability, and attached unsupported schedules. Those claims were removed.