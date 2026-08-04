"""Smoke tests for the FastAPI app."""

from fastapi.testclient import TestClient

from free_claude_gateway.api.server import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Free Claude Gateway"
    assert "docs" in data
