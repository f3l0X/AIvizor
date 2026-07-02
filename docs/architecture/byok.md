# BYOK — Bring Your Own Key (clave de LLM por usuario)

> Estado: implementado en Fase 7.3 (backend); multi-clave + validación al guardar en 7.6.
> Tests: `backend/tests/test_byok_api.py` (26 tests). Suite total: 146 verdes.

Hasta la Fase 7.2 todas las llamadas al LLM usaban **una** cuenta: la del servidor
(`LLM_PROVIDER` + claves en `.env`). BYOK permite que cada usuario aporte **su propia**
API key (Gemini o Claude); su análisis/entrenamiento consume *su* cuota, no la del
servidor. Es la pieza que vuelve el proyecto multi-tenant a nivel de coste de IA.

## Decisiones

- **Las claves se cifran en reposo.** Una API key es un secreto: nunca se guarda en
  claro. Se cifra con **Fernet** (AES-128-CBC + HMAC-SHA256) usando
  `BYOK_ENCRYPTION_KEY`. La BD solo ve el token cifrado.
- **La clave en claro solo entra, nunca sale.** El alta (`PUT`) la recibe; cualquier
  lectura devuelve una **máscara** (`••••wxyz`, últimos 4 caracteres). El cliente no
  puede recuperar la clave que guardó.
- **BYOK es opt-in; el anónimo sigue funcionando.** Analyzer y Trainer resuelven el
  provider por petición: si hay un usuario logueado **con** clave BYOK, usan la suya;
  si no (anónimo, o logueado sin clave), caen al provider por defecto del servidor.
  La demo pública no se rompe.
- **Fallar visible antes que gastar la clave del servidor.** Si un usuario tiene clave
  configurada pero no se puede usar (cifrado rotado, provider no construible), la
  petición devuelve **502** en vez de tirar silenciosamente de la cuenta del servidor.
- **`mock` no admite BYOK.** No tiene sentido como "tu propia" credencial; el provider
  BYOK se restringe a `gemini`/`claude` a nivel de esquema (422 si se pide otro).

## Componentes

| Pieza | Fichero | Rol |
|---|---|---|
| Cifrado | `app/security/crypto.py` | `encrypt_secret` / `decrypt_secret` (Fernet) |
| Modelo | `app/db/models.py::UserApiKey` | tabla `user_api_keys` (1 fila por usuario) |
| Esquemas | `app/schemas/byok.py` | `ApiKeyCreate/StoredApiKey/ApiKeyPublic`, `mask_key` |
| Repositorio | `app/db/repositories.py::ApiKeyRepository` | Protocol + `Sql*` + `InMemory*` |
| Servicio | `app/services/byok.py` | set/get/delete + `resolve_provider_for_user` |
| Factory | `app/llm/factory.py::build_provider*` | construcción reutilizable + caché por clave |
| API | `app/api/keys.py` | endpoints `/api/keys` |

Igual que Auth/Analyzer/Trainer, el servicio de dominio solo habla con el
`ApiKeyRepository` (Protocol) y la capa `crypto`; no conoce HTTP ni SQLAlchemy. El
cifrado/descifrado vive en el servicio: el repositorio solo persiste el texto cifrado.

## Tres representaciones de la clave

Deliberadamente separadas, como en auth:

- `ApiKeyCreate` — entrada del cliente (clave en claro).
- `StoredApiKey` — vista interna del backend (texto **cifrado**). Nunca se serializa.
- `ApiKeyPublic` — salida HTTP: provider, model, timestamps y `masked_key`. Jamás la clave.

## Multi-clave: una por proveedor + activa (Fase 7.6)

Un usuario puede guardar **una clave por proveedor** (gemini/claude) y elegir cuál
está **activa** — la que usan Analyzer/Trainer. Modelo de datos: `user_api_keys` con
único `(user_id, provider)` y un flag `is_active`. Invariante (forzada en la capa de
aplicación): **como mucho una clave activa por usuario**. La primera clave que guarda
un usuario queda activa automáticamente; borrar la activa promueve a otra restante.

## Endpoints (`/api/keys`, requieren sesión)

| Método | Ruta | Comportamiento |
|---|---|---|
| `GET` | `/api/keys` | lista de claves (enmascaradas) con `is_active`. Lista vacía si no hay. |
| `PUT` | `/api/keys` | crea o reemplaza (upsert) la clave de un proveedor. Devuelve la vista pública. |
| `POST` | `/api/keys/test` | valida la clave contra el proveedor **sin guardarla** (204). **400** si no vale. |
| `PUT` | `/api/keys/active` | marca activa la clave de un proveedor (`{provider}`). **404** si no hay clave suya. |
| `DELETE` | `/api/keys/{provider}` | borra esa clave (204). Si era la activa y queda otra, la activa. |

## Validación al guardar

`validate_api_key` (servicio) construye el provider con la clave en claro y hace una
llamada mínima (`LLMProvider.validate()`, un *ping* de 1 token): confirma que la clave
**y el modelo** son utilizables. El frontend llama a `POST /api/keys/test` antes de
`PUT` al guardar, así que un error de credenciales se ve **al momento** en Ajustes en
vez de fallar más tarde durante un análisis. El `mock` valida siempre (no-op), lo que
mantiene la suite offline.

Sin sesión → **401** (todos usan `get_current_user`).

## Resolución del provider por petición

Analyzer (`POST /api/analyze`) y Trainer (`/api/train/*`) usan la dependency `get_llm`,
ahora resolutiva:

1. `get_current_user_optional` lee la cookie **sin lanzar** (devuelve `None` si no hay).
2. Si hay usuario, `resolve_provider_for_user` toma su clave **activa**, la descifra y
   construye el provider vía `build_provider_cached` (cacheado por `(provider, clave,
   modelo)` → reusa el cliente HTTP entre peticiones del mismo usuario).
3. Si no hay usuario o no tiene clave activa → `get_llm()` del servidor (default por env).

## Notas operativas

- Variable nueva en `.env` / `.env.example`: `BYOK_ENCRYPTION_KEY` (Fernet, urlsafe
  base64 de 32 bytes). **Cámbiala en producción** y guárdala fuera del repo. Generar con:
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
  Rotarla invalida las claves ya guardadas: los usuarios deben volver a introducirlas
  (el `GET` no revienta, muestra `••••`; el uso devuelve 502 hasta re-guardar).
- Dependencia nueva: `cryptography` (en `pyproject.toml`). Rebuild de la imagen del
  backend (`docker compose build backend`).
- Migración `0004_user_api_keys` (FK a `users` con `ON DELETE CASCADE`: borrar un
  usuario borra sus claves) y `0005_byok_multikey` (único `(user_id, provider)` +
  `is_active`; backfill: las claves existentes quedan activas).

## Pendiente / futuro

- (Nada crítico pendiente en BYOK.)

> El frontend de gestión de la clave (pantalla de ajustes) se implementó en la
> Fase 7.4 — ver [frontend-auth.md](frontend-auth.md).
