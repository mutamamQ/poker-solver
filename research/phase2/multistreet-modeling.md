# Multi-street heads-up model

## Scope

Phase 2 models a finite postflop heads-up Hold'em spot beginning on a specified flop, turn, or river. Private hands come from exact combo-weighted ranges. Public board cards are exact chance outcomes. Betting uses a configured finite set of pot fractions plus optional all-in. There is at most one bet per street and therefore no raise branch in the first implementation; the supported public actions are check, bet, fold, and call. This is an explicit action abstraction, not unrestricted no-limit Hold'em.

A pot-limit mode caps a wager using the pot-limit rule; an all-in action is additionally capped by effective remaining stack. No-limit mode omits the pot cap but still uses only configured discrete sizes.

## Immutable state

The state needs: config/version; dealt private combos or undealt root; board; street; pot at the beginning of the spot; each player's remaining stack; cumulative contributions since the spot began; current street history; complete public history; and pending chance status. The root conditions incompatible weighted deals by board/card collisions and normalizes `w0*w1` over legal ordered pairs.

After a check-check or bet-call closes flop/turn betting, chance reveals one uniformly selected legal board card; contributions for action legality reset but cumulative contributions do not. If either player is all-in, remaining public cards are dealt without further betting. River closure goes to showdown. Fold terminates immediately.

## Accounting and utility

A bet action's `amount` means chips newly committed by the actor, not raise-to. Calling commits exactly the outstanding amount, bounded by stack; equal starting effective stacks ensure no unmatched heads-up side-pot amount. Pot-limit maximum is computed after including the call when facing a wager; because Phase 2 has no raises, open-bet maximum is the current pot. All action amounts are positive integers.

Terminal returns are net from the start of the spot: initial equal pot ownership is represented by ±`initial_pot/2`; each player's post-start contribution is debited from that player and the final pot award credited, then converted to a zero-sum pair. Bet-fold returns the unmatched portion correctly. Ties split the contested pot.

## Information sets

The acting player's key includes version, player, own cards, public board, full public action/chance history, pot/stacks/contributions, sizing configuration, and variant. It excludes the opponent's cards. Full public history preserves perfect recall; equal keys must have identical ordered actions.

## Complexity boundary

Exhaustive public runouts branch by up to 45 then 44 cards after private cards and a flop. Full-tree vanilla CFR is therefore only a reference for tiny ranges/restricted runout decks. External-sampling MCCFR is the normal multi-street path. Caching hand ranks and immutable transitions is safe; suit/card abstraction is deferred until equivalence has its own tests.

## Sources

- Pot-limit betting rule and minimum raise: https://barge.org/rulebook/pot-limit.html
- CFR extensive-game/information-set requirements: https://proceedings.neurips.cc/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html
- MCCFR: https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html
- OpenSpiel game/state framework: https://github.com/google-deepmind/open_spiel
- PokerKit state-machine reference: https://github.com/uoftcprg/pokerkit
- No-limit game-size study: https://arxiv.org/abs/1302.7008

## Corrections to subagent draft

The earlier draft's pot-limit formula and terminal payoff pseudocode were rejected. Ranges are conditioned on cards; posterior strategy analysis is not implemented as in-place mutation of the chance prior.