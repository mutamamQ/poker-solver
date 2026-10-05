# A04 explicit-continuation oracle — parent recovery

Status: PARTIAL; no S1-I1 candidate defect; mandatory S1-I2 work remains.

The fresh non-author A04 reviewer verified the frozen candidate 8/8 and ran the S1-I1 focused gate (116 passed in 2.42s). Its `/tmp/a04_explicit_oracle.py` then failed before the requested comparison because it invented repository interfaces: terminal `utility()` instead of `returns()`, algorithm `"vanilla"` instead of `"vanilla-cfr"`, unsupported seed use, and nonexistent result/solver attributes. The script and all claimed downstream oracle conclusions are rejected.

Authoritative scope adjudication

`ARCHITECTURE_PHASE4_S1.md:151-159` assigns `tests/test_allstreet_oracle.py`, the exact explicit-continuation oracle/convergence sweep, canonical example, CLI, package exports, and capability integration to S1-I2 after S1-I1 audit. Therefore A04's failure does not identify an S1-I1 implementation defect and does not block committing the accepted S1-I1 core. It does prevent declaring S1 complete.

Required next evidence

S1-I2 must add a permanent production-importing oracle using the real `GameState` protocol and the architecture's two fixtures:

- forced/check-only structural fixture with independently enumerated terminal awards and numerical tolerance derived from exact accumulation;
- strategic automatic-vs-explicit representation comparison satisfying `abs(EV0_auto - EV0_explicit) <= NC_auto + NC_explicit + delta_num`, with a convergence sweep if needed.

A fresh non-author S1-I2 audit must inspect the oracle source and premises and rerun it before S1 acceptance.
