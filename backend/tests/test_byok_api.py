"""Tests de BYOK — *Bring Your Own Key* (Fase 7.3).

Cubre la API (`/api/keys`, requiere sesión), la capa de cifrado y la resolución del
provider por usuario. El ``TestClient`` arrastra la cookie de sesión tras el register,
igual que en ``test_auth_api.py``.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.repositories import InMemoryApiKeyRepository
from app.llm.base import LLMError
from app.llm.mock import MockProvider
from app.schemas.byok import mask_key
from app.security.crypto import CryptoError, decrypt_secret, encrypt_secret
from app.services.byok import resolve_provider_for_user, set_api_key

CREDS = {"email": "byok@example.com", "password": "supersecret1"}
KEY = {"provider": "claude", "api_key": "sk-ant-secret-wxyz", "model": "claude-x"}


def _register(client: TestClient) -> None:
    assert client.post("/api/auth/register", json=CREDS).status_code == 201


# --- API: autorización -----------------------------------------------------


def test_get_key_requires_auth(client: TestClient) -> None:
    assert client.get("/api/keys").status_code == 401


def test_put_key_requires_auth(client: TestClient) -> None:
    assert client.put("/api/keys", json=KEY).status_code == 401


def test_delete_key_requires_auth(client: TestClient) -> None:
    assert client.delete("/api/keys").status_code == 401


# --- API: CRUD -------------------------------------------------------------


def test_get_key_404_when_none(client: TestClient) -> None:
    _register(client)
    assert client.get("/api/keys").status_code == 404


def test_put_key_stores_and_masks(client: TestClient) -> None:
    _register(client)
    r = client.put("/api/keys", json=KEY)
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "claude"
    assert body["model"] == "claude-x"
    assert body["masked_key"] == "••••wxyz"
    # La clave en claro NUNCA sale.
    assert "api_key" not in body
    assert KEY["api_key"] not in r.text


def test_get_key_returns_masked_after_put(client: TestClient) -> None:
    _register(client)
    client.put("/api/keys", json=KEY)
    r = client.get("/api/keys")
    assert r.status_code == 200
    assert r.json()["masked_key"] == "••••wxyz"
    assert KEY["api_key"] not in r.text


def test_put_key_upserts(client: TestClient) -> None:
    _register(client)
    client.put("/api/keys", json=KEY)
    r = client.put(
        "/api/keys",
        json={"provider": "gemini", "api_key": "gm-newkey-5678", "model": None},
    )
    assert r.status_code == 200
    assert r.json()["provider"] == "gemini"
    assert r.json()["masked_key"] == "••••5678"
    # Sigue habiendo una sola config (la nueva).
    assert client.get("/api/keys").json()["provider"] == "gemini"


def test_put_invalid_provider_rejected(client: TestClient) -> None:
    _register(client)
    r = client.put(
        "/api/keys", json={"provider": "mock", "api_key": "whatever12", "model": None}
    )
    assert r.status_code == 422


def test_put_short_key_rejected(client: TestClient) -> None:
    _register(client)
    r = client.put(
        "/api/keys", json={"provider": "claude", "api_key": "short", "model": None}
    )
    assert r.status_code == 422


def test_delete_key_removes(client: TestClient) -> None:
    _register(client)
    client.put("/api/keys", json=KEY)
    assert client.delete("/api/keys").status_code == 204
    assert client.get("/api/keys").status_code == 404


def test_delete_key_idempotent(client: TestClient) -> None:
    _register(client)
    # Borrar sin tener clave no revienta (204).
    assert client.delete("/api/keys").status_code == 204


# --- Cifrado ---------------------------------------------------------------


def test_crypto_round_trip() -> None:
    secret = "sk-ant-abc-123-XYZ"
    token = encrypt_secret(secret)
    assert token != secret  # cifrado, no en claro
    assert decrypt_secret(token) == secret


def test_decrypt_invalid_token_raises() -> None:
    with pytest.raises(CryptoError):
        decrypt_secret("clearly-not-a-fernet-token")


def test_mask_key() -> None:
    assert mask_key("sk-ant-secret-wxyz") == "••••wxyz"
    assert mask_key("abc") == "••••"  # demasiado corta: sin cola


# --- Resolución del provider por usuario -----------------------------------


async def test_resolve_returns_none_without_key() -> None:
    repo = InMemoryApiKeyRepository()
    assert await resolve_provider_for_user(uuid4(), repo=repo) is None


async def test_resolve_builds_provider_with_decrypted_key(monkeypatch) -> None:
    repo = InMemoryApiKeyRepository()
    uid = uuid4()
    await repo.upsert(
        user_id=uid,
        provider="claude",
        api_key_encrypted=encrypt_secret("sk-secret-xyz"),
        model="claude-x",
    )

    captured: dict = {}

    def fake_build(provider: str, api_key: str, model: str | None) -> MockProvider:
        captured.update(provider=provider, api_key=api_key, model=model)
        return MockProvider()

    monkeypatch.setattr("app.services.byok.build_provider_cached", fake_build)

    provider = await resolve_provider_for_user(uid, repo=repo)
    assert provider is not None
    # El provider se construye con la clave DESCIFRADA, no con el ciphertext.
    assert captured == {"provider": "claude", "api_key": "sk-secret-xyz", "model": "claude-x"}


async def test_resolve_raises_llmerror_on_corrupt_ciphertext() -> None:
    repo = InMemoryApiKeyRepository()
    uid = uuid4()
    await repo.upsert(
        user_id=uid, provider="gemini", api_key_encrypted="not-a-valid-token", model=None
    )
    with pytest.raises(LLMError):
        await resolve_provider_for_user(uid, repo=repo)


async def test_set_api_key_encrypts_at_rest() -> None:
    repo = InMemoryApiKeyRepository()
    uid = uuid4()
    from app.schemas.byok import ApiKeyCreate

    public = await set_api_key(
        uid, ApiKeyCreate(provider="claude", api_key="sk-plain-1234"), repo=repo
    )
    stored = await repo.get(uid)
    assert stored is not None
    # En reposo está cifrado; descifrar recupera el original.
    assert stored.api_key_encrypted != "sk-plain-1234"
    assert decrypt_secret(stored.api_key_encrypted) == "sk-plain-1234"
    assert public.masked_key == "••••1234"
