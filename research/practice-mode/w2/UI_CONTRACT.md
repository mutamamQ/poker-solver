# W2 UI contract (parent-authored, binding for all W2 workers)

API: POST /api/v4 with body {"version":4,"operation":OP,"payload":{...}}. Response {version, operation, result, provenance}; errors -> HTTP 4xx/5xx {"error": msg}.
A live captured sample is in research/practice-mode/w2/api-shapes-sample.txt (values are EXAMPLE OUTPUT ONLY — never copy them into code).

- practice-list-spots payload {} -> result.spots[]: {spot_id, family, label, backend, street, board_str[], hero_hand_str[], pot, stacks[], action_history[{kind,amount}], bet_sizes[], hero_seat, solve{algorithm,iterations,seed}, params_hash}, result.families[]
- practice-solve-spot payload {spot_id, solve?:{iterations}} -> result: {spot{...same as above}, provenance{backend, entrypoint, params, params_hash, algorithm, iterations, seed, nash_conv, wall_time_s, solver_version}, legal_actions[{kind,amount}], pot_at_decision, strategy[{action,probability}], action_values[{action,q}], range_strategy[{hand, strategy[{action,probability}]}], optimal_action{kind,amount}, optimal_size}
  The UI must NOT reveal strategy before submit (practice mode): use legal_actions + spot only to render the table before submit.
- practice-submit-play payload {spot_id, play:{kind, amount}, solve?:{iterations}} -> result {user, score{ev_loss_chips, ev_loss_pct_pot, score, grade, chosen_q, best_q, worst_q, solver_mix_q, solver_self_loss, best_action, feedback, mapped_action, size_mapped, play, mappings, provenance}, solved{...same as solve result}}
- Kuhn spots: board_str = [], hero_hand_str = ["J"|"Q"|"K"] (single rank card, no suit).
- Hold'em card strings: rank char + suit char in "cdhs", e.g. "As", "Td".
- Action kinds seen: check, bet, call, fold, raise (lowercase); amount 0 for unsized. Size input applies only to bet/raise; available sizes = amounts of the legal bet/raise actions (server snaps off-tree sizes).

DOM IDs (stable, required, from design report 05): practice-app, spot-list, spot-status, spot-details, board-cards, pot-value, stacks-list, action-history, hero-hand, action-controls, action-size, submit-play, result-panel, score-value, grade-value, ev-loss-value, optimal-mix, range-strategy, provenance, error-message.
Extra IDs: iterations-input (solver iterations override, number, default empty = spot default), resolve-btn (re-solve with iterations), feedback-text, action-values (Q table after submit), spot-filter (family select).

CSS class contract (app.js emits these; style.css styles them):
- Layout: .app-shell (grid: sidebar + main), .sidebar, .main, .topbar, .panel, .panel-title
- Spot list: .spot-item, .spot-item.active, .spot-family, .spot-label, .family-badge
- Table: .table-felt (oval felt), .board, .seat, .seat.hero, .seat.villain, .seat-stack, .pot-chip
- Cards: .card, .card.suit-s, .card.suit-h, .card.suit-d, .card.suit-c, .card.kuhn, .card .rank, .card .suit, .card.back
- History: .history-step
- Actions: .action-btn, .action-btn.selected, .action-btn.act-fold, .act-check, .act-call, .act-bet, .act-raise; .size-row; .size-preset
- Result: .score-ring (with CSS var --score 0..100), .grade-badge, .grade-perfect, .grade-good, .grade-inaccuracy, .grade-mistake, .grade-blunder
- Mix bar: .mix-bar, .mix-seg (inline style width % from API probability), .mix-seg.act-fold/.act-check/.act-call/.act-bet/.act-raise, .mix-legend
- Range table: .range-table, .range-row, .range-row.hero-hand-row, .range-cell (contains a mini .mix-bar)
- Provenance: .prov-grid, .prov-key, .prov-val, .mono
- States: .loading, .spinner, .hidden, .error
Colors (GTO Wizard-like): fold = blue-ish (#5aa0ff), check/call = green (#3bc47a), bet/raise = red/orange gradient (#e8524a / #f08a3c). Dark bg #0f1218, panels #171b24.
