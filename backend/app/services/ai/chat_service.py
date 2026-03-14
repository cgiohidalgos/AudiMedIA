"""
Servicio de chat con historia clínica usando RAG básico.
"""
import json
import logging
from openai import AsyncOpenAI
import asyncio
import random
from app.core.config import settings
from app.schemas.audit import ChatResponse, ChatReference

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Retry utilitario para llamadas a OpenAI
async def retry_with_backoff(func, *args, max_retries=5, base_delay=2, max_delay=32, **kwargs):
    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Manejar solo errores 429 o de red/transitorios
            if hasattr(e, 'status_code') and e.status_code == 429:
                wait = min(base_delay * 2 ** (attempt - 1), max_delay)
                wait = wait * (0.8 + 0.4 * random.random())  # Jitter
                logger.warning(f"⏳ Límite de tasa alcanzado (429). Reintentando en {wait:.1f}s (intento {attempt}/{max_retries})...")
                await asyncio.sleep(wait)
            elif 'rate limit' in str(e).lower() or '429' in str(e):
                wait = min(base_delay * 2 ** (attempt - 1), max_delay)
                wait = wait * (0.8 + 0.4 * random.random())
                logger.warning(f"⏳ Rate limit detectado. Reintentando en {wait:.1f}s (intento {attempt}/{max_retries})...")
                await asyncio.sleep(wait)
            elif attempt == max_retries:
                logger.error(f"❌ Error persistente tras {max_retries} reintentos: {type(e).__name__}: {str(e)}")
                raise
            else:
                logger.warning(f"⚠️ Error transitorio: {type(e).__name__}: {str(e)}. Reintentando...")
                await asyncio.sleep(2)
    raise RuntimeError("No se pudo completar la llamada tras varios reintentos")

SYSTEM_PROMPT = """Eres un asistente de auditoría médica colombiana experto en:
- Normativa: Ley 1438/2011, Decreto 780/2016, Resolución 1995/1999
- Codificación: CIE10, CUPS
- Glosas hospitalarias y auditoría concurrente

INSTRUCCIONES:
1. Responde ÚNICAMENTE con base en la información de la historia clínica proporcionada.
2. Cuando cites información específica del documento, indica la fuente en formato: (página X) o (págs. X, Y).
3. Sé técnico, preciso y varía tus respuestas según la pregunta.
4. Si no encuentras la información, dilo claramente.
5. Para análisis clínicos, finaliza con: '⚠️ Esta respuesta es generada por IA como apoyo al criterio del auditor y no reemplaza la revisión clínica profesional.'"""


async def answer_question(patient, question: str, history: list) -> ChatResponse:
    """Genera respuesta al chat usando los datos clínicos del paciente."""

    # Construir contexto con datos del paciente para el SYSTEM prompt
    context = f"""DATOS DEL PACIENTE:
- ID: {patient.label}
- Diagnóstico: {patient.diagnostico_principal or 'No documentado'} ({patient.codigo_cie10 or 'Sin código'})
- Edad: {patient.edad or 'N/A'} años, Sexo: {patient.sexo or 'N/A'}
- Días hospitalización: {patient.dias_hospitalizacion or 'No registrado'}
- Medicamentos: {len(patient.medicamentos or [])} registrados
- Estudios: {len(patient.estudios_solicitados or [])} solicitados
- Procedimientos: {len(patient.procedimientos or [])} realizados

DATOS COMPLETOS:
{json.dumps({
    'medicamentos': patient.medicamentos or [],
    'evoluciones': patient.evoluciones or [],
    'estudios': patient.estudios_solicitados or [],
    'procedimientos': patient.procedimientos or [],
    'diagnosticos_secundarios': patient.diagnosticos_secundarios or [],
    'antecedentes': patient.antecedentes or {}
}, ensure_ascii=False, indent=2)}"""

    # Construir mensajes: system con contexto + historial + pregunta actual
    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{context}"},
    ]

    # Agregar historial de conversación (últimos 10 mensajes)
    for msg in history[-10:]:
        messages.append({"role": msg.role, "content": msg.content})

    # Agregar la pregunta actual
    messages.append({"role": "user", "content": question})

    logger.info(f"💬 Chat - Pregunta: '{question}'")
    logger.info(f"📝 Chat - Historial previo: {len(history)} mensajes")
    logger.info(f"📋 Chat - Total mensajes a OpenAI: {len(messages)} (system=1, historial={len(history)}, actual=1)")
    logger.info(f"🔍 Chat - Contexto incluye: {len(patient.medicamentos or [])} meds, {len(patient.evoluciones or [])} evoluciones")
    
    try:
        async def call():
            return await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.7,  # Mayor temperatura para respuestas más variadas
                max_tokens=500,
            )
        response = await retry_with_backoff(call)
        answer = response.choices[0].message.content
        logger.info(f"✅ Respuesta generada ({len(answer)} chars): {answer[:150]}...")
        logger.info(f"🎯 Tokens usados: prompt={response.usage.prompt_tokens}, completion={response.usage.completion_tokens}, total={response.usage.total_tokens}")
    except Exception as e:
        logger.error(f"❌ ERROR en chat: {type(e).__name__}: {str(e)}")
        logger.exception("Traceback completo:")
        raise

    # Extraer referencias de página si las hay (simplificado)
    referencias = []
    import re
    matches = re.findall(r'p[áa]gina\s+(\d+)', answer, re.IGNORECASE)
    for match in matches:
        referencias.append(ChatReference(pagina=int(match), fragmento=""))

    return ChatResponse(answer=answer, referencias=referencias)


async def answer_question_multi(patients: list, question: str) -> ChatResponse:
    """Genera respuesta al chat para múltiples pacientes simultáneamente."""
    patients_context = ""
    for patient in patients[:10]:  # máximo 10 pacientes en contexto
        evols = patient.evoluciones or []
        last_evol_date = "No registrada"
        if evols and isinstance(evols[-1], dict):
            last_evol_date = evols[-1].get("fecha") or evols[-1].get("date") or "No registrada"
        patients_context += (
            f"\n• {patient.label} | {patient.diagnostico_principal or 'Sin diagnóstico'}"
            f" | {patient.dias_hospitalizacion or 0} días"
            f" | {len(evols)} evoluciones (últ: {last_evol_date})"
            f" | {len(patient.medicamentos or [])} meds"
            f" | {len(patient.estudios_solicitados or [])} estudios"
        )

    messages = [
        {
            "role": "system",
            "content": (
                f"Eres un asistente de auditoría médica. Tienes el resumen de {len(patients)} pacientes "
                f"hospitalizados. Responde la pregunta analizando todos los pacientes. "
                f"Identifica cada uno por su label. Sé conciso y estructurado.\n\n"
                f"PACIENTES:{patients_context}"
            ),
        },
        {"role": "user", "content": question},
    ]

    try:
        async def call():
            return await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.4,
                max_tokens=700,
            )
        response = await retry_with_backoff(call)
        answer = response.choices[0].message.content
        logger.info(f"💬 Multi-chat respondido para {len(patients)} pacientes")
    except Exception as e:
        logger.error(f"❌ ERROR en multi-chat: {type(e).__name__}: {str(e)}")
        raise

    return ChatResponse(
        answer=answer,
        referencias=[],
        patient_ids=[str(p.id) for p in patients],
    )
