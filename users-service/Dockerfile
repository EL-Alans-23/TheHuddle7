# --- users-service ---
FROM python:3.11-slim

# Salida sin buffer y sin .pyc: logs inmediatos e imagen más limpia.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 1) Dependencias primero -> aprovecha la caché de capas de Docker:
#    si requirements.txt no cambia, no se reinstala en cada build.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Código de la aplicación.
COPY . .

# Puerto del users-service.
EXPOSE 5001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5001"]
