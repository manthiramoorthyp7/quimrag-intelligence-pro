"""SQLAlchemy engine/session setup. Works unmodified against either the
default SQLite URL or an optional Postgres+pgvector DATABASE_URL -- see
config.py and docs/production/ARCHITECTURE_DECISIONS.md #3."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from . import config

os.makedirs(os.path.dirname(config.UPLOAD_DIR), exist_ok=True)
os.makedirs(config.UPLOAD_DIR, exist_ok=True)

connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(config.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db():
    from . import models  # noqa: F401 -- registers models on Base.metadata
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
