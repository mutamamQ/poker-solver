# S4 architecture design-audit candidate manifest

Status: FROZEN
Candidate base directory: `/home/genomix-node/poker-solver`
Accepted base HEAD: `149780bf37e3e3a824e03e6d2c1df3cd99b12cd6`
Preserved historical tag: `phase3-398-green` -> `feba8222a0b614b0c64eca59402403ce733195ea`
Candidate architecture SHA-256: `4285905100a11e3523b241f236233118bb9f4dac67f7c8aa92570fba3048a0e3`
Authoritative authenticated design input SHA-256: `79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d`
Mission SHA-256: `5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61`

Literal SHA-256 rows, resolved from the declared candidate base:

4285905100a11e3523b241f236233118bb9f4dac67f7c8aa92570fba3048a0e3  ARCHITECTURE_PHASE4_S4.md
79c68494efca8453b96440a2b9af0fb90276b33589a89a1e5207fee55e1c9d7d  research/phase4/s4-design/02-engine-integration-codex.md
5720bd0f4a6d1b2a224f3205d09ddc94500d0bae928cfa4cca52f13fd1367b61  PHASE4_MISSION.md

Audit contract:

- This is a DESIGN checkpoint. No S4 production or S4 tests exist yet; their absence is expected and is not a blocker.
- Review specification completeness, internal consistency, mathematical validity, feasibility against accepted source, physical-state reduction, executable future gates, API truthfulness, TDD sequencing, and release boundaries.
- The architecture is authoritative. Raw design reports are evidence only.
- Do not edit the candidate, source, tests, this manifest, STATE.txt, PROGRESS.md, or Git.
- Each reviewer owns only its assigned report and one flat heartbeat in this audit directory.
- Every claimed source fact, equation, fixture count, and API symbol must be checked rather than copied.

Parent freeze receipts:

- exact small fixture: 321 nodes, 136 terminals, 57 chance, 128 decisions, depth 12;
- exact small 1,000-iteration NashConv: `0.0007291666666667806`;
- large support: 66 x 66, 4,356 compatible worlds;
- bucket sizes: P0 `[66]`, P1 `[11,55]`;
- single-world stats: 81 nodes, 34 terminals, 15 chance, 32 decisions, depth 12;
- analytic exact/reduced physical counts: 348,481 / 161;
- signature slots and literal belief entries: 17,424 / 17,424;
- `git diff --check`: PASS;
- no production/test design edits: PASS;
- full pre-S4 regression: `817 passed in 389.11s (0:06:29)`.
