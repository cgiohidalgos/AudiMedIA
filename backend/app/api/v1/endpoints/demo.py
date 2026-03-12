"""
Endpoint para crear casos de prueba sin necesidad de PDF.
Útil para demos y testing del sistema de auditoría.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.user import User
from app.models.patient import PatientCase
from app.models.audit import AuditFinding
from app.api.v1.deps import get_current_user
from app.services.ai.audit_modules import run_all_modules, calculate_risk, generate_audit_summary
from app.schemas.patient import PatientCaseRead
import uuid

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/create-sample-patient", response_model=PatientCaseRead)
async def create_sample_patient(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Crea un paciente de prueba con historia clínica simulada.
    Ejecuta los 4 módulos de auditoría automáticamente.
    Útil para probar el sistema sin necesidad de subir un PDF real.
    """
    
    # Datos clínicos de ejemplo: Infarto Agudo de Miocardio
    clinical_data = {
        "cama": "UCI-305",
        "edad": 68,
        "sexo": "M",
        "diagnostico_principal": "Infarto Agudo de Miocardio con elevación del ST de pared anterior",
        "codigo_cie10": "I21.0",
        "diagnosticos_secundarios": ["I25.1 Cardiopatía isquémica", "I10 Hipertensión arterial"],
        "fecha_ingreso": "2024-01-15",
        "dias_hospitalizacion": 18,
        "dias_esperados": 10,
        "medicamentos": [
            "Aspirina 100mg c/24h",
            "Atorvastatina 80mg c/24h",
            "Enalapril 10mg c/12h",
            "Metoprolol 50mg c/12h"
        ],
        "antecedentes": {
            "cardiovasculares": ["HTA desde hace 5 años"],
            "quirurgicos": []
        },
        "estudios_solicitados": [
            "Ecocardiograma - Resultado: pendiente",
            "Troponinas - Resultado: 8.5 ng/mL (elevadas)",
            "Radiografía de tórax - Indicación: no clara"
        ],
        "procedimientos": ["Cateterismo cardíaco con angioplastia"],
        "evoluciones": [
            {"fecha": "2024-01-15", "nota": "Ingreso por dolor torácico"},
            {"fecha": "2024-01-20", "nota": "Evolución favorable"}
        ]
    }
    
    # Ejecutar módulos de auditoría
    findings = run_all_modules(clinical_data)
    risk_level = calculate_risk(findings)
    summary = generate_audit_summary(findings, clinical_data)
    
    # Crear paciente
    patient = PatientCase(
        id=str(uuid.uuid4()),
        label="Paciente Demo IAM",
        cama=clinical_data.get("cama"),
        edad=clinical_data.get("edad"),
        sexo=clinical_data.get("sexo"),
        diagnostico_principal=clinical_data.get("diagnostico_principal"),
        codigo_cie10=clinical_data.get("codigo_cie10"),
        diagnosticos_secundarios=clinical_data.get("diagnosticos_secundarios", []),
        fecha_ingreso=clinical_data.get("fecha_ingreso"),
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
    
    # Guardar hallazgos
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
    
    await db.commit()
    await db.refresh(patient)
    
    return patient
