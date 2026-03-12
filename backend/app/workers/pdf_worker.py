"""
Worker de procesamiento de PDFs.
Pipeline: validar → extraer texto → OCR → anonimizar → extraer variables → auditar → guardar.
"""
import asyncio
import uuid
import logging
from datetime import datetime, date
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.audit import AuditSession, AuditFinding, DocumentStatus
from app.models.patient import PatientCase, RiskLevel
from app.services.document.pdf_extractor import extract_text_from_pdf, get_total_pages
from app.services.document.anonymizer import anonymize_pages
from app.services.ai.extractor import extract_clinical_variables
from app.services.ai.audit_modules import run_all_modules, calculate_risk, generate_audit_summary, Finding

logger = logging.getLogger(__name__)


async def _update_status(session_id: str, status: DocumentStatus):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AuditSession).where(AuditSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.status = status.value
            await db.commit()


def _parse_date(date_str: str | None) -> date | None:
    """Convierte string de fecha a objeto date. Retorna None si no es válido."""
    if not date_str:
        return None
    try:
        # Intentar varios formatos
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
            try:
                return datetime.strptime(str(date_str), fmt).date()
            except ValueError:
                continue
        logger.warning(f"⚠️ No se pudo parsear fecha: {date_str}")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Error parseando fecha '{date_str}': {e}")
        return None


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
        
        # Validar que no hubo error en la extracción
        if "error" in clinical_data:
            logger.error(f"❌ Error en extracción de variables: {clinical_data['error']}")
            raise Exception(f"Error extrayendo variables: {clinical_data['error']}")
        
        logger.info(f"✅ Variables extraídas correctamente para {label}")

        # 4. GUARDAR PACIENTE Y EJECUTAR MÓDULOS DE AUDITORÍA
        async with AsyncSessionLocal() as db:
            # Obtener sesión
            result = await db.execute(
                select(AuditSession).where(AuditSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if not session:
                logger.error(f"❌ Sesión {session_id} no encontrada")
                return

            # Ejecutar módulos de auditoría
            findings: list[Finding] = run_all_modules(clinical_data)
            risk_level = calculate_risk(findings)
            summary = generate_audit_summary(findings, clinical_data)
            
            logger.info(f"📊 Auditoría: {len(findings)} hallazgos, riesgo {risk_level.value}")

            # Convertir fecha_ingreso de string a date
            fecha_ingreso_date = _parse_date(clinical_data.get("fecha_ingreso"))
            logger.info(f"📅 Fecha ingreso convertida: {clinical_data.get('fecha_ingreso')} → {fecha_ingreso_date}")

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
                fecha_ingreso=fecha_ingreso_date,
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
            from datetime import timezone
            session.fecha_ultima_auditoria = datetime.now(timezone.utc)

            await db.commit()
            
            logger.info(f"✅ Procesamiento completado para {label} (paciente {patient.id})")
            logger.info(f"📄 {total_pages} páginas procesadas, {len(findings)} hallazgos registrados")

    except Exception as e:
        logger.error(f"❌ ERROR procesando PDF (session={session_id}): {type(e).__name__}: {str(e)}")
        logger.exception("Traceback completo:")
        await _update_status(session_id, DocumentStatus.error)  # type: ignore
