"""Backend settings, read from environment variables with safe local-dev
defaults. No secret is hardcoded -- API_KEY, if auth is enabled, must come
from the environment (see security.py)."""
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SQLite by default (ARCHITECTURE_DECISIONS.md #3). Set DATABASE_URL to a
# postgresql+psycopg://... URL to use the optional Postgres/pgvector profile
# instead -- no code change needed, SQLAlchemy handles both via the same models.
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/data/quimrag.db")

UPLOAD_DIR = os.environ.get("QUIMRAG_UPLOAD_DIR", f"{PROJECT_ROOT}/data/uploads")

# Auth is OFF by default for the single-machine/local deployment target
# (ARCHITECTURE_DECISIONS.md #6). Set QUIMRAG_API_KEY to require
# `Authorization: Bearer <key>` on every request except /health.
API_KEY = os.environ.get("QUIMRAG_API_KEY", "")
AUTH_ENABLED = bool(API_KEY)

MAX_UPLOAD_BYTES = int(os.environ.get("QUIMRAG_MAX_UPLOAD_BYTES", 25 * 1024 * 1024))  # 25 MB default
MAX_PAGE_COUNT = int(os.environ.get("QUIMRAG_MAX_PAGE_COUNT", 500))
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}

DEFAULT_WORKSPACE_ID = "default"
DEFAULT_OWNER_ID = "local-user"

# Generation provider: "local" (Ollama, default), "extractive" (no model call
# at all), or "anthropic" (requires ANTHROPIC_API_KEY to be set explicitly --
# never used implicitly, per Phase 7's "never silently send private documents
# to an external API").
GENERATION_PROVIDER = os.environ.get("QUIMRAG_GENERATION_PROVIDER", "local")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

EAR_CALIBRATION_PATH = os.environ.get(
    "QUIMRAG_EAR_MODEL_PATH", f"{PROJECT_ROOT}/research/data/ear_calibration_v2.json"
)

RETRIEVAL_K = int(os.environ.get("QUIMRAG_RETRIEVAL_K", 5))
