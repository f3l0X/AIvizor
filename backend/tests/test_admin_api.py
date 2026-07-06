"""Tests del panel admin (Fase 7.5).

La API ``/api/admin/*`` exige sesión de administrador. Para conseguir una en los
tests registramos un usuario por la API (siempre rol ``user``) y lo promovemos a
admin directamente en el repo en memoria: ``require_admin`` lee el rol del
repositorio, no del JWT, así que la misma cookie pasa a valer como admin.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.repositories import InMemoryUserRepository
from app.schemas.auth import Role

ADMIN = {"email": "admin@example.com", "password": "Supersecret1"}
USER = {"email": "user@example.com", "password": "Supersecret1"}


def _login_as_admin(client: TestClient, repo: InMemoryUserRepository) -> None:
    """Registra ADMIN, lo promueve en el repo y deja la cookie de sesión puesta."""
    assert client.post("/api/auth/register", json=ADMIN).status_code == 201
    for u in repo.users.values():
        if u.email == ADMIN["email"]:
            u.role = Role.ADMIN


def _create_user(client: TestClient) -> str:
    """Crea un usuario normal aparte y devuelve su id. Restaura la sesión previa."""
    # El register hace auto-login y pisa la cookie; la guardamos y la reponemos.
    saved = dict(client.cookies)
    assert client.post("/api/auth/register", json=USER).status_code == 201
    uid = client.get("/api/auth/me").json()["id"]
    client.cookies.clear()
    for k, v in saved.items():
        client.cookies.set(k, v)
    return uid


# --- Autorización ----------------------------------------------------------


def test_list_users_requires_auth(client: TestClient) -> None:
    assert client.get("/api/admin/users").status_code == 401


def test_list_users_forbidden_for_normal_user(client: TestClient) -> None:
    client.post("/api/auth/register", json=USER)  # rol user
    assert client.get("/api/admin/users").status_code == 403


def test_update_user_forbidden_for_normal_user(client: TestClient) -> None:
    client.post("/api/auth/register", json=USER)
    r = client.patch(f"/api/admin/users/{uuid4()}", json={"is_active": False})
    assert r.status_code == 403


def test_delete_user_forbidden_for_normal_user(client: TestClient) -> None:
    client.post("/api/auth/register", json=USER)
    assert client.delete(f"/api/admin/users/{uuid4()}").status_code == 403


# --- Listado ---------------------------------------------------------------


def test_admin_lists_users(client: TestClient, in_memory_user_repo) -> None:
    _login_as_admin(client, in_memory_user_repo)
    _create_user(client)
    r = client.get("/api/admin/users")
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()}
    assert emails == {ADMIN["email"], USER["email"]}
    # Nunca filtra el hash.
    assert all("password_hash" not in u for u in r.json())


# --- Activar / desactivar --------------------------------------------------


def test_admin_deactivates_and_reactivates_user(
    client: TestClient, in_memory_user_repo
) -> None:
    _login_as_admin(client, in_memory_user_repo)
    uid = _create_user(client)

    r = client.patch(f"/api/admin/users/{uid}", json={"is_active": False})
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    r = client.patch(f"/api/admin/users/{uid}", json={"is_active": True})
    assert r.json()["is_active"] is True


def test_admin_changes_role(client: TestClient, in_memory_user_repo) -> None:
    _login_as_admin(client, in_memory_user_repo)
    uid = _create_user(client)
    r = client.patch(f"/api/admin/users/{uid}", json={"role": "admin"})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_update_unknown_user_404(client: TestClient, in_memory_user_repo) -> None:
    _login_as_admin(client, in_memory_user_repo)
    r = client.patch(f"/api/admin/users/{uuid4()}", json={"is_active": False})
    assert r.status_code == 404


# --- Borrado ---------------------------------------------------------------


def test_admin_deletes_user(client: TestClient, in_memory_user_repo) -> None:
    _login_as_admin(client, in_memory_user_repo)
    uid = _create_user(client)
    assert client.delete(f"/api/admin/users/{uid}").status_code == 204
    # Ya no aparece en el listado.
    emails = {u["email"] for u in client.get("/api/admin/users").json()}
    assert USER["email"] not in emails


def test_delete_unknown_user_404(client: TestClient, in_memory_user_repo) -> None:
    _login_as_admin(client, in_memory_user_repo)
    assert client.delete(f"/api/admin/users/{uuid4()}").status_code == 404


# --- Auto-protección del admin --------------------------------------------


def test_admin_cannot_deactivate_self(client: TestClient, in_memory_user_repo) -> None:
    _login_as_admin(client, in_memory_user_repo)
    me = client.get("/api/auth/me").json()["id"]
    r = client.patch(f"/api/admin/users/{me}", json={"is_active": False})
    assert r.status_code == 400


def test_admin_cannot_delete_self(client: TestClient, in_memory_user_repo) -> None:
    _login_as_admin(client, in_memory_user_repo)
    me = client.get("/api/auth/me").json()["id"]
    assert client.delete(f"/api/admin/users/{me}").status_code == 400
