"""Tests de los guardias HTTP (Fase 7.7): límite de body y rate limiting.

El conftest desactiva el rate limiting para el resto de la suite (ráfagas desde
la misma "IP" del TestClient); aquí se habilita explícitamente con límites bajos
vía monkeypatch. Como el middleware consulta ``settings`` en cada petición y solo
registra intentos cuando está habilitado, no hay estado contaminado entre tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.security.http_guards import SlidingWindowLimiter

ANALYZE = {"content": "hola mundo", "input_type": "email", "language": "es"}
CREDS = {"email": "guard@example.com", "password": "supersecret1"}


# --- Límite de tamaño del body ----------------------------------------------


def test_oversized_body_rejected_413(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_body_bytes", 64)
    r = client.post("/api/analyze", json={**ANALYZE, "content": "x" * 500})
    assert r.status_code == 413
    assert "detail" in r.json()


def test_normal_body_passes(client: TestClient) -> None:
    # Con el límite por defecto (1 MB), un payload normal no se ve afectado.
    r = client.post("/api/analyze", json=ANALYZE)
    assert r.status_code == 200


def test_413_carries_cors_headers(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_body_bytes", 64)
    r = client.post(
        "/api/analyze",
        json={**ANALYZE, "content": "x" * 500},
        headers={"Origin": "http://localhost:3000"},
    )
    assert r.status_code == 413
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


# --- Rate limiting -----------------------------------------------------------


def test_auth_rate_limit_returns_429(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 3)
    # Los 3 primeros pasan (aunque fallen con 401: los intentos cuentan igual,
    # que es justo lo que frena la fuerza bruta). El 4º se corta con 429.
    for _ in range(3):
        assert client.post("/api/auth/login", json=CREDS).status_code == 401
    r = client.post("/api/auth/login", json=CREDS)
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) >= 1
    assert r.headers.get("access-control-allow-origin") is None  # sin Origin no hay eco


def test_llm_rate_limit_returns_429(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_llm_per_minute", 2)
    assert client.post("/api/analyze", json=ANALYZE).status_code == 200
    assert client.post("/api/analyze", json=ANALYZE).status_code == 200
    r = client.post(
        "/api/analyze", json=ANALYZE, headers={"Origin": "http://localhost:3000"}
    )
    assert r.status_code == 429
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_rate_limit_disabled_is_noop(client: TestClient) -> None:
    # Con el flag apagado (default de la suite) no se limita ni se registra.
    for _ in range(6):
        assert client.post("/api/analyze", json=ANALYZE).status_code == 200


def test_get_requests_never_limited(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 1)
    for _ in range(5):
        assert client.get("/health").status_code == 200


# --- SlidingWindowLimiter (unidad) -------------------------------------------


def test_limiter_separates_ips() -> None:
    limiter = SlidingWindowLimiter(window_seconds=60)
    assert limiter.allow("auth", "1.1.1.1", limit=1) == (True, 0.0)
    # La misma IP agota su ventana; otra IP no se ve afectada.
    allowed, retry = limiter.allow("auth", "1.1.1.1", limit=1)
    assert allowed is False and retry > 0
    assert limiter.allow("auth", "2.2.2.2", limit=1)[0] is True


def test_limiter_separates_buckets() -> None:
    limiter = SlidingWindowLimiter(window_seconds=60)
    assert limiter.allow("auth", "1.1.1.1", limit=1)[0] is True
    # El bucket llm tiene su propia ventana para la misma IP.
    assert limiter.allow("llm", "1.1.1.1", limit=1)[0] is True


def test_limiter_window_expires() -> None:
    limiter = SlidingWindowLimiter(window_seconds=0.01)
    assert limiter.allow("auth", "1.1.1.1", limit=1)[0] is True
    assert limiter.allow("auth", "1.1.1.1", limit=1)[0] is False
    import time

    time.sleep(0.02)
    assert limiter.allow("auth", "1.1.1.1", limit=1)[0] is True


@pytest.mark.parametrize("path", ["/api/keys/test", "/api/train/next"])
def test_llm_bucket_covers_expensive_routes(
    client: TestClient, monkeypatch, path: str
) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_llm_per_minute", 0)
    # Límite 0 → primera petición ya rechazada, sin importar auth ni payload.
    assert client.post(path, json={}).status_code == 429
