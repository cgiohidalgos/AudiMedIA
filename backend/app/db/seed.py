"""
Crea usuarios por defecto para cada rol si no existen.
Se ejecuta automáticamente al iniciar la aplicación.
"""
import uuid
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, AppRole
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

DEFAULT_USERS = [
    {
        "email": "admin@audiomedia.co",
        "full_name": "Administrador",
        "role": AppRole.admin.value,
        "password": "Admin1234",
    },
    {
        "email": "auditor@audiomedia.co",
        "full_name": "Auditor Demo",
        "role": AppRole.auditor.value,
        "password": "Auditor1234",
    },
    {
        "email": "coordinador@audiomedia.co",
        "full_name": "Coordinador Demo",
        "role": AppRole.coordinador.value,
        "password": "Coordinador1234",
    },
    {
        "email": "medico@audiomedia.co",
        "full_name": "Equipo Médico Demo",
        "role": AppRole.equipo_medico.value,
        "password": "Medico1234",
    },
]


async def seed_default_users(db: AsyncSession) -> None:
    for user_data in DEFAULT_USERS:
        result = await db.execute(
            select(User).where(User.email == user_data["email"])
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            user = User(
                id=str(uuid.uuid4()),
                email=user_data["email"],
                full_name=user_data["full_name"],
                role=user_data["role"],
                hashed_password=get_password_hash(user_data["password"]),
                is_active=True,
            )
            db.add(user)
            logger.info(f"[seed] Usuario creado: {user_data['email']} ({user_data['role']})")
        else:
            logger.info(f"[seed] Ya existe: {user_data['email']} ({existing.role})")

    await db.commit()
