from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.admin import router as admin_router
from app.api.analyze import router as analyze_router
from app.api.auth import router as auth_router
from app.api.keys import router as keys_router
from app.api.train import router as train_router
from app.config import settings
from app.db.repositories import SqlUserRepository
from app.db.session import session_scope
from app.services.auth import ensure_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Siembra del admin inicial (idempotente). No hace nada si ADMIN_EMAIL/PASSWORD
    # están vacíos — caso por defecto en tests, que así no tocan la BD.
    if settings.admin_email and settings.admin_password:
        async with session_scope() as session:
            await ensure_admin(SqlUserRepository(session))
    yield


app = FastAPI(
    title="AIvizor API",
    description="Anti-phishing analyzer + trainer powered by LLMs.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _cors_headers(request: Request) -> dict[str, str]:
    """Cabeceras CORS para una respuesta de error, replicando la política del
    middleware (echo del Origin si está permitido + credenciales)."""
    origin = request.headers.get("origin")
    if origin and origin in settings.cors_origins_list:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return {}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Da una respuesta 500 con cabeceras CORS ante cualquier excepción no controlada.

    FastAPI sirve los 500 no controlados por encima del ``CORSMiddleware``, así que
    sin esto la respuesta llega al navegador SIN cabeceras CORS: el navegador la
    bloquea y el cliente ve un falso "no hay conexión" en vez del error real. El
    `raise` posterior de Starlette sigue registrando el traceback en el servidor.
    """
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers=_cors_headers(request),
    )


app.include_router(analyze_router)
app.include_router(train_router)
app.include_router(auth_router)
app.include_router(keys_router)
app.include_router(admin_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "aivizor-backend",
        "version": app.version,
        "llm_provider": settings.llm_provider,
    }
