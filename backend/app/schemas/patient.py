from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List, Any
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

    model_config = {"from_attributes": True}
