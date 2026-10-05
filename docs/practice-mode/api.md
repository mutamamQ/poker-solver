# Practice mode API (v4 `practice-*` operations)

Every example below was captured from a real call against
`python -m poker_solver.practice.server --port 7794` at commit `5a3e61f`. Each run
used a temporary `POKER_PRACTICE_CACHE_DIR` / `POKER_PRACTICE_DATA_DIR`. Numbers are solver
output from that run. They change with iterations, catalog seed and solver version, so
don't treat them as reference answers. Long arrays and the repeated `provenance.params` /
`solved` objects are shortened, and every shortening is marked with `<...>` or `"..."`.

Source of truth for the schemas: `src/poker_solver/practice/api.py` (validation),
`models.py` (`PracticeSpot.to_json`, `SolvedSpot.to_json`, `SolveProvenance`), `scoring.py`
(`PlayScore.to_json`) and `progress.py`.

## Transport

- HTTP: `POST /api/v4` with body `{"version": 4, "operation": <op>, "payload": {...}}`.
  `version` must be the JSON integer 4. `GET /api/health` returns `{"ok":true}`.
- In process: `poker_solver.api_v4.dispatch_v4(envelope)`, or
  `poker_solver.practice.api.handle_practice(op, payload)`.
- Response envelope: `{"version": 4, "operation": op, "result": ..., "provenance": ...}`.
  `provenance` is the solve provenance for solve/submit and `null` for list/progress/leaderboard.
- Validation fails closed. Unknown or missing payload keys and wrong types raise an error
  (`true` is not an integer). The server answers `400 {"error": "<message>"}`.

Example call:

```bash
curl -sS -X POST -H 'Content-Type: application/json' \
  --data '{"version":4,"operation":"practice-list-spots","payload":{"families":["river-oop-bet-or-check"],"limit":1}}' \
  http://127.0.0.1:7794/api/v4
```

## Common payload fields

| field | type | used by | meaning |
|---|---|---|---|
| `families` | non-empty list of distinct family names | list, solve, submit | catalog subset; unknown names are rejected |
| `seed` | int (default 0) | list, solve, submit | catalog seed; `spot_id`s are only valid for the seed that generated them |
| `limit` | int >= 1 | list | truncate the catalog |
| `spot_id` | string | solve, submit, progress | e.g. `river-oop-bet-or-check/e79981f9d62d` |
| `solve` | `{algorithm?, iterations?, seed?}` | solve, submit | overrides the family default solve. `algorithm` is `vanilla-cfr` (seed must be null) or `external-sampling-mccfr` (int seed). `iterations` is 1..20000. Omitted fields take the `SolveParams` defaults (vanilla-cfr, 200, null), not the family default. Only the `allstreet` backend (`flop-cbet`) accepts MCCFR; the other backends answer `400 backend <b> supports only vanilla-cfr` |
| `user` | string matching `^[A-Za-z0-9_.-]{1,32}$` (default `local`) | submit, progress | progress owner |

`spot_id` is `family + "/" + 12 hex chars`. It does not depend on solve params. `params_hash` is the
sha256 of the full canonical spot including solve params, and it keys the solve cache.

Families at `5a3e61f`, 72 spots at seed 0, verified with `api list`:

| family | backend | game_type | street | spots | default solve |
|---|---|---|---|---|---|
| `kuhn-intro` | kuhn | heads-up | preflop (Kuhn) | 12 | vanilla-cfr 200 |
| `river-oop-bet-or-check` | river | heads-up | river | 12 | vanilla-cfr 200 |
| `river-ip-facing-bet` | river | heads-up | river | 12 | vanilla-cfr 200 |
| `preflop-hu-open` | nplayer-preflop | heads-up | preflop | 12 | vanilla-cfr 300 |
| `preflop-3max-open` | nplayer-preflop | 3-max | preflop | 8 | vanilla-cfr 100 |
| `flop-cbet` | allstreet | heads-up | flop | 8 | vanilla-cfr 200 |
| `turn-barrel` | multistreet | heads-up | turn | 8 | vanilla-cfr 200 |

The default-solve column comes from `catalog.FAMILY_DEFAULT_SOLVE` and may change; read it from
each spot's `solve` field.

## practice-list-spots

