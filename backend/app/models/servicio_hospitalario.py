import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class ServicioHospitalario(Base):
    """Servicios hospitalarios para configuración de notificaciones"""
    __tablename__ = "servicios_hospitalarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    medico_jefe: Mapped[str | None] = mapped_column(String(200), nullable=True)
    correo_notificaciones: Mapped[str | None] = mapped_column(String(200), nullable=True)
    activo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
