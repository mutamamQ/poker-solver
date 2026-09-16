# S3-I2 exports/capability/backward-compatibility audit

**Auditor:** A3I2-I4R (fresh non-author retry)
**Scope:** Package exports, capability manifest, backward compatibility
**Candidate:** FROZEN_FOR_FRESH_NON_AUTHOR_AUDIT (2026-09-16T10:15:55Z)
**Audit timestamp:** 2026-09-16T10:25:35Z
**Status:** PASS

## Manifest verification

**Required:** 20/20 entries verified
**Result:** ✓ All 20 SHA256 hashes match CANDIDATE_MANIFEST.md

```text
ARCHITECTURE_PHASE4_S3.md: 6585176ab281ccc681ecb38579a3fc2b0750253cc05f3e7f182448983c5919db ✓
src/poker_solver/nplayer_preflop.py: 5c8f03f475ce727207157f7ed6ba35824f88165b00d24ddc0916522947de8aae ✓
src/poker_solver/api_v4.py: 70d378d6a52ae544615a5aa4dda6bd9e987f8161f08119914a0762ed0727a1a3 ✓
src/poker_solver/api_v3.py: 01ad9f614a01a4b623a36d42b611d75050fbe3ebdead650fbd4272852e593a4a ✓
src/poker_solver/__init__.py: 0c2a03813d375d362c582b3df0744d80802c5f008e2b42825f4afeaed5326159 ✓
src/poker_solver/cli.py: 3f4df8452f427757d11c7bcee8b44b783efe65290b2f18050cdeba67d94ada13 ✓
tests/test_nplayer_preflop_solve.py: 45291a2e7537883acfcf35a3c700e50fe03225c4a00db3a75372ca243326d51c ✓
tests/test_api_v4_nplayer_preflop.py: 38b36491172a3152157ff369f680ba0a5bab25c5a551db3552ed7074f52ff50d ✓
tests/test_phase4_s3_examples.py: 8c3a416b298aa4bad0c902817500ccf7450f73636330cebc396fac8828f27061 ✓
tests/test_phase4_s3_exports.py: 40df575dd72fd5b39a9bbd7c5f3b1358a2a344f92be0d5b587bdb1b4bc232c60 ✓
examples/phase4/nplayer_2p_preflop.json: 884bd673589224885feeafe8633fc9a4cdae69b18135e9ebf4cd1eae3d7fa8e5 ✓
examples/phase4/nplayer_6p_preflop.json: 3d46183d39b0bb905a3679a38776683c47db9657825c92e55bc239176dcc7365 ✓
examples/phase4/nplayer_9p_preflop.json: 1f7b26a0e3fee5912b9695a59a2a181dbd13f3b5df386a9fe15f07e690dcdfb9 ✓
research/phase4/s3-i2-integration-build/01-integration-author-codex.md: 14b8dd501d1a36d2ad3aac98d360c097504a17c175058668f248e67a3e3f31ff ✓
research/phase4/s3-i2-integration-build/02-parser-contract-parent.md: c1722069adc923e054cee5773e9d337a384e7749907757e2e2563ccc5d452add ✓
research/phase4/s3-i2-integration-build/03-serialization.md: adf2d65d46d032820ff7f2930f6dd00ac04433262f5335f42d46891703334f5b ✓
research/phase4/s3-i2-integration-build/04-capability-exports.md: 680b37a0f199fbb2ac9f51f407a3c3d168217eba190d67f3fabedb8d5f555710 ✓
research/phase4/s3-i2-integration-build/05-examples-cli.md: a15a2528a2c093d1ef91b2fc91b7e73e91de2abdc1d92770d0a23c38c61aa0c8 ✓
research/phase4/s3-i2-integration-build/06-tdd-release.md: 2b5b61269322cb848c61f047e8e358507aa87cf62d8266775117ca865d8c04f3 ✓
research/phase4/s3-i2-integration-audit/PARENT_FULL_REGRESSION.md: 114945024fbf7d2f4356c5f1195fed4770557fb25058ebd23612d75684d9c39f ✓
```

## Export suite: test_phase4_s3_exports.py

**Test count:** 13 tests
**Result:** 13 passed in 0.13s
**Status:** ✓ PASS

### Nine identity exports verified

1. ✓ `NPlayerPreflopConfig` exported from package root (identity match)
2. ✓ `NPlayerPreflopContinuation` exported from package root (identity match)
3. ✓ `NPlayerPreflopSizingRule` exported from package root (identity match)
4. ✓ `NPlayerPreflopPublicAction` exported from package root (identity match)
5. ✓ `NPlayerPreflopState` exported from package root (identity match)
6. ✓ `NPlayerPreflopSolveResult` exported from package root (identity match)
7. ✓ `enumerate_nplayer_preflop_deals` exported from package root (identity match)
8. ✓ `create_nplayer_preflop_root` exported from package root (identity match)
9. ✓ `solve_nplayer_preflop` exported from package root (identity match)

### Capability manifest verification

✓ `nplayer-preflop` feature present with exact specification:
- status: `implemented-bounded`
- players: `[2, 9]`
- street: `preflop-one-round`
- interfaces: `["typed", "json-v4", "cli-phase4"]`
- continuations: `supplied-or-derived-bounded`
- deviation: `exhaustive-diagnostic-only`

✓ Deep-copy isolation verified (caller mutations do not affect fresh responses)
✓ Deterministic response verified (repeated calls return identical results)

### Backward compatibility: S1/S2 preservation

✓ All S1 exports remain identical (AllStreetPostflopConfig, AllStreetSolveResult, create_allstreet_root, solve_allstreet_postflop, dispatch_v4)
✓ All S2 exports remain identical (NPlayerPostflopConfig, DealN, NPlayerPublicAction, NPlayerPostflopState, enumerate_deals, create_nplayer_postflop_root, NPlayerPostflopSolveResult, solve_nplayer_postflop)
✓ All existing v3 capability features remain unchanged (preflop, multiway-postflop, n-player-cfr, allstreet-postflop, nplayer-postflop)

## Adjacent API controls

### test_api_v4_nplayer_preflop.py

**Test count:** 30 tests (actual count verified, not assumed)
**Result:** 30 passed in 0.13s
**Status:** ✓ PASS

Covers: envelope/payload schema, determinism, deep-copy isolation, validation (bool/nonfinite/malformed inputs), bounds enforcement, algorithm restrictions, exact strategy values.

### test_api_v3.py

**Test count:** 8 tests
**Result:** 8 passed in 0.06s
**Status:** ✓ PASS

Covers: capability manifest determinism, presets, ICM, bounty-KO, range operations, inference, validation, CLI.

### test_api_v4.py

**Test count:** 36 tests
**Result:** 36 passed in 2.53s
**Status:** ✓ PASS

Covers: end-to-end solve, determinism (vanilla CFR/MCCFR), validation (unknown/missing/bool/nonfinite fields), resource bounds, blocker conflicts, JSON serialization, metadata, deep response isolation.

## Combined regression

**Total tests:** 87 (13 exports + 30 API preflop + 8 v3 + 36 v4)
**Result:** 87 passed in 4.69s
**Status:** ✓ PASS
**No failures, no blockers**

## Evidence summary

- Manifest: 20/20 entries verified before execution
- Exports: 9/9 identity exports confirmed
- Capability: exact deep-copy isolated nplayer-preflop feature present
- Backward compatibility: S1/S2 exports and v3 capabilities preserved
- API controls: 30 preflop tests (actual count), 8 v3 tests, 36 v4 tests
- Combined: 87 passed, 0 failed
- Audit timestamp: 2026-09-16T10:25:35Z

## Conclusion

**PASS**: All requirements met. Nine identity exports verified, exact capability manifest present with deep-copy isolation, S1/S2 preservation confirmed, 87 tests passed with no blockers.