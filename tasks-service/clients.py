"""Clientes HTTP hacia otros microservicios (comunicación entre servicios).

Aquí vive la lógica de RESILIENCIA: reintentos acotados y manejo de fallos para
que la caída de un servicio dependiente NO tumbe a tasks-service.
"""

import time

import httpx

from config import get_settings

settings = get_settings()

# Política de reintentos para llamadas salientes.
MAX_RETRIES = 3
BACKOFF_SECONDS = 1.0  # espera base; crece linealmente con cada intento
REQUEST_TIMEOUT = 5.0  # segundos máximos por intento


def notify_task_completed(
    task_id: int, mensaje: str, auth_token: str | None = None
) -> bool:
    """Avisa al notifications-service de que una tarea se completó.

    Implementa un patrón de Retry: hasta MAX_RETRIES intentos ante fallos de red
    o respuestas 5xx. Devuelve:
        True  -> la notificación se entregó correctamente.
        False -> se agotaron los reintentos (el llamador decide cómo degradar).

    Token Forwarding: si se recibe `auth_token` (el JWT del cliente original),
    se reenvía en el header 'Authorization' para que el notifications-service,
    que también está protegido, acepte la petición.

    NUNCA propaga la excepción: la resiliencia consiste precisamente en que el
    fallo de un servicio dependiente no haga fallar a tasks-service.
    """
    url = f"{settings.NOTIFICATIONS_SERVICE_URL}/notifications"
    payload = {"task_id": task_id, "mensaje": mensaje}
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = httpx.post(
                url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT
            )

            # Un 5xx es un fallo del lado del servidor: merece reintento.
            if response.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"Respuesta {response.status_code} del notifications-service",
                    request=response.request,
                    response=response,
                )

            response.raise_for_status()  # 4xx -> error no recuperable, sale del bucle
            print(
                f"[tasks-service] Notificación entregada para task_id={task_id} "
                f"(intento {attempt}/{MAX_RETRIES})."
            )
            return True

        except httpx.HTTPStatusError as exc:
            # 4xx: nuestro payload/petición está mal; reintentar no ayuda.
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code is not None and 400 <= status_code < 500:
                print(
                    f"[tasks-service] ERROR no recuperable ({status_code}) al notificar "
                    f"task_id={task_id}: {exc}. No se reintenta."
                )
                return False
            _log_retry(task_id, attempt, exc)

        except (httpx.TransportError, httpx.TimeoutException) as exc:
            # Fallos de red/timeout: candidatos a reintento.
            _log_retry(task_id, attempt, exc)

        # Backoff antes del siguiente intento (no tras el último).
        if attempt < MAX_RETRIES:
            time.sleep(BACKOFF_SECONDS * attempt)

    # Llanto controlado: agotamos los reintentos sin éxito.
    print(
        f"[tasks-service] FALLO al notificar task_id={task_id} tras {MAX_RETRIES} "
        f"intentos. La tarea quedó completada localmente; notificación diferida."
    )
    return False


def _log_retry(task_id: int, attempt: int, exc: Exception) -> None:
    """Registra un intento fallido de notificación."""
    print(
        f"[tasks-service] Fallo al notificar task_id={task_id} "
        f"(intento {attempt}/{MAX_RETRIES}): {exc!r}. Reintentando..."
    )
