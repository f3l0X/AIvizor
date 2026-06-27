"""Fixtures globales para pytest."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.analyze import get_analysis_repo, get_llm
from app.db.repositories import InMemoryAnalysisRepository
from app.llm.base import LLMProvider
from app.llm.mock import MockProvider
from app.main import app


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def in_memory_repo() -> InMemoryAnalysisRepository:
    return InMemoryAnalysisRepository()


@pytest.fixture
def client(
    mock_provider: LLMProvider,
    in_memory_repo: InMemoryAnalysisRepository,
) -> Iterator[TestClient]:
    """TestClient con dependencies sobreescritas: sin red, sin BD."""

    app.dependency_overrides[get_llm] = lambda: mock_provider
    app.dependency_overrides[get_analysis_repo] = lambda: in_memory_repo

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
