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
        └──▶ Cloud Storage         (store images + results)
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

---

## Project Structure
```
dal-i/
├── backend/
│   ├── src/
│   │   ├── main.py        # FastAPI app + endpoints
│   │   ├── speech.py      # Speech-to-Text integration
│   │   ├── vision.py      # Vertex AI + OpenCV processing
│   │   ├── storage.py     # Cloud Storage integration
│   │   └── models.py      # Request/Response data models
│   ├── tests/
│   │   ├── test_main.py
│   │   ├── test_vision.py
│   │   ├── test_speech.py
│   │   └── test_storage.py
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt
│   └── .env.example
├── docs/
│   ├── G4-6_Dal-i_Project_Description_.pdf
│   └── Google Cloud Platform.pdf
├── .gitignore
└── README.md
```

---

## Prerequisites
Make sure you have these installed:
- [Python 3.11+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/)
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)
- [Docker](https://www.docker.com/) *(only needed for containerized runs and deployment)*

> **Windows users:** We strongly recommend using WSL2 to avoid installation issues.
> Open PowerShell as Administrator and run:
> ```powershell
> wsl --install
> ```
> Then follow the setup steps below inside the WSL2 terminal.

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/<your-org>/dal-i.git
cd dal-i
```

### 2. Authenticate with Google Cloud
```bash
# Login to your Google account
gcloud auth login

# Set the project
gcloud config set project proyectosm-494910

# Set up application default credentials
gcloud auth application-default login
```

> You need to be added as Editor on the GCP project first.
> Contact Moisés (moisanpin@gmail.com) if you don't have access.

### 3. Set up Python environment
```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate        # Linux / Mac / WSL2
venv\Scripts\activate           # Windows CMD
.\venv\Scripts\Activate.ps1     # Windows PowerShell

# Install dependencies
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your values
nano .env
```

Your `.env` should look like this:
```
GOOGLE_CLOUD_PROJECT=proyectosm-494910
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
BUCKET_NAME=dal-i-bucket
VERTEX_LOCATION=us-central1
```

> ⚠️ Never commit your `.env` file — it is in `.gitignore` for a reason.

---

## Running Locally

### Without Docker
```bash
# Make sure you are in /backend with venv activated
uvicorn src.main:app --reload
```

API will be available at: `http://localhost:8000`
Auto-generated docs at: `http://localhost:8000/docs`

### With Docker
```bash
# Make sure you are in /backend

# Build the image
docker build -t dal-i-api .

# Run the container (basic)
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT=proyectosm-494910 \
  -e BUCKET_NAME=dal-i-bucket \
  -e VERTEX_LOCATION=us-central1 \
  dal-i-api

# Run the container (with GCP credentials mounted)
docker run -p 8080:8080 \
  -v $(pwd)/service-account.json:/app/service-account.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json \
  -e GOOGLE_CLOUD_PROJECT=proyectosm-494910 \
  -e BUCKET_NAME=dal-i-bucket \
  -e VERTEX_LOCATION=us-central1 \
  dal-i-api
```

API will be available at: `http://localhost:8080`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check if API is running |
| POST | `/upload` | Upload image to Cloud Storage |
| POST | `/process` | Image + style → plotter coordinates |
| POST | `/process/voice` | Image + voice audio → plotter coordinates |

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

---

## Running Tests
```bash
# Make sure venv is activated and you are in /backend
pytest tests/ -v
```

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

**`ModuleNotFoundError`**
→ Make sure your venv is activated: `source venv/bin/activate`

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