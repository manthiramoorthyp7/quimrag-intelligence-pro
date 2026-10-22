#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
command -v tesseract >/dev/null || echo "Tip: brew install tesseract  (needed only for scanned-PDF OCR)"
streamlit run app.py
