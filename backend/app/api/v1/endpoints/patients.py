from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.models.user import User
from app.models.patient import PatientCase
from app.models.audit import AuditFinding
from app.schemas.patient import PatientCaseRead, PatientCaseSummary, AuditSummaryResponse, PatientControlBoard
from app.schemas.audit import AuditFindingRead, AuditFindingUpdate, AuditSessionStatus
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


@router.get("/control-board", response_model=List[PatientControlBoard])
async def get_control_board(
    risk_level: str = None,
    audit_status: str = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Obtiene el cuadro de control inteligente consolidado.
    Muestra todos los pacientes con su estado de auditoría en una tabla interactiva.

    Filtros opcionales:
    - risk_level: alto, medio, bajo
    - audit_status: pending, processing, completed
    """
    from app.models.audit import AuditSession

    query = select(PatientCase).order_by(PatientCase.created_at.desc())

    if risk_level:
        query = query.where(PatientCase.riesgo_auditoria == risk_level)

    if audit_status:
        query = query.where(PatientCase.audit_status == audit_status)

    result = await db.execute(query)
    patients = result.scalars().all()

    control_board = []

    for patient in patients:
        estudios_pendientes = []
        if patient.estudios_solicitados:
            for estudio in patient.estudios_solicitados:
                if isinstance(estudio, dict):
                    tiene_reporte = estudio.get('reporte') or estudio.get('tiene_reporte')
                    if not tiene_reporte:
                        nombre_estudio = estudio.get('nombre') or estudio.get('estudio')
                        if nombre_estudio:
                            estudios_pendientes.append(nombre_estudio)

        session_result = await db.execute(
            select(AuditSession)
            .where(AuditSession.patient_id == patient.id)
            .order_by(AuditSession.fecha_ultima_auditoria.desc())
            .limit(1)
        )
        audit_session = session_result.scalar_one_or_none()
        fecha_ultima_auditoria = audit_session.fecha_ultima_auditoria if audit_session else None

        if patient.codigo_cie10 and patient.diagnostico_principal:
            diagnostico = f"{patient.codigo_cie10} - {patient.diagnostico_principal}"
        elif patient.codigo_cie10:
            diagnostico = patient.codigo_cie10
        elif patient.diagnostico_principal:
            diagnostico = patient.diagnostico_principal
        else:
            diagnostico = "Sin diagnóstico"

        control_board.append(PatientControlBoard(
            id=patient.id,
            cama=patient.cama,
            historia=patient.label,
            diagnostico=diagnostico,
            dias_hospitalizacion=patient.dias_hospitalizacion or 0,
            dias_esperados=patient.dias_esperados or "N/A",
            estudios_pendientes=estudios_pendientes,
            riesgo_glosa=patient.riesgo_auditoria or "pending",
            total_hallazgos=patient.total_hallazgos,
            exposicion_glosas=patient.exposicion_glosas,
            audit_status=patient.audit_status,
            fecha_ultima_auditoria=fecha_ultima_auditoria,
        ))

    return control_board


@router.get("/{patient_id}/session", response_model=AuditSessionStatus)
async def get_audit_session_status(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Obtiene el estado de la sesión de auditoría incremental de un paciente."""
    from app.models.audit import AuditSession

    session_result = await db.execute(
        select(AuditSession)
        .where(AuditSession.patient_id == patient_id)
        .order_by(AuditSession.fecha_ultima_auditoria.desc())
        .limit(1)
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="No se encontró sesión de auditoría para este paciente")

    total = session.total_paginas_conocidas or 0
    auditadas = session.ultima_pagina_auditada or 0
    pct = round((auditadas / total * 100), 1) if total > 0 else 0.0

    return AuditSessionStatus(
        id=session.id,
        patient_id=session.patient_id,
        ultima_pagina_auditada=auditadas,
        total_paginas_conocidas=total,
        porcentaje_completado=pct,
        fecha_ultima_auditoria=session.fecha_ultima_auditoria,
        status=session.status,
        tiene_progreso_previo=auditadas > 0,
    )


@router.post("/{patient_id}/session/reset", status_code=204)
async def reset_audit_session(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(AppRole.admin, AppRole.auditor)),
):
    """
    Reinicia la sesión de auditoría de un paciente.
    Elimina todos los hallazgos existentes y restablece el contador de páginas a 0,
    permitiendo que se procese de nuevo el PDF desde el inicio.
    """
    from app.models.audit import AuditSession, AuditFinding
    from sqlalchemy import delete, update

    # Verificar que el paciente existe
    p_result = await db.execute(select(PatientCase).where(PatientCase.id == patient_id))
    patient = p_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Eliminar todos los hallazgos del paciente
    await db.execute(delete(AuditFinding).where(AuditFinding.patient_id == patient_id))

    # Resetear la sesión de auditoría
    await db.execute(
        update(AuditSession)
        .where(AuditSession.patient_id == patient_id)
        .values(
            ultima_pagina_auditada=0,
            status="pending",
            fecha_ultima_auditoria=None,
        )
    )

    # Resetear contadores en PatientCase
    await db.execute(
        update(PatientCase)
        .where(PatientCase.id == patient_id)
        .values(
            total_hallazgos=0,
            exposicion_glosas=0.0,
            riesgo_auditoria=None,
            audit_status="pending",
        )
    )

    await db.commit()


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
            "edad": patient.edad,
            "sexo": patient.sexo,
            "diagnostico_principal": patient.diagnostico_principal,
            "codigo_cie10": patient.codigo_cie10,
            "diagnosticos_secundarios": patient.diagnosticos_secundarios,
            "fecha_ingreso": patient.fecha_ingreso,
            "dias_hospitalizacion": patient.dias_hospitalizacion,
            "dias_esperados": patient.dias_esperados,
            "medicamentos": patient.medicamentos,
            "antecedentes": patient.antecedentes,
            "estudios_solicitados": patient.estudios_solicitados,
            "procedimientos": patient.procedimientos,
            "evoluciones": patient.evoluciones,
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