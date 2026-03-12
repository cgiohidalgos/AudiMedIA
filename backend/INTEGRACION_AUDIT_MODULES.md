# Integración de Módulos de Auditoría Clínica

## Resumen
Los 4 módulos de auditoría clínica están implementados y probados:

1. ✅ **Módulo 1: Análisis de Estancia** - Detecta estancias prolongadas vs CIE-10
2. ✅ **Módulo 2: Pertinencia CIE-10** - Valida coherencia diagnóstica con criterios
3. ✅ **Módulo 3: Pertinencia Estudios** - Verifica consentimientos y resultados
4. ✅ **Módulo 4: Detección de Glosas** - Calcula exposición económica

## Estructura de Datos

### Input: patient_data (dict)
```python
{
    # BÁSICOS
    "diagnostico_principal": str,
    "codigo_cie10": str,  # Ej: "I21.0"
    "dias_hospitalizacion": int,
    "fecha_ingreso": str,  # ISO format: "2024-01-15"
    "en_uci": bool,
    
    # CLÍNICOS
    "sintomas": List[str] | str,  # ["dolor torácico", "disnea"]
    "antecedentes": str,
    "examenes_realizados": List[str],  # ["Troponinas", "ECG"]
    
    # EVOLUCIONES
    "evoluciones": [
        {"fecha": "2024-01-15", "texto": "..."},
        ...
    ],
    
    # MEDICAMENTOS
    "medicamentos": [
        {
            "nombre": str,
            "orden_medica": bool,
            "indicacion": str
        },
        ...
    ],
    
    # ESTUDIOS
    "estudios_solicitados": [
        {
            "nombre": str,
            "codigo_cups": str,
            "resultado_disponible": bool,
            "fecha_solicitud": str,  # ISO format
            "resultado_fecha": str | None
        },
        ...
    ],
    
    # PROCEDIMIENTOS
    "procedimientos_realizados": [
        {
            "nombre": str,
            "codigo_cups": str,
            "consentimiento_firmado": bool,
            "indicacion": str
        },
        ...
    ]
}
```

### Output: findings (List[Finding])
```python
@dataclass
class Finding:
    modulo: AuditModule  # estancia, cie10, estudios, glosas
    descripcion: str
    riesgo: RiskLevel  # bajo, medio, alto
    pagina: Optional[int]
    recomendacion: str
    valor_glosa_estimado: Optional[float]  # COP
    normativa_aplicable: Optional[str]
    categoria: Optional[str]
```

### Output: summary (dict)
```python
{
    "riesgo_global": "alto" | "medio" | "bajo",
    "total_hallazgos": int,
    "hallazgos_por_riesgo": {
        "alto": int,
        "medio": int,
        "bajo": int
    },
    "hallazgos_por_modulo": {
        "estancia": int,
        "cie10": int,
        "estudios": int,
        "glosas": int
    },
    "exposicion_glosas_cop": float,
    "hallazgos_criticos": [
        {
            "modulo": str,
            "descripcion": str,
            "recomendacion": str,
            "valor_glosa": float
        },
        ...
    ],
    "paciente": {
        "diagnostico": str,
        "codigo_cie10": str,
        "dias_hospitalizacion": int
    },
    "recomendacion_general": str
}
```

## Integración con Endpoint POST /patients

### Opción 1: Integración Directa (Síncrona)

Ejecutar módulos inmediatamente al procesar el PDF.

**Ubicación:** `backend/app/api/v1/endpoints/patients.py`

