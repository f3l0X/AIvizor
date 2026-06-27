"""Detector de patrones de prompt injection en el contenido a analizar.

**No bloquea**: observa. La filosofía del Analyzer es que cualquier intento de
manipulación dentro del contenido es a su vez una señal de phishing y debe
sobrevivir hasta el LLM (que lo marca como indicador). Aquí solo etiquetamos para:

  - métricas (cuántos requests llegan con payloads conocidos),
  - logging estructurado (auditoría),
  - tests deterministas (sabemos detectar patrones de manual).

Esto **no** sustituye al LLM ni al system prompt — es un cinturón más. Un atacante
suficientemente creativo puede esquivar estos patrones; la barrera definitiva es
la validación de salida del schema (`AnalysisResult`).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum


class SignalKind(str, Enum):
    """Tipos de patrón. Mantener cerrado para que las métricas sean comparables."""

    INSTRUCTION_OVERRIDE = "instruction_override"
    ROLE_SPOOFING = "role_spoofing"
    DELIMITER_ESCAPE = "delimiter_escape"
    PROMPT_DISCLOSURE = "prompt_disclosure"
    ENCODING_SMUGGLING = "encoding_smuggling"
    INVISIBLE_CHARS = "invisible_chars"
    SYSTEM_TAG = "system_tag"


@dataclass(frozen=True)
class InjectionSignal:
    kind: SignalKind
    excerpt: str  # fragmento que disparó la detección (máx 80 chars)


# Patrones bilingües ES/EN. Lista no exhaustiva — añadir según vayan apareciendo
# en producción (lo registramos en logs y revisamos métricas).
_INSTRUCTION_OVERRIDE_PATTERNS = [
    r"ignor[ae]\s+(?:las|todas|todo|las\s+anteriores|las\s+instrucciones|previous)",
    r"ignore\s+(?:all|previous|prior|the\s+above|the\s+system)",
    r"disregard\s+(?:all|previous|the\s+above)",
    r"olvida\s+(?:lo|todo|las\s+instrucciones)",
    r"forget\s+(?:everything|previous|all)",
    r"new\s+instructions?:",
    r"nuevas?\s+instrucciones?:",
    r"override\s+(?:your|the)\s+(?:rules|instructions)",
]

_ROLE_SPOOFING_PATTERNS = [
    r"(?i)\byou\s+are\s+now\b",
    r"(?i)\bact\s+as\b",
    r"(?i)\bahora\s+eres\b",
    r"(?i)\bactúa\s+como\b",
    r"(?i)\bpretend\s+(?:to\s+be|you\s+are)\b",
    r"(?i)from\s+now\s+on,?\s+you",
    r"(?i)a\s+partir\s+de\s+ahora",
]

_PROMPT_DISCLOSURE_PATTERNS = [
    # Acepta "show me your instructions", "reveal your system prompt", etc.
    r"(?i)\b(?:reveal|show|print|display|repeat)\s+(?:me\s+|us\s+)?(?:your|the)\s+(?:system\s+|original\s+)?(?:prompt|instructions|rules)",
    r"(?i)\b(?:revela|muestra|imprime|enséñame|enseñame|dame)\s+(?:tus|el|las|tu)\s+(?:instrucciones|prompt|reglas)",
    r"(?i)what\s+(?:are\s+)?your\s+(?:system\s+)?(?:instructions|rules|prompt)",
    r"(?i)cuál(?:es)?\s+son\s+tus\s+(?:instrucciones|reglas)",
]

_SYSTEM_TAG_PATTERNS = [
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"<\|system\|>",
    r"\[SYSTEM\]",
    r"\[INST\]",
    r"<<SYS>>",
]

_ENCODING_SMUGGLING_PATTERNS = [
    # Bloques base64 largos y sospechosos (heurística: ≥ 40 chars).
    r"[A-Za-z0-9+/]{40,}={0,2}",
    # rot13 marker, hex blobs, etc.
    r"(?i)\brot13\b",
    r"(?i)decode\s+(?:the|this)",
    r"(?i)decodifica\s+(?:el|esto)",
]

_DELIMITER_TOKENS = (
    "<<<USER_CONTENT_START>>>",
    "<<<USER_CONTENT_END>>>",
)

# Caracteres invisibles / de control comunes en smuggling (zero-width, BOM, etc.).
_INVISIBLE_CHARS = frozenset(
    [
        "​",  # zero-width space
        "‌",  # zero-width non-joiner
        "‍",  # zero-width joiner
        "⁠",  # word joiner
        "﻿",  # BOM
        "‮",  # right-to-left override
        "‭",  # left-to-right override
    ]
)


def _excerpt(text: str, match_start: int, max_len: int = 80) -> str:
    start = max(0, match_start - 10)
    end = min(len(text), match_start + max_len)
    return text[start:end].replace("\n", " ").strip()


def _search_patterns(text: str, patterns: list[str], kind: SignalKind) -> list[InjectionSignal]:
    out: list[InjectionSignal] = []
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            out.append(InjectionSignal(kind=kind, excerpt=_excerpt(text, m.start())))
    return out


def detect(content: str) -> list[InjectionSignal]:
    """Devuelve la lista de patrones encontrados (puede estar vacía).

    Determinista: misma entrada → misma salida. Pensado para tests y métricas.
    """
    signals: list[InjectionSignal] = []

    if not content:
        return signals

    signals.extend(_search_patterns(content, _INSTRUCTION_OVERRIDE_PATTERNS, SignalKind.INSTRUCTION_OVERRIDE))
    signals.extend(_search_patterns(content, _ROLE_SPOOFING_PATTERNS, SignalKind.ROLE_SPOOFING))
    signals.extend(_search_patterns(content, _PROMPT_DISCLOSURE_PATTERNS, SignalKind.PROMPT_DISCLOSURE))
    signals.extend(_search_patterns(content, _SYSTEM_TAG_PATTERNS, SignalKind.SYSTEM_TAG))
    signals.extend(_search_patterns(content, _ENCODING_SMUGGLING_PATTERNS, SignalKind.ENCODING_SMUGGLING))

    for token in _DELIMITER_TOKENS:
        idx = content.find(token)
        if idx >= 0:
            signals.append(
                InjectionSignal(kind=SignalKind.DELIMITER_ESCAPE, excerpt=_excerpt(content, idx))
            )

    if any(ch in _INVISIBLE_CHARS for ch in content):
        first = next(i for i, ch in enumerate(content) if ch in _INVISIBLE_CHARS)
        signals.append(
            InjectionSignal(
                kind=SignalKind.INVISIBLE_CHARS,
                excerpt=_describe_invisible(content, first),
            )
        )

    return signals


def _describe_invisible(content: str, idx: int) -> str:
    char = content[idx]
    name = unicodedata.name(char, f"U+{ord(char):04X}")
    return f"{name} at position {idx}"
