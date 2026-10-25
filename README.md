# BuildWise AI

An AI-powered multimodal construction intelligence platform. It combines a **FastAPI** backend with a **React** frontend, running fully offline using **Ollama** local LLMs — no cloud API keys required.

The platform assists construction professionals with safety monitoring, structural analysis, project planning, property valuation, weather advisory, daily reporting, and an AI assistant — all powered by locally running language models.

---

## Project structure

```
buildwise-ai/
├── backend/
│   ├── main.py              # FastAPI app — all 7 AI endpoints
│   ├── requirements.txt     # Pinned Python dependencies
│   ├── .env                 # Backend config (not committed)
│   ├── .gitignore
│   └── .venv/               # Python virtual environment (not committed)
└── frontend/
    ├── src/
    │   ├── App.jsx           # Root component + routing
    │   ├── App.css           # Component styles
    │   ├── index.css         # Global styles + Tailwind
    │   ├── main.jsx          # React entry point
    │   ├── features/         # One component per AI feature
    │   │   ├── SafetyMonitoring.jsx
    │   │   ├── CrackDetection.jsx
    │   │   ├── ProjectPlanner.jsx
    │   │   ├── PropertyValuation.jsx
    │   │   ├── WeatherAdvisory.jsx
    │   │   ├── DailySiteReport.jsx
    │   │   └── AIAssistant.jsx
    │   ├── components/       # Shared UI components
    │   │   ├── ImageUploader.jsx
    │   │   ├── ResultCard.jsx
    │   │   └── Spinner.jsx
    │   └── services/
    │       └── api.js        # Typed fetch wrapper for all endpoints
    ├── public/
    ├── .env                  # Frontend config (not committed)
    ├── vite.config.js        # Vite + dev-server proxy config
    └── package.json
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| npm | 9+ | Frontend package manager |
| [Ollama](https://ollama.com) | 0.9+ | Local LLM runtime |

---

## AI models used

| Model | Size | Purpose |
|-------|------|---------|
| `llama3.2` | 2 GB | Text features — planning, valuation, weather, reports, assistant |
| `llava:7b` | 4.7 GB | Vision features — safety monitoring, crack detection |

Both models run **100% locally** via Ollama. No internet connection or API key is needed after the initial model download.

> **System requirement:** 16 GB RAM recommended to run both models. 8 GB RAM can run `llama3.2` only (vision features will be limited).

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/SnehaSwarnkar/buildwise.ai.git
cd buildwise.ai
```

### 2. Install and start Ollama

