from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List, Any, Dict
from app.models.patient import RiskLevel

# Importar schemas de auditoría (evitar duplicación)
from app.schemas.audit import AuditFindingRead, AuditFindingUpdate


class PatientCaseRead(BaseModel):
    id: str
    label: str
    historia_numero: Optional[str]
    cama: Optional[str]
    edad: Optional[int]
    sexo: Optional[str]
    diagnostico_principal: Optional[str]
    codigo_cie10: Optional[str]
    diagnosticos_secundarios: List[Any] = []
    fecha_ingreso: Optional[date]
    fecha_egreso: Optional[date]
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


# NOTA: AuditFindingRead/Update ahora se importan desde schemas.audit para evitar duplicación

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


class PatientControlBoard(BaseModel):
    """Schema para el cuadro de control inteligente."""
    id: str
    cama: Optional[str]
    historia: str  # label anonimizado
    diagnostico: str  # "código_cie10 - descripción"
    codigo_cie10: Optional[str] = None
    fecha_ingreso: Optional[date] = None
    dias_hospitalizacion: int
    dias_esperados: str
    estudios_pendientes: List[str]  # Lista de estudios sin reporte
    riesgo_glosa: str  # ALTO / MEDIO / BAJO
    total_hallazgos: int
    exposicion_glosas: float
    audit_status: str  # pending / processing / completed
    fecha_ultima_auditoria: Optional[datetime] = None

    model_config = {"from_attributes": True}

