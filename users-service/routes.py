"""Rutas REST del users-service.

Endpoints:
    POST /users  -> registra un usuario (la contraseña se guarda hasheada).
    GET  /users  -> lista los usuarios (sin exponer la contraseña).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Usuario, get_session

router = APIRouter(prefix="/users", tags=["users"])

# Contexto de hashing. NUNCA se almacena la contraseña en texto plano.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Esquemas (contrato de la API) -------------------------------------------
class UserCreate(BaseModel):
    """Datos de entrada para registrar un usuario."""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    rol: str = Field(default="user", max_length=30)


class UserOut(BaseModel):
    """Representación pública de un usuario (sin contraseña)."""

    id: int
    username: str
    rol: str

    model_config = {"from_attributes": True}


# --- Endpoints ----------------------------------------------------------------
@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_session)) -> Usuario:
    """Registra un nuevo usuario con la contraseña hasheada."""
    exists = db.scalar(select(Usuario).where(Usuario.username == payload.username))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El username ya está registrado.",
        )

    usuario = Usuario(
        username=payload.username,
        password=pwd_context.hash(payload.password),
        rol=payload.rol,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_session)) -> list[Usuario]:
    """Devuelve todos los usuarios registrados."""
    return list(db.scalars(select(Usuario).order_by(Usuario.id)).all())
