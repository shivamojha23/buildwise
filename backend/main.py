"""
BuildWise AI — FastAPI backend
Supports two AI providers:
  - Ollama  (local dev)  — set USE_OLLAMA=true  in .env
  - Gemini  (production) — set GEMINI_API_KEY=...  in .env
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Settings ──────────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_reload: bool = False
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_image_size_mb: int = 10

    # AI provider switch
    use_ollama: bool = False          # true = Ollama (local), false = Gemini (cloud)

    # Ollama (local dev)
    ollama_base_url: str = "http://localhost:11434"
    ollama_text_model: str = "llama3.2"
    ollama_vision_model: str = "llava:7b"

    # Gemini (production)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def max_image_size_bytes(self) -> int:
        return self.max_image_size_mb * 1024 * 1024

    @property
    def ai_provider(self) -> str:
        return "ollama" if self.use_ollama else "gemini"


settings = Settings()

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger("buildwise")

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="BuildWise AI API",
    description="AI-powered multimodal construction intelligence platform",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global error handler ──────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."},
    )

# ── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup() -> None:
    if settings.use_ollama:
        ok = await _check_ollama()
        logger.info("AI provider=ollama reachable=%s model=%s vision=%s",
                    ok, settings.ollama_text_model, settings.ollama_vision_model)
    else:
        ready = bool(settings.gemini_api_key)
        logger.info("AI provider=gemini ready=%s model=%s", ready, settings.gemini_model)

@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("BuildWise AI server shutting down.")

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_IMAGE_SIZE = settings.max_image_size_bytes
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


# ══════════════════════════════════════════════════════════════════════════════
#  AI PROVIDER LAYER
# ══════════════════════════════════════════════════════════════════════════════

async def _check_ollama() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{settings.ollama_base_url}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


def _extract_json(raw: str) -> dict[str, Any]:
    """Parse JSON from model output, with fallback extraction."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
    logger.error("Cannot parse JSON from model output: %s", raw[:400])
    raise HTTPException(status_code=502,
                        detail="AI returned an unreadable response. Please try again.")


async def _call_ollama(system: str, prompt: str,
                       image_b64: str | None = None) -> dict[str, Any]:
    model = settings.ollama_vision_model if image_b64 else settings.ollama_text_model
    payload: dict[str, Any] = {
        "model": model,
        "prompt": f"{system}\n\n{prompt}",
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2, "num_predict": 2048},
    }
    if image_b64:
        payload["images"] = [image_b64]

    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(f"{settings.ollama_base_url}/api/generate", json=payload)
            r.raise_for_status()
    except httpx.ConnectError:
        raise HTTPException(status_code=503,
                            detail="Cannot reach Ollama. Run `ollama serve` in a terminal.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Ollama timed out. Try again.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e.response.status_code}")

    return _extract_json(r.json().get("response", "{}"))


async def _call_gemini(system: str, prompt: str,
                       image_bytes: bytes | None = None,
                       image_mime: str = "image/jpeg") -> dict[str, Any]:
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Set GEMINI_API_KEY in environment variables.",
        )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
        f"?key={settings.gemini_api_key}"
    )

    parts: list[dict] = [{"text": f"{system}\n\n{prompt}"}]

    if image_bytes:
        parts.insert(0, {
            "inline_data": {
                "mime_type": image_mime,
                "data": base64.b64encode(image_bytes).decode(),
            }
        })

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(url, json=payload)
            r.raise_for_status()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot reach Gemini API.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Gemini API timed out.")
    except httpx.HTTPStatusError as e:
        body = e.response.text[:300]
        raise HTTPException(status_code=502, detail=f"Gemini API error: {body}")

    data = r.json()
    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise HTTPException(status_code=502, detail="Unexpected Gemini response format.")

    return _extract_json(raw)


async def call_ai(system: str, prompt: str,
                  image_bytes: bytes | None = None,
                  image_mime: str = "image/jpeg") -> dict[str, Any]:
    """Unified AI call — routes to Ollama or Gemini based on settings."""
    if settings.use_ollama:
        b64 = base64.b64encode(image_bytes).decode() if image_bytes else None
        return await _call_ollama(system, prompt, b64)
    else:
        return await _call_gemini(system, prompt, image_bytes, image_mime)


# ══════════════════════════════════════════════════════════════════════════════
#  IMAGE VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

async def read_and_validate_image(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415,
                            detail="Unsupported format. Upload JPG, PNG, or WEBP.")
    try:
        data = await file.read(MAX_IMAGE_SIZE + 1)
    finally:
        await file.close()

    if not data:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image exceeds the 10 MB limit.")

    is_jpeg = data.startswith(b"\xff\xd8\xff")
    is_png  = data.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    valid = (
        (file.content_type == "image/jpeg" and is_jpeg)
        or (file.content_type == "image/png"  and is_png)
        or (file.content_type == "image/webp" and is_webp)
    )
    if not valid:
        raise HTTPException(status_code=400,
                            detail="File contents do not match the declared format.")
    return data


