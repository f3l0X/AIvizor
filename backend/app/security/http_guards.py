"""Guardias HTTP de la frontera de entrada (Fase 7.7).

Dos middlewares ASGI puros, sin dependencias nuevas:

  - ``BodySizeLimitMiddleware`` — rechaza bodies mayores que ``settings.max_body_bytes``
    con **413**. Comprueba ``Content-Length`` si viene y, para bodies chunked (sin
    cabecera), cuenta los bytes recibidos y corta al superar el límite.
  - ``RateLimitMiddleware`` — ventana deslizante en memoria por ``(bucket, ip)``.
    Protege login/registro de fuerza bruta y los endpoints que gastan LLM de abuso
    de coste. Excedido → **429** con ``Retry-After``.

Ambos devuelven el error con cabeceras CORS (eco del Origin permitido): sin ellas el
navegador enmascara el 413/429 como "no hay conexión" — la misma lección que el
handler de 500 en ``main.py``.

Nota de despliegue: el rate limiting es por IP directa (``scope["client"]``). Detrás
de un proxy inverso todas las peticiones comparten IP; habría que derivarla de
``X-Forwarded-For`` (confiando solo en el proxy propio). Documentado en security.md.
"""

from __future__ import annotations

import json
import time
from collections import deque

from app.config import settings

# Buckets del rate limit: (método, ruta exacta) → nombre del bucket.
# Solo POSTs sensibles; el resto del tráfico no se toca.
_AUTH_ROUTES = {"/api/auth/register", "/api/auth/login"}
_LLM_ROUTES = {"/api/analyze", "/api/train/next", "/api/train/answer", "/api/keys/test"}


def _cors_headers_for(scope: dict) -> list[tuple[bytes, bytes]]:
    """Cabeceras CORS para una respuesta de error, replicando la política del
    middleware (echo del Origin si está permitido + credenciales)."""
    origin = ""
    for name, value in scope.get("headers", []):
        if name == b"origin":
            origin = value.decode("latin-1")
            break
    if origin and origin in settings.cors_origins_list:
        return [
            (b"access-control-allow-origin", origin.encode("latin-1")),
            (b"access-control-allow-credentials", b"true"),
            (b"vary", b"Origin"),
        ]
    return []


async def _send_error(
    send, scope: dict, status: int, detail: str, extra_headers: list[tuple[bytes, bytes]] = []
) -> None:
    body = json.dumps({"detail": detail}).encode()
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
        *extra_headers,
        *_cors_headers_for(scope),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class BodySizeLimitMiddleware:
    """Rechaza bodies mayores que ``settings.max_body_bytes`` con 413."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        max_bytes = settings.max_body_bytes

        # Vía rápida: si el cliente declara Content-Length, decidimos sin leer nada.
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    if int(value) > max_bytes:
                        await _send_error(send, scope, 413, "Request body too large")
                        return
                except ValueError:
                    pass
                break

        # Bodies chunked (sin Content-Length): contamos según llegan y cortamos.
        received = 0
        response_started = False

        async def counting_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > max_bytes:
                    raise _BodyTooLarge()
            return message

        async def guarded_send(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, guarded_send)
        except _BodyTooLarge:
            # Solo podemos responder si la app aún no empezó a hacerlo.
            if not response_started:
                await _send_error(send, scope, 413, "Request body too large")


class _BodyTooLarge(Exception):
    pass


class SlidingWindowLimiter:
    """Ventana deslizante en memoria: ``allow()`` responde y registra el intento.

    Sin locks a propósito: FastAPI corre en un único event loop y las operaciones
    sobre el deque son síncronas. En multi-proceso cada worker tiene su ventana
    (el límite efectivo escala con los workers — aceptable para este despliegue).
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        self.window = window_seconds
        self._hits: dict[tuple[str, str], deque[float]] = {}

    def allow(self, bucket: str, ip: str, limit: int) -> tuple[bool, float]:
        """Devuelve ``(permitido, segundos_hasta_reintento)``."""
        now = time.monotonic()
        key = (bucket, ip)
        q = self._hits.setdefault(key, deque())
        cutoff = now - self.window
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= limit:
            # Con limit=0 el deque puede estar vacío: el reintento es la ventana entera.
            oldest = q[0] if q else now
            return False, max(1.0, self.window - (now - oldest))
        q.append(now)
        return True, 0.0


class RateLimitMiddleware:
    """Aplica ``SlidingWindowLimiter`` a los POSTs sensibles (auth y LLM)."""

    def __init__(self, app) -> None:
        self.app = app
        self.limiter = SlidingWindowLimiter()

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not settings.rate_limit_enabled:
            await self.app(scope, receive, send)
            return

        bucket_limit = self._bucket_for(scope)
        if bucket_limit is None:
            await self.app(scope, receive, send)
            return

        bucket, limit = bucket_limit
        client = scope.get("client")
        ip = client[0] if client else "unknown"
        allowed, retry_after = self.limiter.allow(bucket, ip, limit)
        if not allowed:
            await _send_error(
                send,
                scope,
                429,
                "Too many requests. Try again shortly.",
                extra_headers=[(b"retry-after", str(int(retry_after)).encode())],
            )
            return

        await self.app(scope, receive, send)

    @staticmethod
    def _bucket_for(scope: dict) -> tuple[str, int] | None:
        if scope.get("method") != "POST":
            return None
        path = scope.get("path", "")
        if path in _AUTH_ROUTES:
            return "auth", settings.rate_limit_auth_per_minute
        if path in _LLM_ROUTES:
            return "llm", settings.rate_limit_llm_per_minute
        return None
