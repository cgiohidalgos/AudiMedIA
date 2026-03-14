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
    """Pipeline completo de procesamiento de una historia clínica.

    Este método ahora soporta auditoría incremental: si la sesión ya está ligada
    a un paciente, sólo se vuelven a procesar las páginas que aún no se habían
    auditado y los hallazgos se agregan al registro existente.
    """
    try:
        # 1. EXTRAER TEXTO
        logger.info(f"📄 [WORKER] Paso 1: Extrayendo texto de PDF...")
        await _update_status(session_id, DocumentStatus.extrayendo)  # type: ignore
        pages = extract_text_from_pdf(pdf_path)
        total_pages = get_total_pages(pdf_path)
        logger.info(f"📄 [WORKER] Extraídas {len(pages)} páginas de texto. Total páginas conocidas: {total_pages}")

        # extraer número de historia (antes de anonimizar) para identificación
        def _extract_history_number(page_list):
            import re
            regex = re.compile(r"\b(?:HC|H\.C\.|Historia\s+[Cc]l[íi]nica)\s*[Nn]?[oO°]?\.?\s*(\d{4,12})\b")
            for p in page_list:
                m = regex.search(p.text)
                if m:
                    return m.group(1)
            return None
        history_num = _extract_history_number(pages)

        # 2. ANONIMIZAR (hace falta para extracción IA)
        logger.info(f"🔒 [WORKER] Paso 2: Anonimizando contenido...")
        await _update_status(session_id, DocumentStatus.anonimizando)
        pages_anon = anonymize_pages(pages)
        logger.info(f"🔒 [WORKER] Anonimización completada para {len(pages_anon)} páginas")

        # función auxiliar para concatenar texto de páginas
        def _pages_to_text(p_list):
            return "\n\n".join(f"[Página {p.page_number}]\n{p.text}" for p in p_list)

        # 3. == INCREMENTAL: determinar páginas nuevas ==
        start_page = 0
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AuditSession).where(AuditSession.id == session_id)
            )
            session_row = result.scalar_one_or_none()
            if not session_row:
                logger.error(f"❌ Sesión {session_id} no encontrada")
                return

            # si hay paciente vinculado y ya procesó todas las páginas
            if session_row.patient_id and (session_row.ultima_pagina_auditada or 0) >= total_pages:
                session_row.status = DocumentStatus.listo.value
                session_row.total_paginas_conocidas = total_pages
                await db.commit()
                logger.info(f"📄 Sesión {session_id} no requiere procesamiento adicional")
                return

            # leer el valor mientras la sesión está abierta
            start_page = session_row.ultima_pagina_auditada or 0

        # decidir rango a procesar
        pages_to_analyze = extract_text_from_pdf(pdf_path, start_page)
        if not pages_to_analyze:
            # nada nuevo — actualizar estado con una sesión fresca
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(AuditSession).where(AuditSession.id == session_id)
                )
                session_row2 = result.scalar_one_or_none()
                if session_row2:
                    session_row2.status = DocumentStatus.listo.value
                    session_row2.total_paginas_conocidas = total_pages
                    await db.commit()
            return

        anon_to_analyze = anonymize_pages(pages_to_analyze)
        text_new = _pages_to_text(anon_to_analyze)

        # 4. EXTRAER VARIABLES (sobre TODO el texto para actualizar metadata)
        logger.info(f"🤖 [WORKER] Paso 4: Extracción de variables con IA...")
        await _update_status(session_id, DocumentStatus.analizando)
        full_anon_text = _pages_to_text(pages_anon)
        logger.info(f"🤖 [WORKER] Texto preparado para IA: {len(full_anon_text)} caracteres")
        clinical_data = await extract_clinical_variables(full_anon_text)
        if "error" in clinical_data:
            logger.error(f"❌ [WORKER] Error en extracción de variables: {clinical_data['error']}")
            raise Exception(f"Error extrayendo variables: {clinical_data['error']}")
        logger.info(f"✅ [WORKER] Variables extraídas correctamente para {label}")
        logger.debug(f"🔍 [WORKER] Variables extraídas: {list(clinical_data.keys())}")

        # Ejecutar módulos sobre el conjunto completo de datos (filtraremos duplicados luego)
        findings: list[Finding] = run_all_modules(clinical_data)
        risk_level = calculate_risk(findings)
        summary = generate_audit_summary(findings, clinical_data)
        logger.info(f"📊 Auditoría incremental: {len(findings)} hallazgos nuevos, riesgo {risk_level.value}")

        fecha_ingreso_date = _parse_date(clinical_data.get("fecha_ingreso"))
        logger.info(f"📅 Fecha ingreso convertida: {clinical_data.get('fecha_ingreso')} → {fecha_ingreso_date}")

        # guardar o actualizar paciente
        async with AsyncSessionLocal() as db:
            # reconectar sesión en este contexto
            result = await db.execute(
                select(AuditSession).where(AuditSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            patient = None
            if session and session.patient_id:
                patient = await db.get(PatientCase, session.patient_id)

            # si no hay paciente ligado, intentar buscar por historia+cama
            if not patient and history_num:
                q = select(PatientCase).where(PatientCase.historia_numero == history_num)
                if clinical_data.get("cama"):
                    q = q.where(PatientCase.cama == clinical_data.get("cama"))
                res = await db.execute(q)
                patient = res.scalar_one_or_none()

            if not patient:
                # crear nuevo paciente (totales se acumularán tras deduplicación)
                patient = PatientCase(
                    id=str(uuid.uuid4()),
                    historia_numero=history_num,
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
                    riesgo_auditoria=summary["riesgo_global"],
                    total_hallazgos=0,
                    exposicion_glosas=0.0,
                    audit_status="pending",
                )
                db.add(patient)
                await db.flush()
            else:
                # actualizar algunos campos en el paciente existente
                patient.historia_numero = history_num or patient.historia_numero
                patient.cama = clinical_data.get("cama") or patient.cama
                patient.edad = clinical_data.get("edad") or patient.edad
                patient.sexo = clinical_data.get("sexo") or patient.sexo
                patient.diagnostico_principal = clinical_data.get("diagnostico_principal") or patient.diagnostico_principal
                patient.codigo_cie10 = clinical_data.get("codigo_cie10") or patient.codigo_cie10
                patient.diagnosticos_secundarios = clinical_data.get("diagnosticos_secundarios", patient.diagnosticos_secundarios)
                patient.fecha_ingreso = fecha_ingreso_date or patient.fecha_ingreso
                patient.dias_hospitalizacion = clinical_data.get("dias_hospitalizacion") or patient.dias_hospitalizacion
                patient.dias_esperados = clinical_data.get("dias_esperados") or patient.dias_esperados
                patient.riesgo = risk_level.value
                patient.medicamentos = clinical_data.get("medicamentos", patient.medicamentos)
                patient.antecedentes = clinical_data.get("antecedentes", patient.antecedentes)
                patient.estudios_solicitados = clinical_data.get("estudios_solicitados", patient.estudios_solicitados)
                patient.procedimientos = clinical_data.get("procedimientos", patient.procedimientos)
                patient.evoluciones = clinical_data.get("evoluciones", patient.evoluciones)
                # Los totales (total_hallazgos, exposicion_glosas) se acumulan tras la deduplicación

            # registrar hallazgos nuevos y evitar duplicados
            # marcar todos los hallazgos previos como heredados antes de procesar
            existing_q = await db.execute(
                select(AuditFinding).where(AuditFinding.patient_id == patient.id)
            )
            existing_f = existing_q.scalars().all()
            seen = {(f.modulo, f.pagina, f.descripcion) for f in existing_f}
            for old in existing_f:
                old.heredado = True
            # además cerrar automáticamente los que no aparecen en el texto nuevo
            closed = []
            for old in existing_f:
                if old.resuelto:
                    continue
                # si la descripción no se encuentra en el fragmento recién auditado
                if text_new and old.descripcion not in text_new:
                    old.resuelto = True
                    old.estado = "resuelto"
                    old.fecha_resolucion = datetime.now()
                    old.notas_resolucion = "Resuelto automáticamente en auditoría incremental"
                    closed.append(old)

            new_findings: list[Finding] = []
            for f in findings:
                key = (f.modulo.value, f.pagina, f.descripcion)
                if key in seen:
                    continue
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
                    heredado=False,
                ))
                seen.add(key)
                new_findings.append(f)

            # recompute resumen solo para hallazgos nuevos (para sumar totales)
            new_summary = generate_audit_summary(new_findings, clinical_data) if new_findings else {"riesgo_global": summary["riesgo_global"], "total_hallazgos": 0, "exposicion_glosas_cop": 0.0}

            # actualizar paciente acumulativos (solo hallazgos NUEVOS, evita doble-conteo)
            patient.riesgo_auditoria = summary["riesgo_global"]
            patient.total_hallazgos = (patient.total_hallazgos or 0) + new_summary["total_hallazgos"]
            patient.exposicion_glosas = (patient.exposicion_glosas or 0.0) + new_summary["exposicion_glosas_cop"]
            patient.audit_status = "completed"

            # actualizar sesión
            session.patient_id = patient.id
            session.historia_numero = history_num
            session.numero_cama = clinical_data.get("cama")
            session.total_paginas_conocidas = total_pages
            session.ultima_pagina_auditada = total_pages
            session.status = DocumentStatus.listo.value
            from datetime import timezone
            session.fecha_ultima_auditoria = datetime.now(timezone.utc)

            await db.commit()
            logger.info(f"✅ Procesamiento completado para {label} (paciente {patient.id})")
            logger.info(f"📄 {total_pages} páginas reconocidas, {len(new_findings)} hallazgos nuevos")

    except Exception as e:
        logger.error(f"❌ ERROR procesando PDF (session={session_id}): {type(e).__name__}: {str(e)}")
        logger.exception("Traceback completo:")
        await _update_status(session_id, DocumentStatus.error)  # type: ignore
