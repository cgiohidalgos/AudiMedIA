import os
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, and_
from typing import List, Optional
from datetime import date
from app.db.session import get_db
from app.models.user import User
from app.models.patient import PatientCase
from app.models.audit import AuditFinding
from app.schemas.patient import PatientCaseRead, PatientCaseSummary, AuditSummaryResponse, PatientControlBoard
from app.schemas.audit import AuditFindingRead, AuditFindingUpdate, AuditSessionStatus, ResetResponse
from app.api.v1.deps import get_current_user, require_role
from app.models.user import AppRole

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/", response_model=List[PatientCaseSummary])
async def list_patients(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(PatientCase).order_by(PatientCase.created_at.desc()))
    return result.scalars().all()


@router.get("/with-findings", response_model=List[AuditSummaryResponse])
async def list_patients_with_findings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Devuelve todos los pacientes con sus hallazgos en 2 queries (sin N+1).
    Reemplaza la secuencia list() + N×audit() del frontend.
    """
    # Query 1: todos los pacientes
    p_result = await db.execute(select(PatientCase).order_by(PatientCase.created_at.desc()))
    patients = p_result.scalars().all()

    if not patients:
        return []

    patient_ids = [p.id for p in patients]

    # Query 2: todos los hallazgos de esos pacientes de una vez
    f_result = await db.execute(
        select(AuditFinding)
        .where(AuditFinding.patient_id.in_(patient_ids))
        .order_by(AuditFinding.riesgo.desc(), AuditFinding.valor_glosa_estimado.desc())
    )
    all_findings = f_result.scalars().all()

    # Agrupar hallazgos por patient_id en Python (O(n), sin queries extra)
    from collections import defaultdict
    findings_by_patient: dict = defaultdict(list)
    for f in all_findings:
        findings_by_patient[f.patient_id].append(f)

    response = []
    for patient in patients:
        findings = findings_by_patient[patient.id]
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
        hallazgos_por_modulo: dict = {}
        for f in findings:
            hallazgos_por_riesgo[f.riesgo] = hallazgos_por_riesgo.get(f.riesgo, 0) + 1
            hallazgos_por_modulo[f.modulo] = hallazgos_por_modulo.get(f.modulo, 0) + 1

        response.append(AuditSummaryResponse(
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
                "cama": patient.cama,
                "edad": patient.edad,
                "sexo": patient.sexo,
                "diagnostico_principal": patient.diagnostico_principal,
                "codigo_cie10": patient.codigo_cie10,
                "diagnosticos_secundarios": patient.diagnosticos_secundarios,
                "fecha_ingreso": patient.fecha_ingreso,
                "fecha_egreso": patient.fecha_egreso,
                "dias_hospitalizacion": patient.dias_hospitalizacion,
                "dias_esperados": patient.dias_esperados,
                "medicamentos": patient.medicamentos,
                "antecedentes": patient.antecedentes,
                "estudios_solicitados": patient.estudios_solicitados,
                "procedimientos": patient.procedimientos,
                "evoluciones": patient.evoluciones,
            },
        ))

    return response


@router.get("/control-board", response_model=List[PatientControlBoard])
async def get_control_board(
    risk_level: Optional[str] = None,
    audit_status: Optional[str] = None,
    q: Optional[str] = None,
    codigo_cie10: Optional[str] = None,
    fecha_ingreso_desde: Optional[date] = None,
    fecha_ingreso_hasta: Optional[date] = None,
    dias_min: Optional[int] = None,
    dias_max: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Obtiene el cuadro de control inteligente consolidado.

    Filtros opcionales:
    - risk_level: alto, medio, bajo
    - audit_status: pending, processing, completed
    - q: búsqueda libre (cama, historia, diagnóstico, CIE-10)
    - codigo_cie10: filtro exacto por código CIE-10
    - fecha_ingreso_desde / fecha_ingreso_hasta: rango de fecha de ingreso
    - dias_min / dias_max: rango de días de hospitalización
    """
    from app.models.audit import AuditSession

    # Subquery: fecha_ultima_auditoria más reciente por patient_id (1 sola query)
    latest_session_sq = (
        select(
            AuditSession.patient_id,
            func.max(AuditSession.fecha_ultima_auditoria).label("fecha_ultima_auditoria"),
        )
        .group_by(AuditSession.patient_id)
        .subquery()
    )

    query = (
        select(PatientCase, latest_session_sq.c.fecha_ultima_auditoria)
        .outerjoin(latest_session_sq, PatientCase.id == latest_session_sq.c.patient_id)
        .order_by(PatientCase.created_at.desc())
    )

    if risk_level:
        query = query.where(PatientCase.riesgo_auditoria == risk_level)

    if audit_status:
        query = query.where(PatientCase.audit_status == audit_status)

    if q:
        q_pattern = f"%{q}%"
        query = query.where(
            or_(
                PatientCase.cama.ilike(q_pattern),
                PatientCase.label.ilike(q_pattern),
                PatientCase.diagnostico_principal.ilike(q_pattern),
                PatientCase.codigo_cie10.ilike(q_pattern),
            )
        )

    if codigo_cie10:
        query = query.where(PatientCase.codigo_cie10.ilike(f"%{codigo_cie10}%"))

    if fecha_ingreso_desde:
        query = query.where(PatientCase.fecha_ingreso >= fecha_ingreso_desde)

    if fecha_ingreso_hasta:
        query = query.where(PatientCase.fecha_ingreso <= fecha_ingreso_hasta)

    if dias_min is not None:
        query = query.where(PatientCase.dias_hospitalizacion >= dias_min)

    if dias_max is not None:
        query = query.where(PatientCase.dias_hospitalizacion <= dias_max)

    result = await db.execute(query)
    rows = result.all()  # cada row: (PatientCase, fecha_ultima_auditoria)

    control_board = []

    for patient, fecha_ultima_auditoria in rows:
        estudios_pendientes = []
        if patient.estudios_solicitados:
            for estudio in patient.estudios_solicitados:
                if isinstance(estudio, dict):
                    tiene_reporte = estudio.get('reporte') or estudio.get('tiene_reporte')
                    if not tiene_reporte:
                        nombre_estudio = estudio.get('nombre') or estudio.get('estudio')
                        if nombre_estudio:
                            estudios_pendientes.append(nombre_estudio)

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
            codigo_cie10=patient.codigo_cie10,
            fecha_ingreso=patient.fecha_ingreso,
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


