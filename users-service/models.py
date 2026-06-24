"""Capa de datos del users-service (Database per Service).

Define el modelo `Usuario`, el engine de SQLAlchemy hacia su PostgreSQL
INDEPENDIENTE y la rutina de inicialización que espera a que la base de datos
esté lista antes de crear las tablas.
"""

import time

from sqlalchemy import Integer, String, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from config import get_settings

settings = get_settings()

# Engine propio de este microservicio. `pool_pre_ping` descarta conexiones
# muertas del pool de forma transparente.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base declarativa exclusiva del esquema de usuarios."""


class Usuario(Base):
    """Tabla 'usuarios': credenciales y rol de cada usuario."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    # Almacena SIEMPRE el hash de la contraseña, nunca el texto plano.
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(String(30), nullable=False, default="user")


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
