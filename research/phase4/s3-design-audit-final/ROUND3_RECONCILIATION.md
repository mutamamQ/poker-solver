# S3 third-candidate reconciliation

- rejected candidate SHA-256: `ac14b51c8271fe498c34c279e80792fe8d42f83266e3fac96caa17095216d5b9`
- replacement candidate SHA-256: `a4dd4f914addda7c28b512dc4949bd52a5c25e1eaee312fec13d61d72c5152d6`
- accepted base HEAD remains `4b3f87f4e6cf38e9dc88aca744b23de2c44c08fe`
- historical baseline remains `phase3-398-green` -> `feba8222a0b614b0c64eca59402403ce733195ea`

The `ac14b51c...` candidate is rejected despite several PASS labels. Parent verification found that its canonical display labels omit UTG for N=3/4/5 while its straddle section permits standard UTG at N>=3 and double UTG/UTG+1 at N>=4. A3H3 amplified the contradiction by saying UTG does not exist at N=3 while accepting standard at N=3, and by assuming UTG=CO at N=4 without a candidate definition.

The replacement explicitly derives operational UTG and UTG+1 aliases from BB for low-handed tables and lists their exact N=3 through N=8 mappings. No other candidate claim changed.

Evidence disposition:

- A3H3 correctly rejected HU Mississippi and N=3 double but its final PASS is rejected for the alias contradiction.
- A3H6's corrected uniform-ante refund algebra is valid but cannot release a rejected candidate.
- A3H2 failed to write its corrected legal short-all-in report or heartbeat; old A3G2 evidence remains rejected.
- A3H5 wrote a report but no required regular heartbeat and audited the rejected hash; it is not release evidence.
- Every report and heartbeat under `s3-design-audit-final/` is historical evidence only.

The replacement candidate requires a wholly fresh six-role design audit in `s3-design-audit-refrozen/`. No old PASS is carried forward.
