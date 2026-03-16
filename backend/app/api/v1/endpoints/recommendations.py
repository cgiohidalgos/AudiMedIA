from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.models.user import User, AppRole
from app.models.patient import PatientCase
from app.models.recommendation import Recommendation
from app.api.v1.deps import get_current_user, require_role
from app.services.ai.recommendations import generate_patient_recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# ── Schemas inline ────────────────────────────────────────────────────────────

class RecommendationRead(BaseModel):
    id: str
    patient_id: str
    finding_id: Optional[str] = None
    tipo: str
    categoria: str
    prioridad: str
    mensaje: str
    detalle: Optional[str] = None
    estado: str
    notas_resolucion: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    fecha_resolucion: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RecommendationUpdate(BaseModel):
    estado: Optional[str] = None          # pendiente | implementada | descartada
    notas_resolucion: Optional[str] = None


class GenerateResponse(BaseModel):
    generadas: int
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/patients/{patient_id}", response_model=List[RecommendationRead])
async def list_recommendations(
    patient_id: str,
    estado: Optional[str] = None,
    prioridad: Optional[str] = None,
    tipo: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista las recomendaciones de un paciente con filtros opcionales."""
    q = select(Recommendation).where(Recommendation.patient_id == patient_id)
    if estado:
        q = q.where(Recommendation.estado == estado)
    if prioridad:
        q = q.where(Recommendation.prioridad == prioridad)
    if tipo:
        q = q.where(Recommendation.tipo == tipo)
    q = q.order_by(
        # alta → media → baja; pendiente primero
        Recommendation.prioridad.desc(),
        Recommendation.created_at.desc(),
    )
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/patients/{patient_id}/generate", response_model=GenerateResponse)
async def generate_recommendations(
    patient_id: str,
    overwrite: bool = False,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.auditor, AppRole.coordinador, AppRole.admin)),
):
    """
    Genera (o regenera) recomendaciones estructuradas para un paciente
    a partir de sus hallazgos de auditoría actuales.
    """
    patient = await db.get(PatientCase, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    new_recs = await generate_patient_recommendations(patient, db, overwrite=overwrite)
    return GenerateResponse(
        generadas=len(new_recs),
        message=(
            f"Se generaron {len(new_recs)} recomendaciones."
            if new_recs
            else "No hay nuevos hallazgos para generar recomendaciones."
        ),
    )


@router.patch("/{recommendation_id}", response_model=RecommendationRead)
async def update_recommendation(
    recommendation_id: str,
    payload: RecommendationUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Actualiza el estado o notas de una recomendación."""
    rec = await db.get(Recommendation, recommendation_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recomendación no encontrada")

    if payload.estado is not None:
        valid_estados = {"pendiente", "implementada", "descartada"}
        if payload.estado not in valid_estados:
            raise HTTPException(
                status_code=422,
                detail=f"Estado inválido. Valores permitidos: {valid_estados}",
            )
        rec.estado = payload.estado
        if payload.estado in ("implementada", "descartada"):
            rec.fecha_resolucion = datetime.utcnow()
        else:
            rec.fecha_resolucion = None

    if payload.notas_resolucion is not None:
        rec.notas_resolucion = payload.notas_resolucion

    await db.commit()
    await db.refresh(rec)
    return rec


@router.delete("/{recommendation_id}", status_code=204)
async def delete_recommendation(
    recommendation_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.auditor, AppRole.coordinador, AppRole.admin)),
):
    """Elimina una recomendación."""
    rec = await db.get(Recommendation, recommendation_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recomendación no encontrada")
    await db.delete(rec)
    await db.commit()


@router.get("/patients/{patient_id}/summary")
async def recommendations_summary(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Resumen de recomendaciones por estado y prioridad para un paciente."""
    result = await db.execute(
        select(Recommendation).where(Recommendation.patient_id == patient_id)
    )
    recs = list(result.scalars().all())

    by_estado: dict[str, int] = {"pendiente": 0, "implementada": 0, "descartada": 0}
    by_prioridad: dict[str, int] = {"alta": 0, "media": 0, "baja": 0}
    by_tipo: dict[str, int] = {}

    for r in recs:
        by_estado[r.estado] = by_estado.get(r.estado, 0) + 1
        by_prioridad[r.prioridad] = by_prioridad.get(r.prioridad, 0) + 1
        by_tipo[r.tipo] = by_tipo.get(r.tipo, 0) + 1

    return {
        "total": len(recs),
        "por_estado": by_estado,
        "por_prioridad": by_prioridad,
        "por_tipo": by_tipo,
    }
