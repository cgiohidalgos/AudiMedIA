import uuid
import json
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Integer, Text, Boolean, TypeDecorator, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
import enum


class RiskLevel(str, enum.Enum):
    bajo = "bajo"
    medio = "medio"
    alto = "alto"


class JSONColumn(TypeDecorator):
    """Tipo personalizado que serializa JSON en SQLite como TEXT."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)


class PatientCase(Base):
    __tablename__ = "patient_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    label: Mapped[str] = mapped_column(String(20), nullable=False)
    cama: Mapped[str] = mapped_column(String(50), nullable=True)
    edad: Mapped[int] = mapped_column(Integer, nullable=True)
    sexo: Mapped[str] = mapped_column(String(10), nullable=True)

    diagnostico_principal: Mapped[str] = mapped_column(Text, nullable=True)
    codigo_cie10: Mapped[str] = mapped_column(String(20), nullable=True)
    diagnosticos_secundarios: Mapped[str] = mapped_column(JSONColumn, default=list)

    fecha_ingreso: Mapped[date] = mapped_column(Date, nullable=True)
    dias_hospitalizacion: Mapped[int] = mapped_column(Integer, nullable=True)
    dias_esperados: Mapped[str] = mapped_column(String(50), nullable=True)

    riesgo: Mapped[str] = mapped_column(String(10), default=RiskLevel.bajo.value)

    medicamentos: Mapped[str] = mapped_column(JSONColumn, default=list)
    antecedentes: Mapped[str] = mapped_column(JSONColumn, default=dict)
    estudios_solicitados: Mapped[str] = mapped_column(JSONColumn, default=list)
    procedimientos: Mapped[str] = mapped_column(JSONColumn, default=list)
    evoluciones: Mapped[str] = mapped_column(JSONColumn, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    audit_sessions = relationship("AuditSession", back_populates="patient", lazy="select")
    findings = relationship("AuditFinding", back_populates="patient", lazy="select", cascade="all, delete-orphan")
