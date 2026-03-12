from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List, Any, Dict
from app.models.patient import RiskLevel


class PatientCaseRead(BaseModel):
    id: str
    label: str
    cama: Optional[str]
    edad: Optional[int]
    sexo: Optional[str]
    diagnostico_principal: Optional[str]
    codigo_cie10: Optional[str]
    diagnosticos_secundarios: List[Any] = []
    fecha_ingreso: Optional[date]
    dias_hospitalizacion: Optional[int]
    dias_esperados: Optional[str]
    riesgo: str
    medicamentos: List[Any] = []
    antecedentes: dict = {}
    estudios_solicitados: List[Any] = []
    procedimientos: List[Any] = []
    evoluciones: List[Any] = []
    created_at: datetime
    
    # Campos de auditoría
    riesgo_auditoria: Optional[str] = None
    total_hallazgos: int = 0
    exposicion_glosas: float = 0.0
    audit_status: str = "pending"

    model_config = {"from_attributes": True}


class PatientCaseSummary(BaseModel):
    id: str
    label: str
    cama: Optional[str]
    diagnostico_principal: Optional[str]
    codigo_cie10: Optional[str]
    dias_hospitalizacion: Optional[int]
    dias_esperados: Optional[str]
    riesgo: str
    
    # Agregar campos de auditoría al resumen
    riesgo_auditoria: Optional[str] = None
    total_hallazgos: int = 0
    exposicion_glosas: float = 0.0

    model_config = {"from_attributes": True}


# ============================================================================
# SCHEMAS DE AUDITORÍA
# ============================================================================

class AuditFindingRead(BaseModel):
    """Schema para leer un hallazgo de auditoría."""
    id: str
    patient_id: str
    modulo: str
    categoria: Optional[str] = None
    riesgo: str
    descripcion: str
    recomendacion: str
    normativa_aplicable: Optional[str] = None
    valor_glosa_estimado: Optional[float] = None
    pagina: Optional[int] = None
    estado: str = "activo"
    resuelto: bool = False
    fecha_resolucion: Optional[datetime] = None
    notas_resolucion: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AuditFindingUpdate(BaseModel):
    """Schema para actualizar un hallazgo."""
    estado: Optional[str] = None  # activo, resuelto, descartado
    notas_resolucion: Optional[str] = None


class AuditSummaryResponse(BaseModel):
    """Resumen ejecutivo de auditoría de un paciente."""
    riesgo_global: str
    total_hallazgos: int
    exposicion_glosas: float
    hallazgos_por_riesgo: Dict[str, int]
    hallazgos_por_modulo: Dict[str, int]
    hallazgos: List[AuditFindingRead]
    recomendacion_general: str
    paciente: Dict[str, Any]


class PatientAuditResponse(BaseModel):
    """Respuesta al crear/actualizar paciente con auditoría."""
    id: str
    label: str
    diagnostico_principal: Optional[str]
    codigo_cie10: Optional[str]
    riesgo_auditoria: Optional[str]
    total_hallazgos: int
    exposicion_glosas: float
    hallazgos_criticos: List[Dict[str, Any]]
    recomendacion_general: str
    audit_status: str

    model_config = {"from_attributes": True}

