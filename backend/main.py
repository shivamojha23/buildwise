"""
BuildWise AI — FastAPI backend
Multimodal construction intelligence platform powered by Ollama (local LLM).
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

    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_reload: bool = False
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_image_size_mb: int = 10

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_text_model: str = "llama3.2"
    ollama_vision_model: str = "llava:7b"

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


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="BuildWise AI API",
    description="AI-powered multimodal construction intelligence platform (Ollama)",
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
    ok = await check_ollama_health()
    logger.info(
        "BuildWise AI started — ollama=%s text_model=%s vision_model=%s",
        "reachable" if ok else "UNREACHABLE",
        settings.ollama_text_model,
        settings.ollama_vision_model,
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("BuildWise AI server shutting down.")


# ── Constants ─────────────────────────────────────────────────────────────────

MAX_IMAGE_SIZE = settings.max_image_size_bytes
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


# ── Ollama helpers ────────────────────────────────────────────────────────────

async def check_ollama_health() -> bool:
    """Return True if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def ollama_chat(
    prompt: str,
    system: str,
    image_b64: str | None = None,
    use_vision: bool = False,
) -> dict[str, Any]:
    """
    Call Ollama /api/generate and parse the JSON response from the model.
    Uses the vision model when an image is provided, text model otherwise.
    """
    model = settings.ollama_vision_model if use_vision else settings.ollama_text_model

    full_prompt = f"{system}\n\n{prompt}"

    payload: dict[str, Any] = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "format": "json",          # ask Ollama to enforce JSON output
        "options": {
            "temperature": 0.2,
            "num_predict": 2048,
        },
    }

    if image_b64:
        payload["images"] = [image_b64]

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=(
                "Cannot reach Ollama. Make sure it is running: run `ollama serve` "
                "in a terminal."
            ),
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned an error: {exc.response.status_code}",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Ollama took too long to respond. Try a shorter prompt or a faster model.",
        )

    raw = response.json().get("response", "{}")
    logger.debug("Ollama raw response: %s", raw[:300])

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Model returned text instead of JSON — try to extract a JSON block
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
        logger.error("Could not parse JSON from model response: %s", raw[:500])
        raise HTTPException(
            status_code=502,
            detail="The AI model returned an unreadable response. Try again.",
        )


# ── Image helpers ─────────────────────────────────────────────────────────────

async def read_and_validate_image(file: UploadFile) -> bytes:
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


def to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


