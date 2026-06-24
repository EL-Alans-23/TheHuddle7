"""Rutas REST del notifications-service.

Endpoints:
    POST /notifications -> recibe un payload, simula el envío y lo registra.
    GET  /notifications -> devuelve el historial de alertas.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_shared import AuthContext, require_auth
from models import HistorialAlerta, get_session

router = APIRouter(prefix="/notifications", tags=["notifications"])


# --- Esquemas (contrato de la API) -------------------------------------------
class NotificationCreate(BaseModel):
    """Payload de una notificación a enviar."""

    # task_id lógico de la tarea relacionada (vive en tasks-service).
    task_id: int = Field(..., gt=0)
    mensaje: str = Field(..., min_length=1)


class NotificationOut(BaseModel):
    """Representación pública de una alerta registrada."""

    id: int
    task_id: int
    mensaje: str
    fecha: datetime

    model_config = {"from_attributes": True}


# --- Endpoints ----------------------------------------------------------------
@router.post("", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
def send_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_session),
    auth: AuthContext = Depends(require_auth),
) -> HistorialAlerta:
    """Simula el envío de una notificación y la guarda en el historial.

    En un entorno real aquí se integraría un proveedor (email, push, SMS) o se
    publicaría en una cola de mensajes. Para este paso, 'enviar' = registrar.
    """
    print(f"[notifications-service] Enviando alerta para task_id={payload.task_id}: {payload.mensaje}")

    alerta = HistorialAlerta(task_id=payload.task_id, mensaje=payload.mensaje)
    db.add(alerta)
    db.commit()
    db.refresh(alerta)
    return alerta


@router.get("", response_model=list[NotificationOut])
def list_notifications(db: Session = Depends(get_session)) -> list[HistorialAlerta]:
    """Devuelve el historial completo de alertas, de más reciente a más antigua."""
    return list(
        db.scalars(select(HistorialAlerta).order_by(HistorialAlerta.fecha.desc())).all()
    )
