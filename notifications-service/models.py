"""Capa de datos del notifications-service (Database per Service).

Define el modelo `HistorialAlerta`, el engine de SQLAlchemy hacia su PostgreSQL
INDEPENDIENTE y la rutina de inicialización que espera a que la base de datos
esté lista antes de crear las tablas.

Nota de arquitectura: `task_id` referencia una tarea que vive en OTRO servicio
(tasks-service), por lo que NO se modela como ForeignKey real entre bases de
datos distintas.
"""

import time
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from config import get_settings

settings = get_settings()

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base declarativa exclusiva del esquema de notificaciones."""


class HistorialAlerta(Base):
    """Tabla 'historial_alertas': registro de notificaciones enviadas."""

    __tablename__ = "historial_alertas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # ID lógico de la tarea relacionada (vive en tasks-service, sin FK cruzada).
    task_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


def wait_for_db(max_retries: int = 30, delay_seconds: int = 2) -> None:
    """Espera a que PostgreSQL acepte conexiones antes de arrancar.

    En un ecosistema de microservicios la base de datos puede tardar en estar
    lista (p. ej. al levantar todo con docker-compose). Reintentamos con un
    bucle `while True` y `time.sleep` hasta conseguir conexión o agotar los
    intentos.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            with engine.connect():
                print(f"[{settings.SERVICE_NAME}] Conexión con PostgreSQL establecida.")
                return
        except OperationalError as exc:
            if attempt >= max_retries:
                raise RuntimeError(
                    f"[{settings.SERVICE_NAME}] No se pudo conectar a PostgreSQL "
                    f"tras {max_retries} intentos."
                ) from exc
            print(
                f"[{settings.SERVICE_NAME}] PostgreSQL no disponible "
                f"(intento {attempt}/{max_retries}). Reintentando en {delay_seconds}s..."
            )
            time.sleep(delay_seconds)


def init_db() -> None:
    """Espera a la BD y crea las tablas si no existen."""
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    print(f"[{settings.SERVICE_NAME}] Esquema verificado (tablas creadas si no existían).")


def get_session():
    """Dependencia para obtener una sesión de BD por petición."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
