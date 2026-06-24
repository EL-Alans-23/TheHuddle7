# Gestor de Tareas — Ecosistema de Microservicios

Ecosistema de microservicios en Python (FastAPI) para la gestión de tareas.

## Arquitectura

| Servicio                 | Puerto | Base de datos       | Responsabilidad                          |
|--------------------------|--------|---------------------|------------------------------------------|
| `users-service`          | 5001   | `users_db`          | Registro, autenticación y emisión de JWT |
| `tasks-service`          | 5002   | `tasks_db`          | CRUD de tareas, asignaciones, estados    |
| `notifications-service`  | 5003   | `notifications_db`  | Envío y registro de notificaciones       |

Cada servicio es **independiente**: tiene su propia base de datos y su propio
ciclo de despliegue. El secreto `JWT_SECRET` es el único contrato de seguridad
compartido — `users-service` firma los tokens y los demás servicios los validan.

## Estructura del proyecto

```
TheHuddle7/
├── .env                      # Variables de entorno (NO versionado)
├── .env.example              # Plantilla de variables
├── .gitignore
├── README.md
├── users-service/
│   ├── app.py
│   ├── config.py
│   └── requirements.txt
├── tasks-service/
│   ├── app.py
│   ├── config.py
│   └── requirements.txt
└── notifications-service/
    ├── app.py
    ├── config.py
    └── requirements.txt
```

## Puesta en marcha (desarrollo)

```bash
# 1. Configurar variables de entorno
cp .env.example .env   # y rellenar los valores

# 2. Por cada servicio (ejemplo: users-service)
cd users-service
python -m venv .venv && source .venv/bin/activate   # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --port 5001
```

> **Paso 1 actual:** solo estructura y configuración base. La lógica de base de
> datos y los endpoints se añadirán en pasos posteriores.
