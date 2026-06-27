"""Tests E2E del endpoint POST /api/analyze."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.repositories import InMemoryAnalysisRepository


def test_analyze_returns_200_with_valid_payload(client: TestClient) -> None:
    r = client.post(
        "/api/analyze",
        json={
            "content": "Estimado cliente, verifique su cuenta ya.",
            "input_type": "email",
            "language": "es",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["language"] == "es"
    assert 0 <= body["risk_score"] <= 100
    assert body["verdict"] in {"legit", "suspicious", "phishing"}
    assert isinstance(body["indicators"], list)


def test_analyze_persists_through_endpoint(
    client: TestClient, in_memory_repo: InMemoryAnalysisRepository
) -> None:
    client.post(
        "/api/analyze",
        json={"content": "ping", "input_type": "sms", "language": "en"},
    )
    assert len(in_memory_repo.items) == 1
    assert in_memory_repo.items[0]["input_type"] == "sms"


def test_analyze_rejects_invalid_input_type(client: TestClient) -> None:
    r = client.post(
        "/api/analyze",
        json={"content": "x", "input_type": "carrier_pigeon", "language": "es"},
    )
    assert r.status_code == 422


def test_analyze_rejects_empty_content(client: TestClient) -> None:
    r = client.post(
        "/api/analyze",
        json={"content": "", "input_type": "email", "language": "es"},
    )
    assert r.status_code == 422


def test_analyze_defaults_language_to_es(client: TestClient) -> None:
    r = client.post(
        "/api/analyze",
        json={"content": "algo", "input_type": "email"},
    )
    assert r.status_code == 200
    assert r.json()["language"] == "es"
