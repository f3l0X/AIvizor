"""Esquemas Pydantic del dominio. Reexporta para acceso plano desde otros módulos."""

from app.schemas.analysis import (
    AnalysisResult,
    AnalyzeRequest,
    Indicator,
)
from app.schemas.common import (
    Difficulty,
    IndicatorType,
    InputType,
    Language,
    Verdict,
)
from app.schemas.training import (
    TrainingAnswer,
    TrainingFeedback,
    TrainingNextRequest,
    TrainingSample,
    TrainingSamplePublic,
)

__all__ = [
    "AnalysisResult",
    "AnalyzeRequest",
    "Difficulty",
    "Indicator",
    "IndicatorType",
    "InputType",
    "Language",
    "TrainingAnswer",
    "TrainingFeedback",
    "TrainingNextRequest",
    "TrainingSample",
    "TrainingSamplePublic",
    "Verdict",
]
