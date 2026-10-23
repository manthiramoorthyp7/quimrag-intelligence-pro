#!/usr/bin/env bash
# Shared helpers sourced by every script in this directory. Never executed
# directly. Resolves the project root relative to this file's own location
# so every script works regardless of the caller's current directory --
# never hardcodes an absolute, machine-specific path.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"

BACKEND_HOST="${QUIMRAG_HOST:-127.0.0.1}"
BACKEND_PORT="${QUIMRAG_BACKEND_PORT:-8000}"
FRONTEND_PORT="${QUIMRAG_FRONTEND_PORT:-8080}"

BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

say() { printf '%b\n' "$1"; }
err() { printf 'ERROR: %s\n' "$1" >&2; }

port_in_use() {
  # True if something is listening on $1 -- lsof is standard on macOS,
  # no extra dependency needed.
  lsof -iTCP -sTCP:LISTEN -P 2>/dev/null | grep -q ":$1 (LISTEN)"
}

pid_alive() {
  [ -n "${1:-}" ] && kill -0 "$1" 2>/dev/null
}

require_venv() {
  if [ ! -x "$VENV_DIR/bin/python" ]; then
    err "No virtualenv at $VENV_DIR -- run scripts/setup.sh first."
    exit 1
  fi
}
