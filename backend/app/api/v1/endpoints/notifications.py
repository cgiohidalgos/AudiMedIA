from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.models.user import User, AppRole
from app.models.notification import Notification
from app.api.v1.deps import get_current_user, require_role
from app.services.notifications import generate_pending_summary, notify_medical_team

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ── Schemas inline ────────────────────────────────────────────────────────────

class NotificationRead(BaseModel):
    id: str
    user_id: str
    patient_id: Optional[str] = None
    titulo: str
    mensaje: str
    tipo: str
    leida: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationCount(BaseModel):
    total: int
    no_leidas: int


class NotifyTeamResponse(BaseModel):
    notificaciones_creadas: int
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[NotificationRead])
async def list_notifications(
    leida: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista las notificaciones del usuario actual (máx. 50, más recientes primero)."""
    q = select(Notification).where(Notification.user_id == current_user.id)
    if leida is not None:
        q = q.where(Notification.leida == leida)
    q = q.order_by(Notification.created_at.desc()).limit(50)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/count", response_model=NotificationCount)
async def count_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el total y el número de notificaciones no leídas del usuario actual."""
    total_res = await db.execute(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == current_user.id
        )
    )
    unread_res = await db.execute(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == current_user.id,
            Notification.leida == False,  # noqa: E712
        )
    )
    return {
        "total": total_res.scalar_one(),
        "no_leidas": unread_res.scalar_one(),
    }


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_as_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marca una notificación como leída."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    notif.leida = True
    await db.commit()
    await db.refresh(notif)
    return notif


@router.post("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marca todas las notificaciones no leídas del usuario como leídas."""
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.leida == False,  # noqa: E712
        )
        .values(leida=True)
    )
    await db.commit()
    return {"message": "Todas las notificaciones marcadas como leídas"}


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina una notificación del usuario actual."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    await db.delete(notif)
    await db.commit()
    return Response(status_code=204)


@router.get("/patients/{patient_id}/summary")
async def pending_summary(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Devuelve un resumen de texto plano de los pendientes para descarga."""
    text = await generate_pending_summary(patient_id, db)
    return PlainTextResponse(content=text, media_type="text/plain; charset=utf-8")


@router.post("/patients/{patient_id}/notify-team", response_model=NotifyTeamResponse)
async def notify_team(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(AppRole.admin, AppRole.coordinador, AppRole.auditor)
    ),
):
    """Crea notificaciones en-app para el equipo médico tratante y coordinadores."""
    count = await notify_medical_team(patient_id, current_user.id, db)
    if count == 0:
        return {
            "notificaciones_creadas": 0,
            "message": "Sin hallazgos activos o sin destinatarios disponibles.",
        }
    return {
        "notificaciones_creadas": count,
        "message": f"Se notificó a {count} miembro{'s' if count != 1 else ''} del equipo.",
    }