```python
from app.services.ai.audit_modules import run_all_modules, generate_audit_summary
from app.models.audit import AuditFinding  # Crear modelo si no existe

@router.post("/", response_model=PatientResponse)
async def create_patient(
    file: UploadFile,
    current_user: User = Depends(require_role(["admin", "auditor", "coordinador"]))
):
    # ... extraer texto del PDF ...
    # ... extraer datos con extractor.py ...
    
    patient_data = {
        "diagnostico_principal": extracted_data.get("diagnostico", ""),
        "codigo_cie10": extracted_data.get("codigo_cie10", ""),
        "dias_hospitalizacion": extracted_data.get("dias_hospitalizacion", 0),
        "fecha_ingreso": extracted_data.get("fecha_ingreso"),
        "sintomas": extracted_data.get("sintomas", []),
        "examenes_realizados": extracted_data.get("examenes", []),
        "evoluciones": extracted_data.get("evoluciones", []),
        "medicamentos": extracted_data.get("medicamentos", []),
        "estudios_solicitados": extracted_data.get("estudios", []),
        "procedimientos_realizados": extracted_data.get("procedimientos", []),
        "en_uci": "UCI" in extracted_data.get("ubicacion", "").upper()
    }
    
    # EJECUTAR MÓDULOS DE AUDITORÍA
    findings = run_all_modules(patient_data)
    summary = generate_audit_summary(findings, patient_data)
    
    # Guardar paciente en base de datos
    patient = PatientCase(
        nombre=extracted_data.get("nombre"),
        documento=extracted_data.get("documento"),
        edad=extracted_data.get("edad"),
        diagnostico=patient_data["diagnostico_principal"],
        codigo_cie10=patient_data["codigo_cie10"],
        fecha_ingreso=patient_data["fecha_ingreso"],
        dias_hospitalizacion=patient_data["dias_hospitalizacion"],
        usuario_id=current_user.id,
        # Nuevos campos para auditoría
        riesgo_auditoria=summary["riesgo_global"],
        total_hallazgos=summary["total_hallazgos"],
        exposicion_glosas=summary["exposicion_glosas_cop"]
    )
    db.add(patient)
    await db.flush()
    
    # Guardar hallazgos en tabla separada
    for finding in findings:
        audit_finding = AuditFinding(
            paciente_id=patient.id,
            modulo=finding.modulo.value,
            descripcion=finding.descripcion,
            riesgo=finding.riesgo.value,
            recomendacion=finding.recomendacion,
            valor_glosa_estimado=finding.valor_glosa_estimado,
            normativa_aplicable=finding.normativa_aplicable,
            categoria=finding.categoria,
            pagina=finding.pagina
        )
        db.add(audit_finding)
    
    await db.commit()
    
    return PatientResponse(
        id=patient.id,
        nombre=patient.nombre,
        diagnostico=patient.diagnostico,
        riesgo_auditoria=summary["riesgo_global"],
        total_hallazgos=summary["total_hallazgos"],
        exposicion_glosas=summary["exposicion_glosas_cop"],
        hallazgos_criticos=summary["hallazgos_criticos"],
        recomendacion_general=summary["recomendacion_general"]
    )
```

### Opción 2: Integración Asíncrona (Background Worker)

Para casos pesados, usar Celery o similar.

**Ubicación:** `backend/app/workers/audit_worker.py`

```python
from app.services.ai.audit_modules import run_all_modules, generate_audit_summary
from app.db.session import AsyncSession
from app.models.patient import PatientCase
from app.models.audit import AuditFinding

async def process_audit_async(patient_id: int, patient_data: dict):
    """
    Procesa auditoría de forma asíncrona.
    Se ejecuta después de que el PDF fue procesado.
    """
    # Ejecutar módulos
    findings = run_all_modules(patient_data)
    summary = generate_audit_summary(findings, patient_data)
    
    # Actualizar paciente
    async with AsyncSession() as db:
        patient = await db.get(PatientCase, patient_id)
        patient.riesgo_auditoria = summary["riesgo_global"]
        patient.total_hallazgos = summary["total_hallazgos"]
        patient.exposicion_glosas = summary["exposicion_glosas_cop"]
        patient.audit_status = "completed"
        
        # Guardar hallazgos
        for finding in findings:
            audit_finding = AuditFinding(
                paciente_id=patient_id,
                modulo=finding.modulo.value,
                descripcion=finding.descripcion,
                riesgo=finding.riesgo.value,
                recomendacion=finding.recomendacion,
                valor_glosa_estimado=finding.valor_glosa_estimado,
                normativa_aplicable=finding.normativa_aplicable,
                categoria=finding.categoria,
                pagina=finding.pagina
            )
            db.add(audit_finding)
        
        await db.commit()
    
    return summary
```

## Modelos de Base de Datos

### PatientCase (Actualización)
```python
# backend/app/models/patient.py

class PatientCase(Base):
    __tablename__ = "patients"
    
    # ... campos existentes ...
    
    # Nuevos campos para auditoría
    riesgo_auditoria: Mapped[str] = mapped_column(String, nullable=True)  # bajo, medio, alto
    total_hallazgos: Mapped[int] = mapped_column(Integer, default=0)
    exposicion_glosas: Mapped[float] = mapped_column(Float, default=0.0)  # COP
    audit_status: Mapped[str] = mapped_column(String, default="pending")  # pending, processing, completed
    
    # Relación
    audit_findings: Mapped[List["AuditFinding"]] = relationship(back_populates="paciente")
```

### AuditFinding (Nuevo Modelo)
```python
# backend/app/models/audit.py

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.session import Base
from datetime import datetime

class AuditFinding(Base):
    """Hallazgo individual de auditoría clínica."""
    __tablename__ = "audit_findings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    
    # Identificación del hallazgo
    modulo: Mapped[str] = mapped_column(String(50), nullable=False)  # estancia, cie10, estudios, glosas
    categoria: Mapped[str] = mapped_column(String(100), nullable=True)  # estancia_prolongada, codigo_incompleto, etc.
    riesgo: Mapped[str] = mapped_column(String(10), nullable=False)  # bajo, medio, alto
    
    # Contenido
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    recomendacion: Mapped[str] = mapped_column(Text, nullable=False)
    normativa_aplicable: Mapped[str] = mapped_column(String(255), nullable=True)
    
    # Impacto
    valor_glosa_estimado: Mapped[float] = mapped_column(Float, nullable=True)
    pagina: Mapped[int] = mapped_column(Integer, nullable=True)
    
    # Auditoría
    fecha_creacion: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    estado: Mapped[str] = mapped_column(String(20), default="activo")  # activo, resuelto, descartado
    fecha_resolucion: Mapped[datetime] = mapped_column(nullable=True)
    notas_resolucion: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Relación
    paciente: Mapped["PatientCase"] = relationship(back_populates="audit_findings")
```

