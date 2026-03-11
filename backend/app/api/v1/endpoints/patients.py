from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.models.user import User
from app.models.patient import PatientCase
from app.models.audit import AuditFinding
from app.schemas.patient import PatientCaseRead, PatientCaseSummary
from app.schemas.audit import AuditFindingRead, AuditFindingUpdate
from app.api.v1.deps import get_current_user

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


@router.patch("/{patient_id}/findings/{finding_id}", response_model=AuditFindingRead)
async def update_finding(
    patient_id: str,
    finding_id: str,
    payload: AuditFindingUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AuditFinding).where(
            AuditFinding.id == finding_id,
            AuditFinding.patient_id == patient_id,
        )
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")

    finding.resuelto = payload.resuelto
    await db.commit()
    await db.refresh(finding)
    return finding
