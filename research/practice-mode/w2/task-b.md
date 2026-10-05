# W2 task-b — web/style.css

Files: `web/style.css` (owned), `research/practice-mode/w2/style-preview.html` (static demo, fake markup, never served).

## Decisions
- Pure CSS, system font stack, no `@import`, no `url()` at all (card back / chip use gradients).
- All tokens in `:root` (colors per brief; `--accent-text #b3a2ff` for accent-coloured text since #7c5cff on dark is < 4.5:1).
- Action buttons use solid action fills with dark ink text (`#0b0e13`) — AA on all four hues; bet/raise get a subtle top gradient. `.act-*` sets `--act`, reused by `.action-btn`, `.mix-seg`, `.mix-legend` swatches and `.history-step` (tinted text).
- `.family-badge` hue via `--fam` + `color-mix()` (with `@supports not` fallback); kuhn violet, river-oop cyan, river-ip amber, plus turn/flop extras and a grey generic fallback.
- `.table-felt`: `border-radius: 50%/50%` oval, dark teal radial felt, rail border, inset shadows. `.seat.villain` absolutely top, `.seat.hero` absolutely bottom with accent glow; `.seat.static` opt-out for in-flow seats. Felt has `padding` so seats overflow the rail slightly — parents should leave ~30px vertical room (main grid gap does).
- `.card`: 44x62 (vars `--card-w/--card-h`), hero hand 52x73, mobile 34x48/40x56. Four-colour suits via `--suit-color`. `.card.kuhn` hides `.suit`, big rank. `.card.back` crosshatch gradient. Deal-in keyframe with stagger; disabled under `prefers-reduced-motion`.
- `.history-step` arrows: `›` pseudo-element placed in the margin before every non-first chip.
- `.score-ring`: `conic-gradient` from `var(--score)`; ring colour defaults to accent, override by adding a `.grade-*` class to the ring (sets `--ring-color`). Number = `#score-value` or `.score-num`.
- `.mix-seg` tiny-label hiding: no pure-CSS way to read inline width, so: `.mix-seg.tiny` / `[data-tiny="true"]` hook (app.js may add when p < ~8%), `width: 0` attribute match, and a container query hiding all labels when the bar < 160px. Labels also clip (overflow hidden), so tiny segments never overflow anyway. Range-cell mini bars (10px) never show labels.
- `.range-table` supports both `<table>` (sticky `thead th`) and a div grid (`.range-head` sticky).
- `#error-message` styled as a banner when non-empty (in addition to `.error`), hidden when empty.
- Generic `button` styling and `#submit-play` primary accent styling added; `:focus-visible` outlines everywhere, action buttons get a white 3px outline.
- Responsive: ≤900px single column (sidebar on top, spot list capped 260px scroll); ≤560px action buttons 100% width, cards scale down, prov-grid single column.
- `forced-colors` minimal support.

## Checks
- Brace balance: 223 `{` / 223 `}`.
- No `@import`, no `url(` in the CSS.
