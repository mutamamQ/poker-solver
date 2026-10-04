# 01 — Scorer / EV-loss metric (design report)

Scope: `practice/evaluate.py` (Q computation) and `practice/scorer.py` (`score_play`). Refines
PRACTICE_MODE_DESIGN.md §5. It does not override §5. Proposed changes are marked **[PARENT DECISION]**.
Verified against `model.py`, `cfr.py`, `best_response.py`, `kuhn.py` and `river.py` on `feat/practice-mode`.

## 1. Protocol facts used (from the source)
- `GameState`: `current_player() -> int` (`CHANCE=-1`, `TERMINAL=-2`), `legal_actions()`,
  `chance_outcomes() -> ((Action, p), ...)`, `child(action)`, `information_state_key(player)`
  (raises if `player` is not the one acting), `returns() -> (u0, u1)` (only at a terminal).
- `CFRSolver(root).train(n)` returns the average profile `dict[InfoKey, dict[Action, float]]`.
  `expected_values(root, profile)` returns `(v0, v1)`. `nash_conv(root, profile)` returns
  `NashConvResult(values, best_response_values, incentives, nash_conv)`.
- Opponent hands are dealt by root chance nodes. In `river.py` the deal probabilities are already
  `w0*w1/Z` over board- and card-compatible pairs. So "range weight x opponent reach" is just
  chance probability x opponent sigma* reach. The walk never reads range weights directly, which
  keeps it backend-agnostic.

## 2. Math definition
Notation: hero `i`, target infoset `I` (found by the adapter's tree walk over `action_history` +
`hero_hand`, per §3), profile sigma*.
For each history `h` in `I`: `w(h) = pi_c(h) * pi_{-i}^{sigma*}(h)`, i.e. the chance reach times the
opponent reach. **Hero's own reach is excluded** (counterfactual weighting).
`v(z)` is the sigma*-value of the subtree at `z` for hero (every player follows sigma*, chance
follows its probabilities).

    M(I)   = sum_{h in I} w(h)                       (counterfactual reach mass)
    Q(a)   = sum_{h in I} w(h) * v(child(h, a)) / M(I)        for a in A(I)
    best_q = max_a Q(a);   worst_q = min_a Q(a);   spread = best_q - worst_q
    solver_mix_q     = sum_a sigma*(I)(a) * Q(a)
    solver_self_loss = best_q - solver_mix_q   (>= 0 up to float error)
    chosen_q = sum_a pi_u(a) * Q(a)           (pi_u = delta_a for a pure play)
    ev_loss  = max(0, best_q - chosen_q)
    ev_loss_pct_pot = 100 * ev_loss / pot_at_decision
    score    = 100 if spread <= EPS else 100 * max(0, 1 - ev_loss / spread)     (EPS = 1e-12)

Linearity: for a mix, `ev_loss(pi_u) = sum_a pi_u(a) * ev_loss(delta_a)` (best_q is constant), and
the score is the matching convex combination. Q is in chips from the hero's perspective, the same
units as `returns()`.
`pot_at_decision` = all chips committed before hero acts. Kuhn: 2 at the root and after a check,
3 when facing a bet. River: `config.pot + sum(a.amount for bet a in history)`, i.e. `pot + bet`
when facing a bet. Here `config.pot` is the dead pot and the stakes are `pot/2` each, per `returns()`.

Grades (by `ev_loss_pct_pot`, §5): `<=0.25` Perfect, `<=1` Good, `<=3` Inaccuracy, `<=8` Mistake,
else Blunder. Use inclusive comparisons, computed on the unrounded float.

