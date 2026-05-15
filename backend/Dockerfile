# Etapa 1: Construir el frontend
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Etapa 2: Servidor Backend
FROM python:3.12-slim
WORKDIR /app

# Instalar dependencias del sistema para OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del backend
COPY backend/src/ ./src/

# Copiar el build del frontend para que el backend lo sirva
COPY --from=frontend-builder /frontend/out ./frontend/out

EXPOSE 8080

# Usar el puerto 8080 (estándar de Cloud Run)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]