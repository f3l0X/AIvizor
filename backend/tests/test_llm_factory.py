"""Tests de la factory: selección por env y errores tempranos."""

from __future__ import annotations

import pytest

from app.llm.base import LLMError
from app.llm.factory import get_llm, reset_llm_cache
from app.llm.mock import MockProvider


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_llm_cache()
    yield
    reset_llm_cache()


def test_factory_returns_mock_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "llm_provider", "mock")
    provider = get_llm()
    assert isinstance(provider, MockProvider)


def test_factory_raises_for_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "llm_provider", "totally-fake")
    with pytest.raises(LLMError):
        get_llm()


def test_factory_raises_when_gemini_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    with pytest.raises(LLMError):
        get_llm()


def test_factory_raises_when_claude_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "llm_provider", "claude")
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    with pytest.raises(LLMError):
        get_llm()
