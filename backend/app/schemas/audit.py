from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.models.audit import AuditModule, DocumentStatus
from app.models.patient import RiskLevel


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
    heredado: bool = False
    fecha_resolucion: Optional[datetime] = None
    notas_resolucion: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AuditFindingUpdate(BaseModel):
    """Schema para actualizar un hallazgo."""
    estado: Optional[str] = None  # activo, resuelto, descartado
    notas_resolucion: Optional[str] = None
    resuelto: Optional[bool] = None  # Mantener compatibilidad con código legacy


class AuditSessionRead(BaseModel):
    id: str
    patient_id: Optional[str]
    historia_numero: Optional[str] = None
    numero_cama: Optional[str]
    ultima_pagina_auditada: int
    total_paginas_conocidas: int
    fecha_ultima_auditoria: Optional[datetime]
    status: str

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    session_id: str
    status: str
    message: str


class ChatRequest(BaseModel):
    patient_id: str
    question: str
    multi_historia: bool = False


class ChatReference(BaseModel):
    pagina: int
    fragmento: str


class ChatResponse(BaseModel):
    answer: str
    referencias: List[ChatReference] = []
    patient_ids: List[str] = []


class AuditSessionStatus(BaseModel):
    """Estado enriquecido de la sesión de auditoría para el frontend."""
    id: str
    patient_id: Optional[str] = None
    ultima_pagina_auditada: int
    total_paginas_conocidas: int
    porcentaje_completado: float
    fecha_ultima_auditoria: Optional[datetime] = None
    status: str
    tiene_progreso_previo: bool


class DashboardMetrics(BaseModel):
    historias_auditadas: int
    glosas_evitadas: int
    ahorro_estimado: float
    estancias_prolongadas: int
    riesgo_alto: int
    pendientes_resueltos: int
    tiempo_promedio_auditoria_min: float


class TarifaConfigRead(BaseModel):
    id: str
    tarifa_dia_hospitalizacion: float
    tarifa_dia_uci: float
    porcentaje_glosas_historico: float
    glosa_evolucion_porcentaje: float
    valor_promedio_glosa: float
    institucion_nombre: str
    activo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TarifaConfigUpdate(BaseModel):
    tarifa_dia_hospitalizacion: Optional[float] = None
    tarifa_dia_uci: Optional[float] = None
    porcentaje_glosas_historico: Optional[float] = None
    glosa_evolucion_porcentaje: Optional[float] = None
    valor_promedio_glosa: Optional[float] = None
    institucion_nombre: Optional[str] = None


class DashboardFinanciero(BaseModel):
    """Dashboard financiero avanzado con múltiples métricas"""
    
    # Período
    periodo_tipo: str  # 'dia', 'semana', 'mes', 'anio'
    fecha_inicio: datetime
    fecha_fin: datetime
    
    # KPIs principales
    glosas_evitadas_mes_cop: float
    glosas_evitadas_anio_cop: float
    estancias_prolongadas_dias: int
    ahorro_estancia_mes_cop: float
    
    # Métricas operacionales
    historias_auditadas_periodo: int
    tasa_riesgo_alto_porcentaje: float
    pendientes_resueltos_porcentaje: float
    tiempo_promedio_auditoria_min: float
    
    # Desglose financiero
    ahorro_por_estancia: float
    ahorro_por_procedimientos: float
    ahorro_por_medicamentos: float
    ahorro_por_evoluciones: float
    
    # ROI y proyecciones
    roi_periodo: float
    proyeccion_ahorro_anual: float


class MetricaTemporal(BaseModel):
    """Métrica para series temporales (gráficos)"""
    fecha: datetime
    valor: float
    etiqueta: str


class DashboardGraficos(BaseModel):
    """Datos para gráficos del dashboard"""
    
    # Tendencia de glosas evitadas
    glosas_tiempo: List[MetricaTemporal]
    
    # Ahorro acumulado
    ahorro_acumulado: List[MetricaTemporal]
    
    # Distribución por módulo
    hallazgos_por_modulo: dict[str, int]
    
    # Comparativo por servicio
    ahorro_por_servicio: dict[str, float]


class ExportRequest(BaseModel):
    """Request para exportación de reportes"""
    formato: str  # 'pdf' o 'excel'
    periodo_inicio: datetime
    periodo_fin: datetime
    incluir_graficos: bool = True
    incluir_detalle_pacientes: bool = False