## 3. Pseudo-code (evaluate.py)
```python
def subtree_value(state, profile, hero):                 # v(z)
    p = state.current_player()
    if p == TERMINAL: return state.returns()[hero]
    if p == CHANCE:   return sum(pr * subtree_value(state.child(a), profile, hero)
                                 for a, pr in state.chance_outcomes())
    pol = profile[state.information_state_key(p)]        # KeyError -> ValueError (fail closed)
    return sum(pol[a] * subtree_value(state.child(a), profile, hero) for a in state.legal_actions())

def action_values(root, profile, hero, target_key) -> tuple[Mapping[Action, float], float]:
    num, mass, actions = {}, 0.0, None
    def walk(state, w):                                  # w = chance * opponent reach
        nonlocal mass, actions
        if w == 0.0: return                              # prune; contributes nothing
        p = state.current_player()
        if p == TERMINAL: return
        if p == CHANCE:
            for a, pr in state.chance_outcomes(): walk(state.child(a), w * pr)
            return
        key, acts = state.information_state_key(p), state.legal_actions()
        if p == hero and key == target_key:
            if actions is not None and acts != actions: raise ValueError("inconsistent infoset")
            actions = acts; mass += w
            for a in acts: num[a] = num.get(a, 0.0) + w * subtree_value(state.child(a), profile, hero)
            return                                       # perfect recall: I is not revisited below
        if p == hero:
            for a in acts: walk(state.child(a), w)       # hero reach NOT multiplied in
        else:
            pol = profile[key]
            for a in acts: walk(state.child(a), w * pol[a])
    walk(root, 1.0)
    if actions is None or mass <= 0.0: raise ValueError("hero infoset has zero reach")
    return MappingProxyType({a: num[a] / mass for a in actions}), mass
```
Cost: one full walk plus `|A|` subtree evaluations per member history. That is fine for Kuhn,
river and small allstreet trees. A memoised one-pass version can come later. It must reproduce
the same numbers (a test pins this, see T3). Validate `hero` is 0/1 (bool rejected) and the profile
entries for visited keys (finite, >= 0, sum 1 within 1e-9), the same checks as
`best_response.validate_policy`.

## 4. scorer.py semantics
- `Play`: either a pure `Action` (kind + amount) or a mix `{Action: p}`. Every p is finite and >= 0,
  the sum is 1 ± 1e-9, every key is legal at I after snapping, and there are no duplicate keys
  after snapping. If snapping merges two sizes, sum their probabilities.
- **Off-tree sizing**: allowed only for sized kinds (`bet`/`raise`) whose kind exists in `A(I)`.
  The candidate set is the legal actions of that kind. Pick `argmin |amount - c.amount|`, and on a
  tie take the smaller amount. Set `mapped_action = snapped`, `size_mapped = True`. Score with
  `Q(snapped)`. Never interpolate. An unknown kind, or a sized amount when no sized action of that
  kind exists, raises `ValueError`. `amount` must be an int, not bool, and >= 0.
- `optimal_action = argmax_a sigma*(a)`, ties broken by `A(I)` order (deterministic).
  `best_action = argmax_a Q(a)`, also tie-broken by `A(I)` order. Report both. Under solver noise
  they can differ (probe: P0 J root at 2000 iterations).
- **Feedback** (numbers only, deterministic template, values rounded only at format time):
  `"Solver: {mix as 'kind[amt] p%' sorted by p desc}. You: {play}{' (mapped from X)' if mapped}.
  EV loss {ev_loss:.3f} chips ({pct:.2f}% pot) -> {grade}. Best EV action: {best_action}
  (Q={best_q:+.3f}); most-weighted alternative: {top non-chosen sigma action} (Q=...)."`
  Add `" Solver noise: {self_loss:.3f} chips."` when `solver_self_loss > 0.25% pot`. No free text,
  no adjectives that are not tied to a grade.

## 5. Edge cases
| case | behaviour |
|---|---|
| zero-reach infoset (M=0: chance or opponent sigma* never reach I, e.g. villain never bets here) | `ValueError`. The adapter must not offer the spot. No uniform fallback, no invented Q |
| hero's own sigma* reach is 0 (hero "never gets here") | Allowed. Q is still defined because the mass excludes hero reach. Flag `hero_reach == 0` in the result for the UI |
| all Q equal (spread <= 1e-12) | score 100, ev_loss 0 for any legal play, grade Perfect |
| single legal action | Q has one entry, spread 0 -> score 100. The catalog should skip such nodes, but the scorer must still accept them |
| hero hand collides with board / not in hero range / weight 0 | The river chance node drops such deals, so I is never visited -> same `ValueError` as zero reach. The adapter should reject it earlier with a clearer message |
| best_q < chosen_q by float noise | the `max(0, ·)` clamp |
| negative self_loss beyond -1e-9 | `ArithmeticError` (evaluator bug), mirroring `nash_conv` |
| pot_at_decision <= 0 | `ValueError` |

