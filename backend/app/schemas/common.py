"""Enums y tipos comunes compartidos entre Analyzer y Trainer.

Centralizados aquí para que cualquier cambio del contrato (p. ej. añadir un nuevo
`IndicatorType`) impacte a la vez al backend, a los prompts y a la validación de salida
del LLM. Los providers concretos (Gemini, Claude) traducen estos enums al formato JSON
schema que cada uno entiende, pero la única fuente de verdad son estas clases.
"""

from enum import Enum


class Language(str, Enum):
    """Idioma del análisis. Se inyecta en el system prompt y condiciona la respuesta."""

    ES = "es"
    EN = "en"


class InputType(str, Enum):
    """Naturaleza del contenido a analizar. Decide qué heurísticas pesa el prompt."""

    EMAIL = "email"
    URL = "url"
    SMS = "sms"


class Verdict(str, Enum):
    """Veredicto agregado del Analizador. Mapea (a grandes rasgos) con `risk_score`:

    - ``LEGIT``      → 0-29
    - ``SUSPICIOUS`` → 30-69
    - ``PHISHING``   → 70-100

    El LLM puede salirse del rango si lo justifican los indicadores; el frontend se queda
    con el ``verdict`` como semáforo y con el ``risk_score`` como matiz.
    """

    LEGIT = "legit"
    SUSPICIOUS = "suspicious"
    PHISHING = "phishing"


class IndicatorType(str, Enum):
    """Catálogo cerrado de señales que el Analizador puede emitir en v1.

    Mantenerlo cerrado nos da tres cosas: (1) validación dura en la salida del LLM
    (cualquier valor fuera de aquí → error), (2) UI consistente (cada tipo puede tener
    su icono y color en `IndicatorCard`), (3) métricas comparables a lo largo del tiempo.
    """

    SENDER_SPOOFING = "sender_spoofing"
    LOOKALIKE_DOMAIN = "lookalike_domain"
    LINK_MISMATCH = "link_mismatch"
    URGENCY_LANGUAGE = "urgency_language"
    CREDENTIAL_REQUEST = "credential_request"
    PAYMENT_REQUEST = "payment_request"
    BRAND_OR_GRAMMAR_ERROR = "brand_or_grammar_error"
    SUSPICIOUS_ATTACHMENT = "suspicious_attachment"
    OTHER = "other"


class Difficulty(int, Enum):
    """Niveles del Entrenador (1 = obvio, 5 = casi indistinguible de legítimo)."""

    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4
    L5 = 5
