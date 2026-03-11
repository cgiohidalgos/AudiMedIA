"""
Servicio de chat con historia clínica usando RAG básico.
"""
import json
from openai import AsyncOpenAI
from app.core.config import settings
from app.schemas.audit import ChatResponse, ChatReference

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """Eres un asistente de auditoría médica colombiana experto en:
- Normativa: Ley 1438/2011, Decreto 780/2016, Resolución 1995/1999
- Codificación: CIE10, CUPS
- Glosas hospitalarias y auditoría concurrente

El usuario es un auditor médico. Responde con base en la información de la historia clínica proporcionada.
Cuando cites información, indica el número de página si está disponible.
Sé conciso y técnico. Si no encuentras la información, dilo claramente."""


async def answer_question(patient, question: str, history: list) -> ChatResponse:
    """Genera respuesta al chat usando los datos clínicos del paciente."""

    # Construir contexto con datos del paciente
    context = f"""Historia clínica: {patient.label}
Diagnóstico principal: {patient.diagnostico_principal or 'No documentado'}
Código CIE10: {patient.codigo_cie10 or 'No asignado'}
Días de hospitalización: {patient.dias_hospitalizacion or 'No registrado'}
Medicamentos: {json.dumps(patient.medicamentos or [], ensure_ascii=False)}
Evoluciones: {json.dumps(patient.evoluciones or [], ensure_ascii=False)}
Estudios solicitados: {json.dumps(patient.estudios_solicitados or [], ensure_ascii=False)}
Procedimientos: {json.dumps(patient.procedimientos or [], ensure_ascii=False)}"""

    # Construir historial de mensajes
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Contexto de la historia clínica:\n{context}"},
    ]

    for msg in history[-10:]:  # Últimos 10 mensajes
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": question})

    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages,
        temperature=0.2,
    )

    answer = response.choices[0].message.content

    # Extraer referencias de página si las hay (simplificado)
    referencias = []
    import re
    matches = re.findall(r'p[áa]gina\s+(\d+)', answer, re.IGNORECASE)
    for match in matches:
        referencias.append(ChatReference(pagina=int(match), fragmento=""))

    return ChatResponse(answer=answer, referencias=referencias)