## 6. Numeric exactness check (actually run)
The probe `/tmp/probe_scorer_01.py` imports the production `poker_solver.cfr/best_response/kuhn/model`
modules and implements exactly §3. It ran CFRSolver on `kuhn_root()` for 200 and 2000 iterations,
then printed Q for all 12 infosets. The probe was deleted afterwards. Command and verbatim output:
```
$ cd /home/genomix-node/poker-solver && source .venv/bin/activate && python /tmp/probe_scorer_01.py
== iterations=200 nash_conv=3.461110e-02 train_s=0.11
P0 J hist=[] mass=0.333333 Q={check:-1.000775, bet:-1.114844} sigma={check:+0.819670, bet:+0.180330} best_q=-1.000775 mix_q=-1.021345 self_loss=2.057e-02
P0 Q hist=[] mass=0.333333 Q={check:-0.326237, bet:-0.495000} sigma={check:+0.982708, bet:+0.017292} best_q=-0.326237 mix_q=-0.329155 self_loss=2.918e-03
P0 K hist=[] mass=0.333333 Q={check:+1.155537, bet:+1.207448} sigma={check:+0.389502, bet:+0.610498} best_q=+1.207448 mix_q=+1.187229 self_loss=2.022e-02
P1 J hist=['check'] mass=0.228702 Q={check:-1.000000, bet:-1.040386} sigma={check:+0.704766, bet:+0.295234} best_q=-1.000000 mix_q=-1.011923 self_loss=1.192e-02
P1 Q hist=['check'] mass=0.201529 Q={check:+0.355754, bet:+0.037766} sigma={check:+0.981136, bet:+0.018864} best_q=+0.355754 mix_q=+0.349755 self_loss=5.998e-03
P1 K hist=['check'] mass=0.300396 Q={check:+1.000000, bet:+1.303087} sigma={check:+0.002500, bet:+0.997500} best_q=+1.303087 mix_q=+1.302329 self_loss=7.577e-04
P1 J hist=['bet'] mass=0.104632 Q={fold:-1.000000, call:-2.000000} sigma={fold:+0.997500, call:+0.002500} best_q=-1.000000 mix_q=-1.002500 self_loss=2.500e-03
P1 Q hist=['bet'] mass=0.131805 Q={fold:-1.000000, call:-1.087892} sigma={fold:+0.587604, call:+0.412396} best_q=-1.000000 mix_q=-1.036246 self_loss=3.625e-02
P1 K hist=['bet'] mass=0.032937 Q={fold:-1.000000, call:+2.000000} sigma={fold:+0.002500, call:+0.997500} best_q=+2.000000 mix_q=+1.992500 self_loss=7.500e-03
P0 J hist=['check', 'bet'] mass=0.169394 Q={fold:-1.000000, call:-2.000000} sigma={fold:+0.998475, call:+0.001525} best_q=-1.000000 mix_q=-1.001525 self_loss=1.525e-03
P0 Q hist=['check', 'bet'] mass=0.215456 Q={fold:-1.000000, call:-1.086481} sigma={fold:+0.445382, call:+0.554618} best_q=-1.000000 mix_q=-1.047964 self_loss=4.796e-02
P0 K hist=['check', 'bet'] mass=0.052350 Q={fold:-1.000000, call:+2.000000} sigma={fold:+0.003209, call:+0.996791} best_q=+2.000000 mix_q=+1.990372 self_loss=9.628e-03
identity: sum_h (1/3)*mix_q(P0,h,root)=-0.054423786 expected_values[0]=-0.054423786 diff=8.33e-17 KUHN_VALUE_P0=-0.055555556
== iterations=2000 nash_conv=1.057566e-02 train_s=1.27
P0 J hist=[] mass=0.333333 Q={check:-1.000078, bet:-0.995481} sigma={check:+0.807675, bet:+0.192325} best_q=-0.995481 mix_q=-0.999193 self_loss=3.713e-03
P0 Q hist=[] mass=0.333333 Q={check:-0.336220, bet:-0.499500} sigma={check:+0.998271, bet:+0.001729} best_q=-0.336220 mix_q=-0.336503 self_loss=2.823e-04
P0 K hist=[] mass=0.333333 Q={check:+1.175517, bet:+1.165410} sigma={check:+0.385665, bet:+0.614335} best_q=+1.175517 mix_q=+1.169308 self_loss=6.209e-03
P1 J hist=['check'] mass=0.230656 Q={check:-1.000000, bet:-1.014501} sigma={check:+0.650512, bet:+0.349488} best_q=-1.000000 mix_q=-1.005068 self_loss=5.068e-03
P1 Q hist=['check'] mass=0.198890 Q={check:+0.353638, bet:+0.030876} sigma={check:+0.998114, bet:+0.001886} best_q=+0.353638 mix_q=+0.353029 self_loss=6.088e-04
P1 K hist=['check'] mass=0.300991 Q={check:+1.000000, bet:+1.301171} sigma={check:+0.000250, bet:+0.999750} best_q=+1.301171 mix_q=+1.301096 self_loss=7.529e-05
P1 J hist=['bet'] mass=0.102677 Q={fold:-1.000000, call:-2.000000} sigma={fold:+0.999750, call:+0.000250} best_q=-1.000000 mix_q=-1.000250 self_loss=2.500e-04
P1 Q hist=['bet'] mass=0.134443 Q={fold:-1.000000, call:-1.046315} sigma={fold:+0.669429, call:+0.330571} best_q=-1.000000 mix_q=-1.015310 self_loss=1.531e-02
P1 K hist=['bet'] mass=0.032342 Q={fold:-1.000000, call:+2.000000} sigma={fold:+0.000250, call:+0.999750} best_q=+2.000000 mix_q=+1.999250 self_loss=7.500e-04
P0 J hist=['check', 'bet'] mass=0.166939 Q={fold:-1.000000, call:-2.000000} sigma={fold:+0.999845, call:+0.000155} best_q=-1.000000 mix_q=-1.000155 self_loss=1.548e-04
P0 Q hist=['check', 'bet'] mass=0.224873 Q={fold:-1.000000, call:-0.963894} sigma={fold:+0.455285, call:+0.544715} best_q=-0.963894 mix_q=-0.980333 self_loss=1.644e-02
P0 K hist=['check', 'bet'] mass=0.058562 Q={fold:-1.000000, call:+2.000000} sigma={fold:+0.000324, call:+0.999676} best_q=+2.000000 mix_q=+1.999028 self_loss=9.723e-04
identity: sum_h (1/3)*mix_q(P0,h,root)=-0.055462774 expected_values[0]=-0.055462774 diff=0.00e+00 KUHN_VALUE_P0=-0.055555556
P0 J root pure check: chosen_q=-1.000078 ev_loss=4.597e-03 pct_pot=0.2298 score=0.00
P0 J root pure bet: chosen_q=-0.995481 ev_loss=0.000e+00 pct_pot=0.0000 score=100.00
P0 J root mix 50/50: chosen_q=-0.997779 ev_loss=2.298e-03 pct_pot=0.1149 score=50.00
P0 K facing bet: fold ev_loss=3.000000 pct_pot=100.00 score=0.00
```
(The 200-iteration rows are summarised to stay inside the line budget. The 2000-iteration block
and both identity lines are verbatim.)

