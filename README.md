
# Dal-i 🤖🎨
**Collaborative Robotic Drawing System**  
UAB Sistemes Multimèdia 2025–2026

A cloud-based system where a SCARA robot plotter captures an image and a voice
command (e.g. "Picasso style"), sends them to a cloud API that processes the image
using AI, simplifies it into drawable strokes, and returns the vector coordinates
for the robot to physically recreate.  

---

## Team G4-6
| Name | Student ID |
|------|-----------|
| Moisés Sánchez Pin | 1603611 |
| Xavier Cañada Escalona | 1708948 |
| David Madueño Noger | 1526933 |
| Lorenzo Jesus Payaro Robles | 1731940 |

---

## Architecture
```
Robot (SCARA Plotter)
        │
        │ HTTP POST (image + voice)
        ▼
  Cloud Run API (Python/FastAPI)
        │
        ├──▶ Cloud Speech-to-Text  (voice → artistic style)
        ├──▶ Vertex AI / Gemini    (style transfer)
        ├──▶ OpenCV Canny          (image → edge lines)
        ├──▶ Cloud Storage         (store images + results)
        └──▶ Cloud Firestore       (store generation history)
        │
        │ JSON (plotter coordinates)
        ▼
Robot draws the image
```

---

## Google Cloud Services
| Service | Purpose |
|---------|---------|
| Cloud Run | Hosts the Python API |
| Cloud Speech-to-Text | Converts voice command to text |
| Vertex AI (Gemini) | Style transfer + image analysis |
| Cloud Storage | Stores images and coordinate results |
| Cloud Firestore | Stores metadata and history of generations |

---

## Project Structure
```
dal-i/
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py        # FastAPI app + endpoints
│   │   ├── speech.py      # Speech-to-Text integration
│   │   ├── vision.py      # Vertex AI + OpenCV processing
│   │   ├── storage.py     # Cloud Storage integration
│   │   ├── db.py          # Firestore integration
│   │   └── models.py      # Request/Response data models
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py    # Shared fixtures (image + audio bytes)
│   │   ├── test_main.py
│   │   ├── test_vision.py
│   │   ├── test_speech.py
│   │   └── test_storage.py
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py             # Convenience script to start backend
├── frontend/
│   ├── app/               # Next.js App Router
│   ├── public/            # Static assets
│   ├── package.json
│   └── tsconfig.json
├── docs/
│   ├── G4-6_Dal-i_Project_Description_.pdf
│   └── Google Cloud Platform.pdf
├── .gitignore
└── README.md
```

---

