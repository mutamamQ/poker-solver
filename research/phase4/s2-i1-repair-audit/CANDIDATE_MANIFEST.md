# S2-I1 repaired frozen candidate manifest

Frozen at: 2026-09-15T22:51:26Z
Base commit: `1d06ac6629e99bc7e3a52851546ff6179c15a945`
Preserved baseline tag: `phase3-398-green` → `feba8222a0b614b0c64eca59402403ce733195ea`

Repairs after rejected first audit:
- projected N=3 public traces cover CHECK, CALL, RAISE, re-raise, FOLD, and fold-out branches plus information partitions;
- five-player settlement creates a real one-chip remainder assigned by declared order;
- refund coverage executes production transitions and asserts current-street-bounded terminal ledgers.

No candidate file may change during this repair audit wave.

| SHA-256 | Path |
|---|---|
| `83861a58872a6dbfb1ce0cdbfebecaf8f016f1575b7a8bf19bc5d734eac5dfdd` | `src/poker_solver/nplayer_postflop.py` |
| `3efc06fd87e13789d3ec3b11f927babbfce268fe306247db54c2f1ea91a1adde` | `tests/test_nplayer_postflop_config.py` |
| `76a880e425bd118e283dea6ce30c2d680fd9a4ba40110b069b589ba20c292b3c` | `tests/test_nplayer_postflop_betting.py` |
| `0b06f6175d4400508ea2c98cf1fe426faed252db14752f80f8e73d6fd3ed172d` | `tests/test_nplayer_postflop_settlement.py` |
| `bfac4422c274583c099748c0ad4ff9996170aa48f5df636e34c978d77cfcc869` | `tests/test_nplayer_postflop_information.py` |

Parent verification before freeze:
- focused S2-I1: 46 passed;
- legacy multiway/N-player/accounting: 44 passed;
- full regression: 602 passed in 207.14s;
- `git diff --check`: pass;
- baseline tag identity: pass.