Findings:
1. **The Q walk is exact.** The identity `sum_h (1/3)·solver_mix_q(P0,h,root) == expected_values[0]`
   holds to 0 / 8e-17 at both iteration counts. Strategy-independent Q values come out exactly:
   K facing a bet gives fold -1, call +2; J facing a bet gives fold -1, call -2; P1 J/K after a
   check gives check -1/+1.
2. **solver_self_loss at the P0 infosets after 2000 iterations: 2.8e-4 to 1.64e-2**
   (nash_conv 1.06e-2). After 200 iterations: up to 4.8e-2. It is small and falls with
   iterations, but the §5 bar "Kuhn at many iterations => self_loss < 1e-3" is NOT met at 2000
   iterations by P0 J root, P0 K root or P0 Q facing a bet. Self_loss is a per-infoset conditional
   quantity. Low-mass, indifferent infosets converge slowly. Tests must therefore use the bound in
   T4, not a fixed 1e-3, unless they train much longer (cost: about 0.64 ms/iteration).
   Hand-check of that bound with the rows above: P0 Q facing a bet gives
   `reach(0.998271)·mass(0.224873)·1.644e-2 ≈ 3.7e-3 <= nash_conv 1.06e-2`. P0 K root gives
   `1·0.3333·6.209e-3 ≈ 2.1e-3`.
