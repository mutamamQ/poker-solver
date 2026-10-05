# S3 refrozen design — final parent acceptance

- accepted at: `2026-09-16T03:45:04Z`
- candidate: `/home/genomix-node/poker-solver/ARCHITECTURE_PHASE4_S3.md`
- architecture SHA-256: `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`
- accepted base HEAD: `4b3f87f4e6cf38e9dc88aca744b23de2c44c08fe`
- preserved tag: `phase3-398-green` -> `feba8222a0b614b0c64eca59402403ce733195ea`
- live delegated owners at acceptance: `0`
- verdict: `PASS`

## Accepted six-scope evidence

| scope | owner | report | report SHA-256 | heartbeat | canonical transcript |
|---|---|---|---|---|---|
| model / ledger / deals / positions | A3Q1 | `01-model-ledger-deals.md` | `b71c7735ce001a89853d40b70fcba35dc1cebb5d430965e0b28275ffb9823ee6` | `.hb/A3Q1` | `/home/genomix-node/.hermes/cache/delegation/live/deleg_408ab5d3/task-0.log` |
| betting / reopening | A3Q2 | `02-betting-reopening.md` | `0fd336edc3bff7cd65e375de392d6d6bd0516cd6046d9ae331556f8031ecf0d5` | `.hb/A3Q2` | `/home/genomix-node/.hermes/cache/delegation/live/deleg_734da2eb/task-0.log` |
| straddles / order | A3M3 | `03-straddles-order.md` | `27562630ab3dcf89aea3b00144e0ae385471d53d6f8ea7905269fc4cceb00aca` | `.hb/A3M3` | `/home/genomix-node/.hermes/cache/delegation/live/deleg_abe8000c/task-1.log` |
| settlement / information | A3L4 | `04-settlement-information.md` | `685b84494732634f3dabb5c77eb983c98f1765746f2b0a73e6f590210e49fa52` | `.hb/A3L4` | `/home/genomix-node/.hermes/cache/delegation/live/deleg_229a5354/task-0.log` |
| solver / API / TDD | A3J5 | `05-solver-api-tdd.md` | `5ed1ca6cdfca267de0795c0af094f1733ddfec953b3907a0cc5cf0dbb1735a3c` | `.hb/A3J5` | `/home/genomix-node/.hermes/cache/delegation/live/deleg_bdc1e7f8/task-4.log` |
| cross-release | A3K6 | `06-cross-release.md` | `ac1f102fddc1c98fd802b819ad6276fdf178645163301e964c19454a57f3533a` | `.hb/A3K6` | `/home/genomix-node/.hermes/cache/delegation/live/deleg_d3ee397e/task-3.log` |

The accepted heartbeat directory contains exactly these six owner files and no superseded heartbeat.

## Parent executable checks

- Canonical position oracle: PASS for N=3..9 with `SB=(b+1)%N`, `BB=(b+2)%N`, operational `UTG=(b+3)%N`, and `UTG+1=(b+4)%N`.
- Exact forced-post ledger oracle: PASS, including N=6 uniform ante 5, SB 10, BB 20, pot 60.
- Mandatory legal short-all-in oracle: PASS with absolute `(SB0,BB1,CO2,BTN3)` vectors; before BB acts `pending=(1)`, `can_raise=[F,T,F,F]`; after raise `pending=(2,3,0)`; no-reopen `[F,F,F,F]`; reopen `[T,F,T,T]`.
- Uniform-ante refund enumeration: PASS for N=2..9 and enumerated ante/street values 0..3.
- Report/heartbeat/transcript index: exactly 6/6/6, each report contains the frozen architecture hash and PASS, each retained heartbeat contains PASS, and each canonical transcript reached a final record.
- `git diff --check`: PASS.
- Full regression: `653 passed in 214.05s` from `uv run pytest`.

## Decision

The S3 design gate is accepted. Rejected candidate `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9` remains rejected. Implementation may begin only through §12's four exclusive production-importing RED owners, followed by parent verification before production ownership.