## Prerequisites
Make sure you have these installed:
- [Python 3.12.x](https://www.python.org/downloads/) (recommended for dependency compatibility)
- [Node.js 18+](https://nodejs.org/) (for frontend development)
- [Git](https://git-scm.com/)
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)
- [Docker](https://www.docker.com/) *(only needed for containerized runs and deployment)*

---

## Setup

### Backend Setup
This project uses a virtual environment in the repository root named `.venv`.
All dependency installation is done from the root with `backend/requirements.txt`.

1. **Clone the repository**
```bash
git clone https://github.com/<your-org>/dal-i.git
cd dal-i
```

2. **Authenticate with Google Cloud**
```bash
gcloud auth login
gcloud config set project proyectosm-494910
gcloud auth application-default login
```

3. **Set up Python environment**
Windows PowerShell:
```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```
Linux / macOS / WSL:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

4. **Set up environment variables**
```bash
cp backend/.env.example backend/.env
```
Edit `backend/.env` with your GCP project details.

### Frontend Setup
```bash
cd frontend
npm install
```

---

## Running Locally

### Backend
The easiest way to run the backend is using the `run.py` script:

```bash
# From the repository root
python backend/run.py
```

Or manually:
```bash
cd backend
uvicorn src.main:app --reload
```

API will be available at: `http://localhost:8000`
Auto-generated docs at: `http://localhost:8000/docs`

### Frontend
```bash
cd frontend
npm run dev
```
Frontend will be available at: `http://localhost:3000`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check if API is running |
| GET | `/history` | Retrieve recent generation history |
| DELETE | `/history/{id}` | Delete a history record |
| POST | `/upload` | Upload image to Cloud Storage |
| POST | `/process` | Image + style → plotter coordinates |
| POST | `/process/voice` | Image + voice audio → plotter coordinates |
| POST | `/process/text` | Image + text prompt → plotter coordinates |

### Example requests

**Health check:**
```bash
curl http://localhost:8000/health
```

**Upload an image:**
```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@test_image.jpg"
```

**Process an image with a style:**
```bash
curl -X POST http://localhost:8000/process \
  -F "file=@test_image.jpg" \
  -F "style=picasso"
```

**Process with voice command:**
```bash
curl -X POST http://localhost:8000/process/voice \
  -F "image=@test_image.jpg" \
  -F "audio=@voice_command.wav"
```

**Process with text prompt:**
```bash
curl -X POST http://localhost:8000/process/text \
  -F "image=@test_image.jpg" \
  -F "text=make it look like a van gogh painting"
```

---

## Docker Support

### Build
```bash
cd backend
docker build -t dal-i-api .
```

### Run
```bash
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT=proyectosm-494910 \
  -e BUCKET_NAME=dal-i-bucket \
  -e VERTEX_LOCATION=us-central1 \
  dal-i-api
```

### Run with credentials
```bash
docker run -p 8080:8080 \
  -v $(pwd)/service-account.json:/app/service-account.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json \
  -e GOOGLE_CLOUD_PROJECT=proyectosm-494910 \
  -e BUCKET_NAME=dal-i-bucket \
  -e VERTEX_LOCATION=us-central1 \
  dal-i-api
```

---

## Running Tests

All 34 tests are fully mocked — no GCP credentials or live services needed.

Windows PowerShell:

```powershell
# from repository root
.\.venv\Scripts\python.exe -m pytest backend -q
```

Linux / macOS / WSL:

```bash
# from repository root
.venv/bin/python -m pytest backend -q
```

### VS Code
Tests are discoverable via the Testing panel out of the box.
If tests show as red/uncollected, check that `.vscode/settings.json` has:
```json
"python.testing.pytestArgs": ["backend"]
```
Do **not** change this to `"."` — it breaks the import path resolution.

---

## Deployment to Cloud Run
```bash
# Make sure you are in /backend
gcloud run deploy dal-i-api \
  --source . \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --project proyectosm-494910
```

---

## Common Issues

**`gcloud: command not found`**
→ Install Google Cloud CLI or use WSL2 (recommended on Windows)

**`Permission denied` on GCP APIs**
→ Make sure you have been added to the project as Editor
→ Contact Moisés (moisanpin@gmail.com)

**VS Code does not detect packages (numpy, cv2, etc.)**
→ Select interpreter: `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (Linux/WSL)
→ If needed, restart VS Code window after selecting the interpreter

**`ModuleNotFoundError`**
→ Reinstall dependencies in project venv:
`python -m pip install -r backend/requirements.txt`

**Python 3.14 related errors (`protobuf`, `google._upb`, `tp_new`)**
→ Recreate environment with Python 3.12.x and reinstall requirements

**`Bucket not found`**
→ The Cloud Storage bucket needs to be created first
→ Contact Moisés to set it up

**`Docker: service-account.json not found`**
→ Make sure the file exists in `/backend` before mounting it

---

## Important Notes
- ⚠️ Never commit `.env` or any `*.json` credential files
- ⚠️ Always stop Cloud Run services when not in use to save credits
- ⚠️ Check GCP billing dashboard regularly
- ✅ Free trial active — ~€256 credit available
- ✅ Budget alerts configured at €0.50, €0.90 and €1.00
- ✅ GCP Project ID: `proyectosm-494910`

