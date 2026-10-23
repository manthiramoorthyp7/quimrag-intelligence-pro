#!/usr/bin/env bash
# Prepares the environment: checks the host, creates/repairs the virtualenv,
# installs dependencies, and creates data directories. Safe to re-run --
# never deletes an existing .venv, never overwrites .env if one already
# exists. Does not touch any other project or process on the machine.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

say "== QuIM-RAG Intelligence Pro -- setup =="
say "Project root: $ROOT_DIR"

say "\n-- Host --"
say "OS: $(uname -s) $(uname -r) ($(uname -m))"
PYVER="$(python3 --version 2>&1 || true)"
say "Python: $PYVER"
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  err "Python 3.10+ is required. Found: $PYVER"
  exit 1
fi
RAM_GB="$(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%.0f", $1/1073741824}' || echo unknown)"
say "RAM: ${RAM_GB} GB"
DISK_AVAIL="$(df -h "$ROOT_DIR" | tail -1 | awk '{print $4}')"
say "Disk available at project root: $DISK_AVAIL"
if command -v system_profiler >/dev/null 2>&1; then
  CHIP="$(system_profiler SPHardwareDataType 2>/dev/null | awk -F': ' '/Chip|Processor Name/{print $2; exit}')"
  say "Chip: ${CHIP:-unknown} (Apple Silicon uses PyTorch MPS automatically -- no CUDA assumed anywhere in this project)"
fi

say "\n-- Virtualenv --"
if [ -x "$VENV_DIR/bin/python" ]; then
  say "Existing virtualenv found at $VENV_DIR -- reusing it (not deleted)."
else
  say "Creating virtualenv at $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
fi

say "\n-- Dependencies --"
"$VENV_DIR/bin/pip" install --upgrade pip -q
if ! "$VENV_DIR/bin/pip" install -r "$ROOT_DIR/requirements.txt" -r "$ROOT_DIR/requirements-dev.txt"; then
  err "Dependency installation failed. Common causes on Apple Silicon:"
  err "  - A package without an arm64 wheel: check the failing package's output above for the exact name,"
  err "    then try 'arch -arm64 \"$VENV_DIR/bin/pip\" install <package>' or check for a newer version."
  err "  - Xcode command line tools missing (needed to build some packages from source):"
  err "    run 'xcode-select --install'."
  exit 1
fi
say "Dependencies installed."

say "\n-- Data directories --"
mkdir -p "$ROOT_DIR/data/uploads"
say "Ready: $ROOT_DIR/data/uploads (document storage), $ROOT_DIR/data/quimrag.db (SQLite, created on first run)"

say "\n-- Configuration --"
if [ -f "$ROOT_DIR/.env" ]; then
  say ".env already exists -- left untouched."
else
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  say "Created .env from .env.example. Edit it if you need non-default settings (auth key, Anthropic key, etc.)."
fi

say "\n-- Ollama (local LLM, default generation provider) --"
if command -v ollama >/dev/null 2>&1 && curl -s -o /dev/null -m 2 http://localhost:11434/api/tags; then
  say "Ollama is installed and running. Installed models:"
  curl -s http://localhost:11434/api/tags | "$VENV_DIR/bin/python" -c "import json,sys; print('\n'.join('  - '+m['name'] for m in json.load(sys.stdin).get('models',[])))" 2>/dev/null || true
else
  say "Ollama is not reachable at http://localhost:11434."
  say "  Install it from https://ollama.com, then run: ollama pull llama3.2"
  say "  Without it, QUIMRAG_GENERATION_PROVIDER=extractive still works fully offline with no model download."
fi

say "\n-- Ports --"
for p in "$BACKEND_PORT" "$FRONTEND_PORT"; do
  if port_in_use "$p"; then
    say "  Port $p is currently in use -- scripts/start.sh will report this and let you pick another via QUIMRAG_BACKEND_PORT/QUIMRAG_FRONTEND_PORT."
  else
    say "  Port $p is free."
  fi
done

say "\nSetup complete. Next: ./scripts/start.sh"
