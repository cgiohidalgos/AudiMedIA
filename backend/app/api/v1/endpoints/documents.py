"""
Endpoint para servir documentos PDF de expedientes clínicos en modo inline
(para visualización en el visor integrado del frontend).
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os

from app.db.session import get_db
from app.api.v1.deps import get_current_user
from app.models.user import User
from app.models.patient import PatientCase
from app.models.audit import AuditSession

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/patients/{patient_id}/pdf")
async def view_patient_pdf(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Sirve el PDF original del paciente en modo inline para el visor integrado.
    Requiere autenticación JWT.
    """
    # Verificar que el paciente existe
    result = await db.execute(select(PatientCase).where(PatientCase.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Obtener la sesión de auditoría más reciente con PDF disponible
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
            detail="No se encontró el PDF para este paciente"
        )

    if not os.path.exists(audit_session.pdf_path):
        raise HTTPException(
            status_code=404,
            detail="El archivo PDF no está disponible en el servidor"
        )

    return FileResponse(
        path=audit_session.pdf_path,
        media_type="application/pdf",
        filename=f"historia_clinica_{patient.label}.pdf",
        headers={
            "Content-Disposition": f"inline; filename=historia_clinica_{patient.label}.pdf",
            "Cache-Control": "no-cache",
        },
    )
