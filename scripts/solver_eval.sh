#!/usr/bin/env bash
# Solver-evaluation benchmark wrapper.
# Usage: scripts/solver_eval.sh [quick|full] [OUT_DIR]
#   quick (default): < 2 min, writes to a temp dir unless OUT_DIR is given.
#   full: the canonical run; writes research/solver-evaluation/results.{json,md} unless OUT_DIR is given.
# Env PYTHON overrides the interpreter (default: repo .venv).
set -euo pipefail

MODE="${1:-quick}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-$ROOT/.venv/bin/python}"
case "$MODE" in
    quick) OUT="${2:-$(mktemp -d -t solver-eval.XXXXXX)}" ;;
    full)  OUT="${2:-$ROOT/research/solver-evaluation}" ;;
    *) echo "usage: $0 [quick|full] [OUT_DIR]" >&2; exit 2 ;;
esac

# Keep any practice solve cache/progress writes out of the user's home directories.
export POKER_PRACTICE_CACHE_DIR="${POKER_PRACTICE_CACHE_DIR:-$(mktemp -d -t solver-eval-cache.XXXXXX)}"
export POKER_PRACTICE_DATA_DIR="${POKER_PRACTICE_DATA_DIR:-$POKER_PRACTICE_CACHE_DIR}"

"$PY" "$ROOT/research/solver-evaluation/benchmark.py" --mode "$MODE" --out "$OUT"
echo "results: $OUT/results.json  $OUT/results.md"
