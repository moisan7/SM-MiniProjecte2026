from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["project_id"] == "proyectosm-494910"

def test_process_text_no_image():
    # Test error handling when no image is provided
    response = client.post("/process/text", data={"text": "estilo Picasso"})
    assert response.status_code == 422 # Unprocessable Entity