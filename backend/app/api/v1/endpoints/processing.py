"""
Endpoints de procesamiento en etapas independientes:
  POST /processing/{session_id}/extract  → Etapa 2: extrae texto y guarda chunks (sin IA)
  POST /processing/{session_id}/process  → Etapa 3: analiza chunks con IA, crea paciente + hallazgos
  GET  /processing/{session_id}/chunks   → Lista de chunks de una sesión
"""
import logging
import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from pydantic import BaseModel

from app.db.session import get_db, AsyncSessionLocal
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.models.audit import AuditSession, DocumentStatus, DocumentChunk, AuditFinding
from app.models.patient import PatientCase, RiskLevel
from app.schemas.audit import UploadResponse
from app.services.document.pdf_extractor import extract_text_from_pdf, get_total_pages
from app.services.document.anonymizer import anonymize_pages
from app.services.document.chunker import split_pages_into_chunks
from app.services.ai.extractor import extract_clinical_variables
from app.services.ai.audit_modules import run_all_modules, calculate_risk, generate_audit_summary, Finding

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/processing", tags=["processing"])


class DocumentChunkRead(BaseModel):
    id: str
    session_id: str
    page_number: int
    chunk_index: int
    text: str
    word_count: int
    is_ocr: bool

    model_config = {"from_attributes": True}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_date(date_str) -> date | None:
    if not date_str:
        return None
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
        try:
            return datetime.strptime(str(date_str), fmt).date()
        except ValueError:
            continue
    return None


# ─── Etapa 2: Extracción de texto → chunks ───────────────────────────────────

@router.post("/{session_id}/extract", response_model=UploadResponse)
async def extract_text(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Etapa 2: Extrae el texto del PDF, lo divide en chunks (300-400 palabras)
    y los guarda en BD. No usa IA.
    """
    result = await db.execute(select(AuditSession).where(AuditSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if session.status not in (DocumentStatus.subido.value, DocumentStatus.error.value):
        raise HTTPException(
            status_code=400,
            detail=f"Estado actual '{session.status}'. Solo se puede extraer desde 'subido'.",
        )

    session.status = DocumentStatus.extrayendo.value
    await db.commit()

    background_tasks.add_task(_do_extract, session_id)

    return UploadResponse(
        session_id=session_id,
        status=DocumentStatus.extrayendo.value,
        message="Extracción de texto iniciada. Espere...",
    )


async def _do_extract(session_id: str):
    """Worker: extrae texto del PDF y guarda chunks en BD (sin IA)."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(AuditSession).where(AuditSession.id == session_id))
            session = result.scalar_one_or_none()
            if not session or not session.pdf_path:
                logger.error(f"❌ [EXTRACT] Sesión {session_id} no encontrada o sin pdf_path")
                return

            # Extracción de texto + OCR fallback (operación bloqueante → executor)
            import asyncio
            loop = asyncio.get_event_loop()
            pages = await loop.run_in_executor(None, extract_text_from_pdf, session.pdf_path)
            total_pages = await loop.run_in_executor(None, get_total_pages, session.pdf_path)

            # Anonimizar (reemplaza nombres/datos personales antes de guardar)
            pages_anon = anonymize_pages(pages)

            # Dividir en chunks de ~400 palabras
            chunks = split_pages_into_chunks(pages_anon, max_words=400)

            # Eliminar chunks anteriores si es re-extracción
            await db.execute(delete(DocumentChunk).where(DocumentChunk.session_id == session_id))

            # Guardar chunks en BD
            for chunk in chunks:
                db.add(DocumentChunk(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    word_count=chunk.word_count,
                    is_ocr=chunk.is_ocr,
                ))

            session.status = DocumentStatus.extraido.value
            session.total_paginas_conocidas = total_pages
            await db.commit()

            logger.info(
                f"✅ [EXTRACT] Sesión {session_id}: {len(chunks)} chunks "
                f"({total_pages} páginas) guardados correctamente"
            )

    except Exception as exc:
        logger.error(f"❌ [EXTRACT] Error en sesión {session_id}: {exc}", exc_info=True)
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(AuditSession).where(AuditSession.id == session_id))
            s = result.scalar_one_or_none()
            if s:
                s.status = DocumentStatus.error.value
                await db.commit()


# ─── Etapa 3: Análisis con IA ────────────────────────────────────────────────

