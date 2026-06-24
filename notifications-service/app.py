"""notifications-service — punto de entrada de la aplicación FastAPI.

Paso 2: al arrancar espera a su PostgreSQL y crea las tablas. El envío de
notificaciones y la integración con colas se añadirán en pasos posteriores.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import get_settings
from models import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Inicializa la base de datos antes de aceptar tráfico."""
    init_db()
    yield


app = FastAPI(
    title="Notifications Service",
    description="Envío y registro de notificaciones del Gestor de Tareas.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["health"])
def health_check() -> dict:
    """Comprobación de estado del servicio."""
    return {
        "service": settings.SERVICE_NAME,
        "status": "ok",
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=settings.PORT, reload=True)