# ══════════════════════════════════════════════════════════════════════════════
#  RESPONSE MODELS
# ══════════════════════════════════════════════════════════════════════════════

class HealthResponse(BaseModel):
    status: str
    application: str
    timestamp: datetime
    ai_ready: bool
    ai_provider: str
    model: str


class Hazard(BaseModel):
    type: str
    severity: str
    location: str
    description: str
    recommendation: str

class SafetyAnalysisResponse(BaseModel):
    overall_risk_level: str
    hazards: list[Hazard]
    ppe_compliance: str
    immediate_actions: list[str]
    summary: str


class CrackDetail(BaseModel):
    type: str
    severity: str
    location: str
    probable_cause: str
    recommended_action: str

class CrackAnalysisResponse(BaseModel):
    crack_detected: bool
    overall_severity: str
    structural_risk: str
    cracks: list[CrackDetail]
    immediate_action_required: bool
    summary: str


class MaterialItem(BaseModel):
    material: str
    quantity: str
    unit: str
    estimated_cost_usd: float

class PlanningResponse(BaseModel):
    project_type: str
    estimated_duration_weeks: int
    phases: list[dict]
    materials: list[MaterialItem]
    total_estimated_cost_usd: float
    key_risks: list[str]
    summary: str


class ValuationResponse(BaseModel):
    estimated_value_usd: float
    price_per_sqft_usd: float
    market_trend: str
    confidence_level: str
    value_drivers: list[str]
    comparable_range_usd: dict
    summary: str


class WeatherAdvisoryResponse(BaseModel):
    location: str
    current_conditions: str
    risk_level: str
    affected_activities: list[str]
    recommendations: list[str]
    work_safe_window: str
    summary: str


class ReportSection(BaseModel):
    section: str
    content: str

class DailyReportResponse(BaseModel):
    date: str
    site_name: str
    overall_progress: str
    sections: list[ReportSection]
    issues_flagged: list[str]
    next_day_plan: str
    summary: str


class AssistantResponse(BaseModel):
    answer: str
    follow_up_suggestions: list[str]
    references: list[str]


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "message": "Welcome to BuildWise AI",
        "documentation": "/docs",
        "health": "/health",
        "version": "2.0.0",
        "ai_provider": settings.ai_provider,
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    if settings.use_ollama:
        ai_ready = await _check_ollama()
        model = f"{settings.ollama_text_model} + {settings.ollama_vision_model}"
    else:
        ai_ready = bool(settings.gemini_api_key)
        model = settings.gemini_model

    return HealthResponse(
        status="healthy",
        application="BuildWise AI",
        timestamp=datetime.now(timezone.utc),
        ai_ready=ai_ready,
        ai_provider=settings.ai_provider,
        model=model,
    )


@app.get("/api/features")
def list_features():
    return {
        "features": [
            {"id": "safety",    "name": "Safety Monitoring",        "status": "available"},
            {"id": "cracks",    "name": "Crack Detection",           "status": "available"},
            {"id": "planning",  "name": "Project Planner",           "status": "available"},
            {"id": "valuation", "name": "Property Valuation",        "status": "available"},
            {"id": "weather",   "name": "Weather Advisory",          "status": "available"},
            {"id": "reports",   "name": "Daily Site Reports",        "status": "available"},
            {"id": "assistant", "name": "AI Construction Assistant", "status": "available"},
        ]
    }


# ── 1. Safety Monitoring ──────────────────────────────────────────────────────

@app.post("/api/safety/analyze", response_model=SafetyAnalysisResponse)
async def analyze_safety(file: UploadFile = File(...), context: str = Form(default="")):
    data = await read_and_validate_image(file)

    system = """You are a certified construction safety engineer with OSHA expertise.
Analyze the construction site image and return ONLY a valid JSON object:
{
  "overall_risk_level": "low or medium or high or critical",
  "hazards": [
    {
      "type": "hazard type",
      "severity": "low or medium or high or critical",
      "location": "where in the image",
      "description": "what the hazard is",
      "recommendation": "how to fix it"
    }
  ],
  "ppe_compliance": "compliant or partial or non-compliant or not-visible",
  "immediate_actions": ["action 1", "action 2"],
  "summary": "2-3 sentence overall assessment"
}
Return ONLY the JSON object, no other text."""

    result = await call_ai(system, f"Analyze this construction site image for safety hazards.{' Context: ' + context if context else ''}", data, file.content_type or "image/jpeg")
    result.setdefault("overall_risk_level", "unknown")
    result.setdefault("hazards", [])
    result.setdefault("ppe_compliance", "not-visible")
    result.setdefault("immediate_actions", [])
    result.setdefault("summary", "Analysis complete.")
    logger.info("Safety analysis — risk=%s hazards=%d", result["overall_risk_level"], len(result["hazards"]))
    return result


