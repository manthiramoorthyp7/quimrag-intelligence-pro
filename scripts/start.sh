#!/usr/bin/env bash
# Starts backend + frontend, binds to 127.0.0.1 by default (override with
# QUIMRAG_HOST to expose it -- never done automatically). Idempotent: if a
# healthy instance this script started is already running, it says so and
# exits rather than starting a second one. Never kills a process it did not
# start itself to free a port -- a genuine conflict is reported with the
# exact recovery command, not resolved automatically.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv

check_already_running() {
  local pid_file="$1" name="$2" port="$3"
  if [ -f "$pid_file" ]; then
    local pid; pid="$(cat "$pid_file")"
    if pid_alive "$pid"; then
      say "$name already running (pid $pid, port $port) -- started by this script previously. Not starting a second instance."
      return 0
    else
      say "$name pid file is stale (process $pid is gone) -- cleaning up."
      rm -f "$pid_file"
    fi
  fi
  return 1
}

start_backend() {
  if check_already_running "$BACKEND_PID_FILE" "Backend" "$BACKEND_PORT"; then return; fi
  if port_in_use "$BACKEND_PORT"; then
    err "Port $BACKEND_PORT is already in use by a process this script did not start."
    err "Either stop that process, or set QUIMRAG_BACKEND_PORT=<other port> and re-run this script."
    exit 1
  fi
  say "Starting backend on http://$BACKEND_HOST:$BACKEND_PORT ..."
  (
    cd "$ROOT_DIR"
    set -a; [ -f .env ] && source .env; set +a
    exec "$VENV_DIR/bin/uvicorn" backend.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
  ) >>"$BACKEND_LOG" 2>&1 &
  echo $! >"$BACKEND_PID_FILE"
  disown

  say "Waiting for backend health check..."
  for _ in $(seq 1 60); do
    if curl -s -o /dev/null -m 2 "http://$BACKEND_HOST:$BACKEND_PORT/health"; then
      say ""
      say "Backend is up: http://$BACKEND_HOST:$BACKEND_PORT (pid $(cat "$BACKEND_PID_FILE"))"
      return
    fi
    printf '.'
    sleep 1
  done
  say ""
  err "Backend did not become healthy within 60s. Check $BACKEND_LOG for the actual error:"
  tail -n 30 "$BACKEND_LOG" >&2 || true
  exit 1
}

start_frontend() {
  if check_already_running "$FRONTEND_PID_FILE" "Frontend" "$FRONTEND_PORT"; then return; fi
  if port_in_use "$FRONTEND_PORT"; then
    err "Port $FRONTEND_PORT is already in use by a process this script did not start."
    err "Either stop that process, or set QUIMRAG_FRONTEND_PORT=<other port> and re-run this script."
    exit 1
  fi
  say "Starting frontend on http://$BACKEND_HOST:$FRONTEND_PORT ..."
  (
    cd "$ROOT_DIR/frontend"
    exec "$VENV_DIR/bin/python" -m http.server "$FRONTEND_PORT" --bind "$BACKEND_HOST"
  ) >>"$FRONTEND_LOG" 2>&1 &
  echo $! >"$FRONTEND_PID_FILE"
  disown
  sleep 1
  if curl -s -o /dev/null -m 2 "http://$BACKEND_HOST:$FRONTEND_PORT/"; then
    say "Frontend is up: http://$BACKEND_HOST:$FRONTEND_PORT (pid $(cat "$FRONTEND_PID_FILE"))"
  else
    err "Frontend did not respond. Check $FRONTEND_LOG."
    exit 1
  fi
}

say "== QuIM-RAG Intelligence Pro -- start =="
start_backend
start_frontend

say "\nApplication URL:  http://$BACKEND_HOST:$FRONTEND_PORT"
say "Backend API:       http://$BACKEND_HOST:$BACKEND_PORT  (docs at /docs, health at /health)"
say "Logs:              $BACKEND_LOG , $FRONTEND_LOG"
say "Stop with:         ./scripts/stop.sh"
