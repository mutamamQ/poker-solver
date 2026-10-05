# D205 N-player solve, reach, and deviation diagnostics — parent recovery

Status: recovered from a tool-limited proposal and corrected against `nplayer.py`.

Reuse decisions

- `NPlayerCFRSolver` already propagates per-player realization reaches and chance reach. Counterfactual regret weight is chance times every opponent reach, excluding the updating player's own reach.
- `expected_values_nplayer` already returns an N-vector for a complete profile.
- `unilateral_deviation_certificate` already exhaustively enumerates each player's pure information-set deviations under a strict `max_pure_strategies` bound. It is a diagnostic, not a convergence or equilibrium certificate.
- Do not add a duplicate mutable `ReachTracker`, do not route through the heads-up `best_response.py`, and do not silently sample when the exact diagnostic exceeds its bound.

Typed solve facade

Add a bounded wrapper around the new root and existing solver. It validates the finite tree using config bounds, trains deterministic vanilla CFR for positive iterations, returns normalized average strategy and expected N-player values, and optionally runs the exact unilateral-deviation certificate with an explicit positive pure-strategy cap. Provenance must state `exhaustive finite pure unilateral deviations; diagnostic only`.

Acceptance fixtures

- Four-player nontrivial singleton-deal tree: at least two actors have choices; train and assert finite normalized deterministic strategy, exact terminal conservation, and N-vector values.
- Five-player tiny tree: run the exact deviation certificate with a hand-countable pure-strategy product below the cap; independently enumerate each possible unilateral policy and compare profile values, best-response values, incentives, and total incentive.
- Nine-player bounded spot: one compatible deal and an all-in or otherwise tiny action tree; train/evaluate deterministically and exercise exact side-pot settlement without claiming practical large-game scalability.
- Add a five-player reach oracle whose one-iteration regret deltas are manually scaled by chance and four opponent reaches, proving own reach exclusion.

Performance gates are structural (`max_deals`, finite node/depth validation, pure-strategy cap), not wall-clock promises. Any exceeded bound fails closed with a stable error. No convergence-rate assertion is required for general-sum multiway CFR.
