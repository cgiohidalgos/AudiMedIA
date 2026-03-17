import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Float, Text, Boolean, func, ForeignKey, Index
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
    subido = "subido"          # Etapa 1 completa: PDF guardado, sin procesar
    extrayendo = "extrayendo"  # Etapa 2 en curso: extrayendo texto
    extraido = "extraido"      # Etapa 2 completa: chunks guardados en BD
    anonimizando = "anonimizando"
    analizando = "analizando"  # Etapa 3 en curso: IA procesando
    listo = "listo"
    error = "error"


class AuditSession(Base):
    """Sesión de auditoría incremental por paciente."""
    __tablename__ = "auditoria_sesion"
    __table_args__ = (
        Index("ix_auditoria_sesion_patient_id", "patient_id"),
        Index("ix_auditoria_sesion_user_id", "user_id"),
        Index("ix_auditoria_sesion_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_cases.id"), nullable=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    # identificación clínica (historia + cama) usada para auditoría incremental
    historia_numero: Mapped[str] = mapped_column(String(50), nullable=True)
    numero_cama: Mapped[str] = mapped_column(String(50), nullable=True)
    ultima_pagina_auditada: Mapped[int] = mapped_column(Integer, default=0)
    total_paginas_conocidas: Mapped[int] = mapped_column(Integer, default=0)
    ai_chunks_done: Mapped[int] = mapped_column(Integer, default=0)
    ai_chunks_total: Mapped[int] = mapped_column(Integer, default=0)
    clinical_data_partial: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    fecha_ultima_auditoria: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.cargando.value)
    pdf_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    pdf_path: Mapped[str] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    patient = relationship("PatientCase", back_populates="audit_sessions")
    user = relationship("User", back_populates="audit_sessions")
    chunks = relationship("DocumentChunk", back_populates="session", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Fragmento de texto extraído de un PDF. Unidad base para RAG."""
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_session_id", "session_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("auditoria_sesion.id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    is_ocr: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session = relationship("AuditSession", back_populates="chunks")


class AuditFinding(Base):
    """Hallazgos individuales de la auditoría clínica."""
    __tablename__ = "audit_findings"
    __table_args__ = (
        Index("ix_audit_findings_patient_id", "patient_id"),
        Index("ix_audit_findings_patient_estado", "patient_id", "estado"),
    )

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
    heredado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_resolucion: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    notas_resolucion: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    patient = relationship("PatientCase", back_populates="findings")


class ChatMessage(Base):
    """Historial del chat con la historia clínica."""
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_patient_id", "patient_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_cases.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    referencias: Mapped[str] = mapped_column(JSONColumn, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
