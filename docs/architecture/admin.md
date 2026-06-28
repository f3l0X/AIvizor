# Panel de administración — gestión de usuarios

> Estado: implementado en Fase 7.5 (backend + frontend).
> Tests: `backend/tests/test_admin_api.py` (12 tests). Suite total: 136 verdes.
> Depende de [auth.md](auth.md) (sesión + `require_admin`) y [byok.md](byok.md)
> (la cascada que borra la clave al borrar el usuario).

Cierra la Fase 7: las fases previas dejaron multi-usuario (7.2), BYOK (7.3) y el
frontend de auth (7.4). La 7.5 añade el panel donde un administrador gestiona las
cuentas: listar, activar/desactivar, cambiar de rol y borrar.

## Decisiones

- **Sin esquema nuevo.** Opera sobre la tabla `users` existente (`is_active` y
  `role` ya estaban previstos desde 7.2). No hay migración.
- **Autorización por rol leído de la BD, no del JWT.** `require_admin` encadena
  `get_current_user`, que recupera el usuario fresco del repositorio; el claim de
  rol del token no decide nada. Así, degradar a alguien surte efecto en su
  siguiente petición sin reemitir su token.
- **Un admin no puede tocar su propia cuenta desde el panel.** Desactivarse o
  degradarse podría dejar el sistema sin ningún admin activo (auto-bloqueo). El
  servicio rechaza cualquier update/delete sobre el propio `id` con un error que
  la API traduce a **400**. El frontend además deshabilita esas acciones en la
  fila propia (UX); la barrera real es el backend.
- **Borrar un usuario arrastra su clave BYOK.** La FK de `user_api_keys` es
  `ON DELETE CASCADE` (migración 0004), así que el `DELETE` del usuario limpia su
  clave a nivel de BD sin lógica extra.
- **PATCH parcial.** `UserAdminUpdate` tiene `is_active` y `role` opcionales: solo
  se modifica el campo que viene. Activar/desactivar y cambiar de rol comparten
  endpoint.

## Componentes

| Pieza | Fichero | Rol |
|---|---|---|
| Repositorio | `app/db/repositories.py::UserRepository` | añade `list_all`, `update`, `delete` (Protocol + `Sql*` + `InMemory*`) |
| Esquema | `app/schemas/auth.py::UserAdminUpdate` | cambios parciales (is_active / role) |
| Servicio | `app/services/admin.py` | `list_users`, `update_user`, `delete_user` + auto-protección |
| API | `app/api/admin.py` | endpoints `/api/admin/*` (todos `require_admin`) |
| Front · tabla | `frontend/components/AdminUserTable.tsx` | listado + acciones por fila |
| Front · página | `frontend/app/[locale]/admin/page.tsx` | ruta protegida (anónimo→login, no-admin→home) |
| Front · acceso | `frontend/components/SessionNav.tsx` | el badge `Admin` enlaza al panel |
| i18n | `frontend/messages/{es,en}.json` | claves `admin.*` |

Como el resto de servicios, `services/admin.py` solo habla con el `UserRepository`;
no conoce HTTP ni SQLAlchemy. Eso permite testear la auto-protección y el CRUD con
la implementación en memoria.

## Endpoints (`/api/admin`, requieren admin)

| Método | Ruta | Comportamiento |
|---|---|---|
| `GET` | `/api/admin/users` | lista de `UserPublic` (sin hash). |
| `PATCH` | `/api/admin/users/{id}` | activa/desactiva o cambia el rol. 404 si no existe; **400** sobre uno mismo. |
| `DELETE` | `/api/admin/users/{id}` | borra la cuenta (cascada a su clave BYOK). 404 si no existe; **400** sobre uno mismo. |

Sin sesión → **401**; sesión no-admin → **403** (todos `require_admin`).

## Notas operativas

- No hay alta de admins por la API pública: `register` siempre crea rol `user`.
  El primer admin se siembra con `ADMIN_EMAIL`/`ADMIN_PASSWORD` (ver [auth.md](auth.md));
  a partir de ahí, un admin puede promover a otros desde el panel.
- El frontend `/[locale]/admin` es client-side y protege por UX; un no-admin que
  fuerce la URL recibe 403 del backend en cada llamada.