## Endpoints Adicionales

### GET /patients/{id}/audit
```python
@router.get("/{patient_id}/audit", response_model=AuditSummaryResponse)
async def get_patient_audit(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "auditor", "coordinador"]))
):
    """Obtiene resumen de auditoría de un paciente."""
    patient = await db.get(PatientCase, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Obtener hallazgos
    findings = await db.execute(
        select(AuditFinding)
        .where(AuditFinding.paciente_id == patient_id)
        .order_by(AuditFinding.riesgo.desc(), AuditFinding.fecha_creacion)
    )
    findings = findings.scalars().all()
    
    return AuditSummaryResponse(
        riesgo_global=patient.riesgo_auditoria,
        total_hallazgos=patient.total_hallazgos,
        exposicion_glosas=patient.exposicion_glosas,
        hallazgos=[
            AuditFindingResponse(
                id=f.id,
                modulo=f.modulo,
                categoria=f.categoria,
                riesgo=f.riesgo,
                descripcion=f.descripcion,
                recomendacion=f.recomendacion,
                valor_glosa_estimado=f.valor_glosa_estimado,
                normativa_aplicable=f.normativa_aplicable,
                estado=f.estado
            )
            for f in findings
        ]
    )
```

### PATCH /patients/{id}/audit/findings/{finding_id}
```python
@router.patch("/{patient_id}/audit/findings/{finding_id}")
async def update_audit_finding(
    patient_id: int,
    finding_id: int,
    update: AuditFindingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "auditor"]))
):
    """
    Actualiza estado de un hallazgo (marcar como resuelto, agregar notas, etc).
    """
    finding = await db.get(AuditFinding, finding_id)
    if not finding or finding.paciente_id != patient_id:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")
    
    if update.estado:
        finding.estado = update.estado
        if update.estado == "resuelto":
            finding.fecha_resolucion = datetime.utcnow()
    
    if update.notas_resolucion:
        finding.notas_resolucion = update.notas_resolucion
    
    await db.commit()
    return {"message": "Hallazgo actualizado", "finding_id": finding_id}
```

## Dashboard: Integración de Métricas

Agregar métricas de auditoría al dashboard financiero existente:

```python
# GET /dashboard/stats

{
    # ... campos existentes ...
    
    "audit_metrics": {
        "casos_riesgo_alto": 15,
        "casos_riesgo_medio": 42,
        "casos_riesgo_bajo": 103,
        "exposicion_total_glosas": 45000000.0,  # COP
        "hallazgos_por_modulo": {
            "estancia": 78,
            "cie10": 45,
            "estudios": 62,
            "glosas": 134
        },
        "top_categorias_riesgo": [
            {"categoria": "evolucion_diaria_faltante", "count": 34, "valor": 5100000},
            {"categoria": "estancia_prolongada", "count": 15, "valor": 12000000},
            {"categoria": "orden_medicamento_faltante", "count": 28, "valor": 5600000}
        ]
    }
}
```

## Testing

Ver script de prueba: `backend/test_audit_modules.py`

```bash
# Ejecutar pruebas
cd backend
python test_audit_modules.py

# Output esperado:
# - Caso IAM: 7 hallazgos, $6M COP
# - Caso Apendicitis: 1 hallazgo, $200K COP
# - Caso Neumonía: 9 hallazgos, $3.7M COP
```

## Próximos Pasos

1. ✅ Módulos de auditoría implementados
2. ⏳ Crear modelo AuditFinding en base de datos
3. ⏳ Integrar con endpoint POST /patients
4. ⏳ Agregar campos audit a PatientCase
5. ⏳ Crear endpoint GET /patients/{id}/audit
6. ⏳ Actualizar dashboard con métricas de auditoría
7. ⏳ Crear casos de prueba con PDFs reales

---

## Archivos JSON de Referencia

- `backend/app/data/cie10_estancia.json` - 40+ códigos CIE-10 con días esperados
- `backend/app/data/cie10_definiciones.json` - 10 diagnósticos con criterios clínicos
- `backend/app/data/procedimientos_cups.json` - Estudios, laboratorio, procedimientos + glosas

---

**Autor:** AudiMedIA Development Team  
**Fecha:** 2024-01-15  
**Versión:** 1.0  
