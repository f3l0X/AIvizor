"""`MockProvider` — implementación determinista de `LLMProvider`.

Razón de ser:
  1. **Tests sin coste.** El CI no debe llamar a APIs externas.
  2. **Dev local sin API key.** ``LLM_PROVIDER=mock`` y arrancas.
  3. **Doble función como contrato.** Si añades un campo al esquema y olvidas
     actualizar el mock, los tests fallan: te obliga a mantenerlo coherente.

Para el Analyzer el mock devuelve un objeto deducido del hash del input. Para
el Trainer mantiene un catálogo de plantillas por nivel × idioma y rota
aleatoriamente entre ellas (cada llamada genera un sample con id nuevo y
contenido posiblemente distinto). Esto evita la sensación de "siempre el mismo
ejemplo" cuando se prueba el flujo en local sin gastar API.

No intenta "imitar" la inteligencia del LLM; sólo devuelve un objeto válido
del ``response_model`` pedido.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel

from app.llm.base import LLMError
from app.schemas.analysis import AnalysisResult, Indicator
from app.schemas.common import Difficulty, IndicatorType, InputType, Language, Verdict
from app.schemas.training import TrainingSample

T = TypeVar("T", bound=BaseModel)


def _stable_score(seed: str) -> int:
    """Score 0-100 derivado del input. Determinista entre llamadas."""
    h = hashlib.sha256(seed.encode("utf-8")).digest()
    return h[0] * 100 // 255


def _verdict_for(score: int) -> Verdict:
    if score < 30:
        return Verdict.LEGIT
    if score < 70:
        return Verdict.SUSPICIOUS
    return Verdict.PHISHING


class MockProvider:
    """Cumple el ``LLMProvider`` Protocol sin tocar la red."""

    name = "mock"

    async def complete_structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        language: Language,
    ) -> T:
        if response_model is AnalysisResult:
            return self._mock_analysis(user, language)  # type: ignore[return-value]
        if response_model is TrainingSample:
            return self._mock_training_sample(user, language)  # type: ignore[return-value]
        raise LLMError(
            f"MockProvider no soporta el response_model {response_model.__name__}. "
            "Añade un branch en mock.py.",
            provider=self.name,
        )

    @staticmethod
    def _mock_analysis(user: str, language: Language) -> AnalysisResult:
        score = _stable_score(user)
        verdict = _verdict_for(score)

        if language is Language.ES:
            summary = (
                f"Análisis MOCK: riesgo {score}/100 ({verdict.value}). "
                "Sustituye LLM_PROVIDER por gemini o claude para resultados reales."
            )
            evidence = user[:120] if user else "(sin contenido)"
            explanation = (
                "Indicador de ejemplo generado por MockProvider para validar el "
                "pipeline sin gastar API."
            )
        else:
            summary = (
                f"MOCK analysis: risk {score}/100 ({verdict.value}). "
                "Switch LLM_PROVIDER to gemini or claude for real output."
            )
            evidence = user[:120] if user else "(empty)"
            explanation = (
                "Example indicator emitted by MockProvider so the pipeline can run "
                "without consuming API quota."
            )

        return AnalysisResult(
            risk_score=score,
            verdict=verdict,
            language=language,
            summary=summary,
            indicators=[
                Indicator(
                    type=IndicatorType.OTHER,
                    evidence=evidence,
                    explanation=explanation,
                )
            ],
        )

    @staticmethod
    def _mock_training_sample(user: str, language: Language) -> TrainingSample:
        # Id aleatorio: cada "next" inserta una fila nueva en training_attempts.
        sample_id = uuid4()

        # Inferimos la dificultad del propio prompt del usuario (lo monta el
        # servicio del trainer y siempre contiene "dificultad N" / "difficulty N").
        difficulty = _infer_difficulty_from_prompt(user)
        input_type = _infer_input_type_from_prompt(user)

        templates = _TEMPLATES[(difficulty, language)]
        tpl = random.choice(templates)  # noqa: S311  — randomness no criptográfica

        return TrainingSample(
            id=sample_id,
            input_type=input_type,
            language=language,
            difficulty=difficulty,
            content=tpl.content,
            true_verdict=tpl.true_verdict,
            true_indicators=tpl.indicators,
        )


# ---------------------------------------------------------------------------
# Helpers de inferencia
# ---------------------------------------------------------------------------

def _infer_difficulty_from_prompt(text: str) -> Difficulty:
    """El servicio del Trainer mete 'dificultad N' / 'difficulty N' en el user prompt."""
    lower = text.lower()
    for level in (5, 4, 3, 2, 1):
        if f"dificultad {level}" in lower or f"difficulty {level}" in lower:
            return Difficulty(level)
    return Difficulty.L2


def _infer_input_type_from_prompt(text: str) -> InputType:
    for kind in (InputType.URL, InputType.SMS, InputType.EMAIL):
        if f"`{kind.value}`" in text:
            return kind
    return InputType.EMAIL


# ---------------------------------------------------------------------------
# Catálogo de plantillas del Trainer
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _T:
    """Plantilla compacta — los tests no dependen del contenido textual, solo del
    set de `IndicatorType` que cada nivel ilustra."""

    content: str
    true_verdict: Verdict
    indicators: list[Indicator] = field(default_factory=list)


def _ind(t: IndicatorType, ev: str, ex: str) -> Indicator:
    return Indicator(type=t, evidence=ev, explanation=ex)


# === L1 — OBVIO (typos + dominio falso + urgencia). 3 variantes ES + 3 EN ===

_L1_ES = [
    _T(
        content=(
            "De: soporte@bbva-seguridad-online.ru\n"
            "Asunto: ¡URGENTE!!! Su cuenta sera cerrada en 24h\n\n"
            "Estimado cliente verifike sus datos AHORA en este link "
            "http://bbva-verificacion.ru/login o su cuenta sera CERRADA."
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "bbva-seguridad-online.ru",
                 "Dominio falso con TLD `.ru` haciéndose pasar por BBVA."),
            _ind(IndicatorType.URGENCY_LANGUAGE, "¡URGENTE!!! Su cuenta sera cerrada en 24h",
                 "Urgencia exagerada y amenaza, típico patrón de phishing."),
            _ind(IndicatorType.BRAND_OR_GRAMMAR_ERROR, "verifike",
                 "Falta ortográfica obvia en un correo supuestamente bancario."),
        ],
    ),
    _T(
        content=(
            "De: notificaciones@hacienda-gobierno.tk\n"
            "Asunto: !!ULTIMA OPORTUNIDAD!! Devolución pendiente 832.50 EUR\n\n"
            "Estimado contribullente, tiene una devolusion pendiente. Reclamala "
            "ANTES de 48h en https://hacienda-gobierno.tk/devolucion o se perdera "
            "para siempre."
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "hacienda-gobierno.tk",
                 "Dominio `.tk` (Tokelau) fingiendo ser la Agencia Tributaria."),
            _ind(IndicatorType.URGENCY_LANGUAGE, "!!ULTIMA OPORTUNIDAD!! ... ANTES de 48h ... se perdera",
                 "Amenaza temporal para obligar a actuar sin pensar."),
            _ind(IndicatorType.BRAND_OR_GRAMMAR_ERROR, "contribullente ... devolusion",
                 "Faltas ortográficas en un supuesto correo oficial."),
        ],
    ),
    _T(
        content=(
            "De: security@paypal-services.online\n"
            "Asunto: ⚠️ CUENTA SUSPENDIDA - Acción Requerida YA\n\n"
            "Su cuenta a sido temporalmente suspedida. Para reactibarla, haga "
            "click aqui INMEDIATAMENTE: http://paypal-services.online/reactivar"
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "paypal-services.online",
                 "Dominio inventado simulando PayPal."),
            _ind(IndicatorType.URGENCY_LANGUAGE, "CUENTA SUSPENDIDA ... INMEDIATAMENTE",
                 "Combinación clásica de amenaza + presión temporal."),
            _ind(IndicatorType.BRAND_OR_GRAMMAR_ERROR, "a sido ... suspedida ... reactibarla",
                 "Múltiples errores gramaticales que ninguna marca seria publicaría."),
        ],
    ),
]

_L1_EN = [
    _T(
        content=(
            "From: support@chase-security-online.ru\n"
            "Subject: URGENT!!! Your account will be CLOSED in 24h\n\n"
            "Dear customer pleese verfy your data NOW at "
            "http://chase-verify.ru/login or your account will be CLOSED."
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "chase-security-online.ru",
                 "Fake domain with `.ru` TLD impersonating Chase."),
            _ind(IndicatorType.URGENCY_LANGUAGE, "URGENT!!! Your account will be CLOSED in 24h",
                 "Excessive urgency and closure threat, classic phishing pattern."),
            _ind(IndicatorType.BRAND_OR_GRAMMAR_ERROR, "pleese verfy",
                 "Obvious typos in a supposedly bank-sent email."),
        ],
    ),
    _T(
        content=(
            "From: irs-refunds@irs-treasury.tk\n"
            "Subject: !!LAST CHANCE!! Pending refund $832.50\n\n"
            "Dear tax payer, you have a refund pendng. Claim it BEFORE 48h at "
            "https://irs-treasury.tk/refund or it will be lost forevr."
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "irs-treasury.tk",
                 "`.tk` domain (Tokelau) pretending to be the IRS."),
            _ind(IndicatorType.URGENCY_LANGUAGE, "!!LAST CHANCE!! ... BEFORE 48h ... lost forevr",
                 "Time pressure to force action without thinking."),
            _ind(IndicatorType.BRAND_OR_GRAMMAR_ERROR, "pendng ... forevr",
                 "Typos in a supposedly official email."),
        ],
    ),
    _T(
        content=(
            "From: security@paypal-services.online\n"
            "Subject: ⚠️ ACCOUNT SUSPENDED - Action Required NOW\n\n"
            "Your account hass been temporarily suspendd. To reactivat, "
            "click here IMMEDIATELY: http://paypal-services.online/reactivate"
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "paypal-services.online",
                 "Made-up domain impersonating PayPal."),
            _ind(IndicatorType.URGENCY_LANGUAGE, "ACCOUNT SUSPENDED ... IMMEDIATELY",
                 "Classic threat + time pressure combo."),
            _ind(IndicatorType.BRAND_OR_GRAMMAR_ERROR, "hass been ... suspendd ... reactivat",
                 "Multiple grammar errors no serious brand would publish."),
        ],
    ),
]

# === L2 — FÁCIL (señales claras pero sin errores groseros) ===

_L2_ES = [
    _T(
        content=(
            "De: servicio@netflix-soporte.com\n"
            "Asunto: Problema con tu método de pago\n\n"
            "Hemos detectado un problema con tu tarjeta. Actualiza tus datos "
            "antes de 24h en https://netflix-soporte.com/cuenta para evitar la "
            "suspensión del servicio."
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "netflix-soporte.com",
                 "El dominio oficial es netflix.com, no netflix-soporte.com."),
            _ind(IndicatorType.URGENCY_LANGUAGE, "antes de 24h ... evitar la suspensión",
                 "Presión temporal para forzar al usuario a meter datos."),
            _ind(IndicatorType.CREDENTIAL_REQUEST, "Actualiza tus datos",
                 "Pide datos de tarjeta vía un enlace en email — un servicio real "
                 "te diría que abras la app o la web oficial."),
        ],
    ),
    _T(
        content=(
            "De: dhl-tracking@dhl-envios.com\n"
            "Asunto: Tu paquete está retenido en aduanas\n\n"
            "Hola, tu envío DHL-928374 está retenido por falta de documentación. "
            "Para liberar el paquete, ingresa tus datos en "
            "https://dhl-envios.com/aduanas antes de 48h."
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "dhl-envios.com",
                 "DHL no usa dhl-envios.com como dominio principal."),
            _ind(IndicatorType.URGENCY_LANGUAGE, "antes de 48h",
                 "Plazo corto característico de campañas de phishing logístico."),
            _ind(IndicatorType.CREDENTIAL_REQUEST, "ingresa tus datos en https://dhl-envios.com/aduanas",
                 "Pide datos personales a través de un enlace en correo, no por la web oficial."),
        ],
    ),
    _T(
        content=(
            "De: noreply@microsoft-365-team.com\n"
            "Asunto: Su cuenta será desactivada en 72 horas\n\n"
            "Hemos detectado actividad sospechosa en su cuenta Microsoft. Para "
            "evitar la desactivación, verifique su identidad aquí: "
            "https://microsoft-365-team.com/verificar"
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "microsoft-365-team.com",
                 "Microsoft usa microsoft.com / microsoftonline.com, no este dominio."),
            _ind(IndicatorType.URGENCY_LANGUAGE, "desactivada en 72 horas",
                 "Amenaza con desactivación para presionar al usuario."),
            _ind(IndicatorType.CREDENTIAL_REQUEST, "verifique su identidad aquí",
                 "Pide login vía enlace de correo — Microsoft nunca lo haría así."),
        ],
    ),
]

_L2_EN = [
    _T(
        content=(
            "From: service@netflix-support.com\n"
            "Subject: Payment issue with your account\n\n"
            "We detected a problem with your card. Update your details within "
            "24h at https://netflix-support.com/account to avoid suspension."
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "netflix-support.com",
                 "Official domain is netflix.com, not netflix-support.com."),
            _ind(IndicatorType.URGENCY_LANGUAGE, "within 24h ... to avoid suspension",
                 "Time pressure to push the user to submit data."),
            _ind(IndicatorType.CREDENTIAL_REQUEST, "Update your details",
                 "Asks for card data via an email link — a real service would point "
                 "you to the official app or website."),
        ],
    ),
    _T(
        content=(
            "From: dhl-tracking@dhl-shipments.com\n"
            "Subject: Your package is held at customs\n\n"
            "Hi, your DHL shipment DHL-928374 is held due to missing paperwork. "
            "To release it, enter your details at "
            "https://dhl-shipments.com/customs within 48h."
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "dhl-shipments.com",
                 "DHL does not use dhl-shipments.com as a primary domain."),
            _ind(IndicatorType.URGENCY_LANGUAGE, "within 48h",
                 "Short deadline typical of logistics phishing campaigns."),
            _ind(IndicatorType.CREDENTIAL_REQUEST, "enter your details at https://dhl-shipments.com/customs",
                 "Asks for personal data via an email link instead of the official site."),
        ],
    ),
    _T(
        content=(
            "From: noreply@microsoft-365-team.com\n"
            "Subject: Your account will be deactivated in 72 hours\n\n"
            "We detected suspicious activity on your Microsoft account. To avoid "
            "deactivation, verify your identity here: "
            "https://microsoft-365-team.com/verify"
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "microsoft-365-team.com",
                 "Microsoft uses microsoft.com / microsoftonline.com, not this domain."),
            _ind(IndicatorType.URGENCY_LANGUAGE, "deactivated in 72 hours",
                 "Deactivation threat to pressure the user."),
            _ind(IndicatorType.CREDENTIAL_REQUEST, "verify your identity here",
                 "Asks for login via email link — Microsoft would never do this."),
        ],
    ),
]

# === L3 — MEDIO (micropagos, link mismatch, sutil) ===

_L3_ES = [
    _T(
        content=(
            "De: notificaciones@correos-postal.com\n"
            "Asunto: Paquete pendiente de entrega\n\n"
            "Hola, tenemos un paquete a su nombre que no se ha podido entregar. "
            "Para reprogramar, abone los 1.99€ de gestión en "
            "https://correos-postal.com/pagar"
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "correos-postal.com",
                 "No es el dominio oficial de Correos (sería correos.es)."),
            _ind(IndicatorType.PAYMENT_REQUEST, "abone los 1.99€ de gestión",
                 "Pedir un micro-pago para 'desbloquear' un envío es señal típica de fraude."),
        ],
    ),
    _T(
        content=(
            "De: facturacion@iberdrola-clientes.net\n"
            "Asunto: Última factura pendiente — corte programado\n\n"
            "Estimado cliente, queda pendiente una factura de 47.32€. Evite el "
            "corte abonando aquí: <a href='http://pago-clientes.net/iberdrola'>"
            "https://iberdrola.es/pago</a>"
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "iberdrola-clientes.net",
                 "Iberdrola usa iberdrola.es, no iberdrola-clientes.net."),
            _ind(IndicatorType.LINK_MISMATCH, "href='http://pago-clientes.net/iberdrola'>https://iberdrola.es/pago",
                 "El texto del enlace dice iberdrola.es pero apunta a pago-clientes.net — el truco más clásico."),
            _ind(IndicatorType.PAYMENT_REQUEST, "Evite el corte abonando",
                 "Pago urgente bajo amenaza, sin posibilidad de verificarlo en la app oficial."),
        ],
    ),
    _T(
        content=(
            "De: soporte@amazon-pedidos-es.com\n"
            "Asunto: Tu pedido #112-3829471 — confirmación de dirección\n\n"
            "Para garantizar la entrega de tu pedido, confirma tu dirección y "
            "abona los 0.99€ de re-verificación postal en "
            "https://amazon-pedidos-es.com/confirmar"
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "amazon-pedidos-es.com",
                 "Amazon usa amazon.es, no amazon-pedidos-es.com."),
            _ind(IndicatorType.PAYMENT_REQUEST, "abona los 0.99€ de re-verificación postal",
                 "Cobro inventado ('re-verificación postal') que Amazon nunca aplicaría."),
        ],
    ),
]

_L3_EN = [
    _T(
        content=(
            "From: notifications@usps-postal.com\n"
            "Subject: Package pending delivery\n\n"
            "Hi, we have a package for you that we could not deliver. "
            "To reschedule, pay the $1.99 handling fee at "
            "https://usps-postal.com/pay"
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "usps-postal.com",
                 "Not the official USPS domain (usps.com)."),
            _ind(IndicatorType.PAYMENT_REQUEST, "pay the $1.99 handling fee",
                 "Requesting a small payment to 'unlock' a delivery is a classic fraud signal."),
        ],
    ),
    _T(
        content=(
            "From: billing@conedison-clients.net\n"
            "Subject: Last unpaid bill — scheduled disconnection\n\n"
            "Dear customer, an invoice of $47.32 remains unpaid. Avoid "
            "disconnection by paying here: "
            "<a href='http://payment-clients.net/conedison'>https://conedison.com/pay</a>"
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "conedison-clients.net",
                 "Con Edison uses conedison.com, not conedison-clients.net."),
            _ind(IndicatorType.LINK_MISMATCH, "href='http://payment-clients.net/conedison'>https://conedison.com/pay",
                 "The link text says conedison.com but points to payment-clients.net — classic trick."),
            _ind(IndicatorType.PAYMENT_REQUEST, "Avoid disconnection by paying",
                 "Urgent payment under threat, with no way to verify in the official app."),
        ],
    ),
    _T(
        content=(
            "From: support@amazon-orders-us.com\n"
            "Subject: Your order #112-3829471 — address confirmation\n\n"
            "To guarantee delivery, confirm your address and pay the "
            "$0.99 postal re-verification fee at "
            "https://amazon-orders-us.com/confirm"
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "amazon-orders-us.com",
                 "Amazon uses amazon.com, not amazon-orders-us.com."),
            _ind(IndicatorType.PAYMENT_REQUEST, "pay the $0.99 postal re-verification fee",
                 "Made-up fee ('postal re-verification') that Amazon would never charge."),
        ],
    ),
]

# === L4 — DIFÍCIL (look-alike sutil, copy profesional) ===

_L4_ES = [
    _T(
        content=(
            "De: soporte@santаnder.es\n"   # note: 'а' es cirílica (U+0430)
            "Asunto: Aviso importante sobre tu próximo cargo\n\n"
            "Estimado cliente, hemos detectado un cargo anómalo de 423,15€. Si "
            "no lo reconoce, puede anularlo desde su Área Cliente. Si lo "
            "reconoce, no es necesario hacer nada.\n\n"
            "Atentamente,\nEquipo Santander"
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "santаnder.es",
                 "El dominio parece santander.es pero la primera 'a' es una cirílica (U+0430). "
                 "Imposible distinguirlo a simple vista — clásico ataque homográfico."),
        ],
    ),
    _T(
        content=(
            "De: facturacion@stripe.cm\n"
            "Asunto: Tu factura mensual está lista\n\n"
            "Hola, tu factura del mes ya está disponible. Puedes descargarla "
            "directamente desde tu panel en https://dashboard.stripe.cm/invoices"
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "stripe.cm",
                 "El TLD real de Stripe es `.com`. Aquí pone `.cm` (Camerún) — "
                 "typosquatting clásico que aprovecha errores de tecleo."),
        ],
    ),
    _T(
        content=(
            "De: hr@miempresa-rrhh.com\n"
            "Asunto: Actualización de tu nómina — acción opcional\n\n"
            "Hola, hemos preparado un resumen de tu nómina del mes en el portal "
            "de RRHH. Puedes consultarlo en cualquier momento aquí: "
            "https://portal-rrhh-miempresa.com/nomina (login con tu email "
            "corporativo)."
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "miempresa-rrhh.com vs portal-rrhh-miempresa.com",
                 "El remitente y el dominio del enlace usan ligeras variantes — un atacante "
                 "que ha hecho ingeniería social previa al ataque sabe el nombre de tu empresa."),
            _ind(IndicatorType.CREDENTIAL_REQUEST, "login con tu email corporativo",
                 "Phishing dirigido (spear-phishing): pide credenciales corporativas "
                 "haciéndose pasar por RRHH."),
        ],
    ),
]

_L4_EN = [
    _T(
        content=(
            "From: support@bаnkofamerica.com\n"   # 'а' cirílica
            "Subject: Notice about your upcoming charge\n\n"
            "Dear customer, we detected an unusual charge of $423.15. If you "
            "do not recognize it, you can cancel it from your Customer Area. "
            "If you recognize it, no action is needed.\n\n"
            "Regards,\nBank of America Team"
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "bаnkofamerica.com",
                 "Looks like bankofamerica.com but the 'a' after 'b' is Cyrillic (U+0430). "
                 "Invisible at first glance — classic homograph attack."),
        ],
    ),
    _T(
        content=(
            "From: billing@stripe.cm\n"
            "Subject: Your monthly invoice is ready\n\n"
            "Hi, this month's invoice is available. You can download it directly "
            "from your dashboard at https://dashboard.stripe.cm/invoices"
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "stripe.cm",
                 "Stripe's real TLD is `.com`. Here it's `.cm` (Cameroon) — "
                 "classic typosquatting that exploits typing mistakes."),
        ],
    ),
    _T(
        content=(
            "From: hr@mycompany-hr.com\n"
            "Subject: Payroll update — optional action\n\n"
            "Hi, we prepared a summary of this month's payroll on the HR portal. "
            "You can review it anytime here: "
            "https://hr-portal-mycompany.com/payroll (sign in with your "
            "corporate email)."
        ),
        true_verdict=Verdict.PHISHING,
        indicators=[
            _ind(IndicatorType.LOOKALIKE_DOMAIN, "mycompany-hr.com vs hr-portal-mycompany.com",
                 "Sender and link domain use slightly different variants — an attacker "
                 "who has done social engineering knows your company name."),
            _ind(IndicatorType.CREDENTIAL_REQUEST, "sign in with your corporate email",
                 "Targeted spear-phishing: asks for corporate credentials by impersonating HR."),
        ],
    ),
]

# === L5 — EXPERTO (LEGÍTIMOS para aprender a no marcar todo como phishing) ===

_L5_ES = [
    _T(
        content=(
            "De: facturacion@stripe.com\n"
            "Asunto: Tu factura mensual de Stripe (junio 2026)\n\n"
            "Hola, adjuntamos la factura del mes. Puedes consultarla y "
            "descargarla desde tu panel en https://dashboard.stripe.com/invoices\n"
            "Si tienes dudas, responde a este correo o escribe a support@stripe.com."
        ),
        true_verdict=Verdict.LEGIT,
        indicators=[],
    ),
    _T(
        content=(
            "De: noreply@github.com\n"
            "Asunto: [GitHub] A new SSH key was added to your account\n\n"
            "Hi, a new SSH key (ed25519:AAAA...) was added to your GitHub "
            "account from IP 81.45.X.X (Madrid, ES). If this was you, you can "
            "ignore this email. If not, revoke the key at "
            "https://github.com/settings/keys and reset your password."
        ),
        true_verdict=Verdict.LEGIT,
        indicators=[],
    ),
    _T(
        content=(
            "De: pedidos@elcorteingles.es\n"
            "Asunto: Tu pedido 80239485 — confirmación\n\n"
            "Gracias por tu pedido. Lo recibirás el martes 30/06. Puedes "
            "consultar el seguimiento en https://www.elcorteingles.es/"
            "mis-pedidos sin necesidad de contraseña adicional."
        ),
        true_verdict=Verdict.LEGIT,
        indicators=[],
    ),
]

_L5_EN = [
    _T(
        content=(
            "From: billing@stripe.com\n"
            "Subject: Your monthly Stripe invoice (June 2026)\n\n"
            "Hi, please find this month's invoice attached. You can view and "
            "download it from your dashboard at https://dashboard.stripe.com/invoices.\n"
            "If you have questions, reply to this email or write to support@stripe.com."
        ),
        true_verdict=Verdict.LEGIT,
        indicators=[],
    ),
    _T(
        content=(
            "From: noreply@github.com\n"
            "Subject: [GitHub] A new SSH key was added to your account\n\n"
            "Hi, a new SSH key (ed25519:AAAA...) was added to your GitHub "
            "account from IP 81.45.X.X (Madrid, ES). If this was you, you can "
            "ignore this email. If not, revoke the key at "
            "https://github.com/settings/keys and reset your password."
        ),
        true_verdict=Verdict.LEGIT,
        indicators=[],
    ),
    _T(
        content=(
            "From: orders@target.com\n"
            "Subject: Your order 80239485 — confirmation\n\n"
            "Thanks for your order. It will arrive on Tuesday 06/30. You can "
            "track it at https://www.target.com/orders without needing to "
            "re-enter your password."
        ),
        true_verdict=Verdict.LEGIT,
        indicators=[],
    ),
]


_TEMPLATES: dict[tuple[Difficulty, Language], list[_T]] = {
    (Difficulty.L1, Language.ES): _L1_ES,
    (Difficulty.L1, Language.EN): _L1_EN,
    (Difficulty.L2, Language.ES): _L2_ES,
    (Difficulty.L2, Language.EN): _L2_EN,
    (Difficulty.L3, Language.ES): _L3_ES,
    (Difficulty.L3, Language.EN): _L3_EN,
    (Difficulty.L4, Language.ES): _L4_ES,
    (Difficulty.L4, Language.EN): _L4_EN,
    (Difficulty.L5, Language.ES): _L5_ES,
    (Difficulty.L5, Language.EN): _L5_EN,
}
