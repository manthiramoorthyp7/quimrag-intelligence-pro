# Installation

Every command below was actually run this session against the real backend (not just written) — see `docs/production/EXECUTION_LOG.md` for what "verified" means for each piece.

## 1. Local development (verified this session)

```bash
git clone <this repo> && cd quimrag-intelligence-pro-v2
git checkout production-platform   # this workstream's branch

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Required for any command that loads embedding/judge models -- without
# these, a HuggingFace Hub connectivity check can hang indefinitely even
# with all models already cached locally (a real, previously-diagnosed
# defect, not a hypothetical one).
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# Optional: start Ollama for real local-LLM generation (falls back to an
# extractive, citation-backed answer automatically if not running)
ollama serve &
ollama pull llama3.2:latest

# Start the API backend
.venv/bin/uvicorn backend.main:app --reload --port 8000
# -> http://127.0.0.1:8000/health, http://127.0.0.1:8000/docs (OpenAPI UI)

# In another terminal, serve the frontend
cd frontend && python3 -m http.server 8080
# -> http://127.0.0.1:8080/index.html
```

Verified this session: `/health` reports `device: MPS`, upload -> background ingestion -> `/ask` with a real Ollama-generated, citation-verified answer -> delete-with-verification, all exercised both via `curl` and by driving the actual frontend in a real browser (DataTransfer-injected file upload, clicked Upload/Ask/Delete, screenshots confirm correct rendering at each step).

## 2. Running the original Streamlit research console (unchanged)

```bash
.venv/bin/streamlit run app.py
```

## 3. Running the test suite

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/pytest -q
# -> 78 passed, 1 skipped (70 core library tests + 8 new backend API tests)
```

## 4. Docker (written this session, NOT yet verified — Docker is not installed in this environment)

```bash
cp .env.example .env    # edit as needed
docker compose up --build                     # API + frontend, SQLite
docker compose --profile console up --build   # + Streamlit research console
docker compose --profile postgres up --build  # + Postgres/pgvector instead of SQLite
```

**Explicit limitation, stated rather than hidden:** `docker`/`docker compose` are not installed on the machine this session ran on, so `Dockerfile`, `Dockerfile.api`, and `docker-compose.yml` have been written and their YAML syntax validated, but **no container has actually been built or run**. Treat this path as "prepared, not verified" until someone with Docker runs it — see `docs/production/EXECUTION_LOG.md`.

## 5. Configuration

See `.env.example` for every supported environment variable and `backend/config.py` for their defaults. Auth is off by default (single-machine target); set `QUIMRAG_API_KEY` to require it.
