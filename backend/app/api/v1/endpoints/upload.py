import os
import uuid
import hashlib
import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.models.user import User
from app.models.audit import AuditSession, DocumentStatus
from app.schemas.audit import UploadResponse
from app.api.v1.deps import get_current_user, require_role
from app.models.user import AppRole
from app.core.config import settings
from app.workers.pdf_worker import process_pdf_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["upload"])

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@router.post("/", response_model=List[UploadResponse])
async def upload_pdfs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(AppRole.admin, AppRole.auditor)),
):
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Máximo 5 PDFs simultáneos")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    responses = []

    for idx, file in enumerate(files):
        logger.info("[upload] archivo recibido: %s (idx=%d)", file.filename, idx)
        if not file.filename.lower().endswith(".pdf"):
            logger.warning("[upload] rechazado (no PDF): %s", file.filename)
            raise HTTPException(status_code=400, detail=f"{file.filename} no es un PDF válido")

        content = await file.read()
        logger.debug("[upload] tamaño: %.1f KB", len(content) / 1024)
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            logger.warning("[upload] rechazado (tamaño): %s", file.filename)
            raise HTTPException(status_code=413, detail=f"{file.filename} supera el tamaño máximo")

        file_hash = hashlib.sha256(content).hexdigest()
        file_path = os.path.join(settings.UPLOAD_DIR, f"{file_hash}.pdf")
        logger.debug("[upload] hash: %s", file_hash)

        with open(file_path, "wb") as f:
            f.write(content)

        # Verificar si es una re-carga (auditoría incremental)
        # Solo reutilizar si la sesión anterior terminó bien (listo/cargando/analizando)
        result = await db.execute(
            select(AuditSession).where(
                AuditSession.pdf_hash == file_hash,
                AuditSession.status != DocumentStatus.error.value,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info("[upload] documento ya existe, retornando sesión: %s", existing.id)
            responses.append(UploadResponse(
                session_id=existing.id,
                status=existing.status,
                message="Documento sin cambios desde la última auditoría",
            ))
            continue

        label = f"Historia {ALPHABET[idx % 26]}"
        session_id = str(uuid.uuid4())
        session = AuditSession(
            id=session_id,
            user_id=current_user.id,
            pdf_hash=file_hash,
            pdf_path=file_path,
            status=DocumentStatus.cargando.value,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        background_tasks.add_task(process_pdf_task, session_id, file_path, label)
        logger.info("[upload] tarea en cola: session_id=%s label=%s", session_id, label)

        responses.append(UploadResponse(
            session_id=session_id,
            status=DocumentStatus.cargando.value,
            message=f"'{file.filename}' cargado como {label}. Procesando...",
            progress=0.0,
        ))

    logger.info("[upload] respuestas enviadas: %d", len(responses))
    return responses


@router.get("/status/{session_id}", response_model=UploadResponse)
async def get_upload_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(AuditSession).where(AuditSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    total = session.total_paginas_conocidas or 0
    done = session.ultima_pagina_auditada or 0
    progress = 0.0
    if total > 0:
        progress = min(100.0, max(0.0, (done / total) * 100))

    # Fallback por estado (para casos donde no hay páginas conocidas aún)
    if total == 0:
        status_map = {
            DocumentStatus.cargando.value: 5,
            DocumentStatus.anonimizando.value: 25,
            DocumentStatus.extrayendo.value: 50,
            DocumentStatus.analizando.value: 75,
            DocumentStatus.listo.value: 100,
            DocumentStatus.error.value: 100,
        }
        progress = status_map.get(session.status, 0)

    logger.info("[upload/status] session=%s status=%s progress=%.1f", session.id, session.status, progress)
    return UploadResponse(
        session_id=session.id,
        status=session.status,
        message=f"Estado: {session.status}",
        progress=progress,
    )
