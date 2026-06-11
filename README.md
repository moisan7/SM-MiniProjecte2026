# Dal-i

**Robotic Drawing System — UAB Sistemes Multimèdia 2025–2026 · Grup G4-6**

Dal-i converts any image into physical robot arm drawings. Upload a photo, pick an artistic style by voice, text, or quick-select button, and the system computes the optimal drawing trajectory. A SCARA robot arm then reproduces the result on paper.

The name is a dual reference: Salvador **Dalí** (surrealist artist) and **DALL-E** (OpenAI image model) — reflecting the project's intersection of classical art and generative AI.

**Live app:** `https://dal-i-api-y55wqasb6a-ew.a.run.app`

---

## Team

| Name | NIU |
|---|---|
| David Madueño Noguer | 1526933 |
| Moisés Sánchez Pin | 1603611 |
| Xavier Cañada Escalona | 1708948 |
| Lorenzo Payaro Robles | 1731940 |

---

## How It Works

1. User uploads an image and picks a style (button / text / voice)
2. If **Advanced Mode** is on, Gemini 2.5 Flash applies visual style transfer first
3. OpenCV Canny detects edges; a TSP-based algorithm optimizes stroke order
4. The system returns plotter coordinates + SVG preview + TTS audio confirmation
5. The Raspberry Pi reads the coordinates and drives the SCARA arm

---

## Architecture

```
Browser
  │  Firebase Anonymous Auth (silent, per-browser UID)
  │
  ├─── Cloud Function: upload   ──► Cloud Storage (dal-i-bucket)
  ├─── Cloud Function: history  ──► Firestore (generation_history/{uid}/items)
  ├─── Cloud Function: speech   ──► STT · TTS · Cloud Translation
  │
  └─── Cloud Run: dal-i-api  (FastAPI + static Next.js frontend)
         ├─► /process       ──► Vertex AI Gemini 2.5 Flash (Advanced Mode)
         ├─► /process/voice ──► edge detection + TSP (Raspberry Pi compatible)
         └─► /process/text  ──► edge detection + TSP (Raspberry Pi compatible)

Raspberry Pi ──► /process/voice or /process/text  (no auth required)
```

All infrastructure runs on **Google Cloud Platform**, region `europe-west1` (Cloud Run) and `us-central1` (Cloud Functions).

---

## Tech Stack

### Cloud (GCP)
| Service | Role |
|---|---|
| Cloud Run | Backend API + static frontend container |
| Cloud Functions (×3) | history, upload, speech — lightweight ops |
| Vertex AI / Gemini 2.5 Flash | Visual style transfer (Advanced Mode) |
| Cloud Speech-to-Text | Voice command transcription (10 languages) |
| Cloud Text-to-Speech | Audio confirmation response |
| Cloud Translation | Auto-translate user input/output |
| Cloud Storage | Image and result storage (`dal-i-bucket`) |
| Firestore | Per-user generation history |
| Firebase Auth | Anonymous authentication (silent, browser-persistent) |
| Cloud Build + Artifact Registry | CI/CD — auto-deploy on push to `main` |

### Application
| Technology | Role |
|---|---|
| FastAPI + Python 3.12 | REST API backend |
| Next.js 16 + React 19 + TypeScript | Frontend (static export) |
| Tailwind CSS 4 | Styling |
| OpenCV 4 | Canny edge detection |
| NumPy | Matrix operations in vision pipeline |
| Pillow | Image resizing and encoding |
| firebase-admin | Token verification on backend |
| functions-framework | Local Cloud Functions development |

---

## Project Structure

```
SM-MiniProjecte2026/
├── backend/
│   ├── src/
│   │   ├── main.py        # FastAPI app — /process, /process/voice, /process/text, /health
│   │   ├── vision.py      # Canny edge detection + TSP optimization
│   │   ├── db.py          # Firestore helpers (uid-scoped)
│   │   ├── storage.py     # Cloud Storage helpers
│   │   └── models.py      # Pydantic request/response models
│   ├── tests/             # 39 unit tests (fully mocked, no GCP needed)
│   ├── Dockerfile         # Multi-stage: Node build → Python slim
│   └── requirements.txt
├── cloudfunctions/
│   ├── history/main.py    # GET paginated / DELETE single / DELETE all (cascade GCS)
│   ├── upload/main.py     # POST image → GCS, validates size + MIME
│   └── speech/main.py     # transcribe / tts / translate (10 languages)
├── frontend/
│   ├── app/
│   │   ├── page.tsx       # Main UI — voice/text/button flows
│   │   ├── lib/
│   │   │   ├── api.ts         # Centralized API client (injects Firebase token)
│   │   │   ├── firebase.ts    # Lazy Firebase init (safe for static export)
│   │   │   └── styleExtractor.ts  # Client-side style extraction (25 styles)
│   │   └── components/
│   │       ├── HistoryPanel.tsx   # Paginated history + Delete All modal
│   │       └── LanguagePicker.tsx # 10-language selector
│   └── .env.production    # Firebase config (baked into static build)
├── docs/
│   ├── presentation/pres.tex   # Beamer slides (LuaLaTeX)
│   └── report/                 # Academic report (LuaLaTeX)
└── cloudbuild.yaml        # CI/CD: build image → Artifact Registry → Cloud Run
```

