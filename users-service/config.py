"""Configuración del users-service.

Carga las variables de entorno desde el `.env` centralizado en la raíz del
proyecto. Las credenciales NUNCA se hardcodean: si una variable obligatoria
falta, el servicio falla rápido al arrancar (fail-fast).
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# El `.env` vive en la raíz del proyecto, dos niveles por encima de este archivo.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _required(key: str) -> str:
    """Devuelve el valor de una variable obligatoria o lanza un error claro."""
    value = os.getenv(key)
    if value is None or value == "":
        raise RuntimeError(
            f"Falta la variable de entorno obligatoria '{key}'. "
            f"Revisa el archivo .env en la raíz del proyecto."
        )
    return value


class Settings:
    """Configuración tipada del servicio de usuarios."""

    SERVICE_NAME: str = "users-service"

    # Servidor
    PORT: int = int(os.getenv("USERS_SERVICE_PORT", "5001"))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Base de datos independiente de este microservicio
    DATABASE_URL: str = _required("USERS_DATABASE_URL")

    # Seguridad JWT compartida (users-service es quien FIRMA los tokens)
    JWT_SECRET: str = _required("JWT_SECRET")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "120"))


@lru_cache
def get_settings() -> Settings:
    """Devuelve una única instancia de Settings (cacheada)."""
    return Settings()
