import uuid
from datetime import date, datetime
from sqlalchemy import String, DateTime, Float, Date, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class EPSContrato(Base):
    """Contratos con EPS para configuración de tarifas especiales"""
    __tablename__ = "eps_contratos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre_eps: Mapped[str] = mapped_column(String(200), nullable=False)
    tarifa_especial: Mapped[float | None] = mapped_column(Float, nullable=True)
    vigencia_desde: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
