# Exact Hold'em equity fixtures

Semantics: enumerate every unordered completion of the board from cards not in either hand or current board. `equity = (wins + ties/2)/total` heads-up. Counts below were generated exhaustively with Treys 0.1.8 on exact cards; the project implementation must independently reproduce them. Treys is a Python 3 port of Deuces, so Treys and Deuces do not count as independent algorithms.

| id | hero | villain | board | win | tie | loss | total | hero equity |
|---|---|---|---|---:|---:|---:|---:|---:|
| preflop_aa_vs_kk | As Ah | Ks Kh | - | 1410336 | 9308 | 292660 | 1712304 | 0.826366112559452 |
| preflop_99_vs_ako | 9h 9d | Ac Kd | - | 943067 | 6697 | 762540 | 1712304 | 0.5527146464646465 |
| flop_top_pair_nfd_vs_99 | As Ks | 9h 9d | Kc 7s 2s | 946 | 0 | 44 | 990 | 0.9555555555555556 |
| flop_set_vs_overpair | 5h 5d | Ac Ah | 5s 9c 2d | 886 | 0 | 104 | 990 | 0.8949494949494949 |
| flop_pair_draw_vs_top_pair | Jh Ts | Kd Qc | Qh 9s 2d | 284 | 0 | 706 | 990 | 0.2868686868686869 |
| turn_flush_vs_full_house | Ah 9h | Kd Kc | Kh 7h 3h 3d | 0 | 0 | 44 | 44 | 0 |
| turn_pair_draw_vs_top_pair | Jc Td | Ah Ks | Kd Jh 9s 2c | 9 | 0 | 35 | 44 | 0.20454545454545456 |
| turn_combo_draw_vs_overpair | Ah Jh | Kd Kc | Th 9h 2c 3d | 12 | 0 | 32 | 44 | 0.2727272727272727 |
| turn_set_vs_flush | 7c 7d | Ah Kh | 7h 2h 9h 2c | 44 | 0 | 0 | 44 | 1 |
| river_two_pair | As Kh | Qd Jc | Ah Kd Qc Js 2h | 1 | 0 | 0 | 1 | 1 |
| river_board_royal | Ac 7d | Ad 6s | Ah Kh Qh Jh Th | 0 | 1 | 0 | 1 | 0.5 |
| river_kicker | Ac Qd | Ah Jc | As Ks 7h 4d 2c | 1 | 0 | 0 | 1 | 1 |
| river_board_royal_2 | 2c 3d | 4c 5d | As Ks Qs Js Ts | 0 | 1 | 0 | 1 | 0.5 |
| river_straight | 6h 5h | As Ad | 7h 8h 9c Tc 2d | 1 | 0 | 0 | 1 | 1 |
| river_full_house | Ks Kd | Qs Qd | Kc Qc 2h 2d 3s | 1 | 0 | 0 | 1 | 1 |
| river_wheel | As 2s | Kh Kd | 3s 4s 5d 9c Tc | 1 | 0 | 0 | 1 | 1 |

Validation must compare integer counts, not rounded percentages. Range equity is a conditional joint distribution: discard board/hand collisions, multiply original combo weights, then renormalize over compatible ordered hand pairs. Suit relabeling is a metamorphic oracle.

## Sources

- PokerStove exhaustive evaluator/tools: https://github.com/andrewprock/pokerstove
- Treys oracle used for the table: https://github.com/ihendley/treys
- PH Evaluator independent implementation candidate: https://github.com/HenryRLee/PokerHandEvaluator
- Standard category probabilities: https://en.wikipedia.org/wiki/Poker_probability

The checked-in implementation must not depend on Treys at runtime; these are external oracle fixtures.
