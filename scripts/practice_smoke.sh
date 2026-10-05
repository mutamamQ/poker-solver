#!/usr/bin/env bash
# Practice-mode smoke test: start the server, hit health/list/solve/submit, print PASS/FAIL.
# Usage: scripts/practice_smoke.sh [PORT]   (default 7787; env PYTHON overrides interpreter)
set -u

PORT="${1:-7787}"
HOST="127.0.0.1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-$ROOT/.venv/bin/python}"
BASE="http://$HOST:$PORT"
LOG="$(mktemp -t practice-smoke.XXXXXX.log)"
PASS=0
FAIL=0

cleanup() {
    if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null
        wait "$SERVER_PID" 2>/dev/null
    fi
    rm -f "$LOG"
}
trap cleanup EXIT

check() {  # check NAME CONDITION_EXIT_CODE [detail]
    if [[ "$2" == 0 ]]; then
        echo "PASS  $1"
        PASS=$((PASS + 1))
    else
        echo "FAIL  $1 ${3:-}"
        FAIL=$((FAIL + 1))
    fi
}

api() {  # api OPERATION PAYLOAD_JSON
    curl -sS -m 60 -X POST -H 'Content-Type: application/json' \
        --data "{\"version\":4,\"operation\":\"$1\",\"payload\":$2}" "$BASE/api/v4"
}

jget() {  # jget JSON PYTHON_EXPR_ON_d
    printf '%s' "$1" | "$PY" -c "import json,sys; d=json.load(sys.stdin); print($2)"
}

PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}" \
    "$PY" -m poker_solver.practice.server --host "$HOST" --port "$PORT" >"$LOG" 2>&1 &
SERVER_PID=$!

for _ in $(seq 1 100); do
    grep -q "Practice server on http://$HOST:$PORT/" "$LOG" 2>/dev/null && break
    kill -0 "$SERVER_PID" 2>/dev/null || break
    sleep 0.1
done
grep -q "Practice server on http://$HOST:$PORT/" "$LOG"
check "startup banner" $? "$(cat "$LOG")"

HEALTH="$(curl -sS -m 10 "$BASE/api/health" 2>&1)"
[[ "$HEALTH" == '{"ok":true}' ]]
check "GET /api/health" $? "$HEALTH"

FAV="$(curl -s -o /dev/null -w '%{http_code}' -m 10 "$BASE/favicon.ico")"
[[ "$FAV" == 204 ]]
check "GET /favicon.ico -> 204" $? "got $FAV"

LIST="$(api practice-list-spots '{}')"
SPOT="$(jget "$LIST" "[s['spot_id'] for s in d['result']['spots'] if s['family'].startswith('river')][0]" 2>/dev/null)"
[[ -n "$SPOT" ]]
check "practice-list-spots (river spot: ${SPOT:-none})" $? "$(printf '%.200s' "$LIST")"

SOLVE="$(api practice-solve-spot "{\"spot_id\":\"$SPOT\",\"solve\":{\"iterations\":40}}")"
OK="$(jget "$SOLVE" "abs(sum(x['probability'] for x in d['result']['strategy'])-1)<1e-6 and d['result']['provenance']['iterations']==40" 2>/dev/null)"
[[ "$OK" == True ]]
check "practice-solve-spot (strategy sums to 1, iterations=40)" $? "$(printf '%.200s' "$SOLVE")"

PLAY="$(jget "$SOLVE" "json.dumps(d['result']['optimal_action'])" 2>/dev/null)"
SUBMIT="$(api practice-submit-play "{\"spot_id\":\"$SPOT\",\"play\":${PLAY:-null},\"solve\":{\"iterations\":40}}")"
GRADE="$(jget "$SUBMIT" "'%s %s' % (d['result']['score']['grade'], d['result']['score']['score'])" 2>/dev/null)"
[[ "$GRADE" =~ ^(Perfect|Good|Inaccuracy|Mistake|Blunder)\  ]]
check "practice-submit-play (grade/score: ${GRADE:-none})" $? "$(printf '%.200s' "$SUBMIT")"

if [[ -f "$ROOT/web/index.html" ]]; then
    CODE="$(curl -s -o /dev/null -w '%{http_code}' -m 10 "$BASE/")"
    [[ "$CODE" == 200 ]]
    check "GET / (index.html)" $? "got $CODE"
fi

echo "----"
if [[ "$FAIL" == 0 ]]; then
    echo "SMOKE PASS ($PASS checks)"
    exit 0
fi
echo "SMOKE FAIL ($FAIL failed, $PASS passed)"
exit 1