---

## Supported Languages

Spanish · English · French · German · Italian · Portuguese · Catalan · Japanese · Chinese · Arabic

Input (voice/text) is automatically translated to English for internal processing, then back to the user's language for TTS confirmation.

---

## Local Development

### Prerequisites
- Python 3.12
- Node.js 18+ and pnpm (`npm install -g pnpm`)
- Google Cloud CLI (WSL2 recommended on Windows)
- GCP project access (`proyectosm-494910`)

### Backend

```bash
# Authenticate with GCP
gcloud auth login
gcloud config set project proyectosm-494910
gcloud auth application-default login

# Set up Python environment (from repo root)
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# Copy env vars (values already set for the project)
cp backend/.env.example backend/.env

# Run (from repo root)
cd backend && uvicorn src.main:app --reload --port 8000
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
# → http://localhost:3000
```

### Cloud Functions (local)

> Cloud Functions call live GCP services (Firestore, Cloud Storage, Speech/TTS/Translation).
> Running them locally only makes sense with `gcloud auth application-default login` and
> access to project `proyectosm-494910`. For end-to-end testing, use the live app instead.

```bash
# Each function runs in its own terminal
cd cloudfunctions/history && pip install -r requirements.txt
functions-framework --target history_handler --port 8081

cd cloudfunctions/upload && pip install -r requirements.txt
functions-framework --target upload_handler --port 8082

cd cloudfunctions/speech && pip install -r requirements.txt
functions-framework --target speech_handler --port 8083
```

Each should print `Serving Flask app '...'`. Requests without a Firebase token return `401` — expected.

---

## API Endpoints

### Cloud Run (`dal-i-api`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Service health check |
| `POST` | `/process` | Required | Style buttons → coordinates |
| `POST` | `/process/voice` | Optional | Voice audio → coordinates (Pi compatible) |
| `POST` | `/process/text` | Optional | Text prompt → coordinates (Pi compatible) |

### Cloud Functions

| Function | Method | Params | Description |
|---|---|---|---|
| `upload` | `POST` | `multipart/form-data` | Upload image to GCS (max 10 MB) |
| `history` | `GET` | `?page_size=12&page_token=` | Paginated generation history |
| `history` | `DELETE` | `?id={docId}` | Delete one item + cascade GCS |
| `history` | `DELETE` | `?deleteAll=true` | Delete all items + cascade GCS |
| `speech` | `POST` | `?action=transcribe` | Audio → text → style (STT + translate) |
| `speech` | `POST` | `?action=tts` | Text → translated audio (TTS) |
| `speech` | `POST` | `?action=translate` | Generic text translation |

All endpoints (except `/health` and Pi-compatible ones) require `Authorization: Bearer <Firebase token>`.

---

## Tests

39 unit tests, fully mocked — no GCP credentials needed.

```bash
# From repo root
pytest backend -q

# With coverage
pytest backend -q --tb=short
```

VSCode: Testing panel works out of the box. If tests are uncollected, verify `.vscode/settings.json`:
```json
{ "python.testing.pytestArgs": ["backend"] }
```

---

## Deployment

CI/CD is automatic: every push to `main` triggers Cloud Build, which builds the Docker image, pushes to Artifact Registry, and does a rolling update of Cloud Run with zero downtime.

**Manual deploy:**
```bash
# Cloud Run (from repo root)
wsl -- bash -c "gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions=SHORT_SHA=\$(git rev-parse --short HEAD) \
  --project proyectosm-494910"

# Cloud Function (example: history)
wsl -- bash -c "gcloud functions deploy history \
  --gen2 --runtime python312 --region us-central1 \
  --source cloudfunctions/history \
  --entry-point history_handler \
  --trigger-http --allow-unauthenticated \
  --project proyectosm-494910"
```

---

## Common Issues

| Problem | Fix |
|---|---|
| `gcloud: command not found` | Use `wsl -- bash -c "gcloud ..."` (gcloud lives in WSL2) |
| `auth/invalid-api-key` | Firebase config missing — check `frontend/.env.production` |
| `auth/admin-restricted-operation` | Enable Anonymous Auth in Firebase Console → Authentication → Sign-in method |
| Button stays disabled (uid null) | Add Cloud Run domain to Firebase Console → Authorized Domains |
| `403` on Cloud Functions deploy | Grant `roles/artifactregistry.reader` to the GCF service account |
| `SHORT_SHA` empty in manual build | Pass `--substitutions=SHORT_SHA=$(git rev-parse --short HEAD)` |
| Raspberry Pi gets `404` on `/process/voice` | Endpoint is on Cloud Run, not Cloud Functions — check base URL |

---