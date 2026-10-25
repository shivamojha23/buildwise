"""
BuildWise AI — FastAPI backend
Multimodal construction intelligence platform.
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Settings ──────────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_reload: bool = False
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    max_image_size_mb: int = 10

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def max_image_size_bytes(self) -> int:
        return self.max_image_size_mb * 1024 * 1024


settings = Settings()

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger("buildwise")

# ── OpenAI client ─────────────────────────────────────────────────────────────

ai = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

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
    ai_ready = bool(settings.openai_api_key)
    logger.info(
        "BuildWise AI started — host=%s port=%d ai_ready=%s model=%s",
        settings.app_host, settings.app_port, ai_ready, settings.openai_model,
    )

@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("BuildWise AI server shutting down.")


# ── Constants ─────────────────────────────────────────────────────────────────

MAX_IMAGE_SIZE = settings.max_image_size_bytes
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


# ── Shared helpers ────────────────────────────────────────────────────────────

async def read_and_validate_image(file: UploadFile) -> bytes:
    """Read, size-check, and magic-byte validate an uploaded image. Returns raw bytes."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image format. Upload a JPG, PNG, or WEBP image.",
        )
    try:
        data = await file.read(MAX_IMAGE_SIZE + 1)
    finally:
        await file.close()

    if not data:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image exceeds the 10 MB upload limit.")

    is_jpeg = data.startswith(b"\xff\xd8\xff")
    is_png = data.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    valid = (
        (file.content_type == "image/jpeg" and is_jpeg)
        or (file.content_type == "image/png" and is_png)
        or (file.content_type == "image/webp" and is_webp)
    )
    if not valid:
        raise HTTPException(
            status_code=400,
            detail="File contents do not match the declared image format.",
        )
    return data


def image_to_data_url(data: bytes, content_type: str) -> str:
    return f"data:{content_type};base64,{base64.b64encode(data).decode()}"


def require_ai() -> OpenAI:
    if ai is None:
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured. Set OPENAI_API_KEY in backend/.env.",
        )
    return ai


def call_ai_json(client: OpenAI, system: str, user_text: str,
                 image_url: str | None = None) -> dict[str, Any]:
    """Call OpenAI and parse the JSON response. Raises HTTPException on failure."""
    messages: list[dict] = [{"role": "system", "content": system}]

    if image_url:
        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}},
                {"type": "text", "text": user_text},
            ],
        })
    else:
        messages.append({"role": "user", "content": user_text})

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("AI returned invalid JSON: %s", exc)
        raise HTTPException(status_code=502, detail="AI returned an unreadable response.")
    except Exception as exc:
        logger.exception("OpenAI call failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")


# ── Response models ───────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    application: str
    timestamp: datetime
    ai_ready: bool


class Hazard(BaseModel):
    type: str
    severity: str          # low | medium | high | critical
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


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "message": "Welcome to BuildWise AI",
        "documentation": "/docs",
        "health": "/health",
        "version": "2.0.0",
    }


@app.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="healthy",
        application="BuildWise AI",
        timestamp=datetime.now(timezone.utc),
        ai_ready=ai is not None,
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
async def analyze_safety(
    file: UploadFile = File(...),
    context: str = Form(default=""),
):
    """Analyze a construction site image for safety hazards and PPE compliance."""
    client = require_ai()
    data = await read_and_validate_image(file)
    image_url = image_to_data_url(data, file.content_type or "image/jpeg")

    system = """You are a certified construction safety engineer with expertise in OSHA standards.
Analyze the provided construction site image and return a JSON object with this exact schema:
{
  "overall_risk_level": "low|medium|high|critical",
  "hazards": [
    {
      "type": "string",
      "severity": "low|medium|high|critical",
      "location": "string describing where in the image",
      "description": "string",
      "recommendation": "string"
    }
  ],
  "ppe_compliance": "compliant|partial|non-compliant|not-visible",
  "immediate_actions": ["string"],
  "summary": "string (2-3 sentences)"
}
Return ONLY valid JSON, no markdown."""

    user = f"Analyze this construction site image for safety hazards.{' Additional context: ' + context if context else ''}"
    result = call_ai_json(client, system, user, image_url)

    # Ensure required keys exist with safe defaults
    result.setdefault("overall_risk_level", "unknown")
    result.setdefault("hazards", [])
    result.setdefault("ppe_compliance", "not-visible")
    result.setdefault("immediate_actions", [])
    result.setdefault("summary", "Analysis complete.")

    logger.info("Safety analysis done — risk=%s hazards=%d", result["overall_risk_level"], len(result["hazards"]))
    return result


# ── 2. Crack Detection ────────────────────────────────────────────────────────

