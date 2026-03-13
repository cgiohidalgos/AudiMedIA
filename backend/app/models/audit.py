import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Float, Text, Boolean, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.patient import JSONColumn
import enum


class AuditModule(str, enum.Enum):
    estancia = "estancia"
    cie10 = "cie10"
    estudios = "estudios"
    glosas = "glosas"


class DocumentStatus(str, enum.Enum):
    cargando = "cargando"
    anonimizando = "anonimizando"
    extrayendo = "extrayendo"
    analizando = "analizando"
    listo = "listo"
    error = "error"


class AuditSession(Base):
    """Sesión de auditoría incremental por paciente."""
    __tablename__ = "auditoria_sesion"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_cases.id"), nullable=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    # identificación clínica (historia + cama) usada para auditoría incremental
    historia_numero: Mapped[str] = mapped_column(String(50), nullable=True)
    numero_cama: Mapped[str] = mapped_column(String(50), nullable=True)
    ultima_pagina_auditada: Mapped[int] = mapped_column(Integer, default=0)
    total_paginas_conocidas: Mapped[int] = mapped_column(Integer, default=0)
    fecha_ultima_auditoria: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.cargando.value)
    pdf_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    pdf_path: Mapped[str] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    patient = relationship("PatientCase", back_populates="audit_sessions")
    user = relationship("User", back_populates="audit_sessions")


class AuditFinding(Base):
    """Hallazgos individuales de la auditoría clínica."""
    __tablename__ = "audit_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_cases.id"), nullable=False)
    
    # Identificación del hallazgo
    modulo: Mapped[str] = mapped_column(String(20), nullable=False)  # estancia, cie10, estudios, glosas
    categoria: Mapped[str] = mapped_column(String(100), nullable=True)  # estancia_prolongada, codigo_incompleto, etc.
    riesgo: Mapped[str] = mapped_column(String(10), nullable=False)  # bajo, medio, alto
    
    # Contenido
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    recomendacion: Mapped[str] = mapped_column(Text, nullable=False)
    normativa_aplicable: Mapped[str] = mapped_column(String(255), nullable=True)
    
    # Impacto económico y ubicación
    valor_glosa_estimado: Mapped[float] = mapped_column(Float, nullable=True)  # En COP
    pagina: Mapped[int] = mapped_column(Integer, nullable=True)
    
    # Estado de resolución
    estado: Mapped[str] = mapped_column(String(20), default="activo")  # activo, resuelto, descartado
    resuelto: Mapped[bool] = mapped_column(Boolean, default=False)  # Mantener compatibilidad
    fecha_resolucion: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    notas_resolucion: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    patient = relationship("PatientCase", back_populates="findings")


class ChatMessage(Base):
    """Historial del chat con la historia clínica."""
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_cases.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    referencias: Mapped[str] = mapped_column(JSONColumn, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
