"""Tests de BYOK — *Bring Your Own Key* multi-clave (Fase 7.3 / 7.6).

Cada usuario puede guardar una clave por proveedor (gemini/claude) y elegir cuál
está activa. Cubre la API (`/api/keys`, requiere sesión), el cifrado y la
resolución del provider **activo**. El ``TestClient`` arrastra la cookie de sesión
tras el register, igual que en ``test_auth_api.py``.
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
GEMINI = {"provider": "gemini", "api_key": "gm-secret-wxyz", "model": "gemini-2.5-flash"}
CLAUDE = {"provider": "claude", "api_key": "sk-ant-secret-abcd", "model": "claude-x"}


def _register(client: TestClient) -> None:
    assert client.post("/api/auth/register", json=CREDS).status_code == 201


def _by_provider(items: list[dict]) -> dict[str, dict]:
    return {k["provider"]: k for k in items}


# --- API: autorización -----------------------------------------------------


def test_list_keys_requires_auth(client: TestClient) -> None:
    assert client.get("/api/keys").status_code == 401


def test_put_key_requires_auth(client: TestClient) -> None:
    assert client.put("/api/keys", json=GEMINI).status_code == 401


def test_set_active_requires_auth(client: TestClient) -> None:
    assert client.put("/api/keys/active", json={"provider": "gemini"}).status_code == 401


def test_delete_key_requires_auth(client: TestClient) -> None:
    assert client.delete("/api/keys/gemini").status_code == 401


# --- API: CRUD multi-clave -------------------------------------------------


def test_list_empty_returns_200(client: TestClient) -> None:
    _register(client)
    r = client.get("/api/keys")
    assert r.status_code == 200
    assert r.json() == []


def test_put_first_key_is_active_and_masked(client: TestClient) -> None:
    _register(client)
    r = client.put("/api/keys", json=GEMINI)
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "gemini"
    assert body["model"] == "gemini-2.5-flash"
    assert body["masked_key"] == "••••wxyz"
    assert body["is_active"] is True  # primera clave → activa
    # La clave en claro NUNCA sale.
    assert "api_key" not in body
    assert GEMINI["api_key"] not in r.text


def test_second_provider_not_active_first_stays(client: TestClient) -> None:
    _register(client)
    client.put("/api/keys", json=GEMINI)
    r = client.put("/api/keys", json=CLAUDE)
    assert r.status_code == 200
    assert r.json()["is_active"] is False
    keys = _by_provider(client.get("/api/keys").json())
    assert set(keys) == {"gemini", "claude"}
    assert keys["gemini"]["is_active"] is True
    assert keys["claude"]["is_active"] is False


def test_put_upserts_same_provider(client: TestClient) -> None:
    _register(client)
    client.put("/api/keys", json=GEMINI)
    r = client.put(
        "/api/keys",
        json={"provider": "gemini", "api_key": "gm-newkey-5678", "model": None},
    )
    assert r.status_code == 200
    assert r.json()["masked_key"] == "••••5678"
    assert r.json()["is_active"] is True  # preserva el activo
    # Sigue habiendo una sola clave de gemini.
    assert len(client.get("/api/keys").json()) == 1


def test_put_invalid_provider_rejected(client: TestClient) -> None:
    _register(client)
    r = client.put("/api/keys", json={"provider": "mock", "api_key": "whatever12"})
    assert r.status_code == 422


def test_put_short_key_rejected(client: TestClient) -> None:
    _register(client)
    r = client.put("/api/keys", json={"provider": "claude", "api_key": "short"})
    assert r.status_code == 422


# --- API: activar ----------------------------------------------------------


def test_set_active_switches_provider(client: TestClient) -> None:
    _register(client)
    client.put("/api/keys", json=GEMINI)  # activa
    client.put("/api/keys", json=CLAUDE)  # inactiva
    r = client.put("/api/keys/active", json={"provider": "claude"})
    assert r.status_code == 200
    assert r.json()["provider"] == "claude"
    assert r.json()["is_active"] is True
    keys = _by_provider(client.get("/api/keys").json())
    assert keys["claude"]["is_active"] is True
    assert keys["gemini"]["is_active"] is False


def test_set_active_unknown_provider_404(client: TestClient) -> None:
    _register(client)
    client.put("/api/keys", json=GEMINI)
    r = client.put("/api/keys/active", json={"provider": "claude"})  # sin clave claude
    assert r.status_code == 404


# --- API: borrado ----------------------------------------------------------


def test_delete_key_removes(client: TestClient) -> None:
    _register(client)
    client.put("/api/keys", json=GEMINI)
    assert client.delete("/api/keys/gemini").status_code == 204
    assert client.get("/api/keys").json() == []


def test_delete_active_promotes_remaining(client: TestClient) -> None:
    _register(client)
    client.put("/api/keys", json=GEMINI)  # activa
    client.put("/api/keys", json=CLAUDE)  # inactiva
    assert client.delete("/api/keys/gemini").status_code == 204  # borra la activa
    keys = _by_provider(client.get("/api/keys").json())
    assert set(keys) == {"claude"}
    assert keys["claude"]["is_active"] is True  # la restante pasa a activa


def test_delete_idempotent(client: TestClient) -> None:
    _register(client)
    # Borrar sin tener clave no revienta (204).
    assert client.delete("/api/keys/gemini").status_code == 204


def test_delete_invalid_provider_422(client: TestClient) -> None:
    _register(client)
    assert client.delete("/api/keys/mock").status_code == 422


# --- API: validar la clave (POST /test) ------------------------------------


def test_test_key_requires_auth(client: TestClient) -> None:
    assert client.post("/api/keys/test", json=GEMINI).status_code == 401


def test_test_key_ok(client: TestClient, monkeypatch) -> None:
    _register(client)
    # Sin red: el provider construido es el mock (validate() es no-op).
    monkeypatch.setattr(
        "app.services.byok.build_provider_cached", lambda *a, **k: MockProvider()
    )
    assert client.post("/api/keys/test", json=GEMINI).status_code == 204


def test_test_key_invalid_returns_400(client: TestClient, monkeypatch) -> None:
    _register(client)

    class _Bad:
        name = "gemini"

        async def validate(self) -> None:
            raise LLMError("clave rechazada", provider="gemini")

    monkeypatch.setattr("app.services.byok.build_provider_cached", lambda *a, **k: _Bad())
    r = client.post("/api/keys/test", json=GEMINI)
    assert r.status_code == 400


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


# --- Resolución del provider activo ----------------------------------------


async def test_resolve_returns_none_without_key() -> None:
    repo = InMemoryApiKeyRepository()
    assert await resolve_provider_for_user(uuid4(), repo=repo) is None


async def test_resolve_uses_active_key(monkeypatch) -> None:
    repo = InMemoryApiKeyRepository()
    uid = uuid4()
    # gemini queda activa (primera); claude inactiva.
    await repo.upsert(
        user_id=uid, provider="gemini",
        api_key_encrypted=encrypt_secret("gm-active"), model="gemini-2.5-flash",
    )
    await repo.upsert(
        user_id=uid, provider="claude",
        api_key_encrypted=encrypt_secret("sk-ant-inactive"), model=None,
    )

    captured: dict = {}

    def fake_build(provider: str, api_key: str, model: str | None) -> MockProvider:
        captured.update(provider=provider, api_key=api_key, model=model)
        return MockProvider()

    monkeypatch.setattr("app.services.byok.build_provider_cached", fake_build)

    provider = await resolve_provider_for_user(uid, repo=repo)
    assert provider is not None
    # Usa la clave ACTIVA (gemini), descifrada.
    assert captured == {"provider": "gemini", "api_key": "gm-active", "model": "gemini-2.5-flash"}

    # Tras cambiar de activa, resuelve la otra.
    await repo.set_active(uid, "claude")
    await resolve_provider_for_user(uid, repo=repo)
    assert captured["provider"] == "claude"
    assert captured["api_key"] == "sk-ant-inactive"


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
    stored = await repo.get(uid, "claude")
    assert stored is not None
    # En reposo está cifrado; descifrar recupera el original.
    assert stored.api_key_encrypted != "sk-plain-1234"
    assert decrypt_secret(stored.api_key_encrypted) == "sk-plain-1234"
    assert public.masked_key == "••••1234"
    assert public.is_active is True  # primera clave → activa
