"""
Endpoints de procesamiento en etapas independientes:
  POST /processing/{session_id}/extract  → Etapa 2: extrae texto y guarda chunks (sin IA)
  POST /processing/{session_id}/process  → Etapa 3: analiza chunks con IA, crea paciente + hallazgos
  GET  /processing/{session_id}/progress → Progreso del análisis IA (lotes procesados)
  GET  /processing/{session_id}/chunks   → Lista de chunks de una sesión
"""
import json
import logging
import math
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
from app.services.ai.extractor import extract_clinical_variables, _merge_clinical_dicts
from app.services.ai.audit_modules import run_all_modules, calculate_risk, generate_audit_summary, Finding

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/processing", tags=["processing"])

# Chunks de BD por lote enviado a la IA (5 chunks à ~400 palabras ≈ 8k chars → 1 llamada OpenAI por lote)
BATCH_SIZE = 5
# Lotes procesados por ronda (el frontend para y muestra resultados parciales)
ROUND_SIZE = 20


class DocumentChunkRead(BaseModel):
    id: str
    session_id: str
    page_number: int
    chunk_index: int
    text: str
    word_count: int
    is_ocr: bool

    model_config = {"from_attributes": True}


class BatchResult(BaseModel):
    session_id: str
    batch_done: int
    total_batches: int
    is_last: bool
    status: str
    message: str


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


# ─── Background task: procesa TODOS los lotes internamente ──────────────────

async def _process_all_batches_bg(session_id: str, user_id: str):
    """
    Tarea en segundo plano: procesa todos los lotes de IA sin intervención del frontend.
    El frontend puede navegar libremente y sólo hace polling a /progress.
    """
    logger.info(f"🚀 [BG] Iniciando procesamiento en segundo plano para sesión {session_id}")
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(AuditSession).where(AuditSession.id == session_id))
            session = result.scalar_one_or_none()
            if not session:
                logger.error(f"❌ [BG] Sesión {session_id} no encontrada")
                return

            total_batches = session.ai_chunks_total or 1
            start_batch = session.ai_chunks_done or 0

            chunks_q = await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.session_id == session_id)
                .order_by(DocumentChunk.chunk_index)
            )
            chunks = chunks_q.scalars().all()

            merged: dict = {}
            if session.clinical_data_partial and session.clinical_data_partial not in ("{}", ""):
                try:
                    merged = json.loads(session.clinical_data_partial)
                except json.JSONDecodeError:
                    merged = {}

            for batch_idx in range(start_batch, total_batches):
                batch_chunks = chunks[batch_idx * BATCH_SIZE: (batch_idx + 1) * BATCH_SIZE]
                batch_text = "\n\n".join(f"[Página {c.page_number}]\n{c.text}" for c in batch_chunks)

                logger.info(
                    f"🤖 [BG] Sesión {session_id}: lote {batch_idx + 1}/{total_batches} "
                    f"({len(batch_chunks)} chunks, {len(batch_text):,} chars)"
                )

                partial = await extract_clinical_variables(batch_text)

                if "error" not in partial:
                    merged = _merge_clinical_dicts(merged, partial)
                else:
                    logger.warning(f"⚠️ [BG] Lote {batch_idx + 1} retornó error: {partial.get('error')}")

                session.clinical_data_partial = json.dumps(merged, ensure_ascii=False)
                session.ai_chunks_done = batch_idx + 1
                await db.commit()

            # Finalizar sesión
            if merged:
                await _finalize_session(session, merged, user_id, db)
            else:
                session.status = DocumentStatus.error.value
                await db.commit()
                logger.error(f"❌ [BG] Sesión {session_id}: sin datos clínicos al finalizar")

        except Exception as exc:
            logger.error(f"❌ [BG] Error en sesión {session_id}: {exc}", exc_info=True)
            try:
                await db.rollback()
                async with AsyncSessionLocal() as db2:
                    r = await db2.execute(select(AuditSession).where(AuditSession.id == session_id))
                    s = r.scalar_one_or_none()
                    if s:
                        s.status = DocumentStatus.error.value
                        await db2.commit()
            except Exception:
                pass


# ─── Etapa 3: Análisis con IA ────────────────────────────────────────────────