Payload `{families?, seed?, limit?}`. Result `{spots: [PracticeSpot JSON], families: [...]}`. Provenance `null`.

Request:

```json
{
  "version": 4,
  "operation": "practice-list-spots",
  "payload": {
    "families": [
      "river-oop-bet-or-check"
    ],
    "limit": 1
  }
}
```

Response:

```json
{
  "version": 4,
  "operation": "practice-list-spots",
  "result": {
    "spots": [
      {
        "format": "practice-spot-v1",
        "family": "river-oop-bet-or-check",
        "backend": "river",
        "game_type": "heads-up",
        "street": "river",
        "board": [
          13,
          7,
          30,
          3,
          8
        ],
        "hero_seat": 0,
        "villain_seats": [
          1
        ],
        "ranges": [
          [
            {
              "cards": [
                17,
                21
              ],
              "weight": 1.0
            },
            {
              "cards": [
                44,
                47
              ],
              "weight": 1.0
            },
            {
              "cards": [
                47,
                51
              ],
              "weight": 1.0
            },
            {
              "cards": [
                48,
                49
              ],
              "weight": 1.0
            }
          ],
          [
            {
              "cards": [
                28,
                31
              ],
              "weight": 1.0
            },
            {
              "cards": [
                32,
                35
              ],
              "weight": 1.0
            },
            {
              "cards": [
                37,
                39
              ],
              "weight": 1.0
            },
            {
              "cards": [
                40,
                43
              ],
              "weight": 1.0
            }
          ]
        ],
        "pot": 100.0,
        "stacks": [
          200,
          200
        ],
        "action_history": [],
        "bet_sizes": [
          33
        ],
        "hero_hand": [
          17,
          21
        ],
        "solve": {
          "algorithm": "vanilla-cfr",
          "iterations": 200,
          "seed": null
        },
        "backend_extra": {
          "bet_pct": 33,
          "spr": 2,
          "range_shape": "polar-vs-catchers",
          "cell_seed": 45988307107695
        },
        "spot_id": "river-oop-bet-or-check/e79981f9d62d",
        "params_hash": "6741d37fded10f9fa8da8cc6ac8ae0e92d8522f3b0debae9c29afe740d309ab9",
        "board_str": [
          "5d",
          "3s",
          "9h",
          "2s",
          "4c"
        ],
        "hero_hand_str": [
          "6d",
          "7d"
        ],
        "label": "River OOP with 6d7d on 5d 3s 9h 2s 4c; pot 100, stack 200, bet 33; line: first to act"
      }
    ],
    "families": [
      "river-oop-bet-or-check"
    ]
  },
  "provenance": null
}
```

Cards are integers 0..51 in `board`, `ranges[].cards` and `hero_hand`, with display strings in
`board_str` / `hero_hand_str`. `ranges` has one list per seat. For Kuhn, `ranges` is empty and
`hero_hand` is `null`; the card is in `backend_extra.kuhn_card` / `hero_hand_str`. For 3-max,
`villain_seats` has 2 entries and `stacks` has 3.

## practice-solve-spot

Payload `{spot_id, families?, seed?, solve?}`. Result: `SolvedSpot` JSON with keys `spot, provenance,
legal_actions, pot_at_decision, strategy, action_values, range_strategy, optimal_action,
optimal_size`. The top-level `provenance` equals `result.provenance`.

Request (40 iterations override):

```json
{
  "version": 4,
  "operation": "practice-solve-spot",
  "payload": {
    "spot_id": "river-oop-bet-or-check/e79981f9d62d",
    "solve": {
      "iterations": 40
    }
  }
}
```

Response (shortened):

