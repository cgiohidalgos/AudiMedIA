from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.models.user import User
from app.models.patient import PatientCase
from app.models.audit import AuditFinding
from app.schemas.patient import PatientCaseRead, PatientCaseSummary, AuditSummaryResponse
from app.schemas.audit import AuditFindingRead, AuditFindingUpdate
from app.api.v1.deps import get_current_user, require_role
from app.models.user import AppRole

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/", response_model=List[PatientCaseSummary])
async def list_patients(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(PatientCase).order_by(PatientCase.created_at.desc()))
    return result.scalars().all()


@router.get("/{patient_id}", response_model=PatientCaseRead)
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(PatientCase).where(PatientCase.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return patient


@router.get("/{patient_id}/findings", response_model=List[AuditFindingRead])
async def get_patient_findings(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AuditFinding)
        .where(AuditFinding.patient_id == patient_id)
        .order_by(AuditFinding.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{patient_id}/audit", response_model=AuditSummaryResponse)
async def get_patient_audit_summary(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Obtiene el resumen completo de auditoría de un paciente"""
    # Obtener paciente
    result = await db.execute(select(PatientCase).where(PatientCase.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Obtener hallazgos
    findings_result = await db.execute(
        select(AuditFinding)
        .where(AuditFinding.patient_id == patient_id)
        .order_by(AuditFinding.riesgo.desc(), AuditFinding.valor_glosa_estimado.desc())
    )
    findings = findings_result.scalars().all()
    
    # Agrupar hallazgos por riesgo y módulo
    hallazgos_por_riesgo = {"alto": 0, "medio": 0, "bajo": 0}
    hallazgos_por_modulo = {}
    
    for finding in findings:
        hallazgos_por_riesgo[finding.riesgo] = hallazgos_por_riesgo.get(finding.riesgo, 0) + 1
        hallazgos_por_modulo[finding.modulo] = hallazgos_por_modulo.get(finding.modulo, 0) + 1
    
    # Generar recomendación general
    if patient.riesgo_auditoria == "alto":
        recomendacion = "Se requiere revisión inmediata por el comité de auditoría. Hallazgos críticos detectados."
    elif patient.riesgo_auditoria == "medio":
        recomendacion = "Requiere seguimiento y aclaraciones documentales en las próximas 48 horas."
    else:
        recomendacion = "Caso de bajo riesgo. Revisión de rutina recomendada."
    
    return AuditSummaryResponse(
        riesgo_global=patient.riesgo_auditoria,
        total_hallazgos=patient.total_hallazgos,
        exposicion_glosas=patient.exposicion_glosas,
        hallazgos_por_riesgo=hallazgos_por_riesgo,
        hallazgos_por_modulo=hallazgos_por_modulo,
        hallazgos=findings,
        recomendacion_general=recomendacion,
        paciente={
            "id": patient.id,
            "label": patient.label,
            "diagnostico_principal": patient.diagnostico_principal,
            "codigo_cie10": patient.codigo_cie10,
            "dias_hospitalizacion": patient.dias_hospitalizacion,
        }
    )


@router.patch("/{patient_id}/findings/{finding_id}", response_model=AuditFindingRead)
async def update_finding(
    patient_id: str,
    finding_id: str,
    payload: AuditFindingUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.admin, AppRole.auditor)),
):
    """Actualiza el estado de un hallazgo de auditoría"""
    from datetime import datetime, timezone
    
    result = await db.execute(
        select(AuditFinding).where(
            AuditFinding.id == finding_id,
            AuditFinding.patient_id == patient_id,
        )
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")

    # Actualizar campos
    if payload.estado:
        finding.estado = payload.estado
        finding.resuelto = (payload.estado == "resuelto")  # Mantener compatibilidad
        if payload.estado == "resuelto":
            finding.fecha_resolucion = datetime.now(timezone.utc)
    
    if payload.notas_resolucion:
        finding.notas_resolucion = payload.notas_resolucion
    
    finding.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(finding)
    return finding
