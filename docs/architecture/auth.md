# Autenticación — multi-usuario con JWT en cookie httpOnly

> Estado: implementada en Fase 7.2 (backend).
> Tests: `backend/tests/test_auth_api.py` (18 tests).
> Relacionado: [byok.md](byok.md) (7.3), [frontend-auth.md](frontend-auth.md) (7.4),
> [admin.md](admin.md) (7.5).

AIvizor v1 era anónimo (sin login). La Fase 7 introduce **multi-usuario completo**
(registro público, login, roles) como base para BYOK por usuario (Fase 7.3) y el
panel admin (Fase 7.5). Es un giro consciente respecto al anti-scope original de
`PLANNING.md`.

## Decisiones

- **Sesión por JWT en cookie httpOnly.** El token va en una cookie `access_token`
  marcada `HttpOnly` (no accesible desde JS → mitiga robo por XSS), `SameSite=lax`
  y `Secure` configurable (solo bajo HTTPS). El frontend no manipula el token;
  basta con `credentials: 'include'` en sus fetch.
- **bcrypt** para el hash de contraseña (truncado defensivo a 72 bytes). La
  contraseña en claro nunca se persiste ni se devuelve.
- **Tres representaciones del usuario**, deliberadamente separadas
  (`app/schemas/auth.py`):
  - `UserCreate` / `UserLogin` — entrada (incluye contraseña en claro).
  - `UserInDB` — vista interna del backend (incluye `password_hash`). Nunca se
    serializa hacia el cliente.
  - `UserPublic` — salida HTTP (sin `password` ni `password_hash`).
  Todos los endpoints responden `UserPublic`: el hash no cruza la frontera HTTP.

## Componentes

| Pieza | Fichero | Rol |
|---|---|---|
| Modelo | `app/db/models.py::User` | tabla `users` (email único, `password_hash`, `role`, `is_active`) |
| Esquemas | `app/schemas/auth.py` | `Role`, `UserCreate/Login/InDB/Public` |
| Hash | `app/security/passwords.py` | `hash_password` / `verify_password` (bcrypt) |
| Token | `app/security/tokens.py` | `create/decode_access_token` (PyJWT HS256) |
| Repositorio | `app/db/repositories.py::UserRepository` | Protocol + `Sql*` + `InMemory*` |
| Servicio | `app/services/auth.py` | `register_user`, `authenticate_user`, `ensure_admin` |
| API | `app/api/auth.py` | endpoints + dependencies de sesión |

El servicio de dominio solo habla con el `UserRepository` (Protocol) y las
utilidades de `security`; no conoce HTTP ni SQLAlchemy. Igual que Analyzer y
Trainer, esto permite testear registro/login con la implementación en memoria,
sin BD ni red.

## Endpoints (`/api/auth`)

| Método | Ruta | Comportamiento |
|---|---|---|
| `POST` | `/register` | crea usuario (rol `user`), **auto-login** (deja la cookie). 409 si el email ya existe. |
| `POST` | `/login` | valida credenciales y pone la cookie. 401 genérico si fallan; 403 si la cuenta está inactiva. |
| `POST` | `/logout` | borra la cookie (204). |
| `POST` | `/change-password` | cambia la contraseña del usuario de la sesión (204). Exige la **actual** (400 si no coincide — no 401: la sesión sigue viva) y la nueva pasa la política (422). La cookie sigue siendo válida (el JWT va ligado al id); no invalida otras sesiones abiertas — limitación conocida (no hay versionado de sesión). |
| `GET`  | `/me` | devuelve el usuario de la sesión. 401 si no hay sesión válida. |

## Dependencies de sesión

- `get_current_user` — lee la cookie, decodifica el JWT, recupera el usuario por id
  y verifica `is_active`. Lanza **401** ante token ausente, inválido, expirado,
  manipulado, o usuario inexistente/inactivo. `decode_access_token` nunca lanza:
  devuelve `None` y el endpoint traduce a 401.
- `require_admin` — encadena `get_current_user` y exige `role == admin`, si no **403**.

## Política de contraseñas (Fase 7.8)

`security/passwords.py::validate_password_strength` — vive junto al hashing y
lee las reglas de `settings` en cada llamada (configurables por env, apagables
en tests con monkeypatch). Política **equilibrada** por defecto:

- ≥ 8 caracteres (`PASSWORD_MIN_LENGTH`),
- una mayúscula, una minúscula y un número (`PASSWORD_REQUIRE_{UPPERCASE,LOWERCASE,DIGIT}`),
- símbolo disponible pero apagado (`PASSWORD_REQUIRE_SPECIAL=false`),
- rechazo de contraseñas ultra comunes (`PASSWORD_REJECT_COMMON`), comparadas
  con `casefold()` — `Password123` también cae.

Se aplica **solo en el registro público**: `register_user` lanza
`WeakPasswordError` (con los códigos incumplidos) y la API lo traduce a **422**
con detail legible. El login no valida fortaleza (usuarios pre-política) y
`ensure_admin` queda **exento a propósito** — el admin sembrado por
`ADMIN_PASSWORD` no pasa por `UserCreate`, y validar ahí podría impedir el
arranque con una contraseña de env corta.

El frontend muestra un **checklist en vivo** en el registro
(`frontend/lib/passwordPolicy.ts`, espejo de los defaults — decisión de UI como
`INDICATORS_BY_INPUT_TYPE`); la barrera real es el backend.

## Admin inicial

Si `ADMIN_EMAIL` y `ADMIN_PASSWORD` están definidos, el `lifespan` de FastAPI
siembra ese admin al arrancar mediante `ensure_admin` (idempotente). Si faltan,
no hace nada — que es el caso por defecto en tests, así que la suite no toca la BD.

## Notas operativas

- Variables nuevas en `.env` / `.env.example`: `JWT_SECRET` (cámbialo en
  producción, mín. 32 bytes), `JWT_EXPIRE_MINUTES`, `COOKIE_SECURE`,
  `COOKIE_SAMESITE`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.
- Dependencias nuevas: `bcrypt`, `pyjwt`, `email-validator` (en `pyproject.toml`).
  La imagen del backend debe reconstruirse (`docker compose build backend`) para
  hornearlas; un contenedor ya en marcha necesita `pip install` o rebuild.
- Migración `0003_users`.
