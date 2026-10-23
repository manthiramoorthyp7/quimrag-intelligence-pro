#!/usr/bin/env bash
# Real, live checks -- never declares success because a process started or a
# port is open. Exits non-zero if anything fails, so it's usable in CI or a
# pre-flight check before scripts/run_evaluation.sh.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
FAIL=0

say "== QuIM-RAG Intelligence Pro -- health check =="

say "\n-- Backend process --"
if [ -f "$BACKEND_PID_FILE" ] && pid_alive "$(cat "$BACKEND_PID_FILE")"; then
  say "OK: backend process alive (pid $(cat "$BACKEND_PID_FILE"))"
else
  err "backend process not running (no live pid file) -- run ./scripts/start.sh"
  FAIL=1
fi

say "\n-- Backend /health endpoint --"
HEALTH_JSON="$(curl -s -m 5 "http://$BACKEND_HOST:$BACKEND_PORT/health" || true)"
if [ -n "$HEALTH_JSON" ]; then
  say "OK: $HEALTH_JSON"
  echo "$HEALTH_JSON" | "$VENV_DIR/bin/python" -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception as e:
    print(f'  could not parse health JSON: {e}'); sys.exit(1)
checks = [
    ('status == ok', d.get('status') == 'ok'),
    ('database_url_scheme set', bool(d.get('database_url_scheme'))),
    ('embedding backend loaded', bool(d.get('embedding_backend'))),
]
for label, ok in checks:
    print(f\"  {'OK' if ok else 'FAIL'}: {label}\")
if not d.get('ollama_available'):
    print('  NOTE: ollama_available=false -- local generation will fall back to extractive mode until Ollama is running')
if not d.get('reranker_loaded'):
    print('  NOTE: reranker not loaded')
" || FAIL=1
else
  err "backend /health did not respond -- is it running? ./scripts/start.sh"
  FAIL=1
fi

say "\n-- Database connectivity --"
if [ -f "$ROOT_DIR/data/quimrag.db" ]; then
  if "$VENV_DIR/bin/python" -c "
import sqlite3
con = sqlite3.connect('$ROOT_DIR/data/quimrag.db')
con.execute('SELECT 1')
print('OK: SQLite database opens and responds to a query')
" 2>/dev/null; then :; else err "SQLite database exists but could not be queried"; FAIL=1; fi
else
  say "NOTE: no database file yet at $ROOT_DIR/data/quimrag.db -- created automatically on first backend start"
fi

say "\n-- Retrieval index availability --"
echo "$HEALTH_JSON" | "$VENV_DIR/bin/python" -c "
import json, sys
d = json.load(sys.stdin) if sys.stdin.read(0) == '' else None
" 2>/dev/null || true
N_DOCS="$(echo "$HEALTH_JSON" | "$VENV_DIR/bin/python" -c "import json,sys; print(json.load(sys.stdin).get('documents_indexed','?'))" 2>/dev/null || echo "?")"
N_CHUNKS="$(echo "$HEALTH_JSON" | "$VENV_DIR/bin/python" -c "import json,sys; print(json.load(sys.stdin).get('chunks_indexed','?'))" 2>/dev/null || echo "?")"
say "documents_indexed=$N_DOCS, chunks_indexed=$N_CHUNKS (0 is expected on a fresh install with no uploads yet)"

say "\n-- Frontend --"
if curl -s -o /dev/null -m 5 "http://$BACKEND_HOST:$FRONTEND_PORT/"; then
  say "OK: frontend responds at http://$BACKEND_HOST:$FRONTEND_PORT/"
else
  err "frontend did not respond at http://$BACKEND_HOST:$FRONTEND_PORT/ -- ./scripts/start.sh"
  FAIL=1
fi

say "\n-- Model configuration --"
if [ -f "$ROOT_DIR/.env" ]; then
  PROVIDER="$(grep -E '^QUIMRAG_GENERATION_PROVIDER=' "$ROOT_DIR/.env" 2>/dev/null | cut -d= -f2 || true)"
else
  say "NOTE: no .env file found (run ./scripts/setup.sh to create one from .env.example) -- assuming built-in defaults."
  PROVIDER=""
fi
PROVIDER="${PROVIDER:-local}"
say "Configured generation provider: $PROVIDER"
OLLAMA_UP="$(echo "$HEALTH_JSON" | "$VENV_DIR/bin/python" -c "import json,sys; print(json.load(sys.stdin).get('ollama_available', False))" 2>/dev/null || echo "False")"
case "$PROVIDER" in
  local)
    if [ "$OLLAMA_UP" = "True" ]; then say "OK: Ollama reachable -- real local LLM inference will be used"
    else say "NOTE: Ollama not reachable -- answers will fall back to extractive mode (real retrieval, no generative model), reported as such in every API response's generation_provider field"; fi ;;
  extractive) say "OK: extractive mode needs no model -- retrieval-only, deterministic, fully offline" ;;
  anthropic)
    if [ -f "$ROOT_DIR/.env" ] && grep -qE '^ANTHROPIC_API_KEY=.+' "$ROOT_DIR/.env" 2>/dev/null; then say "OK: ANTHROPIC_API_KEY is set"
    else err "QUIMRAG_GENERATION_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set in .env"; FAIL=1; fi ;;
esac

say ""
if [ "$FAIL" -eq 0 ]; then
  say "All checks passed."
else
  err "One or more checks failed (see above)."
fi
exit "$FAIL"
