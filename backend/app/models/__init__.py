# Import all models to ensure they are registered with SQLAlchemy
from app.models.patient import PatientCase, RiskLevel, JSONColumn
from app.models.user import User, AppRole
from app.models.audit import AuditSession, AuditFinding, AuditModule, DocumentStatus
from app.models.tarifa import TarifaConfig
from app.models.recommendation import Recommendation

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
]
