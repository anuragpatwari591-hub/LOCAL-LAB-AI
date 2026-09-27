"""API integration tests using FastAPI's TestClient against the real app
(routes, memory, RAG). The inference engine is not expected to be running
in this environment (no model/binary in the isolated test root), so chat
is tested against that real, honest "engine not ready" behavior rather than
a mock pretending to be a language model.
"""

import io

import pytest
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "engine_running" in body


def test_diagnostics_reports_missing_model_honestly(client):
    resp = client.get("/api/diagnostics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["model"]["found"] is False  # isolated test root has no model
    assert "hardware" in body
    assert body["security"]["allow_code_execution"] is False
    assert body["security"]["loopback_only"] is True


def test_modes_endpoint_lists_all_modes(client):
    resp = client.get("/api/modes")
    assert resp.status_code == 200
    ids = {m["id"] for m in resp.json()}
    assert "exam" in ids and "os_lab" in ids and "dbms_oracle" in ids


def test_create_and_list_project(client):
    resp = client.post("/api/projects", json={"name": "SWE Project"})
    assert resp.status_code == 200
    assert "project_id" in resp.json()

    resp = client.get("/api/projects")
    names = [p["name"] for p in resp.json()]
    assert "SWE Project" in names


def test_chat_returns_service_unavailable_when_engine_not_running(client):
    resp = client.post("/api/chat", json={"message": "hello", "mode": "general"})
    assert resp.status_code == 503
    assert "engine" in resp.json()["detail"].lower()


def test_document_upload_and_search(client):
    content = b"Operating systems manage processes, memory, and file systems."
    files = {"file": ("notes.txt", io.BytesIO(content), "text/plain")}
    resp = client.post("/api/documents", files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["chunk_count"] >= 1

    resp = client.get("/api/documents/search", params={"q": "processes and memory"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1


def test_unsupported_document_type_rejected(client):
    files = {"file": ("virus.exe", io.BytesIO(b"binary"), "application/octet-stream")}
    resp = client.post("/api/documents", files=files)
    assert resp.status_code == 400


def test_frontend_index_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"LOCAL-LAB-AI" in resp.content


def test_memory_clear_endpoint(client):
    client.post("/api/projects", json={"name": "to be cleared"})
    resp = client.post("/api/memory/clear")
    assert resp.status_code == 200

    resp = client.get("/api/projects")
    assert resp.json() == []
