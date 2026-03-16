"""Servicio de generación de recomendaciones estructuradas (Nivel 1 por paciente)."""
from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditFinding
from app.models.patient import PatientCase
from app.models.recommendation import Recommendation


# ── Mapas de configuración ────────────────────────────────────────────────────

_TIPO_POR_MODULO = {
    "estancia": "estancia",
    "cie10": "documentacion",
    "glosas": "documentacion",
    "estudios": "estudios",
}

_CATEGORIA_POR_RIESGO = {
    "alto": "alerta",
    "medio": "mejora",
    "bajo": "optimizacion",
}

_PRIORIDAD_POR_RIESGO = {
    "alto": "alta",
    "medio": "media",
    "bajo": "baja",
}


# ── Funciones auxiliares de mensajes ─────────────────────────────────────────

def _mensaje_estancia(f: AuditFinding, patient: PatientCase) -> str:
    dias_real = patient.dias_hospitalizacion or "?"
    dias_esp = patient.dias_esperados or "no definidos"
    return (
        f"Evaluar criterios de egreso: {dias_real} días actuales vs {dias_esp} esperados. "
        f"{f.recomendacion}"
    )


def _mensaje_documentacion(f: AuditFinding) -> str:
    return f.recomendacion or f.descripcion


def _mensaje_estudios(f: AuditFinding) -> str:
    return (
        f"Verificar y completar documentación de estudios: {f.descripcion}. "
        f"{f.recomendacion}"
    )


def _mensaje_complicacion(f: AuditFinding) -> str:
    return (
        f"⚠️ Alerta clínica: {f.descripcion}. "
        f"{f.recomendacion} "
        f"— Esta alerta es generada por IA y no constituye diagnóstico clínico."
    )


def _build_mensaje(f: AuditFinding, patient: PatientCase) -> tuple[str, str]:
    """Retorna (mensaje, detalle) específico según módulo y hallazgo."""
    modulo = f.modulo

    if modulo == "estancia":
        return _mensaje_estancia(f, patient), f.descripcion
    if modulo in ("cie10", "glosas"):
        return _mensaje_documentacion(f), f.descripcion
    if modulo == "estudios":
        return _mensaje_estudios(f), f.descripcion

    # fallback
    return f.recomendacion or f.descripcion, f.descripcion


# ── Función principal ─────────────────────────────────────────────────────────

async def generate_patient_recommendations(
    patient: PatientCase,
    db: AsyncSession,
    overwrite: bool = False,
) -> List[Recommendation]:
    """
    Genera recomendaciones estructuradas (Nivel 1) para un paciente a partir
    de sus hallazgos de auditoría activos.

    Si `overwrite=True`, elimina las anteriores antes de generar.
    Devuelve la lista de recomendaciones guardadas.
    """
    # Obtener hallazgos activos (no descartados)
    result = await db.execute(
        select(AuditFinding)
        .where(
            AuditFinding.patient_id == patient.id,
            AuditFinding.estado != "descartado",
        )
        .order_by(AuditFinding.created_at)
    )
    findings: List[AuditFinding] = list(result.scalars().all())

    # Eliminar existentes si se solicita
    if overwrite:
        existing = await db.execute(
            select(Recommendation).where(Recommendation.patient_id == patient.id)
        )
        for rec in existing.scalars().all():
            await db.delete(rec)
        await db.flush()

    # IDs de hallazgos que ya tienen recomendación (para no duplicar)
    existing_finding_ids: set[str] = set()
    if not overwrite:
        ex_result = await db.execute(
            select(Recommendation.finding_id).where(
                Recommendation.patient_id == patient.id,
                Recommendation.finding_id.isnot(None),
            )
        )
        existing_finding_ids = {r for r in ex_result.scalars().all() if r}

    new_recs: List[Recommendation] = []

    for f in findings:
        if f.id in existing_finding_ids:
            continue  # ya procesado

        tipo = _TIPO_POR_MODULO.get(f.modulo, "documentacion")
        categoria = _CATEGORIA_POR_RIESGO.get(f.riesgo, "mejora")
        prioridad = _PRIORIDAD_POR_RIESGO.get(f.riesgo, "media")

        # Detectar patrón de complicación (estancia alta + motivo complejo)
        if (
            f.modulo == "estancia"
            and (patient.dias_hospitalizacion or 0) > 10
            and f.riesgo == "alto"
        ):
            tipo = "complicacion"
            categoria = "critica"
            prioridad = "alta"
            mensaje, detalle = _mensaje_complicacion(f), f.descripcion
        else:
            mensaje, detalle = _build_mensaje(f, patient)

        rec = Recommendation(
            patient_id=patient.id,
            finding_id=f.id,
            tipo=tipo,
            categoria=categoria,
            prioridad=prioridad,
            mensaje=mensaje,
            detalle=detalle,
            estado="pendiente",
        )
        db.add(rec)
        new_recs.append(rec)

    await db.commit()

    # Refrescar todos para tener IDs y timestamps
    for rec in new_recs:
        await db.refresh(rec)

    return new_recs
