import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User
from app.models.patient import PatientCase
from app.models.audit import ChatMessage
from app.schemas.audit import ChatRequest, ChatResponse
from app.api.v1.deps import get_current_user, require_role
from app.models.user import AppRole
from app.services.ai.chat_service import answer_question

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat_with_historia(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(AppRole.admin, AppRole.auditor, AppRole.coordinador)),
):
    result = await db.execute(select(PatientCase).where(PatientCase.id == payload.patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
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

    response = await answer_question(patient, payload.question, history)

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