# ── 2. Crack Detection ────────────────────────────────────────────────────────

@app.post("/api/cracks/analyze", response_model=CrackAnalysisResponse)
async def analyze_cracks(file: UploadFile = File(...), context: str = Form(default="")):
    data = await read_and_validate_image(file)

    system = """You are a structural engineer specializing in crack analysis.
Analyze the image and return ONLY a valid JSON object:
{
  "crack_detected": true or false,
  "overall_severity": "none or hairline or minor or moderate or severe or critical",
  "structural_risk": "none or low or medium or high or immediate",
  "cracks": [
    {
      "type": "crack type",
      "severity": "severity level",
      "location": "where in the image",
      "probable_cause": "likely cause",
      "recommended_action": "what to do"
    }
  ],
  "immediate_action_required": true or false,
  "summary": "overall assessment"
}
Return ONLY the JSON object."""

    result = await call_ai(system, f"Analyze this image for structural cracks.{' Context: ' + context if context else ''}", data, file.content_type or "image/jpeg")
    result.setdefault("crack_detected", False)
    result.setdefault("overall_severity", "none")
    result.setdefault("structural_risk", "none")
    result.setdefault("cracks", [])
    result.setdefault("immediate_action_required", False)
    result.setdefault("summary", "Analysis complete.")
    logger.info("Crack analysis — detected=%s severity=%s", result["crack_detected"], result["overall_severity"])
    return result


# ── 3. Project Planner ────────────────────────────────────────────────────────

@app.post("/api/planning/generate", response_model=PlanningResponse)
async def generate_plan(
    project_type: str = Form(...), area_sqft: float = Form(...),
    location: str = Form(default=""), budget_usd: float = Form(default=0),
    description: str = Form(default=""),
):
    system = """You are a senior construction project manager with 20 years of experience.
Return ONLY a valid JSON object:
{
  "project_type": "project name",
  "estimated_duration_weeks": 12,
  "phases": [{"phase": "name", "duration_weeks": 2, "activities": ["a1"], "dependencies": []}],
  "materials": [{"material": "name", "quantity": 100, "unit": "bags", "estimated_cost_usd": 500}],
  "total_estimated_cost_usd": 150000,
  "key_risks": ["risk 1"],
  "summary": "overview"
}
Return ONLY the JSON object."""

    prompt = f"Generate a construction plan:\nProject: {project_type}\nArea: {area_sqft} sq ft\nLocation: {location or 'not specified'}\nBudget: {'$' + str(budget_usd) if budget_usd else 'not specified'}\nDescription: {description or 'standard construction'}"
    result = await call_ai(system, prompt)
    result.setdefault("project_type", project_type)
    result.setdefault("estimated_duration_weeks", 0)
    result.setdefault("phases", [])
    result.setdefault("materials", [])
    result.setdefault("total_estimated_cost_usd", 0)
    result.setdefault("key_risks", [])
    result.setdefault("summary", "Plan generated.")
    return result


# ── 4. Property Valuation ─────────────────────────────────────────────────────

@app.post("/api/valuation/estimate", response_model=ValuationResponse)
async def estimate_valuation(
    property_type: str = Form(...), area_sqft: float = Form(...),
    location: str = Form(...), bedrooms: int = Form(default=0),
    bathrooms: int = Form(default=0), year_built: int = Form(default=0),
    condition: str = Form(default="good"), amenities: str = Form(default=""),
):
    system = """You are a certified real estate appraiser.
Return ONLY a valid JSON object:
{
  "estimated_value_usd": 350000,
  "price_per_sqft_usd": 175,
  "market_trend": "stable or declining or appreciating or hot",
  "confidence_level": "low or medium or high",
  "value_drivers": ["driver 1"],
  "comparable_range_usd": {"low": 300000, "mid": 350000, "high": 400000},
  "summary": "valuation summary"
}
Return ONLY the JSON object."""

    prompt = f"Estimate property value:\nType: {property_type}\nArea: {area_sqft} sq ft\nLocation: {location}\nBedrooms: {bedrooms}, Bathrooms: {bathrooms}\nYear built: {year_built or 'unknown'}, Condition: {condition}\nAmenities: {amenities or 'standard'}"
    result = await call_ai(system, prompt)
    result.setdefault("estimated_value_usd", 0)
    result.setdefault("price_per_sqft_usd", 0)
    result.setdefault("market_trend", "stable")
    result.setdefault("confidence_level", "medium")
    result.setdefault("value_drivers", [])
    result.setdefault("comparable_range_usd", {"low": 0, "mid": 0, "high": 0})
    result.setdefault("summary", "Valuation complete.")
    return result


