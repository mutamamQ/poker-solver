from itertools import combinations
from treys import Card, Evaluator

RANKS = "23456789TJQKA"
SUITS = "shdc"
DECK = tuple(r+s for r in RANKS for s in SUITS)
E = Evaluator()
FIXTURES = [
    ("preflop_aa_vs_kk", ("As","Ah"), ("Ks","Kh"), ()),
    ("preflop_99_vs_ako", ("9h","9d"), ("Ac","Kd"), ()),
    ("flop_top_pair_nfd_vs_99", ("As","Ks"), ("9h","9d"), ("Kc","7s","2s")),
    ("flop_set_vs_overpair", ("5h","5d"), ("Ac","Ah"), ("5s","9c","2d")),
    ("flop_oesd_pair_vs_top_pair", ("Jh","Ts"), ("Kd","Qc"), ("Qh","9s","2d")),
    ("turn_flush_vs_full_house", ("Ah","9h"), ("Kd","Kc"), ("Kh","7h","3h","3d")),
    ("turn_pair_draw_vs_top_pair", ("Jc","Td"), ("Ah","Ks"), ("Kd","Jh","9s","2c")),
    ("turn_combo_draw_vs_overpair", ("Ah","Jh"), ("Kd","Kc"), ("Th","9h","2c","3d")),
    ("turn_set_vs_flush", ("7c","7d"), ("Ah","Kh"), ("7h","2h","9h","2c")),
    ("river_two_pair_over_two_pair", ("As","Kh"), ("Qd","Jc"), ("Ah","Kd","Qc","Js","2h")),
    ("river_board_royal_chop", ("Ac","7d"), ("Ad","6s"), ("Ah","Kh","Qh","Jh","Th")),
    ("river_kicker", ("Ac","Qd"), ("Ah","Jc"), ("As","Ks","7h","4d","2c")),
    ("river_board_royal_chop_2", ("2c","3d"), ("4c","5d"), ("As","Ks","Qs","Js","Ts")),
    ("river_straight_vs_overpair", ("6h","5h"), ("As","Ad"), ("7h","8h","9c","Tc","2d")),
    ("river_full_house_k_over_q", ("Ks","Kd"), ("Qs","Qd"), ("Kc","Qc","2h","2d","3s")),
    ("river_wheel_vs_pair", ("As","2s"), ("Kh","Kd"), ("3s","4s","5d","9c","Tc")),
]

def result(fid,h1,h2,board):
    used=set(h1+h2+board)
    assert len(used)==4+len(board)
    remaining=[c for c in DECK if c not in used]
    need=5-len(board)
    wins=ties=losses=0
    for runout in combinations(remaining, need):
        b=[Card.new(c) for c in board+runout]
        s1=E.evaluate([Card.new(c) for c in h1], b)
        s2=E.evaluate([Card.new(c) for c in h2], b)
        if s1<s2: wins+=1
        elif s1==s2: ties+=1
        else: losses+=1
    total=wins+ties+losses
    return fid,wins,ties,losses,total,(wins+ties/2)/total

for f in FIXTURES:
    print(*result(*f), sep="\t")
