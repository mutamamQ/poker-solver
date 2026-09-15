# S1 state integration design (parent recovery)

Status: design only. The assigned BryantGPT workstream and its single retry both failed at the provider boundary; the parent inspected the live Python state machine and supplies this recovery artifact. No production code is changed here.

## Existing state graph

`src/poker_solver/multistreet.py` already represents a complete heads-up flop/turn/river finite extensive-form game. `MultiStreetConfig.allowed_runouts` contains complete remaining-board sequences. `MultiStreetState` proceeds as follows:

| Current node | Event | Next node |
|---|---|---|
| root chance | `DEAL` | starting-street decision, same public board |
| decision | `FOLD` | terminal fold, no continuation |
| decision | full/short `CALL` on river | river showdown terminal |
| decision | non-river `CALL` closing action | public `CHANCE` node |
| decision | second `CHECK` on river | river showdown terminal |
| decision | second `CHECK` before river | public `CHANCE` node |
| public chance | `RUNOUT` to turn | turn decision, pot absorbs street commitments, commitments reset |
| public chance | `RUNOUT` while all-in | next public chance or river showdown, no betting |
| public chance | `RUNOUT` to river | river decision or all-in showdown |

This means the correct S1 integration is not to invoke a separate solver from inside `child()` or `returns()`. The full declared tree should remain one composite immutable `GameState`, and one CFR/MCCFR traversal should propagate terminal values through all streets. Nested independent street solves would change the game, mishandle range-dependent public subgames, multiply work inside CFR traversals, and make cache/order effects part of the result.

## Authoritative composition

1. A new additive S1 facade validates a standard flop request with full two-card runout sequences and no continuation/payoff table.
2. It constructs the existing composite `MultiStreetState` root.
3. A bounded preflight audits/collects that exact root before training.
4. Existing two-player `CFRSolver` or seeded `MCCFRSolver` trains once over the complete tree.
5. River fold/showdown `returns()` remains the only source of utility. No street-boundary node stores a terminal value in automatic mode.
6. Explicit continuation remains a separate reference adapter/fixture, not a branch inside the automatic state transitions.

## Dependency graph

    strict S1 JSON / typed config
                 |
                 v
      S1 request validation + limits
                 |
                 v
    MultiStreetConfig -> create_root
                 |             |
                 |             +-> card evaluator at river
                 v
      complete composite GameState
          |                 |
          v                 v
      CFR/MCCFR       audit / best response
          |
          v
       S1 result metadata/API/CLI

`preflop.py` and `multiway.py` are not modified for S1. Their caller-continuation boundaries belong to S3 and S2 respectively. `nplayer.py` is a future-compatible solver contract, not part of S1's initial heads-up implementation.

## State and accounting invariants

- `Action.amount` remains current-street raise-to.
- Paid chips are `new_target - own_committed`; street commitments move into `pot` exactly once when the next public card is revealed.
- `total_contributed` never resets and is used once by terminal net-utility accounting.
- A fold is terminal immediately; it never requests a public runout or continuation.
- An all-in closed before river skips later decisions but still traverses every declared compatible public runout.
- Public runout chance is conditioned on board plus both realized private hands. The emitted chance action is public; information keys include the resulting board but exclude the opponent hand and private deal index.
- Complete runout sequences are declaration-ordered inputs; emitted next cards are in stable card order with probability equal to compatible sequence multiplicity divided by compatible sequence count.
- Every two-player terminal has two finite returns whose sum is zero. S1 does not add rake or multiway semantics; those are S2 integration concerns.
- Same immutable input, algorithm, iteration count and (for MCCFR) seed yields the same result on the supported runtime.
- Direct construction remains an attack surface: S1 must avoid exposing partially initialized state objects and must add validation/audit gates before solve.

## Migration and boundaries

- Preserve existing version-2 `load_multistreet_config` and `solve_multistreet` byte/behavior compatibility.
- Add an S1 operation/entry point rather than teaching the old strict v2 loader to ignore new fields. Unknown fields must continue to fail closed.
- Standard S1 input contains no `continuation_mode` and no payoff table: automatic is defined structurally by a declared full runout/action tree ending at river terminals.
- The explicit reference path uses a separate typed test adapter with complete leaf coverage and strict zero-sum values; it does not weaken standard request validation.
- S1 is heads-up postflop. Four-to-nine-player automatic state composition is S2; preflop-to-postflop composition is S3; abstraction and continuous sizing are S4/S5.

## Implementation implications

- Reuse `MultiStreetState.child`, `chance_outcomes`, `information_state_key`, and `returns`; do not duplicate them in a recursive continuation module.
- Add a bounded two-player preflight because current `EngineConfig.max_nodes/max_depth` enforcement is explicit for N-player collection and checkdown, not the classic two-player path.
- Keep any count/cache metadata observational only. No cache is required for S1 correctness; a cache may be added only after uncached equivalence and invalidation are audited.
- The first acceptance fixture should use one private combo per player and a tiny declared runout tree so an explicit terminal-table representation is strategically equivalent and independently enumerable.
