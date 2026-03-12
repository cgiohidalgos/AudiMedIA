"""
Servicio de chat con historia clínica usando RAG básico.
"""
import json
import logging
from openai import AsyncOpenAI
from app.core.config import settings
from app.schemas.audit import ChatResponse, ChatReference

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """Eres un asistente de auditoría médica colombiana experto en:
- Normativa: Ley 1438/2011, Decreto 780/2016, Resolución 1995/1999
- Codificación: CIE10, CUPS
- Glosas hospitalarias y auditoría concurrente

Responde las preguntas del auditor médico con base ÚNICAMENTE en la información de la historia clínica.
Cada pregunta es diferente - analiza cuidadosamente lo que te preguntan y responde específicamente.
Sé técnico, preciso y varía tus respuestas según la pregunta.
Si no encuentras la información, dilo claramente."""


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
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=0.7,  # Mayor temperatura para respuestas más variadas
            max_tokens=500,
        )
        
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
