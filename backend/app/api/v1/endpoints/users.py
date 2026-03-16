from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.db.session import get_db
from app.models.user import User, AppRole
from app.schemas.user import UserRead, UserCreate, UserUpdate, UserResetPassword
from app.api.v1.deps import get_current_user, require_role
from app.core.security import get_password_hash

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/", response_model=List[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.admin)),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=UserRead, status_code=201)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.admin)),
):
    """Crear nuevo usuario (solo admin)"""
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="La contraseña debe tener mínimo 8 caracteres")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role.value,
        hashed_password=get_password_hash(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.admin)),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(AppRole.admin)),
):
    """Eliminar usuario (solo admin). No se puede auto-eliminar."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    await db.delete(user)
    await db.commit()


@router.post("/{user_id}/reset-password", response_model=UserRead)
async def reset_password(
    user_id: str,
    payload: UserResetPassword,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(AppRole.admin)),
):
    """Resetear contraseña de un usuario (solo admin)"""
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=422, detail="La contraseña debe tener mínimo 8 caracteres")
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.hashed_password = get_password_hash(payload.new_password)
    await db.commit()
    await db.refresh(user)
    return user
