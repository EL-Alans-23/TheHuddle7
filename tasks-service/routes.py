"""Rutas REST del tasks-service.

Endpoints:
    POST /tasks               -> crea una tarea.
    GET  /tasks               -> lista las tareas.
    PUT  /tasks/{id}/complete -> marca una tarea como completada.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_shared import AuthContext, require_auth
from clients import notify_task_completed
from models import Tarea, get_session

router = APIRouter(prefix="/tasks", tags=["tasks"])


# --- Esquemas (contrato de la API) -------------------------------------------
class TaskCreate(BaseModel):
    """Datos de entrada para crear una tarea."""

    titulo: str = Field(..., min_length=1, max_length=200)
    # user_id lógico del propietario (vive en users-service).
    user_id: int = Field(..., gt=0)


class TaskOut(BaseModel):
    """Representación pública de una tarea."""

    id: int
    titulo: str
    estado: str
    user_id: int

    model_config = {"from_attributes": True}


# --- Endpoints ----------------------------------------------------------------
@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_session),
    auth: AuthContext = Depends(require_auth),
) -> Tarea:
    """Crea una nueva tarea en estado 'pendiente'. Requiere autenticación."""
    tarea = Tarea(titulo=payload.titulo, user_id=payload.user_id, estado="pendiente")
    db.add(tarea)
    db.commit()
    db.refresh(tarea)
    return tarea


@router.get("", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_session)) -> list[Tarea]:
    """Devuelve todas las tareas."""
    return list(db.scalars(select(Tarea).order_by(Tarea.id)).all())


@router.put("/{task_id}/complete", response_model=TaskOut)
def complete_task(
    task_id: int,
    response: Response,
    db: Session = Depends(get_session),
    auth: AuthContext = Depends(require_auth),
) -> Tarea:
    """Marca una tarea como completada y notifica al notifications-service.

    Comportamiento resiliente:
      - La fuente de verdad es la BD local: primero se persiste 'completada'.
      - Después se intenta notificar (con reintentos en el cliente HTTP).
      - Si la notificación se entrega    -> 200 OK.
      - Si la notificación falla del todo -> 202 Accepted (tarea completada
        localmente, notificación diferida/fallida). La operación principal NO
        se revierte ni falla por culpa de un servicio dependiente.
    """
    tarea = db.get(Tarea, task_id)
    if tarea is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada.",
        )

    # 1) Persistimos el cambio de estado (operación principal, transaccional).
    tarea.estado = "completada"
    db.commit()
    db.refresh(tarea)

    # 2) Efecto secundario tolerante a fallos: avisar a notifications-service.
    notified = notify_task_completed(
        task_id=tarea.id,
        mensaje=f"La tarea '{tarea.titulo}' se ha marcado como completada.",
        auth_token=auth.token,  # Token Forwarding: reenviamos el JWT del cliente
    )

    if not notified:
        # La tarea está completada, pero la notificación quedó diferida.
        response.status_code = status.HTTP_202_ACCEPTED

    return tarea
