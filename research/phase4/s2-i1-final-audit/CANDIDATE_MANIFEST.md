# S2-I1 frozen candidate manifest

Frozen at: 2026-09-15T22:27:24Z
Base commit: `1d06ac6629e99bc7e3a52851546ff6179c15a945`
Preserved baseline tag: `phase3-398-green` → `feba8222a0b614b0c64eca59402403ce733195ea`

No candidate file may change during the audit wave.

| SHA-256 | Path |
|---|---|
| `83861a58872a6dbfb1ce0cdbfebecaf8f016f1575b7a8bf19bc5d734eac5dfdd` | `src/poker_solver/nplayer_postflop.py` |
| `3efc06fd87e13789d3ec3b11f927babbfce268fe306247db54c2f1ea91a1adde` | `tests/test_nplayer_postflop_config.py` |
| `76a880e425bd118e283dea6ce30c2d680fd9a4ba40110b069b589ba20c292b3c` | `tests/test_nplayer_postflop_betting.py` |
| `1b97dce26eaf98974f2039eddfdbff3dded600bf4e1fecd46e1047205c21f71d` | `tests/test_nplayer_postflop_settlement.py` |
| `46650955ae9438645f8a381eb43e18af79ca14a83475d1b687fdda6426e56f8a` | `tests/test_nplayer_postflop_information.py` |

Parent pre-freeze evidence:
- S2-I1 focused: `40 passed in 0.17s`.
- Legacy multiway/N-player/accounting: `44 passed in 0.19s`.
- Full regression: `596 passed in 208.28s (0:03:28)`.
- `git diff --check`: pass.
