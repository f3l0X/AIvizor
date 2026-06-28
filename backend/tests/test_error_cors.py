"""Las respuestas de error no controladas (500) deben llevar cabeceras CORS.

Sin esto, un 500 llega al navegador sin `Access-Control-Allow-Origin`, que lo
bloquea: el cliente ve un falso "no se pudo conectar" en vez del error real
(justamente lo que ocultó un fallo de BD en BYOK). Ver el handler en
``app.main.unhandled_exception_handler``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.analyze import get_analysis_repo
from app.api.analyze import get_llm as get_analyzer_llm
from app.db.repositories import InMemoryAnalysisRepository
from app.main import app

ANALYZE_BODY = {"content": "hola", "input_type": "email", "language": "es"}


def _boom() -> object:
    raise RuntimeError("kaboom")


@pytest.fixture
def failing_client() -> Iterator[TestClient]:
    """Cliente cuyo endpoint /api/analyze revienta con una excepción no controlada.

    `raise_server_exceptions=False` para recibir la respuesta 500 en vez de que el
    TestClient la re-lance.
    """
    app.dependency_overrides[get_analysis_repo] = lambda: InMemoryAnalysisRepository()
    app.dependency_overrides[get_analyzer_llm] = _boom  # raise al resolver la dependency
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def test_500_carries_cors_headers_for_allowed_origin(failing_client: TestClient) -> None:
    r = failing_client.post(
        "/api/analyze", json=ANALYZE_BODY, headers={"Origin": "http://localhost:3000"}
    )
    assert r.status_code == 500
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert r.headers.get("access-control-allow-credentials") == "true"


def test_500_does_not_echo_disallowed_origin(failing_client: TestClient) -> None:
    r = failing_client.post(
        "/api/analyze", json=ANALYZE_BODY, headers={"Origin": "http://evil.example"}
    )
    assert r.status_code == 500
    # Un origen no permitido NO se refleja.
    assert "access-control-allow-origin" not in r.headers
