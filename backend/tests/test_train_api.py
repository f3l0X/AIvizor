"""Tests E2E de los endpoints /api/train/{next,answer}."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def test_next_returns_public_sample_without_truth(client: TestClient) -> None:
    r = client.post(
        "/api/train/next",
        json={"difficulty": 1, "input_type": "email", "language": "es"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == {"id", "input_type", "language", "difficulty", "content"}
    assert body["difficulty"] == 1
    assert body["language"] == "es"
    # NUNCA debe filtrarse la verdad al cliente:
    assert "true_verdict" not in body
    assert "true_indicators" not in body


def test_full_loop_next_then_answer(client: TestClient) -> None:
    next_r = client.post(
        "/api/train/next",
        json={"difficulty": 1, "input_type": "email", "language": "es"},
    )
    sample = next_r.json()

    # Respuesta deliberadamente correcta para el mock L1 (phishing con 3 indicadores).
    answer_r = client.post(
        "/api/train/answer",
        json={
            "sample_id": sample["id"],
            "user_verdict": "phishing",
            "marked_indicator_types": [
                "lookalike_domain",
                "urgency_language",
                "brand_or_grammar_error",
            ],
        },
    )
    assert answer_r.status_code == 200, answer_r.text
    feedback = answer_r.json()
    assert feedback["correct"] is True
    assert feedback["score"] == 100
    assert feedback["next_difficulty"] == 2
    assert feedback["missed_indicators"] == []


def test_answer_with_unknown_sample_returns_404(client: TestClient) -> None:
    r = client.post(
        "/api/train/answer",
        json={
            "sample_id": str(uuid4()),
            "user_verdict": "legit",
            "marked_indicator_types": [],
        },
    )
    assert r.status_code == 404


def test_next_rejects_invalid_difficulty(client: TestClient) -> None:
    r = client.post(
        "/api/train/next",
        json={"difficulty": 99, "input_type": "email", "language": "es"},
    )
    assert r.status_code == 422


def test_next_defaults_when_payload_minimal(client: TestClient) -> None:
    r = client.post("/api/train/next", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["difficulty"] == 1  # L1 por defecto
    assert body["language"] == "es"
    assert body["input_type"] == "email"


def test_level_5_sample_is_legit(client: TestClient) -> None:
    """El mock L5 genera ejemplos LEGÍTIMOS para enseñar a no marcar todo como phishing."""
    next_r = client.post(
        "/api/train/next",
        json={"difficulty": 5, "input_type": "email", "language": "es"},
    )
    sample = next_r.json()

    answer_r = client.post(
        "/api/train/answer",
        json={
            "sample_id": sample["id"],
            "user_verdict": "legit",
            "marked_indicator_types": [],
        },
    )
    feedback = answer_r.json()
    assert feedback["correct"] is True
    assert feedback["score"] == 100