# ── 5. Weather Advisory ───────────────────────────────────────────────────────

@app.post("/api/weather/advisory", response_model=WeatherAdvisoryResponse)
async def weather_advisory(
    location: str = Form(...), activities: str = Form(default="general construction"),
    date_range: str = Form(default="next 7 days"),
):
    system = """You are a construction weather risk specialist.
Return ONLY a valid JSON object:
{
  "location": "city name",
  "current_conditions": "typical weather description",
  "risk_level": "low or medium or high or extreme",
  "affected_activities": ["activity 1"],
  "recommendations": ["recommendation 1"],
  "work_safe_window": "e.g. 6 AM to 2 PM on clear days",
  "summary": "advisory summary"
}
Return ONLY the JSON object."""

    prompt = f"Construction weather advisory:\nLocation: {location}\nActivities: {activities}\nPeriod: {date_range}"
    result = await call_ai(system, prompt)
    result.setdefault("location", location)
    result.setdefault("current_conditions", "unknown")
    result.setdefault("risk_level", "medium")
    result.setdefault("affected_activities", [])
    result.setdefault("recommendations", [])
    result.setdefault("work_safe_window", "To be determined")
    result.setdefault("summary", "Advisory generated.")
    return result


# ── 6. Daily Site Reports ─────────────────────────────────────────────────────

@app.post("/api/reports/generate", response_model=DailyReportResponse)
async def generate_report(
    site_name: str = Form(...), date: str = Form(...),
    file: UploadFile = File(default=None),
    activities_completed: str = Form(default=""),
    workers_present: int = Form(default=0),
    equipment_used: str = Form(default=""),
    issues: str = Form(default=""), notes: str = Form(default=""),
):
    image_bytes = None
    image_mime = "image/jpeg"
    if file and file.filename:
        image_bytes = await read_and_validate_image(file)
        image_mime = file.content_type or "image/jpeg"

    system = """You are a construction site manager generating a formal daily report.
Return ONLY a valid JSON object:
{
  "date": "YYYY-MM-DD",
  "site_name": "site name",
  "overall_progress": "behind-schedule or on-schedule or ahead-of-schedule",
  "sections": [
    {"section": "Work Completed", "content": "details"},
    {"section": "Workforce", "content": "details"},
    {"section": "Equipment", "content": "details"},
    {"section": "Safety Observations", "content": "details"},
    {"section": "Materials", "content": "details"},
    {"section": "Weather Impact", "content": "details"}
  ],
  "issues_flagged": ["issue 1"],
  "next_day_plan": "plan for tomorrow",
  "summary": "brief summary"
}
Return ONLY the JSON object."""

    prompt = f"Daily site report:\nSite: {site_name}, Date: {date}\nActivities: {activities_completed or 'not specified'}\nWorkers: {workers_present}, Equipment: {equipment_used or 'not specified'}\nIssues: {issues or 'none'}, Notes: {notes or 'none'}"
    result = await call_ai(system, prompt, image_bytes, image_mime)
    result.setdefault("date", date)
    result.setdefault("site_name", site_name)
    result.setdefault("overall_progress", "on-schedule")
    result.setdefault("sections", [])
    result.setdefault("issues_flagged", [])
    result.setdefault("next_day_plan", "Continue scheduled activities.")
    result.setdefault("summary", "Report generated.")
    return result


# ── 7. AI Construction Assistant ──────────────────────────────────────────────

@app.post("/api/assistant/ask", response_model=AssistantResponse)
async def ask_assistant(question: str = Form(...), context: str = Form(default="")):
    system = """You are an expert AI construction assistant with deep knowledge in:
- Construction engineering and structural design
- Building codes and safety (OSHA, IBC, ACI, AISC)
- Materials science and cost estimation
- Project management and scheduling
- Real estate and property valuation

Return ONLY a valid JSON object:
{
  "answer": "detailed professional answer",
  "follow_up_suggestions": ["question 1?", "question 2?", "question 3?"],
  "references": ["OSHA 1926.502", "ACI 318-14"]
}
Return ONLY the JSON object."""

    prompt = f"Question: {question}" + (f"\nContext: {context}" if context else "")
    result = await call_ai(system, prompt)
    result.setdefault("answer", "No answer generated.")
    result.setdefault("follow_up_suggestions", [])
    result.setdefault("references", [])
    return result
