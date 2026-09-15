# Heads-up Hold'em rules for the reference spot

## Full-rule facts

A player may check only when not facing an unmatched wager, fold or call only when facing one, and bet only when no wager is outstanding. A full raise must increase the wager by at least the largest preceding full bet or raise increment in that round. An all-in wager smaller than a full raise is legal but does not by itself reopen raising to a player whose action is already complete. The minimum opening bet in no-limit Hold'em is the minimum bring-in/big blind for that betting round—not the current pot.

Track `committed[p]` for this spot, `remaining[p]`, `to_call=max(committed)-committed[p]`, and the last full raise increment. An action expressed as `raise_to` adds `raise_to-committed[p]`; never confuse raise-by with raise-to. A call adds `min(to_call, remaining[p])`. In heads-up, unmatched excess caused by a short all-in is returned and is not contestable.

## Utility baseline

Let `initial_pot` be dead money already present at spot start and `c0,c1` new contributions. Utilities are net from spot start. On a fold by f, the nonfolder receives the initial pot plus the opponent's contribution but receives their own contribution back economically: `u_winner = initial_pot + c_f`, `u_folder = -(initial_pot + c_f)` only if initial-pot ownership has deliberately been assigned entirely as zero-sum dead money to the winner/loser pair. A cleaner poker convention allocates a constant initial wealth baseline: terminal utilities are each player's final stack minus starting stack, including an explicit ownership allocation for initial pot. This project will encode terminal payoff directly and assert zero sum, documenting that the initial pot is treated as contested dead money split equally in the baseline: winner payoff `initial_pot/2 + opponent_contribution`, loser negative of it. At showdown, winner payoff `initial_pot/2 + opponent_contribution`, loser negative; a tie is 0 when contributions match. This requires symmetric contributions at showdown in the limited tree.

## Deliberately supported scope

One river only; two players; already posted pot; no rake; no blinds/antes logic; no side pots; equal effective remaining stack; discrete legal bet/raise-to actions supplied by the game configuration; integer or exact rational chip units; fold/check/call/raise; showdown after check-check or call. Range weights are over exact unordered two-card combos. Root chance enumerates only mutually compatible combos and renormalizes joint weights. Duplicate cards and an empty conditional range are errors.

Because action sizes are explicitly enumerated, the engine validates configured actions against stack and full-raise constraints but does not generate every legal no-limit size. Short all-ins and reopening are tested in the generic betting helper even if the shipped reference fixture avoids them.

## Edge cases

- zero remaining stack: immediate showdown, no betting;
- check-check: showdown;
- bet-fold: immediate fold terminal;
- bet-call: matched contributions, showdown;
- raise-to at or below current wager: reject;
- configured amount beyond stack: reject or canonicalize only if explicitly marked all-in;
- duplicate/blocked hand pair: remove before normalization;
- zero compatible joint weight: reject;
- odd chips: use rational/float utility in a solver, not floor division;
- tie on board: zero net utility under symmetric spot baseline.

## Sources

- Poker TDA 2024 rules, especially betting/raising and non-full all-ins: https://www.pokertda.com/view-poker-tda-rules/
- PokerStars game rules: https://www.pokerstars.com/poker/games/rules/
- ACPC configurable poker definitions: https://github.com/ethansbrown/acpc
- OpenSpiel universal poker model: https://github.com/google-deepmind/open_spiel
