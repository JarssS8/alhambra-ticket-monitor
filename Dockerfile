FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos
COPY requirements.txt .
COPY monitor.py .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Crear volumen para historial y logs
VOLUME ["/app/data"]

# Configurar variables de entorno
ENV PYTHONUNBUFFERED=1

# Ejecutar monitor
CMD ["python", "monitor.py"]
