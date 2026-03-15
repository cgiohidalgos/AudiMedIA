import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.db.session import get_db
from app.models.user import User
from app.models.patient import PatientCase
from app.models.audit import ChatMessage, AuditSession, DocumentChunk
from app.schemas.audit import ChatRequest, ChatResponse, ChatMultiRequest
from app.api.v1.deps import get_current_user, require_role
from app.models.user import AppRole
from app.services.ai.chat_service import answer_question, answer_question_multi
from app.services.ai.rag_service import answer_with_rag

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat_with_historia(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(AppRole.admin, AppRole.auditor, AppRole.coordinador)),
):
    logger.info("[chat] pregunta para paciente=%s user=%s", payload.patient_id, current_user.email)
    logger.debug("[chat] pregunta: %s", payload.question[:120])
    result = await db.execute(select(PatientCase).where(PatientCase.id == payload.patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        logger.warning("[chat] paciente no encontrado: %s", payload.patient_id)
        raise HTTPException(status_code=404, detail="Historia clínica no encontrada")

    # Obtener historial ANTES de agregar el mensaje actual
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.patient_id == payload.patient_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(20)
    )
    history = history_result.scalars().all()

    # Ahora sí guardar el mensaje del usuario
    user_msg = ChatMessage(
        id=str(uuid.uuid4()),
        patient_id=payload.patient_id,
        user_id=current_user.id,
        role="user",
        content=payload.question,
    )
    db.add(user_msg)
    await db.flush()

    try:
        response = await answer_question(patient, payload.question, history)
        logger.info("[chat] respuesta generada (%d refs)", len(response.referencias))
    except Exception as exc:
        logger.exception("[chat] error al generar respuesta para paciente=%s", payload.patient_id)
        err = str(exc)
        exc_name = type(exc).__name__
        if "AuthenticationError" in exc_name or "invalid_api_key" in err or "Incorrect API key" in err:
            raise HTTPException(status_code=503, detail="API key de OpenAI inválida o expirada. Actualiza OPENAI_API_KEY en backend/.env")
        if "RateLimitError" in exc_name or "insufficient_quota" in err or "exceeded your current quota" in err:
            raise HTTPException(status_code=402, detail="Cuenta de OpenAI sin créditos. Recarga saldo en platform.openai.com/settings/billing")
        raise HTTPException(status_code=500, detail=f"Error al generar respuesta: {err}")

    assistant_msg = ChatMessage(
        id=str(uuid.uuid4()),
        patient_id=payload.patient_id,
        user_id=current_user.id,
        role="assistant",
        content=response.answer,
        referencias=[r.model_dump() for r in response.referencias],
    )
    db.add(assistant_msg)
    await db.commit()

    return response


@router.get("/history/{patient_id}")
async def get_chat_history(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.patient_id == patient_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content, "referencias": m.referencias} for m in messages]


@router.post("/multi-history", response_model=ChatResponse)
async def chat_multi_history(
    payload: ChatMultiRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(AppRole.admin, AppRole.auditor, AppRole.coordinador)),
):
    """Chat que cruza múltiples historias clínicas simultáneamente."""
    logger.info("[chat/multi] pregunta para %d pacientes user=%s", len(payload.patient_ids or []), current_user.email)
    if not payload.patient_ids:
        raise HTTPException(status_code=400, detail="Se requiere al menos un paciente")

    result = await db.execute(
        select(PatientCase).where(PatientCase.id.in_(payload.patient_ids))
    )
    patients = result.scalars().all()

    if not patients:
        logger.warning("[chat/multi] ningún paciente encontrado para ids: %s", payload.patient_ids)
        raise HTTPException(status_code=404, detail="No se encontraron pacientes")

    try:
        response = await answer_question_multi(list(patients), payload.question)
        logger.info("[chat/multi] respuesta generada para %d pacientes", len(patients))
        return response
    except Exception:
        logger.exception("[chat/multi] error generando respuesta multi")
        raise


# ─── RAG con Cohere Command R ─────────────────────────────────────────────────

class RagChatRequest(BaseModel):
    session_id: str
    question: str
    history: list[dict] = []  # [{"role": "user"|"assistant", "content": str}]


class RagReferenceOut(BaseModel):
    chunk_index: int
    page_number: int
    text_snippet: str
    relevance_score: float


class RagChatResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    answer: str
    references: list[RagReferenceOut]
    model_used: str
    chunks_total: int
    chunks_used: int


@router.post("/rag", response_model=RagChatResponse)
async def rag_chat(
    payload: RagChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(AppRole.admin, AppRole.auditor, AppRole.coordinador)),
):
    """
    Chat RAG sobre el PDF usando Cohere Command R.
    Recupera los chunks más relevantes con Rerank y genera respuesta fundamentada.
    """
    logger.info("[rag] pregunta para sesión=%s user=%s", payload.session_id, current_user.email)

    # Verificar que la sesión existe
    session_q = await db.execute(
        select(AuditSession).where(AuditSession.id == payload.session_id)
    )
    session = session_q.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # Cargar todos los chunks de la sesión
    chunks_q = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.session_id == payload.session_id)
        .order_by(DocumentChunk.chunk_index)
    )
    db_chunks = chunks_q.scalars().all()

    if not db_chunks:
        raise HTTPException(
            status_code=400,
            detail="No hay texto extraído en esta sesión. Ejecuta primero la Etapa 2 (Extraer texto).",
        )

    # Convertir a formato esperado por rag_service
    chunks = [
        {
            "chunk_index": c.chunk_index,
            "page_number": c.page_number,
            "text": c.text,
        }
        for c in db_chunks
    ]

    logger.info("[rag] %d chunks disponibles para sesión=%s", len(chunks), payload.session_id)

    try:
        import asyncio
        # rag_service usa cliente síncrono de Cohere → ejecutar en executor
        loop = asyncio.get_event_loop()
        rag_result = await loop.run_in_executor(
            None,
            answer_with_rag,
            payload.question,
            chunks,
            payload.history,
        )
    except RuntimeError as exc:
        if "COHERE_API_KEY" in str(exc):
            raise HTTPException(status_code=503, detail=str(exc))
        raise HTTPException(status_code=500, detail=f"Error RAG: {exc}")
    except Exception as exc:
        logger.exception("[rag] error en answer_with_rag")
        err = str(exc)
        if "unauthorized" in err.lower() or "invalid api key" in err.lower():
            raise HTTPException(status_code=503, detail="COHERE_API_KEY inválida. Verifica backend/.env")
        raise HTTPException(status_code=500, detail=f"Error al generar respuesta: {err}")

    return RagChatResponse(
        answer=rag_result.answer,
        references=[
            RagReferenceOut(
                chunk_index=r.chunk_index,
                page_number=r.page_number,
                text_snippet=r.text_snippet,
                relevance_score=r.relevance_score,
            )
            for r in rag_result.references
        ],
        model_used=rag_result.model_used,
        chunks_total=len(chunks),
        chunks_used=len(rag_result.references),
    )