@router.post("/{session_id}/process", response_model=UploadResponse)
async def process_with_ai(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Etapa 3 — Init: Prepara el análisis IA, lanza el procesamiento en SEGUNDO PLANO
    y retorna inmediatamente. El frontend sólo hace polling a /progress.
    """
    result = await db.execute(select(AuditSession).where(AuditSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if session.status not in (
        DocumentStatus.extraido.value,
        DocumentStatus.error.value,
        DocumentStatus.analizando.value,
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Estado actual '{session.status}'. Solo se puede extraer desde 'subido'.",
        )

    # ── Continuación: si ya está analizando (bg task corriendo), retornar el estado actual ──
    if session.status == DocumentStatus.analizando.value:
        return UploadResponse(
            session_id=session_id,
            status=DocumentStatus.analizando.value,
            message=f"Análisis en curso: lote {session.ai_chunks_done}/{session.ai_chunks_total}.",
        )

    # ── Reanudación: si hay progreso parcial guardado, continuar desde donde quedó ──
    if (session.ai_chunks_done or 0) > 0 and session.clinical_data_partial not in (None, '{}', ''):
        session.status = DocumentStatus.analizando.value
        await db.commit()
        background_tasks.add_task(_process_all_batches_bg, session_id, current_user.id)
        return UploadResponse(
            session_id=session_id,
            status=DocumentStatus.analizando.value,
            message=f"Reanudando análisis desde lote {session.ai_chunks_done + 1}/{session.ai_chunks_total}.",
        )

    # ── Inicio desde cero ──
    chunks_q = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.session_id == session_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = chunks_q.scalars().all()
    if not chunks:
        raise HTTPException(status_code=400, detail="No hay chunks. Re-extrae el texto primero.")

    total_batches = math.ceil(len(chunks) / BATCH_SIZE) or 1
    session.status = DocumentStatus.analizando.value
    session.ai_chunks_total = total_batches
    session.ai_chunks_done = 0
    session.clinical_data_partial = "{}"
    await db.commit()

    background_tasks.add_task(_process_all_batches_bg, session_id, current_user.id)

    return UploadResponse(
        session_id=session_id,
        status=DocumentStatus.analizando.value,
        message=f"Análisis iniciado en segundo plano: {total_batches} lotes a procesar.",
    )


# ─── Etapa 3a: Guardar resultados parciales y volver a 'extraido' ────────────

@router.post("/{session_id}/partial_finalize", response_model=UploadResponse)
async def partial_finalize(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Guarda paciente y hallazgos con los datos acumulados hasta ahora (is_partial=True)
    y vuelve el status a 'extraido' para permitir continuar el análisis más tarde.
    """
    result = await db.execute(select(AuditSession).where(AuditSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if session.status != DocumentStatus.analizando.value:
        raise HTTPException(
            status_code=400,
            detail=f"Estado '{session.status}'. Solo se puede finalizar parcialmente estando en 'analizando'.",
        )

    clinical_data: dict = {}
    if session.clinical_data_partial and session.clinical_data_partial not in ("{}", ""):
        try:
            clinical_data = json.loads(session.clinical_data_partial)
        except json.JSONDecodeError:
            clinical_data = {}

    if clinical_data:
        try:
            await _finalize_session(session, clinical_data, current_user.id, db, is_partial=True)
        except Exception as exc:
            logger.error(f"⚠️ [PARTIAL] Error en _finalize_session para {session_id}: {exc}", exc_info=True)
            # Aunque falle el guardado de paciente/hallazgos, siempre volver a 'extraido'
            # para que el usuario pueda continuar el análisis
            try:
                await db.rollback()
                result2 = await db.execute(select(AuditSession).where(AuditSession.id == session_id))
                s2 = result2.scalar_one_or_none()
                if s2:
                    s2.status = DocumentStatus.extraido.value
                    await db.commit()
            except Exception:
                pass
    else:
        # Sin datos aún — solo pausar
        session.status = DocumentStatus.extraido.value
        await db.commit()
        logger.info(f"⏸️ [PARTIAL] Sesión {session_id}: sin datos clínicos aún, status→extraido")

    return UploadResponse(
        session_id=session_id,
        status=DocumentStatus.extraido.value,
        message=f"Resultados parciales guardados. Lotes procesados: {session.ai_chunks_done}/{session.ai_chunks_total}.",
    )



# ─── Helper de finalización ──────────────────────────────────────────────────

async def _finalize_session(session: AuditSession, clinical_data: dict, user_id: str, db: AsyncSession, is_partial: bool = False):
    """Crea o actualiza paciente y hallazgos. is_partial=True → mantiene status=extraido para continuar."""
    session_id = session.id
    findings: list[Finding] = run_all_modules(clinical_data)
    risk_level = calculate_risk(findings)
    summary = generate_audit_summary(findings, clinical_data)

    fecha_ingreso_date = _parse_date(clinical_data.get("fecha_ingreso"))
    history_num = clinical_data.get("historia_numero") or session.historia_numero

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

    existing_q = await db.execute(select(AuditFinding).where(AuditFinding.patient_id == patient.id))
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

    patient.total_hallazgos = len(existing_f) + len(new_findings)
    patient.exposicion_glosas = sum((af.valor_glosa_estimado or 0) for af in list(existing_f) + new_findings)
    patient.audit_status = "completed"
    session.patient_id = patient.id
    session.historia_numero = history_num
    # En análisis parcial registrar la página hasta donde se llegó
    if is_partial:
        analyzed_pages = round(
            (session.ai_chunks_done or 0) / (session.ai_chunks_total or 1) * (session.total_paginas_conocidas or 0)
        )
        session.ultima_pagina_auditada = analyzed_pages
        session.status = DocumentStatus.extraido.value  # vuelve a 'extraido' para poder continuar
    else:
        session.ultima_pagina_auditada = session.total_paginas_conocidas
        session.status = DocumentStatus.listo.value
        session.clinical_data_partial = None  # liberar espacio
    await db.commit()
    logger.info(
        f"{'🔄 [PARTIAL]' if is_partial else '✅ [FINALIZE]'} Sesión {session_id} → paciente {patient.id} "
        f"| {len(new_findings)} hallazgos nuevos | riesgo {risk_level.value}"
    )


# ─── Etapa 3b: Procesar un lote ──────────────────────────────────────────────

@router.post("/{session_id}/process_batch", response_model=BatchResult)
async def process_next_batch(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Procesa el siguiente lote de chunks con IA. Llamar repetidamente hasta is_last=True.
    Cada llamada es síncrona y devuelve cuando el lote termina.
    """
    result = await db.execute(select(AuditSession).where(AuditSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if session.status != DocumentStatus.analizando.value:
        raise HTTPException(
            status_code=400,
            detail=f"Estado '{session.status}'. Llame primero a /process para inicializar.",
        )

    batch_idx = session.ai_chunks_done or 0
    total_batches = session.ai_chunks_total or 1

    # Si ya se procesaron todos los lotes retornar sin hacer nada
    if batch_idx >= total_batches:
        return BatchResult(
            session_id=session_id,
            batch_done=batch_idx,
            total_batches=total_batches,
            is_last=True,
            status=session.status,
            message="Todos los lotes ya fueron procesados.",
        )

    # Cargar chunks para este lote
    chunks_q = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.session_id == session_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = chunks_q.scalars().all()
    batch_chunks = chunks[batch_idx * BATCH_SIZE: (batch_idx + 1) * BATCH_SIZE]
    batch_text = "\n\n".join(f"[Página {c.page_number}]\n{c.text}" for c in batch_chunks)

    logger.info(
        f"🤖 [BATCH] Sesión {session_id}: lote {batch_idx + 1}/{total_batches} "
        f"({len(batch_chunks)} chunks, {len(batch_text):,} chars)"
    )

    # Llamada a IA (síncrona, una sola llamada para este lote)
    partial = await extract_clinical_variables(batch_text)

    # Cargar y combinar datos acumulados
    current_partial: dict = {}
    if session.clinical_data_partial and session.clinical_data_partial not in ("{}", ""):
        try:
            current_partial = json.loads(session.clinical_data_partial)
        except json.JSONDecodeError:
            current_partial = {}

    if "error" not in partial:
        merged = _merge_clinical_dicts(current_partial, partial)
    else:
        merged = current_partial
        logger.warning(f"⚠️ [BATCH] Lote {batch_idx + 1} retornó error: {partial.get('error')}")

    # Guardar progreso
    session.clinical_data_partial = json.dumps(merged, ensure_ascii=False)
    session.ai_chunks_done = batch_idx + 1
    is_last = (batch_idx + 1) >= total_batches

    if is_last:
        if merged:
            await _finalize_session(session, merged, current_user.id, db)
        else:
            session.status = DocumentStatus.error.value
            await db.commit()
    else:
        await db.commit()

    return BatchResult(
        session_id=session_id,
        batch_done=batch_idx + 1,
        total_batches=total_batches,
        is_last=is_last,
        status=session.status,
        message=f"Lote {batch_idx + 1}/{total_batches} procesado.",
    )

@router.get("/{session_id}/progress")
async def get_progress(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Devuelve el progreso del análisis IA: lotes procesados vs total."""
    result = await db.execute(select(AuditSession).where(AuditSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {
        "status": session.status,
        "ai_chunks_done": session.ai_chunks_done or 0,
        "ai_chunks_total": session.ai_chunks_total or 0,
    }


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
