# BuildWise AI

An AI-powered construction intelligence platform. The current stage covers project scaffolding, a working FastAPI backend with image upload and validation, and a React frontend dashboard — ready for AI feature integration.

---

## Project structure

```
buildwise-ai/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Pinned Python dependencies
│   ├── .env                 # Backend environment variables (not committed)
│   └── .gitignore
└── frontend/
    ├── src/
    │   ├── App.jsx           # Main React component / UI
    │   ├── App.css           # Component styles
    │   ├── index.css         # Global styles + Tailwind
    │   └── services/
    │       └── api.js        # Fetch wrapper for all backend calls
    ├── public/
    ├── .env                  # Frontend environment variables (not committed)
    ├── vite.config.js        # Vite + dev-server proxy config
    └── package.json
```

---

## Prerequisites

| Tool | Minimum version |
|------|----------------|
| Python | 3.11 |
| Node.js | 18 |
| npm | 9 |

---

## Setup

### 1. Clone and enter the project

```bash
git clone <repo-url>
cd buildwise-ai
```

### 2. Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env .env.local               # or edit .env directly
# → Fill in OPENAI_API_KEY (required for future AI features)
```

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (already has a working default)
# Edit .env only if your backend runs on a different host/port
```

---

## Running locally

Open **two terminals**.

**Terminal 1 — backend**

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — frontend**

```bash
cd frontend
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173).

The Vite dev server proxies `/api` and `/health` requests to the backend, so there are no CORS issues during development.

---

## Environment variables

### `backend/.env`

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_HOST` | `127.0.0.1` | Host the uvicorn server binds to |
| `APP_PORT` | `8000` | Port the uvicorn server listens on |
| `APP_RELOAD` | `true` | Enable hot-reload (disable in production) |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated list of allowed CORS origins |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI API key — required for AI features |
| `MAX_IMAGE_SIZE_MB` | `10` | Maximum accepted image upload size in MB |

### `frontend/.env`

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | Backend base URL used by the API client |

> **Never commit `.env` files containing real secrets.** Both `.gitignore` files already exclude them.

---

## API reference

Interactive docs are available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) when the backend is running.

### `GET /`
Returns a welcome message and links to docs and health endpoints.

### `GET /health`
Returns server health status and UTC timestamp.

```json
{
  "status": "healthy",
  "application": "BuildWise AI",
  "timestamp": "2026-10-24T10:00:00Z"
}
```

### `GET /api/features`
Returns the list of platform features and their current availability status.

```json
{
  "features": [
    { "id": "safety",    "name": "Safety Monitoring",        "status": "available" },
    { "id": "cracks",    "name": "Crack Detection",           "status": "planned"   },
    { "id": "planning",  "name": "Project Planner",           "status": "planned"   },
    { "id": "valuation", "name": "Property Valuation",        "status": "planned"   },
    { "id": "weather",   "name": "Weather Advisory",          "status": "planned"   },
    { "id": "reports",   "name": "Daily Site Reports",        "status": "planned"   },
    { "id": "assistant", "name": "AI Construction Assistant", "status": "planned"   }
  ]
}
```

### `POST /api/safety/analyze`
Accepts a construction-site image and validates it. AI hazard detection is not yet wired in — this endpoint confirms the upload pipeline is working end-to-end.

**Request** — `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `file` | `File` | Image to analyse. JPG, PNG, or WEBP. Max 10 MB. |

**Success response — `200 OK`**

```json
{
  "success": true,
  "filename": "site-photo.jpg",
  "size_bytes": 204800,
  "status": "uploaded",
  "analysis_complete": false,
  "message": "Image uploaded and validated successfully. AI hazard detection has not been configured yet."
}
```

**Error responses**

| Status | Cause |
|--------|-------|
| `400` | Empty file or content does not match declared format |
| `413` | File exceeds the 10 MB limit |
| `415` | Unsupported file type (not JPG / PNG / WEBP) |
| `500` | Unexpected server error |

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend framework | [FastAPI](https://fastapi.tiangolo.com) 0.162 |
| ASGI server | [Uvicorn](https://www.uvicorn.org) 0.54 |
| Data validation | [Pydantic v2](https://docs.pydantic.dev) + pydantic-settings |
| Frontend framework | [React](https://react.dev) 19 |
| Build tool | [Vite](https://vitejs.dev) 8 |
| Styling | [Tailwind CSS](https://tailwindcss.com) v4 |
| AI (planned) | [OpenAI](https://platform.openai.com/docs) |

---

## Features — current status

| Feature | Status | Notes |
|---------|--------|-------|
| Safety Monitoring | **Upload ready** | Image upload + validation working. AI analysis not yet integrated. |
| Crack Detection | Planned | — |
| Project Planner | Planned | — |
| Property Valuation | Planned | — |
| Weather Advisory | Planned | — |
| Daily Site Reports | Planned | — |
| AI Construction Assistant | Planned | — |

---

## Development notes

- The backend reads all config from `.env` via `pydantic-settings`. No values are hardcoded — change `.env` and restart to reconfigure.
- The frontend reads `VITE_API_BASE_URL` at build time. After changing `.env` in the frontend directory, restart `npm run dev`.
- The Vite proxy (`/api`, `/health`) is active **only in development**. In production, configure your reverse proxy (nginx, etc.) to route these paths to the backend.
- FastAPI's automatic docs (`/docs`) reflect the live API schema and are the fastest way to test endpoints manually.
