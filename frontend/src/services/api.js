const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function request(endpoint, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, options);
  } catch {
    throw new Error(
      "Cannot reach the backend. Make sure the FastAPI server is running on port 8000."
    );
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}.`;
    try {
      const body = await response.json();
      if (body?.detail) {
        detail = typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail);
      }
    } catch { /* not JSON */ }
    throw new Error(detail);
  }
  return response.json();
}

// ── Image validation helper ───────────────────────────────────────────────────

const MAX_SIZE = 10 * 1024 * 1024;
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

export function validateImageFile(file) {
  if (!file) return "Please select an image.";
  if (!ALLOWED_TYPES.includes(file.type))
    return "Unsupported file type. Upload a JPG, PNG, or WEBP image.";
  if (file.size > MAX_SIZE)
    return "Image exceeds the 10 MB limit. Please choose a smaller file.";
  return null;
}

// ── Health & features ─────────────────────────────────────────────────────────

export const checkBackendHealth = () => request("/health");
export const getFeatures = () => request("/api/features");

// ── 1. Safety Monitoring ──────────────────────────────────────────────────────

export function analyzeSafety(file, context = "") {
  const err = validateImageFile(file);
  if (err) return Promise.reject(new Error(err));
  const form = new FormData();
  form.append("file", file);
  form.append("context", context);
  return request("/api/safety/analyze", { method: "POST", body: form });
}

// ── 2. Crack Detection ────────────────────────────────────────────────────────

export function analyzeCracks(file, context = "") {
  const err = validateImageFile(file);
  if (err) return Promise.reject(new Error(err));
  const form = new FormData();
  form.append("file", file);
  form.append("context", context);
  return request("/api/cracks/analyze", { method: "POST", body: form });
}

// ── 3. Project Planner ────────────────────────────────────────────────────────

export function generatePlan(fields) {
  const form = new FormData();
  Object.entries(fields).forEach(([k, v]) => form.append(k, v));
  return request("/api/planning/generate", { method: "POST", body: form });
}

// ── 4. Property Valuation ─────────────────────────────────────────────────────

export function estimateValuation(fields) {
  const form = new FormData();
  Object.entries(fields).forEach(([k, v]) => form.append(k, v));
  return request("/api/valuation/estimate", { method: "POST", body: form });
}

// ── 5. Weather Advisory ───────────────────────────────────────────────────────

export function getWeatherAdvisory(fields) {
  const form = new FormData();
  Object.entries(fields).forEach(([k, v]) => form.append(k, v));
  return request("/api/weather/advisory", { method: "POST", body: form });
}

// ── 6. Daily Site Reports ─────────────────────────────────────────────────────

export function generateReport(fields, imageFile = null) {
  const form = new FormData();
  Object.entries(fields).forEach(([k, v]) => form.append(k, v));
  if (imageFile) form.append("file", imageFile);
  return request("/api/reports/generate", { method: "POST", body: form });
}

// ── 7. AI Construction Assistant ──────────────────────────────────────────────

export function askAssistant(question, context = "") {
  const form = new FormData();
  form.append("question", question);
  form.append("context", context);
  return request("/api/assistant/ask", { method: "POST", body: form });
}
