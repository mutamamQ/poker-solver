# S4 architecture design-audit R2 candidate manifest

Status: FROZEN
Candidate base directory: `/home/genomix-node/poker-solver`
Accepted base HEAD: `149780bf37e3e3a824e03e6d2c1df3cd99b12cd6`
Preserved annotated tag object: `phase3-398-green` -> `feba8222a0b614b0c64eca59402403ce733195ea`
Preserved tag peeled commit: `5809ecca28ae6d0588ea07709c90beac3072c167`

## Frozen candidate

- `ARCHITECTURE_PHASE4_S4.md`
  - SHA-256: `37d84511b77f55693e76abc005538ea6b290ba041d1c6b8d38a2a22b37c6e6e2`
  - bytes: `35582`
  - logical lines: `550`
- `PHASE4_MISSION.md`
  - SHA-256: `5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61`
- authoritative physical-engine design input `research/phase4/s4-design/02-engine-integration-codex.md`
  - SHA-256: `79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d`

## R1 finding and repair

R1 alternate API auditor C4D4-CODEX report `research/phase4/s4-design-audit/04-api-result-codex.md` SHA-256 `4b74b1a27da50c6598a0cae4cfcd5846befcea560f6ba821d6e2ff49179c1ee4` rejected the earlier architecture SHA `4285905100a11e3523b241f236233118bb9f4dac67f7c8aa92570fba3048a0e3` for three reproduced findings:

1. incomplete exact response and nested wire schema;
2. ambiguous optional versus required base bounds;
3. integer range weights above `2**53` losing exactness through inherited `_float` parsing.

R2 repairs only that contract surface. It freezes an exhaustive response/key/action/policy/membership/rational/metadata schema, makes base max_nodes/max_depth mandatory only for the new operation and equal to abstraction bounds, preserves prior operation defaults, preserves non-bool integer weights before Fraction conversion, fixes digest canonicalization, and expands I4 RED cases. No production, tests, scripts, dependency, mission, or accepted Git bytes changed.

## Verification receipts

- `git diff --check`: PASS after R2 edit.
- `git diff --name-only -- src tests scripts pyproject.toml`: empty.
- accepted HEAD: exact match.
- annotated tag object and peeled commit: exact matches above.
- latest parent full regression on unchanged production/tests: `817 passed`.
- original A4D6 independent full regression on unchanged production/tests: `817 passed in 391.38s (0:06:31)`.
- R2 is still DESIGN only; missing S4 implementation/tests is expected and is not a finding.

## Auditor rules

Audit the literal candidate paths and hashes above. Do not substitute root `ARCHITECTURE.md`, root `MISSION.md`, or guessed audit-local filenames. Recompute every hash. Production/tests and this manifest are immutable during the wave. Each auditor owns only its assigned report and flat completed heartbeat under `research/phase4/s4-design-audit-r2/`. A pass label without substantive source/design evidence is insufficient. Missing future S4 code is expected. No auditor may edit candidate/source/tests, commit, or create a nested repository.