@router.post("/{patient_id}/session/reset", response_model=ResetResponse)
async def reset_audit_session(
    patient_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(AppRole.admin, AppRole.auditor)),
):
    """
    Reinicia la sesión de auditoría de un paciente.
    Si el PDF sigue en disco, relanza el análisis automáticamente (Opción B).
    Si no existe en disco, deja el estado como 'pending' para que se suba de nuevo.
    """
    from app.models.audit import AuditSession, AuditFinding
    from app.workers.pdf_worker import process_pdf_task
    from sqlalchemy import delete, update

    # Verificar que el paciente existe
    p_result = await db.execute(select(PatientCase).where(PatientCase.id == patient_id))
    patient = p_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Obtener la sesión más reciente que tenga pdf_path
    session_result = await db.execute(
        select(AuditSession)
        .where(AuditSession.patient_id == patient_id)
        .where(AuditSession.pdf_path.isnot(None))
        .order_by(AuditSession.updated_at.desc())
        .limit(1)
    )
    audit_session = session_result.scalar_one_or_none()
    pdf_exists = (
        audit_session is not None
        and audit_session.pdf_path is not None
        and os.path.exists(audit_session.pdf_path)
    )

    # Eliminar todos los hallazgos del paciente
    await db.execute(delete(AuditFinding).where(AuditFinding.patient_id == patient_id))

    # Resetear la sesión: limpiar hash (permite re-subir mismo PDF), poner contadores a 0
    new_status = "cargando" if pdf_exists else "pending"
    await db.execute(
        update(AuditSession)
        .where(AuditSession.patient_id == patient_id)
        .values(
            ultima_pagina_auditada=0,
            status=new_status,
            fecha_ultima_auditoria=None,
            pdf_hash=None,
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

    # Relanzar análisis si el archivo existe en disco
    if pdf_exists:
        background_tasks.add_task(
            process_pdf_task,
            audit_session.id,
            audit_session.pdf_path,
            patient.label,
        )
        return ResetResponse(
            relaunched=True,
            message="Re-análisis iniciado en background. Los resultados se actualizarán en breve.",
        )

    return ResetResponse(
        relaunched=False,
        message="Archivo PDF no encontrado en disco. Sube el PDF para re-analizar.",
    )


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