```json
{
  "version": 4,
  "operation": "practice-solve-spot",
  "result": {
    "spot": {
      "spot_id": "river-oop-bet-or-check/e79981f9d62d",
      "family": "river-oop-bet-or-check",
      "label": "River OOP with 6d7d on 5d 3s 9h 2s 4c; pot 100, stack 200, bet 33; line: first to act",
      "pot": 100.0,
      "bet_sizes": [
        33
      ],
      "solve": {
        "algorithm": "vanilla-cfr",
        "iterations": 40,
        "seed": null
      },
      "params_hash": "4a759acbb6c2b99bab36c716a24991c45f1a37c1fc34bf5b1edef2d778b26521",
      "...": "(full spot object, same shape as practice-list-spots)"
    },
    "provenance": {
      "backend": "river",
      "entrypoint": "poker_solver.river.river_root+cfr.CFRSolver.train",
      "params": "<full canonical spot params, same as result.spot minus spot_id/params_hash/board_str/hero_hand_str/label>",
      "params_hash": "4a759acbb6c2b99bab36c716a24991c45f1a37c1fc34bf5b1edef2d778b26521",
      "algorithm": "vanilla-cfr",
      "iterations": 40,
      "seed": null,
      "nash_conv": 2.0196770988328083,
      "wall_time_s": 2.186929998919368,
      "solver_version": "0.1.0"
    },
    "legal_actions": [
      {
        "kind": "check",
        "amount": 0
      },
      {
        "kind": "bet",
        "amount": 33
      }
    ],
    "pot_at_decision": 100.0,
    "strategy": [
      {
        "action": {
          "kind": "check",
          "amount": 0
        },
        "probability": 0.269429232787546
      },
      {
        "action": {
          "kind": "bet",
          "amount": 33
        },
        "probability": 0.730570767212454
      }
    ],
    "action_values": [
      {
        "action": {
          "kind": "check",
          "amount": 0
        },
        "q": 52.65816908900063
      },
      {
        "action": {
          "kind": "bet",
          "amount": 33
        },
        "q": 56.73291068554683
      }
    ],
    "range_strategy": [
      {
        "hand": "6d7d",
        "strategy": [
          {
            "action": {
              "kind": "check",
              "amount": 0
            },
            "probability": 0.269429232787546
          },
          {
            "action": {
              "kind": "bet",
              "amount": 33
            },
            "probability": 0.730570767212454
          }
        ]
      },
      {
        "hand": "KcKs",
        "strategy": [
          {
            "action": {
              "kind": "check",
              "amount": 0
            },
            "probability": 0.43796621572973526
          },
          {
            "action": {
              "kind": "bet",
              "amount": 33
            },
            "probability": 0.5620337842702647
          }
        ]
      },
      "... one entry per hero-range combo"
    ],
    "optimal_action": {
      "kind": "bet",
      "amount": 33
    },
    "optimal_size": 33
  },
  "provenance": "<same object as result.provenance>"
}
```

Field meanings:
- `strategy`: the solver's average-strategy mix for the dealt hero hand at the decision infoset.
- `action_values[].q`: Q(a) in chips from the hero's view. It is the expected payoff of taking `a`, with
  everyone then following the solved profile (`evaluate.py`).
- `range_strategy`: the same infoset's strategy for every combo in the hero range (the UI grid).
- `optimal_action`: argmax Q. `optimal_size` is its amount, or `null` for non-wagers.
- `provenance.nash_conv`: NashConv of the solved profile when the backend exposes it. It is
  `null` for `preflop-3max-open`.
- Repeating the same request (same `params_hash`) returns the cached solve. In the capture, a
  repeat `flop-cbet` solve took 0.04 s against 8.8 s cold.

3-max example (`preflop-3max-open/a4b66447a35b`, family default 100 iterations, 16.3 s cold on a
loaded 2-CPU host):

```json
{
  "spot": {
    "spot_id": "preflop-3max-open/a4b66447a35b",
    "game_type": "3-max",
    "hero_seat": 0,
    "villain_seats": [
      1,
      2
    ],
    "stacks": [
      40,
      40,
      40
    ],
    "label": "Preflop 3-max BTN with KhKs; blinds 1/2, stack 40, open to 5; line: first to act"
  },
  "legal_actions": [
    {
      "kind": "FOLD",
      "amount": 0
    },
    {
      "kind": "CALL",
      "amount": 2
    },
    {
      "kind": "RAISE",
      "amount": 5
    },
    {
      "kind": "RAISE",
      "amount": 40
    }
  ],
  "strategy": [
    {
      "action": {
        "kind": "FOLD",
        "amount": 0
      },
      "probability": 0.0024999999999999974
    },
    {
      "action": {
        "kind": "CALL",
        "amount": 2
      },
      "probability": 0.0602750179505771
    },
    {
      "action": {
        "kind": "RAISE",
        "amount": 5
      },
      "probability": 0.4822580883564667
    },
    {
      "action": {
        "kind": "RAISE",
        "amount": 40
      },
      "probability": 0.4549668936929561
    }
  ],
  "action_values": [
    {
      "action": {
        "kind": "FOLD",
        "amount": 0
      },
      "q": 0.0
    },
    {
      "action": {
        "kind": "CALL",
        "amount": 2
      },
      "q": 2.8584751749985364
    },
    {
      "action": {
        "kind": "RAISE",
        "amount": 5
      },
      "q": 4.065214176841489
    },
    {
      "action": {
        "kind": "RAISE",
        "amount": 40
      },
      "q": 3.816903557048693
    }
  ],
  "optimal_action": {
    "kind": "RAISE",
    "amount": 5
  },
  "provenance": {
    "backend": "nplayer-preflop",
    "entrypoint": "poker_solver.nplayer_preflop.create_nplayer_preflop_root+nplayer.NPlayerCFRSolver.train (terminal-table: evaluator.evaluate_seven sampled equity)",
    "iterations": 100,
    "nash_conv": null,
    "wall_time_s": 16.216639581136405
  }
}
```

