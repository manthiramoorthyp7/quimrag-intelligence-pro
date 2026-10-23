#!/usr/bin/env bash
# Gracefully stops exactly the processes this project's own scripts/start.sh
# started (by PID file), and nothing else -- never searches for or kills
# processes by name/port, which could hit an unrelated process.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

stop_one() {
  local pid_file="$1" name="$2"
  if [ ! -f "$pid_file" ]; then
    say "$name: not running (no pid file)."
    return
  fi
  local pid; pid="$(cat "$pid_file")"
  if ! pid_alive "$pid"; then
    say "$name: pid file present but process $pid is already gone -- cleaning up."
    rm -f "$pid_file"
    return
  fi
  say "Stopping $name (pid $pid) ..."
  kill -TERM "$pid" 2>/dev/null || true
  for _ in $(seq 1 10); do
    pid_alive "$pid" || break
    sleep 0.5
  done
  if pid_alive "$pid"; then
    say "$name did not exit after SIGTERM -- sending SIGKILL."
    kill -KILL "$pid" 2>/dev/null || true
  fi
  rm -f "$pid_file"
  say "$name stopped."
}

say "== QuIM-RAG Intelligence Pro -- stop =="
stop_one "$BACKEND_PID_FILE" "Backend"
stop_one "$FRONTEND_PID_FILE" "Frontend"
say "\nDocument storage and database are untouched (they live in $ROOT_DIR/data/) -- restarting with scripts/start.sh resumes with the same data."
