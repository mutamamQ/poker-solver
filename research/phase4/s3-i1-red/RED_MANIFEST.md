# S3-I1 RED candidate manifest

Refrozen after architecture-protocol fixture corrections: 2026-09-16T05:28:29Z
Accepted S3 design commit: `65d411793d1d7767d86500d0adffe9f40b379108`
Preserved baseline tag: `phase3-398-green` -> `feba8222a0b614b0c64eca59402403ce733195ea`

## Refrozen hashes

```text
a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6  ARCHITECTURE_PHASE4_S3.md
5a214b900a7ad1b61aa67cd294d7000e3eef0023f82bb834d1e94035f815a867  tests/test_nplayer_preflop_config.py
d61a86d39f864d494f19a91698478c4af39b76d6ad0372321f18d69706349f69  tests/test_nplayer_preflop_betting.py
e3955709899fd1ac907cc6670268940fcb04eec35486417dc8d82773e93589c3  tests/test_nplayer_preflop_settlement.py
282112f2b88e57b1b8b25bbdd69d0f6fb90df714e92ccff80945f9724375e69d  tests/test_nplayer_preflop_information.py
6212f11a238659f8991fcd42ce94098d4872dd4e06eb16e8f6c2b7a2954ea9b2  research/phase4/s3-i1-red/01-config.md
04ae36d13ef68588582541218f33c57dcc45898b84029ff216c40360bf98fe78  research/phase4/s3-i1-red/02-betting.md
45d5aefaf4bcda9dd288f7ec9c79ef009cb2e2afe90686005283034212904207  research/phase4/s3-i1-red/03-settlement.md
13bb38d97faae9c4fca4b2fdd93dab96d90cf640c9670b8f7b434e5c5ed3ac98  research/phase4/s3-i1-red/04-information.md
038c0fe9358d93b01ccc65118dc15155658c1e424219d96872bc4579cfb47f7e  research/phase4/s3-i1-red/05-red-authenticity-plan.md
1858a0d54c4da778fbd731d6047e785e352fe26bae8872fd6a7027f72a06fce8  research/phase4/s3-i1-red/06-boundary-legacy-plan.md
0a8530374999e653d443391038fd8db1a0efd3398418345cc7ff1d5e4d2a85cf  research/phase4/s3-i1-red/.hb/R3I1-1R-PARENT
818d9fe45cfc6ce25bdbf53267a8be9acd268a463f717d818e8b5640c414ff46  research/phase4/s3-i1-red/.hb/R3I1-2S
e9cf6dc32b547e6aade50d97a9e571575a0f61cce6d0e84d15a46a63e8a27aed  research/phase4/s3-i1-red/.hb/R3I1-3V-PARENT
d9232cf539e501102a0b3de0d9e57234540de90ed52a49d8adee6f5bc07cdef7  research/phase4/s3-i1-red/.hb/R3I1-4U-PARENT
8f57a88fbff5c6a82d1603c9cd283cefd44d4369fe832a808953d67250ac1482  research/phase4/s3-i1-red/.hb/R3I1-5S
1829fec516e6a316481cb9eb8d044685a248cccca5cb7134d9c41001fcb37192  research/phase4/s3-i1-red/.hb/R3I1-6S
```

## Parent RED gate

The first GREEN run exposed three fixture-only issues that the missing-module collection gate could not execute: two N=3 button values, eight chance-action protocol calls in the betting suite, and the HU helper's button. The parent corrected only those architecture-public fixture values. Production was then temporarily removed and each final suite independently produced exit 2 with the exact root cause:

`ModuleNotFoundError: No module named 'poker_solver.nplayer_preflop'`

All four final suites compile, import production directly at module scope, and contain no caught import, skip, xfail, placeholder, vacuous chance-root terminal shortcut, or unsupported sizing literal. Production was restored after RED revalidation. Disposition: four final behavioral RED receipts accepted and hash-bound.