3. **Score pathology [PARENT DECISION].** At P0 J root the Q spread is only 4.6e-3 chips. Pure check
   loses 0.23% of the pot (grade Perfect) yet scores 0. The `1 - loss/spread` normalisation explodes
   when the actions are nearly indifferent, which is exactly the mixed-strategy nodes. Proposal:
   `score = 100·max(0, 1 - ev_loss / max(spread, SPREAD_FLOOR_PCT/100 · pot_at_decision))` with
   `SPREAD_FLOOR_PCT = 8` (the Blunder threshold). Then a play scores 0 only if it is both the worst
   action and at least a Blunder-sized loss, and score and grade stay consistent. Keep §5 unchanged
   if the parent rejects this. Either way, T7 below pins the chosen formula.
4. Under noise, `optimal_action` (largest sigma*, check 0.81) differs from `best_action` (largest Q,
   bet) at P0 J root. The UI must show both and the self-loss note.

## 7. Permanent tests for tests/test_practice_scorer.py (no hard-coded strategy numbers)
Fixture: `prof = CFRSolver(kuhn_root()).train(2000)` (module scope, about 1.3 s). `res = nash_conv(root, prof)`.
- **T1 strategy-independent Q (analytic):** for key `("kuhn-v1",0,"K",(CHECK,BET))` assert Q[FOLD] == -1
  and Q[CALL] == 2 (abs 1e-12). Likewise P0 J facing a bet (-1, -2), P1 K after BET (-1, +2) and
  P1 J after CHECK (Q[CHECK] == -1).
- **T2 value identity:** `sum_c (1/3)·solver_mix_q(P0,c,root) == expected_values(root,prof)[0]` (abs 1e-12).
  At P1 infosets, `sum_c` over the mass-weighted values must equal the corresponding identity built
  from `expected_values[1]`. Also check `mass(P0 root) == 1/3` exactly (chance-only reach).
- **T3 cross-check vs a brute-force deviation:** for each P0 infoset I and action a, build
  `prof'` = prof with `prof'[I] = delta_a`. Then
  `expected_values(root,prof')[0] - expected_values(root,prof)[0] == hero_reach(I)·mass(I)·(Q(a) - solver_mix_q)`
  (abs 1e-12). This pins the whole definition, including the exclusion of hero reach.
- **T4 equilibrium bound:** for every hero infoset, `-1e-12 <= self_loss` and
  `hero_reach·mass·self_loss <= res.incentives[hero] + 1e-12`. Also, Σ over hero infosets of the
  same products for a 200-iteration profile vs a 20000-iteration profile: the latter is smaller
  (mark slow if over 15 s, else drop the 20000 run).
- **T5 pure/mixed linearity:** at any I, ev_loss(mix) == Σ p·ev_loss(pure) and the score equals
  the convex combination of the pure scores (no floor active, or with it). A play of best_action
  gives ev_loss 0 and score 100.
- **T6 grades:** K facing a bet, fold -> ev_loss 3, pct 100, Blunder, score 0; call -> Perfect,
  100. Threshold boundaries via a pure `grade(pct)` helper: 0.25->Perfect, 0.2501->Good, 1->Good,
  3->Inaccuracy, 8->Mistake, 8.0001->Blunder.
- **T7 score formula:** a synthetic Q mapping (pure scorer function) covering all-equal Q -> 100,
  a single action -> 100, worst action -> 0, and the floor behaviour if it is adopted.
- **T8 off-tree snapping (river):** use `RiverConfig` trees with bets X<Y in the abstraction.
  Request (X+Y)/2 exactly -> maps to X (tie -> smaller), `size_mapped` True and `chosen_q == Q(X)`.
  Request Y+100 -> Y. A sized request on a fold/call node -> ValueError. The mix {X:.5, X+1:.5}
  merges into {X:1}.
- **T9 fail-closed:** zero-reach infoset (synthetic profile where P1 never bets -> P0 facing a bet
  has mass 0) -> ValueError. River hero hand colliding with the board -> ValueError. Mix sum 1.1,
  negative p, NaN, bool amount, illegal action -> ValueError. A missing profile key -> ValueError,
  not KeyError.
- **T10 sensitivity (no-hardcode DoD link):** Q/score at P0 J root differ between 200 and 2000
  iterations, and feedback text is a pure function of the PlayScore numbers (same input -> identical
  string; changing the profile changes the string).
- **T11 feedback:** contains the formatted ev_loss, grade, best_action and every sigma* action with
  its rounded probability, all derived from the result fields (assert by re-formatting them, not
  with literals).
