"""Tests del flujo de autenticación (Fase 7.2).

El ``TestClient`` mantiene un cookie jar entre requests, así que tras register/login
la cookie httpOnly viaja sola en las llamadas siguientes (simula el navegador).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db.repositories import InMemoryUserRepository
from app.schemas.auth import Role, UserCreate, UserLogin
from app.services.auth import (
    EmailTakenError,
    InactiveUserError,
    InvalidCredentialsError,
    authenticate_user,
    ensure_admin,
    register_user,
)

CREDS = {"email": "alice@example.com", "password": "supersecret1"}


# --- API ------------------------------------------------------------------


def test_register_creates_user_and_sets_cookie(client: TestClient) -> None:
    r = client.post("/api/auth/register", json=CREDS)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == CREDS["email"]
    assert body["role"] == "user"
    assert body["is_active"] is True
    # La salida NUNCA expone hash ni contraseña.
    assert "password" not in body
    assert "password_hash" not in body
    # Auto-login: cookie de sesión puesta.
    assert settings.cookie_name in r.cookies


def test_register_duplicate_email_conflicts(client: TestClient) -> None:
    client.post("/api/auth/register", json=CREDS)
    r = client.post("/api/auth/register", json=CREDS)
    assert r.status_code == 409


def test_register_short_password_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/auth/register",
        json={"email": "bob@example.com", "password": "short"},
    )
    assert r.status_code == 422


def test_register_invalid_email_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "supersecret1"},
    )
    assert r.status_code == 422


def test_me_requires_authentication(client: TestClient) -> None:
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_register_then_me_returns_current_user(client: TestClient) -> None:
    client.post("/api/auth/register", json=CREDS)
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == CREDS["email"]


def test_login_with_valid_credentials(client: TestClient) -> None:
    client.post("/api/auth/register", json=CREDS)
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json=CREDS)
    assert r.status_code == 200
    assert r.json()["email"] == CREDS["email"]
    assert client.get("/api/auth/me").status_code == 200


def test_login_wrong_password_unauthorized(client: TestClient) -> None:
    client.post("/api/auth/register", json=CREDS)
    client.post("/api/auth/logout")
    r = client.post(
        "/api/auth/login",
        json={"email": CREDS["email"], "password": "wrongpassword"},
    )
    assert r.status_code == 401


def test_login_unknown_email_unauthorized(client: TestClient) -> None:
    r = client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "whatever12"},
    )
    assert r.status_code == 401


def test_logout_clears_session(client: TestClient) -> None:
    client.post("/api/auth/register", json=CREDS)
    assert client.get("/api/auth/me").status_code == 200
    r = client.post("/api/auth/logout")
    assert r.status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_tampered_token_unauthorized(client: TestClient) -> None:
    client.cookies.set(settings.cookie_name, "not.a.valid.jwt")
    assert client.get("/api/auth/me").status_code == 401


# --- Servicio -------------------------------------------------------------


async def test_register_user_hashes_password() -> None:
    repo = InMemoryUserRepository()
    user = await register_user(UserCreate(**CREDS), repo=repo)
    assert user.password_hash != CREDS["password"]
    assert user.role is Role.USER


async def test_register_user_duplicate_raises() -> None:
    repo = InMemoryUserRepository()
    await register_user(UserCreate(**CREDS), repo=repo)
    with pytest.raises(EmailTakenError):
        await register_user(UserCreate(**CREDS), repo=repo)


async def test_authenticate_user_roundtrip() -> None:
    repo = InMemoryUserRepository()
    await register_user(UserCreate(**CREDS), repo=repo)
    user = await authenticate_user(UserLogin(**CREDS), repo=repo)
    assert user.email == CREDS["email"]


async def test_authenticate_wrong_password_raises() -> None:
    repo = InMemoryUserRepository()
    await register_user(UserCreate(**CREDS), repo=repo)
    with pytest.raises(InvalidCredentialsError):
        await authenticate_user(
            UserLogin(email=CREDS["email"], password="wrongpassword"), repo=repo
        )


async def test_authenticate_inactive_user_raises() -> None:
    repo = InMemoryUserRepository()
    user = await register_user(UserCreate(**CREDS), repo=repo)
    repo.users[user.id].is_active = False
    with pytest.raises(InactiveUserError):
        await authenticate_user(UserLogin(**CREDS), repo=repo)


async def test_ensure_admin_seeds_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_email", "admin@example.com")
    monkeypatch.setattr(settings, "admin_password", "adminsecret1")
    repo = InMemoryUserRepository()

    assert await ensure_admin(repo) is True
    admin = await repo.get_by_email("admin@example.com")
    assert admin is not None and admin.role is Role.ADMIN
    # Idempotente: segunda llamada no crea otro.
    assert await ensure_admin(repo) is False


async def test_ensure_admin_noop_without_env() -> None:
    repo = InMemoryUserRepository()
    assert await ensure_admin(repo) is False
    assert repo.users == {}