Download from [ollama.com](https://ollama.com/download), then pull the required models:

```bash
ollama pull llama3.2
ollama pull llava:7b
```

Start the Ollama server:

```bash
ollama serve
```

### 3. Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create the .env file (already configured for Ollama defaults)
cp .env.example .env             # or create it manually — see Environment variables below
```

### 4. Frontend

```bash
cd frontend
npm install
```

---

## Running locally

You need **three terminals** running simultaneously.

**Terminal 1 — Ollama**
```bash
ollama serve
```

**Terminal 2 — Backend**
```bash
cd backend
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 3 — Frontend**
```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Environment variables

### `backend/.env`

```env
# Server
APP_HOST=127.0.0.1
APP_PORT=8000
APP_RELOAD=true

# CORS — comma-separated allowed frontend origins
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TEXT_MODEL=llama3.2
OLLAMA_VISION_MODEL=llava:7b

# Upload limits
MAX_IMAGE_SIZE_MB=10
```

### `frontend/.env`

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

> Neither `.env` file is committed to the repository. Create them locally from the examples above.

---

## API reference

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### `GET /health`
Returns server and Ollama connectivity status.

```json
{
  "status": "healthy",
  "application": "BuildWise AI",
  "timestamp": "2026-10-24T10:00:00Z",
  "ai_ready": true,
  "text_model": "llama3.2",
  "vision_model": "llava:7b"
}
```

### `GET /api/features`
Returns the list of all platform features.

### `POST /api/safety/analyze`
Analyzes a construction site image for hazards and PPE compliance.

| Field | Type | Required |
|-------|------|----------|
| `file` | Image (JPG/PNG/WEBP, max 10 MB) | ✅ |
| `context` | Text description of the site | optional |

### `POST /api/cracks/analyze`
Detects and classifies structural cracks in an image.

| Field | Type | Required |
|-------|------|----------|
| `file` | Image (JPG/PNG/WEBP, max 10 MB) | ✅ |
| `context` | Additional structural context | optional |

### `POST /api/planning/generate`
Generates a construction project plan with timeline, phases, and material estimates.

| Field | Type | Required |
|-------|------|----------|
| `project_type` | string | ✅ |
| `area_sqft` | number | ✅ |
| `location` | string | optional |
| `budget_usd` | number | optional |
| `description` | string | optional |

### `POST /api/valuation/estimate`
Estimates property value based on attributes and location.

| Field | Type | Required |
|-------|------|----------|
| `property_type` | string | ✅ |
| `area_sqft` | number | ✅ |
| `location` | string | ✅ |
| `bedrooms` | number | optional |
| `bathrooms` | number | optional |
| `year_built` | number | optional |
| `condition` | poor/fair/good/excellent/new | optional |
| `amenities` | string | optional |

### `POST /api/weather/advisory`
Generates a weather-aware advisory for planned construction activities.

| Field | Type | Required |
|-------|------|----------|
| `location` | string | ✅ |
| `activities` | string | optional |
| `date_range` | string | optional |

### `POST /api/reports/generate`
Auto-generates a structured daily site progress report.

| Field | Type | Required |
|-------|------|----------|
| `site_name` | string | ✅ |
| `date` | YYYY-MM-DD | ✅ |
| `file` | Site photo (optional) | optional |
| `activities_completed` | string | optional |
| `workers_present` | number | optional |
| `equipment_used` | string | optional |
| `issues` | string | optional |
| `notes` | string | optional |

### `POST /api/assistant/ask`
Answers construction-related questions with AI expertise.

| Field | Type | Required |
|-------|------|----------|
| `question` | string | ✅ |
| `context` | Project context string | optional |

**Error responses (all endpoints)**

| Status | Cause |
|--------|-------|
| `400` | Empty or malformed file |
| `413` | File exceeds 10 MB |
| `415` | Unsupported image format |
| `503` | Ollama is not running |
| `504` | Ollama response timeout |
| `502` | Model returned unreadable output |
| `500` | Unexpected server error |

---

## Tech stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend framework | [FastAPI](https://fastapi.tiangolo.com) | 0.162 |
| ASGI server | [Uvicorn](https://www.uvicorn.org) | 0.54 |
| Data validation | [Pydantic v2](https://docs.pydantic.dev) + pydantic-settings | 2.14 |
| HTTP client | [httpx](https://www.python-httpx.org) | 0.28 |
| Local AI runtime | [Ollama](https://ollama.com) | 0.9+ |
| Text model | [Llama 3.2](https://ollama.com/library/llama3.2) | 3.2B |
| Vision model | [LLaVA](https://ollama.com/library/llava) | 7B |
| Frontend framework | [React](https://react.dev) | 19 |
| Build tool | [Vite](https://vitejs.dev) | 8 |
| Styling | [Tailwind CSS](https://tailwindcss.com) | v4 |

---

## Features

| Feature | AI model | Input | Status |
|---------|----------|-------|--------|
| Safety Monitoring | LLaVA 7B (vision) | Site image | ✅ Live |
| Crack Detection | LLaVA 7B (vision) | Structure image | ✅ Live |
| Project Planner | Llama 3.2 (text) | Project details | ✅ Live |
| Property Valuation | Llama 3.2 (text) | Property details | ✅ Live |
| Weather Advisory | Llama 3.2 (text) | Location + activities | ✅ Live |
| Daily Site Reports | Llama 3.2 + LLaVA | Form + optional photo | ✅ Live |
| AI Construction Assistant | Llama 3.2 (text) | Free-text question | ✅ Live |

---

## Known limitations

- **Vision accuracy** — LLaVA 7B is a smaller model. For production use, a larger vision model (e.g. LLaVA 13B or 34B) will give significantly more accurate results.
- **Response time** — Local inference is slower than cloud APIs. Text responses take 5–15 seconds; vision responses 15–45 seconds depending on hardware.
- **JSON reliability** — Smaller models occasionally produce malformed JSON. The backend includes a fallback parser, but complex queries may fail. Retrying usually succeeds.
- **No real-time weather data** — The weather advisory uses the model's training knowledge of typical weather patterns, not live forecast data.
- **Valuation estimates** — Property valuations are AI-generated estimates based on general market knowledge, not live real estate data. Do not use for financial decisions.
