"""Fixtures globales para pytest."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.analyze import get_analysis_repo
from app.api.analyze import get_llm as get_analyzer_llm
from app.api.auth import get_user_repo
from app.api.keys import get_api_key_repo
from app.api.train import get_llm as get_trainer_llm
from app.api.train import get_training_repo
from app.db.repositories import (
    InMemoryAnalysisRepository,
    InMemoryApiKeyRepository,
    InMemoryTrainingAttemptRepository,
    InMemoryUserRepository,
)
from app.config import settings
from app.llm.base import LLMProvider
from app.llm.mock import MockProvider
from app.main import app

# Los tests arrancan el lifespan vía TestClient pero no tienen Postgres: que no
# intente aplicar migraciones (Alembic se prueba aparte / en integración).
settings.auto_migrate = False

# La suite dispara ráfagas de register/login desde la misma "IP" del TestClient;
# el rate limiting se prueba explícitamente en test_http_guards.py.
settings.rate_limit_enabled = False


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def in_memory_repo() -> InMemoryAnalysisRepository:
    return InMemoryAnalysisRepository()


@pytest.fixture
def in_memory_training_repo() -> InMemoryTrainingAttemptRepository:
    return InMemoryTrainingAttemptRepository()


@pytest.fixture
def in_memory_user_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def in_memory_api_key_repo() -> InMemoryApiKeyRepository:
    return InMemoryApiKeyRepository()


@pytest.fixture
def client(
    mock_provider: LLMProvider,
    in_memory_repo: InMemoryAnalysisRepository,
    in_memory_training_repo: InMemoryTrainingAttemptRepository,
    in_memory_user_repo: InMemoryUserRepository,
    in_memory_api_key_repo: InMemoryApiKeyRepository,
) -> Iterator[TestClient]:
    """TestClient con dependencies sobreescritas: sin red, sin BD."""

    app.dependency_overrides[get_analyzer_llm] = lambda: mock_provider
    app.dependency_overrides[get_trainer_llm] = lambda: mock_provider
    app.dependency_overrides[get_analysis_repo] = lambda: in_memory_repo
    app.dependency_overrides[get_training_repo] = lambda: in_memory_training_repo
    app.dependency_overrides[get_user_repo] = lambda: in_memory_user_repo
    app.dependency_overrides[get_api_key_repo] = lambda: in_memory_api_key_repo

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
