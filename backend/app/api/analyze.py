"""Endpoint HTTP del Analyzer: ``POST /api/analyze``.

Solo orquesta inyección de dependencias y traducción de excepciones.
La lógica vive en `services/analyzer.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import AnalysisRepository, SqlAnalysisRepository
from app.db.session import get_db
from app.llm.base import LLMError, LLMProvider
from app.llm.factory import get_llm as _factory_get_llm
from app.schemas.analysis import AnalysisResult, AnalyzeRequest
from app.services.analyzer import analyze_content

router = APIRouter(prefix="/api", tags=["analyzer"])


def get_llm() -> LLMProvider:
    """Dependency override-able en tests."""
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
