"""Módulo COMPARTIDO de autenticación JWT.

⚠️  Este archivo se copia TAL CUAL en cada microservicio. No depende del
`config.py` de ningún servicio en concreto: lee el `JWT_SECRET` y el algoritmo
directamente del `.env` centralizado, de modo que todos los servicios validan
los tokens con el MISMO secreto que usó users-service para firmarlos.

Uso (FastAPI):

    from auth_shared import require_auth, AuthContext

    @router.post("/algo")
    def endpoint(auth: AuthContext = Depends(require_auth)):
        ...  # auth.payload tiene los claims; auth.token es el JWT crudo
"""

import os
from dataclasses import dataclass
from pathlib import Path

import jwt
from dotenv import load_dotenv
from fastapi import Header, HTTPException, status

# El `.env` vive en la raíz del proyecto, un nivel por encima de cada servicio.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

if not JWT_SECRET:
    raise RuntimeError(
        "auth_shared: falta JWT_SECRET en el entorno. Revisa el .env centralizado."
    )


@dataclass
class AuthContext:
    """Identidad autenticada de la petición actual."""

    token: str  # JWT crudo, útil para reenviarlo a otros servicios (forwarding)
    payload: dict  # claims decodificados (sub, username, rol, exp, ...)


def decode_token(token: str) -> dict:
    """Verifica la firma y la expiración del token; devuelve sus claims."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def require_auth(authorization: str | None = Header(default=None)) -> AuthContext:
    """Dependencia que exige un 'Authorization: Bearer <token>' válido.

    Lanza 401 si falta el header, el formato es incorrecto, o el token está
    expirado o tiene una firma inválida.
    """
    unauthorized = lambda detail: HTTPException(  # noqa: E731
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization:
        raise unauthorized("Falta el header 'Authorization'.")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise unauthorized("Formato inválido. Use 'Authorization: Bearer <token>'.")

    token = parts[1]
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise unauthorized("Token expirado.") from exc
    except jwt.InvalidTokenError as exc:
        raise unauthorized("Token inválido.") from exc

    return AuthContext(token=token, payload=payload)
