# Hand-evaluation correctness

## Representation and ordering

Cards use rank `23456789TJQKA` plus suit `shdc`; all inputs must be distinct. A five-card rank is a lexicographically comparable tuple `(category, tie_break...)`, larger is better. Categories are high card 0, pair 1, two pair 2, trips 3, straight 4, flush 5, full house 6, quads 7, straight flush 8. A wheel A2345 has straight high 5. Seven-card Hold'em returns the maximum over all C(7,5)=21 subsets; using zero, one, or two hole cards is legal.

Tie-break vectors: quads `(quad,kicker)`; full house `(trips,pair)`; flush/high card all five descending; straight `(high,)`; trips `(trips,k1,k2)`; two pair `(highPair,lowPair,kicker)`; pair `(pair,k1,k2,k3)`.

## Exact frequencies

For C(52,5)=2,598,960 hands: straight flush 40; quads 624; full house 3,744; flush excluding straight flush 5,108; straight excluding straight flush 10,200; trips 54,912; two pair 123,552; one pair 1,098,240; high card 1,302,540. These sum exactly to 2,598,960.

For best-of-seven among C(52,7)=133,784,560 sets: straight flush 41,584; quads 224,848; full house 3,473,184; flush 4,047,644; straight 6,180,020; trips 6,461,620; two pair 31,433,400; one pair 58,627,800; high card 23,294,460.

## Canonical vectors

1 As Ks Qs Js Ts -> ace-high straight flush
2 5h 4h 3h 2h Ah -> five-high straight flush
3 Kc Kd Kh Ks 2c -> kings quads, 2 kicker
4 Ac Ad Ah Kc Kd -> aces full of kings
5 Kc Kd Kh Ac Ad -> kings full of aces; loses to 4
6 As Js 9s 7s 3s -> ace-high flush
7 Kh Qh Jh 9h 8h -> king-high flush; loses to 6
8 Ac Kd Qh Js Tc -> ace-high straight
9 5c 4d 3h 2s Ac -> five-high straight
10 6c 5d 4h 3s 2c -> six-high straight; beats 9
11 9c 9d 9h Ah Kc -> trips nines, A,K
12 Ac Ad Kc Kd Qh -> aces and kings, Q
13 Ac Ad Qc Qd Kh -> aces and queens, K; loses to 12
14 Ac Ad Kh Qc Jd -> pair aces, K,Q,J
15 Ac Ad Kh Qc Td -> pair aces, K,Q,T; loses to 14
16 Ac Kd Qh Js 9c -> A,K,Q,J,9 high
17 9s 8s 7s 6s 5s 3c 2h -> nine-high straight flush
18 Jc Jd Jh Js Ac Kd Qh -> quad jacks, ace
19 Tc Td Th 9c 9d 8s 7h -> tens full of nines
20 Kh Qh Jh 9h 7h 6c 5d -> king-high flush
21 Tc 9d 8h 7s 6c 4h 2d -> ten-high straight
22 8c 8d 8h Ah Kc Qd Jh -> trips eights, A,K
23 Qc Qd Jc Jd Ah Kh 9s -> queens and jacks, A
24 7c 7d Ah Kc Qh Js 9d -> pair sevens, A,K,Q
25 Ac Kd Qh Js 9c 7h 5d -> A,K,Q,J,9 high
26 hole 2c3d / board AsKsQsJsTs -> board ace-high straight flush
27 hole 9c9d / board 8h7s6c5d4h -> board eight-high straight
28 As As Kh Qc Jd -> duplicate-card error
29 five cards only -> valid 5-card evaluation
30 fewer than 5 or more than 7 cards -> input-length error

## Sources and cross-checks

- Combinatorial frequency tables: https://en.wikipedia.org/wiki/Poker_probability
- Cactus Kev evaluator explanation: http://suffe.cool/poker/evaluator.html
- PH Evaluator, independent perfect-hash implementation/tests: https://github.com/HenryRLee/PokerHandEvaluator
- Deuces pure-Python implementation: https://github.com/worldveil/deuces
- Treys Python 3 port (useful oracle, not independent of Deuces): https://github.com/ihendley/treys

The project must also exhaustively enumerate all 2,598,960 five-card sets and reproduce the category totals; isolated vectors alone are insufficient.
