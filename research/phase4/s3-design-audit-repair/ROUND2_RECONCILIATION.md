# S3 repaired-design audit round 2 reconciliation

Audited candidate: `f0777689eac5df76ab7630dd3725e40f7409e4369ba9de312ac8992a4a4bb83f`.

Verdict: rejected and superseded by parent repair.

Evidence adjudication:

- A3X2 read the right candidate but its PASS was invalid: its no-reopen trace used a union rather than the specified old-pending/old-entitlement intersection, allowed prior callers to re-raise, and later allowed the aggressor to raise again without an intervening raise. It also treated an SB completion as zero cold callers.
- A3X3 read the right candidate but silently truncated a declared straddle despite exact-post validation, placed an all-in straddler in `pending`, and accepted equal live straddles without testing whether the later post established a new wager.
- A3X4 found the decisive ledger counterexample: a permitted unequal or single-seat ante can make `refund_uncalled_excess(total_contributed)` exceed the leader's `street_committed`. Calling terminal failure for an otherwise accepted config a PASS was rejected.
- A3X5 failed before tool execution with `HTTP 502: Model did not return valid tool/structured JSON; no tools executed`.
- A3Y5 was the one provider retry. It correctly verified solver/API/TDD feasibility, but its candidate was subsequently superseded by ledger/betting repairs.
- A3X6 hashed the manifest file itself and compared that digest with the manifest's declared candidate digest. It did not audit the architecture and is rejected.

Parent corrections in the new candidate:

1. Antes are absent or exactly one equal amount per seat; unequal, partial, and single-seat big-blind ante forms are rejected until a separate common-pot ledger exists.
2. Every forced post transfers exactly; straddles strictly increase the live wager; all-in post seats are excluded from `pending` and have no option.
3. SB completion counts as a pre-raise CALL for `cold_callers`.
4. CHECK/CALL consumes raise entitlement; no-reopen short-all-in eligibility is the intersection of old pending and old entitlement.
5. Refund boundedness is guaranteed by validation and the identity `total[i] = uniform_ante + street[i]`.

Parent executable proof exhaustively checked N=2..9, uniform ante 0..3, and every street vector with entries 0..3: every unique-leader total refund is bounded by that leader's street commitment. The unequal-ante counterexample `(total=(0,50,190), street=(0,50,100))` produces refund 140 > street 100 and is now rejected at config validation.
