import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User
from app.models.patient import PatientCase
from app.models.audit import ChatMessage
from app.schemas.audit import ChatRequest, ChatResponse, ChatMultiRequest
from app.api.v1.deps import get_current_user, require_role
from app.models.user import AppRole
from app.services.ai.chat_service import answer_question, answer_question_multi

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
    except Exception:
        logger.exception("[chat] error al generar respuesta para paciente=%s", payload.patient_id)
        raise

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
