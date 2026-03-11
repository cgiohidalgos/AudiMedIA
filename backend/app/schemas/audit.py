from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.models.audit import AuditModule, DocumentStatus
from app.models.patient import RiskLevel


class AuditFindingRead(BaseModel):
    id: str
    modulo: str
    descripcion: str
    riesgo: str
    pagina: Optional[int]
    resuelto: bool
    recomendacion: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditFindingUpdate(BaseModel):
    resuelto: bool


class AuditSessionRead(BaseModel):
    id: str
    patient_id: Optional[str]
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


class DashboardMetrics(BaseModel):
    historias_auditadas: int
    glosas_evitadas: int
    ahorro_estimado: float
    estancias_prolongadas: int
    riesgo_alto: int
    pendientes_resueltos: int
    tiempo_promedio_auditoria_min: float