@app.post("/api/cracks/analyze", response_model=CrackAnalysisResponse)
async def analyze_cracks(
    file: UploadFile = File(...),
    context: str = Form(default=""),
):
    """Detect and classify structural cracks from a site image."""
    client = require_ai()
    data = await read_and_validate_image(file)
    image_url = image_to_data_url(data, file.content_type or "image/jpeg")

    system = """You are a structural engineer specializing in crack analysis and building diagnostics.
Analyze the image and return JSON with this exact schema:
{
  "crack_detected": true|false,
  "overall_severity": "none|hairline|minor|moderate|severe|critical",
  "structural_risk": "none|low|medium|high|immediate",
  "cracks": [
    {
      "type": "string (e.g. hairline, structural, settlement)",
      "severity": "string",
      "location": "string",
      "probable_cause": "string",
      "recommended_action": "string"
    }
  ],
  "immediate_action_required": true|false,
  "summary": "string"
}
Return ONLY valid JSON."""

    user = f"Analyze this image for structural cracks.{' Context: ' + context if context else ''}"
    result = call_ai_json(client, system, user, image_url)

    result.setdefault("crack_detected", False)
    result.setdefault("overall_severity", "none")
    result.setdefault("structural_risk", "none")
    result.setdefault("cracks", [])
    result.setdefault("immediate_action_required", False)
    result.setdefault("summary", "Analysis complete.")

    logger.info("Crack analysis done — detected=%s severity=%s", result["crack_detected"], result["overall_severity"])
    return result


# ── 3. Project Planner ────────────────────────────────────────────────────────

@app.post("/api/planning/generate", response_model=PlanningResponse)
async def generate_plan(
    project_type: str = Form(...),
    area_sqft: float = Form(...),
    location: str = Form(default=""),
    budget_usd: float = Form(default=0),
    description: str = Form(default=""),
):
    """Generate a construction project plan with timeline, materials, and cost estimates."""
    client = require_ai()

    system = """You are a senior construction project manager with 20 years of experience.
Generate a detailed project plan and return JSON with this exact schema:
{
  "project_type": "string",
  "estimated_duration_weeks": integer,
  "phases": [
    {"phase": "string", "duration_weeks": integer, "activities": ["string"], "dependencies": ["string"]}
  ],
  "materials": [
    {"material": "string", "quantity": number, "unit": "string", "estimated_cost_usd": number}
  ],
  "total_estimated_cost_usd": number,
  "key_risks": ["string"],
  "summary": "string"
}
Return ONLY valid JSON."""

    user = (
        f"Project: {project_type}\n"
        f"Area: {area_sqft} sq ft\n"
        f"Location: {location or 'not specified'}\n"
        f"Budget: {'$' + str(budget_usd) if budget_usd else 'not specified'}\n"
        f"Description: {description or 'standard construction'}\n"
        "Generate a detailed construction plan."
    )
    result = call_ai_json(client, system, user)

    result.setdefault("project_type", project_type)
    result.setdefault("estimated_duration_weeks", 0)
    result.setdefault("phases", [])
    result.setdefault("materials", [])
    result.setdefault("total_estimated_cost_usd", 0)
    result.setdefault("key_risks", [])
    result.setdefault("summary", "Plan generated.")

    logger.info("Project plan generated — type=%s duration=%s weeks", result["project_type"], result["estimated_duration_weeks"])
    return result


# ── 4. Property Valuation ─────────────────────────────────────────────────────

@app.post("/api/valuation/estimate", response_model=ValuationResponse)
async def estimate_valuation(
    property_type: str = Form(...),
    area_sqft: float = Form(...),
    location: str = Form(...),
    bedrooms: int = Form(default=0),
    bathrooms: int = Form(default=0),
    year_built: int = Form(default=0),
    condition: str = Form(default="good"),
    amenities: str = Form(default=""),
):
    """Estimate property valuation based on key attributes."""
    client = require_ai()

    system = """You are a certified real estate appraiser with expertise in construction and property valuation.
Analyze the property details and return JSON with this exact schema:
{
  "estimated_value_usd": number,
  "price_per_sqft_usd": number,
  "market_trend": "declining|stable|appreciating|hot",
  "confidence_level": "low|medium|high",
  "value_drivers": ["string"],
  "comparable_range_usd": {"low": number, "mid": number, "high": number},
  "summary": "string"
}
Return ONLY valid JSON."""

    user = (
        f"Property type: {property_type}\n"
        f"Area: {area_sqft} sq ft\n"
        f"Location: {location}\n"
        f"Bedrooms: {bedrooms}, Bathrooms: {bathrooms}\n"
        f"Year built: {year_built or 'unknown'}\n"
        f"Condition: {condition}\n"
        f"Amenities: {amenities or 'standard'}\n"
        "Provide a detailed property valuation."
    )
    result = call_ai_json(client, system, user)

    result.setdefault("estimated_value_usd", 0)
    result.setdefault("price_per_sqft_usd", 0)
    result.setdefault("market_trend", "stable")
    result.setdefault("confidence_level", "medium")
    result.setdefault("value_drivers", [])
    result.setdefault("comparable_range_usd", {"low": 0, "mid": 0, "high": 0})
    result.setdefault("summary", "Valuation complete.")

    logger.info("Valuation done — value=$%s location=%s", result["estimated_value_usd"], location)
    return result