@router.post("/{session_id}/process", response_model=UploadResponse)
async def process_with_ai(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Etapa 3: Usa los chunks guardados para extraer variables clínicas con IA,
    ejecutar módulos de auditoría y crear/actualizar el paciente y sus hallazgos.
    """
    result = await db.execute(select(AuditSession).where(AuditSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if session.status != DocumentStatus.extraido.value:
        raise HTTPException(
            status_code=400,
            detail=f"Estado actual '{session.status}'. La sesión debe estar en 'extraido' para procesar con IA.",
        )

    session.status = DocumentStatus.analizando.value
    await db.commit()

    background_tasks.add_task(_do_process, session_id, current_user.id)

    return UploadResponse(
        session_id=session_id,
        status=DocumentStatus.analizando.value,
        message="Análisis con IA iniciado. Este proceso puede tardar unos minutos...",
    )


async def _do_process(session_id: str, user_id: str):
    """Worker: analiza chunks con IA y crea paciente + hallazgos en BD."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(AuditSession).where(AuditSession.id == session_id))
            session = result.scalar_one_or_none()
            if not session:
                return

            # Cargar todos los chunks ordenados
            chunks_q = await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.session_id == session_id)
                .order_by(DocumentChunk.chunk_index)
            )
            chunks = chunks_q.scalars().all()

            if not chunks:
                logger.error(f"❌ [PROCESS] Sin chunks para sesión {session_id}")
                session.status = DocumentStatus.error.value
                await db.commit()
                return

            # Reconstruir texto completo desde chunks (con referencia de página)
            full_text = "\n\n".join(
                f"[Página {c.page_number}]\n{c.text}" for c in chunks
            )
            logger.info(
                f"🤖 [PROCESS] Sesión {session_id}: {len(chunks)} chunks → "
                f"{len(full_text)} caracteres enviados a IA"
            )

            # Extraer variables clínicas con IA
            clinical_data = await extract_clinical_variables(full_text)
            if "error" in clinical_data:
                raise Exception(f"Error extracción IA: {clinical_data['error']}")

            # Ejecutar módulos de auditoría
            findings: list[Finding] = run_all_modules(clinical_data)
            risk_level = calculate_risk(findings)
            summary = generate_audit_summary(findings, clinical_data)

            fecha_ingreso_date = _parse_date(clinical_data.get("fecha_ingreso"))
            history_num = clinical_data.get("historia_numero") or session.historia_numero

            # Buscar paciente existente o crear uno nuevo
            patient = None
            if session.patient_id:
                patient = await db.get(PatientCase, session.patient_id)

            if not patient and history_num:
                q = select(PatientCase).where(PatientCase.historia_numero == history_num)
                res = await db.execute(q)
                patient = res.scalar_one_or_none()

            label = f"Caso {session_id[:6].upper()}"

            if not patient:
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
                # Actualizar datos del paciente existente
                patient.diagnostico_principal = clinical_data.get("diagnostico_principal") or patient.diagnostico_principal
                patient.codigo_cie10 = clinical_data.get("codigo_cie10") or patient.codigo_cie10
                patient.edad = clinical_data.get("edad") or patient.edad
                patient.sexo = clinical_data.get("sexo") or patient.sexo
                patient.riesgo = risk_level.value
                patient.riesgo_auditoria = summary["riesgo_global"]
                patient.medicamentos = clinical_data.get("medicamentos", patient.medicamentos)
                patient.antecedentes = clinical_data.get("antecedentes", patient.antecedentes)
                patient.estudios_solicitados = clinical_data.get("estudios_solicitados", patient.estudios_solicitados)
                patient.procedimientos = clinical_data.get("procedimientos", patient.procedimientos)
                patient.evoluciones = clinical_data.get("evoluciones", patient.evoluciones)

            # Registrar hallazgos deduplicados
            existing_q = await db.execute(
                select(AuditFinding).where(AuditFinding.patient_id == patient.id)
            )
            existing_f = existing_q.scalars().all()
            seen = {(f.modulo, f.pagina, f.descripcion) for f in existing_f}
            new_findings: list[AuditFinding] = []

            for f in findings:
                key = (f.modulo.value, f.pagina, f.descripcion)
                if key in seen:
                    continue
                af = AuditFinding(
                    id=str(uuid.uuid4()),
                    patient_id=patient.id,
                    modulo=f.modulo.value,
                    categoria=f.categoria,
                    riesgo=f.riesgo.value,
                    descripcion=f.descripcion,
                    recomendacion=f.recomendacion,
                    normativa_aplicable=f.normativa_aplicable,
                    valor_glosa_estimado=f.valor_glosa_estimado,
                    pagina=f.pagina,
                )
                db.add(af)
                new_findings.append(af)
                seen.add(key)

            # Recalcular totales del paciente
            patient.total_hallazgos = len(existing_f) + len(new_findings)
            patient.exposicion_glosas = sum(
                (af.valor_glosa_estimado or 0) for af in list(existing_f) + new_findings
            )
            patient.audit_status = "completed"

            # Vincular sesión al paciente y marcar como completada
            session.patient_id = patient.id
            session.historia_numero = history_num
            session.ultima_pagina_auditada = session.total_paginas_conocidas
            session.status = DocumentStatus.listo.value

            await db.commit()
            logger.info(
                f"✅ [PROCESS] Sesión {session_id} → paciente {patient.id} "
                f"| {len(new_findings)} hallazgos nuevos | riesgo {risk_level.value}"
            )

    except Exception as exc:
        logger.error(f"❌ [PROCESS] Error en sesión {session_id}: {exc}", exc_info=True)
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(AuditSession).where(AuditSession.id == session_id))
            s = result.scalar_one_or_none()
            if s:
                s.status = DocumentStatus.error.value
                await db.commit()


# ─── Consulta de chunks ──────────────────────────────────────────────────────

@router.get("/{session_id}/chunks", response_model=List[DocumentChunkRead])
async def get_chunks(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Devuelve los chunks de texto de una sesión (para depuración / visualización)."""
    chunks_q = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.session_id == session_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return chunks_q.scalars().all()
