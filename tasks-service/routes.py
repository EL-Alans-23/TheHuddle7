"""Rutas REST del tasks-service.

Endpoints:
    POST /tasks               -> crea una tarea.
    GET  /tasks               -> lista las tareas.
    PUT  /tasks/{id}/complete -> marca una tarea como completada.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

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
def create_task(payload: TaskCreate, db: Session = Depends(get_session)) -> Tarea:
    """Crea una nueva tarea en estado 'pendiente'."""
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
def complete_task(task_id: int, db: Session = Depends(get_session)) -> Tarea:
    """Marca una tarea como completada."""
    tarea = db.get(Tarea, task_id)
    if tarea is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada.",
        )
    tarea.estado = "completada"
    db.commit()
    db.refresh(tarea)
    return tarea
