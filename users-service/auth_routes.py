"""Rutas de autenticación del users-service.

users-service es el ÚNICO servicio que FIRMA tokens. Aquí se verifica la
contraseña y se emite un JWT firmado con el `JWT_SECRET` del entorno.
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import get_settings
from models import Usuario, get_session
from routes import pwd_context

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])


# --- Esquemas -----------------------------------------------------------------
class LoginRequest(BaseModel):
    """Credenciales de inicio de sesión."""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    """Token emitido tras un login correcto."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos hasta la expiración


# --- Endpoint -----------------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_session)) -> TokenResponse:
    """Verifica credenciales y devuelve un JWT firmado (expira en 2 horas)."""
    usuario = db.scalar(select(Usuario).where(Usuario.username == payload.username))

    # Mismo mensaje para usuario inexistente o contraseña incorrecta: no se
    # revela cuál de los dos falló (evita enumeración de usuarios).
    if usuario is None or not pwd_context.verify(payload.password, usuario.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )

    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    claims = {
        "sub": str(usuario.id),
        "username": usuario.username,
        "rol": usuario.rol,
        "iat": now,
        "exp": now + expires_delta,
    }

    token = jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return TokenResponse(
        access_token=token,
        expires_in=int(expires_delta.total_seconds()),
    )
