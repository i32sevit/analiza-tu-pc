# Imagen base optimizada para FastAPI
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

# Copiar archivos del backend al contenedor
COPY . /app

# Instalar dependencias
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /app/requirements.txt

# Puerto interno (OpenShift redirige a él)
ENV PORT=8080

# Comando principal (ya incluido en esta imagen)
