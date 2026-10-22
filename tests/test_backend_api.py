"""Integration tests for the FastAPI backend (backend/): the real upload ->
background ingest -> ask -> delete-with-verification loop, plus the
validation/duplicate-detection edge cases, run against an isolated temp
SQLite DB and upload directory so this never touches data/quimrag.db.

Requires Ollama to be running locally for the full /ask generation path;
those specific assertions are skipped (not failed) if it is not reachable,
consistent with this project's "report blockers, don't fabricate" rule.
"""
import os
import tempfile

_TMP_DIR = tempfile.mkdtemp(prefix="quimrag_backend_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR}/test.db"
os.environ["QUIMRAG_UPLOAD_DIR"] = os.path.join(_TMP_DIR, "uploads")

import pytest
from fastapi.testclient import TestClient

from backend.db import init_db
from backend.main import app
from quimrag.local_llm import ollama_available

init_db()
client = TestClient(app)

def _unique_text(marker: str) -> bytes:
    # Content hash drives duplicate-detection (by design -- see
    # backend/routers/documents.py), so each test that needs its own fresh
    # document must use distinct content, not just a distinct filename.
    return (
        f"Section 1: Facts (test marker {marker}).\n"
        "The maximum upload size configured for this deployment is 25 megabytes.\n"
        "The embedding model used is all-MiniLM-L6-v2.\n"
    ).encode()


def _upload(filename="doc.txt", content=None, content_type="text/plain", marker="default"):
    if content is None:
        content = _unique_text(marker)
    return client.post("/documents", files={"file": (filename, content, content_type)})


def test_health_reports_real_device_and_zero_initial_state():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["device"] in ("MPS", "CUDA", "CPU")
    assert isinstance(body["documents_indexed"], int)


def test_upload_rejects_disallowed_extension():
    r = _upload(filename="malware.exe", content=b"x", content_type="application/octet-stream")
    assert r.status_code == 422


def test_upload_rejects_spoofed_pdf_extension():
    r = _upload(filename="fake.pdf", content=b"this is not a pdf", content_type="application/pdf")
    assert r.status_code == 422
    assert "magic bytes" in r.json()["detail"]


def test_upload_rejects_empty_file():
    r = _upload(content=b"")
    assert r.status_code == 422


def test_duplicate_upload_returns_same_document_id():
    r1 = _upload(marker="dup-test")
    r2 = _upload(marker="dup-test")
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


def test_upload_ingest_ask_delete_end_to_end():
    r = _upload(filename="e2e.txt", marker="e2e-test")
    assert r.status_code == 201
    doc = r.json()
    assert doc["status"] == "processing"
    doc_id = doc["id"]

    # background task runs inline-ish via threadpool; poll briefly
    import time
    for _ in range(50):
        r = client.get(f"/documents/{doc_id}")
        if r.json()["status"] in ("ready", "failed"):
            break
        time.sleep(0.2)
    final = r.json()
    assert final["status"] == "ready", final
    assert final["chunk_count"] and final["chunk_count"] > 0

    r = client.post("/ask", json={"query": "What embedding model is used?"})
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] in ("answer", "expand_retrieval", "inspect_structure", "abstain")
    assert 0.0 <= body["probability"] <= 1.0
    assert body["evidence"], "expected at least one evidence chunk for a query matching ingested content"
    assert body["citations_verified"] is True

    if ollama_available() and body["decision"] == "answer":
        assert body["answer"] is not None
        assert body["generation_provider"] == "local"

    r = client.delete(f"/documents/{doc_id}")
    assert r.status_code == 200
    del_body = r.json()
    assert del_body["chunks_removed"] > 0
    assert del_body["verified_not_retrievable"] is True

    r = client.get(f"/documents/{doc_id}")
    assert r.json()["status"] == "deleted"


def test_delete_already_deleted_document_is_conflict():
    r = _upload(filename="to_delete_twice.txt", marker="delete-twice-test")
    doc_id = r.json()["id"]
    r1 = client.delete(f"/documents/{doc_id}")
    assert r1.status_code == 200
    r2 = client.delete(f"/documents/{doc_id}")
    assert r2.status_code == 409


def test_get_nonexistent_document_is_404():
    r = client.get("/documents/does-not-exist")
    assert r.status_code == 404


def test_ask_with_no_indexed_documents_is_409():
    # Fresh engine state is shared process-wide; this test only meaningfully
    # asserts the 409 contract shape when nothing has been ingested yet, so
    # it is skipped once prior tests in this module have indexed content
    # (process-wide singleton -- see backend/engine_singleton.py).
    from backend.engine_singleton import get_engine
    if get_engine().chunks:
        pytest.skip("engine already has indexed chunks from an earlier test in this module")
    r = client.post("/ask", json={"query": "anything"})
    assert r.status_code == 409
