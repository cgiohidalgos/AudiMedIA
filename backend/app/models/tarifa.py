import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Float, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class TarifaConfig(Base):
    """Configuración de tarifas hospitalarias para cálculos financieros"""
    __tablename__ = "tarifas_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Tarifas por día de hospitalización
    tarifa_dia_hospitalizacion: Mapped[float] = mapped_column(Float, default=350000.0, nullable=False)
    tarifa_dia_uci: Mapped[float] = mapped_column(Float, default=1200000.0, nullable=False)
    
    # Porcentaje promedio de glosas aceptadas históricamente
    porcentaje_glosas_historico: Mapped[float] = mapped_column(Float, default=15.0, nullable=False)
    
    # Valor promedio por glosa de evolución faltante (15% valor día)
    glosa_evolucion_porcentaje: Mapped[float] = mapped_column(Float, default=15.0, nullable=False)
    
    # Valor promedio estimado por glosa evitada
    valor_promedio_glosa: Mapped[float] = mapped_column(Float, default=850000.0, nullable=False)
    
    # Institución
    institucion_nombre: Mapped[str] = mapped_column(String(200), default="Hospital General", nullable=False)
    
    # Metadatos
    activo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
