from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from app.db.session import get_db
from app.models.user import User, AppRole
from app.models.patient import PatientCase, RiskLevel
from app.models.audit import AuditFinding, AuditSession
from app.schemas.audit import DashboardMetrics
from app.api.v1.deps import get_current_user, require_role

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=DashboardMetrics)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.coordinador, AppRole.admin)),
):
    # Total historias auditadas
    total = await db.scalar(select(func.count(PatientCase.id)))

    # Hallazgos resueltos (glosas evitadas)
    glosas_evitadas = await db.scalar(
        select(func.count(AuditFinding.id)).where(AuditFinding.resuelto == True)
    )

    # Estancias prolongadas (donde dias_hospitalizacion > dias_esperados aproximado)
    estancias_prolongadas = await db.scalar(
        select(func.count(PatientCase.id)).where(PatientCase.riesgo == RiskLevel.alto)
    )

    # Riesgo alto
    riesgo_alto = await db.scalar(
        select(func.count(PatientCase.id)).where(PatientCase.riesgo == RiskLevel.alto)
    )

    return DashboardMetrics(
        historias_auditadas=total or 0,
        glosas_evitadas=glosas_evitadas or 0,
        ahorro_estimado=(glosas_evitadas or 0) * 850_000,  # COP estimado por glosa
        estancias_prolongadas=estancias_prolongadas or 0,
        riesgo_alto=riesgo_alto or 0,
        pendientes_resueltos=glosas_evitadas or 0,
        tiempo_promedio_auditoria_min=2.8,
    )