# ── Response models ───────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    application: str
    timestamp: datetime
    ai_ready: bool
    text_model: str
    vision_model: str


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


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "message": "Welcome to BuildWise AI",
        "documentation": "/docs",
        "health": "/health",
        "version": "2.0.0",
        "ai_backend": "Ollama (local)",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    ai_ready = await check_ollama_health()
    return HealthResponse(
        status="healthy",
        application="BuildWise AI",
        timestamp=datetime.now(timezone.utc),
        ai_ready=ai_ready,
        text_model=settings.ollama_text_model,
        vision_model=settings.ollama_vision_model,
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
    data = await read_and_validate_image(file)

    system = """You are a certified construction safety engineer with OSHA expertise.
Analyze the construction site image and return ONLY a valid JSON object with this exact structure:
{
  "overall_risk_level": "low or medium or high or critical",
  "hazards": [
    {
      "type": "hazard type name",
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

    prompt = f"Analyze this construction site image for safety hazards.{' Context: ' + context if context else ''}"

    result = await ollama_chat(system=system, prompt=prompt,
                               image_b64=to_b64(data), use_vision=True)

    result.setdefault("overall_risk_level", "unknown")
    result.setdefault("hazards", [])
    result.setdefault("ppe_compliance", "not-visible")
    result.setdefault("immediate_actions", [])
    result.setdefault("summary", "Analysis complete.")

    logger.info("Safety analysis — risk=%s hazards=%d", result["overall_risk_level"], len(result["hazards"]))
    return result


# ── 2. Crack Detection ────────────────────────────────────────────────────────

@app.post("/api/cracks/analyze", response_model=CrackAnalysisResponse)
async def analyze_cracks(
    file: UploadFile = File(...),
    context: str = Form(default=""),
):
    data = await read_and_validate_image(file)

    system = """You are a structural engineer specializing in crack analysis.
Analyze the image and return ONLY a valid JSON object:
{
  "crack_detected": true or false,
  "overall_severity": "none or hairline or minor or moderate or severe or critical",
  "structural_risk": "none or low or medium or high or immediate",
  "cracks": [
    {
      "type": "crack type (e.g. hairline, structural, settlement)",
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

    prompt = f"Analyze this image for structural cracks.{' Context: ' + context if context else ''}"

    result = await ollama_chat(system=system, prompt=prompt,
                               image_b64=to_b64(data), use_vision=True)

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
    project_type: str = Form(...),
    area_sqft: float = Form(...),
    location: str = Form(default=""),
    budget_usd: float = Form(default=0),
    description: str = Form(default=""),
):
    system = """You are a senior construction project manager with 20 years of experience.
Return ONLY a valid JSON object with this structure:
{
  "project_type": "project name",
  "estimated_duration_weeks": 12,
  "phases": [
    {
      "phase": "phase name",
      "duration_weeks": 2,
      "activities": ["activity 1", "activity 2"],
      "dependencies": ["dependency"]
    }
  ],
  "materials": [
    {
      "material": "material name",
      "quantity": 100,
      "unit": "bags",
      "estimated_cost_usd": 500
    }
  ],
  "total_estimated_cost_usd": 150000,
  "key_risks": ["risk 1", "risk 2"],
  "summary": "project overview"
}
Return ONLY the JSON object."""

    prompt = (
        f"Generate a detailed construction plan for:\n"
        f"Project: {project_type}\n"
        f"Area: {area_sqft} sq ft\n"
        f"Location: {location or 'not specified'}\n"
        f"Budget: {'$' + str(budget_usd) if budget_usd else 'not specified'}\n"
        f"Description: {description or 'standard construction'}"
    )

    result = await ollama_chat(system=system, prompt=prompt)

    result.setdefault("project_type", project_type)
    result.setdefault("estimated_duration_weeks", 0)
    result.setdefault("phases", [])
    result.setdefault("materials", [])
    result.setdefault("total_estimated_cost_usd", 0)
    result.setdefault("key_risks", [])
    result.setdefault("summary", "Plan generated.")

    logger.info("Plan generated — type=%s duration=%s weeks", result["project_type"], result["estimated_duration_weeks"])
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
    system = """You are a certified real estate appraiser.
Return ONLY a valid JSON object:
{
  "estimated_value_usd": 350000,
  "price_per_sqft_usd": 175,
  "market_trend": "stable or declining or appreciating or hot",
  "confidence_level": "low or medium or high",
  "value_drivers": ["driver 1", "driver 2"],
  "comparable_range_usd": {"low": 300000, "mid": 350000, "high": 400000},
  "summary": "valuation summary"
}
Return ONLY the JSON object."""

    prompt = (
        f"Estimate property value:\n"
        f"Type: {property_type}\nArea: {area_sqft} sq ft\nLocation: {location}\n"
        f"Bedrooms: {bedrooms}, Bathrooms: {bathrooms}\n"
        f"Year built: {year_built or 'unknown'}, Condition: {condition}\n"
        f"Amenities: {amenities or 'standard'}"
    )

    result = await ollama_chat(system=system, prompt=prompt)

    result.setdefault("estimated_value_usd", 0)
    result.setdefault("price_per_sqft_usd", 0)
    result.setdefault("market_trend", "stable")
    result.setdefault("confidence_level", "medium")
    result.setdefault("value_drivers", [])
    result.setdefault("comparable_range_usd", {"low": 0, "mid": 0, "high": 0})
    result.setdefault("summary", "Valuation complete.")

    logger.info("Valuation done — $%s for %s", result["estimated_value_usd"], location)
    return result


# ── 5. Weather Advisory ───────────────────────────────────────────────────────

@app.post("/api/weather/advisory", response_model=WeatherAdvisoryResponse)
async def weather_advisory(
    location: str = Form(...),
    activities: str = Form(default="general construction"),
    date_range: str = Form(default="next 7 days"),
):
    system = """You are a construction weather risk specialist.
Return ONLY a valid JSON object:
{
  "location": "city name",
  "current_conditions": "description of typical weather",
  "risk_level": "low or medium or high or extreme",
  "affected_activities": ["activity 1", "activity 2"],
  "recommendations": ["recommendation 1", "recommendation 2"],
  "work_safe_window": "e.g. 6 AM to 2 PM on clear days",
  "summary": "advisory summary"
}
Return ONLY the JSON object."""

    prompt = (
        f"Generate a construction weather advisory:\n"
        f"Location: {location}\n"
        f"Activities: {activities}\n"
        f"Period: {date_range}"
    )

    result = await ollama_chat(system=system, prompt=prompt)

    result.setdefault("location", location)
    result.setdefault("current_conditions", "unknown")
    result.setdefault("risk_level", "medium")
    result.setdefault("affected_activities", [])
    result.setdefault("recommendations", [])
    result.setdefault("work_safe_window", "To be determined")
    result.setdefault("summary", "Advisory generated.")

    logger.info("Weather advisory — location=%s risk=%s", location, result["risk_level"])
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
    image_b64 = None
    use_vision = False
    if file and file.filename:
        image_data = await read_and_validate_image(file)
        image_b64 = to_b64(image_data)
        use_vision = True

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
  "summary": "brief overall summary"
}
Return ONLY the JSON object."""

    prompt = (
        f"Generate a daily site report:\n"
        f"Site: {site_name}, Date: {date}\n"
        f"Activities: {activities_completed or 'not specified'}\n"
        f"Workers: {workers_present}, Equipment: {equipment_used or 'not specified'}\n"
        f"Issues: {issues or 'none'}, Notes: {notes or 'none'}"
    )

    result = await ollama_chat(system=system, prompt=prompt,
                               image_b64=image_b64, use_vision=use_vision)

    result.setdefault("date", date)
    result.setdefault("site_name", site_name)
    result.setdefault("overall_progress", "on-schedule")
    result.setdefault("sections", [])
    result.setdefault("issues_flagged", [])
    result.setdefault("next_day_plan", "Continue scheduled activities.")
    result.setdefault("summary", "Report generated.")

    logger.info("Report generated — site=%s date=%s", site_name, date)
    return result


# ── 7. AI Construction Assistant ──────────────────────────────────────────────

@app.post("/api/assistant/ask", response_model=AssistantResponse)
async def ask_assistant(
    question: str = Form(...),
    context: str = Form(default=""),
):
    system = """You are an expert AI construction assistant with deep knowledge in:
- Construction engineering and structural design
- Building codes and safety (OSHA, IBC, ACI, AISC)
- Materials science and cost estimation
- Project management and scheduling
- Real estate and property valuation

Return ONLY a valid JSON object:
{
  "answer": "detailed professional answer here",
  "follow_up_suggestions": [
    "related question 1?",
    "related question 2?",
    "related question 3?"
  ],
  "references": ["OSHA standard or code reference", "another reference"]
}
Return ONLY the JSON object."""

    prompt = (
        f"Question: {question}"
        + (f"\nProject context: {context}" if context else "")
    )

    result = await ollama_chat(system=system, prompt=prompt)

    result.setdefault("answer", "No answer generated.")
    result.setdefault("follow_up_suggestions", [])
    result.setdefault("references", [])

    logger.info("Assistant answered — question length=%d chars", len(question))
    return result
