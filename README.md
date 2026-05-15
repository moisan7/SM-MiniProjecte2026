# DAL-I: Sistema Robótico de Dibujo Colaborativo

Este proyecto es una plataforma interactiva que permite a los usuarios convertir imágenes en trazos para un plotter robótico, utilizando inteligencia artificial para aplicar estilos artísticos mediante comandos de voz o texto.

## Estructura del Proyecto

- `backend/`: API construida con FastAPI, utiliza Vertex AI (Gemini), Cloud Speech-to-Text y Cloud Storage.
- `frontend/`: Interfaz web moderna construida con Next.js y Tailwind CSS.

## Requisitos Previos

1.  **Google Cloud Platform**:
    - Cuenta activa con facturación habilitada.
    - APIs habilitadas: Vertex AI, Speech-to-Text, Cloud Storage.
    - Archivo `credenciales.json` en la raíz del proyecto.
2.  **Node.js** (v18+) y **Python** (3.12+).

## Instalación y Ejecución Local

### 1. Preparar el Backend
```powershell
cd backend
pip install -r requirements.txt
```

### 2. Preparar el Frontend
```powershell
cd frontend
npm install
npm run build
```

### 3. Ejecutar la Aplicación
```powershell
cd backend
$env:GOOGLE_APPLICATION_CREDENTIALS = "..\credenciales.json"
$env:PYTHONPATH = "src"
uvicorn src.main:app --reload
```
Visita `http://localhost:8000` para ver la aplicación.

## Ejecución con Docker

Puedes construir y ejecutar todo el stack (Frontend + Backend) en un solo contenedor:

```powershell
docker build -t dali-app -f backend/Dockerfile .
docker run -p 8080:8080 -e GOOGLE_APPLICATION_CREDENTIALS=/app/credenciales.json -v ${PWD}/credenciales.json:/app/credenciales.json dali-app
```

## Funcionalidades principales

- **Subida de imágenes**: Procesa archivos JPG/PNG.
- **Control por Voz**: Graba instrucciones (ej: "Haz un dibujo estilo Dalí") directamente desde el navegador.
- **Control por Texto**: Escribe el estilo deseado.
- **Visualización en Canvas**: Previsualiza los trazos rojos que el robot realizará sobre la imagen original.
- **Almacenamiento en Cloud**: Las imágenes y resultados se guardan automáticamente en Google Cloud Storage.

## Tests

Para ejecutar las pruebas unitarias y de integración:
```powershell
cd backend
$env:GOOGLE_APPLICATION_CREDENTIALS = "..\credenciales.json"
$env:PYTHONPATH = "src"
pytest
```
