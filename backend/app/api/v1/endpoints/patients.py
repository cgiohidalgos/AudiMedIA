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
    
    # Asegurar que riesgo_global nunca sea None para cumplir con el esquema
    riesgo_global = patient.riesgo_auditoria or "pending"
    
    # Generar recomendación general
    if riesgo_global == "alto":
        recomendacion = "Se requiere revisión inmediata por el comité de auditoría. Hallazgos críticos detectados."
    elif riesgo_global == "medio":
        recomendacion = "Requiere seguimiento y aclaraciones documentales en las próximas 48 horas."
    elif riesgo_global == "pending":
        recomendacion = "Auditoría pendiente de procesamiento."
    else:
        recomendacion = "Caso de bajo riesgo. Revisión de rutina recomendada."
    
    return AuditSummaryResponse(
        riesgo_global=riesgo_global,
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

@router.get("/{patient_id}/export/pdf")
async def export_patient_pdf(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Exporta el reporte de auditoría de un paciente en formato PDF"""
    from fastapi.responses import StreamingResponse
    from app.services.reports.pdf_generator import generate_pdf_report
    
    # Obtener datos de auditoría
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
    
    # Preparar datos
    riesgo_global = patient.riesgo_auditoria or "pending"
    
    if riesgo_global == "alto":
        recomendacion = "Se requiere revisión inmediata por el comité de auditoría. Hallazgos críticos detectados."
    elif riesgo_global == "medio":
        recomendacion = "Requiere seguimiento y aclaraciones documentales en las próximas 48 horas."
    elif riesgo_global == "pending":
        recomendacion = "Auditoría pendiente de procesamiento."
    else:
        recomendacion = "Caso de bajo riesgo. Revisión de rutina recomendada."
    
    # Agrupar hallazgos
    hallazgos_por_riesgo = {"alto": 0, "medio": 0, "bajo": 0}
    hallazgos_por_modulo = {}
    
    for finding in findings:
        hallazgos_por_riesgo[finding.riesgo] = hallazgos_por_riesgo.get(finding.riesgo, 0) + 1
        hallazgos_por_modulo[finding.modulo] = hallazgos_por_modulo.get(finding.modulo, 0) + 1
    
    audit_data = {
        "paciente": {
            "id": patient.id,
            "label": patient.label,
            "diagnostico_principal": patient.diagnostico_principal,
            "codigo_cie10": patient.codigo_cie10,
            "dias_hospitalizacion": patient.dias_hospitalizacion,
        },
        "riesgo_global": riesgo_global,
        "total_hallazgos": patient.total_hallazgos,
        "exposicion_glosas": patient.exposicion_glosas,
        "hallazgos": findings,
        "hallazgos_por_riesgo": hallazgos_por_riesgo,
        "hallazgos_por_modulo": hallazgos_por_modulo,
        "recomendacion_general": recomendacion,
    }
    
    # Generar PDF
    try:
        pdf_buffer = generate_pdf_report(audit_data)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=reporte_auditoria_{patient.label}.pdf"
            }
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar PDF: {str(e)}. Instalar dependencias con: pip install reportlab"
        )


@router.get("/{patient_id}/export/excel")
async def export_patient_excel(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Exporta el reporte de auditoría de un paciente en formato Excel"""
    from fastapi.responses import StreamingResponse
    from app.services.reports.excel_generator import generate_excel_report
    
    # Obtener datos de auditoría (mismo código que PDF)
    result = await db.execute(select(PatientCase).where(PatientCase.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    findings_result = await db.execute(
        select(AuditFinding)
        .where(AuditFinding.patient_id == patient_id)
        .order_by(AuditFinding.riesgo.desc(), AuditFinding.valor_glosa_estimado.desc())
    )
    findings = findings_result.scalars().all()
    
    riesgo_global = patient.riesgo_auditoria or "pending"
    
    if riesgo_global == "alto":
        recomendacion = "Se requiere revisión inmediata por el comité de auditoría. Hallazgos críticos detectados."
    elif riesgo_global == "medio":
        recomendacion = "Requiere seguimiento y aclaraciones documentales en las próximas 48 horas."
    elif riesgo_global == "pending":
        recomendacion = "Auditoría pendiente de procesamiento."
    else:
        recomendacion = "Caso de bajo riesgo. Revisión de rutina recomendada."
    
    hallazgos_por_riesgo = {"alto": 0, "medio": 0, "bajo": 0}
    hallazgos_por_modulo = {}
    
    for finding in findings:
        hallazgos_por_riesgo[finding.riesgo] = hallazgos_por_riesgo.get(finding.riesgo, 0) + 1
        hallazgos_por_modulo[finding.modulo] = hallazgos_por_modulo.get(finding.modulo, 0) + 1
    
    audit_data = {
        "paciente": {
            "id": patient.id,
            "label": patient.label,
            "diagnostico_principal": patient.diagnostico_principal,
            "codigo_cie10": patient.codigo_cie10,
            "dias_hospitalizacion": patient.dias_hospitalizacion,
        },
        "riesgo_global": riesgo_global,
        "total_hallazgos": patient.total_hallazgos,
        "exposicion_glosas": patient.exposicion_glosas,
        "hallazgos": findings,
        "hallazgos_por_riesgo": hallazgos_por_riesgo,
        "hallazgos_por_modulo": hallazgos_por_modulo,
        "recomendacion_general": recomendacion,
    }
    
    # Generar Excel
    try:
        excel_buffer = generate_excel_report(audit_data)
        
        return StreamingResponse(
            excel_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=reporte_auditoria_{patient.label}.xlsx"
            }
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar Excel: {str(e)}. Instalar dependencias con: pip install openpyxl"
        )


@router.get("/{patient_id}/export/html")
async def export_patient_html(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Exporta el reporte de auditoría de un paciente en formato HTML"""
    from fastapi.responses import HTMLResponse
    from app.services.reports.html_generator import generate_html_report
    
    # Obtener datos de auditoría (mismo código que PDF)
    result = await db.execute(select(PatientCase).where(PatientCase.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    findings_result = await db.execute(
        select(AuditFinding)
        .where(AuditFinding.patient_id == patient_id)
        .order_by(AuditFinding.riesgo.desc(), AuditFinding.valor_glosa_estimado.desc())
    )
    findings = findings_result.scalars().all()
    
    riesgo_global = patient.riesgo_auditoria or "pending"
    
    if riesgo_global == "alto":
        recomendacion = "Se requiere revisión inmediata por el comité de auditoría. Hallazgos críticos detectados."
    elif riesgo_global == "medio":
        recomendacion = "Requiere seguimiento y aclaraciones documentales en las próximas 48 horas."
    elif riesgo_global == "pending":
        recomendacion = "Auditoría pendiente de procesamiento."
    else:
        recomendacion = "Caso de bajo riesgo. Revisión de rutina recomendada."
    
    hallazgos_por_riesgo = {"alto": 0, "medio": 0, "bajo": 0}
    hallazgos_por_modulo = {}
    
    for finding in findings:
        hallazgos_por_riesgo[finding.riesgo] = hallazgos_por_riesgo.get(finding.riesgo, 0) + 1
        hallazgos_por_modulo[finding.modulo] = hallazgos_por_modulo.get(finding.modulo, 0) + 1
    
    audit_data = {
        "paciente": {
            "id": patient.id,
            "label": patient.label,
            "diagnostico_principal": patient.diagnostico_principal,
            "codigo_cie10": patient.codigo_cie10,
            "dias_hospitalizacion": patient.dias_hospitalizacion,
        },
        "riesgo_global": riesgo_global,
        "total_hallazgos": patient.total_hallazgos,
        "exposicion_glosas": patient.exposicion_glosas,
        "hallazgos": findings,
        "hallazgos_por_riesgo": hallazgos_por_riesgo,
        "hallazgos_por_modulo": hallazgos_por_modulo,
        "recomendacion_general": recomendacion,
    }
    
    # Generar HTML
    html_content = generate_html_report(audit_data)
    
    return HTMLResponse(content=html_content)


@router.get("/{patient_id}/download/original")
async def download_original_pdf(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Descarga el PDF original (historia clínica sin procesar) del paciente"""
    from fastapi.responses import FileResponse
    from app.models.audit import AuditSession
    import os
    
    # Obtener paciente
    result = await db.execute(select(PatientCase).where(PatientCase.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Obtener la sesión de auditoría más reciente con el PDF
    session_result = await db.execute(
        select(AuditSession)
        .where(AuditSession.patient_id == patient_id)
        .where(AuditSession.pdf_path.isnot(None))
        .order_by(AuditSession.created_at.desc())
        .limit(1)
    )
    audit_session = session_result.scalar_one_or_none()
    
    if not audit_session or not audit_session.pdf_path:
        raise HTTPException(
            status_code=404,
            detail="No se encontró el PDF original para este paciente"
        )
    
    # Verificar que el archivo existe
    if not os.path.exists(audit_session.pdf_path):
        raise HTTPException(
            status_code=404,
            detail="El archivo PDF original no existe en el servidor"
        )
    
    # Retornar el archivo
    return FileResponse(
        path=audit_session.pdf_path,
        media_type="application/pdf",
        filename=f"historia_clinica_{patient.label}.pdf",
        headers={"Content-Disposition": f"attachment; filename=historia_clinica_{patient.label}.pdf"}
    )