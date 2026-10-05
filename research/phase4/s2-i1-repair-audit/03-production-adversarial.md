# S2-I1 repaired production adversarial coverage — parent schema fallback

Fresh A203 and its single replacement both ended with schema-class HTTP 502 before completing review or creating artifacts. No further retry was made under the one-retry rule. This document is parent fallback evidence, not a fresh non-author report.

At 2026-09-15T23:02:36Z parent verified the five repaired candidate hashes and ran all 46 focused tests. Parent also executed a separate 12-check adversarial script covering:
- defensive copy and immutable showdown mapping;
- frozen config and state objects;
- invalid and duplicate board-card rejection;
- direct corrupt-pot rejection;
- out-of-range actor rejection in state history;
- illegal FOLD rejection while CHECK is available;
- actor-labelled history;
- opponent-card noninterference and owner-card distinction;
- exact terminal settlement `(12, -6, -6)` with utility/rake conservation.

Result: `PARENT_A203_PROBES=12/12` and focused `46 passed`. This closes the missing surface operationally; fresh non-author acceptance still depends on the surviving A201/A202/A204/A205/A206 scopes.
