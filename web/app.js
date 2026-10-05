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
  // Action kinds are compared case-insensitively: legacy families emit lowercase
  // ("bet"), the W4 backends emit uppercase ("RAISE"). The original kind string
  // from legal_actions is always what gets sent back to the API.
  var SIZED_KINDS = { bet: true, raise: true };
  // Display names only (values sent to the API are never rewritten).
  var KIND_LABELS = {
    fold: "Fold", check: "Check", call: "Call", bet: "Bet", raise: "Raise",
    allin: "All-in", "all-in": "All-in", all_in: "All-in", shove: "All-in",
  };
  // Keyboard shortcuts -> normalized kinds, tried in order.
  var KEY_KINDS = {
    f: ["fold"],
    c: ["check", "call"],
    b: ["bet", "raise"],
    a: ["allin", "all-in", "all_in", "shove"],
  };
  var USER_KEY = "practice.user";                 // localStorage key
  var USER_RE = /^[A-Za-z0-9_.-]{1,32}$/;         // mirrors the server's user-id rule
  var SERVER_TIMEOUT_S = 90;                      // practice server request timeout
  var CLIENT_ABORT_S = SERVER_TIMEOUT_S + 15;     // client-side safety net
  var LEADERBOARD_LIMIT = 20;
  // Display ordering only (not data): streets in game order, unknown ones appended.
  var STREET_ORDER = ["preflop", "flop", "turn", "river"];

  var state = {
    spots: [],          // from practice-list-spots
    families: [],
    filter: "",
    streetFilter: "",
    gameFilter: "",
    user: "",           // validated player name ("" = server default)
    progressBySpot: {}, // spot_id -> practice-progress spot entry (API data)
    spotsLoaded: false,
    solveTimer: null,
    solveStart: 0,
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

  function normKind(kind) { return String(kind || "").trim().toLowerCase(); }

  function isSized(a) { return !!a && SIZED_KINDS[normKind(a.kind)] === true && isNum(a.amount) && a.amount > 0; }

  // "RAISE" -> "Raise", "all_in" -> "All-in", unknown "SOME_KIND" -> "Some kind".
  function kindLabel(kind) {
    var k = normKind(kind);
    if (Object.prototype.hasOwnProperty.call(KIND_LABELS, k)) return KIND_LABELS[k];
    return cap(k.replace(/[_]+/g, " "));
  }

  function actionLabel(a) {
    if (!a) return "\u2014";
    var label = kindLabel(a.kind);
    if (isNum(a.amount) && a.amount > 0) label += " " + fmtNum(a.amount);
    return label;
  }

  function actClass(kind) {
    var k = normKind(kind);
    if (KIND_LABELS[k] === "All-in") k = "allin";
    return "act-" + k.replace(/[^a-z0-9_-]/g, "");
  }

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
    var ctrl = typeof AbortController === "function" ? new AbortController() : null;
    var abortTimer = ctrl ? setTimeout(function () { ctrl.abort(); }, CLIENT_ABORT_S * 1000) : null;
    return fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body,
      signal: ctrl ? ctrl.signal : undefined,
    }).catch(function (err) {
      if (err && err.name === "AbortError") throw new Error("No response after " + CLIENT_ABORT_S + " s (request aborted)");
      throw err;
    }).finally(function () {
      if (abortTimer) clearTimeout(abortTimer);
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

  // Visible long-solve state: "Solving… Ns" elapsed counter while a request is pending.
  function startSolving(verb) {
    stopSolving();
    var box = $("solve-status");
    state.solveStart = Date.now();
    var tick = function () {
      var secs = Math.floor((Date.now() - state.solveStart) / 1000);
      var txt = verb + "\u2026 " + secs + "s";
      if (secs >= 10) txt += " (server limit " + SERVER_TIMEOUT_S + " s)";
      box.textContent = txt;
      var inline = $("action-controls").querySelector(".solving-inline");
      if (inline) inline.textContent = verb + "\u2026 " + secs + "s";
    };
    tick();
    show(box, true);
    show($("solve-spinner"), true);
    $("practice-app").setAttribute("aria-busy", "true");
    state.solveTimer = setInterval(tick, 1000);
  }

  function stopSolving() {
    if (state.solveTimer) clearInterval(state.solveTimer);
    state.solveTimer = null;
    var box = $("solve-status");
    if (box) { box.textContent = ""; show(box, false); }
    show($("solve-spinner"), false);
    $("practice-app").removeAttribute("aria-busy");
  }

  // ---------------------------------------------------------------- user
  function readStoredUser() {
    try { return window.localStorage.getItem(USER_KEY) || ""; } catch (e) { return ""; }
  }

  function storeUser(name) {
    try {
      if (name) window.localStorage.setItem(USER_KEY, name); else window.localStorage.removeItem(USER_KEY);
    } catch (e) { /* storage unavailable (private mode): keep in memory only */ }
  }

  function setUserHint(msg) {
    var hint = $("user-hint");
    hint.textContent = msg || "";
    show(hint, !!msg);
    $("user-input").setAttribute("aria-invalid", msg ? "true" : "false");
  }

  // Apply the input value; invalid names are not sent (server default is used).
  function applyUser(refresh) {
    var raw = $("user-input").value.trim();
    if (raw && !USER_RE.test(raw)) {
      setUserHint("Name: 1\u201332 of A\u2013Z a\u2013z 0\u20139 _ . -");
      return false;
    }
    setUserHint("");
    var changed = raw !== state.user;
    state.user = raw;
    storeUser(raw);
    if (changed && refresh) {
      loadProgress();
      // The "me" highlight depends on the user: re-mark rows now, then reload.
      rerenderLeaderboard();
      loadLeaderboard();
    }
    return true;
  }

  function withUser(payload) {
    if (state.user) payload.user = state.user;
    return payload;
  }

  // ---------------------------------------------------------------- progress / leaderboard
  function panelStatus(id, msg, cls) {
    var node = $(id);
    node.className = "panel-status" + (cls ? " " + cls : "");
    node.textContent = msg || "";
    show(node, !!msg);
  }

  function fmtWhen(iso) {
    if (typeof iso !== "string" || !iso) return "\u2014";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  }

  function dataTable(headers, rows, className) {
    var table = el("table", "data " + (className || ""));
    var thead = el("thead");
    var hr = el("tr");
    headers.forEach(function (h) {
      var th = el("th", null, h);
      th.scope = "col";
      hr.appendChild(th);
    });
    thead.appendChild(hr);
    table.appendChild(thead);
    // Numeric columns: align the header with its right-aligned cells.
    if (rows.length) {
      Array.prototype.forEach.call(rows[0].children, function (cell, i) {
        if (cell.classList.contains("num") && hr.children[i]) hr.children[i].classList.add("num");
      });
    }
    var tbody = el("tbody");
    rows.forEach(function (r) {
      // data-label lets the narrow (stacked) layout show each cell's header via CSS attr().
      Array.prototype.forEach.call(r.children, function (cell, i) {
        if (headers[i]) cell.dataset.label = headers[i];
      });
      tbody.appendChild(r);
    });
    table.appendChild(tbody);
    return table;
  }

  function td(text, cls) { return el("td", cls || null, text); }

  function spotLabel(spotId) {
    var s = state.spots.find(function (x) { return x.spot_id === spotId; });
    return s && s.label ? s.label : spotId;
  }

  function renderProgress(res) {
    var totalsBox = $("progress-totals");
    var spotsBox = $("progress-spots");
    clear(totalsBox);
    clear(spotsBox);
    $("progress-user").textContent = res && res.user ? "\u00b7 " + res.user : "";
    var totals = (res && res.totals) || {};
    var spots = (res && Array.isArray(res.spots)) ? res.spots : [];
    state.progressBySpot = {};
    spots.forEach(function (e) { if (e && e.spot_id) state.progressBySpot[e.spot_id] = e; });

    [["Attempts", fmtNum(totals.attempts)],
     ["Spots tried", fmtNum(totals.spots_attempted)],
     ["Avg best", fmtScore(totals.avg_best_score)],
     ["Avg last", fmtScore(totals.avg_last_score)]].forEach(function (pair) {
      var cell = el("div", "total-cell");
      cell.appendChild(el("dt", "total-key", pair[0]));
      cell.appendChild(el("dd", "total-val", pair[1]));
      totalsBox.appendChild(cell);
    });
    show(totalsBox, true);

    if (!spots.length) {
      panelStatus("progress-status", "No attempts yet \u2014 submit a play to start tracking.", "empty");
    } else {
      panelStatus("progress-status", "");
      var rows = spots.slice().sort(function (a, b) {
        return String(b.last_at || "").localeCompare(String(a.last_at || ""));
      }).map(function (e) {
        var tr = el("tr");
        if (e.spot_id === state.selectedId) tr.classList.add("current");
        var name = td(spotLabel(e.spot_id), "cell-spot");
        name.title = e.spot_id;
        tr.appendChild(name);
        tr.appendChild(td([e.street, e.game_type].filter(Boolean).join(" \u00b7 ") || "\u2014", "cell-muted"));
        tr.appendChild(td(fmtNum(e.attempts), "num"));
        tr.appendChild(td(fmtScore(e.best_score), "num cell-best"));
        tr.appendChild(td(fmtScore(e.last_score), "num"));
        var g = td("", "cell-grade");
        if (e.last_grade) {
          g.appendChild(el("span", "grade-badge grade-sm grade-" +
            String(e.last_grade).toLowerCase().replace(/[^a-z0-9_-]/g, "-"), e.last_grade));
        } else g.textContent = "\u2014";
        tr.appendChild(g);
        tr.appendChild(td(fmtWhen(e.last_at), "cell-muted cell-when"));
        return tr;
      });
      spotsBox.appendChild(dataTable(["Spot", "Street \u00b7 game", "Tries", "Best", "Last", "Grade", "Last played"], rows, "progress-table"));
    }
  }

  function progressUnavailable(err) {
    state.progressBySpot = {};
    clear($("progress-totals"));
    show($("progress-totals"), false);
    clear($("progress-spots"));
    $("progress-user").textContent = "";
    panelStatus("progress-status", "Progress unavailable" + (err && err.message ? ": " + err.message : ""), "unavailable");
    $("progress-panel").classList.add("is-unavailable");
  }

  var progressToken = 0;
  function loadProgress() {
    var token = ++progressToken;
    panelStatus("progress-status", "Loading progress\u2026", "loading-text");
    return api("practice-progress", withUser({})).then(function (data) {
      if (token !== progressToken) return;
      $("progress-panel").classList.remove("is-unavailable");
      renderProgress(data.result || {});
    }).catch(function (err) {
      if (token !== progressToken) return;
      progressUnavailable(err);
    }).then(function () {
      if (token === progressToken && state.spotsLoaded) renderSpotList();
    });
  }

  // Merge a submit's `progress` spot entry (API data) without a round-trip, then refresh totals.
  function applySubmitProgress(entry) {
    if (entry && typeof entry === "object" && entry.spot_id) {
      state.progressBySpot[entry.spot_id] = entry;
      if (state.spotsLoaded) renderSpotList();
    }
    loadProgress();
    loadLeaderboard();
  }

  var lastLeaderboard = null;   // last practice-leaderboard result (API data), for re-marking "me"

  function rerenderLeaderboard() { if (lastLeaderboard) renderLeaderboard(lastLeaderboard); }

  function renderLeaderboard(res) {
    lastLeaderboard = res || null;
    var box = $("leaderboard-table");
    clear(box);
    var entries = (res && Array.isArray(res.entries)) ? res.entries : [];
    $("leaderboard-scope").textContent = state.filter ? "\u00b7 " + state.filter : "\u00b7 all families";
    if (!entries.length) {
      panelStatus("leaderboard-status", "No ranked players yet.", "empty");
      return;
    }
    panelStatus("leaderboard-status", "");
    var me = state.user || "local";
    var rows = entries.map(function (e) {
      var tr = el("tr");
      if (e.user === me) tr.classList.add("me");
      tr.appendChild(td(fmtNum(e.rank), "num cell-rank"));
      tr.appendChild(td(e.user, "cell-user"));
      tr.appendChild(td(fmtNum(e.spots_attempted), "num"));
      tr.appendChild(td(fmtNum(e.attempts), "num"));
      tr.appendChild(td(fmtScore(e.avg_best_score), "num"));
      tr.appendChild(td(fmtScore(e.total_best_score), "num cell-best"));
      return tr;
    });
    box.appendChild(dataTable(["#", "Player", "Spots", "Tries", "Avg best", "Total best"], rows, "leaderboard-table"));
  }

  var leaderboardToken = 0;
  function loadLeaderboard() {
    var token = ++leaderboardToken;
    var payload = { limit: LEADERBOARD_LIMIT };
    if (state.filter) payload.family = state.filter;
    panelStatus("leaderboard-status", "Loading leaderboard\u2026", "loading-text");
    return api("practice-leaderboard", payload).then(function (data) {
      if (token !== leaderboardToken) return;
      $("leaderboard-panel").classList.remove("is-unavailable");
      renderLeaderboard(data.result || {});
    }).catch(function (err) {
      if (token !== leaderboardToken) return;
      lastLeaderboard = null;
      clear($("leaderboard-table"));
      $("leaderboard-scope").textContent = "";
      $("leaderboard-panel").classList.add("is-unavailable");
      panelStatus("leaderboard-status", "Leaderboard unavailable" + (err && err.message ? ": " + err.message : ""), "unavailable");
    });
  }

  // ---------------------------------------------------------------- spot list
  function filteredSpots() {
    return state.spots.filter(function (s) {
      if (state.filter && s.family !== state.filter) return false;
      if (state.streetFilter && s.street !== state.streetFilter) return false;
      if (state.gameFilter && s.game_type !== state.gameFilter) return false;
      return true;
    });
  }

  // Distinct non-empty string values of `key` across the listed spots.
  function distinct(key) {
    var seen = {};
    var out = [];
    state.spots.forEach(function (s) {
      var v = s[key];
      if (typeof v === "string" && v && !seen[v]) { seen[v] = true; out.push(v); }
    });
    return out;
  }

  function fillSelect(sel, values) {
    var current = sel.value;
    while (sel.options.length > 1) sel.remove(1);
    values.forEach(function (v) {
      var opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      sel.appendChild(opt);
    });
    sel.value = values.indexOf(current) >= 0 ? current : "";
    return sel.value;
  }

  function renderFilter() {
    var fams = state.families.length ? state.families.slice() : distinct("family");
    state.filter = fillSelect($("spot-filter"), fams);
    var streets = distinct("street").sort(function (a, b) {
      var ia = STREET_ORDER.indexOf(a), ib = STREET_ORDER.indexOf(b);
      if (ia < 0) ia = STREET_ORDER.length;
      if (ib < 0) ib = STREET_ORDER.length;
      return ia !== ib ? ia - ib : (a < b ? -1 : a > b ? 1 : 0);
    });
    state.streetFilter = fillSelect($("street-filter"), streets);
    state.gameFilter = fillSelect($("game-filter"), distinct("game_type").sort());
  }

  function fmtScore(v) { return isNum(v) ? v.toFixed(1) : "\u2014"; }

  function bestBadge(spotId) {
    var entry = state.progressBySpot[spotId];
    if (!entry || !isNum(entry.best_score)) return null;
    var badge = el("span", "best-badge", "Best " + fmtScore(entry.best_score));
    var tip = "Best score " + fmtScore(entry.best_score);
    if (isNum(entry.attempts)) tip += " \u00b7 " + entry.attempts + " attempt" + (entry.attempts === 1 ? "" : "s");
    badge.title = tip;
    badge.setAttribute("aria-label", tip);
    // Neutral colour on purpose: the API exposes no grade for the best attempt
    // (only last_grade), so colouring "Best x" by the last grade would misreport it.
    return badge;
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
    status.textContent = spots.length + " spot" + (spots.length === 1 ? "" : "s") +
      (spots.length !== state.spots.length ? " of " + state.spots.length : "");
    spots.forEach(function (s) {
      var li = el("li", "spot-item");
      li.tabIndex = 0;
      li.setAttribute("role", "button");
      li.dataset.spotId = s.spot_id;
      if (s.spot_id === state.selectedId) li.classList.add("active");
      var head = el("span", "spot-head");
      var fam = el("span", "spot-family family-badge", s.family);
      fam.dataset.family = String(s.family || "");
      head.appendChild(fam);
      var badge = bestBadge(s.spot_id);
      if (badge) head.appendChild(badge);
      li.appendChild(head);
      li.appendChild(el("span", "spot-label", s.label));
      var tags = el("span", "spot-tags");
      if (s.street) tags.appendChild(el("span", "spot-tag", s.street));
      if (s.game_type) tags.appendChild(el("span", "spot-tag game-" + String(s.game_type).replace(/[^a-z0-9_-]/gi, ""), s.game_type));
      if (tags.firstChild) li.appendChild(tags);
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
      state.spotsLoaded = true;
      renderFilter();
      renderSpotList();
      if (Object.keys(state.progressBySpot).length) {
        // re-render progress rows so spot labels (from the list) replace raw ids
        loadProgress();
      }
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
    renderVillains(spot);

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

  // Villain seats come from spot.villain_seats (3-max: two entries); fall back to
  // every stack index that is not the hero when the field is absent.
  function villainSeats(spot) {
    if (Array.isArray(spot.villain_seats) && spot.villain_seats.length) return spot.villain_seats.slice();
    var heroSeat = spot.hero_seat;
    return (spot.stacks || []).map(function (_, i) { return i; })
      .filter(function (i) { return i !== heroSeat; });
  }

  function cardBacks(container, n) {
    clear(container);
    for (var i = 0; i < n; i++) {
      var b = el("span", "card back"); b.setAttribute("aria-hidden", "true"); container.appendChild(b);
    }
  }

  function renderVillains(spot) {
    var felt = $("table-felt");
    var villains = villainSeats(spot);
    var nCards = (spot.hero_hand_str || []).length;
    var stacks = spot.stacks || [];
    // Drop seats created for a previous multiway spot.
    Array.prototype.forEach.call(felt.querySelectorAll(".seat.extra-villain"), function (n) { n.remove(); });
    felt.classList.remove("players-2", "players-3", "players-many");
    var players = villains.length + 1;
    felt.classList.add(players <= 2 ? "players-2" : players === 3 ? "players-3" : "players-many");
    felt.dataset.players = String(players);

    var first = $("seat-villain");
    first.classList.remove("villain-left", "villain-right");
    var label = function (seat) {
      var txt = "Villain (P" + seat + ")";
      if (isNum(stacks[seat])) txt += " \u00b7 " + fmtNum(stacks[seat]);
      return txt;
    };
    if (!villains.length) {
      $("villain-name").textContent = "Villain";
      cardBacks(first.querySelector(".seat-cards"), nCards);
      return;
    }
    $("villain-name").textContent = label(villains[0]);
    first.dataset.seat = String(villains[0]);
    cardBacks(first.querySelector(".seat-cards"), nCards);
    if (villains.length > 1) first.classList.add("villain-left");
    var anchor = first;
    villains.slice(1).forEach(function (seat, k) {
      var node = el("div", "seat villain extra-villain" + (k === 0 ? " villain-right" : ""));
      node.id = "seat-villain-" + (k + 2);
      node.dataset.seat = String(seat);
      node.appendChild(el("div", "seat-name", label(seat)));
      var cards = el("div", "seat-cards");
      cardBacks(cards, nCards);
      node.appendChild(cards);
      felt.insertBefore(node, anchor.nextSibling);
      anchor = node;
    });
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
      if (isSized(a) && !seen[a.amount]) {
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
        chip.dataset.amount = String(amt);
        chip.setAttribute("aria-pressed", "false");
        chip.addEventListener("click", function () {
          $("action-size").value = String(amt);
          var idx = legalActions().findIndex(function (a) { return isSized(a) && a.amount === amt; });
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
    if (!keepSize && isSized(a)) {
      $("action-size").value = String(a.amount);
    }
    markPresets();
    updateControls();
  }

  function markPresets() {
    var a = state.selectedAction;
    var v = parseFloat($("action-size").value);
    Array.prototype.forEach.call($("size-presets").querySelectorAll(".size-preset"), function (chip) {
      var on = isSized(a) && Number(chip.dataset.amount) === v;
      chip.classList.toggle("selected", on);
      chip.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  // Indexes of legal actions whose normalized kind is in `kinds`, in kind-priority order.
  function indexesByKinds(kinds) {
    var acts = legalActions();
    var out = [];
    kinds.forEach(function (kind) {
      acts.forEach(function (a, i) { if (normKind(a.kind) === kind) out.push(i); });
    });
    return out;
  }

  // Select the first matching action; pressing the same key again cycles through
  // the matches (e.g. B: Raise 5 -> Raise 40 -> Raise 5).
  function selectByKinds(kinds) {
    var idxs = indexesByKinds(kinds);
    if (!idxs.length) return false;
    var cur = state.selectedAction ? legalActions().indexOf(state.selectedAction) : -1;
    var pos = idxs.indexOf(cur);
    selectAction(idxs[pos >= 0 ? (pos + 1) % idxs.length : 0]);
    return true;
  }

  function currentPlay() {
    var a = state.selectedAction;
    if (!a) return null;
    var amount = isNum(a.amount) ? a.amount : 0;
    if (isSized(a)) {
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
    $("action-controls").appendChild(el("span", "solving-inline", "Solving\u2026"));
    startSolving("Solving");
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
      stopSolving();
      setPending(false);
      // Controls were disabled while solving, which drops focus to <body> (e.g. after
      // "Next spot"). Hand it to the first action so the keyboard flow continues.
      if (focusLost()) {
        var first = $("action-controls").querySelector(".action-btn");
        focusEl(first || $("resolve-btn"));
      }
    });
  }

  function focusLost() {
    var a = document.activeElement;
    return !a || a === document.body || a === document.documentElement ||
      (a.disabled === true) || !document.contains(a);
  }

  function focusEl(node) {
    if (node && !node.disabled && typeof node.focus === "function") node.focus({ preventScroll: false });
  }

  // ---------------------------------------------------------------- submit
  function submitPlay() {
    if (state.pending || state.submitted || !state.selectedId || !state.selectedAction) return;
    var play, override;
    try { play = currentPlay(); override = solveOverride(); } catch (e) { showError(e.message); return; }
    showError("");
    if (!applyUser(false)) { showError("Fix the player name before submitting."); return; }
    var token = state.solveToken;
    var payload = withUser({ spot_id: state.selectedId, play: play });
    if (override) payload.solve = override;
    startSolving("Scoring");
    setPending(true);
    var ok = false;
    api("practice-submit-play", payload).then(function (data) {
      if (token !== state.solveToken) return;
      ok = true;
      var res = data.result || {};
      state.submitted = true;
      renderResult(res.score || {}, res.solved || {});
      if (Object.prototype.hasOwnProperty.call(res, "progress")) applySubmitProgress(res.progress);
      else { loadProgress(); loadLeaderboard(); }
    }).catch(function (err) {
      if (token !== state.solveToken) return;
      showError("Submit failed: " + err.message);
    }).then(function () {
      if (token !== state.solveToken) return;
      stopSolving();
      setPending(false);
      // Keep keyboard users in place: after a result go to "Next spot"; after a
      // failure back to "Submit" (both were disabled while scoring).
      focusEl(ok ? $("next-spot") : $("submit-play"));
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
      if (ev.target && (ev.target.id === "iterations-input" || ev.target.id === "user-input")) return;  // handled separately
      if (!typing && ev.target && ev.target.tagName === "BUTTON") {
        var isPick = ev.target.classList.contains("action-btn") || ev.target.classList.contains("size-preset");
        if (!isPick) return; // native activation (submit, re-solve, next)
        ev.preventDefault();
        if (!ev.target.disabled) ev.target.click(); // select the focused action first
        if (!$("submit-play").disabled) submitPlay();
        return;
      }
      if (!$("submit-play").disabled) { ev.preventDefault(); submitPlay(); }
      return;
    }
    if (typing) return;
    var k = String(key || "").toLowerCase();
    if (!Object.prototype.hasOwnProperty.call(KEY_KINDS, k)) return;
    if (selectByKinds(KEY_KINDS[k])) {
      ev.preventDefault();
      if (k === "b" && isSized(state.selectedAction) && !$("size-row").classList.contains("hidden")) {
        $("action-size").focus();       // B: edit the size next (Enter submits from there)
      } else {
        // Focus the selected button so Enter submits it and focus is never lost.
        var btn = $("action-controls").querySelector(".action-btn.selected");
        if (btn) btn.focus();
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
      loadLeaderboard();
    });
    $("street-filter").addEventListener("change", function (ev) {
      state.streetFilter = ev.target.value;
      renderSpotList();
      updateControls();
    });
    $("game-filter").addEventListener("change", function (ev) {
      state.gameFilter = ev.target.value;
      renderSpotList();
      updateControls();
    });
    var userInput = $("user-input");
    userInput.value = readStoredUser();
    if (userInput.value && !USER_RE.test(userInput.value)) userInput.value = "";
    applyUser(false);
    userInput.addEventListener("change", function () { applyUser(true); });
    userInput.addEventListener("input", function () {
      var raw = userInput.value.trim();
      setUserHint(raw && !USER_RE.test(raw) ? "Name: 1\u201332 of A\u2013Z a\u2013z 0\u20139 _ . -" : "");
    });
    userInput.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") { ev.preventDefault(); applyUser(true); }
    });
    $("progress-refresh").addEventListener("click", function () { loadProgress(); });
    $("leaderboard-refresh").addEventListener("click", function () { loadLeaderboard(); });
    $("action-size").addEventListener("input", function () {
      // Typing a size implies a sized action. An exact legal amount selects that
      // action; any other size keeps the current bet/raise (server snaps it) or
      // picks the first one.
      if (state.submitted || state.pending) return;
      var v = parseFloat($("action-size").value);
      var acts = legalActions();
      var exact = isFinite(v) ? acts.findIndex(function (a) { return isSized(a) && a.amount === v; }) : -1;
      if (exact >= 0) { selectAction(exact, true); return; }
      var sel = state.selectedAction;
      if (isSized(sel)) { markPresets(); return; }
      var idx = acts.findIndex(isSized);
      if (idx >= 0) selectAction(idx, true);
    });
    document.addEventListener("keydown", onKey);
    updateControls();
    loadSpots();
    loadProgress();
    loadLeaderboard();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
