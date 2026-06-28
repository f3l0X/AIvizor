"""Endpoint HTTP del Analyzer: ``POST /api/analyze``.

Solo orquesta inyección de dependencias y traducción de excepciones.
La lógica vive en `services/analyzer.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user_optional
from app.api.keys import get_api_key_repo
from app.db.repositories import AnalysisRepository, ApiKeyRepository, SqlAnalysisRepository
from app.db.session import get_db
from app.llm.base import LLMError, LLMProvider
from app.llm.factory import get_llm as _factory_get_llm
from app.schemas.analysis import AnalysisResult, AnalyzeRequest
from app.schemas.auth import UserInDB
from app.services.analyzer import analyze_content
from app.services.byok import resolve_provider_for_user

router = APIRouter(prefix="/api", tags=["analyzer"])


async def get_llm(
    user: UserInDB | None = Depends(get_current_user_optional),
    api_key_repo: ApiKeyRepository = Depends(get_api_key_repo),
) -> LLMProvider:
    """Resuelve el provider de la petición (override-able en tests).

    Si hay un usuario logueado con clave BYOK, usa su cuenta de LLM; si no, cae al
    provider por defecto del servidor (uso anónimo / demo).
    """
    if user is not None:
        try:
            byok = await resolve_provider_for_user(user.id, repo=api_key_repo)
        except LLMError as e:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e
        if byok is not None:
            return byok
    return _factory_get_llm()


def get_analysis_repo(
    session: AsyncSession = Depends(get_db),
) -> AnalysisRepository:
    """Dependency override-able en tests."""
    return SqlAnalysisRepository(session)


@router.post(
    "/analyze",
    response_model=AnalysisResult,
    status_code=status.HTTP_200_OK,
)
async def analyze(
    payload: AnalyzeRequest,
    llm: LLMProvider = Depends(get_llm),
    repo: AnalysisRepository = Depends(get_analysis_repo),
) -> AnalysisResult:
    try:
        return await analyze_content(payload, llm=llm, repo=repo)
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM provider failed: {e}",
        ) from e
