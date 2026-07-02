# Frontend de autenticación + BYOK

> Estado: implementado en Fase 7.4 (frontend).
> Backend: ver [auth.md](auth.md) (Fase 7.2) y [byok.md](byok.md) (Fase 7.3).

Las Fases 7.2/7.3 dejaron el backend multi-usuario (login por cookie httpOnly) y
BYOK (clave de LLM por usuario) listos pero sin interfaz. La Fase 7.4 añade el
frontend: login, registro, estado de sesión en la cabecera y una pantalla de
ajustes para gestionar la clave BYOK.

## Decisiones

- **El frontend nunca toca el token.** La sesión vive en la cookie httpOnly
  `access_token` que pone el backend; el cliente solo manda `credentials:'include'`
  en cada fetch y el navegador la adjunta sola. No hay token en `localStorage` ni
  en estado de React — el `AuthProvider` solo guarda un espejo de `UserPublic`
  para pintar la UI.
- **`credentials:'include'` en TODAS las peticiones**, incluidas Analyzer y
  Trainer. Así el backend resuelve la clave BYOK del usuario logueado (si la
  tiene) sin que la UI tenga que distinguir anónimo de autenticado: el anónimo
  simplemente viaja sin cookie y cae al provider del servidor.
- **Degradación a anónimo, no a error.** Al montar, `AuthProvider` consulta
  `GET /api/auth/me`; un 401 (o el backend caído) deja la sesión como anónima en
  vez de romper la app. La home pública debe seguir funcionando sin backend de auth.
- **La clave BYOK en claro solo se envía, nunca se conserva.** El formulario la
  manda en el `PUT` y acto seguido la borra del estado; cualquier lectura muestra
  la máscara (`••••wxyz`) que devuelve el backend. Un `GET` con 404 se trata como
  "sin clave configurada", no como error.
- **Rutas protegidas en el cliente = solo UX.** `/settings` redirige a login si la
  sesión es anónima, pero la protección real la impone el backend (401 sin cookie);
  el redirect solo evita mostrar un formulario que fallaría.

## Componentes

| Pieza | Fichero | Rol |
|---|---|---|
| Tipos | `frontend/lib/types.ts` | espejo de `UserPublic`, `Role`, `ApiKeyCreate/Public`, `ByokProvider` |
| Cliente HTTP | `frontend/lib/api.ts` | `register/login/logout/getMe` + BYOK (`getApiKeys/putApiKey/testApiKey/setActiveProvider/deleteApiKey`); `credentials:'include'` en todo |
| Contexto | `frontend/components/AuthProvider.tsx` | sesión en memoria: `user`, `status`, `login/register/logout/refresh` |
| Cabecera | `frontend/components/SessionNav.tsx` | estado de sesión (anónimo / autenticado / badge admin) |
| Formulario | `frontend/components/AuthForm.tsx` | credenciales compartidas por login y registro (`mode`) |
| BYOK | `frontend/components/ApiKeyManager.tsx` | alta/reemplazo/borrado de la clave |
| Home CTA | `frontend/components/HomeAuthCta.tsx` | invita a crear cuenta / atajo a ajustes |
| Páginas | `frontend/app/[locale]/{login,register,settings}/page.tsx` | encuadre de los componentes |
| i18n | `frontend/messages/{es,en}.json` | claves `auth.*`, `settings.*`, `home.cta.*` |

`AuthProvider` envuelve el árbol dentro de `NextIntlClientProvider` en el layout;
todo lo que necesite la sesión usa el hook `useAuth()`.

## Flujos

- **Registro / login** → `AuthForm` llama a `register`/`login`, el backend deja la
  cookie y responde `UserPublic`; el provider lo guarda en memoria y la página
  redirige a la home. El registro hace auto-login en el backend, así que el flujo
  de éxito es idéntico al de login.
- **Logout** → `SessionNav` llama a `logout`; pase lo que pase en el servidor, el
  cliente borra la sesión y vuelve a la home.
- **BYOK** → `ApiKeyManager` carga la clave (404 = sin clave), permite guardar
  (upsert) y borrar. La máscara es lo único que se muestra; la clave en claro se
  descarta tras enviarla.

## Notas operativas

- `NEXT_PUBLIC_API_URL` apunta al backend (default `http://localhost:8000`). El
  backend debe permitir el **origen** del frontend en CORS *con credenciales*
  (hoy `:3000` y `:3001`); un origen no listado bloquea login y BYOK aunque las
  páginas rendericen.
- En dev el `:3000` puede estar ocupado por el stack de Docker. Hay una config
  `frontend-3001` en `.claude/launch.json` para levantar el dev server en `:3001`
  (origen ya permitido por el CORS del backend).

## Pendiente / futuro

- **Panel admin (Fase 7.5).** `SessionNav` ya pinta un badge `Admin` cuando el
  rol lo es; falta la pantalla de gestión de usuarios.
- Validar la clave BYOK contra el provider al guardarla (un `POST /api/keys/test`
  en el backend, ver [byok.md](byok.md)).
