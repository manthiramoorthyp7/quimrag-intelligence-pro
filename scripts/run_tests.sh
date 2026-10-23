#!/usr/bin/env bash
# Runs the full pytest suite. Does not require the app to be running --
# tests use their own in-process FastAPI TestClient / temp SQLite DB, never
# the live data/quimrag.db. Separate from run_evaluation.sh on purpose:
# this is fast (~2 min) correctness testing; evaluation is slow benchmarking.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
cd "$ROOT_DIR"
say "== QuIM-RAG Intelligence Pro -- test suite =="
exec "$VENV_DIR/bin/python" -m pytest -q "$@"
