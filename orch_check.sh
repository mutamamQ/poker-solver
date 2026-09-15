#!/usr/bin/env bash
# Poker-solver orchestrator status check — gathers state for a 30-min health poll.
W=/home/genomix-node/poker-solver
LOG=~/.hermes/logs/agent.log

if tmux has-session -t pokerorch 2>/dev/null; then
  PANE=$(tmux capture-pane -t pokerorch -p 2>/dev/null)
  if printf '%s' "$PANE" | grep -qE 'EXITCODE='; then
    ORCH=EXITED
    CODE=$(printf '%s' "$PANE" | grep -oE 'EXITCODE=[0-9]+' | tail -1)
  else
    ORCH=RUNNING
  fi
else
  ORCH=DEAD
fi

echo "ORCH_STATE=$ORCH ${CODE:-}"

echo "--- PANE_TAIL (last 12 lines) ---"
tmux capture-pane -t pokerorch -p 2>/dev/null | grep -vE '^\s*$' | tail -12

echo "--- WORKSPACE ---"
echo "research_files=$(find $W/research -name '*.md' 2>/dev/null | wc -l)"
echo "review_files=$(find $W/review -type f 2>/dev/null | wc -l)"
echo "python_files=$(find $W -name '*.py' -not -path '*/.venv/*' 2>/dev/null | wc -l)"
for f in ARCHITECTURE.md README.md SWARM_REPORT.md PROGRESS.md pytest.ini pyproject.toml; do
  [ -f "$W/$f" ] && echo "PRESENT: $f"
done
find $W -maxdepth 2 -name 'test_*.py' -o -maxdepth 2 -name '*_test.py' 2>/dev/null | head -15

echo "--- LATEST_LOG_TAIL (last 8 relevant) ---"
grep -aE 'delegate|subagent|bryant|ERROR|WARNING.*approval|pytest' "$LOG" 2>/dev/null | tail -8

echo "--- ERROR_SIGNALS_IN_PANE ---"
printf '%s' "$PANE" | grep -nE '⚠|✗|error|Error|interrupt|Interrupted|blocked|denied' | tail -10
echo "--- END ---"