Amounts: river/Kuhn use `bet`/`check`/`call`/`fold` with a bet amount in chips. Kuhn's bet has amount
0. Allstreet/multistreet/preflop use upper-case kinds (`CHECK`, `CALL`, `FOLD`, `RAISE`) where the
`RAISE` amount is a raise-to target. Always build plays from `legal_actions`.

## practice-submit-play

Payload `{spot_id, play, families?, seed?, solve?, user?}`. `play` is either
- a pure action `{"kind": k, "amount"?: n}` (kind must match a legal kind exactly, case included), or
- a mix `{"mix": [{"action": {"kind", "amount"}, "probability": p}, ...]}` whose probabilities sum to 1.

A wager amount that is not in the solved menu is snapped to the nearest solved size (ties go to the
smaller size) and reported in `mapped_action` / `size_mapped` / `mappings`. An EV is never invented
for an unsolved size.

Result `{user, score, solved, progress}`. `progress` is the per-spot entry after recording, or `null`
if the store failed. A store failure never fails the submit.

Request:

```json
{
  "version": 4,
  "operation": "practice-submit-play",
  "payload": {
    "spot_id": "river-oop-bet-or-check/e79981f9d62d",
    "play": {
      "kind": "check"
    },
    "solve": {
      "iterations": 40
    },
    "user": "alice"
  }
}
```

Response (shortened):

```json
{
  "version": 4,
  "operation": "practice-submit-play",
  "result": {
    "user": "alice",
    "score": {
      "ev_loss_chips": 4.074741596546197,
      "ev_loss_pct_pot": 4.074741596546197,
      "score": 0.0,
      "grade": "Mistake",
      "chosen_q": 52.65816908900063,
      "best_q": 56.73291068554683,
      "worst_q": 52.65816908900063,
      "solver_mix_q": 55.635056183381884,
      "solver_self_loss": 1.0978545021649424,
      "best_action": {
        "kind": "bet",
        "amount": 33
      },
      "feedback": "Solver: bet[33] 73.1%, check 26.9%. You: check. EV loss 4.075 chips (4.07% pot) -> Mistake. Best EV action: bet[33] (Q=+56.733). Solver noise: 1.098 chips.",
      "mapped_action": null,
      "size_mapped": false,
      "play": {
        "kind": "check",
        "amount": 0
      },
      "mappings": [],
      "provenance": "<same as top-level provenance>"
    },
    "solved": "<full practice-solve-spot result object>",
    "progress": {
      "spot_id": "river-oop-bet-or-check/e79981f9d62d",
      "family": "river-oop-bet-or-check",
      "street": "river",
      "game_type": "heads-up",
      "attempts": 1,
      "best_score": 0.0,
      "last_score": 0.0,
      "last_grade": "Mistake",
      "first_at": "2026-10-05T06:09:52.699815Z",
      "last_at": "2026-10-05T06:09:52.699815Z"
    }
  },
  "provenance": {
    "backend": "river",
    "entrypoint": "poker_solver.river.river_root+cfr.CFRSolver.train",
    "params": "<full canonical spot params, same as result.spot minus spot_id/params_hash/board_str/hero_hand_str/label>",
    "params_hash": "4a759acbb6c2b99bab36c716a24991c45f1a37c1fc34bf5b1edef2d778b26521",
    "algorithm": "vanilla-cfr",
    "iterations": 40,
    "seed": null,
    "nash_conv": 2.0196770988328083,
    "wall_time_s": 2.186929998919368,
    "solver_version": "0.1.0"
  }
}
```

