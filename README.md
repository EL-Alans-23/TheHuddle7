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
├── docker-compose.yml        # Orquesta 3 BD + 3 servicios en red privada
├── README.md
├── users-service/
│   ├── Dockerfile
│   ├── app.py · config.py · models.py · routes.py
│   ├── auth_routes.py        # POST /auth/login (emite JWT)
│   ├── auth_shared.py        # verificación JWT (módulo compartido)
│   └── requirements.txt
├── tasks-service/
│   ├── Dockerfile
│   ├── app.py · config.py · models.py · routes.py
│   ├── clients.py            # cliente HTTP resiliente + token forwarding
│   ├── auth_shared.py
│   └── requirements.txt
└── notifications-service/
    ├── Dockerfile
    ├── app.py · config.py · models.py · routes.py
    ├── auth_shared.py
    └── requirements.txt
```

## Puesta en marcha con Docker (recomendado)

Levanta las 3 bases de datos y los 3 servicios con un solo comando:

```bash
cp .env.example .env        # y rellenar JWT_SECRET (genéralo aleatorio)
docker compose up --build
```

Servicios disponibles en `localhost:5001` / `5002` / `5003`. Docs OpenAPI en
`/docs` de cada uno (p. ej. http://localhost:5001/docs).

## Puesta en marcha manual (sin Docker)

```bash
cp .env.example .env        # apuntar las *_DATABASE_URL a tus PostgreSQL locales

# Por cada servicio (ejemplo: users-service)
cd users-service
python -m venv .venv && source .venv/bin/activate   # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Flujo de uso (end-to-end)

```bash
# 1. Registrar un usuario
curl -X POST localhost:5001/users -H "Content-Type: application/json" \
  -d '{"username":"ana","password":"secreto123","rol":"user"}'

# 2. Login -> obtener el JWT (válido 2h)
TOKEN=$(curl -s -X POST localhost:5001/auth/login -H "Content-Type: application/json" \
  -d '{"username":"ana","password":"secreto123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 3. Crear una tarea (requiere Bearer)
curl -X POST localhost:5002/tasks -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"titulo":"Mi tarea","user_id":1}'

# 4. Completar la tarea -> notifica al notifications-service (token forwarding)
curl -X PUT localhost:5002/tasks/1/complete -H "Authorization: Bearer $TOKEN"

# 5. Ver el historial de notificaciones
curl localhost:5003/notifications
```
