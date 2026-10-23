#!/usr/bin/env bash
# Runs this project's research/benchmark scripts -- entirely separate from
# the live chat backend: every script here builds its own in-memory
# QuIMRAG() engine from research/data/*.csv (the locked, document-disjoint
# calibration/evaluation splits), never touching data/quimrag.db or
# data/uploads/ (the live backend's user documents and database). You can
# run this while scripts/start.sh's backend is serving real chat traffic
# without the two interfering -- they share no process, lock, or state.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
cd "$ROOT_DIR"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1

MODE="${1:-}"
usage() {
  cat <<EOF
Usage: ./scripts/run_evaluation.sh <mode>

  quick   Baseline retrieval + EAR selective-prediction only (~2 min).
          research/run_benchmark_v2.py

  full    Everything in 'quick', plus RVQ compression/recall analysis,
          OCR-robustness severity sweep, advanced statistics (ROC-AUC,
          calibration, power analysis), and EAR v2 (~5-8 min, no LLM calls).
          research/run_rvq_analysis.py, research/run_ocr_robustness.py,
          research/PUBLICATION_PACKAGE/compute_advanced_stats.py,
          research/PUBLICATION_PACKAGE/ear_v2_innovation.py

  eiic    The Evidence Integrity Intervention Controller experiment --
          SLOW (20-40+ min): makes real local-LLM generation and judge
          calls for every answered query in both splits. Requires Ollama
          running. research/eval_expanded/run_eiic_experiment.py

  all     quick + full + eiic, sequentially.

Results are written to research/experiments/ (quick/full) and
technical_documentation/results/ (eiic), never into data/ (the live
application's own document/database storage).
EOF
}

run_quick() { say "\n>> research/run_benchmark_v2.py"; "$VENV_DIR/bin/python" research/run_benchmark_v2.py; }
run_full() {
  run_quick
  say "\n>> research/run_rvq_analysis.py"; "$VENV_DIR/bin/python" research/run_rvq_analysis.py
  say "\n>> research/run_ocr_robustness.py"; "$VENV_DIR/bin/python" research/run_ocr_robustness.py
  say "\n>> research/PUBLICATION_PACKAGE/compute_advanced_stats.py"; "$VENV_DIR/bin/python" research/PUBLICATION_PACKAGE/compute_advanced_stats.py
  say "\n>> research/PUBLICATION_PACKAGE/ear_v2_innovation.py"; "$VENV_DIR/bin/python" research/PUBLICATION_PACKAGE/ear_v2_innovation.py
}
run_eiic() {
  if ! curl -s -o /dev/null -m 2 http://localhost:11434/api/tags; then
    err "Ollama is not reachable at http://localhost:11434 -- the EIIC experiment requires real local LLM "
    err "generation and judge calls and will not produce meaningful results without it. Install/start Ollama first."
    exit 1
  fi
  say "\n>> research/eval_expanded/run_eiic_experiment.py (this will take a while -- real LLM calls per claim)"
  "$VENV_DIR/bin/python" research/eval_expanded/run_eiic_experiment.py
}

case "$MODE" in
  quick) run_quick ;;
  full) run_full ;;
  eiic) run_eiic ;;
  all) run_full; run_eiic ;;
  *) usage; exit 1 ;;
esac

say "\nDone. See research/experiments/ and technical_documentation/results/ for output files."
