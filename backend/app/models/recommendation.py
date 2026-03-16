import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class Recommendation(Base):
    """Recomendación estructurada derivada de hallazgos de auditoría."""
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    patient_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patient_cases.id"), nullable=False, index=True
    )
    # Hallazgo de origen (opcional — algunas son institucionales)
    finding_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("audit_findings.id"), nullable=True
    )

    # Clasificación
    tipo: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # documentacion | estancia | estudios | complicacion | institucional
    categoria: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # mejora | optimizacion | alerta | critica
    prioridad: Mapped[str] = mapped_column(
        String(10), nullable=False, default="media"
    )  # baja | media | alta

    # Contenido
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    detalle: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Estado de gestión
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pendiente"
    )  # pendiente | implementada | descartada
    notas_resolucion: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    fecha_resolucion: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relaciones
    patient = relationship("PatientCase", back_populates="recommendations")
