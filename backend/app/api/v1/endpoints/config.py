from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.v1.deps import get_db, require_role
from app.models.user import User, AppRole
from app.models.tarifa import TarifaConfig
from app.models.eps_contrato import EPSContrato
from app.models.servicio_hospitalario import ServicioHospitalario
from app.schemas.audit import (
    TarifaConfigRead,
    TarifaConfigUpdate,
    EPSContratoRead,
    EPSContratoCreate,
    EPSContratoUpdate,
    ServicioRead,
    ServicioCreate,
    ServicioUpdate,
    SistemaParamsRead,
)
from app.core.config import settings

router = APIRouter(prefix="/config", tags=["config"])

# ─── Tarifas Hospitalarias ────────────────────────────────────────────────────

@router.get("/tarifas", response_model=TarifaConfigRead)
async def get_tarifas(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.coordinador, AppRole.admin)),
):
    """Obtener configuración de tarifas actual"""
    tarifa = await db.scalar(select(TarifaConfig).where(TarifaConfig.activo == True))
    if not tarifa:
        tarifa = TarifaConfig()
        db.add(tarifa)
        await db.commit()
        await db.refresh(tarifa)
    return tarifa


@router.put("/tarifas", response_model=TarifaConfigRead)
async def update_tarifas(
    payload: TarifaConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.admin)),
):
    """Actualizar configuración de tarifas (solo admin)"""
    tarifa = await db.scalar(select(TarifaConfig).where(TarifaConfig.activo == True))
    if not tarifa:
        tarifa = TarifaConfig()
        db.add(tarifa)
        await db.flush()
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(tarifa, field, value)
    await db.commit()
    await db.refresh(tarifa)
    return tarifa


# ─── EPS Contratos ────────────────────────────────────────────────────────────

@router.get("/eps", response_model=list[EPSContratoRead])
async def list_eps(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.coordinador, AppRole.admin)),
):
    """Listar contratos con EPS"""
    result = await db.execute(select(EPSContrato).order_by(EPSContrato.nombre_eps))
    return result.scalars().all()


@router.post("/eps", response_model=EPSContratoRead, status_code=201)
async def create_eps(
    payload: EPSContratoCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.admin)),
):
    """Crear nuevo contrato EPS (solo admin)"""
    contrato = EPSContrato(**payload.model_dump())
    db.add(contrato)
    await db.commit()
    await db.refresh(contrato)
    return contrato


@router.put("/eps/{contrato_id}", response_model=EPSContratoRead)
async def update_eps(
    contrato_id: str,
    payload: EPSContratoUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.admin)),
):
    """Actualizar contrato EPS (solo admin)"""
    contrato = await db.scalar(select(EPSContrato).where(EPSContrato.id == contrato_id))
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato EPS no encontrado")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(contrato, field, value)
    await db.commit()
    await db.refresh(contrato)
    return contrato


@router.delete("/eps/{contrato_id}", status_code=204)
async def delete_eps(
    contrato_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.admin)),
):
    """Eliminar contrato EPS (solo admin)"""
    contrato = await db.scalar(select(EPSContrato).where(EPSContrato.id == contrato_id))
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato EPS no encontrado")
    await db.delete(contrato)
    await db.commit()


# ─── Servicios Hospitalarios ──────────────────────────────────────────────────

@router.get("/servicios", response_model=list[ServicioRead])
async def list_servicios(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.coordinador, AppRole.admin)),
):
    """Listar servicios hospitalarios"""
    result = await db.execute(
        select(ServicioHospitalario).order_by(ServicioHospitalario.nombre)
    )
    return result.scalars().all()


@router.post("/servicios", response_model=ServicioRead, status_code=201)
async def create_servicio(
    payload: ServicioCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.admin)),
):
    """Crear nuevo servicio hospitalario (solo admin)"""
    servicio = ServicioHospitalario(**payload.model_dump())
    db.add(servicio)
    await db.commit()
    await db.refresh(servicio)
    return servicio


@router.put("/servicios/{servicio_id}", response_model=ServicioRead)
async def update_servicio(
    servicio_id: str,
    payload: ServicioUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.admin)),
):
    """Actualizar servicio hospitalario (solo admin)"""
    servicio = await db.scalar(
        select(ServicioHospitalario).where(ServicioHospitalario.id == servicio_id)
    )
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(servicio, field, value)
    await db.commit()
    await db.refresh(servicio)
    return servicio


@router.delete("/servicios/{servicio_id}", status_code=204)
async def delete_servicio(
    servicio_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.admin)),
):
    """Eliminar servicio hospitalario (solo admin)"""
    servicio = await db.scalar(
        select(ServicioHospitalario).where(ServicioHospitalario.id == servicio_id)
    )
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    await db.delete(servicio)
    await db.commit()


# ─── Parámetros del Sistema ──────────────────────────────────────────────────

@router.get("/sistema", response_model=SistemaParamsRead)
async def get_sistema_params(
    _: User = Depends(require_role(AppRole.admin)),
):
    """Parámetros del sistema (solo lectura, solo admin)"""
    masked_key = "••••••••" if settings.OPENAI_API_KEY else "(no configurado)"
    return SistemaParamsRead(
        llm_model=settings.LLM_MODEL,
        llm_max_tokens=settings.LLM_MAX_TOKENS,
        openai_key_configured=bool(settings.OPENAI_API_KEY),
        openai_key_preview=masked_key,
        max_pdfs_simultaneos=5,
        retencion_datos_dias=365,
        anonimizacion_activa=True,
    )