# ── 5. Weather Advisory ───────────────────────────────────────────────────────

@app.post("/api/weather/advisory", response_model=WeatherAdvisoryResponse)
async def weather_advisory(
    location: str = Form(...),
    activities: str = Form(default="general construction"),
    date_range: str = Form(default="next 7 days"),
):
    """Generate weather-aware construction site advisory."""
    client = require_ai()

    system = """You are a construction weather risk specialist.
Based on the location and planned activities, generate a weather advisory and return JSON with this exact schema:
{
  "location": "string",
  "current_conditions": "string",
  "risk_level": "low|medium|high|extreme",
  "affected_activities": ["string"],
  "recommendations": ["string"],
  "work_safe_window": "string",
  "summary": "string"
}
Use your knowledge of typical weather patterns for the location and season. Return ONLY valid JSON."""

    user = (
        f"Location: {location}\n"
        f"Planned activities: {activities}\n"
        f"Period: {date_range}\n"
        "Generate a weather advisory for construction work."
    )
    result = call_ai_json(client, system, user)

    result.setdefault("location", location)
    result.setdefault("current_conditions", "unknown")
    result.setdefault("risk_level", "medium")
    result.setdefault("affected_activities", [])
    result.setdefault("recommendations", [])
    result.setdefault("work_safe_window", "To be determined")
    result.setdefault("summary", "Advisory generated.")

    logger.info("Weather advisory done — location=%s risk=%s", location, result["risk_level"])
    return result


# ── 6. Daily Site Reports ─────────────────────────────────────────────────────

@app.post("/api/reports/generate", response_model=DailyReportResponse)
async def generate_report(
    site_name: str = Form(...),
    date: str = Form(...),
    file: UploadFile = File(default=None),
    activities_completed: str = Form(default=""),
    workers_present: int = Form(default=0),
    equipment_used: str = Form(default=""),
    issues: str = Form(default=""),
    notes: str = Form(default=""),
):
    """Generate a daily site progress report, optionally with a site image."""
    client = require_ai()

    image_url = None
    if file and file.filename:
        data = await read_and_validate_image(file)
        image_url = image_to_data_url(data, file.content_type or "image/jpeg")

    system = """You are a construction site manager generating a formal daily progress report.
Return JSON with this exact schema:
{
  "date": "string",
  "site_name": "string",
  "overall_progress": "behind-schedule|on-schedule|ahead-of-schedule",
  "sections": [
    {"section": "string", "content": "string"}
  ],
  "issues_flagged": ["string"],
  "next_day_plan": "string",
  "summary": "string"
}
Sections should include: Work Completed, Workforce, Equipment, Safety Observations, Materials, Weather Impact.
Return ONLY valid JSON."""

    user = (
        f"Site: {site_name}\nDate: {date}\n"
        f"Activities completed: {activities_completed or 'not specified'}\n"
        f"Workers present: {workers_present}\n"
        f"Equipment used: {equipment_used or 'not specified'}\n"
        f"Issues: {issues or 'none reported'}\n"
        f"Notes: {notes or 'none'}\n"
        "Generate a professional daily site report."
    )
    result = call_ai_json(client, system, user, image_url)

    result.setdefault("date", date)
    result.setdefault("site_name", site_name)
    result.setdefault("overall_progress", "on-schedule")
    result.setdefault("sections", [])
    result.setdefault("issues_flagged", [])
    result.setdefault("next_day_plan", "Continue scheduled activities.")
    result.setdefault("summary", "Report generated.")

    logger.info("Daily report generated — site=%s date=%s", site_name, date)
    return result


# ── 7. AI Construction Assistant ──────────────────────────────────────────────

@app.post("/api/assistant/ask", response_model=AssistantResponse)
async def ask_assistant(
    question: str = Form(...),
    context: str = Form(default=""),
):
    """Answer construction-related questions with AI expertise."""
    client = require_ai()

    system = """You are an expert AI construction assistant with deep knowledge in:
- Construction engineering and structural design
- Building codes and safety regulations (OSHA, IBC, ACI, AISC)
- Materials science and cost estimation
- Project management and scheduling
- Real estate and property valuation

Return JSON with this exact schema:
{
  "answer": "string (detailed, professional answer)",
  "follow_up_suggestions": ["string (3 related questions the user might want to ask)"],
  "references": ["string (relevant standards, codes, or resources)"]
}
Return ONLY valid JSON."""

    user = (
        f"Question: {question}"
        + (f"\nProject context: {context}" if context else "")
    )
    result = call_ai_json(client, system, user)

    result.setdefault("answer", "No answer generated.")
    result.setdefault("follow_up_suggestions", [])
    result.setdefault("references", [])

    logger.info("Assistant answered question (%d chars)", len(question))
    return result
