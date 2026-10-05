/* Practice mode UI — vanilla JS, consumes POST /api/v4 (practice-* operations).
 *
 * Rule R1: this file contains NO strategy data, sample spots, EVs or grades.
 * Every displayed value is read from API responses; this file only formats.
 * All API strings are written with textContent (never innerHTML).
 */
(function () {
  "use strict";

  var API_URL = "/api/v4";
  var API_VERSION = 4;
  var SUIT_GLYPHS = { s: "\u2660", h: "\u2665", d: "\u2666", c: "\u2663" };
  var SIZED_KINDS = { bet: true, raise: true };

  var state = {
    spots: [],          // from practice-list-spots
    families: [],
    filter: "",
    selectedId: null,
    solved: null,       // practice-solve-spot result (used ONLY for legal_actions before submit)
    selectedAction: null,
    pending: false,     // any request in flight
    submitted: false,
    solveToken: 0,
  };

  function $(id) { return document.getElementById(id); }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function clear(node) { while (node && node.firstChild) node.removeChild(node.firstChild); }

  function show(node, visible) {
    if (!node) return;
    if (visible) node.classList.remove("hidden"); else node.classList.add("hidden");
  }

  // ---------------------------------------------------------------- format
  function isNum(v) { return typeof v === "number" && isFinite(v); }

  function fmtNum(v, digits) {
    if (!isNum(v)) return v === null || v === undefined ? "\u2014" : String(v);
    if (digits === undefined) {
      return Number.isInteger(v) ? String(v) : String(Math.round(v * 100) / 100);
    }
    return v.toFixed(digits);
  }

  function fmtPct(p) { return isNum(p) ? (p * 100).toFixed(1) + "%" : "\u2014"; }

  function cap(s) { s = String(s || ""); return s.charAt(0).toUpperCase() + s.slice(1); }

  function actionLabel(a) {
    if (!a) return "\u2014";
    var label = cap(a.kind);
    if (isNum(a.amount) && a.amount > 0) label += " " + fmtNum(a.amount);
    return label;
  }

  function actClass(kind) { return "act-" + String(kind || "").toLowerCase().replace(/[^a-z0-9_-]/g, ""); }

  function sameAction(a, b) {
    return !!a && !!b && a.kind === b.kind && Number(a.amount || 0) === Number(b.amount || 0);
  }

  // ---------------------------------------------------------------- cards
  function cardNode(str) {
    str = String(str || "");
    var node = el("span", "card");
    if (str.length === 1) {               // Kuhn: single rank, no suit
      node.classList.add("kuhn");
      node.appendChild(el("span", "rank", str));
      node.setAttribute("aria-label", str);
      return node;
    }
    var rank = str.slice(0, -1);
    var suit = str.slice(-1).toLowerCase();
    if (SUIT_GLYPHS[suit]) node.classList.add("suit-" + suit);
    node.appendChild(el("span", "rank", rank === "T" ? "10" : rank));
    node.appendChild(el("span", "suit", SUIT_GLYPHS[suit] || suit));
    node.setAttribute("aria-label", str);
    return node;
  }

  function renderCards(container, cards) {
    clear(container);
    (cards || []).forEach(function (c) { container.appendChild(cardNode(c)); });
  }

  // Split a range hand string ("9d9h", "J") into card strings.
  function splitHand(hand) {
    hand = String(hand || "");
    if (hand.length <= 1) return [hand];
    var out = [];
    for (var i = 0; i + 1 < hand.length; i += 2) out.push(hand.slice(i, i + 2));
    return out;
  }

  function isHeroHand(hand, heroCards) {
    if (!heroCards || !heroCards.length) return false;
    var a = splitHand(hand).slice().sort().join("");
    var b = heroCards.slice().sort().join("");
    return a === b;
  }

  // ---------------------------------------------------------------- API
  function solveOverride() {
    var raw = $("iterations-input").value.trim();
    if (!raw) return null;
    if (!/^[0-9]+$/.test(raw)) throw new Error("Iterations must be a positive integer.");
    var n = parseInt(raw, 10);
    if (!isFinite(n) || n <= 0) throw new Error("Iterations must be a positive integer.");
    return { iterations: n };
  }

  function api(operation, payload) {
    var body = JSON.stringify({ version: API_VERSION, operation: operation, payload: payload || {} });
    return fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body,
    }).then(function (resp) {
      return resp.text().then(function (text) {
        var data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
        if (!resp.ok) {
          var msg = data && data.error ? data.error : ("HTTP " + resp.status);
          throw new Error(msg);
        }
        if (!data || typeof data !== "object") throw new Error("Malformed API response");
        return data;
      });
    });
  }

  function showError(msg) {
    var box = $("error-message");
    box.textContent = msg ? String(msg) : "";
    show(box, !!msg);
  }

  function setPending(p) {
    state.pending = p;
    updateControls();
  }

  // ---------------------------------------------------------------- spot list
  function filteredSpots() {
    if (!state.filter) return state.spots;
    return state.spots.filter(function (s) { return s.family === state.filter; });
  }

  function renderFilter() {
    var sel = $("spot-filter");
    var current = sel.value;
    while (sel.options.length > 1) sel.remove(1);
    state.families.forEach(function (f) {
      var opt = document.createElement("option");
      opt.value = f;
      opt.textContent = f;
      sel.appendChild(opt);
    });
    sel.value = state.families.indexOf(current) >= 0 ? current : "";
  }

  function renderSpotList() {
    var list = $("spot-list");
    var status = $("spot-status");
    clear(list);
    var spots = filteredSpots();
    status.classList.remove("loading", "error");
    if (!spots.length) {
      status.textContent = "No spots available.";
      show(status, true);
      return;
    }
    status.textContent = spots.length + " spot" + (spots.length === 1 ? "" : "s");
    spots.forEach(function (s) {
      var li = el("li", "spot-item");
      li.tabIndex = 0;
      li.setAttribute("role", "button");
      li.dataset.spotId = s.spot_id;
      if (s.spot_id === state.selectedId) li.classList.add("active");
      var fam = el("span", "spot-family family-badge", s.family);
      li.appendChild(fam);
      li.appendChild(el("span", "spot-label", s.label));
      li.addEventListener("click", function () { selectSpot(s.spot_id); });
      li.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); ev.stopPropagation(); selectSpot(s.spot_id); }
      });
      list.appendChild(li);
    });
  }

  function loadSpots() {
    var status = $("spot-status");
    status.className = "loading";
    clear(status);
    status.appendChild(el("span", "spinner"));
    status.appendChild(document.createTextNode(" Loading spots\u2026"));
    api("practice-list-spots", {}).then(function (data) {
      var res = data.result || {};
      state.spots = Array.isArray(res.spots) ? res.spots : [];
      state.families = Array.isArray(res.families) ? res.families : [];
      renderFilter();
      renderSpotList();
    }).catch(function (err) {
      status.className = "error";
      status.textContent = "Failed to load spots: " + err.message;
      showError("Failed to load spots: " + err.message);
    });
  }

  // ---------------------------------------------------------------- table
  function renderSpot(spot) {
    $("spot-title").textContent = spot.label || spot.spot_id || "";
    var meta = [];
    if (spot.family) meta.push(spot.family);
    if (spot.street) meta.push(spot.street);
    $("spot-meta").textContent = meta.join(" \u00b7 ");

    renderCards($("board-cards"), spot.board_str);
    $("pot-value").textContent = fmtNum(spot.pot);

    var heroSeat = spot.hero_seat;
    renderCards($("hero-hand"), spot.hero_hand_str);
    $("hero-name").textContent = "Hero (P" + heroSeat + ")";
    var villains = (spot.stacks || []).map(function (_, i) { return i; })
      .filter(function (i) { return i !== heroSeat; });
    $("villain-name").textContent = villains.length
      ? "Villain (" + villains.map(function (i) { return "P" + i; }).join(", ") + ")" : "Villain";

    // Villain card backs: one per hero card (Kuhn deals 1, hold'em 2), from the API hand.
    var backs = document.querySelector("#seat-villain .seat-cards");
    if (backs) {
      clear(backs);
      (spot.hero_hand_str || []).forEach(function () {
        var b = el("span", "card back"); b.setAttribute("aria-hidden", "true"); backs.appendChild(b);
      });
    }

    var stacks = $("stacks-list");
    clear(stacks);
    (spot.stacks || []).forEach(function (stack, i) {
      var li = el("li", "stack-item" + (i === heroSeat ? " is-hero" : ""));
      li.appendChild(el("span", "seat-name", "P" + i + (i === heroSeat ? " (Hero)" : "")));
      li.appendChild(el("span", "seat-stack", fmtNum(stack)));
      stacks.appendChild(li);
    });

    var hist = $("action-history");
    clear(hist);
    var steps = spot.action_history || [];
    if (!steps.length) {
      hist.appendChild(el("span", "history-step", "First to act"));
    } else {
      steps.forEach(function (a) {
        hist.appendChild(el("span", "history-step " + actClass(a.kind), actionLabel(a)));
      });
    }
  }

  function clearTable() {
    $("spot-title").textContent = "Select a spot";
    $("spot-meta").textContent = "";
    clear($("board-cards"));
    clear($("hero-hand"));
    clear($("stacks-list"));
    clear($("action-history"));
    $("pot-value").textContent = "\u2014";
  }

  // ---------------------------------------------------------------- actions
  function legalActions() { return (state.solved && state.solved.legal_actions) || []; }

  function sizedAmounts() {
    var seen = {};
    var out = [];
    legalActions().forEach(function (a) {
      if (SIZED_KINDS[a.kind] && isNum(a.amount) && a.amount > 0 && !seen[a.amount]) {
        seen[a.amount] = true;
        out.push(a.amount);
      }
    });
    return out.sort(function (x, y) { return x - y; });
  }

  function renderActions() {
    var box = $("action-controls");
    clear(box);
    legalActions().forEach(function (a, idx) {
      var btn = el("button", "action-btn " + actClass(a.kind), actionLabel(a));
      btn.type = "button";
      btn.dataset.index = String(idx);
      btn.addEventListener("click", function () { selectAction(idx); });
      box.appendChild(btn);
    });

    var amounts = sizedAmounts();
    var sizeRow = $("size-row");
    var presets = $("size-presets");
    clear(presets);
    show(sizeRow, amounts.length > 0);
    if (amounts.length) {
      var input = $("action-size");
      input.value = String(amounts[0]);
      amounts.forEach(function (amt) {
        var chip = el("button", "size-preset", fmtNum(amt));
        chip.type = "button";
        chip.addEventListener("click", function () {
          $("action-size").value = String(amt);
          var idx = legalActions().findIndex(function (a) { return SIZED_KINDS[a.kind] && a.amount === amt; });
          if (idx >= 0) selectAction(idx, true);
        });
        presets.appendChild(chip);
      });
    }
    updateControls();
  }

  function selectAction(idx, keepSize) {
    if (state.submitted || state.pending) return;
    var a = legalActions()[idx];
    if (!a) return;
    state.selectedAction = a;
    var btns = $("action-controls").querySelectorAll(".action-btn");
    Array.prototype.forEach.call(btns, function (b) {
      var sel = b.dataset.index === String(idx);
      b.classList.toggle("selected", sel);
      b.setAttribute("aria-pressed", sel ? "true" : "false");
    });
    if (!keepSize && SIZED_KINDS[a.kind] && isNum(a.amount) && a.amount > 0) {
      $("action-size").value = String(a.amount);
    }
    updateControls();
  }

  function selectByKinds(kinds) {
    var acts = legalActions();
    for (var k = 0; k < kinds.length; k++) {
      for (var i = 0; i < acts.length; i++) {
        if (acts[i].kind === kinds[k]) { selectAction(i); return true; }
      }
    }
    return false;
  }

  function currentPlay() {
    var a = state.selectedAction;
    if (!a) return null;
    var amount = isNum(a.amount) ? a.amount : 0;
    if (SIZED_KINDS[a.kind] && amount > 0) {
      var v = parseFloat($("action-size").value);
      if (!isFinite(v) || v <= 0) throw new Error("Enter a positive size.");
      amount = v;
    }
    return { kind: a.kind, amount: amount };
  }

  function updateControls() {
    var hasSpot = !!state.selectedId;
    $("submit-play").disabled = state.pending || state.submitted || !state.selectedAction;
    $("resolve-btn").disabled = state.pending || !hasSpot;
    $("next-spot").disabled = state.pending || filteredSpots().length === 0;
    var locked = state.pending || state.submitted;
    Array.prototype.forEach.call(document.querySelectorAll(".action-btn, .size-preset"), function (b) {
      b.disabled = locked;
    });
    $("action-size").disabled = locked;
  }

  // ---------------------------------------------------------------- solve
  function selectSpot(spotId) {
    if (state.pending && spotId === state.selectedId) return;
    var override;
    try { override = solveOverride(); } catch (e) { showError(e.message); return; }
    showError("");
    state.selectedId = spotId;
    state.solved = null;
    state.selectedAction = null;
    state.submitted = false;
    var token = ++state.solveToken;

    Array.prototype.forEach.call(document.querySelectorAll(".spot-item"), function (li) {
      li.classList.toggle("active", li.dataset.spotId === spotId);
    });
    var listed = state.spots.find(function (s) { return s.spot_id === spotId; });
    if (listed) renderSpot(listed); else clearTable();
    clear($("action-controls"));
    show($("size-row"), false);
    show($("result-panel"), false);
    show($("solve-spinner"), true);
    $("action-controls").appendChild(el("span", "loading", "Solving\u2026"));
    setPending(true);

    var payload = { spot_id: spotId };
    if (override) payload.solve = override;
    api("practice-solve-spot", payload).then(function (data) {
      if (token !== state.solveToken) return;
      // Keep the solve in memory; before submit only spot + legal_actions are rendered.
      state.solved = data.result || {};
      if (state.solved.spot) renderSpot(state.solved.spot);
      renderActions();
    }).catch(function (err) {
      if (token !== state.solveToken) return;
      clear($("action-controls"));
      showError("Solve failed: " + err.message);
    }).then(function () {
      if (token !== state.solveToken) return;
      show($("solve-spinner"), false);
      setPending(false);
    });
  }

  // ---------------------------------------------------------------- submit
  function submitPlay() {
    if (state.pending || state.submitted || !state.selectedId || !state.selectedAction) return;
    var play, override;
    try { play = currentPlay(); override = solveOverride(); } catch (e) { showError(e.message); return; }
    showError("");
    var token = state.solveToken;
    var payload = { spot_id: state.selectedId, play: play };
    if (override) payload.solve = override;
    show($("solve-spinner"), true);
    setPending(true);
    api("practice-submit-play", payload).then(function (data) {
      if (token !== state.solveToken) return;
      var res = data.result || {};
      state.submitted = true;
      renderResult(res.score || {}, res.solved || {});
    }).catch(function (err) {
      if (token !== state.solveToken) return;
      showError("Submit failed: " + err.message);
    }).then(function () {
      if (token !== state.solveToken) return;
      show($("solve-spinner"), false);
      setPending(false);
    });
  }

  function mixBar(strategy, withLabels) {
    var bar = el("div", "mix-bar");
    (strategy || []).forEach(function (entry) {
      var p = isNum(entry.probability) ? entry.probability : 0;
      var label = actionLabel(entry.action) + " " + fmtPct(p);
      var seg = el("div", "mix-seg " + actClass(entry.action && entry.action.kind));
      seg.style.width = Math.max(0, Math.min(100, p * 100)) + "%";
      seg.title = label;
      seg.setAttribute("aria-label", label);
      if (p < 0.08) seg.classList.add("tiny");
      if (withLabels) seg.textContent = label;
      bar.appendChild(seg);
    });
    return bar;
  }

  function renderResult(score, solved) {
    // Score ring
    var ring = $("score-value");
    var sc = isNum(score.score) ? score.score : 0;
    ring.className = "score-ring";
    ring.style.setProperty("--score", String(sc));
    clear(ring);
    var scoreText = isNum(score.score) ? fmtNum(Math.round(score.score * 10) / 10) : "\u2014";
    ring.appendChild(el("span", "score-num", scoreText));
    ring.setAttribute("aria-label", "Score " + scoreText);

    // Grade
    var grade = $("grade-value");
    var gradeStr = score.grade ? String(score.grade) : "";
    grade.className = "grade-badge";
    if (gradeStr) {
      var gradeCls = "grade-" + gradeStr.toLowerCase().replace(/[^a-z0-9_-]/g, "-");
      grade.classList.add(gradeCls);
      ring.classList.add(gradeCls);
    }
    grade.textContent = gradeStr || "\u2014";

    // EV loss
    $("ev-loss-value").textContent = fmtNum(score.ev_loss_chips, 3) + " chips (" +
      fmtNum(score.ev_loss_pct_pot, 2) + "% pot)";

    // Feedback
    var fb = $("feedback-text");
    fb.textContent = score.feedback || "";
    if (score.size_mapped && score.mapped_action) {
      fb.textContent += " (size mapped to " + actionLabel(score.mapped_action) + ")";
    }

    // Optimal mix + legend
    var mixBox = $("optimal-mix");
    clear(mixBox);
    mixBox.appendChild(mixBar(solved.strategy, true));
    var legend = el("div", "mix-legend");
    (solved.strategy || []).forEach(function (entry) {
      legend.appendChild(el("span", "mix-legend-item " + actClass(entry.action && entry.action.kind),
        actionLabel(entry.action) + " " + fmtPct(entry.probability)));
    });
    mixBox.appendChild(legend);

    // Action values (Q table)
    var qBox = $("action-values");
    clear(qBox);
    var qt = el("table", "q-table");
    var thead = el("thead");
    var hr = el("tr");
    ["Action", "Q (chips)", ""].forEach(function (h) { hr.appendChild(el("th", null, h)); });
    thead.appendChild(hr);
    qt.appendChild(thead);
    var tbody = el("tbody");
    var chosen = score.play || null;
    (solved.action_values || []).forEach(function (row) {
      var tr = el("tr", actClass(row.action && row.action.kind));
      tr.appendChild(el("td", null, actionLabel(row.action)));
      tr.appendChild(el("td", "mono", fmtNum(row.q, 3)));
      var tags = [];
      if (sameAction(row.action, score.best_action)) { tags.push("best"); tr.classList.add("best"); }
      var chosenMatch = sameAction(row.action, score.mapped_action) || sameAction(row.action, chosen);
      if (chosenMatch) { tags.push("yours"); tr.classList.add("chosen"); }
      tr.appendChild(el("td", null, tags.join(", ")));
      tbody.appendChild(tr);
    });
    qt.appendChild(tbody);
    qBox.appendChild(qt);

    // Range strategy
    var rBox = $("range-strategy");
    clear(rBox);
    var heroCards = (solved.spot && solved.spot.hero_hand_str) ||
      (state.solved && state.solved.spot && state.solved.spot.hero_hand_str) || [];
    var table = el("div", "range-table");
    (solved.range_strategy || []).forEach(function (row) {
      var r = el("div", "range-row");
      if (isHeroHand(row.hand, heroCards)) r.classList.add("hero-hand-row");
      var handCell = el("div", "range-cell range-hand");
      splitHand(row.hand).forEach(function (c) { handCell.appendChild(cardNode(c)); });
      r.appendChild(handCell);
      var barCell = el("div", "range-cell");
      barCell.appendChild(mixBar(row.strategy, false));
      r.appendChild(barCell);
      var txt = (row.strategy || []).map(function (e) {
        return actionLabel(e.action) + " " + fmtPct(e.probability);
      }).join(" \u00b7 ");
      r.appendChild(el("div", "range-cell range-text", txt));
      table.appendChild(r);
    });
    rBox.appendChild(table);

    // Provenance
    var prov = (solved.provenance) || score.provenance || {};
    var pBox = $("provenance");
    clear(pBox);
    var grid = el("dl", "prov-grid");
    var keys = ["backend", "entrypoint", "algorithm", "iterations", "seed", "nash_conv",
      "wall_time_s", "solver_version", "params_hash"];
    keys.forEach(function (k) {
      var v = prov[k];
      var text;
      if (v === null || v === undefined) text = k === "seed" ? "none" : "\u2014";
      else if (k === "nash_conv") text = fmtNum(v, 6);
      else if (k === "wall_time_s") text = fmtNum(v, 3) + " s";
      else text = String(v);
      grid.appendChild(el("dt", "prov-key", k));
      var dd = el("dd", "prov-val mono");
      if (k === "params_hash" && typeof v === "string") {
        dd.textContent = v.length > 16 ? v.slice(0, 16) + "\u2026" : v;
        dd.title = v;
        dd.dataset.fullHash = v;
      } else {
        dd.textContent = text;
      }
      grid.appendChild(dd);
    });
    pBox.appendChild(grid);

    show($("result-panel"), true);
    updateControls();
  }

  // ---------------------------------------------------------------- next
  function nextSpot() {
    var spots = filteredSpots();
    if (!spots.length) return;
    var idx = spots.findIndex(function (s) { return s.spot_id === state.selectedId; });
    var next = spots[(idx + 1) % spots.length];
    selectSpot(next.spot_id);
  }

  // ---------------------------------------------------------------- events
  function isTypingTarget(t) {
    if (!t) return false;
    var tag = (t.tagName || "").toLowerCase();
    return tag === "input" || tag === "select" || tag === "textarea" || t.isContentEditable;
  }

  function onKey(ev) {
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    var typing = isTypingTarget(ev.target);
    var key = ev.key;
    if (key === "Enter") {
      if (ev.target && ev.target.id === "iterations-input") return;  // handled separately
      if (!typing && ev.target && ev.target.tagName === "BUTTON" &&
          !ev.target.classList.contains("action-btn") &&
          !ev.target.classList.contains("size-preset")) return; // native activation
      if (!$("submit-play").disabled) { ev.preventDefault(); submitPlay(); }
      return;
    }
    if (typing) return;
    var k = key.toLowerCase();
    if (k === "f") { if (selectByKinds(["fold"])) ev.preventDefault(); }
    else if (k === "c") { if (selectByKinds(["check", "call"])) ev.preventDefault(); }
    else if (k === "b") {
      if (selectByKinds(["bet", "raise"])) {
        ev.preventDefault();
        if (!$("size-row").classList.contains("hidden")) $("action-size").focus();
      }
    }
  }

  function init() {
    $("submit-play").addEventListener("click", submitPlay);
    $("next-spot").addEventListener("click", nextSpot);
    $("resolve-btn").addEventListener("click", function () {
      if (state.selectedId) selectSpot(state.selectedId);
    });
    $("iterations-input").addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" && state.selectedId) { ev.preventDefault(); selectSpot(state.selectedId); }
    });
    $("spot-filter").addEventListener("change", function (ev) {
      state.filter = ev.target.value;
      renderSpotList();
      updateControls();
    });
    $("action-size").addEventListener("input", function () {
      // Typing a size implies a sized action; pick the first bet/raise if none selected.
      var sel = state.selectedAction;
      if (sel && SIZED_KINDS[sel.kind]) return;
      var idx = legalActions().findIndex(function (a) { return SIZED_KINDS[a.kind] && a.amount > 0; });
      if (idx >= 0) selectAction(idx, true);
    });
    document.addEventListener("keydown", onKey);
    updateControls();
    loadSpots();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