Off-menu size `{"kind":"bet","amount":50}` on the same spot (menu is `[33]`), selected `score` fields:

```json
{
  "ev_loss_chips": 0.0,
  "score": 100.0,
  "grade": "Perfect",
  "mapped_action": {
    "kind": "bet",
    "amount": 33
  },
  "size_mapped": true,
  "play": {
    "kind": "bet",
    "amount": 33
  },
  "mappings": [
    {
      "requested": {
        "kind": "bet",
        "amount": 50
      },
      "mapped": {
        "kind": "bet",
        "amount": 33
      }
    }
  ],
  "feedback": "Solver: bet[33] 73.1%, check 26.9%. You: bet[33] (mapped from bet[50] -> bet[33]). EV loss 0.000 chips (0.00% pot) -> Perfect. Best EV action: bet[33] (Q=+56.733); most-weighted alternative: check (Q=+52.658). Solver noise: 1.098 chips."
}
```

Mixed play (30 % check / 70 % bet 33), selected `score` fields:

```json
{
  "chosen_q": 55.51048820658296,
  "ev_loss_chips": 1.222422478963864,
  "score": 69.99999999999989,
  "grade": "Inaccuracy",
  "play": {
    "mix": [
      {
        "action": {
          "kind": "check",
          "amount": 0
        },
        "probability": 0.3
      },
      {
        "action": {
          "kind": "bet",
          "amount": 33
        },
        "probability": 0.7
      }
    ]
  },
  "feedback": "Solver: bet[33] 73.1%, check 26.9%. You: check 30.0%, bet[33] 70.0%. EV loss 1.222 chips (1.22% pot) -> Inaccuracy. Best EV action: bet[33] (Q=+56.733); most-weighted alternative: check (Q=+52.658). Solver noise: 1.098 chips."
}
```

Scoring (`scoring.py`, design §5):
- `ev_loss_chips = max(0, best_q - chosen_q)`, where `chosen_q = sum_a play(a) * Q(a)`.
- `ev_loss_pct_pot = 100 * ev_loss_chips / pot_at_decision`.
- `score = 100 * max(0, 1 - ev_loss / (best_q - worst_q))`, or 100 if all Q are equal (spread <= 1e-12).
  Because the scale is relative to the Q spread, a pure play of the worst action scores 0 even when
  the chip loss is small.
- `grade` by `ev_loss_pct_pot`: <= 0.25 Perfect, <= 1 Good, <= 3 Inaccuracy, <= 8 Mistake, else Blunder.
- `solver_self_loss = best_q - solver_mix_q` measures solver noise. It is 0 at an exact equilibrium
  and is large at low iterations (1.10 chips here at 40 iterations).

## practice-progress

Payload `{user?, spot_id?}`. Result `{user, totals: {attempts, spots_attempted, avg_best_score,
avg_last_score}, spots: [...]}`. Timestamps are ISO-8601 UTC. Averages are `null` when the user has no
attempts. Provenance `null`.

```json
{
  "version": 4,
  "operation": "practice-progress",
  "payload": {
    "user": "alice"
  }
}
```

```json
{
  "version": 4,
  "operation": "practice-progress",
  "result": {
    "user": "alice",
    "totals": {
      "attempts": 3,
      "spots_attempted": 2,
      "avg_best_score": 50.0,
      "avg_last_score": 50.0
    },
    "spots": [
      {
        "spot_id": "kuhn-intro/820b58289136",
        "family": "kuhn-intro",
        "street": "preflop",
        "game_type": "heads-up",
        "attempts": 1,
        "best_score": 0.0,
        "last_score": 0.0,
        "last_grade": "Mistake",
        "first_at": "2026-10-05T06:09:20.951829Z",
        "last_at": "2026-10-05T06:09:20.951829Z"
      },
      {
        "spot_id": "river-oop-bet-or-check/e79981f9d62d",
        "family": "river-oop-bet-or-check",
        "street": "river",
        "game_type": "heads-up",
        "attempts": 2,
        "best_score": 100.0,
        "last_score": 100.0,
        "last_grade": "Perfect",
        "first_at": "2026-10-05T06:09:52.699815Z",
        "last_at": "2026-10-05T06:09:52.761018Z"
      }
    ]
  },
  "provenance": null
}
```

