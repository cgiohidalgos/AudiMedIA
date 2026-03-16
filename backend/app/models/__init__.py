# Import all models to ensure they are registered with SQLAlchemy
from app.models.patient import PatientCase, RiskLevel, JSONColumn
from app.models.user import User, AppRole
from app.models.audit import AuditSession, AuditFinding, AuditModule, DocumentStatus
from app.models.tarifa import TarifaConfig
from app.models.recommendation import Recommendation
from app.models.eps_contrato import EPSContrato
from app.models.servicio_hospitalario import ServicioHospitalario
from app.models.notification import Notification

__all__ = [
    "PatientCase",
    "RiskLevel",
    "JSONColumn",
    "User",
    "AppRole",
    "AuditSession",
    "AuditFinding",
    "AuditModule",
    "DocumentStatus",
    "TarifaConfig",
    "Recommendation",
    "EPSContrato",
    "ServicioHospitalario",
    "Notification",
]
