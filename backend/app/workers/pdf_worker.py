"""
Worker de procesamiento de PDFs.
Pipeline: validar → extraer texto → OCR → anonimizar → extraer variables → auditar → guardar.
"""
import asyncio
import uuid
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.audit import AuditSession, AuditFinding, DocumentStatus
from app.models.patient import PatientCase, RiskLevel
from app.services.document.pdf_extractor import extract_text_from_pdf, get_total_pages
from app.services.document.anonymizer import anonymize_pages
from app.services.ai.extractor import extract_clinical_variables
from app.services.ai.audit_modules import run_all_modules, calculate_risk, generate_audit_summary, Finding


async def _update_status(session_id: str, status: DocumentStatus):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AuditSession).where(AuditSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.status = status.value
            await db.commit()


async def process_pdf_task(session_id: str, pdf_path: str, label: str):
    """Pipeline completo de procesamiento de una historia clínica."""
    try:
        # 1. EXTRAER TEXTO
        await _update_status(session_id, DocumentStatus.extrayendo)  # type: ignore
        pages = extract_text_from_pdf(pdf_path)
        total_pages = get_total_pages(pdf_path)
        full_text = "\n\n".join(f"[Página {p.page_number}]\n{p.text}" for p in pages)

        # 2. ANONIMIZAR
        await _update_status(session_id, DocumentStatus.anonimizando)
        pages = anonymize_pages(pages)
        anon_text = "\n\n".join(f"[Página {p.page_number}]\n{p.text}" for p in pages)

        # 3. EXTRAER VARIABLES CLÍNICAS CON IA
        await _update_status(session_id, DocumentStatus.analizando)
        clinical_data = await extract_clinical_variables(anon_text)

        # 4. GUARDAR PACIENTE Y EJECUTAR MÓDULOS DE AUDITORÍA
        async with AsyncSessionLocal() as db:
            # Obtener sesión
            result = await db.execute(
                select(AuditSession).where(AuditSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if not session:
                return

            # Ejecutar módulos de auditoría
            findings: list[Finding] = run_all_modules(clinical_data)
            risk_level = calculate_risk(findings)
            summary = generate_audit_summary(findings, clinical_data)

            # Crear registro del paciente con campos de auditoría
            patient = PatientCase(
                id=str(uuid.uuid4()),
                label=label,
                cama=clinical_data.get("cama"),
                edad=clinical_data.get("edad"),
                sexo=clinical_data.get("sexo"),
                diagnostico_principal=clinical_data.get("diagnostico_principal"),
                codigo_cie10=clinical_data.get("codigo_cie10"),
                diagnosticos_secundarios=clinical_data.get("diagnosticos_secundarios", []),
                fecha_ingreso=clinical_data.get("fecha_ingreso"),
                dias_hospitalizacion=clinical_data.get("dias_hospitalizacion"),
                dias_esperados=clinical_data.get("dias_esperados"),
                riesgo=risk_level.value,
                medicamentos=clinical_data.get("medicamentos", []),
                antecedentes=clinical_data.get("antecedentes", {}),
                estudios_solicitados=clinical_data.get("estudios_solicitados", []),
                procedimientos=clinical_data.get("procedimientos", []),
                evoluciones=clinical_data.get("evoluciones", []),
                # Campos de auditoría
                riesgo_auditoria=summary["riesgo_global"],
                total_hallazgos=summary["total_hallazgos"],
                exposicion_glosas=summary["exposicion_glosas_cop"],
                audit_status="completed",
            )
            db.add(patient)
            await db.flush()

            # Guardar hallazgos con todos los campos
            for f in findings:
                db.add(AuditFinding(
                    id=str(uuid.uuid4()),
                    patient_id=patient.id,
                    modulo=f.modulo.value,
                    categoria=f.categoria,
                    descripcion=f.descripcion,
                    riesgo=f.riesgo.value,
                    recomendacion=f.recomendacion,
                    normativa_aplicable=f.normativa_aplicable,
                    valor_glosa_estimado=f.valor_glosa_estimado,
                    pagina=f.pagina,
                    estado="activo",
                    resuelto=False,
                ))

            # Actualizar sesión
            session.patient_id = patient.id
            session.total_paginas_conocidas = total_pages
            session.ultima_pagina_auditada = total_pages
            session.status = DocumentStatus.listo.value
            from datetime import datetime, timezone
            session.fecha_ultima_auditoria = datetime.now(timezone.utc)

            await db.commit()

    except Exception as e:
        await _update_status(session_id, DocumentStatus.error)  # type: ignore
        print(f"[ERROR] pdf_worker session={session_id}: {e}")
