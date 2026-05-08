# Proyecto SM - DAL-I

Aquí explicaremos de forma resumida pero completa todo nuestro proyecto una vez terminado.

## Inicialización del Proyecto

### Requisitos Previos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de Configuración

#### 1. Crear el entorno virtual
```bash
python -m venv venv
```

#### 2. Activar el entorno virtual
En Windows:
```cmd
venv\Scripts\activate
```

En macOS/Linux:
```bash
source venv/bin/activate
```

#### 3. Instalar las dependencias
```bash
pip install -r backend/requirements.txt
```

#### 4. Configurar variables de entorno
Crea un archivo `.env` en la raíz del proyecto (si es necesario) con las credenciales de Google Cloud:
```env
# Ejemplo de .env
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json
```

#### 5. Ejecutar el servidor
```bash
cd backend
uvicorn src.main:app --reload
```

El servidor estará disponible en http://localhost:8000

#### 6. Ejecutar los tests (opcional)
```bash
pytest tests/