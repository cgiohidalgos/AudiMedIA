"""
Servicio de notificaciones:
- Genera resumen de texto de pendientes de auditoría.
- Crea notificaciones en-app para el equipo médico tratante.
"""
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.audit import AuditFinding
from app.models.patient import PatientCase
from app.models.user import User, AppRole


async def generate_pending_summary(patient_id: str, db: AsyncSession) -> str:
    """Devuelve un resumen de texto plano con los hallazgos activos del paciente."""
    result = await db.execute(
        select(PatientCase).where(PatientCase.id == patient_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        return "Paciente no encontrado."

    result = await db.execute(
        select(AuditFinding)
        .where(
            AuditFinding.patient_id == patient_id,
            AuditFinding.estado == "activo",
        )
        .order_by(AuditFinding.riesgo.desc())
    )
    findings = result.scalars().all()

    cama_info = f"Cama {patient.cama}" if patient.cama else (patient.historia_numero or "N/A")
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    lines = [
        "=" * 55,
        "  PENDIENTES DE AUDITORÍA MÉDICA",
        "=" * 55,
        f"Historia   : {patient.historia_numero or 'N/A'}",
        f"Cama       : {patient.cama or 'N/A'}",
        f"Diagnóstico: {patient.codigo_cie10 or ''} - {patient.diagnostico_principal or 'N/A'}",
        f"Días hosp. : {patient.dias_hospitalizacion or 'N/A'}",
        f"Riesgo     : {(patient.riesgo or 'bajo').upper()}",
        f"Fecha      : {now_str}",
        "=" * 55,
        "",
    ]

    if findings:
        lines.append(f"Total pendientes: {len(findings)}")
        lines.append("")
        lines.append("HALLAZGOS ACTIVOS:")
        lines.append("-" * 40)
        for i, f in enumerate(findings, 1):
            glosa = (
                f"  (glosa est.: ${f.valor_glosa_estimado:,.0f} COP)"
                if f.valor_glosa_estimado
                else ""
            )
            lines.append(f"{i}. [{f.riesgo.upper()}] [{f.modulo.upper()}] {f.descripcion}{glosa}")
            if f.recomendacion:
                lines.append(f"   → {f.recomendacion}")
        lines.append("")
    else:
        lines.append("Sin hallazgos pendientes.")
        lines.append("")

    lines += [
        "-" * 55,
        "AudiMedIA - Auditoría Médica Inteligente",
        now_str,
    ]
    return "\n".join(lines)


async def notify_medical_team(
    patient_id: str, sender_id: str, db: AsyncSession
) -> int:
    """Crea notificaciones en-app para equipo médico, coordinadores y admin."""
    result = await db.execute(
        select(PatientCase).where(PatientCase.id == patient_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        return 0

    result = await db.execute(
        select(AuditFinding).where(
            AuditFinding.patient_id == patient_id,
            AuditFinding.estado == "activo",
        )
    )
    findings = result.scalars().all()
    if not findings:
        return 0

    # Destinatarios: equipo_medico + coordinadores + admins (excepto el remitente)
    result = await db.execute(
        select(User).where(
            User.role.in_([
                AppRole.equipo_medico.value,
                AppRole.coordinador.value,
                AppRole.admin.value,
            ]),
            User.is_active == True,
            User.id != sender_id,
        )
    )
    recipients = result.scalars().all()
    if not recipients:
        return 0

    cama_info = f"Cama {patient.cama}" if patient.cama else (patient.historia_numero or "Paciente")
    high_risk = sum(1 for f in findings if f.riesgo == "alto")
    n = len(findings)

    titulo = f"Pendientes de auditoría — {cama_info}"
    mensaje = (
        f"{cama_info}: {n} hallazgo{'s' if n != 1 else ''} pendiente{'s' if n != 1 else ''}. "
        f"Riesgo global: {(patient.riesgo or 'bajo').upper()}."
    )
    if high_risk > 0:
        mensaje += f" ({high_risk} de riesgo ALTO)"

    count = 0
    for user in recipients:
        db.add(
            Notification(
                user_id=user.id,
                patient_id=patient_id,
                titulo=titulo,
                mensaje=mensaje,
                tipo="pendientes",
            )
        )
        count += 1

    await db.commit()
    return count