Filtered to one spot:

```json
{
  "version": 4,
  "operation": "practice-progress",
  "payload": {
    "user": "alice",
    "spot_id": "kuhn-intro/820b58289136"
  }
}
```

```json
{
  "version": 4,
  "operation": "practice-progress",
  "result": {
    "user": "alice",
    "totals": {
      "attempts": 1,
      "spots_attempted": 1,
      "avg_best_score": 0.0,
      "avg_last_score": 0.0
    },
    "spots": [
      {
        "spot_id": "kuhn-intro/820b58289136",
        "family": "kuhn-intro",
        "street": "preflop",
        "game_type": "heads-up",
        "attempts": 1,
        "best_score": 0.0,
        "last_score": 0.0,
        "last_grade": "Mistake",
        "first_at": "2026-10-05T06:09:20.951829Z",
        "last_at": "2026-10-05T06:09:20.951829Z"
      }
    ]
  },
  "provenance": null
}
```

## practice-leaderboard

Payload `{limit?: 1..100 = 20, family?}`. Result `{entries: [{rank, user, spots_attempted, attempts,
avg_best_score, total_best_score}]}`. The ranking orders by `total_best_score` desc, then
`avg_best_score` desc, then `user` asc. Ranks are positional, so full ties still get distinct ranks.
Provenance `null`.

```json
{
  "version": 4,
  "operation": "practice-leaderboard",
  "payload": {
    "limit": 5
  }
}
```

```json
{
  "version": 4,
  "operation": "practice-leaderboard",
  "result": {
    "entries": [
      {
        "rank": 1,
        "user": "bob",
        "spots_attempted": 1,
        "attempts": 1,
        "avg_best_score": 100.0,
        "total_best_score": 100.0
      },
      {
        "rank": 2,
        "user": "alice",
        "spots_attempted": 2,
        "attempts": 3,
        "avg_best_score": 50.0,
        "total_best_score": 100.0
      },
      {
        "rank": 3,
        "user": "local",
        "spots_attempted": 1,
        "attempts": 1,
        "avg_best_score": 69.99999999999989,
        "total_best_score": 69.99999999999989
      }
    ]
  },
  "provenance": null
}
```

With `{"family": "kuhn-intro"}` (best per user/spot within that family only):

```json
{
  "version": 4,
  "operation": "practice-leaderboard",
  "result": {
    "entries": [
      {
        "rank": 1,
        "user": "bob",
        "spots_attempted": 1,
        "attempts": 1,
        "avg_best_score": 100.0,
        "total_best_score": 100.0
      },
      {
        "rank": 2,
        "user": "alice",
        "spots_attempted": 1,
        "attempts": 1,
        "avg_best_score": 0.0,
        "total_best_score": 0.0
      }
    ]
  },
  "provenance": null
}
```

## Errors (captured)

| request | HTTP | body |
|---|---|---|
| `practice-solve-spot {"spot_id":"nope/123"}` | 400 | `{"error":"unknown spot_id 'nope/123' for seed 0"}` |
| `practice-progress {"user":"bad user!"}` | 400 | `{"error":"user must match ^[A-Za-z0-9_.-]{1,32}$"}` |
| `practice-list-spots {"bogus":1}` | 400 | `{"error":"practice-list-spots payload has unknown fields: ['bogus']"}` |
| submit `{"kind":"CHECK"}` on a river spot | 400 | `{"error":"play: action kind 'CHECK' is not legal here (legal: ['check', 'bet[33]'])"}` |
| `GET /api/v4` | 405 | `{"error":"method not allowed"}` |
| body `{"a":1,"a":2}` | 400 | `{"error":"malformed JSON: duplicate JSON key: 'a'"}` |
| unknown path `GET /nope` | 404 | `{"error":"not found"}` |
| solve over `POKER_PRACTICE_TIMEOUT` (tested with 1 s on the 3-max spot) | 504 | `{"error":"solve timed out"}` |

The server also returns 413 for bodies over 1 MiB, and 400 for a missing or invalid Content-Length, NaN/Infinity
or excessive nesting. See `server.py`.
