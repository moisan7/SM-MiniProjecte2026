import uvicorn
import os

if __name__ == "__main__":
    # Cambiamos al directorio del script para asegurar que las rutas relativas funcionen
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("🚀 Iniciando Dal-i Backend en http://localhost:8000")
    uvicorn.run(
        "src.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )
